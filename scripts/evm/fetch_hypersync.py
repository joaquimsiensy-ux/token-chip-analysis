#!/usr/bin/env python3
"""envio HyperSync 全量/补拉 ERC20 转账事件,输出 CSV 格式与 fetch_alchemy.py 的 transfers_full.csv 一致。
来源：SIREN(BSC) 分析会话实战产物, 2026-07。

参数读取方式（跑前必看）：
  命令行传参：python3 fetch_hypersync.py <api_token> <from_block>
    - api_token：envio HyperSync 的 Bearer token（从 ~/.claude/api-keys.md 登记文件取用，不写死进 skill 目录）
    - from_block：起始区块号（全量从 0 或合约部署块起；补缺口从缺口起始块起）
  硬编码常量（跑前按标的改脚本顶部）：
    - D          输出目录（原值为 SIREN 会话 scratchpad 路径，必改）
    - TOKEN_ADDR 目标代币合约地址（必改）
    - url        端点 https://bsc.hypersync.xyz/query（换链改子域）
自动按 next_block 游标翻页直到 archive_height，无需断点续传逻辑（够快，一般一次跑完）。
"""
import requests, json, csv, os, sys, time, datetime

D = "/private/tmp/claude-502/-Users-uravvv-Desktop-----fable----/02251dc4-e11a-419c-b617-7991c8cb72f2/scratchpad/siren/data"
TOKEN_ADDR = "0x997a58129890bbda032231a52ed1ddc845fc18e1"
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
OUT = os.path.join(D, "transfers_gap.csv")

def main(api_token, from_block):
    url = "https://bsc.hypersync.xyz/query"
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    f = open(OUT, "w", newline="")
    w = csv.writer(f)
    w.writerow(["block", "ts", "tx", "from", "to", "value_raw", "uniqueId"])
    total = 0
    cur = from_block
    t0 = time.time()
    while True:
        q = {"from_block": cur,
             "logs": [{"address": [TOKEN_ADDR], "topics": [[TRANSFER]]}],
             "field_selection": {
                 "log": ["block_number", "log_index", "transaction_hash", "topic1", "topic2", "data"],
                 "block": ["number", "timestamp"]}}
        ok = False
        for attempt in range(10):
            try:
                r = requests.post(url, json=q, headers=headers, timeout=90)
                if r.status_code == 200:
                    j = r.json(); ok = True; break
                print(f"[http {r.status_code}] {r.text[:150]}", flush=True)
                time.sleep(3 * (attempt + 1))
            except Exception as e:
                print(f"[exc] {str(e)[:100]}", flush=True)
                time.sleep(3 * (attempt + 1))
        if not ok:
            print("[fatal] giving up", flush=True); sys.exit(2)
        bts = {}
        n = 0
        for batch in j.get("data", []):
            for b in batch.get("blocks", []):
                ts = b.get("timestamp")
                ts = int(ts, 16) if isinstance(ts, str) else int(ts)
                bts[int(b["number"])] = ts
            for lg in batch.get("logs", []):
                bn = int(lg["block_number"])
                ts = bts.get(bn)
                iso = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z") if ts else ""
                frm = "0x" + lg["topic1"][-40:]
                to = "0x" + lg["topic2"][-40:]
                data = lg.get("data") or "0x0"
                val = int(data, 16) if data not in ("0x", "") else 0
                li = int(lg["log_index"])
                w.writerow([bn, iso, lg["transaction_hash"], frm, to, val,
                            f"{lg['transaction_hash']}:log:{li}"])
                n += 1
        total += n
        nxt = j.get("next_block")
        ah = j.get("archive_height")
        print(f"[prog] +{n} total {total} next {nxt} height {ah} {time.time()-t0:.0f}s", flush=True)
        if not nxt or (ah and nxt >= ah):
            break
        cur = nxt
        time.sleep(0.15)
    f.close()
    print(f"[COMPLETE] {total} transfers, {time.time()-t0:.0f}s", flush=True)

if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))
