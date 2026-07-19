#!/usr/bin/env python3
"""采 DEX 池 Swap 事件（HyperSync）→ 反解链上价格，重建无 CEX K 线的早期行情/吸筹成本。

用途：发射期/老币早期段无第三方 K 线时，用主池 Swap 的 sqrtPriceX96 反解日中位价，
      给"庄家吸筹加权成本"提供价格轴（SIREN 用 2025-02~03 池 Swap 重建吸筹成本 $0.0375）。

★池版本决定 Swap topic（按错版本静默 0 行）：
  - PancakeSwap V3: 0x19b47279256b2a23a1665c810c8d55a1758940ee09377d4f8d26497a3577dc83
    data 布局 7×32B: amount0,amount1,sqrtPriceX96,liquidity,tick,protocolFeesToken0,protocolFeesToken1
  - Uniswap V3:      0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67
    data 布局 5×32B: amount0,amount1,sqrtPriceX96,liquidity,tick
  用前先对目标池发一小段实测 topic0 分布（见 data-pipeline-evm.md §6 坑表）。

价格反解：price(token1/token0) = (sqrtPriceX96 / 2**96)**2
  标的与配对币按地址字典序定 token0/token1；标的是 token0 时该值=配对币/标的，
  ×配对币 USD 价得标的 USD 价。反解在下游脚本做（本件只落原始 data，不猜 token 顺序）。

用法：python3 fetch_pool_swaps.py <envio_token> --pool 0x.. --from-block N --to-block M \
        --out data/pool_swaps.csv [--topic <swap_topic0>] [--url https://bsc.hypersync.xyz/query]
  envio_token 从 ~/.claude/api-keys.md 取用（铁律 5：不写死进脚本）。
（来源：SIREN(BSC) 分析实战产物，2026-07-19）"""
import requests, json, csv, time, argparse

PANCAKE_V3 = "0x19b47279256b2a23a1665c810c8d55a1758940ee09377d4f8d26497a3577dc83"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("api_token")
    ap.add_argument("--pool", required=True)
    ap.add_argument("--from-block", type=int, required=True)
    ap.add_argument("--to-block", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--topic", default=PANCAKE_V3, help="Swap event topic0（默认 Pancake V3）")
    ap.add_argument("--url", default="https://bsc.hypersync.xyz/query")
    a = ap.parse_args()
    headers = {"Authorization": f"Bearer {a.api_token}", "Content-Type": "application/json"}
    out = csv.writer(open(a.out, "w", newline=""))
    out.writerow(["block", "ts", "tx", "data"])
    cur, n, t0 = a.from_block, 0, time.time()
    s = requests.Session()
    while cur < a.to_block:
        q = {"from_block": cur, "to_block": a.to_block,
             "logs": [{"address": [a.pool.lower()], "topics": [[a.topic]]}],
             "field_selection": {"log": ["block_number", "transaction_hash", "data"],
                                 "block": ["number", "timestamp"]}}
        j = None
        for att in range(8):
            try:
                r = s.post(a.url, json=q, headers=headers, timeout=90)
                if r.status_code == 200:
                    j = r.json()
                    break
            except Exception:
                pass
            time.sleep(3 * (att + 1))
        if j is None:
            print("[fatal] giving up", flush=True)
            break
        bts = {}
        for batch in j.get("data", []):
            for b in batch.get("blocks", []):
                ts = b.get("timestamp")
                bts[int(b["number"])] = int(ts, 16) if isinstance(ts, str) else int(ts)
            for lg in batch.get("logs", []):
                bn = int(lg["block_number"])
                out.writerow([bn, bts.get(bn, ""), lg["transaction_hash"], lg["data"]])
                n += 1
        nxt = j.get("next_block")
        if not nxt or nxt <= cur:
            break
        cur = nxt
        time.sleep(0.5)
    print(f"swaps {n} rows {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
