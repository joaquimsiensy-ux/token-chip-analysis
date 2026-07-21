#!/usr/bin/env python3
"""转账数据公共库（v3.11.2 M 工程件）：格式自适应读取 / 防重组去重 / 多源合并对账 / 缓存。

统一逻辑行（dict）：
  block:int  ts:str(ISO,可空)  tx:str  log_index:int  from:str  to:str
  value_raw:int  block_hash:str(可空——老数据没有,新采集必有)

支持的输入格式（iter_transfers 自动识别）：
  1) v1 单进程 CSV: block,ts,tx,from,to,value_raw,uniqueId[,block_hash]
  2) par 分段 CSV : block,ts,tx,log_index,from,to,value_raw[,block_hash]
  3) v2 parquet 目录（run_*/logs.parquet + blocks.parquet，自动 join 时间戳）

去重键（防链重组,v3.11.2 起标准）: (block_hash or block, tx, log_index)
  —— 老数据无 block_hash 时退化为 (block, tx, log_index)，重组风险窗仅存在于
     已 final 的历史段之外，尾部新数据一律带 block_hash。

多源合并对账（merge_sources）: 重叠块区间内各源 (tx,log_index) 集合必须完全相等，
  不等即打印差集样本并 exit(3)（fail-closed——PING 案 uniqueId 双计 5485 负余额事故的制度化防线）。

缓存（~/.cache/chip-analysis/）:
  deploy_blocks.json         # chain:token -> 部署块（首拉后永存,免每次从 0 扫）
  anchors/<chain>.csv        # block,ts 锚点库,跨币复用,bisect 插值
（来源：v3.11.2 采集加速工程,2026-07-21）"""
import bisect, csv, datetime, glob, json, os, sys

CACHE_DIR = os.path.expanduser("~/.cache/chip-analysis")
ZERO = "0x0000000000000000000000000000000000000000"


