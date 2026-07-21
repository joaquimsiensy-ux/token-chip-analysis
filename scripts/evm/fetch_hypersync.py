#!/usr/bin/env python3
"""envio HyperSync 全量/补拉 ERC20 转账事件，输出 CSV 与 fetch_alchemy.py 的 transfers_full.csv 同构。
来源：SIREN(BSC) 2026-07 实战产物；v3.5 参数化+断点续传（ASTEROID(ETH) 2026-07-18 收编）。

用法：python3 fetch_hypersync.py <api_token> <from_block> \
        --url https://eth.hypersync.xyz/query --token-addr 0x标的 --out data/transfers_full.csv
  - api_token：envio Bearer token（~/.claude/api-keys.md 取用，不写死进 skill）
  - from_block：起始块（部署块起；断点续传时自动改用已有 CSV 末行块）
  - --url 换链改子域（bsc/eth/base…）；--sleep 请求间隔，按账号档位选：
      免费层 0.5s（2026-07-18 起限流收紧后的实测稳值；ETH 低峰可试 0.25s）
      Starter 付费档 0.12s（≈500rpm 爆发上限；单进程即吃满，勿再多进程同 key 并发）
      （Starter=100rpm 基础+overage 爆发，超量按请求计费，token 设置里需开 overage ceiling 5x）
断点续传：--out 已存在且非空时自动从末行块续拉（重叠由下游按 uniqueId 去重）；
  老 7 列 CSV 续拉时自动维持 7 列，新文件起手为 8 列（尾列 block_hash，供防重组去重键）。
"""
import requests, json, csv, os, sys, time, datetime, argparse

TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("api_token")
    ap.add_argument("from_block", type=int)
    ap.add_argument("--url", default="https://bsc.hypersync.xyz/query")
    ap.add_argument("--token-addr", required=True)
    ap.add_argument("--out", default="data/transfers_full.csv")
    ap.add_argument("--sleep", type=float, default=0.25)
    a = ap.parse_args()
    headers = {"Authorization": f"Bearer {a.api_token}", "Content-Type": "application/json"}
    resume, mode, with_bh = a.from_block, "w", True
    if os.path.exists(a.out) and os.path.getsize(a.out) > 100:
        with open(a.out) as fh:
            with_bh = "block_hash" in fh.readline()  # 老 7 列文件续拉时维持老格式
        with open(a.out, "rb") as fh:
            try:
                fh.seek(-4096, os.SEEK_END)
            except OSError:
                fh.seek(0)
            tail = fh.read().decode(errors="ignore").strip().splitlines()
            last = tail[-1].split(",")
            if last and last[0].isdigit():
                resume, mode = int(last[0]), "a"
                print(f"[resume] 从已有 CSV 末行块 {resume} 续拉（block_hash 列: {with_bh}）", flush=True)
    f = open(a.out, mode, newline="")
    w = csv.writer(f)
    if mode == "w":
        w.writerow(["block", "ts", "tx", "from", "to", "value_raw", "uniqueId", "block_hash"])
    total, cur, t0, e429 = 0, resume, time.time(), 0
    while True:
        q = {"from_block": cur,
             "logs": [{"address": [a.token_addr], "topics": [[TRANSFER]]}],
             "field_selection": {
                 "log": ["block_number", "block_hash", "log_index", "transaction_hash", "topic1", "topic2", "data"],
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
                iso = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z") if ts else ""
                frm = "0x" + lg["topic1"][-40:]
                to = "0x" + lg["topic2"][-40:]
                data = lg.get("data") or "0x0"
                val = int(data, 16) if data not in ("0x", "") else 0
                li = int(lg["log_index"])
                row = [bn, iso, lg["transaction_hash"], frm, to, val,
                       f"{lg['transaction_hash']}:log:{li}"]
                if with_bh:
                    row.append(lg.get("block_hash") or "")
                w.writerow(row)
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
    print(f"[COMPLETE] {total} transfers this run, tip {ah}, 429s {e429}, {time.time()-t0:.0f}s", flush=True)

if __name__ == "__main__":
    main()
