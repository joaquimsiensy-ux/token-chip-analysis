#!/usr/bin/env python3
"""新旧重放引擎等价性性质测试（hypothesis 随机边角数据，A1 回归门禁的活体部分）。

随机生成转账流——覆盖 mint / burn(0x0+dead) / 自转 / 同块多事件 / value=0 /
大整数 / 无序阵营映射 / 负余额盘(gate fail 场景)——同一语义事件盘分别喂给
旧引擎（replay_pass1+replay_pass2）、DuckDB 引擎（replay_duck）与流式引擎
（replay_stream），gate 值与退出码三引擎全等；仅 gate PASS 才对表正式 pass2 产物。
另保留一例超 HUGEINT 的 VARINT 确定性对表（pass1 vs replay_duck；stream 的声明
安全域不含 VARINT）。

已知有意行为差异（不在等价断言范围）：
  - 同 (tag,tx,li) 键不同内容：旧=静默 keep-last，新=fail-closed 硬退（生成器不生成此类）
  - 新引擎 replay_stats 多 reject 记账扩展字段（契约键对比时忽略）
环境无 duckdb 时整测试 SKIP（离线全家桶不因缺依赖挂）。
用法：python3 scripts/tests/test_engine_equivalence.py   （约 30-60 秒）
"""
import datetime, hashlib, json, os, subprocess, sys, tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
EVM = os.path.join(HERE, "..", "evm")
sys.path.insert(0, EVM)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "bench"))
from evm_channel_fixture import write_csv_channel_receipt

try:
    import duckdb  # noqa: F401
except ImportError:
    print("SKIP: duckdb 未安装，等价性测试跳过")
    sys.exit(0)
try:
    from hypothesis import given, settings, strategies as st, HealthCheck
except ImportError:
    print("SKIP: hypothesis 未安装，等价性测试跳过")
    sys.exit(0)

import golden_baseline as gb

Z = "0x0000000000000000000000000000000000000000"
DEAD = "0x000000000000000000000000000000000000dead"
ADDRS = [f"0x{i:040x}" for i in range(0xa1, 0xa7)]   # 6 个普通地址


