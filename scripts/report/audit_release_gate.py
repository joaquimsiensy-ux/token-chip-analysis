#!/usr/bin/env python3
"""独立筹码报告发布硬闸。

检查净室复核必需资产、输入哈希、三账、候选完整性、命题证据、
对抗复核否决项和历史图对账。退出码 0=PASS，2=BLOCK，1=用法/程序错误。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

LIB = Path(__file__).resolve().parents[1] / "lib"
sys.path.insert(0, str(LIB))
from chain_registry import (formal_ready, known_chains_for_release,
                            missing_formal_capabilities, release_tier_for, resolve_alias)


SHARED_REQUIRED = (
    "accounting_mode.json",
    "reconciliation_report.json",
    "address_classification.json",
    "membership_ledger.json",
    "position_ledger.json",
    "economic_control_ledger.json",
    "dormant_warehouse_audit.json",
    "adversarial_review.json",
    "shared_release_receipt.json",
)
AUDIT_ONLY_REQUIRED = (
    "audit_input_manifest.json",
    "claim_registry.json",
    "reproduce_audit.py",
)
NEW_ANALYSIS_REQUIRED = (
    "distribution_scan.json",
    "distribution_rounds.json",
    "a5_report_seal.json",
)
REQUIRED_BY_PROFILE = {
    "new-analysis": SHARED_REQUIRED + NEW_ANALYSIS_REQUIRED,
    "independent-audit": SHARED_REQUIRED + AUDIT_ONLY_REQUIRED,
}
PASS_WORDS = {"pass", "passed", "ok"}
ACCOUNTING_EXTRA = frozenset({"standard"})
DECISIVE_TYPES = {
    "entity_attribution", "economic_control", "whale_tier", "cex_identity",
    "cex_channel", "historical_peak", "historical_chart", "negative_exhaustive",
}
def normalize_chain(value):
    return resolve_alias(value)


def formal_chain_error(value):
    chain = normalize_chain(value)
    if formal_ready(chain):
        return None
    if chain == "arbitrum":
        return ("chain=arbitrum 为探索支持：缺少 references/labels/labels-arbitrum.csv "
                "及完整目标链标签门禁；可保留采集、对账和 identity snapshot，"
                "但不得编译正式 analysis")
    if release_tier_for(chain) == "formal":
        missing = ",".join(missing_formal_capabilities(chain))
        return f"chain={chain} 尚未闭合正式发布能力（缺 {missing}），不得编译正式 analysis"
    if chain in known_chains_for_release():
        return f"chain={chain} 为 exploration，不得编译正式 analysis"
    return f"chain={chain or '<missing>'} 未进入正式支持矩阵，不得编译正式 analysis"


def check_formal_case_chain(data, errors):
    """Bind formal release to one chain declared by both accounting and reconciliation."""
    claims = []
    accounting = data.get("accounting_mode.json")
    if isinstance(accounting, dict):
        claims.append(("accounting_mode.json", normalize_chain(accounting.get("chain"))))
    reconciliation = data.get("reconciliation_report.json")
    if isinstance(reconciliation, dict):
        target = reconciliation.get("target") or {}
        claims.append(("reconciliation_report.json", normalize_chain(target.get("chain"))))
    missing = [name for name, chain in claims if not chain]
    if missing:
        errors.append("正式发布链声明缺失: " + ", ".join(missing))
        return None
    unique = {chain for _, chain in claims}
    if len(unique) != 1:
        errors.append("正式发布链声明不一致: "
                      + ", ".join(f"{name}={chain}" for name, chain in claims))
        return None
    chain = next(iter(unique), "")
    reason = formal_chain_error(chain)
    if reason:
        errors.append(reason)
        return None
    return chain


def load_json(path: Path, errors: list[str]):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"JSON无法读取 {path.name}: {exc}")
        return {}


def status_pass(value, extra=frozenset()) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in (PASS_WORDS | extra)


def strict_int(value, label, errors, *, raw=False):
    """Accept only non-boolean int or a base-10 integer string; never truncate floats."""
    if isinstance(value, bool):
        n = None
    elif isinstance(value, int):
        n = value
    elif isinstance(value, str) and value.strip() == value \
            and value not in {"", "+", "-"} \
            and value.lstrip("+-").isdigit():
        n = int(value, 10)
    else:
        n = None
    if n is None:
        errors.append(f"{label} 不是整数 raw amount" if raw else f"{label} 非整数")
        return None
    if n < 0:
        errors.append(f"{label} 为负数")
    return n


def finite_decimal(value, label, errors):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        errors.append(f"{label} 必须是有限实数")
        return None
    try:
        n = Decimal(str(value))
    except (InvalidOperation, ValueError):
        errors.append(f"{label} 必须是有限实数")
        return None
    if not n.is_finite():
        errors.append(f"{label} 必须是有限实数")
        return None
    if n < 0:
        errors.append(f"{label} 不得为负")
        return None
    return n


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(8 * 1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def canonical_json_sha(value) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def safe_case_path(case_dir: Path, rel: str) -> Path | None:
    try:
        p = (case_dir / rel).resolve()
        p.relative_to(case_dir)
        return p
    except (ValueError, OSError):
        return None


def regular_case_path(case_dir: Path, rel: str) -> Path | None:
    """Return a contained regular file and reject symlinks in every path component."""
    rel_path = Path(rel)
    if rel_path.is_absolute() or not rel_path.parts \
            or any(part in {"", ".", ".."} for part in rel_path.parts):
        return None
    lexical = case_dir
    try:
        for part in rel_path.parts:
            lexical = lexical / part
            if lexical.is_symlink():
                return None
        resolved = safe_case_path(case_dir, rel)
        return resolved if resolved is not None and resolved.is_file() else None
    except OSError:
        return None


def check_manifest(case_dir: Path, d: dict, errors: list[str]):
    if not d.get("frozen_at") or not d.get("data_cutoff"):
        errors.append("输入清单缺 frozen_at 或 data_cutoff")
    files = d.get("files")
    if not isinstance(files, list) or not files:
        errors.append("输入清单 files 为空")
        return
    raw_count = 0
    for i, item in enumerate(files):
        if not isinstance(item, dict):
            errors.append(f"输入清单 files[{i}] 不是对象")
            continue
        rel = item.get("path")
        if item.get("evidence_layer") == "raw":
            raw_count += 1
        if not rel or not item.get("sha256") or item.get("size") is None:
            errors.append(f"输入清单 files[{i}] 缺 path/sha256/size")
            continue
        p = regular_case_path(case_dir, str(rel))
        if p is None:
            errors.append(f"输入文件不存在、越界或不是普通非符号链接文件: {rel}")
            continue
        declared_size = strict_int(item["size"], f"输入文件 {rel} size", errors)
        if declared_size is None:
            continue
        if p.stat().st_size != declared_size:
            errors.append(f"输入文件大小变化: {rel}")
            continue
        if sha256_file(p).lower() != str(item["sha256"]).lower():
            errors.append(f"输入文件哈希变化: {rel}")
    if raw_count == 0:
        errors.append("输入清单没有 evidence_layer=raw 的原始证据")
    late = d.get("late_additions", [])
    if late and not all(isinstance(x, dict) and x.get("path") and x.get("added_at")
                        for x in late):
        errors.append("late_additions 必须逐项记录 path 与 added_at")


def check_accounting(d: dict, errors: list[str]):
    if d.get("schema") != "accounting-gate/v1" or d.get("exit_code") != 0 \
            or not isinstance(d.get("checks"), dict) or not d.get("checks"):
        errors.append("记账模型缺生产 gate schema/exit/checks receipt")
        return
    verdict = d.get("status", d.get("verdict", d.get("mode")))
    if not status_pass(verdict, ACCOUNTING_EXTRA):
        errors.append(f"记账模型未放行: {verdict!r}")


def check_reconciliation(d: dict, errors: list[str]):
    if d.get("schema") != "reconciliation-report/v2" or not isinstance(d.get("target"), dict):
        errors.append("四查对账缺 v2 target/子工具 receipts (balance/supply/supply_truth/time)")
        return
    checks = d.get("checks", d)
    aliases = {
        "balance": ("balance", "balance_reconciliation"),
        "supply": ("supply", "supply_closure"),
        "supply_truth": ("supply_truth", "supply_truth_gate"),
        "time": ("time", "time_anchors", "temporal"),
    }
    for label, keys in aliases.items():
        value = next((checks[k] for k in keys if k in checks), None)
        if isinstance(value, dict):
            value = value.get("status", value.get("passed"))
        if not status_pass(value):
            errors.append(f"四查对账未通过: {label}")


def unresolved_count(d: dict, errors: list[str] | None = None, label="资产") -> int:
    lists = [d.get(k) for k in ("unresolved_candidates", "unresolved", "unresolved_items")
             if isinstance(d.get(k), list)]
    actual = sum(len(x) for x in lists)
    declared = d.get("unresolved_count")
    if declared is not None:
        local_errors = errors if errors is not None else []
        declared_n = strict_int(declared, f"{label} unresolved_count", local_errors)
        if declared_n is None:
            return actual or 1
        if lists and declared_n != actual and errors is not None:
            errors.append(f"{label} unresolved_count={declared_n} 与明细={actual} 不一致")
        return actual if lists else declared_n
    return actual


def check_classification(d: dict, errors: list[str]):
    threshold = d.get("current_owner_threshold_pct")
    threshold_n = finite_decimal(threshold, "current_owner_threshold_pct", errors)
    if threshold_n is None or threshold_n > Decimal("0.1"):
        errors.append("地址分类未覆盖全部当前≥0.1%总供应 owner（0.1%/0.2% 双线，tiering §6a）")
    float_threshold = d.get("current_owner_float_threshold_pct")
    if float_threshold is not None:
        float_n = finite_decimal(float_threshold, "current_owner_float_threshold_pct", errors)
        if float_n is None or float_n > Decimal("0.2"):
            errors.append("地址分类流通线阈值超 0.2%（tiering §6a 双线）")
    if not d.get("historical_peak_candidates_included"):
        errors.append("地址分类未覆盖历史峰值候选")
    n_unresolved = unresolved_count(d, errors, "地址分类")
    if n_unresolved:
        errors.append(f"地址分类仍有 {n_unresolved} 个未决候选")


def check_ledger(name: str, d: dict, errors: list[str]):
    entries = d.get("entries", d.get("entities"))
    if not isinstance(entries, list):
        errors.append(f"{name} 缺 entries/entities 数组")
        entries = []
    if not entries:
        errors.append(f"{name} 明细为空——空壳账本不得通过正式发布闸")
    if name == "economic_control_ledger.json":
        n_top = unresolved_count(d, errors, "经济控制账")
        if n_top:
            errors.append(f"经济控制账仍有 {n_top} 项未决暴露")
        nested = sum(len(e.get("unresolved_facility_exposure") or [])
                     for e in entries if isinstance(e, dict))
        if nested:
            errors.append(f"经济控制账实体内共有 {nested} 项 unresolved_facility_exposure 未裁决")


def raw_int(value, label, errors):
    n = strict_int(value, label, errors, raw=True)
    return 0 if n is None else n


def check_three_ledgers(case_dir: Path, data: dict, errors: list[str]):
    """Recompute membership -> position -> economic control closure from details."""
    md = data.get("membership_ledger.json", {})
    pd = data.get("position_ledger.json", {})
    ed = data.get("economic_control_ledger.json", {})
    members = md.get("entries", md.get("entities", []))
    positions = pd.get("entries", pd.get("entities", []))
    economics = ed.get("entries", ed.get("entities", []))
    if not all(isinstance(x, list) and x for x in (members, positions, economics)):
        return

    member_map = {}
    snapshot_cache = {}

    def load_balance_snapshot(source: dict, label: str):
        if not isinstance(source, dict):
            errors.append(f"{label} 缺 balance_source 来源绑定")
            return None
        rel = str(source.get("path", "")).strip()
        expected_sha = str(source.get("sha256", "")).strip().lower()
        as_of_block = source.get("as_of_block")
        if not rel or len(expected_sha) != 64 or as_of_block is None:
            errors.append(f"{label}.balance_source 缺 path/sha256/as_of_block")
            return None
        p = regular_case_path(case_dir, rel)
        if p is None:
            errors.append(f"{label}.balance_source 文件不存在或越界: {rel}")
            return None
        cache_key = (str(p), expected_sha, str(as_of_block))
        if cache_key in snapshot_cache:
            return snapshot_cache[cache_key]
        if sha256_file(p).lower() != expected_sha:
            errors.append(f"{label}.balance_source sha256 与当前快照不一致")
            snapshot_cache[cache_key] = None
            return None
        snapshot = load_json(p, errors)
        if snapshot.get("schema") != "address-balance-snapshot/v1" \
                or snapshot.get("as_of_block") != as_of_block:
            errors.append(f"{label}.balance_source schema/as_of_block 不一致")
            snapshot_cache[cache_key] = None
            return None
        rows = snapshot.get("entries")
        if not isinstance(rows, list):
            errors.append(f"{label}.balance_source entries 非数组")
            snapshot_cache[cache_key] = None
            return None
        balances = {}
        for j, item in enumerate(rows):
            if not isinstance(item, dict) or not str(item.get("address", "")).strip():
                errors.append(f"{label}.balance_source.entries[{j}] 缺地址")
                continue
            addr = str(item["address"]).strip()
            key = addr.lower() if addr.lower().startswith("0x") else addr
            if key in balances:
                errors.append(f"{label}.balance_source 地址重复: {addr}")
            balances[key] = raw_int(item.get("balance_raw"),
                                    f"{label}.balance_source.entries[{j}].balance_raw",
                                    errors)
        snapshot_cache[cache_key] = balances
        return balances

    for i, row in enumerate(members):
        if not isinstance(row, dict):
            errors.append(f"membership[{i}] 不是对象")
            continue
        entity, address = str(row.get("entity_id", "")).strip(), str(row.get("address", "")).strip()
        status = str(row.get("membership", "")).strip()
        if not entity or not address or status not in {"strict", "expanded", "excluded"}:
            errors.append(f"membership[{i}] 缺 entity_id/address 或 membership 非法")
            continue
        key = address.lower() if address.lower().startswith("0x") else address
        if key in member_map:
            errors.append(f"成员地址重复: {address}")
        balance = None
        if status != "excluded":
            if row.get("as_of_balance_raw") is None:
                proof = row.get("zero_balance_proof")
                if not isinstance(proof, dict) or not proof:
                    errors.append(f"membership[{i}] 缺 as_of_balance_raw 或 zero_balance_proof")
                else:
                    balance = 0
            else:
                balance = raw_int(row.get("as_of_balance_raw"),
                                  f"membership[{i}].as_of_balance_raw", errors)
            balances = load_balance_snapshot(row.get("balance_source"), f"membership[{i}]")
            if balances is not None and balance is not None:
                if key not in balances:
                    errors.append(f"membership[{i}] 地址不在绑定的余额快照: {address}")
                elif balances[key] != balance:
                    errors.append(f"membership[{i}] as_of_balance_raw 与绑定快照不一致")
        member_map[key] = (entity, status, balance)

    pos_seen, wallet_by_entity, position_by_address = set(), {}, {}
    for i, row in enumerate(positions):
        if not isinstance(row, dict):
            errors.append(f"position[{i}] 不是对象")
            continue
        entity = str(row.get("entity_id", "")).strip()
        address = str(row.get("address", "")).strip()
        location = str(row.get("location_id", "")).strip()
        if not entity or not address or not location:
            errors.append(f"position[{i}] 缺 entity_id/address/location_id")
            continue
        addr_key = address.lower() if address.lower().startswith("0x") else address
        if addr_key not in member_map or member_map[addr_key][0] != entity \
                or member_map[addr_key][1] == "excluded":
            errors.append(f"position[{i}] 地址未映射到同实体有效成员: {address}")
        key = (location, addr_key)
        if key in pos_seen:
            errors.append(f"位置账重复 location/address: {key}")
        pos_seen.add(key)
        amt = raw_int(row.get("amount_raw"), f"position[{i}].amount_raw", errors)
        wallet_by_entity[entity] = wallet_by_entity.get(entity, 0) + amt
        position_by_address[addr_key] = position_by_address.get(addr_key, 0) + amt

    for address, (entity, status, balance) in member_map.items():
        if status == "excluded" or balance is None:
            continue
        positioned = position_by_address.get(address, 0)
        if positioned != balance:
            errors.append(f"实体 {entity} 地址 {address} 逐地址余额与位置账不闭合: "
                          f"{positioned} != {balance}")

    econ_ids, dc_keys = set(), set()
    for i, row in enumerate(economics):
        if not isinstance(row, dict):
            errors.append(f"economic[{i}] 不是对象")
            continue
        entity = str(row.get("entity_id", "")).strip()
        if not entity or entity in econ_ids:
            errors.append(f"economic[{i}] entity_id 缺失或重复")
            continue
        econ_ids.add(entity)
        wallet = raw_int(row.get("wallet_self_held_raw"),
                         f"economic[{i}].wallet_self_held_raw", errors)
        if wallet != wallet_by_entity.get(entity, 0):
            errors.append(f"实体 {entity} 钱包自持与位置账不闭合: {wallet} != "
                          f"{wallet_by_entity.get(entity, 0)}")
        claims = row.get("confirmed_facility_claims") or []
        if not isinstance(claims, list):
            errors.append(f"economic[{i}].confirmed_facility_claims 非数组")
            claims = []
        facility_sum = 0
        for j, claim in enumerate(claims):
            if not isinstance(claim, dict):
                errors.append(f"economic[{i}].claims[{j}] 非对象")
                continue
            facility_sum += raw_int(claim.get("token_raw"),
                                    f"economic[{i}].claims[{j}].token_raw", errors)
            key = str(claim.get("double_count_key", "")).strip()
            if not key or key in dc_keys:
                errors.append(f"economic[{i}].claims[{j}] double_count_key 缺失或重复")
            dc_keys.add(key)
            if not claim.get("ownership_evidence") or not claim.get("amount_method") \
                    or claim.get("as_of_block") is None:
                errors.append(f"economic[{i}].claims[{j}] 缺所有权/数量算法/目标块证据")
        confirmed = raw_int(row.get("confirmed_economic_control_raw"),
                            f"economic[{i}].confirmed_economic_control_raw", errors)
        if confirmed != wallet + facility_sum:
            errors.append(f"实体 {entity} 经济控制算术不闭合: {confirmed} != {wallet}+{facility_sum}")

    active_entities = {entity for entity, status, _ in member_map.values()
                       if status != "excluded"}
    if active_entities != econ_ids or set(wallet_by_entity) != econ_ids:
        errors.append("三账实体集合不闭合（成员→位置→经济控制存在漏记或多记）")


def check_dormant(case_dir: Path, d: dict, errors: list[str]):
    if not d.get("full_history_event_replay"):
        errors.append("静置仓审计不是基于全量逐事件重放")
    required = ("historical_peaks", "zeroed_or_drawn_down",
                "long_dormant", "critical_window_upstream", "boundary_ring")
    coverage = d.get("coverage", {})
    for key in required:
        if not status_pass(coverage.get(key)):
            errors.append(f"静置仓审计覆盖未通过: {key}")
    n_unresolved = unresolved_count(d, errors, "静置仓审计")
    if n_unresolved:
        errors.append(f"静置仓审计仍有 {n_unresolved} 个未决候选")
    # v6.9.1 集合对账（codex 复核修复：coverage 五键是自报布尔，闸不住漏仓——
    # 必须绑定 wave-scan/v3 落盘的候选全集并逐址对账；缺绑定/旧 schema 一律拒）。
    ref = d.get("universe_ref")
    if not isinstance(ref, dict) or not ref.get("path") or not ref.get("sha256"):
        errors.append("静置仓审计缺 universe_ref（须绑定 wave-scan/v3 报告的 path+sha256）")
        return
    wp = regular_case_path(case_dir, str(ref["path"]))
    if wp is None:
        errors.append(f"universe_ref 指向的 wave_scan 报告不存在: {ref.get('path')}")
        return
    if sha256_file(wp).lower() != str(ref["sha256"]).lower():
        errors.append("universe_ref sha256 与 wave_scan 报告实际内容不一致")
        return
    wr = load_json(wp, errors)
    universe = wr.get("scan_universe")
    if str(wr.get("schema")) != "wave-scan/v3" or not isinstance(universe, list):
        errors.append("wave_scan 报告缺 scan_universe 逐址全集（schema 须 wave-scan/v3，"
                      "旧 v2 产物只有计数无法对账——重跑 wave_scan）")
        return
    cands = d.get("candidates", [])
    if not isinstance(cands, list):
        cands = []

    def canon_addr(v) -> str:
        # v6.9.4（codex 验收 P1）：尾随空格/EVM 大小写变体可绕重复检测与对账——
        # 一律 strip；EVM(0x) 地址再统一小写（Solana base58 大小写敏感，不动大小写）。
        s = str(v or "").strip()
        return s.lower() if s.lower().startswith("0x") else s

    addr_list = [canon_addr(c["candidate_address"]) for c in cands
                 if isinstance(c, dict) and str(c.get("candidate_address") or "").strip()]
    cand_addrs = set(addr_list)
    # v6.9.3（codex 验收 P1）：同一地址多行冲突裁决会被 set 静默吞并——重复即拒。
    if len(addr_list) != len(cand_addrs):
        dup = sorted({a for a in addr_list if addr_list.count(a) > 1})
        errors.append(f"静置仓候选地址重复 {len(dup)} 个（示例 {dup[:3]}）"
                      "——同址多行裁决可互相矛盾，候选地址必须唯一（规范化后判重）")
    missing = [str(u.get("addr")) for u in universe
               if isinstance(u, dict) and u.get("must_adjudicate")
               and canon_addr(u.get("addr")) not in cand_addrs]
    if missing:
        errors.append(f"候选全集对账失败: {len(missing)} 个必裁决地址不在审计候选内"
                      f"（示例 {missing[:3]}）——coverage 自报通过不作数")
    # v6.9.2（codex 验收 P1）：挂名≠裁决——每条列出的候选必须有地址＋合法三类裁决＋理由，
    # 机器逐条重验，自报 unresolved_count=0 不作数（v6.9.3 补：无地址的裁决记录同拒）。
    valid_decisions = {"strict", "expanded", "excluded"}
    bad = [str((c.get("candidate_address") if isinstance(c, dict) else None)
               or f"candidates[{i}]")
           for i, c in enumerate(cands)
           if not isinstance(c, dict)
           or not str(c.get("candidate_address") or "").strip()
           or str(c.get("boundary_decision", "")).lower() not in valid_decisions
           or not str(c.get("decision_reason", "")).strip()]
    if bad:
        errors.append(f"静置仓候选 {len(bad)} 条缺地址或缺合法裁决"
                      f"（candidate_address 非空＋boundary_decision 须 strict/expanded/excluded"
                      f"＋decision_reason 非空；示例 {bad[:3]}）——仅把地址挂进名单不算裁决")


def check_daily_peaks(case_dir: Path, errors: list[str]):
    """日级峰值口径闭环（v6.9.1）：案目录出现 peaks_summary.json 即视为用了
    peaks_daily 替代件——旧上界公式产物拒收（Σmax(day_delta,0) 非恒等上界，
    同日等额进出会漏），且四类触发日必须有显式产物（空也要声明）。"""
    ps_path = case_dir / "peaks_summary.json"
    if not ps_path.is_file():
        return
    ps = load_json(ps_path, errors)
    if str(ps.get("ub_formula")) != "prev_close_plus_gross_in/v2":
        errors.append("peaks_daily 产物是旧上界公式（缺 ub_formula=prev_close_plus_gross_in/v2）"
                      "——同日等额进出会被对冲漏检，升级脚本重跑")
    # v6.9.2（codex 验收 P2）：目录复用时残留的旧 trigger_days.json 不作数——
    # 本次运行必须真带 --trigger-days，且产物哈希与 summary 登记咬合。
    if not ps.get("trigger_days_file"):
        errors.append("peaks_daily 本次运行未带 --trigger-days（四类触发日义务未履行）"
                      "——目录里残留的旧 trigger_days.json 不作数，带触发日清单重跑")
        return
    tp = case_dir / "trigger_days.json"
    if not tp.is_file() or tp.is_symlink():
        errors.append("peaks_summary 声称产出触发日但 trigger_days.json 缺失")
        return
    expected = str(ps.get("trigger_days_sha256", "")).lower()
    if not expected or sha256_file(tp).lower() != expected:
        errors.append("trigger_days.json 与本次 peaks_daily 运行不咬合"
                      "（sha256 不匹配或 summary 未登记）——陈旧/换包产物拒收")
    td = load_json(tp, errors)
    if str(td.get("schema")) != "trigger-days-replay/v1":
        errors.append("trigger_days.json schema 非法（须 trigger-days-replay/v1）")
    elif not td.get("days") and not td.get("empty_reason"):
        errors.append("trigger_days.json 触发日为空且无 empty_reason 显式声明")


def check_reproduce_receipt(case_dir: Path, rel, cid, errors: list[str]):
    """Revalidate a controlled receipt; never execute command text from a claim."""
    if not isinstance(rel, str) or not rel.strip():
        errors.append(f"confirmed 命题 {cid} 缺 reproduce receipt")
        return
    receipt_path = regular_case_path(case_dir, rel)
    if receipt_path is None:
        errors.append(f"命题 {cid} reproduce receipt 路径非法或不存在: {rel}")
        return
    receipt = load_json(receipt_path, errors)
    if receipt.get("schema") != "reproduce-receipt/v2" or receipt.get("status") != "PASS" \
            or receipt.get("exit_code") != 0:
        errors.append(f"命题 {cid} reproduce receipt 非 PASS/exit 0")
    freshness = receipt.get("freshness")
    if not isinstance(freshness, dict) or not freshness.get("nonce") \
            or freshness.get("staging_created_by_controller") is not True \
            or freshness.get("inode_preserved") is not True \
            or freshness.get("output_absent_before_run") is not True \
            or not receipt.get("started_at_utc") or not receipt.get("finished_at_utc"):
        errors.append(f"命题 {cid} reproduce receipt 缺本次运行新鲜性证明")
    entry = receipt.get("entrypoint")
    if not isinstance(entry, dict) or entry.get("path") != "reproduce_audit.py":
        errors.append(f"命题 {cid} reproduce receipt 非受控固定入口 reproduce_audit.py")
    else:
        entry_path = case_dir / "reproduce_audit.py"
        if entry_path.is_symlink() or not entry_path.is_file():
            errors.append(f"命题 {cid} 固定入口脚本不存在或为符号链接")
        elif entry.get("sha256") != sha256_file(entry_path):
            errors.append(f"命题 {cid} 入口脚本哈希漂移")
    manifest = receipt.get("input_manifest")
    manifest_path = case_dir / "audit_input_manifest.json"
    manifest_ok = manifest_path.is_file() and not manifest_path.is_symlink()
    actual_manifest_sha = sha256_file(manifest_path) if manifest_ok else None
    if not isinstance(manifest, dict) or manifest.get("path") != "audit_input_manifest.json" \
            or manifest.get("sha256") != actual_manifest_sha:
        errors.append(f"命题 {cid} reproduce receipt 输入 manifest 未绑定当前冻结输入")
    args = receipt.get("args")
    if not isinstance(args, list) or not all(isinstance(x, str) for x in args):
        errors.append(f"命题 {cid} reproduce receipt args 非字符串数组")
    output = receipt.get("output")
    if not isinstance(output, dict):
        errors.append(f"命题 {cid} reproduce receipt 缺输出摘要")
        return
    out_rel = output.get("path")
    out_path = regular_case_path(case_dir, str(out_rel or ""))
    if out_path is None:
        errors.append(f"命题 {cid} reproduce 输出不存在或路径非法")
        return
    if output.get("size") != out_path.stat().st_size or output.get("sha256") != sha256_file(out_path):
        errors.append(f"命题 {cid} reproduce 输出大小/哈希漂移")
    try:
        out_json = json.loads(out_path.read_text(encoding="utf-8"))
        summary = out_json.get("summary") if isinstance(out_json, dict) and "summary" in out_json \
            else out_json
        if receipt.get("summary_sha256") != canonical_json_sha(summary):
            errors.append(f"命题 {cid} reproduce 输出摘要不一致")
    except Exception as exc:
        errors.append(f"命题 {cid} reproduce 输出摘要不可读: {exc}")


def check_claims(case_dir: Path, d: dict, report: Path | None, errors: list[str]):
    claims = d.get("claims")
    if not isinstance(claims, list) or not claims:
        errors.append("claim_registry.json 没有 claims")
        return set()
    if report:
        expected = d.get("report_sha256")
        if report.is_symlink() or not report.is_file():
            errors.append("待发布报告不存在或为符号链接")
        elif not expected:
            errors.append("命题表缺 report_sha256，无法证明覆盖当前报告版本")
        elif sha256_file(report) != str(expected).lower():
            errors.append("命题表 report_sha256 与待发布报告不一致")
    claim_types = set()
    ids = set()
    for i, claim in enumerate(claims):
        if not isinstance(claim, dict):
            errors.append(f"claims[{i}] 不是对象")
            continue
        cid = claim.get("claim_id")
        ctype = claim.get("claim_type")
        verdict = str(claim.get("verdict", "")).lower()
        if not cid or cid in ids:
            errors.append(f"claims[{i}] claim_id 缺失或重复")
        ids.add(cid)
        claim_types.add(ctype)
        if not claim.get("statement") or not claim.get("report_locations"):
            errors.append(f"命题 {cid} 缺 statement/report_locations")
        if verdict not in {"confirmed", "weakened", "refuted", "unverified"}:
            errors.append(f"命题 {cid} verdict 非法")
        if verdict == "confirmed":
            evidence = claim.get("evidence_files") or []
            if not evidence:
                errors.append(f"confirmed 命题 {cid} 缺原始证据")
            for rel in evidence:
                p = regular_case_path(case_dir, str(rel))
                if p is None:
                    errors.append(f"命题 {cid} 证据文件不存在: {rel}")
            check_reproduce_receipt(case_dir, claim.get("reproduce_receipt"), cid, errors)
            if claim.get("blocking_unresolved"):
                errors.append(f"命题 {cid} 尚有阻断项却标 confirmed")
        if ctype in DECISIVE_TYPES and verdict == "confirmed":
            if not claim.get("counter_hypotheses"):
                errors.append(f"关键命题 {cid} 未记录备择解释")
        if ctype == "negative_exhaustive" and verdict == "confirmed":
            unresolved = strict_int(claim.get("unresolved_candidates", 1),
                                    f"命题 {cid} unresolved_candidates", errors)
            if not claim.get("scope_complete") or unresolved is None or unresolved:
                errors.append(f"完整阴性命题 {cid} 未证明候选集完整且未决为零")
        if ctype in {"cex_identity", "cex_channel"} and verdict == "confirmed":
            if claim.get("beneficial_owner_proven") is not True:
                errors.append(f"CEX命题 {cid} 未证明最终受益人，不得作排他性确权")
    return claim_types


def check_adversarial(d: dict, errors: list[str]):
    if d.get("schema") != "adversarial-review/v2" or not isinstance(d.get("target"), dict):
        errors.append("对抗复核缺 v2 target/runner receipts")
        return
    reviews = d.get("reviews")
    if not isinstance(reviews, list):
        errors.append("对抗复核缺 reviews 数组")
        return
    roles = {str(r.get("role", "")).lower() for r in reviews if isinstance(r, dict)}
    if not any("completeness" in x for x in roles):
        errors.append("对抗复核缺完整性批评角色")
    if not any(("attribution" in x or "entity" in x) for x in roles):
        errors.append("对抗复核缺实体归因怀疑者")
    blockers = d.get("blocking_findings", [])
    unresolved = [x for x in blockers if not isinstance(x, dict) or not x.get("resolved")]
    if unresolved:
        errors.append(f"对抗复核仍有 {len(unresolved)} 个未关闭发布否决项")
    if not status_pass(d.get("release_decision")):
        errors.append("对抗复核 release_decision 未放行")


def check_chart(d: dict, errors: list[str]):
    required = (
        "same_grain_series", "last_day_snapshot_match", "supply_closed",
        "large_address_coverage_complete", "gap_and_interpolation_check_passed",
        "ledger_membership_match",
    )
    for key in required:
        if not status_pass(d.get(key)):
            errors.append(f"历史图对账未通过: {key}")
    if d.get("negative_clamp_used"):
        errors.append("历史图使用负值钳零")
    if str(d.get("series_method", "")).lower() in {"mixed_interpolation", "forward_fill_closure"}:
        errors.append("历史图使用混合插值或末日封口")


def run(case_dir: Path, report: Path | None, *, profile="independent-audit"):
    errors = []
    case_dir = case_dir.resolve()
    if profile not in REQUIRED_BY_PROFILE:
        raise ValueError(f"未知发布 profile: {profile}")
    required = REQUIRED_BY_PROFILE[profile]
    missing = [name for name in required if not (case_dir / name).is_file()]
    errors.extend(f"缺必需资产: {name}" for name in missing)
    data = {}
    for name in required:
        p = case_dir / name
        if p.suffix == ".json" and p.is_file():
            data[name] = load_json(p, errors)
    check_formal_case_chain(data, errors)
    if "audit_input_manifest.json" in data:
        check_manifest(case_dir, data["audit_input_manifest.json"], errors)
    try:
        import shared_release_receipt
        errors.extend(f"共享发布 receipt: {x}" for x in shared_release_receipt.validate_bundle(case_dir))
    except Exception as exc:
        errors.append(f"共享发布 receipt validator 失败: {exc}")
    if "accounting_mode.json" in data:
        check_accounting(data["accounting_mode.json"], errors)
    if "reconciliation_report.json" in data:
        check_reconciliation(data["reconciliation_report.json"], errors)
    if "address_classification.json" in data:
        check_classification(data["address_classification.json"], errors)
    for name in ("membership_ledger.json", "position_ledger.json",
                 "economic_control_ledger.json"):
        if name in data:
            check_ledger(name, data[name], errors)
    check_three_ledgers(case_dir, data, errors)
    if "dormant_warehouse_audit.json" in data:
        check_dormant(case_dir, data["dormant_warehouse_audit.json"], errors)
    check_daily_peaks(case_dir, errors)
    claim_types = set()
    if "claim_registry.json" in data:
        claim_types = check_claims(case_dir, data["claim_registry.json"], report, errors)
    if "adversarial_review.json" in data:
        check_adversarial(data["adversarial_review.json"], errors)
    if profile == "new-analysis" and "distribution_scan.json" in data:
        try:
            import holder_distribution_scan
            errors.extend("持仓分布 initial scan: " + x for x in
                          holder_distribution_scan.validate_scan(
                              case_dir, "distribution_scan.json", "initial"))
        except Exception as exc:
            errors.append(f"持仓分布 initial scan validator 失败: {exc}")
    if "historical_chart" in claim_types:
        chart_path = case_dir / "chart_reconciliation.json"
        if not chart_path.is_file():
            errors.append("报告含历史图命题但缺 chart_reconciliation.json")
        else:
            check_chart(load_json(chart_path, errors), errors)
    return errors


def main(argv=None):
    ap = argparse.ArgumentParser(description="独立筹码报告发布硬闸")
    ap.add_argument("case_dir", type=Path)
    ap.add_argument("--report", type=Path)
    ap.add_argument("--json-out", type=Path)
    ap.add_argument("--profile", choices=sorted(REQUIRED_BY_PROFILE),
                    default="independent-audit")
    args = ap.parse_args(argv)
    if not args.case_dir.is_dir():
        print(f"ERROR: 案目录不存在: {args.case_dir}", file=sys.stderr)
        return 1
    report_arg = args.report
    if report_arg and (not report_arg.is_file() or report_arg.is_symlink()):
        print(f"ERROR: 报告不存在或为符号链接: {report_arg}", file=sys.stderr)
        return 1
    report = report_arg.resolve() if report_arg else None
    errors = run(args.case_dir, report, profile=args.profile)
    result = {"status": "BLOCK" if errors else "PASS", "errors": errors}
    if args.json_out:
        args.json_out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8")
    if errors:
        print("BLOCK: 独立复核发布硬闸未通过")
        for item in errors:
            print(f"- {item}")
        return 2
    print(f"PASS: {args.profile} 必经发布门禁全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
