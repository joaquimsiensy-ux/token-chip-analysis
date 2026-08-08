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

用法：python3 fetch_pool_swaps.py [--token-file <文件>] --pool 0x.. --from-block N --to-block M \
        --out data/pool_swaps.csv [--topic <swap_topic0>] [--url https://bsc.hypersync.xyz/query]
  token 优先级：显式 --token-file > HYPERSYNC_TOKEN > ~/.config/hypersync/token；禁止位置参数明文传入。
（来源：SIREN(BSC) 分析实战产物，2026-07-19）"""
import requests, json, csv, time, argparse, sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from artifact_quarantine import quarantine_current

PANCAKE_V3 = "0x19b47279256b2a23a1665c810c8d55a1758940ee09377d4f8d26497a3577dc83"
DEFAULT_TOKEN_FILE = "~/.config/hypersync/token"

def _load_token(ap, token_file):
    if token_file is not None:
        path = os.path.expanduser(token_file)
    else:
        env_token = os.environ.get("HYPERSYNC_TOKEN", "").strip()
        if env_token:
            return env_token
        path = os.path.expanduser(DEFAULT_TOKEN_FILE)
    try:
        token = Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        token = ""
    if not token:
        ap.error(f"HyperSync token 文件缺失或为空：{path}；key 登记见 ~/.claude/api-keys.md §1")
    return token


def parse_args(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--token-file", default=None,
                    help="token 文件；显式给出时优先于 HYPERSYNC_TOKEN")
    ap.add_argument("--pool", required=True)
    ap.add_argument("--from-block", type=int, required=True)
    ap.add_argument("--to-block", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--topic", default=PANCAKE_V3, help="Swap event topic0（默认 Pancake V3）")
    ap.add_argument("--url", default="https://bsc.hypersync.xyz/query")
    a = ap.parse_args(argv)
    if a.from_block < 0 or a.to_block < 0 or a.from_block >= a.to_block:
        ap.error("块区间必须满足 0 <= from-block < to-block")
    a.token = _load_token(ap, a.token_file)
    return a


def main():
    a = parse_args()
    headers = {"Authorization": f"Bearer {a.token}", "Content-Type": "application/json"}
    out_path = Path(os.path.abspath(os.path.expanduser(a.out)))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        stale = quarantine_current(out_path)
    except Exception as exc:
        print(f"[fatal] 旧 canonical 无法退出本次正式位置: {exc}", flush=True)
        return 1
    if stale is not None:
        print(f"[stale] previous canonical moved to {stale}", flush=True)
    tmp_path = out_path.with_name(f".{out_path.name}.tmp.{os.getpid()}")
    out_file = tmp_path.open("x", newline="")
    out = csv.writer(out_file)
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
            out_file.close()
            tmp_path.unlink(missing_ok=True)
            return 2
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
        if isinstance(nxt, bool) or not isinstance(nxt, int):
            print(f"[fatal] provider 缺整数 next_block，current={cur} to_block={a.to_block}",
                  flush=True)
            out_file.close()
            tmp_path.unlink(missing_ok=True)
            return 2
        if nxt <= cur:
            print(f"[fatal] next_block 停滞，current={cur} next_block={nxt} "
                  f"to_block={a.to_block}", flush=True)
            out_file.close()
            tmp_path.unlink(missing_ok=True)
            return 2
        cur = nxt
        time.sleep(0.5)
    out_file.flush(); os.fsync(out_file.fileno()); out_file.close()
    os.replace(tmp_path, out_path)
    print(f"swaps {n} rows {time.time()-t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
