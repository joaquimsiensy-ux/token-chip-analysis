#!/usr/bin/env python3
"""Production aggregator and validator for shared formal release evidence."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE.parent / "lib"))

from adversarial_review_runner import (
    AGGREGATE_SCHEMA,
    CLAIM_REVIEW_ROLES,
    LEDGER_SCHEMA,
    ROLES,
    V4_RERUN_HINT,
    build_required_refs,
    load_claim_registry,
    validate_blocker_linkage,
    validate_blocking_findings,
    validate_review_receipt,
    validate_review_ledger,
    validate_union_coverage,
)
from chain_registry import (evm_chain_id_for, evm_family, formal_ready,
                            recon_adapter_for, resolve_alias)
from anchor_point_contract import (LEGACY_FINAL_BLOCK_EDGE_KIND, V2_SCHEMA,
                                   V3_SCHEMA,
                                   balance_block_source_of,
                                   is_legacy_final_block_edge_point,
                                   strict_json_loads)
from producer_history import historical_producer_hashes
from receipt_validate import validate_receipt
from supply_truth_gate import (FORMAL_TOLERANCE_BPS_MAX,
                               WAIVER_TOLERANCE_BPS_CAP, decide,
                               parse_replay_stats)

FILES = ("accounting_mode.json", "reconciliation_report.json", "adversarial_review.json")
ACCOUNTING_PRODUCERS = {
    "evm": "scripts/evm/accounting_gate.py",
    "solana": "scripts/solana/accounting_gate_sol.py",
}
RECON_PRODUCERS = {
    "evm": {
        "balance": {"scripts/evm/verify_recon.py"},
        "supply": {"scripts/evm/verify_recon.py"},
        "supply_truth": {"scripts/lib/supply_truth_gate.py"},
        "time": {"scripts/lib/time_spotcheck.py"},
    },
    "solana": {
        "balance": {"scripts/solana/anchor_sampler.py"},
        "supply": {"scripts/solana/scan_token_accounts.py"},
        "supply_truth": {"scripts/lib/supply_truth_gate.py"},
        "time": {"scripts/solana/anchor_sampler.py"},
        "exact_reconcile": {"scripts/solana/replay_edges.py"},
    },
}
RECON_CHECK_KEYS = {
    "evm": ("balance", "supply", "supply_truth", "time"),
    "solana": ("supply", "balance", "supply_truth", "time", "exact_reconcile"),
}
SOLANA_FROZEN_OBSERVATION_BUNDLE = "data/solana_observation_bundle_frozen.json"
RECON_RUNNERS = {"scripts/report/reconciliation_report.py"}
ADVERSARIAL_RUNNERS = {"scripts/report/adversarial_review_runner.py"}
GMGN_DIVERGENCE_NOTE_SCHEMA = "gmgn-divergence-note/v1"
GMGN_DIVERGENCE_WARNING = "gmgn_divergence"
GMGN_EXPLANATION_MIN_CHARS = 30
GMGN_DIVERGENCE_CAUSES = {
    "gmgn_data_lag", "methodology_diff", "gmgn_upstream_error",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def regular(root, rel):
    root = Path(root).resolve()
    raw = root / str(rel)
    if raw.is_symlink():
        raise ValueError(f"evidence file invalid: {rel}")
    path = raw.resolve()
    path.relative_to(root)
    if not path.is_file():
        raise ValueError(f"evidence file invalid: {rel}")
    return path


def ref_ok(root, ref):
    if not isinstance(ref, dict):
        raise ValueError("evidence ref missing")
    path = regular(root, ref.get("path"))
    if ref.get("sha256") != sha(path):
        raise ValueError(f"evidence hash mismatch: {path.name}")
    return path


def repo_ref_ok(ref, allowed, label, allowed_hashes=None):
    if not isinstance(ref, dict):
        raise ValueError(f"{label} producer/runner ref missing")
    rel = str(ref.get("path", ""))
    if rel not in allowed:
        raise ValueError(f"{label} producer/runner path is not whitelisted: {rel}")
    path = (REPO / rel).resolve()
    path.relative_to(REPO)
    admitted = {sha(path)} if path.is_file() else set()
    if allowed_hashes is not None:
        admitted.update(allowed_hashes)
    if not path.is_file() or ref.get("sha256") not in admitted:
        raise ValueError(f"{label} producer/runner is not current repository script")
    return path


def chain_family(chain):
    family = recon_adapter_for(chain)
    if family not in RECON_PRODUCERS:
        raise ValueError(f"chain has no registered reconciliation adapter: {chain!r}")
    return family


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _reject_constant(value: str):
    raise ValueError(f"JSON non-finite number {value} is forbidden")


def _finite_number(value, *, integer=False, minimum=0) -> bool:
    if isinstance(value, bool) or not isinstance(value, int if integer else (int, float)):
        return False
    if isinstance(value, int):
        try:
            float(value)
        except OverflowError:
            return False
    if isinstance(value, float) and not math.isfinite(value):
        return False
    return value >= minimum


def _meaningful_text(value) -> bool:
    """文本至少含一个消费侧明确批准的可渲染字符。

    白名单覆盖 ASCII、拉丁补充/扩展、通用/CJK 标点、日文假名、CJK 统一表意文字、
    韩文音节与全角可打印形式。两侧刻意双写（独立重验纪律），改动须两处同步并过
    行为向量守卫。
    """
    if not isinstance(value, str):
        return False
    for char in value:
        point = ord(char)
        if 0x21 <= point <= 0x7E:
            return True
        if 0x00A1 <= point <= 0x024F and point != 0x00AD:
            return True
        if 0x2010 <= point <= 0x2027:
            return True
        if 0x3001 <= point <= 0x3029 or 0x3030 <= point <= 0x303D:
            return True
        if 0x3041 <= point <= 0x3096 or 0x309B <= point <= 0x30FF:
            return True
        if 0x3400 <= point <= 0x4DBF or 0x4E00 <= point <= 0x9FFF:
            return True
        if 0xAC00 <= point <= 0xD7A3:
            return True
        if 0xFF01 <= point <= 0xFF5E:
            return True
    return False


def _meaningful_length(value) -> int:
    """Count only the consumer whitelist's meaningful characters."""
    if not isinstance(value, str):
        return 0
    count = 0
    for char in value:
        point = ord(char)
        allowed = (
            0x21 <= point <= 0x7E
            or (0x00A1 <= point <= 0x024F and point != 0x00AD)
            or 0x2010 <= point <= 0x2027
            or 0x3001 <= point <= 0x3029
            or 0x3030 <= point <= 0x303D
            or 0x3041 <= point <= 0x3096
            or 0x309B <= point <= 0x30FF
            or 0x3400 <= point <= 0x4DBF
            or 0x4E00 <= point <= 0x9FFF
            or 0xAC00 <= point <= 0xD7A3
            or 0xFF01 <= point <= 0xFF5E
        )
        count += int(allowed)
    return count


def _strict_utc_datetime(value, label: str) -> datetime:
    try:
        if not isinstance(value, str) or len(value) != 20:
            raise ValueError
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError(f"{label} must use YYYY-MM-DDTHH:MM:SSZ") from exc
    _require(parsed <= datetime.now(timezone.utc) + timedelta(days=1),
             f"{label} later than now+1d")
    return parsed


def _validate_evidence_content(path: Path, label: str) -> None:
    content = path.read_bytes()
    _require(bool(content), f"{label} must not be empty")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return
    _require(_meaningful_text(text), f"{label} UTF-8 text lacks meaningful characters")


