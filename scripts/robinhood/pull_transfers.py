#!/usr/bin/env python3
"""从 envio HyperSync 拉取代币全量 Transfer 事件（Robinhood 链，logs 路线）。

来源：RAXOL(Robinhood) 分析实战 2026-07-12，v1.3 参数化收编（token/key 移入工作目录 config.json）。
用法：cd 到工作目录（含 config.json，见同目录 config.example.json）后
  python3 pull_transfers.py
输出：data/transfers.jsonl.gz  每行 {block, ts, tx, logi, from, to, amount(str, wei), txfrom, txto}
断点续传：输出文件已存在时从末行 block+1 继续。
注意：HyperSync 该链 logs 快、transactions 按地址扫全链极慢（按地址查交易改用
Blockscout robinhoodchain.blockscout.com，见 references/data-pipeline-robinhood.md）。
"""
import json, gzip, os, sys, time
import urllib.request
import ssl, certifi

SSL_CTX = ssl.create_default_context(cafile=certifi.where())
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
OUT = os.path.join("data", "transfers.jsonl.gz")


def load_cfg():
    with open("config.json") as f:
        cfg = json.load(f)
    token = (cfg.get("token") or "").lower()
    hs = cfg.get("hypersync") or {}
    url = hs.get("url") or "https://robinhood.hypersync.xyz/query"
    key = hs.get("key") or os.environ.get("HYPERSYNC_KEY") or ""
    if not token.startswith("0x") or len(token) != 42:
        sys.exit("config.json 的 token 缺失或不是合法 0x 地址")
    if not key:
        sys.exit("HyperSync key 缺失：填 config.json hypersync.key 或设环境变量 HYPERSYNC_KEY（key 见 ~/.claude/api-keys.md envio 条目）")
    return token, url, key


def query(url, key, token, from_block):
    body = {
        "from_block": from_block,
        "logs": [{"address": [token], "topics": [[TRANSFER]]}],
        "field_selection": {
            "log": ["block_number", "log_index", "transaction_hash", "topic1", "topic2", "data"],
            "block": ["number", "timestamp"],
            "transaction": ["hash", "from", "to"],
        },
    }
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {key}"})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=120, context=SSL_CTX) as r:
                return json.load(r)
        except Exception as e:
            wait = 2 ** attempt
            print(f"  重试 {attempt+1}: {e} (等 {wait}s)", flush=True)
            time.sleep(wait)
    raise RuntimeError("HyperSync 连续失败")


def main():
    token, url, key = load_cfg()
    os.makedirs("data", exist_ok=True)
    start = 0
    mode = "wb"
    if os.path.exists(OUT):
        last = None
        with gzip.open(OUT, "rt") as f:
            for line in f:
                if line.strip():
                    last = line
        if last:
            start = json.loads(last)["block"] + 1
            mode = "ab"
            print(f"断点续传: 从块 {start} 继续", flush=True)

    total = 0
    t0 = time.time()
    with gzip.open(OUT, mode) as out:
        fb = start
        while True:
            resp = query(url, key, token, fb)
            ah = resp.get("archive_height") or 0
            nb = resp.get("next_block")
            for batch in resp.get("data", []):
                ts_map = {b["number"]: int(b["timestamp"], 16) if isinstance(b["timestamp"], str) else b["timestamp"]
                          for b in batch.get("blocks", [])}
                txfrom = {}
                txto = {}
                for t in batch.get("transactions", []):
                    txfrom[t["hash"]] = (t.get("from") or "").lower()
                    txto[t["hash"]] = (t.get("to") or "").lower()
                for lg in batch.get("logs", []):
                    amt = int(lg["data"], 16) if lg.get("data") and lg["data"] != "0x" else 0
                    row = {
                        "block": lg["block_number"],
                        "ts": ts_map.get(lg["block_number"]),
                        "tx": lg["transaction_hash"],
                        "logi": lg["log_index"],
                        "from": "0x" + lg["topic1"][-40:],
                        "to": "0x" + lg["topic2"][-40:],
                        "amount": str(amt),
                        "txfrom": txfrom.get(lg["transaction_hash"], ""),
                        "txto": txto.get(lg["transaction_hash"], ""),
                    }
                    out.write((json.dumps(row) + "\n").encode())
                    total += 1
            if nb is None or nb <= fb:
                print(f"next_block 停滞于 {fb}, 结束", flush=True)
                break
            fb = nb
            if total and total % 50000 < 100:
                print(f"  进度: 块 {fb}/{ah}, 已 {total} 条, {time.time()-t0:.0f}s", flush=True)
            if fb >= ah:
                print(f"已达链高 {ah}", flush=True)
                break
    print(f"完成: 共 {total} 条新事件, 耗时 {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
