#!/usr/bin/env python3
"""R9 batch-1 process-boundary regressions.

Only external transports are replaced.  Every assertion launches the real CLI
in a child process so a Python ``return 1`` cannot masquerade as process success.
"""
from __future__ import annotations

import argparse
import json
import os
import stat
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
        "import time\ntime.sleep = lambda _seconds: None\n", encoding="utf-8")
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

    fake_curl = transport / "curl"
    fake_curl.write_text(r'''#!/usr/bin/env python3
import base64
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
out = Path(args[args.index("-o") + 1])
body = json.loads(args[args.index("-d") + 1])
method = body["method"]
scenario = os.environ.get("R9_SCAN_SCENARIO", "success")

if scenario == "network":
    raise SystemExit(7)
if scenario == "parse" and method == "getTokenSupply":
    out.write_text("{not-json", encoding="utf-8")
    raise SystemExit(0)

if method == "getTokenSupply":
    slot = 78 if scenario == "supply_slot" else 77
    result = {"context": {"slot": slot},
              "value": {"amount": "100", "decimals": 0}}
elif method == "getProgramAccounts":
    slot = 78 if scenario == "gpa_slot" else 77
    amount = 99 if scenario == "accounting" else 100
    raw = bytes(32) + amount.to_bytes(8, "little")
    result = {"context": {"slot": slot}, "value": [{
        "pubkey": "Account1",
        "account": {"data": [base64.b64encode(raw).decode(), "base64"]},
    }]}
    if scenario == "publish":
        marker = Path(os.environ["R9_SCAN_RECEIPT"])
        marker.mkdir(parents=False, exist_ok=False)
elif method == "getAccountInfo":
    result = {"context": {"slot": 77}, "value": {
        "owner": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"}}
else:
    raise AssertionError(method)

out.write_text(json.dumps({"result": result}), encoding="utf-8")
''', encoding="utf-8")
    fake_curl.chmod(fake_curl.stat().st_mode | stat.S_IXUSR)
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
                "--dry-run", "--chain", "bsc", "--token", TOKEN,
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
    assert plan["schema"] == "anchor-plan/v2" and plan["final_block"] == 300
    assert receipt["schema"] == "anchor-plan-receipt/v2" and receipt["verdict"] == "PASS"
    consumer = run([
        sys.executable, str(SPOTCHECK), "--plan", str(plan_path), "--dry-run",
        "--chain", "bsc", "--token", TOKEN, "--final-block", "300",
        "--out", str(root / "spotcheck.json")], root)
    assert consumer.returncode == 0, detail(consumer)

    beyond = root / "beyond.csv"
    beyond.write_text(
        "block,ts,tx,from,to,value\n"
        f"301,2025-01-01T00:00:00Z,0xt2,0x{'0' * 40},0x{'1' * 40},100\n",
        encoding="utf-8")
    bad_dir = root / "bad-plan"
    bad = run([sys.executable, str(ANCHOR), "--input", str(beyond),
               "--chain", "bsc", "--token", TOKEN, "--total-supply", "100",
               "--decimals", "0", "--min-pct", "0", "--final-block", "300",
               "--out-dir", str(bad_dir)], root)
    assert bad.returncode != 0, detail(bad)
    assert not (bad_dir / "anchor_plan.json").exists()
    assert not (bad_dir / "anchor_plan.receipt.json").exists()


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
    command, env = pool_command(root, out, transport)
    success = run(command, root, env={**env, "R9_POOL_SCENARIO": "success"})
    assert success.returncode == 0 and out.is_file(), detail(success)
    failed = run(command, root, env={**env, "R9_POOL_SCENARIO": "missing_cursor"})
    stale = list(root.glob("pool.csv.stale*"))
    assert failed.returncode != 0, detail(failed)
    assert not out.exists() and stale, "failed rerun left prior canonical CSV current"

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
    env = {"PYTHONPATH": str(transport),
           "PATH": str(transport) + os.pathsep + os.environ.get("PATH", ""),
           "R9_SCAN_RECEIPT": str(receipt)}
    command = [sys.executable, str(SCAN), MINT, "--program", "spl",
               "--rpc", "http://fixture", "--timeout", "1", "--as-of-slot", "77",
               "--out", str(out), "--receipt", str(receipt), "--work-dir", str(work)]
    return command, env


def test_r9_04_scan_process_and_marker(root, transport):
    cases = ("path_conflict", "supply_slot", "gpa_slot", "publish")
    for scenario in cases:
        case = root / scenario
        case.mkdir()
        out = case / "snapshot.json"
        receipt = case / "snapshot.receipt.json"
        command, env = scan_command(case, out, receipt, transport)
        if scenario == "path_conflict":
            command[command.index("--receipt") + 1] = str(out)
        proc = run(command, case, env={**env, "R9_SCAN_SCENARIO": scenario})
        assert proc.returncode != 0, f"scan scenario={scenario}\n{detail(proc)}"
        assert not receipt.is_file(), f"scan scenario={scenario} left a current marker"

    old = root / "old"
    old.mkdir()
    out = old / "snapshot.json"
    receipt = old / "snapshot.receipt.json"
    out.write_text('{"old": true}\n', encoding="utf-8")
    receipt.write_text('{"verdict": "PASS", "old": true}\n', encoding="utf-8")
    command, env = scan_command(old, out, receipt, transport)
    proc = run(command, old, env={**env, "R9_SCAN_SCENARIO": "supply_slot"})
    assert proc.returncode != 0, detail(proc)
    assert not out.exists() and not receipt.exists(), \
        "failed scan left prior canonical data/marker current"
    assert list(old.glob("snapshot.json.stale*"))
    assert list(old.glob("snapshot.receipt.json.stale*"))

    for scenario in ("network", "parse", "accounting"):
        case = root / scenario
        case.mkdir()
        out = case / "snapshot.json"
        receipt = case / "snapshot.receipt.json"
        command, env = scan_command(case, out, receipt, transport)
        proc = run(command, case, env={**env, "R9_SCAN_SCENARIO": scenario})
        assert proc.returncode != 0 and not receipt.is_file(), \
            f"scan scenario={scenario}\n{detail(proc)}"


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
