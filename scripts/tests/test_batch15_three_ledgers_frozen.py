#!/usr/bin/env python3
"""Batch 15 B-7 owner source and series-cutoff frozen projection regressions."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MPL_CACHE = Path("/private/tmp/batch15-matplotlib-cache")
MPL_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CACHE))
sys.path[:0] = [str(ROOT / "scripts/report"), str(ROOT / "scripts/lib"),
                str(ROOT / "scripts/tests")]

import audit_release_gate as gate  # noqa: E402
import holder_distribution_scan as distribution  # noqa: E402
import shared_release_receipt as shared  # noqa: E402
from test_batch11_frozen_bundle_binding import (  # noqa: E402
    FROZEN_SLOT,
    LIVE_SLOT,
    MINT,
    build_bundle,
    build_case as build_frozen_case,
    ref,
)
from test_repair_batch_d import build_solana_case  # noqa: E402


def write_json(path: Path, value) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    return path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_gate_data(root: Path) -> dict:
    names = (
        "accounting_mode.json", "reconciliation_report.json",
        "membership_ledger.json", "position_ledger.json",
        "economic_control_ledger.json",
    )
    return {name: json.loads((root / name).read_text(encoding="utf-8"))
            for name in names}


def write_ledgers(root: Path, *, slot: int, owner: str, amount: int) -> None:
    snapshot = write_json(root / "balances_snapshot.json", {
        "schema": "address-balance-snapshot/v1",
        "as_of_block": slot,
        "entries": [{"address": owner, "balance_raw": str(amount)}],
    })
    source = {"path": "balances_snapshot.json", "sha256": sha(snapshot),
              "as_of_block": slot}
    write_json(root / "membership_ledger.json", {"entries": [{
        "entity_id": "e1", "address": owner, "membership": "strict",
        "as_of_balance_raw": str(amount), "balance_source": source,
    }]})
    write_json(root / "position_ledger.json", {"entries": [{
        "entity_id": "e1", "address": owner, "location_id": f"wallet:{owner}",
        "amount_raw": str(amount),
    }]})
    write_json(root / "economic_control_ledger.json", {
        "entries": [{
            "entity_id": "e1", "wallet_self_held_raw": str(amount),
            "confirmed_facility_claims": [],
            "confirmed_economic_control_raw": str(amount),
            "unresolved_facility_exposure": [],
        }],
        "double_count_check_passed": True,
        "unresolved_count": 0,
        "unresolved": [],
    })


def build_unit_case(root: Path, *, accounting_slot: int = FROZEN_SLOT,
                    ledger_slot: int = FROZEN_SLOT,
                    owner: str = "owner-a", amount: int = 60):
    fixture = build_frozen_case(root)
    write_json(root / "accounting_mode.json", {
        "schema": "accounting-gate/v1", "chain": "solana", "mint": MINT,
        "token": MINT, "as_of_block": accounting_slot,
        "verdict": "PASS", "exit_code": 0, "mode": "standard",
        "execution_mode": "formal",
    })
    write_ledgers(root, slot=ledger_slot, owner=owner, amount=amount)
    return fixture


def check_three_ledgers(root: Path, fixture, *, fake_check=None) -> list[str]:
    original = shared.validate_reconciliation_check
    try:
        shared.validate_reconciliation_check = fake_check or fixture["fake_check"]
        errors: list[str] = []
        gate.check_three_ledgers(root, load_gate_data(root), errors, chain="sol")
        return errors
    finally:
        shared.validate_reconciliation_check = original


def assert_two_b7_errors(errors: list[str], *, frozen: int, observed: int) -> None:
    time_errors = [item for item in errors
                   if "与四查冻结时点" in item and "不一致" in item]
    value_errors = [item for item in errors if "不等值" in item]
    assert len(errors) == 2 and len(time_errors) == 1 and len(value_errors) == 1, \
        "R1 errors 必须恰好命中 B-7 时点不一致＋逐址不等值: " \
        + json.dumps(errors, ensure_ascii=False)
    assert str(frozen) in time_errors[0] and str(observed) in time_errors[0], errors


def test_r1_g1_frozen_ledgers_use_exact_owners() -> None:
    with tempfile.TemporaryDirectory(prefix="batch15-r1-", dir="/private/tmp") as raw:
        root = Path(raw)
        fixture = build_unit_case(root)
        errors = check_three_ledgers(root, fixture)
        if errors:
            assert_two_b7_errors(errors, frozen=FROZEN_SLOT, observed=LIVE_SLOT)
            raise AssertionError(
                "R1 修前精确红：" + json.dumps(errors, ensure_ascii=False))
        assert errors == []


def test_n1_live_ledgers_rejected_in_frozen_case() -> None:
    with tempfile.TemporaryDirectory(prefix="batch15-n1-", dir="/private/tmp") as raw:
        root = Path(raw)
        fixture = build_unit_case(root, accounting_slot=FROZEN_SLOT,
                                  ledger_slot=LIVE_SLOT, amount=70)
        errors = check_three_ledgers(root, fixture)
        assert_two_b7_errors(errors, frozen=FROZEN_SLOT, observed=LIVE_SLOT)


def test_n2_tampered_frozen_owners_fail_without_fallback() -> None:
    with tempfile.TemporaryDirectory(prefix="batch15-n2-", dir="/private/tmp") as raw:
        root = Path(raw)
        fixture = build_unit_case(root)
        write_json(fixture["frozen_owners"], {"owner-a": 61, "owner-b": 39})
        errors = check_three_ledgers(root, fixture)
        assert any("冻结态深验未通过" in item for item in errors), errors
        assert not any("不等值" in item for item in errors), errors


def test_n3_frozen_owners_symlink_rejected() -> None:
    with tempfile.TemporaryDirectory(prefix="batch15-n3-", dir="/private/tmp") as raw:
        root = Path(raw)
        fixture = build_unit_case(root)
        fixture["frozen_owners"].unlink()
        os.symlink(fixture["live_bundle"].parent / "holders_owners.json",
                   fixture["frozen_owners"])
        errors = check_three_ledgers(root, fixture)
        assert any("冻结态深验未通过" in item or "实物不可用" in item
                   for item in errors), errors
        assert not any("不等值" in item for item in errors), errors


def test_n4a_true_static_case_unchanged() -> None:
    with tempfile.TemporaryDirectory(prefix="batch15-n4a-", dir="/private/tmp") as raw:
        root = Path(raw)
        fixture = build_unit_case(root, accounting_slot=LIVE_SLOT,
                                  ledger_slot=LIVE_SLOT, amount=70)
        live_owners = root / "data/observe_live/holders_owners.json"
        live_ref = ref(live_owners, "data/observe_live/holders_owners.json")

        def static_check(_root, key, item, check_target, family):
            if key == "exact_reconcile":
                return {
                    "target": {"chain": "solana", "token": MINT,
                               "as_of_block": LIVE_SLOT},
                    "inputs": {"holders_owners": live_ref},
                    "edge_source_binding": {"cache_kind": "base", "gid": None,
                                            "soltx_edges_sha256": "1" * 64,
                                            "soltx_meta_sha256": "2" * 64,
                                            "edge_logical_sha256": "3" * 64},
                }
            return fixture["fake_check"](_root, key, item, check_target, family)

        errors = check_three_ledgers(root, fixture, fake_check=static_check)
        assert errors == [], errors


def test_n4b_accounting_cannot_disguise_dynamic_as_static() -> None:
    with tempfile.TemporaryDirectory(prefix="batch15-n4b-", dir="/private/tmp") as raw:
        root = Path(raw)
        fixture = build_unit_case(root, accounting_slot=LIVE_SLOT,
                                  ledger_slot=LIVE_SLOT, amount=70)
        errors = check_three_ledgers(root, fixture)
        assert any("accounting target 与中央选择器结果不一致" in item
                   for item in errors), errors
        assert not any("不等值" in item for item in errors), errors


def test_n5_absolute_exact_ref_inside_passes_outside_rejected() -> None:
    with tempfile.TemporaryDirectory(prefix="batch15-n5-in-", dir="/private/tmp") as raw:
        root = Path(raw)
        fixture = build_unit_case(root)
        fixture["state"]["exact_ref"]["path"] = str(fixture["frozen_owners"])
        assert check_three_ledgers(root, fixture) == []

    with tempfile.TemporaryDirectory(prefix="batch15-n5-root-", dir="/private/tmp") as raw, \
            tempfile.TemporaryDirectory(prefix="batch15-n5-out-", dir="/private/tmp") as outer:
        root = Path(raw)
        fixture = build_unit_case(root)
        outside = write_json(Path(outer) / "holders_owners.json",
                             {"owner-a": 60, "owner-b": 40})
        fixture["state"]["exact_ref"] = ref(outside, str(outside))
        errors = check_three_ledgers(root, fixture)
        assert any("冻结态深验未通过" in item for item in errors), errors
        assert not any("不等值" in item for item in errors), errors


def test_n8_snapshot_default_is_frozen_explicit_is_observation() -> None:
    with tempfile.TemporaryDirectory(prefix="batch15-n8-", dir="/private/tmp") as raw:
        root = Path(raw)
        build_unit_case(root)
        default_path, default_rel = distribution.find_snapshot(root, None)
        explicit_rel = "data/observe_live/holders_owners.json"
        explicit_path, shown_rel = distribution.find_snapshot(root, explicit_rel)
        assert default_path == root / "data/holders_owners.json"
        assert default_rel == "data/holders_owners.json"
        assert explicit_path == root / explicit_rel and shown_rel == explicit_rel


def case_ref(root: Path, path: Path, shown: str | None = None) -> dict:
    return {"path": shown or path.relative_to(root).as_posix(),
            "size": path.stat().st_size, "sha256": sha(path)}


def rewrite_jsonl_slot(path: Path, slot: int) -> None:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    for row in rows:
        row["as_of_slot"] = slot
    path.write_text("".join(json.dumps(row) + "\n" for row in rows),
                    encoding="utf-8")


def build_dynamic_integration_case(root: Path):
    """Turn batch D's real static gate fixture into frozen-500/live-501."""
    report = build_solana_case(root)
    frozen_bundle = root / "data/solana_observation_bundle_frozen.json"
    frozen_bundle.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / "supply_receipt.json", frozen_bundle)

    live_bundle, live_owners = build_bundle(
        root, "data/observe_live", LIVE_SLOT,
        {"ownersol1": 70, "ownersol2": 30},
        "data/observe_live/solana_observation_bundle.json")
    live_target = {"chain": "solana", "token": MINT,
                   "as_of_block": LIVE_SLOT}

    anchor_path = root / "fixture_anchors.jsonl"
    rewrite_jsonl_slot(anchor_path, LIVE_SLOT)
    anchor_ref = case_ref(root, anchor_path)
    for name in ("balance_receipt.json", "time_receipt.json"):
        path = root / name
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["target"] = dict(live_target)
        doc["output"] = dict(anchor_ref)
        write_json(path, doc)

    supply_truth_path = root / "supply_truth_receipt.json"
    supply_truth = json.loads(supply_truth_path.read_text(encoding="utf-8"))
    supply_truth["target"] = dict(live_target)
    supply_truth["observed_context_slot"] = LIVE_SLOT + 3
    supply_truth["inputs"]["observation_bundle"] = case_ref(
        root, live_bundle)
    write_json(supply_truth_path, supply_truth)

    wrapper_path = root / "reconciliation_report.json"
    wrapper = json.loads(wrapper_path.read_text(encoding="utf-8"))
    wrapper["target"] = dict(live_target)
    wrapper["checks"]["supply"]["receipt"] = case_ref(root, live_bundle)
    for key in ("balance", "time", "supply_truth"):
        path = root / f"{key}_receipt.json"
        wrapper["checks"][key]["receipt"] = case_ref(root, path, path.name)
    write_json(wrapper_path, wrapper)

    data_map = json.loads((root / "data_map.json").read_text(encoding="utf-8"))
    data_map["files"] = [
        {"path": "data/holders_owners.json",
         "sha256": sha(root / "data/holders_owners.json")},
        {"path": "data/observe_live/holders_owners.json", "sha256": sha(live_owners)},
        {"path": "data/solana_observation_bundle_frozen.json",
         "sha256": sha(frozen_bundle)},
    ]
    write_json(root / "data_map.json", data_map)

    shared.create_bundle(root)

    from formal_ready_test_harness import run_formal_script
    dist = ROOT / "scripts/report/holder_distribution_scan.py"
    snapshot = "data/observe_live/holders_owners.json"
    proc = run_formal_script(
        dist, ["--case-dir", str(root), "--stage", "initial",
               "--snapshot", snapshot])
    assert proc.returncode == 0, proc.stdout + proc.stderr

    rounds = root / "distribution_rounds.json"
    if rounds.exists():
        rounds.unlink()
    fig1 = root / "charts/final/fig1.png"
    if fig1.exists():
        fig1.unlink()
    proc = run_formal_script(
        dist, ["--case-dir", str(root), "--stage", "final", "--round", "1",
               "--snapshot", snapshot])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    proc = run_formal_script(
        dist, ["record-round", "--case-dir", str(root),
               "--scan", "dist_rounds/round_1/distribution_scan.json"])
    assert proc.returncode == 0, proc.stdout + proc.stderr

    figures = ROOT / "scripts/report/figures_from_facts.py"
    proc = subprocess.run(
        [sys.executable, str(figures), "fig1", "--state", "analysis-state.json",
         "--out", "charts/final/fig1.png"], cwd=root,
        capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    a5 = ROOT / "scripts/report/a5_report_seal.py"
    proc = run_formal_script(
        a5, ["--case-dir", str(root), "--report", str(report),
             "--a4-seal", str(root / "a4_seal.json"),
             "--out", str(root / "a5_report_seal.json")])
    assert proc.returncode == 0, proc.stdout + proc.stderr

    resign_points = (
        "live supply observation bundle", "balance receipt", "time receipt",
        "supply-truth receipt", "reconciliation wrapper", "data_map binding",
        "shared release receipt", "initial distribution scan",
        "final distribution scan", "distribution rounds", "fig1 legend receipt",
        "A5 report seal",
    )
    assert len(resign_points) <= 12, resign_points
    return report, resign_points


def test_n6_dynamic_full_gate() -> None:
    with tempfile.TemporaryDirectory(prefix="batch15-n6-", dir="/private/tmp") as raw:
        root = Path(raw)
        report, _resign_points = build_dynamic_integration_case(root)
        errors = gate.run(root, report, profile="new-analysis")
        if errors:
            relevant = [item for item in errors if "与四查冻结时点" in item
                        or "不等值" in item or "cutoff" in item]
            assert any("与四查冻结时点" in item for item in relevant), errors
            assert any("不等值" in item for item in relevant), errors
            assert any("cutoff" in item for item in relevant), errors
            raise AssertionError(
                "N6 修前动态集成红：" + json.dumps(relevant, ensure_ascii=False))
        assert errors == []


def test_n7_wrong_projected_cutoff_rejected() -> None:
    with tempfile.TemporaryDirectory(prefix="batch15-n7-", dir="/private/tmp") as raw:
        root = Path(raw)
        report, _resign_points = build_dynamic_integration_case(root)
        original = gate._frozen_consumer_target

        def wrong_cutoff(case_dir, data, errors, label):
            expected, wrapper, receipts = original(case_dir, data, errors, label)
            if label == "发布期序列 cutoff 目标" and expected is not None:
                expected = {**expected, "as_of_block": LIVE_SLOT}
            return expected, wrapper, receipts

        try:
            gate._frozen_consumer_target = wrong_cutoff
            errors = gate.run(root, report, profile="new-analysis")
        finally:
            gate._frozen_consumer_target = original
        assert any("cutoff" in item for item in errors), errors


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv not in ([], ["--r1"]):
        raise SystemExit("usage: test_batch15_three_ledgers_frozen.py [--r1]")
    tests = [test_r1_g1_frozen_ledgers_use_exact_owners, test_n6_dynamic_full_gate]
    if not argv:
        tests += [
            test_n1_live_ledgers_rejected_in_frozen_case,
            test_n2_tampered_frozen_owners_fail_without_fallback,
            test_n3_frozen_owners_symlink_rejected,
            test_n4a_true_static_case_unchanged,
            test_n4b_accounting_cannot_disguise_dynamic_as_static,
            test_n5_absolute_exact_ref_inside_passes_outside_rejected,
            test_n8_snapshot_default_is_frozen_explicit_is_observation,
            test_n7_wrong_projected_cutoff_rejected,
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
        print(f"FAIL batch15 frozen consumers: {len(failed)}/{len(tests)}")
        return 1
    print(f"PASS batch15 frozen consumers: {len(tests)}/{len(tests)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
