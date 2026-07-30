#!/usr/bin/env python3
"""供给真值闸（supply truth gate）——重放终态对链上 totalSupply 的硬校验。

背景（GNT 实测，2026-07-28）：老合约 migrate() 直接改账本、不发任何 Transfer/Burn
事件，全量重放余额虚高 10 倍，而 mint/burn 闭合、负余额、accounting_gate 全部检测项
均 PASS（模型错但自洽）。唯一暴露手段：重放净供给 mint_total − burn_total 对比链上
实查 totalSupply()。本闸在重放收尾必跑（analyze / easy / update 三条 workflow 同责），
成本一次 RPC 调用。

判定（fail-closed）:
  |replay_net − onchain| <= onchain × tolerance_bps/10000  → PASS
  超容差 → FAIL：该币余额一律禁用重放结果，改 Multicall3/RPC 实时直查；
  地址全集与转账历史仍可用重放（静默改账不影响历史事件本身）；
  重放余额仅可作"≥阈值超集"筛选（migrate 只减不增，数学严格）。

用法:
  EVM:    python3 supply_truth_gate.py --chain bsc --token 0x... --replay-stats replay_stats.json
  Solana: python3 supply_truth_gate.py --chain solana --mint <mint> --replay-stats stats.json
  绕过 stats 文件直接传数: --replay-net-raw <最小单位整数>
  --rpc URL          不给时用链默认免 key 端点（DEFAULT_RPC，与 accounting_gate 同表）
  --proxy URL        只作用于 RPC（Alchemy 国内走 clash 时传 http://127.0.0.1:7897）
  --tolerance-bps N  容差，默认 10（0.1%）
  --out PATH         结果 JSON 落盘（默认 supply_truth.json，写工作目录）

replay-stats 字段识别（依次尝试，值可为 int 或十进制字符串）:
  mint_total_wei/burn_total_wei → mint_total_raw/burn_total_raw → mint_total/burn_total

退出码: 0 = PASS
        2 = FAIL（超容差＝存在静默改账/记账错位——硬停，处置见上）
        1 = 检测自身失败（网络/字段缺失）——修通道重跑，禁当 PASS
（来源：GNT replay-silent-burn-trap 2026-07-28；v6.0.0 唯一批准代码例外）"""
import argparse
import json
import os
import sys

SEL_TOTSUP = "0x18160ddd"  # totalSupply()

DEFAULT_RPC = {
    "bsc": "https://bsc-dataseed.bnbchain.org",
    "eth": "https://ethereum-rpc.publicnode.com",
    "base": "https://mainnet.base.org",
    "arbitrum": "https://arb1.arbitrum.io/rpc",
    "polygon": "https://polygon-rpc.com",
    "solana": "https://api.mainnet-beta.solana.com",
}

FIELD_PAIRS = [("mint_total_wei", "burn_total_wei"),
               ("mint_total_raw", "burn_total_raw"),
               ("mint_total", "burn_total")]


def parse_replay_stats(stats: dict):
    """从 replay_stats 字典取 (mint_total, burn_total)，找不到抛 KeyError。"""
    for mk, bk in FIELD_PAIRS:
        if mk in stats:
            return int(str(stats[mk])), int(str(stats.get(bk, 0)))
    raise KeyError(f"replay_stats 缺 mint/burn 字段（认 {FIELD_PAIRS}）")


def decide(replay_net: int, onchain: int, tolerance_bps: int = 10):
    """纯判定：返回 (verdict, diff, diff_bps)。verdict ∈ {PASS, FAIL}。"""
    diff = replay_net - onchain
    if onchain == 0:
        # 链上供给为 0（全部销毁/迁空）：重放净供给也必须为 0 才算一致
        return ("PASS" if replay_net == 0 else "FAIL"), diff, None
    diff_bps = abs(diff) * 10000 / onchain
    return ("PASS" if diff_bps <= tolerance_bps else "FAIL"), diff, diff_bps


def _post(url, payload, proxy=None, timeout=30):
    import requests
    proxies = {"http": proxy, "https": proxy} if proxy else None
    r = requests.post(url, json=payload, proxies=proxies, timeout=timeout)
    r.raise_for_status()
    return r.json()


