#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段三·基础量化:逐地址净流量 / 首笔资金来源 / 互转图 / 官方地址流出。
来源：FIL(Filecoin) 分析会话实战产物, 2026-07。
纯本地计算,输入 data/,输出 analysis/。用法: python3 analyze_base.py
"""
import json, os, datetime
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(HERE, "analysis")
os.makedirs(OUT, exist_ok=True)
CUTOFF = 1767225600  # 2026-01-01
ATTO = 1e18

def load(p):
    with open(p) as f:
        return json.load(f)

def d2s(ts):
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%d")

rl = load(os.path.join(DATA, "richlist.json"))
top = {}          # address -> richlist item
for i, it in enumerate(rl):
    it["rank"] = i + 1
    assert it["address"] not in top, f"富豪榜有重复地址 {it['address']},请先重抓"
    top[it["address"]] = it

def dedup(transfers):
    """按 (message,type,from,to,value) 去重——分页漂移会产生重复条目"""
    seen, out = set(), []
    for t in transfers:
        k = (t.get("message"), t.get("type"), t.get("from"), t.get("to"), t.get("value"))
        if k not in seen:
            seen.add(k)
            out.append(t)
    return out

# 地址可能以 robust(f1/f3)或 ID(f0)出现在流水里,建立双向映射
alias = {}        # any-form -> canonical(richlist address)
details = {}
for a in top:
    p = os.path.join(DATA, "addr", a, "detail.json")
    if os.path.exists(p):
        d = load(p) or {}
        details[a] = d
        alias[a] = a
        if d.get("id"):
            alias[d["id"]] = a
        if d.get("robust"):
            alias[d["robust"]] = a

rows = []          # 每地址汇总
edges = defaultdict(float)   # top200 互转边 (from_canon,to_canon) -> FIL
edge_seen = set()  # 同一笔转账在双方流水各出现一次,按消息键全局去重
funder_map = defaultdict(list)  # funder -> [(canon, first_ts, amount_fil)]
daily_net = defaultdict(lambda: defaultdict(float))  # canon -> date -> net FIL(近6个月)

for a, it in top.items():
    adir = os.path.join(DATA, "addr", a)
    det = details.get(a, {})
    rec_p = os.path.join(adir, "transfers_recent.json")
    ear_p = os.path.join(adir, "transfers_earliest.json")
    rec = load(rec_p) if os.path.exists(rec_p) else {"transfers": [], "truncated": False, "totalCount": None}
    ear = load(ear_p) if os.path.exists(ear_p) else {"transfers": []}

    inflow = outflow = 0.0
    for t in dedup(rec["transfers"]):
        v = int(t["value"]) / ATTO  # Filfox 的 value 自带方向符号:流入为正、流出为负
        ty = t.get("type")
        day = d2s(t["timestamp"])
        if v >= 0:
            inflow += v
        else:
            outflow += -v
        daily_net[a][day] += v
        # top200 互转边
        f_can, t_can = alias.get(t.get("from", "")), alias.get(t.get("to", ""))
        if f_can and t_can and f_can != t_can and ty in ("send", "transfer", "receive"):
            # 键用 abs(value):同一笔在双方流水里 value 符号相反,含符号会双计
            ek = (t.get("message"), t.get("from"), t.get("to"), abs(int(t.get("value", 0))))
            if ek not in edge_seen:
                edge_seen.add(ek)
                edges[(f_can, t_can)] += abs(v)

    # 首笔资金来源:最早的 receive(排除自己),取前3笔
    ear_sorted = sorted(ear["transfers"], key=lambda t: t["timestamp"])
    funders = []
    for t in ear_sorted:
        if t.get("type") == "receive" and t.get("from") and t["from"] != a:
            funders.append({"from": t["from"], "ts": t["timestamp"], "date": d2s(t["timestamp"]), "fil": abs(int(t["value"])) / ATTO})
        if len(funders) >= 3:
            break
    if funders:
        funder_map[funders[0]["from"]].append((a, funders[0]["ts"], funders[0]["fil"]))

    rows.append({
        "rank": it["rank"], "address": a, "id": det.get("id"),
        "balance_fil": int(it["balance"]) / ATTO,
        "actor": it.get("actor"),
        "created": d2s(it["createTimestamp"]),
        "last_seen": d2s(it["lastSeenTimestamp"]),
        "transfer_count": det.get("transferCount"),
        "owned_miners": len(det.get("ownedMiners", []) or []),
        "tag": (det.get("tag") or {}).get("name"),
        "in_6m": round(inflow, 2), "out_6m": round(outflow, 2), "net_6m": round(inflow - outflow, 2),
        "truncated": rec.get("truncated", False),
        "funders_first3": funders,
    })

rows.sort(key=lambda r: r["rank"])
json.dump(rows, open(os.path.join(OUT, "top200_flows.json"), "w"), ensure_ascii=False, indent=1)

# 共同资金来源(≥2个富豪榜地址由同一 funder 首笔注资)
common_funders = {
    f: [{"address": a, "first_ts": ts, "date": d2s(ts), "fil": round(v, 2), "rank": top[a]["rank"]} for a, ts, v in lst]
    for f, lst in funder_map.items() if len(lst) >= 2
}
json.dump(common_funders, open(os.path.join(OUT, "common_funders.json"), "w"), ensure_ascii=False, indent=1)

# 互转边
edge_list = [{"from": f, "to": t, "fil": round(v, 2), "from_rank": top[f]["rank"], "to_rank": top[t]["rank"]}
             for (f, t), v in sorted(edges.items(), key=lambda kv: -kv[1])]
json.dump(edge_list, open(os.path.join(OUT, "edges_top200.json"), "w"), ensure_ascii=False, indent=1)

# 官方标签地址流出(全历史)
official = {}
op = os.path.join(DATA, "official_scan.json")
if os.path.exists(op):
    for aid, d in load(op).items():
        tag = (d.get("tag") or {}).get("name")
        tp = os.path.join(DATA, "official", f"{aid}_transfers.json")
        if not tag or not os.path.exists(tp):
            continue
        outs = []
        for t in load(tp)["transfers"]:
            if t.get("type") in ("send", "transfer") and int(t["value"]) / ATTO >= 1000:
                outs.append({"date": d2s(t["timestamp"]), "to": t["to"], "fil": round(int(t["value"]) / ATTO, 2)})
        ms = d.get("multisig") or {}
        official[aid] = {
            "tag": tag, "balance_fil": round(int(d.get("balance", 0)) / ATTO, 2),
            "initial_fil": round(int(ms.get("initialBalance", 0)) / ATTO, 2) if ms else None,
            "unlock_end": d2s(ms["unlockEndTimestamp"]) if ms.get("unlockEndTimestamp") else None,
            "available_fil": round(int(ms.get("availableBalance", 0)) / ATTO, 2) if ms else None,
            "big_outs_all_history": outs,
        }
json.dump(official, open(os.path.join(OUT, "official_multisigs.json"), "w"), ensure_ascii=False, indent=1)

# 每日净流量矩阵(供时间序列图)
json.dump({a: dict(m) for a, m in daily_net.items()}, open(os.path.join(OUT, "daily_net.json"), "w"), ensure_ascii=False)

# 汇总统计
ov = load(os.path.join(DATA, "overview.json"))
circ = int(ov["circulatingSupply"]) / ATTO
tot_bal = sum(r["balance_fil"] for r in rows)
print(f"top200 地址数: {len(rows)}")
print(f"top200 合计: {tot_bal:,.0f} FIL = 流通量的 {tot_bal/circ*100:.1f}% (流通 {circ:,.0f})")
print(f"共同 funder 命中: {len(common_funders)} 组")
print(f"top200 互转边: {len(edge_list)} 条")
print(f"官方标签 multisig: {len(official)} 个")
print(f"净买入前10 (6个月):")
for r in sorted(rows, key=lambda r: -r["net_6m"])[:10]:
    print(f"  #{r['rank']} {r['address'][:22]} net {r['net_6m']:+,.0f} FIL (截断:{r['truncated']})")
print(f"净卖出前10 (6个月):")
for r in sorted(rows, key=lambda r: r["net_6m"])[:10]:
    print(f"  #{r['rank']} {r['address'][:22]} net {r['net_6m']:+,.0f} FIL (截断:{r['truncated']})")
