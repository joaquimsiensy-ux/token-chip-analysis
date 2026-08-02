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
      + snapshot_series.input_manifest.json（配置与逐档输入哈希）
      + stdout 摘要（列由 config.summary_cols 驱动；近90天斜率实体由 config.summary_fund 指定）
"""
import glob, hashlib, json, os, sys
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
        return json.load(f), os.path.realpath(path)

CFG, CONFIG_PATH = _load_config()
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = CFG.get("data_dir") or os.path.join(BASE, "data")
OUT = CFG.get("out_dir") or os.path.join(BASE, "analysis", "out")
os.makedirs(OUT, exist_ok=True)

SYMBOL = CFG.get("token_symbol", "")
if not isinstance(CFG.get("watch"), dict) or not CFG["watch"]:
    sys.exit("config.watch 必须是非空对象")
WATCH = {k: v.lower() for k, v in CFG["watch"].items()}
SUMMARY_FUND = CFG.get("summary_fund") or next(iter(WATCH))
SUMMARY_COLS = CFG.get("summary_cols") or {}
MAX_SNAPSHOTS = CFG.get("max_snapshots", 10_000)
MAX_HOLDERS = CFG.get("max_holders_per_snapshot", 5_000)
MAX_SNAPSHOT_BYTES = CFG.get("max_snapshot_bytes", 64 * 1024 * 1024)
for name, value in (("max_snapshots", MAX_SNAPSHOTS),
                    ("max_holders_per_snapshot", MAX_HOLDERS),
                    ("max_snapshot_bytes", MAX_SNAPSHOT_BYTES)):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        sys.exit(f"config.{name} 必须是正整数")

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


rows = []
used_inputs = []
paths = sorted(glob.glob(os.path.join(DATA, "snapshots", "top1000_*.json")))
if not paths:
    sys.exit(f"未找到快照：{os.path.join(DATA, 'snapshots', 'top1000_*.json')}")
if len(paths) > MAX_SNAPSHOTS:
    sys.exit(f"小样本上限：快照 {len(paths)} > {MAX_SNAPSHOTS}")
for path in paths:
    if os.path.getsize(path) > MAX_SNAPSHOT_BYTES:
        sys.exit(f"小样本上限：快照文件过大 {path}")
    ts = int(os.path.basename(path).split("_")[1].split(".")[0])
    snap = json.load(open(path))
    used_inputs.append(path)
    if not snap.get("holders"):  # 中段空档 → 用 top100 补采文件
        alt = os.path.join(DATA, "snapshots", f"top100_{ts}.json")
        if os.path.exists(alt):
            if os.path.getsize(alt) > MAX_SNAPSHOT_BYTES:
                sys.exit(f"小样本上限：补采快照文件过大 {alt}")
            snap = json.load(open(alt))
            used_inputs.append(alt)
    if not isinstance(snap.get("holders"), dict) or not snap["holders"]:
        sys.exit(f"快照 holders 为空且无有效补采文件：{path}")
    if len(snap["holders"]) > MAX_HOLDERS:
        sys.exit(f"小样本上限：{path} holders {len(snap['holders'])} > {MAX_HOLDERS}")
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

result_path = os.path.join(OUT, "snapshot_series.json")
with open(result_path, "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False)
    f.write("\n")
manifest = {
    "schema": "hyperliquid-snapshot-series-inputs/v1",
    "small_sample_only": True,
    "limits": {"max_snapshots": MAX_SNAPSHOTS, "max_holders_per_snapshot": MAX_HOLDERS,
               "max_snapshot_bytes": MAX_SNAPSHOT_BYTES},
    "config": {"path": CONFIG_PATH, "sha256": sha256_file(CONFIG_PATH)},
    "inputs": [{"path": os.path.realpath(p), "sha256": sha256_file(p)}
               for p in used_inputs],
    "output": {"path": os.path.realpath(result_path), "sha256": sha256_file(result_path),
               "rows": len(rows)},
}
with open(os.path.join(OUT, "snapshot_series.input_manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2, sort_keys=True)
    f.write("\n")

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
