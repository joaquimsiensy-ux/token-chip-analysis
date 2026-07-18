#!/usr/bin/env python3
"""U0 硬步骤：旧实体表地址 getCode 复检（EVM）——防公共设施/合约混入实体表被增量更新继承。
教训来源：TRASH 案 0x53bf（UniversalRouter 残留庄#1 实体表随 appendix 传代）、
RAXOL 案（公共 bot 卖币执行合约被误判协同实体）；脚本为 VEX(getcode_recheck) 实战
参数化收编（v2.10.0）。

检查范围 = appendix 的 whale_groups 全部地址 ∪ vault_addresses ∪ addresses 表
         ∪ --extra 文件补充地址（JSON: {addr: 备注} 或 [addr,...]）。
输出分类：EOA / CONTRACT(字节数) / EIP7702->委托目标 / RPC_FAIL。
非 EOA 条目务必逐个核对角色定义是否成立（"漏斗/中转/马甲"若实为公共合约＝实体定义错误），
并对疑似者查浏览器 counters（全链总 tx/币种数/调用者分散度——单币用户少≠私有）。

用法（工作目录含 config.json，config 需有 rpc 字段）：
  python3 getcode_recheck.py [--appendix appendix.json] [--extra extra_addrs.json]
                             [--out data/getcode_recheck.json]
"""
import argparse, json, sys, time
import urllib.request
import ssl, certifi

SSL_CTX = ssl.create_default_context(cafile=certifi.where())
DEFAULT_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def load_cfg():
    with open("config.json") as f:
        cfg = json.load(f)
    rpc = cfg.get("rpc") or ""
    if not rpc:
        sys.exit("config.json 缺 rpc 字段")
    return rpc, cfg.get("rpc_ua") or DEFAULT_UA


def rpc_call(rpc, ua, method, params, retry=6):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(rpc, data=body,
                                 headers={"Content-Type": "application/json", "User-Agent": ua})
    for i in range(retry):
        try:
            with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as r:
                return json.loads(r.read())["result"]
        except Exception:
            time.sleep(1.5 * (i + 1))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--appendix", default="appendix.json")
    ap.add_argument("--extra", default=None, help="补充地址 JSON（{addr:备注} 或 [addr,...]）")
    ap.add_argument("--out", default="data/getcode_recheck.json")
    args = ap.parse_args()

    rpc, ua = load_cfg()
    with open(args.appendix) as f:
        app = json.load(f)

    targets = {}
    for g in app.get("whale_groups", []):
        for a in g.get("addresses", []):
            targets[a.lower()] = g.get("label", f"实体#{g.get('id')}")
    for v in app.get("vault_addresses", []):
        targets.setdefault(v["address"].lower(), "金库表")
    for a in app.get("addresses", []):
        targets.setdefault(a["address"].lower(), (a.get("role") or "addresses表")[:40])
    if args.extra:
        with open(args.extra) as f:
            extra = json.load(f)
        if isinstance(extra, dict):
            for a, why in extra.items():
                targets.setdefault(a.lower(), str(why))
        else:
            for a in extra:
                targets.setdefault(a.lower(), "extra")

    out = {}
    for a, role in targets.items():
        code = rpc_call(rpc, ua, "eth_getCode", [a, "latest"])
        if code is None:
            kind = "RPC_FAIL"
        elif not code or code == "0x":
            kind = "EOA"
        elif code.startswith("0xef0100"):
            kind = f"EIP7702->0x{code[8:48]}"
        else:
            kind = f"CONTRACT({len(code)//2-1}B)"
        out[a] = {"role": role, "kind": kind}
        time.sleep(0.15)

    with open(args.out, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    n_c = sum(1 for v in out.values() if v["kind"].startswith("CONTRACT"))
    n_7702 = sum(1 for v in out.values() if v["kind"].startswith("EIP7702"))
    n_fail = sum(1 for v in out.values() if v["kind"] == "RPC_FAIL")
    print(f"复检 {len(out)} 址：合约 {n_c}、EIP7702 {n_7702}、RPC失败 {n_fail}（清单落盘 {args.out}）")
    for a, v in out.items():
        if v["kind"] != "EOA":
            print(f"  {a} [{v['role']}] {v['kind']}")
    if n_c:
        print("⚠ 实体表中存在合约地址：逐个核对是否公共设施（address-book.md 先查），"
              "误入的要在本次更新中剔除并写入复核修正记录（全落点同步：账本/实体表/图/JSON/文案）")


if __name__ == "__main__":
    main()
