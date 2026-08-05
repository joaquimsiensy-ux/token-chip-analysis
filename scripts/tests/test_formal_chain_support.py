#!/usr/bin/env python3
"""Arbitrum stays collectable/G8-known but every formal seal and compile rail rejects it."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REPORT = ROOT / "scripts/report"
sys.path.insert(0, str(REPORT))
sys.path.insert(0, str(HERE))

import a4_gate
import a5_report_seal
import audit_release_gate
import entity_identity_gate
import identity_snapshot_receipt
from test_audit_release_gate import build_case


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def main():
    reason = audit_release_gate.formal_chain_error("arbitrum")
    assert reason and "探索支持" in reason and "labels-arbitrum.csv" in reason, reason
    assert "arbitrum" in entity_identity_gate.KNOWN_CHAINS
    assert "arbitrum" in identity_snapshot_receipt.EVM_CHAINS

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        report = build_case(root)
        accounting = json.loads((root / "accounting_mode.json").read_text())
        accounting["chain"] = "arbitrum"
        write_json(root / "accounting_mode.json", accounting)
        reconciliation = json.loads((root / "reconciliation_report.json").read_text())
        reconciliation["target"]["chain"] = "arbitrum"
        write_json(root / "reconciliation_report.json", reconciliation)
        for profile in ("new-analysis", "independent-audit"):
            errors = audit_release_gate.run(root, report, profile=profile)
            assert reason in errors, (profile, errors)

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        write_json(root / "analysis-state.json", {"chain": "arbitrum", "whale_groups": []})
        write_json(root / "identity_gate.json", {"chain": "arbitrum"})
        chain, errors = a4_gate.validate_formal_case_chain(root)
        assert chain is None and reason in errors, errors

        (root / "charts/final").mkdir(parents=True)
        (root / "charts/final/x.png").write_bytes(b"png")
        report = root / "report.md"
        report.write_text("# R\n![x](charts/final/x.png)\n", encoding="utf-8")
        write_json(root / "a4_seal.json", {
            "schema": "a4-seal/v4", "verdict": "PASS", "chain": "arbitrum",
            "workflow_type": "independent-audit", "revision": 1,
            "previous_seal": None, "charts_dir": "charts/final", "claims": [{"id": "C1"}],
        })
        try:
            a5_report_seal.create_seal(root, report, root / "a4_seal.json",
                                       root / "a5_report_seal.json")
        except ValueError as exc:
            assert "探索支持" in str(exc), exc
        else:
            raise AssertionError("A5 seal accepted exploratory Arbitrum")

        write_json(root / "facts.json", {})
        write_json(root / "a5_report_seal.json", {})
        for mode in ("analysis-new", "analysis-audit"):
            output_path = root / f"{mode}.html"
            cmd = [sys.executable, str(REPORT / "build_html.py"), "--mode", mode,
                   "--md", str(report), "--out", str(output_path),
                   "--facts", str(root / "facts.json"),
                   "--state", str(root / "analysis-state.json"),
                   "--a4-seal", str(root / "a4_seal.json"),
                   "--a5-seal", str(root / "a5_report_seal.json")]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            output = (proc.stdout + proc.stderr).strip()
            assert proc.returncode == 2 and "正式编译拒绝" in output \
                and "探索支持" in output, output
            assert not output_path.exists()
            print("EVIDENCE command:", " ".join(cmd))
            print("EVIDENCE exit:", proc.returncode)
            print("EVIDENCE output:", output.splitlines()[-1])

    print("PASS: Arbitrum collection/G8 capability retained; release/A4/A5/formal compile fail closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