def _canonical_request_sha256(request: dict) -> str:
    canonical = json.dumps(request, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _utc_datetime(value, label: str) -> datetime:
    try:
        if not isinstance(value, str) or not value.endswith("Z"):
            raise ValueError
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
        if parsed.utcoffset() != timedelta(0):
            raise ValueError
        return parsed
    except ValueError as exc:
        raise ValueError(f"{label} invalid") from exc


def _validate_over_cap_approval(root, waiver_path: Path, waiver: dict, ref,
                                *, tolerance: int, replay_path: Path):
    approval_path = _bound_case_ref(
        root, ref, "tolerance waiver over-cap approval", base=waiver_path.parent)
    try:
        approval_text = approval_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(
            f"over-cap approval file read failed (channel failure): {exc}") from exc
    try:
        approval = json.loads(approval_text, parse_constant=_reject_constant)
    except (json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise ValueError(f"over-cap approval JSON invalid: {exc}") from exc
    required = {
        "schema", "request", "request_sha256", "nonce", "expires_at_utc",
        "user_approval", "reported_to_user", "approved_by", "user_decided_at_utc",
    }
    _require(isinstance(approval, dict)
             and all(key in approval and approval.get(key) is not None
                     for key in required),
             "over-cap approval schema or required fields incomplete")
    _require(approval.get("schema") == "over-cap-approval/v1",
             "over-cap approval schema invalid")
    request = approval.get("request")
    request_keys = {
        "target", "observed_diff_bps", "requested_tolerance_bps",
        "replay_stats", "reason",
    }
    _require(isinstance(request, dict) and set(request) == request_keys,
             "over-cap approval request fields invalid")
    request_observed = request.get("observed_diff_bps")
    request_tolerance = request.get("requested_tolerance_bps")
    _require(_finite_number(request_observed),
             "over-cap approval request.observed_diff_bps must be finite and non-negative")
    _require(_finite_number(request_tolerance, integer=True),
             "over-cap approval request.requested_tolerance_bps must be finite non-negative integer")
    recomputed_sha = _canonical_request_sha256(request)
    _require(approval.get("request_sha256") == recomputed_sha,
             "over-cap approval request_sha256 mismatch against independent recomputation")
    _require(request.get("target") == waiver.get("target"),
             "over-cap approval request.target mismatch")
    _require(request_observed == waiver.get("observed_diff_bps"),
             "over-cap approval request.observed_diff_bps mismatch")
    _require(request_tolerance == tolerance,
             "over-cap approval request.requested_tolerance_bps mismatch")
    _require(request.get("reason") == waiver.get("reason"),
             "over-cap approval request.reason mismatch")
    approval_replay = _bound_case_ref(
        root, request.get("replay_stats"),
        "over-cap approval request.replay_stats", base=approval_path.parent)
    _require(approval_replay == replay_path,
             "over-cap approval request.replay_stats does not bind waiver input")
    for label in ("nonce", "user_approval", "reported_to_user", "approved_by"):
        _require(_meaningful_text(approval.get(label)),
                 f"over-cap approval {label} invalid")
    decided_at = _utc_datetime(
        approval.get("user_decided_at_utc"),
        "over-cap approval user_decided_at_utc")
    expires_at = _utc_datetime(
        approval.get("expires_at_utc"), "over-cap approval expires_at_utc")
    now = datetime.now(timezone.utc)
    _require(decided_at <= now + timedelta(days=1),
             "over-cap approval user_decided_at_utc later than now+1d")
    _require(expires_at > decided_at,
             "over-cap approval expires_at_utc must follow user_decided_at_utc")
    _require(expires_at - decided_at <= timedelta(days=30),
             "over-cap approval lifetime must not exceed 30 days")
    _require(expires_at > now, "over-cap approval expired")
    return approval


def canonical_target(target):
    if not isinstance(target, dict) or set(target) != {"chain", "token", "as_of_block"}:
        raise ValueError("target must contain exactly chain/token/as_of_block")
    slot = target.get("as_of_block")
    if isinstance(slot, bool) or not isinstance(slot, int) or slot < 0:
        raise ValueError("target as_of_block/slot must be a non-negative integer")
    chain = resolve_alias(target.get("chain"))
    token = str(target.get("token") or "").strip()
    if chain in evm_family():
        token = token.lower()
    if not chain or not token:
        raise ValueError("target chain/token must be non-empty")
    return {"chain": chain, "token": token, "as_of_block": slot}


def _bound_case_ref(root, ref, label, *, base=None):
    if not isinstance(ref, dict) or not {"path", "size", "sha256"} <= set(ref):
        raise ValueError(f"{label} must bind path/size/sha256")
    case_root = Path(root).resolve()
    base = Path(base or case_root).resolve()
    raw = Path(str(ref.get("path") or ""))
    if not raw.parts or ".." in raw.parts:
        raise ValueError(f"{label} path must be a safe contained path")
    lexical = raw if raw.is_absolute() else base / raw
    # 外部记录可能使用 macOS /var、/tmp 或案根 alias；这些祖先别名必须先归一化，
    # 不能逐祖先把系统 symlink 当成案外逃逸。文件自身的 symlink 仍显式拒绝；
    # 中间 symlink 若指向案外，则会在 resolve 后的包含判定中被拒绝。
    if lexical.is_symlink():
        raise ValueError(f"{label} path is a symlink")
    try:
        path = lexical.resolve(strict=True)
        path.relative_to(case_root.resolve())
    except (OSError, ValueError) as exc:
        raise ValueError(f"{label} file invalid or escapes case root") from exc
    if not path.is_file():
        raise ValueError(f"{label} is not a regular file")
    _require(not isinstance(ref.get("size"), bool) and isinstance(ref.get("size"), int)
             and ref.get("size") == path.stat().st_size,
             f"{label} size mismatch")
    _require(ref.get("sha256") == sha(path), f"{label} sha256 mismatch")
    return path


MIGRATION_HINT = "存量案例须重跑对应生产者获取当前回执"
VERIFY_RECON_V3_HINT = "存量案须以 verify_recon v3 重跑对账"
TIME_SPOTCHECK_V3_HINT = "存量案须以 time_spotcheck v3 重跑时间抽查"


def _bound_replay_totals(root, receipt):
    """读收据 inputs 绑定的那份 replay_stats 实物，解出 (path, mint_total, burn_total)。

    上游 validate_receipt 已经对这个文件做过"存在＋size＋sha256"三验，所以这里直接读
    内容即可；读不出 mint/burn（旧格式、字段缺失）一律 fail-closed，不放行。

    实物**必须落在案根内**（N-1）：上游三验只管"这个路径上的文件与收据登记的哈希一致"，
    不管它在哪。绑一份案外伪造账本同样自洽，而案根里那本真账没人再看一眼——
    伪造件不进案目录，就不会出现在 audit_input_manifest 的清单里、人工翻案子时也看不见，
    等于绕开了本仓"内容绑定"防线的全部可见性。强制在案根内之后，伪造者只能覆盖案内那份
    真账本，那会立刻把 balance/supply 两查收据的输入哈希打炸，一望即知。
    resolve() 已经跟完符号链接，所以"案内软链指向案外"也会在这里被拦下。
    """
    inputs = receipt.get("inputs") or {}
    replay_input = inputs.get("replay_stats")
    _require(isinstance(replay_input, dict),
             "supply_truth receipt must bind replay_stats input")
    shown = Path(str(replay_input.get("path") or ""))
    # A-3：收据可记案根相对路径（可搬家）；相对路径基于案根解析，绝对路径照旧收紧。
    replay_path = (shown if shown.is_absolute() else Path(root) / shown).resolve()
    try:
        replay_path.relative_to(Path(root).resolve())
    except ValueError as exc:
        raise ValueError(
            f"收据绑定的 replay_stats 实物不在当前案根内——{MIGRATION_HINT}"
            "（对账实物必须与收据同案；存量案或整目录复制过的案子，收据里记的是老绝对路径）"
        ) from exc
    try:
        stats = json.loads(replay_path.read_text(encoding="utf-8"))
        if not isinstance(stats, dict):
            raise TypeError("replay_stats 不是 JSON 对象")
        mint_total, burn_total = parse_replay_stats(stats)
    except Exception as exc:
        raise ValueError(
            f"supply_truth 绑定的 replay_stats 解不出 mint/burn: {exc}；"
            f"{MIGRATION_HINT}") from exc
    return replay_path, mint_total, burn_total


def _validate_tolerance_policy(root, receipt, target):
    """独立重算 primary 结论，并重验 formal 容差与 waiver 输入绑定。"""
    try:
        replay_net = int(str(receipt.get("replay_net")))
        onchain = int(str(receipt.get("onchain_total_supply")))
    except (TypeError, ValueError) as exc:
        raise ValueError("supply_truth primary inputs are not integers") from exc
    tolerance = receipt.get("tolerance_bps")
    _require(not isinstance(tolerance, bool) and isinstance(tolerance, int)
             and tolerance >= 0,
             "supply_truth formal tolerance_bps must be a non-negative integer")
    recomputed_verdict, _, recomputed_diff_bps = decide(replay_net, onchain, tolerance)
    _require(receipt.get("primary_verdict") == recomputed_verdict,
             "supply_truth primary_verdict 与 decide 独立重算值不一致")

    # 消费侧不能只拿收据自报的三个数互相印证：replay_net 必须对得上案根里那份被哈希
    # 绑定的 replay_stats 实物，否则改一个数就能绕开整套容差钳制与 waiver（F-A）。
    replay_path, stats_mint, stats_burn = _bound_replay_totals(root, receipt)
    _require(stats_mint - stats_burn == replay_net,
             f"supply_truth replay_net 与绑定 replay_stats 实物的 mint−burn 不一致；"
             f"{MIGRATION_HINT}")

    inputs = receipt.get("inputs") or {}
    waiver_input = inputs.get("tolerance_waiver")
    if tolerance > FORMAL_TOLERANCE_BPS_MAX:
        _require(isinstance(waiver_input, dict),
                 f"supply_truth formal tolerance above "
                 f"{FORMAL_TOLERANCE_BPS_MAX}bps lacks tolerance waiver")
    if waiver_input is None:
        return

    waiver_shown = Path(str(waiver_input.get("path") or ""))
    waiver_path = (waiver_shown if waiver_shown.is_absolute()
                   else Path(root) / waiver_shown).resolve()
    try:
        waiver_path.relative_to(Path(root).resolve())
    except ValueError as exc:
        raise ValueError(
            f"收据记录的 tolerance waiver 路径不在当前案根内——{MIGRATION_HINT}"
            "（存量案或整目录复制过的案子，收据里记的是老绝对路径，不是 waiver 放错了地方）"
        ) from exc
    # 读不动＝通道故障，JSON 坏了＝内容不合法，两类别再顶着同一句"JSON invalid"（F-D）。
    try:
        waiver_text = waiver_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(
            f"tolerance waiver 文件读取失败（通道故障，非政策问题）: {exc}") from exc
    try:
        waiver = json.loads(waiver_text, parse_constant=_reject_constant)
    except (json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise ValueError(f"tolerance waiver JSON invalid: {exc}") from exc
    required = {
        "schema", "approved_tolerance_bps", "approved_by", "user_decided_at_utc",
        "target", "replay_stats", "evidence_refs", "reason", "observed_diff_bps",
    }
    _require(isinstance(waiver, dict)
             and all(key in waiver and waiver.get(key) not in (None, "", [])
                     for key in required),
             "tolerance waiver schema or required fields incomplete")
    _require(waiver.get("schema") == "tolerance-waiver/v1",
             "tolerance waiver schema invalid")
    approved = waiver.get("approved_tolerance_bps")
    _require(_finite_number(approved, integer=True),
             "tolerance waiver approved_tolerance_bps invalid")
    observed_diff = waiver.get("observed_diff_bps")
    _require(_finite_number(observed_diff),
             "tolerance waiver observed_diff_bps invalid")
    # 本次实际偏差必须落在裁决人签字时看到的偏差之内；比较值取自同一个 decide()，
    # 与生产侧同源，不会在浮点边界上分叉（F-E）。
    actual_diff = float(0.0 if recomputed_diff_bps is None else recomputed_diff_bps)
    _require(math.isfinite(actual_diff),
             "supply_truth recomputed actual diff must be finite")
    _require(actual_diff <= float(observed_diff),
             "supply_truth 实际偏差超过 tolerance waiver 记录的 observed_diff_bps"
             "——裁决人没见过这么大的偏差，该收据失效须重新人工裁决")
    _require(_meaningful_text(waiver.get("approved_by")),
             "tolerance waiver approved_by invalid")
    _utc_datetime(waiver.get("user_decided_at_utc"),
                  "tolerance waiver user_decided_at_utc")
    _require(waiver.get("target") == target,
             "tolerance waiver target mismatch")
    _require(_meaningful_text(waiver.get("reason")),
             "tolerance waiver reason invalid")
    waiver_replay = _bound_case_ref(
        root, waiver.get("replay_stats"), "tolerance waiver replay_stats",
        base=waiver_path.parent)
    _require(waiver_replay == replay_path,
             "tolerance waiver replay_stats does not bind receipt input")
    evidence_refs = waiver.get("evidence_refs")
    _require(isinstance(evidence_refs, list) and bool(evidence_refs),
             "tolerance waiver evidence_refs invalid")
    evidence_paths = []
    evidence_shas = []
    replay_sha = sha(waiver_replay)
    for index, ref in enumerate(evidence_refs):
        label = f"tolerance waiver evidence_refs[{index}]"
        evidence_path = _bound_case_ref(
            root, ref, label,
            base=waiver_path.parent)
        evidence_paths.append(evidence_path)
        _validate_evidence_content(evidence_path, label)
        evidence_sha = sha(evidence_path)
        evidence_shas.append(evidence_sha)
        # 人工核对证据不能就是被豁免的那份输入自身（F-E）。
        _require(evidence_path != waiver_replay and evidence_sha != replay_sha,
                 f"tolerance waiver evidence_refs[{index}] 不得与 replay_stats 内容相同")
    over_cap_ref = waiver.get("over_cap_approval")
    over_cap = any(value > WAIVER_TOLERANCE_BPS_CAP for value in
                   (approved, observed_diff, tolerance, actual_diff))
    _require(not over_cap or over_cap_ref is not None,
             f"tolerance waiver above {WAIVER_TOLERANCE_BPS_CAP}bps lacks over-cap approval")
    if over_cap_ref is not None:
        approval_path = _bound_case_ref(
            root, over_cap_ref, "tolerance waiver over-cap approval",
            base=waiver_path.parent)
        _require(approval_path not in evidence_paths
                 and sha(approval_path) not in evidence_shas,
                 "tolerance waiver evidence_refs content must be independent of over-cap approval")
        approval_input = inputs.get("over_cap_approval")
        _require(isinstance(approval_input, dict),
                 "supply_truth receipt inputs missing over_cap_approval")
        receipt_approval_path = _bound_case_ref(
            root, approval_input, "supply_truth receipt over_cap_approval")
        _require(receipt_approval_path == approval_path,
                 "supply_truth receipt over_cap_approval does not bind waiver same file")
        _validate_over_cap_approval(
            root, waiver_path, waiver, over_cap_ref, tolerance=tolerance,
            replay_path=waiver_replay)
    _require(tolerance <= approved,
             "supply_truth tolerance exceeds waiver approved_tolerance_bps")


def _bound_json_input(root, receipt, name, label):
    ref = (receipt.get("inputs") or {}).get(name)
    path = _bound_case_ref(root, ref, label)
    try:
        value = json.loads(path.read_text(encoding="utf-8"),
                           parse_constant=_reject_constant)
    except (OSError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise ValueError(f"{label} JSON invalid: {exc}") from exc
    return path, value


def _integer(value, label):
    if isinstance(value, bool) or isinstance(value, float):
        raise ValueError(f"{label} must be an integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be an integer") from exc
    if str(value).strip() != str(parsed):
        raise ValueError(f"{label} must use canonical integer spelling")
    return parsed


def _decimal(value, label):
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be decimal") from exc
    if not parsed.is_finite():
        raise ValueError(f"{label} must be finite")
    return parsed


def _recon_bound_reality(root, receipt, target):
    _, config = _bound_json_input(root, receipt, "config", "verify_recon config")
    _, balances_raw = _bound_json_input(
        root, receipt, "balances", "verify_recon balances")
    _, stats = _bound_json_input(
        root, receipt, "replay_stats", "verify_recon replay_stats")
    _require(isinstance(config, dict), "verify_recon config must be an object")
    _require(isinstance(balances_raw, dict) and bool(balances_raw),
             "verify_recon balances must be a non-empty object")
    _require(isinstance(stats, dict), "verify_recon replay_stats must be an object")
    config_token = str(config.get("token") or "").lower()
    _require(config_token == str(target["token"]).lower(),
             "verify_recon config token does not match target token")
    decimals = config.get("decimals")
    _require(isinstance(decimals, int) and not isinstance(decimals, bool) and decimals >= 0,
             "verify_recon config decimals invalid")
    supply_human = _decimal(config.get("total_supply_human"),
                            "verify_recon total_supply_human")
    nominal = int(supply_human * (Decimal(10) ** decimals))
    balances = {}
    for raw_address, raw_value in balances_raw.items():
        address = str(raw_address).lower()
        _require(bool(address) and address not in balances,
                 f"verify_recon balances duplicate/empty address: {address!r}")
        balances[address] = _integer(raw_value, f"verify_recon balance {address}")
    stats_end = stats.get("max_block")
    if stats_end is None:
        stats_end = stats.get("last_block")
    _require(_integer(stats_end, "verify_recon replay_stats cutoff")
             == canonical_target(target)["as_of_block"],
             "verify_recon replay_stats cutoff does not match target.as_of_block")
    try:
        mint, burn = parse_replay_stats(stats)
    except Exception as exc:
        raise ValueError(f"verify_recon replay_stats mint/burn invalid: {exc}") from exc
    balance_sum = sum(balances.values())
    negatives = sorted(address for address, value in balances.items() if value < 0)
    closed = mint == nominal and balance_sum == mint and not negatives
    return balances, {
        "mint_total_raw": str(mint), "burn_total_raw": str(burn),
        "nominal_supply_raw": str(nominal), "balance_sum_raw": str(balance_sum),
        "negative_count": len(negatives), "negative_addresses": negatives,
        "closed": closed,
    }, nominal


def _validate_recon_supply(observations, expected):
    shown = observations.get("supply_closure")
    _require(isinstance(shown, dict), "supply_closure missing")
    for field, value in expected.items():
        _require(shown.get(field) == value,
                 f"supply_closure {field} differs from bound artifacts")


def _validate_balance_transcript(root, receipt, rows, target):
    _, transcript = _bound_json_input(
        root, receipt, "transcript", "verify_recon transcript")
    _require(isinstance(transcript, list) and len(transcript) == len(rows),
             "verify_recon transcript length does not match balance rows")
    token = str(target["token"]).lower()
    block = hex(canonical_target(target)["as_of_block"])
    for seq, (call, row) in enumerate(zip(transcript, rows)):
        _require(isinstance(call, dict) and call.get("seq") == seq,
                 f"verify_recon transcript seq {seq} is not continuous")
        _require(call.get("method") == "eth_call",
                 f"verify_recon transcript method {seq} must be eth_call")
        address = str(row.get("address") or "").lower()
        data = "0x70a08231" + "0" * 24 + address.replace("0x", "")
        _require(call.get("params") == [{"to": token, "data": data}, block],
                 f"verify_recon transcript params {seq} do not bind row address/block")
        raw = call.get("result")
        _require(isinstance(raw, str) and raw.startswith("0x") and len(raw) > 2,
                 f"verify_recon transcript result {seq} is not hex")
        try:
            chain_raw = int(raw, 16)
        except ValueError as exc:
            raise ValueError(
                f"verify_recon transcript result {seq} is not hex") from exc
        _require(str(chain_raw) == row.get("chain_raw"),
                 f"verify_recon transcript result {seq} differs from row.chain_raw")


def _validate_recon_balance(root, receipt, observations, balances, target):
    shown = observations.get("balance_reconciliation")
    _require(isinstance(shown, dict), "balance_reconciliation missing")
    requested = shown.get("requested_top_n")
    _require(isinstance(requested, int) and not isinstance(requested, bool)
             and requested > 0,
             "balance_reconciliation requested_top_n must be a positive integer")
    _require(shown.get("selection") == "top_n_then_skip_sinks",
             "balance_reconciliation selection semantics invalid")
    rows = shown.get("rows")
    _require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows),
             "balance_reconciliation rows invalid")
    from supply_semantics import DEAD, ZERO
    expected_addresses = [
        address for address, _ in
        sorted(balances.items(), key=lambda item: (-item[1], item[0]))[:requested]
        if address not in {ZERO, DEAD}
    ]
    addresses = [str(row.get("address") or "").lower() for row in rows]
    _require(addresses == expected_addresses,
             "balance_reconciliation address sequence differs from bound balances")
    counts = Counter()
    for index, (row, address) in enumerate(zip(rows, addresses)):
        _require(row.get("replay_raw") == str(balances[address]),
                 f"balance row {index} replay_raw differs from bound balances")
        status = row.get("status")
        _require(status in {"OK", "MISMATCH", "RPC_ERROR"},
                 f"balance row {index} status invalid")
        counts[status] += 1
        if status == "RPC_ERROR":
            _require("chain_raw" not in row and "diff_raw" not in row,
                     f"balance row {index} RPC_ERROR carries chain values")
            continue
        chain_raw = _integer(row.get("chain_raw"), f"balance row {index} chain_raw")
        diff_raw = chain_raw - balances[address]
        _require(row.get("diff_raw") == str(diff_raw),
                 f"balance row {index} diff_raw is not recomputed")
        _require(status == ("OK" if diff_raw == 0 else "MISMATCH"),
                 f"balance row {index} status is inconsistent with diff_raw")
    _require(shown.get("checked") == len(rows),
             "balance_reconciliation checked differs from rows")
    _require(shown.get("matched") == counts["OK"],
             "balance_reconciliation matched differs from rows")
    _require(shown.get("mismatched") == counts["MISMATCH"],
             "balance_reconciliation mismatched differs from rows")
    _require(shown.get("rpc_errors") == counts["RPC_ERROR"],
             "balance_reconciliation rpc_errors differs from rows")
    _require(not counts["MISMATCH"] and not counts["RPC_ERROR"],
             "PASS balance receipt contains MISMATCH/RPC_ERROR row")
    _require(bool(rows), "balance_reconciliation must check at least one non-sink row")
    _validate_balance_transcript(root, receipt, rows, target)


def _validate_gmgn_divergences(value, label):
    _require(isinstance(value, list), f"{label} must be an ordered list")
    normalized = []
    seen = set()
    keys = {"address", "gmgn_pct", "replay_pct", "diff_pp"}
    for index, row in enumerate(value):
        _require(isinstance(row, dict) and set(row) == keys,
                 f"{label}[{index}] fields invalid")
        address = row.get("address")
        _require(isinstance(address, str) and bool(address) and address == address.lower(),
                 f"{label}[{index}].address invalid")
        _require(address not in seen, f"{label} duplicate address: {address}")
        seen.add(address)
        item = {"address": address}
        for key in ("gmgn_pct", "replay_pct", "diff_pp"):
            raw = row.get(key)
            parsed = _decimal(raw, f"{label}[{index}].{key}")
            _require(isinstance(raw, str) and str(parsed) == raw,
                     f"{label}[{index}].{key} must use canonical Decimal spelling")
            item[key] = raw
        normalized.append(item)
    return normalized


def _validate_gmgn_divergence_note(case_root, note_path, target, input_refs,
                                   divergences):
    """Consumer-side independent validator for gmgn-divergence-note/v1."""
    root = Path(case_root).resolve()
    path = Path(note_path)
    try:
        path = path.resolve(strict=True)
        relative = path.relative_to(root)
    except (OSError, ValueError) as exc:
        raise ValueError("GMGN divergence note escapes case root") from exc
    lexical = root
    for part in relative.parts:
        lexical = lexical / part
        _require(not lexical.is_symlink(), "GMGN divergence note path is a symlink")
    _require(path.is_file(), "GMGN divergence note is not a regular file")
    try:
        note = json.loads(path.read_text(encoding="utf-8"),
                          parse_constant=_reject_constant)
    except (OSError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise ValueError(f"GMGN divergence note JSON invalid: {exc}") from exc
    required = {
        "schema", "request", "request_sha256", "findings", "conclusion",
        "investigator", "investigated_at_utc",
    }
    _require(isinstance(note, dict) and set(note) == required,
             "GMGN divergence note fields invalid")
    _require(note.get("schema") == GMGN_DIVERGENCE_NOTE_SCHEMA,
             f"GMGN divergence note schema must be {GMGN_DIVERGENCE_NOTE_SCHEMA}")
    request = note.get("request")
    _require(isinstance(request, dict)
             and set(request) == {"target", "inputs_sha256", "divergences"},
             "GMGN divergence note request fields invalid")
    _require(request.get("target") == target,
             "GMGN divergence note request.target mismatch")
    hashes = request.get("inputs_sha256")
    hash_keys = {"config", "balances", "replay_stats", "gmgn"}
    _require(isinstance(hashes, dict) and set(hashes) == hash_keys,
             "GMGN divergence note inputs_sha256 fields invalid")
    for key in sorted(hash_keys):
        shown = hashes.get(key)
        expected = (input_refs.get(key) or {}).get("sha256")
        _require(isinstance(shown, str) and len(shown) == 64
                 and all(char in "0123456789abcdef" for char in shown)
                 and shown == expected,
                 f"GMGN divergence note inputs_sha256.{key} mismatch")
    shown_divergences = _validate_gmgn_divergences(
        request.get("divergences"), "GMGN divergence note request.divergences")
    expected_divergences = _validate_gmgn_divergences(
        divergences, "recomputed GMGN divergences")
    _require(shown_divergences == expected_divergences,
             "GMGN divergence note does not cover recomputed divergences")
    _require(note.get("request_sha256") == _canonical_request_sha256(request),
             "GMGN divergence note request_sha256 mismatch")
    findings = note.get("findings")
    _require(isinstance(findings, list) and len(findings) == len(expected_divergences),
             "GMGN divergence note findings coverage invalid")
    for index, (finding, divergence) in enumerate(zip(findings, expected_divergences)):
        _require(isinstance(finding, dict) and set(finding) in (
            {"address", "cause", "explanation"},
            {"address", "cause", "explanation", "evidence_refs"}),
            f"GMGN divergence note findings[{index}] fields invalid")
        _require(finding.get("address") == divergence["address"],
                 f"GMGN divergence note findings[{index}] address mismatch")
        _require(finding.get("cause") in GMGN_DIVERGENCE_CAUSES,
                 f"GMGN divergence note findings[{index}].cause invalid")
        explanation = finding.get("explanation")
        _require(_meaningful_text(explanation)
                 and _meaningful_length(explanation) >= GMGN_EXPLANATION_MIN_CHARS,
                 f"GMGN divergence note findings[{index}].explanation too short")
        if "evidence_refs" in finding:
            refs = finding.get("evidence_refs")
            _require(isinstance(refs, list),
                     f"GMGN divergence note findings[{index}].evidence_refs invalid")
            for ref_index, ref in enumerate(refs):
                _bound_case_ref(
                    root, ref,
                    f"GMGN divergence note findings[{index}].evidence_refs[{ref_index}]",
                    base=path.parent)
    conclusion = note.get("conclusion")
    _require(_meaningful_text(conclusion) and "重放数据经查证无误" in conclusion,
             "GMGN divergence note conclusion lacks required attestation")
    _require(_meaningful_text(note.get("investigator")),
             "GMGN divergence note investigator invalid")
    _strict_utc_datetime(note.get("investigated_at_utc"),
                         "GMGN divergence note investigated_at_utc")
    return note


def _validate_recon_gmgn(root, receipt, observations, balances, nominal):
    gmgn_ref = (receipt.get("inputs") or {}).get("gmgn")
    gmgn_path = _bound_case_ref(root, gmgn_ref, "verify_recon gmgn")
    expected = []
    seen = set()
    try:
        with gmgn_path.open(newline="", encoding="utf-8") as stream:
            source_rows = list(csv.DictReader(stream))[:10]
    except (OSError, csv.Error) as exc:
        raise ValueError(f"verify_recon gmgn CSV invalid: {exc}") from exc
    for index, source in enumerate(source_rows):
        address = str(source.get("address") or "").lower()
        if not address:
            continue
        _require(address not in seen, f"verify_recon gmgn duplicate address: {address}")
        seen.add(address)
        fraction = _decimal(source.get("pct") or "0", f"gmgn row {index} pct")
        gmgn_pct = fraction * Decimal(100)
        replay_pct = (Decimal(balances.get(address, 0)) * Decimal(100)
                      / Decimal(nominal) if nominal else Decimal(0))
        diff = abs(gmgn_pct - replay_pct)
        expected.append({
            "address": address, "gmgn_pct": str(gmgn_pct),
            "replay_pct": str(replay_pct), "diff_pp": str(diff),
            "status": "OK" if diff < Decimal("0.15") else "DIFF",
        })
    shown = observations.get("gmgn_comparison")
    _require(isinstance(shown, dict), "gmgn_comparison missing")
    _require(_decimal(shown.get("tolerance_pp"), "gmgn tolerance_pp")
             == Decimal("0.15"), "gmgn tolerance_pp invalid")
    rows = shown.get("rows")
    _require(rows == expected, "gmgn rows differ from bound CSV/balances")
    _require(shown.get("checked") == len(expected),
             "gmgn checked differs from bound CSV")
    _require(shown.get("diff_count") == sum(row["status"] == "DIFF" for row in expected),
             "gmgn diff_count differs from recomputed rows")
    divergences = [
        {key: row[key] for key in ("address", "gmgn_pct", "replay_pct", "diff_pp")}
        for row in expected if row["status"] == "DIFF"
    ]
    warnings = receipt.get("warnings")
    _require(isinstance(warnings, list)
             and all(item == GMGN_DIVERGENCE_WARNING for item in warnings)
             and len(warnings) == len(set(warnings)),
             "verify_recon warnings must be a duplicate-free known-string array")
    _require((GMGN_DIVERGENCE_WARNING in warnings) == bool(divergences),
             "verify_recon warnings do not interlock with recomputed GMGN divergences")
    inputs = receipt.get("inputs") or {}
    if divergences:
        note_ref = inputs.get("divergence_note")
        _require(isinstance(note_ref, dict),
                 "recomputed GMGN divergence requires inputs.divergence_note")
        note_path = _bound_case_ref(root, note_ref, "GMGN divergence note")
        _validate_gmgn_divergence_note(
            root, note_path, receipt.get("target"), inputs, divergences)
    else:
        _require("divergence_note" not in inputs,
                 "zero GMGN divergence must not bind inputs.divergence_note")
    return divergences


def _validate_evm_reconciliation_receipt(root, receipt, target):
    observations = receipt.get("observations")
    _require(isinstance(observations, dict), "verify_recon observations missing")
    balances, supply, nominal = _recon_bound_reality(root, receipt, target)
    _validate_recon_supply(observations, supply)
    _validate_recon_balance(root, receipt, observations, balances, target)
    _validate_recon_gmgn(root, receipt, observations, balances, nominal)


def _plan_point(row, family, plan):
    schema = plan.get("schema")
    if schema == V3_SCHEMA:
        source = balance_block_source_of(row, family, plan)
        if source is not None:
            block = (row["day_end_block"] if source == "day_end_block"
                     else plan.get("final_block"))
            return ("balance", row.get("kind"), row.get("addr"),
                    block, str(row.get("expected_balance_raw")))
        if row.get("block") is None:
            raise ValueError("time plan tx point missing block")
        return ("tx", row.get("kind"), row.get("tx"), row.get("from"),
                row.get("to"), row.get("block"), str(row.get("expected_value_raw")))
    elif schema == V2_SCHEMA:
        if row.get("expected_balance_raw") is not None and row.get("addr"):
            legacy_edge = is_legacy_final_block_edge_point(row, family, plan)
            if row.get("kind") == LEGACY_FINAL_BLOCK_EDGE_KIND and not legacy_edge:
                raise ValueError("time plan contains malformed legacy final-block edge point")
            block = row.get("day_end_block")
            if block is None:
                if not legacy_edge:
                    raise ValueError("time plan balance point missing day_end_block")
                block = plan.get("final_block")
            return ("balance", row.get("kind"), row.get("addr"),
                    block, str(row.get("expected_balance_raw")))
        if row.get("tx") and row.get("expected_value_raw") is not None:
            if row.get("kind") == LEGACY_FINAL_BLOCK_EDGE_KIND:
                raise ValueError("time plan tx point carries legacy final-block edge kind")
            if row.get("block") is None:
                raise ValueError("time plan tx point missing block")
            return ("tx", row.get("kind"), row.get("tx"), row.get("from"),
                    row.get("to"), row.get("block"), str(row.get("expected_value_raw")))
        raise ValueError("time plan contains unclassifiable point")
    else:
        raise ValueError(f"unsupported plan schema: {schema!r}")


def _time_row_point(row):
    if row.get("type") == "balance":
        return ("balance", row.get("kind"), row.get("addr"), row.get("block"),
                str(row.get("expect_raw")))
    if row.get("type") == "tx":
        return ("tx", row.get("kind"), row.get("tx"), row.get("from"),
                row.get("to"), row.get("block"), str(row.get("expect_raw")))
    raise ValueError("time row type invalid")


def _tx_transcript_matches(raw_receipt, row, token):
    if not isinstance(raw_receipt, dict):
        return False, 0
    try:
        receipt_block = int(raw_receipt.get("blockNumber", "0x0"), 16)
        expected_value = _integer(row.get("expect_raw"), "time tx expect_raw")
    except (TypeError, ValueError):
        return False, 0
    topic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    expected_from = str(row.get("from") or "").lower().replace("0x", "").rjust(40, "0")[-40:]
    expected_to = str(row.get("to") or "").lower().replace("0x", "").rjust(40, "0")[-40:]
    hit = False
    for log in raw_receipt.get("logs") or []:
        topics = log.get("topics") or [] if isinstance(log, dict) else []
        try:
            matches = (str(log.get("address") or "").lower() == token
                       and len(topics) >= 3 and str(topics[0]).lower() == topic
                       and str(topics[1])[-40:].lower() == expected_from
                       and str(topics[2])[-40:].lower() == expected_to
                       and int(log.get("data", "0x0"), 16) == expected_value)
        except (TypeError, ValueError):
            matches = False
        if matches:
            hit = True
            break
    if row.get("block") is None:
        raise ValueError("time receipt tx row missing block")
    block_ok = receipt_block == row.get("block")
    return hit and block_ok, receipt_block


def _validated_time_plan_authority(root, receipt, target):
    """Independently bind the consumed plan to its anchor_plan authority chain."""
    try:
        plan_path, _ = _bound_json_input(root, receipt, "plan", "time plan")
        plan_receipt_path, _ = _bound_json_input(
            root, receipt, "plan_receipt", "time plan receipt")
        plan = strict_json_loads(
            plan_path.read_text(encoding="utf-8"), parse_constant=_reject_constant)
        plan_receipt = strict_json_loads(
            plan_receipt_path.read_text(encoding="utf-8"),
            parse_constant=_reject_constant)
        input_ref = (receipt.get("inputs") or {}).get("input")
        input_path = _bound_case_ref(root, input_ref, "time merged input")
        _require(isinstance(plan, dict) and isinstance(plan_receipt, dict),
                 "plan/receipt must be objects")

        plan_schema = plan.get("schema")
        allowed_plan_schemas = {V2_SCHEMA, V3_SCHEMA}
        _require(plan_schema in allowed_plan_schemas,
                 "plan schema must be anchor-plan/v2 or anchor-plan/v3")
        historical_hashes = historical_producer_hashes(
            "scripts/lib/anchor_plan.py", plan_schema)
        plan_errors = validate_receipt(
            plan_receipt, case_root=root,
            allowed_producer_hashes=historical_hashes)
        _require(not plan_errors, f"plan receipt envelope invalid: {plan_errors[:1]}")
        _require(plan_receipt.get("schema") == "anchor-plan-receipt/v2"
                 and plan_receipt.get("verdict") == "PASS"
                 and plan_receipt.get("exit_code") == 0,
                 "plan receipt schema/verdict invalid")
        producer = plan_receipt.get("producer")
        repo_ref_ok(producer, {"scripts/lib/anchor_plan.py"}, "time anchor plan",
                    allowed_hashes=historical_hashes)

        _require(plan.get("target") == plan_receipt.get("target"),
                 "plan target differs from signed receipt target")
        _require(canonical_target(plan_receipt.get("target")) == canonical_target(target),
                 "signed target differs from time receipt target")
        signed_target = plan["target"]
        _require(plan.get("chain") == signed_target.get("chain")
                 and plan.get("token") == signed_target.get("token")
                 and plan.get("final_block") == signed_target.get("as_of_block"),
                 "plan compatibility target fields diverge")
        _require(plan.get("producer") == producer,
                 "plan producer differs from signed receipt producer")

        identity = plan_receipt.get("input_identity")
        _require(isinstance(identity, dict) and plan.get("input") == identity,
                 "plan input identity differs from signed receipt")
        identity_path = _bound_case_ref(root, identity, "time plan input identity")
        _require(identity_path == input_path,
                 "signed input identity is not the time receipt input object")

        manifest = (plan_receipt.get("inputs") or {}).get("input_manifest")
        _bound_case_ref(root, manifest, "time plan input manifest")
        _require(isinstance(manifest, dict) and plan.get("input_manifest") == manifest,
                 "plan input manifest differs from signed receipt binding")

        output = plan_receipt.get("output")
        output_path = _bound_case_ref(root, output, "time signed plan output")
        _require(output_path == plan_path,
                 "signed output is not the consumed plan object")
        _require(plan_receipt.get("plan_schema") in allowed_plan_schemas
                 and plan_receipt.get("plan_schema") == plan_schema,
                 "plan receipt plan_schema mismatch")
        generated_at = plan.get("generated_at")
        _require(isinstance(generated_at, str) and bool(generated_at)
                 and plan_receipt.get("generated_at") == generated_at,
                 "plan generated_at differs from signed receipt")
        for field in ("matrix_points", "forced_points"):
            _require(isinstance(plan.get(field), list), f"plan {field} invalid")
        point_count = sum(len(plan[field]) for field in ("matrix_points", "forced_points"))
        probe_count = plan_receipt.get("probe_count")
        _require(not isinstance(probe_count, bool) and isinstance(probe_count, int)
                 and probe_count == point_count,
                 "plan receipt probe_count differs from consumed plan")
        return plan
    except ValueError as exc:
        raise ValueError(f"time plan authority chain broken: {exc}") from exc


def _validate_time_receipt(root, receipt, target):
    plan = _validated_time_plan_authority(root, receipt, target)
    expected_points = []
    for field in ("matrix_points", "forced_points"):
        rows = plan.get(field)
        _require(isinstance(rows, list), f"time plan {field} invalid")
        expected_points.extend(_plan_point(row, field, plan) for row in rows)
    rows = receipt.get("rows")
    _require(isinstance(rows, list) and bool(rows)
             and all(isinstance(row, dict) for row in rows), "time rows invalid")
    _require(Counter(_time_row_point(row) for row in rows) == Counter(expected_points),
             "time rows do not correspond one-to-one with plan points")
    _, transcript = _bound_json_input(root, receipt, "transcript", "time transcript")
    _require(isinstance(transcript, list) and len(transcript) == len(rows),
             "time transcript length differs from rows")
    counts = Counter()
    token = str(target["token"]).lower()
    for seq, (row, call) in enumerate(zip(rows, transcript)):
        _require(isinstance(call, dict) and call.get("seq") == seq,
                 f"time transcript seq {seq} is not continuous")
        status = row.get("status")
        _require(status in {"OK", "MISMATCH", "RPC_ERR"},
                 f"time row {seq} status invalid")
        counts[status] += 1
        if row.get("type") == "balance":
            data = "0x70a08231" + str(row["addr"]).lower().replace("0x", "").rjust(64, "0")
            _require(call.get("method") == "eth_call"
                     and call.get("params") == [{"to": token, "data": data}, hex(row["block"])],
                     f"time balance transcript params {seq} mismatch")
            raw = call.get("result")
            _require(isinstance(raw, str) and raw.startswith("0x"),
                     f"time balance transcript result {seq} invalid")
            try:
                chain_raw = int(raw, 16)
            except ValueError as exc:
                raise ValueError(f"time balance transcript result {seq} invalid") from exc
            expected_raw = _integer(row.get("expect_raw"), f"time row {seq} expect_raw")
            _require(row.get("chain_raw") == str(chain_raw)
                     and row.get("diff_raw") == str(chain_raw - expected_raw)
                     and status == ("OK" if chain_raw == expected_raw else "MISMATCH"),
                     f"time balance row {seq} differs from transcript/expectation")
        else:
            _require(call.get("method") == "eth_getTransactionReceipt"
                     and call.get("params") == [row.get("tx")],
                     f"time tx transcript params {seq} mismatch")
            matched, receipt_block = _tx_transcript_matches(call.get("result"), row, token)
            _require(row.get("receipt_block") == receipt_block
                     and status == ("OK" if matched else "MISMATCH"),
                     f"time tx row {seq} differs from transcript")
    balance_count = sum(row.get("type") == "balance" for row in rows)
    tx_count = sum(row.get("type") == "tx" for row in rows)
    counter_fields = ("points", "balance_points", "tx_points",
                      "exact_match", "mismatch", "rpc_err")
    for field in counter_fields:
        value = receipt.get(field)
        _require(not isinstance(value, bool) and isinstance(value, int),
                 f"time receipt counter {field} must be an integer, not a boolean")
    _require(receipt.get("points") == len(rows)
             and receipt.get("balance_points") == balance_count
             and receipt.get("tx_points") == tx_count
             and receipt.get("exact_match") == counts["OK"]
             and receipt.get("mismatch") == counts["MISMATCH"]
             and receipt.get("rpc_err") == counts["RPC_ERR"],
             "time receipt counters differ from rows")
    _require(not counts["MISMATCH"] and not counts["RPC_ERR"],
             "PASS time receipt contains MISMATCH/RPC_ERR row")


def _validate_anchor_receipt(root, receipt, target):
    output_path = _bound_case_ref(root, receipt.get("output"), "anchor output")
    rows = []
    try:
        for line_no, line in enumerate(output_path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            value = json.loads(line, parse_constant=_reject_constant)
            _require(isinstance(value, dict), f"anchor output row {line_no} invalid")
            rows.append(value)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"anchor output invalid: {exc}") from exc
    date_range = receipt.get("date_range")
    _require(isinstance(date_range, dict)
             and set(date_range) == {"start", "end"}, "anchor date_range invalid")
    try:
        start = datetime.fromisoformat(date_range["start"]).date()
        end = datetime.fromisoformat(date_range["end"]).date()
    except (TypeError, ValueError) as exc:
        raise ValueError("anchor date_range invalid") from exc
    _require(start <= end, "anchor date_range start exceeds end")
    dates = []
    failures = []
    covered = 0
    for index, row in enumerate(rows):
        try:
            day = datetime.fromisoformat(str(row.get("date"))).date()
        except ValueError as exc:
            raise ValueError(f"anchor row {index} date invalid") from exc
        _require(start <= day <= end, f"anchor row {index} date outside target range")
        dates.append(day.isoformat())
        _require(row.get("chain") == "solana"
                 and str(row.get("mint") or "").lower() == str(target["token"]).lower()
                 and row.get("as_of_slot") == target["as_of_block"]
                 and isinstance(row.get("endpoint"), str) and bool(row.get("endpoint")),
                 f"anchor row {index} identity differs from target")
        if row.get("error"):
            failures.append({"date": row.get("date"), "error": row.get("error"),
                             "from_slot": row.get("from_slot"),
                             "to_slot": row.get("to_slot")})
        else:
            covered += 1
    _require(len(dates) == len(set(dates)), "anchor output contains duplicate dates")
    requested = (end - start).days + 1
    _require(len(rows) == requested, "anchor output row count differs from requested days")
    coverage = receipt.get("coverage")
    _require(isinstance(coverage, dict)
             and coverage.get("requested_days") == requested
             and coverage.get("covered_days") == covered
             and coverage.get("failed_days") == len(failures),
             "anchor coverage differs from output rows")
    _require(receipt.get("failures") == failures,
             "anchor failures differ from output error rows")
    _require(not failures, "PASS anchor receipt contains error rows")


def validate_reconciliation_check(root, key, item, target, family):
    """Validate one producer receipt semantically; wrapper fields are comparisons, not truth."""
    root = Path(root).resolve()
    if not isinstance(item, dict):
        raise ValueError(f"reconciliation {key} item missing")
    path = ref_ok(root, item.get("receipt"))
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"reconciliation {key} receipt JSON invalid: {exc}") from exc
    migration = "存量案例须重跑对应生产者获取当前回执"
    # A-3/B-6：正式消费线对全部 envelope inputs 强制案根约束（相对路径基于案根解析；
    # 绝对路径解析后也必须在案根内）——EVM inputs.balances 等同族输入不再可绑案外实物。
    envelope_errors = validate_receipt(receipt, case_root=root)
    if envelope_errors:
        raise ValueError(
            f"reconciliation {key} receipt envelope invalid: {envelope_errors[0]}；{migration}")
    if family == "solana" and key == "exact_reconcile":
        exact_target = canonical_target(receipt.get("target"))
        wrapper_target = canonical_target(target)
        _require(exact_target["chain"] == wrapper_target["chain"]
                 and exact_target["token"] == wrapper_target["token"]
                 and exact_target["as_of_block"] <= wrapper_target["as_of_block"],
                 "reconciliation exact_reconcile receipt target must match wrapper "
                 "chain/token and its cache slot must not be later than the observed slot；"
                 f"{migration}")
    else:
        _require(canonical_target(receipt.get("target")) == canonical_target(target),
                 f"reconciliation {key} receipt target mismatch；{migration}")
    _require(receipt.get("verdict") == item.get("status")
             and receipt.get("exit_code") == item.get("exit_code"),
             f"reconciliation {key} wrapper/receipt verdict mismatch")
    _require(receipt.get("verdict") == "PASS" and receipt.get("exit_code") == 0,
             f"reconciliation {key} receipt is not PASS/0")

    schema = receipt.get("schema")
    obs = receipt.get("observations") or {}
    if family == "evm" and key in {"balance", "supply"}:
        _require(receipt.get("mode") == "formal",
                 f"reconciliation {key} receipt must be formal；{migration}")
        _require(formal_ready(target["chain"]),
                 f"正式对账消费面只接受 formal-ready 链；{migration}")
        _require(schema == "evm-reconciliation-receipt/v3",
                 f"reconciliation {key} unknown schema {schema!r}; expected "
                 f"evm-reconciliation-receipt/v3；{VERIFY_RECON_V3_HINT}")
        _validate_evm_reconciliation_receipt(root, receipt, target)
    elif family == "solana" and key in {"balance", "time"}:
        _require(receipt.get("mode") == "formal",
                 f"reconciliation {key} receipt must be formal；{migration}")
        _require(formal_ready(target["chain"]),
                 f"正式对账消费面只接受 formal-ready 链；{migration}")
        _require(schema == "solana-anchor-sampler-receipt/v2",
                 f"reconciliation {key} unknown schema {schema!r}；{migration}")
        _validate_anchor_receipt(root, receipt, target)
    elif family == "solana" and key == "supply":
        _require(schema == "solana-observation-bundle/v1",
                 f"reconciliation supply unknown schema {schema!r}；{migration}")
        _require(receipt.get("closed") is True
                 and str(receipt.get("supply_raw")) == str(receipt.get("sum_accounts_raw"))
                 and isinstance(receipt.get("output"), dict),
                 "solana supply receipt is not a closed snapshot")
        from solana_observation import validate_observation_bundle
        validate_observation_bundle(receipt, expected_mint=target["token"])
        ref_ok(root, receipt["output"])
    elif key == "supply_truth":
        schema_migration = (
            "存量 EVM 案须以 observe_supply.py 生成观测件，并以 "
            "supply_truth_gate --observation-bundle 重跑"
            if family == "evm" else migration)
        if family == "evm":
            _require(schema == "supply-truth-receipt/v4",
                     f"reconciliation supply_truth unknown schema {schema!r}; "
                     f"expected supply-truth-receipt/v4；{schema_migration}")
        else:
            _require(schema == "supply-truth-receipt/v3",
                     f"reconciliation supply_truth unknown schema {schema!r}; "
                     f"expected supply-truth-receipt/v3；{schema_migration}")
        _require(receipt.get("gate") == "supply_truth"
                 and receipt.get("replay_net") is not None
                 and receipt.get("onchain_total_supply") is not None
                 and receipt.get("diff") is not None
                 and all(field in receipt for field in (
                     "decision_rule", "burn_form", "primary_verdict",
                     "sink_reconciliation")),
                 "supply_truth receipt observations incomplete")
        rule = receipt.get("decision_rule")
        _require(rule in {"primary_form1", "sink_fallback_form2"},
                 "supply_truth decision_rule invalid")
        if rule == "primary_form1":
            _require(receipt.get("primary_verdict") == "PASS"
                     and receipt.get("burn_form") is None
                     and receipt.get("sink_reconciliation") is None,
                     "primary_form1 receipt semantics invalid")
        else:
            sink = receipt.get("sink_reconciliation")
            _require(family == "evm" and receipt.get("primary_verdict") == "FAIL"
                     and receipt.get("burn_form") == "dead_sink"
                     and isinstance(sink, dict) and set(sink) == {"zero", "dead"},
                     "sink_fallback_form2 receipt semantics invalid")
            for address in ("zero", "dead"):
                row = sink.get(address)
                _require(isinstance(row, dict)
                         and set(row) == {"replay_raw", "onchain_raw"}
                         and isinstance(row.get("replay_raw"), str)
                         and row.get("replay_raw") == row.get("onchain_raw"),
                         f"sink_fallback_form2 {address} reconciliation invalid")
            try:
                mint_raw = int(str(receipt["mint_total"]))
                burn_raw = int(str(receipt["burn_total"]))
                onchain_raw = int(str(receipt["onchain_total_supply"]))
                sink_raw = sum(int(sink[address]["replay_raw"])
                               for address in ("zero", "dead"))
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("sink_fallback_form2 scalar fields invalid") from exc
            _require(mint_raw == onchain_raw and sink_raw == burn_raw,
                     "sink_fallback_form2 scalar/sink closure invalid")
            # 两个标量同样不能自报自验：对回案根里被哈希绑定的 replay_stats 实物（F-A）。
            _, stats_mint, stats_burn = _bound_replay_totals(root, receipt)
            _require(mint_raw == stats_mint and burn_raw == stats_burn,
                     f"sink_fallback_form2 mint_total/burn_total 与绑定 replay_stats "
                     f"实物不一致；{migration}")
        _require(receipt.get("mode") == "formal",
                 f"supply_truth receipt must be formal；{migration}")
        _require(formal_ready(target["chain"]),
                 f"正式对账消费面只接受 formal-ready 链；{migration}")
        _require(isinstance(receipt.get("inputs"), dict) and bool(receipt["inputs"]),
                 "supply_truth receipt must bind replay_stats input")
        _validate_tolerance_policy(root, receipt, target)
        if family == "solana":
            bundle_ref = (receipt.get("inputs") or {}).get("observation_bundle")
            _require(isinstance(bundle_ref, dict),
                     "solana supply_truth does not bind observation bundle")
            bundle_shown = Path(str(bundle_ref.get("path") or ""))
            bundle_path = (bundle_shown if bundle_shown.is_absolute()
                           else Path(root) / bundle_shown).resolve()
            bundle_path.relative_to(root)
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            from solana_observation import validate_observation_bundle
            validate_observation_bundle(bundle, bundle_path=bundle_path,
                                        expected_mint=target["token"])
            _require(isinstance(receipt.get("observed_context_slot"), int)
                     and receipt["observed_context_slot"] == bundle["supply"]["slot"]
                     and bundle["snapshot"]["slot"]
                     == canonical_target(target)["as_of_block"],
                     "solana supply_truth observation/bundle slots are not bound")
            # 链上供给这个数在 Solana 侧有案内实物可对——bundle 就在手上（上面刚读进来
            # 比过两处 slot），不比一下就等于让收据自报链上总量（N-2）。
            try:
                bundle_supply = int(str(bundle["supply"]["amount"]))
                receipt_supply = int(str(receipt.get("onchain_total_supply")))
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"solana supply_truth onchain/bundle supply amount is not an "
                    f"integer；{migration}") from exc
            _require(receipt_supply == bundle_supply,
                     "solana supply_truth onchain_total_supply is not bound to "
                     "bundle supply amount")
        elif family == "evm":
            bundle_ref = (receipt.get("inputs") or {}).get("observation_bundle")
            _require(isinstance(bundle_ref, dict),
                     "EVM supply_truth does not bind observation bundle")
            bundle_path = _bound_case_ref(
                root, bundle_ref, "EVM supply_truth observation bundle")
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            _require(bundle.get("schema") == "evm-observation-bundle/v1",
                     "EVM supply_truth observation bundle schema invalid")
            from evm_observation import validate_evm_observation_bundle
            validate_evm_observation_bundle(
                bundle, bundle_path=bundle_path, expected_token=target["token"],
                expected_chain_id=evm_chain_id_for(target["chain"]))
            _require(bundle["anchor"]["number"]
                     == canonical_target(target)["as_of_block"],
                     "EVM supply_truth bundle anchor mismatch against target.as_of_block")
            try:
                bundle_supply = int(str(bundle["supply"]["total_supply_raw"]))
                receipt_supply = int(str(receipt.get("onchain_total_supply")))
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"EVM supply_truth N-2 onchain/bundle total supply is not an "
                    f"integer；{schema_migration}") from exc
            _require(receipt_supply == bundle_supply,
                     "EVM supply_truth N-2 mismatch: onchain_total_supply is not "
                     "bound to bundle.supply.total_supply_raw")
            if rule == "sink_fallback_form2":
                sink = receipt["sink_reconciliation"]
                _require(str(sink["zero"]["onchain_raw"])
                         == str(bundle["supply"]["zero_balance_raw"]),
                         "EVM supply_truth ZERO sink is not bound to bundle supply")
                _require(str(sink["dead"]["onchain_raw"])
                         == str(bundle["supply"]["dead_balance_raw"]),
                         "EVM supply_truth DEAD sink is not bound to bundle supply")
    elif family == "evm" and key == "time":
        _require(receipt.get("mode") == "formal",
                 f"reconciliation time receipt must be formal；{migration}")
        _require(formal_ready(target["chain"]),
                 f"正式对账消费面只接受 formal-ready 链；{migration}")
        _require(schema == "time-spotcheck/v3",
                 f"reconciliation time unknown schema {schema!r}; expected "
                 f"time-spotcheck/v3；{TIME_SPOTCHECK_V3_HINT}")
        _validate_time_receipt(root, receipt, target)
    elif family == "solana" and key == "exact_reconcile":
        _require(schema == "solana-reconcile/v4",
                 "Solana exact_reconcile 必须重跑 replay_edges.py reconcile 生成 v4 收据")
        _require(receipt.get("mode") == "formal"
                 and receipt.get("gate_pass") is True
                 and receipt.get("negative_balance_count") == 0
                 and receipt.get("snapshot_mismatch_count") == 0,
                 "Solana exact_reconcile 未达到 formal 全平")
        from solana_exact_validate import validate_reconcile_receipt_deep
        checked = validate_reconcile_receipt_deep(path, case_root=root)
        _require(checked["ok"], "Solana exact_reconcile 独立深验失败: "
                 + "; ".join(checked["reasons"]))
    else:
        raise ValueError(f"reconciliation {key} has no validator for family={family}；{migration}")
    return receipt


