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

用法：
  python3 replay_duck.py --channels channels.json --out-dir out \
      [--camps camps.json] [--emit-csv] [--merged-parquet] \
      [--mem-limit 8GB] [--threads 6]
"""
import argparse, csv, glob, json, os, sys

import duckdb

Z = '0x0000000000000000000000000000000000000000'
DEAD = '0x000000000000000000000000000000000000dead'


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
        # names 强制按位置命名（复刻旧引擎位置解析——v1 文件表头 value/value_raw 两代并存）
        src = (f"read_csv('{c['path']}', header=true, all_varchar=true, "
               f"ignore_errors=true, names=['block','ts','tx','from','to','value','uniqueId'])")
        raw, bad, seg = con.execute(f"""
            WITH r AS (SELECT TRY_CAST(block AS BIGINT) b,
                              TRY_CAST(regexp_extract(uniqueId, '(\\d+)$', 1) AS BIGINT) li,
                              value ~ '^\\d+$' AS okv
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
                   TRY_CAST(regexp_extract(uniqueId, '(\\d+)$', 1) AS BIGINT) li,
                   lower("from") frm,
                   COALESCE(NULLIF(lower("to"), ''), '{Z}') t2,
                   value v, '{c['tag']}' tag
            FROM {src}
            WHERE TRY_CAST(block AS BIGINT) IS NOT NULL
              AND TRY_CAST(regexp_extract(uniqueId, '(\\d+)$', 1) AS BIGINT) IS NOT NULL
              AND value ~ '^\\d+$'
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
    su = con.execute("SELECT COALESCE(SUM(s), 0) FROM bal").fetchone()[0]
    neg = con.execute("SELECT COUNT(*) FROM bal WHERE s < 0").fetchone()[0]
    uniq = con.execute("SELECT COUNT(*) FROM bal").fetchone()[0]
    n_events = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    mint_total, burn_total, su = int(mint_total), int(burn_total), int(su)

    # 峰值：块末口径 cumsum 窗口；VARINT 窗口不可用时回退 Python 流式（输入已聚合）
    peak_min = mint_total // 1000
    con.execute("CREATE TABLE ab AS SELECT a, b, SUM(d) dd FROM deltas GROUP BY a, b")
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


def replay_pass2(con, camps_path, out_dir, mint_total, vt):
    """日度阵营/实体序列——known 累加按 camps.json 键序，与旧 snap() 逐表达式同构。"""
    spec = json.load(open(camps_path))
    camps_order = list(spec.get("camps", {}).keys())
    if "销毁" not in camps_order:
        camps_order.append("销毁")
    addr2camp = {}
    for c, addrs in spec.get("camps", {}).items():
        for ad in addrs:
            addr2camp[ad.lower()] = c          # 后配置覆盖先前（复刻 dict 语义）
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

    total = mint_total
    series = {c: [] for c in camps_order}
    series["散户"] = []
    eseries = {e: [] for e in ents_order}
    camp_cum = {c: 0 for c in camps_order}
    ent_cum = {e: 0 for e in ents_order}
    for day in dates:
        known = 0
        for c in camps_order:
            camp_cum[c] += camp_delta.get((day, c), 0)
            v = camp_cum[c] / total * 100
            series[c].append(round(v, 4))
            known += v
        series["散户"].append(round(max(0, 100 - known), 4))
        for e in ents_order:
            ent_cum[e] += ent_delta.get((day, e), 0)
            eseries[e].append(round(ent_cum[e] / total * 100, 4))
    if "销毁" in series and all(v == 0 for v in series["销毁"]):
        del series["销毁"]
    json.dump({"dates": dates, **series}, open(f"{out_dir}/camp_series.json", "w"))
    json.dump({"dates": dates, **eseries}, open(f"{out_dir}/entity_series.json", "w"))
    print(f"天数={len(dates)} 阵营={[k for k in series]} 实体={ents_order}", flush=True)


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
    ap.add_argument("--mem-limit", default="8GB")
    ap.add_argument("--threads", type=int, default=6)
    ap.add_argument("--force-varint", action="store_true",
                    help="强制任意精度 VARINT 路径（HUGEINT 聚合溢出报错时的显式出路；慢 ~5x 仍精确）")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    chans = json.load(open(a.channels))["channels"]
    segs = sorted((c["lo"], c["hi"], c["tag"]) for c in chans)
    for (l1, h1, t1), (l2, h2, t2) in zip(segs, segs[1:]):
        if l2 < h1:
            raise SystemExit(f"块段重叠：{t1}=[{l1},{h1}) 与 {t2}=[{l2},{h2}) ——通道归属必须互斥")

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
    # uint256 策略：events.v 统一为十进制字符串，探最大位数（≤37 走 HUGEINT，超界
    # VARINT——注意 VARINT 仅可加/SUM，乘法退化 DOUBLE）；HUGEINT 聚合若仍溢出
    # DuckDB 会硬报错（实测 fail-loud 不静默环绕），届时 --force-varint 重跑
    maxlen = con.execute("SELECT COALESCE(MAX(LENGTH(v)), 0) FROM events").fetchone()[0]
    vt = "VARINT" if a.force_varint else ("HUGEINT" if maxlen <= 37 else "VARINT")
    print(f"value 最大位数={maxlen} -> {vt} 路径", flush=True)
    stats, mint_total = replay_pass1(con, a.out_dir, vt)
    stats.update(rej)
    json.dump(stats, open(f"{a.out_dir}/replay_stats.json", "w"), indent=1)
    print("stats:", json.dumps(stats, indent=1), flush=True)
    emit_merged(con, a.out_dir, a.emit_csv, a.merged_parquet)
    if a.camps:
        replay_pass2(con, a.camps, a.out_dir, mint_total, vt)
    print("[gate]", "PASS" if stats["gate_pass"] else "FAIL——禁止进入下游分析")
    sys.exit(0 if stats["gate_pass"] else 4)


if __name__ == "__main__":
    main()
