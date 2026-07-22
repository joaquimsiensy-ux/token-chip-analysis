#!/usr/bin/env python3
"""批量地址 gas/资金同源溯源：各找最早 3 笔签名，解出 SOL 入金来源（pipeline §8.3）。

用法：python3 gas_origin.py <addr1> <addr2> ...
输出：data/gas_origins.json（累积合并，已查过的跳过）+ stdout 摘要
识别马甲网络最有效的一招：多地址 funder 收敛到同一母钱包即实锤（聚类规则见 playbook §6，
注意 CEX 热钱包/公共桥同源不作关联证据）。
与 mint 无关，纯 SOL 层，任何 Solana 标的直接复用。
来源：PUB(Solana) 分析 2026-07-14 收编（逻辑未动）。
"""
import json, subprocess, sys, time
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
        except Exception:
            pass
        time.sleep(1.6 * (i + 1))
    return None


def ft(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%m-%d %H:%M") if ts else "?"


def oldest_sigs(addr, want=3, max_pages=2):
    # 翻页上限：高频中转数千签名会翻到天荒地老（LAYOFF 实测 20 址 15 分钟卡死）
    # 达上限时最老笔可能未触达，结果标 approx（gas_fast.py 同款语义）
    sigs, before = [], None
    approx = False
    for _ in range(max_pages):
        params = [addr, {"limit": 1000}]
        if before:
            params[1]["before"] = before
        res = rpc("getSignaturesForAddress", params)
        if res is None:
            return None, False
        if not res:
            break
        sigs.extend(res)
        before = res[-1]["signature"]
        time.sleep(0.15)
        if len(res) < 1000:
            break
    else:
        approx = True
    sigs = [s for s in sigs if s.get("err") is None]
    return (sigs[-want:] if sigs else []), approx


def main():
    targets = sys.argv[1:]
    if not targets:
        sys.exit(__doc__)
    Path("data").mkdir(exist_ok=True)
    out_f = Path("data/gas_origins.json")
    out = json.loads(out_f.read_text()) if out_f.exists() else {}
    for a in targets:
        if a in out:
            print(f"{a} 已有，跳过")
            continue
        olds, approx = oldest_sigs(a)
        if olds is None:
            print(f"{a} 签名拉取失败")
            continue
        rec = {"first_txs": [], "approx": approx}
        for s in reversed(olds):  # 最老在前
            tx = rpc("getTransaction", [s["signature"], {"encoding": "jsonParsed",
                                                         "maxSupportedTransactionVersion": 0}])
            time.sleep(0.15)
            if not tx:
                continue
            keys = [k["pubkey"] if isinstance(k, dict) else k
                    for k in tx["transaction"]["message"].get("accountKeys", [])]
            meta = tx.get("meta") or {}
            deltas = {}
            for i, k in enumerate(keys):
                try:
                    d = (meta["postBalances"][i] - meta["preBalances"][i]) / 1e9
                    if abs(d) > 1e-9:
                        deltas[k] = round(d, 6)
                except Exception:
                    pass
            # 本尊收 SOL 时的最大出资方
            my = deltas.get(a, 0)
            funder = None
            if my > 0:
                cands = {k: v for k, v in deltas.items() if v < 0 and k != a}
                if cands:
                    funder = min(cands.items(), key=lambda kv: kv[1])[0]
            rec["first_txs"].append({"sig": s["signature"], "ts": s.get("blockTime"),
                                     "my_sol_delta": my, "funder": funder, "deltas": deltas})
        out[a] = rec
        out_f.write_text(json.dumps(out, ensure_ascii=False))
        f0 = rec["first_txs"][0] if rec["first_txs"] else {}
        print(f"{a}  最早笔 {ft(f0.get('ts'))}  SOLΔ={f0.get('my_sol_delta')}  funder={f0.get('funder')}"
              f"{'  [approx:翻页达上限,最老笔可能未触达]' if approx else ''}")


if __name__ == "__main__":
    main()
