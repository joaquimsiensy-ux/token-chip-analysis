#!/usr/bin/env python3
"""U2 抽样对表：重放余额 vs 链上 balanceOf 实查（EVM）。
名单 = 旧研报全部实体地址（whale_groups ∪ 观察哨 watch ∪ addresses[watch=true]）
     + 最新 top20 + 固定种子随机 5 个中小户 —— 与 update-workflow U2 第 2 条一致。

来源：RAXOL(balance_check) / Pointless(verify_balances) / TRASH(reconcile_inc) /
VEX(verify_balances) 四次 /token-update 实战合并参数化收编（v2.10.0）。
归档块探测与"精确相等"口径取 Pointless 版（wei 级零误差；探测失败自动退 latest——
此时活跃地址（池/热钱包）因链头继续增长出现微差属正常，人工核对差异明细即可）。

用法（工作目录含 config.json，config 需有 "rpc" 字段；Robinhood 链 RPC 必须浏览器 UA，
config 可选 "rpc_ua" 覆盖默认）：
  python3 verify_balances.py [--balances data/balances_new.json] [--appendix appendix.json]
                             [--block N]   # 显式对账块；默认用 balances 文件 meta 的 last_block
appendix.json 缺失时自动改读 analysis-state.json（v3.3：未买入标的默认无监控包，同构机器子集）。
退出码（v3.3 硬关卡）：归档块口径全一致=0；归档块口径存在 MISMATCH=1（对账关卡 FAIL，回 U1 补数据）；
退化 latest 口径且存在差异=2（INCONCLUSIVE，不作放行依据——活跃地址天然微差，须换归档块或人工逐条核对）。
"""
import argparse, json, os, random, sys, time
import urllib.request
import ssl, certifi

SSL_CTX = ssl.create_default_context(cafile=certifi.where())
DEFAULT_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
ZERO = "0x" + "0" * 40


def load_cfg():
    with open("config.json") as f:
        cfg = json.load(f)
    token = (cfg.get("token") or "").lower()
    rpc = cfg.get("rpc") or ""
    ua = cfg.get("rpc_ua") or DEFAULT_UA
    dec = int(cfg.get("decimals", 18))
    if not rpc:
        sys.exit("config.json 缺 rpc 字段（如 https://rpc.mainnet.chain.robinhood.com）")
    if not token.startswith("0x"):
        sys.exit("config.json 的 token 缺失")
    return token, rpc, ua, dec


def load_balances(path):
    with open(path) as f:
        d = json.load(f)
    meta_block = d.get("last_block") if isinstance(d.get("balances"), dict) else None
    if isinstance(d.get("balances"), dict):
        d = d["balances"]
    return {k.lower(): int(v) for k, v in d.items()}, meta_block


def is_addr(a):
    return isinstance(a, str) and a.startswith("0x") and len(a) == 42


def build_names(app, bal):
    names = set()
    skipped = []
    for g in app.get("whale_groups", []):
        for a in g.get("addresses", []):
            (names.add(a.lower()) if is_addr(a) else skipped.append(a))
    for m in app.get("monitoring_advice", []):
        w = m.get("watch", "")
        (names.add(w.lower()) if is_addr(w) else (skipped.append(w) if str(w).startswith("0x") else None))
    for a in app.get("addresses", []):
        if a.get("watch"):
            aa = a.get("address", "")
            (names.add(aa.lower()) if is_addr(aa) else skipped.append(aa))
    for v in app.get("vault_addresses", []):
        aa = v.get("address", "")
        (names.add(aa.lower()) if is_addr(aa) else skipped.append(aa))
    if skipped:
        print(f"WARN: {len(skipped)} 个非标准地址值被跳过（poolId/缩写地址不许直接对表；"
              f"缩写须回旧数据 grep 解析——U0 4b 继承禁令）: {skipped[:5]}")
    pos = {k: v for k, v in bal.items() if v > 0 and k != ZERO}
    names.update(a for a, _ in sorted(pos.items(), key=lambda x: -x[1])[:20])
    random.seed(42)
    tot = sum(pos.values())
    mids = [a for a, v in pos.items() if tot * 5e-6 < v < tot * 5e-3 and a not in names]
    names.update(random.sample(mids, min(5, len(mids))))
    return sorted(names)


