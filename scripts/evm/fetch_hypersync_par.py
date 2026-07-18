#!/usr/bin/env python3
"""HyperSync 多段并行全量采集器（亿级标的主力，fetch_hypersync.py 的并行扩展版）。
段计划固化（plan.json，段边界一经生成绝不能变）+ 每段 .prog 断点续传 + 指数退避。
与 watchdog_dual.py 配套时，>= 边界段可由第二通道认领（.aldone 完成标记）。

用法: python3 fetch_hypersync_par.py --config config.json [--section hypersync_par]
config.json 对应节（见 config.example.json）:
  {"url": "https://base.hypersync.xyz/query", "key": "<envio key，从 api-keys.md 取>",
   "token": "<标的合约>", "from_block": 0, "to_block": null,
   "segments": 12, "workers": 6, "outdir": "data/base"}
（来源：VIRTUAL(Base+ETH) 多链分析 2026-07-18 收编，v3.4 参数化）"""
import requests, json, csv, os, sys, time, datetime, threading, queue, argparse

TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def get_height(url, key):
    r = requests.get(url.replace("/query", "/height"),
                     headers={"Authorization": f"Bearer {key}"}, timeout=30)
    return r.json()["height"]


def worker(url, key, token, seg_q, outdir, stats, lock):
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    while True:
        try:
            seg = seg_q.get_nowait()
        except queue.Empty:
            return
        i, s0, s1 = seg  # [s0, s1)
        prog_f = os.path.join(outdir, f"part_{i:02d}.prog")
        csv_f = os.path.join(outdir, f"part_{i:02d}.csv")
        cur = s0
        mode = "w"
        if os.path.exists(prog_f):
            saved = int(open(prog_f).read().strip() or s0)
            if saved >= s1:
                with lock:
                    stats["done_segs"] += 1
                continue
            cur = saved
            mode = "a"
        f = open(csv_f, mode, newline="")
        w = csv.writer(f)
        if mode == "w":
            w.writerow(["block", "ts", "tx", "log_index", "from", "to", "value_raw"])
        while cur < s1:
            q = {"from_block": cur, "to_block": s1,
                 "logs": [{"address": [token], "topics": [[TRANSFER]]}],
                 "field_selection": {
                     "log": ["block_number", "log_index", "transaction_hash", "topic1", "topic2", "data"],
                     "block": ["number", "timestamp"]}}
            j = None
            for attempt in range(12):
                try:
                    r = requests.post(url, json=q, headers=headers, timeout=120)
                    if r.status_code == 200:
                        j = r.json()
                        break
                    time.sleep(min(3 * 2 ** attempt, 300))
                except Exception:
                    time.sleep(min(3 * 2 ** attempt, 300))
            if j is None:
                with lock:
                    stats["errors"] += 1
                time.sleep(60)
                continue  # 段内死磕，进度文件保底
            bts = {}
            n = 0
            for batch in j.get("data", []):
                for b in batch.get("blocks", []):
                    ts = b.get("timestamp")
                    bts[int(b["number"])] = int(ts, 16) if isinstance(ts, str) else int(ts)
                for lg in batch.get("logs", []):
                    bn = int(lg["block_number"])
                    ts = bts.get(bn)
                    iso = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") if ts else ""
                    w.writerow([bn, iso, lg["transaction_hash"], int(lg["log_index"]),
                                "0x" + lg["topic1"][-40:], "0x" + lg["topic2"][-40:],
                                int(lg.get("data") or "0x0", 16) if lg.get("data") not in ("0x", "", None) else 0])
                    n += 1
            nxt = j.get("next_block")
            if not nxt or nxt <= cur:
                nxt = cur + 1
            cur = min(nxt, s1)
            f.flush()
            open(prog_f, "w").write(str(cur))
            with lock:
                stats["rows"] += n
            time.sleep(0.1)
        f.close()
        with lock:
            stats["done_segs"] += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--section", default="hypersync_par")
    a = ap.parse_args()
    cfg = json.load(open(a.config))
    c = cfg[a.section]
    if not c.get("key"):
        sys.exit(f"[FATAL] config[{a.section}].key 为空——HyperSync key 从 ~/.claude/api-keys.md 登记文件取用后填入工作目录 config.json（铁律 5：key 不写死进脚本）")
    url, key, token = c["url"], c["key"], c["token"].lower()
    outdir = c.get("outdir", "data")
    os.makedirs(outdir, exist_ok=True)
    plan_f = os.path.join(outdir, "plan.json")
    if os.path.exists(plan_f):
        # 断点重启：沿用既有分段计划——段边界绝不能变（.prog/CSV 按旧边界续传）
        plan = json.load(open(plan_f))
        height = plan["height"]
        segs = [tuple(s) for s in plan["segments"]]
        print(f"[plan] reuse existing plan: height={height} segments={len(segs)}", flush=True)
    else:
        height = get_height(url, key)
        if c.get("to_block"):
            height = min(height, c["to_block"])
        from_block = c.get("from_block", 0)
        n_seg = c.get("segments", 8)
        span = height - from_block
        seg_size = span // n_seg + 1
        segs = []
        for i in range(n_seg):
            s0 = from_block + i * seg_size
            s1 = min(s0 + seg_size, height)
            if s0 < s1:
                segs.append((i, s0, s1))
        json.dump({"height": height, "segments": segs}, open(plan_f, "w"))
    print(f"[plan] height={height} segments={len(segs)} workers={c.get('workers', 4)}", flush=True)
    seg_q = queue.Queue()
    for s in segs:
        seg_q.put(s)
    stats = {"rows": 0, "done_segs": 0, "errors": 0}
    lock = threading.Lock()
    threads = [threading.Thread(target=worker, args=(url, key, token, seg_q, outdir, stats, lock), daemon=True)
               for _ in range(c.get("workers", 4))]
    t0 = time.time()
    for t in threads:
        t.start()
    while any(t.is_alive() for t in threads):
        time.sleep(60)
        el = time.time() - t0
        rate = stats["rows"] / el if el else 0
        print(f"[prog] rows={stats['rows']:,} segs_done={stats['done_segs']}/{len(segs)} "
              f"rate={rate:.0f}/s errors={stats['errors']} elapsed={el/3600:.2f}h", flush=True)
    print(f"[COMPLETE] rows={stats['rows']:,} elapsed={(time.time()-t0)/3600:.2f}h", flush=True)


if __name__ == "__main__":
    main()
