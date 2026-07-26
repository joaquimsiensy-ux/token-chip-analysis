#!/usr/bin/env python3
"""关联地址聚类（三条独立规则 + Union-Find）。
来源：OPN(BSC) 分析会话实战产物, 2026-07。

用法：python3 cluster.py <chain>   （工作目录含 config.json、<chain>_part_*.csv、gmgn/ 数据）
产物：<chain>_clusters.json + stdout 摘要

三条规则（互相独立，命中任一即合并）：
  R1 非交易所地址间累计直转 > 总量 0.005%（默认）
  R2 ≥2 地址共享同一非 CEX 的 gas 资金来源（GMGN native_transfer.from）
     —— CEX 热钱包绝不可作关联依据：从交易所提币的所有用户共享热钱包
  R3 从 team_treasury 一跳收币（标记 team_downstream，单独报告，不与外部集群混合）
排除：出度或入度 > 200 的服务型地址（空投分发器/DEX路由/聚合器/池子）。
定性纪律："币源 100% 可溯至金库"是 COMPUTED；"项目方控制"只能到 INFERRED MED——
静置的下游仓库无法排除 OTC 场外接币方。
"""
import json, glob, os, sys
from collections import defaultdict

_LABELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "labels")
if not os.path.isdir(_LABELS_DIR):
    # 脚本被拷贝到案目录跑时相对路径断裂（SPX6900 2026-07-25 实踩），回落 skill 安装位
    _LABELS_DIR = os.path.expanduser("~/.claude/skills/token-chip-analysis/scripts/labels")
sys.path.insert(0, _LABELS_DIR)
try:
    from labels_resolver import LabelResolver, append_misses   # 批量标签库共享内核（默认启用，--no-labels 关闭）
except Exception:
    LabelResolver = None
    append_misses = None
try:
    from gatekeeper import funnel_scan, scan_profiles   # v4.2 行为守门员（--no-gatekeeper 关闭）
except Exception:
    funnel_scan = None
    scan_profiles = None

DIR = os.getcwd()
CFG = json.load(open(os.path.join(DIR, "config.json")))
DEC = 10 ** CFG.get("decimals", 18)
Z = "0x0000000000000000000000000000000000000000"

LABELS = {}
for group in ("cex_wallets", "team_wallets", "mm_wallets"):
    for a, v in CFG.get(group, {}).items():
        if a.startswith("0x") and "|" in v:
            LABELS[a.lower()] = v.split("|", 1)[0]
CEX = {a for a, v in CFG.get("cex_wallets", {}).items() if a.startswith("0x")}
CEX = {a.lower() for a in CEX}
TEAM = {a.lower() for a, v in CFG.get("team_wallets", {}).items() if a.startswith("0x")}

class UF:
    def __init__(self): self.p = {}
    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]; x = self.p[x]
        return x
    def union(self, a, b): self.p[self.find(a)] = self.find(b)

