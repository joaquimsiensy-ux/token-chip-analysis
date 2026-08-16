#!/usr/bin/env python3
"""A9 价格双源抽查——报告用价格序列与独立第二源对照（首/中/尾 3 点日收盘）。

痛点定位：报告图 1 右轴价格此前单源直用（CG/CMC/GMGN/llama 任一），源本身取错币、
错链、错单位时无人拦截。本脚本抽 3 个日收盘点与独立第二源对照：
  偏差 >5% WARN、>15% FAIL（退出码 2）；第二源无该时段数据 → 如实标 skip（不算过
  也不算挂；3 点全 skip 退出码 3=对照不可得，人工换源）。偏差用对称口径
  |a-b|/((a+b)/2)，不偏袒任一源。

第二源自动选择：主源 ≠ defillama → DefiLlama historical（复用同目录 llama_price）；
主源 = defillama → binance.vision 现货日 K（须 --binance-symbol，如 CAKEUSDT）。
也可 --second 显式指定（defillama / binance）。

价格文件自适应（_load_series）：
  - price_series.json：[[ts_sec, price], ...]
  - CG market_chart / llama series：{"prices": [[ts_ms, price], ...]}
  - CSV：表头嗅探时间列（ts/timestamp/time/date）+ 价格列（price/close）
  时间戳 >1e12 自动判毫秒。

网络：DefiLlama 与 data-api.binance.vision 均实测直连通（api-keys.md 免注册通道节）；
个别网络环境不通时加 --proxy <proxy-url>，代理地址推荐统一放在 CHIP_PROXY。

用法:
  python3 price_check.py --price-file data/cg_price_365d.json --source coingecko \
      --chain bsc --addr 0x4fa7... [--second defillama|binance] \
      [--binance-symbol CAKEUSDT] [--points 3] [--proxy URL] [--out check.json]
（来源：A9 小工程件，2026-07-22；QUQ CG vs DefiLlama 实测通过）"""
import argparse
import csv
import datetime
import json
import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llama_price import CHAIN_ALIAS  # noqa: E402（复用链名容错表）

WARN_PCT, FAIL_PCT = 5.0, 15.0
BINANCE_KLINES = "https://data-api.binance.vision/api/v3/klines"
LLAMA_HIST = "https://coins.llama.fi/prices/historical"


def _load_series(path):
    """价格文件 → [(ts_sec, price)] 升序。格式自适应，认不出硬退。"""
    if path.endswith(".csv"):
        rows = list(csv.DictReader(open(path)))
        if not rows:
            sys.exit("[fatal] 价格 CSV 为空")
        cols = {c.lower(): c for c in rows[0]}
        tcol = next((cols[k] for k in ("ts", "timestamp", "time", "date") if k in cols), None)
        pcol = next((cols[k] for k in ("price", "close") if k in cols), None)
        if not tcol or not pcol:
            sys.exit(f"[fatal] CSV 认不出时间/价格列：{list(cols)}")
        out = []
        for r in rows:
            t, p = r[tcol], r[pcol]
            if "-" in t:  # 日期字符串
                ts = int(datetime.datetime.strptime(t[:10], "%Y-%m-%d")
                         .replace(tzinfo=datetime.timezone.utc).timestamp())
            else:
                ts = int(float(t))
            out.append((ts, float(p)))
    else:
        d = json.load(open(path))
        if isinstance(d, dict) and "prices" in d:
            out = [(int(t), float(p)) for t, p in d["prices"]]
        elif isinstance(d, list) and d and isinstance(d[0], (list, tuple)):
            out = [(int(t), float(p)) for t, p in d]
        else:
            sys.exit(f"[fatal] 价格 JSON 认不出结构（既非 [[ts,p]] 也非 {{'prices':...}}）")
    out = [(t // 1000 if t > 10 ** 12 else t, p) for t, p in out]
    return sorted(out)


def _daily_close(series):
    """[(ts,p)] → {日期: 当日最后一个点的价}（UTC 日收盘）。"""
    d = {}
    for ts, p in series:
        day = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).date().isoformat()
        d[day] = p  # 升序输入，后写覆盖=当日最后点
    return d


def _get(url, proxy, params=None, tries=4):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, timeout=30,
                             proxies={"http": proxy, "https": proxy} if proxy else None)
            if r.status_code == 429:
                time.sleep(3 * (i + 1))
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            print(f"[warn] 重试 {url.split('/')[2]}: {str(e)[:70]}", file=sys.stderr)
            time.sleep(2 * (i + 1))
    return None  # 网络耗尽 → 调用侧按 skip 处理（如实标注，不硬退）


def second_llama(day, chain, addr, proxy):
    """DefiLlama 当日收盘近似 = 当日 23:59:59 的 historical 价（4h 窗口内最近点）。"""
    ts = int(datetime.datetime.strptime(day, "%Y-%m-%d")
             .replace(tzinfo=datetime.timezone.utc).timestamp()) + 86399
    coin = f"{CHAIN_ALIAS.get(chain, chain)}:{addr}"
    j = _get(f"{LLAMA_HIST}/{ts}/{coin}", proxy, params={"searchWidth": "4h"})
    c = ((j or {}).get("coins") or {}).get(coin)
    return (float(c["price"]), f"defillama@{c.get('timestamp')}") if c else (None, "defillama 无该时点数据")


