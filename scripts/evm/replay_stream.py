#!/usr/bin/env python3
"""EVM 亿级流式重放（replay_duck 的 no-materialize 变体）——pass1 等价产物。

## 何时用这个而不是 replay_duck.py

`replay_duck.py` 的 build_events 会 `CREATE TABLE raw_rows` + `CREATE TABLE events`
**把全量行物化两次**；data-pipeline-evm-recon §12 已记录该瓶颈（QUQ 1.03 亿行 temp
需求 >114.5GiB，本机三跑三败，标注"待修"）。样本达到**亿级、或可用磁盘不足样本
体积 4 倍**时，标准路径不可行——用本脚本。

实测（KOGE(BSC) 3.595 亿行 / M3 16GB / 可用盘 47GB）：**185 秒完成**，峰值内存
2.4GB，temp 全程 0 字节。同机 replay_duck 无法完成。

原理：hash aggregate 的内存需求由"行数级"降到"唯一地址数级"——不物化任何中间
表，直接对 parquet 流式聚合。字段解码与产物口径**逐字对齐 replay_duck**。

## 前提：去重可跳过（必须先验证！）

本脚本不做 events 层去重。合法性前提是"去重键无重复"，**开跑前必须验证**：
`(block_number, tx, log_index)` 的 block 分量决定分段 → 跨段不可能重复，故
"把全块空间切 N 段、逐段 GROUP BY 查重"等价于全局查重但零 shuffle：

    --verify-dedup       # 内置，默认开；8 段扫 3.6 亿行实测 87 秒

单 run 采集通常零重复；多 run 拼接或断点续拉过的数据**必须**跑这一步，
发现重复即退回 replay_duck（或先做块界感知合并）。

## 用法

    python3 replay_stream.py --channels channels.json --out-dir data [--mem-limit 7GB]

channels.json 与 replay_duck 同格式（path 为 v2 采集根目录）。多通道时各段并集
处理；**通道间若有块区间重叠，本脚本会拒绝运行**（重叠意味着需要去重）。

## 产物（与 replay_duck pass1 同名同格式）

    <out>/balances_final.json   {addr: wei_str}，仅非零
    <out>/mint_ledger.json      {addr: wei_str}，from=0x0 的 to 侧汇总
    <out>/replay_stats.json     契约键与 replay_duck 一致（+ engine/dedup 说明）
    <out>/inflow.json           {addr: wei_str} 累计流入（峰值预筛的一级恒等上界）
    <out>/addr_meta.json        {addr: [first_blk, last_blk]}
    <out>/blockts.parquet       block_number -> ts_i，供 peaks_daily.py 等下游复用

⚠ 峰值（peaks.json）不由本脚本产出——亿级块末窗口同样会爆盘，用配套的
`peaks_daily.py`（两级口径：日末峰值 + 日内恒等上界）。

⚠ **等价性回归待补**：本脚本尚未与 replay_duck 做黄金基准对表（KOGE 案无小样本
基准可用）。首次用于新标的时，建议取一个 ≤200 万行的块区间两引擎各跑一次，比对
balances_final / mint_ledger / stats 的 supply 三键后再放量。

（来源：KOGE(BSC) 3.595 亿行分析，2026-07-25）
"""
import argparse
import json
import os
import sys
import time

import duckdb

Z = "0x" + "0" * 40
DEAD = "0x000000000000000000000000000000000000dead"

# 与 replay_duck._v2_select 完全一致的 value 解码（两段 HUGEINT，禁 VARINT 乘法）
VAL = ("CASE WHEN data IS NULL OR data IN ('','0x') THEN 0::HUGEINT ELSE "
       "('0x'||substr(data,35,16))::UBIGINT::HUGEINT * '18446744073709551616'::HUGEINT "
       "+ ('0x'||substr(data,51,16))::UBIGINT::HUGEINT END")


def _logs_glob(path):
    return os.path.join(path, "run_*", "logs.parquet")


