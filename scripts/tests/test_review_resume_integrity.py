#!/usr/bin/env python3
"""2026-08-02 review regressions: H-02 through H-06."""
import csv
import gzip
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVM = HERE.parent / "evm"
SOL = HERE.parent / "solana"
FETCH_V2 = EVM / "fetch_hypersync_v2.py"
sys.path.insert(0, str(EVM))
sys.path.insert(0, str(SOL))
sys.path.insert(0, str(HERE))

from fetch_hypersync_v2 import (MANIFEST_SCHEMA, QUERY_SCHEMA, SCRIPT_PATH,
                                ensure_outdir_identity, find_resume_block,
                                sha256_file)
from channels_preflight import _csv_stats, _file_fingerprints, _v2_stats
from fetch_sqd_transfers_v2 import cache_identity, cache_identity_matches, cache_paths
from replay_edges import cmd_evolution, cmd_reconcile
from evm_channel_fixture import write_csv_channel_receipt

ZERO_EVM = "0x" + "0" * 40
A_EVM = "0x" + "a" * 40
ZERO_SOL = "0x" + "0" * 40


def run(cmd, cwd):
    return subprocess.run([sys.executable] + [str(x) for x in cmd], cwd=cwd,
                          capture_output=True, text=True)


def make_parquet(root, blocks, run_name="run_0"):
    import duckdb
    run_dir = Path(root) / run_name
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
    con.close()
    return run_dir


