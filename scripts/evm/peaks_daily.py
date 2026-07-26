#!/usr/bin/env python3
"""EVM 峰值持仓 · 日级两级口径（亿级样本 / 刷量盘的块末窗口替代件）。

## 何时用这个而不是 replay_duck 的块末窗口

`replay_duck` 的峰值走 `(addr, block)` 聚合 + `PARTITION BY addr ORDER BY block`
窗口。**刷量盘上这条路会爆盘**：KOGE(BSC) 3.595 亿行实测，一级 inflow 预筛
（≥0.1% 供应）后仍剩 157,459 个候选，块级 dd 表 3 分钟吃掉 19GB temp、直奔
磁盘耗尽。改日级后 6,217 候选 / 734,079 行 / **164 秒**全部完成。

## 两级口径（判级不失真）

    L1 日末峰值 = 候选地址逐日净变动累积后的日末最大值（主口径）
    L2 日内上界 = Σ max(day_delta, 0) ≥ 任意时刻真实峰值（恒等上界，全整数）

判级用 L1；凡 L1 未达某门槛但 L2 达到者 → 落入 `needs_block_precision.json`，
对这批（通常只有个位数）再单独跑块级精确值即可。**只会多查不会漏查。**

粗粒度的代价是日内脉冲被平滑（峰值可能低估），与 playbook-entity-cluster-tiering
「月末快照粒度天然满足 sig 原子化，但峰值可能被平滑低估」是同一权衡；L2 上界正是
用来兜住这个代价的。

## 候选门槛按"判级需求"定，不要照抄 0.1%

恒等式保证：任意时刻持仓 ≤ 累计流入，故峰值 ≥ pct 的地址必在 `inflow ≥ pct` 内。
判级实际只需要 ≥1%（其他大户线）以上。KOGE 实测：≥0.1% 有 131,833 址、**≥1% 只有
6,217 址，差 21 倍**——刷量盘尤其悬殊（大量地址累计流入巨大但持仓恒为 0）。
默认 `--pct 0.01`；需要更细的阴性排查再调低。

## 用法

    python3 peaks_daily.py --logs <v2目录> --blockts <blockts.parquet> \
        --total-supply-wei <wei> --out-dir data [--pct 0.01]

`blockts.parquet` 由 replay_stream.py 产出（列：block_number, ts_i）。

## 产物

    <out>/daily_delta.parquet        (addr, day, delta) 候选地址日净变动
                                     —— 同时就是阵营/实体日序列的原料
    <out>/peaks_daily.json           {addr: {peak_daily, peak_day, upper_bound, last_bal}}
    <out>/needs_block_precision.json {门槛: [需补块级精确值的地址]}
    <out>/peaks_summary.json

（来源：KOGE(BSC) 3.595 亿行分析，2026-07-25）
"""
import argparse
import json
import os
import time

import duckdb

