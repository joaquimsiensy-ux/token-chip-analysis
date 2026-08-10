#!/usr/bin/env python3
"""alchemy_getAssetTransfers 全量拉取 ERC20 转账(自带块时间戳,1000条/页),断点续传+块段接力。
来源：SIREN(BSC) 会话实战产物 2026-07；v2.26 参数化+块段接力（PING(Base) 分析，2026-07-17）。

用法（config 模式，key 不落 skill 目录）：
  python3 fetch_alchemy.py --config config.json --chain <eth|bsc|base> \
      --out-dir data_alchemy [--from-block N --to-block M]
  config.json 字段：
    alchemy_key      Alchemy API key（从 ~/.claude/api-keys.md 登记文件取用）
    alchemy_network  eth-mainnet / bnb-mainnet / base-mainnet 等（*.g.alchemy.com 国内须走 clash 代理）
    token            目标代币合约地址
    proxy            可选，如 http://127.0.0.1:7897（不填则用系统/环境变量代理）

块段接力（Base 双通道拓扑，见 data-pipeline-evm §8.1）：
  多进程各管一段：用 --from-block/--to-block 划互斥块段并行拉，各段独立 --out-dir；
  与 HyperSync 段拼接时必须用 replay_pass1.py 按块段划通道归属去重
  （HyperSync/Alchemy 的 uniqueId 尾号语义不同，跨通道直接按尾号去重必错）。
断点续传：不依赖会过期的 pageKey，按已有 CSV 末行区块重叠续拉、段内靠 uniqueId 去重；
免费层高峰期可遇平台级 "global traffic" 限流（实测可整夜不可用），中断后重跑即续。
"""
import json, csv, os, sys, time, argparse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from chain_registry import attested_evm_chains
from net import RpcAttestationError, attested_rpc_pool


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="config.json（alchemy_key/alchemy_network/token/proxy）")
    ap.add_argument("--out-dir", default=".", help="输出目录（transfers_full.csv 所在）")
    ap.add_argument("--from-block", type=int, default=0, help="起始块（含）；有已存 CSV 时取 max(末行块,此值)")
    ap.add_argument("--to-block", type=int, default=None, help="终止块（含）；缺省 latest")
    ap.add_argument("--receipt", help="成功收尾后写正式 evm-collector-run/v2（须显式块界）")
    ap.add_argument("--chain", required=True,
                    choices=sorted(attested_evm_chains()),
                    help="目标链；chain id 只读 chain_registry")
    a = ap.parse_args()

    cfg = json.load(open(a.config))
    key, token = cfg.get("alchemy_key", ""), cfg.get("token", "")
    if not key or not token:
        sys.exit("config 缺 alchemy_key/token（key 从 ~/.claude/api-keys.md 取用，不写死进 skill 目录）")
    ep = f"https://{cfg.get('alchemy_network', 'base-mainnet')}.g.alchemy.com/v2/{key}"
    proxy = cfg.get("proxy") or None
    pool = attested_rpc_pool(ep, a.chain, formal=True, proxy=proxy,
                             rps=4, concurrency=1, attempts=6)
    try:
        pool.attest()
    except RpcAttestationError as exc:
        print(f"[fatal] RPC chain attestation failed: {exc}", file=sys.stderr)
        return 1
    os.makedirs(a.out_dir, exist_ok=True)
    out = os.path.join(a.out_dir, "transfers_full.csv")
    existed_before = os.path.exists(out) and os.path.getsize(out) > 0
    if a.receipt and (a.to_block is None or existed_before):
        ap.error("正式 Alchemy receipt 要求显式 --to-block 且输出运行前不存在")
    ckpt = os.path.join(a.out_dir, "alchemy_pagekey.json")
    pagekey = None
    mode = "w"
    start = a.from_block
    if os.path.exists(out) and os.path.getsize(out) > 100:
        # 从已有文件的最后区块续拉(pageKey 可能过期,不依赖它)
        with open(out, "rb") as fh:
            fh.seek(max(-4096, -os.path.getsize(out)), os.SEEK_END)
            last = fh.read().decode("utf-8", "replace").strip().split("\n")[-1]
        try:
            start = max(start, int(last.split(",")[0]))  # 重叠最后一个区块,靠 uniqueId 去重
            mode = "a"
            print(f"[resume] from block {start}", flush=True)
        except ValueError:
            pass
    f = open(out, mode, newline="")
    w = csv.writer(f)
    if mode == "w":
        w.writerow(["block", "ts", "tx", "from", "to", "value_raw", "uniqueId"])
    total, page, t0 = 0, 0, time.time()
    to_block_hex = hex(a.to_block) if a.to_block is not None else "latest"
    while True:
        params = {"fromBlock": hex(start), "toBlock": to_block_hex, "contractAddresses": [token],
                  "category": ["erc20"], "maxCount": "0x3e8", "order": "asc", "withMetadata": True}
        if pagekey:
            params["pageKey"] = pagekey
        ok = False
        for attempt in range(14):
            try:
                response = pool.call("alchemy_getAssetTransfers", [params])
                if response.get("ok") and isinstance(response.get("result"), dict):
                    r = {"result": response["result"]}
                    ok = True
                    break
                err = str(response.get("error", ""))
                if "429" in err or "rate" in err.lower() or "capacity" in err.lower() or "exceeded" in err.lower():
                    wait_s = min(1200, 20 * (attempt + 1) ** 1.5)
                    print(f"[429] attempt {attempt+1}, wait {wait_s:.0f}s", flush=True)
                    time.sleep(wait_s)
                else:
                    print(f"[err] {err[:120]}", flush=True)
                    time.sleep(5)
            except Exception:
                time.sleep(5)
        if not ok:
            print("[fatal] page fetch failed, exiting for cooldown restart", flush=True)
            f.close()
            sys.exit(2)
        res = r["result"]
        ts_list = res.get("transfers", [])
        for t in ts_list:
            raw = (t.get("rawContract") or {}).get("value")
            val = int(raw, 16) if raw else int((t.get("value") or 0) * 1e18)
            w.writerow([int(t["blockNum"], 16),
                        (t.get("metadata") or {}).get("blockTimestamp", ""),
                        t["hash"], t["from"], t["to"] or "", val, t.get("uniqueId", "")])
        total += len(ts_list)
        page += 1
        pagekey = res.get("pageKey")
        json.dump({"pageKey": pagekey, "total_so_far": total}, open(ckpt, "w"))
        if page % 20 == 0:
            f.flush()
            last_ts = ts_list[-1].get("metadata", {}).get("blockTimestamp", "?") if ts_list else "?"
            print(f"[prog] page {page}, total {total}, at {last_ts}, {time.time()-t0:.0f}s", flush=True)
        if not pagekey:
            break
        time.sleep(1.5)
    f.close()
    if a.receipt:
        from csv_collector_receipt import emit_native_receipt
        emit_native_receipt(out, a.receipt, __file__, token, ep.rsplit("/", 1)[0],
                            a.from_block, a.to_block + 1, a.to_block + 1,
                            fresh_output=not existed_before)
    print(f"[COMPLETE] {total} transfers this run, {page} pages, {time.time()-t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
