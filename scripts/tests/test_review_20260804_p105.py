#!/usr/bin/env python3
"""P1-05: new analysis and clean-room audit have distinct mandatory profiles."""
from __future__ import annotations

import importlib.util
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_TEST = HERE / "test_audit_release_gate.py"
spec = importlib.util.spec_from_file_location("audit_fixture_profiles", BASE_TEST)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)

AUDIT_ONLY = (
    "audit_input_manifest.json", "claim_registry.json",
    "reproduce_audit.py", "reproduce_receipt.json", "reproduce_output.json",
)


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def add_new_analysis_distribution(root: Path, report: Path) -> None:
    balances = {f"owner-{i:03d}": max(1, int(2_000_000 / (1.035 ** i))) for i in range(240)}
    snap = root / "data/holders_owners.json"; write_json(snap, balances)
    total = sum(balances.values())
    write_json(root / "supply_truth.json", {"verdict": "PASS", "exit_code": 0,
                                                "total_supply_raw": str(total),
                                                "net_supply_raw": str(total)})
    write_json(root / "data_map.json", {"files": [{"path": "data/holders_owners.json",
                                                        "sha256": sha(snap)}]})
    write_json(root / "candidate_screening.json", {"auto_excluded_candidate": []})
    dist = HERE.parent / "report/holder_distribution_scan.py"
    p = subprocess.run([sys.executable, str(dist), "--case-dir", str(root), "--stage", "initial"],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    for name, value in {
        "handoff_manifest.json": {"consumer_min_schema": "handoff/v3", "status": "READY", "run_id": "fixture"},
        "identity_snapshot_receipt.json": {"schema": "identity-snapshot-receipt/v1"},
        "entity_freeze.json": {"schema": "entity-freeze/v1", "revisions": []},
        "analysis-state.json": {"whale_groups": []}, "facts.json": {"entities": {}},
        "evidence.json": {"source": "fixture"},
        "a4_claims.json": {"schema": "a4-claims/v2", "claims": [{"id": "C1"}]},
    }.items():
        write_json(root / name, value)
    write_json(root / "a4_seal.json", {"schema": "a4-seal/v4", "verdict": "PASS",
        "workflow_type": "new-analysis", "revision": 1, "previous_seal": None,
        "charts_dir": "charts/final", "claims": [{"id": "C1", "verdict": "CONFIRMED"}]})
    p = subprocess.run([sys.executable, str(dist), "--case-dir", str(root), "--stage", "final",
                        "--round", "1"], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    p = subprocess.run([sys.executable, str(dist), "record-round", "--case-dir", str(root),
                        "--scan", "dist_rounds/round_1/distribution_scan.json"],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    report.write_text(report.read_text(encoding="utf-8")
        + "\n当前快照呈正常形态;这只表示本闸未检出结构性畸形,不等于没有庄。\n"
        + "\n![持仓分布](charts/final/holder_distribution_current.png)\n", encoding="utf-8")
    a5 = HERE.parent / "report/a5_report_seal.py"
    p = subprocess.run([sys.executable, str(a5), "--case-dir", str(root), "--report", str(report),
                        "--a4-seal", str(root / "a4_seal.json"),
                        "--out", str(root / "a5_report_seal.json")], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        report = fixture.build_case(root, historical=False)
        for name in AUDIT_ONLY:
            (root / name).unlink(missing_ok=True)
        add_new_analysis_distribution(root, report)
        assert not fixture.gate.run(root, report, profile="new-analysis")
        audit_errors = fixture.gate.run(root, report, profile="independent-audit")
        assert any("audit_input_manifest.json" in x for x in audit_errors)
        assert any("claim_registry.json" in x for x in audit_errors)

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        report = fixture.build_case(root, historical=False)
        assert not fixture.gate.run(root, report, profile="independent-audit")

    print("PASS: P1-05 mandatory new-analysis vs independent-audit release profiles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