def validate_reconciliation_report(root, expected_target=None, *, return_receipts=False):
    """Deeply validate the v3 controlled wrapper and all family checks."""
    root = Path(root).resolve()
    recon = json.loads(regular(root, "reconciliation_report.json").read_text())
    target = recon.get("target")
    if recon.get("schema") == "reconciliation-report/v2":
        hint = ("EVM 请用 reconciliation_report.py --reseal；Solana 必须重跑 "
                "replay_edges.py reconcile v4 与五项 runner")
        raise ValueError(f"reconciliation-report/v2 已 fail-closed；{hint}")
    if (recon.get("schema") != "reconciliation-report/v3"
            or not isinstance(target, dict)
            or set(target) != {"chain", "token", "as_of_block"}
            or not target.get("chain") or not target.get("token")
            or recon.get("verdict") != "PASS" or recon.get("exit_code") != 0):
        raise ValueError("reconciliation target/schema/verdict invalid")
    _require(formal_ready(target["chain"]),
             "正式对账消费面只接受 formal-ready 链；迁移指引："
             "请在 formal-ready 链重跑四项对账生产者并重建 reconciliation_report.json")
    if expected_target is not None and canonical_target(target) != canonical_target(expected_target):
        raise ValueError("reconciliation target/schema mismatch")
    family = chain_family(target["chain"])
    _require(recon.get("family") == family,
             "reconciliation wrapper family 必须由 target 推导且与 target 一致")
    repo_ref_ok(recon.get("producer"), RECON_RUNNERS, "reconciliation wrapper")
    checks = recon.get("checks")
    keys = RECON_CHECK_KEYS[family]
    if not isinstance(checks, dict) or tuple(checks) != keys:
        raise ValueError(f"reconciliation wrapper checks 必须按顺序恰为 {keys}")
    receipts = {}
    for key in keys:
        item = checks[key]
        if (not isinstance(item, dict) or item.get("status") != "PASS"
                or item.get("exit_code") != 0):
            raise ValueError(f"reconciliation {key} lacks PASS execution receipt")
        repo_ref_ok(item.get("producer"), RECON_PRODUCERS[family][key],
                    f"reconciliation {key}")
        receipts[key] = validate_reconciliation_check(root, key, item, target, family)
    if family == "evm":
        # A-5（N-1 第二建议）：EVM 的 balance/supply（verify_recon）与 supply_truth 三份
        # 收据绑定的 replay_stats 必须是同一份实物（sha256 全等）。案根约束（上面
        # case_root）只保证"账本在案内"，同源校验补上"三查核的是同一本账"——
        # 否则可在案内放两本账，各查各的、互相印证不了。
        stats_shas = {}
        for key in ("balance", "supply", "supply_truth"):
            ref = (receipts[key].get("inputs") or {}).get("replay_stats")
            if not isinstance(ref, dict) or not ref.get("sha256"):
                raise ValueError(
                    f"reconciliation {key} receipt does not bind replay_stats input；{MIGRATION_HINT}")
            stats_shas[key] = str(ref["sha256"]).lower()
        if len(set(stats_shas.values())) != 1:
            raise ValueError(
                "reconciliation balance/supply/supply_truth 绑定的 replay_stats 不同源"
                f"（sha256 不一致: {stats_shas}）——三查必须核同一份重放账本；{MIGRATION_HINT}")
    else:
        exact_ref = (receipts["exact_reconcile"].get("inputs") or {}).get(
            "holders_owners")
        exact_path = _bound_case_ref(root, exact_ref, "exact holders_owners")
        exact_target = canonical_target(receipts["exact_reconcile"].get("target"))
        wrapper_target = canonical_target(target)
        if exact_target["as_of_block"] == wrapper_target["as_of_block"]:
            # 静态态保持批 5 原语义：exact 与 supply 必须消费同一个 owners 文件。
            supply_ref = (receipts["supply"].get("holder_outputs") or {}).get("owners")
            supply_receipt_ref = checks["supply"].get("receipt") or {}
            supply_receipt_path = _bound_case_ref(
                root, supply_receipt_ref, "Solana supply receipt")
            supply_path = _bound_case_ref(
                root, supply_ref, "Solana supply holder_outputs.owners",
                base=supply_receipt_path.parent)
            _require(exact_path == supply_path,
                     "exact_reconcile.inputs.holders_owners 与 supply observation bundle "
                     "holder_outputs.owners 不是同一文件")
        else:
            binding_hint = ("冻结态第五查快照必须哈希绑定冻结观测 bundle "
                            f"{SOLANA_FROZEN_OBSERVATION_BUNDLE}")
            try:
                frozen_path = regular(root, SOLANA_FROZEN_OBSERVATION_BUNDLE)
                frozen_bundle = json.loads(frozen_path.read_text(encoding="utf-8"))
                envelope_errors = validate_receipt(frozen_bundle, case_root=root)
                _require(not envelope_errors,
                         f"{binding_hint}；信封校验失败: "
                         + (envelope_errors[0] if envelope_errors else "unknown"))
                from solana_observation import validate_observation_bundle
                validate_observation_bundle(
                    frozen_bundle, bundle_path=frozen_path,
                    expected_mint=exact_target["token"])
            except Exception as exc:
                if binding_hint in str(exc):
                    raise
                raise ValueError(f"{binding_hint}；冻结 bundle 深验失败: {exc}") from exc
            _require(canonical_target(frozen_bundle.get("target")) == exact_target,
                     f"{binding_hint}；冻结 bundle target 必须与 exact_reconcile target 全等")
            frozen_ref = (frozen_bundle.get("holder_outputs") or {}).get("owners")
            _require(isinstance(frozen_ref, dict)
                     and not isinstance(frozen_ref.get("size"), bool)
                     and isinstance(frozen_ref.get("size"), int)
                     and frozen_ref.get("size") == exact_ref.get("size")
                     and frozen_ref.get("sha256") == exact_ref.get("sha256"),
                     f"{binding_hint}；exact holders_owners 与冻结 bundle owners 的 "
                     "sha256+size 必须全等")
    return (target, receipts) if return_receipts else target


