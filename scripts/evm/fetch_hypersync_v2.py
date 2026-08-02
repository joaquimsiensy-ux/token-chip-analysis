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
import argparse, asyncio, glob, json, os, re, sys, time

import hypersync
from hypersync import (BlockField, ClientConfig, FieldSelection, HexOutput,
                       LogField, LogSelection, Query, StreamConfig)

TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
MANIFEST_SCHEMA = "hypersync-v2-done/v2"
QUERY_SCHEMA = "erc20-transfer-fields/v2"


def find_resume_block(outdir, default_from, to_block, token_addr, url):
    """Resume only manifests bound to the same capture identity and bounds."""
    best = default_from
    for f in glob.glob(os.path.join(outdir, "run_*", "done.json")):
        try:
            d = json.load(open(f))
        except Exception as exc:
            raise SystemExit(f"[fail-closed] unreadable done manifest {f}: {exc}")
        if int(d.get("capture_from", -1)) != int(default_from):
            continue
        expected = {"schema": MANIFEST_SCHEMA, "query_schema": QUERY_SCHEMA,
                    "token": token_addr.lower(), "url": url}
        if any(d.get(k) != v for k, v in expected.items()):
            raise SystemExit(f"[fail-closed] done manifest identity mismatch: {f}")
        frm, end, nb = int(d.get("from_block", -1)), int(d.get("to_block", -1)), int(d.get("next_block", -1))
        if not (default_from <= frm < end == nb <= to_block):
            raise SystemExit(f"[fail-closed] done manifest bounds invalid/outside request: {f}")
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
    json.dump({"schema": MANIFEST_SCHEMA, "query_schema": QUERY_SCHEMA,
               "capture_from": a.from_block, "next_block": to_block,
               "from_block": start, "to_block": to_block, "elapsed_s": round(el, 1),
               "token": a.token_addr.lower(), "url": url,
               "client_version": getattr(hypersync, "__version__", "unknown")},
              open(os.path.join(run_dir, "done.json"), "w"))
    print(f"[COMPLETE] [{start},{to_block}) -> {run_dir} 用时 {el:.0f}s", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
