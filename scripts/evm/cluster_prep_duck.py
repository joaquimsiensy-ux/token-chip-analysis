#!/usr/bin/env python3
"""聚类数据准备的 DuckDB 缩图件：亿级 part CSV → 三张聚合 parquet（cluster.py --prep 直读）。

来源：2026-07-22 DuckDB 引擎改造工程（@CX 方案 B6"先缩图,再换库"）。动机：cluster.py
把全量事件装进 rows/seen/edge/deg 四个 Python 容器（codex 点名的内存瓶颈），亿级样本
（QUQ 1.03 亿行）直接不可行；本件把重活（去重/边聚合/度数/行为指纹底数）交给 DuckDB，
cluster.py 只拿聚合结果跑规则判定，语义零变化。

产物（--out-dir 下）：
  edges_agg.parquet   f, t, v(SUM wei 十进制串), cnt          —— R1 边阈值输入
  profile.parquet     addr, fan_in, fan_out, tx_in, tx_out,    —— 守门员指纹底数 + deg
                      inflow, outflow, max_peer_flow, peers     （全整数；retention/
                      top_peer_share 等浮点派生留 cluster.py 端算，防 SQL/Python 舍入口径差）
  bal.parquet         addr, bal(wei 十进制串)

口径与 cluster.py 老路逐条对齐：
  (tx,log_index) 全局去重（老路 seen 集合）；bal 双向累计（含负）；deg=唯一对手数
  （双向去重）；peer_flow 双向合并同一对手（gatekeeper.funnel_profile 同款）。

用法：python3 cluster_prep_duck.py <chain> [--dir 工作目录] [--out-dir data/cluster_prep]
      [--mem-limit 8GB] [--threads 6]
"""
import argparse, glob, json, os, sys

