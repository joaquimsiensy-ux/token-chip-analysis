#!/usr/bin/env python3
"""Golden envelope plus fault injection for the small receipt kernel."""
from __future__ import annotations

import json
import multiprocessing
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT / "scripts/lib"))

import receipt_kernel as kernel
import receipt_validate as validator


@contextmanager
def pushd(path):
    old = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


def envelope(root, *, target=None):
    evidence = root / "evidence.json"
    evidence.write_text('{"ok":true}\n', encoding="utf-8")
    return kernel.build_envelope(
        "fixture-receipt/v1",
        target or {"chain": "bsc", "token": "0xtoken", "as_of_block": 123},
        __file__, "formal", inputs={"evidence": evidence},
    )


def concurrent_writer(path, payload, queue):
    try:
        kernel.publish_exclusive(path, payload)
        queue.put("PASS")
    except Exception as exc:
        queue.put(type(exc).__name__)


def rework_counterexamples(root, env):
    """Fable boundary attacks: collect all four failures before asserting."""
    failures = []

    for label, fields in (
            ("reserved producer", {"producer": {"path": "forged", "sha256": "0" * 64}}),
            ("reserved inputs", {"inputs": ["raw-list"]})):
        try:
            kernel.finalize_envelope(env, "PASS", 0, **fields)
        except kernel.ReceiptKernelError:
            pass
        else:
            failures.append(f"{label} override was accepted")

    restore_dir = root / "rework-restore"; restore_dir.mkdir()
    restore_out = restore_dir / "formal.json"
    restore_out.write_text('{"old":"restore-precious"}\n', encoding="utf-8")
    real_replace = kernel.os.replace
    restore_calls = {"n": 0}

    def fail_restore_rollback(src, dst, *args, **kwargs):
        restore_calls["n"] += 1
        if restore_calls["n"] == 3:
            raise OSError("restore rollback injected")
        return real_replace(src, dst, *args, **kwargs)

    restore_exc = None
    with mock.patch.object(kernel.os, "replace", side_effect=fail_restore_rollback):
        try:
            kernel.publish_restore_on_fail(
                restore_out, {"new": "bad"}, validate=lambda _: False)
        except BaseException as exc:
            restore_exc = exc
    restore_backups = list(restore_dir.glob(".formal.json.rollback.*"))
    if (restore_exc is None or not restore_backups
            or not any("restore-precious" in path.read_text(encoding="utf-8")
                       for path in restore_backups)
            or not any(str(path) in str(restore_exc) for path in restore_backups)):
        failures.append("restore rollback failure did not preserve/name the old backup")

    txn_dir = root / "rework-txn"; txn_dir.mkdir()
    data = txn_dir / "data.json"; receipt = txn_dir / "receipt.json"
    data.write_text('{"old":"data-precious"}\n', encoding="utf-8")
    receipt.write_text('{"old":"receipt-precious"}\n', encoding="utf-8")
    txn_calls = {"n": 0}

    def fail_txn_publish_and_rollback(src, dst, *args, **kwargs):
        txn_calls["n"] += 1
        if txn_calls["n"] == 4:
            raise OSError("second publish injected")
        if txn_calls["n"] == 5:
            raise OSError("first rollback injected")
        return real_replace(src, dst, *args, **kwargs)

    txn_exc = None
    with mock.patch.object(kernel.os, "replace", side_effect=fail_txn_publish_and_rollback):
        try:
            kernel.publish_txn(data, {"new": 1}, receipt, {"new": 2})
        except BaseException as exc:
            txn_exc = exc
    txn_backups = list(txn_dir.glob(".*.rollback.*"))
    if (txn_exc is None or not txn_backups
            or not any("precious" in path.read_text(encoding="utf-8") for path in txn_backups)
            or not any(str(path) in str(txn_exc) for path in txn_backups)):
        failures.append("txn rollback failure did not preserve/name a recoverable backup")

    assert not failures, "rework counterexamples still vulnerable: " + "; ".join(failures)


