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
                ref(meta, registered), "reconcile.inputs.soltx_meta", [data, case])
        except provenance.SeriesProvenanceError as exc:
            raise AssertionError(f"R1 修前真实阻断：{exc}") from exc
        assert got == meta, (got, meta)


def test_n1_dotdot_registered_path_rejected() -> None:
    with tempfile.TemporaryDirectory(prefix="batch16-n1-", dir="/private/tmp") as raw:
        case = Path(raw)
        data = case / "data"
        data.mkdir()
        bad = {"path": "data/../outside.json", "size": 1, "sha256": "0" * 64}
        expect_error(
            lambda: provenance._resolve_ref(bad, "inputs.dotdot", [data, case]),
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
            lambda: provenance._resolve_ref(bad, "inputs.absolute", [data, case]),
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
                ref(meta, registered), "inputs.symlink", [data, case]),
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
            lambda: provenance._resolve_ref(size_ref, "inputs.size", [data, case]),
            "size 不匹配",
        )
        sha_ref = ref(sha_file, "deep/sha.json")
        sha_ref["sha256"] = "0" * 64
        expect_error(
            lambda: provenance._resolve_ref(sha_ref, "inputs.sha", [data, case]),
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
        rows, edge, meta = prepare_complete_case(case)
        old_cwd = Path.cwd()
        try:
            os.chdir(case)
            receipt_path, receipt, _before, _after, result = make_reconcile(
                case, rows, edge, meta, snapshot_slot=1, as_of_slot=1)
        finally:
            os.chdir(old_cwd)
        assert result is True

        deep_meta = (case / "data/sqd_repair" / ("b" * 64) / "gen-x"
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
        original_resolver = provenance.resolve_formal_cache
        provenance.resolve_formal_cache = lambda _mint, _root: (
            edge.resolve(), deep_meta.resolve(), "base", None,
            receipt["edge_source_binding"])
        try:
            got = provenance.registry_anchor_check(
                sidecar, resolved, series, expected_chain="solana",
                expected_mint=MINT, expected_cutoff_slot=1)
        finally:
            provenance.resolve_formal_cache = original_resolver
        assert got == receipt_path


TESTS = [
    ("R1 deep registered path", test_r1_deep_registered_path_resolves_from_case_root),
    ("N1 dotdot", test_n1_dotdot_registered_path_rejected),
    ("N2 absolute", test_n2_absolute_registered_path_rejected),
    ("N3 symlink chain", test_n3_intermediate_symlink_rejected),
    ("N4 size/sha", test_n4_deep_size_and_sha_mismatch_rejected),
    ("N5 basename unchanged", test_n5_basename_precedence_and_mismatch_behavior_unchanged),
    ("N6 registry anchor", test_n6_registry_anchor_accepts_same_deep_meta_as_resolver),
]


def main() -> int:
    selected = TESTS
    if sys.argv[1:] == ["--r1"]:
        selected = TESTS[:1]
    elif sys.argv[1:]:
        raise SystemExit("usage: test_batch16_resolve_ref_case_path.py [--r1]")
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
