#!/usr/bin/env python3
"""传仓网络 BFS 追踪器：从种子地址沿大额出账边自动追到终点（CEX/池子/现持仓/粉尘化分发/中转）。
来源：AKE(BSC) 分析会话实战产物，2026-07-19（v3.7 收编）。Eco 系 110 亿 5 层传仓链即由本工具追穿。
用法（工作目录含 data/merged.csv 与 data/balances_final.json，CEX/池子表按标的在脚本头部字典补充）：
  python3 trace_network.py <输出.json> <seed1> [seed2 ...]
边阈值 MIN_EDGE（默认 5000 万枚）与 MAX_HOPS（6 跳）按标的体量调整。
注意：输出打印为截断地址，凡进实体表的地址必须回 merged.csv 验证存在性+走量（防投毒幽灵，见 playbook §6）。
"""
import csv, json, sys
from collections import defaultdict

MIN_EDGE = 5e7 * 1e18   # 5000 万枚
MAX_HOPS = 6

CEX = {
 "0xc882b111a75c0c657fc507c04fbfcd2cc984f071": "Gate.io 5",
 "0x0d0707963952f2fba59dd06f2b425ace40b492fe": "Gate.io 1",
 "0x73d8bd54f7cf5fab43fe4ef40a62d390644946db": "BinanceAlphaRouter",
 "0x4982085c9e2f89f2ecb8131eca71afad896e89cb": "MEXC 13",
 "0x7dafba1d69f6c01ae7567ffd7b046ca03b706f83": "Kraken 245",
 "0xcc282e2004428939ee5149a9e7872f0b4d5d5ec7": "Kraken HW3",
 "0xb8e6d31e7b212b2b7250ee9c26c56cebbfbe6b23": "KuCoin 15",
 "0x17a30350771d02409046a683b18fe1c13ccfc4a8": "KuCoin 29",
 "0x53f78a071d04224b8e254e243fffc6d9f2f3fa23": "KuCoin 31",
 "0xcded3bb9d2dc98f6e4e772095b48051acfb84df9": "KuCoin 56",
 "0x124d9bf2fecbc16b54ec4accdb14d44c2144f012": "LBank 5",
}
try:
    r2 = json.load(open('data/research/route2_cex_wallets.json'))
    for grp in (r2.get('cex_hotwallets') or {}).values():
        for it in grp or []:
            a = (it.get('address') or '').lower()
            if a:
                CEX.setdefault(a, it.get('label') or 'cex')
    for it in r2.get('top100_labeled') or []:
        a = (it.get('address') or '').lower()
        if a:
            CEX.setdefault(a, it.get('label') or 'cex')
except Exception:
    pass

POOLS = {
 "0x4d3bf29ba30f8bfe4624e7678709afa195689c5d": "PancakeV3主池",
 "0x83fcd80d7973cca1aa821590bbec66d27a2d4ad4": "UniV3_USDT池",
 "0x28e2ea090877bf75740558f6bfb36a5ffee9e9df": "UniV4_PoolManager",
 "0x48198e931598bdbfa2171e8fe9767a09c13066ff": "V3小池",
 "0x31e492e0b47ebda736b8655f6e9cb564bc9d4435": "V2_WBNB池",
 "0x168770fc147cbe3b94e958bb9404dde5406dde08": "V2_USDT池",
}

print("[index] 建边表…", file=sys.stderr)
out_edges = defaultdict(lambda: defaultdict(int))   # from -> to -> sum
out_count = defaultdict(int)
in_count = defaultdict(int)
with open('data/merged.csv') as f:
    rr = csv.reader(f)
    next(rr)
    for row in rr:
        _, _, _, _, frm, to, val = row
        out_edges[frm][to] += int(val)
        out_count[frm] += 1
        in_count[to] += 1

bal = json.load(open('data/balances_final.json'))

seeds = [s.lower() for s in sys.argv[2:]]
outpath = sys.argv[1]
visited = set()
frontier = [(s, 0) for s in seeds]
nodes = {}
edges = []
while frontier:
    addr, hop = frontier.pop(0)
    if addr in visited or hop > MAX_HOPS:
        continue
    visited.add(addr)
    cur = int(bal.get(addr, 0)) / 1e18
    n_out = out_count.get(addr, 0)
    kind = "transit"
    label = ""
    if addr in CEX:
        kind, label = "CEX", CEX[addr]
    elif addr in POOLS:
        kind, label = "POOL", POOLS[addr]
    elif cur > 5e7:
        kind = "HOLDER"
    elif n_out > 3000:
        kind = "DUST_DISTRIBUTOR"   # 粉尘化分发（数千笔出账）
    nodes[addr] = {"hop": hop, "kind": kind, "label": label, "cur_bal": cur,
                   "n_out": n_out, "n_in": in_count.get(addr, 0)}
    if kind in ("CEX", "POOL", "DUST_DISTRIBUTOR"):
        continue   # 终点不外扩
    for to, amt in sorted(out_edges.get(addr, {}).items(), key=lambda kv: -kv[1]):
        if amt < MIN_EDGE:
            break
        edges.append({"from": addr, "to": to, "amount": amt / 1e18, "hop": hop})
        if to not in visited:
            frontier.append((to, hop + 1))

json.dump({"nodes": nodes, "edges": edges}, open(outpath, "w"), indent=1)
# 摘要
kinds = defaultdict(list)
for a, n in nodes.items():
    kinds[n["kind"]].append((a, n))
print(f"节点 {len(nodes)}，边 {len(edges)}")
for k in ("CEX", "POOL", "HOLDER", "DUST_DISTRIBUTOR", "transit"):
    lst = kinds.get(k, [])
    tot = sum(x[1]["cur_bal"] for x in lst)
    print(f"  {k}: {len(lst)} 个" + (f"（现持合计 {tot:,.0f}）" if k == "HOLDER" else ""))
for a, n in sorted(kinds.get("HOLDER", []), key=lambda x: -x[1]["cur_bal"])[:15]:
    print(f"   HOLDER hop{n['hop']} {a} 现持 {n['cur_bal']:,.0f}")
for a, n in sorted(kinds.get("CEX", []), key=lambda x: x[1]["hop"])[:10]:
    print(f"   CEX hop{n['hop']} {a} {n['label']}")
