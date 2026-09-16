#!/usr/bin/env python3
"""W1：终态重开、归档完整性与登记快照解析的离线回归。"""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from test_distribution_gate import (
    make_case, add_final_inputs, run_scan, smooth_balances, check, write_json, SCAN, sha,
    prepare_explanation_case, EXPLAIN,
)
import holder_distribution_scan as distribution

GATE = SCAN.with_name("a4_gate.py")
ROUND1 = "dist_rounds/round_1/distribution_scan.json"


def read(root, rel):
    return json.loads((root / rel).read_text(encoding="utf-8"))


def require(p, rc=0, message=""):
    detail = f"exit={p.returncode}\n{p.stdout}{p.stderr}"
    assert p.returncode == rc, detail
    assert message in p.stdout + p.stderr, detail
    return p


def cli(root, cmd, *extra):
    return subprocess.run([sys.executable, str(SCAN), cmd, "--case-dir", str(root),
                           *extra], capture_output=True, text=True)


def available_reopen(root):
    p = require(cli(root, "reopen-cycle", "--help"))
    assert "--reason" in p.stdout, p.stdout + p.stderr


def reopen(root, *extra):
    return cli(root, "reopen-cycle", "--reason", "x", *extra)


def validate(root, rel=ROUND1):
    return cli(root, "validate", "--scan", rel, "--expected-stage", "final")


def record(root, rel=ROUND1, *extra):
    return cli(root, "record-round", "--scan", rel, *extra)


def normal(root, terminal=True):
    make_case(root, smooth_balances())
    require(run_scan(root))
    add_final_inputs(root, [{"id": "C1", "text": "夹具分布结论", "files": ["evidence.json"],
                            "report_locations": ["报告.md:1"]}])
    require(run_scan(root, "final", "--round", "1"))
    if terminal:
        require(record(root), message="NORMAL")


def tree(root):
    return {p.relative_to(root).as_posix(): sha(p) if p.is_file() else "directory"
            for p in root.rglob("*")}


def new_round1(root):
    require(reopen(root))
    require(run_scan(root, "final", "--round", "1"))
    require(validate(root))


def explain(root, n):
    rel = f"dist_rounds/round_{n}/explanation.json"
    require(subprocess.run([sys.executable, str(EXPLAIN), "--case-dir", str(root),
                            "--scan", f"dist_rounds/round_{n}/distribution_scan.json",
                            "--out", rel], capture_output=True, text=True))
    assert read(root, rel)["verdict"] == "EXPLAINED"
    return rel


def finalize(root):
    (root / "findings.md").write_text("# 测试结论\n", encoding="utf-8")
    write_json(root / "identity_gate.json", {"chain": "bsc"})
    claims = read(root, "a4_claims.json")["claims"]
    write_json(root / "verdicts.json", [{"id": c["id"], "verdict": "CONFIRMED"} for c in claims])
    return subprocess.run([sys.executable, str(GATE), "finalize", "--case-dir", str(root),
                           "--verdicts-file", str(root / "verdicts.json"),
                           "--workflow-type", "new-analysis", "--seal-files", "findings.md"],
                          capture_output=True, text=True)


def rejects_when_no_terminal(root):
    normal(root, terminal=False)
    available_reopen(root)
    before = tree(root)
    require(reopen(root), 2, "terminal")
    assert tree(root) == before


def archives_and_allows_round1(root):
    normal(root)
    original = tree(root)
    require(reopen(root), message="PASS: cycle 1 archived")
    assert not (root / "distribution_rounds.json").exists()
    assert not (root / "dist_rounds").exists()
    assert list((root / "charts/final").iterdir()) == []
    receipt = read(root, "distribution_reopen.json")
    assert receipt["schema"] == "distribution-reopen/v1" and len(receipt["cycles"]) == 1
    entry = receipt["cycles"][0]
    assert entry["cycle"] == 1 and entry["prior_terminal"]["round_n"] == 1
    archived = {x["from"]: x for x in entry["archived"]}
    for rel in ("distribution_rounds.json", ROUND1,
                "charts/final/holder_distribution_current.png", "a4_seal.json", "a4_claims.json"):
        row = archived[rel]
        assert sha(root / row["to"]) == row["sha256"] == original[rel]
        copied = rel in {"a4_seal.json", "a4_claims.json"}
        assert row["mode"] == ("copied" if copied else "moved")
        assert row["to"] == "data/stage2/dist_cycle1/" + ("a4_snapshot/" if copied else "") + rel
    assert "evidence_refs" in entry["note"] and "不复制" in entry["note"]
    require(run_scan(root, "final", "--round", "1"))
    assert read(root, ROUND1)["input_binding"]["reopened_from_cycle"]["cycle"] == 1
    require(validate(root))
    require(record(root), message="NORMAL")
    ledger = read(root, "distribution_rounds.json")
    assert len(ledger["rounds"]) == 1 and ledger["terminal"]["round_n"] == 1
    assert (root / ledger["terminal"]["final_chart_path"]).is_file()


