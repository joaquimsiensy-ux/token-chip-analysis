#!/usr/bin/env python3
"""Batch 18 blind-review digest: witness anti-forgery and classifier defense."""
from __future__ import annotations

import copy
import contextlib
import dataclasses
import gzip
import hashlib
import io
import json
import sys
import tempfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts/report"), str(ROOT / "scripts/lib"),
                str(ROOT / "scripts/tests")]

import shared_release_receipt as shared  # noqa: E402
from test_batch15_three_ledgers_frozen import (  # noqa: E402
    build_dynamic_integration_case,
    write_json,
)
from test_batch18_manifest_stage2_loop import (  # noqa: E402
    artifact_paths,
    dump,
    generate,
    load,
    make_case,
)


INVALID = ["reconciliation witness 无效/过期"]


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while block := stream.read(131072):
            digest.update(block)
    return digest.hexdigest()


def _ref(root: Path, path: Path, shown=None) -> dict:
    return {
        "path": shown if shown is not None else path.relative_to(root).as_posix(),
        "size": path.stat().st_size,
        "sha256": _sha(path),
    }


def _repo_ref(relative: str) -> dict:
    path = ROOT / relative
    return {"path": relative, "sha256": _sha(path)}


def _build_repaired_reconciliation_case(root: Path, *, slots: int) -> tuple[Path, Path]:
    """Build a real formal repair generation and a five-check reconciliation wrapper."""
    import replay_edges
    import sqd_cache_identity
    import test_sqd_gap_repair as repair_fixture
    from solana_attested_session import SOLANA_MAINNET_GENESIS_HASH
    from scripts.solana import sqd_gap_repair
    from test_batch7_validator_coverage_gaps import _missing_tx

    upper = 19_999
    repair_slots = list(range(upper - slots + 1, upper + 1))
    total_repair = 50 * slots
    zero = replay_edges.ZERO
    base_rows = [
        [1_700_000_000, 10_000, 0, -1, zero, "A", total_repair],
        [1_700_000_001, 10_000, 1, -1, zero, "CurveOwner", 100],
        [1_700_000_002, 10_000, 2, -1, "CurveOwner", "B", 100],
    ]
    case = repair_fixture.build_batch3b_case(root, set(repair_slots), base_rows)
    coverage_pointer = json.loads(
        (case / "data/sqd_coverage/CURRENT.json").read_text(encoding="utf-8"))
    coverage_path = case / coverage_pointer["inputs"]["coverage_map"]["path"]
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    cache_meta_path = next((case / "data").glob("soltx-*.meta.json"))
    cache_meta_doc = json.loads(cache_meta_path.read_text(encoding="utf-8"))
    cache_meta_doc["endpoint_sha256"] = coverage["sqd"]["endpoint_fingerprint"]
    write_json(cache_meta_path, cache_meta_doc)
    responses = {}
    for slot in repair_slots:
        responses.update(repair_fixture.repair_slot_responses(
            sqd_gap_repair, slot, _missing_tx(slot), nonce_count=0,
            missing_first=True))
    transport = repair_fixture.write_repair_fixture(root / "repair-fixture", responses)
    assert sqd_gap_repair.main([
        "repair", "--mint", repair_fixture.MINT, "--case-root", str(case),
        "--transport-fixture", str(transport)]) == 0

    original_history = sqd_cache_identity.historical_producer_hashes

    def admitted_history(script, protocol):
        admitted = set(original_history(script, protocol))
        if script == "scripts/solana/sqd_gap_repair.py":
            admitted.add(_sha(ROOT / script))
        return admitted

    sqd_cache_identity.historical_producer_hashes = admitted_history
    rows, cache_meta, binding = replay_edges.load_edges(
        repair_fixture.MINT, case_root=case)
    balances = {}
    for _ts, _slot, _tx, _instr, source, target, amount in rows:
        if source != zero:
            balances[source] = balances.get(source, 0) - amount
        if target != zero:
            balances[target] = balances.get(target, 0) + amount
    owners = {owner: amount for owner, amount in balances.items() if amount > 0}
    assert not {owner: amount for owner, amount in balances.items() if amount < 0}
    supply = sum(owners.values())
    data = case / "data"
    owners_path = data / "holders_owners.json"
    accounts_path = data / "holders_accounts.json"
    write_json(owners_path, owners)
    write_json(accounts_path, [
        {"account": f"account-{index}", "owner": owner, "amount_raw": amount}
        for index, (owner, amount) in enumerate(sorted(owners.items()))])
    target = {"chain": "solana", "token": repair_fixture.MINT,
              "as_of_block": upper}
    snapshot_path = data / "holders_snapshot_meta.json"
    write_json(snapshot_path, {
        "schema": "solana-holder-snapshot-v2", "mint": repair_fixture.MINT,
        "target": target, "closed": True, "supply_raw": str(supply),
        "outputs": {"holders_owners": _ref(case, owners_path, owners_path.name)},
    })
    try:
        with contextlib.chdir(case):
            assert replay_edges.cmd_reconcile(
                rows, 1, mint=repair_fixture.MINT, cache_meta_path=cache_meta,
                case_root=case, as_of_slot=upper,
                edge_source_binding=binding) is True
    finally:
        sqd_cache_identity.historical_producer_hashes = original_history
    exact_path = data / "reconcile_receipt.json"

    inputs = {}
    for name in ("_supply.json", "_gpa_raw_all.json", "_gpa_raw_all.meta.json"):
        inputs[name] = write_json(data / name, {"fixture": name})
    supply_output = write_json(case / "supply_snapshot.json", {
        "schema": "solana-holder-snapshot/v3", "owners": owners})
    supply_receipt = {
        "schema": "solana-observation-bundle/v1", "target": target,
        "producer": _repo_ref("scripts/solana/scan_token_accounts.py"),
        "mode": "formal", "verdict": "PASS", "exit_code": 0,
        "inputs": {
            "supply_rpc": _ref(case, inputs["_supply.json"],
                               str(inputs["_supply.json"])),
            "gpa_rpc": _ref(case, inputs["_gpa_raw_all.json"],
                            str(inputs["_gpa_raw_all.json"])),
            "gpa_meta": _ref(case, inputs["_gpa_raw_all.meta.json"],
                             str(inputs["_gpa_raw_all.meta.json"])),
        },
        "as_of_slot": upper, "as_of_block": upper,
        "observed_context_slot": upper, "snapshot": {"slot": upper},
        "mint_pre": {"slot": upper - 2, "json_parsed_slot": upper - 1,
                     "raw_sha256": "f" * 64},
        "mint_post": {"slot": upper + 2, "raw_sha256": "f" * 64},
        "supply": {"slot": upper + 3, "amount": str(supply), "decimals": 0,
                   "semantics": "cross-check observation only; not the freeze point"},
        "closure": {"gpa_amount": str(supply), "mint_raw_amount": str(supply),
                    "token_supply_amount": str(supply), "closed": True},
        "attestation": {
            "expected_genesis": SOLANA_MAINNET_GENESIS_HASH,
            "observed_genesis": SOLANA_MAINNET_GENESIS_HASH,
        },
        "activity": {"mode": "complete", "writable_hits": [], "sample_size": 0,
                     "rpc_calls": 3, "complete": True},
        "holder_outputs": {"accounts": _ref(case, accounts_path),
                           "owners": _ref(case, owners_path)},
        "closed": True, "supply_raw": str(supply),
        "sum_accounts_raw": str(supply), "output": _ref(case, supply_output),
    }
    supply_path = write_json(case / "supply_receipt.json", supply_receipt)
    stats_path = write_json(case / "fixture_replay_stats.json", {
        "mint_total_raw": str(supply), "burn_total_raw": "0"})
    replay_ref = _ref(case, stats_path)
    anchor_path = case / "fixture_anchors.jsonl"
    anchor_rows = [
        {"date": f"2026-01-0{day}", "chain": "solana",
         "mint": repair_fixture.MINT, "endpoint": "fixture://solana",
         "as_of_slot": upper, "from_slot": day, "to_slot": day + 10,
         "n_rows": 1, "accounts": {}}
        for day in (1, 2, 3)]
    anchor_path.write_text("".join(json.dumps(row) + "\n" for row in anchor_rows),
                           encoding="utf-8")
    checks = {}
    producers = {
        "supply": "scripts/solana/scan_token_accounts.py",
        "balance": "scripts/solana/anchor_sampler.py",
        "supply_truth": "scripts/lib/supply_truth_gate.py",
        "time": "scripts/solana/anchor_sampler.py",
        "exact_reconcile": "scripts/solana/replay_edges.py",
    }
    for key in ("supply", "balance", "supply_truth", "time"):
        if key == "supply":
            path = supply_path
        elif key in {"balance", "time"}:
            path = write_json(case / f"{key}_receipt.json", {
                "schema": "solana-anchor-sampler-receipt/v2", "target": target,
                "date_range": {"start": "2026-01-01", "end": "2026-01-03"},
                "output": _ref(case, anchor_path),
                "coverage": {"requested_days": 3, "covered_days": 3,
                             "failed_days": 0},
                "failures": [], "verdict": "PASS", "exit_code": 0,
                "producer": _repo_ref(producers[key]), "mode": "formal",
                "inputs": {"config": replay_ref},
            })
        else:
            path = write_json(case / "supply_truth_receipt.json", {
                "schema": "supply-truth-receipt/v3", "target": target,
                "gate": "supply_truth", "chain": "solana",
                "replay_net": str(supply), "onchain_total_supply": str(supply),
                "diff": "0", "diff_bps": 0.0, "tolerance_bps": 10,
                "decision_rule": "primary_form1", "burn_form": None,
                "primary_verdict": "PASS", "sink_reconciliation": None,
                "observed_context_slot": upper + 3,
                "verdict": "PASS", "exit_code": 0,
                "producer": _repo_ref(producers[key]), "mode": "formal",
                "inputs": {"replay_stats": replay_ref,
                           "observation_bundle": _ref(case, supply_path)},
            })
        checks[key] = {"status": "PASS", "exit_code": 0,
                       "receipt": _ref(case, path),
                       "producer": _repo_ref(producers[key])}
    checks["exact_reconcile"] = {
        "status": "PASS", "exit_code": 0,
        "receipt": _ref(case, exact_path),
        "producer": _repo_ref(producers["exact_reconcile"]),
    }
    write_json(case / "reconciliation_report.json", {
        "schema": "reconciliation-report/v3", "family": "solana",
        "target": target,
        "producer": _repo_ref("scripts/report/reconciliation_report.py"),
        "verdict": "PASS", "exit_code": 0, "checks": checks,
    })
    return case, exact_path


