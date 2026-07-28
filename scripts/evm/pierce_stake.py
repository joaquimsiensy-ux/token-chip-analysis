#!/usr/bin/env python3
"""嵌套质押穿透器：Multicall3 批量读 RewardTracker 的 depositBalances(user, token)。

为什么需要它（GMX(Arbitrum) 2026-07-26 定，方法学见 playbook-supply-recon §8b）：
多层 RewardTracker 结构（主池 → Bonus 层 → Fee 层）下，用户的份额代币会被逐层
存入下一层，**份额代币的现货余额恒为 0**，只能靠 `mint−burn` 累计算出份额；而份额里
混着 escrow 版代币（esGMX 之类），必须再查 `depositBalances(user, 标的)` 才能拆出
**纯标的币存款**。实测同一标的不同实体的「纯币÷份额」比值可差 250 倍（小庄 1.0000、
项目方 0.0039），直接用份额代理会系统性高估持仓。

用法:
  # 1) 先用份额排序产出候选清单（每行 "地址,份额" 或纯地址）
  # 2) 再穿透（默认 selector 即 depositBalances(address,address)）
  python3 pierce_stake.py --tracker 0x质押合约 --token 0x标的 \
      --addrs stakers_ranked.csv --topn 1500 --out pierce.json \
      [--rpc https://arb1.arbitrum.io/rpc] [--batch 150] [--selector 0xf5d9d63e]

  # 单参数函数（如 stakedAmounts(address)）用 --one-arg
  python3 pierce_stake.py --tracker 0x... --addrs a.txt --out s.json \
      --selector 0x10c1c103 --one-arg

输出: {地址: 原始 wei 字符串}，只收录 >0 的地址。stderr 打印批次失败告警。

常用 selector（keccak 前 4 字节；自行核算勿凭记忆）:
  depositBalances(address,address) = 0xf5d9d63e
  stakedAmounts(address)          = 0x10c1c103
  balanceOf(address)              = 0x70a08231
算法: from Crypto.Hash import keccak; k=keccak.new(digest_bits=256); k.update(b'sig'); k.hexdigest()[:8]
（pycryptodome 本机可用；eth_hash/pysha3 未装。hashlib 的 sha3_256 是 NIST 版≠keccak，不能用）
"""
import argparse, json, sys, time

import requests

MC3 = "0xca11bde05977b3631167028862be2a173976ca11"
DEFAULT_NODES = ["https://arb1.arbitrum.io/rpc",
                 "https://arbitrum-one.publicnode.com",
                 "https://1rpc.io/arb"]


def _pad(addr):
    return addr[2:].lower().rjust(64, "0")


def encode_aggregate3(target, addrs, token=None, selector="f5d9d63e"):
    """aggregate3(Call3[]) 编码。token=None 时为单参数调用。

    ⚠ elem_size 必须跟着 calldata 长度变：Call3 头占 4 word（target/allowFailure/
    offset/len），data 段按 32 字节向上取整。36B calldata → 0xC0，68B → 0xE0。
    """
    n = len(addrs)
    cd_len = 4 + 32 + (32 if token else 0)
    data_words = (cd_len + 31) // 32
    elem_size = 32 * 4 + 32 * data_words
    head = "82ad56cb" + hex(32)[2:].rjust(64, "0") + hex(n)[2:].rjust(64, "0")
    offsets, elems = "", ""
    for i, a in enumerate(addrs):
        offsets += hex(n * 32 + i * elem_size)[2:].rjust(64, "0")
        cd = selector.lstrip("0x") + _pad(a) + (_pad(token) if token else "")
        elems += (_pad(target)                              # target
                  + "0" * 63 + "1"                          # allowFailure = true
                  + hex(0x60)[2:].rjust(64, "0")            # offset to bytes
                  + hex(cd_len)[2:].rjust(64, "0")          # bytes length
                  + cd.ljust(data_words * 64, "0"))         # data padded
    return "0x" + head + offsets + elems