def accounting_expected_target(reconciliation_target, reconciliation_receipts):
    """Select the accounting ledger target for static and frozen reconciliation."""
    wrapper_target = canonical_target(reconciliation_target)
    if chain_family(wrapper_target["chain"]) != "solana":
        return wrapper_target
    exact = (reconciliation_receipts or {}).get("exact_reconcile")
    _require(isinstance(exact, dict),
             "Solana accounting target selection lacks exact_reconcile receipt")
    exact_target = canonical_target(exact.get("target"))
    _require(exact_target["chain"] == wrapper_target["chain"]
             and exact_target["token"] == wrapper_target["token"],
             "Solana accounting/exact target chain or token mismatch")
    _require(exact_target["as_of_block"] <= wrapper_target["as_of_block"],
             "Solana accounting/exact target is later than wrapper target")
    return exact_target if exact_target["as_of_block"] < wrapper_target["as_of_block"] \
        else wrapper_target


def validate_solana_derived_bindings(root, exact_binding, *, extra_paths=()):
    """Require every present/referenced Solana edge-derived JSON to bind exact."""
    root = Path(root).resolve()
    candidates = {"wave_scan_report.json", "flow_anomaly_report.json"}
    data_map = root / "data_map.json"
    if data_map.is_file():
        try:
            mapped = json.loads(data_map.read_text(encoding="utf-8"))
            candidates.update(item.get("path") for item in mapped.get("files", [])
                              if isinstance(item, dict)
                              and isinstance(item.get("path"), str))
        except Exception as exc:
            raise ValueError(f"data_map.json 无法用于边源绑定深验: {exc}") from exc
    candidates.update(path for path in extra_paths if isinstance(path, str))
    for rel in sorted(candidates):
        name = Path(rel).name
        relevant = (rel in {"wave_scan_report.json", "flow_anomaly_report.json"}
                    or "entity_source_trace" in name
                    or name.startswith("curve_cost")
                    or name.startswith("closed_audit-")
                    or name.endswith(".provenance.json"))
        if not relevant:
            continue
        try:
            shown = Path(rel)
            if shown.is_absolute() or not shown.parts or ".." in shown.parts:
                raise ValueError("path must be a safe case-relative path")
            lexical = root / shown
            current = root
            for part in shown.parts:
                current = current / part
                if current.is_symlink():
                    raise ValueError("path traverses a symlink")
            resolved = lexical.resolve(strict=True)
            resolved.relative_to(root)
            path = _bound_case_ref(
                root, {"path": rel, "size": resolved.stat().st_size,
                       "sha256": sha(resolved)}, f"derived artifact {rel}")
            value = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            continue
        except Exception as exc:
            raise ValueError(f"Solana 派生产物 {rel} 无法深验: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"Solana 派生产物 {rel} 顶层不是对象")
        if name.endswith(".provenance.json") and value.get("series_format") != "sol-rows":
            continue
        if value.get("edge_source_binding") != exact_binding:
            raise ValueError(
                f"Solana 派生产物 {rel}.edge_source_binding 与 exact_reconcile 不全等")
    return True


def validate_adversarial_review(root, expected_target=None):
    """Deeply revalidate the v4 aggregate from registry and artifact bytes."""
    root = Path(root).resolve()
    try:
        adversarial = json.loads(
            regular(root, "adversarial_review.json").read_text(),
            parse_constant=_reject_constant)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"adversarial review JSON invalid: {exc}") from exc
    schema = adversarial.get("schema") if isinstance(adversarial, dict) else None
    if schema != AGGREGATE_SCHEMA:
        if schema in {"adversarial-review/v2", "adversarial-review/v3"}:
            raise ValueError(V4_RERUN_HINT)
        raise ValueError(f"adversarial review must use {AGGREGATE_SCHEMA}；{V4_RERUN_HINT}")
    target = adversarial.get("target")
    if not isinstance(target, dict):
        raise ValueError("adversarial target missing")
    if expected_target is not None \
            and canonical_target(target) != canonical_target(expected_target):
        raise ValueError("adversarial target mismatch")
    repo_ref_ok(adversarial.get("producer"), ADVERSARIAL_RUNNERS,
                "adversarial aggregate")

    registry_ref = adversarial.get("claim_registry")
    if not isinstance(registry_ref, dict):
        raise ValueError("adversarial claim_registry ref missing")
    _, _, claim_ids, actual_registry_ref = load_claim_registry(
        root, registry_ref.get("path", ""), meaningful_text=_meaningful_text,
        reject_constant=_reject_constant)
    if registry_ref != actual_registry_ref:
        raise ValueError("adversarial claim_registry size/sha256/schema binding invalid")
    registry_sha256 = actual_registry_ref["sha256"]

    reviews = adversarial.get("reviews")
    if not isinstance(reviews, list) or not reviews:
        raise ValueError("adversarial reviews must be a non-empty array")
    roles = set()
    reviewed_sets = []
    execution_sha256s = set()
    artifact_sha256s = set()
    review_entrypoints = set()
    review_entries = []
    for item in reviews:
        if not isinstance(item, dict) or item.get("exit_code") != 0:
            raise ValueError("review lacks successful execution receipt")
        role = item.get("role")
        if role not in ROLES:
            raise ValueError(f"unsupported adversarial role in aggregate: {role!r}")
        roles.add(role)
        artifact = item.get("artifact")
        artifact_path = ref_ok(root, artifact)
        if artifact.get("size") != artifact_path.stat().st_size:
            raise ValueError("review artifact size binding invalid")
        artifact_sha256 = artifact.get("sha256")
        if artifact_sha256 in artifact_sha256s:
            raise ValueError("duplicate review artifact content")
        artifact_sha256s.add(artifact_sha256)
        repo_ref_ok(item.get("runner"), ADVERSARIAL_RUNNERS, f"adversarial {role}")
        execution = item.get("execution_receipt")
        execution_path = ref_ok(root, execution)
        if execution.get("size") != execution_path.stat().st_size:
            raise ValueError("review execution receipt size binding invalid")
        execution_sha256 = execution.get("sha256")
        if execution_sha256 in execution_sha256s:
            raise ValueError("duplicate review execution receipt content")
        execution_sha256s.add(execution_sha256)
        execution_data, artifact_data, reviewed = validate_review_receipt(
            root, execution.get("path"), role, artifact,
            registry_sha256=registry_sha256, claim_ids=claim_ids,
            meaningful_text=_meaningful_text, reject_constant=_reject_constant)
        entrypoint_key = execution_data["entrypoint"]["sha256"]
        if entrypoint_key in review_entrypoints:
            raise ValueError("duplicate review entrypoint content")
        review_entrypoints.add(entrypoint_key)
        review_entries.append((role, artifact["path"], artifact_data))
        if role in CLAIM_REVIEW_ROLES:
            reviewed_sets.append(reviewed)
    if not ROLES.issubset(roles):
        raise ValueError(f"required adversarial roles missing: {sorted(ROLES - roles)}")
    validate_union_coverage(claim_ids, reviewed_sets)
    blockers = validate_blocking_findings(
        adversarial.get("blocking_findings"), meaningful_text=_meaningful_text)
    required_refs = build_required_refs(review_entries)
    validate_blocker_linkage(blockers, required_refs)
    ledger_binding, active_ledger = validate_review_ledger(root)
    aggregate_ledger = adversarial.get("review_ledger")
    if (not isinstance(aggregate_ledger, dict)
            or set(aggregate_ledger) != {"entries", "active", "tip_sha"}
            or type(aggregate_ledger.get("entries")) is not int
            or type(aggregate_ledger.get("active")) is not int
            or not isinstance(aggregate_ledger.get("tip_sha"), str)
            or aggregate_ledger != ledger_binding):
        raise ValueError("adversarial review_ledger binding invalid")
    if any(item.get("schema") != LEDGER_SCHEMA for item in active_ledger.values()):
        raise ValueError("active review ledger row schema invalid")
    active_receipt_sha256s = {
        item["receipt_sha"] for item in active_ledger.values()
    }
    if not (len(active_ledger) == len(active_receipt_sha256s) == len(reviews)):
        raise ValueError(
            "review ledger cardinality differs from aggregate reviews: "
            f"active={len(active_ledger)} "
            f"active_receipt_sha256s={len(active_receipt_sha256s)} "
            f"aggregate_reviews={len(reviews)}")
    if active_receipt_sha256s != execution_sha256s:
        raise ValueError("review ledger active receipt set differs from aggregate reviews")
    unresolved = [item for item in blockers if not item["resolved"]]
    if unresolved:
        raise ValueError(f"对抗复核仍有 {len(unresolved)} 个未关闭发布否决项")
    if adversarial.get("release_decision") != "PASS":
        raise ValueError("adversarial release_decision is not PASS")
    return target