def test_f1_only_issued_witness_identity_is_accepted() -> None:
    with tempfile.TemporaryDirectory(prefix="b18r1-f1-", dir="/private/tmp") as raw:
        root = Path(raw)
        build_dynamic_integration_case(root)
        issued = shared.witness_reconciliation_report(root)
        forged_target = dict(issued.target)
        forged_target["as_of_block"] += 1
        direct = shared.DeepReconciliationWitness(
            root=issued.root, report_sha256=issued.report_sha256,
            target=forged_target, receipts={}, frontier_files=issued.frontier_files)
        replaced = dataclasses.replace(issued, target=forged_target)
        value_equal = shared.DeepReconciliationWitness(
            root=issued.root, report_sha256=issued.report_sha256,
            target=copy.deepcopy(issued.target),
            receipts=copy.deepcopy(issued.receipts),
            frontier_files=tuple(issued.frontier_files))

        assert shared.validate_bundle(
            root, reconciliation_provider=lambda: issued) == []
        for forged in (direct, replaced, value_equal):
            assert forged is not issued
            assert shared.validate_bundle(
                root, reconciliation_provider=lambda forged=forged: forged) == INVALID


def test_f2_issued_witness_binds_frontier_files() -> None:
    with tempfile.TemporaryDirectory(prefix="b18r1-f2a-", dir="/private/tmp") as raw:
        root = Path(raw)
        build_dynamic_integration_case(root)
        witness = shared.witness_reconciliation_report(root)
        bound = {path for path, _digest in witness.frontier_files}
        receipt = root / "data/reconcile_receipt.json"
        owners = root / "data/holders_owners.json"
        assert str(receipt.resolve()) in bound and str(owners.resolve()) in bound
        assert shared.validate_bundle(
            root, reconciliation_provider=lambda: witness) == []
        receipt.write_text(receipt.read_text(encoding="utf-8") + "\n",
                           encoding="utf-8")
        assert shared.validate_bundle(
            root, reconciliation_provider=lambda: witness) == INVALID

    with tempfile.TemporaryDirectory(prefix="b18r1-f2b-", dir="/private/tmp") as raw:
        root = Path(raw)
        build_dynamic_integration_case(root)
        witness = shared.witness_reconciliation_report(root)
        cached_accounting = shared.validate_accounting_receipt(root)
        owners = root / "data/holders_owners.json"
        write_json(owners, {"ownersol1": 61, "ownersol2": 39})
        original = shared.validate_accounting_receipt

        def cached(*_args, **_kwargs):
            return cached_accounting

        try:
            shared.validate_accounting_receipt = cached
            errors = shared.validate_bundle(
                root, reconciliation_provider=lambda: witness)
        finally:
            shared.validate_accounting_receipt = original
        assert errors == INVALID, errors


