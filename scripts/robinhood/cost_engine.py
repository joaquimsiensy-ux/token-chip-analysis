#!/usr/bin/env python3
"""建仓成本引擎：tx 级 swap 对价重建（本币 vs 报价币），输出每实体成本/已实现盈亏。
来源：Pointless(Robinhood) 分析 2026-07-13 收编参数化。
依赖: data/transfers.jsonl.gz, data/weth_pool.jsonl(pull_weth_pool.py 产出),
      data/quote_usd_hour.json([[ts,o,h,l,c],...] 报价币/USD 小时K,如 ETH/USDT),
      data/transit_contracts.json(原子中转设施名单)
config 读: pool, decimals, total_supply_tokens, 可选 fee_distributor(该地址→用户的转账算 fee 不算买入)
输出: data/swaps.json（tx级对价）、data/entity_pnl.json（地址级成本/卖出/已实现USD）
方法说明见 data-pipeline-robinhood.md（swap.to 归因 + 原子中转剔除 + 分钟级报价币换算）。
"""
import json, gzip, bisect, sys
from decimal import Decimal
from collections import defaultdict
from amounts import raw_to_units

cfg = json.load(open('config.json'))
dec = int(cfg.get('decimals') or 18)
quote_dec = int(cfg.get('quote_decimals') if cfg.get('quote_decimals') is not None else 18)
TOTAL = int(cfg.get('total_supply_tokens') or 0) * 10 ** dec
POOL = (cfg.get('pool') or '').lower()
V4PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
ZERO = "0x0000000000000000000000000000000000000000"
DEAD = "0x000000000000000000000000000000000000dead"
FEE_DIST = (cfg.get('fee_distributor') or '').lower()
transit = set(json.load(open('data/transit_contracts.json')))
MARKETS = {POOL, V4PM} | transit
MIN_SHARE = 0.003  # 只落盘买卖合计≥0.3%总供应的地址

qk = json.load(open('data/quote_usd_hour.json'))
q_ts = [r[0] for r in qk]
_TS_MS = q_ts and q_ts[0] > 10**12  # K线 key 为毫秒(币安原生)则把秒级 ts 对齐
def quote_usd(ts):
    t = ts * 1000 if _TS_MS else ts
    i = max(0, min(bisect.bisect_right(q_ts, t) - 1, len(qk) - 1))
    return qk[i][4]

tok_flow = defaultdict(lambda: defaultdict(int)); tx_ts = {}
with gzip.open('data/transfers.jsonl.gz', 'rt') as f:
    for line in f:
        e = json.loads(line)
        frm, to, amt, tx = e['from'].lower(), e['to'].lower(), int(e['amount']), e['tx']
        tx_ts[tx] = e['ts']
        if frm in MARKETS and to not in MARKETS and to not in (ZERO, DEAD):
            if frm != FEE_DIST:
                tok_flow[tx][to] += amt
        elif to in MARKETS and frm not in MARKETS and frm not in (ZERO, DEAD):
            tok_flow[tx][frm] -= amt

q_in = defaultdict(int); q_out = defaultdict(int)
with open('data/weth_pool.jsonl') as f:
    for line in f:
        e = json.loads(line); amt = int(e['amount'])
        if e['to'].lower() == POOL: q_in[e['tx']] += amt
        elif e['from'].lower() == POOL: q_out[e['tx']] += amt

swaps = []
pnl = defaultdict(lambda: {"buy_tok": 0, "buy_usd": Decimal(0), "sell_tok": 0,
                           "sell_usd": Decimal(0), "unpriced_tok": 0})
for tx, flows in tok_flow.items():
    ts = tx_ts[tx]; qusd = Decimal(str(quote_usd(ts)))
    win = raw_to_units(q_in.get(tx, 0), quote_dec)
    wout = raw_to_units(q_out.get(tx, 0), quote_dec)
    buyers = {a: v for a, v in flows.items() if v > 0}
    sellers = {a: -v for a, v in flows.items() if v < 0}
    tb, ts_ = sum(buyers.values()), sum(sellers.values())
    if tb > 0 and win > 0:
        for a, v in buyers.items():
            pnl[a]["buy_tok"] += v
            pnl[a]["buy_usd"] += win * (Decimal(v) / Decimal(tb)) * qusd
        swaps.append({"tx": tx, "ts": ts, "side": "buy",
                      "tok": float(raw_to_units(tb, dec)), "quote": float(win)})
    elif tb > 0:
        for a, v in buyers.items(): pnl[a]["unpriced_tok"] += v
    if ts_ > 0 and wout > 0:
        for a, v in sellers.items():
            pnl[a]["sell_tok"] += v
            pnl[a]["sell_usd"] += wout * (Decimal(v) / Decimal(ts_)) * qusd
        swaps.append({"tx": tx, "ts": ts, "side": "sell",
                      "tok": float(raw_to_units(ts_, dec)), "quote": float(wout)})

json.dump(swaps, open('data/swaps.json', 'w'))
out = {}
for a, p in pnl.items():
    if p["buy_tok"] + p["sell_tok"] >= TOTAL * MIN_SHARE:
        bt, st = p["buy_tok"], p["sell_tok"]
        realized = p["sell_usd"] - (p["buy_usd"] * (min(st, bt) / bt if bt else 0))
        bt_units, st_units = raw_to_units(bt, dec), raw_to_units(st, dec)
        out[a] = {"buy_tok": float(bt_units), "buy_usd": float(p["buy_usd"]),
                  "avg_buy_usd_per_m": float(p["buy_usd"] / (bt_units / 10**6)) if bt else 0,
                  "sell_tok": float(st_units), "sell_usd": float(p["sell_usd"]),
                  "realized_usd": float(realized),
                  "unpriced_tok": float(raw_to_units(p["unpriced_tok"], dec))}
json.dump(out, open('data/entity_pnl.json', 'w'), indent=1)
print(f"swaps: {len(swaps)} 笔tx级对价, entity_pnl: {len(out)} 地址", flush=True)
