#!/usr/bin/env python3
"""DuckDB 版重放引擎（pass1+pass2 合一）——与 replay_pass1/replay_pass2 逐字段等价的列式实现。

来源：2026-07-22 DuckDB 引擎改造工程（@CX 方案 A2）。动机：旧引擎把全量事件装进
Python dict（140 万行实测峰值 1.22GB，亿级外推 ~90GB，16GB 机器不可行）；本引擎
扫描聚合交给 DuckDB（内存可设上限、超限落盘外排），百分比等浮点计算保留与旧引擎
逐表达式同构的 Python 代码，实现基线级（golden_baseline.py）逐字段等价。

语义复刻要点（与 replay_pass1.py 逐条对照，改动前必读旧引擎源码）：
  mint（from=0x0）：mint_total/mint_by_to 记账，0x0 余额不减；
  burn（to∈{0x0,dead}）：burn_total 记账，to 余额照加（供给闭合 su==mint_total 依赖此口径）；
  峰值：块末口径、严格大于才更新（peak_blk=首达块）、只存 >0 且 ≥总铸量0.1%；
  first_seen 排除 0x0（含 to 侧）；last_active 的 to 侧不排 0x0（含 0x0/dead）；
  pass2：烧入 0x0 计"销毁"阵营、mint 不记账、散户=max(0,100-known)、known 按
  camps.json 键序浮点累加（顺序影响第 15 位，同构保逐位一致）、round(4)。

uint256 策略（防浮点退化——UHUGEINT 的 SUM 会静默退化 DOUBLE，实测）：
  值位数 ≤37 → HUGEINT 快路径（±1.7e38 安全）；超界 → VARINT 任意精度（慢 ~5x 仍精确）；
  VARINT 窗口函数不可用时峰值计算回退 Python 流式（输入已是 (addr,block,delta) 聚合行）。

新增的 reject 记账（fail-closed 强化，旧引擎静默丢行）：
  n_source_rows / n_bad_fields / n_out_of_segment / n_dedup_removed 写入 replay_stats.json
  扩展字段（不影响与旧 stats 的对表键）；空 ts 行 >0 时硬退出（旧引擎会把这类行
  归入"上一个有效日"，属未定义行为，新引擎要求先修数据）。

峰值窗口预筛（2026-07-22 优化）：以"累计流入 ≥ 峰值门槛×0.8"先筛候选地址，仅候选
  进入逐窗精确计算——累计流入是峰值的数学恒等上界（详见 replay_pass1 内注释），
  预筛只多收不漏收，peaks.json 与全量逐窗版逐键逐值等价；QUQ 1.03 亿行实测
  峰值段 432s 级 → 秒级~十秒级。诊断打印 [peak] 预筛候选数与分段耗时。

用法：
  python3 replay_duck.py --channels channels.json --out-dir out \
      [--camps camps.json] [--emit-csv] [--merged-parquet] [--no-merged] \
      [--mem-limit 8GB] [--threads 6]
"""
import argparse, csv, glob, json, os, sys, time
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from camp_spec import validate_camp_spec
from channels_preflight import preflight_channels, replay_provenance
from supply_semantics import DEAD, ZERO as Z


def _v2_select(c, dir_):
    """v2 parquet 目录（run_*/logs.parquet + blocks.parquet）→ 标准逻辑行 SELECT 片段。

    value 解析：data 为 '0x'+64hex；高 32 hex 全零（调用前已探测）时两段 UBIGINT
    组合成 HUGEINT——⚠不能用 VARINT 乘法（实测 VARINT*VARINT 退化 DOUBLE，
    DuckDB 1.5.4）；HUGEINT 乘加溢出会硬报错（fail-loud）不静默环绕。"""
    logs = os.path.join(dir_, "run_*", "logs.parquet")
    blocks = os.path.join(dir_, "run_*", "blocks.parquet")
    val = ("CAST(('0x'||substr(data,35,16))::UBIGINT::HUGEINT * '18446744073709551616'::HUGEINT"
           " + ('0x'||substr(data,51,16))::UBIGINT::HUGEINT AS VARCHAR)")
    return f"""
        SELECT l.block_number b,
               COALESCE(strftime(make_timestamp((bt.ts_i * 1000000)::BIGINT), '%Y-%m-%dT%H:%M:%S'), '') ts,
               lower(l.transaction_hash) tx, l.log_index li,
               '0x' || right(lower(COALESCE(l.topic1, repeat('0', 64))), 40) frm,
               '0x' || right(lower(COALESCE(l.topic2, repeat('0', 64))), 40) t2,
               CASE WHEN l.data IS NULL OR l.data IN ('', '0x') THEN '0' ELSE {val} END v,
               '{c['tag']}' tag
        FROM read_parquet('{logs}', union_by_name=true) l
        LEFT JOIN (SELECT number, TRY_CAST(ANY_VALUE(timestamp) AS UBIGINT) ts_i
                   FROM read_parquet('{blocks}', union_by_name=true)
                   WHERE number IS NOT NULL GROUP BY number) bt
               ON bt.number = l.block_number
        WHERE l.block_number IS NOT NULL AND l.log_index IS NOT NULL
          AND (l.data IS NULL OR l.data IN ('', '0x') OR LENGTH(l.data) = 66)
          AND l.block_number >= {c['lo']} AND l.block_number < {c['hi']}"""


