#!/usr/bin/env python3
"""2026-08-04 review regressions: P0-01 channel provenance and P0-02 freshness."""
from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
EVM = HERE.parent / "evm"
REPORT = HERE.parent / "report"
MAKE_RECEIPT = EVM / "make_channel_receipt.py"
REPRODUCE = REPORT / "reproduce_receipt.py"
TOKEN_A = "0x" + "a" * 40
TOKEN_B = "0x" + "b" * 40


def run(*args, cwd=None):
    return subprocess.run([sys.executable, *map(str, args)], cwd=cwd,
                          capture_output=True, text=True)


def write_csv(path: Path, rows=1):
    path.write_text(
        "block,ts,tx,log_index,from,to,value_raw,block_hash\n" +
        "".join(f"5,1,0xtx{i},{i},0x{'0'*40},0x{'1'*40},1,0xhash\n"
                for i in range(rows)), encoding="utf-8")


def test_p001_legacy_csv_cannot_self_attest(root: Path):
    data = root / "one-row.csv"
    write_csv(data)
    out = root / "receipt.json"
    p = run(MAKE_RECEIPT, "--data", data, "--format", "v1csv",
            "--token", TOKEN_B, "--lo", 0, "--hi", 100, "--tag", "legacy",
            "--out", out)
    assert p.returncode == 2, p.stdout + p.stderr
    assert not out.exists(), "无 token 字段/采集回执的 CSV 不得取得正式 PASS receipt"

    empty = root / "empty.csv"
    write_csv(empty, rows=0)
    p = run(MAKE_RECEIPT, "--data", empty, "--format", "v1csv",
            "--token", TOKEN_A, "--lo", 0, "--hi", 100, "--tag", "empty",
            "--empty-proof", "ok", "--out", out)
    assert p.returncode == 2 and not out.exists(), p.stdout + p.stderr


