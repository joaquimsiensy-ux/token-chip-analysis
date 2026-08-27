#!/usr/bin/env python3
"""Batch 14 Solana accounting observation-bundle content fallback guards."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts/report"), str(ROOT / "scripts/lib"),
                str(ROOT / "scripts/tests")]

import shared_release_receipt as shared  # noqa: E402
from test_batch11_frozen_bundle_binding import (  # noqa: E402
    FROZEN_BUNDLE,
    FROZEN_SLOT,
    LIVE_SLOT,
    MINT,
    build_bundle,
    write_json,
)
from test_evm_observation_release import build_case as build_evm_case  # noqa: E402


LIVE_BUNDLE = "data/solana_observation_bundle.json"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def repo_ref(rel: str) -> dict:
    path = ROOT / rel
    return {"path": rel, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def accounting_ref(root: Path, frozen_bytes: bytes) -> dict:
    return {
        "path": LIVE_BUNDLE,
        "size": len(frozen_bytes),
        "sha256": sha_bytes(frozen_bytes),
    }


def build_case(root: Path, *, static: bool = False) -> dict:
    frozen_path, _ = build_bundle(
        root, "data", FROZEN_SLOT,
        {"owner-a": 60, "owner-b": 40}, FROZEN_BUNDLE)
    frozen_bytes = frozen_path.read_bytes()
    live_path, _ = build_bundle(
        root, "data/live_inputs", LIVE_SLOT,
        {"owner-a": 70, "owner-b": 20, "owner-c": 10}, LIVE_BUNDLE)
    if static:
        live_path.write_bytes(frozen_bytes)
    else:
        # Keep the live JSON valid while making R1 deterministically exercise
        # the size-mismatch branch before the frozen-content fallback.
        live_path.write_bytes(live_path.read_bytes() + b"\n")
        if live_path.stat().st_size == len(frozen_bytes):
            live_path.write_bytes(live_path.read_bytes() + b" ")
    accounting = {
        "schema": "accounting-gate/v1",
        "chain": "solana",
        "mint": MINT,
        "producer": repo_ref("scripts/solana/accounting_gate_sol.py"),
        "execution_mode": "formal",
        "checks": {"owner_program": "spl-token"},
        "verdict": "PASS",
        "exit_code": 0,
        "as_of_block": FROZEN_SLOT,
        "observed_context_slot": FROZEN_SLOT,
        "observation_bundle": accounting_ref(root, frozen_bytes),
    }
    write_json(root / "accounting_mode.json", accounting)
    return {
        "target": {"chain": "solana", "token": MINT,
                   "as_of_block": FROZEN_SLOT},
        "accounting": accounting,
        "frozen_path": frozen_path,
        "frozen_bytes": frozen_bytes,
        "live_path": live_path,
    }


def validate(root: Path, fixture: dict):
    return shared.validate_accounting_receipt(
        root, accounting=fixture["accounting"],
        expected_target=fixture["target"])


def expect_reject(call, needle: str) -> str:
    try:
        call()
    except ValueError as exc:
        assert needle in str(exc), str(exc)
        return str(exc)
    raise AssertionError(f"expected rejection containing {needle!r}")


def test_r1_g1_size_mismatch_uses_frozen_bundle() -> None:
    with tempfile.TemporaryDirectory(prefix="batch14-r1-", dir="/private/tmp") as raw:
        root = Path(raw)
        fixture = build_case(root)
        assert fixture["live_path"].stat().st_size != len(fixture["frozen_bytes"])
        target, _accounting, bundle_sha = validate(root, fixture)
        assert target == shared.canonical_target(fixture["target"])
        assert bundle_sha == sha_bytes(fixture["frozen_bytes"])


def test_g1_sha_mismatch_uses_frozen_bundle() -> None:
    with tempfile.TemporaryDirectory(prefix="batch14-g1-sha-", dir="/private/tmp") as raw:
        root = Path(raw)
        fixture = build_case(root)
        live_bytes = bytearray(fixture["frozen_bytes"])
        live_bytes[-2] = ord(" ") if live_bytes[-2] != ord(" ") else ord("\t")
        fixture["live_path"].write_bytes(bytes(live_bytes))
        assert fixture["live_path"].stat().st_size == len(fixture["frozen_bytes"])
        assert sha_bytes(fixture["live_path"].read_bytes()) \
            != sha_bytes(fixture["frozen_bytes"])
        _target, _accounting, bundle_sha = validate(root, fixture)
        assert bundle_sha == sha_bytes(fixture["frozen_bytes"])


def test_g1_fallback_still_runs_bundle_deep_validation() -> None:
    with tempfile.TemporaryDirectory(prefix="batch14-g1-deep-", dir="/private/tmp") as raw:
        root = Path(raw)
        fixture = build_case(root)
        frozen = json.loads(fixture["frozen_path"].read_text(encoding="utf-8"))
        frozen["attestation"]["observed_genesis"] = "wrong-genesis"
        write_json(fixture["frozen_path"], frozen)
        changed = fixture["frozen_path"].read_bytes()
        fixture["accounting"]["observation_bundle"] = accounting_ref(root, changed)
        expect_reject(lambda: validate(root, fixture), "genesis attestation invalid")


def test_n1_changed_frozen_bundle_rethrows_original_error() -> None:
    with tempfile.TemporaryDirectory(prefix="batch14-n1-", dir="/private/tmp") as raw:
        root = Path(raw)
        fixture = build_case(root)
        fixture["frozen_path"].write_bytes(fixture["frozen_bytes"] + b"\n")
        error = expect_reject(lambda: validate(root, fixture),
                              "solana accounting observation bundle size mismatch")
        assert "frozen" not in error.lower()


def test_n2_missing_frozen_bundle_rethrows_original_error() -> None:
    with tempfile.TemporaryDirectory(prefix="batch14-n2-", dir="/private/tmp") as raw:
        root = Path(raw)
        fixture = build_case(root)
        fixture["frozen_path"].unlink()
        expect_reject(lambda: validate(root, fixture),
                      "solana accounting observation bundle size mismatch")


def test_n3_path_escape_never_uses_fallback() -> None:
    with tempfile.TemporaryDirectory(prefix="batch14-n3-escape-", dir="/private/tmp") as raw:
        root = Path(raw)
        fixture = build_case(root)
        fixture["accounting"]["observation_bundle"]["path"] = "../escape.json"
        expect_reject(lambda: validate(root, fixture),
                      "path must be a safe contained path")


def test_n3_symlink_never_uses_fallback() -> None:
    with tempfile.TemporaryDirectory(prefix="batch14-n3-symlink-", dir="/private/tmp") as raw:
        root = Path(raw)
        fixture = build_case(root)
        link = root / "data/accounting-link.json"
        link.symlink_to(fixture["live_path"])
        fixture["accounting"]["observation_bundle"]["path"] = \
            "data/accounting-link.json"
        expect_reject(lambda: validate(root, fixture), "path is a symlink")


def test_n4_static_solana_is_unchanged() -> None:
    with tempfile.TemporaryDirectory(prefix="batch14-static-", dir="/private/tmp") as raw:
        root = Path(raw)
        fixture = build_case(root, static=True)
        _target, _accounting, bundle_sha = validate(root, fixture)
        assert bundle_sha == sha_bytes(fixture["live_path"].read_bytes())


def test_n4_evm_is_unchanged() -> None:
    with tempfile.TemporaryDirectory(prefix="batch14-evm-", dir="/private/tmp") as raw:
        root = Path(raw)
        fixture = build_evm_case(root)
        target, _accounting, bundle_sha = shared.validate_accounting_receipt(
            root, expected_target=fixture["target"])
        assert target == shared.canonical_target(fixture["target"])
        assert bundle_sha == shared.sha(root / "evm_observation_bundle.json")


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv not in ([], ["--r1"]):
        raise SystemExit(
            "usage: test_batch14_accounting_bundle_fallback.py [--r1]")
    tests = [test_r1_g1_size_mismatch_uses_frozen_bundle]
    if not argv:
        tests += [
            test_g1_sha_mismatch_uses_frozen_bundle,
            test_g1_fallback_still_runs_bundle_deep_validation,
            test_n1_changed_frozen_bundle_rethrows_original_error,
            test_n2_missing_frozen_bundle_rethrows_original_error,
            test_n3_path_escape_never_uses_fallback,
            test_n3_symlink_never_uses_fallback,
            test_n4_static_solana_is_unchanged,
            test_n4_evm_is_unchanged,
        ]
    failed = []
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}")
        except Exception as exc:
            failed.append(test.__name__)
            print(f"FAIL {test.__name__}: {type(exc).__name__}: {exc}")
    print(f"batch14 tests={len(tests)} failed={len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