def file_meta(path, block_col):
    import duckdb
    con = duckdb.connect()
    rows, lo, hi = con.execute(
        f"SELECT COUNT(*), MIN({block_col}), MAX({block_col}) FROM read_parquet(?)",
        [str(path)]).fetchone()
    con.close()
    return {"size": path.stat().st_size, "rows": rows, "min_block": lo,
            "max_block": hi, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def make_done(out, mutate=None):
    ensure_outdir_identity(out, A_EVM, "https://bsc.hypersync.xyz")
    run_dir = make_parquet(out, [10, 19], "run_10")
    done = {"schema": MANIFEST_SCHEMA, "query_schema": QUERY_SCHEMA,
            "capture_from": 10, "from_block": 10, "to_block": 20, "next_block": 20,
            "token": A_EVM, "url": "https://bsc.hypersync.xyz",
            "files": {"logs.parquet": file_meta(run_dir / "logs.parquet", "block_number"),
                      "blocks.parquet": file_meta(run_dir / "blocks.parquet", "number")},
            "collector": {"path": SCRIPT_PATH, "sha256": sha256_file(FETCH_V2)}}
    (run_dir / "done.json").write_text(json.dumps(done))
    if mutate == "missing":
        (run_dir / "logs.parquet").unlink()
    elif mutate == "truncated":
        (run_dir / "logs.parquet").write_bytes(b"truncated")
    elif mutate == "hash":
        done["files"]["logs.parquet"]["sha256"] = "0" * 64
        (run_dir / "done.json").write_text(json.dumps(done))
    return run_dir, done


def make_legacy_done(out, mutate=None):
    run_dir = make_parquet(out, [10, 19], "run_10")
    done = {"schema": "hypersync-v2-done/v2", "query_schema": QUERY_SCHEMA,
            "capture_from": 10, "from_block": 10, "to_block": 20, "next_block": 20,
            "token": A_EVM, "url": "https://bsc.hypersync.xyz",
            "client_version": "legacy-fixture"}
    done_path = run_dir / "done.json"
    done_path.write_text(json.dumps(done))
    if mutate == "missing":
        (run_dir / "logs.parquet").unlink()
    elif mutate == "truncated":
        (run_dir / "logs.parquet").write_bytes(b"truncated")
    return run_dir, done


def channel_receipt(tmp, tag, data_path, lo, hi, rows):
    p = Path(tmp) / f"{tag}.receipt.json"
    data_path = Path(data_path)
    fmt = "v2" if data_path.is_dir() else "v1csv"
    if fmt == "v1csv":
        return write_csv_channel_receipt(tmp, tag, data_path, A_EVM, lo, hi)
    _, min_block, max_block = (_v2_stats(data_path) if fmt == "v2"
                               else _csv_stats(data_path))
    p.write_text(json.dumps({"schema": "evm-channel-receipt/v2", "status": "PASS",
                             "tag": tag, "token": A_EVM, "lo": lo, "hi": hi,
                             "data_path": str(data_path), "format": fmt, "rows": rows,
                             "min_block": min_block, "max_block": max_block,
                             "files": _file_fingerprints(data_path, fmt)}))
    return str(p)


def test_h02(tmp):
    d1, d2 = Path(tmp) / "d1", Path(tmp) / "d2"
    make_parquet(d1, [1, 15])  # block 15 is pollution outside d1 responsibility [0,10)
    make_parquet(d2, [11])
    channels = Path(tmp) / "channels.json"
    channels.write_text(json.dumps({"schema": "evm-channels/v2", "token": A_EVM,
        "expected_from": 0, "expected_to": 20, "channels": [
        {"path": str(d1), "lo": 0, "hi": 10, "tag": "a", "format": "v2",
         "receipt": channel_receipt(tmp, "a", d1, 0, 10, 2)},
        {"path": str(d2), "lo": 10, "hi": 20, "tag": "b", "format": "v2",
         "receipt": channel_receipt(tmp, "b", d2, 10, 20, 1)}]}))
    out = Path(tmp) / "out"
    p = run([EVM / "replay_stream.py", "--channels", channels, "--out-dir", out], tmp)
    preflight = json.loads((out / "channels_preflight.json").read_text())
    assert p.returncode != 0 and preflight["status"] == "BLOCK", p.stdout + p.stderr


def test_h03(tmp):
    out = Path(tmp) / "resume_ok"
    _, done = make_done(out)
    assert find_resume_block(str(out), 10, 30, A_EVM, done["url"]) == 20
    try:
        find_resume_block(str(out), 10, 30, "0x" + "b" * 40, done["url"])
    except SystemExit:
        pass
    else:
        raise AssertionError("cross-token done manifest must reject")

    for mutation in ("missing", "truncated", "hash"):
        bad_out = Path(tmp) / f"resume_{mutation}"
        make_done(bad_out, mutation)
        try:
            find_resume_block(str(bad_out), 10, 30, A_EVM, done["url"])
        except SystemExit:
            pass
        else:
            raise AssertionError(f"done exists but parquet {mutation} must reject")

    # staged_capture.sh 的 skip 路径也必须复用实体验证，不得只看 JSON。
    staged_out = Path(tmp) / "staged_missing"
    make_done(staged_out, "missing")
    p = subprocess.run([str(EVM / "staged_capture.sh"), A_EVM, done["url"],
                        str(staged_out), "10", "20"], capture_output=True, text=True)
    assert p.returncode != 0 and "FATAL" in p.stdout + p.stderr


def test_u2b_staged_capture_first_run(tmp):
    fake_bin = Path(tmp) / "fake-bin"
    fake_bin.mkdir()
    fake_python = fake_bin / "python3"
    fake_python.write_text(
        "#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$U2B_CALLS\"\nexit 7\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")

    # All three first-capture states must reach the fetch loop; the fake transport then fails.
    for tag in ("absent", "empty", "ds-store"):
        root = Path(tmp) / f"first-{tag}"
        if tag != "absent":
            root.mkdir()
        if tag == "ds-store":
            (root / ".DS_Store").write_text("finder", encoding="utf-8")
        calls = Path(tmp) / f"{tag}.calls"
        env["U2B_CALLS"] = str(calls)
        proc = subprocess.run(
            [str(EVM / "staged_capture.sh"), A_EVM, "https://invalid.example",
             str(root), "10", "20"],
            capture_output=True, text=True, env=env,
        )
        output = proc.stdout + proc.stderr
        assert proc.returncode == 1, output
        assert "outdir 缺普通文件 capture_identity.json" not in output
        assert len(calls.read_text(encoding="utf-8").splitlines()) == 2

    # Any other hidden file proves the root is not a vacuum and keeps the recovery gate closed.
    legacy = Path(tmp) / "first-hidden"
    legacy.mkdir()
    (legacy / ".foo").write_text("not exempt", encoding="utf-8")
    calls = Path(tmp) / "hidden.calls"
    env["U2B_CALLS"] = str(calls)
    proc = subprocess.run(
        [str(EVM / "staged_capture.sh"), A_EVM, "https://invalid.example",
         str(legacy), "10", "20"],
        capture_output=True, text=True, env=env,
    )
    assert proc.returncode == 2 and "--recover-identity" in proc.stdout + proc.stderr
    assert not calls.exists()


def test_r2_refresh_manifests(tmp):
    good_out = Path(tmp) / "legacy_good"
    _, old = make_legacy_done(good_out)
    try:
        find_resume_block(str(good_out), 10, 30, A_EVM, old["url"])
    except SystemExit:
        pass
    else:
        raise AssertionError("R2 旧 manifest 未迁移前必须 BLOCK")
    p = run([FETCH_V2, "--recover-identity", "--outdir", good_out], tmp)
    assert p.returncode == 0, p.stdout + p.stderr
    p = run([FETCH_V2, "--refresh-manifests", "--outdir", good_out], tmp)
    assert p.returncode == 0, p.stdout + p.stderr
    upgraded = json.loads((good_out / "run_10" / "done.json").read_text())
    assert upgraded["schema"] == "hypersync-v2-done/v4"
    assert upgraded["collector"] is None
    assert upgraded["collector_provenance"] == "legacy-unattributed"
    assert set(upgraded["files"]) == {"logs.parquet", "blocks.parquet"}
    assert (good_out / "capture_identity.json").is_file()
    assert find_resume_block(str(good_out), 10, 30, A_EVM, old["url"]) == 20

    for mutation in ("missing", "truncated"):
        bad_out = Path(tmp) / f"legacy_{mutation}"
        _, old = make_legacy_done(bad_out, mutation)
        before = (bad_out / "run_10" / "done.json").read_bytes()
        p = run([FETCH_V2, "--recover-identity", "--outdir", bad_out], tmp)
        after = (bad_out / "run_10" / "done.json").read_bytes()
        assert p.returncode != 0 and before == after, p.stdout + p.stderr
        assert "run_10" in p.stdout + p.stderr
        try:
            find_resume_block(str(bad_out), 10, 30, A_EVM, old["url"])
        except SystemExit:
            pass
        else:
            raise AssertionError(f"R2 {mutation} 迁移失败后续拉仍必须 BLOCK")


def test_h04(tmp):
    src = Path(tmp) / "standard8.csv"
    with src.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["block", "ts", "tx", "log_index", "from", "to", "value_raw", "block_hash"])
        w.writerow([1, "2026-01-01", "0xtx", 0, ZERO_EVM, A_EVM, 100, "0xhash"])
    ch = Path(tmp) / "csv_channels.json"
    ch.write_text(json.dumps({"schema": "evm-channels/v2", "token": A_EVM,
                              "expected_from": 0, "expected_to": 2, "channels": [
        {"path": str(src), "lo": 0, "hi": 2, "tag": "x", "format": "v1csv",
         "receipt": channel_receipt(tmp, "x", src, 0, 2, 1)}]}))
    for script in ("replay_pass1.py", "replay_duck.py"):
        out = Path(tmp) / script
        out.mkdir()
        p = run([EVM / script, "--channels", ch, "--out-dir", out], tmp)
        assert p.returncode == 0, f"{script}: {p.stdout}{p.stderr}"


