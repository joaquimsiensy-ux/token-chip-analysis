#!/usr/bin/env python3
"""批量 RPC 通用件（net.py 的第一个实战消费者，B5 2026-07-22）。

替代各分析会话里现场手写的"线程池/curl 子进程批量 getCode/收据"模式：
进程内异步（无子进程树可被沙箱杀）+ 令牌桶限速 + 统一重试。

用法:
  # 批量判 EOA/合约（金库性质判定、聚类前设施筛查的标配动作）
  python3 rpc_batch.py <rpc_url> getcode <地址文件|逗号串> --chain bsc [--out out.json]
  # 批量交易收据（对价重建/gas 溯源）
  python3 rpc_batch.py <rpc_url> receipts <txhash文件|逗号串> --chain bsc [--out out.json]
  # 任意方法（每行 JSON: {"method": "...", "params": [...], "key": "可选结果键"}）
  python3 rpc_batch.py <rpc_url> raw <jsonl文件> --chain bsc [--out out.json]
通用参数: --rps 8 --conc 8 --browser-ua(robinhood 链 WAF 必开) --attempts 6

输出:
  getcode  -> {addr: {"code_len": N, "is_contract": bool}}   （code 本体太长不落盘，
              需要字节码指纹时用 raw 模式自取）
  receipts -> {txhash: 收据对象或 null}
  raw      -> {key或序号: result}
失败项记 {"error": ...}，退出码: 全成 0 / 有失败 1（fail-loud，别拿部分结果当全量）。
（来源：B5 网络层改造，2026-07-22）"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chain_registry import attested_evm_chains  # noqa: E402
from net import RpcAttestationError, attested_rpc_pool  # noqa: E402


def load_list(src, pattern, what):
    if os.path.exists(src):
        items = [ln.strip() for ln in open(src) if ln.strip()]
    else:
        items = [s.strip() for s in src.split(",") if s.strip()]
    for x in items:
        if not re.fullmatch(pattern, x):
            sys.exit(f"[fatal] 不是合法{what}: {x}")
    # 去重保序
    seen, out = set(), []
    for x in items:
        lx = x.lower()
        if lx not in seen:
            seen.add(lx)
            out.append(lx)
    return out


def main():
    ap = argparse.ArgumentParser(description="批量 RPC（进程内异步+限速+重试）")
    ap.add_argument("rpc_url")
    ap.add_argument("mode", choices=["getcode", "receipts", "raw"])
    ap.add_argument("src", help="文件路径或逗号分隔串（raw 模式必须是 jsonl 文件）")
    ap.add_argument("--chain", required=True,
                    choices=sorted(attested_evm_chains()),
                    help="目标链；chain id 只读 chain_registry")
    ap.add_argument("--out", default=None)
    ap.add_argument("--rps", type=float, default=8.0)
    ap.add_argument("--conc", type=int, default=8)
    ap.add_argument("--attempts", type=int, default=6)
    ap.add_argument("--browser-ua", action="store_true",
                    help="带浏览器 UA（robinhood 链 RPC 的 WAF 必开）")
    a = ap.parse_args()

    pool = attested_rpc_pool(
        a.rpc_url, a.chain, formal=True, rps=a.rps, concurrency=a.conc,
        attempts=a.attempts, browser_ua=a.browser_ua)
    try:
        pool.attest()
    except RpcAttestationError as exc:
        print(f"[fatal] RPC chain attestation failed: {exc}", file=sys.stderr)
        return 1

    if a.mode == "getcode":
        addrs = load_list(a.src, r"0x[0-9a-fA-F]{40}", "EVM 地址")
        res = pool.call_many([("eth_getCode", [x, "latest"]) for x in addrs])
        out = {}
        for addr, r in zip(addrs, res):
            if r["ok"]:
                code = r["result"] or "0x"
                out[addr] = {"code_len": max(0, (len(code) - 2) // 2),
                             "is_contract": code not in ("0x", "0x0", None)}
            else:
                out[addr] = {"error": r["error"]}
        n_c = sum(1 for v in out.values() if v.get("is_contract"))
        n_e = sum(1 for v in out.values() if "error" in v)
        print(f"[SUMMARY] {len(addrs)} 址 | 合约 {n_c} | EOA {len(addrs) - n_c - n_e} | 失败 {n_e}")
    elif a.mode == "receipts":
        txs = load_list(a.src, r"0x[0-9a-fA-F]{64}", "交易哈希")
        res = pool.call_many([("eth_getTransactionReceipt", [x]) for x in txs])
        out = {}
        for tx, r in zip(txs, res):
            out[tx] = r["result"] if r["ok"] else {"error": r["error"]}
        n_e = sum(1 for v in out.values() if isinstance(v, dict) and "error" in v)
        print(f"[SUMMARY] {len(txs)} 收据 | 失败 {n_e}")
    else:
        calls, keys = [], []
        for i, ln in enumerate(open(a.src)):
            ln = ln.strip()
            if not ln:
                continue
            j = json.loads(ln)
            calls.append((j["method"], j.get("params", [])))
            keys.append(str(j.get("key", i)))
        res = pool.call_many(calls)
        out = {k: (r["result"] if r["ok"] else {"error": r["error"]})
               for k, r in zip(keys, res)}
        n_e = sum(1 for r in res if not r["ok"])
        print(f"[SUMMARY] {len(calls)} 调用 | 失败 {n_e}")

    if a.out:
        tmp = a.out + ".tmp"
        with open(tmp, "w") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        os.replace(tmp, a.out)
        print(f"[out] {a.out}")
    else:
        print(json.dumps(out, ensure_ascii=False)[:2000])

    has_err = any(
        (isinstance(v, dict) and "error" in v) for v in out.values())
    return 1 if has_err else 0


if __name__ == "__main__":
    raise SystemExit(main())
