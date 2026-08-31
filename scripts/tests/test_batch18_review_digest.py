#!/usr/bin/env python3
"""Batch 18 blind-review digest: witness anti-forgery and classifier defense."""
from __future__ import annotations

import copy
import dataclasses
import sys
import tempfile
from pathlib import Path


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


def test_f1_only_issued_witness_identity_is_accepted() -> None:
    with tempfile.TemporaryDirectory(prefix="b18r1-f1-", dir="/private/tmp") as raw:
        root = Path(raw)
        build_dynamic_integration_case(root)
        issued = shared.witness_reconciliation_report(root)
        forged_target = dict(issued.target)
        forged_target["as_of_block"] += 1
        direct = shared.DeepReconciliationWitness(
            root=issued.root, report_sha256=issued.report_sha256,
            target=forged_target, receipts={}, bound_files=issued.bound_files)
        replaced = dataclasses.replace(issued, target=forged_target)
        value_equal = shared.DeepReconciliationWitness(
            root=issued.root, report_sha256=issued.report_sha256,
            target=copy.deepcopy(issued.target),
            receipts=copy.deepcopy(issued.receipts),
            bound_files=tuple(issued.bound_files))

        assert shared.validate_bundle(
            root, reconciliation_provider=lambda: issued) == []
        for forged in (direct, replaced, value_equal):
            assert forged is not issued
            assert shared.validate_bundle(
                root, reconciliation_provider=lambda forged=forged: forged) == INVALID


def test_f2_issued_witness_binds_deep_file_closure() -> None:
    with tempfile.TemporaryDirectory(prefix="b18r1-f2a-", dir="/private/tmp") as raw:
        root = Path(raw)
        build_dynamic_integration_case(root)
        witness = shared.witness_reconciliation_report(root)
        bound = {path for path, _digest in witness.bound_files}
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


def main() -> int:
    tests = [
        test_f1_only_issued_witness_identity_is_accepted,
        test_f2_issued_witness_binds_deep_file_closure,
        test_f3_non_object_scans_do_not_truncate_manifest_classification,
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