def validate_accounting_receipt(root, accounting=None, expected_target=None):
    """Validate the production accounting receipt and its observation source.

    This is the sole accounting validator consumed by shared release, stage-1
    handoff READY, and the independent audit release gate.
    """
    root = Path(root).resolve()
    if accounting is None:
        accounting = json.loads(
            regular(root, "accounting_mode.json").read_text(encoding="utf-8"))
    if (not isinstance(accounting, dict) or accounting.get("exit_code") != 0
            or str(accounting.get("verdict", "")).upper() not in {"PASS", "WARN"}
            or not accounting.get("chain")
            or not (accounting.get("token") or accounting.get("mint"))
            or not isinstance(accounting.get("checks"), dict)
            or not accounting["checks"]):
        raise ValueError("accounting evidence is not a production gate receipt")

    family = chain_family(accounting["chain"])
    if family == "evm":
        if accounting.get("schema") != "accounting-gate/v2":
            raise ValueError(
                f"EVM accounting schema {accounting.get('schema')!r} is not "
                "accounting-gate/v2; 存量案须以 observe_supply.py + "
                "accounting_gate --bundle 重跑")
    elif accounting.get("schema") != "accounting-gate/v1":
        raise ValueError(
            f"solana accounting schema {accounting.get('schema')!r} is not "
            f"accounting-gate/v1；{MIGRATION_HINT}")
    _require(accounting.get("execution_mode") == "formal",
             f"{family} accounting exploration evidence is not releasable")

    repo_ref_ok(accounting.get("producer"), {ACCOUNTING_PRODUCERS[family]},
                "accounting")
    token = accounting.get("token") or accounting.get("mint")
    target = canonical_target({
        "chain": accounting["chain"], "token": str(token),
        "as_of_block": accounting.get("as_of_block"),
    })
    if expected_target is not None \
            and target != canonical_target(expected_target):
        raise ValueError("accounting target mismatch")

    if family == "evm":
        tip = accounting.get("tip_block")
        as_of = accounting.get("as_of_block")
        _require(not isinstance(tip, bool) and isinstance(tip, int) and tip >= 0,
                 "EVM accounting tip_block missing or invalid")
        _require(not isinstance(as_of, bool) and isinstance(as_of, int) and as_of >= 0
                 and as_of <= tip,
                 "EVM accounting as_of_block must be <= tip_block")
        probe = accounting.get("model_probe_block")
        _require(not isinstance(probe, bool) and isinstance(probe, int) and probe >= 0,
                 "EVM accounting model_probe_block missing or invalid")
        _require(probe == tip,
                 "EVM accounting model_probe_block must equal tip_block")
        _require(as_of <= probe,
                 "EVM accounting as_of_block must be <= model_probe_block")

        bundle_ref = accounting.get("observation_bundle")
        _require(isinstance(bundle_ref, dict),
                 "EVM accounting does not bind observation bundle")
        bundle_path = _bound_case_ref(
            root, bundle_ref, "EVM accounting observation bundle")
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        _require(bundle.get("schema") == "evm-observation-bundle/v1",
                 "EVM accounting observation bundle schema invalid")
        from evm_observation import validate_evm_observation_bundle
        validate_evm_observation_bundle(
            bundle, bundle_path=bundle_path, expected_token=target["token"],
            expected_chain_id=evm_chain_id_for(target["chain"]))
        _require(as_of == bundle["anchor"]["number"],
                 "EVM accounting bundle anchor mismatch: as_of_block != "
                 "bundle anchor.number")
        observed = accounting.get("observed_anchor")
        _require(isinstance(observed, dict)
                 and observed.get("block") == bundle["anchor"]["number"],
                 "EVM accounting observed anchor block mismatch")
        _require(observed.get("block_hash") == bundle["anchor"]["block_hash"],
                 "EVM accounting observed anchor block_hash mismatch")
        return target, accounting, sha(bundle_path)

    bundle_ref = accounting.get("observation_bundle")
    _require(isinstance(bundle_ref, dict),
             "solana accounting does not bind observation bundle")
    bundle_path = _bound_case_ref(
        root, bundle_ref, "solana accounting observation bundle")
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    from solana_observation import validate_observation_bundle
    validate_observation_bundle(
        bundle, bundle_path=bundle_path, expected_mint=token)
    _require(accounting.get("observed_context_slot") == bundle["snapshot"]["slot"],
             "solana accounting slot is not bundle snapshot slot")
    return target, accounting, sha(bundle_path)


