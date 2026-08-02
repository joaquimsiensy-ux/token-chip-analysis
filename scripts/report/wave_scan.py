#!/usr/bin/env python3
"""wave_scan.py — 全体持仓地址波次扫描器 v3（casebook S-04 检验②③的机械化收尾）。

背景：PYTHIA 案 W1 波次（341 址、单址峰值 0.05~2.92%、合并峰值 63.44%）两次整体漏检——
单址视角的任何门槛都物理抓不到"雷达线下批量协同"，只有全体视角的机械扫描能命中。
v2（2026-08-01 用户四轮拍板）：扫描对象从"清零层"扩为全体历史峰值 ≥0.02% 地址（不做
现仓过滤，退出强度由三桶标签与 C 表达）；A 升两层结构防"7 日窗"被生长稀释；C 改
"峰值→30% 峰值耗时"口径；D 参数四条合一；成员零截断；负余额升 exit 2。
v3（2026-08-02 codex 复核补闸）：候选全集逐址落盘 scan_universe＋must_adjudicate 四类
机械标记（top200／越线 ≥0.1%／回落 ≥80%／静置 ≥30 天，后两类带 ≥0.05% 历史大仓门槛）——
v2 只落一个计数，孤仓不成波次/等额组就从产物消失，发布闸想对账都没账可对；
dormant_warehouse_audit.json 以 universe_ref{path,sha256} 绑定本报告做集合包含对账。

四指纹（阈值全部用合并口径，与 0.1% 单址线彻底脱钩；schema 权威定义 references/scan-schemas.md）：
  A 同窗建仓（两层，必要条件）：seed_window——存在真实 7 日滑窗，窗内"首次有意义建仓"
    成员 ≥20 且该窗成员合并逐日余额峰值 ≥10% 总供应 → 触发；触发后才双向生长（段长
    ≤45 日、连续 3 天零新成员即停）＋相邻段合并试探，扩成 expanded_wave
  B 喂币专属度（保持 v6.6.1 原样）：成员主源占比 ≥90% 且该主源全局喂币对象 ≤2，
    专属率 ≥50% → 强协同；cohort_hint 外部用户潮提示与 score 公式一并原样
  C 集中清仓（v2 口径）：合并余额从峰值跌到 30%×峰值耗时 ≤30 日 → 强化标记
    （W1 实测 72 天不触发＝预期——用户裁定 C 为未来快速清仓考虑周全，非为 W1 专设；
    回测义务主体是 A 与 D，C 是强化标记位非闸本体）
  D 等额面额聚类（四条合一，2026-08-01 用户定稿）：同精确 raw 面额 ＋ 单笔 ≥0.001%
    总供应 ＋ 任意 7 日滑窗内 ≥20 个不同收方 ＋ 组合计过手 ≥1% 总供应 → 报警。
    不切子组、不限清零层；时间紧凑度降为展示字段。裁决纪律：必查
    top_sender_global_out_degree——上千＝场内设施整数面额"撞衫"，个位数＝定向分仓。

聚类时间轴＝first_meaningful_day（抗 dust）：首次日末余额 ≥ 自身峰值 ×first-meaningful-ratio
的日子；原始 first_in 保留为审计字段。

输入三选一：
  --edges-sol "data/soltx-*.jsonl.gz"   Solana 5 元组行 [ts, slot, from_owner, to_owner, amount_raw]
  --edges-evm-v2 data/v2                EVM v2 采集目录（run_*/logs.parquet+blocks.parquet；
                                        hex→HUGEINT 两段组合，高 32 hex 非零硬退 exit 2）
  --duckdb path [--edges-table edges]   已物化工作库（表含 f,t,ts,amt 四列）

输出：--out wave_scan_report.json（schema wave-scan/v3，成员/收方/全集数组全量零截断）。
候选非空时 requires_adjudication=true——−2 必须按 candidate-adjudications/v1 成员级
逐条裁决（validator 校验），裁决完毕前历史大户兜底桶不准关闸（split-run §3.2）。

退出码：0=扫描完成（有无候选都算）；2=数据探测失败/参数错误/负余额达实质线/候选被
负余额地址污染（fail-closed）；1=脚本自身错误。

回测基线（装闸必附原案回测——retrospective.md 元规则第二条；改本脚本阈值/算法后必须重跑）：
  PYTHIA（Solana 485 万边，默认参数，2026-08-01 v6.8.1 实测锚点）：
    - A：存在 7 日种子窗 ≥20 员且合并峰 ≥10%（W1 金标窗），expanded_wave 覆盖旧终裁
      W1 名单 341 址 ≥85%；
    - D：恰报 7 组、1e12 面额组置顶（168 收方含 Q1 亲发 44 分仓，组过手 33.66% 供应，
      top_sender 出度 41）；其余 6 组主发送方全为场内设施（出度 72,207）撞衫；
    - C 负例：W1 峰→30% 实测 72 天不触发＝预期；
    - 负余额：历史最低点口径实抓 1 址（1.2e-6% 粉尘级，不达实质线警告不拦截）。
  A/D 任一抓不到＝闸坏了，禁止发版。数值锚点唯一权威＝tests/fixtures/pythia_anchors.json。
"""
import argparse
import gzip
import glob
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

