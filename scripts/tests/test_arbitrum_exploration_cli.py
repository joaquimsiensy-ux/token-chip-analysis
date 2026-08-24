#!/usr/bin/env python3
"""F-10 regressions: exploration execution is allowed, formal consumption is not."""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

from test_audit_release_gate import write_deep_recon_fixtures


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts/report"), str(ROOT / "scripts/lib")]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value), encoding="utf-8")


def receipt_item(root, *, chain, mode):
    target = {"chain": chain, "token": "0xtoken", "as_of_block": 123}
    source = root / "fixture.txt"
    source.write_text("fixture\n", encoding="utf-8")
    receipt_path = root / f"{chain}-{mode}.json"
    receipt, _ = write_deep_recon_fixtures(root, target, source)
    receipt["mode"] = mode
    write_json(receipt_path, receipt)
    item = {"status": "PASS", "exit_code": 0,
            "receipt": {"path": receipt_path.name, "sha256": sha(receipt_path)}}
    return target, item


def expect_consumer_reject(shared, root, target, item, fragment):
    try:
        shared.validate_reconciliation_check(root, "balance", item, target, "evm")
    except ValueError as exc:
        assert fragment in str(exc), exc
    else:
        raise AssertionError("formal reconciliation consumer accepted forbidden receipt")


def test_consumer_rejects_exploration_mode():
    shared = load(ROOT / "scripts/report/shared_release_receipt.py", "f10_shared_mode")
    with tempfile.TemporaryDirectory(prefix="f10_consumer_mode_") as td:
        root = Path(td)
        target, item = receipt_item(root, chain="bsc", mode="exploration")
        expect_consumer_reject(shared, root, target, item, "must be formal")


def test_consumer_rejects_exploration_tier_relabelled_formal():
    shared = load(ROOT / "scripts/report/shared_release_receipt.py", "f10_shared_tier")
    with tempfile.TemporaryDirectory(prefix="f10_consumer_tier_") as td:
        root = Path(td)
        target, item = receipt_item(root, chain="arbitrum", mode="formal")
        expect_consumer_reject(shared, root, target, item,
                               "正式对账消费面只接受 formal-ready 链")


def test_wrapper_target_rejects_exploration_tier():
    shared = load(ROOT / "scripts/report/shared_release_receipt.py", "f10_shared_wrapper")
    with tempfile.TemporaryDirectory(prefix="f10_wrapper_tier_") as td:
        root = Path(td)
        runner = ROOT / "scripts/report/reconciliation_report.py"
        write_json(root / "reconciliation_report.json", {
            "schema": "reconciliation-report/v3", "family": "evm",
            "target": {"chain": "arbitrum", "token": "0xtoken", "as_of_block": 123},
            "producer": {"path": "scripts/report/reconciliation_report.py",
                         "sha256": sha(runner)},
            "checks": {}, "verdict": "PASS", "exit_code": 0,
        })
        try:
            shared.validate_reconciliation_report(root)
        except ValueError as exc:
            assert "正式对账消费面只接受 formal-ready 链" in str(exc), exc
            assert "迁移指引" in str(exc), exc
        else:
            raise AssertionError("wrapper accepted exploration-tier target")


def test_formal_receipt_regression():
    shared = load(ROOT / "scripts/report/shared_release_receipt.py", "f10_shared_formal")
    with tempfile.TemporaryDirectory(prefix="f10_consumer_formal_") as td:
        root = Path(td)
        target, item = receipt_item(root, chain="bsc", mode="formal")
        shared.validate_reconciliation_check(root, "balance", item, target, "evm")


def run_script(rel, args):
    return subprocess.run(
        [sys.executable, str(ROOT / rel), *args], capture_output=True, text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})


def combined_output(proc):
    return proc.stdout + proc.stderr


def test_accounting_cli_policy():
    accounting = load(ROOT / "scripts/evm/accounting_gate.py", "f10_accounting")

    class ReachedExecution(RuntimeError):
        pass

    with tempfile.TemporaryDirectory(prefix="f10_accounting_") as td:
        args = ["--token", "0xtoken", "--chain", "arbitrum", "--exploration",
                "--rpc", "http://127.0.0.1:1", "--hypersync-token-file",
                str(Path(td) / "missing-token")]
        with mock.patch.object(accounting, "resolve_proxy", return_value=None), \
                mock.patch.object(accounting, "Rpc", side_effect=ReachedExecution):
            try:
                accounting.main(args)
            except ReachedExecution:
                pass
            else:
                raise AssertionError("accounting CLI did not enter execution path")

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            try:
                accounting.main(["--token", "0xtoken", "--chain", "arbitrum"])
            except SystemExit as exc:
                assert exc.code == 2, exc.code
            else:
                raise AssertionError("accounting CLI accepted arbitrum without --exploration")
        assert "探索档链必须显式 --exploration" in stderr.getvalue(), stderr.getvalue()


def test_verify_recon_cli_policy():
    verify = load(ROOT / "scripts/evm/verify_recon.py", "f10_verify")
    required = ["--config", "missing-config", "--balances", "missing-balances",
                "--replay-stats", "missing-stats", "--gmgn", "missing-gmgn",
                "--token", "0xtoken", "--end-block", "123", "--out", "missing-out"]
    parsed = verify.parse_args([*required, "--chain", "arbitrum", "--exploration"])
    assert parsed.execution_mode == "exploration"
    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        try:
            verify.parse_args([*required, "--chain", "arbitrum"])
        except SystemExit as exc:
            assert exc.code == 2, exc.code
        else:
            raise AssertionError("verify_recon accepted arbitrum without --exploration")
    assert "探索档链必须显式 --exploration" in stderr.getvalue(), stderr.getvalue()


