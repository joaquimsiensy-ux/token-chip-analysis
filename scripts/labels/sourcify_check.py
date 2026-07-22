#!/usr/bin/env python3
"""Sourcify 合约验证批查——聚类前设施识别第三通道（补标签库 lookup 与 GoPlus 之外）。

价值：verified 合约名直接暴露地址身份（PancakeRouter / GnosisSafeProxy / UniswapV3Pool…），
代理合约连实现名一起返回（FiatTokenProxy -> FiatTokenV2_2）——把"这是路由/池/托管
Safe/代理"的判定做在聚类前，直接降低把设施地址错并进实体集群的风险。

用法:
  python3 sourcify_check.py <chain> <地址文件(每行一个)|逗号分隔地址串> [--out out.json]
  chain ∈ eth/bsc/base/arbitrum/polygon（Sourcify 无 robinhood 等小众链——不支持即明说，
  别拿 404 当"不是合约"）

输出 JSON: {addr(小写): {"verified": bool, "match": full|partial|null, "name": 合约名,
            "language", "proxy_type", "implementations": [{"address","name"}]}}
stdout 给摘要（verified 计数 + 名字直方图）。

实测（2026-07-22）：sourcify.dev 国内直连免代理免 key；0.2s 间隔 10 连发无 429；
未验证/EOA 返回 HTTP 404（match:null）——404 只说明"Sourcify 没有源码"，EOA/合约判定
仍以 eth_getCode 为准。⚠️ v1 批量端点 check-all-by-addresses 在 brownout 弃用期
（2026-07-07→2027-01-08 不可用），一律走 v2 逐地址。
（来源：B10 Sourcify 接入，2026-07-22）"""
import argparse
import json
import os
import re
import sys
import time

import requests

CHAIN_IDS = {"eth": 1, "bsc": 56, "base": 8453, "arbitrum": 42161, "polygon": 137}
BASE = "https://sourcify.dev/server/v2/contract"
FIELDS = "compilation,proxyResolution"


def query_one(sess, chain_id, addr):
    url = f"{BASE}/{chain_id}/{addr}?fields={FIELDS}"
    for attempt in range(6):
        try:
            r = sess.get(url, timeout=30)
        except requests.RequestException as e:
            print(f"[warn] {addr} 网络异常重试: {str(e)[:80]}", file=sys.stderr, flush=True)
            time.sleep(2 * (attempt + 1))
            continue
        if r.status_code == 404:
            return {"verified": False, "match": None}
        if r.status_code in (429, 500, 502, 503):
            time.sleep(3 * (attempt + 1))
            continue
        r.raise_for_status()
        j = r.json()
        comp = j.get("compilation") or {}
        prox = j.get("proxyResolution") or {}
        return {
            "verified": j.get("match") is not None,
            "match": j.get("match"),
            "name": comp.get("name"),
            "language": comp.get("language"),
            "proxy_type": prox.get("proxyType") if prox.get("isProxy") else None,
            "implementations": [
                {"address": (i.get("address") or "").lower(), "name": i.get("name")}
                for i in (prox.get("implementations") or [])],
        }
    return {"verified": None, "match": None, "error": "重试耗尽"}


def main():
    ap = argparse.ArgumentParser(description="Sourcify 合约验证批查")
    ap.add_argument("chain", choices=sorted(CHAIN_IDS))
    ap.add_argument("addrs", help="地址文件路径（每行一个）或逗号分隔地址串")
    ap.add_argument("--out", default=None, help="输出 JSON 路径（默认 stdout 打印全量）")
    ap.add_argument("--interval", type=float, default=0.25)
    a = ap.parse_args()

    if os.path.exists(a.addrs):
        raw = [ln.strip() for ln in open(a.addrs) if ln.strip()]
    else:
        raw = [s.strip() for s in a.addrs.split(",") if s.strip()]
    addrs = []
    for x in raw:
        if not re.fullmatch(r"0x[0-9a-fA-F]{40}", x):
            sys.exit(f"[fatal] 不是合法 EVM 地址: {x}")
        lx = x.lower()
        if lx not in addrs:
            addrs.append(lx)
    if not addrs:
        sys.exit("[fatal] 地址列表为空")

    cid = CHAIN_IDS[a.chain]
    sess = requests.Session()
    out, n_ver, n_proxy = {}, 0, 0
    for i, addr in enumerate(addrs, 1):
        res = query_one(sess, cid, addr)
        out[addr] = res
        if res.get("verified"):
            n_ver += 1
            if res.get("proxy_type"):
                n_proxy += 1
        if i % 25 == 0 or i == len(addrs):
            print(f"[prog] {i}/{len(addrs)} verified={n_ver}", file=sys.stderr, flush=True)
        time.sleep(a.interval)

    if a.out:
        tmp = a.out + ".tmp"
        with open(tmp, "w") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        os.replace(tmp, a.out)

    names = {}
    for r in out.values():
        if r.get("name"):
            names[r["name"]] = names.get(r["name"], 0) + 1
    print(f"[SUMMARY] {len(addrs)} 址 | verified {n_ver}（其中代理 {n_proxy}）| 未验证/EOA {len(addrs) - n_ver}")
    for nm, c in sorted(names.items(), key=lambda kv: -kv[1])[:20]:
        print(f"  {nm}: {c}")
    if a.out:
        print(f"[out] {a.out}")
    else:
        print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