Z = "0x0000000000000000000000000000000000000000"
DEAD = "0x000000000000000000000000000000000000dead"
SCHEMA = "wave-scan/v3"


def log(msg):
    print(f"[wave_scan] {msg}", flush=True)


def day_str(day):
    return datetime.fromtimestamp(day * 86400, timezone.utc).strftime("%Y-%m-%d")


def content_id(prefix, parts, n=12):
    return f"{prefix}-{hashlib.sha256(','.join(parts).encode()).hexdigest()[:n]}"


# ---------------- 数据装载 ----------------
#
# edges 的前四列是所有扫描器的公共契约。后五列只供需要逐笔重演的
# entity_source_trace 使用：不能再把 slot/block/log 顺序压扁成秒级 ts。
# order_exact=true 表示 chain_pos1..3 足以唯一恢复链上执行顺序；否则 ingest_seq 只代表
# 采集文件观察顺序，溯源器会把同一最细粒度桶内的因果流转记为 order_ambiguous，不能
# 把观察顺序伪装成链上真序。

def load_sol(con, pattern):
    files = sorted(glob.glob(pattern))
    if not files:
        log(f"探测失败：--edges-sol 无匹配文件: {pattern}")
        sys.exit(2)
    con.execute("""CREATE TABLE edges (
        ts BIGINT, f VARCHAR, t VARCHAR, amt HUGEINT,
        chain_pos1 BIGINT, chain_pos2 BIGINT, chain_pos3 BIGINT,
        order_exact BOOLEAN, ingest_seq BIGINT)""")
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
                # 兼容既有 5 元组 [ts,slot,from,to,amt]；它只有 slot、没有 tx/instruction
                # 序号，slot 内顺序不可证。新 7 元组
                # [ts,slot,transaction_index,instruction_index,from,to,amt] 才是精确顺序。
                seq = total + len(rows)
                if isinstance(r, list) and len(r) == 5:
                    rows.append((int(r[0]), r[2], r[3], int(r[4]),
                                 int(r[1]), None, None, False, seq))
                elif isinstance(r, list) and len(r) == 7:
                    rows.append((int(r[0]), r[4], r[5], int(r[6]),
                                 int(r[1]), int(r[2]), int(r[3]), True, seq))
                else:
                    log(f"探测失败：Solana 边须为 5 元组或带 tx/instruction 序号的 7 元组，收到 {r!r}")
                    sys.exit(2)
                if len(rows) >= 200_000:
                    con.executemany("INSERT INTO edges VALUES (?,?,?,?,?,?,?,?,?)", rows)
                    total += len(rows)
                    rows = []
        if rows:
            con.executemany("INSERT INTO edges VALUES (?,?,?,?,?,?,?,?,?)", rows)
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
               l.block_number AS bn,
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
            SELECT ANY_VALUE(ts) AS ts, ANY_VALUE(f) AS f, ANY_VALUE(t) AS t, ANY_VALUE(amt) AS amt,
                   ANY_VALUE(bn)::BIGINT AS chain_pos1, 0::BIGINT AS chain_pos2,
                   ANY_VALUE(li)::BIGINT AS chain_pos3, true AS order_exact,
                   ANY_VALUE(li)::BIGINT AS ingest_seq
            FROM ({body}) GROUP BY tx, li""")
    else:
        log(f"{len(spans)} 个 run 块区间互斥——VIEW 轻路径（每次查询流式重扫 parquet）")
        con.execute(f"""CREATE VIEW edges AS
            SELECT ts, f, t, amt, bn::BIGINT AS chain_pos1, 0::BIGINT AS chain_pos2,
                   li::BIGINT AS chain_pos3, true AS order_exact, li::BIGINT AS ingest_seq
            FROM ({body})""")
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
    # 已物化库允许携带不同链的顺序列。只有完整 EVM(block+log) 或
    # Solana(slot+tx+instruction) 序号才宣称 exact；其余最细已知桶内交给溯源器记未决。
    def first(*names):
        return next((n for n in names if n in cols), None)

    slot = first("slot")
    block = first("block_number", "block")
    txi = first("transaction_index", "tx_index")
    ins = first("instruction_index", "inner_instruction_index", "log_index")
    logi = first("log_index")
    if block and logi:
        p1, p2, p3, exact = block, "0", logi, "true"
    elif slot and txi and ins:
        p1, p2, p3, exact = slot, txi, ins, "true"
    elif slot:
        p1, p2, p3, exact = slot, txi or "NULL", ins or "NULL", "false"
    elif block:
        p1, p2, p3, exact = block, txi or "NULL", logi or "NULL", "false"
    else:
        p1 = p2 = p3 = "NULL"
        exact = "false"
    con.execute(f"""CREATE VIEW edges AS
        SELECT ts, f, t, CAST(amt AS HUGEINT) amt,
               TRY_CAST({p1} AS BIGINT) AS chain_pos1,
               TRY_CAST({p2} AS BIGINT) AS chain_pos2,
               TRY_CAST({p3} AS BIGINT) AS chain_pos3,
               {exact} AS order_exact,
               row_number() OVER ()::BIGINT AS ingest_seq
        FROM src.{table}""")
    return con.execute("SELECT COUNT(*) FROM edges").fetchone()[0]


# ---------------- 阶段 0：地址概要（逐日末余额峰值口径＋抗 dust 首建日） ----------------

def build_addr_summary(con, exclude, meaningful_ratio):
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
            -- min_bal＝历史逐日末余额最低点：负余额哨兵按它判（v6.8.1 codex 复核修复——
            -- 只看 final_bal 会漏"先负后回正"的数据缺失自愈假象）
            SELECT owner, MAX(bal) AS peak, MIN(bal) AS min_bal, SUM(delta) AS final_bal,
                   MAX(day) AS last_day
            FROM run GROUP BY 1
        ), fi AS (
            -- 两侧并集：纯流出地址（只在 f 侧出现＝数据缺失指纹）不得被内连接静默丢弃，
            -- 否则负余额哨兵对其失明（v2 修复；此类地址 first_in_day 取首次活动日）
            SELECT owner, MIN(day) AS first_in_day FROM (
                SELECT t AS owner, ts // 86400 AS day FROM edges
                UNION ALL
                SELECT f, ts // 86400 FROM edges
            ) GROUP BY 1
        ), fm AS (
            -- 抗 dust：首个日末余额 ≥ 自身峰值 × ratio 的日子（dust 空投不再拉歪聚类时间轴）
            SELECT r.owner, MIN(r.day) AS first_meaningful_day
            FROM run r JOIN agg a ON a.owner = r.owner
            WHERE a.peak > 0 AND r.bal >= a.peak * {meaningful_ratio}
            GROUP BY r.owner
        )
        SELECT a.owner, a.peak, a.min_bal, a.final_bal, fi.first_in_day,
               COALESCE(fm.first_meaningful_day, fi.first_in_day) AS first_meaningful_day,
               a.last_day
        FROM agg a JOIN fi ON fi.owner = a.owner
        LEFT JOIN fm ON fm.owner = a.owner""")
    return con.execute("SELECT COUNT(*) FROM addr").fetchone()[0]