def _v2_probe(con, c, dir_):
    """v2 值域探测：data 高 32 hex 非零或 hi64 段 ≥2^63 → 两段 HUGEINT 会溢出，硬退。"""
    logs = os.path.join(dir_, "run_*", "logs.parquet")
    n_hi, mx = con.execute(f"""
        SELECT COUNT(*) FILTER (WHERE substr(data, 3, 32) <> repeat('0', 32)),
               COALESCE(MAX(TRY_CAST('0x' || substr(data, 35, 16) AS UBIGINT)), 0)
        FROM read_parquet('{logs}', union_by_name=true)
        WHERE data IS NOT NULL AND LENGTH(data) = 66""").fetchone()
    if n_hi or int(mx) >= 2**63:
        raise SystemExit(f"[fail-closed] 通道 {c['tag']}：value 超 127bit（高位非零 {n_hi} 行，"
                         f"hi64 最大 {mx}）——两段 HUGEINT 路径会溢出，此类超大值币需扩展"
                         f" UDF 十进制路径（VARINT 乘法退化 DOUBLE 不可用），先人工核数据")


def build_events(con, chans):
    """各通道段过滤+字段清洗+段内 keep-last 去重 → events 表。返回 reject 记账 dict。

    通道格式：path 为目录 → v2 parquet（run_*/logs.parquet）；否则 v1 7列 CSV。
    可用 "format": "v2"|"v1csv" 显式指定。"""
    parts, acc = [], {"n_source_rows": 0, "n_bad_fields": 0, "n_out_of_segment": 0}
    for c in chans:
        if not os.path.exists(c["path"]):
            print(f"[warn] 缺文件 {c['path']}（tag={c['tag']}），跳过")
            continue
        fmt = c.get("format") or ("v2" if os.path.isdir(c["path"]) else "v1csv")
        if fmt == "v2":
            _v2_probe(con, c, c["path"])
            part = _v2_select(c, c["path"])
            raw, bad, seg = con.execute(f"""
                SELECT COUNT(*),
                       COUNT(*) FILTER (WHERE block_number IS NULL OR log_index IS NULL
                            OR (data IS NOT NULL AND data NOT IN ('','0x') AND LENGTH(data) <> 66)),
                       COUNT(*) FILTER (WHERE block_number IS NOT NULL AND log_index IS NOT NULL
                            AND (block_number < {c['lo']} OR block_number >= {c['hi']}))
                FROM read_parquet('{os.path.join(c["path"], "run_*", "logs.parquet")}',
                                  union_by_name=true)""").fetchone()
            acc["n_source_rows"] += raw
            acc["n_bad_fields"] += bad
            acc["n_out_of_segment"] += seg
            parts.append(part)
            n = con.execute(f"SELECT COUNT(*) FROM ({part})").fetchone()[0]
            print(f"{c['tag']}=[{c['lo']},{c['hi']}) v2 收 {n} 条", flush=True)
            continue
        with open(c["path"], newline="") as fh:
            header = next(csv.reader(fh), [])
        standard8 = set(("block", "ts", "tx", "log_index", "from", "to",
                         "value_raw", "block_hash")) <= set(header)
        legacy7 = set(("block", "ts", "tx", "from", "to", "uniqueId")) <= set(header) \
            and ("value" in header or "value_raw" in header)
        if not (standard8 or legacy7):
            raise SystemExit(f"[fail-closed] {c['path']} CSV header 非 legacy7/standard8: {header}")
        src = f"read_csv('{c['path']}', header=true, all_varchar=true, ignore_errors=true)"
        value_col = "value_raw" if "value_raw" in header else "value"
        li_expr = ("TRY_CAST(log_index AS BIGINT)" if standard8 else
                   "TRY_CAST(regexp_extract(uniqueId, '(\\d+)$', 1) AS BIGINT)")
        raw, bad, seg = con.execute(f"""
            WITH r AS (SELECT TRY_CAST(block AS BIGINT) b,
                              {li_expr} li,
                              {value_col} ~ '^\\d+$' AS okv
                       FROM {src})
            SELECT COUNT(*),
                   COUNT(*) FILTER (WHERE b IS NULL OR li IS NULL OR NOT okv),
                   COUNT(*) FILTER (WHERE b IS NOT NULL AND li IS NOT NULL AND okv
                                    AND (b < {c['lo']} OR b >= {c['hi']}))
            FROM r""").fetchone()
        acc["n_source_rows"] += raw
        acc["n_bad_fields"] += bad
        acc["n_out_of_segment"] += seg
        parts.append(f"""
            SELECT TRY_CAST(block AS BIGINT) b, ts, lower(tx) tx,
                   {li_expr} li,
                   lower("from") frm,
                   COALESCE(NULLIF(lower("to"), ''), '{Z}') t2,
                   {value_col} v, '{c['tag']}' tag
            FROM {src}
            WHERE TRY_CAST(block AS BIGINT) IS NOT NULL
              AND {li_expr} IS NOT NULL
              AND {value_col} ~ '^\\d+$'
              AND TRY_CAST(block AS BIGINT) >= {c['lo']}
              AND TRY_CAST(block AS BIGINT) < {c['hi']}""")
        n = con.execute(f"SELECT COUNT(*) FROM ({parts[-1]})").fetchone()[0]
        print(f"{c['tag']}=[{c['lo']},{c['hi']}) 收 {n} 条", flush=True)
    if not parts:
        raise SystemExit("无可用通道数据")
    union = " UNION ALL ".join(parts)
    con.execute(f"CREATE TABLE raw_rows AS {union}" if len(parts) == 1
                else f"CREATE TABLE raw_rows AS SELECT * FROM ({union})")
    # 段内 (tag,tx,li) 去重。旧引擎是 dict 覆盖=keep-last；正常数据同键必同值（同一链上
    # 事件重复拉取），任取即等价。同键不同值=数据损坏，fail-closed 硬退（旧引擎会静默
    # 取末行——本引擎升级为对账关卡，与 A3 缺口③同类防线）。
    n_conflict = con.execute("""
        SELECT COUNT(*) FROM (
          SELECT tag, tx, li FROM raw_rows GROUP BY tag, tx, li
          HAVING COUNT(DISTINCT (b, ts, frm, t2, v)) > 1)""").fetchone()[0]
    if n_conflict:
        sample = con.execute("""
            SELECT tag, tx, li, COUNT(*) FROM raw_rows GROUP BY tag, tx, li
            HAVING COUNT(DISTINCT (b, ts, frm, t2, v)) > 1 LIMIT 3""").fetchall()
        raise SystemExit(f"[fail-closed] {n_conflict} 个去重键对应多个不同事件内容"
                         f"（样本 {sample}）——数据损坏，先仲裁再重放")
    con.execute("""
        CREATE TABLE events AS
        SELECT ANY_VALUE(b) b, ANY_VALUE(ts) ts, tx, li,
               ANY_VALUE(frm) frm, ANY_VALUE(t2) t2, ANY_VALUE(v) v
        FROM raw_rows GROUP BY tag, tx, li""")
    con.execute("DROP TABLE raw_rows")
    n_events = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    kept_before_dedup = acc["n_source_rows"] - acc["n_bad_fields"] - acc["n_out_of_segment"]
    acc["n_dedup_removed"] = kept_before_dedup - n_events
    print(f"合计事件 {n_events}", flush=True)
    return acc


