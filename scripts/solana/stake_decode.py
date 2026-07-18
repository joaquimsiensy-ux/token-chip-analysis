#!/usr/bin/env python3
"""质押/托管池账本解码器：池 token account 签名史 → 逐用户存/取账本 → 闭合验证。

用法：python3 stake_decode.py <pool_owner> [--mint <mint>] [--cap 2500]
mint 来源：--mint / MINT 环境变量 / 工作目录 config.json 的 mint 字段。
输出：data/stake_ledger.json
  {"ledger": {user_owner: {staked, unstaked, net, n}}, "raw_rows": [逐笔 decode]}

用途（pipeline §2 自建质押合约判别五步法的配套账本验证）：
- 账本净额合计 vs 池链上当前余额精确对表（脚本自动做）——对不上=签名史没拉全或有非常规边
- "支付奖励"（用户取回>本金）与"自由赎回"记录是排除"归集仓伪装成质押池"的关键证据
- 池 ATA 从 data/holders_accounts.json 找（scan_token_accounts.py 产物），
  缺省 fallback getTokenAccountsByOwner
配套：owner 程序两跳判别/ProgramData/upgrade_authority 检查见 pipeline §2（RPC 直查，无需本脚本）。
来源：PUB(Solana) 分析 2026-07-14 收编（原三合一脚本拆出核心；creator 流水→whale_deep.py，
gas 溯源→gas_origin.py）。
"""
import argparse, json, os, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

RPC = "https://api.mainnet-beta.solana.com"
PROXY = "http://127.0.0.1:7897"


def rpc(method, params, retries=5):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    for i in range(retries):
        p = subprocess.run(["curl", "-s", "-m", "30", "-x", PROXY, RPC, "-X", "POST",
                            "-H", "Content-Type: application/json", "-d", body],
                           capture_output=True, text=True, timeout=45)
        try:
            d = json.loads(p.stdout)
            if "result" in d:
                return d["result"]
            if "error" in d:
                print(f"  rpc err: {str(d['error'])[:80]}", file=sys.stderr)
        except Exception:
            pass
        time.sleep(1.6 * (i + 1))
    return None


def resolve_mint(cli):
    if cli:
        return cli
    if os.environ.get("MINT"):
        return os.environ["MINT"]
    p = Path("config.json")
    if p.exists():
        m = json.loads(p.read_text()).get("mint")
        if m:
            return m
    sys.exit("mint 未指定：--mint / MINT 环境变量 / config.json:mint")


def all_sigs(addr, cap):
    sigs, before = [], None
    while len(sigs) < cap:
        params = [addr, {"limit": 1000}]
        if before:
            params[1]["before"] = before
        res = rpc("getSignaturesForAddress", params)
        if res is None:
            print(f"  签名拉取失败 {addr}", file=sys.stderr)
            break
        if not res:
            break
        sigs.extend(res)
        before = res[-1]["signature"]
        time.sleep(0.15)
        if len(res) < 1000:
            break
    return [s for s in sigs if s.get("err") is None]


def decode(sig, self_owner, mint):
    tx = rpc("getTransaction", [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}])
    if tx is None:
        return None
    meta = tx.get("meta") or {}
    msg = tx["transaction"]["message"]

    def bal(entries, owner):
        t = 0
        for e in entries or []:
            if e.get("mint") == mint and e.get("owner") == owner:
                t += int(e["uiTokenAmount"]["amount"])
        return t
    delta = bal(meta.get("postTokenBalances"), self_owner) - bal(meta.get("preTokenBalances"), self_owner)
    others = {}
    for e in (meta.get("postTokenBalances") or []):
        if e.get("mint") == mint and e.get("owner") != self_owner:
            others[e["owner"]] = others.get(e["owner"], 0) + int(e["uiTokenAmount"]["amount"])
    for e in (meta.get("preTokenBalances") or []):
        if e.get("mint") == mint and e.get("owner") != self_owner:
            others[e["owner"]] = others.get(e["owner"], 0) - int(e["uiTokenAmount"]["amount"])
    others = {k: v for k, v in others.items() if v != 0}
    keys = [a["pubkey"] if isinstance(a, dict) else a for a in msg.get("accountKeys", [])]
    return {"sig": sig, "blockTime": tx.get("blockTime"), "delta_raw": delta,
            "counterparties": others, "fee_payer": keys[0] if keys else None}


def find_pool_atas(pool_owner, mint):
    atas = []
    f = Path("data/holders_accounts.json")
    if f.exists():
        for r in json.loads(f.read_text()):
            if r["owner"] == pool_owner:
                atas.append(r["account"])
    if not atas:
        res = rpc("getTokenAccountsByOwner", [pool_owner, {"mint": mint}, {"encoding": "jsonParsed"}])
        for v in (res or {}).get("value", []):
            atas.append(v["pubkey"])
    return atas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pool_owner")
    ap.add_argument("--mint")
    ap.add_argument("--cap", type=int, default=2500, help="每 ATA 签名上限")
    args = ap.parse_args()
    mint = resolve_mint(args.mint)

    atas = find_pool_atas(args.pool_owner, mint)
    if not atas:
        sys.exit(f"未找到 {args.pool_owner} 的 token account")
    print(f"池 token accounts: {atas}")
    ledger, rows = {}, []
    for ata in atas:
        sigs = all_sigs(ata, args.cap)
        print(f"  {ata} 有效签名 {len(sigs)}")
        for s in sigs:
            r = decode(s["signature"], args.pool_owner, mint)
            time.sleep(0.15)
            if r is None or r["delta_raw"] == 0:
                continue
            rows.append(r)
            # 池 delta>0 = 用户存入；对手方 = 用户
            for u, v in r["counterparties"].items():
                e = ledger.setdefault(u, {"staked": 0, "unstaked": 0, "n": 0})
                if r["delta_raw"] > 0 and v < 0:
                    e["staked"] += -v
                    e["n"] += 1
                elif r["delta_raw"] < 0 and v > 0:
                    e["unstaked"] += v
                    e["n"] += 1
    for u, e in ledger.items():
        e["net"] = e["staked"] - e["unstaked"]
    json.dump({"ledger": ledger, "raw_rows": rows}, open("data/stake_ledger.json", "w"))

    tot = sum(e["net"] for e in ledger.values())
    # 闭合验证：账本净额合计 vs 池链上当前余额
    onchain = 0
    for ata in atas:
        res = rpc("getTokenAccountBalance", [ata])
        if res:
            onchain += int(res["value"]["amount"])
        time.sleep(0.15)
    print(f"\n账本：{len(ledger)} 个用户，{len(rows)} 笔有效变动，净存合计 {tot:,} raw")
    print(f"池链上余额 {onchain:,} raw  差={onchain - tot:,}"
          + ("  [闭合]" if abs(onchain - tot) <= 2 else "  [不闭合：签名史没拉全或有非常规边，勿进分析]"))
    over = [(u, e) for u, e in ledger.items() if e["unstaked"] > e["staked"]]
    if over:
        print(f"取回>存入的用户 {len(over)} 个（若为池支付奖励，是排除归集仓伪装的证据）：")
        for u, e in over[:10]:
            print(f"  {u}  存 {e['staked']:,} / 取 {e['unstaked']:,}")
    print("\n净存 top15：")
    for u, e in sorted(ledger.items(), key=lambda kv: -kv[1]["net"])[:15]:
        print(f"  {u}  净 {e['net']:>16,}（存 {e['staked']:,}/取 {e['unstaked']:,}，{e['n']} 笔）")
    print("已写 data/stake_ledger.json")


if __name__ == "__main__":
    main()
