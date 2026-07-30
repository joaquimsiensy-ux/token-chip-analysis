#!/usr/bin/env python3
"""聚类扰动敏感度测试（A4 2026-07-22）——阶段 4 复核材料，不进报告行内。

对已冻结的标签实体（analysis-state.json whale_groups：项目方/大庄/小庄/离场庄/刷量）重建其【机械证据图】
（R1 达标直转边 + R2 gas 同源边，口径与 cluster.py 一致），施加四类扰动，输出每个
实体的"脆弱性清单"：哪个扰动导致成员集合变化超阈值或判级翻转；全稳实体明写稳定。

四类扰动：
  ①单源边逐一移除    仅一种证据类型支撑的边（R1 无 gas 同源补充 / gas 组无 R1 补充）
  ②stale 设施标签放开  labels_resolver stale_hint（时效敏感类目>90天未核验）的 no_merge
                        拦截若失效，实体会经该设施吸入哪些外部地址（提示级模拟）
  ③判级门槛 ±10%      大庄=20%总供应、小庄=5%总供应或10%流通（可参数化）上下浮动重算判级
  ④桥接边逐一移除    证据图割边（Tarjan）移除后实体分裂的块与持仓占比

诚实边界（读报告前必知）：
  - 图内证据仅覆盖 R1/R2 机械证据；人工行为证据（同模板合约/时序协同/交棒单笔等）
    不在扰动范围——实体分裂≠结论错误，是"机械证据不足以独立支撑"的复核提示。
  - 成员中被机械规则拦截者（CEX/no_merge 设施/度>200 服务型）本就进不了机械图，
    单独列 mechanical_excluded——它们与实体的绑定完全依赖人工证据，天然是复核重点。
  - 未跑行为守门员（gatekeeper）；R2 未复算 funnel 拦截，与 cluster.py 有此差异。

用法（案目录含 analysis-state.json、data/key_edges.csv 或 <chain>_part_*.csv、gmgn/）：
  python3 cluster_sensitivity.py [--dir 案目录] [--edges 边表CSV] [--p0-pct 20]
      [--p1-pct 5] [--p1-circ-pct 10] [--jitter 0.10] [--r1-denom 20000]
      [--deg-max 200] [--split-frac 0.10] [--circulating-m N] [--no-labels]
产物：<dir>/sensitivity_report.json + sensitivity_report.md
"""
import argparse, datetime, glob, json, os, sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "labels"))
try:
    from labels_resolver import LabelResolver
except Exception:
    LabelResolver = None

ZERO = "0x" + "0" * 40
DEAD = "0x000000000000000000000000000000000000dead"


# ---------------- 输入装载 ----------------

def load_state(path):
    s = json.load(open(path))
    tok = s.get("token") or {}
    ents = []
    LABEL_PREFIX = ("项目方", "大庄", "小庄", "离场庄", "刷量")
    for g in s.get("whale_groups") or []:
        label = g.get("label") or ""
        legacy_tier = (g.get("tier") or "").upper()   # v5.0 前旧 state 兼容
        if not (label.startswith(LABEL_PREFIX) or label.startswith("狙击集团")
                or legacy_tier in ("P0", "P1")):
            continue
        members = []
        for a in g.get("addresses") or []:
            if isinstance(a, dict):
                a = a.get("address")
            a = (a or "").strip().lower()
            if a.startswith("0x") and len(a) == 42 and a not in (ZERO, DEAD):
                members.append(a)
        declared = next((p for p in LABEL_PREFIX if label.startswith(p)),
                        "狙击集团(legacy)" if label.startswith("狙击集团") else (legacy_tier or "?"))
        ents.append({"label": label or "?", "grade": declared,
                     "share_pct": g.get("current_share_pct"),
                     "members": sorted(set(members))})
    return tok, ents


def find_edges(case_dir, chain, cli):
    if cli:
        return sorted(glob.glob(cli)) or [cli]
    for cand in (os.path.join(case_dir, "data", "key_edges.csv"),
                 os.path.join(case_dir, "eth_transfers.csv")):
        if os.path.exists(cand):
            return [cand]
    parts = sorted(glob.glob(os.path.join(case_dir, f"{chain}_part_*.csv")))
    if parts:
        return parts
    sys.exit(f"找不到边表：--edges 指定，或案目录放 data/key_edges.csv / {chain}_part_*.csv")


