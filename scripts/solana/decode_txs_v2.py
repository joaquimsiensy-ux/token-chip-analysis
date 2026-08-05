#!/usr/bin/env python3
"""溯源解码 v2——JSON-RPC 批量 + 全局签名去重缓存 + 端点可换(Helius 就位即切)。

来源:Solana 采集加速工程 2026-07-21(@CX 交叉复核方案 2"三板斧")。v1(decode_txs.py)保留。
相对 v1:
  1. getTransaction 改 JSON-RPC batch(公共 mainnet-beta 默认 8 笔/POST)——单笔串行 0.75s 间隔≈1.3 笔/s,
     批量后同样限速礼貌下 10-20 倍
  2. 跨地址共享 sig 结果缓存(--cache-dir,按 sig 前 2 字符分 256 片)——庄家关联地址间
     重复交易极多,第二个地址起大量命中零请求
  3. --rpc 可换端点:默认 api.mainnet-beta(须 --proxy);Helius 免费层免代理但不支持
     JSON-RPC batch，须改用 --workers 单笔并发并遵守账号级 10 RPS

用法: python3 decode_txs_v2.py --sigs <jsonl> --out <jsonl> [--mint M] [--pool P]
      [--batch 8] [--interval 0.8] [--proxy http://127.0.0.1:7897]
      [--cache-dir data/txcache] [--rpc <url>]
输出行与 v1 逐字段一致({sig, slot, ts, deltas} / {sig, decode_fail});断点续传兼容 v1 输出。
"""
import argparse, hashlib, json, os, sys, time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import requests

DEF_RPC = "https://api.mainnet-beta.solana.com"
OUTPUT_SCHEMA = "solana-tx-decode-output-v2"
RECEIPT_SCHEMA = "solana-tx-decode-receipt/v1"


def log(msg):
    print(f"[decode2] {msg}", file=sys.stderr, flush=True)


class SigCache:
    """Identity-bound signature cache; failed decodes are never cached."""
    SCHEMA = "solana-tx-decode-cache-v2"

    def __init__(self, root, mint, pool, rpc, chain_id="solana-mainnet"):
        self.root = Path(root) if root else None
        self.mem = {}
        if self.root:
            identity = {"schema": self.SCHEMA, "chain_id": chain_id, "mint": mint,
                        "pool": pool or "", "rpc": rpc}
            digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
            self.root = self.root / digest
            self.root.mkdir(parents=True, exist_ok=True)
            meta = self.root / "meta.json"
            if meta.exists() and json.loads(meta.read_text()) != identity:
                raise SystemExit("[fail-closed] decode cache identity mismatch")
            meta.write_text(json.dumps(identity, indent=2, sort_keys=True))
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


def _amount(tb):
    ui = tb.get("uiTokenAmount") or {}
    raw = ui.get("amount")
    decimals = ui.get("decimals")
    if not isinstance(raw, str) or not raw.isdigit() or not isinstance(decimals, int):
        raise ValueError("token balance missing exact raw amount/decimals")
    return int(raw), decimals


def _display(raw, decimals):
    return format(Decimal(raw).scaleb(-decimals), "f")


def decode_result(sig, res, mint, pool):
    """Decode owner deltas using raw integers; UI fields are exact strings only."""
    meta = res.get("meta") or {}
    pre, post = {}, {}
    decimals_seen = set()
    for tb in (meta.get("preTokenBalances") or []):
        if tb.get("mint") != mint:
            continue
        o = tb.get("owner")
        if not o:
            continue
        amt, decimals = _amount(tb)
        decimals_seen.add(decimals)
        pre[o] = pre.get(o, 0) + amt
    for tb in (meta.get("postTokenBalances") or []):
        if tb.get("mint") != mint:
            continue
        o = tb.get("owner")
        if not o:
            continue
        amt, decimals = _amount(tb)
        decimals_seen.add(decimals)
        post[o] = post.get(o, 0) + amt
    if len(decimals_seen) > 1:
        raise ValueError(f"inconsistent decimals for mint {mint}: {sorted(decimals_seen)}")
    decimals = next(iter(decimals_seen), 0)
    deltas_raw = {}
    for o in set(pre) | set(post):
        dl = post.get(o, 0) - pre.get(o, 0)
        if dl:
            deltas_raw[o] = dl
    row = {"sig": sig, "slot": res.get("slot"), "ts": res.get("blockTime"),
           "mint": mint, "decimals": decimals, "deltas_raw": deltas_raw,
           "deltas": {o: _display(v, decimals) for o, v in deltas_raw.items()}}
    if pool and pool in post:
        row["pool_balance_raw"] = post[pool]
        row["pool_balance"] = _display(post[pool], decimals)
    return row


