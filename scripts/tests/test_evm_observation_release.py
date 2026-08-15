#!/usr/bin/env python3
"""Workorder C regressions for EVM observation consumers and READY handoff."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts/lib"), str(ROOT / "scripts/report"),
                str(ROOT / "scripts/tests")]

import handoff_manifest as handoff  # noqa: E402
import shared_release_receipt as shared  # noqa: E402
import audit_release_gate as audit_release  # noqa: E402
from endpoint_identity import endpoint_fingerprint  # noqa: E402
from test_supply_truth_gate import TOKEN, write_evm_bundle  # noqa: E402


AS_OF = 123
TOTAL = 1000
FAILS = []


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def repo_ref(rel: str) -> dict:
    return {"path": rel, "sha256": sha(ROOT / rel)}


def file_ref(path: Path, *, shown: str | None = None) -> dict:
    return {"path": shown if shown is not None else path.name,
            "size": path.stat().st_size, "sha256": sha(path)}


def receipt_ref(path: Path) -> dict:
    return {"path": path.name, "sha256": sha(path)}


def refresh_wrapper(root: Path) -> None:
    wrapper = json.loads((root / "reconciliation_report.json").read_text())
    for item in wrapper["checks"].values():
        item["receipt"]["sha256"] = sha(root / item["receipt"]["path"])
    write(root / "reconciliation_report.json", wrapper)


def build_case(root: Path) -> dict:
    bundle_path = write_evm_bundle(
        root, token=TOKEN, as_of=AS_OF, total=TOTAL, zero=0, dead=0)
    bundle = json.loads(bundle_path.read_text())
    target = dict(bundle["target"])
    bundle_rel = file_ref(bundle_path)
    bundle_abs = file_ref(bundle_path, shown=str(bundle_path.resolve()))

    replay_path = root / "replay_stats.json"
    write(replay_path, {"mint_total_raw": TOTAL, "burn_total_raw": 0})
    replay_ref = file_ref(replay_path)
    fixture_path = root / "fixture.json"
    write(fixture_path, {"fixture": True})
    fixture_ref = file_ref(fixture_path)

    accounting = {
        "schema": "accounting-gate/v2", "chain": "eth", "token": TOKEN,
        "producer": repo_ref("scripts/evm/accounting_gate.py"),
        "execution_mode": "formal", "as_of_block": AS_OF,
        "tip_block": AS_OF + 20, "model_probe_block": AS_OF + 20,
        "observation_bundle": bundle_abs,
        "observed_anchor": {"block": AS_OF,
                            "block_hash": bundle["anchor"]["block_hash"]},
        "checks": {"proxy": {"is_proxy": False}},
        "verdict": "PASS", "exit_code": 0,
    }
    write(root / "accounting_mode.json", accounting)

    producer_paths = {
        "balance": "scripts/evm/verify_recon.py",
        "supply": "scripts/evm/verify_recon.py",
        "supply_truth": "scripts/lib/supply_truth_gate.py",
        "time": "scripts/lib/time_spotcheck.py",
    }
    receipts = {}
    for key, producer in producer_paths.items():
        if key in {"balance", "supply"}:
            body = {
                "schema": "evm-reconciliation-receipt/v2",
                "observations": {
                    "balance_reconciliation": {"checked": 1, "matched": 1,
                                                "mismatched": 0, "rpc_errors": 0},
                    "supply_closure": {"closed": True, "negative_count": 0},
                },
                "inputs": {"replay_stats": replay_ref},
            }
        elif key == "supply_truth":
            body = {
                "schema": "supply-truth-receipt/v4", "gate": "supply_truth",
                "replay_net": str(TOTAL), "onchain_total_supply": str(TOTAL),
                "mint_total": str(TOTAL), "burn_total": "0", "diff": "0",
                "diff_bps": 0.0, "tolerance_bps": 10,
                "decision_rule": "primary_form1", "burn_form": None,
                "primary_verdict": "PASS", "sink_reconciliation": None,
                "inputs": {"replay_stats": replay_ref,
                           "observation_bundle": bundle_rel},
                "observation_bundle": bundle_abs,
            }
        else:
            body = {
                "schema": "time-spotcheck/v2", "points": 1, "exact_match": 1,
                "mismatch": 0, "rpc_err": 0, "inputs": {"fixture": fixture_ref},
            }
        body.update({"target": target, "producer": repo_ref(producer),
                     "mode": "formal", "verdict": "PASS", "exit_code": 0})
        path = root / f"reconciliation_{key}_receipt.json"
        write(path, body)
        receipts[key] = body

    checks = {
        key: {"status": "PASS", "exit_code": 0,
              "receipt": receipt_ref(root / f"reconciliation_{key}_receipt.json"),
              "producer": repo_ref(producer_paths[key])}
        for key in producer_paths
    }
    write(root / "reconciliation_report.json", {
        "schema": "reconciliation-report/v2", "target": target,
        "producer": repo_ref("scripts/report/reconciliation_report.py"),
        "verdict": "PASS", "exit_code": 0, "checks": checks,
    })
    write(root / "adversarial_review.json", {})
    return {"target": target, "bundle": bundle, "bundle_path": bundle_path,
            "accounting": accounting, "receipts": receipts}


def expect_error(call, needle: str, *, absent: str | None = None) -> str:
    try:
        call()
    except Exception as exc:  # noqa: BLE001 - assertion helper
        message = str(exc)
        assert needle.lower() in message.lower(), message
        if absent is not None:
            assert absent.lower() not in message.lower(), message
        return message
    raise AssertionError(f"invalid EVM release evidence accepted; expected {needle!r}")


def supply_item(root: Path) -> dict:
    path = root / "reconciliation_supply_truth_receipt.json"
    return {"receipt": receipt_ref(path), "status": "PASS", "exit_code": 0}


def handoff_fails(root: Path) -> list[str]:
    for name, value in {
        "candidate_universe.json": {"candidates": [{"id": "c1", "address": TOKEN,
                                                       "reasons": ["fixture"]}]},
        "anomalies.json": [],
        "wave_scan_report.json": {"schema": "wave-scan/v3", "waves": [],
                                  "equal_amount_groups": [], "requires_adjudication": False,
                                  "scan_universe": [], "scan_universe_count": 0,
                                  "must_adjudicate_count": 0},
        "flow_anomaly_report.json": {"schema": "flow-anomaly/v2", "sinks": [],
                                     "sprays": [], "requires_adjudication": False},
    }.items():
        write(root / name, value)
    artifacts = [{"path": p.name} for p in root.iterdir() if p.is_file()]
    manifest = {"scope": {"chains": ["eth"], "contract": TOKEN},
                "artifacts": artifacts}
    completed = subprocess.CompletedProcess([], 0, "", "")
    fails: list[str] = []
    with mock.patch.object(handoff.subprocess, "run", return_value=completed):
        handoff._verify_light_schema(str(root), fails, manifest, legacy=False)
    return fails


def test_accounting_missing_bundle_rejected():
    with tempfile.TemporaryDirectory(prefix="evm-release-accounting-missing-") as raw:
        root = Path(raw)
        case = build_case(root)
        accounting = copy.deepcopy(case["accounting"])
        accounting.pop("observation_bundle")
        expect_error(lambda: shared.validate_accounting_receipt(root, accounting),
                     "does not bind")


def test_accounting_anchor_mismatch_rejected():
    with tempfile.TemporaryDirectory(prefix="evm-release-accounting-anchor-") as raw:
        root = Path(raw)
        case = build_case(root)
        accounting = copy.deepcopy(case["accounting"])
        accounting["as_of_block"] += 1
        accounting["observed_anchor"]["block"] += 1
        expect_error(lambda: shared.validate_accounting_receipt(root, accounting),
                     "bundle anchor mismatch")


def test_supply_missing_bundle_rejected():
    with tempfile.TemporaryDirectory(prefix="evm-release-supply-missing-") as raw:
        root = Path(raw)
        case = build_case(root)
        receipt = copy.deepcopy(case["receipts"]["supply_truth"])
        receipt["inputs"].pop("observation_bundle")
        write(root / "reconciliation_supply_truth_receipt.json", receipt)
        expect_error(lambda: shared.validate_reconciliation_check(
            root, "supply_truth", supply_item(root), case["target"], "evm"),
            "does not bind")


def test_supply_n2_mismatch_rejected():
    with tempfile.TemporaryDirectory(prefix="evm-release-supply-n2-") as raw:
        root = Path(raw)
        case = build_case(root)
        receipt = copy.deepcopy(case["receipts"]["supply_truth"])
        receipt["onchain_total_supply"] = str(TOTAL + 1)
        write(root / "reconciliation_supply_truth_receipt.json", receipt)
        expect_error(lambda: shared.validate_reconciliation_check(
            root, "supply_truth", supply_item(root), case["target"], "evm"), "N-2")


def test_accounting_supply_bundle_same_source_rejected():
    with tempfile.TemporaryDirectory(prefix="evm-release-source-chain-") as raw:
        root = Path(raw)
        case = build_case(root)
        alt = root / "alt"
        alt.mkdir()
        alt_bundle = write_evm_bundle(
            alt, token=TOKEN, as_of=AS_OF, total=TOTAL, zero=0, dead=0)
        alt_value = json.loads(alt_bundle.read_text())
        alt_value["attestation"]["endpoint"] = endpoint_fingerprint(
            "https://second-rpc.example.test")
        write(alt_bundle, alt_value)
        receipt = copy.deepcopy(case["receipts"]["supply_truth"])
        receipt["inputs"]["observation_bundle"] = file_ref(
            alt_bundle, shown="alt/evm_observation_bundle.json")
        write(root / "reconciliation_supply_truth_receipt.json", receipt)
        expect_error(lambda: shared.validate_evm_observation_source_chain(
            root, case["accounting"], receipt), "not the same source")


def test_evm_legacy_schemas_rejected_with_migration():
    with tempfile.TemporaryDirectory(prefix="evm-release-legacy-") as raw:
        root = Path(raw)
        case = build_case(root)
        accounting = copy.deepcopy(case["accounting"])
        accounting["schema"] = "accounting-gate/v1"
        expect_error(lambda: shared.validate_accounting_receipt(root, accounting),
                     "observe_supply.py")
        receipt = copy.deepcopy(case["receipts"]["supply_truth"])
        receipt["schema"] = "supply-truth-receipt/v3"
        write(root / "reconciliation_supply_truth_receipt.json", receipt)
        expect_error(lambda: shared.validate_reconciliation_check(
            root, "supply_truth", supply_item(root), case["target"], "evm"),
            "observe_supply.py")


def test_handoff_rejects_accounting_missing_anchor_and_source_split():
    mutations = (
        ("missing", lambda root, case: (
            lambda obj: (obj.pop("observation_bundle"),
                         write(root / "accounting_mode.json", obj)))(
                json.loads((root / "accounting_mode.json").read_text())), "does not bind"),
        ("anchor", lambda root, case: _lift_handoff_accounting_anchor(root),
         "anchor mismatch"),
        ("source", lambda root, case: _bind_alt_supply_bundle(root, case), "same source"),
    )
    for label, mutate, needle in mutations:
        with tempfile.TemporaryDirectory(prefix=f"evm-handoff-{label}-") as raw:
            root = Path(raw)
            case = build_case(root)
            mutate(root, case)
            refresh_wrapper(root)
            failures = handoff_fails(root)
            assert any(needle.lower() in item.lower() for item in failures), failures


def _bind_alt_supply_bundle(root: Path, case: dict) -> None:
    (root / "alt").mkdir()
    alt_bundle = write_evm_bundle(
        root / "alt", token=TOKEN, as_of=AS_OF, total=TOTAL, zero=0, dead=0)
    alt_value = json.loads(alt_bundle.read_text())
    alt_value["attestation"]["endpoint"] = endpoint_fingerprint(
        "https://second-rpc.example.test")
    write(alt_bundle, alt_value)
    path = root / "reconciliation_supply_truth_receipt.json"
    receipt = json.loads(path.read_text())
    receipt["inputs"]["observation_bundle"] = file_ref(
        alt_bundle, shown="alt/evm_observation_bundle.json")
    write(path, receipt)


def _lift_handoff_accounting_anchor(root: Path) -> None:
    lifted = AS_OF + 1
    accounting = json.loads((root / "accounting_mode.json").read_text())
    accounting["as_of_block"] = lifted
    accounting["observed_anchor"]["block"] = lifted
    write(root / "accounting_mode.json", accounting)
    wrapper = json.loads((root / "reconciliation_report.json").read_text())
    target = {**wrapper["target"], "as_of_block": lifted}
    wrapper["target"] = target
    for item in wrapper["checks"].values():
        path = root / item["receipt"]["path"]
        receipt = json.loads(path.read_text())
        receipt["target"] = target
        write(path, receipt)
    write(root / "reconciliation_report.json", wrapper)


def test_f02_original_scalar_rewrite_rejected():
    with tempfile.TemporaryDirectory(prefix="evm-release-f02-") as raw:
        root = Path(raw)
        case = build_case(root)
        accounting = json.loads((root / "accounting_mode.json").read_text())
        accounting["schema"] = "accounting-gate/v1"
        accounting.pop("execution_mode", None)
        accounting.pop("observation_bundle", None)
        accounting.pop("observed_anchor", None)
        write(root / "accounting_mode.json", accounting)
        replay = root / "replay_stats.json"
        write(replay, {"mint_total_raw": 777, "burn_total_raw": 0})
        replay_binding = file_ref(replay)
        for key in ("balance", "supply", "supply_truth"):
            path = root / f"reconciliation_{key}_receipt.json"
            receipt = json.loads(path.read_text())
            receipt["inputs"]["replay_stats"] = replay_binding
            if key == "supply_truth":
                receipt["schema"] = "supply-truth-receipt/v3"
                receipt["replay_net"] = receipt["onchain_total_supply"] = "777"
                receipt["mint_total"] = "777"
                receipt["inputs"].pop("observation_bundle", None)
                receipt.pop("observation_bundle", None)
            write(path, receipt)
        refresh_wrapper(root)
        with mock.patch.object(shared, "validate_adversarial_review",
                               return_value=case["target"]):
            expect_error(lambda: shared.validate_sources(root), "observe_supply.py")


def test_f03_retarget_dies_at_bundle_anchor_not_target():
    with tempfile.TemporaryDirectory(prefix="evm-release-f03-") as raw:
        root = Path(raw)
        case = build_case(root)
        lifted = 999999
        target = {**case["target"], "as_of_block": lifted}
        accounting = json.loads((root / "accounting_mode.json").read_text())
        accounting["as_of_block"] = lifted
        accounting["tip_block"] = accounting["model_probe_block"] = lifted
        accounting["observed_anchor"]["block"] = lifted
        write(root / "accounting_mode.json", accounting)
        wrapper = json.loads((root / "reconciliation_report.json").read_text())
        wrapper["target"] = target
        for item in wrapper["checks"].values():
            path = root / item["receipt"]["path"]
            receipt = json.loads(path.read_text())
            receipt["target"] = target
            write(path, receipt)
            item["receipt"]["sha256"] = sha(path)
        write(root / "reconciliation_report.json", wrapper)
        assert shared.canonical_target(target) == shared.canonical_target({
            "chain": accounting["chain"], "token": accounting["token"],
            "as_of_block": accounting["as_of_block"]})
        with mock.patch.object(shared, "validate_adversarial_review", return_value=target):
            message = expect_error(
                lambda: shared.validate_sources(root),
                "bundle anchor mismatch", absent="target mismatch")
        print(f"F03_LAYER={message}")


def test_solana_accounting_and_supply_paths_unchanged():
    from test_r9_batch3_release_guards import build_case as build_solana
    with tempfile.TemporaryDirectory(prefix="evm-release-solana-control-",
                                     dir="/private/tmp") as raw:
        root = Path(raw)
        bundle = build_solana(root)
        target, accounting, bundle_sha = shared.validate_accounting_receipt(root)
        receipt = shared.validate_reconciliation_check(
            root, "supply_truth", {"receipt": receipt_ref(root / "supply_truth.json"),
                                   "status": "PASS", "exit_code": 0},
            bundle["target"], "solana")
        assert target == shared.canonical_target(bundle["target"])
        assert accounting["schema"] == "accounting-gate/v1"
        assert bundle_sha is not None and receipt["schema"] == "supply-truth-receipt/v3"


def test_audit_release_reuses_public_accounting_validator():
    with tempfile.TemporaryDirectory(prefix="evm-release-audit-common-") as raw:
        root = Path(raw)
        case = build_case(root)
        errors: list[str] = []
        with mock.patch.object(
                shared, "validate_accounting_receipt",
                wraps=shared.validate_accounting_receipt) as validator:
            audit_release.check_accounting(root, case["accounting"], errors)
        assert not errors, errors
        assert validator.call_count == 1


def main() -> int:
    tests = (
        test_accounting_missing_bundle_rejected,
        test_accounting_anchor_mismatch_rejected,
        test_supply_missing_bundle_rejected,
        test_supply_n2_mismatch_rejected,
        test_accounting_supply_bundle_same_source_rejected,
        test_evm_legacy_schemas_rejected_with_migration,
        test_handoff_rejects_accounting_missing_anchor_and_source_split,
        test_f02_original_scalar_rewrite_rejected,
        test_f03_retarget_dies_at_bundle_anchor_not_target,
        test_solana_accounting_and_supply_paths_unchanged,
        test_audit_release_reuses_public_accounting_validator,
    )
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001 - aggregate red/green evidence
            FAILS.append((test.__name__, str(exc)))
            print(f"FAIL {test.__name__}: {exc}")
        else:
            print(f"PASS {test.__name__}")
    if FAILS:
        print(f"FAIL workorder C EVM observation release: {len(FAILS)}/{len(tests)}")
        return 1
    print(f"PASS workorder C EVM observation release: {len(tests)}/{len(tests)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
