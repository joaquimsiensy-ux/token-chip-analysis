#!/usr/bin/env python3
"""拉取 Uniswap V4 PoolManager 上标的全部池的 Swap + ModifyLiquidity 事件（HyperSync logs）。

TRASH(Robinhood) 分析现场件 2026-07-14——skill 管道 V4 采集 Known Gap 的首次实做。
用法：cd 工作目录（含 config.json，池子写 swap_pools_v4 数组=poolId 列表）后 python3 pull_swaps_v4.py
输出 data/swaps_v4.jsonl.gz 每行：
  swap:   {ev:"swap", block, ts, tx, logi, pool, sender, a0, a1, sqrtp, liq, tick, fee, txfrom, txto}
  modliq: {ev:"modliq", block, ts, tx, logi, pool, sender, tickl, ticku, liqdelta, txfrom, txto}
a0/a1 为 V4 事件原始带符号 int128（十进制字符串）；符号方向以实 tx 对照 Transfer 校准后再用。
断点续传：输出已存在时从末行 block+1 续。
topic0 实测于链上（2026-07-14）：Swap=0x40e9cecb…, ModifyLiquidity=0xf208f491…
"""
import json, gzip, os, sys, time
import urllib.request
import ssl, certifi

SSL_CTX = ssl.create_default_context(cafile=certifi.where())
SWAP_V4 = "0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f"
MODLIQ_V4 = "0xf208f4912782fd25c7f114ca3723a2d5dd6f3bcc3ac8db5af63baa85f711d5ec"
OUT = os.path.join("data", "swaps_v4.jsonl.gz")

with open("config.json") as f:
    CFG = json.load(f)
POOLS = [p.lower() for p in CFG["swap_pools_v4"]]
PM = CFG["pool_manager"].lower()
URL = CFG["hypersync"]["url"]
KEY = CFG["hypersync"]["key"]


def to_int(hexword, bits=256):
    v = int(hexword, 16)
    if v >= 1 << 255:
        v -= 1 << 256
    return v


def query(from_block):
    body = {
        "from_block": from_block,
        "logs": [{"address": [PM], "topics": [[SWAP_V4, MODLIQ_V4], POOLS]}],
        "field_selection": {
            "log": ["block_number", "log_index", "transaction_hash",
                    "topic0", "topic1", "topic2", "data"],
            "block": ["number", "timestamp"],
            "transaction": ["hash", "from", "to"],
        },
    }
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {KEY}"})
    for attempt in range(8):
        try:
            with urllib.request.urlopen(req, timeout=120, context=SSL_CTX) as r:
                return json.load(r)
        except Exception as e:
            wait = min(2 ** attempt, 60)
            print(f"  重试 {attempt+1}: {e} (等 {wait}s)", flush=True)
            time.sleep(wait)
    raise RuntimeError("HyperSync 连续失败")


def main():
    start = 0
    n_have = 0
    if os.path.exists(OUT):
        last = None
        with gzip.open(OUT, "rt") as f:
            for line in f:
                if line.strip():
                    n_have += 1
                    last = line
        if last:
            start = json.loads(last)["block"] + 1
        print(f"断点续传: 已有 {n_have} 条, 从 block {start} 续", flush=True)
    fo = gzip.open(OUT, "at")
    total = n_have
    bad = 0
    t0 = time.time()
    while True:
        res = query(start)
        for batch in res.get("data", []):
            blocks = {b["number"]: b.get("timestamp") for b in batch.get("blocks", [])}
            txfrom, txto = {}, {}
            for t in batch.get("transactions", []):
                txfrom[t["hash"]] = (t.get("from") or "").lower()
                txto[t["hash"]] = (t.get("to") or "").lower()
            for lg in batch.get("logs", []):
                raw = (lg.get("data") or "0x")[2:]
                ts = blocks.get(lg["block_number"])
                base = {
                    "block": lg["block_number"],
                    "ts": int(ts, 16) if isinstance(ts, str) else ts,
                    "tx": lg.get("transaction_hash"),
                    "logi": lg.get("log_index"),
                    "pool": (lg.get("topic1") or "").lower(),
                    "sender": "0x" + (lg.get("topic2") or "0x" + "0" * 64)[-40:],
                    "txfrom": txfrom.get(lg.get("transaction_hash"), ""),
                    "txto": txto.get(lg.get("transaction_hash"), ""),
                }
                t0h = lg.get("topic0")
                if t0h == SWAP_V4 and len(raw) >= 64 * 6:
                    base.update({
                        "ev": "swap",
                        "a0": str(to_int("0x" + raw[0:64])),
                        "a1": str(to_int("0x" + raw[64:128])),
                        "sqrtp": str(int("0x" + raw[128:192], 16)),
                        "liq": str(int("0x" + raw[192:256], 16)),
                        "tick": to_int("0x" + raw[256:320]),
                        "fee": int("0x" + raw[320:384], 16),
                    })
                elif t0h == MODLIQ_V4 and len(raw) >= 64 * 4:
                    base.update({
                        "ev": "modliq",
                        "tickl": to_int("0x" + raw[0:64]),
                        "ticku": to_int("0x" + raw[64:128]),
                        "liqdelta": str(to_int("0x" + raw[128:192])),
                    })
                else:
                    bad += 1
                    continue
                fo.write(json.dumps(base, separators=(",", ":")) + "\n")
                total += 1
        nb = res.get("next_block")
        arch = res.get("archive_height")
        fo.flush()
        print(f"block→{nb} 共 {total} 条 (解码失败 {bad}) ({time.time()-t0:.0f}s)", flush=True)
        if not nb or (arch and nb >= arch):
            break
        start = nb
        time.sleep(0.3)
    fo.close()
    if bad:
        print(f"警告: {bad} 条 log 解码失败（长度不足），需人工核查", flush=True)
    print(f"完成: {total} 条 → {OUT}", flush=True)


if __name__ == "__main__":
    main()
