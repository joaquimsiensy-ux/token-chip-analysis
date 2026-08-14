#!/usr/bin/env python3
"""Production aggregator and validator for shared formal release evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE.parent / "lib"))

from adversarial_review_runner import (
    AGGREGATE_SCHEMA,
    CLAIM_REVIEW_ROLES,
    ROLES,
    V3_RERUN_HINT,
    load_claim_registry,
    validate_blocking_findings,
    validate_review_receipt,
    validate_union_coverage,
)
from chain_registry import recon_adapter_for, resolve_alias
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
    },
}
RECON_RUNNERS = {"scripts/report/reconciliation_report.py"}
ADVERSARIAL_RUNNERS = {"scripts/report/adversarial_review_runner.py"}


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


def repo_ref_ok(ref, allowed, label):
    if not isinstance(ref, dict):
        raise ValueError(f"{label} producer/runner ref missing")
    rel = str(ref.get("path", ""))
    if rel not in allowed:
        raise ValueError(f"{label} producer/runner path is not whitelisted: {rel}")
    path = (REPO / rel).resolve()
    path.relative_to(REPO)
    if not path.is_file() or ref.get("sha256") != sha(path):
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
    """文本至少含一个消费侧明确批准的可渲染字符。"""
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
    token = str(target.get("token") or "").strip().lower()
    if not chain or not token:
        raise ValueError("target chain/token must be non-empty")
    return {"chain": chain, "token": token, "as_of_block": slot}


def _bound_case_ref(root, ref, label, *, base=None):
    if not isinstance(ref, dict) or not {"path", "size", "sha256"} <= set(ref):
        raise ValueError(f"{label} must bind path/size/sha256")
    case_root = Path(root).resolve()
    base = Path(base or case_root).resolve()
    raw = Path(str(ref.get("path") or ""))
    if raw.is_absolute() or not raw.parts or ".." in raw.parts:
        raise ValueError(f"{label} path must be a safe relative path")
    lexical = base
    for part in raw.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise ValueError(f"{label} path is a symlink")
    try:
        path = lexical.resolve(strict=True)
        path.relative_to(case_root)
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


def validate_reconciliation_check(root, key, item, target, family):
    """Validate one producer receipt semantically; wrapper fields are comparisons, not truth."""
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
        _require(schema == "evm-reconciliation-receipt/v2",
                 f"reconciliation {key} unknown schema {schema!r}；{migration}")
        if key == "balance":
            bal = obs.get("balance_reconciliation") or {}
            _require(isinstance(bal.get("checked"), int) and bal["checked"] > 0
                     and bal.get("matched") == bal["checked"]
                     and bal.get("mismatched") == 0 and bal.get("rpc_errors") == 0,
                     "balance receipt observations incomplete or non-PASS")
        else:
            supply = obs.get("supply_closure") or {}
            _require(supply.get("closed") is True and supply.get("negative_count") == 0,
                     "supply receipt observations incomplete or non-closed")
    elif family == "solana" and key in {"balance", "time"}:
        _require(schema == "solana-anchor-sampler-receipt/v2",
                 f"reconciliation {key} unknown schema {schema!r}；{migration}")
        coverage = receipt.get("coverage") or {}
        _require(isinstance(coverage.get("requested_days"), int)
                 and coverage["requested_days"] > 0
                 and coverage.get("covered_days") == coverage["requested_days"]
                 and coverage.get("failed_days") == 0 and receipt.get("failures") == [],
                 "anchor receipt coverage incomplete")
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
        _require(schema == "supply-truth-receipt/v3",
                 f"reconciliation supply_truth unknown schema {schema!r}；{migration}")
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
        _require(receipt.get("mode") == "formal" and isinstance(receipt.get("inputs"), dict)
                 and bool(receipt["inputs"]),
                 "supply_truth receipt must be formal and bind replay_stats input")
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
    elif family == "evm" and key == "time":
        _require(schema == "time-spotcheck/v2",
                 f"reconciliation time unknown schema {schema!r}；{migration}")
        _require(isinstance(receipt.get("points"), int) and receipt["points"] > 0
                 and receipt.get("exact_match") == receipt["points"]
                 and receipt.get("mismatch") == 0 and receipt.get("rpc_err") == 0,
                 "time receipt observations incomplete or non-PASS")
    else:
        raise ValueError(f"reconciliation {key} has no validator for family={family}；{migration}")
    return receipt


def validate_reconciliation_report(root, expected_target=None):
    """Deeply validate the controlled wrapper and all four bound receipts."""
    root = Path(root).resolve()
    recon = json.loads(regular(root, "reconciliation_report.json").read_text())
    target = recon.get("target")
    if (recon.get("schema") != "reconciliation-report/v2"
            or not isinstance(target, dict)
            or set(target) != {"chain", "token", "as_of_block"}
            or not target.get("chain") or not target.get("token")
            or recon.get("verdict") != "PASS" or recon.get("exit_code") != 0):
        raise ValueError("reconciliation target/schema/verdict invalid")
    if expected_target is not None and canonical_target(target) != canonical_target(expected_target):
        raise ValueError("reconciliation target/schema mismatch")
    family = chain_family(target["chain"])
    repo_ref_ok(recon.get("producer"), RECON_RUNNERS, "reconciliation wrapper")
    checks = recon.get("checks")
    if not isinstance(checks, dict) or set(checks) != {"balance", "supply", "supply_truth", "time"}:
        raise ValueError("reconciliation wrapper must contain exactly four checks")
    receipts = {}
    for key in ("balance", "supply", "supply_truth", "time"):
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
    return target


def validate_adversarial_review(root, expected_target=None):
    """Deeply revalidate the v3 aggregate from registry and artifact bytes."""
    root = Path(root).resolve()
    try:
        adversarial = json.loads(
            regular(root, "adversarial_review.json").read_text(),
            parse_constant=_reject_constant)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"adversarial review JSON invalid: {exc}") from exc
    schema = adversarial.get("schema") if isinstance(adversarial, dict) else None
    if schema != AGGREGATE_SCHEMA:
        if schema == "adversarial-review/v2":
            raise ValueError(V3_RERUN_HINT)
        raise ValueError(f"adversarial review must use {AGGREGATE_SCHEMA}；{V3_RERUN_HINT}")
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
    claim_review_entrypoints = set()
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
        execution_data, _, reviewed = validate_review_receipt(
            root, execution.get("path"), role, artifact,
            registry_sha256=registry_sha256, claim_ids=claim_ids,
            meaningful_text=_meaningful_text, reject_constant=_reject_constant)
        if role in CLAIM_REVIEW_ROLES:
            entrypoint_key = (role, execution_data["entrypoint"]["sha256"])
            if entrypoint_key in claim_review_entrypoints:
                raise ValueError("duplicate claim-review role and entrypoint content")
            claim_review_entrypoints.add(entrypoint_key)
            reviewed_sets.append(reviewed)
    if not ROLES.issubset(roles):
        raise ValueError(f"required adversarial roles missing: {sorted(ROLES - roles)}")
    validate_union_coverage(claim_ids, reviewed_sets)
    blockers = validate_blocking_findings(
        adversarial.get("blocking_findings"), meaningful_text=_meaningful_text)
    unresolved = [item for item in blockers if not item["resolved"]]
    if unresolved:
        raise ValueError(f"对抗复核仍有 {len(unresolved)} 个未关闭发布否决项")
    if adversarial.get("release_decision") != "PASS":
        raise ValueError("adversarial release_decision is not PASS")
    return target


def validate_sources(root):
    root = Path(root).resolve()
    accounting = json.loads(regular(root, "accounting_mode.json").read_text())
    adversarial = json.loads(
        regular(root, "adversarial_review.json").read_text(),
        parse_constant=_reject_constant)
    if (accounting.get("schema") != "accounting-gate/v1" or accounting.get("exit_code") != 0
            or str(accounting.get("verdict", "")).upper() not in {"PASS", "WARN"}
            or not accounting.get("chain") or not (accounting.get("token") or accounting.get("mint"))
            or not isinstance(accounting.get("checks"), dict) or not accounting["checks"]):
        raise ValueError("accounting evidence is not a production gate receipt")
    family = chain_family(accounting["chain"])
    if family == "evm":
        tip = accounting.get("tip_block")
        as_of = accounting.get("as_of_block")
        _require(not isinstance(tip, bool) and isinstance(tip, int) and tip >= 0,
                 "EVM accounting tip_block missing or invalid")
        _require(not isinstance(as_of, bool) and isinstance(as_of, int) and as_of >= 0
                 and as_of <= tip,
                 "EVM accounting as_of_block must be <= tip_block")
        # 时点闸不能只挂在 tip_block 一个自报字段上：生产侧把同一个 tip 同时写进
        # model_probe_block，消费侧就得两个都验，想抬时点必须同时改两处（F-B）。
        probe = accounting.get("model_probe_block")
        _require(not isinstance(probe, bool) and isinstance(probe, int) and probe >= 0,
                 "EVM accounting model_probe_block missing or invalid")
        _require(probe == tip,
                 "EVM accounting model_probe_block must equal tip_block")
        _require(as_of <= probe,
                 "EVM accounting as_of_block must be <= model_probe_block")
    expected_accounting = ACCOUNTING_PRODUCERS[family]
    repo_ref_ok(accounting.get("producer"), {expected_accounting}, "accounting")
    token = accounting.get("token") or accounting.get("mint")
    target = {"chain": accounting["chain"], "token": str(token).lower(),
              "as_of_block": accounting.get("as_of_block")}
    if family == "solana":
        _require(accounting.get("execution_mode") == "formal",
                 "solana accounting exploration evidence is not releasable")
        bundle_ref = accounting.get("observation_bundle")
        _require(isinstance(bundle_ref, dict),
                 "solana accounting does not bind observation bundle")
        acc_shown = Path(str(bundle_ref.get("path") or ""))
        bundle_path = (acc_shown if acc_shown.is_absolute()
                       else Path(root) / acc_shown).resolve()
        bundle_path.relative_to(root)
        _require(bundle_path.is_file() and bundle_ref.get("size") == bundle_path.stat().st_size
                 and bundle_ref.get("sha256") == sha(bundle_path),
                 "solana accounting observation bundle ref invalid")
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        from solana_observation import validate_observation_bundle
        validate_observation_bundle(bundle, bundle_path=bundle_path,
                                    expected_mint=token)
        _require(accounting.get("observed_context_slot") == bundle["snapshot"]["slot"],
                 "solana accounting slot is not bundle snapshot slot")
    validate_reconciliation_report(root, target)
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
