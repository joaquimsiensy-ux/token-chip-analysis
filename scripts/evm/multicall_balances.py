#!/usr/bin/env python3
"""用 Multicall3 批量查询一批地址的 ERC20 当前余额(每批 200 地址一次 eth_call,公共节点轮换)。
来源：SIREN(BSC) 分析会话实战产物, 2026-07。
用法：无命令行参数；TOKEN/输入地址文件路径/输出路径均硬编码在脚本内（原值为 SIREN 会话
scratchpad 路径），跑前按标的改 TOKEN、__main__ 里的输入输出路径。encode/decode 与
query() 为通用件可直接复用；Multicall3 合约 0xca11bde0…76ca11 各链同地址。
"""
import requests, json, sys, time, random

D = "/private/tmp/claude-502/-Users-uravvv-Desktop-----fable----/02251dc4-e11a-419c-b617-7991c8cb72f2/scratchpad/siren/data"
TOKEN = "0x997a58129890bbda032231a52ed1ddc845fc18e1"
MC3 = "0xca11bde05977b3631167028862be2a173976ca11"
NODES = ["https://bsc-rpc.publicnode.com", "https://bsc.drpc.org",
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

def query(addrs_all, label):
    res = {}
    B = 200
    for i in range(0, len(addrs_all), B):
        batch = addrs_all[i:i+B]
        data = encode_aggregate3(batch)
        ok = False
        for attempt in range(8):
            n = random.choice(NODES)
            try:
                r = requests.post(n, json={"jsonrpc": "2.0", "id": 1, "method": "eth_call",
                                           "params": [{"to": MC3, "data": data}, "latest"]},
                                  timeout=30).json()
                if "result" in r and r["result"] and r["result"] != "0x":
                    vals = decode_aggregate3(r["result"], len(batch))
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

if __name__ == "__main__":
    SP = "/private/tmp/claude-502/-Users-uravvv-Desktop-----fable----/02251dc4-e11a-419c-b617-7991c8cb72f2/scratchpad"
    addrs = []
    dist_amt = {}
    for l in open(f"{SP}/siren_bnb_distribution_recipients.txt"):
        parts = l.strip().split()
        if parts and parts[0].startswith("0x") and len(parts[0]) == 42:
            a = parts[0].lower()
            addrs.append(a)
            if len(parts) >= 2:
                try: dist_amt[a] = float(parts[1])
                except ValueError: pass
    json.dump(dist_amt, open(f"{D}/entity986_bnb_dist.json", "w"))
    core = ["0xd8c78fe899d3828f16ce5771939a69029102c187",
            "0xfe5bcc32063ced8384507d41c334ead5c70fbb56",
            "0xf3689a9546c7e6fd466c8cd4a36f71891d72b2a8",
            "0x4fafd85f669245856e0d5f7b7264a5c7d23e1eb1"]
    allq = list(dict.fromkeys(addrs + core))
    res = query(allq, "SIREN余额")
    json.dump(res, open(f"{D}/entity986_balances.json", "w"))
    hold = [(a, b) for a, b in res.items() if b and b > 1]
    tot = sum(b for _, b in hold)
    fails = sum(1 for v in res.values() if v is None)
    print(f"\n地址总数 {len(allq)},查询失败 {fails}")
    print(f"当前仍持币(>1枚): {len(hold)} 个,合计 {tot:,.0f} SIREN = {tot/1e9*100:.4f}% 供应")
    for a, b in sorted(hold, key=lambda x: -x[1])[:20]:
        print(f"  {a}  {b:,.0f}  ({b/1e9*100:.4f}%)")
