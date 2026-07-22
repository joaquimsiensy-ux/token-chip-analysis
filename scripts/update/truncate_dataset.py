#!/usr/bin/env python3
"""A10 时间封存截断器——把案 data 目录的转账主数据按时间截断出副本，供封存重跑。

用途背景：季度质量抽检的"时间封存测试"——只给前 70-80% 历史重跑聚类判级，封存
尾段验证实体是否延续协同，检验方法有没有"后见拟合"（靠后期数据倒推早期结论）。
本脚本产出截断副本 + manifest；重跑分析一律指向副本目录，原始数据绝不动。

处理三态转账主数据（其余中间产物一概不复制——封存重跑本来就该从主数据重放）：
  1. EVM v1 CSV：data-dir 直下 transfers*.csv（ts ISO / timestamp unix 两代表头自适应）
  2. EVM v2：data-dir/v2/run_*/{logs,blocks}.parquet（cutoff_ts→由 blocks 定 cutoff_block
     再过滤，目录结构保真输出，下游 replay 零适配）
  3. Solana：data-dir 直下 soltx-*.jsonl.gz（行=[ts,slot,from,to,value]，流式 gzip 逐行）

安全约束：--out-dir 不许落在 --data-dir 内（realpath 校验硬退）；对 data-dir 只读。
大文件走 DuckDB COPY / 流式 gzip，防内存。

用法:
  python3 truncate_dataset.py --data-dir 案/data --out-dir /tmp/holdout_data \
      (--ratio 0.7 | --cutoff-ts 1750000000|2026-06-01) [--mem-limit 6GB]
（来源：A10 小工程件，2026-07-22）"""
import argparse
import datetime
import glob
import gzip
import json
import os
import sys

import duckdb


def to_ts(s):
    if s.replace(".", "").isdigit():
        return int(float(s))
    return int(datetime.datetime.strptime(s[:10], "%Y-%m-%d")
               .replace(tzinfo=datetime.timezone.utc).timestamp())


def csv_time_expr(con, path):
    """CSV 时间列自适应 → (可比 unix 秒表达式, 说明)。"""
    cols = {r[0].lower() for r in con.execute(
        f"DESCRIBE SELECT * FROM read_csv('{path}', header=true, all_varchar=true)").fetchall()}
    if "ts" in cols:  # ISO（'2025-10-07T22:33:09.000Z' / 无 Z 两代并存）
        return ("epoch(strptime(substr(\"ts\", 1, 19), '%Y-%m-%dT%H:%M:%S'))", "ts(ISO)")
    if "timestamp" in cols:
        return ('TRY_CAST("timestamp" AS BIGINT)', "timestamp(unix)")
    sys.exit(f"[fatal] {path} 认不出时间列（ts/timestamp）：{sorted(cols)}")


