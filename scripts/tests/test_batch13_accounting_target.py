#!/usr/bin/env python3
"""Batch 13 accounting receipt expected-target two-state regressions."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts/report"), str(ROOT / "scripts/lib"),
                str(ROOT / "scripts/tests")]

import handoff_manifest  # noqa: E402
import audit_release_gate  # noqa: E402
import shared_release_receipt as shared  # noqa: E402
from test_evm_observation_release import build_case as build_evm_case  # noqa: E402
from test_r9_batch3_release_guards import build_case as build_solana_case  # noqa: E402


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


class Completed:
    returncode = 0
    stdout = ""
    stderr = ""


def verify_failures(root: Path, *, wrapper_target: dict, exact_target: dict) -> list[str]:
    """Exercise the real handoff light-schema accounting call in isolation."""
    write_json(root / "candidate_universe.json", {
        "candidates": [{"id": "c1", "address": "owner-a", "reasons": ["fixture"]}],
    })
    write_json(root / "anomalies.json", [])
    write_json(root / "data_map.json", {"files": []})
    write_json(root / "reconciliation_report.json", {
        "target": wrapper_target,
        "checks": {"exact_reconcile": {"receipt": {"path": "exact.json"}}},
    })
    write_json(root / "wave_scan_report.json", {
        "schema": "wave-scan/v5", "edge_order_granularity": "transaction",
        "order_ambiguous": True, "non_formal": False, "waves": [],
        "equal_amount_groups": [], "requires_adjudication": False,
        "scan_universe": [], "scan_universe_count": 0,
        "must_adjudicate_count": 0,
    })
    write_json(root / "flow_anomaly_report.json", {
        "schema": "flow-anomaly/v3", "sinks": [], "sprays": [],
        "requires_adjudication": False,
    })
    manifest = {
        "scope": {"chains": [wrapper_target["chain"]],
                  "contract": wrapper_target["token"]},
        "artifacts": [],
    }
    receipts = {
        "supply_truth": {},
        "exact_reconcile": {
            "target": exact_target,
            "edge_source_binding": {},
            "inputs": {},
        },
    }
    originals = (
        handoff_manifest.validate_reconciliation_report,
        handoff_manifest.validate_solana_derived_bindings,
        handoff_manifest._solana_required_exact_paths,
        handoff_manifest.validate_evm_observation_source_chain,
        handoff_manifest.subprocess.run,
    )
    fails: list[str] = []
    try:
        handoff_manifest.validate_reconciliation_report = lambda *_a, **_k: (
            wrapper_target, receipts)
        handoff_manifest.validate_solana_derived_bindings = lambda *_a, **_k: None
        handoff_manifest._solana_required_exact_paths = lambda *_a, **_k: set()
        handoff_manifest.validate_evm_observation_source_chain = lambda *_a, **_k: None
        handoff_manifest.subprocess.run = lambda *_a, **_k: Completed()
        handoff_manifest._verify_light_schema(root, fails, manifest, legacy=False)
    finally:
        (handoff_manifest.validate_reconciliation_report,
         handoff_manifest.validate_solana_derived_bindings,
         handoff_manifest._solana_required_exact_paths,
         handoff_manifest.validate_evm_observation_source_chain,
         handoff_manifest.subprocess.run) = originals
    return fails


def test_r1_g1_frozen_accounting_binds_exact_target() -> None:
    with tempfile.TemporaryDirectory(prefix="batch13-r1-", dir="/private/tmp") as raw:
        root = Path(raw)
        bundle = build_solana_case(root)
        frozen_target = dict(bundle["target"])
        wrapper_target = {**frozen_target,
                          "as_of_block": frozen_target["as_of_block"] + 1}
        failures = verify_failures(
            root, wrapper_target=wrapper_target, exact_target=frozen_target)
        mismatch = [item for item in failures if "accounting target mismatch" in item]
        assert not mismatch, " | ".join(mismatch)


def accounting_mismatches(failures: list[str]) -> list[str]:
    return [item for item in failures if "accounting target mismatch" in item]


def test_n1_accounting_must_equal_exact_frozen_target() -> None:
    with tempfile.TemporaryDirectory(prefix="batch13-n1-", dir="/private/tmp") as raw:
        root = Path(raw)
        bundle = build_solana_case(root)
        frozen_target = dict(bundle["target"])
        wrapper_target = {**frozen_target,
                          "as_of_block": frozen_target["as_of_block"] + 2}
        accounting_path = root / "accounting_mode.json"
        accounting = json.loads(accounting_path.read_text(encoding="utf-8"))
        accounting["as_of_block"] = frozen_target["as_of_block"] - 1
        write_json(accounting_path, accounting)
        failures = verify_failures(
            root, wrapper_target=wrapper_target, exact_target=frozen_target)
        assert accounting_mismatches(failures), failures


def test_n2_accounting_chain_token_mismatch_rejected() -> None:
    with tempfile.TemporaryDirectory(prefix="batch13-n2-", dir="/private/tmp") as raw:
        root = Path(raw)
        bundle = build_solana_case(root)
        frozen_target = dict(bundle["target"])
        wrapper_target = {**frozen_target,
                          "as_of_block": frozen_target["as_of_block"] + 2}
        accounting_path = root / "accounting_mode.json"
        accounting = json.loads(accounting_path.read_text(encoding="utf-8"))
        accounting["mint"] = "2" * 32
        write_json(accounting_path, accounting)
        failures = verify_failures(
            root, wrapper_target=wrapper_target, exact_target=frozen_target)
        assert accounting_mismatches(failures), failures
    with tempfile.TemporaryDirectory(prefix="batch13-n2-chain-",
                                     dir="/private/tmp") as raw:
        root = Path(raw)
        bundle = build_solana_case(root)
        frozen_target = {**bundle["target"], "chain": "eth"}
        wrapper_target = {**frozen_target,
                          "as_of_block": frozen_target["as_of_block"] + 2}
        failures = verify_failures(
            root, wrapper_target=wrapper_target, exact_target=frozen_target)
        assert accounting_mismatches(failures), failures


def test_n3_static_solana_is_unchanged() -> None:
    with tempfile.TemporaryDirectory(prefix="batch13-n3-", dir="/private/tmp") as raw:
        root = Path(raw)
        bundle = build_solana_case(root)
        target = dict(bundle["target"])
        failures = verify_failures(root, wrapper_target=target, exact_target=target)
        assert not accounting_mismatches(failures), failures


def test_n4_evm_is_unchanged() -> None:
    with tempfile.TemporaryDirectory(prefix="batch13-evm-") as raw:
        root = Path(raw)
        fixture = build_evm_case(root)
        target = dict(fixture["target"])
        failures = verify_failures(root, wrapper_target=target, exact_target=target)
        assert not accounting_mismatches(failures), failures


def test_shared_release_uses_frozen_accounting_target() -> None:
    with tempfile.TemporaryDirectory(prefix="batch13-shared-", dir="/private/tmp") as raw:
        root = Path(raw)
        bundle = build_solana_case(root)
        frozen_target = dict(bundle["target"])
        wrapper_target = {**frozen_target,
                          "as_of_block": frozen_target["as_of_block"] + 1}
        receipts = {"supply_truth": {},
                    "exact_reconcile": {"target": frozen_target}}
        originals = (shared.validate_reconciliation_report,
                     shared.validate_evm_observation_source_chain,
                     shared.validate_adversarial_review)

        def fake_reconciliation(_root, expected_target=None, *, return_receipts=False):
            if expected_target is not None \
                    and shared.canonical_target(expected_target) \
                    != shared.canonical_target(wrapper_target):
                raise ValueError("reconciliation target/schema mismatch")
            return (wrapper_target, receipts) if return_receipts else wrapper_target

        try:
            shared.validate_reconciliation_report = fake_reconciliation
            shared.validate_evm_observation_source_chain = lambda *_a, **_k: None
            shared.validate_adversarial_review = lambda _root, expected_target=None: (
                frozen_target if shared.canonical_target(expected_target)
                == shared.canonical_target(frozen_target)
                else (_ for _ in ()).throw(AssertionError(expected_target)))
            assert shared.validate_sources(root) == shared.canonical_target(frozen_target)
        finally:
            (shared.validate_reconciliation_report,
             shared.validate_evm_observation_source_chain,
             shared.validate_adversarial_review) = originals


def audit_case_data(accounting: dict, wrapper_target: dict, shared_target: dict) -> dict:
    return {
        "accounting_mode.json": accounting,
        "reconciliation_report.json": {"target": wrapper_target},
        "shared_release_receipt.json": {"target": shared_target},
    }


def test_audit_two_state_and_negatives() -> None:
    with tempfile.TemporaryDirectory(prefix="batch13-audit-", dir="/private/tmp") as raw:
        root = Path(raw)
        bundle = build_solana_case(root)
        frozen_target = dict(bundle["target"])
        wrapper_target = {**frozen_target,
                          "as_of_block": frozen_target["as_of_block"] + 1}
        accounting = json.loads((root / "accounting_mode.json").read_text(encoding="utf-8"))
        receipts = {"supply_truth": {},
                    "exact_reconcile": {"target": frozen_target}}
        original = shared.validate_reconciliation_report
        try:
            shared.validate_reconciliation_report = lambda *_a, **_k: (
                wrapper_target, receipts)
            errors: list[str] = []
            chain = audit_release_gate.check_formal_case_chain(
                root, audit_case_data(accounting, wrapper_target, frozen_target), errors)
            assert chain == "sol" and not errors, errors

            wrong_slot = dict(accounting)
            wrong_slot["as_of_block"] = frozen_target["as_of_block"] - 1
            errors = []
            assert audit_release_gate.check_formal_case_chain(
                root, audit_case_data(wrong_slot, wrapper_target, frozen_target), errors) is None
            assert any("as_of_block" in item for item in errors), errors

            wrong_token = dict(accounting)
            wrong_token["mint"] = "2" * 32
            errors = []
            assert audit_release_gate.check_formal_case_chain(
                root, audit_case_data(wrong_token, wrapper_target, frozen_target), errors) is None
            assert any("token" in item for item in errors), errors
        finally:
            shared.validate_reconciliation_report = original


def test_audit_static_state_is_unchanged() -> None:
    with tempfile.TemporaryDirectory(prefix="batch13-audit-static-", dir="/private/tmp") as raw:
        root = Path(raw)
        bundle = build_solana_case(root)
        target = dict(bundle["target"])
        accounting = json.loads((root / "accounting_mode.json").read_text(encoding="utf-8"))
        errors: list[str] = []
        chain = audit_release_gate.check_formal_case_chain(
            root, audit_case_data(accounting, target, target), errors)
        assert chain == "sol" and not errors, errors


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv not in ([], ["--r1"]):
        raise SystemExit("usage: test_batch13_accounting_target.py [--r1]")
    tests = [test_r1_g1_frozen_accounting_binds_exact_target]
    if not argv:
        tests += [
            test_n1_accounting_must_equal_exact_frozen_target,
            test_n2_accounting_chain_token_mismatch_rejected,
            test_n3_static_solana_is_unchanged,
            test_n4_evm_is_unchanged,
            test_shared_release_uses_frozen_accounting_target,
            test_audit_two_state_and_negatives,
            test_audit_static_state_is_unchanged,
        ]
    failed = []
    for test in tests:
        try:
            test()
        except Exception as exc:
            failed.append((test.__name__, exc))
            print(f"FAIL {test.__name__}: {type(exc).__name__}: {exc}")
        else:
            print(f"PASS {test.__name__}")
    if failed:
        print(f"FAIL batch13 accounting target regressions: {len(failed)}/{len(tests)}")
        return 1
    print(f"PASS batch13 accounting target regressions: {len(tests)}/{len(tests)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