def replay_pass1(con, out_dir, vt):
    """聚合出 bal/peak/mint/burn/first/last + stats，写 pass1 四件产物。返回 (stats, mint_total)。"""
    con.execute(f"""
        CREATE VIEW deltas AS
        SELECT t2 AS a, b, CAST(v AS {vt}) AS d FROM events
        UNION ALL
        SELECT frm, b, -CAST(v AS {vt}) FROM events WHERE frm <> '{Z}'""")
    con.execute("CREATE TABLE bal AS SELECT a, SUM(d) s FROM deltas GROUP BY a")
    mint_total = con.execute(
        f"SELECT COALESCE(SUM(CAST(v AS {vt})), 0) FROM events WHERE frm = '{Z}'").fetchone()[0]
    burn_total = con.execute(
        f"SELECT COALESCE(SUM(CAST(v AS {vt})), 0) FROM events WHERE t2 IN ('{Z}','{DEAD}')").fetchone()[0]
    zero_event_inflow, dead_event_inflow, dead_event_outflow = con.execute(f"""
        SELECT COALESCE(SUM(CAST(v AS {vt})) FILTER (WHERE t2 = '{Z}'), 0),
               COALESCE(SUM(CAST(v AS {vt})) FILTER (WHERE t2 = '{DEAD}'), 0),
               COALESCE(SUM(CAST(v AS {vt})) FILTER (WHERE frm = '{DEAD}'), 0)
        FROM events""").fetchone()
    su = con.execute("SELECT COALESCE(SUM(s), 0) FROM bal").fetchone()[0]
    neg = con.execute("SELECT COUNT(*) FROM bal WHERE s < 0").fetchone()[0]
    uniq = con.execute("SELECT COUNT(*) FROM bal").fetchone()[0]
    n_events = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    mint_total, burn_total, su = int(mint_total), int(burn_total), int(su)
    zero_event_inflow = int(zero_event_inflow)
    dead_event_inflow = int(dead_event_inflow)
    dead_event_outflow = int(dead_event_outflow)
    dead_sink_net = dead_event_inflow - dead_event_outflow

    # 峰值：块末口径 cumsum 窗口；VARINT 窗口不可用时回退 Python 流式（输入已聚合）
    peak_min = mint_total // 1000
    _tp0 = time.time()
    # ── 候选预筛（2026-07-22 峰值窗口优化；QUQ 1.03 亿行窗口段 432s 的降本关卡）──
    # 数学完备性论证（恒等上界，全整数、无浮点参与）：
    #   地址 a 在任意块 B 的块末余额 cum(B) = Σ_{b≤B} dd(b) = Σ_{b≤B}[in(b) − out(b)]
    #     ≤ Σ_{b≤B} in(b) ≤ Σ_全程 in(b) = 累计流入      （in(b) ≥ 0 恒成立）
    #   即 峰值 ≤ 累计流入；逆否：累计流入 < 门槛 ⟹ 峰值 < 门槛，必不进 peaks.json。
    #   故按"累计流入 ≥ 门槛下界"预筛只可能多收候选、绝不漏掉任何真实达标地址；
    #   候选集内的精确逐窗计算 SQL/回退流式逻辑与全量版逐字相同 ⟹ 输出逐键逐值等价。
    #   ⚠禁用终态余额预筛：峰值高但后来清仓者终态=0，会漏（§12"终态/流量"中只有流量完备）。
    # 门槛下界 = peak_min×0.8 整数向下取整：上界本身已数学完备，0.8 是防御带（防未来
    #   峰值口径/门槛语义漂移时阈值附近仍兜住，宁多勿漏）；peak_min=0（mint<1000 微型盘）
    #   时下界=0，SUM(v)≥0 恒真 → 候选=全部收方地址，退化为全量语义。纯付方地址（从未
    #   收币）不进候选：其 cum 恒 ≤ 0，被下方 HAVING MAX(c)>0 过滤，与全量版输出一致。
    # 类型安全（data-pipeline-evm-recon §12 坑对照）：累计流入是流量、无供给守恒上界，
    #   HUGEINT SUM 理论可超 ±1.7e38（DuckDB 溢出=硬报错不静默环绕）——捕获后回退
    #   VARINT 任意精度重算（VARINT 的 SUM 精确；乘法才退化 DOUBLE，此处无乘法）。
    prescreen = (peak_min * 8) // 10

    def _mk_cand(t):
        con.execute("DROP TABLE IF EXISTS peak_cand")
        con.execute(f"""
            CREATE TABLE peak_cand AS
            SELECT t2 AS a FROM events GROUP BY t2
            HAVING SUM(CAST(v AS {t})) >= '{prescreen}'::{t}""")

    try:
        _mk_cand(vt)
    except duckdb.Error as e:
        print(f"[peak] 预筛 {vt} 流入聚合溢出（{str(e)[:60]}），回退 VARINT 重算", flush=True)
        _mk_cand("VARINT")
    n_cand = con.execute("SELECT COUNT(*) FROM peak_cand").fetchone()[0]
    _tp1 = time.time()
    print(f"[peak] 一级预筛（累计流入）候选 {n_cand}/{uniq} 址（门槛下界 {prescreen}）"
          f"{_tp1 - _tp0:.1f}s", flush=True)
    con.execute("""
        CREATE TABLE ab_pre AS
        SELECT a, b, SUM(d) dd FROM deltas
        WHERE a IN (SELECT a FROM peak_cand) GROUP BY a, b""")
    _tp2 = time.time()
    # ── 二级预筛（更紧的完备上界，逐块粒度）───────────────────────────────
    # 块末峰值 = max_B Σ_{b≤B} dd(b) ≤ Σ_b max(dd(b), 0) =「正块净增之和」
    #   （任意前缀和 ≤ 其正项之和；整数恒等，与一级同理只多收不漏收）。
    #   一级（累计流入=Σ in(b)）对同块进出抵消的刷量/路由/接力地址无筛选力
    #   （QUQ 刷量盘实测一级只筛掉 39% 地址、窗口耗时几乎不降）；二级在块级
    #   聚合后的 dd 上求正项和，同块对倒地址 dd≈0 被精准滤掉，而真实建仓地址
    #   （峰值达标者）必然正块净增达标。ab_pre 含一级候选的**全部** (a,b) 行
    #   （一级按地址整体保留，无行缺失），故该和是真上界。
    #   溢出兜底同一级：正项和 ≤ 累计流入，HUGEINT 理论可溢 → 回退 VARINT。
    def _mk_cand2(t):
        con.execute("DROP TABLE IF EXISTS peak_cand2")
        con.execute(f"""
            CREATE TABLE peak_cand2 AS
            SELECT a FROM ab_pre GROUP BY a
            HAVING SUM(GREATEST(CAST(dd AS {t}), '0'::{t})) >= '{prescreen}'::{t}""")

    try:
        _mk_cand2(vt)
    except duckdb.Error as e:
        print(f"[peak] 二级预筛 {vt} 聚合溢出（{str(e)[:60]}），回退 VARINT 重算", flush=True)
        _mk_cand2("VARINT")
    con.execute("CREATE TABLE ab AS SELECT * FROM ab_pre WHERE a IN (SELECT a FROM peak_cand2)")
    con.execute("DROP TABLE ab_pre")
    n_cand2, n_ab = con.execute(
        "SELECT (SELECT COUNT(*) FROM peak_cand2), COUNT(*) FROM ab").fetchone()
    _tp3 = time.time()
    print(f"[peak] 二级预筛（正块净增）候选 {n_cand2} 址、ab {n_ab} 行 {_tp3 - _tp2:.1f}s",
          flush=True)
    try:
        con.execute("""
            CREATE TABLE peaks AS
            WITH cum AS (SELECT a, b, SUM(dd) OVER (PARTITION BY a ORDER BY b) c FROM ab),
                 mx AS (SELECT a, MAX(c) mc FROM cum GROUP BY a HAVING MAX(c) > 0)
            SELECT m.a, m.mc, MIN(cum.b) pb FROM mx m
            JOIN cum ON cum.a = m.a AND cum.c = m.mc GROUP BY m.a, m.mc""")
        peak_rows = con.execute(
            f"SELECT a, mc, pb FROM peaks WHERE mc >= {peak_min}").fetchall()
    except duckdb.Error as e:
        print(f"[peak] SQL 窗口不可用（{str(e)[:80]}），回退 Python 流式", flush=True)
        peak_rows = _peaks_python(con, peak_min)
    print(f"[peak] 窗口+取数 {time.time() - _tp3:.1f}s；峰值段合计 {time.time() - _tp0:.1f}s",
          flush=True)

    first_seen = dict(con.execute(f"""
        SELECT a, MIN(b) FROM (
          SELECT frm a, b FROM events WHERE frm <> '{Z}'
          UNION ALL SELECT t2, b FROM events WHERE t2 <> '{Z}') GROUP BY a""").fetchall())
    last_active = dict(con.execute(f"""
        SELECT a, MAX(b) FROM (
          SELECT frm a, b FROM events WHERE frm <> '{Z}'
          UNION ALL SELECT t2, b FROM events) GROUP BY a""").fetchall())

    stats = {"events": n_events, "mint_total_wei": str(mint_total),
             "burn_total_wei": str(burn_total), "sum_balances_wei": str(su),
             "zero_event_inflow_wei": str(zero_event_inflow),
             "dead_event_inflow_wei": str(dead_event_inflow),
             "dead_event_outflow_wei": str(dead_event_outflow),
             "dead_sink_net_wei": str(dead_sink_net),
             "supply_check_ok": su == mint_total, "neg_balance_addrs": neg,
             "unique_addrs": uniq, "gate_pass": su == mint_total and neg == 0}

    json.dump({a: str(int(s)) for a, s in
               con.execute("SELECT a, s FROM bal WHERE s <> 0").fetchall()},
              open(f"{out_dir}/balances_final.json", "w"))
    json.dump({a: {"peak": str(int(mc)), "peak_blk": pb,
                   "first_blk": first_seen.get(a), "last_blk": last_active.get(a)}
               for a, mc, pb in peak_rows},
              open(f"{out_dir}/peaks.json", "w"))
    json.dump({a: str(int(s)) for a, s in con.execute(
        f"SELECT t2, SUM(CAST(v AS {vt})) FROM events WHERE frm = '{Z}' GROUP BY t2").fetchall()},
              open(f"{out_dir}/mint_ledger.json", "w"))
    return stats, mint_total