def fetch_onchain_supply(chain, token=None, mint=None, rpc=None, proxy=None) -> int:
    """链上实查当前总供给（最小单位整数）。失败抛异常（上层转 exit 1）。"""
    url = rpc or DEFAULT_RPC[chain]
    if chain == "solana":
        res = _post(url, {"jsonrpc": "2.0", "id": 1, "method": "getTokenSupply",
                          "params": [mint]}, proxy)
        return int(res["result"]["value"]["amount"])
    res = _post(url, {"jsonrpc": "2.0", "id": 1, "method": "eth_call",
                      "params": [{"to": token, "data": SEL_TOTSUP}, "latest"]}, proxy)
    hexval = res["result"]
    if not hexval or hexval == "0x":
        raise ValueError(f"eth_call totalSupply 返回空（{hexval!r}）——地址/链是否正确？")
    return int(hexval, 16)


def main():
    ap = argparse.ArgumentParser(description="供给真值闸：重放净供给 vs 链上 totalSupply")
    ap.add_argument("--chain", required=True, choices=sorted(DEFAULT_RPC))
    ap.add_argument("--token", help="EVM 合约地址")
    ap.add_argument("--mint", help="Solana mint")
    ap.add_argument("--replay-stats", help="replay_stats.json 路径")
    ap.add_argument("--replay-net-raw", type=int, help="直接给重放净供给（最小单位）")
    ap.add_argument("--rpc")
    ap.add_argument("--proxy")
    ap.add_argument("--tolerance-bps", type=int, default=10)
    ap.add_argument("--out", default="supply_truth.json")
    a = ap.parse_args()

    try:
        if a.replay_net_raw is not None:
            replay_net, mint_t, burn_t = a.replay_net_raw, None, None
        elif a.replay_stats:
            with open(a.replay_stats) as f:
                mint_t, burn_t = parse_replay_stats(json.load(f))
            replay_net = mint_t - burn_t
        else:
            print("必须给 --replay-stats 或 --replay-net-raw", file=sys.stderr)
            return 1
        if a.chain == "solana" and not a.mint:
            print("solana 链必须给 --mint", file=sys.stderr)
            return 1
        if a.chain != "solana" and not a.token:
            print("EVM 链必须给 --token", file=sys.stderr)
            return 1
        onchain = fetch_onchain_supply(a.chain, a.token, a.mint, a.rpc, a.proxy)
    except Exception as e:  # 网络/字段/文件——检测自身失败，禁当 PASS
        print(f"检测自身失败（exit 1，修通道重跑）: {e}", file=sys.stderr)
        return 1

    verdict, diff, diff_bps = decide(replay_net, onchain, a.tolerance_bps)
    result = {
        "gate": "supply_truth", "chain": a.chain,
        "token": a.token or a.mint,
        "replay_net": str(replay_net), "mint_total": str(mint_t) if mint_t is not None else None,
        "burn_total": str(burn_t) if burn_t is not None else None,
        "onchain_total_supply": str(onchain),
        "diff": str(diff), "diff_bps": round(diff_bps, 4) if diff_bps is not None else None,
        "tolerance_bps": a.tolerance_bps, "verdict": verdict,
        "exit_code": 0 if verdict == "PASS" else 2,
        "on_fail": ("余额禁用重放结果改链上实时直查；地址全集/转账历史仍可用重放；"
                    "重放余额仅可作≥阈值超集筛选" if verdict == "FAIL" else None),
    }
    with open(a.out, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    ratio = f"{diff_bps:.1f}bps" if diff_bps is not None else "n/a"
    print(f"[supply_truth] {verdict}  重放净供给={replay_net}  链上={onchain}  差={diff}（{ratio}，容差 {a.tolerance_bps}bps）→ {a.out}")
    if verdict == "FAIL":
        print("[supply_truth] FAIL：存在静默改账/记账错位。余额改走链上实时直查，重放余额仅作超集筛选。", file=sys.stderr)
    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