def main():
    with tempfile.TemporaryDirectory(prefix="receipt-kernel-") as td:
        root = Path(td).resolve()

        # Golden fixture: emitter output must pass the separately implemented validator.
        env = envelope(root)
        good = kernel.finalize_envelope(env, "PASS", 0, observation={"value": 1})
        golden = root / "golden.json"
        kernel.publish_exclusive(golden, good)
        assert validator.validate_receipt(json.loads(golden.read_text())) == []
        tampered_producer = dict(good, producer={**good["producer"], "sha256": "0" * 64})
        assert "producer hash mismatch" in validator.validate_receipt(tampered_producer)
        contradictory = dict(good, exit_code=2)
        assert "verdict/exit_code inconsistent" in validator.validate_receipt(contradictory)
        rework_counterexamples(root, env)

        # Missing and empty target members are rejected by both sides.
        for bad in ({"chain": "bsc", "token": "0xtoken"},
                    {"chain": "bsc", "token": "", "as_of_block": 123}):
            try:
                envelope(root, target=bad)
            except kernel.ReceiptKernelError:
                pass
            else:
                raise AssertionError(f"bad target accepted: {bad}")
        invalid = dict(good, target={"chain": "bsc", "token": "0xtoken"})
        assert any("as_of_block" in item for item in validator.validate_receipt(invalid))

        # Input mutation after hashing invalidates the independent recomputation.
        (root / "evidence.json").write_text('{"ok":false}\n', encoding="utf-8")
        assert any("input evidence" in item and "mismatch" in item
                   for item in validator.validate_receipt(good))
        env = envelope(root)
        good = kernel.finalize_envelope(env, "PASS", 0)

        # Disk-full style staging failure must leave no formal artifact.
        disk_out = root / "disk-full.json"
        with mock.patch.object(kernel, "_stage", side_effect=OSError("disk full")):
            try:
                kernel.publish_overwrite(disk_out, good)
            except OSError:
                pass
            else:
                raise AssertionError("disk-full injection did not fail")
        assert not disk_out.exists()

        # Two processes racing an exclusive publish: exactly one wins.
        race = root / "race.json"
        ctx = multiprocessing.get_context("fork")
        queue = ctx.Queue()
        workers = [ctx.Process(target=concurrent_writer, args=(race, good, queue))
                   for _ in range(2)]
        for proc in workers: proc.start()
        for proc in workers: proc.join(10)
        results = [queue.get(timeout=2) for _ in workers]
        assert results.count("PASS") == 1 and results.count("ReceiptKernelError") == 1, results

        # ERROR is always a unique side receipt and cannot overwrite an old PASS.
        canonical = root / "canonical.json"
        kernel.publish_exclusive(canonical, good)
        before = canonical.read_bytes()
        error_path = kernel.publish_error_receipt(canonical, env, "injected", run_id="fixed")
        assert canonical.read_bytes() == before
        assert error_path.name == "canonical.error.fixed.json" and error_path.exists()
        assert json.loads(error_path.read_text())["verdict"] == "ERROR"

        # Relative traversal and a final symlink are both rejected.
        child = root / "child"; child.mkdir()
        outside = root / "outside.json"; outside.write_text("{}\n", encoding="utf-8")
        link = child / "link.json"; link.symlink_to(outside)
        with pushd(child):
            for shown in ("../outside.json", "link.json"):
                try:
                    kernel.build_envelope("fixture/v1",
                        {"chain": "bsc", "token": "x", "as_of_block": 1},
                        __file__, "formal", inputs={"x": shown})
                except kernel.ReceiptKernelError:
                    pass
                else:
                    raise AssertionError(f"unsafe input accepted: {shown}")

        # Failure on the second replace rolls both transaction members back.
        data = root / "data.json"; receipt = root / "txn-receipt.json"
        data.write_text('{"old":"data"}\n', encoding="utf-8")
        receipt.write_text('{"old":"receipt"}\n', encoding="utf-8")
        old_data, old_receipt = data.read_bytes(), receipt.read_bytes()
        real_replace = kernel.os.replace
        state = {"failed": False}
        def fail_second(src, dst, *args, **kwargs):
            dst_path = (receipt.parent / dst) if kwargs.get("dst_dir_fd") is not None else Path(dst)
            if dst_path.resolve() == receipt.resolve() and not state["failed"]:
                state["failed"] = True
                raise OSError("second replace injected")
            return real_replace(src, dst, *args, **kwargs)
        with mock.patch.object(kernel.os, "replace", side_effect=fail_second):
            try:
                kernel.publish_txn(data, {"new": "data"}, receipt, {"new": "receipt"})
            except OSError:
                pass
            else:
                raise AssertionError("dual-file transaction failure was ignored")
        assert data.read_bytes() == old_data and receipt.read_bytes() == old_receipt

        # Post-publish validation failure restores the prior formal artifact.
        restore = root / "restore.json"; restore.write_text('{"old":true}\n', encoding="utf-8")
        old_restore = restore.read_bytes()
        try:
            kernel.publish_restore_on_fail(restore, {"new": True}, validate=lambda _: False)
        except kernel.ReceiptKernelError:
            pass
        else:
            raise AssertionError("restore-on-fail validation failure was ignored")
        assert restore.read_bytes() == old_restore

    print("PASS receipt kernel: golden + target/hash/disk/concurrency/error/path/txn/restore faults")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
