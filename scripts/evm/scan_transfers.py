#!/usr/bin/env python3
"""通用 ERC20 全量 Transfer 扫链（多线程 + 毒段减半补扫 + 时间戳锚点）。
来源：OPN(BSC) 分析会话实战产物, 2026-07。

用法（在工作目录，需同目录 config.json）：
  python3 scan_transfers.py <chain> scan     # 主扫块（后台跑，断点续传）
  python3 scan_transfers.py <chain> fill     # 补扫失败段（1000块子段，失败自动减半至125）
  python3 scan_transfers.py <chain> anchors  # 块高→时间戳锚点（每100k块一个）
  python3 scan_transfers.py <chain> status   # 查看进度

产物：<chain>_part_*.csv（block,tx,li,from,to,value_raw）、<chain>_done.json、<chain>_ts_anchors.json
经验：全部 HTTP 走 subprocess+curl（macOS python urllib 常缺 SSL 证书链）；
     起点用块时间戳二分（eth_getCode 查历史需归档节点，公共节点会误报未部署）；
     扫完必须做余额对账（见 analyze_holdings.py），不对账的数据不可用。
"""
import json, time, os, sys, subprocess, threading, queue

TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
DIR = os.getcwd()
CFG = json.load(open(os.path.join(DIR, "config.json")))
TOKEN = CFG["token"].lower()

def raw_call(url, method, params, timeout=90):
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    r = subprocess.run(["curl", "-s", "-m", str(timeout), "-X", "POST", url,
                        "-H", "Content-Type: application/json", "-d", payload],
                       capture_output=True, text=True, timeout=timeout + 20)
    return json.loads(r.stdout)

def getlogs(url, frm, to, retries=4):
    for a in range(retries):
        try:
            d = raw_call(url, "eth_getLogs", [{"address": TOKEN, "topics": [TOPIC],
                                               "fromBlock": hex(frm), "toBlock": hex(to)}])
            if isinstance(d.get("result"), list):
                return d["result"]
            msg = str(d.get("error", {}))[:100]
            if "Too many" in msg or "rate" in msg.lower():
                time.sleep(10 * (a + 1)); continue
        except Exception:
            pass
        time.sleep(3 * (a + 1))
    return None

def write_logs(f, logs):
    for lg in logs:
        f.write(f"{int(lg['blockNumber'],16)},{lg['transactionHash']},{int(lg['logIndex'],16)},"
                f"0x{lg['topics'][1][-40:]},0x{lg['topics'][2][-40:]},{int(lg['data'],16)}\n")
    f.flush()

def find_start_block(chain_cfg, head):
    """块时间戳二分：定位 start_time_utc 对应块（宁可偏早多扫，不可漏铸造）"""
    import datetime
    target = int(datetime.datetime.fromisoformat(chain_cfg["start_time_utc"].replace("Z", "+00:00")).timestamp())
    rpc = chain_cfg["ts_rpc"]
    lo, hi = chain_cfg.get("bisect_low_block", 1), head
    while lo < hi:
        mid = (lo + hi) // 2
        ts = int(raw_call(rpc, "eth_getBlockByNumber", [hex(mid), False])["result"]["timestamp"], 16)
        if ts < target: lo = mid + 1
        else: hi = mid
        time.sleep(0.25)
    return lo

def mode_scan(chain):
    cc = CFG["chains"][chain]
    STEP = 10_000
    head = int(raw_call(cc["ts_rpc"], "eth_blockNumber", [])["result"], 16)
    done_path = os.path.join(DIR, f"{chain}_done.json")
    meta_path = os.path.join(DIR, f"{chain}_scan_meta.json")
    if os.path.exists(meta_path):
        meta = json.load(open(meta_path))
    else:
        meta = {"start_block": find_start_block(cc, head), "head": head}
        json.dump(meta, open(meta_path, "w"))
    print(f"start={meta['start_block']} head={meta['head']}", flush=True)
    done = set(json.load(open(done_path))) if os.path.exists(done_path) else set()
    segs = [b for b in range(meta["start_block"], meta["head"] + 1, STEP) if b not in done]
    total = len(segs) + len(done)
    q = queue.Queue()
    for s in segs: q.put(s)
    lock = threading.Lock()

    def worker(wid, url, cooldown, seg_step):
        f = open(os.path.join(DIR, f"{chain}_part_{wid}.csv"), "a")
        while True:
            try: seg = q.get_nowait()
            except queue.Empty: break
            logs = getlogs(url, seg, min(seg + min(seg_step, STEP) - 1, meta["head"]))
            with lock:
                if logs is not None:
                    write_logs(f, logs)
                    done.add(seg)
                    if len(done) % 100 == 0:
                        json.dump(sorted(done), open(done_path, "w"))
                        print(f"[progress] {len(done)}/{total} ({100*len(done)/total:.1f}%)", flush=True)
                else:
                    q.put(seg)  # 失败放回，最终由 fill 模式收尾
            time.sleep(cooldown)
        f.close()

    threads, wid = [], 0
    for ep in cc["scan_rpc_pool"]:
        for _ in range(ep.get("workers", 1)):
            threads.append(threading.Thread(target=worker, args=(wid, ep["url"], ep["cooldown"], ep["step"])))
            wid += 1
    for t in threads: t.start()
    for t in threads: t.join()
    json.dump(sorted(done), open(done_path, "w"))
    print(f"SCAN DONE {len(done)}/{total}（剩余毒段请跑 fill 模式）", flush=True)

