#!/usr/bin/env python3
"""A6 分层抽查计划器——对账三查"时间抽查"的锚点选取升级（纯随机 → 分层矩阵+强制覆盖）。

痛点定位：旧流程时间抽查是纯随机锚点，容易全抽在平静期（转账稀疏、余额不动），
抽了等于没抽。本脚本按「时间三段（早/中/晚）× 余额档（大/中/小户）」分层随机抽
"地址-日"锚点，再叠加四类强制覆盖点（全史最大单笔 / 最大单日净变动 / 数据源交界块
附近 / 门槛 ±10% 边缘地址），每点附预期日终余额与浏览器核对 URL，人工照单核对。

输入自适应（列名嗅探，见 _detect_input）：
  - v2 parquet 目录（run_*/logs.parquet + blocks.parquet，HyperSync v2 原始 hex）
  - v1 7列 CSV（block,ts,tx,from,to,value|value_raw,uniqueId；ts ISO）
  - GME 变体 CSV（block,tx,log_index,from,to,value,timestamp；unix 秒）
  - 单 parquet 文件（列名同上述 CSV 任一变体）
  ⚠ Solana soltx-*.jsonl.gz 不支持（Solana 案是混合重建、无全量 merged，锚点抽查
    走 solana/anchor_sampler.py 通道）；value 超 127bit 的超大值币硬退（同 replay_duck）。

纯离线：只读输入文件做 DuckDB 聚合，不打任何外网；大文件靠 DuckDB 列式+mem-limit。

用法:
  python3 anchor_plan.py --input <transfers.csv|merged.parquet|v2目录> \
      --chain bsc --token 0x4fa7... --total-supply 1000000000 --decimals 18 \
      [--threshold-pct 1.0] [--boundary-blocks 111305341,111314259] \
      [--per-cell 1] [--edge-max 5] [--seed 42] [--mem-limit 6GB] --out-dir plan_out

输出：out-dir/anchor_plan.json（结构化）+ anchor_plan.md（人工核对清单）。
（来源：A6 小工程件，2026-07-22；QUQ v2 1.03 亿行实测通过）"""
import argparse
import datetime
import json
import os
import sys

import duckdb

Z = '0x0000000000000000000000000000000000000000'
DEAD = '0x000000000000000000000000000000000000dead'

# 浏览器核对 URL 模板（token 余额页 / tx 页 / 历史余额工具页）
EXPLORER = {
    "bsc":      ("https://bscscan.com", "evm"),
    "eth":      ("https://etherscan.io", "evm"),
    "ethereum": ("https://etherscan.io", "evm"),
    "base":     ("https://basescan.org", "evm"),
    "arbitrum": ("https://arbiscan.io", "evm"),
    "polygon":  ("https://polygonscan.com", "evm"),
    "solana":   ("https://solscan.io", "sol"),
}


def urls(chain, token, addr=None, tx=None):
    base, kind = EXPLORER.get(chain, (f"https://{chain}scan.com", "evm"))
    u = {}
    if kind == "sol":
        if addr:
            u["addr"] = f"{base}/account/{addr}" + (f"?token_address={token}" if token else "")
        if tx:
            u["tx"] = f"{base}/tx/{tx}"
    else:
        if addr and token:
            u["addr"] = f"{base}/token/{token}?a={addr}"
        elif addr:
            u["addr"] = f"{base}/address/{addr}"
        if tx:
            u["tx"] = f"{base}/tx/{tx}"
        u["balance_tool"] = f"{base}/tokencheck-tool"  # 历史余额按块号查（填 token+addr+block）
    return u


