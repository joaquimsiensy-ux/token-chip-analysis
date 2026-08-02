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
from pathlib import Path


REQUIRED = (
    "audit_input_manifest.json",
    "accounting_mode.json",
    "reconciliation_report.json",
    "address_classification.json",
    "membership_ledger.json",
    "position_ledger.json",
    "economic_control_ledger.json",
    "dormant_warehouse_audit.json",
    "claim_registry.json",
    "adversarial_review.json",
    "reproduce_audit.py",
)
PASS_WORDS = {"pass", "passed", "ok"}
ACCOUNTING_EXTRA = frozenset({"standard"})
DECISIVE_TYPES = {
    "entity_attribution", "economic_control", "whale_tier", "cex_identity",
    "cex_channel", "historical_peak", "historical_chart", "negative_exhaustive",
}


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
        p = safe_case_path(case_dir, str(rel))
        if p is None:
            errors.append(f"输入文件越出案目录: {rel}")
            continue
        if not p.is_file():
            errors.append(f"输入文件不存在: {rel}")
            continue
        if p.stat().st_size != int(item["size"]):
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
    verdict = d.get("status", d.get("verdict", d.get("mode")))
    if not status_pass(verdict, ACCOUNTING_EXTRA):
        errors.append(f"记账模型未放行: {verdict!r}")


def check_reconciliation(d: dict, errors: list[str]):
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
        try:
            declared_n = int(declared)
        except (TypeError, ValueError):
            if errors is not None:
                errors.append(f"{label} unresolved_count 非整数")
            return actual or 1
        if lists and declared_n != actual and errors is not None:
            errors.append(f"{label} unresolved_count={declared_n} 与明细={actual} 不一致")
        return actual if lists else declared_n
    return actual


def check_classification(d: dict, errors: list[str]):
    threshold = d.get("current_owner_threshold_pct")
    if threshold is None or float(threshold) > 0.1:
        errors.append("地址分类未覆盖全部当前≥0.1%总供应 owner（0.1%/0.2% 双线，tiering §6a）")
    float_threshold = d.get("current_owner_float_threshold_pct")
    if float_threshold is not None and float(float_threshold) > 0.2:
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
    try:
        n = int(value)
    except (TypeError, ValueError):
        errors.append(f"{label} 不是整数 raw amount")
        return 0
    if n < 0:
        errors.append(f"{label} 为负数")
    return n


def check_three_ledgers(data: dict, errors: list[str]):
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
        member_map[key] = (entity, status)

    pos_seen, wallet_by_entity = set(), {}
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

    active_entities = {entity for entity, status in member_map.values() if status != "excluded"}
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
    # 必须绑定 wave_scan v3 落盘的候选全集并逐址对账；缺绑定/旧 schema 一律拒）。
    ref = d.get("universe_ref")
    if not isinstance(ref, dict) or not ref.get("path") or not ref.get("sha256"):
        errors.append("静置仓审计缺 universe_ref（须绑定 wave_scan v3 报告的 path+sha256）")
        return
    wp = safe_case_path(case_dir, str(ref["path"]))
    if wp is None or not wp.is_file():
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
    if not tp.is_file():
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
    receipt_path = safe_case_path(case_dir, rel)
    raw_receipt = case_dir / rel
    if receipt_path is None or raw_receipt.is_symlink() or not receipt_path.is_file():
        errors.append(f"命题 {cid} reproduce receipt 路径非法或不存在: {rel}")
        return
    receipt = load_json(receipt_path, errors)
    if receipt.get("schema") != "reproduce-receipt/v1" or receipt.get("status") != "PASS" \
            or receipt.get("exit_code") != 0:
        errors.append(f"命题 {cid} reproduce receipt 非 PASS/exit 0")
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
    if not isinstance(manifest, dict) or manifest.get("path") != "audit_input_manifest.json" \
            or manifest.get("sha256") != sha256_file(manifest_path):
        errors.append(f"命题 {cid} reproduce receipt 输入 manifest 未绑定当前冻结输入")
    args = receipt.get("args")
    if not isinstance(args, list) or not all(isinstance(x, str) for x in args):
        errors.append(f"命题 {cid} reproduce receipt args 非字符串数组")
    output = receipt.get("output")
    if not isinstance(output, dict):
        errors.append(f"命题 {cid} reproduce receipt 缺输出摘要")
        return
    out_rel = output.get("path")
    out_path = safe_case_path(case_dir, str(out_rel or ""))
    if out_path is None or (case_dir / str(out_rel or "")).is_symlink() or not out_path.is_file():
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
        if not expected:
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
                p = safe_case_path(case_dir, str(rel))
                if p is None or not p.is_file():
                    errors.append(f"命题 {cid} 证据文件不存在: {rel}")
            check_reproduce_receipt(case_dir, claim.get("reproduce_receipt"), cid, errors)
            if claim.get("blocking_unresolved"):
                errors.append(f"命题 {cid} 尚有阻断项却标 confirmed")
        if ctype in DECISIVE_TYPES and verdict == "confirmed":
            if not claim.get("counter_hypotheses"):
                errors.append(f"关键命题 {cid} 未记录备择解释")
        if ctype == "negative_exhaustive" and verdict == "confirmed":
            if not claim.get("scope_complete") or int(claim.get("unresolved_candidates", 1)):
                errors.append(f"完整阴性命题 {cid} 未证明候选集完整且未决为零")
        if ctype in {"cex_identity", "cex_channel"} and verdict == "confirmed":
            if claim.get("beneficial_owner_proven") is not True:
                errors.append(f"CEX命题 {cid} 未证明最终受益人，不得作排他性确权")
    return claim_types


def check_adversarial(d: dict, errors: list[str]):
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


def run(case_dir: Path, report: Path | None):
    errors = []
    case_dir = case_dir.resolve()
    missing = [name for name in REQUIRED if not (case_dir / name).is_file()]
    errors.extend(f"缺必需资产: {name}" for name in missing)
    data = {}
    for name in REQUIRED:
        p = case_dir / name
        if p.suffix == ".json" and p.is_file():
            data[name] = load_json(p, errors)
    if "audit_input_manifest.json" in data:
        check_manifest(case_dir, data["audit_input_manifest.json"], errors)
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
    check_three_ledgers(data, errors)
    if "dormant_warehouse_audit.json" in data:
        check_dormant(case_dir, data["dormant_warehouse_audit.json"], errors)
    check_daily_peaks(case_dir, errors)
    claim_types = set()
    if "claim_registry.json" in data:
        claim_types = check_claims(case_dir, data["claim_registry.json"], report, errors)
    if "adversarial_review.json" in data:
        check_adversarial(data["adversarial_review.json"], errors)
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
    args = ap.parse_args(argv)
    if not args.case_dir.is_dir():
        print(f"ERROR: 案目录不存在: {args.case_dir}", file=sys.stderr)
        return 1
    report = args.report.resolve() if args.report else None
    if report and not report.is_file():
        print(f"ERROR: 报告不存在: {report}", file=sys.stderr)
        return 1
    errors = run(args.case_dir, report)
    result = {"status": "BLOCK" if errors else "PASS", "errors": errors}
    if args.json_out:
        args.json_out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8")
    if errors:
        print("BLOCK: 独立复核发布硬闸未通过")
        for item in errors:
            print(f"- {item}")
        return 2
    print("PASS: 独立复核必需资产、证据链、否决项与图表门禁全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
