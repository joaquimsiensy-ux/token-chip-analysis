#!/usr/bin/env python3
"""溯源解码 v2——JSON-RPC 批量 + 全局签名去重缓存 + 端点可换(Helius 就位即切)。

来源:Solana 采集加速工程 2026-07-21(@CX 交叉复核方案 2"三板斧")。v1(decode_txs.py)保留。
相对 v1:
  1. getTransaction 改 JSON-RPC batch(默认 20 笔/POST)——单笔串行 0.75s 间隔≈1.3 笔/s,
     批量后同样限速礼貌下 10-20 倍
  2. 跨地址共享 sig 结果缓存(--cache-dir,按 sig 前 2 字符分 256 片)——庄家关联地址间
     重复交易极多,第二个地址起大量命中零请求
  3. --rpc 可换端点:默认 api.mainnet-beta(须 --proxy);Helius key 就位后
     --rpc https://mainnet.helius-rpc.com/?api-key=<key> 免代理且 50 RPS

用法: python3 decode_txs_v2.py --sigs <jsonl> --out <jsonl> [--mint M] [--pool P]
      [--batch 20] [--interval 0.8] [--proxy http://127.0.0.1:7897]
      [--cache-dir data/txcache] [--rpc <url>]
输出行与 v1 逐字段一致({sig, slot, ts, deltas} / {sig, decode_fail});断点续传兼容 v1 输出。
"""
import argparse, json, sys, time
from pathlib import Path
import requests

DEF_RPC = "https://api.mainnet-beta.solana.com"


def log(msg):
    print(f"[decode2] {msg}", file=sys.stderr, flush=True)


class SigCache:
    """按 sig 前 2 字符分片的追加式缓存:行 = 完整输出行(含 decode_fail 行)。"""
    def __init__(self, root):
        self.root = Path(root) if root else None
        self.mem = {}
        if self.root:
            self.root.mkdir(parents=True, exist_ok=True)
            for fp in self.root.glob("*.jsonl"):
                for ln in open(fp):
                    try:
                        d = json.loads(ln)
                        if not d.get("decode_fail"):     # 失败行不缓存——给重试机会
                            self.mem[d["sig"]] = d
                    except Exception:
                        continue

    def get(self, sig):
        return self.mem.get(sig)

    def put(self, row):
        if not self.root or row.get("decode_fail"):
            return
        self.mem[row["sig"]] = row
        fp = self.root / f"{row['sig'][:2]}.jsonl"
        with open(fp, "a") as f:
            f.write(json.dumps(row) + "\n")


def decode_result(sig, res, mint, pool):
    """getTransaction result → 输出行(与 v1 逐字段同构:uiAmount owner 净额)。"""
    meta = res.get("meta") or {}
    pre, post = {}, {}
    for tb in (meta.get("preTokenBalances") or []):
        if tb.get("mint") != mint:
            continue
        o = tb.get("owner")
        amt = float((tb.get("uiTokenAmount") or {}).get("uiAmount") or 0)
        pre[o] = pre.get(o, 0.0) + amt
    for tb in (meta.get("postTokenBalances") or []):
        if tb.get("mint") != mint:
            continue
        o = tb.get("owner")
        amt = float((tb.get("uiTokenAmount") or {}).get("uiAmount") or 0)
        post[o] = post.get(o, 0.0) + amt
    deltas = {}
    for o in set(pre) | set(post):
        dl = post.get(o, 0.0) - pre.get(o, 0.0)
        if abs(dl) > 1e-9:
            deltas[o] = round(dl, 6)
    row = {"sig": sig, "slot": res.get("slot"), "ts": res.get("blockTime"), "deltas": deltas}
    if pool and pool in post:
        row["pool_balance"] = round(post[pool], 6)
    return row


