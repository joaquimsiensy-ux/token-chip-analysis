#!/usr/bin/env python3
"""拉主池报价币(WETH)侧 Transfer（from=pool 或 to=pool），供 cost_engine.py 逐笔 swap 对价。
来源：Pointless(Robinhood) 分析 2026-07-13 收编参数化。
用法：cd 工作目录（含 config.json，需 pool + hypersync.key；报价币默认 WETH，可 config.quote_token 覆盖）后
  python3 pull_weth_pool.py
输出 data/weth_pool.jsonl：{block, ts, tx, logi, from, to, amount}
"""
import json, os, ssl, certifi, urllib.request, time, sys

SSL_CTX = ssl.create_default_context(cafile=certifi.where())
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

cfg = json.load(open("config.json"))
URL = cfg["hypersync"]["url"]; KEY = cfg["hypersync"]["key"]
POOL = (cfg.get("pool") or "").lower()
QUOTE = (cfg.get("quote_token") or "0x0bd7d308f8e1639fab988df18a8011f41eacad73").lower()  # WETH 默认
FROM_BLOCK = int(cfg.get("deploy_block") or 0)
if not POOL.startswith("0x"):
    sys.exit("config.json 缺 pool")
POOL_TOPIC = "0x000000000000000000000000" + POOL[2:]


def query(body):
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {KEY}"})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=120, context=SSL_CTX) as r:
                return json.load(r)
        except Exception:
            time.sleep(2 ** attempt)
    raise RuntimeError("HyperSync fail")


def pull(topics, tag):
    rows = []; fb = FROM_BLOCK
    while True:
        d = query({"from_block": fb,
                   "logs": [{"address": [QUOTE], "topics": topics}],
                   "field_selection": {"log": ["block_number", "log_index", "transaction_hash", "topic1", "topic2", "data"],
                                        "block": ["number", "timestamp"]}})
        for batch in d.get("data", []):
            bts = {b["number"]: (int(b["timestamp"], 16) if isinstance(b["timestamp"], str) else b["timestamp"])
                   for b in batch.get("blocks", [])}
            for lg in batch.get("logs", []):
                rows.append({"block": lg["block_number"], "ts": bts.get(lg["block_number"], 0),
                             "tx": lg["transaction_hash"], "logi": lg["log_index"],
                             "from": "0x" + lg["topic1"][26:], "to": "0x" + lg["topic2"][26:],
                             "amount": str(int(lg["data"], 16))})
        nb = d.get("next_block"); ah = d.get("archive_height", 0)
        if not nb or nb == fb or fb >= ah:
            break
        fb = nb
    print(f"{tag}: {len(rows)} 条", flush=True)
    return rows


rows = pull([[TRANSFER], [POOL_TOPIC]], "from=pool")
rows += pull([[TRANSFER], [], [POOL_TOPIC]], "to=pool")
uniq = {(r["tx"], r["logi"]): r for r in rows}
rows = sorted(uniq.values(), key=lambda x: (x["block"], x["logi"]))
with open("data/weth_pool.jsonl", "w") as f:
    for r in rows:
        f.write(json.dumps(r) + "\n")
print(f"共 {len(rows)} 条 → data/weth_pool.jsonl", flush=True)
