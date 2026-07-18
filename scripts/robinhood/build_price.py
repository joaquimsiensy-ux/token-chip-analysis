#!/usr/bin/env python3
"""重建标的全历史 USD 价格序列（Robinhood 链，主池 V3 swap sqrtPriceX96 路线）。
来源：CASHCAT(Robinhood) 分析实战 2026-07-13，v1.5 参数化收编（主池从 config.json pool 读）。
前置：data/swaps.jsonl.gz(pull_swaps.py) + data/ethusdt_1h.json(binance.vision) + data/ohlcv_minute.json(pull_ohlcv.py)。
主池 V3 swap sqrtPriceX96 → WETH/CASHCAT → × ETHUSD(小时K) = USD 价格。
与 GT 分钟K/小时K重叠段交叉验证（中位偏差应 <2%）。
输出 data/price_series.json:
  {"minute": [[ts, usd], ...], "hour": [[ts, usd], ...], "xcheck": {...}}
"""
import json, gzip, bisect

import json as _j
_cfg = _j.load(open("config.json"))
MAIN_POOL = _cfg["pool"].lower()
# 方向自动判定（NOXA(Robinhood) 分析 2026-07-15 修复：出生标的恰好 quote=token1，写死导致
# token>quote 的标的价格恒为倒数、GT 交叉验证偏差 10^13 倍量级）：V3 token0=地址小的一方，
# (sqrtp/Q96)^2 = token1/token0；标的为 token1 时取倒数得 quote per token。
_TOKEN = (_cfg.get("token") or "").lower()
_QUOTE = (_cfg.get("quote_token") or "0x0bd7d308f8e1639fab988df18a8011f41eacad73").lower()
TOKEN_IS_T1 = _TOKEN > _QUOTE
Q96 = 2 ** 96

eth = json.load(open("data/ethusdt_1h.json"))  # [[ts, close], ...] 升序
ETS = [r[0] for r in eth]


def ethusd(ts):
    # K线 key 为币安原生毫秒时把秒级 ts 对齐（NOXA 分析 2026-07-15 修复：不适配会恒取首根）
    t = ts * 1000 if ETS and ETS[0] > 10 ** 12 else ts
    i = bisect.bisect_right(ETS, t) - 1
    i = max(0, min(i, len(eth) - 1))
    return eth[i][1]


def main():
    # 每分钟取主池最后一笔 swap 的 sqrtp
    minute_last = {}
    n = 0
    with gzip.open("data/swaps.jsonl.gz", "rt") as f:
        for line in f:
            r = json.loads(line)
            if r["pool"] != MAIN_POOL:
                continue
            n += 1
            m = r["ts"] - r["ts"] % 60
            key = (r["block"], r.get("logi") or 0)
            if m not in minute_last or key >= minute_last[m][0]:
                minute_last[m] = (key, int(r["sqrtp"]), r["ts"])
    print(f"主池 swap {n} 笔, 覆盖 {len(minute_last)} 分钟")

    minute = []
    for m in sorted(minute_last):
        _, sqrtp, ts = minute_last[m]
        ratio = (sqrtp / Q96) ** 2      # token1/token0
        weth_per = (1.0 / ratio) if TOKEN_IS_T1 else ratio   # quote per token
        usd = weth_per * ethusd(ts)
        minute.append([m, usd])
    # 小时序列 = 每小时最后一分钟
    hour_last = {}
    for m, usd in minute:
        h = m - m % 3600
        hour_last[h] = usd
    hour = [[h, hour_last[h]] for h in sorted(hour_last)]

    # 与 GT 分钟K交叉验证（重叠段）
    gt_min = json.load(open("data/ohlcv_minute.json"))
    gt_map = {}
    for row in gt_min["rows"]:
        # GT ohlcv row: [ts, o, h, l, c, vol]
        gt_map[row[0] - row[0] % 60] = row[4]
    mine = dict(minute)
    diffs = []
    for m, c in gt_map.items():
        if m in mine and c:
            diffs.append(abs(mine[m] - c) / c)
    diffs.sort()
    xc = {"n_overlap": len(diffs),
          "median_rel_diff": diffs[len(diffs)//2] if diffs else None,
          "p90_rel_diff": diffs[int(len(diffs)*0.9)] if diffs else None}
    print("GT 交叉验证:", xc)

    with open("data/price_series.json", "w") as f:
        json.dump({"minute": minute, "hour": hour, "xcheck": xc}, f)
    print(f"输出 minute={len(minute)} hour={len(hour)}")


if __name__ == "__main__":
    main()
