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
from datetime import datetime, timedelta, timezone

BASE = "https://filfox.info/api/v1"
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = None
ADDR_DIR = None
OFFICIAL_DIR = None
WINDOW_DAYS = 180
PRICE_DAYS = WINDOW_DAYS
ANALYSIS_TIME_UTC = None
CUTOFF = None
MAX_RECENT_PAGES = 30  # 每地址窗口流水最多30页(3000笔),超出记 truncated
MAX_OFFICIAL_PAGES = 1000  # 官方地址全史硬上限；命中必须 truncated+BLOCK
THROTTLE = 0.1  # curl 每次新建 TLS 连接自带 ~0.3-0.5s 开销,实际约 2-3 req/s
UA = {"User-Agent": "Mozilla/5.0 (chip-analysis research script)"}


def configure_window(analysis_time, window_days=180):
    """Bind transfer, price and manifest coverage to one UTC analysis window."""
    global WINDOW_DAYS, PRICE_DAYS, ANALYSIS_TIME_UTC, CUTOFF
    if isinstance(window_days, bool) or not isinstance(window_days, int) or window_days <= 0:
        raise ValueError("window_days must be a positive integer")
    if isinstance(analysis_time, str):
        raw = analysis_time.strip().replace("Z", "+00:00")
        analysis_time = datetime.fromisoformat(raw)
    if not isinstance(analysis_time, datetime) or analysis_time.tzinfo is None:
        raise ValueError("analysis_time must be a timezone-aware ISO-8601 datetime")
    analysis_time = analysis_time.astimezone(timezone.utc)
    WINDOW_DAYS = window_days
    PRICE_DAYS = window_days
    ANALYSIS_TIME_UTC = analysis_time.replace(microsecond=0)
    CUTOFF = int((ANALYSIS_TIME_UTC - timedelta(days=window_days)).timestamp())
    return CUTOFF


