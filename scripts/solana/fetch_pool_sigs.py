#!/usr/bin/env python3
"""池子/地址签名全史落盘（只拉签名列表不 decode）。

用法: python3 fetch_pool_sigs.py <address> <outfile.jsonl> [--rpc URL]
输出: 每行 {signature, slot, blockTime, err}，从新到老追加；断点续传（读末行 signature 作 before 游标）。
"""
import json, subprocess, sys, time
from pathlib import Path

RPC = "https://api.mainnet-beta.solana.com"

def rpc_call(method, params, retries=5):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    for i in range(retries):
        p = subprocess.run(["curl", "-s", "-m", "40", RPC,
                            "-H", "Content-Type: application/json", "-d", body],
                           capture_output=True, text=True)
        try:
            d = json.loads(p.stdout)
            if "result" in d:
                return d["result"]
            if "error" in d and d["error"].get("code") == 429:
                time.sleep(3 * (i + 1)); continue
        except Exception:
            pass
        time.sleep(1.5 * (i + 1))
    return None

def main():
    addr, outfile = sys.argv[1], Path(sys.argv[2])
    before = None
    total = 0
    if outfile.exists():
        # 断点续传：取末行签名作为 before
        with open(outfile) as f:
            last = None
            for line in f:
                line = line.strip()
                if line:
                    last = line
                    total += 1
            if last:
                before = json.loads(last)["signature"]
        print(f"[resume] 已有 {total} 条, before={before[:20] if before else None}...", file=sys.stderr, flush=True)
    f = open(outfile, "a")
    pages = 0
    t0 = time.time()
    while True:
        params = [addr, {"limit": 1000}]
        if before:
            params[1]["before"] = before
        res = rpc_call("getSignaturesForAddress", params)
        if res is None:
            print(f"[fail] RPC 连续失败 at page {pages}, total={total}", file=sys.stderr, flush=True)
            break
        if not res:
            print(f"[done] 翻到底. total={total}, pages={pages}, 耗时{time.time()-t0:.0f}s", file=sys.stderr, flush=True)
            break
        for r in res:
            f.write(json.dumps({"signature": r["signature"], "slot": r["slot"],
                                "blockTime": r.get("blockTime"), "err": (r.get("err") is not None)}) + "\n")
        total += len(res)
        before = res[-1]["signature"]
        pages += 1
        if pages % 50 == 0:
            f.flush()
            bt = res[-1].get("blockTime")
            ts = time.strftime("%m-%d %H:%M", time.gmtime(bt)) if bt else "?"
            print(f"[progress] {total} sigs, 翻到 {ts}, {time.time()-t0:.0f}s", file=sys.stderr, flush=True)
        time.sleep(0.13)
        if len(res) < 1000:
            print(f"[done] 尾页. total={total}, pages={pages}, 耗时{time.time()-t0:.0f}s", file=sys.stderr, flush=True)
            break
    f.close()

if __name__ == "__main__":
    main()
