#!/usr/bin/env python3
"""Result/curl_json fail-closed regressions for the shared network layer."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/lib"))

import net


def _run(stdout, *, returncode=0, stderr="", status=200):
    stdout = f"{stdout}\n__CURL_HTTP_STATUS__:{status}"
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
        (_run("", returncode=7, stderr="connect failed", status=0), "transport"),
        (_run("upstream rejected", returncode=22, status=429), "http_status"),
        (_run(""), "decode"),
        (_run("not-json"), "decode"),
        (_run('{"ready":true}', returncode=61, stderr="bad content encoding"), "transport"),
    ]
    for completed, category in cases:
        with mock.patch.object(net.subprocess, "run", return_value=completed):
            got = net.curl_json("https://fixture.invalid", attempts=1)
        assert got.ok is False and got.value is None, got
        assert got.error["category"] == category, got.error
        expected_keys = {"category", "message", "http_status", "retryable"}
        if completed.returncode:
            expected_keys.add("returncode")
        assert set(got.error) == expected_keys, got.error
        if completed.returncode == 61:
            assert got.error["returncode"] == 61 and got.error["http_status"] == 200
            assert got.error["retryable"] is True

    calls = []
    with mock.patch.object(net.subprocess, "run", side_effect=lambda *a, **k: (
            calls.append(1) or _run("quota", returncode=22, status=402))):
        got = net.curl_json("https://fixture.invalid", attempts=4,
                            no_retry_statuses=(402, 429))
    assert got.ok is False and got.error["http_status"] == 402, got
    assert got.error["retryable"] is False and len(calls) == 1, (got, calls)

    calls = []
    with mock.patch.object(net.subprocess, "run", side_effect=lambda *a, **k: (
            calls.append(1) or _run("busy", returncode=22, status=429))), \
            mock.patch.object(net.time, "sleep"):
        got = net.curl_json("https://fixture.invalid", attempts=3)
    assert got.error["http_status"] == 429 and got.error["retryable"] is True
    assert len(calls) == 3, "default retry behavior changed"

    secret = "NET_SECRET_KEY_12345678901234567890"
    endpoint = f"https://fixture.invalid/?api-key={secret}"
    with mock.patch.object(net.subprocess, "run", return_value=_run(
            "denied", returncode=22, status=402,
            stderr=f"curl: endpoint {endpoint} denied")):
        got = net.curl_json(endpoint, attempts=1)
    assert secret not in json.dumps(got.error), got.error

    url = "https://fixture.invalid"
    argv_calls = []
    def capture(argv, **kwargs):
        argv_calls.append(list(argv))
        return _run('{"ready":true}')
    with mock.patch.object(net.subprocess, "run", side_effect=capture):
        got = net.curl_json(url, attempts=1)
    assert len(argv_calls) == 1, argv_calls
    argv = argv_calls[0]
    assert argv.count("--compressed") == 1, argv
    assert argv.index("--compressed") == argv.index("--fail-with-body") + 1
    assert "--write-out" in argv, argv
    assert argv[argv.index("--write-out") + 1] == "\n__CURL_HTTP_STATUS__:%{http_code}"
    assert argv[-1] == url, argv
    assert got.ok is True and got.value == {"ready": True} and got.error is None, got

    ndjson = '{"header":{"number":1}}\n{"header":{"number":2}}\n'
    with mock.patch.object(net.subprocess, "run", return_value=_run(ndjson)):
        got = net.curl_json("https://fixture.invalid", attempts=1)
    assert got.ok is True and [row["header"]["number"] for row in got.value] == [1, 2], got
    print("PASS: net Result 显式状态与 curl_json 失败分类")


if __name__ == "__main__":
    main()