def test_h05():
    assert cache_paths("AbC")[0] != cache_paths("aBc")[0]
    meta = {**cache_identity("AbC", "ep"), "collection_upper_slot": 99}
    assert cache_identity_matches(meta, "AbC", "ep")
    assert not cache_identity_matches(meta, "aBc", "ep")
    assert not cache_identity_matches({**meta, "endpoint": "other"}, "AbC", "ep")


def test_h06(tmp):
    old = os.getcwd()
    os.chdir(tmp)
    try:
        Path("data").mkdir()
        mint = "MintCaseSensitive" + "1" * 15
        edges = [[100, 1, ZERO_SOL, "A", 100], [3700, 2, ZERO_SOL, "B", 100]]
        edge_key = hashlib.sha256(mint.encode("utf-8")).hexdigest()
        edge_path = Path(f"data/soltx-{edge_key}.jsonl.gz")
        with gzip.open(edge_path, "wt", encoding="utf-8") as fh:
            for edge in edges:
                fh.write(json.dumps(edge, ensure_ascii=False) + "\n")
        owners = Path("data/holders_owners.json")
        owners.write_text(json.dumps({"A": 100, "B": 100}))
        owner_ref = {"path": owners.name, "size": owners.stat().st_size,
                     "sha256": hashlib.sha256(owners.read_bytes()).hexdigest()}
        Path("data/holders_snapshot_meta.json").write_text(json.dumps({
            "schema": "solana-holder-snapshot-v2", "mint": mint,
            "target": {"chain": "solana", "token": mint,
                       "as_of_block": 2},
            "closed": True, "supply_raw": "200",
            "outputs": {"holders_owners": owner_ref}}))
        cache_meta = Path(f"data/soltx-{edge_key}.meta.json")
        cache_meta.write_text(json.dumps({
            "schema": "sqd-solana-cache/v3", "mint": mint,
            "from_slot": 1, "collection_upper_slot": 2}))
        assert cmd_reconcile(edges, 1, mint=mint,
                             cache_meta_path=cache_meta)
        Path("data/holders_snapshot_meta.json").unlink()
        assert not cmd_reconcile(edges, 1, mint=mint,
                                 cache_meta_path=cache_meta)
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
        test_u2b_staged_capture_first_run(tmp)
    with tempfile.TemporaryDirectory() as tmp:
        test_r2_refresh_manifests(tmp)
    with tempfile.TemporaryDirectory() as tmp:
        test_h04(tmp)
    test_h05()
    with tempfile.TemporaryDirectory() as tmp:
        test_h06(tmp)
    print("PASS: H-02/H-03 + U2b staged first capture + R2 legacy manifest refresh + "
          "H-04/H-05/H-06")
    return 0


if __name__ == "__main__":
    sys.exit(main())