def retention_bucket(final_bal, peak):
    r = final_bal / peak if peak > 0 else 0.0
    return "cleared" if r < 0.10 else ("partial_exit" if r <= 0.50 else "retained")


# ---------------- 指纹 A：种子窗触发 → 双向生长 ----------------

def find_waves(con, members, win_days, min_members, min_seed_peak_raw, max_span, gap_stop=3):
    """members: [(owner, first_meaningful_day, peak, final)]。
    两层结构：先找真实 win_days 日窗（窗内首建成员 ≥min_members 且窗成员合并逐日峰
    ≥min_seed_peak_raw）作种子；触发后才双向生长成段。
    合并峰 ≤ Σ成员单址峰（逐日余额非负），先用单址峰和剪枝再跑 SQL 验真峰。
    返回 [(d0, d1, mem, seed_dict)]。"""
    from collections import Counter
    pool = {m[0]: m for m in members}
    waves = []
    while True:
        cnt = Counter(m[1] for m in pool.values())
        if not cnt:
            break
        days = sorted(cnt)
        wins = []
        for d in days:
            n = sum(cnt.get(d + i, 0) for i in range(win_days))
            if n >= min_members:
                wins.append((n, d))
        wins.sort(reverse=True)
        seed = None
        for n, d in wins:
            win_mem = [m for m in pool.values() if d <= m[1] <= d + win_days - 1]
            if sum(m[2] for m in win_mem) < min_seed_peak_raw:
                continue  # 单址峰和是合并峰上界，不达标必不触发
            series = combined_series(con, [m[0] for m in win_mem])
            peak = max((b for _, b in series), default=0)
            if peak >= min_seed_peak_raw:
                seed = (d, n, peak)
                break
        if seed is None:
            break
        d0 = d1 = None
        sd, sn, speak = seed
        d0, d1 = sd, sd + win_days - 1
        seed_dict = {"start": day_str(d0), "end": day_str(d1),
                     "member_count": sn, "combined_peak_pct": speak}
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
        waves.append((d0, d1, mem, seed_dict))
    return waves