def test_f3_non_object_scans_do_not_truncate_manifest_classification() -> None:
    with tempfile.TemporaryDirectory(prefix="b18r1-f3-", dir="/private/tmp") as raw:
        root = Path(raw)
        make_case(str(root))
        array_rel = "data/x/distribution_scan.json"
        ordinary_rel = "data/x/ordinary.json"
        string_binding_rel = "data/y/distribution_scan.json"
        final_rel = "data/z/distribution_scan.json"
        dump(root / array_rel, [1, 2])
        dump(root / ordinary_rel, {"ordinary": True})
        dump(root / string_binding_rel,
             {"stage": "final", "input_binding": "not-an-object"})
        dump(root / final_rel, {"stage": "final", "input_binding": {
            "handoff_manifest": {"run_id": "A", "sha256": "0" * 64}}})
        data_map = load(root / "data_map.json")
        data_map["files"].extend([
            {"path": array_rel, "source": "test"},
            {"path": ordinary_rel, "source": "test"},
            {"path": string_binding_rel, "source": "test"},
            {"path": final_rel, "source": "test"},
        ])
        dump(root / "data_map.json", data_map)
        proc = generate(root, "b18r1-green")
        assert proc.returncode == 0, proc.stdout + proc.stderr
        paths = artifact_paths(root)
        assert {array_rel, ordinary_rel, string_binding_rel} <= paths, paths
        assert final_rel not in paths, paths
        assert f"跳过反绑产物 {final_rel}" in proc.stderr, proc.stderr


