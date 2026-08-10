#!/usr/bin/env python3
"""HyperSync 多段并行全量采集器（亿级标的主力，fetch_hypersync.py 的并行扩展版）。
段计划固化（plan.json，段边界一经生成绝不能变）+ 每段 .prog 断点续传 + 指数退避。
与 watchdog_dual.py 配套时，>= 边界段可由第二通道认领（.aldone 完成标记）。

用法: python3 fetch_hypersync_par.py --config config.json [--section hypersync_par]
config.json 对应节（见 config.example.json）:
  {"url": "https://base.hypersync.xyz/query", "key": "<envio key，从 api-keys.md 取>",
   "token": "<标的合约>", "from_block": 0, "to_block": null,
   "segments": 12, "workers": 6, "sleep": 0.1, "outdir": "data/base"}
⚠️ 档位与并发（v3.11.2，Starter 付费档实测前的规划值）:
  - 免费层: workers 2-3 × sleep 0.5（key 级共享限流,多进程收益有限）
  - Starter 付费档(500rpm 爆发): 全局请求率 workers×(1/sleep) 必须 ≤ 8/s——
    workers=1 sleep=0.12 即吃满;workers>2 只会互相挤兑触发 429,别开
（来源：VIRTUAL(Base+ETH) 多链分析 2026-07-18 收编，v3.4 参数化；v3.11.2 付费档指引）"""
import requests, json, csv, os, sys, time, datetime, threading, queue, argparse

TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
PROGRESS_SCHEMA = "hypersync-par-progress/v2"


def _fsync_dir(path):
    fd = os.open(path or ".", os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_json(path, obj):
    """Publish metadata only after its bytes are durable on the same filesystem."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    _fsync_dir(os.path.dirname(path))


def _progress_identity(token, url, segment):
    i, s0, s1 = segment
    return {"schema": PROGRESS_SCHEMA, "token": token, "endpoint": url,
            "segment": i, "from_block": s0, "to_block": s1}


def load_progress(path, csv_path, identity):
    """Resume only from a bound checkpoint whose exact CSV extent is present."""
    try:
        saved = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise RuntimeError(f"unsafe/unreadable progress {path}: {e}") from e
    for key, expected in identity.items():
        if saved.get(key) != expected:
            raise RuntimeError(f"progress identity mismatch {key}: {saved.get(key)!r} != {expected!r}")
    if not os.path.isfile(csv_path):
        raise RuntimeError("progress exists but segment CSV is missing")
    actual_size = os.path.getsize(csv_path)
    if saved.get("csv_size") != actual_size:
        raise RuntimeError(f"segment CSV extent mismatch: {actual_size} != {saved.get('csv_size')}")
    nxt = saved.get("next_block")
    if isinstance(nxt, bool) or not isinstance(nxt, int):
        raise RuntimeError("progress next_block must be an integer")
    if not (identity["from_block"] <= nxt <= identity["to_block"]):
        raise RuntimeError(f"progress next_block outside segment: {nxt}")
    return nxt


def require_next_block(payload, cur, segment_end):
    nxt = payload.get("next_block")
    if isinstance(nxt, bool) or not isinstance(nxt, int):
        raise RuntimeError(f"missing/non-integer next_block at {cur}")
    if not (cur < nxt <= segment_end):
        raise RuntimeError(f"stalled/out-of-segment next_block {nxt} at {cur}")
    return nxt


def get_height(url, key):
    r = requests.get(url.replace("/query", "/height"),
                     headers={"Authorization": f"Bearer {key}"}, timeout=30)
    return r.json()["height"]


def worker(url, key, token, seg_q, outdir, stats, lock, sleep_s):
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    while True:
        try:
            seg = seg_q.get_nowait()
        except queue.Empty:
            return
        i, s0, s1 = seg  # [s0, s1)
        prog_f = os.path.join(outdir, f"part_{i:02d}.prog")
        csv_f = os.path.join(outdir, f"part_{i:02d}.csv")
        identity = _progress_identity(token, url, seg)
        cur = s0
        mode = "w"
        with_bh = True
        try:
            if os.path.exists(prog_f):
                cur = load_progress(prog_f, csv_f, identity)
                if cur >= s1:
                    with lock:
                        stats["done_segs"] += 1
                    continue
                mode = "a"
                with open(csv_f, encoding="utf-8") as fh:
                    with_bh = "block_hash" in fh.readline()  # 老 7 列 part 续拉维持老格式
            f = open(csv_f, mode, newline="")
            w = csv.writer(f)
            if mode == "w":
                w.writerow(["block", "ts", "tx", "log_index", "from", "to", "value_raw", "block_hash"])
            while cur < s1:
                q = {"from_block": cur, "to_block": s1,
                 "logs": [{"address": [token], "topics": [[TRANSFER]]}],
                 "field_selection": {
                     "log": ["block_number", "block_hash", "log_index", "transaction_hash", "topic1", "topic2", "data"],
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
                    raise RuntimeError(f"request retries exhausted at block {cur}")
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
                        row = [bn, iso, lg["transaction_hash"], int(lg["log_index"]),
                               "0x" + lg["topic1"][-40:], "0x" + lg["topic2"][-40:],
                               int(lg.get("data") or "0x0", 16) if lg.get("data") not in ("0x", "", None) else 0]
                        if with_bh:
                            row.append(lg.get("block_hash") or "")
                        w.writerow(row)
                        n += 1
                nxt = require_next_block(j, cur, s1)
                f.flush()
                os.fsync(f.fileno())
                atomic_json(prog_f, {**identity, "next_block": nxt,
                                      "csv_size": os.path.getsize(csv_f)})
                cur = nxt
                with lock:
                    stats["rows"] += n
                time.sleep(sleep_s)
            f.close()
            with lock:
                stats["done_segs"] += 1
        except Exception as e:
            try:
                f.close()
            except (NameError, UnboundLocalError):
                pass
            with lock:
                stats["errors"] += 1
                stats["fatal"].append(f"segment {i}: {e}")


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
        atomic_json(plan_f, {"height": height, "segments": segs})
    print(f"[plan] height={height} segments={len(segs)} workers={c.get('workers', 4)}", flush=True)
    seg_q = queue.Queue()
    for s in segs:
        seg_q.put(s)
    stats = {"rows": 0, "done_segs": 0, "errors": 0, "fatal": []}
    lock = threading.Lock()
    sleep_s = c.get("sleep", 0.1)
    threads = [threading.Thread(target=worker, args=(url, key, token, seg_q, outdir, stats, lock, sleep_s), daemon=True)
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
    if stats["fatal"]:
        for msg in stats["fatal"]:
            print(f"[FATAL] {msg}", file=sys.stderr)
        sys.exit(2)
    print(f"[COMPLETE] rows={stats['rows']:,} elapsed={(time.time()-t0)/3600:.2f}h", flush=True)


if __name__ == "__main__":
    main()
