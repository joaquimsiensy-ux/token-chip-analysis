#!/usr/bin/env python3
"""HyperSync 官方客户端采集器 v2（Rust 内核自动并发 + Parquet 直写）。
与 v1（fetch_hypersync.py 手写 JSON 轮询）的差别：传输为压缩二进制、客户端内部并发流水线
（掩盖 RTT——v3.11.2 POC 实测正是 RTT 主导瓶颈）、直接落 Parquet 免逐行 CSV。

用法: python3 fetch_hypersync_v2.py <from_block> \
        --url https://bsc.hypersync.xyz --token-addr 0x标的 --outdir data/v2 \
        [--to-block N] [--concurrency 10] [--token-file ~/.config/hypersync/token]
  - API token 读取优先级（C3 密钥治理，2026-07-22——**不要把 token 放进命令行**，
    ps 进程列表可见）：位置参数（仅旧用法兼容，勿新用）> 环境变量 HYPERSYNC_TOKEN
    > --token-file 文件（默认 ~/.config/hypersync/token，chmod 600）
  - --url 注意是裸域名（官方客户端自己拼路径，不要带 /query）
  - --concurrency 官方默认 10；高密度合约建议 20 起调；免费层别超 4（限流）
  - 断点续传：--outdir 已有 run_*/ 时自动从最大 next_block 续拉，新数据落新 run_<from>/ 子目录
输出: <outdir>/run_<from>/logs.parquet + blocks.parquet
  下游用 transfers_lib.py 的 read_transfers() 合成标准 8 列表（自动 join 时间戳）。
（来源：v3.11.2 采集加速工程，2026-07-21）"""
import argparse, asyncio, glob, hashlib, json, os, re, sys, time
from pathlib import Path

import hypersync
from hypersync import (BlockField, ClientConfig, FieldSelection, HexOutput,
                       LogField, LogSelection, Query, StreamConfig)

TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
MANIFEST_SCHEMA = "hypersync-v2-done/v3"
QUERY_SCHEMA = "erc20-transfer-fields/v2"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def inspect_run_files(run_dir, from_block, to_block):
    """Validate both Parquets and return their content-bound receipt metadata."""
    try:
        import duckdb
    except ImportError as e:
        raise ValueError("duckdb 未安装，无法重验 Parquet 完整性") from e
    run = Path(run_dir)
    specs = {
        "logs.parquet": ("block_number", {"block_number", "block_hash", "log_index",
                                            "transaction_hash", "topic1", "topic2", "data"}),
        "blocks.parquet": ("number", {"number", "timestamp"}),
    }
    result = {}
    con = duckdb.connect()
    try:
        for name, (block_col, required) in specs.items():
            path = run / name
            if not path.is_file():
                raise ValueError(f"{name} 不存在")
            try:
                cols = {r[0] for r in con.execute(
                    "DESCRIBE SELECT * FROM read_parquet(?)", [str(path)]).fetchall()}
                if not required <= cols:
                    raise ValueError(f"{name} schema 缺字段: {sorted(required - cols)}")
                rows, lo, hi = con.execute(
                    f"SELECT COUNT(*), MIN({block_col}), MAX({block_col}) FROM read_parquet(?)",
                    [str(path)]).fetchone()
            except ValueError:
                raise
            except Exception as e:
                raise ValueError(f"{name} 不可读或已截断: {e}") from e
            if rows and (lo is None or hi is None or int(lo) < int(from_block)
                         or int(hi) >= int(to_block)):
                raise ValueError(f"{name} 块范围 [{lo},{hi}] 越出 [{from_block},{to_block})")
            result[name] = {"size": path.stat().st_size, "rows": int(rows),
                            "min_block": int(lo) if lo is not None else None,
                            "max_block": int(hi) if hi is not None else None,
                            "sha256": sha256_file(path)}
        missing = con.execute(
            "SELECT COUNT(*) FROM read_parquet(?) l LEFT JOIN read_parquet(?) b "
            "ON l.block_number=b.number WHERE l.block_number IS NOT NULL AND b.number IS NULL",
            [str(run / "logs.parquet"), str(run / "blocks.parquet")]).fetchone()[0]
        if missing:
            raise ValueError(f"blocks.parquet 缺 {missing} 个 logs 所在块")
    finally:
        con.close()
    return result