def second_reopen_is_cycle2(root):
    archives_and_allows_round1(root)
    require(reopen(root), message="PASS: cycle 2 archived")
    assert [e["cycle"] for e in read(root, "distribution_reopen.json")["cycles"]] == [1, 2]
    assert (root / "data/stage2/dist_cycle2/distribution_rounds.json").is_file()


def refuses_extra_final_chart(root):
    normal(root)
    require(reopen(root, "--dry-run"))
    (root / "charts/final/x.png").write_bytes(b"extra")
    before = tree(root)
    require(reopen(root), 2, "charts/final 含其他文件")
    assert tree(root) == before


def dry_run_moves_nothing(root):
    normal(root)
    write_json(root / "a5_report_seal.json", {"fixture": True})
    write_json(root / "a5_assembly_workorder.json", {"bindings": {"rounds": {"fixture": True}}})
    before = tree(root)
    p = require(reopen(root, "--dry-run"), message="将搬运")
    assert "将失效的下游件" in p.stdout and "bindings.rounds" in p.stdout
    assert "a5_report_seal.json" in p.stdout
    assert tree(root) == before


def validator_rebuilds_reopen_binding(root):
    normal(root)
    new_round1(root)
    scan_path = root / ROUND1
    receipt_path = root / "distribution_reopen.json"
    scan_bytes, receipt_bytes = scan_path.read_bytes(), receipt_path.read_bytes()
    for change in ("cycle", "missing_receipt", "missing_binding", "archive_sha", "ledger_sha",
                   "empty_archive", "terminal", "seal_sha", "duplicate_from", "duplicate_to"):
        scan = json.loads(scan_bytes); receipt = json.loads(receipt_bytes)
        entry = receipt["cycles"][-1]
        require(validate(root))
        try:
            if change == "cycle":
                scan["input_binding"]["reopened_from_cycle"]["cycle"] = 9
            elif change == "missing_receipt":
                receipt_path.unlink()
            elif change == "missing_binding":
                del scan["input_binding"]["reopened_from_cycle"]
            elif change == "archive_sha":
                entry["archived"][0]["sha256"] = "0" * 64
            elif change == "ledger_sha":
                entry["prior_ledger_sha256"] = "0" * 64
            elif change == "empty_archive":
                entry["archived"] = []
            elif change == "terminal":
                entry["prior_terminal"]["round_n"] = 9
            elif change == "seal_sha":
                entry["a4_seal_sha_at_reopen"] = "0" * 64
            elif change == "duplicate_from":
                entry["archived"][1]["from"] = entry["archived"][0]["from"]
            elif change == "duplicate_to":
                entry["archived"][1]["to"] = entry["archived"][0]["to"]
            if change != "missing_receipt":
                write_json(receipt_path, receipt)
            write_json(scan_path, scan)
            require(validate(root), 2, "BLOCK: distribution scan validate")
        finally:
            scan_path.write_bytes(scan_bytes); receipt_path.write_bytes(receipt_bytes)
    # 空台账仍是合法首轮；无回执的存量 scan 不要求新键。
    require(validate(root))
    write_json(root / "distribution_rounds.json", {
        "schema": "distribution-rounds/v1", "rounds": [], "terminal": None})
    require(run_scan(root, "final", "--round", "1"))
    require(validate(root))


def snapshot_prefers_registered(root):
    make_case(root, smooth_balances())
    shutil.copyfile(root / "data/holders_owners.json", root / "data/balances_final.json")
    require(run_scan(root))
    assert read(root, "distribution_scan.json")["input_binding"]["snapshot"]["path"] == "data/holders_owners.json"


def snapshot_two_registered_blocks(root):
    make_case(root, smooth_balances())
    require(run_scan(root))
    path = root / "data/balances_final.json"
    shutil.copyfile(root / "data/holders_owners.json", path)
    dm = read(root, "data_map.json")
    dm["files"].append({"path": "data/balances_final.json", "sha256": sha(path)})
    write_json(root / "data_map.json", dm)
    require(run_scan(root), 2, "唯一登记")


def final_snapshot_from_initial_binding_no_fallback(root):
    normal(root, terminal=False)
    initial = read(root, "distribution_scan.json")
    initial["input_binding"]["snapshot"]["path"] = "data/missing.json"
    write_json(root / "distribution_scan.json", initial)
    require(run_scan(root, "final", "--round", "1"), 2, "initial")


