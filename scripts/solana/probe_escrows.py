# 收编自 CLUDE(Solana) 分析 2026-07-13；标的专属地址列表请按新标的替换（TARGETS/WHALES 常量或改造为 argparse）
#!/usr/bin/env python3
"""探查 escrow/PDA 账户：最老创建交易 + Streamflow stream 元数据解码。

对每个目标账户：
1. getSignaturesForAddress 翻到最老（limit 1000 + before 游标）
2. 最老 tx getTransaction(jsonParsed) → 记录涉及程序与账户
3. 若涉及 Streamflow 程序：定位 stream 元数据账户（owner=strm），raw 解码
   sender@moff-128 / recipient@moff-64 / 参数区 moff+148 起 u64 序列（管道文档 §2）
输出：data/escrow_probe.json + stdout 摘要
"""
import base64, json, subprocess, sys, time
from pathlib import Path

RPC = "https://api.mainnet-beta.solana.com"
PROXY = "http://127.0.0.1:7897"
import os as _os, json as _json
def _load_mint():
    m = _os.environ.get("MINT")
    if m: return m
    p = Path("config.json")
    if p.exists():
        return _json.loads(p.read_text()).get("mint")
    raise SystemExit("需要 mint：设 MINT 环境变量或工作目录 config.json 里给 mint 字段")
MINT = _load_mint()
STRM = "strmRqUCoQUgGUan5YhzUZa6KqdzwX5L6FpUxfmKg5m"
ALPHA = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

TARGETS = [
    ("8mdvt3hwUfZoP3CY4bcAEQ4aSDk4WakUqBBxsRZPf4pX", "StreamflowVault#1 7.13%"),
    ("3wxPkfjghd5emawiXKv6pi4ahc2CRMWcunZJpUzKpNjH", "StreamflowVault#2 5.29%"),
    ("9Ar3BuWUryoiPqj8c2ZTqgrucf7FMPq7roL1U3Eyg5So", "StreamflowVault#3 4.97%"),
    ("E1q5bq2AHwoD3dhUxCebxsTt3hBqdApTz8z5yhu1sn8S", "StreamflowVault#4 2.40%"),
    ("9igEyPWysUYTu7wM7k1fhpT4344pt2UM7Ww4PY62PHSz", "未注资PDA 2.19%"),
    ("7kfVZ7a534jUu1C7keMtNxHM2jfgNbZhVnX8bD4HUeW7", "defAh9DW程序PDA 2.0%"),
    ("EviNYQP3c1dksnkFoU7yHhQ5NyBHCq4trUPpGZvc4Fk8", "PrintrStakePool"),
]


def b58e(b: bytes) -> str:
    n = int.from_bytes(b, "big"); s = ""
    while n:
        n, r = divmod(n, 58); s = ALPHA[r] + s
    for byte in b:
        if byte == 0: s = "1" + s
        else: break
    return s


def b58d(s: str) -> bytes:
    n = 0
    for c in s: n = n * 58 + ALPHA.index(c)
    b = n.to_bytes((n.bit_length() + 7) // 8, "big")
    pad = 0
    for c in s:
        if c == "1": pad += 1
        else: break
    return b"\x00" * pad + b


def rpc(method, params, retries=4):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    for i in range(retries):
        p = subprocess.run(["curl", "-s", "-m", "30", "-x", PROXY, RPC, "-X", "POST",
                            "-H", "Content-Type: application/json", "-d", body],
                           capture_output=True, text=True, timeout=45)
        try:
            d = json.loads(p.stdout)
            if "result" in d: return d["result"]
            if "error" in d and "429" not in str(d["error"]): return None
        except Exception:
            pass
        time.sleep(2 * (i + 1))
    return None


def oldest_sig(addr):
    before, oldest, pages = None, None, 0
    while pages < 12:
        params = [addr, {"limit": 1000}]
        if before: params[1]["before"] = before
        res = rpc("getSignaturesForAddress", params)
        if res is None: return None, None
        if not res: break
        oldest = res[-1]; before = oldest["signature"]; pages += 1
        time.sleep(0.15)
        if len(res) < 1000: break
    return (oldest or {}).get("signature"), (oldest or {}).get("blockTime")


def decode_stream_meta(meta_addr):
    info = rpc("getAccountInfo", [meta_addr, {"encoding": "base64"}])
    v = (info or {}).get("value")
    if not v or v.get("owner") != STRM: return None
    raw = base64.b64decode(v["data"][0])
    mint_b = b58d(MINT)
    moff = raw.find(mint_b)
    if moff < 128: return None
    sender = b58e(raw[moff-128:moff-96])
    recipient = b58e(raw[moff-64:moff-32])
    vals = []
    for k in range(10):
        off = moff + 148 + k*8
        if off + 8 <= len(raw):
            vals.append(int.from_bytes(raw[off:off+8], "little"))
    return {"meta": meta_addr, "sender": sender, "recipient": recipient,
            "u64_seq_from_moff148": vals, "data_len": len(raw)}


def main():
    out = []
    for addr, label in TARGETS:
        sig, bt = oldest_sig(addr)
        rec = {"addr": addr, "label": label, "oldest_sig": sig, "oldest_blocktime": bt}
        if sig:
            tx = rpc("getTransaction", [sig, {"encoding": "jsonParsed",
                                              "maxSupportedTransactionVersion": 0}])
            if tx:
                progs, accts = set(), []
                msg = tx["transaction"]["message"]
                for ins in msg.get("instructions", []):
                    pid = ins.get("programId", "")
                    progs.add(pid)
                for inner in (tx.get("meta", {}).get("innerInstructions") or []):
                    for ins in inner.get("instructions", []):
                        progs.add(ins.get("programId", ""))
                accts = [a["pubkey"] if isinstance(a, dict) else a
                         for a in msg.get("accountKeys", [])]
                rec["programs"] = sorted(progs)
                rec["account_keys"] = accts
                rec["fee_payer"] = accts[0] if accts else None
                if STRM in progs:
                    for cand in accts:
                        dec = decode_stream_meta(cand)
                        if dec:
                            rec["streamflow"] = dec
                            break
                        time.sleep(0.12)
        out.append(rec)
        print(f"[{label}] oldest={sig and sig[:20]}… bt={bt} feePayer={rec.get('fee_payer','?')}")
        if rec.get("streamflow"):
            sf = rec["streamflow"]
            print(f"   stream sender={sf['sender']} recipient={sf['recipient']}")
            print(f"   u64seq={sf['u64_seq_from_moff148'][:8]}")
        time.sleep(0.3)
    Path("data/escrow_probe.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("saved data/escrow_probe.json")


if __name__ == "__main__":
    main()