def test_time_spotcheck_cli_policy():
    with tempfile.TemporaryDirectory(prefix="f10_time_") as td:
        common = ["--plan", str(Path(td) / "missing-plan.json"),
                  "--input", str(Path(td) / "missing-input.csv"),
                  "--chain", "arbitrum", "--token", "0xtoken",
                  "--final-block", "123", "--out", str(Path(td) / "out.json"),
                  "--dry-run"]
        positive = run_script("scripts/lib/time_spotcheck.py", [*common, "--exploration"])
        assert positive.returncode == 2, combined_output(positive)
        assert "anchor_plan/receipt 校验失败" in combined_output(positive), combined_output(positive)
        negative = run_script("scripts/lib/time_spotcheck.py", common)
        assert negative.returncode == 2, combined_output(negative)
        assert "探索档链必须显式 --exploration" in combined_output(negative), \
            combined_output(negative)


def test_supply_truth_cli_policy():
    with tempfile.TemporaryDirectory(prefix="f10_supply_") as td:
        common = ["--chain", "arbitrum", "--token", "0xtoken",
                  "--as-of-block", "123", "--replay-stats",
                  str(Path(td) / "missing-stats.json"), "--out", str(Path(td) / "out.json")]
        positive = run_script("scripts/lib/supply_truth_gate.py", [*common, "--exploration"])
        assert positive.returncode == 1, combined_output(positive)
        assert "探索档链必须显式 --exploration" not in combined_output(positive)
        negative = run_script("scripts/lib/supply_truth_gate.py", common)
        assert negative.returncode == 2, combined_output(negative)
        assert "探索档链必须显式 --exploration" in combined_output(negative), \
            combined_output(negative)


def test_formal_cli_defaults_regression():
    from chain_registry import resolve_execution_mode

    assert resolve_execution_mode("eth", False, "accounting_adapter") == "formal"
    assert resolve_execution_mode("bsc", False, "balance_producer") == "formal"
    assert resolve_execution_mode("base", False, "time_producer") == "formal"
    assert resolve_execution_mode("solana", False, "supply") == "formal"
    accounting = load(ROOT / "scripts/evm/accounting_gate.py", "f10_accounting_formal")
    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        try:
            accounting.main(["--token", "0xtoken", "--chain", "eth"])
        except SystemExit as exc:
            assert exc.code == 2, exc.code
        else:
            raise AssertionError("accounting formal baseline unexpectedly executed")
    assert "正式模式必须给 --bundle" in stderr.getvalue(), stderr.getvalue()

    verify = load(ROOT / "scripts/evm/verify_recon.py", "f10_verify_formal")
    required = ["--config", "missing-config", "--balances", "missing-balances",
                "--replay-stats", "missing-stats", "--gmgn", "missing-gmgn",
                "--token", "0xtoken", "--end-block", "123", "--out", "missing-out"]
    assert verify.parse_args([*required, "--chain", "bsc"]).execution_mode == "formal"

    with tempfile.TemporaryDirectory(prefix="f10_formal_cli_") as td:
        time_args = ["--plan", str(Path(td) / "missing-plan.json"),
                     "--input", str(Path(td) / "missing-input.csv"),
                     "--chain", "base", "--token", "0xtoken", "--final-block", "123",
                     "--out", str(Path(td) / "time.json"), "--dry-run"]
        time_result = run_script("scripts/lib/time_spotcheck.py", time_args)
        assert time_result.returncode == 2, combined_output(time_result)
        assert "anchor_plan/receipt 校验失败" in combined_output(time_result), \
            combined_output(time_result)

        supply_result = run_script("scripts/lib/supply_truth_gate.py", [
            "--chain", "solana", "--out", str(Path(td) / "supply.json")])
        assert supply_result.returncode == 2, combined_output(supply_result)
        assert "solana 链必须给 --mint" in combined_output(supply_result), \
            combined_output(supply_result)


CONSUMER_TESTS = [
    test_consumer_rejects_exploration_mode,
    test_consumer_rejects_exploration_tier_relabelled_formal,
    test_wrapper_target_rejects_exploration_tier,
    test_formal_receipt_regression,
]

CLI_TESTS = [
    test_accounting_cli_policy,
    test_verify_recon_cli_policy,
    test_time_spotcheck_cli_policy,
    test_supply_truth_cli_policy,
    test_formal_cli_defaults_regression,
]


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    consumer_only = args == ["--consumer-only"]
    if args and not consumer_only:
        raise SystemExit("usage: test_arbitrum_exploration_cli.py [--consumer-only]")
    failures = []
    for test in CONSUMER_TESTS + ([] if consumer_only else CLI_TESTS):
        try:
            test()
        except Exception as exc:  # noqa: BLE001 - runner must report every counterexample
            failures.append((test.__name__, exc))
            print(f"FAIL {test.__name__}: {type(exc).__name__}: {exc}")
        else:
            print(f"PASS {test.__name__}")
    if failures:
        print(f"FAIL F-10: {len(failures)} regression(s) failed")
        return 1
    print("PASS F-10: exploration CLI execution + formal consumer isolation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