def _peaks_python(con, peak_min):
    """VARINT 慢路径兜底：从聚合行 (addr,block,delta) 流式算块末峰值（精确 int）。"""
    cur = con.execute("SELECT a, b, dd FROM ab ORDER BY a, b")
    out, cur_a, c, mc, pb = [], None, 0, 0, None
    while True:
        rows = cur.fetchmany(200000)
        if not rows:
            break
        for a, b, dd in rows:
            if a != cur_a:
                if cur_a is not None and mc > 0 and mc >= peak_min:
                    out.append((cur_a, mc, pb))
                cur_a, c, mc, pb = a, 0, 0, None
            c += int(dd)
            if c > mc:
                mc, pb = c, b
    if cur_a is not None and mc > 0 and mc >= peak_min:
        out.append((cur_a, mc, pb))
    return out


def emit_merged(con, out_dir, emit_csv, merged_parquet):
    if merged_parquet or not emit_csv:
        con.execute(f"""COPY (SELECT b AS block, ts, tx, li AS log_index,
                                     frm AS "from", t2 AS "to", v AS value
                              FROM events ORDER BY b, li)
                        TO '{out_dir}/merged.parquet' (COMPRESSION zstd)""")
        print(f"merged.parquet 写出", flush=True)
    if emit_csv:
        cur = con.execute("SELECT b, ts, tx, li, frm, t2, v FROM events ORDER BY b, li")
        with open(f"{out_dir}/merged.csv", "w", newline="") as g:
            w = csv.writer(g)
            w.writerow(["block", "ts", "tx", "log_index", "from", "to", "value"])
            while True:
                rows = cur.fetchmany(200000)
                if not rows:
                    break
                for b, ts, tx, li, frm, t2, v in rows:
                    w.writerow([b, ts, tx, li, frm, t2, int(v)])
        print(f"merged.csv 写出（旧格式兼容模式）", flush=True)


