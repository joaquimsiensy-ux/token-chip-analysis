"""publicnode 大响应 504 时的分片全量扫描 v2:按 amount 字段(offset 64, u64 LE)低位字节递归分片。

关键洞察:零余额账户(amount=0)的 8 字节全为 0,全部堆在全零前缀片——递归下钻全零前缀,
8 字节全零终点片=纯零余额账户,直接跳过(分析只要非零余额)。
任何过大的子片(截断/超时)同样递归下钻,自适应热点。

用法: python3 scan_sharded.py <mint> [--smoke]
输出: data/holders_accounts.json / data/holders_owners.json(与 scan_token_accounts.py 兼容)
缓存: data/_shards2/shard_<hex前缀>.json 断点续跑。
"""
import base64, json, subprocess, sys, time
from pathlib import Path

RPC = "https://solana-rpc.publicnode.com"
ALPHA = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58encode(b: bytes) -> str:
    n = int.from_bytes(b, "big")
    s = ""
    while n:
        n, r = divmod(n, 58)
        s = ALPHA[r] + s
    for byte in b:
        if byte == 0:
            s = "1" + s
        else:
            break
    return s or "1"


def rpc_call(payload, timeout=100, retries=5):
    body = json.dumps(payload)
    for i in range(retries):
        p = subprocess.run(["curl", "-s", "-m", str(timeout), RPC,
                            "-H", "Content-Type: application/json", "-d", body],
                           capture_output=True, text=True)
        try:
            d = json.loads(p.stdout)
            if "result" in d:
                return d["result"]
            err = str(d.get("error", ""))[:100]
        except Exception:
            err = f"truncated/empty ({len(p.stdout)}B)"
        print(f"[warn] attempt {i+1}: {err}", file=sys.stderr, flush=True)
        time.sleep(2.5 * (i + 1))
    return None


def fetch_prefix(mint, prefix: bytes):
    """amount 低位前缀过滤取账户;返回 None=失败/过大。"""
    return rpc_call({"jsonrpc": "2.0", "id": 1, "method": "getProgramAccounts", "params": [
        "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
        {"encoding": "base64", "dataSlice": {"offset": 32, "length": 40},
         "filters": [{"dataSize": 165},
                     {"memcmp": {"offset": 0, "bytes": mint}},
                     {"memcmp": {"offset": 64, "bytes": b58encode(prefix)}}]}]},
        retries=2 if len(prefix) == 1 else 5)


def decode_rows(res):
    rows = []
    for it in res:
        raw = base64.b64decode(it["account"]["data"][0])
        owner = b58encode(raw[0:32])
        amount = int.from_bytes(raw[32:40], "little")
        if amount > 0:
            rows.append({"account": it["pubkey"], "owner": owner, "amount_raw": amount})
    return rows


def fetch_tree(mint, prefix: bytes, shards_dir: Path, stats: dict):
    """递归取该前缀下全部非零账户。全零 8 字节终点片跳过。"""
    if len(prefix) == 8:
        if all(b == 0 for b in prefix):
            stats["skipped_zero_leaf"] = stats.get("skipped_zero_leaf", 0) + 1
            return []
        # 8 字节定死仍失败=网络问题(该前缀几乎必为空);记账跳过,最后补扫
        print(f"[WARN] leaf fetch fail {prefix.hex()},记入 leaf_fail", flush=True)
        stats.setdefault("leaf_fail", []).append(prefix.hex())
        return []
    cache = shards_dir / f"shard_{prefix.hex()}.json"
    if cache.exists() and cache.stat().st_size > 2:
        return json.loads(cache.read_text())
    # 全零前缀不发请求直接下钻(必然包含海量零余额账户)
    if all(b == 0 for b in prefix) and len(prefix) < 8:
        res = None
    else:
        res = fetch_prefix(mint, prefix)
        time.sleep(0.25)
    if res is not None:
        rows = decode_rows(res)
    else:
        rows = []
        nxt = len(prefix)
        for b2 in range(256):
            child = prefix + bytes([b2])
            if all(x == 0 for x in child):
                # 纯零路径:继续递归(下一级会再下钻直到 8 字节全零跳过)
                rows.extend(fetch_tree(mint, child, shards_dir, stats))
            else:
                r2 = fetch_prefix(mint, child)
                time.sleep(0.22)
                if r2 is None:
                    rows.extend(fetch_tree(mint, child, shards_dir, stats))
                else:
                    rows.extend(decode_rows(r2))
        print(f"[split] prefix {prefix.hex()} -> {len(rows)} nonzero rows", flush=True)
    cache.write_text(json.dumps(rows))
    stats["done"] = stats.get("done", 0) + 1
    return rows


def main():
    mint = sys.argv[1]
    smoke = "--smoke" in sys.argv
    data = Path("data"); shards_dir = data / "_shards2"; shards_dir.mkdir(parents=True, exist_ok=True)

    sup = rpc_call({"jsonrpc": "2.0", "id": 1, "method": "getTokenSupply", "params": [mint]})
    supply_raw = int(sup["value"]["amount"]); decimals = sup["value"]["decimals"]
    print(f"supply={supply_raw} decimals={decimals}", flush=True)

    accounts = []
    t0 = time.time()
    stats = {}
    rng = range(0, 4) if smoke else range(256)
    for b in rng:
        accounts.extend(fetch_tree(mint, bytes([b]), shards_dir, stats))
        if b % 16 == 15 or smoke:
            print(f"shard {b+1}: cum nonzero accounts={len(accounts)} elapsed={time.time()-t0:.0f}s", flush=True)

    if smoke:
        print("SMOKE:", len(accounts), "nonzero accounts in shards", list(rng)); return

    owners = {}
    for a in accounts:
        owners[a["owner"]] = owners.get(a["owner"], 0) + a["amount_raw"]
    total = sum(owners.values())
    json.dump(accounts, open(data / "holders_accounts.json", "w"))
    json.dump(dict(sorted(owners.items(), key=lambda kv: -kv[1])), open(data / "holders_owners.json", "w"))
    print(f"nonzero token accounts={len(accounts)}  unique owners={len(owners)}", flush=True)
    print(f"对账: 扫描加总={total} vs getTokenSupply={supply_raw}  diff={supply_raw-total}", flush=True)
    ui = lambda v: v / (10 ** decimals)
    for o, v in sorted(owners.items(), key=lambda kv: -kv[1])[:20]:
        print(f"  top {o} {ui(v):>18,.0f} {v/supply_raw*100:6.2f}%", flush=True)


if __name__ == "__main__":
    main()