def main():
    ap = argparse.ArgumentParser(description="Solana 溯源解码 v2(批量+去重缓存)")
    ap.add_argument("--sigs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mint", default=None)
    ap.add_argument("--pool", default=None)
    ap.add_argument("--batch", type=int, default=8,
                    help="每 POST 笔数(mainnet-beta 实测方法级限流约 10 笔/窗,batch>10 多出部分吃 429;Helius 可调大)")
    ap.add_argument("--interval", type=float, default=0.8, help="批间隔秒")
    ap.add_argument("--proxy", default=None)
    ap.add_argument("--cache-dir", default="data/txcache", help="跨地址共享缓存;空串禁用")
    ap.add_argument("--rpc", default=DEF_RPC)
    a = ap.parse_args()

    mint = a.mint
    if not mint:
        cfg = Path("config.json")
        if cfg.exists():
            mint = json.loads(cfg.read_text()).get("mint")
    if not mint:
        log("no mint")
        sys.exit(1)

    sess = requests.Session()
    if a.proxy:
        sess.proxies = {"http": a.proxy, "https": a.proxy}

    # 输入:jsonl({signature, err})或裸签名行;失败交易剔除;保序去重
    sigs, seen = [], set()
    for line in open(a.sigs):
        line = line.strip()
        if not line:
            continue
        if line.startswith("{"):
            d = json.loads(line)
            if d.get("err"):
                continue
            s = d.get("signature")
        else:
            s = line
        if s and s not in seen:
            seen.add(s)
            sigs.append(s)

    outp = Path(a.out)
    done = set()
    if outp.exists():
        for line in open(outp):
            try:
                done.add(json.loads(line)["sig"])
            except Exception:
                pass
    cache = SigCache(a.cache_dir or None)
    f = open(outp, "a")
    todo = []
    hit = 0
    for s in sigs:
        if s in done:
            continue
        c = cache.get(s)
        if c is not None:
            f.write(json.dumps(c) + "\n")   # 缓存命中直接落盘,零请求
            hit += 1
        else:
            todo.append(s)
    log(f"total={len(sigs)} done={len(done)} cache_hit={hit} todo={len(todo)}")

    t0, n_ok, n_fail = time.time(), 0, 0
    retry_cnt = {}
    i = 0
    while i < len(todo):
        chunk = todo[i:i + a.batch]
        body = [{"jsonrpc": "2.0", "id": k, "method": "getTransaction",
                 "params": [sig, {"encoding": "jsonParsed",
                                  "maxSupportedTransactionVersion": 0,
                                  "commitment": "confirmed"}]}
                for k, sig in enumerate(chunk)]
        results = None
        for attempt in range(5):
            try:
                r = sess.post(a.rpc, json=body, timeout=60)
                if r.status_code == 429:
                    time.sleep(6 * (attempt + 1))
                    continue
                d = r.json()
                if isinstance(d, list):
                    results = d
                    break
                if isinstance(d, dict) and (d.get("error") or {}).get("code") == 429:
                    time.sleep(6 * (attempt + 1))
                    continue
                # 端点不支持 batch(返回单对象错误)→ 降级单笔模式
                if isinstance(d, dict):
                    log("端点疑似不支持 batch,降级为单笔(batch=1)")
                    a.batch = 1
                    break
            except Exception:
                time.sleep(2.5 * (attempt + 1))
        if results is None and a.batch == 1 and len(chunk) > 1:
            continue        # 刚降级:同一窗口按 batch=1 重切
        by_id = {r.get("id"): r for r in results} if results else {}
        n_429 = 0
        for k, sig in enumerate(chunk):
            item = by_id.get(k) or {}
            err = item.get("error") or {}
            res = item.get("result")
            if err.get("code") == 429 or (res is None and not item):
                # 方法级限流(mainnet-beta 对 batch 子请求逐个限流,实测 20 笔只放行约 9 笔)
                # → 收回队列重试,绝不能记成 decode_fail
                n_429 += 1
                rc = retry_cnt.get(sig, 0)
                if rc < 4:
                    retry_cnt[sig] = rc + 1
                    todo.append(sig)
                else:
                    n_fail += 1
                    f.write(json.dumps({"sig": sig, "decode_fail": True}) + "\n")
            elif res is None:
                n_fail += 1
                f.write(json.dumps({"sig": sig, "decode_fail": True}) + "\n")
            else:
                row = decode_result(sig, res, mint, a.pool)
                f.write(json.dumps(row) + "\n")
                cache.put(row)
                n_ok += 1
        i += len(chunk)
        if n_429 > len(chunk) * 0.3:
            time.sleep(a.interval * 3)   # 429 密集:临时加倍退避,礼貌给节点喘息
        f.flush()
        if (i // max(a.batch, 1)) % 10 == 0:
            rate = i / (time.time() - t0)
            eta = (len(todo) - i) / rate / 60 if rate else -1
            log(f"{i}/{len(todo)} ok={n_ok} fail={n_fail} rate={rate:.1f}/s ETA={eta:.0f}min")
        time.sleep(a.interval)
    f.close()
    el = (time.time() - t0) / 60
    log(f"DONE ok={n_ok} fail={n_fail} cache_hit={hit} 耗时{el:.1f}min")


if __name__ == "__main__":
    main()