def _blocks_glob(path):
    return os.path.join(path, "run_*", "blocks.parquet")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channels", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--mem-limit", default="7GB")
    ap.add_argument("--threads", type=int, default=5)
    ap.add_argument("--temp-dir", default=None)
    ap.add_argument("--verify-dedup", dest="verify", action="store_true", default=True)
    ap.add_argument("--no-verify-dedup", dest="verify", action="store_false")
    ap.add_argument("--dedup-segments", type=int, default=8)
    a = ap.parse_args()

    chans = json.load(open(a.channels))["channels"]
    lo = min(c["lo"] for c in chans)
    hi = max(c["hi"] for c in chans)
    # 通道块区间重叠 → 需要去重 → 本脚本不适用
    spans = sorted((c["lo"], c["hi"]) for c in chans)
    for (a1, b1), (a2, b2) in zip(spans, spans[1:]):
        if a2 < b1:
            sys.exit(f"[fail-closed] 通道块区间重叠 [{a1},{b1}) vs [{a2},{b2})——"
                     f"存在去重需求，请改用 replay_duck.py 或先做块界感知合并")

    os.makedirs(a.out_dir, exist_ok=True)
    tmp = a.temp_dir or os.path.join(a.out_dir, ".duck_tmp")
    os.makedirs(tmp, exist_ok=True)

    con = duckdb.connect()
    con.execute(f"SET memory_limit='{a.mem_limit}'")
    con.execute(f"SET threads={a.threads}")
    con.execute(f"SET temp_directory='{tmp}'")
    con.execute("SET preserve_insertion_order=false")
    t0 = time.time()

    raw_parts = [f"SELECT *, {int(c['lo'])}::BIGINT __lo, {int(c['hi'])}::BIGINT __hi, "
                 f"'{c['tag']}' __tag FROM read_parquet('{_logs_glob(c['path'])}', union_by_name=true)"
                 for c in chans]
    RAW = "(" + " UNION ALL ".join(raw_parts) + ")"
    READ = f"(SELECT * EXCLUDE (__lo,__hi,__tag) FROM {RAW} " \
           "WHERE block_number >= __lo AND block_number < __hi)"

    # ── 0. fail-closed 前置探测（对齐 _v2_probe + build_events 的 reject 记账）──
    n_src, n_bad, n_hi, n_of, n_seg = con.execute(f"""
        SELECT COUNT(*),
               COUNT(*) FILTER (WHERE block_number IS NULL OR log_index IS NULL
                    OR (data IS NOT NULL AND data NOT IN ('','0x') AND LENGTH(data) <> 66)),
               COUNT(*) FILTER (WHERE data IS NOT NULL AND LENGTH(data)=66
                    AND substr(data,3,32) <> repeat('0',32)),
               COUNT(*) FILTER (WHERE data IS NOT NULL AND LENGTH(data)=66
                    AND ('0x'||substr(data,35,16))::UBIGINT >= 9223372036854775808),
               COUNT(*) FILTER (WHERE block_number IS NOT NULL
                    AND (block_number < __lo OR block_number >= __hi))
        FROM {RAW}""").fetchone()
    print(f"[probe] rows={n_src:,} bad_fields={n_bad} hi32_nonzero={n_hi} "
          f"hi64_overflow={n_of} out_of_segment={n_seg}  {time.time()-t0:.1f}s", flush=True)
    if n_bad or n_seg:
        receipt = {"engine": "replay_stream.py (no-materialize variant)",
                   "n_source_rows": n_src, "n_bad_fields": n_bad,
                   "n_out_of_segment": n_seg, "gate_pass": False,
                   "failure": "rejected_input_rows",
                   "policy": "n_bad_fields == 0 and n_out_of_segment == 0"}
        json.dump(receipt, open(f"{a.out_dir}/replay_stats.json", "w"), indent=1)
        sys.exit(f"[fail-closed] 输入含 rejected rows: bad_fields={n_bad} "
                 f"out_of_segment={n_seg}——修复或重新采集后再重放")
    if n_hi or n_of:
        sys.exit("[fail-closed] value 超两段 HUGEINT 安全域，需切 VARINT 路径")

    # ── 0b. 块界感知去重验证 ──
    n_dup = None
    if a.verify:
        t = time.time()
        n_dup = 0
        step = max(1, (hi - lo) // a.dedup_segments)
        for i in range(a.dedup_segments):
            s0 = lo + i * step
            s1 = hi if i == a.dedup_segments - 1 else s0 + step
            n_dup += con.execute(f"""SELECT COUNT(*) FROM (
                SELECT block_number, transaction_hash, log_index FROM {READ}
                WHERE block_number >= {s0} AND block_number < {s1}
                GROUP BY 1,2,3 HAVING COUNT(*) > 1)""").fetchone()[0]
        print(f"[dedup] {a.dedup_segments} 段全跨度重复键 = {n_dup}  {time.time()-t:.1f}s", flush=True)
        if n_dup:
            sys.exit(f"[fail-closed] 发现 {n_dup} 个重复去重键——本脚本不做去重，"
                     f"请改用 replay_duck.py")

    con.execute(f"""CREATE VIEW ev AS
        SELECT block_number b, log_index li,
               '0x'||right(lower(COALESCE(topic1, repeat('0',64))),40) frm,
               '0x'||right(lower(COALESCE(topic2, repeat('0',64))),40) t2,
               {VAL} v
        FROM {READ}
        WHERE block_number IS NOT NULL AND log_index IS NOT NULL
          AND (data IS NULL OR data IN ('','0x') OR LENGTH(data)=66)
          """)

    # ── 1. 余额（deltas 口径逐字对齐 replay_duck：to 侧 +v 含 mint；from 侧 -v 排除 0x0）──
    t = time.time()
    con.execute(f"""CREATE TABLE bal AS
        SELECT a, SUM(d)::HUGEINT s FROM (
            SELECT t2 a, v d FROM ev
            UNION ALL
            SELECT frm, -v FROM ev WHERE frm <> '{Z}') GROUP BY a""")
    n_addr = con.execute("SELECT COUNT(*) FROM bal").fetchone()[0]
    print(f"[bal] unique_addrs={n_addr:,}  {time.time()-t:.1f}s", flush=True)

    # ── 2. mint / burn / 供给闭合 ──
    t = time.time()
    mint_total = int(con.execute(f"SELECT COALESCE(SUM(v),0)::HUGEINT FROM ev WHERE frm='{Z}'").fetchone()[0])
    burn_total = int(con.execute(f"SELECT COALESCE(SUM(v),0)::HUGEINT FROM ev WHERE t2 IN ('{Z}','{DEAD}')").fetchone()[0])
    su = int(con.execute("SELECT COALESCE(SUM(s),0)::HUGEINT FROM bal").fetchone()[0])
    neg = con.execute("SELECT COUNT(*) FROM bal WHERE s<0").fetchone()[0]
    n_events = con.execute("SELECT COUNT(*) FROM ev").fetchone()[0]
    print(f"[supply] mint={mint_total} burn={burn_total} sum_bal={su} neg={neg} "
          f"closed={su == mint_total}  {time.time()-t:.1f}s", flush=True)

    # ── 3. first/last 活跃块 + 累计流入（峰值一级预筛的恒等上界）──
    t = time.time()
    con.execute(f"""CREATE TABLE addr_meta AS
        SELECT a, MIN(b) first_blk, MAX(b) last_blk FROM (
            SELECT frm a, b FROM ev WHERE frm <> '{Z}'
            UNION ALL SELECT t2, b FROM ev WHERE t2 <> '{Z}') GROUP BY a""")
    con.execute("CREATE TABLE inflow AS SELECT t2 a, SUM(v)::HUGEINT inv FROM ev GROUP BY t2")
    print(f"[meta] addr_meta+inflow  {time.time()-t:.1f}s", flush=True)

    # ── 4. 块->时间戳映射（下游日序列/图表复用）──
    t = time.time()
    block_parts = [f"SELECT * FROM read_parquet('{_blocks_glob(c['path'])}', union_by_name=true) "
                   f"WHERE number >= {int(c['lo'])} AND number < {int(c['hi'])}" for c in chans]
    bsrc = "(" + " UNION ALL ".join(block_parts) + ")"
    con.execute(f"""COPY (SELECT number::BIGINT block_number,
                        TRY_CAST(ANY_VALUE(timestamp) AS UBIGINT)::BIGINT ts_i
                    FROM {bsrc}
                    WHERE number IS NOT NULL GROUP BY number)
                  TO '{a.out_dir}/blockts.parquet' (FORMAT parquet)""")
    nb = con.execute(f"SELECT COUNT(*) FROM read_parquet('{a.out_dir}/blockts.parquet')").fetchone()[0]
    print(f"[blockts] blocks={nb:,}  {time.time()-t:.1f}s", flush=True)

    # ── 5. 落盘 ──
    t = time.time()
    json.dump({x: str(int(s)) for x, s in con.execute("SELECT a,s FROM bal WHERE s<>0").fetchall()},
              open(f"{a.out_dir}/balances_final.json", "w"))
    json.dump({x: str(int(s)) for x, s in con.execute(
        f"SELECT t2, SUM(v)::HUGEINT FROM ev WHERE frm='{Z}' GROUP BY t2").fetchall()},
        open(f"{a.out_dir}/mint_ledger.json", "w"))
    json.dump({x: str(int(v)) for x, v in con.execute("SELECT a,inv FROM inflow").fetchall()},
              open(f"{a.out_dir}/inflow.json", "w"))
    json.dump({x: [fb, lb] for x, fb, lb in
               con.execute("SELECT a,first_blk,last_blk FROM addr_meta").fetchall()},
              open(f"{a.out_dir}/addr_meta.json", "w"))

    stats = {"engine": "replay_stream.py (no-materialize variant)",
             "events": n_events, "n_source_rows": n_src, "n_bad_fields": n_bad,
             "n_out_of_segment": n_seg, "n_dedup_removed": 0,
             "dedup_verified_segments": a.dedup_segments if a.verify else None,
             "dedup_duplicate_keys": n_dup,
             "mint_total_wei": str(mint_total), "burn_total_wei": str(burn_total),
             "sum_balances_wei": str(su), "supply_check_ok": su == mint_total,
             "neg_balance_addrs": neg, "unique_addrs": n_addr,
             "gate_pass": su == mint_total and neg == 0,
             "block_range": list(con.execute("SELECT MIN(b),MAX(b) FROM ev").fetchone()),
             "elapsed_s": round(time.time() - t0, 1)}
    json.dump(stats, open(f"{a.out_dir}/replay_stats.json", "w"), indent=1)
    print(f"[write] {time.time()-t:.1f}s", flush=True)
    print(json.dumps(stats, indent=1))
    if not stats["gate_pass"]:
        sys.exit(4)   # 与 replay_duck 一致：供给闭合 gate 挂 → exit 4


if __name__ == "__main__":
    main()