def second_binance(day, symbol, proxy):
    """binance.vision 现货日 K 收盘价（UTC 日）。"""
    t0 = int(datetime.datetime.strptime(day, "%Y-%m-%d")
             .replace(tzinfo=datetime.timezone.utc).timestamp()) * 1000
    j = _get(BINANCE_KLINES, proxy, params={"symbol": symbol, "interval": "1d",
                                            "startTime": t0, "endTime": t0 + 86400000 - 1,
                                            "limit": 1})
    if isinstance(j, list) and j:
        return float(j[0][4]), f"binance.vision {symbol} 1d close"
    return None, f"binance.vision 无 {symbol} 该日 K（未上现货或早于上所）"


def main():
    ap = argparse.ArgumentParser(description="A9 价格双源抽查（首/中/尾 3 点日收盘对照）")
    ap.add_argument("--price-file", required=True, help="报告用价格序列（json/csv 自适应）")
    ap.add_argument("--source", required=True,
                    help="主源名（coingecko/cmc/gmgn/defillama/binance/...，用于选第二源与留档）")
    ap.add_argument("--chain", default=None, help="链名（DefiLlama 对照必须）")
    ap.add_argument("--addr", default=None, help="合约地址（DefiLlama 对照必须）")
    ap.add_argument("--second", choices=["defillama", "binance"], default=None,
                    help="显式指定第二源（缺省自动：主源非 defillama → defillama，否则 binance）")
    ap.add_argument("--binance-symbol", default=None, help="币安现货交易对（如 CAKEUSDT）")
    ap.add_argument("--points", type=int, default=3, help="抽点数（默认 3=首/中/尾）")
    ap.add_argument("--proxy", default=None, help="代理 URL（两端点默认直连通；推荐取 CHIP_PROXY）")
    ap.add_argument("--out", default=None, help="结果 JSON 落盘路径（可选）")
    a = ap.parse_args()

    second = a.second or ("binance" if a.source.lower() in ("defillama", "llama") else "defillama")
    if second == "defillama" and not (a.chain and a.addr):
        sys.exit("[fatal] 第二源 defillama 需要 --chain 与 --addr")
    if second == "binance" and not a.binance_symbol:
        sys.exit("[fatal] 第二源 binance 需要 --binance-symbol（如 CAKEUSDT）；"
                 "未上币安现货的币请用 --second defillama")

    daily = _daily_close(_load_series(a.price_file))
    days = sorted(daily)
    if len(days) < 2:
        sys.exit(f"[fatal] 价格序列过短（{len(days)} 天），抽不成首/中/尾")
    n = min(a.points, len(days))
    if n >= len(days):
        picks = days
    else:  # 均匀取 n 点（n=3 即首/中/尾）
        idx = sorted({round(i * (len(days) - 1) / (n - 1)) for i in range(n)}) if n > 1 else [0]
        picks = [days[i] for i in idx]

    results, n_fail, n_warn, n_skip = [], 0, 0, 0
    for day in picks:
        p1 = daily[day]
        if second == "defillama":
            p2, src2 = second_llama(day, a.chain, a.addr, a.proxy)
        else:
            p2, src2 = second_binance(day, a.binance_symbol, a.proxy)
        if p2 is None or p2 <= 0 or p1 <= 0:
            status, dev = "SKIP", None
            n_skip += 1
        else:
            dev = round(abs(p1 - p2) / ((p1 + p2) / 2) * 100, 2)
            status = "FAIL" if dev > FAIL_PCT else ("WARN" if dev > WARN_PCT else "PASS")
            n_fail += status == "FAIL"
            n_warn += status == "WARN"
        results.append({"day": day, "main_price": p1, "second_price": p2,
                        "second_note": src2, "deviation_pct": dev, "status": status})
        print(f"  {day}  主源={p1:.8g}  第二源={p2 if p2 is None else format(p2, '.8g')}"
              f"  偏差={dev}%  [{status}]  ({src2})", flush=True)

    verdict = ("FAIL" if n_fail else
               "ALL_SKIP" if n_skip == len(picks) else
               "WARN" if n_warn else "PASS")
    out = {"generated_at": datetime.datetime.now(datetime.timezone.utc)
               .strftime("%Y-%m-%dT%H:%M:%SZ"),
           "price_file": os.path.abspath(a.price_file), "main_source": a.source,
           "second_source": second, "thresholds": {"warn_pct": WARN_PCT, "fail_pct": FAIL_PCT},
           "points": results, "verdict": verdict}
    if a.out:
        with open(a.out, "w") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"[{verdict}] {len(picks)} 点：FAIL={n_fail} WARN={n_warn} SKIP={n_skip}"
          + (f" -> {a.out}" if a.out else ""))
    if verdict == "FAIL":
        sys.exit(2)       # 偏差超 15%：价格源大概率取错，报告用价前必须人工裁决
    if verdict == "ALL_SKIP":
        sys.exit(3)       # 对照不可得：换第二源或人工核对，不许当 PASS 用


if __name__ == "__main__":
    main()
