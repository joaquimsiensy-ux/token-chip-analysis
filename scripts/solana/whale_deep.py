#!/usr/bin/env python3
"""大户 ATA 级全流水深挖（每笔带对手方/程序/本尊 SOL 变动）。

用法：python3 whale_deep.py <owner1> [owner2 ...] [--mint <mint>] [--known-sig <sig>]
mint 来源：--mint / MINT 环境变量 / 工作目录 config.json 的 mint 字段。
输出：data/whale_deep.json（累积合并，键=owner，已查过的跳过）

ATA 发现三级（pipeline §3a 坑 1/坑 4）：
  1. data/holders_accounts.json（scan_token_accounts.py 产物，现存 ATA）
  2. getTokenAccountsByOwner 实时查
  3. 销户反查：从任一已知含该 owner 的交易（data/stake_ledger.json 的 raw_rows，
     或 --known-sig 手动给一笔）的 tokenBalances accountIndex 映射 accountKeys 反查 ATA
     ——ATA 已销户时地址签名史仍可查
与 trace_wallet.py 的分工：trace_wallet 查 owner 级签名（高频钱包会被他币稀释），
本脚本查 ATA 级签名——只含目标币相关，是大户全流水的正解。
来源：PUB(Solana) 分析 2026-07-14 收编（参数化 mint + known-sig 反查入口）。
"""
import argparse, json, os, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from proxy_config import resolve_proxy

RPC = "https://api.mainnet-beta.solana.com"
PROXY = None


def rpc(method, params, retries=5):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    for i in range(retries):
        cmd = ["curl", "-s", "-m", "30"]
        if PROXY:
            cmd += ["-x", PROXY]
        cmd += [RPC, "-X", "POST",
                "-H", "Content-Type: application/json", "-d", body]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        try:
            d = json.loads(p.stdout)
            if "result" in d:
                return d["result"]
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


def atas_from_tx(sig, owner, mint):
    """从一笔已知交易的 tokenBalances 反查该 owner 的 ATA 地址（销户后可用）。"""
    atas = set()
    tx = rpc("getTransaction", [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}])
    if not tx:
        return atas
    keys = [a["pubkey"] if isinstance(a, dict) else a
            for a in tx["transaction"]["message"].get("accountKeys", [])]
    meta = tx.get("meta") or {}
    for e in (meta.get("preTokenBalances") or []) + (meta.get("postTokenBalances") or []):
        if e.get("mint") == mint and e.get("owner") == owner:
            atas.add(keys[e["accountIndex"]])
    return atas


def find_atas(owner, mint, known_sig=None):
    atas = set()
    f = Path("data/holders_accounts.json")
    if f.exists():
        for r in json.loads(f.read_text()):
            if r["owner"] == owner:
                atas.add(r["account"])
    if not atas:
        res = rpc("getTokenAccountsByOwner", [owner, {"mint": mint}, {"encoding": "jsonParsed"}])
        for v in (res or {}).get("value", []):
            atas.add(v["pubkey"])
    if not atas and known_sig:
        atas |= atas_from_tx(known_sig, owner, mint)
    if not atas:  # 销户反查：托管池账本里该 owner 的已知 sig
        lf = Path("data/stake_ledger.json")
        if lf.exists():
            d = json.loads(lf.read_text())
            for row in d.get("raw_rows", []):
                if owner in row.get("counterparties", {}):
                    atas |= atas_from_tx(row["sig"], owner, mint)
                    if atas:
                        break
    return sorted(atas)