def decode(res, n):
    """Result[] → [int|None]（success=false 或空返回记 None）。"""
    h = res[2:]
    arr_off = int(h[0:64], 16) * 2
    cnt = int(h[arr_off:arr_off + 64], 16)
    if cnt != n:
        raise ValueError(f"count mismatch {cnt} vs {n}")
    base = arr_off + 64
    out = []
    for i in range(n):
        eo = int(h[base + i * 64: base + (i + 1) * 64], 16) * 2 + base
        ok = int(h[eo:eo + 64], 16)
        bo = int(h[eo + 64:eo + 128], 16) * 2 + eo
        blen = int(h[bo:bo + 64], 16)
        data = h[bo + 64: bo + 64 + blen * 2]
        out.append(int(data, 16) if ok and blen >= 32 else None)
    return out


def query(nodes, target, addrs, token, selector):
    payload = encode_aggregate3(target, addrs, token, selector)
    err = "?"
    for attempt in range(6):
        node = nodes[attempt % len(nodes)]
        try:
            r = requests.post(node, json={"jsonrpc": "2.0", "id": 1, "method": "eth_call",
                                          "params": [{"to": MC3, "data": payload}, "latest"]},
                              timeout=60).json()
            if r.get("result") and r["result"] != "0x":
                return decode(r["result"], len(addrs))
            err = str(r.get("error"))[:120]
        except Exception as e:
            err = str(e)[:120]
        time.sleep(1.5)
    print(f"  [warn] batch of {len(addrs)} failed: {err}", file=sys.stderr)
    return [None] * len(addrs)


def load_addrs(path, topn):
    out = []
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        a = line.split(",")[0].strip().lower()
        if a.startswith("0x") and len(a) == 42:
            out.append(a)
        if topn and len(out) >= topn:
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tracker", required=True, help="质押/tracker 合约地址")
    ap.add_argument("--token", default=None, help="标的代币地址（单参数函数省略）")
    ap.add_argument("--addrs", required=True, help="候选地址文件（每行 地址 或 地址,份额）")
    ap.add_argument("--out", required=True)
    ap.add_argument("--topn", type=int, default=0, help="0=全部")
    ap.add_argument("--batch", type=int, default=150)
    ap.add_argument("--selector", default="0xf5d9d63e")
    ap.add_argument("--one-arg", action="store_true", help="单参数函数（忽略 --token）")
    ap.add_argument("--rpc", action="append", default=None, help="可多次传入，轮换")
    a = ap.parse_args()

    nodes = a.rpc or DEFAULT_NODES
    token = None if a.one_arg else a.token
    if not a.one_arg and not token:
        sys.exit("[fatal] 双参数调用必须给 --token（或加 --one-arg）")

    cand = load_addrs(a.addrs, a.topn)
    if not cand:
        sys.exit("[fatal] 候选地址为空——fail-closed，拒绝输出空结果")
    print(f"[pierce] {len(cand)} 个候选，batch={a.batch}, selector={a.selector}")

    res, nfail = {}, 0
    for i in range(0, len(cand), a.batch):
        chunk = cand[i:i + a.batch]
        vals = query(nodes, a.tracker, chunk, token, a.selector)
        for addr, v in zip(chunk, vals):
            if v is None:
                nfail += 1
            elif v > 0:
                res[addr] = v
        print(f"  {min(i + a.batch, len(cand))}/{len(cand)}", flush=True)
        time.sleep(0.3)

    json.dump({k: str(v) for k, v in res.items()}, open(a.out, "w"))
    tot = sum(res.values()) / 1e18
    print(f"[pierce] 查得 {len(res)} 个非零地址，合计 {tot:,.4f}（decimals=18 口径）"
          f"{f'，{nfail} 个查询失败' if nfail else ''} -> {a.out}")
    if nfail:
        print("  [warn] 有查询失败，勿把结果当完整覆盖；对账时以覆盖率如实报告", file=sys.stderr)


if __name__ == "__main__":
    main()
