#!/usr/bin/env python3
"""ETH 主网全量代币转账 + 关键地址交易史（Etherscan V2 免费 key，仅 chainid=1）。
来源：OPN(BSC) 分析会话实战产物, 2026-07。

用法（工作目录含 config.json）：
  python3 fetch_etherscan.py tokentx                # 全量转账 → eth_transfers.csv
  python3 fetch_etherscan.py txlist <address>       # 某地址普通交易 → eth_txlist_<addr前8>.json
  python3 fetch_etherscan.py internal <address>     # 某地址内部交易

注意：免费 key 只支持以太坊主网；BSC/Base 等链会返回
"Free API access is not supported for this chain"——那些链用 scan_transfers.py 扫块。
块游标分页：offset=10000 满页时去掉最后一个可能截断的块，从该块续拉。
"""
import json, time, os, sys, csv, subprocess, urllib.parse
FORMAL_CHANNEL_ELIGIBLE = False  # diagnostic/supplemental output; preflight must reject

DIR = os.getcwd()
CFG = json.load(open(os.path.join(DIR, "config.json")))
TOKEN = CFG["token"].lower()
KEY = CFG["chains"]["eth"]["etherscan_key"]
BASE = "https://api.etherscan.io/v2/api"

def call(params, retries=5):
    params = dict(params, chainid=1, apikey=KEY)
    url = BASE + "?" + urllib.parse.urlencode(params)
    for a in range(retries):
        try:
            r = subprocess.run(["curl", "-s", "-m", "60", url], capture_output=True, text=True, timeout=90)
            d = json.loads(r.stdout)
            if d.get("status") == "1" or d.get("message") == "No transactions found":
                return d.get("result") or []
            if "rate limit" in str(d.get("result", "")).lower():
                time.sleep(2); continue
            print("[warn]", str(d.get("result"))[:100], flush=True)
            return d.get("result") or []
        except Exception as e:
            print(f"[err {a}] {e}", flush=True); time.sleep(3)
    return []

def tokentx():
    rows, startblock = [], 0
    while True:
        batch = call({"module": "account", "action": "tokentx", "contractaddress": TOKEN,
                      "startblock": startblock, "endblock": 99999999, "page": 1,
                      "offset": 10000, "sort": "asc"})
        if not isinstance(batch, list) or not batch:
            break
        rows.extend(batch)
        print(f"+{len(batch)} (total {len(rows)})", flush=True)
        if len(batch) < 10000:
            break
        last = int(batch[-1]["blockNumber"])
        rows = [r for r in rows if int(r["blockNumber"]) < last]
        startblock = last
        time.sleep(0.3)
    with open(os.path.join(DIR, "eth_transfers.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["block", "ts", "tx", "from", "to", "value_raw"])
        for r in rows:
            w.writerow([r["blockNumber"], r["timeStamp"], r["hash"], r["from"], r["to"], r["value"]])
    print(f"eth_transfers.csv: {len(rows)} rows", flush=True)

def addr_action(action, addr):
    rows = call({"module": "account", "action": action, "address": addr,
                 "startblock": 0, "endblock": 99999999, "page": 1, "offset": 10000, "sort": "asc"})
    out = os.path.join(DIR, f"eth_{action}_{addr[:10]}.json")
    json.dump(rows, open(out, "w"))
    print(f"{out}: {len(rows) if isinstance(rows, list) else rows}", flush=True)

if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "tokentx":
        tokentx()
    elif mode == "txlist":
        addr_action("txlist", sys.argv[2].lower())
    elif mode == "internal":
        addr_action("txlistinternal", sys.argv[2].lower())
