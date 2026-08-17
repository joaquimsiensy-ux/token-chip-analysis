#!/usr/bin/env python3
"""Shared deterministic input identity and EVM anchor-selection core."""
import datetime
import hashlib
import json
import os
from pathlib import Path

import duckdb

from anchor_point_contract import LEGACY_FINAL_BLOCK_EDGE_KIND

Z = "0x0000000000000000000000000000000000000000"
DEAD = "0x000000000000000000000000000000000000dead"
EXPECTED_PLAN_PRODUCER = "scripts/lib/anchor_plan.py"
MIN_PER_CELL = 2
MIN_EDGE_MAX = 3

REPLAY_PARAMETER_FIELDS = (
    "chain", "token", "final_block", "total_supply", "decimals",
    "threshold_pct", "min_pct", "per_cell", "edge_max", "seed",
    "boundary_blocks",
)


def validate_anchor_coverage_parameters(per_cell, edge_max):
    """Reject plans whose caller-controlled sampling budget is too weak."""
    for value, field, minimum in (
            (per_cell, "per_cell", MIN_PER_CELL),
            (edge_max, "edge_max", MIN_EDGE_MAX)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"minimum coverage requires integer {field}")
        if value < minimum:
            raise ValueError(
                f"minimum coverage requires {field}>={minimum}; got {value}")
EXPLORER = {
    "bsc": ("https://bscscan.com", "evm"),
    "eth": ("https://etherscan.io", "evm"),
    "ethereum": ("https://etherscan.io", "evm"),
    "base": ("https://basescan.org", "evm"),
    "arbitrum": ("https://arbiscan.io", "evm"),
    "polygon": ("https://polygonscan.com", "evm"),
    "solana": ("https://solscan.io", "sol"),
}


