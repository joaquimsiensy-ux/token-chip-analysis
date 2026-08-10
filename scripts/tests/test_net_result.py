#!/usr/bin/env python3
"""Result/curl_json fail-closed regressions for the shared network layer."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/lib"))

import net


def _run(stdout, *, returncode=0, stderr=""):
    return subprocess.CompletedProcess(["curl"], returncode, stdout=stdout, stderr=stderr)


def main():
    result = net.Result(ok=True, value={"ready": True})
    try:
        bool(result)
    except TypeError:
        pass
    else:
        raise AssertionError("Result allowed implicit truth testing")

    cases = [
        (_run("", returncode=7, stderr="connect failed"), "transport"),
        (_run("upstream rejected", returncode=22), "http_status"),
        (_run(""), "decode"),
        (_run("not-json"), "decode"),
    ]
    for completed, category in cases:
        with mock.patch.object(net.subprocess, "run", return_value=completed):
            got = net.curl_json("https://fixture.invalid", attempts=1)
        assert got.ok is False and got.value is None, got
        assert got.error["category"] == category, got.error

    with mock.patch.object(net.subprocess, "run", return_value=_run('{"ready":true}')):
        got = net.curl_json("https://fixture.invalid", attempts=1)
    assert got.ok is True and got.value == {"ready": True} and got.error is None, got

    ndjson = '{"header":{"number":1}}\n{"header":{"number":2}}\n'
    with mock.patch.object(net.subprocess, "run", return_value=_run(ndjson)):
        got = net.curl_json("https://fixture.invalid", attempts=1)
    assert got.ok is True and [row["header"]["number"] for row in got.value] == [1, 2], got
    print("PASS: net Result 显式状态与 curl_json 失败分类")


if __name__ == "__main__":
    main()