def mode_fill(chain):
    """补扫毒段：TGE 高峰段单段日志量可超节点响应上限，需减半递归"""
    cc = CFG["chains"][chain]
    STEP = 10_000
    url = cc["scan_rpc_pool"][0]["url"]
    meta = json.load(open(os.path.join(DIR, f"{chain}_scan_meta.json")))
    done_path = os.path.join(DIR, f"{chain}_done.json")
    done = set(json.load(open(done_path)))
    segs = [b for b in range(meta["start_block"], meta["head"] + 1, STEP) if b not in done]
    print(f"fill segs: {len(segs)}", flush=True)

    def scan_range(frm, to, sub):
        out, cur = [], frm
        while cur <= to:
            end = min(cur + sub - 1, to)
            logs = getlogs(url, cur, end)
            if logs is None:
                if sub <= 125: return None
                part = scan_range(cur, end, sub // 2)
                if part is None: return None
                out.extend(part)
            else:
                out.extend(logs)
            cur = end + 1
        return out

    q = queue.Queue()
    for s in segs: q.put(s)
    lock = threading.Lock()

    def worker(wid):
        f = open(os.path.join(DIR, f"{chain}_part_fill{wid}.csv"), "a")
        while True:
            try: seg = q.get_nowait()
            except queue.Empty: break
            logs = scan_range(seg, min(seg + STEP - 1, meta["head"]), 1000)
            if logs is None:
                print(f"[w{wid}] seg {seg} FAILED at 125", flush=True); continue
            write_logs(f, logs)
            with lock:
                done.add(seg)
                json.dump(sorted(done), open(done_path, "w"))
            print(f"[w{wid}] seg {seg} ok +{len(logs)}", flush=True)
            time.sleep(0.2)
        f.close()

    ths = [threading.Thread(target=worker, args=(i,)) for i in range(6)]
    for t in ths: t.start()
    for t in ths: t.join()
    remain = [b for b in range(meta["start_block"], meta["head"] + 1, STEP) if b not in done]
    print(f"FILL DONE remaining={len(remain)}", flush=True)

def mode_anchors(chain):
    cc = CFG["chains"][chain]
    meta = json.load(open(os.path.join(DIR, f"{chain}_scan_meta.json")))
    lo, hi = meta["start_block"], meta["head"]
    table = {}
    anchors = list(range(lo, hi, 100_000)) + [hi]
    for i, b in enumerate(anchors):
        for _ in range(5):
            try:
                table[b] = int(raw_call(cc["ts_rpc"], "eth_getBlockByNumber", [hex(b), False])["result"]["timestamp"], 16)
                break
            except Exception:
                time.sleep(2)
        time.sleep(0.25)
        if i % 50 == 0: print(f"anchor {i}/{len(anchors)}", flush=True)
    json.dump(table, open(os.path.join(DIR, f"{chain}_ts_anchors.json"), "w"))
    print(f"ANCHORS DONE {len(table)}", flush=True)

def mode_status(chain):
    done_path = os.path.join(DIR, f"{chain}_done.json")
    meta = json.load(open(os.path.join(DIR, f"{chain}_scan_meta.json")))
    done = set(json.load(open(done_path))) if os.path.exists(done_path) else set()
    total = len(range(meta["start_block"], meta["head"] + 1, 10_000))
    import glob
    rows = sum(sum(1 for _ in open(p)) for p in glob.glob(os.path.join(DIR, f"{chain}_part_*.csv")))
    print(f"{len(done)}/{total} segs ({100*len(done)/max(total,1):.1f}%), {rows} rows")

if __name__ == "__main__":
    chain, mode = sys.argv[1], sys.argv[2]
    {"scan": mode_scan, "fill": mode_fill, "anchors": mode_anchors, "status": mode_status}[mode](chain)