def explicit_unregistered_snapshot_still_blocks(root):
    make_case(root, smooth_balances())
    require(run_scan(root, "initial", "--snapshot", "data/holders_owners.json"))
    shutil.copyfile(root / "data/holders_owners.json", root / "data/balances_final.json")
    require(run_scan(root, "initial", "--snapshot", "data/balances_final.json"), 2,
            "data_map 必须唯一登记")


def reopen_then_finalize_then_round1_terminal(root):
    normal(root)
    require(reopen(root))
    require(finalize(root))
    assert read(root, "a4_seal.json")["revision"] == 2
    require(run_scan(root, "final", "--round", "1"))
    require(validate(root))
    require(record(root), message="NORMAL")
    ledger = read(root, "distribution_rounds.json")
    assert len(ledger["rounds"]) == 1 and ledger["terminal"]["status"] == "NORMAL"
    assert read(root, ROUND1)["input_binding"]["reopened_from_cycle"]["cycle"] == 1
    assert not (root / "a5_report_seal.json").exists()
    assert not (root / "a5_assembly_workorder.json").exists()


def reopen_abnormal_round1_unexplained_then_round2(root):
    _, final = prepare_explanation_case(root)
    require(final)
    require(record(root, ROUND1, "--explanation", explain(root, 1)), message="EXPLAINED")
    require(reopen(root))
    require(run_scan(root, "final", "--round", "1"))
    require(record(root), message="UNEXPLAINED")
    assert read(root, "distribution_rounds.json")["terminal"] is None
    require(finalize(root))
    require(run_scan(root, "final", "--round", "2"))
    rel = "dist_rounds/round_2/distribution_scan.json"
    assert read(root, rel)["input_binding"]["reopened_from_cycle"]["cycle"] == 1
    require(validate(root, rel))
    path = root / "distribution_reopen.json"; original = path.read_bytes()
    try:
        path.unlink()
        require(validate(root, rel), 2, "案根无 distribution_reopen.json")
    finally:
        path.write_bytes(original)
    require(record(root, rel, "--explanation", explain(root, 2)), message="EXPLAINED")
    ledger = read(root, "distribution_rounds.json")
    assert len(ledger["rounds"]) == 2 and ledger["terminal"]["status"] == "EXPLAINED"


def manual_cycles_and_move_rollback(root):
    normal(root)
    for name in ("dist_cycle1_v7j", "dist_cycle2", "dist_cycle3_aborted"):
        (root / "data/stage2" / name).mkdir(parents=True)
    require(reopen(root, "--dry-run"), message="dist_cycle4")
    before = tree(root)
    real_move = shutil.move
    calls = []

    def fail_second(src, dst):
        calls.append(str(src))
        if len(calls) == 2:
            raise OSError("injected move failure")
        return real_move(src, dst)

    with patch.object(distribution.shutil, "move", side_effect=fail_second):
        assert distribution.cmd_reopen_cycle(SimpleNamespace(case_dir=str(root), reason="x", dry_run=False)) == 1
    after = tree(root)
    assert all(after.get(rel) == value for rel, value in before.items())
    assert not (root / "distribution_reopen.json").exists()
    # 回滚留下的空目录按历史编号占位保留；不删除它来伪造连续序号。
    require(reopen(root), message="cycle 5 archived")
    receipt = read(root, "distribution_reopen.json")
    assert [e["cycle"] for e in receipt["cycles"]] == [5]
    require(run_scan(root, "final", "--round", "1"))
    require(validate(root))
    require(record(root))
    require(reopen(root), message="cycle 6 archived")
    assert [e["cycle"] for e in read(root, "distribution_reopen.json")["cycles"]] == [5, 6]


def main():
    tests = [rejects_when_no_terminal, archives_and_allows_round1, second_reopen_is_cycle2,
             refuses_extra_final_chart, dry_run_moves_nothing, validator_rebuilds_reopen_binding,
             snapshot_prefers_registered, snapshot_two_registered_blocks,
             final_snapshot_from_initial_binding_no_fallback, explicit_unregistered_snapshot_still_blocks,
             reopen_then_finalize_then_round1_terminal, reopen_abnormal_round1_unexplained_then_round2,
             manual_cycles_and_move_rollback]
    passed = 0
    for test in tests:
        with tempfile.TemporaryDirectory(prefix="w1-reopen-") as td:
            try:
                test(Path(td))
            except Exception as exc:
                check(test.__name__, False, f"{type(exc).__name__}: {exc}")
            else:
                passed += int(check(test.__name__, True))
    print(f"reopen-cycle: {passed}/{len(tests)} PASS")
    return int(passed != len(tests))


if __name__ == "__main__":
    raise SystemExit(main())