def all_sigs(addr, cap=2000):
    sigs, before = [], None
    while len(sigs) < cap:
        params = [addr, {"limit": 1000}]
        if before:
            params[1]["before"] = before
        res = rpc("getSignaturesForAddress", params)
        if res is None or not res:
            break
        sigs.extend(res)
        before = res[-1]["signature"]
        time.sleep(0.15)
        if len(res) < 1000:
            break
    return [s for s in sigs if s.get("err") is None]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("owners", nargs="+")
    ap.add_argument("--mint")
    ap.add_argument("--known-sig", help="ATA 已销户且账本无记录时，手动给一笔含该 owner 的交易签名")
    ap.add_argument("--rpc", help="覆盖 RPC 端点（如 Helius，免代理时配 --proxy none）")
    ap.add_argument("--proxy", default=None,
                    help="代理 URL；空字符串或 none 显式直连（默认经 CHIP_PROXY/端口探测解析）")
    ap.add_argument("--out", default="data/whale_deep.json", help="输出文件（并行分组时各组独立文件防写冲突）")
    args = ap.parse_args()
    global RPC, PROXY
    if args.rpc:
        RPC = args.rpc
    try:
        PROXY = resolve_proxy(args.proxy)
    except ValueError as exc:
        ap.error(str(exc))
    mint = resolve_mint(args.mint)
    Path("data").mkdir(exist_ok=True)
    out_f = Path(args.out)
    out = json.loads(out_f.read_text()) if out_f.exists() else {}
    for owner in args.owners:
        if owner in out:
            print(f"{owner} 已有，跳过")
            continue
        atas = find_atas(owner, mint, args.known_sig)
        print(f"{owner} ATA: {atas}")
        if not atas:
            print("  未找到 ATA（试 --known-sig 给一笔已知交易反查）")
            continue
        rows = []
        for ata in atas:
            sigs = all_sigs(ata)
            print(f"  {ata} 签名 {len(sigs)}")
            for s in sigs:
                tx = rpc("getTransaction", [s["signature"], {"encoding": "jsonParsed",
                                                             "maxSupportedTransactionVersion": 0}])
                time.sleep(0.15)
                if not tx:
                    continue
                meta = tx.get("meta") or {}
                msg = tx["transaction"]["message"]

                def bal(entries, who):
                    t = 0
                    for e in entries or []:
                        if e.get("mint") == mint and e.get("owner") == who:
                            t += int(e["uiTokenAmount"]["amount"])
                    return t
                delta = bal(meta.get("postTokenBalances"), owner) - bal(meta.get("preTokenBalances"), owner)
                others = {}
                for e in (meta.get("postTokenBalances") or []):
                    if e.get("mint") == mint and e.get("owner") != owner:
                        others[e["owner"]] = others.get(e["owner"], 0) + int(e["uiTokenAmount"]["amount"])
                for e in (meta.get("preTokenBalances") or []):
                    if e.get("mint") == mint and e.get("owner") != owner:
                        others[e["owner"]] = others.get(e["owner"], 0) - int(e["uiTokenAmount"]["amount"])
                progs = set()
                for ins in msg.get("instructions", []):
                    progs.add(ins.get("programId", ""))
                keys = [a["pubkey"] if isinstance(a, dict) else a for a in msg.get("accountKeys", [])]
                sol_d = None
                if owner in keys:
                    i = keys.index(owner)
                    try:
                        sol_d = (meta["postBalances"][i] - meta["preBalances"][i]) / 1e9
                    except Exception:
                        pass
                rows.append({"sig": s["signature"], "blockTime": s.get("blockTime"),
                             "delta_raw": delta, "sol_delta": sol_d,
                             "counterparties": {k: v for k, v in others.items() if v != 0},
                             "programs": sorted(p for p in progs if p)})
        rows.sort(key=lambda r: r.get("blockTime") or 0)
        out[owner] = {"atas": atas, "rows": rows}
        out_f.write_text(json.dumps(out, ensure_ascii=False))
        buys = sum(r["delta_raw"] for r in rows if r["delta_raw"] > 0)
        sells = sum(-r["delta_raw"] for r in rows if r["delta_raw"] < 0)
        print(f"  流水 {len(rows)} 笔 | 累计入 {buys:,} / 出 {sells:,}（raw）")


if __name__ == "__main__":
    main()