def main():
    ap = argparse.ArgumentParser(description="A10 时间封存截断器（EVM v1/v2 + Solana soltx）")
    ap.add_argument("--data-dir", required=True, help="案 data 目录（只读源）")
    ap.add_argument("--out-dir", required=True, help="截断副本输出目录（不许在 data-dir 内）")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--ratio", type=float, help="按时间跨度截前段比例（如 0.7）")
    g.add_argument("--cutoff-ts", help="显式截断点（unix 秒或 YYYY-MM-DD，含端点）")
    ap.add_argument("--mem-limit", default="6GB")
    a = ap.parse_args()

    src = os.path.realpath(a.data_dir)
    dst = os.path.realpath(a.out_dir)
    if not os.path.isdir(src):
        sys.exit(f"[fatal] data 目录不存在: {src}")
    if dst == src or dst.startswith(src + os.sep):
        sys.exit("[fatal] out-dir 落在 data-dir 内——绝不写原始数据目录，换个输出位置")
    if a.ratio is not None and not (0 < a.ratio < 1):
        sys.exit("[fatal] --ratio 必须在 (0,1) 之间")
    os.makedirs(dst, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET memory_limit='{a.mem_limit}';")

    # ── 盘点三态数据源 ────────────────────────────────────────────
    csvs = sorted(glob.glob(os.path.join(src, "transfers*.csv")))
    v2dir = os.path.join(src, "v2")
    v2runs = sorted(glob.glob(os.path.join(v2dir, "run_*"))) if os.path.isdir(v2dir) else []
    v2runs = [r for r in v2runs if os.path.exists(os.path.join(r, "logs.parquet"))]
    solgz = sorted(glob.glob(os.path.join(src, "soltx-*.jsonl.gz")))
    if not (csvs or v2runs or solgz):
        sys.exit(f"[fatal] {src} 下没有 transfers*.csv / v2/run_* / soltx-*.jsonl.gz 任何一态")
    print(f"[scan] v1csv={len(csvs)} v2run={len(v2runs)} soltx={len(solgz)}", flush=True)

    # ── 定截断点：显式给定，或 ratio × 全局时间跨度 ─────────────────
    spans = []
    csv_exprs = {p: csv_time_expr(con, p) for p in csvs}
    for p in csvs:
        e, _ = csv_exprs[p]
        spans.append(con.execute(
            f"SELECT MIN({e}), MAX({e}) FROM read_csv('{p}', header=true, "
            f"all_varchar=true, ignore_errors=true)").fetchone())
    if v2runs:
        blocks = os.path.join(v2dir, "run_*", "blocks.parquet")
        spans.append(con.execute(
            f"SELECT MIN(TRY_CAST(timestamp AS UBIGINT)), MAX(TRY_CAST(timestamp AS UBIGINT)) "
            f"FROM read_parquet('{blocks}', union_by_name=true)").fetchone())
    for p in solgz:  # 流式扫 ts（首元素；首行 sanity）
        lo = hi = None
        with gzip.open(p, "rt") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                ts = json.loads(line)[0]
                if lo is None:
                    if not (10 ** 9 < ts < 2 * 10 ** 9):
                        sys.exit(f"[fatal] {p} 首行 [0]={ts} 不像 unix 秒——行格式非 [ts,...]，先人工核")
                    lo = hi = ts
                else:
                    lo, hi = min(lo, ts), max(hi, ts)
        spans.append((lo, hi))
    lo = min(int(s[0]) for s in spans if s[0] is not None)
    hi = max(int(s[1]) for s in spans if s[1] is not None)
    cutoff = to_ts(a.cutoff_ts) if a.cutoff_ts else int(lo + a.ratio * (hi - lo))
    if not (lo <= cutoff <= hi):
        print(f"[warn] 截断点 {cutoff} 在数据范围 [{lo},{hi}] 之外——产物可能为空/全量", file=sys.stderr)
    print(f"[cutoff] 全局范围 [{lo},{hi}] → 截断点 {cutoff} "
          f"({datetime.datetime.fromtimestamp(cutoff, datetime.timezone.utc):%Y-%m-%d %H:%M:%S}Z)",
          flush=True)

    manifest = {"generated_at": datetime.datetime.now(datetime.timezone.utc)
                    .strftime("%Y-%m-%dT%H:%M:%SZ"),
                "data_dir": src, "out_dir": dst, "ratio": a.ratio,
                "cutoff_ts": cutoff, "global_span": [lo, hi], "files": []}

    def log_file(src_p, out_p, before, after, extra=None):
        rec = {"src": src_p, "out": out_p, "rows_before": before, "rows_after": after}
        if extra:
            rec.update(extra)
        manifest["files"].append(rec)
        print(f"  {os.path.basename(out_p) or out_p}: {before} → {after} 行", flush=True)

    # ── v1 CSV ───────────────────────────────────────────────────
    for p in csvs:
        e, kind = csv_exprs[p]
        out_p = os.path.join(dst, os.path.basename(p))
        rd = f"read_csv('{p}', header=true, all_varchar=true, ignore_errors=true)"
        before = con.execute(f"SELECT COUNT(*) FROM {rd}").fetchone()[0]
        con.execute(f"COPY (SELECT * FROM {rd} WHERE {e} <= {cutoff}) TO '{out_p}' "
                    f"(HEADER, DELIMITER ',')")
        after = con.execute(f"SELECT COUNT(*) FROM read_csv('{out_p}', header=true, "
                            f"all_varchar=true)").fetchone()[0]
        log_file(p, out_p, before, after, {"time_col": kind})

    # ── v2 parquet（每 run 保结构；先由该 run 的 blocks 定 cutoff_block）──
    for run in v2runs:
        name = os.path.basename(run)
        bsrc = os.path.join(run, "blocks.parquet")
        lsrc = os.path.join(run, "logs.parquet")
        r = con.execute(f"SELECT MAX(number) FROM read_parquet('{bsrc}') "
                        f"WHERE TRY_CAST(timestamp AS UBIGINT) <= {cutoff}").fetchone()
        cb = r[0]
        if cb is None:  # 整个 run 在截断点之后 → 不输出
            n = con.execute(f"SELECT COUNT(*) FROM read_parquet('{lsrc}')").fetchone()[0]
            log_file(lsrc, "(整段晚于截断点，弃)", n, 0, {"cutoff_block": None})
            continue
        outrun = os.path.join(dst, "v2", name)
        os.makedirs(outrun, exist_ok=True)
        for fn, key in (("logs.parquet", "block_number"), ("blocks.parquet", "number")):
            sp, op = os.path.join(run, fn), os.path.join(outrun, fn)
            before = con.execute(f"SELECT COUNT(*) FROM read_parquet('{sp}')").fetchone()[0]
            con.execute(f"COPY (SELECT * FROM read_parquet('{sp}') WHERE {key} <= {cb}) "
                        f"TO '{op}' (FORMAT parquet)")
            after = con.execute(f"SELECT COUNT(*) FROM read_parquet('{op}')").fetchone()[0]
            log_file(sp, op, before, after, {"cutoff_block": int(cb)})

    # ── Solana soltx jsonl.gz（流式）──────────────────────────────
    for p in solgz:
        out_p = os.path.join(dst, os.path.basename(p))
        before = after = 0
        with gzip.open(p, "rt") as fi, gzip.open(out_p, "wt") as fo:
            for line in fi:
                t = line.strip()
                if not t:
                    continue
                before += 1
                if json.loads(t)[0] <= cutoff:
                    fo.write(t + "\n")
                    after += 1
        log_file(p, out_p, before, after)

    mp = os.path.join(dst, "truncate_manifest.json")
    with open(mp, "w") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print(f"[done] 截断副本 {len(manifest['files'])} 项 -> {dst}（manifest: {mp}）")


if __name__ == "__main__":
    main()
