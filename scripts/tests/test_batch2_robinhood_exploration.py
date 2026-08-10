#!/usr/bin/env python3
"""B2-E: Robinhood exploration assets cannot flow back into formal release."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REPORT = ROOT / "scripts/report"
sys.path[:0] = [str(ROOT / "scripts/lib"), str(REPORT), str(HERE)]

import a4_gate
import a5_report_seal
import audit_release_gate
from chain_registry import (CHAIN_REGISTRY, evm_chain_id_for, formal_ready,
                            missing_formal_capabilities, release_tier_for)
from test_audit_release_gate import build_case
from test_handoff_manifest import make_case, run as run_handoff


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def exemption_sentinel(record):
    """RH exemptions are valid only while both policy and attestation gaps remain."""
    if record.get("release_tier") != "exploration" or record.get("evm_chain_id") is not None:
        raise AssertionError("RH exemption expired: formal/re-attested Robinhood requires re-review")


def main():
    robinhood = CHAIN_REGISTRY["robinhood"]
    exemption_sentinel(robinhood)
    assert release_tier_for("robinhood") == "exploration"
    assert evm_chain_id_for("robinhood") is None
    assert not formal_ready("robinhood")
    assert "release_tier" in missing_formal_capabilities("robinhood")
    assert robinhood["capabilities"]["labels_table"] is True

    # The sentinel itself must turn red if either exemption invalidation condition changes.
    for update in ({"release_tier": "formal"}, {"evm_chain_id": 4663}):
        changed = dict(robinhood)
        changed.update(update)
        try:
            exemption_sentinel(changed)
        except AssertionError:
            pass
        else:
            raise AssertionError(f"RH exemption sentinel missed {update}")

    reason = audit_release_gate.formal_chain_error("robinhood")
    assert reason and "exploration" in reason, reason
    labels = ROOT / "references/labels/labels-robinhood.csv"
    assert labels.is_file() and labels.stat().st_size > 0

    # A syntactically complete exploration case (including four hashed receipts) is
    # rejected by the formal handoff before it can enter READY/data-map consumption.
    with tempfile.TemporaryDirectory(prefix="rh-handoff-") as td:
        root = Path(td)
        make_case(str(root), chain="robinhood")
        proc = run_handoff(["generate", "--case-dir", str(root), "--status", "READY",
                            "--mode", "full", "--producer-model", "test-model",
                            "--chain", "robinhood", "--contract", "0x0",
                            "--frozen-block", "999"])
        output = proc.stdout + proc.stderr
        assert proc.returncode == 2 and "robinhood" in output.lower(), output
        assert not (root / "handoff_manifest.json").exists()

    with tempfile.TemporaryDirectory(prefix="rh-audit-") as td:
        root = Path(td)
        report = build_case(root)
        accounting = json.loads((root / "accounting_mode.json").read_text())
        accounting["chain"] = "robinhood"
        write_json(root / "accounting_mode.json", accounting)
        reconciliation = json.loads((root / "reconciliation_report.json").read_text())
        reconciliation["target"]["chain"] = "robinhood"
        write_json(root / "reconciliation_report.json", reconciliation)
        for profile in ("new-analysis", "independent-audit"):
            errors = audit_release_gate.run(root, report, profile=profile)
            assert reason in errors, (profile, errors)

    with tempfile.TemporaryDirectory(prefix="rh-seals-") as td:
        root = Path(td)
        write_json(root / "analysis-state.json", {"chain": "robinhood", "whale_groups": []})
        write_json(root / "identity_gate.json", {"chain": "robinhood"})
        chain, errors = a4_gate.validate_formal_case_chain(root)
        assert chain is None and reason in errors, errors

        (root / "charts/final").mkdir(parents=True)
        (root / "charts/final/x.png").write_bytes(b"png")
        report = root / "report.md"
        report.write_text("# R\n![x](charts/final/x.png)\n", encoding="utf-8")
        write_json(root / "a4_seal.json", {
            "schema": "a4-seal/v4", "verdict": "PASS", "chain": "robinhood",
            "workflow_type": "independent-audit", "revision": 1,
            "previous_seal": None, "charts_dir": "charts/final", "claims": [{"id": "C1"}],
        })
        try:
            a5_report_seal.create_seal(root, report, root / "a4_seal.json",
                                       root / "a5_report_seal.json")
        except ValueError as exc:
            assert "exploration" in str(exc), exc
        else:
            raise AssertionError("A5 accepted an old Robinhood A4 seal as a re-sign")

        write_json(root / "facts.json", {})
        write_json(root / "a5_report_seal.json", {})
        for mode in ("analysis-new", "analysis-audit"):
            output_path = root / f"{mode}.html"
            proc = subprocess.run([
                sys.executable, str(REPORT / "build_html.py"), "--mode", mode,
                "--md", str(report), "--out", str(output_path),
                "--facts", str(root / "facts.json"),
                "--state", str(root / "analysis-state.json"),
                "--a4-seal", str(root / "a4_seal.json"),
                "--a5-seal", str(root / "a5_report_seal.json"),
            ], capture_output=True, text=True)
            output = proc.stdout + proc.stderr
            assert proc.returncode == 2 and "exploration" in output, output
            assert not output_path.exists()

    print("PASS B2-E: RH exploration is blocked by READY/A4/A5/build/audit and exemption sentinel")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