Z = "0x" + "0" * 40
VAL = ("CASE WHEN data IS NULL OR data IN ('','0x') THEN 0::HUGEINT ELSE "
       "('0x'||substr(data,35,16))::UBIGINT::HUGEINT * '18446744073709551616'::HUGEINT "
       "+ ('0x'||substr(data,51,16))::UBIGINT::HUGEINT END")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", required=True, help="v2 采集根目录（含 run_*/logs.parquet）")
    ap.add_argument("--blockts", required=True, help="replay_stream 产出的 blockts.parquet")
    ap.add_argument("--total-supply-wei", required=True, type=int)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--pct", type=float, default=0.01, help="候选门槛（占总供应），默认 1%%")
    ap.add_argument("--levels", default="0.01,0.05,0.10,0.20", help="需要复查的判级门槛")
    ap.add_argument("--mem-limit", default="6GB")
    ap.add_argument("--threads", type=int, default=4)
    a = ap.parse_args()

    TOT = a.total_supply_wei
    th = int(TOT * a.pct)
    os.makedirs(a.out_dir, exist_ok=True)
    tmp = os.path.join(a.out_dir, ".duck_tmp")
    os.makedirs(tmp, exist_ok=True)

    con = duckdb.connect()
    con.execute(f"SET memory_limit='{a.mem_limit}'")
    con.execute(f"SET threads={a.threads}")
    con.execute(f"SET temp_directory='{tmp}'")
    con.execute("SET preserve_insertion_order=false")
    t0 = time.time()

    READ = f"read_parquet('{os.path.join(a.logs, 'run_*', 'logs.parquet')}', union_by_name=true)"
    con.execute(f"""CREATE VIEW ev AS
        SELECT block_number b,
               '0x'||right(lower(COALESCE(topic1, repeat('0',64))),40) frm,
               '0x'||right(lower(COALESCE(topic2, repeat('0',64))),40) t2,
               {VAL} v
        FROM {READ}
        WHERE block_number IS NOT NULL AND log_index IS NOT NULL
          AND (data IS NULL OR data IN ('','0x') OR LENGTH(data)=66)""")

    t = time.time()
    con.execute(f"""CREATE TABLE cand AS
        SELECT t2 a FROM ev GROUP BY t2 HAVING SUM(v)::HUGEINT >= {th}""")
    n = con.execute("SELECT COUNT(*) FROM cand").fetchone()[0]
    print(f"[cand] 累计流入 >= {a.pct*100:.3f}% 总供应: {n:,} 址  {time.time()-t:.1f}s", flush=True)

    t = time.time()
    con.execute(f"""CREATE TABLE bts AS
        SELECT block_number, strftime(make_timestamp((ts_i*1000000)::BIGINT), '%Y-%m-%d') d
        FROM read_parquet('{a.blockts}')""")
    con.execute(f"""CREATE TABLE dd AS
        SELECT a, d, SUM(x)::HUGEINT delta FROM (
            SELECT e.t2 a, bts.d d, e.v x FROM ev e JOIN bts ON bts.block_number = e.b
              WHERE e.t2 IN (SELECT a FROM cand)
            UNION ALL
            SELECT e.frm, bts.d, -e.v FROM ev e JOIN bts ON bts.block_number = e.b
              WHERE e.frm <> '{Z}' AND e.frm IN (SELECT a FROM cand)
        ) GROUP BY a, d""")
    ndd = con.execute("SELECT COUNT(*) FROM dd").fetchone()[0]
    print(f"[dd] 日级行 {ndd:,}  {time.time()-t:.1f}s", flush=True)
    con.execute(f"""COPY (SELECT a, d "day", delta::VARCHAR delta FROM dd ORDER BY a, d)
                  TO '{a.out_dir}/daily_delta.parquet' (FORMAT parquet)""")

    t = time.time()
    rows = con.execute("""
        SELECT a, MAX(cum)::VARCHAR peak, ARG_MAX(d, cum) peak_day,
               MAX(ub)::VARCHAR upper_bound, LAST(cum ORDER BY d)::VARCHAR last_bal
        FROM (SELECT a, d,
                     SUM(delta) OVER (PARTITION BY a ORDER BY d
                          ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) cum,
                     SUM(GREATEST(delta,0)) OVER (PARTITION BY a ORDER BY d
                          ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) ub
              FROM dd)
        GROUP BY a""").fetchall()
    res = {x: {"peak_daily": p, "peak_day": pd, "upper_bound": ub, "last_bal": lb}
           for x, p, pd, ub, lb in rows}
    json.dump(res, open(f"{a.out_dir}/peaks_daily.json", "w"))
    print(f"[peak] {len(res):,} 址日末峰值+上界  {time.time()-t:.1f}s", flush=True)

    need = {}
    for lvl in [float(x) for x in a.levels.split(",")]:
        g = int(TOT * lvl)
        hit = [x for x, v in res.items() if int(v["peak_daily"]) < g <= int(v["upper_bound"])]
        need[f"{lvl:.4f}"] = hit
        ok = sum(1 for v in res.values() if int(v["peak_daily"]) >= g)
        print(f"  门槛 {lvl*100:>6.2f}%: 日末达标 {ok:>5} 址；"
              f"日末未达但上界达标（需块级精确）{len(hit):>5} 址", flush=True)
    json.dump(need, open(f"{a.out_dir}/needs_block_precision.json", "w"), indent=1)

    summary = {"engine": "peaks_daily.py", "cand_pct": a.pct, "cand_threshold_wei": str(th),
               "candidates": n, "daily_rows": ndd, "peaks_recorded": len(res),
               "levels_checked": a.levels, "elapsed_s": round(time.time() - t0, 1)}
    json.dump(summary, open(f"{a.out_dir}/peaks_summary.json", "w"), indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
