#!/usr/bin/env python3
"""通用 escrow/PDA 探查工具：最老创建交易 + Streamflow stream 元数据解码。

对每个目标账户：
1. getSignaturesForAddress 翻到最老（limit 1000 + before 游标）
2. 最老 tx getTransaction(jsonParsed) → 记录涉及程序与账户
3. 若涉及 Streamflow 程序：定位 stream 元数据账户（owner=strm），raw 解码
   sender@moff-128 / recipient@moff-64 / 参数区 moff+148 起 u64 序列（管道文档 §2）
目标由 --targets-file JSON 数组注入，每项为 {"address": "...", "label": "..."}。
输出：data/escrow_probe.json + stdout 摘要
"""
import argparse
import base64
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from proxy_config import resolve_proxy

RPC = "https://api.mainnet-beta.solana.com"
PROXY = None
import os as _os, json as _json
def _load_mint():
    m = _os.environ.get("MINT")
    if m: return m
    p = Path("config.json")
    if p.exists():
        return _json.loads(p.read_text()).get("mint")
    raise SystemExit("需要 mint：设 MINT 环境变量或工作目录 config.json 里给 mint 字段")
MINT = None
STRM = "strmRqUCoQUgGUan5YhzUZa6KqdzwX5L6FpUxfmKg5m"
ALPHA = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


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
        cmd = ["curl", "-s", "-m", "30"]
        if PROXY:
            cmd += ["-x", PROXY]
        cmd += [RPC, "-X", "POST", "-H", "Content-Type: application/json", "-d", body]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
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


def parse_args():
    parser = argparse.ArgumentParser(description="探查 Solana escrow/PDA 与 Streamflow 元数据")
    parser.add_argument("--targets-file", help='JSON 数组文件，元素为 {"address", "label"}')
    parser.add_argument("--rpc", default=RPC, help=f"Solana RPC（默认：{RPC}）")
    parser.add_argument("--proxy", default=None,
                        help="代理 URL；空字符串或 none 显式直连（默认经 CHIP_PROXY/端口探测解析）")
    args = parser.parse_args()
    if not args.targets_file:
        parser.error("缺少必填参数：--targets-file")
    return args


def load_targets(path):
    try:
        raw = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"读取 --targets-file 失败：{exc}")
    if not isinstance(raw, list) or any(
            not isinstance(item, dict) or not item.get("address") or "label" not in item
            for item in raw):
        raise SystemExit('--targets-file 必须是 JSON 数组，元素为 {"address", "label"}')
    return [(item["address"], item["label"]) for item in raw]


def main():
    global MINT, RPC, PROXY
    args = parse_args()
    RPC = args.rpc
    try:
        PROXY = resolve_proxy(args.proxy)
    except ValueError as exc:
        raise SystemExit(f"--proxy: {exc}") from exc
    MINT = _load_mint()
    targets = load_targets(args.targets_file)
    out = []
    for addr, label in targets:
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
