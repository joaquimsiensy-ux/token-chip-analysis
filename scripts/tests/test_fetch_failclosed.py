#!/usr/bin/env python3
"""F-03/F-04 回归：HyperSync 失败、缺游标与停滞都不得伪完成。"""
import contextlib
import importlib.util
import io
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
POOL = ROOT / "scripts" / "evm" / "fetch_pool_swaps.py"
LOGS = ROOT / "scripts" / "evm" / "fetch_hypersync_logs.py"


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
                mod.main()
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


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)

        pool = load(POOL, "pool_failclosed")
        class FailingSession:
            def post(self, *args, **kwargs):
                raise RuntimeError("fixture failure")
        code, out = invoke(pool, pool_args(root / "pool-fail.csv"),
                           [((pool.requests, "Session"), FailingSession)])
        assert isinstance(code, int) and code != 0 and "swaps " not in out, out

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
