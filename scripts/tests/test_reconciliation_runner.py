#!/usr/bin/env python3
"""Seven fail-closed counterexamples for the controlled reconciliation runner."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts/report"), str(ROOT / "scripts/tests")]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = load(ROOT / "scripts/report/reconciliation_report.py", "reconciliation_runner_tests")


PRODUCERS = {
    "balance": "scripts/evm/verify_recon.py",
    "supply": "scripts/evm/verify_recon.py",
    "supply_truth": "scripts/lib/supply_truth_gate.py",
    "time": "scripts/lib/time_spotcheck.py",
}
TARGET = {"chain": "bsc", "token": "0xtoken", "as_of_block": 123}


def make_spec(root, *, inputs=None):
    spec = {
        "family": "evm", "case_dir": str(root), "target": dict(TARGET),
        "checks": {
            key: {"producer": producer, "argv": ["--receipt", f"{key}.json"],
                  "receipt": f"{key}.json"}
            for key, producer in PRODUCERS.items()
        },
    }
    if inputs is not None:
        spec["inputs"] = inputs
    return spec


def producer_side_effect(*, wrong_target=None, mutate=None):
    calls = {"count": 0}

    def run(command, cwd, capture_output, text):
        calls["count"] += 1
        receipt = command[-1]
        target = dict(TARGET)
        if wrong_target == Path(receipt).stem:
            target["token"] = "0xwrong"
        (Path(cwd) / receipt).write_text(json.dumps({
            "schema": "fixture/v1", "target": target,
            "verdict": "PASS", "exit_code": 0,
        }), encoding="utf-8")
        if mutate is not None and calls["count"] == 1:
            mutate()
        return subprocess.CompletedProcess(command, 0, "", "")

    return run


def wrapper(root):
    return json.loads((root / "reconciliation_report.json").read_text(encoding="utf-8"))


def test_01_preexisting_receipt_rejected():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "balance.json").write_text("{}", encoding="utf-8")
        with mock.patch.object(runner.subprocess, "run") as launched:
            rc = runner.run_job(make_spec(root))
        assert rc == 2 and launched.call_count == 0
        assert wrapper(root)["verdict"] == "FAIL"


def test_02_wrong_target_rejected():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        with mock.patch.object(runner.subprocess, "run",
                               side_effect=producer_side_effect(wrong_target="supply")):
            rc = runner.run_job(make_spec(root))
        assert rc == 2 and "target mismatch" in wrapper(root)["error"]


def test_03_unlisted_producer_rejected():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        spec = make_spec(root)
        spec["checks"]["time"]["producer"] = "scripts/report/audit_release_gate.py"
        with mock.patch.object(runner.subprocess, "run") as launched:
            rc = runner.run_job(spec)
        assert rc == 2 and launched.call_count == 0
        assert "not whitelisted" in wrapper(root)["error"]


def test_04_declared_input_drift_rejected():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        source = root / "input.jsonl"
        source.write_text("before\n", encoding="utf-8")
        mutate = lambda: source.write_text("after\n", encoding="utf-8")
        with mock.patch.object(runner.subprocess, "run",
                               side_effect=producer_side_effect(mutate=mutate)):
            rc = runner.run_job(make_spec(root, inputs={"raw": "input.jsonl"}))
        assert rc == 2 and "input changed" in wrapper(root)["error"]


def test_05_hand_composed_wrapper_rejected():
    from test_audit_release_gate import build_case
    from shared_release_receipt import validate_sources
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        build_case(root, historical=False)
        value = wrapper(root)
        value.pop("producer")
        (root / "reconciliation_report.json").write_text(json.dumps(value), encoding="utf-8")
        try:
            validate_sources(root)
        except ValueError as exc:
            assert "wrapper" in str(exc), exc
        else:
            raise AssertionError("aggregator accepted hand-composed wrapper")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        build_case(root, historical=False)
        value = wrapper(root)
        value["verdict"] = "FAIL"
        value["exit_code"] = 2
        (root / "reconciliation_report.json").write_text(json.dumps(value), encoding="utf-8")
        try:
            validate_sources(root)
        except ValueError as exc:
            assert "target/schema" in str(exc), exc
        else:
            raise AssertionError("aggregator accepted runner FAIL/2 wrapper")


def test_06_nonzero_producer_exit_rejected():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        failed = subprocess.CompletedProcess(["producer"], 9, "", "failed")
        with mock.patch.object(runner.subprocess, "run", return_value=failed):
            rc = runner.run_job(make_spec(root))
        value = wrapper(root)
        assert rc == 2 and value["verdict"] == "FAIL"
        assert value["checks"]["balance"]["process_exit_code"] == 9


def test_07_atomic_publish_failure_leaves_no_formal_file():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        with mock.patch.object(runner.subprocess, "run", side_effect=producer_side_effect()), \
                mock.patch.object(runner.os, "replace", side_effect=OSError("disk full")):
            rc = runner.run_job(make_spec(root))
        assert rc == 2 and not (root / "reconciliation_report.json").exists()
        assert not list(root.glob(".reconciliation_report.json.tmp.*"))


def main():
    tests = [
        test_01_preexisting_receipt_rejected,
        test_02_wrong_target_rejected,
        test_03_unlisted_producer_rejected,
        test_04_declared_input_drift_rejected,
        test_05_hand_composed_wrapper_rejected,
        test_06_nonzero_producer_exit_rejected,
        test_07_atomic_publish_failure_leaves_no_formal_file,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print("PASS: reconciliation runner rejected all 7 controlled-execution counterexamples")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
