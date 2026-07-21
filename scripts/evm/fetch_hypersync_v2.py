#!/usr/bin/env python3
"""HyperSync 官方客户端采集器 v2（Rust 内核自动并发 + Parquet 直写）。
与 v1（fetch_hypersync.py 手写 JSON 轮询）的差别：传输为压缩二进制、客户端内部并发流水线
（掩盖 RTT——v3.11.2 POC 实测正是 RTT 主导瓶颈）、直接落 Parquet 免逐行 CSV。

用法: python3 fetch_hypersync_v2.py <api_token> <from_block> \
        --url https://bsc.hypersync.xyz --token-addr 0x标的 --outdir data/v2 \
        [--to-block N] [--concurrency 10]
  - --url 注意是裸域名（官方客户端自己拼路径，不要带 /query）
  - --concurrency 官方默认 10；高密度合约建议 20 起调；免费层别超 4（限流）
  - 断点续传：--outdir 已有 run_*/ 时自动从最大 next_block 续拉，新数据落新 run_<from>/ 子目录
输出: <outdir>/run_<from>/logs.parquet + blocks.parquet
  下游用 transfers_lib.py 的 read_transfers() 合成标准 8 列表（自动 join 时间戳）。
（来源：v3.11.2 采集加速工程，2026-07-21）"""
import argparse, asyncio, glob, json, os, re, time

import hypersync
from hypersync import (BlockField, ClientConfig, FieldSelection, HexOutput,
                       LogField, LogSelection, Query, StreamConfig)

TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def find_resume_block(outdir, default_from):
    """扫描已有 run_*/done.json 取最大 next_block 作为续拉起点。"""
    best = default_from
    for f in glob.glob(os.path.join(outdir, "run_*", "done.json")):
        try:
            nb = json.load(open(f)).get("next_block", 0)
            best = max(best, nb)
        except Exception:
            pass
    return best


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("api_token")
    ap.add_argument("from_block", type=int)
    ap.add_argument("--url", default="https://bsc.hypersync.xyz")
    ap.add_argument("--token-addr", required=True)
    ap.add_argument("--outdir", default="data/v2")
    ap.add_argument("--to-block", type=int, default=None)
    ap.add_argument("--concurrency", type=int, default=10)
    a = ap.parse_args()
    url = re.sub(r"/query/?$", "", a.url.rstrip("/"))  # 容错：v1 习惯带 /query
    os.makedirs(a.outdir, exist_ok=True)
    start = find_resume_block(a.outdir, a.from_block)
    if start > a.from_block:
        print(f"[resume] 从上次 next_block {start} 续拉", flush=True)
    client = hypersync.HypersyncClient(ClientConfig(url=url, bearer_token=a.api_token))
    height = await client.get_height()
    to_block = a.to_block or height
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
    json.dump({"next_block": to_block, "from_block": start, "elapsed_s": round(el, 1),
               "token": a.token_addr.lower(), "url": url},
              open(os.path.join(run_dir, "done.json"), "w"))
    print(f"[COMPLETE] [{start},{to_block}) -> {run_dir} 用时 {el:.0f}s", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
