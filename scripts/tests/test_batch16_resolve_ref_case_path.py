#!/usr/bin/env python3
"""Batch 16 case-root-relative sidecar reference fallback regressions."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts/solana"), str(ROOT / "scripts/report"),
                str(ROOT / "scripts/lib"), str(ROOT / "scripts/tests")]

import camp_series_provenance as provenance  # noqa: E402
import solana_exact_validate as exact  # noqa: E402
from test_reconcile_v4_receipt import (  # noqa: E402
    MINT,
    make_reconcile,
    prepare_complete_case,
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ref(path: Path, shown: str) -> dict:
    return {"path": shown, "size": path.stat().st_size, "sha256": sha(path)}


def write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def expect_error(call, needle: str) -> str:
    try:
        call()
    except provenance.SeriesProvenanceError as exc:
        detail = str(exc)
        assert needle in detail, detail
        return detail
    raise AssertionError(f"预期拒收但通过，缺少错误关键词 {needle!r}")


def prepare_deep_registry_case(case: Path, marker: str):
    rows, edge, meta = prepare_complete_case(case)
    old_cwd = Path.cwd()
    try:
        os.chdir(case)
        receipt_path, receipt, _before, _after, result = make_reconcile(
            case, rows, edge, meta, snapshot_slot=1, as_of_slot=1)
    finally:
        os.chdir(old_cwd)
    assert result is True

    deep_meta = (case / "data/sqd_repair" / (marker * 64) / "gen-x"
                 / meta.name)
    deep_meta.parent.mkdir(parents=True)
    meta.rename(deep_meta)
    receipt["inputs"]["soltx_meta"] = ref(
        deep_meta, deep_meta.relative_to(case).as_posix())
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    checked = exact.validate_reconcile_receipt_deep(receipt_path, case_root=case)
    assert checked["ok"], checked["reasons"]

    series = write(case / "data/camp_share_series.json", "[]\n")
    sidecar = {"series_format": "sol-rows",
               "edge_source_binding": receipt["edge_source_binding"]}
    resolved = {"inputs.reconcile_receipt": receipt_path}
    return receipt_path, receipt, edge, deep_meta, series, sidecar, resolved


def registry_with_resolver(case_data, *, case_root_marker):
    receipt_path, receipt, edge, deep_meta, series, sidecar, resolved = case_data
    original_resolver = provenance.resolve_formal_cache
    provenance.resolve_formal_cache = lambda _mint, _root: (
        edge.resolve(), deep_meta.resolve(), "base", None,
        receipt["edge_source_binding"])
    try:
        kwargs = {}
        if case_root_marker is not ...:
            kwargs["case_root"] = case_root_marker
        return provenance.registry_anchor_check(
            sidecar, resolved, series, expected_chain="solana",
            expected_mint=MINT, expected_cutoff_slot=1, **kwargs)
    finally:
        provenance.resolve_formal_cache = original_resolver


def test_r1_deep_registered_path_resolves_from_case_root() -> None:
    with tempfile.TemporaryDirectory(prefix="batch16-r1-", dir="/private/tmp") as raw:
        case = Path(raw)
        data = case / "data"
        meta = write(
            data / "sqd_repair" / ("a" * 64) / "gen-x"
            / "soltx-a.repaired.meta.json",
            '{"schema":"sqd-solana-cache/v4"}\n',
        )
        registered = meta.relative_to(case).as_posix()
        try:
            got = provenance._resolve_ref(
                ref(meta, registered), "reconcile.inputs.soltx_meta", [data, case],
                case_root=case)
        except provenance.SeriesProvenanceError as exc:
            raise AssertionError(f"R1 修前真实阻断：{exc}") from exc
        assert got == meta, (got, meta)


def test_r2_cross_case_registered_path_is_rejected() -> None:
    with tempfile.TemporaryDirectory(prefix="batch16-r2-", dir="/private/tmp") as raw:
        parent = Path(raw)
        case_a = parent / "caseA"
        case_a.mkdir()
        write(case_a / "camp_share_series.json", "[]\n")
        sibling = write(parent / "caseB/data/x.json", "sibling-case\n")
        sibling_ref = ref(sibling, "caseB/data/x.json")
        explicit = expect_error(
            lambda: provenance._resolve_ref(
                sibling_ref, "reconcile.inputs.soltx_meta", [case_a, parent],
                case_root=case_a),
            "找不到",
        )
        assert "相对案根" in explicit and str(case_a) in explicit, explicit
        implicit = expect_error(
            lambda: provenance._resolve_ref(
                sibling_ref, "reconcile.inputs.soltx_meta", [case_a, parent]),
            "找不到",
        )
        assert "按登记路径" not in implicit, implicit


def test_r3_resolved_receipt_outside_explicit_case_root_is_rejected_first() -> None:
    with tempfile.TemporaryDirectory(prefix="batch16-r3-", dir="/private/tmp") as raw:
        parent = Path(raw)
        case = parent / "caseA"
        series = write(case / "camp_share_series.json", "[]\n")
        outside_receipt = write(parent / "reconcile_receipt.json", "{}\n")
        provenance.write_series_sidecar(
            series, producer="batch16-r3", series_format="sol-rows",
            denominator="net_supply",
            inputs={"reconcile_receipt": outside_receipt},
        )
        sidecar, _raw, resolved = provenance.load_series_with_sidecar(series)
        assert resolved["inputs.reconcile_receipt"] == outside_receipt
        detail = expect_error(
            lambda: provenance.registry_anchor_check(
                sidecar, resolved, series, expected_chain="solana",
                expected_mint=MINT, expected_cutoff_slot=1, case_root=case),
            "位于案根",
        )
        assert str(outside_receipt) in detail and str(case.resolve()) in detail, detail


def test_r4_basename_search_cannot_escape_explicit_case_root() -> None:
    with tempfile.TemporaryDirectory(prefix="batch16-r4-", dir="/private/tmp") as raw:
        parent = Path(raw)
        case = parent / "caseA"
        case.mkdir()
        outside = write(parent / "holders_owners.json", "outside\n")
        try:
            got = provenance._resolve_ref(
                ref(outside, outside.name), "reconcile.inputs.holders_owners",
                [case, parent], case_root=case)
        except provenance.SeriesProvenanceError as exc:
            detail = str(exc)
            assert "找不到" in detail, detail
        else:
            raise AssertionError(f"R4 修前越出本案：basename 命中父目录文件 {got}")


def test_n1_dotdot_registered_path_rejected() -> None:
    with tempfile.TemporaryDirectory(prefix="batch16-n1-", dir="/private/tmp") as raw:
        case = Path(raw)
        data = case / "data"
        data.mkdir()
        bad = {"path": "data/../outside.json", "size": 1, "sha256": "0" * 64}
        expect_error(
            lambda: provenance._resolve_ref(
                bad, "inputs.dotdot", [data, case], case_root=case),
            "登记路径",
        )


def test_n2_absolute_registered_path_rejected() -> None:
    with tempfile.TemporaryDirectory(prefix="batch16-n2-", dir="/private/tmp") as raw:
        case = Path(raw)
        data = case / "data"
        data.mkdir()
        bad = {"path": "/private/tmp/batch16-absolute.json",
               "size": 1, "sha256": "0" * 64}
        expect_error(
            lambda: provenance._resolve_ref(
                bad, "inputs.absolute", [data, case], case_root=case),
            "登记路径",
        )


def test_n3_intermediate_symlink_rejected() -> None:
    with tempfile.TemporaryDirectory(prefix="batch16-n3-case-", dir="/private/tmp") as raw, \
            tempfile.TemporaryDirectory(prefix="batch16-n3-out-", dir="/private/tmp") as outer:
        case = Path(raw)
        data = case / "data"
        data.mkdir()
        external = Path(outer) / "real-repair"
        meta = write(external / "gen-x" / "soltx-link.meta.json", "linked\n")
        (data / "sqd_repair").symlink_to(external, target_is_directory=True)
        registered = "data/sqd_repair/gen-x/soltx-link.meta.json"
        expect_error(
            lambda: provenance._resolve_ref(
                ref(meta, registered), "inputs.symlink", [data, case],
                case_root=case),
            "符号链接",
        )


def test_n4_deep_size_and_sha_mismatch_rejected() -> None:
    with tempfile.TemporaryDirectory(prefix="batch16-n4-", dir="/private/tmp") as raw:
        case = Path(raw)
        data = case / "data"
        size_file = write(case / "deep" / "size.json", "size\n")
        sha_file = write(case / "deep" / "sha.json", "good\n")
        size_ref = ref(size_file, "deep/size.json")
        size_ref["size"] += 1
        expect_error(
            lambda: provenance._resolve_ref(
                size_ref, "inputs.size", [data, case], case_root=case),
            "size 不匹配",
        )
        sha_ref = ref(sha_file, "deep/sha.json")
        sha_ref["sha256"] = "0" * 64
        expect_error(
            lambda: provenance._resolve_ref(
                sha_ref, "inputs.sha", [data, case], case_root=case),
            "sha256 不匹配",
        )


def test_n5_basename_precedence_and_mismatch_behavior_unchanged() -> None:
    with tempfile.TemporaryDirectory(prefix="batch16-n5-", dir="/private/tmp") as raw:
        case = Path(raw)
        data = case / "data"
        data.mkdir()
        for base, name in ((data, "in-data.json"), (case, "in-root.json")):
            actual = write(base / name, f"{name}\n")
            got = provenance._resolve_ref(
                ref(actual, f"unmaterialized/deep/{name}"),
                f"inputs.{name}", [data, case])
            assert got == actual, (got, actual)

        deep = write(case / "deep" / "shadowed.json", "good")
        write(data / "shadowed.json", "evil")
        expect_error(
            lambda: provenance._resolve_ref(
                ref(deep, "deep/shadowed.json"), "inputs.shadowed", [data, case]),
            "sha256 不匹配",
        )


def test_n6_registry_anchor_accepts_same_deep_meta_as_resolver() -> None:
    with tempfile.TemporaryDirectory(prefix="batch16-n6-", dir="/private/tmp") as raw:
        case = Path(raw)
        case_data = prepare_deep_registry_case(case, "b")
        got = registry_with_resolver(case_data, case_root_marker=case)
        assert got == case_data[0]


def test_n7_registry_anchor_derives_case_root_from_data_receipt() -> None:
    with tempfile.TemporaryDirectory(prefix="batch16-n7-", dir="/private/tmp") as raw:
        case = Path(raw)
        case_data = prepare_deep_registry_case(case, "c")
        got = registry_with_resolver(case_data, case_root_marker=...)
        assert got == case_data[0]


def test_n8_receipt_outside_data_does_not_infer_parent_root() -> None:
    with tempfile.TemporaryDirectory(prefix="batch16-n8-", dir="/private/tmp") as raw:
        parent = Path(raw)
        case = parent / "caseA"
        case_data = list(prepare_deep_registry_case(case, "d"))
        receipt_path, receipt = case_data[:2]
        root_receipt = case / receipt_path.name
        receipt_path.rename(root_receipt)
        sibling = write(parent / "caseB/deep/sibling.meta.json", "sibling\n")
        receipt["inputs"]["soltx_meta"] = ref(
            sibling, "caseB/deep/sibling.meta.json")
        root_receipt.write_text(json.dumps(receipt), encoding="utf-8")
        case_data[0] = root_receipt
        case_data[6] = {"inputs.reconcile_receipt": root_receipt}

        original_deep = exact.validate_reconcile_receipt_deep
        exact.validate_reconcile_receipt_deep = lambda *_args, **_kwargs: {
            "ok": True, "reasons": []}
        try:
            detail = expect_error(
                lambda: registry_with_resolver(
                    tuple(case_data), case_root_marker=...),
                "找不到",
            )
        finally:
            exact.validate_reconcile_receipt_deep = original_deep
        assert "按登记路径" not in detail, detail


def test_n9_explicit_case_root_overrides_inference() -> None:
    with tempfile.TemporaryDirectory(prefix="batch16-n9-", dir="/private/tmp") as raw:
        parent = Path(raw)
        case = parent / "caseA"
        outside = parent / "caseB"
        outside.mkdir()
        case_data = prepare_deep_registry_case(case, "e")
        detail = expect_error(
            lambda: registry_with_resolver(case_data, case_root_marker=outside),
            "找不到",
        )
        assert str(outside) in detail, detail
        got = registry_with_resolver(case_data, case_root_marker=case)
        assert got == case_data[0]


def test_n10_none_root_outside_data_keeps_parent_basename_behavior() -> None:
    with tempfile.TemporaryDirectory(prefix="batch16-n10-", dir="/private/tmp") as raw:
        parent = Path(raw)
        case = parent / "caseA"
        receipt = write(case / "reconcile_receipt.json", "{}\n")
        owners = write(parent / "holders_owners.json", "legacy-parent\n")
        got = provenance._resolve_ref(
            ref(owners, owners.name), "reconcile.inputs.holders_owners",
            [receipt.parent, receipt.parent.parent])
        assert got == owners


def test_n11_inferred_root_rejects_other_resolved_parent_input() -> None:
    with tempfile.TemporaryDirectory(prefix="batch16-n11-", dir="/private/tmp") as raw:
        parent = Path(raw)
        case = parent / "caseA"
        series = write(case / "camp_share_series.json", "[]\n")
        receipt = write(case / "data/reconcile_receipt.json", "{}\n")
        outside = write(parent / "sniper_set.json", "{}\n")
        sidecar = {"series_format": "sol-rows"}
        resolved = {
            "inputs.reconcile_receipt": receipt,
            "inputs.sniper_set": outside,
        }
        detail = expect_error(
            lambda: provenance.registry_anchor_check(
                sidecar, resolved, series, expected_chain="solana",
                expected_mint=MINT, expected_cutoff_slot=1),
            "位于案根",
        )
        assert "inputs.sniper_set" in detail and str(case.resolve()) in detail, detail


def test_n12_evm_explicit_root_ignores_parent_supply_truth() -> None:
    with tempfile.TemporaryDirectory(prefix="batch16-n12-", dir="/private/tmp") as raw:
        parent = Path(raw)
        case = parent / "caseA"
        series = write(case / "camp_share_series.json", "{}\n")
        stats = write(case / "replay_stats.json", "{}\n")
        write(parent / "supply_truth.json", "{}\n")
        sidecar = {
            "series_format": "evm-dict",
            "inputs": {"replay_stats": ref(stats, stats.name)},
        }
        detail = expect_error(
            lambda: provenance.registry_anchor_check(
                sidecar, {"inputs.replay_stats": stats}, series,
                case_root=case),
            "案根内找不到 supply_truth.json",
        )
        assert str(parent / "supply_truth.json") not in detail, detail


TESTS = [
    ("R1 deep registered path", test_r1_deep_registered_path_resolves_from_case_root),
    ("R2 cross-case registered path", test_r2_cross_case_registered_path_is_rejected),
    ("N1 dotdot", test_n1_dotdot_registered_path_rejected),
    ("N2 absolute", test_n2_absolute_registered_path_rejected),
    ("N3 symlink chain", test_n3_intermediate_symlink_rejected),
    ("N4 size/sha", test_n4_deep_size_and_sha_mismatch_rejected),
    ("N5 basename unchanged", test_n5_basename_precedence_and_mismatch_behavior_unchanged),
    ("N6 registry anchor", test_n6_registry_anchor_accepts_same_deep_meta_as_resolver),
    ("N7 registry inferred case root", test_n7_registry_anchor_derives_case_root_from_data_receipt),
    ("N8 root receipt has no inference", test_n8_receipt_outside_data_does_not_infer_parent_root),
    ("N9 explicit case root wins", test_n9_explicit_case_root_overrides_inference),
    ("R3 resolved receipt containment", test_r3_resolved_receipt_outside_explicit_case_root_is_rejected_first),
    ("R4 basename case-root containment", test_r4_basename_search_cannot_escape_explicit_case_root),
    ("N10 None root compatibility", test_n10_none_root_outside_data_keeps_parent_basename_behavior),
    ("N11 inferred root containment", test_n11_inferred_root_rejects_other_resolved_parent_input),
    ("N12 EVM supply truth containment", test_n12_evm_explicit_root_ignores_parent_supply_truth),
]


def main() -> int:
    selected = TESTS
    selectors = {
        "--r1": "R1 ", "--r2": "R2 ", "--r3": "R3 ", "--r4": "R4 ",
        "--n10": "N10 ", "--n11": "N11 ", "--n12": "N12 ",
    }
    if len(sys.argv) == 2 and sys.argv[1] in selectors:
        prefix = selectors[sys.argv[1]]
        selected = [item for item in TESTS if item[0].startswith(prefix)]
    elif sys.argv[1:]:
        raise SystemExit(
            "usage: test_batch16_resolve_ref_case_path.py "
            "[--r1|--r2|--r3|--r4|--n10|--n11|--n12]")
    failed = []
    for name, test in selected:
        try:
            test()
        except Exception as exc:  # noqa: BLE001 - standalone regression runner
            failed.append((name, exc))
            print(f"FAIL {name}: {exc}")
    if failed:
        print(f"FAIL batch16 resolve_ref case path: {len(failed)}/{len(selected)}")
        return 1
    print(f"PASS batch16 resolve_ref case path: {len(selected)}/{len(selected)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
