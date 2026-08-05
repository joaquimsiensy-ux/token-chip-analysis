#!/usr/bin/env python3
"""P1-05: new analysis and clean-room audit have distinct mandatory profiles."""
from __future__ import annotations

import importlib.util
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


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        report = fixture.build_case(root, historical=False)
        for name in AUDIT_ONLY:
            (root / name).unlink(missing_ok=True)
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
