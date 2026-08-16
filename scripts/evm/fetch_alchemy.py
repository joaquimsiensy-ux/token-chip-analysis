#!/usr/bin/env python3
"""alchemy_getAssetTransfers 全量拉取 ERC20 转账(自带块时间戳,1000条/页),断点续传+块段接力。
来源：SIREN(BSC) 会话实战产物 2026-07；v2.26 参数化+块段接力（PING(Base) 分析，2026-07-17）。

用法（config 模式，key 不落 skill 目录）：
  python3 fetch_alchemy.py --config config.json --chain <eth|bsc|base> \
      --out-dir data_alchemy [--from-block N --to-block M]
  config.json 字段：
    alchemy_key      Alchemy API key（从 ~/.claude/api-keys.md 登记文件取用）
    alchemy_network  eth-mainnet / bnb-mainnet / base-mainnet 等（受限网络需代理）
    token            目标代币合约地址
    proxy            可选代理 URL；推荐由 CHIP_PROXY 统一配置后写入本字段

块段接力（Base 双通道拓扑，见 data-pipeline-evm §8.1）：
  多进程各管一段：用 --from-block/--to-block 划互斥块段并行拉，各段独立 --out-dir；
  与 HyperSync 段拼接时必须用 replay_pass1.py 按块段划通道归属去重
  （HyperSync/Alchemy 的 uniqueId 尾号语义不同，跨通道直接按尾号去重必错）。
断点续传：不依赖会过期的 pageKey，按已有 CSV 末行区块重叠续拉、段内靠 uniqueId 去重；
免费层高峰期可遇平台级 "global traffic" 限流（实测可整夜不可用），中断后重跑即续。

正式资格说明：Alchemy 协议仅提供分页 pageKey，没有 provider 侧块进度证据，
`evm-collector-run/v2` 的块游标语义不成立。因此本采集器仅支持探索采集，不支持正式
receipt；恢复正式资格需要后续升版为分型收据。
"""
import json, csv, os, re, sys, time, argparse

FORMAL_CHANNEL_ELIGIBLE = False

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from chain_registry import attested_evm_chains
from net import RpcAttestationError, attested_rpc_pool


def validate_transfers_page(res, req_from, req_to, seen_pagekeys):
    """Validate a complete Alchemy page before any row is published."""
    if not isinstance(res, dict) or "transfers" not in res \
            or not isinstance(res["transfers"], list):
        raise ValueError("Alchemy result must contain a transfers list")
    transfers = res["transfers"]
    for index, transfer in enumerate(transfers):
        if not isinstance(transfer, dict):
            raise ValueError(f"Alchemy transfer[{index}] must be an object")
        block_hex = transfer.get("blockNum")
        if not isinstance(block_hex, str) \
                or re.fullmatch(r"0x[0-9a-fA-F]+", block_hex) is None:
            raise ValueError(f"Alchemy transfer[{index}] has invalid blockNum")
        block_num = int(block_hex, 16)
        if block_num < req_from or (req_to is not None and block_num > req_to):
            raise ValueError(f"Alchemy transfer[{index}] blockNum escapes requested interval")
        for field in ("hash", "from", "uniqueId"):
            value = transfer.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Alchemy transfer[{index}] has invalid {field}")
        if "to" not in transfer:
            raise ValueError(f"Alchemy transfer[{index}] is missing to")
        raw_contract = transfer.get("rawContract")
        raw = raw_contract.get("value") if isinstance(raw_contract, dict) else None
        if not isinstance(raw, str) \
                or re.fullmatch(r"0x[0-9a-fA-F]+", raw) is None:
            raise ValueError(f"Alchemy transfer[{index}] has invalid rawContract.value")
    page_key = None
    if "pageKey" in res:
        page_key = res["pageKey"]
        if not isinstance(page_key, str) or not page_key.strip():
            raise ValueError("Alchemy pageKey must be a non-empty string when present")
        if page_key in seen_pagekeys:
            raise ValueError("Alchemy pageKey repeated")
        seen_pagekeys.add(page_key)
    return transfers, page_key