def duck_aggregate(files, supply_raw, r1_denom, member_set):
    """DuckDB 一次过：达标聚合边 + 相关地址度数/余额。返回 (edges, deg, bal)。
    edges: {(f,t): sum_raw}（有向，达标口径 sum*r1_denom >= supply_raw）；
    成员间边即使不达标也带回（记 below_threshold，供报告披露，不作证据边）。"""
    import duckdb
    con = duckdb.connect()
    con.execute("SET threads TO 4")
    # value 强制 VARCHAR 再 CAST HUGEINT：嗅探对 1e24 级大整数会推断 DOUBLE（精度丢失）
    opts = "header=true, types={'value': 'VARCHAR'}"
    src = f"read_csv(?, {opts}, union_by_name=true)" if len(files) > 1 else f"read_csv(?, {opts})"
    files_arg = files if len(files) > 1 else files[0]
    con.execute(f"""
        CREATE TEMP TABLE agg AS
        SELECT lower("from") f, lower("to") t, SUM(CAST(value AS HUGEINT)) v
        FROM {src} GROUP BY 1, 2""", [files_arg])
    mem_list = list(member_set)
    con.execute("CREATE TEMP TABLE mem(a VARCHAR)")
    con.executemany("INSERT INTO mem VALUES (?)", [(a,) for a in mem_list])
    thr_edges = con.execute(
        "SELECT f, t, v FROM agg WHERE v * ? >= ? AND f <> t", [r1_denom, supply_raw]).fetchall()
    mem_edges = con.execute("""
        SELECT f, t, v FROM agg WHERE f <> t
          AND f IN (SELECT a FROM mem) AND t IN (SELECT a FROM mem)""").fetchall()
    edges = {(f, t): int(v) for f, t, v in thr_edges}
    member_edges = {(f, t): int(v) for f, t, v in mem_edges}
    rel = set(member_set) | {x for e in edges for x in e} | {ZERO, DEAD}
    con.execute("CREATE TEMP TABLE rel(a VARCHAR)")
    con.executemany("INSERT INTO rel VALUES (?)", [(a,) for a in sorted(rel)])
    deg = dict(con.execute("""
        SELECT addr, COUNT(DISTINCT peer) FROM (
          SELECT f addr, t peer FROM agg UNION ALL SELECT t, f FROM agg)
        WHERE addr IN (SELECT a FROM rel) GROUP BY addr""").fetchall())
    bal = dict(con.execute("""
        SELECT addr, SUM(d) FROM (
          SELECT f addr, -v d FROM agg UNION ALL SELECT t, v FROM agg)
        WHERE addr IN (SELECT a FROM rel) GROUP BY addr""").fetchall())
    n_agg = con.execute("SELECT COUNT(*) FROM agg").fetchone()[0]
    con.close()
    return edges, member_edges, {k: int(v) for k, v in deg.items()}, \
        {k: int(v) for k, v in bal.items()}, n_agg


def load_balances(case_dir):
    """终态余额快照（可靠源）：data/balances_final.json（addr→raw str）或
    balances_latest.json（{last_block, balances}）。缺则返回 None（退化用边表重放，
    对'关键边抽取集'边表重放净额不可靠——抽取集对非 keyset 地址的边不完整）。"""
    p1 = os.path.join(case_dir, "data", "balances_final.json")
    p2 = os.path.join(case_dir, "data", "balances_latest.json")
    if os.path.exists(p1):
        d = json.load(open(p1))
        return {k.lower(): int(v) for k, v in d.items()}, "data/balances_final.json"
    if os.path.exists(p2):
        d = json.load(open(p2))
        b = d.get("balances") or {}
        if b:
            return {k.lower(): int(v) for k, v in b.items()}, "data/balances_latest.json"
    return None, None


def load_gas_sources(case_dir, chain, cex, resv):
    """gmgn/<chain>_holders_*.json → funder -> {addr}（口径同 cluster.py R2）。"""
    gas = defaultdict(set)
    for fn in glob.glob(os.path.join(case_dir, "gmgn", f"{chain}_holders_*.json")):
        try:
            lst = json.load(open(fn)).get("list") or []
        except Exception:
            continue
        for h in lst:
            nf = ((h.get("native_transfer") or {}).get("from_address") or "").lower()
            if nf and nf != ZERO and nf not in cex and not (resv and resv.no_merge(nf)):
                gas[nf].add((h.get("address") or "").lower())
    return gas