def completed_sigs(outp, mint):
    done = set()
    if Path(outp).exists():
        for line in open(outp):
            try:
                row = json.loads(line)
                if not row.get("decode_fail") and row.get("mint", mint) == mint:
                    done.add(row["sig"])
            except Exception:
                pass
    return done


def output_identity(mint, pool, rpc):
    return {"schema": OUTPUT_SCHEMA, "chain_id": "solana-mainnet",
            "mint": mint, "pool": pool or "", "rpc": rpc}


def _atomic_json(path, obj):
    path = Path(path)
    tmp = path.with_name("." + path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def prepare_output(outp, mint, pool, rpc):
    """Bind append-only output to one mint/pool/RPC identity and return completed sigs."""
    outp = Path(outp)
    identity = output_identity(mint, pool, rpc)
    meta = Path(str(outp) + ".meta.json")
    if outp.exists() and outp.stat().st_size:
        try:
            existing = json.loads(meta.read_text())
        except Exception:
            raise SystemExit("[fail-closed] existing decode output has no readable identity meta")
        if existing != identity:
            raise SystemExit("[fail-closed] existing output is not bound to this mint/pool/rpc; "
                             "use a new --out path")
    else:
        outp.parent.mkdir(parents=True, exist_ok=True)
        _atomic_json(meta, identity)
    return completed_sigs(outp, mint)


def finalize_decode(outp, requested_sigs, mint, pool, rpc):
    """Write a complete receipt and return nonzero while any requested sig is unresolved."""
    outp = Path(outp)
    latest = {}
    if outp.exists():
        with outp.open(encoding="utf-8") as f:
            for line in f:
                try:
                    row = json.loads(line)
                    sig = row.get("sig")
                    if sig:
                        latest[sig] = row
                except Exception:
                    continue
    requested = list(dict.fromkeys(requested_sigs))
    failed = [s for s in requested if s not in latest or latest[s].get("decode_fail")
              or latest[s].get("mint", mint) != mint]
    succeeded = [s for s in requested if s not in set(failed)]
    failed_digest = hashlib.sha256("\n".join(sorted(failed)).encode()).hexdigest()
    output_hash = hashlib.sha256(outp.read_bytes()).hexdigest() if outp.exists() else None
    receipt = {"schema": RECEIPT_SCHEMA,
               "status": "PASS" if not failed else "BLOCK",
               "exit_code": 0 if not failed else 3,
               "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "identity": output_identity(mint, pool, rpc),
               "input_signature_count": len(requested),
               "success_count": len(succeeded), "failure_count": len(failed),
               "failed_signatures": failed, "failed_signatures_sha256": failed_digest,
               "output": {"path": str(outp),
                          "size": outp.stat().st_size if outp.exists() else 0,
                          "sha256": output_hash}}
    _atomic_json(str(outp) + ".receipt.json", receipt)
    return receipt["exit_code"]


def main():
    ap = argparse.ArgumentParser(description="Solana 溯源解码 v2(批量+去重缓存)")
    ap.add_argument("--sigs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mint", default=None)
    ap.add_argument("--pool", default=None)
    ap.add_argument("--batch", type=int, default=8,
                    help="每 POST 笔数(mainnet-beta 默认8；Helius免费层不支持batch，须用--workers单笔并发)")
    ap.add_argument("--interval", type=float, default=0.8, help="批间隔秒")
    ap.add_argument("--proxy", default=None)
    ap.add_argument("--cache-dir", default="data/txcache", help="跨地址共享缓存;空串禁用")
    ap.add_argument("--rpc", default=DEF_RPC)
    ap.add_argument("--workers", type=int, default=1,
                    help="单笔并发线程数(>1 时忽略 batch;Helius 免费层建议 6+interval 0.12=贴 10RPS)")
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
    done = prepare_output(outp, mint, a.pool, a.rpc)
    cache = SigCache(a.cache_dir or None, mint, a.pool, a.rpc)
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

    # 单笔并发路径(--workers>1):多线程各自 Session 并发发单笔,主线程节流提交+统一落盘。
    # 适用 Helius 这类"不支持 batch 但 RPS 富余"的端点(免费层 10 RPS,串行只吃到 1.6/s)。
    if a.workers > 1:
        import threading as _th
        from concurrent.futures import ThreadPoolExecutor as _TPE
        tl = _th.local()

        def one(sig):
            if not hasattr(tl, "s"):
                tl.s = requests.Session()
                if a.proxy:
                    tl.s.proxies = {"http": a.proxy, "https": a.proxy}
            b = {"jsonrpc": "2.0", "id": 0, "method": "getTransaction",
                 "params": [sig, {"encoding": "jsonParsed",
                                  "maxSupportedTransactionVersion": 0,
                                  "commitment": "confirmed"}]}
            for attempt in range(5):
                try:
                    r = tl.s.post(a.rpc, json=b, timeout=45)
                    if r.status_code == 429:
                        time.sleep(4 * (attempt + 1))
                        continue
                    d = r.json()
                    if (d.get("error") or {}).get("code") == 429:
                        time.sleep(4 * (attempt + 1))
                        continue
                    return sig, d.get("result")
                except Exception:
                    time.sleep(2 * (attempt + 1))
            return sig, None

        with _TPE(a.workers) as ex:
            futs = []
            for sig in todo:
                futs.append(ex.submit(one, sig))
                time.sleep(a.interval)          # 节流提交=全局速率上限 1/interval
            for k, fut in enumerate(futs):
                sig, res = fut.result()
                if res is None:
                    n_fail += 1
                    f.write(json.dumps({"sig": sig, "decode_fail": True}) + "\n")
                else:
                    row = decode_result(sig, res, mint, a.pool)
                    f.write(json.dumps(row) + "\n")
                    cache.put(row)
                    n_ok += 1
                if (k + 1) % 100 == 0:
                    f.flush()
                    rate = (k + 1) / (time.time() - t0)
                    log(f"{k+1}/{len(todo)} ok={n_ok} fail={n_fail} rate={rate:.1f}/s")
        f.close()
        log(f"DONE ok={n_ok} fail={n_fail} cache_hit={hit} 耗时{(time.time()-t0)/60:.1f}min")
        return finalize_decode(outp, sigs, mint, a.pool, a.rpc)

    i = 0
    while i < len(todo):
        chunk = todo[i:i + a.batch]
        body = [{"jsonrpc": "2.0", "id": k, "method": "getTransaction",
                 "params": [sig, {"encoding": "jsonParsed",
                                  "maxSupportedTransactionVersion": 0,
                                  "commitment": "confirmed"}]}
                for k, sig in enumerate(chunk)]
        if len(chunk) == 1:
            body = body[0]   # 单笔发裸对象——部分端点把单元素数组也当 batch 拒(Helius 免费层实测)
        results = None
        for attempt in range(5):
            try:
                r = sess.post(a.rpc, json=body, timeout=60)
                if r.status_code == 429:
                    time.sleep(6 * (attempt + 1))
                    continue
                d = r.json()
                if isinstance(d, dict) and "id" in d:
                    d = [d]          # 单对象响应 → 统一列表处理
                if isinstance(d, list):
                    results = d
                    break
                if isinstance(d, dict) and (d.get("error") or {}).get("code") == 429:
                    time.sleep(6 * (attempt + 1))
                    continue
                # 无 id 的顶层错误对象 = batch 被端点拒绝(如 Helius 免费层 -32403)→ 降级单笔
                if isinstance(d, dict):
                    log(f"端点拒绝 batch({json.dumps(d.get('error'))[:80]})——降级单笔模式")
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
    return finalize_decode(outp, sigs, mint, a.pool, a.rpc)


if __name__ == "__main__":
    sys.exit(main())
