#!/usr/bin/env python3
"""B1-A negative tests for receipt-kernel path identity and recovery."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT / "scripts/lib"))

import receipt_kernel as kernel


PASS = {"schema": "fixture/v1", "verdict": "PASS", "exit_code": 0}
FAIL = {"schema": "fixture/v1", "verdict": "FAIL", "exit_code": 2}


def expect_rejected(call, label):
    try:
        call()
    except kernel.ReceiptKernelError:
        return
    raise AssertionError(f"{label}: unsafe path was accepted")


def invoke(kind, path, peer):
    if kind == "exclusive":
        return kernel.publish_exclusive(path, {"kind": kind})
    if kind == "overwrite":
        return kernel.publish_overwrite(path, {"kind": kind})
    if kind == "txn":
        return kernel.publish_txn(path, {"kind": kind}, peer, {"receipt": True})
    if kind == "restore":
        return kernel.publish_restore_on_fail(path, {"kind": kind})
    if kind == "error":
        return kernel.publish_error_receipt(
            path, {"schema": "fixture/v1"}, "injected", run_id="fixture")
    raise AssertionError(kind)


def test_symlinks(root):
    for kind in ("exclusive", "overwrite", "txn", "restore", "error"):
        case = root / f"final-{kind}"
        case.mkdir()
        outside = root / f"outside-final-{kind}.json"
        bad = case / "artifact.json"
        bad.symlink_to(outside)
        peer = case / "peer.json"
        expect_rejected(lambda k=kind, p=bad, q=peer: invoke(k, p, q),
                        f"{kind} final symlink")
        assert bad.is_symlink() and not outside.exists(), (kind, bad, outside)

        case = root / f"middle-{kind}"
        case.mkdir()
        outside_dir = root / f"outside-middle-{kind}"
        outside_dir.mkdir()
        (case / "link").symlink_to(outside_dir, target_is_directory=True)
        bad = case / "link" / "artifact.json"
        peer = case / "peer.json"
        expect_rejected(lambda k=kind, p=bad, q=peer: invoke(k, p, q),
                        f"{kind} intermediate symlink")
        assert not (outside_dir / "artifact.json").exists(), kind


def test_alias_and_pass_protection(root):
    case = root / "alias"
    case.mkdir()
    same = case / "same.json"
    expect_rejected(lambda: kernel.publish_txn(same, {"data": 1},
                                                same, {"receipt": 1}),
                    "identical data/receipt path")
    assert not same.exists()

    data = case / "data.json"
    receipt = case / "receipt.json"
    data.write_text('{"old":"precious"}\n', encoding="utf-8")
    os.link(data, receipt)
    before = data.read_bytes()
    expect_rejected(lambda: kernel.publish_txn(data, {"new": 1}, receipt, {"new": 2}),
                    "hardlink alias")
    assert data.read_bytes() == before and receipt.read_bytes() == before

    canonical = root / "canonical-pass.json"
    kernel.publish_overwrite(canonical, PASS)
    before = canonical.read_bytes()
    expect_rejected(lambda: kernel.publish_overwrite(canonical, FAIL),
                    "PASS downgrade")
    assert canonical.read_bytes() == before


def test_fail_closed_and_fault_on_fault(root):
    staged_failure = root / "stage-failure.json"
    with mock.patch.object(kernel, "_stage", side_effect=OSError("disk full")):
        try:
            kernel.publish_overwrite(staged_failure, {"new": True})
        except OSError:
            pass
        else:
            raise AssertionError("stage failure was ignored")
    assert not staged_failure.exists()

    case = root / "fault-on-fault"
    case.mkdir()
    data = case / "data.json"
    receipt = case / "receipt.json"
    data.write_text('{"old":"data-precious"}\n', encoding="utf-8")
    receipt.write_text('{"old":"receipt-precious"}\n', encoding="utf-8")
    real_replace = kernel.os.replace
    calls = {"n": 0}

    def fail_publish_and_rollback(src, dst, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 4:
            raise OSError("second publish injected")
        if calls["n"] == 5:
            raise OSError("rollback injected")
        return real_replace(src, dst, *args, **kwargs)

    with mock.patch.object(kernel.os, "replace", side_effect=fail_publish_and_rollback):
        try:
            kernel.publish_txn(data, {"new": 1}, receipt, {"new": 2})
        except kernel.ReceiptKernelError as exc:
            failure = str(exc)
        else:
            raise AssertionError("fault-on-fault was ignored")
    backups = list(case.glob(".*.rollback.*"))
    assert backups and any("precious" in p.read_text(encoding="utf-8") for p in backups)
    assert all(str(p) in failure for p in backups if p.exists())
    assert not any(p.name.startswith(".data.json.tmp") or
                   p.name.startswith(".receipt.json.tmp") for p in case.iterdir())


def main():
    with tempfile.TemporaryDirectory(prefix="batch1-receipt-") as td:
        root = Path(td).resolve()
        test_symlinks(root)
        test_alias_and_pass_protection(root)
        test_fail_closed_and_fault_on_fault(root)
    print("PASS B1-A receipt paths: symlink/alias/rollback/fail-closed/PASS protection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
