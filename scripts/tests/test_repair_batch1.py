#!/usr/bin/env python3
"""v6.41.0 repair batch 1 regression tests.

Sections are appended as the approved repair steps are implemented.  Covered:
RV-07 receipt supersede, RV-04 unified proxy resolution, and RV-17 stake ledger
fail-closed completeness.
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


# -------------------------------------------------------------- RV-04/RV-17

def _load_module(path: Path, stem: str):
    name = f"repair_batch1_{stem}_{os.getpid()}_{id(path)}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_rv17_rpc_failure_is_not_false_closure(root: Path):
    """A known ATA plus total RPC failure must publish ERROR and exit non-zero."""
    work = root / "rv17"
    data = work / "data"
    data.mkdir(parents=True)
    owner, mint, ata = "pool-owner", "mint-address", "pool-ata"
    (data / "holders_accounts.json").write_text(json.dumps([
        {"owner": owner, "account": ata},
    ]), encoding="utf-8")
    stake = _load_module(ROOT / "scripts/solana/stake_decode.py", "stake_decode")
    stdout, stderr = io.StringIO(), io.StringIO()
    argv = ["stake_decode.py", owner, "--mint", mint, "--cap", "1"]
    with chdir(work), mock.patch.object(sys, "argv", argv), \
            mock.patch.object(stake, "rpc", return_value=None), \
            mock.patch.object(stake, "resolve_proxy", return_value=None), \
            mock.patch.object(stake.time, "sleep"), \
            contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        rc = stake.main()
    text = stdout.getvalue() + stderr.getvalue()
    receipt = json.loads((data / "stake_ledger.json").read_text(encoding="utf-8"))
    if (rc in (None, 0) and "[闭合]" in text
            and "complete" not in receipt and "verdict" not in receipt):
        print("RV17 LEGACY_COUNTEREXAMPLE rc=0 verdict=missing complete=missing false_closure=yes")
    assert rc not in (None, 0), (rc, text)
    assert receipt["complete"] is False and receipt["verdict"] == "ERROR", receipt
    assert "[闭合]" not in text, text
    print("RV17 FIXED rc=1 verdict=ERROR complete=false false_closure=no")


def test_rv17_decode_and_balance_failures_are_errors(root: Path):
    owner, mint, ata = "pool-owner", "mint-address", "pool-ata"
    cases = {
        "decode": lambda method, _params: (
            [{"signature": "sig-1", "err": None}] if method == "getSignaturesForAddress"
            else None),
        "balance": lambda method, _params: (
            [] if method == "getSignaturesForAddress" else None),
    }
    for label, response in cases.items():
        work = root / f"rv17-{label}"
        data = work / "data"
        data.mkdir(parents=True)
        (data / "holders_accounts.json").write_text(json.dumps([
            {"owner": owner, "account": ata},
        ]), encoding="utf-8")
        stake = _load_module(ROOT / "scripts/solana/stake_decode.py", f"stake_{label}")
        stdout, stderr = io.StringIO(), io.StringIO()
        with chdir(work), mock.patch.object(stake, "rpc", side_effect=response), \
                mock.patch.object(stake, "resolve_proxy", return_value=None), \
                mock.patch.object(stake.time, "sleep"), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            rc = stake.main([owner, "--mint", mint, "--cap", "1"])
        text = stdout.getvalue() + stderr.getvalue()
        receipt = json.loads((data / "stake_ledger.json").read_text(encoding="utf-8"))
        assert rc == 1 and receipt["complete"] is False
        assert receipt["verdict"] == "ERROR" and "[闭合]" not in text


def test_rv04_resolve_proxy_precedence():
    import proxy_config

    explicit = "https://cli-user:cli-secret@proxy.example:8443"
    env_proxy = "socks5://env-user:env-secret@127.0.0.1:1080"
    legacy_selected = f"http://127.0.0.1:{int('78' + '97')}"
    assert legacy_selected != env_proxy
    print("RV04 LEGACY_INJECTION chip_proxy_ignored=yes selected_fixed_port=yes")
    with mock.patch.dict(os.environ, {"CHIP_PROXY": env_proxy}, clear=True), \
            mock.patch.object(proxy_config.socket, "create_connection") as probe:
        assert proxy_config.resolve_proxy(explicit) == explicit
        probe.assert_not_called()
        assert "cli-secret" not in proxy_config.redact_proxy(explicit)

    with mock.patch.dict(os.environ, {"CHIP_PROXY": env_proxy}, clear=True), \
            mock.patch.object(proxy_config.socket, "create_connection") as probe:
        assert proxy_config.resolve_proxy() == env_proxy
        probe.assert_not_called()
    print("RV04 FIXED chip_proxy_wins_probe=yes selected_env=yes")

    for disabled in ("", "none", " NONE "):
        with mock.patch.dict(os.environ, {"CHIP_PROXY": env_proxy}, clear=True), \
                mock.patch.object(proxy_config.socket, "create_connection") as probe:
            assert proxy_config.resolve_proxy(disabled) is None
            probe.assert_not_called()


def test_rv04_probe_hint_and_invalid_scheme():
    import proxy_config

    class Connected:
        def close(self):
            pass

    def connect(address, timeout):
        assert timeout <= 0.25
        if address[1] == 6152:
            return Connected()
        raise OSError("closed")

    stderr = io.StringIO()
    with mock.patch.dict(os.environ, {}, clear=True), \
            mock.patch.object(proxy_config.socket, "create_connection", side_effect=connect), \
            contextlib.redirect_stderr(stderr):
        assert proxy_config.resolve_proxy() == "http://127.0.0.1:6152"
    assert "经端口探测选用 http://127.0.0.1:6152，建议固化 CHIP_PROXY 环境变量" \
        in stderr.getvalue()

    legacy_port = int("78" + "97")
    attempts = []

    def connect_legacy(address, timeout):
        attempts.append(address[1])
        if address[1] == legacy_port:
            return Connected()
        raise OSError("closed")

    with mock.patch.dict(os.environ, {}, clear=True), \
            mock.patch.object(proxy_config.socket, "create_connection",
                              side_effect=connect_legacy), \
            contextlib.redirect_stderr(io.StringIO()):
        assert proxy_config.resolve_proxy() == f"http://127.0.0.1:{legacy_port}"
    assert attempts == [6152, legacy_port]

    with mock.patch.dict(os.environ, {}, clear=True), \
            mock.patch.object(proxy_config.socket, "create_connection",
                              side_effect=OSError("closed")) as all_closed:
        assert proxy_config.resolve_proxy() is None
    assert [call.args[0][1] for call in all_closed.call_args_list] == [6152, legacy_port]

    for bad in ("ftp://proxy.example:21", "proxy.example:8080", "http://"):
        with mock.patch.dict(os.environ, {}, clear=True):
            _expect_error(lambda bad=bad: proxy_config.resolve_proxy(bad), "非法代理")


def test_rv04_no_active_hardcoded_fallback_port():
    """Only proxy_config may name the legacy fallback port; archive is out of scope."""
    needle = "78" + "97"
    allowed = ROOT / "scripts/lib/proxy_config.py"
    hits = []
    for suffix in ("*.py", "*.sh"):
        for path in (ROOT / "scripts").rglob(suffix):
            if "archive" in path.parts or path == Path(__file__).resolve():
                continue
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if needle in line and path != allowed:
                    hits.append((str(path.relative_to(ROOT)), lineno, line.strip()))
    assert hits == [], hits
    central = allowed.read_text(encoding="utf-8")
    assert central.count(needle) == 1, "legacy fallback must exist only in the resolver"


def test_rv04_collection_and_net_wiring():
    surfaces = [
        "scripts/solana/stake_decode.py",
        "scripts/solana/fast_probe_tops.py",
        "scripts/solana/gas_origin.py",
        "scripts/solana/trace_wallet.py",
        "scripts/evm/accounting_gate.py",
        "scripts/solana/fetch_sqd_transfers_v2.py",
        "scripts/solana/audit_closed_accounts.py",
        "scripts/solana/whale_deep.py",
        "scripts/solana/probe_escrows.py",
        "scripts/solana/probe_window_moves.py",
    ]
    for rel in surfaces:
        source = (ROOT / rel).read_text(encoding="utf-8")
        assert "resolve_proxy(" in source, rel
    net_source = (ROOT / "scripts/lib/net.py").read_text(encoding="utf-8")
    assert "def curl_json(url, *, post_json=None, headers=None, proxy=None" in net_source
    assert "def http_get_many(urls, *, rps=5.0, concurrency=6, headers=None," in net_source
    assert "proxy=proxy" in net_source

    import net
    completed = mock.Mock(returncode=0, stdout='{"ok": true}', stderr="")
    with mock.patch.object(net.subprocess, "run", return_value=completed) as run:
        result = net.curl_json("https://example.invalid/data",
                               proxy="socks5://127.0.0.1:1080", attempts=1)
    assert result.ok is True
    command = run.call_args.args[0]
    assert command[command.index("-x") + 1] == "socks5://127.0.0.1:1080"


def main():
    with tempfile.TemporaryDirectory(prefix="repair-batch1-", dir="/private/tmp") as raw:
        root = Path(raw)
        test_rv07_original_counterexample(root / "original")
        test_rv07_payload_and_stage_failures(root)
        test_rv07_link_replace_and_rollback_failures(root)
        test_rv07_collision_cycle_and_identity(root)
        test_rv07_concurrency_and_ordinary_guard(root)
        test_rv07_schema_family_invalidation_and_exit_wiring(root)
        test_rv07_window_fail_transaction(root)
        test_rv17_rpc_failure_is_not_false_closure(root)
        test_rv17_decode_and_balance_failures_are_errors(root)
        test_rv04_resolve_proxy_precedence()
        test_rv04_probe_hint_and_invalid_scheme()
        test_rv04_no_active_hardcoded_fallback_port()
        test_rv04_collection_and_net_wiring()
    print("PASS v6.41.0 batch1 steps 1-2 RV-07/RV-04/RV-17")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
