#!/usr/bin/env python3
"""HyperSync 拉指定合约的【全部事件 logs】（不筛 topic0），保留 topic0-3+data。
基于 skill scripts/evm/fetch_hypersync.py 改（Transfer 专用版→全事件版），用于 BondingManager 质押账本重建。
用法：python3 fetch_hypersync_logs.py <api_token> <from_block> --url <endpoint> --addr <合约> --out <csv>
断点续传：--out 已存在且非空时自动从末行块续拉（重叠由下游按 uniqueId 去重）。
"""
import requests, csv, os, sys, time, datetime, argparse

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("api_token")
    ap.add_argument("from_block", type=int)
    ap.add_argument("--url", required=True)
    ap.add_argument("--addr", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sleep", type=float, default=0.4)
    a = ap.parse_args()
    headers = {"Authorization": f"Bearer {a.api_token}", "Content-Type": "application/json"}
    resume, mode = a.from_block, "w"
    if os.path.exists(a.out) and os.path.getsize(a.out) > 100:
        with open(a.out, "rb") as fh:
            try:
                fh.seek(-8192, os.SEEK_END)
            except OSError:
                fh.seek(0)
            tail = fh.read().decode(errors="ignore").strip().splitlines()
            last = tail[-1].split(",")
            if last and last[0].isdigit():
                resume, mode = int(last[0]), "a"
                print(f"[resume] 从已有 CSV 末行块 {resume} 续拉", flush=True)
    f = open(a.out, mode, newline="")
    w = csv.writer(f)
    if mode == "w":
        w.writerow(["block", "ts", "tx", "topic0", "topic1", "topic2", "topic3", "data", "uniqueId"])
    total, cur, t0, e429 = 0, resume, time.time(), 0
    while True:
        q = {"from_block": cur,
             "logs": [{"address": [a.addr]}],
             "field_selection": {
                 "log": ["block_number", "log_index", "transaction_hash", "topic0", "topic1", "topic2", "topic3", "data"],
                 "block": ["number", "timestamp"]}}
        ok = False
        for attempt in range(12):
            try:
                r = requests.post(a.url, json=q, headers=headers, timeout=90)
                if r.status_code == 200:
                    j = r.json(); ok = True; break
                if r.status_code == 429:
                    e429 += 1
                print(f"[http {r.status_code}] {r.text[:120]}", flush=True)
                time.sleep(min(3 * (attempt + 1), 30))
            except Exception as e:
                print(f"[exc] {str(e)[:100]}", flush=True)
                time.sleep(min(3 * (attempt + 1), 30))
        if not ok:
            print("[fatal] giving up", flush=True); sys.exit(2)
        bts, n = {}, 0
        for batch in j.get("data", []):
            for b in batch.get("blocks", []):
                ts = b.get("timestamp")
                bts[int(b["number"])] = int(ts, 16) if isinstance(ts, str) else int(ts)
            for lg in batch.get("logs", []):
                bn = int(lg["block_number"])
                ts = bts.get(bn)
                iso = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") if ts else ""
                li = int(lg["log_index"])
                w.writerow([bn, iso, lg["transaction_hash"],
                            lg.get("topic0") or "", lg.get("topic1") or "",
                            lg.get("topic2") or "", lg.get("topic3") or "",
                            lg.get("data") or "",
                            f"{lg['transaction_hash']}:log:{li}"])
                n += 1
        total += n
        nxt, ah = j.get("next_block"), j.get("archive_height")
        if total % 50000 < n or n == 0:
            print(f"[prog] +{n} total {total} next {nxt} height {ah} 429s {e429} {time.time()-t0:.0f}s", flush=True)
        if not nxt or (ah and nxt >= ah):
            break
        cur = nxt
        time.sleep(a.sleep)
    f.close()
    print(f"[COMPLETE] {total} logs this run, tip {ah}, 429s {e429}, {time.time()-t0:.0f}s", flush=True)

if __name__ == "__main__":
    main()