def main(chain):
    # 批量标签库（references/labels/）：设施/locker 禁作聚类合并边（exclude≠删除——
    # 资金路径叙事保留，只是不并进实体）。自动决策只认目标链直接命中（resolver 纪律）。
    resv = None
    if LabelResolver is not None and "--no-labels" not in sys.argv:
        resv = LabelResolver(chain)
        if not resv.warn_if_degraded():     # 降级=显式 stderr 警告（"没命中"≠"没加载"，v4）
            print(f"批量标签库: {chain} 表 {len(resv.table)} 条已加载（--no-labels 可关闭）")
    elif LabelResolver is None:
        print("[labels][degraded_mode] labels_resolver 导入失败——本次运行无标签兜底", file=sys.stderr)
    excluded = {}   # 被拦截的设施地址 -> 标签信息（写入 clusters.json 供对账，不是从数据里删）

    def no_merge(a):
        if resv is None: return False
        if resv.no_merge(a):
            if a not in excluded:
                r = resv.get(a)
                excluded[a] = {"name": r["name"], "category": r["category"], "tier": r["tier"]}
            return True
        return False

    # --prep <dir>：读 cluster_prep_duck.py 的 DuckDB 缩图件（亿级样本必用——老路四容器
    # 内存不可行）；不带 --prep 走老路全量装载。两路语义等价（ASTEROID 沙盘 diff 验证）。
    prep_dir = None
    if "--prep" in sys.argv:
        i = sys.argv.index("--prep")
        prep_dir = (sys.argv[i + 1] if i + 1 < len(sys.argv)
                    and not sys.argv[i + 1].startswith("--")
                    else os.path.join(DIR, "data", "cluster_prep"))
    rows, profiles = None, None
    if prep_dir:
        import pyarrow.parquet as pq
        _ea = pq.read_table(os.path.join(prep_dir, "edges_agg.parquet"))
        edge = {(f, t): int(v) for f, t, v in zip(_ea.column("f").to_pylist(),
                                                  _ea.column("t").to_pylist(),
                                                  _ea.column("v").to_pylist())}
        _bt = pq.read_table(os.path.join(prep_dir, "bal.parquet"))
        bal = defaultdict(int, {a: int(b) for a, b in
                                zip(_bt.column("addr").to_pylist(), _bt.column("bal").to_pylist())})
        _pt = pq.read_table(os.path.join(prep_dir, "profile.parquet"))
        profiles = [dict(zip(_pt.column_names, r))
                    for r in zip(*(_pt.column(c).to_pylist() for c in _pt.column_names))]
        deg_n = {p["addr"]: int(p["peers"]) for p in profiles}
        print(f"[prep] DuckDB 缩图件：edges {len(edge):,} / addrs {len(deg_n):,}（{prep_dir}）")
    else:
        rows, seen = [], set()
        for p in glob.glob(os.path.join(DIR, f"{chain}_part_*.csv")):
            for line in open(p):
                parts = line.strip().split(",")
                if len(parts) == 6 and parts[0] != "block":
                    k = (parts[1], parts[2])
                    if k in seen: continue
                    seen.add(k)
                    rows.append((parts[3].lower(), parts[4].lower(), int(parts[5])))
        # edge 存原始 wei 整数累计（fail-closed 修复 2026-07-22）：修复前 v/DEC/1e6 浮点
        # 累计后与浮点阈值比较——违反 SKILL.md 阈值整数运算纪律，边界值判定受舍入影响。
        bal = defaultdict(int); edge = defaultdict(int); deg = defaultdict(set)
        for f, t, v in rows:
            if v == 0: continue   # zero-value transferFrom 投毒边不进账（与 prep 路同口径，v3.25）
            bal[f] -= v; bal[t] += v
            edge[(f, t)] += v
            deg[f].add(t); deg[t].add(f)
        deg_n = {a: len(s) for a, s in deg.items()}

    # v4.2 行为守门员：漏斗形状（多进多出+过手不留存）的地址一律禁作合并边——
    # 静态库兜"已知设施"，这里兜"没见过的"（新桥/新所钱包/新 bot 每天在增长，库永远追不全）。
    # 两案校准（bibi BSC + TRASH Robinhood）：47 个实体地址误伤 0；serial/team 白名单豁免。
    funnel_hits = {}
    if funnel_scan is not None and "--no-gatekeeper" not in sys.argv:
        exempt = set(TEAM)
        if resv is not None:
            exempt |= {a for a in deg_n if resv.is_serial(a)}
        funnel_hits = (scan_profiles(profiles, exempt=exempt) if profiles is not None
                       else funnel_scan(rows, exempt=exempt))
        n_strong = sum(1 for p in funnel_hits.values() if p["verdict"] == "FUNNEL")
        print(f"行为守门员: FUNNEL {n_strong} | CANDIDATE {len(funnel_hits) - n_strong}"
              f"（明细落 clusters.json gatekeeper_blocked；--no-gatekeeper 关闭）")

    def funnel_block(a):
        v = funnel_hits.get(a)
        return bool(v) and v["verdict"] == "FUNNEL"

    uf = UF()
    # 判定层一律整数交叉乘法（供给 wei 口径）：R1 边阈值默认 0.005%=1/20000；
    # 百倍换手老 meme 用 --r1-denom 2000（=0.05%）上调一档，见 playbook-entity-cluster-methods 阈值校准条
    r1_denom = 20000
    if "--r1-denom" in sys.argv:
        _i = sys.argv.index("--r1-denom")
        if _i + 1 < len(sys.argv):
            r1_denom = int(sys.argv[_i + 1])
    supply_raw = int(round(CFG.get("total_supply_m", 1000) * 1e6)) * DEC
    # R1
    for (f, t), m in edge.items():
        if m * r1_denom < supply_raw: continue
        if f in CEX or t in CEX or f == Z or t == Z or f in TEAM or t in TEAM: continue
        if no_merge(f) or no_merge(t): continue   # 标签库设施/locker 不作合并边
        if funnel_block(f) or funnel_block(t): continue   # 守门员：漏斗形状不作合并边（v4.2）
        if deg_n.get(f, 0) > 200 or deg_n.get(t, 0) > 200: continue
        uf.union(f, t)
    # R2
    gas_src = defaultdict(set)
    for fn in glob.glob(os.path.join(DIR, f"gmgn/{chain}_holders_*.json")):
        try: lst = json.load(open(fn)).get("list") or []
        except Exception: continue
        for h in lst:
            nf = (h.get("native_transfer") or {}).get("from_address")
            if nf and nf.lower() not in CEX and nf != Z and not no_merge(nf.lower()) \
                    and not funnel_block(nf.lower()):
                # 标签库/守门员命中的公共 funder（Relay solver/提款热钱包等）不作 gas 同源种子——历史假聚类头号来源
                gas_src[nf.lower()].add(h["address"].lower())
    for src, addrs in gas_src.items():
        addrs = {a for a in addrs if a not in CEX and a not in TEAM and deg_n.get(a, 0) <= 200
                 and not no_merge(a) and not funnel_block(a)}
        base = None
        for a in addrs:
            if base is None: base = a
            else: uf.union(base, a)
    # R3：金库一跳（单独标记）。从聚合边扫（条件只依赖 (f,t) 对，逐行=聚合等价；
    # 整数累计，展示层再除——两路共用，2026-07-22 与 --prep 一并统一）
    downstream = defaultdict(int)
    for (f, t), v in edge.items():
        if f in TEAM and t not in CEX and t not in TEAM and t != Z and deg_n.get(t, 0) <= 200:
            downstream[t] += v

    clusters = defaultdict(set)
    for a in list(uf.p):
        clusters[uf.find(a)].add(a)
    out = []
    for root, members in clusters.items():
        tot_raw = sum(bal.get(a, 0) for a in members)
        tot = tot_raw / DEC / 1e6
        # 集群准入 0.01%=1/10000（整数判定；tot 浮点仅展示）
        if tot_raw * 10000 < supply_raw and len(members) < 3: continue
        # addr 二级键保证确定性输出（并列余额时 set 迭代序不定，2026-07-22 修）
        mb = sorted(members, key=lambda a: (-bal.get(a, 0), a))
        out.append({"size": len(members), "total_M": round(tot, 3),
                    "pct_supply": round(tot / CFG.get("total_supply_m", 1000) * 100, 3),
                    "has_team_source": any(m in downstream for m in members),
                    "members": [{"addr": a, "bal_M": round(bal.get(a, 0)/DEC/1e6, 3)} for a in mb[:12]]})
    out.sort(key=lambda c: (-c["total_M"], -c["size"],
                            c["members"][0]["addr"] if c["members"] else ""))
    def _lbl(a):
        r = resv.get(a) if resv else None
        return r["name"] if (r and not r["cross_chain"]) else ""

    # 实战 miss 队列（v4）：疑似公共设施却未命中标签库的高权重地址，落盘供人工审核回填
    n_miss = 0
    if resv is not None and append_misses is not None:
        miss = []
        for a, pn in deg_n.items():
            if pn > 200 and resv.get(a) is None and a not in CEX and a != Z:
                miss.append((a, pn, f"高度数节点 deg={pn}（疑似路由/分发设施）"))
        for src, addrs in gas_src.items():
            if len(addrs) >= 3 and resv.get(src) is None and src not in TEAM:
                miss.append((src, len(addrs), f"共同 gas funder 服务 {len(addrs)} 地址（疑似热钱包/代付服务）"))
        # v4.2 守门员联动：行为判定 FUNNEL 且静态库无记录 → 最高优先级回填候选
        # （行为发现 → 人工确认 → 静态库成长，是库最健康的扩容闭环）
        for a, p in funnel_hits.items():
            if p["verdict"] == "FUNNEL" and resv.get(a) is None and a not in CEX:
                miss.append((a, p["tx_in"] + p["tx_out"],
                             f"守门员FUNNEL in{p['fan_in']}/out{p['fan_out']} ret={p['retention']:.3f}"
                             f"（漏斗形状，判明身份后回填标签库）"))
        token_tag = CFG.get("symbol") or os.path.basename(DIR)
        n_miss = append_misses(chain, miss, f"{token_tag} cluster")
        if n_miss:
            print(f"实战 miss 队列: 新记 {n_miss} 个未命中高权重地址（references/labels/miss-queue/{chain}.csv，人工审核后回填 manual 层）")

    json.dump({"clusters": out,
               "labels_meta": (resv.meta() if resv else {"degraded": True, "reason": "labels 未启用/导入失败"}),
               "miss_queue_new": n_miss,
               "gatekeeper_blocked": [{"addr": a, **{k: v for k, v in p.items()
                                                     if k in ("verdict", "fan_in", "fan_out", "tx_in", "tx_out",
                                                              "retention", "top_peer_share")}}
                                      for a, p in sorted(funnel_hits.items())],
               "label_excluded_nodes": [{"addr": a, **info} for a, info in sorted(excluded.items())],
               "team_downstream": [{"addr": a, "received_M": round(v/DEC/1e6, 3), "bal_M": round(bal.get(a, 0)/DEC/1e6, 3),
                                    "label": _lbl(a)}
                                   for a, v in sorted(downstream.items(), key=lambda x: -x[1])[:40]]},
              open(os.path.join(DIR, f"{chain}_clusters.json"), "w"), ensure_ascii=False, indent=1)
    print(f"clusters: {len(out)}")
    if excluded:
        print(f"批量标签库拦截 {len(excluded)} 个设施/托管地址不作合并边（明细在 clusters.json label_excluded_nodes）:")
        for a, info in list(sorted(excluded.items()))[:10]:
            print(f"  {a[:18]} {info['name'][:44]} <{info['category']}>")
    for c in out[:15]:
        heads = ", ".join(m["addr"] + f"({m['bal_M']}M)" for m in c["members"][:4])   # 结果行打全址（截断屏显=补全事故诱因）
        team = " [含金库下游]" if c["has_team_source"] else ""
        print(f"size={c['size']:<4} bal={c['total_M']:>9.3f}M ({c['pct_supply']:.2f}%){team}  {heads}")
    print(f"\n金库一跳接收者 top15（区分'官方控制'与'来源官方'！）:")
    for d in sorted(downstream.items(), key=lambda x: -x[1])[:15]:
        print(f"{d[0]}  收 {d[1]/DEC/1e6:.3f}M  现持 {bal.get(d[0],0)/DEC/1e6:.3f}M")

if __name__ == "__main__":
    main(sys.argv[1])
