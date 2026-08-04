#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Filecoin 筹码分析 - 阶段一数据抓取脚本
来源：FIL(Filecoin) 分析会话实战产物, 2026-07。
只做只读 GET 请求(Filfox / CoinGecko 免费 API),结果存本目录 data/ 下 JSON。
节流 ~3 req/s,带重试,断点续抓(已存在文件直接跳过)。
用法:
  python3 fetch_data.py --data-dir <案目录/data> --smoke 10
  python3 fetch_data.py --data-dir <案目录/data>
"""
import argparse, hashlib, json, os, subprocess, sys, time

BASE = "https://filfox.info/api/v1"
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = None
ADDR_DIR = None
OFFICIAL_DIR = None
CUTOFF = 1767225600  # 2026-01-01 00:00 UTC,近6个月窗口起点
MAX_RECENT_PAGES = 30  # 每地址近6个月流水最多30页(3000笔),超出记 truncated
THROTTLE = 0.1  # curl 每次新建 TLS 连接自带 ~0.3-0.5s 开销,实际约 2-3 req/s
UA = {"User-Agent": "Mozilla/5.0 (chip-analysis research script)"}


def configure_data_dir(data_dir):
    """注入本次案例数据目录；只更新配置，不写磁盘。"""
    global DATA, ADDR_DIR, OFFICIAL_DIR
    DATA = os.path.realpath(os.path.abspath(os.fspath(data_dir)))
    ADDR_DIR = os.path.join(DATA, "addr")
    OFFICIAL_DIR = os.path.join(DATA, "official")
    return DATA


def initialize_data_dirs():
    """进入正式执行后才创建输出目录。"""
    if not DATA or not ADDR_DIR or not OFFICIAL_DIR:
        raise RuntimeError("data directory is not configured; pass --data-dir")
    os.makedirs(ADDR_DIR, exist_ok=True)
    os.makedirs(OFFICIAL_DIR, exist_ok=True)

_last = [0.0]
def get_json(url, retries=5):
    # 本机 Python 缺 CA 证书,统一走系统 curl(用系统证书链)
    wait = time.time() - _last[0]
    if wait < THROTTLE:
        time.sleep(THROTTLE - wait)
    for i in range(retries):
        _last[0] = time.time()
        try:
            r = subprocess.run(
                ["curl", "-s", "--max-time", "30", "-w", "\n%{http_code}",
                 "-H", "User-Agent: " + UA["User-Agent"], url],
                capture_output=True, text=True, timeout=40)
            body, _, code = r.stdout.rpartition("\n")
            if code == "404":
                return None
            if code == "200" and body:
                return json.loads(body)
        except Exception:
            pass
        time.sleep(2 ** i + 1)
    print(f"  !! 放弃: {url}", flush=True)
    return {"_error": url}

def valid_file(path):
    """已存在且内容有效(非上次失败留下的坏缓存)"""
    if not os.path.exists(path):
        return False
    try:
        with open(path) as f:
            d = json.load(f)
    except Exception:
        return False
    if d is None or (isinstance(d, dict) and "_error" in d) or d == []:
        return False
    return True

def save(path, obj):
    if obj is None or (isinstance(obj, dict) and "_error" in obj):
        raise RuntimeError(f"refuse to save incomplete/error response: {path}")
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, path)

def done(path):
    return valid_file(path)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def fetch_overview():
    p = os.path.join(DATA, "overview.json")
    if not done(p):
        save(p, get_json(f"{BASE}/overview"))
        print("overview 完成", flush=True)

def fetch_richlist(n):
    # 注意:count 参数已失效(返回过滤后的 account 榜),必须用 pageSize(全量榜,含 miner/multisig)
    p = os.path.join(DATA, "richlist.json")
    if done(p):
        with open(p) as f:
            rl = json.load(f)
        addrs = [x["address"] for x in rl]
        if len(rl) >= n and len(set(addrs)) == len(addrs):
            return rl[:n]
    items, seen = [], set()
    for page in range((n + 99) // 100):
        d = get_json(f"{BASE}/rich-list?pageSize=100&page={page}")
        for x in d.get("richList", []):
            if x["address"] not in seen:
                seen.add(x["address"])
                items.append(x)
    assert len(items) >= n, f"富豪榜只拿到 {len(items)} 条"
    save(p, items)
    print(f"富豪榜 {len(items)} 条完成(唯一地址)", flush=True)
    return items[:n]

def fetch_address(addr, rank):
    adir = os.path.join(ADDR_DIR, addr)
    os.makedirs(adir, exist_ok=True)
    # 1) 详情
    pd = os.path.join(adir, "detail.json")
    if not done(pd):
        detail = get_json(f"{BASE}/address/{addr}")
        save(pd, detail)
    # 2) 近6个月流水
    pr = os.path.join(adir, "transfers_recent.json")
    if not done(pr):
        transfers, truncated, total, complete_reason = [], False, None, None
        for page in range(MAX_RECENT_PAGES):
            d = get_json(f"{BASE}/address/{addr}/transfers?pageSize=100&page={page}")
            if not d or "_error" in d:
                raise RuntimeError(f"address {addr} transfers page {page} network/API failure")
            total = d.get("totalCount", 0)
            batch = d.get("transfers", [])
            transfers.extend(batch)
            if not batch or batch[-1]["timestamp"] < CUTOFF:
                complete_reason = "empty_page" if not batch else "reached_window_cutoff"
                break
        else:
            truncated = True
            complete_reason = "restricted_page_cap"
        transfers = [t for t in transfers if t["timestamp"] >= CUTOFF]
        save(pr, {"scope": "restricted-6m-max3000", "totalCount": total,
                  "complete": True, "complete_reason": complete_reason,
                  "truncated": truncated, "transfers": transfers})
    # 3) 最早流水(首笔资金来源)
    pe = os.path.join(adir, "transfers_earliest.json")
    if not done(pe):
        with open(pr) as f:
            total = json.load(f).get("totalCount") or 0
        earliest = []
        if total:
            last_page = max(0, (total - 1) // 100)
            for page in {last_page, max(0, last_page - 1)}:
                d = get_json(f"{BASE}/address/{addr}/transfers?pageSize=100&page={page}")
                if not d or "_error" in d:
                    raise RuntimeError(f"address {addr} earliest page {page} network/API failure")
                earliest.extend(d.get("transfers", []))
        save(pe, {"complete": True, "pages": sorted({last_page, max(0, last_page - 1)})
                  if total else [], "transfers": earliest})
    print(f"[{rank}] {addr} 完成", flush=True)

def fetch_official_scan():
    """Scan f00-f0160 with four-bucket receipt and retry failed IDs on rerun."""
    p = os.path.join(DATA, "official_scan.json")
    receipt_path = os.path.join(DATA, "official_scan_receipt.json")
    progress_path = os.path.join(DATA, "official_scan_progress.json")
    requested = [f"f0{i}" for i in range(161)]

    # 只有 PASS receipt 与当前 official_scan 哈希一致才能短路；旧版孤立
    # official_scan.json 不再被当成完成证据。
    if done(p) and done(receipt_path):
        try:
            receipt = json.load(open(receipt_path, encoding="utf-8"))
            if (receipt.get("schema") == "filecoin-official-scan/v1"
                    and receipt.get("status") == "PASS"
                    and receipt.get("requested") == requested
                    and receipt.get("output", {}).get("sha256") == sha256_file(p)):
                return receipt
        except Exception:
            pass

    progress = {"schema": "filecoin-official-scan-progress/v1",
                "requested": requested, "succeeded": {}, "not_found": [], "failed": []}
    if done(progress_path):
        try:
            previous = json.load(open(progress_path, encoding="utf-8"))
            if (previous.get("schema") == progress["schema"]
                    and previous.get("requested") == requested
                    and isinstance(previous.get("succeeded"), dict)
                    and isinstance(previous.get("not_found"), list)):
                progress = previous
        except Exception:
            pass
    completed = set(progress["succeeded"]) | set(progress["not_found"])
    failed = []
    for aid in requested:
        if aid in completed:
            continue
        d = get_json(f"{BASE}/address/{aid}")
        if d is None:
            progress["not_found"].append(aid)
        elif isinstance(d, dict) and "_error" in d:
            failed.append({"address": aid, "error": d.get("_error")})
        elif isinstance(d, dict):
            progress["succeeded"][aid] = d
        else:
            failed.append({"address": aid, "error": "unexpected response type"})
    progress["not_found"] = sorted(set(progress["not_found"]))
    progress["failed"] = failed
    save(progress_path, progress)

    receipt = {"schema": "filecoin-official-scan/v1", "requested": requested,
               "succeeded": sorted(progress["succeeded"]),
               "not_found": progress["not_found"], "failed": failed,
               "counts": {"requested": len(requested),
                          "succeeded": len(progress["succeeded"]),
                          "not_found": len(progress["not_found"]),
                          "failed": len(failed)}}
    if failed:
        receipt.update({"status": "BLOCK", "complete": False,
                        "retry_addresses": [x["address"] for x in failed]})
        save(receipt_path, receipt)
        raise RuntimeError(f"official scan {len(failed)} addresses failed; retry list preserved")

    found = {aid: d for aid, d in progress["succeeded"].items()
             if d.get("tag") or d.get("actor") == "multisig"}
    save(p, found)
    receipt.update({"status": "PASS", "complete": True, "retry_addresses": [],
                    "output": {"path": "official_scan.json", "sha256": sha256_file(p)}})
    save(receipt_path, receipt)
    print(f"官方扫描完成,命中 {len(found)} 个", flush=True)
    return receipt

def fetch_official_transfers():
    """对官方扫描命中的、带标签的地址拉全历史流水(通常笔数很少)"""
    p = os.path.join(DATA, "official_scan.json")
    if not done(p):
        return
    with open(p) as f:
        found = json.load(f)
    for aid, d in found.items():
        if not d.get("tag"):
            continue
        po = os.path.join(OFFICIAL_DIR, f"{aid}_transfers.json")
        if done(po):
            continue
        transfers = []
        for page in range(50):
            r = get_json(f"{BASE}/address/{aid}/transfers?pageSize=100&page={page}")
            if not r or "_error" in r:
                raise RuntimeError(f"official {aid} page {page} network/API failure")
            batch = r.get("transfers", [])
            transfers.extend(batch)
            if len(batch) < 100:
                break
        save(po, {"complete": True, "transfers": transfers})
        print(f"官方地址 {aid} ({d['tag'].get('name')}) 流水 {len(transfers)} 笔", flush=True)

def fetch_price():
    p = os.path.join(DATA, "price_180d.json")
    if not done(p):
        d = get_json("https://api.coingecko.com/api/v3/coins/filecoin/market_chart?vs_currency=usd&days=180&interval=daily")
        save(p, d)
        print("价格序列完成", flush=True)


def write_collection_manifest(n, official_receipt=None):
    manifest = {"schema": "filecoin-collection/v3", "status": "PASS",
                "mode": "restricted/top-200-windowed", "top_n": n,
                "window_start": CUTOFF, "max_transfers_per_address": MAX_RECENT_PAGES * 100,
                "complete": True, "limitations": ["not full actor universe", "six-month window",
                                                     "per-address page cap"],
                "substage_receipts": {}}
    if official_receipt is not None:
        if official_receipt.get("status") != "PASS" or not official_receipt.get("complete"):
            raise RuntimeError("official scan receipt is not PASS/complete")
        rp = os.path.join(DATA, "official_scan_receipt.json")
        manifest["substage_receipts"]["official_scan"] = {
            "path": "official_scan_receipt.json", "sha256": sha256_file(rp)}
    save(os.path.join(DATA, "collection_manifest.json"), manifest)
    return manifest

def main(argv=None):
    parser = argparse.ArgumentParser(description="Filecoin restricted collector")
    parser.add_argument("--data-dir", required=True,
                        help="案目录的数据目录（禁止默认写 skill 目录）")
    parser.add_argument("--smoke", type=int, metavar="N",
                        help="只抓富豪榜前 N 名")
    args = parser.parse_args(argv)
    configure_data_dir(args.data_dir)
    initialize_data_dirs()
    n = args.smoke if args.smoke is not None else 200
    if n <= 0 or n > 200:
        parser.error("--smoke N 必须在 1..200")
    t0 = time.time()
    fetch_overview()
    fetch_price()
    rl = fetch_richlist(200)[:n]
    for idx, item in enumerate(rl):
        fetch_address(item["address"], idx + 1)
    official_receipt = None
    if n >= 200 or args.smoke is None:
        official_receipt = fetch_official_scan()
        fetch_official_transfers()
    manifest = write_collection_manifest(n, official_receipt)
    print(f"受限采集完成(mode={manifest['mode']}),耗时 {time.time()-t0:.0f}s", flush=True)

if __name__ == "__main__":
    main()