def _detect_input(con, path):
    """输入自适应 → 返回标准事件视图 SQL（列 b, day, tx, frm, t2, v[HUGEINT]）。"""
    if os.path.isdir(path):
        logs = os.path.join(path, "run_*", "logs.parquet")
        blocks = os.path.join(path, "run_*", "blocks.parquet")
        # 值域探测（同 replay_duck：高 32 hex 非零或 hi64 ≥ 2^63 → 两段 HUGEINT 溢出，硬退）
        n_hi, mx = con.execute(f"""
            SELECT COUNT(*) FILTER (WHERE substr(data, 3, 32) <> repeat('0', 32)),
                   COALESCE(MAX(TRY_CAST('0x' || substr(data, 35, 16) AS UBIGINT)), 0)
            FROM read_parquet('{logs}', union_by_name=true)
            WHERE data IS NOT NULL AND LENGTH(data) = 66""").fetchone()
        if n_hi or int(mx) >= 2 ** 63:
            sys.exit(f"[fail-closed] value 超 127bit（高位非零 {n_hi} 行）——超大值币需扩展，先人工核数据")
        val = ("('0x'||substr(data,35,16))::UBIGINT::HUGEINT * '18446744073709551616'::HUGEINT"
               " + ('0x'||substr(data,51,16))::UBIGINT::HUGEINT")
        return f"""
            SELECT l.block_number b,
                   strftime(make_timestamp((bt.ts_i * 1000000)::BIGINT), '%Y-%m-%d') d,
                   lower(l.transaction_hash) tx,
                   '0x' || right(lower(COALESCE(l.topic1, repeat('0', 64))), 40) frm,
                   '0x' || right(lower(COALESCE(l.topic2, repeat('0', 64))), 40) t2,
                   CASE WHEN l.data IS NULL OR l.data IN ('', '0x')
                        THEN 0::HUGEINT ELSE {val} END v
            FROM read_parquet('{logs}', union_by_name=true) l
            JOIN (SELECT number, TRY_CAST(ANY_VALUE(timestamp) AS UBIGINT) ts_i
                  FROM read_parquet('{blocks}', union_by_name=true)
                  WHERE number IS NOT NULL GROUP BY number) bt ON bt.number = l.block_number
            WHERE l.block_number IS NOT NULL
              AND (l.data IS NULL OR l.data IN ('', '0x') OR LENGTH(l.data) = 66)"""
    # 单文件：csv / parquet，先探列名
    reader = (f"read_csv('{path}', header=true, all_varchar=true, ignore_errors=true)"
              if path.endswith(".csv") or path.endswith(".csv.gz")
              else f"read_parquet('{path}')")
    cols = {r[0].lower() for r in con.execute(f"DESCRIBE SELECT * FROM {reader}").fetchall()}
    need = {"from", "to", "block"}
    if not need <= cols:
        sys.exit(f"[fatal] 认不出的表结构（缺 {need - cols}）：{sorted(cols)}")
    vcol = "value_raw" if "value_raw" in cols else "value"
    if "ts" in cols:      # ISO 字符串（v1 两代表头通用）
        day = 'substr("ts", 1, 10)'
    elif "timestamp" in cols:  # GME 变体：unix 秒
        day = "strftime(make_timestamp(TRY_CAST(\"timestamp\" AS BIGINT) * 1000000), '%Y-%m-%d')"
    else:
        sys.exit(f"[fatal] 找不到时间列（ts/timestamp）：{sorted(cols)}")
    return f"""
        SELECT TRY_CAST("block" AS BIGINT) b, {day} d, lower("tx") tx,
               lower("from") frm, COALESCE(NULLIF(lower("to"), ''), '{Z}') t2,
               TRY_CAST("{vcol}" AS HUGEINT) v
        FROM {reader}
        WHERE TRY_CAST("block" AS BIGINT) IS NOT NULL
          AND TRY_CAST("{vcol}" AS HUGEINT) IS NOT NULL"""


