#!/usr/bin/env python3
"""P1-04: strict finite percentages and exact raw/count integers."""
from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_TEST = HERE / "test_audit_release_gate.py"
spec = importlib.util.spec_from_file_location("audit_fixture", BASE_TEST)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


def read(root, name):
    return json.loads((root / name).read_text())


def main():
    for bad in ("NaN", "Infinity", "-Infinity", True):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report = fixture.build_case(root, historical=False)
            obj = read(root, "address_classification.json")
            obj["current_owner_threshold_pct"] = bad
            fixture.write_json(root, "address_classification.json", obj)
            errors = fixture.gate.run(root, report)
            assert any("有限实数" in x for x in errors), (bad, errors)

    for bad in ("NaN", "Infinity", "-Infinity", True, 1.9, "1.9"):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report = fixture.build_case(root, historical=False)
            obj = read(root, "position_ledger.json")
            obj["entries"][0]["amount_raw"] = bad
            fixture.write_json(root, "position_ledger.json", obj)
            errors = fixture.gate.run(root, report)
            assert any("不是整数 raw amount" in x for x in errors), (bad, errors)

    for bad in ("NaN", "Infinity", "-Infinity", True, 1.9, "1.9"):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report = fixture.build_case(root, historical=False)
            obj = read(root, "address_classification.json")
            obj["unresolved_count"] = bad
            fixture.write_json(root, "address_classification.json", obj)
            errors = fixture.gate.run(root, report)
            assert any("unresolved_count 非整数" in x for x in errors), (bad, errors)

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        report = fixture.build_case(root, historical=False)
        obj = read(root, "address_classification.json")
        obj["current_owner_threshold_pct"] = 0.1
        obj["current_owner_float_threshold_pct"] = 0.2
        fixture.write_json(root, "address_classification.json", obj)
        assert not fixture.gate.run(root, report)
    print("PASS: P1-04 strict finite percentages/raw integers/unresolved counts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
