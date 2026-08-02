#!/usr/bin/env python3
"""requests.Session 连接复用版 decode（省 TLS 握手，比 curl 版快约 3 倍）。

用法: python3 decode_txs_fast.py --sigs <jsonl> --out <jsonl> [--mint M] [--pool P]
     [--interval 0.75] [--proxy http://...]
输出行格式与 decode_txs.py 一致，断点续传兼容。
"""
import argparse, json, sys, time
from pathlib import Path
import requests
from decode_txs_v2 import decode_result

RPC = "https://api.mainnet-beta.solana.com"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sigs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mint", default=None)
    ap.add_argument("--pool", default=None)
    ap.add_argument("--interval", type=float, default=0.75)
    ap.add_argument("--proxy", default=None)
    args = ap.parse_args()

    sess = requests.Session()
    if args.proxy:
        sess.proxies = {"http": args.proxy, "https": args.proxy}
    mint = args.mint
    if not mint:
        cfg = Path("config.json")
        if cfg.exists():
            mint = json.loads(cfg.read_text()).get("mint")
    if not mint:
        print("no mint", file=sys.stderr); sys.exit(1)

    def rpc(sig, retries=5):
        body = {"jsonrpc": "2.0", "id": 1, "method": "getTransaction",
                "params": [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0,
                                 "commitment": "confirmed"}]}
        for i in range(retries):
            try:
                r = sess.post(RPC, json=body, timeout=35)
                d = r.json()
                if "result" in d:
                    return d["result"]
                if (d.get("error") or {}).get("code") == 429:
                    time.sleep(5 * (i + 1)); continue
            except Exception:
                pass
            time.sleep(1.8 * (i + 1))
        return None

    sigs = []
    for line in open(args.sigs):
        line = line.strip()
        if not line: continue
        if line.startswith("{"):
            d = json.loads(line)
            if d.get("err"): continue
            sigs.append(d["signature"])
        else:
            sigs.append(line)
    outp = Path(args.out)
    done = set()
    if outp.exists():
        for line in open(outp):
            try: done.add(json.loads(line)["sig"])
            except Exception: pass
    todo = [s for s in sigs if s not in done]
    print(f"[fast-decode] total={len(sigs)} done={len(done)} todo={len(todo)}", file=sys.stderr, flush=True)

    f = open(outp, "a")
    t0 = time.time(); n_ok = 0; n_fail = 0
    for i, sig in enumerate(todo):
        res = rpc(sig)
        if res is None:
            n_fail += 1
            f.write(json.dumps({"sig": sig, "decode_fail": True}) + "\n")
        else:
            row = decode_result(sig, res, mint, args.pool)
            f.write(json.dumps(row) + "\n")
            n_ok += 1
        if (i + 1) % 200 == 0:
            f.flush()
            rate = (i + 1) / (time.time() - t0)
            eta = (len(todo) - i - 1) / rate / 60
            print(f"[fast-decode] {i+1}/{len(todo)} ok={n_ok} fail={n_fail} rate={rate:.2f}/s ETA={eta:.0f}min",
                  file=sys.stderr, flush=True)
        time.sleep(args.interval)
    f.close()
    print(f"[fast-decode] DONE ok={n_ok} fail={n_fail} 耗时{(time.time()-t0)/60:.1f}min", file=sys.stderr, flush=True)

if __name__ == "__main__":
    main()