def main():
    ap = argparse.ArgumentParser(description="A6 分层抽查计划器（时间三段×余额档+强制覆盖点）")
    ap.add_argument("--input", required=True, help="merged 转账数据：csv / parquet / v2 目录")
    ap.add_argument("--chain", required=True, help="bsc/eth/base/arbitrum/polygon/...")
    ap.add_argument("--token", default=None, help="代币合约地址（拼核对 URL 用，建议提供）")
    ap.add_argument("--total-supply", type=float, required=True, help="总供应（human 单位）")
    ap.add_argument("--decimals", type=int, required=True)
    ap.add_argument("--threshold-pct", type=float, default=1.0,
                    help="大户门槛（占总供应%%，默认 1.0；中户=其 1/10，小户再往下）")
    ap.add_argument("--min-pct", type=float, default=0.0001,
                    help="小户下限（占总供应%%，默认 0.0001，滤尘埃）")
    ap.add_argument("--boundary-blocks", default=None,
                    help="数据源交界块号，逗号分隔（拿不到就不传，跳过该类强制点）")
    ap.add_argument("--per-cell", type=int, default=1, help="每格抽点数（默认 1，共 3×3 格）")
    ap.add_argument("--edge-max", type=int, default=5, help="门槛±10%% 边缘地址最多列几个")
    ap.add_argument("--seed", type=int, default=42, help="随机种子（同种子可复现）")
    ap.add_argument("--mem-limit", default="6GB")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()

    os.makedirs(a.out_dir, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET memory_limit='{a.mem_limit}'; SET threads={a.threads}; "
                f"SET preserve_insertion_order=false;")
    ev = _detect_input(con, a.input)
    scale = 10 ** a.decimals
    supply_raw = int(a.total_supply * scale)

    def pct(raw):  # 原始值 → 占总供应百分比
        return round(int(raw) / supply_raw * 100, 6)

    def human(raw):
        return round(int(raw) / scale, 6)

    print("[1/5] 日频净变动聚合（全量扫描，大数据需几分钟）…", flush=True)
    con.execute(f"""
        CREATE TEMP TABLE daily AS
        SELECT addr, d, SUM(dv)::HUGEINT delta
        FROM (SELECT frm addr, d, -v dv FROM ({ev}) WHERE frm <> '{Z}'
              UNION ALL
              SELECT t2 addr, d, v dv FROM ({ev}))
        WHERE d IS NOT NULL GROUP BY addr, d""")
    con.execute("""
        CREATE TEMP TABLE bal AS
        SELECT addr, SUM(delta)::HUGEINT bal FROM daily GROUP BY addr""")
    con.execute(f"""
        CREATE TEMP TABLE dayblk AS
        SELECT d, MAX(b) day_end_block, MIN(b) day_start_block
        FROM ({ev}) WHERE d IS NOT NULL GROUP BY d""")
    d0, d1, ndays = con.execute(
        "SELECT MIN(d), MAX(d), COUNT(DISTINCT d) FROM dayblk").fetchone()
    if not d0:
        sys.exit("[fatal] 数据里解析不出任何日期")
    print(f"    时间范围 {d0} → {d1}（{ndays} 个活跃日）", flush=True)

    # 时间三等分（按日历跨度，不是活跃日数——平静期也占段位，正是要覆盖的对象）
    t0 = datetime.date.fromisoformat(d0)
    t1 = datetime.date.fromisoformat(d1)
    span = max((t1 - t0).days, 2)
    cut1 = (t0 + datetime.timedelta(days=span // 3)).isoformat()
    cut2 = (t0 + datetime.timedelta(days=span * 2 // 3)).isoformat()
    thr_raw = int(a.threshold_pct / 100 * supply_raw)
    mid_raw = thr_raw // 10
    min_raw = int(a.min_pct / 100 * supply_raw)

    print("[2/5] 分层矩阵抽样（3 时段 × 3 余额档）…", flush=True)
    con.execute(f"""
        CREATE TEMP TABLE cells AS
        SELECT dd.addr, dd.d, dd.delta,
               CASE WHEN dd.d < '{cut1}' THEN '早' WHEN dd.d < '{cut2}' THEN '中'
                    ELSE '晚' END tseg,
               CASE WHEN b.bal >= {thr_raw} THEN '大户'
                    WHEN b.bal >= {mid_raw} THEN '中户' ELSE '小户' END tier
        FROM daily dd JOIN bal b USING (addr)
        WHERE b.bal >= {min_raw} AND dd.addr NOT IN ('{Z}', '{DEAD}')""")
    picked = con.execute(f"""
        SELECT tseg, tier, addr, d FROM (
            SELECT *, row_number() OVER (PARTITION BY tseg, tier
                       ORDER BY hash(addr || d || '{a.seed}')) rn
            FROM cells) WHERE rn <= {a.per_cell}
        ORDER BY tseg, tier""").fetchall()

    def day_end_balance(addr, day):
        r = con.execute(
            "SELECT COALESCE(SUM(delta), 0)::VARCHAR FROM daily WHERE addr=? AND d<=?",
            [addr, day]).fetchone()
        return int(r[0])

    def blk_of(day):
        r = con.execute("SELECT day_end_block FROM dayblk WHERE d<=? "
                        "ORDER BY d DESC LIMIT 1", [day]).fetchone()
        return int(r[0]) if r else None

    def final_pct(addr):
        r = con.execute("SELECT bal::VARCHAR FROM bal WHERE addr=?", [addr]).fetchone()
        return pct(r[0]) if r else None

    def point(addr, day, kind, note=""):
        raw = day_end_balance(addr, day)
        return {"kind": kind, "addr": addr, "day": day,
                "day_end_block": blk_of(day),
                "expected_balance_raw": str(raw),
                "expected_balance_human": human(raw), "expected_pct": pct(raw),
                "final_pct": final_pct(addr),
                "note": note, "check_urls": urls(a.chain, a.token, addr=addr)}

    # 档位按"最终余额"划分；抽点日的余额可与档位量级不同（早期尚未建仓等），二者都列出
    matrix = [point(ad, dy, f"矩阵[{ts}·{ti}]",
                    note=f"{ts}期活跃、最终余额属{ti}档；核对该日终持仓")
              for ts, ti, ad, dy in picked]

    print("[3/5] 强制覆盖点：最大单笔 / 最大单日净变动…", flush=True)
    forced = []
    r = con.execute(f"""SELECT tx, frm, t2, v::VARCHAR, b, d FROM ({ev})
                        ORDER BY v DESC LIMIT 1""").fetchone()
    if r:
        tx, frm, t2, v, b, day = r
        forced.append({"kind": "全史最大单笔转账", "tx": tx, "from": frm, "to": t2,
                       "day": day, "block": int(b),
                       "expected_value_raw": v, "expected_value_human": human(v),
                       "expected_pct": pct(v),
                       "note": "浏览器打开 tx 核对金额与双方地址",
                       "check_urls": urls(a.chain, a.token, tx=tx)})
    r = con.execute(f"""SELECT addr, d, delta::VARCHAR FROM daily
                        WHERE addr NOT IN ('{Z}', '{DEAD}')
                        ORDER BY abs(delta) DESC LIMIT 1""").fetchone()
    if r:
        ad, dy, dl = r
        p = point(ad, dy, "最大单日净变动地址-日",
                  note=f"该日净变动 {human(dl)}（{pct(dl)}% 供应）；核对当日流水与日终余额")
        p["day_delta_human"] = human(dl)
        forced.append(p)

    print("[4/5] 强制覆盖点：交界块附近 / 门槛±10% 边缘地址…", flush=True)
    bounds = [int(x) for x in a.boundary_blocks.split(",")] if a.boundary_blocks else []
    for bb in bounds:
        for side, cond, order in (("前", f"b <= {bb}", "DESC"), ("后", f"b > {bb}", "ASC")):
            r = con.execute(f"""SELECT tx, frm, t2, v::VARCHAR, b, d FROM ({ev})
                                WHERE {cond} ORDER BY b {order} LIMIT 1""").fetchone()
            if r:
                tx, frm, t2, v, b, day = r
                forced.append({"kind": f"交界块 {bb} {side}最近转账", "tx": tx,
                               "from": frm, "to": t2, "block": int(b), "day": day,
                               "expected_value_raw": v, "expected_value_human": human(v),
                               "note": "数据源交界完备性：核对该 tx 存在且交界两侧无缺段",
                               "check_urls": urls(a.chain, a.token, tx=tx)})
    edges = con.execute(f"""
        SELECT addr, bal::VARCHAR FROM bal
        WHERE bal BETWEEN {int(thr_raw * 0.9)} AND {int(thr_raw * 1.1)}
          AND addr NOT IN ('{Z}', '{DEAD}')
        ORDER BY hash(addr || '{a.seed}') LIMIT {a.edge_max}""").fetchall()
    for ad, bl in edges:
        forced.append({"kind": "门槛±10% 边缘地址", "addr": ad, "day": d1,
                       "expected_balance_raw": bl, "expected_balance_human": human(bl),
                       "expected_pct": pct(bl),
                       "note": f"最终余额贴 {a.threshold_pct}% 门槛（±10%）——错一笔就跨档，重点核对",
                       "check_urls": urls(a.chain, a.token, addr=ad)})

    print("[5/5] 写出计划…", flush=True)
    stats = {r[0] + "·" + r[1]: r[2] for r in con.execute(
        "SELECT tseg, tier, COUNT(*) FROM cells GROUP BY tseg, tier").fetchall()}
    plan = {"generated_at": datetime.datetime.now(datetime.timezone.utc)
                .strftime("%Y-%m-%dT%H:%M:%SZ"),
            "input": os.path.abspath(a.input), "chain": a.chain, "token": a.token,
            "total_supply": a.total_supply, "decimals": a.decimals,
            "threshold_pct": a.threshold_pct, "seed": a.seed,
            "date_range": [d0, d1], "time_cuts": [cut1, cut2],
            "cell_population": stats, "boundary_blocks": bounds,
            "matrix_points": matrix, "forced_points": forced}
    jp = os.path.join(a.out_dir, "anchor_plan.json")
    with open(jp, "w") as f:
        json.dump(plan, f, ensure_ascii=False, indent=1)

    md = [f"# 分层抽查计划（{a.chain} · {a.token or '?'}）",
          f"数据 {d0} → {d1}；时段切点 {cut1} / {cut2}；门槛 {a.threshold_pct}%；seed={a.seed}",
          "", "## 一、分层矩阵抽点（时间三段 × 余额档）",
          "| 格 | 地址 | 日期 | 日终块 | 预期余额 | 占供应% | 最终% | 核对 URL |",
          "|---|---|---|---|---|---|---|---|"]
    for p in matrix:
        md.append(f"| {p['kind']} | `{p['addr']}` | {p['day']} | {p['day_end_block']} "
                  f"| {p['expected_balance_human']:,} | {p['expected_pct']} | {p['final_pct']} "
                  f"| {p['check_urls'].get('addr', '')} |")
    md += ["", "## 二、强制覆盖点", ""]
    for p in forced:
        md.append(f"### {p['kind']}")
        for k in ("addr", "tx", "from", "to", "day", "block", "day_end_block"):
            if p.get(k) is not None:
                md.append(f"- {k}: `{p[k]}`")
        for k in ("expected_balance_human", "expected_pct", "expected_value_human",
                  "day_delta_human"):
            if p.get(k) is not None:
                md.append(f"- {k}: {p[k]:,}" if isinstance(p[k], (int, float))
                          else f"- {k}: {p[k]}")
        md.append(f"- 说明: {p['note']}")
        for uk, uv in p["check_urls"].items():
            md.append(f"- URL({uk}): {uv}")
        md.append("")
    md += ["## 核对方法",
           "- 地址-日锚点：EVM 用浏览器 tokencheck-tool（token+地址+上表『日终块』查历史余额），"
           "或在地址页翻该日交易核流水；tx 锚点：打开 tx 页核金额与双方。",
           "- 任何一点对不上 → 按对账三查流程回溯该地址全史重放，不许只改单点。"]
    mp = os.path.join(a.out_dir, "anchor_plan.md")
    with open(mp, "w") as f:
        f.write("\n".join(md) + "\n")
    print(f"[done] 矩阵点 {len(matrix)} + 强制点 {len(forced)} → {jp} / {mp}")


if __name__ == "__main__":
    main()