import duckdb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chain")
    ap.add_argument("--dir", default=".", help="工作目录（含 {chain}_part_*.csv）")
    ap.add_argument("--v2", default=None, help="v2 parquet 目录（run_*/logs.parquet，替代 part CSV 输入）")
    ap.add_argument("--out-dir", default=None, help="默认 <dir>/data/cluster_prep")
    ap.add_argument("--mem-limit", default="8GB")
    ap.add_argument("--threads", type=int, default=6)
    a = ap.parse_args()
    parts = [] if a.v2 else sorted(glob.glob(os.path.join(a.dir, f"{a.chain}_part_*.csv")))
    if not parts and not a.v2:
        raise SystemExit(f"未找到 {a.chain}_part_*.csv（--dir {a.dir}）")
    out = a.out_dir or os.path.join(a.dir, "data", "cluster_prep")
    os.makedirs(out, exist_ok=True)
    tmp = os.path.join(out, ".duck_tmp")
    os.makedirs(tmp, exist_ok=True)

    import shutil as _sh
    free_gb = _sh.disk_usage(tmp).free / 2**30
    if free_gb < 10.0:
        raise SystemExit(f"[disk] {tmp} 所在卷仅剩 {free_gb:.1f}GB（<10GB 预检线）——先清盘再跑")
    con = duckdb.connect()
    con.execute(f"SET memory_limit='{a.mem_limit}'")
    con.execute(f"SET threads={a.threads}")
    con.execute(f"SET temp_directory='{tmp}'")
    # 护栏取 min(40GB 经验值, 盘余量-5GB)：QUQ 首跑 temp 爆 46.5GB；撞上限报错可控，撞盘满不可控
    con.execute(f"SET max_temp_directory_size='{min(40, max(int(free_gb) - 5, 5))}GB'")
    con.execute("SET preserve_insertion_order=false")

    if a.v2:
        # v2 parquet 直读（值两段 HUGEINT——VARINT 乘法退化 DOUBLE 不可用；高位超界硬退）
        logs = os.path.join(a.v2, "run_*", "logs.parquet")
        n_hi = con.execute(f"""
            SELECT COUNT(*) FILTER (WHERE substr(data,3,32) <> repeat('0',32))
            FROM read_parquet('{logs}', union_by_name=true)
            WHERE data IS NOT NULL AND LENGTH(data) = 66""").fetchone()[0]
        if n_hi:
            raise SystemExit(f"[fail-closed] value 高 128bit 非零 {n_hi} 行——两段 HUGEINT 会溢出")
        # 块界感知去重（replay_pass1_quq 同款洞察的 SQL 化）：HyperSync 单 run 流式无重复，
        # 重复只可能在断点续拉的 run 边界重叠段——只对重叠块区间的行 GROUP BY 去重，
        # 非重叠区间直通零 shuffle。全局 (tx,li) 去重在 1 亿行上 temp 需求 >37GB（实测爆）。
        run_ranges = []
        for run in sorted(glob.glob(os.path.join(a.v2, "run_*"))):
            lp = os.path.join(run, "logs.parquet")
            if os.path.exists(lp):
                lo_hi = con.execute(f"SELECT MIN(block_number), MAX(block_number) "
                                    f"FROM read_parquet('{lp}')").fetchone()
                if lo_hi[0] is not None:
                    run_ranges.append((int(lo_hi[0]), int(lo_hi[1])))
        overlaps = []
        for i in range(len(run_ranges)):
            for j in range(i + 1, len(run_ranges)):
                lo = max(run_ranges[i][0], run_ranges[j][0])
                hi = min(run_ranges[i][1], run_ranges[j][1])
                if lo <= hi:
                    overlaps.append((lo, hi))
        overlaps.sort()
        merged_ov = []
        for lo, hi in overlaps:
            if merged_ov and lo <= merged_ov[-1][1] + 1:
                merged_ov[-1] = (merged_ov[-1][0], max(merged_ov[-1][1], hi))
            else:
                merged_ov.append((lo, hi))
        ov_cond = " OR ".join(f"(block_number BETWEEN {lo} AND {hi})" for lo, hi in merged_ov) or "FALSE"
        n_ov = con.execute(f"SELECT COUNT(*) FROM read_parquet('{logs}', union_by_name=true) "
                           f"WHERE {ov_cond}").fetchone()[0]
        print(f"run 段 {len(run_ranges)} 个，重叠区间 {len(merged_ov)} 段共 {n_ov:,} 行需查重", flush=True)
        val = ("CAST(('0x'||substr(data,35,16))::UBIGINT::HUGEINT * '18446744073709551616'::HUGEINT"
               " + ('0x'||substr(data,51,16))::UBIGINT::HUGEINT AS VARCHAR)")
        base = f"""
            SELECT block_number bn, lower(transaction_hash) tx, log_index li,
                   '0x' || right(lower(COALESCE(topic1, repeat('0',64))), 40) f,
                   '0x' || right(lower(COALESCE(topic2, repeat('0',64))), 40) t,
                   CASE WHEN data IS NULL OR data IN ('','0x') THEN '0' ELSE {val} END v
            FROM read_parquet('{logs}', union_by_name=true)
            WHERE block_number IS NOT NULL AND log_index IS NOT NULL
              AND (data IS NULL OR data IN ('','0x') OR LENGTH(data) = 66)"""
        # raw = 非重叠直通 UNION 重叠段去重后的行（f/t/v 三列，tx/li 用后即弃）
        con.execute(f"""
            CREATE VIEW raw AS
            SELECT f, t, v FROM ({base}) WHERE NOT ({ov_cond})
            UNION ALL
            SELECT ANY_VALUE(f), ANY_VALUE(t), ANY_VALUE(v)
            FROM ({base}) WHERE {ov_cond} GROUP BY tx, li""")
    else:
        src = ", ".join(f"'{p}'" for p in parts)
        # 6 列 part 格式：block,tx,log_index,from,to,value（prep_cluster_inputs.py 产）
        con.execute(f"""
            CREATE VIEW raw AS
            SELECT lower(tx) tx, TRY_CAST(log_index AS BIGINT) li,
                   lower("from") f, lower("to") t, value v
            FROM read_csv([{src}], header=true, all_varchar=true, ignore_errors=true,
                          names=['block','tx','log_index','from','to','value'])
            WHERE TRY_CAST(block AS BIGINT) IS NOT NULL
              AND TRY_CAST(log_index AS BIGINT) IS NOT NULL AND value ~ '^\\d+$'""")
    maxlen = con.execute("SELECT COALESCE(MAX(LENGTH(v)),0) FROM raw").fetchone()[0]
    vt = "HUGEINT" if maxlen <= 37 else "VARINT"   # VARINT 仅可加/SUM（乘法退化 DOUBLE）
    print(f"value 最大位数={maxlen} -> {vt}", flush=True)

    # 唯一全量重活 = (f,t) 边聚合（不物化去重中间表——QUQ 亿级两次 temp 爆的教训：
    # 首跑 (a,p) 双向 2 亿行 46.5GB、二跑 (tx,li) 全局去重 shuffle 37GB）。
    # bal/profile 全部从 edges_agg 派生（(f,t) 聚合保和，逐行=聚合数学等价）。
    # zero-value transferFrom 投毒边过滤（v3.25，与 cluster.py 老路同口径）：0 额伪造
    # Transfer 会把投毒对手方串进簇并虚增 profile 度数；bal 不受影响（±0）。v 为十进制串无前导零。
    if a.v2:
        con.execute(f"CREATE TABLE ea AS SELECT f, t, SUM(CAST(v AS {vt})) v, COUNT(*) cnt "
                    f"FROM raw WHERE v <> '0' GROUP BY f, t")
    else:
        con.execute(f"""
            CREATE TABLE ea AS
            SELECT f, t, SUM(v) v, COUNT(*) cnt FROM (
              SELECT ANY_VALUE(f) f, ANY_VALUE(t) t, CAST(ANY_VALUE(v) AS {vt}) v
              FROM raw GROUP BY tx, li)
            WHERE v <> 0
            GROUP BY f, t""")
    n = con.execute("SELECT SUM(cnt) FROM ea").fetchone()[0]
    print(f"去重后事件 {n:,}", flush=True)
    con.execute(f"""COPY (SELECT f, t, CAST(v AS VARCHAR) v, cnt FROM ea)
                    TO '{out}/edges_agg.parquet' (COMPRESSION zstd)""")
    con.execute(f"""
        COPY (SELECT a AS addr, CAST(SUM(d) AS VARCHAR) bal FROM (
                SELECT t a, v d FROM ea UNION ALL SELECT f, -v FROM ea)
              GROUP BY a)
        TO '{out}/bal.parquet' (COMPRESSION zstd)""")
    # 行为指纹底数（gatekeeper.funnel_profile 同口径，全整数）——全部由 ea 派生：
    #   fan_in per t = ea 行数（每 (f,t) 一行）≡ COUNT(DISTINCT f)；tx_in = SUM(cnt)；
    #   peer_flow 双向合并 = ea 两方向按 (a,p) 相加；peers = 双向 DISTINCT 对手数。
    con.execute(f"""
        COPY (
          WITH i AS (SELECT t a, COUNT(*) fan_in, SUM(cnt) tx_in, SUM(v) inflow
                     FROM ea GROUP BY t),
               o AS (SELECT f a, COUNT(*) fan_out, SUM(cnt) tx_out, SUM(v) outflow
                     FROM ea GROUP BY f),
               pf AS (SELECT a, MAX(s) mpf FROM (
                        SELECT a, p, SUM(v) s FROM (
                          SELECT t a, f p, v FROM ea
                          UNION ALL SELECT f, t, v FROM ea)
                        GROUP BY a, p) GROUP BY a),
               dg AS (SELECT a, COUNT(DISTINCT p) peers FROM (
                        SELECT t a, f p FROM ea UNION ALL SELECT f, t FROM ea)
                      GROUP BY a)
          SELECT COALESCE(i.a, o.a) addr,
                 COALESCE(i.fan_in, 0) fan_in, COALESCE(o.fan_out, 0) fan_out,
                 COALESCE(i.tx_in, 0) tx_in, COALESCE(o.tx_out, 0) tx_out,
                 CAST(COALESCE(i.inflow, 0) AS VARCHAR) inflow,
                 CAST(COALESCE(o.outflow, 0) AS VARCHAR) outflow,
                 CAST(COALESCE(pf.mpf, 0) AS VARCHAR) max_peer_flow,
                 COALESCE(dg.peers, 0) peers
          FROM i FULL OUTER JOIN o ON i.a = o.a
          LEFT JOIN pf ON pf.a = COALESCE(i.a, o.a)
          LEFT JOIN dg ON dg.a = COALESCE(i.a, o.a))
        TO '{out}/profile.parquet' (COMPRESSION zstd)""")
    ne = con.execute(f"SELECT COUNT(*) FROM '{out}/edges_agg.parquet'").fetchone()[0]
    np_ = con.execute(f"SELECT COUNT(*) FROM '{out}/profile.parquet'").fetchone()[0]
    json.dump({"events_dedup": n, "edges_agg": ne, "addrs": np_, "value_type": vt,
               "parts": parts or [a.v2]},
              open(os.path.join(out, "prep_meta.json"), "w"), indent=1)
    print(f"edges_agg {ne:,} 条 / profile {np_:,} 址 -> {out}", flush=True)


if __name__ == "__main__":
    main()
