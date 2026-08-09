#!/usr/bin/env python3
"""Mutation-sensitive negatives for the six batch-3 Solana release assertions."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts/lib"), str(ROOT / "scripts/tests")]
from test_r9_batch3_solana_observation import (  # noqa: E402
    MINT, SolanaTransportFake)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def shared_module():
    override = os.environ.get("R9_SHARED_RELEASE_MODULE")
    path = Path(override) if override else ROOT / "scripts/report/shared_release_receipt.py"
    module = load(path, f"r9_b3_release_{hash(path)}")
    # Mutation runs load an exact temporary source copy; repository identity
    # must still resolve against the real frozen worktree.
    module.REPO = ROOT
    module.HERE = ROOT / "scripts/report"
    return module


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def ref(path):
    return {"path": path.name, "size": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def expect_error(call, needle):
    try:
        call()
    except Exception as exc:
        assert needle.lower() in str(exc).lower(), str(exc)
        return
    raise AssertionError(f"invalid release evidence accepted; expected {needle!r}")


def build_case(case):
    scan = load(ROOT / "scripts/solana/scan_token_accounts.py", "r9_b3_release_scan")
    accounting = load(
        ROOT / "scripts/solana/accounting_gate_sol.py", "r9_b3_release_accounting")
    supply = load(ROOT / "scripts/lib/supply_truth_gate.py", "r9_b3_release_supply")
    old = Path.cwd()
    os.chdir(case)
    try:
        assert scan.main([
            MINT, "--program", "spl", "--rpc", "fixture://solana",
            "--out", "supply_snapshot.json", "--bundle", "bundle.json",
            "--work-dir", "data",
        ], request_json=SolanaTransportFake()) == 0
        bundle = json.loads((case / "bundle.json").read_text())
        slot = bundle["snapshot"]["slot"]
        try:
            accounting.main([
                "--mint", MINT, "--bundle", "bundle.json",
                "--as-of-slot", str(slot), "--out", "accounting_mode.json",
            ])
        except SystemExit as exc:
            assert exc.code == 0
        write(case / "replay_stats.json", {"mint_total_raw": 100, "burn_total_raw": 0})
        assert supply.main([
            "--chain", "solana", "--mint", MINT,
            "--observation-bundle", "bundle.json", "--as-of-block", str(slot),
            "--replay-stats", "replay_stats.json", "--out", "supply_truth.json",
        ]) == 0
        write(case / "adversarial_review.json", {})
        return bundle
    finally:
        os.chdir(old)


class AccountingPassed(RuntimeError):
    pass


def validate_accounting_prefix(shared, case):
    with mock.patch.object(
            shared, "validate_reconciliation_report",
            side_effect=AccountingPassed("accounting guards passed")):
        shared.validate_sources(case)


def test_release_rejects_solana_accounting_exploration():
    with tempfile.TemporaryDirectory(prefix="r9-release-exploration-") as raw:
        case = Path(raw).resolve()
        build_case(case)
        accounting = json.loads((case / "accounting_mode.json").read_text())
        accounting["execution_mode"] = "exploration"
        write(case / "accounting_mode.json", accounting)
        shared = shared_module()
        expect_error(lambda: validate_accounting_prefix(shared, case), "exploration")


def test_release_rejects_accounting_without_bundle_binding():
    with tempfile.TemporaryDirectory(prefix="r9-release-accounting-ref-") as raw:
        case = Path(raw).resolve()
        build_case(case)
        accounting = json.loads((case / "accounting_mode.json").read_text())
        accounting.pop("observation_bundle", None)
        write(case / "accounting_mode.json", accounting)
        shared = shared_module()
        expect_error(lambda: validate_accounting_prefix(shared, case), "does not bind")


def test_release_rejects_accounting_slot_not_snapshot_slot():
    with tempfile.TemporaryDirectory(prefix="r9-release-accounting-slot-") as raw:
        case = Path(raw).resolve()
        bundle = build_case(case)
        accounting = json.loads((case / "accounting_mode.json").read_text())
        accounting["observed_context_slot"] = bundle["snapshot"]["slot"] + 1
        write(case / "accounting_mode.json", accounting)
        shared = shared_module()
        expect_error(lambda: validate_accounting_prefix(shared, case), "snapshot slot")


def supply_item(case, filename):
    return {"receipt": ref(case / filename), "status": "PASS", "exit_code": 0}


def test_release_rejects_supply_truth_without_bundle_binding():
    with tempfile.TemporaryDirectory(prefix="r9-release-truth-ref-") as raw:
        case = Path(raw).resolve()
        bundle = build_case(case)
        receipt = json.loads((case / "supply_truth.json").read_text())
        receipt["inputs"].pop("observation_bundle", None)
        write(case / "supply_truth.json", receipt)
        shared = shared_module()
        expect_error(lambda: shared.validate_reconciliation_check(
            case, "supply_truth", supply_item(case, "supply_truth.json"),
            bundle["target"], "solana"), "does not bind")


def test_release_rejects_supply_truth_observed_slot_not_supply_slot():
    with tempfile.TemporaryDirectory(prefix="r9-release-truth-slot-") as raw:
        case = Path(raw).resolve()
        bundle = build_case(case)
        receipt = json.loads((case / "supply_truth.json").read_text())
        receipt["observed_context_slot"] = bundle["supply"]["slot"] + 1
        write(case / "supply_truth.json", receipt)
        shared = shared_module()
        expect_error(lambda: shared.validate_reconciliation_check(
            case, "supply_truth", supply_item(case, "supply_truth.json"),
            bundle["target"], "solana"), "slots are not bound")


def test_release_rejects_invalid_solana_supply_bundle():
    with tempfile.TemporaryDirectory(prefix="r9-release-supply-bundle-") as raw:
        case = Path(raw).resolve()
        bundle = build_case(case)
        bundle["attestation"]["observed_genesis"] = "wrong-genesis"
        write(case / "bundle.json", bundle)
        shared = shared_module()
        expect_error(lambda: shared.validate_reconciliation_check(
            case, "supply", supply_item(case, "bundle.json"),
            bundle["target"], "solana"), "genesis")


def main():
    tests = (
        test_release_rejects_solana_accounting_exploration,
        test_release_rejects_accounting_without_bundle_binding,
        test_release_rejects_accounting_slot_not_snapshot_slot,
        test_release_rejects_supply_truth_without_bundle_binding,
        test_release_rejects_supply_truth_observed_slot_not_supply_slot,
        test_release_rejects_invalid_solana_supply_bundle,
    )
    for test in tests:
        test()
    print(f"PASS R9 B3F3-G3: Solana release negatives {len(tests)}/{len(tests)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