def urls(chain, token, addr=None, tx=None):
    base, kind = EXPLORER.get(chain, (f"https://{chain}scan.com", "evm"))
    result = {}
    if kind == "sol":
        if addr:
            result["addr"] = f"{base}/account/{addr}" + (
                f"?token_address={token}" if token else "")
        if tx:
            result["tx"] = f"{base}/tx/{tx}"
    else:
        if addr and token:
            result["addr"] = f"{base}/token/{token}?a={addr}"
        elif addr:
            result["addr"] = f"{base}/address/{addr}"
        if tx:
            result["tx"] = f"{base}/tx/{tx}"
        result["balance_tool"] = f"{base}/tokencheck-tool"
    return result


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def input_identity(raw_path):
    """Return the canonical content identity used by producer and consumer."""
    shown = Path(raw_path).expanduser()
    if shown.is_symlink():
        raise ValueError(f"input symlink rejected: {raw_path}")
    path = shown.resolve(strict=True)
    if path.is_file():
        size = path.stat().st_size
        file_hash = sha256_file(path)
        files = [{"path": str(path), "size": size, "sha256": file_hash}]
        return {"path": str(path), "kind": "file", "size": size,
                "sha256": file_hash}, files
    if not path.is_dir():
        raise ValueError(f"input is not a file or directory: {raw_path}")
    files = []
    for item in sorted(path.rglob("*")):
        if item.is_symlink():
            raise ValueError(f"input directory contains symlink: {item}")
        if item.is_file():
            files.append({"path": item.relative_to(path).as_posix(),
                          "size": item.stat().st_size, "sha256": sha256_file(item)})
    if not files:
        raise ValueError(f"input directory contains no regular files: {raw_path}")
    encoded = json.dumps(files, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return {"path": str(path), "kind": "directory",
            "size": sum(item["size"] for item in files),
            "sha256": hashlib.sha256(encoded).hexdigest()}, files


def _detect_input(con, raw_path):
    """Adapt supported transfer inputs to columns b, d, tx, frm, t2 and v."""
    path = str(raw_path)
    if os.path.isdir(path):
        logs = os.path.join(path, "run_*", "logs.parquet")
        blocks = os.path.join(path, "run_*", "blocks.parquet")
        n_hi, maximum = con.execute(f"""
            SELECT COUNT(*) FILTER (WHERE substr(data, 3, 32) <> repeat('0', 32)),
                   COALESCE(MAX(TRY_CAST('0x' || substr(data, 35, 16) AS UBIGINT)), 0)
            FROM read_parquet('{logs}', union_by_name=true)
            WHERE data IS NOT NULL AND LENGTH(data) = 66""").fetchone()
        if n_hi or int(maximum) >= 2 ** 63:
            raise ValueError(
                f"value exceeds 127 bits (nonzero high bits in {n_hi} rows); manual extension required")
        value = (
            "('0x'||substr(data,35,16))::UBIGINT::HUGEINT * "
            "'18446744073709551616'::HUGEINT"
            " + ('0x'||substr(data,51,16))::UBIGINT::HUGEINT")
        return f"""
            SELECT l.block_number b,
                   strftime(make_timestamp((bt.ts_i * 1000000)::BIGINT), '%Y-%m-%d') d,
                   lower(l.transaction_hash) tx,
                   '0x' || right(lower(COALESCE(l.topic1, repeat('0', 64))), 40) frm,
                   '0x' || right(lower(COALESCE(l.topic2, repeat('0', 64))), 40) t2,
                   CASE WHEN l.data IS NULL OR l.data IN ('', '0x')
                        THEN 0::HUGEINT ELSE {value} END v
            FROM read_parquet('{logs}', union_by_name=true) l
            JOIN (SELECT number, TRY_CAST(ANY_VALUE(timestamp) AS UBIGINT) ts_i
                  FROM read_parquet('{blocks}', union_by_name=true)
                  WHERE number IS NOT NULL GROUP BY number) bt ON bt.number = l.block_number
            WHERE l.block_number IS NOT NULL
              AND (l.data IS NULL OR l.data IN ('', '0x') OR LENGTH(l.data) = 66)"""
    reader = (f"read_csv('{path}', header=true, all_varchar=true, ignore_errors=true)"
              if path.endswith(".csv") or path.endswith(".csv.gz")
              else f"read_parquet('{path}')")
    columns = {row[0].lower()
               for row in con.execute(f"DESCRIBE SELECT * FROM {reader}").fetchall()}
    required = {"from", "to", "block"}
    if not required <= columns:
        raise ValueError(f"unrecognized transfer table; missing {required - columns}: {sorted(columns)}")
    value_column = "value_raw" if "value_raw" in columns else "value"
    if "ts" in columns:
        day = 'substr("ts", 1, 10)'
    elif "timestamp" in columns:
        day = "strftime(make_timestamp(TRY_CAST(\"timestamp\" AS BIGINT) * 1000000), '%Y-%m-%d')"
    else:
        raise ValueError(f"transfer table has no ts/timestamp column: {sorted(columns)}")
    return f"""
        SELECT TRY_CAST("block" AS BIGINT) b, {day} d, lower("tx") tx,
               lower("from") frm, COALESCE(NULLIF(lower("to"), ''), '{Z}') t2,
               TRY_CAST("{value_column}" AS HUGEINT) v
        FROM {reader}
        WHERE TRY_CAST("block" AS BIGINT) IS NOT NULL
          AND TRY_CAST("{value_column}" AS HUGEINT) IS NOT NULL"""


def _progress(callback, message):
    if callback is not None:
        callback(message)


def generate_anchor_selection(*, input_path, chain, token, total_supply, decimals,
                              threshold_pct, min_pct, boundary_blocks, per_cell,
                              edge_max, seed, mem_limit="6GB", threads=4,
                              progress=None):
    """Replay the full deterministic anchor selection and return plan result fields."""
    con = duckdb.connect()
    try:
        con.execute(f"SET memory_limit='{mem_limit}'; SET threads={threads}; "
                    "SET preserve_insertion_order=false;")
        events = _detect_input(con, input_path)
        scale = 10 ** decimals
        supply_raw = int(total_supply * scale)
        if supply_raw <= 0:
            raise ValueError("total_supply and decimals must produce a positive raw supply")

        def pct(raw):
            return round(int(raw) / supply_raw * 100, 6)

        def human(raw):
            return round(int(raw) / scale, 6)

        _progress(progress, "[1/5] 日频净变动聚合（全量扫描，大数据需几分钟）…")
        con.execute(f"""
            CREATE TEMP TABLE daily AS
            SELECT addr, d, SUM(dv)::HUGEINT delta
            FROM (SELECT frm addr, d, -v dv FROM ({events}) WHERE frm <> '{Z}'
                  UNION ALL
                  SELECT t2 addr, d, v dv FROM ({events}))
            WHERE d IS NOT NULL GROUP BY addr, d""")
        con.execute("""
            CREATE TEMP TABLE bal AS
            SELECT addr, SUM(delta)::HUGEINT bal FROM daily GROUP BY addr""")
        con.execute(f"""
            CREATE TEMP TABLE dayblk AS
            SELECT d, MAX(b) day_end_block, MIN(b) day_start_block
            FROM ({events}) WHERE d IS NOT NULL GROUP BY d""")
        d0, d1, ndays = con.execute(
            "SELECT MIN(d), MAX(d), COUNT(DISTINCT d) FROM dayblk").fetchone()
        if not d0:
            raise ValueError("input contains no parseable dates")
        _progress(progress, f"    时间范围 {d0} → {d1}（{ndays} 个活跃日）")

        t0 = datetime.date.fromisoformat(d0)
        t1 = datetime.date.fromisoformat(d1)
        span = max((t1 - t0).days, 2)
        cut1 = (t0 + datetime.timedelta(days=span // 3)).isoformat()
        cut2 = (t0 + datetime.timedelta(days=span * 2 // 3)).isoformat()
        threshold_raw = int(threshold_pct / 100 * supply_raw)
        middle_raw = threshold_raw // 10
        minimum_raw = int(min_pct / 100 * supply_raw)

        _progress(progress, "[2/5] 分层矩阵抽样（3 时段 × 3 余额档）…")
        con.execute(f"""
            CREATE TEMP TABLE cells AS
            SELECT dd.addr, dd.d, dd.delta,
                   CASE WHEN dd.d < '{cut1}' THEN '早' WHEN dd.d < '{cut2}' THEN '中'
                        ELSE '晚' END tseg,
                   CASE WHEN b.bal >= {threshold_raw} THEN '大户'
                        WHEN b.bal >= {middle_raw} THEN '中户' ELSE '小户' END tier
            FROM daily dd JOIN bal b USING (addr)
            WHERE b.bal >= {minimum_raw} AND dd.addr NOT IN ('{Z}', '{DEAD}')""")
        picked = con.execute(f"""
            SELECT tseg, tier, addr, d FROM (
                SELECT *, row_number() OVER (PARTITION BY tseg, tier
                           ORDER BY hash(addr || d || '{seed}'), addr, d) rn
                FROM cells) WHERE rn <= {per_cell}
            ORDER BY tseg, tier""").fetchall()

        def day_end_balance(addr, day):
            row = con.execute(
                "SELECT COALESCE(SUM(delta), 0)::VARCHAR FROM daily WHERE addr=? AND d<=?",
                [addr, day]).fetchone()
            return int(row[0])

        def block_of(day, kind, addr):
            row = con.execute(
                "SELECT day_end_block FROM dayblk WHERE d=?", [day]).fetchone()
            if row is None:
                raise ValueError(
                    "day_end_block missing for "
                    f"kind={kind!r} addr={addr!r} day={day!r}")
            return int(row[0])

        def final_pct(addr):
            row = con.execute("SELECT bal::VARCHAR FROM bal WHERE addr=?", [addr]).fetchone()
            return pct(row[0]) if row else None

        def point(addr, day, kind, note=""):
            raw = day_end_balance(addr, day)
            return {"kind": kind, "addr": addr, "day": day,
                    "balance_block_source": "day_end_block",
                    "day_end_block": block_of(day, kind, addr),
                    "expected_balance_raw": str(raw),
                    "expected_balance_human": human(raw), "expected_pct": pct(raw),
                    "final_pct": final_pct(addr), "note": note,
                    "check_urls": urls(chain, token, addr=addr)}

        matrix = [point(addr, day, f"矩阵[{segment}·{tier}]",
                        note=f"{segment}期活跃、最终余额属{tier}档；核对该日终持仓")
                  for segment, tier, addr, day in picked]

        _progress(progress, "[3/5] 强制覆盖点：最大单笔 / 最大单日净变动…")
        forced = []
        row = con.execute(f"""SELECT tx, frm, t2, v::VARCHAR, b, d FROM ({events})
                              ORDER BY v DESC, b, tx, frm, t2 LIMIT 1""").fetchone()
        if row:
            tx, sender, receiver, value, block, day = row
            forced.append({"kind": "全史最大单笔转账", "tx": tx,
                           "from": sender, "to": receiver, "day": day,
                           "block": int(block), "expected_value_raw": value,
                           "expected_value_human": human(value), "expected_pct": pct(value),
                           "note": "浏览器打开 tx 核对金额与双方地址",
                           "check_urls": urls(chain, token, tx=tx)})
        row = con.execute(f"""SELECT addr, d, delta::VARCHAR FROM daily
                              WHERE addr NOT IN ('{Z}', '{DEAD}')
                              ORDER BY abs(delta) DESC, addr, d LIMIT 1""").fetchone()
        if row:
            addr, day, delta = row
            selected = point(
                addr, day, "最大单日净变动地址-日",
                note=f"该日净变动 {human(delta)}（{pct(delta)}% 供应）；核对当日流水与日终余额")
            selected["day_delta_human"] = human(delta)
            forced.append(selected)

        _progress(progress, "[4/5] 强制覆盖点：交界块附近 / 门槛±10% 边缘地址…")
        bounds = list(boundary_blocks)
        for boundary in bounds:
            for side, condition, order in (
                    ("前", f"b <= {boundary}", "DESC"),
                    ("后", f"b > {boundary}", "ASC")):
                row = con.execute(f"""SELECT tx, frm, t2, v::VARCHAR, b, d FROM ({events})
                                      WHERE {condition}
                                      ORDER BY b {order}, tx, frm, t2 LIMIT 1""").fetchone()
                if row:
                    tx, sender, receiver, value, block, day = row
                    forced.append({
                        "kind": f"交界块 {boundary} {side}最近转账", "tx": tx,
                        "from": sender, "to": receiver, "block": int(block), "day": day,
                        "expected_value_raw": value, "expected_value_human": human(value),
                        "note": "数据源交界完备性：核对该 tx 存在且交界两侧无缺段",
                        "check_urls": urls(chain, token, tx=tx),
                    })
        edges = con.execute(f"""
            SELECT addr, bal::VARCHAR FROM bal
            WHERE bal BETWEEN {int(threshold_raw * 0.9)} AND {int(threshold_raw * 1.1)}
              AND addr NOT IN ('{Z}', '{DEAD}')
            ORDER BY hash(addr || '{seed}'), addr LIMIT {edge_max}""").fetchall()
        for addr, balance in edges:
            forced.append({
                "kind": LEGACY_FINAL_BLOCK_EDGE_KIND, "addr": addr, "day": d1,
                "balance_block_source": "final_block",
                "expected_balance_raw": balance,
                "expected_balance_human": human(balance), "expected_pct": pct(balance),
                "note": f"最终余额贴 {threshold_pct}% 门槛（±10%）——错一笔就跨档，重点核对",
                "check_urls": urls(chain, token, addr=addr),
            })

        stats = {row[0] + "·" + row[1]: row[2] for row in con.execute(
            "SELECT tseg, tier, COUNT(*) FROM cells GROUP BY tseg, tier").fetchall()}
        return {
            "date_range": [d0, d1], "time_cuts": [cut1, cut2],
            "cell_population": stats, "boundary_blocks": bounds,
            "matrix_points": matrix, "forced_points": forced,
        }
    finally:
        con.close()
