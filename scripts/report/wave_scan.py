#!/usr/bin/env python3
"""wave_scan.py — 历史清零层波次扫描器（casebook S-04 检验②③的机械化收尾）。

背景：PYTHIA 案 W1 波次（341 址、单址峰值仅 0.05~0.3%、合并峰值 63.44%）两次整体
漏检——单址视角的任何门槛都物理抓不到"雷达线下批量协同"，只有全体视角的机械扫描
能命中（复盘 2026-08-01：三道文字闸全部空转，装闸必附原案回测）。

四指纹（阈值全部用合并口径，与 0.1% 单址线彻底脱钩）：
  A 同窗建仓聚类（必要条件）：清零层按首建日 7 日滑窗锚窗生长成段（段长 ≤45 日、
    连续 3 天零新成员即停），窗内成员 ≥20 且合并逐日余额峰值 ≥5% 总供应 → 候选波次
  B 喂币专属度：成员主源占比 ≥90% 且该主源全局喂币对象 ≤2，专属率 ≥50% → 强协同
  C 集中清仓窗：存在 ≤14 日滑窗内合并余额净降 ≥50%×峰值 → 组织性清仓
    （不用"峰值→10% 峰值总耗时"口径：W1 实测 81 天 >45，原案回测证明该口径抓不到本尊）
  D 等额面额聚类（独立于清零层，含在持仓）：同精确 raw 面额流入 ≥5 个不同收方且
    组合计 ≥0.5% 总供应 → 报警（Q1 系 44×100 万枚整分仓教训）；窗口集中/单一发送方/
    高留存三项计分

输入三选一：
  --edges-sol "data/soltx-*.jsonl.gz"   Solana 5 元组行 [ts, slot, from_owner, to_owner, amount_raw]
  --edges-evm-v2 data/v2                EVM v2 采集目录（run_*/logs.parquet+blocks.parquet；
                                        hex→HUGEINT 两段组合，同 replay_duck._v2_select 口径，
                                        高 32 hex 非零硬退 exit 2）
  --duckdb path [--edges-table edges]   已物化工作库（表含 f,t,ts,amt 四列）

输出：--out wave_scan_report.json（schema wave-scan/v1）。候选波次与等额组非空时
requires_adjudication=true——−2 必须逐条裁决后历史大户兜底桶才准关闸（split-run §3.2）。

退出码：0=扫描完成（有无候选都算）；2=数据探测失败/参数错误（fail-closed）；1=脚本自身错误。

回测基线（装闸必附原案回测——retrospective.md 元规则第二条；改本脚本阈值/算法后必须重跑）：
  PYTHIA（Solana 485 万边，默认参数，2026-08-01 实测锚点）：
    - 候选波次 wave-2025-04-04 覆盖旧终裁 W1 名单 339/341=99.4%、合并峰 74.155%
      （纯 W1 为 63.438%，差值=同期混入的 Q1/EwUU8oi 等清零仓——机械层预期行为，−2 提纯）、
      C 指纹 0.807 hit、exclusive 标记 293 个（232 个属 W1）；
    - 等额组 1000000000000（100 万枚）×57 仓、窗 26.4 天、score=2 置顶（Q1 系分仓批次，
      命中本案 Q1 系成员 35+）；发射窗大段正确标 launch_window=true。
  两条任一抓不到＝闸坏了，禁止发版。
"""
import argparse
import gzip
import glob
import json
import os
import sys
from datetime import datetime, timezone

Z = "0x0000000000000000000000000000000000000000"
DEAD = "0x000000000000000000000000000000000000dead"
SCHEMA = "wave-scan/v1"


def log(msg):
    print(f"[wave_scan] {msg}", flush=True)


def day_str(day):
    return datetime.fromtimestamp(day * 86400, timezone.utc).strftime("%Y-%m-%d")


# ---------------- 数据装载：统一成 edges(ts BIGINT, f VARCHAR, t VARCHAR, amt HUGEINT) ----------------

