#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段三·关联地址聚类(本次从零设计的规则,不套任何历史模板)
来源：FIL(Filecoin) 分析会话实战产物, 2026-07。
用法: python3 cluster.py   (输入 analysis/ 下 analyze_base.py 的产物,输出 clusters.json)

三类独立证据:
  E1 共同首笔资金来源(funder 为交易所/热钱包时证据作废——人人都从交易所提币)
  E2 top200 之间直接互转(任一端为交易所则作废;≥1万 FIL 强边,否则中边)
  E3 vanity 后缀(≥4 字符相同的地址尾缀;f1 地址为随机哈希,同尾缀概率约 1/32^4,仅作佐证/弱边)

连通分量只用强/中边;簇置信度:
  HIGH = ≥2 类独立证据,或单类≥2条强边
  MED  = 单类 1 条强边或多条中边
  LOW  = 仅弱证据(不成簇,仅列出线索)
"""
import json, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
AN = os.path.join(HERE, "analysis")

# v4.2：接入批量标签库 resolver（codex 第四轮复核：README 宣称"全链路接入"但本脚本
# 此前只读项目内 labels.json——labels-filecoin.csv 的官方设施标签对 FIL 聚类实际不生效）
sys.path.insert(0, os.path.join(HERE, '..', 'labels'))
from labels_resolver import LabelResolver
_RESV = LabelResolver('filecoin')
_RESV.warn_if_degraded()

def load(p, default=None):
    fp = os.path.join(AN, p) if not os.path.isabs(p) else p
    if os.path.exists(fp):
        with open(fp) as f:
            return json.load(f)
    return default

rows = load("top200_flows.json")
common_funders = load("common_funders.json", {})
edges = load("edges_top200.json", [])
labels = load(os.path.join(HERE, "labels.json"), {})  # 阶段二考证产出: addr -> {entity, category, confidence}

byaddr = {r["address"]: r for r in rows}
ranks = {r["address"]: r["rank"] for r in rows}

def is_exchange_like(addr):
    """交易所/托管/热钱包:批量标签库 no_merge 命中(v4.2),或项目 labels.json 命中,
    或转账笔数巨大(启发式)"""
    if _RESV.no_merge(addr):
        return True
    lab = labels.get(addr) or {}
    if lab.get("category") in ("exchange", "custodian", "bridge_or_defi"):
        return True
    r = byaddr.get(addr)
    if r and (r.get("transfer_count") or 0) > 50000:
        return True
    return False

# ---------- 收集证据边 ----------
evid_edges = []   # {a, b, kind, strength, detail}

# E1 共同 funder
for funder, members in common_funders.items():
    if is_exchange_like(funder):
        continue
    fl = labels.get(funder) or {}
    ms = [m for m in members if m["address"] in byaddr]
    for i in range(len(ms)):
        for j in range(i + 1, len(ms)):
            a, b = ms[i], ms[j]
            near = abs(a["first_ts"] - b["first_ts"]) <= 30 * 86400
            evid_edges.append({
                "a": a["address"], "b": b["address"], "kind": "E1共同资金来源",
                "strength": "strong" if near else "medium",
                "detail": f"同一 funder {funder[:20]}…({fl.get('entity','未知')}) 首笔注资:"
                          f"{a['date']} {a['fil']:,.0f} FIL / {b['date']} {b['fil']:,.0f} FIL",
                "funder": funder,
            })

# E2 直接互转
for e in edges:
    if is_exchange_like(e["from"]) or is_exchange_like(e["to"]):
        continue
    evid_edges.append({
        "a": e["from"], "b": e["to"], "kind": "E2直接互转",
        "strength": "strong" if e["fil"] >= 10000 else "medium",
        "detail": f"近6个月 #{e['from_rank']}→#{e['to_rank']} 直接转账 {e['fil']:,.0f} FIL",
    })

# E3 vanity 后缀(弱,仅佐证)
suffix_groups = defaultdict(list)
for a in byaddr:
    if a.startswith("f1") and len(a) > 6:
        suffix_groups[a[-4:]].append(a)
weak_hints = []
for suf, addrs in suffix_groups.items():
    if len(addrs) >= 2:
        weak_hints.append({"kind": "E3相同尾缀", "suffix": suf,
                           "addresses": addrs,
                           "detail": f"{len(addrs)} 个地址共享尾缀 …{suf}(随机概率约百万分之一/对)"})

# ---------- 连通分量(strong+medium 边) ----------
parent = {}
def find(x):
    parent.setdefault(x, x)
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x
def union(x, y):
    parent[find(x)] = find(y)

for e in evid_edges:
    union(e["a"], e["b"])

comp = defaultdict(list)
for a in set([e["a"] for e in evid_edges] + [e["b"] for e in evid_edges]):
    comp[find(a)].append(a)

overview = load(os.path.join(HERE, "data", "overview.json"))
circ = int(overview["circulatingSupply"]) / 1e18

clusters = []
for root, members in comp.items():
    if len(members) < 2:
        continue
    med = [e for e in evid_edges if e["a"] in members and e["b"] in members]
    kinds = {e["kind"] for e in med}
    strongs = [e for e in med if e["strength"] == "strong"]
    if len(kinds) >= 2 or len(strongs) >= 2:
        conf = "HIGH"
    elif strongs or len(med) >= 2:
        conf = "MED"
    else:
        conf = "LOW"
    # vanity 佐证
    hints = [h for h in weak_hints if len(set(h["addresses"]) & set(members)) >= 2]
    bal = sum(byaddr[m]["balance_fil"] for m in members)
    clusters.append({
        "members": sorted(members, key=lambda m: ranks.get(m, 999)),
        "member_ranks": sorted(ranks.get(m, 999) for m in members),
        "total_fil": round(bal),
        "pct_circulating": round(bal / circ * 100, 2),
        "confidence": conf,
        "evidence": med,
        "vanity_hints": hints,
        "labels": {m: labels.get(m) for m in members if labels.get(m)},
    })

clusters.sort(key=lambda c: -c["total_fil"])
out = {"clusters": clusters, "weak_hints_unclustered": weak_hints,
       "labels_meta": _RESV.meta()}   # v4.2：标签库口径进产物，事后可审计
json.dump(out, open(os.path.join(AN, "clusters.json"), "w"), ensure_ascii=False, indent=1)

print(f"识别出 {len(clusters)} 个关联簇(≥2成员)")
for c in clusters:
    print(f"\n[{c['confidence']}] 成员排名 {c['member_ranks']} 合计 {c['total_fil']:,} FIL = 流通量 {c['pct_circulating']}%")
    for e in c["evidence"][:6]:
        print(f"   - {e['kind']}({e['strength']}): {e['detail']}")
    for h in c["vanity_hints"]:
        print(f"   - 佐证 {h['detail']}")