configure_window(datetime.now(timezone.utc), WINDOW_DAYS)


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
    # count 参数已失效；pageSize=100 主抓与 pageSize=50 独立对照必须逐址一致。
    p = os.path.join(DATA, "richlist.json")

    def collect(page_size):
        out = []
        for page in range((n + page_size - 1) // page_size):
            d = get_json(f"{BASE}/rich-list?pageSize={page_size}&page={page}")
            if not isinstance(d, dict) or "_error" in d \
                    or not isinstance(d.get("richList"), list):
                raise RuntimeError(
                    f"rich-list pagination request failed: pageSize={page_size} page={page}")
            out.extend(d["richList"])
        return out[:n]

    primary = collect(100)
    reference = collect(50)
    primary_addresses = [str(x.get("address", "")) for x in primary]
    reference_addresses = [str(x.get("address", "")) for x in reference]
    errors = []
    if len(primary) != n or len(reference) != n:
        errors.append(f"count mismatch: 100={len(primary)} 50={len(reference)} expected={n}")
    if len(set(primary_addresses)) != len(primary_addresses) or "" in primary_addresses:
        errors.append("pageSize=100 result has empty/duplicate addresses")
    if primary_addresses != reference_addresses:
        first = next((i for i, pair in enumerate(zip(primary_addresses, reference_addresses))
                      if pair[0] != pair[1]), None)
        errors.append(f"pageSize=100/50 address order mismatch at index {first}")
    receipt = {"schema": "filecoin-richlist-pagination/v1",
               "status": "BLOCK" if errors else "PASS", "complete": not errors,
               "compared_count": n, "primary_page_size": 100,
               "reference_page_size": 50, "errors": errors}
    save(os.path.join(DATA, "richlist_pagination_receipt.json"), receipt)
    if errors:
        raise RuntimeError("rich-list pagination consistency failed: " + "; ".join(errors))
    save(p, primary)
    print(f"富豪榜 {len(primary)} 条完成(pageSize 100/50逐址一致)", flush=True)
    return primary

def fetch_address(addr, rank):
    adir = os.path.join(ADDR_DIR, addr)
    os.makedirs(adir, exist_ok=True)
    # 1) 详情
    pd = os.path.join(adir, "detail.json")
    if not done(pd):
        detail = get_json(f"{BASE}/address/{addr}")
        save(pd, detail)
    # 2) 与价格同源窗口的流水
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
        save(pr, {"scope": f"restricted-{WINDOW_DAYS}d-max3000", "totalCount": total,
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
    outputs = []
    for aid, d in found.items():
        if not d.get("tag"):
            continue
        po = os.path.join(OFFICIAL_DIR, f"{aid}_transfers.json")
        if done(po):
            try:
                cached = json.load(open(po, encoding="utf-8"))
                if cached.get("complete") is True and cached.get("truncated") is False:
                    outputs.append({"address": aid,
                                    "path": os.path.relpath(po, DATA),
                                    "sha256": sha256_file(po),
                                    "count": len(cached.get("transfers") or [])})
                    continue
            except Exception:
                pass
        transfers, seen = [], set()
        duplicate_count, total, pages = 0, None, 0
        truncated, complete_reason = False, None
        for page in range(MAX_OFFICIAL_PAGES):
            r = get_json(f"{BASE}/address/{aid}/transfers?pageSize=100&page={page}")
            if not r or "_error" in r:
                raise RuntimeError(f"official {aid} page {page} network/API failure")
            reported = r.get("totalCount")
            if isinstance(reported, bool) or not isinstance(reported, int) or reported < 0:
                raise RuntimeError(f"official {aid} page {page} totalCount invalid")
            total = reported if total is None else max(total, reported)
            batch = r.get("transfers", [])
            if not isinstance(batch, list):
                raise RuntimeError(f"official {aid} page {page} transfers is not a list")
            pages = page + 1
            for item in batch:
                key = json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                if key in seen:
                    duplicate_count += 1
                    continue
                seen.add(key)
                transfers.append(item)
            if len(transfers) >= total:
                complete_reason = "total_count_reached"
                break
            if not batch:
                truncated = True
                complete_reason = "empty_before_total_count"
                break
        else:
            truncated = True
            complete_reason = "official_page_cap"
        complete = not truncated and total is not None and len(transfers) >= total
        payload = {"scope": "official-address-full-history", "totalCount": total,
                   "complete": complete, "complete_reason": complete_reason,
                   "truncated": truncated, "pages_fetched": pages,
                   "duplicate_count": duplicate_count, "transfers": transfers}
        save(po, payload)
        if not complete:
            raise RuntimeError(
                f"official {aid} history incomplete: reason={complete_reason} "
                f"unique={len(transfers)} totalCount={total}")
        outputs.append({"address": aid, "path": os.path.relpath(po, DATA),
                        "sha256": sha256_file(po), "count": len(transfers)})
        print(f"官方地址 {aid} ({d['tag'].get('name')}) 流水 {len(transfers)} 笔", flush=True)
    receipt = {"schema": "filecoin-official-transfers/v1", "status": "PASS",
               "complete": True, "addresses": len(outputs), "outputs": outputs}
    save(os.path.join(DATA, "official_transfers_receipt.json"), receipt)
    return receipt

def fetch_price():
    p = os.path.join(DATA, f"price_{PRICE_DAYS}d.json")
    if not done(p):
        d = get_json("https://api.coingecko.com/api/v3/coins/filecoin/market_chart"
                     f"?vs_currency=usd&days={PRICE_DAYS}&interval=daily")
        save(p, d)
        print("价格序列完成", flush=True)


def write_smoke_receipt(n):
    pagination_path = os.path.join(DATA, "richlist_pagination_receipt.json")
    pagination = json.load(open(pagination_path, encoding="utf-8")) \
        if os.path.isfile(pagination_path) else {}
    if pagination.get("status") != "PASS" or pagination.get("complete") is not True:
        raise RuntimeError("smoke requires PASS richlist pagination receipt")
    receipt = {"schema": "filecoin-smoke/v1", "status": "SMOKE",
               "mode": "smoke/top-n", "top_n": n, "complete": False,
               "formal_release_eligible": False,
               "richlist_pagination_receipt": {
                   "path": "richlist_pagination_receipt.json",
                   "sha256": sha256_file(pagination_path)}}
    save(os.path.join(DATA, "smoke_receipt.json"), receipt)
    return receipt


def write_collection_manifest(n, official_receipt=None, transfers_receipt=None):
    if n != 200:
        raise RuntimeError("formal Filecoin collection manifest requires top_n == 200")
    if official_receipt is None or transfers_receipt is None:
        raise RuntimeError("formal Filecoin collection manifest requires both official receipts")
    manifest = {"schema": "filecoin-collection/v3", "status": "PASS",
                "mode": "restricted/top-200-windowed", "top_n": n,
                "analysis_time_utc": ANALYSIS_TIME_UTC.isoformat().replace("+00:00", "Z"),
                "window_days": WINDOW_DAYS, "window_start": CUTOFF,
                "price_days": PRICE_DAYS,
                "max_transfers_per_address": MAX_RECENT_PAGES * 100,
                "complete": True, "limitations": ["not full actor universe",
                                                     f"{WINDOW_DAYS}-day window",
                                                     "per-address page cap"],
                "substage_receipts": {}}
    pagination_path = os.path.join(DATA, "richlist_pagination_receipt.json")
    if not os.path.isfile(pagination_path):
        raise RuntimeError("formal manifest requires richlist pagination receipt")
    pagination = json.load(open(pagination_path, encoding="utf-8"))
    if pagination.get("status") != "PASS" or pagination.get("complete") is not True:
        raise RuntimeError("richlist pagination receipt is not PASS/complete")
    manifest["substage_receipts"]["richlist_pagination"] = {
        "path": "richlist_pagination_receipt.json", "sha256": sha256_file(pagination_path)}
    for key, receipt, filename in (
            ("official_scan", official_receipt, "official_scan_receipt.json"),
            ("official_transfers", transfers_receipt, "official_transfers_receipt.json")):
        if receipt.get("status") != "PASS" or receipt.get("complete") is not True:
            raise RuntimeError(f"{key} receipt is not PASS/complete")
        rp = os.path.join(DATA, filename)
        if not os.path.isfile(rp):
            raise RuntimeError(f"{key} receipt file missing: {filename}")
        manifest["substage_receipts"][key] = {
            "path": filename, "sha256": sha256_file(rp)}
    save(os.path.join(DATA, "collection_manifest.json"), manifest)
    return manifest

def main(argv=None):
    parser = argparse.ArgumentParser(description="Filecoin restricted collector")
    parser.add_argument("--data-dir", required=True,
                        help="案目录的数据目录（禁止默认写 skill 目录）")
    parser.add_argument("--smoke", type=int, metavar="N",
                        help="只抓富豪榜前 N 名")
    parser.add_argument("--analysis-time",
                        default=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                        help="分析时点 ISO-8601（默认当前 UTC；写入 manifest）")
    parser.add_argument("--window-days", type=int, default=180,
                        help="流水与价格共用回看天数（默认 180）")
    args = parser.parse_args(argv)
    try:
        configure_window(args.analysis_time, args.window_days)
    except ValueError as exc:
        parser.error(str(exc))
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
    if args.smoke is not None:
        receipt = write_smoke_receipt(n)
        print(f"smoke 采集完成(top_n={n}, formal=false),耗时 {time.time()-t0:.0f}s", flush=True)
        return receipt
    official_receipt = fetch_official_scan()
    transfers_receipt = fetch_official_transfers()
    manifest = write_collection_manifest(n, official_receipt, transfers_receipt)
    print(f"受限采集完成(mode={manifest['mode']}),耗时 {time.time()-t0:.0f}s", flush=True)

if __name__ == "__main__":
    main()