# ---------------- 图算法 ----------------

def components(nodes, adj):
    seen, comps = set(), []
    for n in nodes:
        if n in seen:
            continue
        stack, comp = [n], set()
        seen.add(n)
        while stack:
            x = stack.pop()
            comp.add(x)
            for y in adj.get(x, ()):
                if y not in seen:
                    seen.add(y)
                    stack.append(y)
        comps.append(comp)
    return comps


def bridges(nodes, adj):
    """Tarjan 割边（迭代版）。返回 {(u,v)}（u<v 排序）。"""
    disc, low, out = {}, {}, set()
    timer = [0]
    for root in nodes:
        if root in disc:
            continue
        stack = [(root, None, iter(adj.get(root, ())))]
        disc[root] = low[root] = timer[0]; timer[0] += 1
        while stack:
            u, parent, it = stack[-1]
            advanced = False
            for v in it:
                if v not in disc:
                    disc[v] = low[v] = timer[0]; timer[0] += 1
                    stack.append((v, u, iter(adj.get(v, ()))))
                    advanced = True
                    break
                elif v != parent:
                    low[u] = min(low[u], disc[v])
            if not advanced:
                stack.pop()
                if parent is not None:
                    low[parent] = min(low[parent], low[u])
                    if low[u] > disc[parent]:
                        out.add(tuple(sorted((parent, u))))
    return out


def split_stats(comps, main_set, bal, ent_bal_raw):
    """扰动后基线主分量 main_set 是否分裂：分裂时返回除最大持仓块外的脱落块列表。"""
    pieces = []
    for c in comps:
        real = {m for m in c if not m.startswith("GAS:")} & main_set
        if real:
            pieces.append(real)
    if len(pieces) <= 1:
        return []
    pieces.sort(key=lambda p: sum(max(bal.get(m, 0), 0) for m in p), reverse=True)
    drops = []
    for p in pieces[1:]:
        b = sum(max(bal.get(m, 0), 0) for m in p)
        drops.append({"members": sorted(p)[:8], "n": len(p),
                      "bal_frac_of_entity": round(b / ent_bal_raw, 4) if ent_bal_raw else 0.0})
    return drops


# ---------------- 主流程 ----------------

