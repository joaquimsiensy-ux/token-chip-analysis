#!/usr/bin/env python3
"""DefiLlama 免费价格通道——老币历史价格主兜底（B11，2026-07-22 实测入库）。

痛点定位：CoinGecko 免费层 days=max 已死（限 365 天），2021 前老币早期价格此前只有
Poloniex candles（仅覆盖其上所币）与链上池储备重建两条路。DefiLlama 免 key、直连、
限速宽，按 {链}:{合约地址} 直查，实测 CAKE 2021-01-01 价格直接命中。

用法:
  # 日线全史序列（分段拉 chart 端点，单段上限 500 点）
  python3 llama_price.py series <chain> <addr> --start 2021-01-01 [--end 2026-07-22] --out prices.json
  # 单时点/当前价（可多币批量，逗号分隔 chain:addr）
  python3 llama_price.py spot bsc:0x...,ethereum:0x...  [--ts 1609459200]

chain ∈ ethereum/bsc/base/arbitrum/polygon/solana（DefiLlama 命名，注意是 ethereum 不是 eth；
本脚本容错 eth→ethereum）。Solana 用 solana:<mint>。

series 输出与 CoinGecko market_chart 同构（下游画图零改动）:
  {"source": "defillama", "coin": "...", "symbol": "...", "confidence": ...,
   "prices": [[ts_ms, price], ...]}
注意:
  - DefiLlama 的价是聚合价（DEX+CEX 混合，confidence 字段给可信度）；发射窗口精确配价
    仍以链上主池 swap 重建为准，本通道定位=日线粒度的图 1 右轴与建仓成本区间估算
  - 币未被 DefiLlama 收录时返回空 coins——脚本明确报"未收录"退出码 3，别拿空当零价
（来源：B11 DefiLlama 接入实测，2026-07-22：三端点直连通、chart 单段上限 500 点）"""
import argparse
import datetime
import json
import os
import sys
import time

import requests

BASE = "https://coins.llama.fi"
CHAIN_ALIAS = {"eth": "ethereum"}
KNOWN = {"ethereum", "bsc", "base", "arbitrum", "polygon", "solana"}


def to_ts(s):
    if s.isdigit():
        return int(s)
    return int(datetime.datetime.strptime(s, "%Y-%m-%d")
               .replace(tzinfo=datetime.timezone.utc).timestamp())


def get(url, tries=5):
    for i in range(tries):
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 429:
                time.sleep(3 * (i + 1))
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            print(f"[warn] 重试: {str(e)[:80]}", file=sys.stderr, flush=True)
            time.sleep(2 * (i + 1))
    sys.exit("[fatal] DefiLlama 请求重试耗尽")


def cmd_series(a):
    chain = CHAIN_ALIAS.get(a.chain, a.chain)
    if chain not in KNOWN:
        sys.exit(f"[fatal] 不认识的链 {a.chain}（支持 {sorted(KNOWN)}，robinhood 等小众链未收录）")
    coin = f"{chain}:{a.addr}"
    start = to_ts(a.start)
    end = to_ts(a.end) if a.end else int(time.time())
    day = 86400
    pts, sym, conf = {}, None, None
    cur = start
    while cur < end + day:
        span = min(500, (end - cur) // day + 2)
        j = get(f"{BASE}/chart/{coin}?start={cur}&span={span}&period=1d")
        c = (j.get("coins") or {}).get(coin)
        if not c:
            if not pts:
                print(f"[fatal] DefiLlama 未收录 {coin}（空 coins）——换 CoinGecko/Poloniex/链上重建",
                      file=sys.stderr)
                sys.exit(3)
            break
        sym = c.get("symbol") or sym
        conf = c.get("confidence", conf)
        got = c.get("prices") or []
        for p in got:
            pts[int(p["timestamp"])] = float(p["price"])
        if not got:
            break
        last = max(int(p["timestamp"]) for p in got)
        nxt = last + day
        if nxt <= cur:  # 无进展防死循环
            break
        cur = nxt
        time.sleep(0.3)
    if not pts:
        sys.exit(3)
    series = sorted(pts.items())
    out = {"source": "defillama", "coin": coin, "symbol": sym, "confidence": conf,
           "prices": [[t * 1000, v] for t, v in series]}
    if a.out:
        tmp = a.out + ".tmp"
        with open(tmp, "w") as f:
            json.dump(out, f)
        os.replace(tmp, a.out)
        d0 = datetime.datetime.fromtimestamp(series[0][0], datetime.timezone.utc).date()
        d1 = datetime.datetime.fromtimestamp(series[-1][0], datetime.timezone.utc).date()
        print(f"[done] {sym or coin} {len(series)} 个日线点 [{d0} → {d1}] -> {a.out}")
    else:
        print(json.dumps(out))


def cmd_spot(a):
    coins = []
    for c in a.coins.split(","):
        c = c.strip()
        if ":" not in c:
            sys.exit(f"[fatal] spot 参数须为 chain:addr 形式: {c}")
        ch, addr = c.split(":", 1)
        coins.append(f"{CHAIN_ALIAS.get(ch, ch)}:{addr}")
    path = (f"prices/historical/{a.ts}/" if a.ts else "prices/current/") + ",".join(coins)
    j = get(f"{BASE}/{path}")
    got = j.get("coins") or {}
    for c in coins:
        r = got.get(c)
        if r:
            print(f"{c}\t{r.get('symbol')}\t{r.get('price')}\tts={r.get('timestamp')}")
        else:
            print(f"{c}\t未收录", file=sys.stderr)
    if len(got) < len(coins):
        sys.exit(3)


def main():
    ap = argparse.ArgumentParser(description="DefiLlama 免费价格通道")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s1 = sub.add_parser("series", help="日线全史序列（CoinGecko market_chart 同构输出）")
    s1.add_argument("chain")
    s1.add_argument("addr")
    s1.add_argument("--start", required=True, help="YYYY-MM-DD 或 unix 秒")
    s1.add_argument("--end", default=None)
    s1.add_argument("--out", default=None)
    s2 = sub.add_parser("spot", help="单时点/当前价批量")
    s2.add_argument("coins", help="chain:addr[,chain:addr...]")
    s2.add_argument("--ts", type=int, default=None, help="unix 秒（缺省=当前价）")
    a = ap.parse_args()
    if a.cmd == "series":
        cmd_series(a)
    else:
        cmd_spot(a)


if __name__ == "__main__":
    main()
