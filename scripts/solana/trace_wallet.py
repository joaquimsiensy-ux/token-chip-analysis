#!/usr/bin/env python3
"""单钱包全签名流水解码（api.mainnet-beta，限速+重试）。

用法：python3 trace_wallet.py <wallet> [--max-sigs 1200] [--mint <mint>]
输出：data/trace_<addr前8>.json
  每笔：{sig, blockTime, err, fee_payer, programs, self_delta(按mint), sol_delta, memo}
解码规则（data-pipeline-solana.md §3a）：
- 活跃度看 pre/postTokenBalances 里本尊(owner=目标)按 mint 过滤的净变动，不数签名条数
- source/destination 是 token account，映射回钱包必须经 tokenBalances 的 owner 字段
"""
import argparse, json, subprocess, sys, time
from pathlib import Path

RPC = "https://api.mainnet-beta.solana.com"
PROXY = "http://127.0.0.1:7897"


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wallet")
    ap.add_argument("--max-sigs", type=int, default=1200)
    ap.add_argument("--mint", required=True)
    args = ap.parse_args()
    w = args.wallet

    sigs, before = [], None
    while len(sigs) < args.max_sigs:
        params = [w, {"limit": min(1000, args.max_sigs - len(sigs))}]
        if before:
            params[1]["before"] = before
        res = rpc("getSignaturesForAddress", params)
        if res is None:
            print("FATAL: 签名拉取失败", file=sys.stderr); sys.exit(1)
        if not res:
            break
        sigs.extend(res); before = res[-1]["signature"]
        time.sleep(0.2)
        if len(res) < 1000:
            break
    print(f"{w[:8]}… 签名数 {len(sigs)}（含失败）")

    out = []
    for k, s in enumerate(sigs):
        if s.get("err") is not None:
            out.append({"sig": s["signature"], "blockTime": s.get("blockTime"), "err": True})
            continue
        tx = rpc("getTransaction", [s["signature"], {"encoding": "jsonParsed",
                                                     "maxSupportedTransactionVersion": 0}])
        time.sleep(0.13)
        if tx is None:
            out.append({"sig": s["signature"], "blockTime": s.get("blockTime"), "fetch_fail": True})
            continue
        msg = tx["transaction"]["message"]
        meta = tx.get("meta") or {}
        keys = [a["pubkey"] if isinstance(a, dict) else a for a in msg.get("accountKeys", [])]
        progs = set()
        for ins in msg.get("instructions", []):
            progs.add(ins.get("programId", ""))
        for inner in (meta.get("innerInstructions") or []):
            for ins in inner.get("instructions", []):
                progs.add(ins.get("programId", ""))
        # 本尊按 mint 的净变动（owner 口径）
        def bal(entries):
            t = 0
            for e in entries or []:
                if e.get("mint") == args.mint and e.get("owner") == w:
                    t += int(e["uiTokenAmount"]["amount"])
            return t
        delta = bal(meta.get("postTokenBalances")) - bal(meta.get("preTokenBalances"))
        # 本尊 SOL 变动
        # ⚠️ w 传 token account(ATA) 时本值恒≈0(ATA 的 lamports 不动)——据此把"流入"判为
        # 零成本费领取是系统性误判(CLUDE 增量复核实证:40+ 笔整数 SOL 市场买入被误标费领取)。
        # w 为 ATA 时以 owner_sol_delta 为准;流入定性必须看资金侧,不能只看币侧。
        sol_delta = None
        if w in keys:
            i = keys.index(w)
            try:
                sol_delta = (meta["postBalances"][i] - meta["preBalances"][i]) / 1e9
            except Exception:
                pass
        # w 若是 token account:补算其 owner 主钱包的 SOL 变动(v2.9.0,CLUDE 教训)
        owner_sol_delta = None
        for e in (meta.get("postTokenBalances") or []) + (meta.get("preTokenBalances") or []):
            ai = e.get("accountIndex")
            if ai is not None and ai < len(keys) and keys[ai] == w \
                    and e.get("owner") and e["owner"] != w and e["owner"] in keys:
                j = keys.index(e["owner"])
                try:
                    owner_sol_delta = (meta["postBalances"][j] - meta["preBalances"][j]) / 1e9
                except Exception:
                    pass
                break
        # 对手方：同 tx 内该 mint 其他 owner 的变动
        others = {}
        for e in (meta.get("postTokenBalances") or []):
            if e.get("mint") == args.mint and e.get("owner") != w:
                others[e["owner"]] = others.get(e["owner"], 0) + int(e["uiTokenAmount"]["amount"])
        for e in (meta.get("preTokenBalances") or []):
            if e.get("mint") == args.mint and e.get("owner") != w:
                others[e["owner"]] = others.get(e["owner"], 0) - int(e["uiTokenAmount"]["amount"])
        others = {k2: v for k2, v in others.items() if v != 0}
        out.append({"sig": s["signature"], "blockTime": s.get("blockTime"),
                    "fee_payer": keys[0] if keys else None,
                    "programs": sorted(p for p in progs if p),
                    "self_delta_raw": delta, "sol_delta": sol_delta,
                    "owner_sol_delta": owner_sol_delta,
                    "counterparties": others})
        if (k + 1) % 25 == 0:
            print(f"  decoded {k+1}/{len(sigs)}")
    f = Path(f"data/trace_{w[:8]}.json")
    f.write_text(json.dumps(out, ensure_ascii=False))
    print(f"saved {f} ({len(out)} tx)")


if __name__ == "__main__":
    main()