def replay_pass2(con, camps_path, out_dir, mint_total, vt, *, diagnostic_gate_failed=False):
    """日度阵营/实体序列——known 累加按 camps.json 键序，与旧 snap() 逐表达式同构。"""
    spec = json.load(open(camps_path))
    # F-05：互斥校验（同营内+跨营重复硬拒 exit 2）在原始列表上、lower 规范化之后做；
    # 与 replay_pass2.py 同一共享实现（scripts/lib/camp_spec.py），两 EVM 引擎同深
    camps_valid = validate_camp_spec(spec.get("camps", {}), chain_family="evm",
                                     source_label=str(camps_path))
    camps_order = list(camps_valid.keys())
    if "销毁" not in camps_order:
        camps_order.append("销毁")
    addr2camp = {}
    for c, addrs in camps_valid.items():
        for ad in addrs:
            addr2camp[ad] = c
    addr2camp.pop(Z, None)                     # 0x0 永不走阵营映射（销毁另算）
    ent_pairs = [(ad.lower(), e) for e, addrs in spec.get("entities", {}).items()
                 for ad in addrs]
    ents_order = list(spec.get("entities", {}).keys())

    n_empty_ts = con.execute(
        "SELECT COUNT(*) FROM events WHERE ts IS NULL OR ts = ''").fetchone()[0]
    if n_empty_ts:
        raise SystemExit(f"[fail-closed] {n_empty_ts} 行 ts 为空——旧引擎会把这类行归入"
                         f"上一个有效日（未定义行为），请先补时间戳再跑 pass2")

    con.execute("CREATE TABLE camp_map (addr VARCHAR, camp VARCHAR)")
    if addr2camp:
        con.executemany("INSERT INTO camp_map VALUES (?, ?)", list(addr2camp.items()))
    con.execute("CREATE TABLE ent_map (addr VARCHAR, ent VARCHAR)")
    if ent_pairs:
        con.executemany("INSERT INTO ent_map VALUES (?, ?)", ent_pairs)

    dates = [r[0] for r in con.execute(
        "SELECT DISTINCT substr(ts,1,10) FROM events ORDER BY 1").fetchall()]
    camp_delta = {(d, c): int(v) for d, c, v in con.execute(f"""
        SELECT d, camp, SUM(dv) FROM (
          SELECT substr(e.ts,1,10) d, m.camp, CAST(e.v AS {vt}) dv
          FROM events e JOIN camp_map m ON e.t2 = m.addr WHERE e.t2 <> '{Z}'
          UNION ALL
          SELECT substr(e.ts,1,10), m.camp, -CAST(e.v AS {vt})
          FROM events e JOIN camp_map m ON e.frm = m.addr WHERE e.frm <> '{Z}'
          UNION ALL
          SELECT substr(ts,1,10), '销毁', CAST(v AS {vt}) FROM events WHERE t2 = '{Z}'
        ) GROUP BY d, camp""").fetchall()}
    ent_delta = {(d, e): int(v) for d, e, v in con.execute(f"""
        SELECT d, ent, SUM(dv) FROM (
          SELECT substr(e.ts,1,10) d, m.ent, CAST(e.v AS {vt}) dv
          FROM events e JOIN ent_map m ON e.t2 = m.addr WHERE e.t2 <> '{Z}'
          UNION ALL
          SELECT substr(e.ts,1,10), m.ent, -CAST(e.v AS {vt})
          FROM events e JOIN ent_map m ON e.frm = m.addr WHERE e.frm <> '{Z}'
        ) GROUP BY d, ent""").fetchall()}

    # 每日净供应变动（mint − burn）——当期供应口径分母的数据来源（3.36 修复）
    supply_delta = {d: int(v) for d, v in con.execute(f"""
        SELECT substr(ts,1,10) d,
               SUM(CASE WHEN frm = '{Z}' THEN CAST(v AS {vt}) ELSE 0 END)
             - SUM(CASE WHEN t2  = '{Z}' THEN CAST(v AS {vt}) ELSE 0 END)
        FROM events GROUP BY 1""").fetchall()}

    # 【3.36 分母口径修复】旧版固定用 mint_total（全史铸造总量）作分母，会把**尚未铸造**的
    # 代币提前计入残差桶「散户」——标的后期一旦大额增发，早期散户占比被系统性虚高，且图形
    # 看上去完全正常（各阵营加总仍是 100%），属静默的传播级错误。
    # 实证：IQ(ETH) 2026-07-26，2025-09 单月增发 181%，2025-09-25 的散户被算成 55.6%，
    #       真值 11.28%（虚高 44pp）；该日实际总供应仅 68.8 亿，而分母用的是全史 310.8 亿。
    # 修复=分母改用**当期净供应**（累计 mint − 累计 burn）。销毁的币已从分母扣除，故销毁
    # 不再作为阵营参与堆叠，改单列 burn_cum_pct（累计销毁 ÷ 当期供应，可能 >100%，仅供参考，
    # 绘图时勿并入堆叠）。旧口径可用 CHIP_LEGACY_CAMP_DENOM=1 取回（黄金基准回归对比用）。
    legacy = os.environ.get("CHIP_LEGACY_CAMP_DENOM") == "1"
    stack_camps = camps_order if legacy else [c for c in camps_order if c != "销毁"]

    series = {c: [] for c in stack_camps}
    series["散户"] = []
    eseries = {e: [] for e in ents_order}
    camp_cum = {c: 0 for c in camps_order}
    ent_cum = {e: 0 for e in ents_order}
    burn_pct, supply = [], 0
    for day in dates:
        supply += supply_delta.get(day, 0)
        camp_cum["销毁"] = camp_cum.get("销毁", 0) + (
            0 if "销毁" in stack_camps else camp_delta.get((day, "销毁"), 0))
        total = mint_total if legacy else supply
        if total <= 0:                      # 供应尚未产生（理论上仅可能出现在首日之前）
            for c in stack_camps:
                camp_cum[c] += camp_delta.get((day, c), 0)
                series[c].append(0.0)
            series["散户"].append(0.0)
            for e in ents_order:
                ent_cum[e] += ent_delta.get((day, e), 0)
                eseries[e].append(0.0)
            burn_pct.append(0.0)
            continue
        known = 0
        for c in stack_camps:
            camp_cum[c] += camp_delta.get((day, c), 0)
            v = camp_cum[c] / total * 100
            series[c].append(round(v, 4))
            known += v
        series["散户"].append(round(max(0, 100 - known), 4))
        for e in ents_order:
            ent_cum[e] += ent_delta.get((day, e), 0)
            eseries[e].append(round(ent_cum[e] / total * 100, 4))
        burn_pct.append(round(camp_cum.get("销毁", 0) / total * 100, 4))
    if "销毁" in series and all(v == 0 for v in series["销毁"]):
        del series["销毁"]
    out = {"dates": dates, **series}
    if not legacy:
        out["_meta"] = {"denominator": "current_net_supply",
                        "note": "分母=当期净供应(累计mint−累计burn)；burn_cum_pct 不参与堆叠"}
        out["burn_cum_pct"] = burn_pct
    if diagnostic_gate_failed:
        out["status"] = "DIAGNOSTIC_GATE_FAILED"
    entity_out = {"dates": dates, **eseries}
    if diagnostic_gate_failed:
        entity_out["status"] = "DIAGNOSTIC_GATE_FAILED"
    json.dump(out, open(f"{out_dir}/camp_series.json", "w"))
    json.dump(entity_out, open(f"{out_dir}/entity_series.json", "w"))
    if diagnostic_gate_failed:
        print(f"[camp-series] gate FAIL：诊断序列已隔离到 {out_dir}；"
              "不生成正式 provenance sidecar", flush=True)
        return
    # F-04：producer sidecar——与 replay_pass2.py 同族同深（同一共享实现），
    # balances_final.json 由同进程 pass1 刚写出（同一次重放同源，末点对账的快照锚）
    from camp_series_provenance import write_series_sidecar
    _den = "mint_total_legacy" if legacy else "current_net_supply"
    _sidecar_inputs = {"replay_stats": f"{out_dir}/replay_stats.json"}
    _fb = f"{out_dir}/balances_final.json"
    if not os.path.exists(_fb):
        # F-C6：缺终态快照当场硬拒（同 replay_pass2 口径 exit 2），不许静默少绑拖到编译期
        print(f"[camp-series] 缺 {_fb}（pass1 终态快照，末点对账的锚）"
              f"——同进程 pass1 应已写出，缺失即数据链断裂", file=sys.stderr)
        raise SystemExit(2)
    write_series_sidecar(f"{out_dir}/camp_series.json",
                         producer="scripts/evm/replay_duck.py",
                         series_format="evm-dict", denominator=_den,
                         camps_spec_path=camps_path,
                         final_balances_path=_fb,
                         inputs=_sidecar_inputs)
    write_series_sidecar(f"{out_dir}/entity_series.json",
                         producer="scripts/evm/replay_duck.py",
                         series_format="evm-entity-dict", denominator=_den,
                         camps_spec_path=camps_path, inputs=_sidecar_inputs)
    print(f"天数={len(dates)} 分母={'mint_total(legacy)' if legacy else '当期净供应'} "
          f"阵营={[k for k in series]} 实体={ents_order}", flush=True)


