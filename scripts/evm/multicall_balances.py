#!/usr/bin/env python3
"""用 Multicall3 批量查询一批地址的 ERC20 当前余额(每批 200 地址一次 eth_call,公共节点轮换)。

用法：python3 scripts/evm/multicall_balances.py --chain bsc --token 0x... --input addresses.txt \
  --out balances.json [--rpc https://... --rpc https://...]
输入文件须一行一个地址。默认节点均为 BSC 公共节点；查询其他 EVM 链必须显式传 --rpc。
encode/decode 与 query() 为通用件；Multicall3 合约 0xca11bde0…76ca11 各链同地址。
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from chain_registry import attested_evm_chains
from net import RpcAttestationError, attested_rpc_pool

TOKEN = None
MC3 = "0xca11bde05977b3631167028862be2a173976ca11"
DEFAULT_BSC_NODES = ["https://bsc-rpc.publicnode.com", "https://bsc.drpc.org",
                     "https://bsc-dataseed.bnbchain.org", "https://bsc-dataseed1.defibit.io"]

def encode_aggregate3(addrs):
    n = len(addrs)
    head = "82ad56cb" + hex(32)[2:].rjust(64, "0") + hex(n)[2:].rjust(64, "0")
    offsets = ""
    elems = ""
    elem_size = 0xC0
    for i, a in enumerate(addrs):
        offsets += hex(n * 32 + i * elem_size)[2:].rjust(64, "0")
        calldata = "70a08231" + a[2:].lower().rjust(64, "0")
        elems += (TOKEN[2:].rjust(64, "0")          # target
                  + "1".rjust(64, "0")               # allowFailure = true
                  + hex(0x60)[2:].rjust(64, "0")     # bytes offset
                  + hex(len(calldata)//2)[2:].rjust(64, "0")  # bytes len 0x24
                  + calldata.ljust(128, "0"))        # calldata padded 2 words
    return "0x" + head + offsets + elems

def decode_aggregate3(hexdata, n):
    b = bytes.fromhex(hexdata[2:])
    # 顶层: offset(32) -> 数组区
    arr = int.from_bytes(b[0:32], "big")
    ln = int.from_bytes(b[arr:arr+32], "big")
    assert ln == n, (ln, n)
    base = arr + 32
    out = []
    for i in range(n):
        off = int.from_bytes(b[base+i*32:base+(i+1)*32], "big")
        p = base + off
        success = int.from_bytes(b[p:p+32], "big")
        do = int.from_bytes(b[p+32:p+64], "big")
        dlen = int.from_bytes(b[p+do:p+do+32], "big")
        data = b[p+do+32:p+do+32+dlen]
        val = int.from_bytes(data, "big") if (success and dlen >= 32) else None
        out.append(val)
    return out

def query(pool, addrs_all, label):
    res = {}
    B = 200
    for i in range(0, len(addrs_all), B):
        batch = addrs_all[i:i+B]
        data = encode_aggregate3(batch)
        ok = False
        for attempt in range(8):
            try:
                result = pool.call("eth_call", [{"to": MC3, "data": data}, "latest"])
                raw = result.get("result") if result.get("ok") else None
                if raw and raw != "0x":
                    vals = decode_aggregate3(raw, len(batch))
                    for a, v in zip(batch, vals):
                        res[a] = (v / 1e18) if v is not None else None
                    ok = True
                    break
            except Exception:
                pass
            time.sleep(0.5 * (attempt + 1))
        if not ok:
            for a in batch:
                res[a] = None
        print(f"[{label}] {min(i+B,len(addrs_all))}/{len(addrs_all)} done", flush=True)
    return res

def parse_args():
    parser = argparse.ArgumentParser(description="用 Multicall3 批量查询 ERC20 余额")
    parser.add_argument("--token", help="ERC20 token 合约地址")
    parser.add_argument("--input", help="地址清单文件，一行一个地址")
    parser.add_argument("--out", help="JSON 输出路径")
    parser.add_argument("--chain", default="bsc",
                        choices=sorted(attested_evm_chains()),
                        help="目标链（默认 bsc；chain id 只读 chain_registry）")
    parser.add_argument("--rpc", action="append", help=(
        "RPC URL，可多次传入；默认使用 4 个 BSC 公共节点，跨链必须显式传 --rpc"))
    args = parser.parse_args()
    missing = [name for name in ("token", "input", "out") if not getattr(args, name)]
    if missing:
        parser.error("缺少必填参数：" + "、".join("--" + name for name in missing))
    return args


def main():
    global TOKEN
    args = parse_args()
    TOKEN = args.token.lower()
    nodes = args.rpc or DEFAULT_BSC_NODES
    pool = attested_rpc_pool(nodes, args.chain, formal=True, rps=4, concurrency=1)
    try:
        pool.attest()
    except RpcAttestationError as exc:
        print(f"[fatal] RPC chain attestation failed: {exc}", file=sys.stderr)
        return 1
    addrs = []
    for line in open(args.input):
        address = line.strip().lower()
        if address:
            addrs.append(address)
    addrs = list(dict.fromkeys(addrs))
    res = query(pool, addrs, "余额")
    with open(args.out, "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    fails = sum(1 for value in res.values() if value is None)
    print(f"\n地址总数 {len(addrs)}, 查询失败 {fails}")
    print(f"[done] -> {args.out}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
