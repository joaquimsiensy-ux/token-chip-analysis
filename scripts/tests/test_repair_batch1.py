#!/usr/bin/env python3
"""v6.41.0 repair batch 1 regression tests.

Sections are appended as the approved repair steps are implemented.  This first
section covers RV-07: a real FAIL must supersede an old PASS receipt without
weakening the ordinary PASS-downgrade guard.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [
    str(ROOT / "scripts/lib"),
    str(ROOT / "scripts/evm"),
    str(ROOT / "scripts/solana"),
    str(ROOT / "scripts/tests"),
]

import supply_truth_gate as supply  # noqa: E402
import receipt_kernel as kernel  # noqa: E402
from test_repair_batch_a import SupplyPool, TOKEN  # noqa: E402


@contextlib.contextmanager
def chdir(path: Path):
    old = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


# -------------------------------------------------------------------- RV-07

def _run_supply(root: Path, mint: int, onchain: int):
    stats = root / "replay_stats.json"
    stats.write_text(
        json.dumps({"mint_total_raw": str(mint), "burn_total_raw": "0"}),
        encoding="utf-8",
    )
    out = root / "supply_truth.json"
    argv = [
        "--chain", "eth", "--token", TOKEN, "--as-of-block", "123",
        "--rpc", "offline://fixture", "--tolerance-bps", "10",
        "--replay-stats", stats.name, "--out", str(out),
    ]
    stderr = io.StringIO()
    with chdir(root), mock.patch.object(
            supply, "attested_rpc_pool", return_value=SupplyPool(onchain)), \
            contextlib.redirect_stderr(stderr):
        rc = supply.main(argv)
    return rc, stderr.getvalue()


def test_rv07_original_counterexample(root: Path):
    """Old PASS + real FAIL must become exit 2 + canonical FAIL + PASS archive."""
    root.mkdir(parents=True, exist_ok=True)
    out = root / "supply_truth.json"
    rc_pass, _ = _run_supply(root, mint=100, onchain=100)
    assert rc_pass == 0, (rc_pass, _)
    old_bytes = out.read_bytes()

    # Re-enable the legacy publication path on the fixed tree.  This is the
    # approved equivalent injection proving the old exit-1/deadlock behavior.
    with mock.patch.object(
            supply, "publish_supersede",
            side_effect=lambda path, payload, **_: kernel.publish_overwrite(path, payload)):
        legacy_rc, legacy_stderr = _run_supply(root, mint=1, onchain=100)
    legacy_current = json.loads(out.read_text(encoding="utf-8"))
    legacy_archives = list(root.glob("supply_truth.json.superseded-*"))
    assert legacy_rc == 1 and legacy_current["verdict"] == "PASS"
    assert legacy_archives == [] and "cannot be downgraded" in legacy_stderr
    print("RV07 LEGACY_INJECTION rc=1 canonical=PASS archives=0 "
          "error=existing_PASS_cannot_be_downgraded")

    rc_fail, stderr = _run_supply(root, mint=1, onchain=100)
    current = json.loads(out.read_text(encoding="utf-8"))
    archived = list(root.glob("supply_truth.json.superseded-*"))
    assert rc_fail == 2, (rc_fail, stderr)
    assert current["verdict"] == "FAIL", current
    assert len(archived) == 1 and archived[0].read_bytes() == old_bytes, archived
    print("RV07 FIXED rc=2 canonical=FAIL archives=1 archived_verdict=PASS")


def _payload(root: Path, verdict: str, *, schema="fixture-receipt/v1", target=None):
    root.mkdir(parents=True, exist_ok=True)
    env = kernel.build_envelope(
        schema,
        target or {"chain": "eth", "token": TOKEN, "as_of_block": 123},
        __file__,
        "formal",
    )
    return kernel.finalize_envelope(
        env, verdict, 0 if verdict == "PASS" else 2, observation={"value": verdict})


def _expect_error(fn, needle=None):
    try:
        fn()
    except BaseException as exc:
        if needle is not None:
            assert needle in str(exc), exc
        return exc
    raise AssertionError("expected fail-closed exception")


def test_rv07_payload_and_stage_failures(root: Path):
    case = root / "payload-stage"
    canonical = case / "receipt.json"
    passed = _payload(case, "PASS")
    failed = _payload(case, "FAIL")
    kernel.publish_overwrite(canonical, passed)
    before = canonical.read_bytes()

    _expect_error(lambda: kernel.publish_supersede(
        canonical, passed, schema_family="fixture-receipt/"), "FAIL/2")
    inconsistent = dict(failed, exit_code=1)
    _expect_error(lambda: kernel.publish_supersede(
        canonical, inconsistent, schema_family="fixture-receipt/"), "FAIL/2")
    with mock.patch.object(kernel, "_stage", side_effect=OSError("stage injected")):
        _expect_error(lambda: kernel.publish_supersede(
            canonical, failed, schema_family="fixture-receipt/"), "stage injected")
    assert canonical.read_bytes() == before
    assert list(case.glob("receipt.json.superseded-*")) == []


def test_rv07_link_replace_and_rollback_failures(root: Path):
    # 1) archive hard-link failure leaves the PASS canonical untouched.
    link_case = root / "link-failure"
    link_out = link_case / "receipt.json"
    passed = _payload(link_case, "PASS")
    failed = _payload(link_case, "FAIL")
    kernel.publish_overwrite(link_out, passed)
    before = link_out.read_bytes()
    with mock.patch.object(kernel.os, "link", side_effect=OSError("link injected")):
        _expect_error(lambda: kernel.publish_supersede(
            link_out, failed, schema_family="fixture-receipt/"), "link injected")
    assert link_out.read_bytes() == before
    assert list(link_case.glob("receipt.json.superseded-*")) == []

    # 2) replacement failure removes the just-created archive link.
    replace_case = root / "replace-failure"
    replace_out = replace_case / "receipt.json"
    passed = _payload(replace_case, "PASS")
    failed = _payload(replace_case, "FAIL")
    kernel.publish_overwrite(replace_out, passed)
    before = replace_out.read_bytes()
    with mock.patch.object(kernel.os, "replace", side_effect=OSError("replace injected")):
        _expect_error(lambda: kernel.publish_supersede(
            replace_out, failed, schema_family="fixture-receipt/"), "replace injected")
    assert replace_out.read_bytes() == before
    assert list(replace_case.glob("receipt.json.superseded-*")) == []

    # 3) if archive-link rollback itself fails, both the old canonical and the
    # recoverable archive are preserved and named in the raised error.
    rollback_case = root / "rollback-failure"
    rollback_out = rollback_case / "receipt.json"
    passed = _payload(rollback_case, "PASS")
    failed = _payload(rollback_case, "FAIL")
    kernel.publish_overwrite(rollback_out, passed)
    before = rollback_out.read_bytes()
    real_unlink = kernel._unlink_at

    def fail_archive_unlink(target, name):
        if ".superseded-" in name:
            raise OSError("rollback injected")
        return real_unlink(target, name)

    with mock.patch.object(kernel.os, "replace", side_effect=OSError("replace injected")), \
            mock.patch.object(kernel, "_unlink_at", side_effect=fail_archive_unlink):
        exc = _expect_error(lambda: kernel.publish_supersede(
            rollback_out, failed, schema_family="fixture-receipt/"), "rollback also failed")
    archives = list(rollback_case.glob("receipt.json.superseded-*"))
    assert rollback_out.read_bytes() == before and len(archives) == 1
    assert archives[0].read_bytes() == before and str(archives[0]) in str(exc)


def test_rv07_collision_cycle_and_identity(root: Path):
    # 4) archive-name collision is a hard failure, never an overwrite.
    collision = root / "collision"
    collision_out = collision / "receipt.json"
    passed = _payload(collision, "PASS")
    failed = _payload(collision, "FAIL")
    kernel.publish_overwrite(collision_out, passed)
    before = collision_out.read_bytes()
    occupied = collision / "receipt.json.superseded-fixed"
    occupied.write_text("occupied\n", encoding="utf-8")
    with mock.patch.object(kernel, "_run_id", return_value="fixed"):
        _expect_error(lambda: kernel.publish_supersede(
            collision_out, failed, schema_family="fixture-receipt/"), "already exists")
    assert collision_out.read_bytes() == before and occupied.read_text() == "occupied\n"

    # 5) rapid PASS→FAIL→PASS→FAIL uses run-id uniqueness and keeps both PASSes.
    cycle = root / "cycle"
    cycle_out = cycle / "receipt.json"
    pass1 = _payload(cycle, "PASS")
    fail1 = _payload(cycle, "FAIL")
    kernel.publish_overwrite(cycle_out, pass1)
    first_inode = cycle_out.stat().st_ino
    kernel.publish_supersede(cycle_out, fail1, schema_family="fixture-receipt/")
    first_archive = list(cycle.glob("receipt.json.superseded-*"))[0]
    assert first_archive.stat().st_ino == first_inode
    pass2 = {**pass1, "observation": {"value": "PASS-2"}}
    kernel.publish_overwrite(cycle_out, pass2)
    fail2 = {**fail1, "observation": {"value": "FAIL-2"}}
    kernel.publish_supersede(cycle_out, fail2, schema_family="fixture-receipt/")
    archives = sorted(cycle.glob("receipt.json.superseded-*"))
    assert len(archives) == 2
    assert [json.loads(path.read_text())["verdict"] for path in archives] == ["PASS", "PASS"]
    assert json.loads(cycle_out.read_text())["observation"]["value"] == "FAIL-2"

    # 6/7) target or schema-family mismatch cannot archive or alter the old PASS.
    for label, old_schema, new_target in (
            ("target", "fixture-receipt/v1",
             {"chain": "eth", "token": TOKEN, "as_of_block": 124}),
            ("schema", "other-receipt/v1", None)):
        case = root / f"mismatch-{label}"
        out = case / "receipt.json"
        old = _payload(case, "PASS", schema=old_schema)
        new = _payload(case, "FAIL", target=new_target)
        kernel.publish_overwrite(out, old)
        before = out.read_bytes()
        _expect_error(lambda: kernel.publish_supersede(
            out, new, schema_family="fixture-receipt/"))
        assert out.read_bytes() == before
        assert list(case.glob("receipt.json.superseded-*")) == []


def test_rv07_concurrency_and_ordinary_guard(root: Path):
    case = root / "concurrency"
    out = case / "receipt.json"
    passed = _payload(case, "PASS")
    failed = _payload(case, "FAIL")
    kernel.publish_overwrite(out, passed)
    before = out.read_bytes()
    lock = case / ".receipt.json.supersede.lock"
    lock.write_text("held\n", encoding="utf-8")
    _expect_error(lambda: kernel.publish_supersede(
        out, failed, schema_family="fixture-receipt/"), "concurrent")
    assert out.read_bytes() == before and list(case.glob("receipt.json.superseded-*")) == []
    lock.unlink()

    # Keep-red proof: ordinary overwrite still rejects an unarchived downgrade.
    _expect_error(lambda: kernel.publish_overwrite(out, failed), "cannot be downgraded")
    assert out.read_bytes() == before and list(case.glob("receipt.json.superseded-*")) == []


def test_rv07_schema_family_invalidation_and_exit_wiring(root: Path):
    case = root / "family-invalidation"
    case.mkdir()
    owned = case / "owned.json"
    owned.write_text(json.dumps({"schema": "time-spotcheck/v2"}), encoding="utf-8")
    archived = supply.invalidate_stale_receipt(
        owned, schema_family="time-spotcheck/")
    assert archived is not None and not owned.exists() and Path(archived).is_file()

    unrelated = case / "unrelated.json"
    unrelated.write_text(json.dumps({"schema": "other/v1"}), encoding="utf-8")
    assert supply.invalidate_stale_receipt(
        unrelated, schema_family="time-spotcheck/") is None
    assert unrelated.is_file()

    # Five approved true-FAIL exits must call the explicit primitive.  This is
    # a source-wiring guard; behavioral tests above cover kernel + supply + the
    # multi-file window transaction.
    surfaces = {
        ROOT / "scripts/lib/supply_truth_gate.py": 1,
        ROOT / "scripts/evm/verify_recon.py": 1,
        ROOT / "scripts/lib/time_spotcheck.py": 2,
        ROOT / "scripts/solana/window_fetch.py": 1,
    }
    for path, minimum in surfaces.items():
        text = path.read_text(encoding="utf-8")
        assert text.count("publish_supersede(") >= minimum, (path, minimum)


def _load_window_module(work: Path):
    name = f"repair_batch1_window_{os.getpid()}_{id(work)}"
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "scripts/solana/window_fetch.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_rv07_window_fail_transaction(root: Path):
    work = root / "window"
    work.mkdir()
    (work / "config.json").write_text(json.dumps({"mint": "mint1"}), encoding="utf-8")
    with chdir(work):
        window = _load_window_module(work)
        out = work / "window.jsonl"
        receipt = work / "window_receipt.json"
        gaps = Path(str(out) + ".gaps.json")
        argv = ["0", "10", str(out), "--conc", "1", "--receipt", str(receipt)]
        good = ([(1, 1, "a", "b", 1)], True, [1])
        bad = ([(1, 1, "a", "b", 1)], False, [1])
        with mock.patch.object(window, "scan_seg", return_value=good):
            assert window.main(argv) == 0
        old_data = out.read_bytes()
        old_receipt = receipt.read_bytes()
        old_gaps = gaps.read_bytes()

        # Dedicated injection: receipt switch fails after data archive link was
        # prepared.  Rollback must retain old data/PASS/gaps and remove links.
        with mock.patch.object(window, "scan_seg", return_value=bad), \
                mock.patch.object(window, "publish_supersede",
                                  side_effect=OSError("receipt switch injected")):
            assert window.main(argv) == 1
        assert out.read_bytes() == old_data
        assert receipt.read_bytes() == old_receipt
        assert gaps.read_bytes() == old_gaps
        assert list(work.glob("window.jsonl.stale.*")) == []
        assert list(work.glob("window.jsonl.gaps.json.failed-*")) == []

        # Real FAIL commit: receipt switches first, then old data canonical is
        # removed while its hard-link archive remains.
        with mock.patch.object(window, "scan_seg", return_value=bad):
            assert window.main(argv) == 2
        current = json.loads(receipt.read_text(encoding="utf-8"))
        receipt_archives = list(work.glob("window_receipt.json.superseded-*"))
        data_archives = list(work.glob("window.jsonl.stale.*"))
        assert current["verdict"] == "FAIL" and not out.exists()
        assert len(receipt_archives) == 1 and receipt_archives[0].read_bytes() == old_receipt
        assert len(data_archives) == 1 and data_archives[0].read_bytes() == old_data
        bound_gaps = Path(current["inputs"]["gaps"]["path"])
        assert bound_gaps.exists() and bound_gaps.name.startswith(
            "window.jsonl.gaps.json.failed-")


def main():
    with tempfile.TemporaryDirectory(prefix="repair-batch1-rv07-", dir="/private/tmp") as raw:
        root = Path(raw)
        test_rv07_original_counterexample(root / "original")
        test_rv07_payload_and_stage_failures(root)
        test_rv07_link_replace_and_rollback_failures(root)
        test_rv07_collision_cycle_and_identity(root)
        test_rv07_concurrency_and_ordinary_guard(root)
        test_rv07_schema_family_invalidation_and_exit_wiring(root)
        test_rv07_window_fail_transaction(root)
    print("PASS v6.41.0 batch1 step1 RV-07")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
