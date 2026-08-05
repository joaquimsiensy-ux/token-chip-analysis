#!/usr/bin/env python3
"""P2-02: every missing audit asset must return structured BLOCK, never traceback."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
DEFAULT_GATE = HERE.parent / "report" / "audit_release_gate.py"
GATE = Path(os.environ.get("TOKEN_CHIP_AUDIT_GATE", DEFAULT_GATE))

fixture_spec = importlib.util.spec_from_file_location(
    "audit_gate_fixture", HERE / "test_audit_release_gate.py")
fixture = importlib.util.module_from_spec(fixture_spec)
fixture_spec.loader.exec_module(fixture)

gate_spec = importlib.util.spec_from_file_location("audit_gate_under_test", GATE)
gate = importlib.util.module_from_spec(gate_spec)
gate_spec.loader.exec_module(gate)


def main() -> int:
    required = gate.REQUIRED_BY_PROFILE["independent-audit"] \
        if hasattr(gate, "REQUIRED_BY_PROFILE") else gate.REQUIRED
    for missing_name in required:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report = fixture.build_case(root, historical=False)
            (root / missing_name).unlink()
            result_path = root / "gate_result.json"
            proc = subprocess.run(
                [sys.executable, str(GATE), str(root), "--report", str(report),
                 "--json-out", str(result_path)],
                capture_output=True, text=True,
            )
            assert proc.returncode == 2, (
                missing_name, proc.returncode, proc.stdout, proc.stderr)
            assert "Traceback" not in proc.stderr, (missing_name, proc.stderr)
            assert result_path.is_file(), (missing_name, proc.stdout, proc.stderr)
            result = json.loads(result_path.read_text(encoding="utf-8"))
            assert result["status"] == "BLOCK", (missing_name, result)
            assert any(f"缺必需资产: {missing_name}" in item
                       for item in result["errors"]), (missing_name, result)

    print(f"PASS: P2-02 {len(required)} required-asset deletions return exit 2 JSON BLOCK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
