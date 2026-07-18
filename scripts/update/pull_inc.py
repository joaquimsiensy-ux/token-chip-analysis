#!/usr/bin/env python3
"""U1 增量拉取（EVM/HyperSync）：从旧全量转账文件末行区块（含，重叠窗）拉到链头，
输出独立增量文件，并自动做重叠窗一致性校验。

来源：RAXOL(2026-07-14 pull_incremental) + VEX(2026-07-15 pull_inc) 两次 /token-update
实战合并参数化收编（v2.10.0）；与全量版 scripts/robinhood/pull_transfers.py 同构。

用法：cd 到工作目录（含 config.json，见 robinhood/config.example.json）后
  python3 pull_inc.py [--old data/transfers.jsonl.gz] [--out data/transfers_inc.jsonl.gz]
                      [--start-block N]
起点：默认读 --old 末行 block（含该块＝重叠窗，与 update-workflow U0 第 4 条一致）；
     旧文件缺失时必须显式给 --start-block（从 data_cutoff 换算并自行前移重叠段）。
断点续传：--out 已存在时从其末行 block+1 继续。
重叠窗校验：拉取完成后自动比对重叠块在新旧两文件中的行集合（键 tx,logi,from,to,amount），
     不一致=旧数据或链数据有洞，退出码 1（U1 硬步骤，不许跳过）。
输出行格式与全量文件一致：{block, ts, tx, logi, from, to, amount(str wei), txfrom, txto}
"""
import argparse, gzip, json, os, sys, time
import urllib.request
import ssl, certifi

SSL_CTX = ssl.create_default_context(cafile=certifi.where())
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def load_cfg():
    with open("config.json") as f:
        cfg = json.load(f)
    token = (cfg.get("token") or "").lower()
    hs = cfg.get("hypersync") or {}
    url = hs.get("url") or ""
    key = hs.get("key") or os.environ.get("HYPERSYNC_KEY") or ""
    if not token.startswith("0x") or len(token) != 42:
        sys.exit("config.json 的 token 缺失或不是合法 0x 地址")
    if not url:
        sys.exit("config.json 缺 hypersync.url（如 https://robinhood.hypersync.xyz/query）")
    if not key:
        sys.exit("HyperSync key 缺失：填 config.json hypersync.key 或设环境变量 HYPERSYNC_KEY"
                 "（key 见 ~/.claude/api-keys.md envio 条目）")
    return token, url, key


def last_block_of(path):
    last = None
    with gzip.open(path, "rt") as f:
        for line in f:
            if line.strip():
                last = line
    return json.loads(last)["block"] if last else None


def rows_at_block(path, block):
    """取某文件中指定块的全部行，返回可比对的键集合。"""
    keys = set()
    with gzip.open(path, "rt") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            if r["block"] == block:
                keys.add((r["tx"], r["logi"], r["from"], r["to"], r["amount"]))
            elif r["block"] > block and path.endswith("_inc.jsonl.gz"):
                break  # 增量文件按块升序，提前止损
    return keys


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
    for attempt in range(8):
        try:
            with urllib.request.urlopen(req, timeout=120, context=SSL_CTX) as r:
                return json.load(r)
        except Exception as e:
            wait = 2 * (attempt + 1)
            print(f"  重试 {attempt+1}: {e} (等 {wait}s)", flush=True)
            time.sleep(wait)
    raise RuntimeError("HyperSync 连续失败")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", default=os.path.join("data", "transfers.jsonl.gz"),
                    help="旧全量转账文件（取末行块作为起点，含重叠窗）")
    ap.add_argument("--out", default=os.path.join("data", "transfers_inc.jsonl.gz"))
    ap.add_argument("--start-block", type=int, default=None,
                    help="显式起点（旧文件缺失时用；自行保证含重叠段）")
    args = ap.parse_args()

    token, url, key = load_cfg()

    overlap_block = None
    if args.start_block is not None:
        start = args.start_block
        print(f"显式起点 {start}（未做重叠窗校验准备，交付前自行声明）", flush=True)
    else:
        if not os.path.exists(args.old):
            sys.exit(f"旧全量文件 {args.old} 不存在：给 --old 正确路径，或用 --start-block 显式起点")
        start = last_block_of(args.old)
        if start is None:
            sys.exit(f"{args.old} 为空文件")
        overlap_block = start
        print(f"起点=旧数据末行块 {start}（含，重叠窗）", flush=True)

    mode = "wb"
    if os.path.exists(args.out):
        lb = last_block_of(args.out)
        if lb is not None:
            start = lb + 1
            mode = "ab"
            print(f"断点续传：从 {start}", flush=True)

    n = 0
    with gzip.open(args.out, mode) as fout:
        fb = start
        while True:
            resp = query(url, key, token, fb)
            ah = resp.get("archive_height") or 0
            nb = resp.get("next_block")
            for batch in resp.get("data", []):
                ts_map = {b["number"]: int(b["timestamp"], 16) if isinstance(b["timestamp"], str) else b["timestamp"]
                          for b in batch.get("blocks", [])}
                txfrom, txto = {}, {}
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
                    fout.write((json.dumps(row) + "\n").encode())
                    n += 1
            if nb is None or nb <= fb:
                print(f"next_block 停滞于 {fb}，结束", flush=True)
                break
            fb = nb
            if nb >= ah:
                print(f"拉取完成：增量 {n} 条，停在 next_block={nb}, archive_height={ah}", flush=True)
                break
    print(f"本次写入 {n} 条 → {args.out}", flush=True)

    # ── 重叠窗一致性校验（U1 硬步骤）──
    if overlap_block is not None:
        old_keys = rows_at_block(args.old, overlap_block)
        new_keys = rows_at_block(args.out, overlap_block)
        if old_keys == new_keys:
            print(f"重叠窗校验 PASS：块 {overlap_block} 两侧 {len(old_keys)} 行完全一致")
        else:
            print(f"重叠窗校验 FAIL：块 {overlap_block} 旧 {len(old_keys)} 行 vs 新 {len(new_keys)} 行，"
                  f"差集 旧-新 {len(old_keys - new_keys)} / 新-旧 {len(new_keys - old_keys)}")
            print("＝旧数据末块不完整或链数据异常，回 U1 排查，不许带伤进 U2")
            sys.exit(1)


if __name__ == "__main__":
    main()
