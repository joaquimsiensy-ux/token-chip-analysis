#!/usr/bin/env python3
"""增量更新:批量核实窗口内地址流转并分类(pool_buy/pool_sell/direct_transfer)。

/token-update 快照对比法核心件(data-pipeline-solana §10):对 snapshot_diff 筛出的
大额变动地址,拉 ATA 级签名史(api.mainnet-beta 全史),逐笔解析 pre/postTokenBalances,
按对手方(池 vs 钱包)分类定性,并汇总"直转对"(换仓/洗仓/归集识别的核心输出)。

用法:
  python3 probe_window_moves.py --targets targets.json --cutoff 2026-07-13T04:00:00Z \
      --mint <MINT> [--pools 池地址,逗号分隔] [--accounts data/holders_accounts.json,data/holders_accounts_旧.json] \
      [--max-parse 8] [--out data/window_moves.json] [--proxy http://127.0.0.1:7897]

  targets.json = {地址: "为什么查"};cutoff 用 ISO 字符串(内部 datetime 解析——
  ⚠️ 禁止手算 unix 时间戳,CLUDE 实战手算错 2 天导致首跑作废)。

注意:
- 直转对金额以"对手方 |Δ|"为准(不是本址净额——本址净额含同 tx 其他来源,会虚高)。
- 每址解析上限 --max-parse 笔,超出只记 window_tx_count;净额一律以快照 diff 为权威。
来源:CLUDE(Solana) 增量更新 2026-07-15(补扫 38 址全覆盖版,修正首版金额聚合虚高)。
"""
import argparse, json, subprocess, time
from datetime import datetime, timezone
from pathlib import Path


def rpc(url, proxy, method, params, timeout=30):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    cmd = ["curl", "-s", "-m", str(timeout)]
    if proxy:
        cmd += ["-x", proxy]
    cmd += [url, "-X", "POST", "-H", "Content-Type: application/json", "-d", body]
    for attempt in range(4):
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 15)
        if p.returncode == 0 and p.stdout.strip():
            try:
                r = json.loads(p.stdout)
                if "result" in r:
                    return r["result"]
                if "error" in r and "429" not in str(r["error"]):
                    return None
            except json.JSONDecodeError:
                pass
        time.sleep(1.5 * (attempt + 1))
    return None


def parse_cutoff(s):
    s = s.strip()
    if s.isdigit():
        return int(s)
    return int(datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc).timestamp())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", required=True)
    ap.add_argument("--cutoff", required=True, help="ISO 时间(如 2026-07-13T04:00:00Z)或 unix 秒")
    ap.add_argument("--mint", required=True)
    ap.add_argument("--pools", default="", help="池地址逗号分隔(用于 pool/transfer 分类)")
    ap.add_argument("--accounts", default="data/holders_accounts.json",
                    help="holders_accounts.json 列表,逗号分隔(新旧都给,清零户 ATA 只在旧文件)")
    ap.add_argument("--decimals", type=int, default=6)
    ap.add_argument("--max-parse", type=int, default=8)
    ap.add_argument("--rpc", default="https://api.mainnet-beta.solana.com")
    ap.add_argument("--proxy", default="http://127.0.0.1:7897")
    ap.add_argument("--pause", type=float, default=0.26)
    ap.add_argument("--out", default="data/window_moves.json")
    args = ap.parse_args()

    cutoff = parse_cutoff(args.cutoff)
    print(f"cutoff={cutoff} ({datetime.fromtimestamp(cutoff, timezone.utc).isoformat()})")
    pools = {x for x in args.pools.split(",") if x}
    dec = 10 ** args.decimals
    targets = json.loads(Path(args.targets).read_text())

    atas = {}
    for f in args.accounts.split(","):
        for row in json.loads(Path(f).read_text()):
            atas.setdefault(row["owner"], set()).add(row["account"])

    out, transfer_pairs = {}, []
    for owner, why in targets.items():
        accs = sorted(atas.get(owner, []))
        rec = {"why": why, "atas": accs, "moves": [], "classify": ""}
        if not accs:
            rec["classify"] = "no_ata"
            out[owner] = rec
            print(f"!! {owner[:10]}… 无ATA  ({why})")
            continue
        win_sigs = []
        for acc in accs:
            before = None
            for _page in range(6):
                params = [acc, {"limit": 100}]
                if before:
                    params[1]["before"] = before
                sigs = rpc(args.rpc, args.proxy, "getSignaturesForAddress", params)
                time.sleep(args.pause)
                if not sigs:
                    break
                for s in sigs:
                    bt = s.get("blockTime") or 0
                    if bt >= cutoff and not s.get("err"):
                        win_sigs.append((bt, s["signature"]))
                if (sigs[-1].get("blockTime") or 0) < cutoff or len(sigs) < 100:
                    break
                before = sigs[-1]["signature"]
        win_sigs = sorted(set(win_sigs))
        rec["window_tx_count"] = len(win_sigs)
        pool_flow = transfer_flow = 0
        for bt, sig in win_sigs[:args.max_parse]:
            tx = rpc(args.rpc, args.proxy, "getTransaction",
                     [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}])
            time.sleep(args.pause)
            if not tx:
                continue
            meta = tx.get("meta") or {}
            deltas = {}
            for side, sgn in (("preTokenBalances", -1), ("postTokenBalances", 1)):
                for b in meta.get(side) or []:
                    if b.get("mint") != args.mint:
                        continue
                    o = b.get("owner", "?")
                    deltas[o] = deltas.get(o, 0) + sgn * int(b["uiTokenAmount"]["amount"])
            deltas = {o: d for o, d in deltas.items() if d != 0}
            me = deltas.get(owner, 0)
            others = {o: d for o, d in deltas.items() if o != owner}
            pool_cp = sum(abs(d) for o, d in others.items() if o in pools)
            wallet_cp = {o: d for o, d in others.items() if o not in pools}
            if pools and pool_cp >= abs(me) * 0.9:
                pool_flow += me
            elif wallet_cp:
                transfer_flow += me
                for o, d in wallet_cp.items():
                    # 金额取对手方 |d|(本址净额会把同 tx 其他来源算进来,虚高)
                    if me < 0 and d > 0:
                        transfer_pairs.append((owner, o, d / dec))
                    elif me > 0 and d < 0:
                        transfer_pairs.append((o, owner, -d / dec))
            rec["moves"].append({
                "ts": bt, "utc": time.strftime("%m-%d %H:%M", time.gmtime(bt)), "sig": sig,
                "my_delta_ui": me / dec,
                "counterparties": {o: d / dec for o, d in sorted(others.items(), key=lambda kv: kv[1])[:5]}})
        if abs(transfer_flow) > abs(pool_flow):
            rec["classify"] = "direct_transfer"
        elif pool_flow > 0:
            rec["classify"] = "pool_buy"
        elif pool_flow < 0:
            rec["classify"] = "pool_sell"
        else:
            rec["classify"] = "mixed/none"
        out[owner] = rec
        print(f"{owner[:10]}… {rec['classify']:<16} tx{len(win_sigs)}  {why}")

    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("\n== 直转对(from → to,金额=对手方口径) ==")
    agg = {}
    for f, t, a in transfer_pairs:
        agg[(f, t)] = agg.get((f, t), 0) + a
    for (f, t), a in sorted(agg.items(), key=lambda kv: -kv[1]):
        print(f"  {f} → {t}  {a:,.0f}")
    print(f"\n明细已写 {args.out}")


if __name__ == "__main__":
    main()
