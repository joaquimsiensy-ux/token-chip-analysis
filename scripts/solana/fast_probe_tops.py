#!/usr/bin/env python3
"""top 大户快速画像：token account 首笔（建仓起点+来源）+ 签名时间分布 + 大额入账来源。

比全量 decode 快一个数量级：每个 owner 约 4-8 个 RPC 调用。
输出 data/top_probe.json：
  {owner: {first_ts, first_src_owner, sig_count, sig_span, big_ins: [(ts, amt, from)...(解码前3大额入账)]}}

标的专属地址通过环境变量传入（2026-07-13 参数化，替代原 CLUDE 硬编码常量）：
  PROBE_SKIP  逗号分隔，跳过不探测（如已确认的基础设施地址）
  PROBE_EXTRA 逗号分隔，top N 之外追加探测的地址
"""
import argparse, json, subprocess, sys, time
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

SKIP = set(filter(None, _os.environ.get("PROBE_SKIP", "").split(",")))
EXTRA = list(filter(None, _os.environ.get("PROBE_EXTRA", "").split(",")))


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
            if "result" in d:
                return d["result"]
        except Exception:
            pass
        time.sleep(1.5 * (i + 1))
    return None


def probe_tx(sig, owner):
    tx = rpc("getTransaction", [sig, {"encoding": "jsonParsed",
                                      "maxSupportedTransactionVersion": 0}])
    if tx is None:
        return None
    meta = tx.get("meta") or {}

    def bal(entries):
        t = 0
        for e in entries or []:
            if e.get("mint") == MINT and e.get("owner") == owner:
                t += int(e["uiTokenAmount"]["amount"])
        return t
    delta = bal(meta.get("postTokenBalances")) - bal(meta.get("preTokenBalances"))
    others = {}
    for e in (meta.get("postTokenBalances") or []):
        if e.get("mint") == MINT and e.get("owner") != owner:
            others[e["owner"]] = others.get(e["owner"], 0) + int(e["uiTokenAmount"]["amount"])
    for e in (meta.get("preTokenBalances") or []):
        if e.get("mint") == MINT and e.get("owner") != owner:
            others[e["owner"]] = others.get(e["owner"], 0) - int(e["uiTokenAmount"]["amount"])
    cp = min(others.items(), key=lambda kv: kv[1])[0] if others else None  # 最大流出方=来源
    progs = json.dumps(tx["transaction"]["message"])[:0]  # 省内存
    amm = False
    for ins in tx["transaction"]["message"].get("instructions", []):
        if ins.get("programId", "").startswith("pAMM"):
            amm = True
    return {"delta": delta, "cp": cp, "amm": amm,
            "bt": tx.get("blockTime")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("n", nargs="?", type=int, default=30, help="探测 top owner 数（默认 30）")
    parser.add_argument("--proxy", default=None,
                        help="代理 URL；空字符串或 none 显式直连（默认经 CHIP_PROXY/端口探测解析）")
    args = parser.parse_args(argv)
    global MINT, PROXY
    try:
        PROXY = resolve_proxy(args.proxy)
    except ValueError as exc:
        parser.error(str(exc))
    MINT = _load_mint()
    n = args.n
    owners = json.load(open("data/holders_owners.json"))
    accounts = json.load(open("data/holders_accounts.json"))
    rc = json.load(open("data/rugcheck_report.json"))
    infra = set((rc.get("knownAccounts") or {}).keys())
    acct_of = {}
    for r in accounts:
        acct_of.setdefault(r["owner"], []).append(r["account"])

    targets = [o for o in list(owners.keys())[:n] if o not in SKIP and o not in infra]
    targets += EXTRA
    print(f"targets: {len(targets)}")

    out_f = Path("data/top_probe.json")
    out = json.loads(out_f.read_text()) if out_f.exists() else {}
    for k, owner in enumerate(targets):
        if owner in out:
            continue
        tas = acct_of.get(owner, [])
        rec = {"token_accounts": tas, "cur_raw": owners.get(owner, 0)}
        all_sigs = []
        for ta in tas:
            sigs, before = [], None
            for _ in range(3):  # 最多 3000 条
                params = [ta, {"limit": 1000}]
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
            all_sigs.extend([s for s in sigs if s.get("err") is None])
        all_sigs.sort(key=lambda s: s.get("blockTime") or 0)
        rec["sig_count"] = len(all_sigs)
        if all_sigs:
            rec["first_ts"] = all_sigs[0].get("blockTime")
            rec["last_ts"] = all_sigs[-1].get("blockTime")
            first = probe_tx(all_sigs[0]["signature"], owner)
            time.sleep(0.13)
            rec["first_tx"] = first
            rec["first_sig"] = all_sigs[0]["signature"]
            # 若首笔非入账（罕见），再看第二笔
            if first and first["delta"] <= 0 and len(all_sigs) > 1:
                second = probe_tx(all_sigs[1]["signature"], owner)
                rec["second_tx"] = second
                time.sleep(0.13)
            # 最后一笔（现状判定：最近动作）
            last = probe_tx(all_sigs[-1]["signature"], owner)
            rec["last_tx"] = last
            time.sleep(0.13)
        out[owner] = rec
        out_f.write_text(json.dumps(out))
        ft = rec.get("first_ts")
        from datetime import datetime, timezone
        fts = datetime.fromtimestamp(ft, tz=timezone.utc).strftime("%m-%d %H:%M") if ft else "?"
        print(f"[{k+1}/{len(targets)}] {owner[:12]}… sigs={rec['sig_count']} first={fts} "
              f"src={(rec.get('first_tx') or {}).get('cp','?') and str((rec.get('first_tx') or {}).get('cp'))[:12]}", flush=True)
    print("done")


if __name__ == "__main__":
    raise SystemExit(main())