def validate_evm_observation_source_chain(root, accounting, supply_truth_receipt):
    """Require accounting and supply-truth to bind identical observation bytes."""
    if chain_family(accounting.get("chain")) != "evm":
        return None
    accounting_ref = accounting.get("observation_bundle")
    supply_ref = (supply_truth_receipt.get("inputs") or {}).get(
        "observation_bundle")
    _require(isinstance(accounting_ref, dict),
             "EVM accounting does not bind observation bundle")
    _require(isinstance(supply_ref, dict),
             "EVM supply_truth does not bind observation bundle")
    accounting_path = _bound_case_ref(
        root, accounting_ref, "EVM accounting observation bundle")
    supply_path = _bound_case_ref(
        root, supply_ref, "EVM supply_truth observation bundle")
    accounting_sha = sha(accounting_path).lower()
    supply_sha = sha(supply_path).lower()
    _require(accounting_sha == supply_sha,
             "EVM accounting and supply_truth observation bundles are not the "
             f"same source (sha256 mismatch: accounting={accounting_sha}, "
             f"supply_truth={supply_sha})")
    return accounting_sha


def validate_sources(root):
    root = Path(root).resolve()
    target, accounting, _ = validate_accounting_receipt(root)
    if chain_family(target["chain"]) == "evm":
        # EVM has no fifth receipt; preserve the original target comparison path.
        recon_target, receipts = validate_reconciliation_report(
            root, target, return_receipts=True)
    else:
        recon_target, receipts = validate_reconciliation_report(
            root, return_receipts=True)
        expected_accounting = accounting_expected_target(recon_target, receipts)
        if expected_accounting == canonical_target(recon_target):
            # Static Solana preserves the original wrapper/accounting equality.
            if canonical_target(target) != canonical_target(recon_target):
                raise ValueError("reconciliation target/schema mismatch")
        else:
            # Frozen Solana keeps the validator strict; only the caller-selected
            # expected target changes from the live wrapper to the exact receipt.
            target, accounting, _ = validate_accounting_receipt(
                root, accounting=accounting, expected_target=expected_accounting)
    validate_evm_observation_source_chain(
        root, accounting, receipts["supply_truth"])
    validate_adversarial_review(root, target)
    return target


