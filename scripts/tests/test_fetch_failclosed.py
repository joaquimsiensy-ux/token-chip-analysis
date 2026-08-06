#!/usr/bin/env python3
"""F-03/F-04 回归：HyperSync 失败、缺游标与停滞都不得伪完成。"""
import contextlib
import importlib.util
import io
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "evm"))
POOL = ROOT / "scripts" / "evm" / "fetch_pool_swaps.py"
LOGS = ROOT / "scripts" / "evm" / "fetch_hypersync_logs.py"
TRANSFERS = ROOT / "scripts" / "evm" / "fetch_hypersync.py"


class StopLoop(BaseException):
    pass


class Response:
    status_code = 200
    text = ""

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def invoke(mod, argv, patches):
    output = io.StringIO()
    code = 0
    try:
        with mock.patch.object(sys, "argv", argv), mock.patch.object(mod.time, "sleep"), \
                contextlib.redirect_stdout(output):
            with contextlib.ExitStack() as stack:
                for target, value in patches:
                    stack.enter_context(mock.patch.object(target[0], target[1], value))
                result = mod.main()
                if isinstance(result, int):
                    code = result
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
    except StopLoop:
        code = None
    return code, output.getvalue()


def pool_args(out):
    token = out.parent / "token"
    token.write_text("fake-token\n", encoding="utf-8")
    return [str(POOL), "--token-file", str(token), "--pool", "0x" + "1" * 40,
            "--from-block", "0", "--to-block", "10", "--out", str(out)]


def logs_args(out):
    token = out.parent / "token"
    token.write_text("fake-token\n", encoding="utf-8")
    return [str(LOGS), "0", "--token-file", str(token), "--url", "http://fixture",
            "--addr", "0x" + "1" * 40, "--out", str(out), "--sleep", "0"]


def transfer_args(out, frm="0", to="10"):
    token = out.parent / "token"
    token.write_text("fake-token\n", encoding="utf-8")
    return [str(TRANSFERS), frm, "--token-file", str(token), "--url", "http://fixture",
            "--token-addr", "0x" + "1" * 40, "--to-block", to,
            "--out", str(out), "--sleep", "0"]


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)

        for frm, to, label in (("10", "10", "equal"), ("100", "10", "reverse"),
                               ("-1", "10", "negative")):
            pool = load(POOL, f"pool_bad_range_{label}")
            out_path = root / f"pool-{label}.csv"
            args = pool_args(out_path)
            args[args.index("--from-block") + 1] = frm
            args[args.index("--to-block") + 1] = to
            code, _ = invoke(pool, args, [])
            assert code == 2 and not out_path.exists(), f"非法区间 {frm}->{to} 留下产物"

        transfers = load(TRANSFERS, "transfers_bad_range")
        out_path = root / "transfers-bad-range.csv"
        code, _ = invoke(transfers, transfer_args(out_path, "10", "10"), [])
        assert code == 2 and not out_path.exists(), "transfer 空区间未在开文件前拒绝"

        pool = load(POOL, "pool_failclosed")
        class FailingSession:
            def post(self, *args, **kwargs):
                raise RuntimeError("fixture failure")
        code, out = invoke(pool, pool_args(root / "pool-fail.csv"),
                           [((pool.requests, "Session"), FailingSession)])
        assert isinstance(code, int) and code != 0 and "swaps " not in out, out
        assert not (root / "pool-fail.csv").exists(), "失败留下正式 pool CSV"

        pool = load(POOL, "pool_midstream_failure")
        class MidstreamSession:
            def __init__(self): self.calls = 0
            def post(self, *args, **kwargs):
                self.calls += 1
                if self.calls == 1:
                    return Response({"data": [{"blocks": [{"number": 1, "timestamp": 1}],
                        "logs": [{"block_number": 1, "transaction_hash": "0xtx", "data": "0x"}]}],
                        "next_block": 5})
                raise RuntimeError("second page failed")
        mid = root / "pool-mid.csv"
        code, _ = invoke(pool, pool_args(mid), [((pool.requests, "Session"), MidstreamSession)])
        assert code == 2 and not mid.exists(), "中途失败遗留部分正式 pool CSV"

        pool = load(POOL, "pool_missing_cursor")
        class MissingSession:
            def post(self, *args, **kwargs):
                return Response({"data": []})
        code, out = invoke(pool, pool_args(root / "pool-missing.csv"),
                           [((pool.requests, "Session"), MissingSession)])
        assert isinstance(code, int) and code != 0 and "swaps " not in out, out

        logs = load(LOGS, "logs_missing_cursor")
        code, out = invoke(logs, logs_args(root / "logs-missing.csv"),
                           [((logs.requests, "post"), lambda *a, **k: Response(
                               {"data": [], "archive_height": 10}))])
        assert isinstance(code, int) and code != 0 and "[COMPLETE]" not in out, out
        assert not (root / "logs-missing.csv").exists(), "logs 失败留下正式 CSV"

        logs = load(LOGS, "logs_stalled_cursor")
        calls = {"n": 0}
        def stalled(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] > 1:
                raise StopLoop()
            return Response({"data": [], "next_block": 0, "archive_height": 10})
        code, out = invoke(logs, logs_args(root / "logs-stalled.csv"),
                           [((logs.requests, "post"), stalled)])
        assert isinstance(code, int) and code != 0 and "[COMPLETE]" not in out, out

        transfers = load(TRANSFERS, "transfers_network_fail")
        tr_out = root / "transfers-fail.csv"
        code, out = invoke(transfers, transfer_args(tr_out),
                           [((transfers.requests, "post"), lambda *a, **k:
                             (_ for _ in ()).throw(RuntimeError("fixture failure")))])
        assert code == 2 and "[COMPLETE]" not in out and not tr_out.exists(), \
            "transfer 失败留下正式 CSV"

        transfers = load(TRANSFERS, "transfers_receipt_commit_fail")
        tr_out = root / "transfers-commit.csv"
        tr_receipt = root / "transfers-commit.receipt.json"
        args = transfer_args(tr_out) + ["--receipt", str(tr_receipt)]
        real_replace = os.replace
        replace_calls = {"n": 0}
        def fail_receipt_replace(src, dst):
            replace_calls["n"] += 1
            if replace_calls["n"] == 2:
                raise OSError("receipt rename failed")
            return real_replace(src, dst)
        code, out = invoke(transfers, args,
                           [((transfers.requests, "post"), lambda *a, **k: Response(
                               {"data": [], "next_block": 10, "archive_height": 10})),
                            ((transfers.os, "replace"), fail_receipt_replace)])
        assert code == 1 and not tr_out.exists() and not tr_receipt.exists(), \
            "receipt 提交失败后未撤回正式 transfer CSV"

        pool = load(POOL, "pool_complete")
        class CompleteSession:
            def post(self, *args, **kwargs):
                return Response({"data": [], "next_block": 10})
        code, out = invoke(pool, pool_args(root / "pool-ok.csv"),
                           [((pool.requests, "Session"), CompleteSession)])
        assert code == 0 and "swaps 0 rows" in out, out

        logs = load(LOGS, "logs_complete")
        code, out = invoke(logs, logs_args(root / "logs-ok.csv"),
                           [((logs.requests, "post"), lambda *a, **k: Response(
                               {"data": [], "next_block": 10, "archive_height": 10}))])
        assert code == 0 and "[COMPLETE]" in out, out
    print("PASS: HyperSync 采集器失败与游标异常均 fail-closed")


if __name__ == "__main__":
    main()
