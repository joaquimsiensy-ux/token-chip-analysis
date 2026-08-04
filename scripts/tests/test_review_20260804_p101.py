#!/usr/bin/env python3
"""P1-01: one HyperSync outdir has one immutable capture identity."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVM = HERE.parent / "evm"
sys.path.insert(0, str(EVM))

from fetch_hypersync_v2 import QUERY_SCHEMA, find_resume_block

TOKEN_A = "0x" + "a" * 40
TOKEN_B = "0x" + "b" * 40
URL_A = "https://bsc.hypersync.xyz"
URL_B = "https://eth.hypersync.xyz"


def meta(path, col):
    import duckdb
    con = duckdb.connect()
    rows, lo, hi = con.execute(
        f"SELECT COUNT(*), MIN({col}), MAX({col}) FROM read_parquet(?)", [str(path)]
    ).fetchone()
    con.close()
    return {"size": path.stat().st_size, "rows": rows, "min_block": lo,
            "max_block": hi, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def make_done(root, *, token=TOKEN_A, url=URL_A, query=QUERY_SCHEMA):
    import duckdb
    run = root / "run_0"
    run.mkdir(parents=True)
    con = duckdb.connect()
    con.execute("CREATE TABLE logs(block_number BIGINT, block_hash VARCHAR, log_index BIGINT, "
                "transaction_hash VARCHAR, topic1 VARCHAR, topic2 VARCHAR, data VARCHAR)")
    con.execute("INSERT INTO logs VALUES (5,'h',0,'t','1','2','3')")
    con.execute(f"COPY logs TO '{run / 'logs.parquet'}' (FORMAT parquet)")
    con.execute("CREATE TABLE blocks(number BIGINT, timestamp BIGINT)")
    con.execute("INSERT INTO blocks VALUES (5,1)")
    con.execute(f"COPY blocks TO '{run / 'blocks.parquet'}' (FORMAT parquet)")
    con.close()
    done = {"schema": "hypersync-v2-done/v3", "query_schema": query,
            "capture_from": 0, "from_block": 0, "to_block": 10, "next_block": 10,
            "token": token, "url": url,
            "files": {"logs.parquet": meta(run / "logs.parquet", "block_number"),
                      "blocks.parquet": meta(run / "blocks.parquet", "number")}}
    (run / "done.json").write_text(json.dumps(done), encoding="utf-8")


def must_block(root, token, url):
    try:
        find_resume_block(str(root), 100, 200, token, url)
    except SystemExit:
        return
    raise AssertionError("different outdir capture identity must fail closed")


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        make_done(root)
        must_block(root, TOKEN_B, URL_A)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        make_done(root)
        must_block(root, TOKEN_A, URL_B)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        make_done(root, query="other-query")
        must_block(root, TOKEN_A, URL_A)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        make_done(root)
        assert find_resume_block(str(root), 100, 200, TOKEN_A, URL_A) == 100
        identity = json.loads((root / "capture_identity.json").read_text())
        assert identity["token"] == TOKEN_A and identity["query_schema"] == QUERY_SCHEMA
    print("PASS: P1-01 immutable HyperSync outdir identity and legal capture coexistence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