def batch_call(rpc, ua, token, addrs, tag):
    reqs = []
    for i, a in enumerate(addrs):
        data = "0x70a08231" + a[2:].rjust(64, "0")
        reqs.append({"jsonrpc": "2.0", "id": i, "method": "eth_call",
                     "params": [{"to": token, "data": data}, tag]})
    req = urllib.request.Request(rpc, data=json.dumps(reqs).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": ua})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=60, context=SSL_CTX) as r:
                res = json.loads(r.read())
                if isinstance(res, dict):  # 单条错误响应
                    raise RuntimeError(res.get("error"))
                out = {}
                for x in res:
                    if "result" not in x or not x["result"]:
                        raise RuntimeError(f"id {x.get('id')} 无 result: {x.get('error')}")
                    out[addrs[x["id"]]] = int(x["result"], 16)
                return out
        except Exception as e:
            print(f"  重试 {attempt+1}: {e}", flush=True)
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("RPC batch 连续失败")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--balances", default="data/balances_new.json")
    ap.add_argument("--appendix", default="appendix.json")
    ap.add_argument("--block", type=int, default=None)
    args = ap.parse_args()

    token, rpc, ua, dec = load_cfg()
    unit = 10 ** dec
    bal, meta_block = load_balances(args.balances)
    apath = args.appendix
    if not os.path.exists(apath) and apath == "appendix.json" and os.path.exists("analysis-state.json"):
        print("NOTE: 无 appendix.json（未买入标的无监控包），改读 analysis-state.json（U0 4c）")
        apath = "analysis-state.json"
    with open(apath) as f:
        app = json.load(f)
    names = build_names(app, bal)
    print(f"对表名单 {len(names)} 址（实体表∪观察哨∪top20∪随机5）")

    # 归档块探测：优先在数据末块对账（重放口径与链上时点严格对齐）
    blk = args.block if args.block is not None else meta_block
    tag = "latest"
    if blk is not None:
        try:
            batch_call(rpc, ua, token, names[:1], hex(blk))
            tag = hex(blk)
            print(f"归档查询可用：按块 {blk} 对账")
        except Exception:
            print(f"归档查询不可用（块 {blk}），退化 latest——活跃地址微差属正常")
    else:
        print("balances 文件无 last_block 元信息且未给 --block，用 latest")

    onchain = {}
    for i in range(0, len(names), 20):
        onchain.update(batch_call(rpc, ua, token, names[i:i + 20], tag))
        time.sleep(0.3)

    ok = bad = 0
    for a in names:
        r, o = bal.get(a, 0), onchain.get(a, 0)
        if r == o:
            ok += 1
        else:
            bad += 1
            print(f"MISMATCH {a}: 重放 {r/unit:,.2f} vs 链上 {o/unit:,.2f} (Δ {(r-o)/unit:+,.4f})")
    print(f"对表 {len(names)} 址：精确一致 {ok}、不一致 {bad}")
    # v3.3 硬关卡：文档承诺的"不过不进分析"由退出码兜底，不再依赖人读输出
    if bad and tag != "latest":
        print("FAIL: 归档块精确口径存在 MISMATCH=增量数据有洞（最常见：重叠窗处理错/窗口漏段）——回 U1 补数据")
        sys.exit(1)
    if bad:
        print("INCONCLUSIVE: latest 口径存在差异，不作对账关卡放行依据——换归档块重跑，或逐条人工确认均为截止后新交易")
        sys.exit(2)
    print(f"PASS{'' if tag != 'latest' else '（latest 口径——归档块不可用时的降级通过，结论按人工确认口径）'}")


if __name__ == "__main__":
    main()