def validate_done_manifest(done_path, default_from, to_block, token_addr, url):
    """Revalidate manifest identity, bounds, Parquet schemas, ranges, sizes and hashes."""
    try:
        d = json.load(open(done_path, encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"unreadable done manifest {done_path}: {exc}") from exc
    expected = {"schema": MANIFEST_SCHEMA, "query_schema": QUERY_SCHEMA,
                "token": token_addr.lower(), "url": url}
    if any(d.get(k) != v for k, v in expected.items()):
        raise ValueError(f"done manifest identity mismatch: {done_path}")
    try:
        capture = int(d.get("capture_from", -1))
        frm, end, nb = (int(d.get(k, -1)) for k in ("from_block", "to_block", "next_block"))
    except (TypeError, ValueError) as e:
        raise ValueError(f"done manifest bounds non-integer: {done_path}") from e
    if capture != int(default_from) or not (default_from <= frm < end == nb <= to_block):
        raise ValueError(f"done manifest bounds invalid/outside request: {done_path}")
    actual = inspect_run_files(Path(done_path).parent, frm, end)
    recorded = d.get("files")
    if not isinstance(recorded, dict) or set(recorded) != set(actual):
        raise ValueError(f"done manifest files receipt missing/extra: {done_path}")
    for name, meta in actual.items():
        if recorded.get(name) != meta:
            raise ValueError(f"done manifest {name} size/rows/range/hash drift: {done_path}")
    return d


def atomic_write_json(path, obj):
    path = Path(path)
    tmp = path.with_name("." + path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    dir_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def find_resume_block(outdir, default_from, to_block, token_addr, url):
    """Resume only manifests bound to the same capture identity and bounds."""
    best = default_from
    for f in glob.glob(os.path.join(outdir, "run_*", "done.json")):
        try:
            raw = json.load(open(f, encoding="utf-8"))
        except Exception as exc:
            raise SystemExit(f"[fail-closed] unreadable done manifest {f}: {exc}")
        if int(raw.get("capture_from", -1)) != int(default_from):
            continue
        try:
            d = validate_done_manifest(f, default_from, to_block, token_addr, url)
        except ValueError as exc:
            raise SystemExit(f"[fail-closed] {exc}") from exc
        nb = int(d["next_block"])
        best = max(best, nb)
    return best


def resolve_token(a):
    """C3：token 优先级 位置参数(旧兼容) > $HYPERSYNC_TOKEN > --token-file 文件。"""
    if a.api_token:
        print("[warn] token 经命令行传入（ps 可见）——建议改用 --token-file/环境变量",
              flush=True)
        return a.api_token
    env = os.environ.get("HYPERSYNC_TOKEN", "").strip()
    if env:
        return env
    try:
        tok = open(os.path.expanduser(a.token_file)).read().strip()
    except OSError:
        sys.exit(f"[fatal] 读不到 HyperSync token 文件: {a.token_file}"
                 "（也可设环境变量 HYPERSYNC_TOKEN）")
    if not tok:
        sys.exit(f"[fatal] token 文件为空: {a.token_file}")
    return tok


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("api_token", nargs="?", default=None,
                    help="（旧用法兼容，勿新用——token 会进 ps）留空则读 env/文件")
    ap.add_argument("from_block", type=int)
    ap.add_argument("--url", default="https://bsc.hypersync.xyz")
    ap.add_argument("--token-addr", required=True)
    ap.add_argument("--outdir", default="data/v2")
    ap.add_argument("--to-block", type=int, default=None)
    ap.add_argument("--concurrency", type=int, default=10)
    ap.add_argument("--token-file", default="~/.config/hypersync/token",
                    help="API token 文件路径（默认 ~/.config/hypersync/token）")
    a = ap.parse_args()
    token = resolve_token(a)
    url = re.sub(r"/query/?$", "", a.url.rstrip("/"))  # 容错：v1 习惯带 /query
    client = hypersync.HypersyncClient(ClientConfig(url=url, bearer_token=token))
    height = await client.get_height()
    to_block = a.to_block or height
    os.makedirs(a.outdir, exist_ok=True)
    start = find_resume_block(a.outdir, a.from_block, to_block, a.token_addr, url)
    if start > a.from_block:
        print(f"[resume] 从已验证 manifest 的 next_block {start} 续拉", flush=True)
    if start >= to_block:
        sys.exit(f"[fail-closed] resume start {start} >= to_block {to_block}; "
                 "请求为空或已完成，拒绝写空完成记录")
    run_dir = os.path.join(a.outdir, f"run_{start}")
    os.makedirs(run_dir, exist_ok=True)
    query = Query(
        from_block=start,
        to_block=to_block,
        logs=[LogSelection(address=[a.token_addr.lower()], topics=[[TRANSFER]])],
        field_selection=FieldSelection(
            log=[LogField.BLOCK_NUMBER, LogField.BLOCK_HASH, LogField.LOG_INDEX,
                 LogField.TRANSACTION_HASH, LogField.TOPIC1, LogField.TOPIC2,
                 LogField.DATA],
            block=[BlockField.NUMBER, BlockField.TIMESTAMP],
        ),
    )
    cfg = StreamConfig(hex_output=HexOutput.PREFIXED, concurrency=a.concurrency)
    t0 = time.time()
    await client.collect_parquet(run_dir, query, cfg)
    el = time.time() - t0
    try:
        files = inspect_run_files(run_dir, start, to_block)
    except ValueError as exc:
        sys.exit(f"[fail-closed] collected Parquet validation failed: {exc}")
    for name in files:
        with open(os.path.join(run_dir, name), "rb") as f:
            os.fsync(f.fileno())
    done = {"schema": MANIFEST_SCHEMA, "query_schema": QUERY_SCHEMA,
               "capture_from": a.from_block, "next_block": to_block,
               "from_block": start, "to_block": to_block, "elapsed_s": round(el, 1),
               "token": a.token_addr.lower(), "url": url,
               "client_version": getattr(hypersync, "__version__", "unknown"),
               "files": files}
    atomic_write_json(os.path.join(run_dir, "done.json"), done)
    print(f"[COMPLETE] [{start},{to_block}) -> {run_dir} 用时 {el:.0f}s", flush=True)


def verify_done_cli(argv):
    ap = argparse.ArgumentParser(description="Revalidate a HyperSync v2 done receipt and Parquets")
    ap.add_argument("--done", required=True)
    ap.add_argument("--capture-from", required=True, type=int)
    ap.add_argument("--to-block", required=True, type=int)
    ap.add_argument("--token-addr", required=True)
    ap.add_argument("--url", required=True)
    a = ap.parse_args(argv)
    url = re.sub(r"/query/?$", "", a.url.rstrip("/"))
    try:
        validate_done_manifest(a.done, a.capture_from, a.to_block, a.token_addr, url)
    except ValueError as exc:
        print(f"[fail-closed] {exc}", file=sys.stderr)
        return 2
    print(f"[verified] {a.done}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "verify-done":
        sys.exit(verify_done_cli(sys.argv[2:]))
    asyncio.run(main())
