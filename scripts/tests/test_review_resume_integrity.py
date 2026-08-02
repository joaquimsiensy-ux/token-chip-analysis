#!/usr/bin/env python3
"""2026-08-02 review regressions: H-02 through H-06."""
import csv
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVM = HERE.parent / "evm"
SOL = HERE.parent / "solana"
sys.path.insert(0, str(EVM))
sys.path.insert(0, str(SOL))

from fetch_hypersync_v2 import MANIFEST_SCHEMA, QUERY_SCHEMA, find_resume_block
from fetch_sqd_transfers_v2 import cache_identity_matches, cache_paths
from replay_edges import cmd_evolution, cmd_reconcile

ZERO_EVM = "0x" + "0" * 40
A_EVM = "0x" + "a" * 40
ZERO_SOL = "0x" + "0" * 40


def run(cmd, cwd):
    return subprocess.run([sys.executable] + [str(x) for x in cmd], cwd=cwd,
                          capture_output=True, text=True)


def make_parquet(root, blocks):
    import duckdb
    run_dir = Path(root) / "run_0"
    run_dir.mkdir(parents=True)
    con = duckdb.connect()
    con.execute("CREATE TABLE logs(block_number BIGINT, block_hash VARCHAR, log_index BIGINT, "
                "transaction_hash VARCHAR, topic1 VARCHAR, topic2 VARCHAR, data VARCHAR)")
    for b in blocks:
        con.execute("INSERT INTO logs VALUES (?,?,?,?,?,?,?)", [b, "0xhash", 0, f"0xtx{b}",
                    "0x" + "0" * 64, "0x" + "0" * 24 + "a" * 40,
                    "0x" + f"{100:064x}"])
    con.execute(f"COPY logs TO '{run_dir / 'logs.parquet'}' (FORMAT parquet)")
    con.execute("CREATE TABLE bl(number BIGINT, timestamp BIGINT)")
    for b in blocks:
        con.execute("INSERT INTO bl VALUES (?,?)", [b, 1700000000 + b])
    con.execute(f"COPY bl TO '{run_dir / 'blocks.parquet'}' (FORMAT parquet)")


def test_h02(tmp):
    d1, d2 = Path(tmp) / "d1", Path(tmp) / "d2"
    make_parquet(d1, [1, 15])  # block 15 is pollution outside d1 responsibility [0,10)
    make_parquet(d2, [11])
    channels = Path(tmp) / "channels.json"
    channels.write_text(json.dumps({"channels": [
        {"path": str(d1), "lo": 0, "hi": 10, "tag": "a"},
        {"path": str(d2), "lo": 10, "hi": 20, "tag": "b"}]}))
    out = Path(tmp) / "out"
    p = run([EVM / "replay_stream.py", "--channels", channels, "--out-dir", out], tmp)
    stats = json.loads((out / "replay_stats.json").read_text())
    assert p.returncode != 0 and stats["n_out_of_segment"] == 1, p.stdout + p.stderr


def test_h03(tmp):
    out = Path(tmp) / "resume"
    run_dir = out / "run_10"
    run_dir.mkdir(parents=True)
    done = {"schema": MANIFEST_SCHEMA, "query_schema": QUERY_SCHEMA,
            "capture_from": 10, "from_block": 10, "to_block": 20, "next_block": 20,
            "token": A_EVM, "url": "https://bsc.hypersync.xyz"}
    (run_dir / "done.json").write_text(json.dumps(done))
    assert find_resume_block(str(out), 10, 30, A_EVM, done["url"]) == 20
    try:
        find_resume_block(str(out), 10, 30, "0x" + "b" * 40, done["url"])
    except SystemExit:
        pass
    else:
        raise AssertionError("cross-token done manifest must reject")


def test_h04(tmp):
    src = Path(tmp) / "standard8.csv"
    with src.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["block", "ts", "tx", "log_index", "from", "to", "value_raw", "block_hash"])
        w.writerow([1, "2026-01-01", "0xtx", 0, ZERO_EVM, A_EVM, 100, "0xhash"])
    ch = Path(tmp) / "csv_channels.json"
    ch.write_text(json.dumps({"channels": [{"path": str(src), "lo": 0, "hi": 2, "tag": "x"}]}))
    for script in ("replay_pass1.py", "replay_duck.py"):
        out = Path(tmp) / script
        out.mkdir()
        p = run([EVM / script, "--channels", ch, "--out-dir", out], tmp)
        assert p.returncode == 0, f"{script}: {p.stdout}{p.stderr}"


def test_h05():
    assert cache_paths("AbC")[0] != cache_paths("aBc")[0]
    meta = {"schema": "sqd-solana-cache/v3", "mint": "AbC", "endpoint": "ep",
            "collector": "fetch_sqd_transfers_v2.py/v3", "collection_upper_slot": 99}
    assert cache_identity_matches(meta, "AbC", "ep")
    assert not cache_identity_matches(meta, "aBc", "ep")
    assert not cache_identity_matches({**meta, "endpoint": "other"}, "AbC", "ep")


def test_h06(tmp):
    old = os.getcwd()
    os.chdir(tmp)
    try:
        Path("data").mkdir()
        edges = [[100, 1, ZERO_SOL, "A", 100], [3700, 2, ZERO_SOL, "B", 100]]
        Path("data/holders_owners.json").write_text(json.dumps({"A": 100, "B": 100}))
        Path("data/holders_snapshot_meta.json").write_text(json.dumps({"closed": True, "supply_raw": "200"}))
        assert cmd_reconcile(edges, 1)
        Path("data/holders_snapshot_meta.json").unlink()
        assert not cmd_reconcile(edges, 1)
        Path("camps.json").write_text(json.dumps({"A营": ["A"], "B营": ["B"]}))
        cmd_evolution(edges, 1, "camps.json", set())
        series = json.loads(Path("data/camp_share_series.json").read_text())
        assert series[0]["_supply_raw"] == "100" and series[0]["A营"] == 100.0, series
        assert series[-1]["_supply_raw"] == "200" and series[-1]["A营"] == 50.0, series
    finally:
        os.chdir(old)


def main():
    try:
        import duckdb  # noqa: F401
    except ImportError:
        raise SystemExit("duckdb required for H-02/H-04 regression")
    with tempfile.TemporaryDirectory() as tmp:
        test_h02(tmp)
    with tempfile.TemporaryDirectory() as tmp:
        test_h03(tmp)
    with tempfile.TemporaryDirectory() as tmp:
        test_h04(tmp)
    test_h05()
    with tempfile.TemporaryDirectory() as tmp:
        test_h06(tmp)
    print("PASS: H-02 channel bounds, H-03 resume identity, H-04 CSV8, H-05 case cache, H-06 reconcile/denominator")
    return 0


if __name__ == "__main__":
    sys.exit(main())