def _meta(path, block_col):
    import duckdb
    con = duckdb.connect()
    rows, lo, hi = con.execute(
        f"SELECT COUNT(*), MIN({block_col}), MAX({block_col}) FROM read_parquet(?)",
        [str(path)]).fetchone()
    con.close()
    return {"size": path.stat().st_size, "rows": rows, "min_block": lo,
            "max_block": hi, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def _v2_run(root: Path, token=TOKEN_A, query_schema="erc20-transfer-fields/v2"):
    import duckdb
    run_dir = root / "run_0"
    run_dir.mkdir(parents=True)
    con = duckdb.connect()
    con.execute("CREATE TABLE logs(block_number BIGINT, block_hash VARCHAR, log_index BIGINT, "
                "transaction_hash VARCHAR, topic1 VARCHAR, topic2 VARCHAR, data VARCHAR)")
    con.execute("INSERT INTO logs VALUES (5,'0xh',0,'0xt','0x1','0x2','0x3')")
    con.execute(f"COPY logs TO '{run_dir / 'logs.parquet'}' (FORMAT parquet)")
    con.execute("CREATE TABLE blocks(number BIGINT, timestamp BIGINT)")
    con.execute("INSERT INTO blocks VALUES (5,1)")
    con.execute(f"COPY blocks TO '{run_dir / 'blocks.parquet'}' (FORMAT parquet)")
    con.close()
    done = {"schema": "hypersync-v2-done/v3", "query_schema": query_schema,
            "capture_from": 0, "from_block": 0, "to_block": 100, "next_block": 100,
            "token": token, "url": "https://bsc.hypersync.xyz",
            "files": {"logs.parquet": _meta(run_dir / "logs.parquet", "block_number"),
                      "blocks.parquet": _meta(run_dir / "blocks.parquet", "number")}}
    (run_dir / "done.json").write_text(json.dumps(done), encoding="utf-8")
    return run_dir


def test_round4_csv_prefix_and_cursor_fail_closed(root: Path):
    sys.path.insert(0, str(EVM))
    import fetch_hypersync as collector

    class Response:
        status_code = 200
        text = ""
        def __init__(self, nxt): self.nxt = nxt
        def json(self):
            return {"data": [], "next_block": self.nxt, "archive_height": 100}

    def invoke(out, receipt, nxt, preexisting=False):
        if preexisting:
            write_csv(out)
        collector.requests.post = lambda *a, **k: Response(nxt)
        old = sys.argv
        token_file = root / "hypersync.token"
        token_file.write_text("secret\n", encoding="utf-8")
        sys.argv = ["fetch_hypersync.py", "0", "--token-file", str(token_file),
                    "--token-addr", TOKEN_A,
                    "--url", "https://fixture/query", "--out", str(out),
                    "--to-block", "100", "--receipt", str(receipt), "--sleep", "0"]
        try:
            result = collector.main()
            return int(result) if isinstance(result, int) else 0
        except SystemExit as exc:
            return int(exc.code) if isinstance(exc.code, int) else 2
        finally:
            sys.argv = old

    out, receipt = root / "prefix.csv", root / "prefix.collector.json"
    assert invoke(out, receipt, 100, preexisting=True) != 0 and not receipt.exists(), \
        "unreceipted existing prefix must never receive formal PASS"
    out2, receipt2 = root / "none.csv", root / "none.collector.json"
    assert invoke(out2, receipt2, None) != 0 and not receipt2.exists(), \
        "missing provider next_block must fail closed"
    out3, receipt3 = root / "stalled.csv", root / "stalled.collector.json"
    assert invoke(out3, receipt3, 0) != 0 and not receipt3.exists(), \
        "non-progress cursor must fail closed"


def test_p001_v2_done_identity_and_completion(root: Path):
    data = root / "v2"
    run_dir = _v2_run(data)
    sys.path.insert(0, str(EVM))
    from fetch_hypersync_v2 import ensure_outdir_identity
    ensure_outdir_identity(data, TOKEN_A, "https://bsc.hypersync.xyz")
    out = root / "v2.receipt.json"
    p = run(MAKE_RECEIPT, "--data", data, "--format", "v2", "--token", TOKEN_A,
            "--lo", 0, "--hi", 100, "--tag", "v2", "--out", out)
    assert p.returncode == 0, p.stdout + p.stderr

    done_path = run_dir / "done.json"
    done = json.loads(done_path.read_text())
    done["token"] = TOKEN_B
    done_path.write_text(json.dumps(done))
    out.unlink()
    p = run(MAKE_RECEIPT, "--data", data, "--format", "v2", "--token", TOKEN_A,
            "--lo", 0, "--hi", 100, "--tag", "v2", "--out", out)
    assert p.returncode == 2 and not out.exists(), p.stdout + p.stderr

    done["token"] = TOKEN_A
    done["query_schema"] = "wrong-query"
    done_path.write_text(json.dumps(done))
    p = run(MAKE_RECEIPT, "--data", data, "--format", "v2", "--token", TOKEN_A,
            "--lo", 0, "--hi", 100, "--tag", "v2", "--out", out)
    assert p.returncode == 2 and not out.exists(), p.stdout + p.stderr


def _base_case(root: Path, script: str):
    (root / "audit_input_manifest.json").write_text("{}\n", encoding="utf-8")
    (root / "reproduce_audit.py").write_text(script, encoding="utf-8")
    return root / "reproduce_output.json"


def test_p002_stale_noop_touch_symlink_replace(root: Path):
    output = _base_case(root, "pass\n")
    output.write_text('{"summary":{"stale":true}}\n', encoding="utf-8")
    p = run(REPRODUCE, root)
    assert p.returncode == 2, p.stdout + p.stderr

    output.unlink(missing_ok=True)
    (root / "reproduce_audit.py").write_text(
        "from pathlib import Path\nPath('reproduce_output.json').touch()\n", encoding="utf-8")
    p = run(REPRODUCE, root)
    assert p.returncode == 2, p.stdout + p.stderr

    target = root / "elsewhere.json"
    target.write_text('{"summary":{"bad":true}}\n', encoding="utf-8")
    output.unlink(missing_ok=True)
    output.symlink_to(target)
    (root / "reproduce_audit.py").write_text("pass\n", encoding="utf-8")
    p = run(REPRODUCE, root)
    assert p.returncode == 2, p.stdout + p.stderr
    output.unlink()

    (root / "reproduce_audit.py").write_text(
        "import json, os\n"
        "p=os.environ['CHIP_REPRODUCE_OUTPUT']\n"
        "open(p,'w').write('{}')\n"
        "os.unlink(p)\n"
        "json.dump({'summary':{'replacement':True}},open(p,'w'))\n", encoding="utf-8")
    p = run(REPRODUCE, root)
    assert p.returncode == 2, p.stdout + p.stderr


def main():
    with tempfile.TemporaryDirectory() as td:
        test_p001_legacy_csv_cannot_self_attest(Path(td))
    with tempfile.TemporaryDirectory() as td:
        test_round4_csv_prefix_and_cursor_fail_closed(Path(td))
    with tempfile.TemporaryDirectory() as td:
        test_p001_v2_done_identity_and_completion(Path(td))
    with tempfile.TemporaryDirectory() as td:
        test_p002_stale_noop_touch_symlink_replace(Path(td))
    print("PASS: P0-01 collector provenance + P0-02 reproduce freshness regressions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
