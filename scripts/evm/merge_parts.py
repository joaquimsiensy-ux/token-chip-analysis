#!/usr/bin/env python3
"""把 fetch_hypersync_par 的多段 part_XX.csv 合并转换成 replay_pass1 期望的 7 列格式。
来源：AKE(BSC) 分析会话实战产物，2026-07-19（v3.7 收编）；920 万行 48 段合并零重复实测。
part 列：block,ts,tx,log_index,from,to,value_raw
输出列：block,ts,tx,from,to,value,uniqueId（uniqueId=hs:{tx}:{log_index}）
段互斥由 plan.json 保证，仍按 (tx,log_index) 全局去重兜底；统计丢弃行数=重复键数（dropped-audit）。
"""
import csv, glob, json, os, sys

OUTDIR = "data/bsc"
OUT = "data/transfers_full.csv"

parts = sorted(glob.glob(os.path.join(OUTDIR, "part_*.csv")))
if not parts:
    sys.exit("no part files")
seen = set()
n_in = n_out = n_dup = n_bad = 0
rows = []
for p in parts:
    with open(p) as f:
        r = csv.reader(f)
        next(r, None)
        for row in r:
            if len(row) != 7:
                n_bad += 1
                continue
            blk, ts, tx, li, frm, to, val = row
            n_in += 1
            key = (tx, int(li))
            if key in seen:
                n_dup += 1
                continue
            seen.add(key)
            rows.append((int(blk), int(li), ts, tx, frm, to, val))
rows.sort(key=lambda x: (x[0], x[1]))
with open(OUT, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["block", "ts", "tx", "from", "to", "value", "uniqueId"])
    for blk, li, ts, tx, frm, to, val in rows:
        w.writerow([blk, ts, tx, frm, to, val, f"hs:{tx}:{li}"])
n_out = len(rows)
stats = {"files": len(parts), "rows_in": n_in, "rows_out": n_out, "dup_dropped": n_dup, "bad": n_bad,
         "first_block": rows[0][0], "last_block": rows[-1][0]}
json.dump(stats, open(os.path.join("data", "merge_stats.json"), "w"), indent=1)
print(json.dumps(stats, indent=1))
