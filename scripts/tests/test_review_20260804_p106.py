#!/usr/bin/env python3
"""P1-06: A4 and clean-room claim registries must describe the same claims."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
GATE = HERE.parent / "report" / "a4_gate.py"


def dump(path, obj):
    path.write_text(json.dumps(obj), encoding="utf-8")


def fixture(root):
    for name in ("findings.md", "analysis-state.json", "facts.json", "identity_gate.json",
                 "raw1.json", "raw2.json"):
        (root / name).write_text("{}\n", encoding="utf-8")
    (root / "charts" / "final").mkdir(parents=True)
    a4 = {"schema": "a4-claims/v2", "claims": [
        {"id": "C1", "text": "Entity A controls 10%", "files": ["raw1.json"],
         "report_locations": ["subject.md:10"]},
        {"id": "C2", "text": "No other whale exists", "files": ["raw2.json"],
         "report_locations": ["subject.md:20"]},
    ]}
    audit = {"claims": [
        {"claim_id": "C1", "statement": "Entity A controls 10%",
         "evidence_files": ["raw1.json"], "report_locations": ["subject.md:10"],
         "verdict": "confirmed"},
        {"claim_id": "C2", "statement": "No other whale exists",
         "evidence_files": ["raw2.json"], "report_locations": ["subject.md:20"],
         "verdict": "weakened"},
    ]}
    verdicts = [{"id": "C1", "verdict": "CONFIRMED"},
                {"id": "C2", "verdict": "WEAKENED", "revision_note": "scope limited"}]
    dump(root / "a4_claims.json", a4)
    dump(root / "claim_registry.json", audit)
    dump(root / "verdicts.json", verdicts)
    return audit


def finalize(root):
    return subprocess.run([sys.executable, str(GATE), "finalize", "--case-dir", str(root),
                           "--verdicts-file", str(root / "verdicts.json"),
                           "--seal-files", "findings.md,analysis-state.json,facts.json,identity_gate.json",
                           "--workflow-type", "independent-audit"], capture_output=True, text=True)


def must_block(mutator):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        audit = fixture(root)
        mutator(audit)
        dump(root / "claim_registry.json", audit)
        p = finalize(root)
        assert p.returncode == 2, p.stdout + p.stderr


def main():
    must_block(lambda x: x["claims"].pop())
    must_block(lambda x: x["claims"].append({
        "claim_id": "C3", "statement": "extra", "evidence_files": [],
        "report_locations": ["subject.md:30"], "verdict": "confirmed"}))
    must_block(lambda x: x["claims"][0].update(statement="different text"))
    must_block(lambda x: x["claims"][0].update(verdict="refuted"))
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        fixture(root)
        assert finalize(root).returncode == 0
    print("PASS: P1-06 claim registry id/text/verdict/evidence/location alignment")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