def test_review2_f1_payload_digest_rejects_in_place_mutation() -> None:
    import hashlib
    import json

    for surface in ("target", "receipts"):
        with tempfile.TemporaryDirectory(
                prefix=f"b18r2-f1-{surface}-", dir="/private/tmp") as raw:
            root = Path(raw)
            build_dynamic_integration_case(root)
            witness = shared.witness_reconciliation_report(root)
            canonical = json.dumps(
                (witness.target, witness.receipts), sort_keys=True,
                ensure_ascii=False, separators=(",", ":"))
            assert witness.payload_sha256 == hashlib.sha256(
                canonical.encode("utf-8")).hexdigest()
            assert shared.validate_bundle(
                root, reconciliation_provider=lambda: witness) == []
            if surface == "target":
                witness.target["as_of_block"] += 1
            else:
                receipt = witness.receipts["supply"]
                receipt["supply_raw"] = str(int(receipt["supply_raw"]) + 1)
            assert shared.validate_bundle(
                root, reconciliation_provider=lambda: witness) == INVALID


def test_review2_f2_supply_output_stays_in_mandatory_frontier() -> None:
    import json

    with tempfile.TemporaryDirectory(prefix="b18r2-f2-", dir="/private/tmp") as raw:
        root = Path(raw)
        build_dynamic_integration_case(root)
        witness = shared.witness_reconciliation_report(root)
        observation_ref = witness.receipts["supply_truth"]["inputs"][
            "observation_bundle"]
        bundle_path = (root / observation_ref["path"]).resolve()
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        output_path = (root / bundle["output"]["path"]).resolve()
        bound = {Path(path) for path, _digest in witness.frontier_files}
        assert bundle_path in bound and output_path in bound
        assert len(bound) <= 512
        assert shared.validate_bundle(
            root, reconciliation_provider=lambda: witness) == []
        output_path.write_text(
            output_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        assert shared.validate_bundle(
            root, reconciliation_provider=lambda: witness) == INVALID


def test_review3_r1_real_deep_validation_precedes_frontier_collection() -> None:
    from solana_exact_validate import validate_reconcile_receipt_deep

    with tempfile.TemporaryDirectory(prefix="b18r3-r1-", dir="/private/tmp") as raw:
        root, exact_path = _build_repaired_reconciliation_case(Path(raw), slots=100)
        checked = validate_reconcile_receipt_deep(exact_path, case_root=root)
        assert checked["ok"], checked["reasons"]
        print("RED_PRECONDITION R1 repaired exact-reconcile real deep validation PASS")
        witness = shared.witness_reconciliation_report(root)
        frontier = {Path(path) for path, _digest in witness.frontier_files}
        bundle = json.loads(exact_path.read_text(encoding="utf-8"))["inputs"][
            "repair_bundle"]
        bundle_path = root / bundle["path"]
        manifest = json.loads((bundle_path.parent / json.loads(
            bundle_path.read_text(encoding="utf-8"))["evidence_manifest"]["path"]
        ).read_text(encoding="utf-8"))
        leaves = {bundle_path.parent / row["path"] for row in manifest}
        assert bundle_path.resolve() in frontier
        assert not ({path.resolve() for path in leaves} & frontier)
        assert len(frontier) <= 512


def _replace_check_receipt(root: Path, key: str, path: Path) -> None:
    wrapper_path = root / "reconciliation_report.json"
    wrapper = json.loads(wrapper_path.read_text(encoding="utf-8"))
    wrapper["checks"][key]["receipt"] = _ref(root, path)
    write_json(wrapper_path, wrapper)


def test_review3_r2_r3_frontier_and_wrapper_freshness() -> None:
    with tempfile.TemporaryDirectory(prefix="b18r3-r2-", dir="/private/tmp") as raw:
        root = Path(raw)
        build_dynamic_integration_case(root)
        witness = shared.witness_reconciliation_report(root)
        owners = root / "data/observe_live/holders_owners.json"
        assert owners.resolve() in {Path(path) for path, _ in witness.frontier_files}
        owners.write_text(owners.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        try:
            shared._consume_reconciliation_witness(root, witness)
        except ValueError as exc:
            assert str(exc) == INVALID[0]
        else:
            raise AssertionError("same witness accepted changed first-level owners")

    with tempfile.TemporaryDirectory(prefix="b18r3-r3-wrapper-", dir="/private/tmp") as raw:
        root = Path(raw)
        build_dynamic_integration_case(root)
        witness = shared.witness_reconciliation_report(root)
        wrapper = root / "reconciliation_report.json"
        frontier = {Path(path) for path, _ in witness.frontier_files}
        assert wrapper.resolve() not in frontier
        wrapper.write_text(wrapper.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        try:
            shared._consume_reconciliation_witness(root, witness)
        except ValueError as exc:
            assert str(exc) == INVALID[0]
        else:
            raise AssertionError("report_sha256 did not reject wrapper mutation")

    with tempfile.TemporaryDirectory(prefix="b18r3-r3-frozen-", dir="/private/tmp") as raw:
        root = Path(raw)
        build_dynamic_integration_case(root)
        witness = shared.witness_reconciliation_report(root)
        frozen = root / shared.SOLANA_FROZEN_OBSERVATION_BUNDLE
        assert frozen.resolve() in {Path(path) for path, _ in witness.frontier_files}
        frozen.write_text(frozen.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        try:
            shared._consume_reconciliation_witness(root, witness)
        except ValueError as exc:
            assert str(exc) == INVALID[0]
        else:
            raise AssertionError("same witness accepted changed frozen bundle")


def test_review3_r4_repaired_leaf_boundary_is_explicit() -> None:
    """2026-09-01 decision: first-level frontier, not recursive leaf freshness."""
    with tempfile.TemporaryDirectory(prefix="b18r3-r4-", dir="/private/tmp") as raw:
        root, exact_path = _build_repaired_reconciliation_case(Path(raw), slots=1)
        witness = shared.witness_reconciliation_report(root)
        exact = json.loads(exact_path.read_text(encoding="utf-8"))
        bundle_path = root / exact["inputs"]["repair_bundle"]["path"]
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        manifest_path = bundle_path.parent / bundle["evidence_manifest"]["path"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        leaf = bundle_path.parent / manifest[0]["path"]
        frontier = {Path(path) for path, _ in witness.frontier_files}
        assert bundle_path.resolve() in frontier and leaf.resolve() not in frontier

        original = leaf.read_bytes()
        mutated = bytearray(original)
        mutated[-2] = ord("0") if mutated[-2] != ord("0") else ord("1")
        leaf.write_bytes(mutated)
        # Step 1: the same witness truthfully does not promise recursive leaf freshness.
        assert shared._consume_reconciliation_witness(root, witness) == (
            witness.target, witness.receipts)
        # Step 2: re-issuance reruns real deep validation and must see the changed leaf.
        try:
            shared.witness_reconciliation_report(root)
        except ValueError as exc:
            assert "独立深验失败" in str(exc) or "evidence" in str(exc)
        else:
            raise AssertionError("new witness was issued over a changed evidence leaf")
        # Step 3: changing the first-level bundle binding expires the original witness.
        bundle_path.write_text(bundle_path.read_text(encoding="utf-8") + "\n",
                               encoding="utf-8")
        try:
            shared._consume_reconciliation_witness(root, witness)
        except ValueError as exc:
            assert str(exc) == INVALID[0]
        else:
            raise AssertionError("same witness accepted changed repair bundle")


def test_review3_frontier_resolver_equivalence_and_fail_closed() -> None:
    # gpa_rpc physical parent is the first holder-output search base.
    with tempfile.TemporaryDirectory(prefix="b18r3-resolver-gpa-", dir="/private/tmp") as raw:
        root = Path(raw)
        build_dynamic_integration_case(root)
        wrapper = json.loads((root / "reconciliation_report.json").read_text())
        supply_path = root / wrapper["checks"]["supply"]["receipt"]["path"]
        supply = json.loads(supply_path.read_text(encoding="utf-8"))
        detached = root / "detached-work"
        detached.mkdir()
        old_gpa_ref = supply["inputs"].pop("_gpa_raw_all.json")
        old_gpa = Path(old_gpa_ref["path"])
        new_gpa = detached / "gpa.json"
        new_gpa.write_bytes(old_gpa.read_bytes())
        supply["inputs"]["gpa_rpc"] = _ref(root, new_gpa, str(new_gpa))
        detached_outputs = []
        for name in ("accounts", "owners"):
            old = supply_path.parent / supply["holder_outputs"][name]["path"]
            new = detached / old.name
            new.write_bytes(old.read_bytes())
            supply["holder_outputs"][name] = _ref(root, new, new.name)
            detached_outputs.append(new.resolve())
        write_json(supply_path, supply)
        _replace_check_receipt(root, "supply", supply_path)
        truth_path = root / wrapper["checks"]["supply_truth"]["receipt"]["path"]
        truth = json.loads(truth_path.read_text(encoding="utf-8"))
        truth["inputs"]["observation_bundle"] = _ref(root, supply_path)
        write_json(truth_path, truth)
        _replace_check_receipt(root, "supply_truth", truth_path)
        witness = shared.witness_reconciliation_report(root)
        frontier = {Path(path) for path, _ in witness.frontier_files}
        assert set(detached_outputs) <= frontier

    # Intermediate in-case symlink and /tmp macOS ancestor alias match bound_case_ref.
    with tempfile.TemporaryDirectory(prefix="b18r3-resolver-alias-", dir="/private/tmp") as raw:
        root = Path(raw)
        build_dynamic_integration_case(root)
        real_dir = root / "real-anchor"
        real_dir.mkdir()
        anchor = real_dir / "anchors.jsonl"
        anchor.write_bytes((root / "fixture_anchors.jsonl").read_bytes())
        link_dir = root / "anchor-link"
        link_dir.symlink_to(real_dir, target_is_directory=True)
        for key, shown in (
                ("balance", "anchor-link/anchors.jsonl"),
                ("time", str(anchor).replace("/private/tmp/", "/tmp/", 1))):
            wrapper = json.loads((root / "reconciliation_report.json").read_text())
            receipt_path = root / wrapper["checks"][key]["receipt"]["path"]
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["output"] = _ref(root, anchor, shown)
            write_json(receipt_path, receipt)
            _replace_check_receipt(root, key, receipt_path)
        witness = shared.witness_reconciliation_report(root)
        assert anchor.resolve() in {Path(path) for path, _ in witness.frontier_files}

    # Best-effort fallback binds both root and receipt-parent candidates when distinct.
    with tempfile.TemporaryDirectory(prefix="b18r3-resolver-dual-", dir="/private/tmp") as raw:
        root = Path(raw)
        build_dynamic_integration_case(root)
        wrapper = json.loads((root / "reconciliation_report.json").read_text())
        supply_path = root / wrapper["checks"]["supply"]["receipt"]["path"]
        local_shadow = supply_path.parent / "frontier-shadow.bin"
        root_shadow = root / "frontier-shadow.bin"
        local_shadow.write_bytes(b"receipt-parent")
        root_shadow.write_bytes(b"case-root-different")
        supply = json.loads(supply_path.read_text(encoding="utf-8"))
        supply["frontier_probe"] = _ref(root, local_shadow, local_shadow.name)
        write_json(supply_path, supply)
        _replace_check_receipt(root, "supply", supply_path)
        truth_path = root / wrapper["checks"]["supply_truth"]["receipt"]["path"]
        truth = json.loads(truth_path.read_text(encoding="utf-8"))
        truth["inputs"]["observation_bundle"] = _ref(root, supply_path)
        write_json(truth_path, truth)
        _replace_check_receipt(root, "supply_truth", truth_path)
        witness = shared.witness_reconciliation_report(root)
        frontier = {Path(path) for path, _ in witness.frontier_files}
        assert {local_shadow.resolve(), root_shadow.resolve()} <= frontier

    # Mandatory refs never silently disappear even when the caller already deep-validated.
    with tempfile.TemporaryDirectory(prefix="b18r3-resolver-missing-", dir="/private/tmp") as raw:
        root = Path(raw)
        build_dynamic_integration_case(root)
        target, receipts = shared.validate_reconciliation_report(
            root, return_receipts=True)
        missing = root / "data/observe_live/holders_owners.json"
        missing.unlink()
        try:
            shared._reconciliation_frontier_files(root, target, receipts)
        except ValueError as exc:
            assert "holder_outputs.owners" in str(exc) or "file" in str(exc)
        else:
            raise AssertionError("mandatory missing holder output was skipped")


def _write_edges(path: Path, rows) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row) + "\n")


def _run_closed_audit(root: Path, *, edge_kind: str, mode: str) -> dict:
    import audit_closed_accounts as audit

    edge_path = root / f"{edge_kind}.jsonl.gz"
    if edge_kind == "invalid":
        with gzip.open(edge_path, "wt", encoding="utf-8") as stream:
            stream.write("{bad-json\n")
    elif edge_kind == "empty":
        _write_edges(edge_path, [])
    elif edge_kind != "missing":
        _write_edges(edge_path, [[1, 100, 0, -1, "OWN1", "OWN2", 5]])
    out = root / f"{edge_kind}-{mode}.json"
    argv = [
        "audit_closed_accounts.py", "MINTx", "--edges", str(edge_path),
        "--out", str(out), "--mode", mode, "--interval", "0",
        "--wall-min", "1", "--block-samples", "2", "--sample-inits", "2",
    ]
    clock = [0.0] + [61.0] * 64
    with mock.patch.object(sys, "argv", argv), \
            mock.patch.object(audit.time, "monotonic", side_effect=clock), \
            mock.patch.object(audit.Rpc, "call", return_value=[]), \
            contextlib.redirect_stderr(io.StringIO()):
        try:
            audit.main()
        except SystemExit as exc:
            assert exc.code == 1
    return json.loads(out.read_text(encoding="utf-8"))


def test_review3_f4_five_bails_share_complete_report_contract() -> None:
    cases = (
        ("missing", "blocks", "edges_missing", "边集不存在"),
        ("invalid", "blocks", "edges_invalid", "第 1 行非法"),
        ("empty", "blocks", "edges_empty", "边文件为空"),
        ("valid", "sigs", "signature_discovery", "mint 签名史为空"),
        ("valid", "blocks", "init_discovery", "抽样未命中"),
    )
    expected_sampled = {
        "decoded_txs", "init_events", "alive", "closed", "deep_checked",
        "deep_account_classes", "gma_batch_failed", "wall_truncated",
        "sampling_phase", "counts_complete",
    }
    for index, (edge_kind, mode, phase, direct) in enumerate(cases):
        with tempfile.TemporaryDirectory(
                prefix=f"b18r3-f4-{index}-", dir="/private/tmp") as raw:
            report = _run_closed_audit(Path(raw), edge_kind=edge_kind, mode=mode)
            sampled = report["sampled"]
            assert set(sampled) == expected_sampled
            assert sampled["sampling_phase"] == phase
            assert sampled["counts_complete"] is False
            assert sampled["wall_truncated"] is True
            assert sampled["deep_account_classes"] == {
                "events_found": 0, "all_zero_delta": 0, "fetch_failed": 0}
            reasons = report["invalid_reasons"]
            assert any(direct in reason for reason in reasons), reasons
            assert sum("墙钟" in reason for reason in reasons) == 1, reasons


def test_review4_r1_signature_discovery_bail_preserves_complete() -> None:
    import audit_closed_accounts as audit

    reports = []
    for index, complete in enumerate((True, False)):
        with tempfile.TemporaryDirectory(
                prefix=f"b18r4-r1-{index}-", dir="/private/tmp") as raw, \
                mock.patch.object(
                    audit, "fetch_mint_sigs",
                    return_value=([], complete, False)):
            report = _run_closed_audit(Path(raw), edge_kind="valid", mode="sigs")
            reports.append(report)
            assert report["sampled"]["sampling_phase"] == "signature_discovery"
            assert report["sampled"]["counts_complete"] is False
            assert any(
                "mint 签名史为空/拉取失败" in reason
                for reason in report["invalid_reasons"])

    histories = [report["mint_sig_history"] for report in reports]
    expected = [
        {"total": 0, "complete": True, "in_range": 0},
        {"total": 0, "complete": False, "in_range": 0},
    ]
    assert histories == expected, (
        f"two-state mint_sig_history={histories!r}; expected={expected!r}")
    assert [history["complete"] for history in histories] == [True, False]


def main() -> int:
    tests = [
        test_f1_only_issued_witness_identity_is_accepted,
        test_f2_issued_witness_binds_frontier_files,
        test_f3_non_object_scans_do_not_truncate_manifest_classification,
        test_review2_f1_payload_digest_rejects_in_place_mutation,
        test_review2_f2_supply_output_stays_in_mandatory_frontier,
        test_review3_r1_real_deep_validation_precedes_frontier_collection,
        test_review3_r2_r3_frontier_and_wrapper_freshness,
        test_review3_r4_repaired_leaf_boundary_is_explicit,
        test_review3_frontier_resolver_equivalence_and_fail_closed,
        test_review3_f4_five_bails_share_complete_report_contract,
        test_review4_r1_signature_discovery_bail_preserves_complete,
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
        print(f"FAIL batch18 review digest: {len(failed)}/{len(tests)}")
        return 1
    print(f"PASS batch18 review digest: {len(tests)}/{len(tests)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
