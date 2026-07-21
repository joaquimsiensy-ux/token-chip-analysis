#!/usr/bin/env python3
"""SQD Portal EVM 薄采集器（免 key 免注册；v3.11.2 定位=HyperSync 故障预案 + 数仓准入期对照源,平时不跑）。

用法: python3 fetch_sqd_evm.py <chain|dataset> <from_block> --token-addr 0x标的 \
        --out data/sqd.csv [--to-block N] [--sleep 0.5]
  - chain 快捷名: bsc/eth/base/arbitrum（其余直接传数据集名,如 optimism-mainnet）
  - 公共端点限流约 20 请求/10 秒 —— sleep 默认 0.5s,别调低
  - 断点续传: --out 已存在时从末行块+1 续拉
输出: 标准 8 列 CSV(block,ts,tx,log_index,from,to,value_raw,block_hash),
  transfers_lib.iter_transfers 直读,可与 HyperSync 产物 merge_sources 对账合并。
（来源：v3.11.2 采集加速工程,2026-07-21;响应结构按当日实测:header{number,timestamp,hash},
  log{logIndex(str),transactionHash,data,topics[]},NDJSON 每行一块,响应按大小截断需续请求）"""
import argparse, csv, json, os, sys, time

import requests

TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
DATASETS = {"bsc": "binance-mainnet", "eth": "ethereum-mainnet",
            "base": "base-mainnet", "arbitrum": "arbitrum-one"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chain")
    ap.add_argument("from_block", type=int)
    ap.add_argument("--token-addr", required=True)
    ap.add_argument("--out", default="data/sqd.csv")
    ap.add_argument("--to-block", type=int, default=None)
    ap.add_argument("--sleep", type=float, default=0.5)
    a = ap.parse_args()
    ds = DATASETS.get(a.chain, a.chain)
    base = f"https://portal.sqd.dev/datasets/{ds}"
    token = a.token_addr.lower()

    if a.to_block is None:
        r = requests.get(f"{base}/finalized-head", timeout=30)
        a.to_block = int(r.json()["number"])

    resume, mode = a.from_block, "w"
    if os.path.exists(a.out) and os.path.getsize(a.out) > 100:
        with open(a.out, "rb") as fh:
            try:
                fh.seek(-4096, os.SEEK_END)
            except OSError:
                fh.seek(0)
            tail = fh.read().decode(errors="ignore").strip().splitlines()
            last = tail[-1].split(",")
            if last and last[0].isdigit():
                resume, mode = int(last[0]) + 1, "a"
                print(f"[resume] 从块 {resume} 续拉", flush=True)

    f = open(a.out, mode, newline="")
    w = csv.writer(f)
    if mode == "w":
        w.writerow(["block", "ts", "tx", "log_index", "from", "to", "value_raw", "block_hash"])

    import datetime as dt
    total, cur, t0, errs = 0, resume, time.time(), 0
    sess = requests.Session()
    while cur <= a.to_block:
        body = {"type": "evm", "fromBlock": cur, "toBlock": a.to_block,
                "fields": {"block": {"number": True, "timestamp": True, "hash": True},
                           "log": {"logIndex": True, "transactionHash": True,
                                   "topics": True, "data": True}},
                "logs": [{"address": [token], "topic0": [TRANSFER]}]}
        try:
            r = sess.post(f"{base}/stream", json=body, timeout=180)
        except Exception as e:
            errs += 1
            print(f"[exc] {str(e)[:100]}", flush=True)
            time.sleep(min(2 * errs, 60))
            continue
        if r.status_code == 429:
            time.sleep(5)
            continue
        if r.status_code != 200:
            errs += 1
            print(f"[http {r.status_code}] {r.text[:120]}", flush=True)
            time.sleep(min(2 * errs, 60))
            continue
        errs = 0
        last_block, n = cur, 0
        for line in r.text.splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            h = d.get("header", {})
            bn = int(h["number"])
            last_block = max(last_block, bn)
            ts = h.get("timestamp")
            iso = dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S") if ts else ""
            bh = h.get("hash") or ""
            for lg in d.get("logs", []):
                tp = lg.get("topics") or []
                frm = "0x" + tp[1][-40:].lower() if len(tp) > 1 else ""
                to = "0x" + tp[2][-40:].lower() if len(tp) > 2 else ""
                data = lg.get("data") or "0x0"
                val = int(data, 16) if data not in ("0x", "") else 0
                w.writerow([bn, iso, lg["transactionHash"], int(lg["logIndex"]),
                            frm, to, val, bh])
                n += 1
        total += n
        f.flush()
        if total and total % 20000 < n:
            el = time.time() - t0
            print(f"[prog] +{n} total {total} block {last_block}/{a.to_block} "
                  f"{total/el:.0f}/s {el:.0f}s", flush=True)
        if last_block >= a.to_block:
            break
        cur = last_block + 1
        time.sleep(a.sleep)
    f.close()
    print(f"[COMPLETE] {total} rows -> {a.out}, [{resume},{a.to_block}] "
          f"{time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