def merge_adjacent_waves(con, segs, merge_gap, merge_gain):
    """相邻段合并试探：间隔 ≤merge_gap 天的两段，合并后合并峰值 > max(各自峰)×merge_gain
    才真合并（峰值证据驱动——防波次被段长上限切碎：W1 回测首跑被切成 30%+45.8% 两段，
    合并后 63.4% 才是本尊）。seed 取两段中 combined_peak_pct 更高者。
    返回 [(d0, d1, mem, series, peak, seed)]。"""
    def enrich(seg):
        d0, d1, mem, seed = seg
        series = combined_series(con, [m[0] for m in mem])
        peak = max((b for _, b in series), default=0)
        return [d0, d1, mem, series, peak, seed]

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
                seed = a[5] if a[5]["combined_peak_pct"] >= b[5]["combined_peak_pct"] else b[5]
                segs[i] = [a[0], b[1], mem, series, peak, seed]
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
    """指纹 B（保持 v6.6.1 原样）：主源 ≥major_share 且该主源全局喂币对象（排 Z/DEAD）≤max_out_degree。"""
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


def peak_to_target_days(series, peak, target_ratio):
    """指纹 C（v2 口径）：合并余额从峰值首次跌到 target_ratio×峰值的耗时（连续 UTC 日历日）。
    只搜索峰值日之后；返回 None＝数据末仍未跌破。series 稀疏（仅变动日）不影响正确性——
    两变动日之间余额恒定，首个记录到 ≤目标线的变动日即首次跌破日。"""
    if not series or peak <= 0:
        return None
    peak_day = next(d for d, b in series if b == peak)
    target = peak * target_ratio
    for d, b in series:
        if d <= peak_day:
            continue
        if b <= target:
            return d - peak_day
    return None


def recycle_targets(con, addrs, d0, d1):
    """清仓窗（峰值日 d0 → 数据末 d1）成员对外流出 top10（剔段内互转与 Z/DEAD）。"""
    ph = "', '".join(addrs)
    return con.execute(f"""
        SELECT t, SUM(amt) FROM edges
        WHERE f IN ('{ph}') AND t NOT IN ('{ph}') AND t NOT IN ('{Z}', '{DEAD}')
          AND ts // 86400 BETWEEN {d0} AND {d1}
        GROUP BY 1 ORDER BY 2 DESC LIMIT 10""").fetchall()


# ---------------- 指纹 D：等额面额聚类（四条合一） ----------------

