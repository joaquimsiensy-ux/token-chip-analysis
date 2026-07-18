#!/usr/bin/env python3
"""批量 gas 溯源：查候选大户地址收到的原生币转账（value>0），识别母钱包。

来源：RAXOL(Robinhood) 分析实战 2026-07-12，v1.3 参数化收编（key/阈值/基础设施名单移入 config.json）。
用法：cd 到工作目录（含 config.json 且已跑完 pull_transfers.py）后
  python3 gas_trace.py
候选筛选：重放 data/transfers.jsonl.gz 得每地址峰值/现仓，占总量 ≥peak_share_min 或
现仓 ≥balance_share_min 且不在 infra_addresses 名单的入选。
输出：data/gas_in.jsonl 每行 {addr, from, value(str), block, ts, hash}，每地址最早 per_addr_limit 笔。
坑：f70da（Relay solver）等平台 gas 中继必须在 infra_addresses 里剔除，
"同用它供 gas"≠同一实体（见 references/data-pipeline-robinhood.md 坑 1）。
"""
import json, gzip, os, sys, time, ssl, certifi
import urllib.request
from collections import defaultdict

SSL_CTX = ssl.create_default_context(cafile=certifi.where())


def load_cfg():
    with open("config.json") as f:
        cfg = json.load(f)
    hs = cfg.get("hypersync") or {}
    url = hs.get("url") or "https://robinhood.hypersync.xyz/query"
    key = hs.get("key") or os.environ.get("HYPERSYNC_KEY") or ""
    if not key:
        sys.exit("HyperSync key 缺失：填 config.json hypersync.key 或设环境变量 HYPERSYNC_KEY（key 见 ~/.claude/api-keys.md envio 条目）")
    dec = int(cfg.get("decimals") or 18)
    tot = int(cfg.get("total_supply_tokens") or 0) * 10 ** dec
    if not tot:
        sys.exit("config.json 的 total_supply_tokens 缺失（用于占比阈值筛选）")
    infra = {a.lower() for a in cfg.get("infra_addresses") or []}
    gt = cfg.get("gas_trace") or {}
    return {
        "url": url, "key": key, "tot": tot, "infra": infra,
        "peak_min": float(gt.get("peak_share_min", 0.004)),
        "bal_min": float(gt.get("balance_share_min", 0.0008)),
        "limit": int(gt.get("per_addr_limit", 8)),
    }


def build_targets(c):
    bal = defaultdict(int)
    peak = defaultdict(int)
    with gzip.open(os.path.join("data", "transfers.jsonl.gz"), "rt") as f:
        for line in f:
            r = json.loads(line)
            a = int(r["amount"])
            bal[r["from"]] -= a
            bal[r["to"]] += a
            if bal[r["to"]] > peak[r["to"]]:
                peak[r["to"]] = bal[r["to"]]
    targets = set()
    for ad, p in peak.items():
        if ad in c["infra"]:
            continue
        if p >= c["tot"] * c["peak_min"] or bal[ad] >= c["tot"] * c["bal_min"]:
            targets.add(ad)
    return sorted(targets)


def query(c, body):
    req = urllib.request.Request(c["url"], data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {c['key']}"})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=120, context=SSL_CTX) as r:
                return json.load(r)
        except Exception:
            time.sleep(2 ** attempt)
    raise RuntimeError("HyperSync 连续失败")


def main():
    c = load_cfg()
    targets = build_targets(c)
    print(f"溯源目标: {len(targets)} 个地址", flush=True)
    got = defaultdict(list)
    B = 50
    for i in range(0, len(targets), B):
        batch = targets[i:i+B]
        fb = 0
        while True:
            resp = query(c, {
                "from_block": fb,
                "transactions": [{"to": batch}],
                "field_selection": {
                    "transaction": ["from", "to", "value", "block_number", "hash"],
                    "block": ["number", "timestamp"],
                },
            })
            ah = resp.get("archive_height") or 0
            nb = resp.get("next_block")
            for b in resp.get("data", []):
                ts_map = {bl["number"]: int(bl["timestamp"], 16) if isinstance(bl["timestamp"], str) else bl["timestamp"]
                          for bl in b.get("blocks", [])}
                for t in b.get("transactions", []):
                    v = t.get("value")
                    v = int(v, 16) if isinstance(v, str) else (v or 0)
                    if v <= 0:
                        continue
                    to = (t.get("to") or "").lower()
                    if len(got[to]) >= c["limit"]:
                        continue
                    got[to].append({
                        "addr": to, "from": (t.get("from") or "").lower(),
                        "value": str(v), "block": t["block_number"],
                        "ts": ts_map.get(t["block_number"]), "hash": t["hash"],
                    })
            if nb is None or nb <= fb or nb >= ah:
                break
            fb = nb
        print(f"  批 {i//B+1}/{(len(targets)+B-1)//B} 完成", flush=True)
    out = os.path.join("data", "gas_in.jsonl")
    with open(out, "w") as f:
        for ad in targets:
            for row in got[ad]:
                f.write(json.dumps(row) + "\n")
    print(f"完成: {sum(len(v) for v in got.values())} 条入金记录, 覆盖 {sum(1 for a in targets if got[a])}/{len(targets)} 地址", flush=True)


if __name__ == "__main__":
    main()
