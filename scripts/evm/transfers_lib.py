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

多源合并对账（merge_sources，小样本专用）: 重叠块区间内各源 (tx,log_index) 集合必须完全相等，
  不等即打印差集样本并 exit(3)（fail-closed——PING 案 uniqueId 双计 5485 负余额事故的制度化防线）。
  默认最多 1,000,000 行；正式亿级入口用 replay_stream.py / DuckDB，不允许本函数全量排序。

缓存（~/.cache/chip-analysis/）:
  deploy_blocks.json         # chain:token -> 部署块（首拉后永存,免每次从 0 扫）
  anchors/<chain>.csv        # block,ts 锚点库,跨币复用,bisect 插值
（来源：v3.11.2 采集加速工程,2026-07-21）"""
import bisect, csv, datetime, glob, hashlib, json, os, sys

CACHE_DIR = os.path.expanduser("~/.cache/chip-analysis")
ZERO = "0x0000000000000000000000000000000000000000"
DEFAULT_SMALL_SAMPLE_MAX_ROWS = 1_000_000


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
            pf = pq.ParquetFile(bp)
            for batch in pf.iter_batches(batch_size=100_000, columns=["number", "timestamp"]):
                cols = batch.to_pydict()
                for n, t in zip(cols["number"], cols["timestamp"]):
                    if n is not None:
                        bts[int(n)] = int(t, 16) if isinstance(t, str) else int(t)
        pf = pq.ParquetFile(lp)
        wanted = ("block_number", "block_hash", "log_index", "transaction_hash",
                  "topic1", "topic2", "data")
        available = [c for c in wanted if c in pf.schema_arrow.names]
        required = {"block_number", "log_index", "transaction_hash", "topic1", "topic2"}
        if not required.issubset(available):
            raise ValueError(f"parquet missing columns: {sorted(required - set(available))}")
        for batch in pf.iter_batches(batch_size=100_000, columns=available):
            cols = batch.to_pydict()
            n = batch.num_rows
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
    return (row["block"], row["tx"], row["log_index"])


def canonical_payload(row):
    """Return the consensus-critical event payload for duplicate/source checks."""
    return (
        int(row["block"]),
        str(row["tx"]).lower(),
        int(row["log_index"]),
        str(row["from"]).lower(),
        str(row["to"]).lower(),
        int(row["value_raw"]),
        str(row.get("block_hash") or "").lower(),
    )


def _source_sha256(path):
    """Stable hash for either a file or a directory of input files."""
    h = hashlib.sha256()
    files = [path] if os.path.isfile(path) else sorted(
        p for p in glob.glob(os.path.join(path, "**", "*"), recursive=True)
        if os.path.isfile(p)
    )
    for item in files:
        rel = os.path.relpath(item, path) if os.path.isdir(path) else os.path.basename(item)
        h.update(rel.encode("utf-8") + b"\0")
        with open(item, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
    return h.hexdigest()


def dedup_iter(rows):
    """按 (block,tx,log_index) 去重 + 重组冲突检测（fail-closed 修复 2026-07-22）。

    修复前主键含 block_hash：同一事件出现两个不同 hash（链重组）或"一源带 hash
    一源不带"（混合源）时键不同 → 两个版本都保留=静默双计。修复后：同键重复
    正常跳过；同键出现两个**非空且不同**的 block_hash = 重组冲突，exit(3) 先仲裁
    （与 merge_sources 重叠区对账同级的防线）。"""
    seen = {}   # (block,tx,log_index) -> 首见规范 payload
    for r in rows:
        k = dedup_key(r)
        if k in seen:
            payload = canonical_payload(r)
            if seen[k] != payload:
                print(f"[FAIL-CLOSED] 重复键 payload 冲突：{k}\n"
                      f"  first={seen[k]}\n  next ={payload}", flush=True)
                print("[FAIL-CLOSED] 禁止继续——同一事件主键的链上字段不一致，"
                      "先用独立 archive RPC 仲裁", flush=True)
                sys.exit(3)
            continue
        seen[k] = canonical_payload(r)
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

def _small_sample_rows(path, remaining):
    rows = []
    for row in iter_transfers(path):
        if len(rows) >= remaining:
            raise RuntimeError(f"small-sample row limit exceeded while reading {path}")
        rows.append(row)
    return rows


def _write_input_manifest(out, *, mode, max_rows, sources, output_rows, overlap_checks=0):
    manifest = {
        "schema": "transfers-small-sample-inputs/v1",
        "mode": mode,
        "small_sample_only": True,
        "max_rows": max_rows,
        "inputs": [{"path": os.path.realpath(s["path"]), "sha256": _source_sha256(s["path"]),
                    "rows": len(s["rows"]), "lo": s.get("lo"), "hi": s.get("hi")}
                   for s in sources],
        "output": {"path": os.path.realpath(out), "sha256": _source_sha256(out),
                   "rows": output_rows},
        "overlap_checks": overlap_checks,
    }
    with open(out + ".input_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def merge_sources(paths, out, legacy7=False, max_rows=DEFAULT_SMALL_SAMPLE_MAX_ROWS):
    """按块序合并多来源;两两重叠块区间内 (tx,log_index) 集合必须完全相等,否则 exit(3)。
    小样本专用，超过 max_rows 拒绝；正式大数据走 replay_stream.py/DuckDB。
    out 以 .parquet 结尾走 parquet,否则 CSV。返回 (总行数, 重叠检查数)。"""
    if isinstance(max_rows, bool) or not isinstance(max_rows, int) or max_rows <= 0:
        raise ValueError("max_rows must be a positive integer")
    srcs = []
    loaded = 0
    for p in paths:
        try:
            rows = _small_sample_rows(p, max_rows - loaded)
        except RuntimeError as e:
            print(f"[FAIL-CLOSED] {e}; 正式大数据请用 replay_stream.py/DuckDB", flush=True)
            sys.exit(4)
        loaded += len(rows)
        rows.sort(key=lambda r: (r["block"], r["log_index"]))
        srcs.append({"path": p, "rows": rows,
                     "lo": rows[0]["block"] if rows else None,
                     "hi": rows[-1]["block"] if rows else None})
    checks = 0
    for i in range(len(srcs)):
        for j in range(i + 1, len(srcs)):
            a, b = srcs[i], srcs[j]
            if not a["rows"] or not b["rows"]:
                continue
            all_a = {(r["tx"], r["log_index"]): canonical_payload(r) for r in a["rows"]}
            all_b = {(r["tx"], r["log_index"]): canonical_payload(r) for r in b["rows"]}
            global_mismatch = [k for k in set(all_a) & set(all_b) if all_a[k] != all_b[k]]
            if global_mismatch:
                sample = [{"key": k, "a": all_a[k], "b": all_b[k]}
                          for k in global_mismatch[:3]]
                print(f"[FAIL-CLOSED] 跨源同 (tx,log_index) payload 冲突 "
                      f"{len(global_mismatch)} 条(样本 {sample})", flush=True)
                print(f"[inputs] sha256 {a['path']}={_source_sha256(a['path'])} "
                      f"{b['path']}={_source_sha256(b['path'])}", flush=True)
                sys.exit(3)
            lo, hi = max(a["lo"], b["lo"]), min(a["hi"], b["hi"])
            if lo > hi:
                continue
            sa = {(r["tx"], r["log_index"]): canonical_payload(r)
                  for r in a["rows"] if lo <= r["block"] <= hi}
            sb = {(r["tx"], r["log_index"]): canonical_payload(r)
                  for r in b["rows"] if lo <= r["block"] <= hi}
            checks += 1
            only_a = set(sa) - set(sb)
            only_b = set(sb) - set(sa)
            mismatch = [k for k in set(sa) & set(sb) if sa[k] != sb[k]]
            if only_a or only_b or mismatch:
                sample = [{"key": k, "a": sa[k], "b": sb[k]} for k in mismatch[:3]]
                print(f"[FAIL-CLOSED] 重叠区 [{lo},{hi}] 事件不一致: "
                      f"{a['path']} 独有 {len(only_a)} 条(样本 {list(only_a)[:5]}); "
                      f"{b['path']} 独有 {len(only_b)} 条(样本 {list(only_b)[:5]}); "
                      f"同键 payload 冲突 {len(mismatch)} 条(样本 {sample})", flush=True)
                print(f"[inputs] sha256 {a['path']}={_source_sha256(a['path'])} "
                      f"{b['path']}={_source_sha256(b['path'])}", flush=True)
                print("[FAIL-CLOSED] 禁止继续——先仲裁差异(独立 archive RPC 查 receipt)再合并", flush=True)
                sys.exit(3)
    merged = dedup_iter(r for s in srcs for r in
                        sorted((x for x in s["rows"]), key=lambda r: (r["block"], r["log_index"])))
    merged = sorted(merged, key=lambda r: (r["block"], r["log_index"]))
    n = write_parquet(merged, out) if out.endswith(".parquet") else write_csv(merged, out, legacy7)
    _write_input_manifest(out, mode="merge", max_rows=max_rows, sources=srcs,
                          output_rows=n, overlap_checks=checks)
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
    s2.add_argument("--max-rows", type=int, default=DEFAULT_SMALL_SAMPLE_MAX_ROWS)
    s3 = sub.add_parser("merge"); s3.add_argument("srcs", nargs="+"); s3.add_argument("--out", required=True)
    s3.add_argument("--legacy7", action="store_true")
    s3.add_argument("--max-rows", type=int, default=DEFAULT_SMALL_SAMPLE_MAX_ROWS)
    a = ap.parse_args()
    if a.cmd == "count":
        n = sum(1 for _ in iter_transfers(a.path))
        print(n)
    elif a.cmd == "convert":
        try:
            source_rows = _small_sample_rows(a.src, a.max_rows)
        except RuntimeError as e:
            sys.exit(f"[FAIL-CLOSED] {e}; 正式大数据请用 replay_stream.py/DuckDB")
        rows = sorted(dedup_iter(source_rows), key=lambda r: (r["block"], r["log_index"]))
        n = write_parquet(rows, a.dst) if a.dst.endswith(".parquet") else write_csv(rows, a.dst, a.legacy7)
        _write_input_manifest(a.dst, mode="convert", max_rows=a.max_rows,
                              sources=[{"path": a.src, "rows": source_rows,
                                        "lo": min((r["block"] for r in source_rows), default=None),
                                        "hi": max((r["block"] for r in source_rows), default=None)}],
                              output_rows=n)
        print(f"converted {n} rows -> {a.dst}")
    elif a.cmd == "merge":
        n, ck = merge_sources(a.srcs, a.out, a.legacy7, a.max_rows)
        print(f"merged {n} rows ({ck} overlap checks passed) -> {a.out}")