def _write_inputs(tmp, events):
    """events: [(from,to,value,block_step)] -> v1 7列 CSV + channels/camps。"""
    rows, blk, li = [], 100, 0
    day0 = datetime.date(2026, 1, 1)
    for frm, to, val, step in events:
        blk += step
        ts = (day0 + datetime.timedelta(days=blk // 4)).isoformat() + "T12:00:00"
        tx = f"0x{li:064x}"
        rows.append((blk, ts, tx, frm, to, val, f"{tx}:log:{li}"))
        li += 1
    with open(os.path.join(tmp, "transfers.csv"), "w") as f:
        f.write("block,ts,tx,from,to,value,uniqueId\n")
        for r in rows:
            f.write(",".join(str(x) for x in r) + "\n")
    write_csv_channel_receipt(tmp, "t", Path(tmp) / "transfers.csv",
                              ADDRS[0], 0, 99999999999)
    json.dump({"schema": "evm-channels/v2", "token": ADDRS[0],
               "expected_from": 0, "expected_to": 99999999999,
               "channels": [{"path": "transfers.csv", "lo": 0,
                             "hi": 99999999999, "tag": "t", "format": "v1csv",
                             "receipt": "t.receipt.json"}]},
              open(os.path.join(tmp, "channels.json"), "w"))
    json.dump({"camps": {"阵营A": [ADDRS[0], ADDRS[1]], "阵营B": [ADDRS[2]],
                         "销毁": [DEAD]},
               "entities": {"实体X": [ADDRS[1], ADDRS[2]]}},
              open(os.path.join(tmp, "camps.json"), "w"))


def _parquet_meta(path, block_col):
    con = duckdb.connect()
    rows, lo, hi = con.execute(
        f"SELECT COUNT(*), MIN({block_col}), MAX({block_col}) FROM read_parquet(?)",
        [str(path)]).fetchone()
    con.close()
    return {"size": path.stat().st_size, "rows": rows, "min_block": lo,
            "max_block": hi, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def _write_v2_inputs(tmp, events):
    """Mirror the semantic event list into a formally receipted v2 parquet channel."""
    root = Path(tmp) / "v2_input"
    run_dir = root / "run_0"
    run_dir.mkdir(parents=True)
    con = duckdb.connect()
    con.execute("CREATE TABLE logs(block_number BIGINT, block_hash VARCHAR, "
                "log_index BIGINT, transaction_hash VARCHAR, topic1 VARCHAR, "
                "topic2 VARCHAR, data VARCHAR)")
    con.execute("CREATE TABLE blocks(number BIGINT, timestamp BIGINT)")
    blk, li = 100, 0
    seen_blocks = set()
    for frm, to, val, step in events:
        blk += step
        tx = f"0x{li:064x}"
        con.execute("INSERT INTO logs VALUES (?,?,?,?,?,?,?)", [
            blk, f"0x{blk:064x}", li, tx,
            "0x" + "0" * 24 + frm[2:], "0x" + "0" * 24 + to[2:],
            "0x" + f"{val:064x}",
        ])
        if blk not in seen_blocks:
            con.execute("INSERT INTO blocks VALUES (?,?)", [blk, 1700000000 + blk])
            seen_blocks.add(blk)
        li += 1
    con.execute(f"COPY logs TO '{run_dir / 'logs.parquet'}' (FORMAT parquet)")
    con.execute(f"COPY blocks TO '{run_dir / 'blocks.parquet'}' (FORMAT parquet)")
    con.close()

    url = "https://fixture.hypersync.xyz"
    from fetch_hypersync_v2 import QUERY_SCHEMA, ensure_outdir_identity
    ensure_outdir_identity(root, ADDRS[0], url)
    done = {
        "schema": "hypersync-v2-done/v3", "query_schema": QUERY_SCHEMA,
        "capture_from": 0, "from_block": 0, "to_block": 99999999999,
        "next_block": 99999999999, "token": ADDRS[0], "url": url,
        "files": {
            "logs.parquet": _parquet_meta(run_dir / "logs.parquet", "block_number"),
            "blocks.parquet": _parquet_meta(run_dir / "blocks.parquet", "number"),
        },
    }
    (run_dir / "done.json").write_text(json.dumps(done), encoding="utf-8")
    receipt = Path(tmp) / "v2.receipt.json"
    made = _run(tmp, [os.path.join(EVM, "make_channel_receipt.py"),
                      "--data", root, "--format", "v2", "--token", ADDRS[0],
                      "--lo", "0", "--hi", "99999999999", "--tag", "v2",
                      "--out", receipt])
    assert made.returncode == 0, made.stdout + made.stderr
    manifest = Path(tmp) / "channels_v2.json"
    manifest.write_text(json.dumps({
        "schema": "evm-channels/v2", "token": ADDRS[0],
        "expected_from": 0, "expected_to": 99999999999,
        "channels": [{"path": str(root), "lo": 0, "hi": 99999999999,
                      "tag": "v2", "format": "v2", "receipt": str(receipt)}],
    }), encoding="utf-8")
    return manifest


def _run(tmp, cmd):
    p = subprocess.run([sys.executable] + cmd, cwd=tmp,
                       capture_output=True, text=True, timeout=120)
    return p


# 事件生成：首笔保证 mint>0；hypothesis 公共域受 replay_stream HUGEINT 安全域约束。
_addr = st.sampled_from(ADDRS)
_to_any = st.sampled_from(ADDRS + [Z, DEAD])
_val = st.one_of(st.integers(0, 10**21),
                 st.integers(10**30, 10**34))
_step = st.sampled_from([0, 0, 1, 1, 5])               # 0=同块多事件
_ev = st.tuples(st.sampled_from(ADDRS + [Z]), _to_any, _val, _step)


@settings(max_examples=10, deadline=None,
          suppress_health_check=[HealthCheck.too_slow])
@given(first_mint=st.integers(10**18, 10**22), evs=st.lists(_ev, min_size=0, max_size=40))
def equivalence_case(first_mint, evs):
    events = [(Z, ADDRS[0], first_mint, 1)] + list(evs)
    with tempfile.TemporaryDirectory() as tmp:
        _write_inputs(tmp, events)
        v2_manifest = _write_v2_inputs(tmp, events)
        old_out, new_out = os.path.join(tmp, "old"), os.path.join(tmp, "new")
        stream_out = os.path.join(tmp, "stream")
        os.makedirs(old_out)
        p1 = _run(tmp, [os.path.join(EVM, "replay_pass1.py"),
                        "--channels", "channels.json", "--out-dir", old_out])
        pd = _run(tmp, [os.path.join(EVM, "replay_duck.py"),
                        "--channels", "channels.json", "--out-dir", new_out,
                        "--camps", "camps.json", "--emit-csv",
                        "--threads", "2", "--mem-limit", "2GB"])
        ps = _run(tmp, [os.path.join(EVM, "replay_stream.py"),
                        "--channels", v2_manifest, "--out-dir", stream_out,
                        "--dedup-segments", "2", "--threads", "2",
                        "--mem-limit", "2GB"])
        assert p1.returncode in (0, 4), \
            f"旧 pass1 异常退出:\n{p1.stdout}\n{p1.stderr}"
        assert p1.returncode == pd.returncode == ps.returncode, \
            f"三引擎 gate 退出码不等: pass1={p1.returncode} duck={pd.returncode} " \
            f"stream={ps.returncode}\n输入:{events}\n{ps.stdout}\n{ps.stderr}"
        sa, sb = gb.snapshot(old_out, "old"), gb.snapshot(new_out, "new")
        ss = json.load(open(os.path.join(stream_out, "replay_stats.json")))
        for k in gb.STATS_CONTRACT:
            assert sa["replay_stats"].get(k) == sb["replay_stats"].get(k), \
                f"stats.{k} 不等: {sa['replay_stats'].get(k)} vs {sb['replay_stats'].get(k)}\n输入:{events}"
        assert ss["gate_pass"] == sa["replay_stats"]["gate_pass"], \
            f"stream gate 不等\n输入:{events}"
        for k in ["merged_csv", "balances_final", "peaks", "mint_ledger"]:
            assert sa[k] == sb[k], f"{k} 不等\n输入:{events}"
        p2 = _run(tmp, [os.path.join(EVM, "replay_pass2.py"), "camps.json",
                        "--data-dir", old_out])
        if p1.returncode == 0:
            assert p2.returncode == 0, f"旧 pass2 异常退出:\n{p2.stdout}\n{p2.stderr}"
            sa = gb.snapshot(old_out, "old")
            for k in ["merged_csv", "balances_final", "peaks", "mint_ledger",
                      "camp_series", "entity_series"]:
                assert sa[k] == sb[k], f"{k} 不等\n输入:{events}"
        else:
            assert p2.returncode == 4, p2.stdout + p2.stderr
            formal = ["camp_series.json", "entity_series.json",
                      "camp_series.provenance.json", "entity_series.provenance.json"]
            assert not any(os.path.exists(os.path.join(old_out, n)) for n in formal)
            assert not any(os.path.exists(os.path.join(new_out, n)) for n in formal)
            diag = os.path.join(new_out, "diagnostics", "gate-failed")
            assert all(json.load(open(os.path.join(diag, n)))["status"] ==
                       "DIAGNOSTIC_GATE_FAILED"
                       for n in ("camp_series.json", "entity_series.json"))


def varint_equivalence_case():
    """Keep the >HUGEINT contract covered on the two engines that declare it."""
    events = [(Z, ADDRS[0], 10**45, 1), (ADDRS[0], ADDRS[1], 10**44, 1)]
    with tempfile.TemporaryDirectory() as tmp:
        _write_inputs(tmp, events)
        old_out, new_out = os.path.join(tmp, "old"), os.path.join(tmp, "new")
        os.makedirs(old_out)
        p1 = _run(tmp, [os.path.join(EVM, "replay_pass1.py"),
                        "--channels", "channels.json", "--out-dir", old_out])
        p2 = _run(tmp, [os.path.join(EVM, "replay_pass2.py"), "camps.json",
                        "--data-dir", old_out])
        pd = _run(tmp, [os.path.join(EVM, "replay_duck.py"),
                        "--channels", "channels.json", "--out-dir", new_out,
                        "--camps", "camps.json", "--emit-csv", "--force-varint",
                        "--threads", "2", "--mem-limit", "2GB"])
        assert (p1.returncode, p2.returncode, pd.returncode) == (0, 0, 0), \
            p1.stdout + p1.stderr + p2.stdout + p2.stderr + pd.stdout + pd.stderr
        sa, sb = gb.snapshot(old_out, "old"), gb.snapshot(new_out, "new")
        for k in ["merged_csv", "balances_final", "peaks", "mint_ledger",
                  "camp_series", "entity_series"]:
            assert sa[k] == sb[k], f"VARINT {k} 不等"


def main():
    equivalence_case()
    varint_equivalence_case()
    print("PASS: 三引擎 gate/退出码 10 例 hypothesis 全等；gate PASS 六产物全等；"
          "gate FAIL 正式序列零产物；VARINT 双引擎确定性对表通过")


if __name__ == "__main__":
    main()
