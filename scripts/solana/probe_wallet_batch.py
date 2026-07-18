# 收编自 CLUDE(Solana) 分析 2026-07-13；标的专属地址列表请按新标的替换（TARGETS/WHALES 常量或改造为 argparse）
#!/usr/bin/env python3
"""复核缺口侦查：发射日隐鲸群 5 地址全流水 + 3FFb 源头 + defAh PDA authority + DRWN 池创建者。

隐鲸群（SQD 全窗口净买>10M 且现仓 0，完整地址取自 gz 重算）：判定是否第 4 庄
  - 出货时间窗（回答 3 月拉升卖方归因）
  - 对手方 / SOL 回款去向（关联性：同窗出货/回款归集/gas 同源）
3FFb（88 签名）：CLUDE 12M 来源层 + SOL 注资方，与 BL7/Fy8/4ryn 交叉
输出 data/hidden_whales_probe.json
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

WHALES = [
    "AEiiScFekUardNBJQb64WRyzyGwATkvEgzyxwrkyhW9f",
    "3y5VNvpV5Mc7x7k8TJcvquyuJarywLbUAHzzTyUt3iip",
    "49foKJpRnZUaPKsDgnQhUFRMk7NX4zD5KgtVpxgvctLa",
    "4eUcUSTpnQgxXarPRdfd1BrKvTphsPSKHxknbQ9rsVD6",
    "7oTNzV4tbmoCy1zz1zykFSJuxhv1UcQM95HTAS3qFjYx",
]
FFB = "3FFb3iW911R2RG8gd5w1Ay8vRW3gjD3eP6X2QbmrK68z"
DEFAH_OWNER = "7kfVZ7a534jUu1C7keMtNxHM2jfgNbZhVnX8bD4HUeW7"


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


def all_sigs(addr, max_pages=4):
    sigs, before = [], None
    for _ in range(max_pages):
        params = [addr, {"limit": 1000}]
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
    return sigs


def decode_wallet(addr, sigs, cap=160):
    """decode 全部成功签名（超 cap 均匀抽样），记 CLUDE 变动 + SOL 变动 + 对手方。"""
    ok = [s for s in sigs if s.get("err") is None and s.get("blockTime")]
    ok.sort(key=lambda s: s["blockTime"])
    sample = ok if len(ok) <= cap else [ok[int(i * (len(ok) - 1) / (cap - 1))] for i in range(cap)]
    moves = []
    for s in sample:
        tx = rpc("getTransaction", [s["signature"], {"encoding": "jsonParsed",
                                                     "maxSupportedTransactionVersion": 0}])
        time.sleep(0.13)
        if tx is None:
            continue
        meta = tx.get("meta") or {}

        def tok(entries):
            t = 0
            for e in entries or []:
                if e.get("mint") == MINT and e.get("owner") == addr:
                    t += int(e["uiTokenAmount"]["amount"])
            return t
        delta = tok(meta.get("postTokenBalances")) - tok(meta.get("preTokenBalances"))
        # SOL 变动（本地址）与最大 SOL 对手
        keys = [k["pubkey"] if isinstance(k, dict) else k
                for k in (tx.get("transaction", {}).get("message", {}).get("accountKeys") or [])]
        pre, post = meta.get("preBalances") or [], meta.get("postBalances") or []
        sol_self, sol_cp, sol_cp_amt = 0, None, 0
        for i, k in enumerate(keys):
            if i >= len(pre) or i >= len(post):
                break
            dd = post[i] - pre[i]
            if k == addr:
                sol_self = dd
            elif abs(dd) > abs(sol_cp_amt):
                sol_cp, sol_cp_amt = k, dd
        # token 对手
        others = {}
        for e in (meta.get("postTokenBalances") or []):
            if e.get("mint") == MINT and e.get("owner") != addr:
                others[e["owner"]] = others.get(e["owner"], 0) + int(e["uiTokenAmount"]["amount"])
        for e in (meta.get("preTokenBalances") or []):
            if e.get("mint") == MINT and e.get("owner") != addr:
                others[e["owner"]] = others.get(e["owner"], 0) - int(e["uiTokenAmount"]["amount"])
        tok_cp = max(others.items(), key=lambda kv: abs(kv[1]))[0] if others else None
        fee_payer = keys[0] if keys else None
        if delta or abs(sol_self) > 5_000_000:  # token 变动或 >0.005 SOL
            moves.append({"ts": s["blockTime"], "delta": delta, "tok_cp": tok_cp,
                          "sol_self": sol_self, "sol_cp": sol_cp, "sol_cp_amt": sol_cp_amt,
                          "fee_payer": fee_payer, "sig": s["signature"]})
    return {"sig_total": len(sigs), "decoded": len(sample), "moves": moves}


def main():
    out_f = Path("data/hidden_whales_probe.json")
    out = json.loads(out_f.read_text()) if out_f.exists() else {}

    for addr in WHALES + [FFB]:
        if addr in out:
            print(f"skip {addr[:8]} (已有)", flush=True)
            continue
        sigs = all_sigs(addr)
        rec = decode_wallet(addr, sigs)
        out[addr] = rec
        out_f.write_text(json.dumps(out))
        first_sell = next((m for m in rec["moves"] if m["delta"] < 0), None)
        print(f"{addr[:8]}… sigs={rec['sig_total']} decoded={rec['decoded']} "
              f"moves={len(rec['moves'])} 首笔卖出 ts={first_sell['ts'] if first_sell else 'n/a'}", flush=True)

    # defAh PDA：7kfV 的 CLUDE token account 归属主与 PDA data
    if "_defah" not in out:
        info = rpc("getAccountInfo", [DEFAH_OWNER, {"encoding": "base64"}])
        out["_defah"] = {"owner_account_info": (info or {}).get("value")}
        out_f.write_text(json.dumps(out))
        print("defAh PDA info 已取", flush=True)
    print("done")


if __name__ == "__main__":
    main()
