#!/usr/bin/env python3
"""批量地址 gas/资金同源溯源：各找最早 3 笔签名，解出 SOL 入金来源（pipeline §8.3）。

gas_fast 的加固能力于 v6.24.0 全部并入本脚本：默认最多翻 2 页，达到上限时
标记 approx；--full 取消翻页上限，恢复 gas_origin 旧版一直翻到最老的行为。

用法：python3 gas_origin.py [--full] <addr1> <addr2> ...
输出：data/gas_origins.json（累积合并，已查过的跳过）+ stdout 摘要
识别马甲网络最有效的一招：多地址 funder 收敛到同一母钱包即实锤（聚类规则见 playbook §6，
注意 CEX 热钱包/公共桥同源不作关联证据）。
与 mint 无关，纯 SOL 层，任何 Solana 标的直接复用。
来源：PUB(Solana) 分析 2026-07-14 收编；gas_fast 于 v6.24.0 并入。
"""
import argparse, json, subprocess, sys, time
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
        cmd += [RPC, "-X", "POST", "-H", "Content-Type: application/json", "-d", body]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        try:
            d = json.loads(p.stdout)
            if "result" in d:
                return d["result"]
            if (d.get("error") or {}).get("code") == 429:
                time.sleep(3 * (i + 1))
                continue
        except Exception:
            pass
        time.sleep(1.6 * (i + 1))
    return None


def ft(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%m-%d %H:%M") if ts else "?"


def oldest_sigs(addr, want=3, max_pages=2):
    # 翻页上限：高频中转数千签名会翻到天荒地老（LAYOFF 实测 20 址 15 分钟卡死）
    # 达上限时最老笔可能未触达，结果标 approx；None 表示 --full 无上限。
    sigs, before = [], None
    approx = False
    pages = 0
    while True:
        if max_pages is not None and pages >= max_pages:
            approx = True
            break
        params = [addr, {"limit": 1000}]
        if before:
            params[1]["before"] = before
        res = rpc("getSignaturesForAddress", params)
        if res is None:
            return None, False
        if not res:
            break
        sigs.extend(res)
        pages += 1
        before = res[-1]["signature"]
        time.sleep(0.15)
        if len(res) < 1000:
            break
    sigs = [s for s in sigs if s.get("err") is None]
    return (sigs[-want:] if sigs else []), approx


def get_funder(sig, addr):
    """返回 gas_fast 的 funder/my_sol_delta，并保留 gas_origin 的完整 SOL deltas。"""
    tx = rpc("getTransaction", [sig, {"encoding": "jsonParsed",
                                      "maxSupportedTransactionVersion": 0}])
    if not tx:
        return None, None, None
    keys = [k["pubkey"] if isinstance(k, dict) else k
            for k in tx["transaction"]["message"].get("accountKeys", [])]
    meta = tx.get("meta") or {}
    pre = meta.get("preBalances", [])
    post = meta.get("postBalances", [])
    deltas = {}
    my_delta = 0.0
    funder = None
    most_negative = 0.0
    for i, key in enumerate(keys):
        try:
            delta = (post[i] - pre[i]) / 1e9
        except (IndexError, TypeError):
            continue
        if abs(delta) > 1e-9:
            deltas[key] = round(delta, 6)
        if key == addr:
            my_delta = delta
        elif delta < most_negative:
            most_negative = delta
            funder = key
    return funder, my_delta, deltas


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true",
                        help="取消默认 2 页上限，一直翻到最老签名；已有 approx 记录会重查")
    parser.add_argument("--proxy", default=None,
                        help="代理 URL；空字符串或 none 显式直连（默认经 CHIP_PROXY/端口探测解析）")
    parser.add_argument("addresses", nargs="+", metavar="ADDR", help="待溯源的 Solana 地址")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    global PROXY
    try:
        PROXY = resolve_proxy(args.proxy)
    except ValueError as exc:
        raise SystemExit(f"--proxy: {exc}") from exc
    targets = args.addresses
    max_pages = None if args.full else 2
    Path("data").mkdir(exist_ok=True)
    out_f = Path("data/gas_origins.json")
    out = json.loads(out_f.read_text()) if out_f.exists() else {}
    for a in targets:
        if a in out and not (args.full and out[a].get("approx")):
            print(f"{a} 已有，跳过")
            continue
        olds, approx = oldest_sigs(a, max_pages=max_pages)
        if olds is None:
            print(f"{a} 签名拉取失败")
            continue
        rec = {"first_txs": [], "approx": approx}
        for s in reversed(olds):  # 最老在前
            funder, my_delta, deltas = get_funder(s["signature"], a)
            time.sleep(0.15)
            if deltas is None:
                continue
            rec["first_txs"].append({"sig": s["signature"], "ts": s.get("blockTime"),
                                     "my_sol_delta": my_delta, "funder": funder,
                                     "deltas": deltas})
        out[a] = rec
        out_f.write_text(json.dumps(out, ensure_ascii=False))
        f0 = rec["first_txs"][0] if rec["first_txs"] else {}
        print(f"{a}  最早笔 {ft(f0.get('ts'))}  SOLΔ={f0.get('my_sol_delta')}  funder={f0.get('funder')}"
              f"{'  [approx:翻页达上限,最老笔可能未触达]' if approx else ''}")


if __name__ == "__main__":
    raise SystemExit(main())
