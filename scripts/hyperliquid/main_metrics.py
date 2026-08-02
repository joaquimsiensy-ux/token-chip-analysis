#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hyperliquid 阶段2主计算：配置驱动的聚类/团队分发/CEX流向/创世留存。
输入: data/addresses/*.json, data/entities/*, data/static/*
输出: analysis/out/{clusters,vesting_trace,cex_flows,retention}.json
用法: python3 main_metrics.py   (在 <BASE>/ 的子目录放置本脚本,BASE 下须有 data/)
"""
import argparse, json, glob, os
from collections import defaultdict
from datetime import datetime, timezone

ap = argparse.ArgumentParser()
ap.add_argument("--config", default=os.path.join(os.path.dirname(__file__), "config.json"))
args, _ = ap.parse_known_args()
CFG = json.load(open(args.config))
allowed = {"token_symbol", "token_id", "candle_coin", "tge_ms", "snapshot_start_s",
           "entities", "team_entity", "fills_recent_entity", "evm_bridge", "watch",
           "summary_fund", "summary_cols", "data_dir", "out_dir", "system_addresses",
           "cex_keywords", "min_transfer_amount", "genesis_min_amount", "genesis_window_days",
           "asset_type"}
unknown = {k for k in CFG if not k.startswith("_comment") and k not in allowed}
required = {"token_symbol", "tge_ms", "entities", "team_entity", "system_addresses",
            "asset_type"}
if unknown or not required <= set(CFG):
    raise SystemExit(f"config schema 非法 unknown={sorted(unknown)} missing={sorted(required-set(CFG))}")
if CFG["asset_type"] not in {"spot", "native"}:
    raise SystemExit("asset_type 只允许 spot|native")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = CFG.get("data_dir") or os.path.join(BASE, "data")
OUT = CFG.get("out_dir") or os.path.join(BASE, "analysis", "out")
os.makedirs(OUT, exist_ok=True)

def load(rel):
    return json.load(open(os.path.join(DATA, rel.removeprefix("data/"))))

aliases = load("data/static/global_aliases.json")
AMAP = {}
if isinstance(aliases, dict):
    AMAP = {k.lower(): v for k, v in aliases.items()}
else:
    for a in aliases:
        if isinstance(a, dict):
            AMAP[a.get("address", "").lower()] = a.get("alias") or a.get("name")

# 批量标签库兜底（v4 2026-07-17：labels-hyperliquid.csv 首建后接入；--no-labels 关闭）
# 作用：①AMAP（本次现拉的 aliases）之外的静态标签兜底 ②聚类合并边 no_merge 拦截
import sys as _sys
_sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "labels"))
RESV = None
if "--no-labels" not in _sys.argv:
    try:
        from labels_resolver import LabelResolver
        RESV = LabelResolver("hyperliquid")
        if not RESV.warn_if_degraded():
            print(f"批量标签库: hyperliquid 表 {len(RESV.table)} 条已加载（--no-labels 可关闭）")
            for _a, _row in RESV.table.items():
                AMAP.setdefault(_a, _row["name"])
    except Exception as _e:
        print(f"[labels][degraded_mode] labels_resolver 不可用（{_e}）——本次运行无标签兜底", file=_sys.stderr)

CEX_KEY = tuple(CFG.get("cex_keywords") or ("Binance", "OKX", "Bybit", "KuCoin", "Gate", "MEXC"))
CEX = {k for k, v in AMAP.items() if v and any(x in v for x in CEX_KEY)}
ENTITIES = {k: v.lower() for k, v in CFG["entities"].items()}
SYS = {a.lower() for a in CFG["system_addresses"]}
TEAM = ENTITIES[CFG["team_entity"]]
ASSET = CFG["token_symbol"]
TGE_MS = int(CFG["tge_ms"])
MIN_TRANSFER = float(CFG.get("min_transfer_amount", 1000))
GENESIS_MIN = float(CFG.get("genesis_min_amount", 100))
GENESIS_DAYS = int(CFG.get("genesis_window_days", 60))

holders = {k.lower(): float(v) for k, v in load("data/static/holders.json")["holders"].items()}
td = load("data/static/token_details.json")
CIRC = float(td["circulatingSupply"])
GEN = {a.lower(): float(b) for a, b in td["genesis"]["userBalances"]}

def month(ms): return datetime.fromtimestamp(ms/1000, tz=timezone.utc).strftime("%Y-%m")

# ---------- 读入所有地址级数据 ----------
ADDR = {}
for p in glob.glob(os.path.join(DATA, "addresses", "*.json")):
    d = json.load(open(p))
    ADDR[d["addr"].lower()] = d

def total_holding(a):
    """现货 + 质押 + 待提取"""
    spot = holders.get(a, 0.0)
    d = ADDR.get(a, {}).get("delegation") or {}
    return spot + float(d.get("delegated", 0) or 0) + float(d.get("totalPendingWithdrawal", 0) or 0)

# ---------- 1) 构图聚类 ----------
edges = defaultdict(set)          # (a,b)排序对 -> 证据类型集合
transfer_amt = defaultdict(float)

first_hype_in = {}                # addr -> (time, source) 首笔标的入账
event_minutes = defaultdict(set)  # addr -> 分钟桶集合（转账行为时序指纹）
genesis_sink = defaultdict(set)   # sink -> 来自哪些 genesis 地址（TGE 后 60 天内）

for a, d in ADDR.items():
    for ev in d["ledger"]:
        dl = ev.get("delta", {})
        t = dl.get("type")
        if t in ("spotTransfer", "send") and dl.get("token") == ASSET:
            amt = float(dl.get("amount", 0) or 0)
            src = (dl.get("user") or "").lower()
            dst = (dl.get("destination") or "").lower()
            if not src or not dst or src == dst:
                continue
            # 首笔入账
            if dst == a and (a not in first_hype_in or ev["time"] < first_hype_in[a][0]):
                first_hype_in[a] = (ev["time"], src)
            # 直接转账边（双方均非 CEX/系统）
            if amt >= MIN_TRANSFER and src not in CEX | SYS and dst not in CEX | SYS:
                key = tuple(sorted((src, dst)))
                edges[key].add("transfer")
                transfer_amt[key] += amt
            # genesis 归集：genesis 地址在 TGE 后 60 天内把 HYPE 汇出
            if src in GEN and ev["time"] < TGE_MS + GENESIS_DAYS*86400_000 \
                    and amt >= GENESIS_MIN and dst not in CEX | SYS:
                genesis_sink[dst].add(src)
            if src == a:
                event_minutes[a].add(ev["time"] // 60000)

# 共同资金来源 fan-out：同一 source 给多个地址做首笔注资
by_src = defaultdict(list)
for a, (t, src) in first_hype_in.items():
    if src not in CEX | SYS and src != TEAM:
        by_src[src].append((t, a))
for src, lst in by_src.items():
    lst.sort()
    for i in range(len(lst)):
        for j in range(i+1, len(lst)):
            if lst[j][0] - lst[i][0] <= 72*3600_000:
                key = tuple(sorted((lst[i][1], lst[j][1])))
                edges[key].add("common_funding")

# genesis fan-in 归集边
for sink, sources in genesis_sink.items():
    if len(sources) >= 3:
        for s in sources:
            key = tuple(sorted((s, sink)))
            edges[key].add("genesis_fanin")

# 时序同步（仅对 worklist 内地址两两比较代价高——限制在有≥5个时间桶的地址）
sync_cand = {a: m for a, m in event_minutes.items() if len(m) >= 5}
keys = sorted(sync_cand)
for i in range(len(keys)):
    for j in range(i+1, len(keys)):
        a, b = keys[i], keys[j]
        inter = sync_cand[a] & sync_cand[b]
        if len(inter) >= 3:
            jac = len(inter) / len(sync_cand[a] | sync_cand[b])
            if jac > 0.6:
                edges[tuple(sorted((a, b)))].add("time_sync")

# 枢纽剔除：与超过 HUB_DEG 个不同地址有边的节点视为服务商（OTC/部署者/归集服务），
# 其边不作为"同一实体"证据（否则会把无关地址桥接成超级大杂烩集群）
deg = defaultdict(set)
for (a, b) in edges:
    deg[a].add(b); deg[b].add(a)
HUB_DEG = 15
HUBS = {a for a, s in deg.items() if len(s) > HUB_DEG}
print(f"识别服务枢纽 {len(HUBS)} 个（连接对手 >{HUB_DEG}），其边不参与聚类")

# 成边条件：双方均非枢纽，且 ≥2 类证据或 1 类强证据；标签库设施/公共通道禁作合并边（v4）
STRONG = {"transfer", "common_funding", "genesis_fanin"}
_label_blocked = set()
adj = defaultdict(set)
for (a, b), ev in edges.items():
    if a in HUBS or b in HUBS:
        continue
    if RESV is not None and (RESV.no_merge(a) or RESV.no_merge(b)):
        _label_blocked.add(a if RESV.no_merge(a) else b)
        continue
    if len(ev) >= 2 or (ev & STRONG):
        adj[a].add(b); adj[b].add(a)
if _label_blocked:
    print(f"批量标签库拦截 {len(_label_blocked)} 个设施地址不作合并边: "
          + ", ".join(sorted(_label_blocked)[:6]) + ("…" if len(_label_blocked) > 6 else ""))

# 连通分量
seen, clusters = set(), []
for start in adj:
    if start in seen: continue
    comp, stack = set(), [start]
    while stack:
        x = stack.pop()
        if x in seen: continue
        seen.add(x); comp.add(x)
        stack.extend(adj[x] - seen)
    clusters.append(comp)

cluster_rows = []
for comp in clusters:
    hold = sum(total_holding(a) for a in comp)
    ev_types = set()
    for (a, b), ev in edges.items():
        if a in comp and b in comp: ev_types |= ev
    cluster_rows.append({
        "size": len(comp),
        "holding": hold,
        "pct_circ": hold / CIRC * 100,
        "evidence": sorted(ev_types),
        "members": sorted(comp, key=lambda x: -total_holding(x))[:50],
        "labels": sorted({lbl for m in comp for lbl in [AMAP.get(m)] if lbl}),
    })
cluster_rows.sort(key=lambda r: -r["holding"])
json.dump(cluster_rows, open(os.path.join(OUT, "clusters.json"), "w"), ensure_ascii=False)
big = [c for c in cluster_rows if c["pct_circ"] >= 1.0]
print(f"聚类: {len(cluster_rows)} 个集群; ≥1% 流通盘的 {len(big)} 个")
for c in cluster_rows[:10]:
    print(f"  成员{c['size']:>3} 持仓{c['holding']/1e6:>7.2f}M ({c['pct_circ']:.2f}%) 证据{c['evidence']} 标签{c['labels'][:3]}")

# ---------- 2) 团队 92 接收地址去向 ----------
wl = load("data/worklist.json")
team_recv = [a.lower() for a in wl["team_recv"]]
vest = {"kept_spot": 0.0, "restaked": 0.0, "to_cex": 0.0, "to_others": 0.0, "received": 0.0}
rows = []
for a in team_recv:
    d = ADDR.get(a)
    if not d: continue
    recv = out_cex = out_other = restake = 0.0
    for ev in d["ledger"]:
        dl = ev.get("delta", {})
        if dl.get("token") != ASSET: continue
        t = dl.get("type"); amt = float(dl.get("amount", 0) or 0)
        src = (dl.get("user") or "").lower(); dst = (dl.get("destination") or "").lower()
        if t in ("spotTransfer", "send"):
            if dst == a and src == TEAM: recv += amt
            elif src == a:
                if dst in CEX: out_cex += amt
                else: out_other += amt
        elif t == "cStakingTransfer" and dl.get("isDeposit"): restake += amt
    hold_now = total_holding(a)
    rows.append({"addr": a, "recv_from_team": recv, "to_cex": out_cex,
                 "to_others": out_other, "restaked": restake, "holding_now": hold_now})
    vest["received"] += recv; vest["to_cex"] += out_cex
    vest["to_others"] += out_other; vest["restaked"] += restake
    vest["kept_spot"] += hold_now
json.dump({"summary": vest, "rows": rows}, open(os.path.join(OUT, "vesting_trace.json"), "w"), ensure_ascii=False)
print(f"\n团队分发去向: 收到 {vest['received']/1e6:.2f}M | 转CEX {vest['to_cex']/1e6:.3f}M | "
      f"转他人 {vest['to_others']/1e6:.3f}M | 再质押 {vest['restaked']/1e6:.3f}M | 现持有 {vest['kept_spot']/1e6:.2f}M")

# ---------- 3) 全体 worklist 地址 → CEX 月度流向 ----------
cex_month = defaultdict(lambda: [0.0, 0.0])  # month -> [in_to_cex, out_from_cex]
for a, d in ADDR.items():
    for ev in d["ledger"]:
        dl = ev.get("delta", {})
        if dl.get("type") in ("spotTransfer", "send") and dl.get("token") == ASSET:
            amt = float(dl.get("amount", 0) or 0)
            src = (dl.get("user") or "").lower(); dst = (dl.get("destination") or "").lower()
            if dst in CEX and src == a: cex_month[month(ev["time"])][0] += amt
            if src in CEX and dst == a: cex_month[month(ev["time"])][1] += amt
json.dump(dict(cex_month), open(os.path.join(OUT, "cex_flows.json"), "w"))
print("\nworklist 地址 ↔ 已标注CEX 月度流向（近8月, 万枚）:")
for m in sorted(cex_month)[-8:]:
    i, o = cex_month[m]
    print(f"  {m}: 流入CEX {i/1e4:>8.1f} | 从CEX流出 {o/1e4:>8.1f} | 净流入CEX {(i-o)/1e4:>+8.1f}")

# ---------- 4) genesis top500 留存（含质押修正）----------
gen500 = sorted(GEN.items(), key=lambda kv: -kv[1])[:500]
gen500 = [(a, g) for a, g in gen500 if a not in SYS]
ret = {"full": 0, "partial": 0, "exited": 0, "no_data": 0}
tot_gen = tot_now = 0.0
for a, g in gen500:
    if a not in ADDR:
        ret["no_data"] += 1; continue
    h = total_holding(a)
    tot_gen += g; tot_now += min(h, g)
    if h >= g * 0.5: ret["full"] += 1
    elif h >= g * 0.1: ret["partial"] += 1
    else: ret["exited"] += 1
json.dump({"counts": ret, "tot_gen": tot_gen, "tot_now": tot_now},
          open(os.path.join(OUT, "retention.json"), "w"))
print(f"\ngenesis top500（排除系统实体, 质押修正后）: 保留≥50%: {ret['full']} | 10-50%: {ret['partial']} | "
      f"<10%(视为退出): {ret['exited']} | 无数据: {ret['no_data']}")
print(f"这些地址创世共 {tot_gen/1e6:.1f}M, 现仍持有(截顶) {tot_now/1e6:.1f}M = {tot_now/max(tot_gen,1)*100:.0f}%")