def equal_amount_groups(con, total, min_amt_raw, win_days, min_win_recv, min_group_pct):
    """四条合一（2026-08-01 用户定稿）：同精确面额 ＋ 单笔 ≥min_amt_raw ＋ 任意 win_days 日
    滑窗内 ≥min_win_recv 个不同收方 ＋ 组合计过手（该面额全部转账，排哨兵）≥min_group_pct%
    总供应。不切子组、零截断。

    滑窗扫**全部转账事件**而非各收方首收事件（v6.8.1 codex 复核修复）：按"每收方首次
    收到该面额"去重会吞掉复收事件——同一批收方分两轮收同面额时第二轮全盲，与"任意
    win_days 日滑窗内 ≥N 个不同收方"的定义不等价。"""
    from collections import Counter, defaultdict
    win_sec = win_days * 86400
    # 预筛：全史 distinct 收方 <N 的面额物理不可能达标，SQL 端先砍
    rows = con.execute(f"""
        WITH ev AS (
            SELECT amt, ts, t, f FROM edges
            WHERE amt >= {min_amt_raw} AND f NOT IN ('{Z}', '{DEAD}') AND t NOT IN ('{Z}', '{DEAD}')
        )
        SELECT amt, ts, t, f FROM ev
        WHERE amt IN (SELECT amt FROM ev GROUP BY amt HAVING COUNT(DISTINCT t) >= {min_win_recv})
        ORDER BY amt, ts, t, f""").fetchall()
    by_amt = defaultdict(list)
    for amt, ts, t, f in rows:
        by_amt[int(amt)].append((int(ts), t, f))
    out = []
    for amt, evs in by_amt.items():
        # 滑窗内 distinct 收方数（全事件双指针＋计数器；复收正确计入窗口）
        best, best_j = 0, 0
        cnt = Counter()
        j = 0
        for i in range(len(evs)):
            cnt[evs[i][1]] += 1
            while evs[i][0] - evs[j][0] > win_sec:
                cnt[evs[j][1]] -= 1
                if not cnt[evs[j][1]]:
                    del cnt[evs[j][1]]
                j += 1
            if len(cnt) > best:
                best, best_j = len(cnt), j
        if best < min_win_recv:
            continue
        group_total = sum(amt for _ in evs)
        pct = group_total * 100.0 / total
        if pct < min_group_pct:
            continue
        recv = sorted({t for _, t, _ in evs})
        # top_sender＝触达 distinct 收方最多的发送方（裁决问的是"这组收方主要是谁喂的"——
        # 按事件数选会被"对同一收方反复发"绑架；平手按地址字典序定序保证稳定输出）
        send_touch = {}
        for _, t, f in evs:
            send_touch.setdefault(f, set()).add(t)
        top_sender = max(send_touch.items(), key=lambda kv: (len(kv[1]), kv[0]))[0]
        top_touched = send_touch[top_sender]
        out_deg = con.execute(f"""
            SELECT COUNT(DISTINCT t) FROM edges
            WHERE f = '{top_sender}' AND t NOT IN ('{Z}', '{DEAD}')""").fetchone()[0]
        phr = "', '".join(recv)
        fin = con.execute(
            f"SELECT COALESCE(SUM(final_bal), 0) FROM addr WHERE owner IN ('{phr}')").fetchone()[0]
        retention = min(int(fin), group_total) / group_total if group_total else 0.0
        first_ts, last_ts = evs[0][0], evs[-1][0]
        out.append({
            "id": content_id(f"eqg-{amt}", recv, 8),
            "amount_raw": str(amt),
            "recipients": len(recv), "tx_count": len(evs),
            "group_total_pct": round(pct, 4),
            "densest_7d_window": {
                "start": datetime.fromtimestamp(evs[best_j][0], timezone.utc).strftime("%Y-%m-%d"),
                "recipients": best},
            "window": [datetime.fromtimestamp(first_ts, timezone.utc).strftime("%Y-%m-%d"),
                       datetime.fromtimestamp(last_ts, timezone.utc).strftime("%Y-%m-%d")],
            "window_days": round((last_ts - first_ts) / 86400.0, 1),
            "top_sender": top_sender,
            "top_sender_recv_share": round(len(top_touched) / len(recv), 2),
            "top_sender_global_out_degree": int(out_deg),
            "retention": round(retention, 3),
            "members": recv,
        })
    out.sort(key=lambda g: -g["group_total_pct"])
    return out


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
    ap.add_argument("--exclude-file", help="已知设施地址清单（json 数组或每行一址文本），不参与扫描")
    ap.add_argument("--mem-limit", default="8GB")
    # 扫描对象与抗 dust
    ap.add_argument("--min-peak-pct", type=float, default=0.02, help="扫描纳入线：逐日峰值 ≥此%%总供应（不做现仓过滤）")
    ap.add_argument("--first-meaningful-ratio", type=float, default=0.05,
                    help="抗 dust：首日末余额 ≥自身峰值×此比例才算有意义首建")
    ap.add_argument("--neg-bal-limit-pct", type=float, default=0.01,
                    help="负余额实质线：负余额合计 ≥此%%总供应即 exit 2")
    ap.add_argument("--must-dormant-pct", type=float, default=0.05,
                    help="必裁决线之'历史大仓'档：峰值 ≥此%%总供应且回落≥80%%或静置≥30天即标 must_adjudicate")
    # 指纹 A（两层）
    ap.add_argument("--window-days", type=int, default=7)
    ap.add_argument("--min-members", type=int, default=20)
    ap.add_argument("--seed-min-peak-pct", type=float, default=10.0,
                    help="种子窗触发线：真实 7 日窗自身合并峰 ≥此%%总供应")
    ap.add_argument("--max-span-days", type=int, default=45)
    ap.add_argument("--merge-gap-days", type=int, default=7, help="相邻段间隔 ≤此天数时做合并试探")
    ap.add_argument("--merge-gain", type=float, default=1.15, help="合并峰 > max(各自峰)×此系数才真合并")
    # 指纹 B（保持 v6.6.1 原样）
    ap.add_argument("--feeder-major", type=float, default=0.90)
    ap.add_argument("--feeder-max-out", type=int, default=2)
    ap.add_argument("--exclusive-rate", type=float, default=0.50)
    # 指纹 C（v2 口径）
    ap.add_argument("--exit-target-ratio", type=float, default=0.30, help="C：跌到峰值×此比例")
    ap.add_argument("--exit-max-days", type=int, default=30, help="C：耗时 ≤此日数才 hit")
    # 指纹 D（四条合一）
    ap.add_argument("--equal-min-amt-pct", type=float, default=0.001, help="D：单笔 ≥此%%总供应")
    ap.add_argument("--equal-win-days", type=int, default=7, help="D：滑窗日数")
    ap.add_argument("--equal-win-recv", type=int, default=20, help="D：滑窗内 ≥此数不同收方")
    ap.add_argument("--equal-min-group-pct", type=float, default=1.0, help="D：组合计过手 ≥此%%总供应")
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

    n_addr = build_addr_summary(con, exclude, a.first_meaningful_ratio)
    log(f"地址概要 {n_addr:,} 址（逐日末余额峰值口径＋抗 dust 首建日）")

    # 负余额闸（v6.8.1：按历史最低点 min_bal 判，不只看期末——"先负后回正"是数据缺失
    # 的自愈假象，峰值/首建日早已被污染；达实质线或污染候选即 exit 2，数据问题回采集侧解决）
    neg_cnt, neg_sum = con.execute(
        "SELECT COUNT(*), COALESCE(SUM(-min_bal), 0) FROM addr WHERE min_bal < 0").fetchone()
    neg_cnt, neg_sum = int(neg_cnt), int(neg_sum)
    if neg_cnt:
        log(f"⚠ 历史负余额地址 {neg_cnt:,} 个（最深缺口合计 -{neg_sum:,} raw）——数据完整性存疑")
        if neg_sum >= total * a.neg_bal_limit_pct / 100.0:
            log(f"负缺口合计达实质线（≥{a.neg_bal_limit_pct}% 总供应）——数据不可信，exit 2")
            sys.exit(2)
    neg_set = {r[0] for r in con.execute("SELECT owner FROM addr WHERE min_bal < 0").fetchall()}

    min_peak_raw = total * a.min_peak_pct / 100.0
    universe = con.execute(f"""
        SELECT owner, first_meaningful_day, peak, final_bal, first_in_day, last_day FROM addr
        WHERE peak >= {min_peak_raw}
        ORDER BY first_meaningful_day, owner""").fetchall()
    members = [(o, int(d), int(p), int(f), int(fi), int(ld))
               for o, d, p, f, fi, ld in universe]
    buckets = {"cleared": 0, "partial_exit": 0, "retained": 0}
    for m in members:
        buckets[retention_bucket(m[3], m[2])] += 1
    log(f"扫描全集 {len(members):,} 址（峰值≥{a.min_peak_pct}%，不做现仓过滤）"
        f" 三桶: cleared={buckets['cleared']} partial_exit={buckets['partial_exit']} retained={buckets['retained']}")

    # ---- 候选全集逐址落盘＋必裁决标记（v3；2026-08-02 codex 复核补闸：只落
    # scan_universe_count 一个计数，发布闸想对账都没账可对——孤仓不成波次/等额组
    # 就从产物里消失，requires_adjudication 还是 false。四类机械命中即 must_adjudicate，
    # 静置仓审计候选必须全覆盖，audit_release_gate 做集合包含校验）----
    data_end_day = int(con.execute("SELECT MAX(ts) // 86400 FROM edges").fetchone()[0])
    peak_rank = {m[0]: i + 1
                 for i, m in enumerate(sorted(members, key=lambda m: -m[2]))}
    must_raw = total * a.must_dormant_pct / 100.0
    line01_raw = total * 0.1 / 100.0
    universe_out = []
    for o, fmd, p, f, fi, ld in members:
        reasons = []
        if peak_rank[o] <= 200:
            reasons.append("peak_top200")
        if p >= line01_raw:
            reasons.append("peak_ge_0.1pct")
        if p >= must_raw and p > 0 and f / p <= 0.20:
            reasons.append("drawdown_ge_80pct")
        if p >= must_raw and f > 0 and data_end_day - ld >= 30:
            reasons.append("dormant_ge_30d")
        universe_out.append({
            "addr": o, "peak_raw": str(p),
            "peak_pct": round(p * 100.0 / total, 4), "final_raw": str(f),
            "retention_bucket": retention_bucket(f, p),
            "first_meaningful_day": day_str(fmd), "last_active_day": day_str(ld),
            "must_adjudicate": bool(reasons), "must_reasons": reasons,
        })
    must_cnt = sum(1 for u in universe_out if u["must_adjudicate"])
    log(f"全集落盘 {len(universe_out):,} 址，其中必裁决 {must_cnt:,} 址"
        f"（top200/≥0.1%/回落≥80%/静置≥30d 四类机械命中）")

    seed_peak_raw = total * a.seed_min_peak_pct / 100.0
    raw_segs = find_waves(con, [(m[0], m[1], m[2], m[3]) for m in members],
                          a.window_days, a.min_members, seed_peak_raw, a.max_span_days)
    first_in_map = {m[0]: m[4] for m in members}
    data_first_day = con.execute("SELECT MIN(ts) // 86400 FROM edges").fetchone()[0] or 0
    waves_out = []
    for d0, d1, mem, series, peak, seed in merge_adjacent_waves(con, raw_segs, a.merge_gap_days, a.merge_gain):
        addrs = [m[0] for m in mem]
        peak_pct = peak * 100.0 / total
        peak_day = next(d for d, b in series if b == peak)
        excl_set, rate = feeder_exclusivity(con, addrs, a.feeder_major, a.feeder_max_out)
        c_days = peak_to_target_days(series, peak, a.exit_target_ratio)
        c_hit = c_days is not None and c_days <= a.exit_max_days
        # 排除提示（不过滤只提示）：B≈0 且成员巨多＝外部驱动用户潮（刷分/空投/政策窗）指纹，
        # 与庄家协同波次（PYTHIA W1 341 址 B=0.4+）相反——保持 v6.6.1 原样
        hint = ("疑似外部驱动用户潮（无专属喂币且成员巨多）——非协同实体特征，判断层按行为 cohort 快速排除"
                if rate < 0.05 and len(mem) > 500 else None)
        rec = recycle_targets(con, addrs, peak_day, series[-1][0])
        mem_sorted = sorted(mem, key=lambda m: -m[2])
        w_buckets = {"cleared": 0, "partial_exit": 0, "retained": 0}
        for m in mem:
            w_buckets[retention_bucket(m[3], m[2])] += 1
        seed_out = dict(seed)
        seed_out["combined_peak_pct"] = round(seed_out["combined_peak_pct"] * 100.0 / total, 3)
        waves_out.append({
            "id": content_id("wave", sorted(addrs)),
            "seed_window": seed_out,
            "build_window": [day_str(d0), day_str(d1)],
            "launch_window": d0 <= data_first_day + 3,
            "cohort_hint": hint,
            "member_count": len(mem),
            "combined_peak_pct": round(peak_pct, 3),
            "combined_peak_date": day_str(peak_day),
            "final_pct": round(sum(m[3] for m in mem) * 100.0 / total, 4),
            "retention_buckets": w_buckets,
            "fingerprints": {
                "A_seed_window": True,
                "B_feeder_exclusive": {"members": len(excl_set), "rate": round(rate, 3),
                                       "hit": rate >= a.exclusive_rate},
                "C_peak_to_30pct": {"days": c_days, "hit": c_hit},
            },
            "score": 1 + int(rate >= a.exclusive_rate) + int(c_hit),
            "recycle_top": [{"to": t, "pct": round(int(v) * 100.0 / total, 3)} for t, v in rec],
            "members": [{"addr": m[0],
                         "first_in": day_str(first_in_map[m[0]]),
                         "first_meaningful": day_str(m[1]),
                         "peak_pct": round(m[2] * 100.0 / total, 4),
                         "retention_bucket": retention_bucket(m[3], m[2]),
                         "feeder_exclusive": m[0] in excl_set} for m in mem_sorted],
        })
    waves_out.sort(key=lambda w: -w["combined_peak_pct"])

    eq_min_raw = int(total * a.equal_min_amt_pct / 100.0)
    eq_groups = equal_amount_groups(con, total, eq_min_raw, a.equal_win_days,
                                    a.equal_win_recv, a.equal_min_group_pct)

    # 候选污染闸：任何候选成员/收方是负余额地址 → 数据不可信，exit 2
    polluted = []
    for w in waves_out:
        bad = [m["addr"] for m in w["members"] if m["addr"] in neg_set]
        if bad:
            polluted.append((w["id"], bad[:3]))
    for g in eq_groups:
        bad = [x for x in g["members"] if x in neg_set]
        if bad:
            polluted.append((g["id"], bad[:3]))
    if polluted:
        for cid, bad in polluted:
            log(f"候选 {cid} 含负余额地址（示例 {bad}）——候选被数据缺失污染，exit 2")
        sys.exit(2)

    report = {
        "schema": SCHEMA,
        "generated_at": t0.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "params": {k: v for k, v in vars(a).items() if k not in ("out",)},
        "total_supply_raw": str(total),
        "edges": n_edges,
        "scan_universe_count": len(members),
        "scan_universe": universe_out,
        "must_adjudicate_count": must_cnt,
        "retention_buckets": buckets,
        "negative_balance_addrs": neg_cnt,
        "first_meaningful_ratio": a.first_meaningful_ratio,
        "waves": waves_out,
        "equal_amount_groups": eq_groups,
        "requires_adjudication": bool(waves_out or eq_groups),
        "note": "候选≠结论：波次可能混入同期建仓的独立地址、等额组可能是 CEX 提币/设施整数面额撞衫——"
                "按 candidate-adjudications/v1 成员级逐条裁决归 −2/A3 判断层（等额组必查 "
                "top_sender_global_out_degree）；候选未裁决完毕前历史大户兜底桶不准关闸（casebook S-04）。",
    }
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    log(f"候选波次 {len(waves_out)} 个 / 等额组 {len(eq_groups)} 个 → {a.out}")
    for w in waves_out:
        log(f"  {w['id']} 成员{w['member_count']} 合并峰 {w['combined_peak_pct']}% "
            f"@{w['combined_peak_date']} 种子窗{w['seed_window']['member_count']}员/{w['seed_window']['combined_peak_pct']}% "
            f"B={w['fingerprints']['B_feeder_exclusive']['rate']} "
            f"C={w['fingerprints']['C_peak_to_30pct']['days']}天 score={w['score']}")
    for g in eq_groups:
        log(f"  等额组 {g['amount_raw']} ×{g['recipients']}仓 过手{g['group_total_pct']}% "
            f"最密7日窗{g['densest_7d_window']['recipients']}仓 主发送方出度{g['top_sender_global_out_degree']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"[wave_scan] 脚本自身错误（exit 1，修完重跑）: {e}", file=sys.stderr)
        raise SystemExit(1)