def _iso(ts):
    if ts in (None, "", 0):
        return ""
    return datetime.datetime.fromtimestamp(int(ts), datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S")


# ---------------- 读取:格式自适应 ----------------

def _iter_csv(path):
    with open(path, newline="") as f:
        rd = csv.reader(f)
        header = next(rd, None)
        if not header:
            return
        cols = {c: i for i, c in enumerate(header)}
        is_v1 = "uniqueId" in cols
        bh_i = cols.get("block_hash")
        for r in rd:
            if not r or not r[0].isdigit():
                continue
            if is_v1:
                li = int(r[cols["uniqueId"]].rsplit(":", 1)[-1]) if ":" in r[cols["uniqueId"]] else 0
            else:
                li = int(r[cols["log_index"]])
            yield {"block": int(r[cols["block"]]), "ts": r[cols["ts"]],
                   "tx": r[cols["tx"]], "log_index": li,
                   "from": r[cols["from"]].lower(), "to": r[cols["to"]].lower(),
                   "value_raw": int(r[cols["value_raw"]]),
                   "block_hash": (r[bh_i] if bh_i is not None and bh_i < len(r) else "")}


def _iter_parquet_dir(path):
    import pyarrow.parquet as pq
    runs = sorted(glob.glob(os.path.join(path, "run_*"))) or [path]
    for run in runs:
        lp = os.path.join(run, "logs.parquet")
        if not os.path.exists(lp):
            continue
        bts = {}
        bp = os.path.join(run, "blocks.parquet")
        if os.path.exists(bp):
            bt = pq.read_table(bp, columns=["number", "timestamp"])
            for n, t in zip(bt.column("number").to_pylist(), bt.column("timestamp").to_pylist()):
                if n is not None:
                    bts[int(n)] = int(t, 16) if isinstance(t, str) else int(t)
        t = pq.read_table(lp)
        cols = {c: t.column(c).to_pylist() for c in
                ("block_number", "block_hash", "log_index", "transaction_hash",
                 "topic1", "topic2", "data") if c in t.column_names}
        n = t.num_rows
        for i in range(n):
            bn = int(cols["block_number"][i])
            data = cols.get("data", [None] * n)[i]
            yield {"block": bn, "ts": _iso(bts.get(bn)),
                   "tx": cols["transaction_hash"][i],
                   "log_index": int(cols["log_index"][i]),
                   "from": "0x" + (cols["topic1"][i] or "0x" + "0" * 64)[-40:].lower(),
                   "to": "0x" + (cols["topic2"][i] or "0x" + "0" * 64)[-40:].lower(),
                   "value_raw": int(data, 16) if data not in (None, "", "0x") else 0,
                   "block_hash": cols.get("block_hash", [""] * n)[i] or ""}


def iter_transfers(path):
    """自适应迭代任意来源的转账数据文件/目录。"""
    if os.path.isdir(path):
        yield from _iter_parquet_dir(path)
    elif path.endswith(".parquet"):
        yield from _iter_parquet_dir(os.path.dirname(path) or ".")
    else:
        yield from _iter_csv(path)


def dedup_key(row):
    return (row["block_hash"] or row["block"], row["tx"], row["log_index"])


def dedup_iter(rows):
    seen = set()
    for r in rows:
        k = dedup_key(r)
        if k in seen:
            continue
        seen.add(k)
        yield r


# ---------------- 写出 ----------------

STD_COLS = ["block", "ts", "tx", "log_index", "from", "to", "value_raw", "block_hash"]


def write_csv(rows, out, legacy7=False):
    """legacy7=True 输出 v1 老 7 列（含 uniqueId）,给尚未迁移的下游。"""
    n = 0
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        if legacy7:
            w.writerow(["block", "ts", "tx", "from", "to", "value_raw", "uniqueId"])
            for r in rows:
                w.writerow([r["block"], r["ts"], r["tx"], r["from"], r["to"],
                            r["value_raw"], f"{r['tx']}:log:{r['log_index']}"])
                n += 1
        else:
            w.writerow(STD_COLS)
            for r in rows:
                w.writerow([r[c] for c in STD_COLS])
                n += 1
    return n


def write_parquet(rows, out):
    import pyarrow as pa
    import pyarrow.parquet as pq
    rows = list(rows) if not isinstance(rows, list) else rows
    arrays = {
        "block": pa.array([r["block"] for r in rows], pa.int64()),
        "ts": pa.array([r["ts"] for r in rows], pa.string()),
        "tx": pa.array([r["tx"] for r in rows], pa.string()),
        "log_index": pa.array([r["log_index"] for r in rows], pa.int64()),
        "from": pa.array([r["from"] for r in rows], pa.string()),
        "to": pa.array([r["to"] for r in rows], pa.string()),
        # uint256 最大 78 位十进制,任何数值类型都装不下 —— 一律存字符串,下游 int() 还原
        "value_raw": pa.array([str(r["value_raw"]) for r in rows], pa.string()),
        "block_hash": pa.array([r["block_hash"] for r in rows], pa.string()),
    }
    pq.write_table(pa.table(arrays), out, compression="zstd")
    return len(rows)


# ---------------- 多源合并 + 重叠区对账（fail-closed） ----------------

def merge_sources(paths, out, legacy7=False):
    """按块序合并多来源;两两重叠块区间内 (tx,log_index) 集合必须完全相等,否则 exit(3)。
    out 以 .parquet 结尾走 parquet,否则 CSV。返回 (总行数, 重叠检查数)。"""
    srcs = []
    for p in paths:
        rows = sorted(iter_transfers(p), key=lambda r: (r["block"], r["log_index"]))
        if rows:
            srcs.append({"path": p, "rows": rows,
                         "lo": rows[0]["block"], "hi": rows[-1]["block"]})
    checks = 0
    for i in range(len(srcs)):
        for j in range(i + 1, len(srcs)):
            a, b = srcs[i], srcs[j]
            lo, hi = max(a["lo"], b["lo"]), min(a["hi"], b["hi"])
            if lo > hi:
                continue
            sa = {(r["tx"], r["log_index"]) for r in a["rows"] if lo <= r["block"] <= hi}
            sb = {(r["tx"], r["log_index"]) for r in b["rows"] if lo <= r["block"] <= hi}
            checks += 1
            if sa != sb:
                d1, d2 = list(sa - sb)[:5], list(sb - sa)[:5]
                print(f"[FAIL-CLOSED] 重叠区 [{lo},{hi}] 集合不等: "
                      f"{a['path']} 独有 {len(sa-sb)} 条(样本 {d1}); "
                      f"{b['path']} 独有 {len(sb-sa)} 条(样本 {d2})", flush=True)
                print("[FAIL-CLOSED] 禁止继续——先仲裁差异(独立 archive RPC 查 receipt)再合并", flush=True)
                sys.exit(3)
    merged = dedup_iter(r for s in srcs for r in
                        sorted((x for x in s["rows"]), key=lambda r: (r["block"], r["log_index"])))
    merged = sorted(merged, key=lambda r: (r["block"], r["log_index"]))
    n = write_parquet(merged, out) if out.endswith(".parquet") else write_csv(merged, out, legacy7)
    return n, checks


# ---------------- 部署块缓存 ----------------

def get_deploy_block(chain, token, fetch_fn=None):
    """查全局缓存;miss 且给了 fetch_fn 则调用并写回。fetch_fn() -> int"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    p = os.path.join(CACHE_DIR, "deploy_blocks.json")
    db = {}
    if os.path.exists(p):
        db = json.load(open(p))
    k = f"{chain}:{token.lower()}"
    if k in db:
        return db[k]
    if fetch_fn is None:
        return None
    v = fetch_fn()
    if v:
        db[k] = int(v)
        json.dump(db, open(p, "w"), indent=1)
    return v


# ---------------- 时间戳锚点库（跨币复用） ----------------

def anchor_path(chain):
    d = os.path.join(CACHE_DIR, "anchors")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{chain}.csv")


def add_anchors(chain, pairs):
    """pairs: [(block,ts_epoch)…] 追加进锚点库并去重排序。"""
    p = anchor_path(chain)
    seen = {}
    if os.path.exists(p):
        for r in csv.reader(open(p)):
            if r and r[0].isdigit():
                seen[int(r[0])] = int(r[1])
    for b, t in pairs:
        seen[int(b)] = int(t)
    with open(p, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["block", "ts"])
        for b in sorted(seen):
            w.writerow([b, seen[b]])
    return len(seen)


def load_anchors(chain):
    p = anchor_path(chain)
    blocks, tss = [], []
    if os.path.exists(p):
        for r in csv.reader(open(p)):
            if r and r[0].isdigit():
                blocks.append(int(r[0]))
                tss.append(int(r[1]))
    return blocks, tss


def estimate_ts(blocks, tss, block):
    """锚点线性插值。⚠发射窗口精确配价禁用（恒定偏差坑,见 data-pipeline-evm §6）。"""
    if not blocks:
        return None
    i = bisect.bisect_left(blocks, block)
    if i == 0:
        return tss[0]
    if i >= len(blocks):
        return tss[-1]
    b0, b1, t0, t1 = blocks[i - 1], blocks[i], tss[i - 1], tss[i]
    return t0 + (t1 - t0) * (block - b0) // max(1, b1 - b0)


if __name__ == "__main__":
    # 轻量 CLI: 统计/转换/合并
    import argparse
    ap = argparse.ArgumentParser(description="transfers_lib CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s1 = sub.add_parser("count"); s1.add_argument("path")
    s2 = sub.add_parser("convert"); s2.add_argument("src"); s2.add_argument("dst")
    s2.add_argument("--legacy7", action="store_true")
    s3 = sub.add_parser("merge"); s3.add_argument("srcs", nargs="+"); s3.add_argument("--out", required=True)
    s3.add_argument("--legacy7", action="store_true")
    a = ap.parse_args()
    if a.cmd == "count":
        n = sum(1 for _ in iter_transfers(a.path))
        print(n)
    elif a.cmd == "convert":
        rows = sorted(dedup_iter(iter_transfers(a.src)), key=lambda r: (r["block"], r["log_index"]))
        n = write_parquet(rows, a.dst) if a.dst.endswith(".parquet") else write_csv(rows, a.dst, a.legacy7)
        print(f"converted {n} rows -> {a.dst}")
    elif a.cmd == "merge":
        n, ck = merge_sources(a.srcs, a.out, a.legacy7)
        print(f"merged {n} rows ({ck} overlap checks passed) -> {a.out}")
