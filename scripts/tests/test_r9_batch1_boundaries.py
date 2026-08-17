#!/usr/bin/env python3
"""R9 batch-1 process-boundary regressions.

Only external transports are replaced.  Every assertion launches the real CLI
in a child process so a Python ``return 1`` cannot masquerade as process success.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
POOL = ROOT / "scripts/evm/fetch_pool_swaps.py"
SCAN = ROOT / "scripts/solana/scan_token_accounts.py"
ANCHOR = ROOT / "scripts/lib/anchor_plan.py"
SPOTCHECK = ROOT / "scripts/lib/time_spotcheck.py"
TOKEN = "0x" + "9" * 40
MINT = "Mint111111111111111111111111111111111111111"


def run(command, cwd, *, env=None):
    child_env = os.environ.copy()
    child_env["PYTHONDONTWRITEBYTECODE"] = "1"
    if env:
        child_env.update(env)
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                          env=child_env)


def detail(proc):
    return (f"rc={proc.returncode}\nstdout:\n{proc.stdout[-1200:]}\n"
            f"stderr:\n{proc.stderr[-1200:]}")


def write_transport_fixtures(root):
    transport = root / "transport"
    transport.mkdir()
    (transport / "sitecustomize.py").write_text(
        r'''
import base64
import json
import os
import time
import urllib.request
from pathlib import Path

time.sleep = lambda _seconds: None
_slot = 100


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        if self.payload is None:
            return b"{not-json"
        return json.dumps(self.payload).encode("utf-8")


def _next_slot(config=None):
    global _slot
    minimum = int((config or {}).get("minContextSlot", 0))
    _slot = max(_slot + 1, minimum)
    return _slot


def _mint_raw():
    raw = bytearray(82)
    raw[36:44] = (100).to_bytes(8, "little")
    raw[44] = 0
    raw[45] = 1
    return bytes(raw)


def _urlopen(request, **_kwargs):
    body = json.loads(request.data)
    method = body["method"]
    scenario = os.environ.get("R9_SCAN_SCENARIO", "success")
    trace = os.environ.get("R9_SCAN_TRACE")
    if trace:
        with open(trace, "a", encoding="utf-8") as handle:
            handle.write(method + "\n")
    if scenario == "network":
        raise RuntimeError("injected network failure")
    if method == "getGenesisHash":
        result = "5eykt4UsFv8P8NJdTREpY1vzqKqZKvdpKuc147dw2N9d"
    elif method == "getAccountInfo":
        config = body["params"][1]
        slot = _next_slot(config)
        if config.get("encoding") == "jsonParsed":
            data = {"parsed": {"type": "mint", "info": {
                "mintAuthority": None, "freezeAuthority": None,
                "supply": "100", "decimals": 0}}}
        else:
            data = [base64.b64encode(_mint_raw()).decode(), "base64"]
        result = {"context": {"slot": slot}, "value": {
            "owner": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA", "data": data}}
    elif method == "getProgramAccounts":
        config = body["params"][1]
        slot = _next_slot(config)
        if scenario == "gpa_slot":
            slot -= 2
        amount = 99 if scenario == "accounting" else 100
        raw = bytes(32) + amount.to_bytes(8, "little")
        result = {"context": {"slot": slot}, "value": [{
            "pubkey": "Account1", "account": {
                "data": [base64.b64encode(raw).decode(), "base64"]}}]}
        if scenario == "publish":
            Path(os.environ["R9_SCAN_RECEIPT"]).mkdir(parents=False, exist_ok=False)
    elif method == "getSignaturesForAddress":
        result = []
    elif method == "getTokenSupply":
        if scenario == "parse":
            return _Response(None)
        slot = 100 if scenario == "supply_slot" else _next_slot()
        result = {"context": {"slot": slot},
                  "value": {"amount": "100", "decimals": 0}}
    else:
        raise AssertionError(method)
    return _Response({"jsonrpc": "2.0", "id": body.get("id", 1), "result": result})


urllib.request.urlopen = _urlopen
''', encoding="utf-8")
    (transport / "requests.py").write_text(r'''
import os

class Response:
    status_code = 200
    text = ""

    def __init__(self, payload=None, parse_error=False):
        self.payload = payload
        self.parse_error = parse_error

    def json(self):
        if self.parse_error:
            raise ValueError("injected invalid JSON")
        return self.payload

class Session:
    def post(self, *_args, **_kwargs):
        scenario = os.environ.get("R9_POOL_SCENARIO", "success")
        if scenario == "network":
            raise RuntimeError("injected network failure")
        if scenario == "parse":
            return Response(parse_error=True)
        if scenario == "missing_cursor":
            return Response({"data": []})
        if scenario == "stalled_cursor":
            return Response({"data": [], "next_block": 0})
        return Response({"data": [], "next_block": 10})
''', encoding="utf-8")

    return transport


def test_r9_02_real_anchor_producer_consumer(root):
    source = root / "transfers.csv"
    source.write_text(
        "block,ts,tx,from,to,value\n"
        f"100,2025-01-01T00:00:00Z,0xt1,0x{'0' * 40},0x{'1' * 40},100\n"
        f"200,2025-02-01T00:00:00Z,0xt2,0x{'1' * 40},0x{'2' * 40},40\n"
        f"300,2025-03-01T00:00:00Z,0xt3,0x{'2' * 40},0x{'1' * 40},10\n",
        encoding="utf-8")
    out_dir = root / "plan"
    command = [sys.executable, str(ANCHOR), "--input", str(source),
               "--chain", "bsc", "--token", TOKEN, "--total-supply", "100",
               "--decimals", "0", "--min-pct", "0", "--final-block", "300",
               "--out-dir", str(out_dir)]
    producer = run(command, root)
    legacy_replay = None
    if producer.returncode != 0 and "unrecognized arguments: --final-block" in producer.stderr:
        legacy = command[:]
        at = legacy.index("--final-block")
        del legacy[at:at + 2]
        legacy_replay = run(legacy, root)
        if legacy_replay.returncode == 0:
            consumer = run([
                sys.executable, str(SPOTCHECK), "--plan", str(out_dir / "anchor_plan.json"),
                "--input", str(source), "--dry-run", "--chain", "bsc", "--token", TOKEN,
                "--final-block", "300", "--out", str(root / "spotcheck.json")], root)
            raise AssertionError(
                "R9-02 producer rejected --final-block; legacy real producer output then "
                f"failed consumer contract\nproducer: {detail(producer)}\n"
                f"legacy producer: {detail(legacy_replay)}\nconsumer: {detail(consumer)}")
    assert producer.returncode == 0, detail(producer)
    plan_path = out_dir / "anchor_plan.json"
    receipt_path = out_dir / "anchor_plan.receipt.json"
    assert plan_path.is_file() and receipt_path.is_file()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert plan["schema"] == "anchor-plan/v3" and plan["final_block"] == 300
    assert receipt["schema"] == "anchor-plan-receipt/v2" and receipt["verdict"] == "PASS"
    consumer = run([
        sys.executable, str(SPOTCHECK), "--plan", str(plan_path), "--dry-run",
        "--input", str(source), "--chain", "bsc", "--token", TOKEN, "--final-block", "300",
        "--out", str(root / "spotcheck.json")], root)
    assert consumer.returncode == 0, detail(consumer)

    weak_dir = root / "weak-plan"
    weak = run([sys.executable, str(ANCHOR), "--input", str(source),
                "--chain", "bsc", "--token", TOKEN, "--total-supply", "100",
                "--decimals", "0", "--min-pct", "0", "--final-block", "300",
                "--per-cell", "1", "--edge-max", "1",
                "--out-dir", str(weak_dir)], root)
    assert weak.returncode != 0, "weak per_cell=1/edge_max=1 plan was accepted\n" + detail(weak)
    assert not (weak_dir / "anchor_plan.json").exists() \
        and not (weak_dir / "anchor_plan.receipt.json").exists()

    beyond = root / "beyond.csv"
    beyond.write_text(
        "block,ts,tx,from,to,value\n"
        f"301,2025-01-01T00:00:00Z,0xt2,0x{'0' * 40},0x{'1' * 40},100\n",
        encoding="utf-8")
    bad = run([sys.executable, str(ANCHOR), "--input", str(beyond),
               "--chain", "bsc", "--token", TOKEN, "--total-supply", "100",
               "--decimals", "0", "--min-pct", "0", "--final-block", "300",
               "--out-dir", str(out_dir)], root)
    assert bad.returncode != 0, detail(bad)
    assert not plan_path.exists() and not receipt_path.exists(), \
        "failed anchor rerun left prior plan/receipt current"
    assert list(out_dir.glob("anchor_plan.json.stale.*"))
    assert list(out_dir.glob("anchor_plan.receipt.json.stale.*"))
    assert list(out_dir.glob("anchor_plan.receipt.error.*.json")), \
        "failed anchor producer did not publish a unique ERROR receipt"
    stale_consumer = run([
        sys.executable, str(SPOTCHECK), "--plan", str(plan_path), "--dry-run",
        "--input", str(beyond), "--chain", "bsc", "--token", TOKEN, "--final-block", "300",
        "--out", str(root / "stale-spotcheck.json")], root)
    assert stale_consumer.returncode != 0, detail(stale_consumer)


def pool_command(root, out, transport):
    token = root / "hypersync.token"
    token.write_text("fixture-token\n", encoding="utf-8")
    env = {"PYTHONPATH": str(transport)}
    command = [sys.executable, str(POOL), "--token-file", str(token),
               "--pool", "0x" + "1" * 40, "--from-block", "0",
               "--to-block", "10", "--out", str(out), "--url", "http://fixture"]
    return command, env


def test_r9_03_pool_process_and_stale(root, transport):
    out = root / "pool.csv"
    marker = root / "pool.csv.receipt.json"
    command, env = pool_command(root, out, transport)
    success = run(command, root, env={**env, "R9_POOL_SCENARIO": "success"})
    assert success.returncode == 0 and out.is_file() and marker.is_file(), detail(success)
    failed = run(command, root, env={**env, "R9_POOL_SCENARIO": "missing_cursor"})
    stale = list(root.glob("pool.csv.stale*"))
    assert failed.returncode != 0, detail(failed)
    assert not out.exists() and not marker.exists() and stale, \
        "failed rerun left prior canonical CSV/marker current"
    assert list(root.glob("pool.csv.receipt.error.*.json")), \
        "failed pool producer did not publish a unique ERROR receipt"
    assert list(root.glob("pool.csv.receipt.json.stale.*")), \
        "failed pool producer did not quarantine the prior PASS marker"

    for scenario in ("network", "parse", "missing_cursor", "stalled_cursor"):
        target = root / f"pool-{scenario}.csv"
        command, env = pool_command(root, target, transport)
        proc = run(command, root, env={**env, "R9_POOL_SCENARIO": scenario})
        assert proc.returncode != 0 and not target.exists(), \
            f"pool scenario={scenario}\n{detail(proc)}"

    bad = command[:]
    bad[bad.index("--from-block") + 1] = "10"
    proc = run(bad, root, env={**env, "R9_POOL_SCENARIO": "success"})
    assert proc.returncode != 0, detail(proc)


def scan_command(root, out, receipt, transport):
    work = root / "work"
    trace = root / "rpc.trace"
    env = {"PYTHONPATH": str(transport),
           "R9_SCAN_RECEIPT": str(receipt), "R9_SCAN_TRACE": str(trace)}
    command = [sys.executable, str(SCAN), MINT, "--program", "spl",
               "--rpc", "http://fixture", "--timeout", "1",
               "--out", str(out), "--receipt", str(receipt), "--work-dir", str(work)]
    return command, env, trace


def test_r9_04_scan_process_and_marker(root, transport):
    cases = ("path_conflict", "supply_slot", "gpa_slot", "publish")
    for scenario in cases:
        case = root / scenario
        case.mkdir()
        out = case / "snapshot.json"
        receipt = case / "snapshot.receipt.json"
        command, env, trace = scan_command(case, out, receipt, transport)
        if scenario == "path_conflict":
            command[command.index("--receipt") + 1] = str(out)
        proc = run(command, case, env={**env, "R9_SCAN_SCENARIO": scenario})
        assert proc.returncode != 0, f"scan scenario={scenario}\n{detail(proc)}"
        assert not receipt.is_file(), f"scan scenario={scenario} left a current marker"
        if scenario != "path_conflict":
            assert trace.read_text(encoding="utf-8").splitlines()[0] == "getGenesisHash"

    old = root / "old"
    old.mkdir()
    out = old / "snapshot.json"
    receipt = old / "snapshot.receipt.json"
    out.write_text('{"old": true}\n', encoding="utf-8")
    receipt.write_text('{"verdict": "PASS", "old": true}\n', encoding="utf-8")
    command, env, trace = scan_command(old, out, receipt, transport)
    proc = run(command, old, env={**env, "R9_SCAN_SCENARIO": "supply_slot"})
    assert proc.returncode != 0, detail(proc)
    assert not out.exists() and not receipt.exists(), \
        "failed scan left prior canonical data/marker current"
    assert list(old.glob("snapshot.json.stale*"))
    assert list(old.glob("snapshot.receipt.json.stale*"))
    assert trace.read_text(encoding="utf-8").splitlines()[0] == "getGenesisHash"

    for scenario in ("network", "parse", "accounting"):
        case = root / scenario
        case.mkdir()
        out = case / "snapshot.json"
        receipt = case / "snapshot.receipt.json"
        command, env, trace = scan_command(case, out, receipt, transport)
        proc = run(command, case, env={**env, "R9_SCAN_SCENARIO": scenario})
        assert proc.returncode != 0 and not receipt.is_file(), \
            f"scan scenario={scenario}\n{detail(proc)}"
        assert trace.read_text(encoding="utf-8").splitlines()[0] == "getGenesisHash"


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=("all", "anchor", "pool", "scan"), default="all")
    args = parser.parse_args(argv)
    selected = {
        "anchor": lambda root, _transport: test_r9_02_real_anchor_producer_consumer(root),
        "pool": test_r9_03_pool_process_and_stale,
        "scan": test_r9_04_scan_process_and_marker,
    }
    names = tuple(selected) if args.only == "all" else (args.only,)
    failures = []
    with tempfile.TemporaryDirectory(prefix="r9-b1-") as td:
        root = Path(td).resolve()
        transport = write_transport_fixtures(root)
        for name in names:
            case = root / name
            case.mkdir()
            try:
                selected[name](case, transport)
            except Exception as exc:
                failures.append((name, str(exc)))
                print(f"FAIL R9 batch1 {name}: {exc}")
            else:
                print(f"PASS R9 batch1 {name}")
    if failures:
        print(f"R9 batch1 process-boundary failures: {len(failures)}/{len(names)}")
        return 1
    print(f"PASS R9 batch1 process-boundary suite: {len(names)}/{len(names)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