def _quarantine_new_output(path):
    if not os.path.lexists(path):
        return None
    candidate = path + ".partial"
    suffix = 1
    while os.path.lexists(candidate):
        candidate = f"{path}.{suffix}.partial"
        suffix += 1
    os.rename(path, candidate)
    return candidate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="config.json（alchemy_key/alchemy_network/token/proxy）")
    ap.add_argument("--out-dir", default=".", help="输出目录（transfers_full.csv 所在）")
    ap.add_argument("--from-block", type=int, default=0, help="起始块（含）；有已存 CSV 时取 max(末行块,此值)")
    ap.add_argument("--to-block", type=int, default=None, help="终止块（含）；缺省 latest")
    ap.add_argument(
        "--receipt",
        help="已除名：Alchemy 无 provider 侧完成证据，不支持正式 receipt，仅探索采集",
    )
    ap.add_argument("--chain", required=True,
                    choices=sorted(attested_evm_chains()),
                    help="目标链；chain id 只读 chain_registry")
    a = ap.parse_args()
    if a.receipt:
        ap.error("Alchemy 通道无 provider 侧完成证据，不支持正式 receipt，仅探索采集；正式备用通道请用 SQD")

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
    f = None
    opened = False
    success = False
    try:
        f = open(out, mode, newline="")
        opened = True
        w = csv.writer(f)
        if mode == "w":
            w.writerow(["block", "ts", "tx", "from", "to", "value_raw", "uniqueId"])
        total, page, t0 = 0, 0, time.time()
        to_block_hex = hex(a.to_block) if a.to_block is not None else "latest"
        seen_pagekeys = set()
        while True:
            params = {"fromBlock": hex(start), "toBlock": to_block_hex, "contractAddresses": [token],
                      "category": ["erc20"], "maxCount": "0x3e8", "order": "asc", "withMetadata": True}
            if pagekey:
                params["pageKey"] = pagekey
            ok = False
            ts_list, next_pagekey = None, None
            for attempt in range(14):
                try:
                    response = pool.call("alchemy_getAssetTransfers", [params])
                    if response.get("ok"):
                        try:
                            ts_list, next_pagekey = validate_transfers_page(
                                response.get("result"), start, a.to_block, seen_pagekeys)
                        except ValueError as exc:
                            print(f"[protocol] attempt {attempt+1}: {str(exc)[:120]}", flush=True)
                            time.sleep(5)
                            continue
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
                except Exception as exc:
                    print(f"[exc] {str(exc)[:120]}", flush=True)
                    time.sleep(5)
            if not ok:
                print("[fatal] page fetch failed or remained invalid after retries", flush=True)
                sys.exit(2)
            for transfer in ts_list:
                raw = transfer["rawContract"]["value"]
                w.writerow([int(transfer["blockNum"], 16),
                            (transfer.get("metadata") or {}).get("blockTimestamp", ""),
                            transfer["hash"], transfer["from"], transfer["to"] or "",
                            int(raw, 16), transfer["uniqueId"]])
            total += len(ts_list)
            page += 1
            pagekey = next_pagekey
            with open(ckpt, "w") as checkpoint:
                json.dump({"pageKey": pagekey, "total_so_far": total}, checkpoint)
            if page % 20 == 0:
                f.flush()
                last_ts = ts_list[-1].get("metadata", {}).get("blockTimestamp", "?") if ts_list else "?"
                print(f"[prog] page {page}, total {total}, at {last_ts}, {time.time()-t0:.0f}s", flush=True)
            if not pagekey:
                break
            time.sleep(1.5)
        f.close()
        print(f"[COMPLETE] {total} transfers this run, {page} pages, {time.time()-t0:.0f}s", flush=True)
        success = True
        return 0
    finally:
        if f is not None and not f.closed:
            f.close()
        if opened and not success:
            if mode == "w":
                partial = _quarantine_new_output(out)
                if partial:
                    print(f"[warning] incomplete Alchemy output moved to {partial}", flush=True)
            else:
                print("[warning] incomplete Alchemy resume left existing output in place", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
