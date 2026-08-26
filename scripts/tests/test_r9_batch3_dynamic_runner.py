#!/usr/bin/env python3
"""Solana controlled runner adopts the producer-observed GPA slot exactly once."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts/report"), str(ROOT / "scripts/lib")]
OBSERVED_SLOT = 103
CACHE_SLOT = 101


def load_runner():
    path = ROOT / "scripts/report/reconciliation_report.py"
    spec = importlib.util.spec_from_file_location("r9_b3_dynamic_runner", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def job(case):
    placeholder = "{observed_as_of_block}"
    return {
        "case_dir": str(case),
        "derive_as_of_from": "supply",
        "target": {"chain": "solana", "token": "mint", "as_of_block": None},
        "checks": {
            "supply": {"producer": "scripts/solana/scan_token_accounts.py",
                       "argv": ["--out", "snapshot.json", "--bundle", "supply.json"],
                       "receipt": "supply.json"},
            "balance": {"producer": "scripts/solana/anchor_sampler.py",
                        "argv": ["--as-of-slot", placeholder, "--receipt", "balance.json"],
                        "receipt": "balance.json"},
            "supply_truth": {"producer": "scripts/lib/supply_truth_gate.py",
                             "argv": ["--as-of-block", placeholder, "--out", "truth.json"],
                             "receipt": "truth.json"},
            "time": {"producer": "scripts/solana/anchor_sampler.py",
                     "argv": ["--as-of-slot", placeholder, "--receipt", "time.json"],
                     "receipt": "time.json"},
            "exact_reconcile": {"producer": "scripts/solana/replay_edges.py",
                                "argv": ["reconcile", "--as-of-slot", str(CACHE_SLOT),
                                         "--receipt", "exact.json"],
                                "receipt": "exact.json"},
        },
    }


def launch_receipts(exact_target, calls):
    def launch(command, cwd, capture_output, text):
        name = Path(command[1]).name
        calls.append(name)
        if name == "scan_token_accounts.py":
            receipt = "supply.json"
            target = {"chain": "solana", "token": "mint",
                      "as_of_block": OBSERVED_SLOT}
        elif name == "replay_edges.py":
            assert str(CACHE_SLOT) in command
            assert str(OBSERVED_SLOT) not in command
            receipt = "exact.json"
            target = dict(exact_target)
        else:
            assert str(OBSERVED_SLOT) in command
            assert "{observed_as_of_block}" not in command
            receipt = next(name for name in ("balance.json", "truth.json", "time.json")
                           if name in command)
            target = {"chain": "solana", "token": "mint",
                      "as_of_block": OBSERVED_SLOT}
        (Path(cwd) / receipt).write_text(json.dumps({
            "schema": "fixture/v1", "target": target,
            "verdict": "PASS", "exit_code": 0,
        }), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    return launch


def run_with_exact_target(runner, exact_target):
    with tempfile.TemporaryDirectory(prefix="r9-b3-runner-") as raw:
        case = Path(raw).resolve()
        calls = []
        with mock.patch.object(
                runner.subprocess, "run",
                side_effect=launch_receipts(exact_target, calls)):
            rc = runner.run_job(job(case))
        wrapper = json.loads((case / "reconciliation_report.json").read_text())
        return rc, wrapper, calls


def test_dynamic_slot_is_observed_while_exact_stays_frozen():
    runner = load_runner()
    exact_target = {"chain": "solana", "token": "mint", "as_of_block": CACHE_SLOT}
    rc, wrapper, calls = run_with_exact_target(runner, exact_target)
    assert rc == 0 and wrapper["target"]["as_of_block"] == OBSERVED_SLOT
    assert calls == ["scan_token_accounts.py", "anchor_sampler.py",
                     "supply_truth_gate.py", "anchor_sampler.py", "replay_edges.py"]


def test_dynamic_spec_placeholder_partition():
    runner = load_runner()
    with tempfile.TemporaryDirectory(prefix="r9-b3-spec-") as raw:
        case = Path(raw).resolve()
        valid = job(case)
        runner._validate_spec(valid, case)

        exact_placeholder = job(case)
        exact_placeholder["checks"]["exact_reconcile"]["argv"][2] = \
            "{observed_as_of_block}"
        try:
            runner._validate_spec(exact_placeholder, case)
        except runner.RunnerError as exc:
            assert "must not consume" in str(exc) and "finalized_upper_slot" in str(exc)
        else:
            raise AssertionError("exact_reconcile accepted observed-slot placeholder")

        for key in ("balance", "supply_truth", "time"):
            missing = job(case)
            missing["checks"][key]["argv"] = [
                "102" if value == "{observed_as_of_block}" else value
                for value in missing["checks"][key]["argv"]]
            try:
                runner._validate_spec(missing, case)
            except runner.RunnerError as exc:
                assert f"dynamic solana check {key} must consume" in str(exc)
            else:
                raise AssertionError(f"{key} accepted missing observed-slot placeholder")

        missing_flag = job(case)
        missing_flag["checks"]["exact_reconcile"]["argv"] = [
            "reconcile", str(CACHE_SLOT), "--receipt", "exact.json"]
        try:
            runner._validate_spec(missing_flag, case)
        except runner.RunnerError as exc:
            assert "exactly one --as-of-slot" in str(exc)
        else:
            raise AssertionError("exact_reconcile accepted a slot without --as-of-slot")

        duplicate_flag = job(case)
        duplicate_flag["checks"]["exact_reconcile"]["argv"].append(
            f"--as-of-slot={CACHE_SLOT}")
        try:
            runner._validate_spec(duplicate_flag, case)
        except runner.RunnerError as exc:
            assert "exactly one --as-of-slot" in str(exc)
        else:
            raise AssertionError("exact_reconcile accepted duplicate slot arguments")

        embedded_placeholder = job(case)
        embedded_placeholder["checks"]["exact_reconcile"]["argv"][1:3] = [
            "--as-of-slot={observed_as_of_block}"]
        try:
            runner._validate_spec(embedded_placeholder, case)
        except runner.RunnerError as exc:
            assert "must not consume" in str(exc)
        else:
            raise AssertionError("exact_reconcile accepted embedded observed placeholder")


def test_dynamic_exact_target_boundaries():
    runner = load_runner()
    mismatches = [
        {"chain": "bsc", "token": "mint", "as_of_block": CACHE_SLOT},
        {"chain": "solana", "token": "other", "as_of_block": CACHE_SLOT},
    ]
    for target in mismatches:
        rc, wrapper, _calls = run_with_exact_target(runner, target)
        assert rc == 2 and "must match wrapper chain/token" in wrapper["error"]

    for bad_slot in (OBSERVED_SLOT + 1, True, -1):
        target = {"chain": "solana", "token": "mint", "as_of_block": bad_slot}
        rc, wrapper, _calls = run_with_exact_target(runner, target)
        assert rc == 2 and "exact_reconcile receipt target" in wrapper["error"]


def main():
    test_dynamic_slot_is_observed_while_exact_stays_frozen()
    test_dynamic_spec_placeholder_partition()
    test_dynamic_exact_target_boundaries()
    print("PASS R9 B3-G2/batch10: dynamic checks use observed slot; exact stays frozen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
