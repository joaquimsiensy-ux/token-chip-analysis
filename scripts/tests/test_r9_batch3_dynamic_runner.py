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
                                "argv": ["reconcile", "--as-of-slot", placeholder,
                                         "--receipt", "exact.json"],
                                "receipt": "exact.json"},
        },
    }


def test_dynamic_slot_is_observed_then_substituted():
    runner = load_runner()
    with tempfile.TemporaryDirectory(prefix="r9-b3-runner-") as raw:
        case = Path(raw).resolve()
        calls = []

        def launch(command, cwd, capture_output, text):
            calls.append(Path(command[1]).name)
            if Path(command[1]).name == "scan_token_accounts.py":
                receipt = "supply.json"
                target = {"chain": "solana", "token": "mint", "as_of_block": 103}
            else:
                assert "103" in command and "{observed_as_of_block}" not in command
                receipt = next(name for name in ("balance.json", "truth.json", "time.json",
                                                  "exact.json")
                               if name in command)
                target = {"chain": "solana", "token": "mint", "as_of_block": 103}
            (Path(cwd) / receipt).write_text(json.dumps({
                "schema": "fixture/v1", "target": target,
                "verdict": "PASS", "exit_code": 0,
            }), encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, "", "")

        with mock.patch.object(runner.subprocess, "run", side_effect=launch):
            rc = runner.run_job(job(case))
        wrapper = json.loads((case / "reconciliation_report.json").read_text())
        assert rc == 0 and wrapper["target"]["as_of_block"] == 103
        assert calls[0] == "scan_token_accounts.py"
        assert calls == ["scan_token_accounts.py", "anchor_sampler.py",
                         "supply_truth_gate.py", "anchor_sampler.py", "replay_edges.py"]


def main():
    test_dynamic_slot_is_observed_then_substituted()
    print("PASS R9 B3-G2: Solana runner adopts observed supply snapshot slot")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
