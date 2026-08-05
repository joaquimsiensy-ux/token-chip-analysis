#!/usr/bin/env python3
"""Blockscout 版 gas 溯源（HyperSync transactions 按地址扫全链极慢时的替代主力）。
来源：Pointless(Robinhood) 分析 2026-07-13 收编参数化。
对候选大户逐地址查最早入金交易（native value>0 的 to=该地址 + 合约内部转入），识别母钱包/金主。
用法：cd 工作目录（含 config.json 且已跑完 pull_transfers.py）后
  python3 gas_trace_bs.py
候选=峰值≥gas_trace.peak_share_min(默认0.4%) 或现仓≥balance_share_min，且不在 infra_addresses。
可选 config.gas_trace.extra_targets=[...] 追加重点地址（如部署者/金库）。
输出 data/gas_in_bs.jsonl：{addr,funder,value_eth,ts,hash,method}（每地址最早≤6笔）+ 末尾 funder→目标数汇总。
断点续传：已有输出中的地址跳过。坑：Blockscout 须带浏览器 UA（默认 UA 被 403）。
"""
import json, gzip, ssl, certifi, urllib.request, time, os, sys
from collections import defaultdict
from resume_guard import require_fetch_success

SSL_CTX = ssl.create_default_context(cafile=certifi.where())
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')
BS = "https://robinhoodchain.blockscout.com/api/v2"

cfg = json.load(open('config.json'))
dec = int(cfg.get('decimals') or 18)
TOTAL = int(cfg.get('total_supply_tokens') or 0) * 10 ** dec
if not TOTAL:
    sys.exit("config.json 缺 total_supply_tokens")
infra = set(a.lower() for a in cfg.get('infra_addresses') or [])
gt = cfg.get('gas_trace') or {}
PEAK_MIN = float(gt.get('peak_share_min', 0.004))
BAL_MIN = float(gt.get('balance_share_min', 0.0008))
EXTRA = [a.lower() for a in gt.get('extra_targets', [])]

bal = defaultdict(int); peak = defaultdict(int)
with gzip.open('data/transfers.jsonl.gz', 'rt') as f:
    for line in f:
        r = json.loads(line)
        a = int(r['amount'])
        bal[r['from'].lower()] -= a
        bal[r['to'].lower()] += a
        if bal[r['to'].lower()] > peak[r['to'].lower()]:
            peak[r['to'].lower()] = bal[r['to'].lower()]

targets = set(EXTRA)
for ad, p in peak.items():
    if ad in infra:
        continue
    if p >= TOTAL * PEAK_MIN or bal.get(ad, 0) >= TOTAL * BAL_MIN:
        targets.add(ad)
targets = sorted(targets)
print(f"目标 {len(targets)} 个", flush=True)

done = set()
OUT = 'data/gas_in_bs.jsonl'
if os.path.exists(OUT):
    with open(OUT) as f:
        for line in f:
            row = json.loads(line)
            if row.get("status") in {"PASS", "EMPTY"} or row.get("funder"):
                done.add(row['addr'])
    print(f"已完成 {len(done)} 个，续跑", flush=True)


def get(url):
    req = urllib.request.Request(url, headers={'accept': 'application/json', 'User-Agent': UA})
    for i in range(4):
        try:
            with urllib.request.urlopen(url=req, timeout=30, context=SSL_CTX) as r:
                return True, json.load(r)
        except Exception:
            time.sleep(2 * (i + 1))
    return False, None


fout = open(OUT, 'a')
n = 0
failures = []
for ad in targets:
    if ad in done:
        continue
    ok, d = get(f"{BS}/addresses/{ad}/transactions?filter=to")
    n += 1
    if not ok:
        failures.append(ad)
        print(f"  {ad} API 重试耗尽，进入 retry queue（不写 EMPTY/done）", flush=True)
        continue
    d = require_fetch_success(ok, d)
    rows = []
    if d:
        items = d.get('items', [])
        vals = [t for t in items if int(t.get('value', '0')) > 0]
        vals.sort(key=lambda t: t['timestamp'])
        for t in vals[:6]:
            fu = (t.get('from') or {}).get('hash', '').lower()
            # L1→L2 桥别名自检：funder = 目标地址 + 0x1111…1111 ⇒ 本人从 L1 自充值，不是独立金主
            # （来源：TRASH(Robinhood) 增量更新 2026-07-14，3 例把自充值误判为独立金主）
            ALIAS = 0x1111000000000000000000000000000000001111
            self_alias = False
            try:
                self_alias = (int(fu, 16) - ALIAS) % (1 << 160) == int(ad, 16)
            except ValueError:
                pass
            rows.append({"addr": ad, "funder": fu, "self_alias": self_alias,
                         "status": "PASS",
                         "value_eth": int(t['value']) / 1e18, "ts": t['timestamp'],
                         "hash": t['hash'], "method": t.get('method'),
                         "n_page_txs": len(items), "has_next": bool(d.get('next_page_params'))})
    if not rows:
        rows = [{"addr": ad, "funder": None, "status": "EMPTY", "note": "no_native_in"}]
    for r in rows:
        fout.write(json.dumps(r) + "\n")
    fout.flush()
    if n % 20 == 0:
        print(f"  {n} done", flush=True)
    time.sleep(0.25)
fout.close()
json.dump({"schema": "gas-trace-retry/v2", "addresses": failures},
          open("data/gas_in_bs.retry.json", "w"), indent=2)
if failures:
    print(f"BLOCK: {len(failures)} 地址网络失败，未进入 done", flush=True)
    sys.exit(2)
print("全部完成", flush=True)

funders = defaultdict(set)
n_alias = 0
with open(OUT) as f:
    for line in f:
        r = json.loads(line)
        if r.get('self_alias'):
            n_alias += 1
            continue  # 自充值不进金主聚合
        if r.get('funder'):
            funders[r['funder']].add(r['addr'])
if n_alias:
    print(f"\n[alias 自检] {n_alias} 笔入金为 L1→L2 桥自充值（本人跨链），已从金主聚合剔除")
print("\n=== funder -> ≥2 个目标（母钱包候选，已剔 infra；上千用户者仍是公共设施） ===")
for fu, ads in sorted(funders.items(), key=lambda x: -len(x[1])):
    if len(ads) >= 2:
        tag = ' [infra]' if fu in infra else ''
        print(f"{fu} -> {len(ads)} 个{tag}")
