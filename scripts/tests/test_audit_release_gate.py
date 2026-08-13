#!/usr/bin/env python3
"""独立复核发布硬闸离线契约测试。"""

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
GATE = HERE.parent / "report" / "audit_release_gate.py"
REPRODUCE = HERE.parent / "report" / "reproduce_receipt.py"
from formal_ready_test_harness import test_vertical_slices
spec = importlib.util.spec_from_file_location("audit_release_gate", GATE)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
_gate_run = gate.run


def _run_with_test_vertical_slices(*args, **kwargs):
    with test_vertical_slices():
        return _gate_run(*args, **kwargs)


gate.run = _run_with_test_vertical_slices


def write_json(root, name, value):
    (root / name).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def repo_ref(rel):
    path = REPO / rel
    return {"path": rel, "sha256": sha(path)}


def build_case(root, historical=True):
    raw = root / "raw_transfers.jsonl"
    raw.write_text('{"from":"a","to":"b","raw":"1"}\n', encoding="utf-8")
    write_json(root, "balances_snapshot.json", {
        "schema": "address-balance-snapshot/v1", "as_of_block": 123,
        "entries": [{"address": "0xabc", "balance_raw": "100"}],
    })
    report = root / "report.md"
    report.write_text("# 审计报告\n", encoding="utf-8")
    write_json(root, "audit_input_manifest.json", {
        "frozen_at": "2026-07-26T00:00:00Z",
        "data_cutoff": "2026-07-25T23:59:59Z",
        "files": [
            {"path": raw.name, "size": raw.stat().st_size, "sha256": sha(raw),
             "evidence_layer": "raw", "available_at_audit_start": True},
            {"path": "balances_snapshot.json",
             "size": (root / "balances_snapshot.json").stat().st_size,
             "sha256": sha(root / "balances_snapshot.json"),
             "evidence_layer": "derived", "available_at_audit_start": True},
        ],
        "late_additions": [],
    })
    target = {"chain": "bsc", "token": "0xtoken", "as_of_block": 123}
    write_json(root, "accounting_mode.json", {"schema": "accounting-gate/v1",
        "chain": "bsc", "token": "0xtoken", "as_of_block": 123,
        "tip_block": 123, "model_probe_block": 123,
        "producer": repo_ref("scripts/evm/accounting_gate.py"),
        "verdict": "PASS", "exit_code": 0, "mode": "standard",
        "checks": {"fot": {"status": "clean"}}})
    producers = {"balance": "scripts/evm/verify_recon.py",
                 "supply": "scripts/evm/verify_recon.py",
                 "supply_truth": "scripts/lib/supply_truth_gate.py",
                 "time": "scripts/lib/time_spotcheck.py"}
    checks = {}
    envelope_input = {"fixture": {"path": str(raw.resolve()), "size": raw.stat().st_size,
                                    "sha256": sha(raw)}}
    for key in ("balance", "supply", "supply_truth", "time"):
        evidence = root / f"{key}_receipt.json"
        if key in {"balance", "supply"}:
            receipt_doc = {"schema": "evm-reconciliation-receipt/v2", "target": target,
                "verdict": "PASS", "exit_code": 0, "observations": {
                    "supply_closure": {"closed": True, "negative_count": 0},
                    "balance_reconciliation": {"checked": 1, "matched": 1,
                        "mismatched": 0, "rpc_errors": 0},
                    "gmgn_comparison": {"checked": 1, "diff_count": 0}}}
        elif key == "supply_truth":
            receipt_doc = {"schema": "supply-truth-receipt/v3", "target": target,
                "gate": "supply_truth", "replay_net": "100",
                "onchain_total_supply": "100", "diff": "0",
                "diff_bps": 0.0, "tolerance_bps": 10,
                "decision_rule": "primary_form1", "burn_form": None,
                "primary_verdict": "PASS", "sink_reconciliation": None,
                "verdict": "PASS", "exit_code": 0}
        else:
            receipt_doc = {"schema": "time-spotcheck/v2", "target": target,
                "points": 1, "exact_match": 1, "mismatch": 0, "rpc_err": 0,
                "verdict": "PASS", "exit_code": 0}
        receipt_doc.update({"producer": repo_ref(producers[key]), "mode": "formal",
                            "inputs": ({"replay_stats": envelope_input["fixture"]}
                                       if key == "supply_truth" else envelope_input)})
        write_json(root, evidence.name, receipt_doc)
        checks[key] = {"status": "PASS", "exit_code": 0,
                       "receipt": {"path": evidence.name, "sha256": sha(evidence)},
                       "producer": repo_ref(producers[key])}
    write_json(root, "reconciliation_report.json", {
        "schema": "reconciliation-report/v2", "target": target,
        "producer": repo_ref("scripts/report/reconciliation_report.py"),
        "verdict": "PASS", "exit_code": 0, "checks": checks})
    write_json(root, "address_classification.json", {
        "current_owner_threshold_pct": 0.1,
        "current_owner_float_threshold_pct": 0.2,
        "historical_peak_candidates_included": True,
        "unresolved_count": 0, "unresolved_candidates": [],
    })
    write_json(root, "membership_ledger.json", {"entries": [
        {"entity_id": "e1", "address": "0xabc", "membership": "strict",
         "as_of_balance_raw": "100",
         "balance_source": {"path": "balances_snapshot.json",
                            "sha256": sha(root / "balances_snapshot.json"),
                            "as_of_block": 123}}]})
    write_json(root, "position_ledger.json", {"entries": [
        {"entity_id": "e1", "address": "0xabc", "location_id": "wallet:0xabc",
         "amount_raw": "100"}]})
    write_json(root, "economic_control_ledger.json", {
        "entries": [{"entity_id": "e1", "wallet_self_held_raw": "100",
                     "confirmed_facility_claims": [],
                     "confirmed_economic_control_raw": "100",
                     "unresolved_facility_exposure": []}],
        "double_count_check_passed": True, "unresolved_count": 0, "unresolved": []})
    # v6.9.1：静置仓审计必须绑定 wave-scan/v3 落盘全集并逐址对账（coverage 自报不作数）
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
    (root / "reproduce_audit.py").write_text(
        "import json, os\njson.dump({'summary': {'claim': 'C1', 'value': 1}}, "
        "open(os.environ.get('CHIP_REPRODUCE_OUTPUT','reproduce_output.json'),'w'))\n",
        encoding="utf-8")
    write_json(root, "reproduce_output.json", {"summary": {"claim": "C1", "value": 1}})
    summary = {"claim": "C1", "value": 1}
    write_json(root, "reproduce_receipt.json", {
        "schema": "reproduce-receipt/v2", "status": "PASS", "exit_code": 0,
        "entrypoint": {"path": "reproduce_audit.py", "sha256": sha(root / "reproduce_audit.py")},
        "input_manifest": {"path": "audit_input_manifest.json",
                           "sha256": sha(root / "audit_input_manifest.json")},
        "args": [],
        "output": {"path": "reproduce_output.json",
                   "size": (root / "reproduce_output.json").stat().st_size,
                   "sha256": sha(root / "reproduce_output.json")},
        "summary_sha256": hashlib.sha256(
            json.dumps(summary, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "started_at_utc": "2026-08-02T00:00:00Z",
        "finished_at_utc": "2026-08-02T00:00:01Z",
        "freshness": {"nonce": "fixture", "staging_created_by_controller": True,
                      "inode_preserved": True, "output_absent_before_run": True},
    })
    ctype = "historical_chart" if historical else "snapshot_balance"
    write_json(root, "claim_registry.json", {
        "report_sha256": sha(report),
        "claims": [{
            "claim_id": "C1", "statement": "重算命题",
            "claim_type": ctype, "report_locations": ["report.md:1"],
            "verdict": "confirmed", "evidence_files": [raw.name],
            "reproduce_command": "python3 reproduce_audit.py  # 仅说明",
            "reproduce_receipt": "reproduce_receipt.json",
            "counter_hypotheses": ["数据缺口"],
            "blocking_unresolved": False,
        }],
    })
    reviews = []
    runner = REPO / "scripts/report/adversarial_review_runner.py"
    for role in ("entity_attribution_skeptic", "completeness_critic"):
        entry = root / f"review_{role}.py"
        entry.write_text("import os\nfrom pathlib import Path\n"
                         "Path(os.environ['CHIP_REVIEW_OUTPUT']).write_text("
                         "'review evidence for '+os.environ['CHIP_REVIEW_ROLE']+'\\n')\n",
                         encoding="utf-8")
        artifact = root / f"review_{role}.md"
        execution = root / f"review_{role}_execution.json"
        for stale in (artifact, execution):
            if stale.exists():
                stale.unlink()
        proc = subprocess.run([sys.executable, str(runner), str(root), "--role", role,
                               "--entrypoint", entry.name, "--artifact", artifact.name,
                               "--receipt", execution.name], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        reviews.append({"role": role, "exit_code": 0,
                        "artifact": {"path": artifact.name, "size": artifact.stat().st_size,
                                     "sha256": sha(artifact)},
                        "runner": repo_ref("scripts/report/adversarial_review_runner.py"),
                        "execution_receipt": {"path": execution.name,
                                              "sha256": sha(execution)}})
    write_json(root, "adversarial_review.json", {
        "schema": "adversarial-review/v2", "target": target, "reviews": reviews,
        "blocking_findings": [], "release_decision": "PASS",
    })
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
    sys.path.insert(0, str(HERE.parent / "report"))
    from shared_release_receipt import create_bundle
    create_bundle(root)
    return report


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        report = build_case(root)
        assert not gate.run(root, report), "完整合格案例应 PASS"

        # Round4 P0-03：裸布尔不得替代生产 receipt。
    with tempfile.TemporaryDirectory() as td:
        root = Path(td); report = build_case(root, historical=False)
        write_json(root, "accounting_mode.json", {"status": True})
        write_json(root, "reconciliation_report.json",
                   {"balance": True, "supply": True, "supply_truth": True, "time": True})
        write_json(root, "adversarial_review.json", {"reviews": [
            {"role": "entity_attribution_skeptic"}, {"role": "completeness_critic"}],
            "blocking_findings": [], "release_decision": True})
        errors = gate.run(root, report, profile="new-analysis")
        assert errors, "caller booleans must not pass shared release gates"

    with tempfile.TemporaryDirectory() as td:
        root = Path(td); report = build_case(root, historical=False)
        recon = json.loads((root / "reconciliation_report.json").read_text())
        recon["checks"]["time"]["exit_code"] = 7
        write_json(root, "reconciliation_report.json", recon)
        errors = gate.run(root, report, profile="new-analysis")
        assert any("time" in x or "共享发布" in x for x in errors), errors
    with tempfile.TemporaryDirectory() as td:
        root = Path(td); report = build_case(root, historical=False)
        accounting = json.loads((root / "accounting_mode.json").read_text())
        accounting["checks"]["fot"]["status"] = "tampered-after-receipt"
        write_json(root, "accounting_mode.json", accounting)
        errors = gate.run(root, report, profile="new-analysis")
        assert any("input hashes changed" in x for x in errors), errors

    # 输入冻结后变化必须阻断。
        (root / "raw_transfers.jsonl").write_text("tampered\n", encoding="utf-8")
        errors = gate.run(root, report)
        assert any("大小变化" in x or "哈希变化" in x for x in errors), errors

    # 2026-08-02 B-05：空三账、汇总 count 压明细、跨账漏记/重复均须拒绝。
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        report = build_case(root, historical=False)
        write_json(root, "membership_ledger.json", {"entries": []})
        write_json(root, "position_ledger.json", {"entries": []})
        write_json(root, "economic_control_ledger.json", {"entries": [], "empty_reason": "自报空"})
        errors = gate.run(root, report)
        assert sum("明细为空" in x for x in errors) == 3, errors

        report = build_case(root, historical=False)
        cls = json.loads((root / "address_classification.json").read_text())
        cls.update({"unresolved_count": 0, "unresolved_candidates": [{"address": "0xbad"}]})
        write_json(root, "address_classification.json", cls)
        errors = gate.run(root, report)
        assert any("与明细=1 不一致" in x for x in errors), errors

        report = build_case(root, historical=False)
        pos = json.loads((root / "position_ledger.json").read_text())
        pos["entries"].append(dict(pos["entries"][0]))
        write_json(root, "position_ledger.json", pos)
        errors = gate.run(root, report)
        assert any("位置账重复" in x for x in errors), errors

    # P2-01：实体集合相同不代表逐地址余额闭合。
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        report = build_case(root, historical=False)
        write_json(root, "balances_snapshot.json", {
            "schema": "address-balance-snapshot/v1", "as_of_block": 123,
            "entries": [
                {"address": "0xabc", "balance_raw": "100"},
                {"address": "0xdef", "balance_raw": "5"},
            ],
        })
        members = json.loads((root / "membership_ledger.json").read_text())
        for row in members["entries"]:
            row["balance_source"]["sha256"] = sha(root / "balances_snapshot.json")
        members["entries"].append({
            "entity_id": "e1", "address": "0xdef", "membership": "expanded",
            "as_of_balance_raw": "5",
            "balance_source": {"path": "balances_snapshot.json",
                               "sha256": sha(root / "balances_snapshot.json"),
                               "as_of_block": 123},
        })
        write_json(root, "membership_ledger.json", members)
        manifest = json.loads((root / "audit_input_manifest.json").read_text())
        balance_item = next(x for x in manifest["files"]
                            if x["path"] == "balances_snapshot.json")
        balance_item.update({"size": (root / "balances_snapshot.json").stat().st_size,
                             "sha256": sha(root / "balances_snapshot.json")})
        write_json(root, "audit_input_manifest.json", manifest)
        receipt = json.loads((root / "reproduce_receipt.json").read_text())
        receipt["input_manifest"]["sha256"] = sha(root / "audit_input_manifest.json")
        write_json(root, "reproduce_receipt.json", receipt)
        errors = gate.run(root, report)
        assert any("逐地址余额" in x for x in errors), errors

        # 来源哈希不能由成员账自报漂移。
        members["entries"][0]["balance_source"]["sha256"] = "0" * 64
        write_json(root, "membership_ledger.json", members)
        errors = gate.run(root, report)
        assert any("balance_source sha256" in x for x in errors), errors

    # P2-01：零余额成员可用显式 zero_balance_proof，位置账缺行按 0 闭合。
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        report = build_case(root, historical=False)
        write_json(root, "balances_snapshot.json", {
            "schema": "address-balance-snapshot/v1", "as_of_block": 123,
            "entries": [
                {"address": "0xabc", "balance_raw": "100"},
                {"address": "0xzero", "balance_raw": "0"},
            ],
        })
        members = json.loads((root / "membership_ledger.json").read_text())
        for row in members["entries"]:
            row["balance_source"]["sha256"] = sha(root / "balances_snapshot.json")
        members["entries"].append({
            "entity_id": "e1", "address": "0xzero", "membership": "strict",
            "zero_balance_proof": {"method": "bound_snapshot_zero"},
            "balance_source": {"path": "balances_snapshot.json",
                               "sha256": sha(root / "balances_snapshot.json"),
                               "as_of_block": 123},
        })
        write_json(root, "membership_ledger.json", members)
        manifest = json.loads((root / "audit_input_manifest.json").read_text())
        balance_item = next(x for x in manifest["files"]
                            if x["path"] == "balances_snapshot.json")
        balance_item.update({"size": (root / "balances_snapshot.json").stat().st_size,
                             "sha256": sha(root / "balances_snapshot.json")})
        write_json(root, "audit_input_manifest.json", manifest)
        receipt = json.loads((root / "reproduce_receipt.json").read_text())
        receipt["input_manifest"]["sha256"] = sha(root / "audit_input_manifest.json")
        write_json(root, "reproduce_receipt.json", receipt)
        assert not gate.run(root, report), gate.run(root, report)

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

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        report = build_case(root, historical=False)
        (root / "reproduce_output.json").unlink()
        (root / "reproduce_receipt.json").unlink()
        p = subprocess.run([sys.executable, str(REPRODUCE), str(root)],
                           capture_output=True, text=True)
        assert p.returncode == 0 and not gate.run(root, report), p.stdout + p.stderr

    # P1-05：命令文本不是证据；只认受控 reproduce receipt 及当前文件重验。
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        report = build_case(root, historical=False)
        claims = json.loads((root / "claim_registry.json").read_text())
        claims["claims"][0]["reproduce_command"] = ""
        claims["claims"][0].pop("reproduce_receipt")
        write_json(root, "claim_registry.json", claims)
        errors = gate.run(root, report)
        assert any("reproduce receipt" in x for x in errors), errors

        report = build_case(root, historical=False)
        receipt = json.loads((root / "reproduce_receipt.json").read_text())
        (root / "fake.py").write_text("print('fake')\n")
        receipt["entrypoint"] = {"path": "fake.py", "sha256": sha(root / "fake.py")}
        write_json(root, "reproduce_receipt.json", receipt)
        errors = gate.run(root, report)
        assert any("固定入口" in x for x in errors), errors

        report = build_case(root, historical=False)
        (root / "reproduce_audit.py").write_text("print('drift')\n")
        errors = gate.run(root, report)
        assert any("入口脚本哈希" in x for x in errors), errors

        report = build_case(root, historical=False)
        receipt = json.loads((root / "reproduce_receipt.json").read_text())
        receipt["summary_sha256"] = "0" * 64
        write_json(root, "reproduce_receipt.json", receipt)
        errors = gate.run(root, report)
        assert any("输出摘要" in x for x in errors), errors

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
        assert any("明细为空" in x for x in errors), errors

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

    # 6.9.1 修复反例（codex 复核）：日级峰值口径闭环；6.9.2 补咬合（codex 验收 P2）。
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        report = build_case(root, historical=False)
        # e) 旧上界公式产物 → BLOCK（Σmax(day_delta,0) 同日对冲漏检）
        write_json(root, "peaks_summary.json", {"engine": "peaks_daily.py"})
        errors = gate.run(root, report)
        assert any("旧上界公式" in x for x in errors), errors
        # f) 本次运行未带 --trigger-days、目录残留旧 trigger_days.json → BLOCK（陈旧不作数）
        write_json(root, "trigger_days.json",
                   {"schema": "trigger-days-replay/v1", "days": {},
                    "empty_reason": "上一轮运行的残留产物"})
        write_json(root, "peaks_summary.json",
                   {"engine": "peaks_daily.py",
                    "ub_formula": "prev_close_plus_gross_in/v2",
                    "trigger_days_file": False, "trigger_days_sha256": None})
        errors = gate.run(root, report)
        assert any("未带 --trigger-days" in x for x in errors), errors
        # k) 带了触发日但产物被换包（sha 不咬合）→ BLOCK
        write_json(root, "peaks_summary.json",
                   {"engine": "peaks_daily.py",
                    "ub_formula": "prev_close_plus_gross_in/v2",
                    "trigger_days_file": True,
                    "trigger_days_sha256": "0" * 64})
        errors = gate.run(root, report)
        assert any("不咬合" in x for x in errors), errors
        # g) 咬合正确但触发日空且无显式声明 → BLOCK
        write_json(root, "trigger_days.json",
                   {"schema": "trigger-days-replay/v1", "days": {},
                    "empty_reason": None})
        write_json(root, "peaks_summary.json",
                   {"engine": "peaks_daily.py",
                    "ub_formula": "prev_close_plus_gross_in/v2",
                    "trigger_days_file": True,
                    "trigger_days_sha256": sha(root / "trigger_days.json")})
        errors = gate.run(root, report)
        assert any("empty_reason" in x for x in errors), errors
        # h) 显式空声明＋哈希咬合 → 峰值/触发日检查放行
        write_json(root, "trigger_days.json",
                   {"schema": "trigger-days-replay/v1", "days": {},
                    "empty_reason": "夹具案：窗内无四类触发日"})
        write_json(root, "peaks_summary.json",
                   {"engine": "peaks_daily.py",
                    "ub_formula": "prev_close_plus_gross_in/v2",
                    "trigger_days_file": True,
                    "trigger_days_sha256": sha(root / "trigger_days.json")})
        errors = gate.run(root, report)
        assert not any(("trigger" in x or "上界" in x) for x in errors), errors

    # 6.9.2 修复反例（codex 验收 P1）：挂名≠裁决——空壳候选拒。
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        report = build_case(root, historical=False)
        da = json.loads((root / "dormant_warehouse_audit.json").read_text())
        da["candidates"] = [{"candidate_address": "0xmustaddr"}]  # 挂名但零裁决字段
        write_json(root, "dormant_warehouse_audit.json", da)
        errors = gate.run(root, report)
        assert any("缺合法裁决" in x for x in errors), errors
        # l) 6.9.3：同址两行冲突裁决（strict vs excluded）→ 重复即拒
        da["candidates"] = [
            {"candidate_address": "0xmustaddr", "boundary_decision": "strict",
             "decision_reason": "夹具：闭环证据"},
            {"candidate_address": "0xmustaddr", "boundary_decision": "excluded",
             "decision_reason": "夹具：公共设施"},
        ]
        write_json(root, "dormant_warehouse_audit.json", da)
        errors = gate.run(root, report)
        assert any("地址重复" in x for x in errors), errors
        # n) 6.9.4：同址用尾随空格＋EVM 大小写变体伪装成两条 → 规范化后仍判重复
        da["candidates"] = [
            {"candidate_address": "0xMUSTADDR ", "boundary_decision": "strict",
             "decision_reason": "夹具：变体一"},
            {"candidate_address": "0xmustaddr", "boundary_decision": "excluded",
             "decision_reason": "夹具：变体二"},
        ]
        write_json(root, "dormant_warehouse_audit.json", da)
        errors = gate.run(root, report)
        assert any("地址重复" in x for x in errors), errors
        # m) 6.9.3：裁决字段齐全但没有地址 → 无名裁决记录拒
        da["candidates"] = [
            {"candidate_address": "0xmustaddr", "boundary_decision": "excluded",
             "decision_reason": "夹具：静置巨仓已裁决"},
            {"boundary_decision": "excluded", "decision_reason": "夹具：无名记录"},
        ]
        write_json(root, "dormant_warehouse_audit.json", da)
        errors = gate.run(root, report)
        assert any("缺地址" in x for x in errors), errors

    print("PASS: audit_release_gate 净室资产/哈希/CEX受益权/阴性结论/"
          "图表封口与负钳零/对抗复核否决/四查WARN拦截/双线阈值/"
          "嵌套未决暴露/静置仓全集对账/日级峰值口径闭环十一类契约全过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
