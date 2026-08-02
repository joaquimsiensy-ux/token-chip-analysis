#!/usr/bin/env python3
"""独立复核发布硬闸离线契约测试。"""

import hashlib
import importlib.util
import json
import os
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
GATE = HERE.parent / "report" / "audit_release_gate.py"
spec = importlib.util.spec_from_file_location("audit_release_gate", GATE)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def write_json(root, name, value):
    (root / name).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_case(root, historical=True):
    raw = root / "raw_transfers.jsonl"
    raw.write_text('{"from":"a","to":"b","raw":"1"}\n', encoding="utf-8")
    report = root / "report.md"
    report.write_text("# 审计报告\n", encoding="utf-8")
    write_json(root, "audit_input_manifest.json", {
        "frozen_at": "2026-07-26T00:00:00Z",
        "data_cutoff": "2026-07-25T23:59:59Z",
        "files": [{"path": raw.name, "size": raw.stat().st_size, "sha256": sha(raw),
                   "evidence_layer": "raw", "available_at_audit_start": True}],
        "late_additions": [],
    })
    write_json(root, "accounting_mode.json", {"status": "PASS", "mode": "standard"})
    write_json(root, "reconciliation_report.json", {
        "checks": {"balance": "PASS", "supply": "PASS",
                   "supply_truth": "PASS", "time": "PASS"}})
    write_json(root, "address_classification.json", {
        "current_owner_threshold_pct": 0.1,
        "current_owner_float_threshold_pct": 0.2,
        "historical_peak_candidates_included": True,
        "unresolved_count": 0,
    })
    write_json(root, "membership_ledger.json", {"entries": []})
    write_json(root, "position_ledger.json", {"entries": []})
    write_json(root, "economic_control_ledger.json", {
        "entries": [], "empty_reason": "夹具案例无达标庄级实体",
        "double_count_check_passed": True, "unresolved_count": 0})
    # v6.9.1：静置仓审计必须绑定 wave_scan v3 落盘全集并逐址对账（coverage 自报不作数）
    write_json(root, "wave_scan_report.json", {
        "schema": "wave-scan/v3",
        "scan_universe_count": 2,
        "scan_universe": [
            {"addr": "0xmustaddr", "peak_pct": 3.0, "must_adjudicate": True,
             "must_reasons": ["peak_ge_0.1pct", "dormant_ge_30d"]},
            {"addr": "0xminoraddr", "peak_pct": 0.03, "must_adjudicate": False,
             "must_reasons": []},
        ],
    })
    write_json(root, "dormant_warehouse_audit.json", {
        "full_history_event_replay": True,
        "coverage": {
            "historical_peaks": "PASS", "zeroed_or_drawn_down": "PASS",
            "long_dormant": "PASS", "critical_window_upstream": "PASS",
            "boundary_ring": "PASS",
        },
        "unresolved_count": 0,
        "universe_ref": {"path": "wave_scan_report.json",
                         "sha256": sha(root / "wave_scan_report.json")},
        "candidates": [{"candidate_address": "0xmustaddr",
                        "boundary_decision": "excluded",
                        "decision_reason": "夹具：静置巨仓已裁决"}],
    })
    ctype = "historical_chart" if historical else "snapshot_balance"
    write_json(root, "claim_registry.json", {
        "report_sha256": sha(report),
        "claims": [{
            "claim_id": "C1", "statement": "重算命题",
            "claim_type": ctype, "report_locations": ["report.md:1"],
            "verdict": "confirmed", "evidence_files": [raw.name],
            "reproduce_command": "python3 reproduce_audit.py",
            "counter_hypotheses": ["数据缺口"],
            "blocking_unresolved": False,
        }],
    })
    write_json(root, "adversarial_review.json", {
        "reviews": [
            {"role": "entity_attribution_skeptic"},
            {"role": "completeness_critic"},
        ],
        "blocking_findings": [],
        "release_decision": "PASS",
    })
    (root / "reproduce_audit.py").write_text("print('ok')\n", encoding="utf-8")
    if historical:
        write_json(root, "chart_reconciliation.json", {
            "series_method": "full_event_replay",
            "same_grain_series": True,
            "last_day_snapshot_match": True,
            "supply_closed": True,
            "large_address_coverage_complete": True,
            "gap_and_interpolation_check_passed": True,
            "ledger_membership_match": True,
            "negative_clamp_used": False,
        })
    return report


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        report = build_case(root)
        assert not gate.run(root, report), "完整合格案例应 PASS"

        # 输入冻结后变化必须阻断。
        (root / "raw_transfers.jsonl").write_text("tampered\n", encoding="utf-8")
        errors = gate.run(root, report)
        assert any("大小变化" in x or "哈希变化" in x for x in errors), errors

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        report = build_case(root)
        # 运营/CEX通道未证明最终受益人，不能 confirmed。
        claims = json.loads((root / "claim_registry.json").read_text())
        claims["claims"][0]["claim_type"] = "cex_channel"
        claims["claims"][0]["beneficial_owner_proven"] = False
        write_json(root, "claim_registry.json", claims)
        errors = gate.run(root, report)
        assert any("最终受益人" in x for x in errors), errors

        # 完整阴性结论候选不完整必须阻断。
        claims["claims"][0].update({
            "claim_type": "negative_exhaustive",
            "beneficial_owner_proven": True,
            "scope_complete": False,
            "unresolved_candidates": 2,
        })
        write_json(root, "claim_registry.json", claims)
        errors = gate.run(root, report)
        assert any("完整阴性命题" in x for x in errors), errors

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        report = build_case(root)
        chart = json.loads((root / "chart_reconciliation.json").read_text())
        chart.update({"series_method": "forward_fill_closure",
                      "negative_clamp_used": True})
        write_json(root, "chart_reconciliation.json", chart)
        errors = gate.run(root, report)
        assert any("末日封口" in x for x in errors), errors
        assert any("负值钳零" in x for x in errors), errors

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        report = build_case(root, historical=False)
        review = json.loads((root / "adversarial_review.json").read_text())
        review["blocking_findings"] = [{"id": "B1", "resolved": False}]
        write_json(root, "adversarial_review.json", review)
        errors = gate.run(root, report)
        assert any("发布否决项" in x for x in errors), errors

    # 6.5.0 修复反例：WARN 不再当 PASS；缺 supply_truth 阻断。
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        report = build_case(root, historical=False)
        write_json(root, "reconciliation_report.json", {
            "checks": {"balance": "WARN", "supply": "PASS", "time": "PASS"}})
        errors = gate.run(root, report)
        assert any("balance" in x for x in errors), errors
        assert any("supply_truth" in x for x in errors), errors

    # 6.5.0 修复反例：0.5% 旧线不再放行（现行 0.1%/0.2% 双线）。
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        report = build_case(root, historical=False)
        cls = json.loads((root / "address_classification.json").read_text())
        cls["current_owner_threshold_pct"] = 0.5
        write_json(root, "address_classification.json", cls)
        errors = gate.run(root, report)
        assert any("0.1%" in x for x in errors), errors

    # 6.5.0 修复反例：实体内嵌套未决设施暴露必须阻断；空账本须 empty_reason。
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        report = build_case(root, historical=False)
        write_json(root, "economic_control_ledger.json", {
            "entries": [{"entity_id": "e1",
                         "unresolved_facility_exposure": [{"facility": "cex"}]}],
            "double_count_check_passed": True, "unresolved_count": 0})
        errors = gate.run(root, report)
        assert any("unresolved_facility_exposure" in x for x in errors), errors
        write_json(root, "economic_control_ledger.json", {
            "entries": [], "double_count_check_passed": True, "unresolved_count": 0})
        errors = gate.run(root, report)
        assert any("empty_reason" in x for x in errors), errors

    # 6.9.1 修复反例（codex 复核）：静置仓候选全集对账——coverage 自报布尔不作数。
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        report = build_case(root, historical=False)
        da = json.loads((root / "dormant_warehouse_audit.json").read_text())
        # a) 缺 universe_ref 绑定 → BLOCK
        da_no_ref = {k: v for k, v in da.items() if k != "universe_ref"}
        write_json(root, "dormant_warehouse_audit.json", da_no_ref)
        errors = gate.run(root, report)
        assert any("universe_ref" in x for x in errors), errors
        # b) 必裁决地址不在审计候选 → BLOCK（孤仓漏检的机器拦截）
        da_missing = dict(da)
        da_missing["candidates"] = []
        write_json(root, "dormant_warehouse_audit.json", da_missing)
        errors = gate.run(root, report)
        assert any("对账失败" in x for x in errors), errors
        # c) wave_scan 报告扫描后被换（sha 不符）→ BLOCK
        write_json(root, "dormant_warehouse_audit.json", da)
        wr = json.loads((root / "wave_scan_report.json").read_text())
        wr["scan_universe"] = []
        write_json(root, "wave_scan_report.json", wr)
        errors = gate.run(root, report)
        assert any("不一致" in x for x in errors), errors
        # d) 旧 v2 产物（只有计数、无逐址全集）→ BLOCK
        write_json(root, "wave_scan_report.json",
                   {"schema": "wave-scan/v2", "scan_universe_count": 2})
        da_v2 = dict(da)
        da_v2["universe_ref"] = {"path": "wave_scan_report.json",
                                 "sha256": sha(root / "wave_scan_report.json")}
        write_json(root, "dormant_warehouse_audit.json", da_v2)
        errors = gate.run(root, report)
        assert any("scan_universe" in x for x in errors), errors

    # 6.9.1 修复反例（codex 复核）：日级峰值口径闭环。
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        report = build_case(root, historical=False)
        # e) 旧上界公式产物 → BLOCK（Σmax(day_delta,0) 同日对冲漏检）
        write_json(root, "peaks_summary.json", {"engine": "peaks_daily.py"})
        errors = gate.run(root, report)
        assert any("旧上界公式" in x for x in errors), errors
        # f) 新公式但四类触发日无产物 → BLOCK
        write_json(root, "peaks_summary.json",
                   {"engine": "peaks_daily.py",
                    "ub_formula": "prev_close_plus_gross_in/v2"})
        errors = gate.run(root, report)
        assert any("trigger_days.json" in x for x in errors), errors
        # g) 触发日空且无显式声明 → BLOCK
        write_json(root, "trigger_days.json",
                   {"schema": "trigger-days-replay/v1", "days": {},
                    "empty_reason": None})
        errors = gate.run(root, report)
        assert any("empty_reason" in x for x in errors), errors
        # h) 显式空声明 → 峰值/触发日检查放行
        write_json(root, "trigger_days.json",
                   {"schema": "trigger-days-replay/v1", "days": {},
                    "empty_reason": "夹具案：窗内无四类触发日"})
        errors = gate.run(root, report)
        assert not any(("trigger" in x or "上界" in x) for x in errors), errors

    print("PASS: audit_release_gate 净室资产/哈希/CEX受益权/阴性结论/"
          "图表封口与负钳零/对抗复核否决/四查WARN拦截/双线阈值/"
          "嵌套未决暴露/静置仓全集对账/日级峰值口径闭环十一类契约全过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