def _disk_precheck(tmp_path, chans=None, min_free_gb=10.0):
    """起跑前磁盘预检（QUQ 亿级 temp 两次爆仓教训；run_guarded 的事中水位是第二道）。
    输入文件总体积 ×4 作 temp 需求粗估（parquet 展开系数保守值），只警告不硬拒；
    盘余量 < min_free_gb 硬拒。"""
    import shutil as _sh
    free_gb = _sh.disk_usage(tmp_path).free / 2**30
    if free_gb < min_free_gb:
        raise SystemExit(f"[disk] {tmp_path} 所在卷仅剩 {free_gb:.1f}GB（<{min_free_gb}GB 预检线）"
                         "——先清盘再跑（旧分析 data/v2/run_*、.duck_tmp、旧 CSV 是常见大户）")
    if chans:
        in_bytes = 0
        for c in chans:
            p = c.get("path", "")
            for f in (glob.glob(os.path.join(p, "run_*", "logs.parquet")) if os.path.isdir(p)
                      else glob.glob(p)):
                try:
                    in_bytes += os.path.getsize(f)
                except OSError:
                    pass
        need_gb = in_bytes / 2**30 * 4
        if need_gb > free_gb:
            print(f"[disk][警告] 输入 {in_bytes/2**30:.1f}GB×4≈{need_gb:.0f}GB temp 粗估 > "
                  f"盘余 {free_gb:.0f}GB——建议 run_guarded --min-free-disk-gb 陪跑或先清盘",
                  flush=True)
    return free_gb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channels", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--camps", help="camps.json；给了就顺跑 pass2")
    ap.add_argument("--emit-csv", action="store_true", help="流式写旧格式 merged.csv（对表/未迁移下游用）")
    ap.add_argument("--merged-parquet", action="store_true", help="强制同时写 merged.parquet")
    ap.add_argument("--no-merged", action="store_true",
                    help="不写任何 merged 产物（亿级基准/对表跑省盘省时；默认关=行为不变）")
    ap.add_argument("--mem-limit", default="8GB")
    ap.add_argument("--threads", type=int, default=6)
    ap.add_argument("--force-varint", action="store_true",
                    help="强制任意精度 VARINT 路径（HUGEINT 聚合溢出报错时的显式出路；慢 ~5x 仍精确）")
    a = ap.parse_args()
    chans = preflight_channels(a.channels, a.out_dir)

    tmp = os.path.join(a.out_dir, ".duck_tmp")
    os.makedirs(tmp, exist_ok=True)
    free_gb = _disk_precheck(tmp, chans)
    con = duckdb.connect()
    con.execute(f"SET memory_limit='{a.mem_limit}'")
    con.execute(f"SET threads={a.threads}")
    con.execute(f"SET temp_directory='{tmp}'")
    # temp 上限=盘余量-5GB 安全边（DuckDB 撞上限报错可控；撞盘满拖死整机不可控）
    con.execute(f"SET max_temp_directory_size='{max(int(free_gb) - 5, 5)}GB'")
    con.execute("SET preserve_insertion_order=false")

    rej = build_events(con, chans)
    if rej["n_bad_fields"] or rej["n_out_of_segment"]:
        receipt = {**rej, "gate_pass": False,
                   "failure": "rejected_input_rows",
                   "policy": "n_bad_fields == 0 and n_out_of_segment == 0"}
        json.dump(receipt, open(f"{a.out_dir}/replay_stats.json", "w"), indent=1)
        raise SystemExit(
            f"[fail-closed] 输入含 rejected rows: bad_fields={rej['n_bad_fields']} "
            f"out_of_segment={rej['n_out_of_segment']}——修复或重新采集后再重放")
    # uint256 策略：events.v 统一为十进制字符串，探最大位数（≤37 走 HUGEINT，超界
    # VARINT——注意 VARINT 仅可加/SUM，乘法退化 DOUBLE）；HUGEINT 聚合若仍溢出
    # DuckDB 会硬报错（实测 fail-loud 不静默环绕），届时 --force-varint 重跑
    maxlen = con.execute("SELECT COALESCE(MAX(LENGTH(v)), 0) FROM events").fetchone()[0]
    vt = "VARINT" if a.force_varint else ("HUGEINT" if maxlen <= 37 else "VARINT")
    print(f"value 最大位数={maxlen} -> {vt} 路径", flush=True)
    stats, mint_total = replay_pass1(con, a.out_dir, vt)
    stats.update(rej)
    stats.update(replay_provenance(a.out_dir, __file__))
    json.dump(stats, open(f"{a.out_dir}/replay_stats.json", "w"), indent=1)
    print("stats:", json.dumps(stats, indent=1), flush=True)
    if not a.no_merged:
        emit_merged(con, a.out_dir, a.emit_csv, a.merged_parquet)
    if a.camps:
        if stats["gate_pass"]:
            replay_pass2(con, a.camps, a.out_dir, mint_total, vt)
        else:
            diagnostic_dir = os.path.join(a.out_dir, "diagnostics", "gate-failed")
            os.makedirs(diagnostic_dir, exist_ok=True)
            replay_pass2(con, a.camps, diagnostic_dir, mint_total, vt,
                         diagnostic_gate_failed=True)
    print("[gate]", "PASS" if stats["gate_pass"] else "FAIL——禁止进入下游分析")
    sys.exit(0 if stats["gate_pass"] else 4)


if __name__ == "__main__":
    main()
