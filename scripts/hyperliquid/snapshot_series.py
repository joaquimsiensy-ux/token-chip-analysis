#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 top-1000 历史快照序列提取：关键实体现货持仓曲线、集中度时序、持有人数时序。
来源：HYPE(Hyperliquid) 分析会话实战产物, 2026-07（标的常量已外置，HYPE 原值见 config.example.json，
参数化已用原值对 HYPE 实战输出对拍验证，数值一致）。

用法: python3 snapshot_series.py [--config <path>]
  配置读取顺序：--config 指定路径 > 脚本同目录 config.json；缺失则报错退出。
输入: <data_dir>/snapshots/top1000_*.json（collect.py snapshots 子命令产物；
      某档 holders 为空时自动用同时间戳 top100_<ts>.json 补采文件替代）
输出: <out_dir>/snapshot_series.json（字段 = ts/date/holdersCount/top10/top50/top100/top1000 + watch 各键）
      + stdout 摘要（列由 config.summary_cols 驱动；近90天斜率实体由 config.summary_fund 指定）
"""
import json, os, sys, glob
from datetime import datetime, timezone

def _load_config():
    """--config <path> 优先，否则脚本同目录 config.json；缺失即退出（不设默认标的）。"""
    if "--config" in sys.argv:
        i = sys.argv.index("--config")
        if i + 1 >= len(sys.argv):
            sys.exit("--config 后须跟配置文件路径")
        path = sys.argv[i + 1]
        del sys.argv[i:i + 2]
    else:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if not os.path.exists(path):
        sys.exit(f"缺配置 {path}：复制 config.example.json 为 config.json 按标的填写，或用 --config 指定")
    with open(path) as f:
        return json.load(f)

CFG = _load_config()
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = CFG.get("data_dir") or os.path.join(BASE, "data")
OUT = CFG.get("out_dir") or os.path.join(BASE, "analysis", "out")
os.makedirs(OUT, exist_ok=True)

SYMBOL = CFG.get("token_symbol", "")
WATCH = {k: v.lower() for k, v in CFG["watch"].items()}
SUMMARY_FUND = CFG.get("summary_fund") or next(iter(WATCH))
SUMMARY_COLS = CFG.get("summary_cols") or {}

rows = []
for path in sorted(glob.glob(os.path.join(DATA, "snapshots", "top1000_*.json"))):
    ts = int(os.path.basename(path).split("_")[1].split(".")[0])
    snap = json.load(open(path))
    if not snap.get("holders"):  # 中段空档 → 用 top100 补采文件
        alt = os.path.join(DATA, "snapshots", f"top100_{ts}.json")
        if os.path.exists(alt):
            snap = json.load(open(alt))
    holders = {k.lower(): float(v) for k, v in snap.get("holders", {}).items()}
    vals = sorted(holders.values(), reverse=True)
    row = {
        "ts": ts,
        "date": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"),
        "holdersCount": snap.get("holdersCount"),
        "top10": sum(vals[:10]),
        "top50": sum(vals[:50]),
        "top100": sum(vals[:100]),
        "top1000": sum(vals),
    }
    for name, addr in WATCH.items():
        row[name] = holders.get(addr, 0.0)
    rows.append(row)

json.dump(rows, open(os.path.join(OUT, "snapshot_series.json"), "w"))

# 摘要打印（列由 config.summary_cols 驱动，仅影响 stdout，不影响输出 JSON）
first, last = rows[0], rows[-1]
mid = rows[len(rows)//2]
print(f"档数: {len(rows)}  区间: {first['date']} ~ {last['date']}")
hdr = f"{'日期':<12}" + "".join(f"{label:>12}" for label in SUMMARY_COLS)
print(hdr + f"{'top10(M)':>10}{'持有人数':>10}")
for r in [rows[0], rows[len(rows)//4], mid, rows[3*len(rows)//4], rows[-1]]:
    line = f"{r['date']:<12}" + "".join(f"{r[key]/1e6:>12.2f}" for key in SUMMARY_COLS.values())
    print(line + f"{r['top10']/1e6:>10.1f}{r['holdersCount'] or 0:>10}")

# summary_fund 实体近90天斜率（HYPE 场景=援助基金回购速度）
recent = [r for r in rows if r["ts"] >= last["ts"] - 90*86400]
if len(recent) >= 2:
    d_amt = recent[-1][SUMMARY_FUND] - recent[0][SUMMARY_FUND]
    d_days = (recent[-1]["ts"] - recent[0]["ts"]) / 86400
    print(f"\n{SUMMARY_FUND} 近90天: {recent[0][SUMMARY_FUND]/1e6:.2f}M -> {recent[-1][SUMMARY_FUND]/1e6:.2f}M"
          f"  日均净变化 {d_amt/d_days:,.0f} {SYMBOL}/天")
prev_year = [r for r in rows if r["ts"] <= last["ts"] - 90*86400]
if len(prev_year) >= 2:
    d2 = prev_year[-1][SUMMARY_FUND] - prev_year[0][SUMMARY_FUND]
    dd2 = (prev_year[-1]["ts"] - prev_year[0]["ts"]) / 86400
    print(f"{SUMMARY_FUND} 90天前的历史区间: 日均净变化 {d2/dd2:,.0f} {SYMBOL}/天")