def load_sol(con, pattern):
    files = sorted(glob.glob(pattern))
    if not files:
        log(f"探测失败：--edges-sol 无匹配文件: {pattern}")
        sys.exit(2)
    con.execute("CREATE TABLE edges (ts BIGINT, f VARCHAR, t VARCHAR, amt HUGEINT)")
    total = 0
    for fp in files:
        rows = []
        opener = gzip.open if fp.endswith(".gz") else open
        with opener(fp, "rt", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                # [ts, slot, from_owner, to_owner, amount_raw]
                rows.append((int(r[0]), r[2], r[3], int(r[4])))
                if len(rows) >= 200_000:
                    con.executemany("INSERT INTO edges VALUES (?,?,?,?)", rows)
                    total += len(rows)
                    rows = []
        if rows:
            con.executemany("INSERT INTO edges VALUES (?,?,?,?)", rows)
            total += len(rows)
        log(f"  已装载 {os.path.basename(fp)} → 累计 {total:,} 边")
    if not total:
        log("探测失败：边表为空")
        sys.exit(2)
    return total


def load_evm_v2(con, dir_):
    logs = os.path.join(dir_, "run_*", "logs.parquet")
    blocks = os.path.join(dir_, "run_*", "blocks.parquet")
    if not glob.glob(logs):
        log(f"探测失败：--edges-evm-v2 目录无 run_*/logs.parquet: {dir_}")
        sys.exit(2)
    n_hi, mx = con.execute(f"""
        SELECT COUNT(*) FILTER (WHERE substr(data, 3, 32) <> repeat('0', 32)),
               COALESCE(MAX(TRY_CAST('0x' || substr(data, 35, 16) AS UBIGINT)), 0)
        FROM read_parquet('{logs}', union_by_name=true)
        WHERE data IS NOT NULL AND LENGTH(data) = 66""").fetchone()
    if n_hi or int(mx) >= 2 ** 63:
        log("探测失败：data 高 32 hex 非零或 hi64 越界，两段 HUGEINT 会溢出——先用 replay_duck 物化后走 --duckdb")
        sys.exit(2)
    val = ("('0x'||substr(data,35,16))::UBIGINT::HUGEINT * '18446744073709551616'::HUGEINT"
           " + ('0x'||substr(data,51,16))::UBIGINT::HUGEINT")
    body = f"""
        SELECT lower(l.transaction_hash) AS tx, l.log_index AS li,
               bt.ts_i::BIGINT AS ts,
               '0x' || right(lower(COALESCE(l.topic1, repeat('0', 64))), 40) AS f,
               '0x' || right(lower(COALESCE(l.topic2, repeat('0', 64))), 40) AS t,
               CASE WHEN l.data IS NULL OR l.data IN ('', '0x') THEN 0::HUGEINT ELSE {val} END AS amt
        FROM read_parquet('{logs}', union_by_name=true) l
        JOIN (SELECT number, TRY_CAST(ANY_VALUE(timestamp) AS UBIGINT) ts_i
              FROM read_parquet('{blocks}', union_by_name=true)
              WHERE number IS NOT NULL GROUP BY number) bt
          ON bt.number = l.block_number
        WHERE l.block_number IS NOT NULL AND l.log_index IS NOT NULL
          AND (l.data IS NULL OR l.data IN ('', '0x') OR LENGTH(l.data) = 66)
          AND bt.ts_i IS NOT NULL"""
    # run 块区间重叠探测：互斥 → VIEW 轻路径（不物化不去重，亿级行免临时盘——QUQ 1.03 亿行
    # 物化去重实测要 29.7GB temp 直接 OOM）；真重叠才走 (tx,li) 去重物化（replay_duck 靠
    # channels 边界防重，本处全量直读须自防）
    spans = sorted((int(lo), int(hi)) for _, lo, hi in con.execute(f"""
        SELECT filename, MIN(block_number), MAX(block_number)
        FROM read_parquet('{logs}', union_by_name=true, filename=true)
        WHERE block_number IS NOT NULL GROUP BY 1""").fetchall())
    overlapped = any(spans[i][1] >= spans[i + 1][0] for i in range(len(spans) - 1))
    if overlapped:
        log("run 块区间存在重叠——物化 (tx,li) 去重路径（需较大临时盘）")
        con.execute(f"""
            CREATE TABLE edges AS
            SELECT ANY_VALUE(ts) AS ts, ANY_VALUE(f) AS f, ANY_VALUE(t) AS t, ANY_VALUE(amt) AS amt
            FROM ({body}) GROUP BY tx, li""")
    else:
        log(f"{len(spans)} 个 run 块区间互斥——VIEW 轻路径（每次查询流式重扫 parquet）")
        con.execute(f"CREATE VIEW edges AS SELECT ts, f, t, amt FROM ({body})")
    n = con.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    if not n:
        log("探测失败：v2 目录装载后边表为空")
        sys.exit(2)
    return n


def attach_duckdb(con, path, table):
    if not os.path.isfile(path):
        log(f"探测失败：--duckdb 文件不存在: {path}")
        sys.exit(2)
    con.execute(f"ATTACH '{path}' AS src (READ_ONLY)")
    cols = {r[0] for r in con.execute(f"DESCRIBE src.{table}").fetchall()}
    need = {"f", "t", "ts", "amt"}
    if not need <= cols:
        log(f"探测失败：src.{table} 缺列 {need - cols}")
        sys.exit(2)
    con.execute(f"CREATE VIEW edges AS SELECT ts, f, t, CAST(amt AS HUGEINT) amt FROM src.{table}")
    return con.execute("SELECT COUNT(*) FROM edges").fetchone()[0]


# ---------------- 阶段 0：地址概要（逐日末余额峰值口径） ----------------

def build_addr_summary(con, exclude):
    ex = "', '".join([Z, DEAD] + sorted(exclude))
    con.execute(f"""
        CREATE TABLE addr AS
        WITH daily AS (
            SELECT owner, day, SUM(d) AS delta FROM (
                SELECT t AS owner, ts // 86400 AS day, amt AS d FROM edges WHERE t NOT IN ('{ex}')
                UNION ALL
                SELECT f, ts // 86400, -amt FROM edges WHERE f NOT IN ('{ex}')
            ) GROUP BY 1, 2
        ), run AS (
            SELECT owner, day, delta,
                   SUM(delta) OVER (PARTITION BY owner ORDER BY day) AS bal
            FROM daily
        ), agg AS (
            SELECT owner, MAX(bal) AS peak, SUM(delta) AS final_bal FROM run GROUP BY 1
        ), fi AS (
            SELECT t AS owner, MIN(ts // 86400) AS first_in_day FROM edges GROUP BY 1
        )
        SELECT a.owner, a.peak, a.final_bal, fi.first_in_day
        FROM agg a JOIN fi ON fi.owner = a.owner""")
    return con.execute("SELECT COUNT(*) FROM addr").fetchone()[0]


# ---------------- 指纹 A：清零层锚窗生长 ----------------

def find_waves(members, win_days, min_members, max_span, gap_stop=3):
    """members: [(owner, first_in_day, peak, final)]；返回 [(d0, d1, [成员...])]。"""
    from collections import Counter
    pool = {m[0]: m for m in members}
    waves = []
    while True:
        cnt = Counter(m[1] for m in pool.values())
        if not cnt:
            break
        days = sorted(cnt)
        best_d, best_n = None, 0
        for d in days:
            n = sum(cnt.get(d + i, 0) for i in range(win_days))
            if n > best_n:
                best_d, best_n = d, n
        if best_n < min_members:
            break
        d0, d1 = best_d, best_d + win_days - 1
        # 双向生长：一侧 gap_stop 天内仍有新成员即扩 1 天（容忍 ≤gap_stop-1 天空档），两侧全停或达 max_span 止
        while d1 - d0 + 1 < max_span:
            left = any(cnt.get(d0 - 1 - g, 0) for g in range(gap_stop))
            right = any(cnt.get(d1 + 1 + g, 0) for g in range(gap_stop))
            if left:
                d0 -= 1
            if right and d1 - d0 + 1 < max_span:
                d1 += 1
            if not left and not right:
                break
        mem = [m for m in pool.values() if d0 <= m[1] <= d1]
        for m in mem:
            del pool[m[0]]
        waves.append((d0, d1, mem))
    return waves


def merge_adjacent_waves(con, segs, merge_gap, merge_gain):
    """相邻段合并试探：间隔 ≤merge_gap 天的两段，合并后合并峰值 > max(各自峰)×merge_gain
    才真合并（峰值证据驱动——防波次被段长上限切碎：W1 回测首跑被切成 30%+45.8% 两段，
    合并后 63.4% 才是本尊）。返回 [(d0, d1, mem, series, peak)]。"""
    def enrich(seg):
        d0, d1, mem = seg
        series = combined_series(con, [m[0] for m in mem])
        peak = max((b for _, b in series), default=0)
        return [d0, d1, mem, series, peak]

    segs = sorted((enrich(s) for s in segs), key=lambda s: s[0])
    changed = True
    while changed:
        changed = False
        for i in range(len(segs) - 1):
            a, b = segs[i], segs[i + 1]
            if b[0] - a[1] > merge_gap:
                continue
            mem = a[2] + b[2]
            series = combined_series(con, [m[0] for m in mem])
            peak = max((x for _, x in series), default=0)
            if peak > max(a[4], b[4]) * merge_gain:
                segs[i] = [a[0], b[1], mem, series, peak]
                del segs[i + 1]
                changed = True
                break
    return segs


def combined_series(con, addrs):
    """成员集合的合并逐日余额序列 [(day, bal)]。"""
    ph = "', '".join(addrs)
    rows = con.execute(f"""
        WITH d AS (
            SELECT day, SUM(v) AS delta FROM (
                SELECT ts // 86400 AS day, amt AS v FROM edges WHERE t IN ('{ph}')
                UNION ALL
                SELECT ts // 86400, -amt FROM edges WHERE f IN ('{ph}')
            ) GROUP BY 1
        )
        SELECT day, SUM(delta) OVER (ORDER BY day) AS bal FROM d ORDER BY day""").fetchall()
    return [(int(d), int(b)) for d, b in rows]


def feeder_exclusivity(con, addrs, major_share, max_out_degree):
    """指纹 B：主源 ≥major_share 且该主源全局喂币对象（排 Z/DEAD）≤max_out_degree。"""
    ph = "', '".join(addrs)
    rows = con.execute(f"""
        SELECT t, f, SUM(amt) AS a FROM edges
        WHERE t IN ('{ph}') AND f NOT IN ('{ph}')
        GROUP BY 1, 2""").fetchall()
    from collections import defaultdict
    by_recv = defaultdict(list)
    for t, f, a in rows:
        by_recv[t].append((f, int(a)))
    top_feeders = {}
    for t, srcs in by_recv.items():
        srcs.sort(key=lambda x: -x[1])
        tot = sum(a for _, a in srcs)
        if tot > 0 and srcs[0][1] >= tot * major_share and srcs[0][0] != Z:
            top_feeders[t] = srcs[0][0]
    if not top_feeders:
        return set(), 0.0
    fset = sorted(set(top_feeders.values()))
    phf = "', '".join(fset)
    deg = dict(con.execute(f"""
        SELECT f, COUNT(DISTINCT t) FROM edges
        WHERE f IN ('{phf}') AND t NOT IN ('{Z}', '{DEAD}') GROUP BY 1""").fetchall())
    exclusive = {t for t, f in top_feeders.items() if deg.get(f, 99) <= max_out_degree}
    return exclusive, len(exclusive) / max(len(addrs), 1)


def concentrated_exit(series, peak, exit_win, drop_ratio):
    """指纹 C：≤exit_win 日窗内最大净降占峰值比例。"""
    if not series or peak <= 0:
        return 0.0, False
    best = 0
    n = len(series)
    j = 0
    for i in range(n):
        j = max(j, i)
        while j + 1 < n and series[j + 1][0] - series[i][0] <= exit_win:
            j += 1
        drop = series[i][1] - min(b for _, b in series[i:j + 1])
        if drop > best:
            best = drop
    ratio = best / peak
    return ratio, ratio >= drop_ratio


def recycle_targets(con, addrs, d0, d1):
    """清仓窗（峰值日 d0 → 数据末 d1）成员对外流出 top10（剔段内互转与 Z/DEAD）。"""
    ph = "', '".join(addrs)
    return con.execute(f"""
        SELECT t, SUM(amt) FROM edges
        WHERE f IN ('{ph}') AND t NOT IN ('{ph}') AND t NOT IN ('{Z}', '{DEAD}')
          AND ts // 86400 BETWEEN {d0} AND {d1}
        GROUP BY 1 ORDER BY 2 DESC LIMIT 10""").fetchall()


# ---------------- 指纹 D：等额面额聚类 ----------------

def equal_amount_groups(con, total, min_amt_raw, min_members, min_group_pct, top_n, link_days):
    """同精确面额 → 组内按时间连通切子组（相邻笔间隔 ≤link_days 连通）——不切子组时
    44 分仓会被全史同面额（CEX 提整数币等）稀释成 478 天大组而失分（PYTHIA 回测实证）。"""
    from collections import defaultdict, Counter
    rows = con.execute(f"""
        SELECT amt, ts, f, t FROM edges
        WHERE amt >= {min_amt_raw} AND t NOT IN ('{Z}', '{DEAD}')
        ORDER BY amt, ts""").fetchall()
    by_amt = defaultdict(list)
    for amt, ts, f, t in rows:
        by_amt[int(amt)].append((int(ts), f, t))
    out = []
    for amt, txs in by_amt.items():
        sub, subs = [txs[0]], []
        for prev, cur in zip(txs, txs[1:]):
            if cur[0] - prev[0] <= link_days * 86400:
                sub.append(cur)
            else:
                subs.append(sub)
                sub = [cur]
        subs.append(sub)
        for sub in subs:
            recv = sorted({t for _, _, t in sub})
            if len(recv) < min_members:
                continue
            group_total = amt * len(recv)
            pct = group_total * 100.0 / total
            if pct < min_group_pct:
                continue
            first_by_recv = {}
            for ts, f, t in sub:
                first_by_recv.setdefault(t, (ts, f))
            top_sender, top_cnt = Counter(f for _, f in first_by_recv.values()).most_common(1)[0]
            phr = "', '".join(recv)
            fin = con.execute(
                f"SELECT COALESCE(SUM(final_bal), 0) FROM addr WHERE owner IN ('{phr}')").fetchone()[0]
            retention = min(int(fin), group_total) / group_total if group_total else 0.0
            window_days = (sub[-1][0] - sub[0][0]) / 86400.0
            score = int(window_days <= 30) + int(top_cnt >= len(recv) * 0.8) + int(retention >= 0.7)
            out.append({
                "amount_raw": str(amt),
                "recipients": len(recv), "tx_count": len(sub),
                "group_total_pct": round(pct, 4),
                "window": [datetime.fromtimestamp(sub[0][0], timezone.utc).strftime("%Y-%m-%d"),
                           datetime.fromtimestamp(sub[-1][0], timezone.utc).strftime("%Y-%m-%d")],
                "window_days": round(window_days, 1),
                "top_sender": top_sender,
                "top_sender_recv_share": round(top_cnt / len(recv), 2),
                "retention": round(retention, 3),
                "score": score,
                "members_top": recv[:50],
                "members_truncated": max(0, len(recv) - 50),
            })
    out.sort(key=lambda g: (-g["score"], -g["group_total_pct"]))
    return out[:top_n]


# ---------------- 主流程 ----------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--edges-sol", help="Solana jsonl.gz glob（行=[ts,slot,from,to,amt]）")
    src.add_argument("--edges-evm-v2", help="EVM v2 采集目录（run_*/logs.parquet）")
    src.add_argument("--duckdb", help="已物化 DuckDB 库路径")
    ap.add_argument("--edges-table", default="edges", help="--duckdb 模式的边表名（需 f,t,ts,amt 列）")
    ap.add_argument("--total-supply", required=True, help="总供应 raw（分母冻结值）")
    ap.add_argument("--decimals", type=int, default=None, help="仅用于展示换算")
    ap.add_argument("--out", default="wave_scan_report.json")
    ap.add_argument("--exclude-file", help="已知设施地址清单（json 数组或每行一址文本），不参与清零层")
    ap.add_argument("--mem-limit", default="8GB")
    # 指纹 A
    ap.add_argument("--min-peak-pct", type=float, default=0.02, help="清零层入层线：逐日峰值 ≥此%%总供应")
    ap.add_argument("--cleared-ratio", type=float, default=0.10, help="清零判定：现仓 ≤峰值×此比例")
    ap.add_argument("--window-days", type=int, default=7)
    ap.add_argument("--min-members", type=int, default=20)
    ap.add_argument("--max-span-days", type=int, default=45)
    ap.add_argument("--min-combined-peak-pct", type=float, default=5.0)
    ap.add_argument("--merge-gap-days", type=int, default=7, help="相邻段间隔 ≤此天数时做合并试探")
    ap.add_argument("--merge-gain", type=float, default=1.15, help="合并峰 > max(各自峰)×此系数才真合并")
    # 指纹 B
    ap.add_argument("--feeder-major", type=float, default=0.90)
    ap.add_argument("--feeder-max-out", type=int, default=2)
    ap.add_argument("--exclusive-rate", type=float, default=0.50)
    # 指纹 C
    ap.add_argument("--exit-window-days", type=int, default=14)
    ap.add_argument("--exit-drop-ratio", type=float, default=0.50)
    # 指纹 D
    ap.add_argument("--equal-min-amt-pct", type=float, default=0.02)
    ap.add_argument("--equal-min-members", type=int, default=5)
    ap.add_argument("--equal-min-group-pct", type=float, default=0.5)
    ap.add_argument("--equal-link-days", type=int, default=14, help="等额组内相邻笔间隔 ≤此天数连通成子组")
    ap.add_argument("--equal-top", type=int, default=12)
    a = ap.parse_args()

    import duckdb
    total = int(a.total_supply)
    if total <= 0:
        log("参数错误：--total-supply 必须为正")
        sys.exit(2)
    exclude = set()
    if a.exclude_file:
        with open(a.exclude_file, encoding="utf-8") as fh:
            txt = fh.read().strip()
            try:
                exclude = set(json.loads(txt))
            except json.JSONDecodeError:
                exclude = {x.strip() for x in txt.splitlines() if x.strip()}

    con = duckdb.connect()
    con.execute(f"SET memory_limit='{a.mem_limit}'")
    con.execute("SET preserve_insertion_order=false")
    t0 = datetime.now(timezone.utc)
    if a.edges_sol:
        n_edges = load_sol(con, a.edges_sol)
    elif a.edges_evm_v2:
        n_edges = load_evm_v2(con, a.edges_evm_v2)
    else:
        n_edges = attach_duckdb(con, a.duckdb, a.edges_table)
    log(f"边表就绪 {n_edges:,} 条")

    n_addr = build_addr_summary(con, exclude)
    log(f"地址概要 {n_addr:,} 址（逐日末余额峰值口径）")

    min_peak_raw = total * a.min_peak_pct / 100.0
    cleared = con.execute(f"""
        SELECT owner, first_in_day, peak, final_bal FROM addr
        WHERE peak >= {min_peak_raw} AND final_bal <= peak * {a.cleared_ratio}
        ORDER BY first_in_day""").fetchall()
    members = [(o, int(d), int(p), int(f)) for o, d, p, f in cleared]
    log(f"清零层 {len(members):,} 址（峰值≥{a.min_peak_pct}% 且现仓≤峰值×{a.cleared_ratio}）")

    raw_segs = find_waves(members, a.window_days, a.min_members, a.max_span_days)
    data_first_day = con.execute("SELECT MIN(ts) // 86400 FROM edges").fetchone()[0] or 0
    waves_out = []
    for d0, d1, mem, series, peak in merge_adjacent_waves(con, raw_segs, a.merge_gap_days, a.merge_gain):
        addrs = [m[0] for m in mem]
        peak_pct = peak * 100.0 / total
        if peak_pct < a.min_combined_peak_pct:
            continue
        peak_day = next(d for d, b in series if b == peak)
        excl_set, rate = feeder_exclusivity(con, addrs, a.feeder_major, a.feeder_max_out)
        drop_ratio, c_hit = concentrated_exit(series, peak, a.exit_window_days, a.exit_drop_ratio)
        # 排除提示（不过滤只提示）：B≈0 且成员巨多＝外部驱动用户潮（刷分/空投/政策窗）指纹，
        # 与庄家协同波次（PYTHIA W1 341 址 B=0.4+）相反——QUQ 回测 3 波刷分潮实证
        hint = ("疑似外部驱动用户潮（无专属喂币且成员巨多）——非协同实体特征，判断层按行为 cohort 快速排除"
                if rate < 0.05 and len(mem) > 500 else None)
        rec = recycle_targets(con, addrs, peak_day, series[-1][0])
        mem_sorted = sorted(mem, key=lambda m: -m[2])
        waves_out.append({
            "id": f"wave-{day_str(d0)}",
            "build_window": [day_str(d0), day_str(d1)],
            "launch_window": d0 <= data_first_day + 3,
            "cohort_hint": hint,
            "member_count": len(mem),
            "combined_peak_pct": round(peak_pct, 3),
            "combined_peak_date": day_str(peak_day),
            "final_pct": round(sum(m[3] for m in mem) * 100.0 / total, 4),
            "fingerprints": {
                "A_same_window": True,
                "B_feeder_exclusive": {"members": len(excl_set), "rate": round(rate, 3),
                                       "hit": rate >= a.exclusive_rate},
                "C_concentrated_exit": {"max_drop_pct_of_peak": round(drop_ratio, 3),
                                        "window_days": a.exit_window_days, "hit": c_hit},
            },
            "score": 1 + int(rate >= a.exclusive_rate) + int(c_hit),
            "recycle_top": [{"to": t, "pct": round(int(v) * 100.0 / total, 3)} for t, v in rec],
            "members": [{"addr": m[0], "first_in": day_str(m[1]),
                         "peak_pct": round(m[2] * 100.0 / total, 4),
                         "feeder_exclusive": m[0] in excl_set} for m in mem_sorted[:2000]],
            "members_truncated": max(0, len(mem) - 2000),
        })
    waves_out.sort(key=lambda w: -w["combined_peak_pct"])

    eq_min_raw = int(total * a.equal_min_amt_pct / 100.0)
    eq_groups = equal_amount_groups(con, total, eq_min_raw, a.equal_min_members,
                                    a.equal_min_group_pct, a.equal_top, a.equal_link_days)

    report = {
        "schema": SCHEMA,
        "generated_at": t0.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "params": {k: v for k, v in vars(a).items() if k not in ("out",)},
        "total_supply_raw": str(total),
        "edges": n_edges,
        "cleared_layer_count": len(members),
        "waves": waves_out,
        "equal_amount_groups": eq_groups,
        "requires_adjudication": bool(waves_out or eq_groups),
        "note": "候选≠结论：波次可能混入同期建仓的独立地址、等额组可能是 CEX 提币/空投——"
                "逐条裁决归 −2/A3 判断层；候选未清零前历史大户兜底桶不准关闸（casebook S-04）。",
    }
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    log(f"候选波次 {len(waves_out)} 个 / 等额组 {len(eq_groups)} 个 → {a.out}")
    for w in waves_out:
        log(f"  {w['id']} 成员{w['member_count']} 合并峰 {w['combined_peak_pct']}% "
            f"@{w['combined_peak_date']} B={w['fingerprints']['B_feeder_exclusive']['rate']} "
            f"C={w['fingerprints']['C_concentrated_exit']['max_drop_pct_of_peak']} score={w['score']}")
    for g in eq_groups:
        log(f"  等额组 {g['amount_raw']} ×{g['recipients']}仓 ={g['group_total_pct']}% "
            f"窗{g['window_days']}天 score={g['score']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"[wave_scan] 脚本自身错误（exit 1，修完重跑）: {e}", file=sys.stderr)
        raise SystemExit(1)