def grade(share_supply, share_circ, big, small, small_c):
    """按当前占比重算判级（v5.0 标签制：大庄/小庄/未达标；离场庄按峰值另判不在此列）。"""
    if share_supply is None:
        return "?"
    if share_supply >= big:
        return "大庄"
    if share_supply >= small or (share_circ is not None and share_circ >= small_c):
        return "小庄"
    return "未达标"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=os.getcwd(), help="案目录（默认 cwd）")
    ap.add_argument("--state", default=None, help="analysis-state.json 路径")
    ap.add_argument("--edges", default=None, help="边表 CSV（可 glob；默认自动发现）")
    ap.add_argument("--chain", default=None)
    ap.add_argument("--big-pct", dest="p0_pct", type=float, default=20.0, help="大庄门槛：%%总供应（默认20）")
    ap.add_argument("--small-pct", dest="p1_pct", type=float, default=5.0, help="小庄门槛：%%总供应（默认5）")
    ap.add_argument("--small-circ-pct", dest="p1_circ_pct", type=float, default=10.0, help="小庄门槛：%%流通（默认10）")
    ap.add_argument("--jitter", type=float, default=0.10, help="门槛扰动幅度（默认±10%%）")
    ap.add_argument("--r1-denom", type=int, default=20000, help="R1 边阈值=供给/denom（默认20000=0.005%%）")
    ap.add_argument("--deg-max", type=int, default=200, help="服务型地址度数拦截（默认200）")
    ap.add_argument("--split-frac", type=float, default=0.10,
                    help="脱落块持仓占实体比例超此值记敏感（默认0.10）")
    ap.add_argument("--circulating-m", type=float, default=None,
                    help="流通量（百万枚；默认=总供应-0xdead 余额）")
    ap.add_argument("--no-labels", action="store_true")
    ap.add_argument("--out", default=None, help="输出前缀（默认 <dir>/sensitivity_report）")
    args = ap.parse_args()

    case_dir = os.path.abspath(args.dir)
    state_p = args.state or os.path.join(case_dir, "analysis-state.json")
    tok, ents = load_state(state_p)
    if not ents:
        sys.exit("analysis-state.json 无标签实体（whale_groups label 过滤后为空）")
    chain = args.chain or {"bnb": "bsc", "binance": "bsc", "ethereum": "eth",
                           "solana": "sol"}.get((tok.get("chain") or "").lower(),
                                                (tok.get("chain") or "bsc").lower())
    dec = 10 ** int(tok.get("decimals", 18))
    supply_tokens = float(str(tok.get("total_supply", "0")).replace(",", "") or 0)
    if not supply_tokens:
        sys.exit("token.total_supply 缺失")
    supply_raw = int(supply_tokens) * dec

    cfg_p = os.path.join(case_dir, "config.json")
    cfg = json.load(open(cfg_p)) if os.path.exists(cfg_p) else {}
    cex = {a.lower() for a, v in (cfg.get("cex_wallets") or {}).items() if a.startswith("0x")}
    cex |= {a.lower() for a, v in (cfg.get("known_infra") or {}).items()
            if a.startswith("0x") and str(v).lower().startswith("cex")}

    resv = None
    if LabelResolver is not None and not args.no_labels:
        resv = LabelResolver(chain)
        resv.warn_if_degraded()

    all_members = set()
    for e in ents:
        all_members |= set(e["members"])

    files = find_edges(case_dir, chain, args.edges)
    print(f"边表: {len(files)} 文件 | 实体 {len(ents)} 个 | 成员并集 {len(all_members)}")
    edges, member_edges, deg, bal, n_agg = duck_aggregate(files, supply_raw, args.r1_denom, all_members)
    print(f"聚合边 {n_agg:,} → 达标边(≥供给/{args.r1_denom}) {len(edges):,} | 成员间聚合边 {len(member_edges):,}")

    snap, bal_src = load_balances(case_dir)
    if snap is not None:
        bal = snap   # 快照优先：边表若是"关键边抽取集"，重放净额对部分地址会严重虚高
        print(f"余额源: {bal_src}（{len(bal):,} 址快照）")
    else:
        bal_src = "edge-replay（⚠️ 抽取集边表下净额不可靠，仅作相对参考）"
        print(f"余额源: {bal_src}")

    gas = load_gas_sources(case_dir, chain, cex, resv)
    print(f"gas 同源组（gmgn native_transfer）: {len(gas)} 个 funder")

    # 无向达标边视图 + 标签/度数拦截判定
    und = defaultdict(int)
    for (f, t), v in edges.items():
        und[tuple(sorted((f, t)))] += v

    def mech_block(a):
        """机械聚类规则下不可作合并边端点的原因；None=可作。"""
        if a in cex:
            return "config CEX"
        if resv is not None and resv.no_merge(a):
            r = resv.get(a)
            return f"标签库 no_merge:{r['name'][:30]}<{r['category']}>"
        if deg.get(a, 0) > args.deg_max:
            return f"度数 {deg.get(a, 0)}>{args.deg_max}(服务型)"
        return None

    # 流通量（小庄流通口径）
    circ_raw = (int(args.circulating_m * 1e6) * dec if args.circulating_m
                else supply_raw - max(bal.get(DEAD, 0), 0))

    today = datetime.date.today().isoformat()
    report = {"generated": today, "case_dir": case_dir, "chain": chain,
              "symbol": tok.get("symbol"),
              "params": {"big_pct": args.p0_pct, "small_pct": args.p1_pct,
                         "small_circ_pct": args.p1_circ_pct, "jitter": args.jitter,
                         "r1_denom": args.r1_denom, "deg_max": args.deg_max,
                         "split_frac": args.split_frac},
              "inputs": {"edge_files": files, "agg_pairs": n_agg,
                         "threshold_edges": len(edges), "gas_funders": len(gas),
                         "balance_source": bal_src,
                         "labels_meta": (resv.meta() if resv else {"degraded": True}),
                         "circulating_raw_est": str(circ_raw)},
              "positioning": "阶段4复核材料——不进报告行内，不引入任何行内置信度标签",
              "entities": []}

    for ent in ents:
        M = set(ent["members"])
        notes = []
        if not M:
            notes.append("state 中该实体 addresses 为占位/外部引用（如'(见data/xxx.json)'），"
                         "无可扰动成员——群体型实体（行为群体名单等）不适用图扰动")
        exc = {m: mech_block(m) for m in M}
        ok_nodes = {m for m in M if exc[m] is None}
        excluded = {m: r for m, r in exc.items() if r}

        # R1 证据边（无向、达标、两端可并）
        r1 = {}
        for (u, v), s in und.items():
            if u in ok_nodes and v in ok_nodes:
                r1[(u, v)] = s
        # R2 gas 组（组内本实体成员 ≥2）
        gas_groups = {}
        for src, addrs in gas.items():
            grp = {a for a in addrs if a in ok_nodes}
            if len(grp) >= 2:
                gas_groups[src] = grp

        # 证据图（gas 星型虚拟节点）
        adj = defaultdict(set)
        nodes = set(M)
        for (u, v) in r1:
            adj[u].add(v); adj[v].add(u)
        for src, grp in gas_groups.items():
            g = f"GAS:{src}"
            nodes.add(g)
            for a in grp:
                adj[g].add(a); adj[a].add(g)

        comps0 = components(nodes, adj)
        real_comps0 = [sorted(m for m in c if not m.startswith("GAS:")) for c in comps0]
        real_comps0 = [c for c in real_comps0 if c]
        main_comp = max(real_comps0, key=lambda c: sum(max(bal.get(m, 0), 0) for m in c)) \
            if real_comps0 else []
        main_set = set(main_comp)
        isolated = sorted(m for m in M
                          if m not in main_set and not adj.get(m) and m not in excluded)
        ent_bal_raw = sum(max(bal.get(m, 0), 0) for m in M) or 1
        replay_share = sum(max(bal.get(m, 0), 0) for m in M) / supply_raw * 100

        findings = []

        # ---- ①单源边逐一移除 ----
        def covered_by_gas(u, v):
            return any(u in grp and v in grp for grp in gas_groups.values())

        reported_edges = set()
        single_r1 = [(u, v) for (u, v) in r1 if not covered_by_gas(u, v)]
        for (u, v) in single_r1:
            adj2 = {k: set(s) for k, s in adj.items()}
            adj2[u].discard(v); adj2[v].discard(u)
            comps = components(nodes, adj2)
            drops = split_stats(comps, main_set, bal, ent_bal_raw)
            bad = [d for d in drops if d["bal_frac_of_entity"] >= args.split_frac or d["n"] >= 3]
            if bad:
                reported_edges.add((u, v))
                findings.append({"perturbation": "①单源边移除", "edge": [u, v],
                                 "edge_type": "R1-only（无 gas 同源补充）",
                                 "sum_tokens_M": round(r1[(u, v)] / dec / 1e6, 3),
                                 "split_off": bad})
        for src, grp in gas_groups.items():
            # 整组 gas 证据移除（该 funder 数据不可靠时）——组对之间无 R1 补充才可能分裂
            adj2 = {k: set(s) for k, s in adj.items()}
            g = f"GAS:{src}"
            for a in list(adj2.get(g, ())):
                adj2[a].discard(g)
            adj2.pop(g, None)
            comps = components(nodes - {g}, adj2)
            drops = split_stats(comps, main_set, bal, ent_bal_raw)
            bad = [d for d in drops if d["bal_frac_of_entity"] >= args.split_frac or d["n"] >= 3]
            if bad:
                findings.append({"perturbation": "①单源证据组移除", "gas_funder": src,
                                 "group_size": len(grp), "split_off": bad})

        # ---- ②stale 设施标签放开（提示级模拟） ----
        stale_hits = []
        if resv is not None:
            neigh_infra = set()
            for (f, t) in edges:
                if f in M and t not in M:
                    neigh_infra.add(t)
                elif t in M and f not in M:
                    neigh_infra.add(f)
            for x in sorted(neigh_infra):
                r = resv.get(x)
                if not r or r["cross_chain"] or r["merge_policy"] != "no_merge":
                    continue
                if not r.get("stale_hint"):
                    continue
                if deg.get(x, 0) > args.deg_max:
                    stale_hits.append({"infra": x, "name": r["name"][:40],
                                       "stale_days": r["stale_days"],
                                       "effect": f"标签放开也被度数拦截(deg={deg.get(x,0)})——实体稳定"})
                    continue
                # 放开该设施：它与成员/外部的达标边全部可并 → 会拉进哪些外部地址
                pulled = {f for (f, t) in edges if t == x} | {t for (f, t) in edges if f == x}
                pulled = {p for p in pulled if p not in M and p not in (ZERO, DEAD)
                          and mech_block(p) is None}
                stale_hits.append({"infra": x, "name": r["name"][:40],
                                   "stale_days": r["stale_days"], "pulled_n": len(pulled),
                                   "effect": f"若标签失效将经此吸入 {len(pulled)} 个外部地址",
                                   "pulled_sample": sorted(pulled)[:6]})
            for s in stale_hits:
                if s.get("pulled_n", 0) > 0:
                    findings.append({"perturbation": "②stale 设施标签", **s})

        # ---- ③门槛 ±10% 判级 ----
        share = ent.get("share_pct")
        share_circ = (share * supply_raw / circ_raw) if (share is not None and circ_raw) else None
        j = args.jitter
        g_lo = grade(share, share_circ, args.p0_pct * (1 - j), args.p1_pct * (1 - j),
                     args.p1_circ_pct * (1 - j))
        g_base = grade(share, share_circ, args.p0_pct, args.p1_pct, args.p1_circ_pct)
        g_hi = grade(share, share_circ, args.p0_pct * (1 + j), args.p1_pct * (1 + j),
                     args.p1_circ_pct * (1 + j))
        grades = {"threshold_-10%": g_lo, "base": g_base, "threshold_+10%": g_hi}
        if g_base != ent["grade"]:
            notes.append(f"按当前占比 {share}% 的基线判级为「{g_base}」≠ 申报标签 {ent['grade']}"
                         f"——常见于离场庄/项目方（标签按峰值或身份而非当前占比）或口径差异，复核时核对口径")
        if len({g_lo, g_base, g_hi}) > 1:
            findings.append({"perturbation": "③门槛±10%", "share_pct": share,
                             "share_circ_pct": round(share_circ, 3) if share_circ else None,
                             "grades": grades,
                             "note": "判级贴线——门槛浮动即翻转，复核时以证据强度而非占比数字定级"})

        # ---- ④桥接边逐一移除（跳过①已报的同边——①是证据源视角、④是图论视角，重叠时只记一次） ----
        br = bridges(nodes, adj)
        br = {e for e in br if e not in reported_edges}
        for (u, v) in sorted(br):
            adj2 = {k: set(s) for k, s in adj.items()}
            adj2[u].discard(v); adj2[v].discard(u)
            comps = components(nodes, adj2)
            drops = split_stats(comps, main_set, bal, ent_bal_raw)
            bad = [d for d in drops if d["bal_frac_of_entity"] >= args.split_frac or d["n"] >= 3]
            if bad:
                findings.append({"perturbation": "④桥接边移除",
                                 "edge": [u, v],
                                 "edge_kind": "gas星型" if (u.startswith("GAS:") or v.startswith("GAS:")) else "R1",
                                 "split_off": bad})

        stable = not findings
        if not r1 and not gas_groups:
            verdict = ("NO-MECH-EVIDENCE（无机械证据可扰动——实体归属完全依赖人工证据，"
                       "本测试无法为其提供稳健性背书）")
            if findings:
                verdict += f"；另有 {len(findings)} 项非图扰动敏感（见清单）"
        elif stable:
            verdict = "STABLE（四类扰动下稳定）"
        else:
            verdict = f"FRAGILE（{len(findings)} 项敏感）"
        report["entities"].append({
            "label": ent["label"], "grade": ent["grade"], "declared_share_pct": share,
            "replay_share_pct": round(replay_share, 3),
            "members_total": len(M),
            "mechanical_graph": {
                "mergeable_nodes": len(ok_nodes), "r1_edges": len(r1),
                "gas_groups": len(gas_groups),
                "main_component_size": len(main_comp),
                "isolated_members": len(isolated),
                "isolated_sample": isolated[:10],
                "mechanical_excluded": [{"addr": a, "reason": r}
                                        for a, r in sorted(excluded.items())][:40],
            },
            "member_edges_below_threshold": sum(
                1 for (f, t), v in member_edges.items()
                if f in M and t in M and v * args.r1_denom < supply_raw),
            "grades_under_jitter": grades,
            "notes": notes,
            "findings": findings,
            "verdict": verdict,
        })

    out_prefix = args.out or os.path.join(case_dir, "sensitivity_report")
    json.dump(report, open(out_prefix + ".json", "w"), ensure_ascii=False, indent=1)

    # ---- Markdown ----
    L = [f"# 聚类扰动敏感度报告 · {tok.get('symbol')} ({chain})  {today}",
         "",
         f"定位：**阶段 4 复核材料**（不进报告行内，无行内置信度标签）。机械证据=R1 达标直转"
         f"（≥供给/{args.r1_denom}）+R2 gas 同源；人工行为证据不在扰动范围——分裂≠结论错误，"
         f"是「机械证据不足以独立支撑」的定向复核提示。",
         "",
         f"输入：聚合边 {n_agg:,} / 达标边 {len(edges):,} / gas funder {len(gas)} / "
         f"标签表 {report['inputs']['labels_meta'].get('table_rows', 0)} 行", ""]
    for e in report["entities"]:
        mg = e["mechanical_graph"]
        L += [f"## {e['label']}  [{e['grade']}]  申报 {e['declared_share_pct']}% / 重放合计 {e['replay_share_pct']}%",
              f"- 基线机械图：成员 {e['members_total']}（可并 {mg['mergeable_nodes']}，"
              f"机械拦截 {len(mg['mechanical_excluded'])}，孤立 {mg['isolated_members']}）| "
              f"R1 边 {mg['r1_edges']} | gas 组 {mg['gas_groups']} | 主分量 {mg['main_component_size']} 成员"]
        if mg["mechanical_excluded"]:
            L.append(f"- 机械拦截成员（与实体绑定完全依赖人工证据，复核重点）：")
            for x in mg["mechanical_excluded"][:8]:
                L.append(f"    - `{x['addr']}` {x['reason']}")
            if len(mg["mechanical_excluded"]) > 8:
                L.append(f"    - …共 {len(mg['mechanical_excluded'])} 个（详见 JSON）")
        if mg["isolated_members"]:
            L.append(f"- 机械孤立成员 {mg['isolated_members']} 个（无任何 R1/R2 边，示例 "
                     f"{', '.join('`'+a+'`' for a in mg['isolated_sample'][:4])}）")
        L.append(f"- 门槛±10% 判级：{e['grades_under_jitter']['threshold_-10%']} / "
                 f"{e['grades_under_jitter']['base']} / {e['grades_under_jitter']['threshold_+10%']}"
                 f"（门槛-10% / 基线 / +10%）")
        for n in e.get("notes", []):
            L.append(f"- 注：{n}")
        if e["findings"]:
            L.append(f"- **脆弱性清单（{len(e['findings'])} 项）**：")
            for f_ in e["findings"]:
                head = f_["perturbation"]
                if "edge" in f_:
                    head += f" `{f_['edge'][0]}—{f_['edge'][1]}`"
                if "gas_funder" in f_:
                    head += f" funder=`{f_['gas_funder']}`(组{f_['group_size']})"
                if "infra" in f_:
                    head += f" `{f_['infra']}` {f_['name']} stale={f_['stale_days']}d"
                L.append(f"    - {head}")
                for d in f_.get("split_off", [])[:3]:
                    L.append(f"        - 脱落 {d['n']} 成员 / 实体持仓 {d['bal_frac_of_entity']*100:.1f}%："
                             f"{', '.join('`'+m+'`' for m in d['members'][:3])}")
                if "effect" in f_:
                    L.append(f"        - {f_['effect']}")
                if "grades" in f_:
                    L.append(f"        - {f_['grades']}")
        L.append(f"- **裁定：{e['verdict']}**")
        L.append("")
    L += ["---", "复核动作建议：FRAGILE 项逐条走对抗复核（该边/该标签若不成立，实体叙事还立得住吗）；"
          "机械拦截/孤立成员核对人工证据留痕是否已在报告成员表注明。"]
    open(out_prefix + ".md", "w").write("\n".join(L))
    print(f"\n产物: {out_prefix}.json / .md")
    for e in report["entities"]:
        print(f"  {e['grade']} {e['label'][:40]}: {e['verdict']}")


if __name__ == "__main__":
    main()
