#!/usr/bin/env python3
"""拉取标的 V3 池的全量 Swap 事件（HyperSync logs 路线，Robinhood 链）。
来源：CASHCAT(Robinhood) 分析实战 2026-07-13，v1.5 参数化收编。
用法：cd 到工作目录（含 config.json，池子写 swap_pools 数组）后 python3 pull_swaps.py
输出 data/swaps.jsonl.gz 每行:
  {block, ts, tx, logi, pool, sender, recip, a0, a1, sqrtp}
a0=CASHCAT(token0) 池子视角变化量, a1=WETH(token1); 均为带符号十进制字符串。
断点续传：输出已存在时从末行 block+1 续。
"""
import json, gzip, os, sys, time
import urllib.request
import ssl, certifi
from resume_guard import bind_output, overlap_state, require_progress, write_receipt

SSL_CTX = ssl.create_default_context(cafile=certifi.where())
SWAP_V3 = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
OUT = os.path.join("data", "swaps.jsonl.gz")

with open("config.json") as f:
    CFG = json.load(f)
# 池子清单: 优先 config.swap_pools(数组); 回退 notes.pools.v3_main/v3_second
_p = CFG.get("swap_pools")
if not _p:
    np_ = (CFG.get("notes") or {}).get("pools") or {}
    _p = [v for k, v in np_.items() if isinstance(v, str) and v.startswith("0x")]
POOLS = [a.lower() for a in _p]
if not POOLS:
    import sys; sys.exit("config.json 缺 swap_pools 数组(或 notes.pools)")
URL = CFG["hypersync"]["url"]
KEY = CFG["hypersync"]["key"]


def to_int(h):
    v = int(h, 16)
    if v >= 1 << 255:
        v -= 1 << 256
    return v


def query(from_block):
    body = {
        "from_block": from_block,
        "logs": [{"address": POOLS, "topics": [[SWAP_V3]]}],
        "field_selection": {
            "log": ["address", "block_number", "log_index", "transaction_hash",
                     "topic1", "topic2", "data"],
            "block": ["number", "timestamp"],
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
    identity = {"collector": "pull_swaps_v3/v2", "token": (CFG.get("token") or "").lower(),
                "pools": sorted(POOLS), "url": URL, "query_schema": "uniswap-v3-swap/v2"}
    bind_output(OUT, identity)
    start, overlap_keys, n_have = overlap_state(OUT, ("block", "tx", "logi"))
    print(f"断点续传: 已有 {n_have} 条, 重叠回拉 block {start}", flush=True)
    fo = gzip.open(OUT, "at")
    total = n_have
    t0 = time.time()
    while True:
        res = query(start)
        wrote = 0
        for batch in res.get("data", []):
            blocks = {b["number"]: b.get("timestamp") for b in batch.get("blocks", [])}
            for lg in batch.get("logs", []):
                event_key = (lg["block_number"], lg.get("transaction_hash"), lg.get("log_index"))
                if event_key in overlap_keys:
                    continue
                data = lg.get("data") or "0x"
                raw = data[2:]
                if len(raw) < 64 * 5:
                    continue
                a0 = to_int("0x" + raw[0:64])
                a1 = to_int("0x" + raw[64:128])
                sqrtp = int("0x" + raw[128:192], 16)
                ts = blocks.get(lg["block_number"])
                fo.write(json.dumps({
                    "block": lg["block_number"],
                    "ts": int(ts, 16) if isinstance(ts, str) else ts,
                    "tx": lg.get("transaction_hash"),
                    "logi": lg.get("log_index"),
                    "pool": (lg.get("address") or "").lower(),
                    "sender": "0x" + (lg.get("topic1") or "0x" + "0"*64)[-40:],
                    "recip": "0x" + (lg.get("topic2") or "0x" + "0"*64)[-40:],
                    "a0": str(a0), "a1": str(a1), "sqrtp": str(sqrtp),
                }, separators=(",", ":")) + "\n")
                total += 1
                wrote += 1
        nb = res.get("next_block")
        arch = res.get("archive_height")
        if wrote:
            fo.flush()
        el = time.time() - t0
        print(f"block→{nb} 共 {total} 条 swap ({el:.0f}s)", flush=True)
        reached = require_progress(start, nb, arch)
        if reached:
            break
        start = nb
        time.sleep(0.3)
    fo.close()
    write_receipt(OUT, identity, arch, nb, total)
    print(f"完成: {total} 条 → {OUT}", flush=True)


if __name__ == "__main__":
    main()
