# 收编自 CLUDE(Solana) 分析 2026-07-13；标的专属地址列表请按新标的替换（TARGETS/WHALES 常量或改造为 argparse）
#!/usr/bin/env python3
"""隐鲸补查（第二轮）：高频钱包的 CLUDE ATA 级签名史——出货窗口精确化。

owner 级签名史被其他币活动稀释（4000 条抽样漏 CLUDE 笔），改查 CLUDE token account：
  1. getTokenAccountsByOwner(owner, mint) 拿 ATA（若未 close）
  2. close 了则从已知买入笔 tx 的 postTokenBalances 拿 account 地址
  3. getSignaturesForAddress(ATA) 全量（只含 CLUDE 相关，量小）→ 全部 decode
目标：AEiiScFekU / 3y5VNvpV / 49foKJpR / 7oTNzV4tbm（7oTN 329 签名已覆盖但补全卖出序列）
输出并入 data/hidden_whales_probe.json 的 <owner>_ata 键
"""
import json, subprocess, time
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
T22 = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"

TARGETS = [
    "AEiiScFekUardNBJQb64WRyzyGwATkvEgzyxwrkyhW9f",
    "3y5VNvpV5Mc7x7k8TJcvquyuJarywLbUAHzzTyUt3iip",
    "49foKJpRnZUaPKsDgnQhUFRMk7NX4zD5KgtVpxgvctLa",
    "7oTNzV4tbmoCy1zz1zykFSJuxhv1UcQM95HTAS3qFjYx",
]


def rpc(method, params, retries=4):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    for i in range(retries):
        p = subprocess.run(["curl", "-s", "-m", "30", "-x", PROXY, RPC, "-X", "POST",
                            "-H", "Content-Type: application/json", "-d", body],
                           capture_output=True, text=True, timeout=45)
        try:
            d = json.loads(p.stdout)
            if "result" in d:
                return d["result"]
        except Exception:
            pass
        time.sleep(1.5 * (i + 1))
    return None


def find_ata(owner, probe):
    # 路 1：现存账户
    res = rpc("getTokenAccountsByOwner", [owner, {"mint": MINT}, {"encoding": "jsonParsed"}])
    vals = (res or {}).get("value") or []
    if vals:
        return vals[0]["pubkey"], "live"
    # 路 2：从已知 CLUDE 买入笔 tx 拿 account 地址
    rec = probe.get(owner) or {}
    for m in rec.get("moves", []):
        if not m.get("delta"):
            continue
        tx = rpc("getTransaction", [m["sig"], {"encoding": "jsonParsed",
                                               "maxSupportedTransactionVersion": 0}])
        time.sleep(0.13)
        if not tx:
            continue
        meta = tx.get("meta") or {}
        keys = [k["pubkey"] if isinstance(k, dict) else k
                for k in (tx.get("transaction", {}).get("message", {}).get("accountKeys") or [])]
        for e in (meta.get("postTokenBalances") or []) + (meta.get("preTokenBalances") or []):
            if e.get("mint") == MINT and e.get("owner") == owner:
                idx = e.get("accountIndex")
                if idx is not None and idx < len(keys):
                    return keys[idx], "from_tx"
    return None, None


def main():
    out_f = Path("data/hidden_whales_probe.json")
    probe = json.loads(out_f.read_text())
    for owner in TARGETS:
        key = owner + "_ata"
        if key in probe:
            print(f"skip {owner[:8]}", flush=True)
            continue
        ata, how = find_ata(owner, probe)
        if not ata:
            probe[key] = {"error": "ata_not_found"}
            out_f.write_text(json.dumps(probe))
            print(f"{owner[:8]}… ATA 未找到", flush=True)
            continue
        sigs, before = [], None
        for _ in range(3):
            params = [ata, {"limit": 1000}]
            if before:
                params[1]["before"] = before
            res = rpc("getSignaturesForAddress", params)
            if not res:
                break
            sigs.extend(res)
            before = res[-1]["signature"]
            time.sleep(0.15)
            if len(res) < 1000:
                break
        ok = [s for s in sigs if s.get("err") is None and s.get("blockTime")]
        ok.sort(key=lambda s: s["blockTime"])
        moves = []
        cap = 120
        sample = ok if len(ok) <= cap else [ok[int(i * (len(ok) - 1) / (cap - 1))] for i in range(cap)]
        for s in sample:
            tx = rpc("getTransaction", [s["signature"], {"encoding": "jsonParsed",
                                                         "maxSupportedTransactionVersion": 0}])
            time.sleep(0.13)
            if not tx:
                continue
            meta = tx.get("meta") or {}

            def tok(entries):
                t = 0
                for e in entries or []:
                    if e.get("mint") == MINT and e.get("owner") == owner:
                        t += int(e["uiTokenAmount"]["amount"])
                return t
            delta = tok(meta.get("postTokenBalances")) - tok(meta.get("preTokenBalances"))
            if not delta:
                continue
            others = {}
            for e in (meta.get("postTokenBalances") or []):
                if e.get("mint") == MINT and e.get("owner") != owner:
                    others[e["owner"]] = others.get(e["owner"], 0) + int(e["uiTokenAmount"]["amount"])
            for e in (meta.get("preTokenBalances") or []):
                if e.get("mint") == MINT and e.get("owner") != owner:
                    others[e["owner"]] = others.get(e["owner"], 0) - int(e["uiTokenAmount"]["amount"])
            cp = max(others.items(), key=lambda kv: abs(kv[1]))[0] if others else None
            moves.append({"ts": s["blockTime"], "delta": delta, "cp": cp, "sig": s["signature"]})
        probe[key] = {"ata": ata, "how": how, "ata_sig_total": len(sigs), "moves": moves}
        out_f.write_text(json.dumps(probe))
        sells = [m for m in moves if m["delta"] < 0]
        span = (f"{sells[0]['ts']}~{sells[-1]['ts']}" if sells else "无卖出笔")
        print(f"{owner[:8]}… ATA={ata[:8]}({how}) sigs={len(sigs)} CLUDE笔={len(moves)} 卖出={len(sells)} 窗口={span}", flush=True)
    print("done")


if __name__ == "__main__":
    main()