def create_bundle(root, out=None):
    root = Path(root).resolve()
    target = validate_sources(root)
    out = Path(out or root / "shared_release_receipt.json").resolve()
    if out.parent != root:
        raise ValueError("shared receipt must be in case root")
    payload = {"schema": "shared-release-receipt/v1", "status": "PASS",
               "producer": {"path": "shared_release_receipt.py", "sha256": sha(__file__)},
               "target": target,
               "inputs": {name: {"path": name, "sha256": sha(root / name)} for name in FILES}}
    tmp = out.with_name(f".{out.name}.tmp.{os.getpid()}")
    with tmp.open("x") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, out)
    return payload


def validate_bundle(root):
    errors = []
    root = Path(root).resolve()
    try:
        data = json.loads(regular(root, "shared_release_receipt.json").read_text())
        target = validate_sources(root)
        if (data.get("schema") != "shared-release-receipt/v1"
                or data.get("status") != "PASS" or data.get("target") != target):
            raise ValueError("shared receipt schema/target invalid")
        expected_producer = {"path": "shared_release_receipt.py", "sha256": sha(__file__)}
        if data.get("producer") != expected_producer:
            raise ValueError("shared receipt producer mismatch")
        expected = {name: {"path": name, "sha256": sha(root / name)} for name in FILES}
        if data.get("inputs") != expected:
            raise ValueError("shared receipt input hashes changed")
    except Exception as exc:
        errors.append(str(exc))
    return errors


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("case_dir")
    args = ap.parse_args(argv)
    try:
        create_bundle(args.case_dir)
    except Exception as exc:
        ap.exit(2, f"BLOCK: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
