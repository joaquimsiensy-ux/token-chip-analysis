#!/usr/bin/env python3
"""2026-08-02 review regressions: B-01/B-02 fail-closed integrity."""
import csv
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
EVM = os.path.join(HERE, "..", "evm")
sys.path.insert(0, EVM)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from transfers_lib import merge_sources
from evm_channel_fixture import write_csv_channel_receipt

ZERO = "0x" + "0" * 40
A = "0x" + "a" * 40
B = "0x" + "b" * 40
HDR8 = ["block", "ts", "tx", "log_index", "from", "to", "value_raw", "block_hash"]


def write8(path, row):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HDR8)
        w.writerow(row)


def expect_merge_reject(field, index, changed):
    with tempfile.TemporaryDirectory() as tmp:
        base = [100, "2026-01-01", "0xtx", 0, A, B, 100, "0xhash"]
        other = list(base)
        other[index] = changed
        p1, p2 = os.path.join(tmp, "a.csv"), os.path.join(tmp, "b.csv")
        write8(p1, base)
        write8(p2, other)
        try:
            merge_sources([p1, p2], os.path.join(tmp, "out.csv"))
        except SystemExit as e:
            assert e.code == 3, (field, e.code)
        else:
            raise AssertionError(f"B-01 {field} mismatch must reject")


def replay_case(row, hi=200):
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "in.csv")
        with open(src, "w") as f:
            f.write("block,ts,tx,from,to,value,uniqueId\n")
            f.write(row + "\n")
        ch = os.path.join(tmp, "channels.json")
        receipt = write_csv_channel_receipt(tmp, "x", src, A, 0, hi)
        json.dump({"schema": "evm-channels/v2", "token": A, "expected_from": 0,
                   "expected_to": hi, "channels": [
                       {"path": src, "lo": 0, "hi": hi, "tag": "x",
                        "format": "v1csv", "receipt": receipt}]}, open(ch, "w"))
        out = os.path.join(tmp, "out")
        p = subprocess.run([sys.executable, os.path.join(EVM, "replay_duck.py"),
                            "--channels", ch, "--out-dir", out], capture_output=True, text=True)
        stats = json.load(open(os.path.join(out, "replay_stats.json")))
        return p.returncode, stats, p.stdout + p.stderr


def preflight_out_of_segment_case():
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "in.csv")
        good = f"100,2026-01-01,0xtx,{ZERO},{A},100,log_0\n"
        open(src, "w").write("block,ts,tx,from,to,value,uniqueId\n" + good)
        receipt = write_csv_channel_receipt(tmp, "x", src, A, 0, 200)
        open(src, "w").write("block,ts,tx,from,to,value,uniqueId\n" +
                              f"250,2026-01-01,0xtx,{ZERO},{A},100,log_0\n")
        ch = os.path.join(tmp, "channels.json")
        json.dump({"schema": "evm-channels/v2", "token": A, "expected_from": 0,
                   "expected_to": 200, "channels": [{"path": src, "lo": 0, "hi": 200,
                   "tag": "x", "format": "v1csv", "receipt": receipt}]}, open(ch, "w"))
        out = os.path.join(tmp, "out")
        p = subprocess.run([sys.executable, os.path.join(EVM, "replay_duck.py"),
                            "--channels", ch, "--out-dir", out], capture_output=True, text=True)
        preflight = json.load(open(os.path.join(out, "channels_preflight.json")))
        return p.returncode, preflight, p.stdout + p.stderr


def main():
    for field, index, value in [
        ("amount", 6, 999), ("from", 4, ZERO), ("to", 5, A),
        ("block", 0, 101), ("block_hash", 7, "0xother")]:
        expect_merge_reject(field, index, value)

    try:
        import duckdb  # noqa: F401
    except ImportError:
        print("SKIP replay reject cases: duckdb not installed; B-01 merge cases PASS")
        return 0

    rc, st, out = replay_case(f"100,2026-01-01,0xtx,{ZERO},{A},not-an-int,log_0")
    assert rc != 0 and st["n_bad_fields"] == 1 and not st["gate_pass"], out
    rc, st, out = preflight_out_of_segment_case()
    assert rc != 0 and st["status"] == "BLOCK", out
    print("PASS: B-01 payload mismatches and B-02 rejected rows fail closed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
