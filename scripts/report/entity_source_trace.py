#!/usr/bin/env python3
"""entity_source_trace.py — 已知实体币源溯源闸（provenance-ledger/v2，v6.8.1）。

背景：W1 波次二次漏检复盘第一道防线——PYTHIA 案 Q1 的 20 个直接上家里 9 个是 W1、
3yMk 的 11 个上家里 10 个是 W1，19 根藤裸露在进货单上却因"找到并入证据就收工"的溯源
习惯无人彻查。本闸把"每个已知实体的币从哪来"变成机器义务：溯源到可证来源/边界终点
为止，未决量显式记账，不许静默收工。

v2 算法（2026-08-01 codex 验收 P0-1 翻案后重写）：
  v1 的"截至 T 全部历史流入按金额归一化"数学错误——比例守恒只在单次流出瞬间成立，
  流入流出交错时老来源被消耗的份额不会自动缩水（反例：先收 A 100 → 转出 90 → 再收
  B 90，真实库存 A 10%/B 90%，v1 算成 A 52.6%/B 47.4%）。
  v2 改为**祖先子图正向模拟**：
    1. 逆向 BFS：从实体成员出发沿入边收集全部上游节点，遇终点（mint/标签确证/设施
       启发式）停止展开；深度（距实体最短跳数）超 --depth-limit 或节点数超
       --node-budget 的节点记截断终点。
    2. 正向重演：子图内全部 ≤T 转账按 (ts, 同秒组内拓扑序) 逐笔处理。每个节点维护
       "来源构成账户"：流入按发送方账户当时构成转移入账（发送方是终点则记终点构成），
       流出等比扣减；实体成员集收缩为单一超级账户（内部互转不记账）。
    3. 锚点读数：处理完 ≤T 边后超级账户的向量＝库存终点构成；direct_upstream 进货单
       另以**毛流入事实清单**口径单列（≤T 全史直接上家聚合，零分摊、不随流出扣减——
       周转枢纽的现存库存构成会把早期藤蔓等比消耗殆尽，PYTHIA 实测 Q1 峰值现存构成
       EwUU 100%、W1 藤全部衰减不可见；而 W1 教训的本义是"从谁进过货"这个事实本身）。
  正向模拟下总量守恒是构造保证（每笔进出都过账），closure_check 降级为实现自检；
  回环（含跨时回环）天然良定义（构成随币流动，无需 SCC 概念——v1 的 same_slot_scc
  终点类别废除）。同一 UTC 秒内多笔边先按组内拓扑排序（场内路由 A→B→C 常同秒），
  有环组按 (f,t,amt) 字典序兜底并计入 simulation.same_ts_cycle_groups 诚实标注——
  同秒真序不可知属数据粒度限制。

FIFO/LIFO 上下界（P0-5）：同一模拟骨架换消耗策略——pro_rata（主法，等比扣减）/
fifo（先进先出，老币先耗）/lifo（后进先出，新币先耗）三遍模拟。任一 stock>0 锚点的
第一大终点构成条目在三策略间不一致 → conservative_vs_aggressive_verdict_stable=false
→ **exit 2 阻断**（报告仍落盘供诊断；freeze 端独立复查此字段，双重防线）。

终点分类（BFS 停止点）：
  PROVEN_ORIGIN：mint哨兵 / labels 确证 launch_alloc·airdrop·vesting
  BOUNDARY：labels 确证 DEX 池·CEX·设施·桥（evidence=label_confirmed）
    ——"DEX 池流出"只能记 dex_pool 边界，不得写成"swap 买入"（无对价腿数据）
  UNRESOLVED：facility_candidate（启发式：全局对手方双向 ≥阈值——标签库未确证前只记候选）/
    depth_limit / budget_truncated（BFS 预算截断）/ data_gap（账户被取用时库存不足＝
    上游数据缺失，短缺部分显式入账）

硬规则（复核翻案教训）：
  - 支路级停止：设施来的支路停，同一钱包其他支路必须继续穿透
    （3yMk 教训：EwUU8oi 来的 8.77% 停、10 条 W1 支路继续）——BFS 终点判定天然逐节点独立。
  - 黑箱不得翻译成"用户买入/提币"；清零地址来源必须穿透（peak 锚点对零现仓实体仍有意义）。

输入：--entity-file {entity_id:[addr…]}（强制 {str: 非空 str 数组}，成员跨实体重复即拒）；
--labels-file 可选 {addr:{"kind":"cex|dex_pool|facility|bridge|launch_alloc|airdrop|vesting",…}}；
边表三通道同 wave_scan（--edges-sol/--edges-evm-v2/--duckdb）。
输出：--out provenance_ledger.json。实体条目含 members_sha256（成员集规范化哈希，
freeze 端与 --entity-file 逐实体绑定比对——台账不得复用于改过名册的冻结）。

退出码：0=溯源完成且闭合且敏感性稳定；2=数据/参数错误、闭合自检失败或敏感性翻转
（fail-closed）；1=脚本自身错误。

回测基线（装闸必附原案回测；fixtures/pythia_anchors.json，v2 重算后数字以新实测为准）：
  - Q1 峰值锚点 direct_upstream 中 ≥9 个 W1 名单地址现形；
  - 3yMk：EwUU8oi 设施支路停（facility_candidate/confirmed）而 W1 支路穿透（path_len ≥2）。
"""
import argparse
import hashlib
import json
import os
import sys
from collections import deque
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wave_scan import Z, DEAD, load_sol, load_evm_v2, attach_duckdb, day_str  # noqa: E402

SCHEMA = "provenance-ledger/v2"
POLICIES = ("pro_rata", "fifo", "lifo")
LABEL_KIND_MAP = {
    "cex": ("BOUNDARY", "cex_confirmed"), "dex_pool": ("BOUNDARY", "dex_pool"),
    "facility": ("BOUNDARY", "facility_confirmed"), "bridge": ("BOUNDARY", "bridge"),
    "launch_alloc": ("PROVEN_ORIGIN", "launch_alloc"), "airdrop": ("PROVEN_ORIGIN", "proven_airdrop"),
    "vesting": ("PROVEN_ORIGIN", "proven_vesting"),
}
ENTITY_NODE = "@ENTITY"
EPS = 1e-6


def log(msg):
    print(f"[source_trace] {msg}", flush=True)


def members_sha256(addrs):
    return hashlib.sha256(",".join(sorted(addrs)).encode()).hexdigest()


def load_entity_map(path):
    """强制 {str: 非空 str 数组}；成员去重后跨实体重复即拒（P2-3 类型硬检查）。"""
    with open(path, encoding="utf-8") as fh:
        obj = json.load(fh)
    if not isinstance(obj, dict) or not obj:
        log("参数错误：--entity-file 需为非空 {entity_id:[addr…]}")
        sys.exit(2)
    out, seen = {}, {}
    for eid, addrs in obj.items():
        if not isinstance(eid, str) or not eid:
            log(f"参数错误：--entity-file 实体 ID 必须是非空字符串: {eid!r}")
            sys.exit(2)
        if (not isinstance(addrs, list) or not addrs
                or not all(isinstance(x, str) and x for x in addrs)):
            log(f"参数错误：--entity-file 实体 {eid} 成员必须是非空字符串数组（收到 {type(addrs).__name__}）")
            sys.exit(2)
        uniq = sorted(set(addrs))
        if len(uniq) != len(addrs):
            log(f"参数错误：--entity-file 实体 {eid} 含重复成员")
            sys.exit(2)
        for x in uniq:
            if x in seen:
                log(f"参数错误：地址 {x} 同时属于实体 {seen[x]} 与 {eid}——先并册再溯源")
                sys.exit(2)
            seen[x] = eid
        out[eid] = uniq
    return out


def load_labels(path):
    with open(path, encoding="utf-8") as fh:
        obj = json.load(fh)
    if not isinstance(obj, dict):
        log("参数错误：--labels-file 需为 {addr:{kind,…}}")
        sys.exit(2)
    labels = {}
    for addr, meta in obj.items():
        if not isinstance(meta, dict):
            log(f"参数错误：--labels-file 条目 {addr} 值必须是对象（收到 {type(meta).__name__}）")
            sys.exit(2)
        kind = meta.get("kind")
        if kind in LABEL_KIND_MAP:
            labels[addr] = meta
        elif kind is not None:
            log(f"  ⚠ 标签 {addr} kind={kind!r} 不在已知集合，忽略（不作终点）")
    return labels


# ---------------- 账户：三种消耗策略同接口 ----------------

class VectorAccount:
    """pro-rata：单向量，流出等比扣减。"""
    __slots__ = ("vec",)

    def __init__(self):
        self.vec = {}

    def add(self, comp):
        for k, v in comp.items():
            if v > 0:
                self.vec[k] = self.vec.get(k, 0.0) + v

    def take(self, amt):
        avail = sum(self.vec.values())
        if avail <= EPS:
            self.vec.clear()
            return {}, amt
        if amt >= avail - EPS:
            comp = dict(self.vec)
            self.vec.clear()
            return comp, max(0.0, amt - avail)
        r = amt / avail
        comp = {}
        for k in list(self.vec):
            part = self.vec[k] * r
            comp[k] = part
            self.vec[k] -= part
        return comp, 0.0

    def total(self):
        return sum(self.vec.values())

    def snapshot(self):
        return dict(self.vec)


class LayeredAccount:
    """FIFO/LIFO：分层账户，每层 (金额, 归一化构成)；流出按端序消耗。"""
    __slots__ = ("layers", "lifo")

    def __init__(self, lifo):
        self.layers = deque()
        self.lifo = lifo

    def add(self, comp):
        s = sum(v for v in comp.values() if v > 0)
        if s <= EPS:
            return
        self.layers.append((s, {k: v / s for k, v in comp.items() if v > 0}))

    def take(self, amt):
        comp, need = {}, amt
        while need > EPS and self.layers:
            la, lu = self.layers[-1] if self.lifo else self.layers[0]
            use = min(la, need)
            for k, f in lu.items():
                comp[k] = comp.get(k, 0.0) + use * f
            if use >= la - EPS:
                self.layers.pop() if self.lifo else self.layers.popleft()
            else:
                nl = (la - use, lu)
                if self.lifo:
                    self.layers[-1] = nl
                else:
                    self.layers[0] = nl
            need -= use
        return comp, max(0.0, need)

    def total(self):
        return sum(la for la, _ in self.layers)

    def snapshot(self):
        out = {}
        for la, lu in self.layers:
            for k, f in lu.items():
                out[k] = out.get(k, 0.0) + la * f
        return out


def make_account(policy):
    if policy == "pro_rata":
        return VectorAccount()
    return LayeredAccount(lifo=(policy == "lifo"))


# ---------------- 终点判定 ----------------

class Classifier:
    def __init__(self, con, labels, facility_min_degree):
        self.labels = labels
        log("物化全局出入度（设施启发式）…")
        self.degree = {r[0]: (int(r[1]), int(r[2])) for r in con.execute(f"""
            SELECT owner, MAX(od) AS od, MAX(ind) AS ind FROM (
                SELECT f AS owner, COUNT(DISTINCT t) AS od, 0 AS ind FROM edges
                WHERE t NOT IN ('{Z}', '{DEAD}') GROUP BY f
                UNION ALL
                SELECT t AS owner, 0, COUNT(DISTINCT f) FROM edges
                WHERE f <> '{Z}' GROUP BY t
            ) GROUP BY owner""").fetchall()}
        self.facility_min_degree = facility_min_degree

    def classify(self, addr):
        """BFS 终点判定：mint → 标签 → 设施启发式；非终点返回 None。"""
        if addr == Z:
            return ("PROVEN_ORIGIN", "mint", Z)
        lb = self.labels.get(addr)
        if lb:
            kind = LABEL_KIND_MAP.get(lb.get("kind"))
            if kind:
                return (kind[0], kind[1], addr)
        od, ind = self.degree.get(addr, (0, 0))
        if od >= self.facility_min_degree and ind >= self.facility_min_degree:
            return ("UNRESOLVED", "facility_candidate", addr)
        return None


# ---------------- 逆向 BFS：祖先子图 ----------------

def build_ancestors(con, members, T, classifier, depth_limit, node_budget):
    """从实体成员逆向沿 ≤T 入边扩张。返回
    (ancestors, term_key{addr:(kind,sub,via)}, term_plen{addr:int}, n_depth_cut, n_budget_cut)。
    终点/截断节点不展开——设施支路在此停、其他支路继续（支路级停止天然成立）。"""
    Mset = set(members)
    q = deque((m, 0) for m in sorted(Mset))
    ancestors, term_key, term_plen = set(), {}, {}
    n_depth = n_budget = 0
    visited = set(Mset)
    while q:
        node, d = q.popleft()
        srcs = con.execute("SELECT DISTINCT f FROM e WHERE t = ? AND ts <= ?", [node, T]).fetchall()
        for (u,) in sorted(srcs):
            if u in visited:
                continue
            visited.add(u)
            cls = classifier.classify(u)
            if cls:
                term_key[u] = cls
                term_plen[u] = d + 1
                continue
            if d + 1 > depth_limit:
                term_key[u] = ("UNRESOLVED", "depth_limit", None)
                term_plen[u] = d + 1
                n_depth += 1
                continue
            if len(ancestors) >= node_budget:
                term_key[u] = ("UNRESOLVED", "budget_truncated", None)
                term_plen[u] = d + 1
                n_budget += 1
                continue
            ancestors.add(u)
            q.append((u, d + 1))
    return ancestors, term_key, term_plen, n_depth, n_budget


# ---------------- 同秒组内拓扑排序 ----------------

def order_same_ts(group):
    """group=[(f,t,amt)] 同一 ts。Kahn 拓扑（场内路由 A→B→C 同秒链正确处理）；
    有环组按 (f,t,amt) 字典序兜底。返回 (ordered, had_cycle)。"""
    if len(group) <= 1:
        return group, False
    nodes = {x for e in group for x in (e[0], e[1])}
    indeg = {n: 0 for n in nodes}
    adj = {n: set() for n in nodes}
    for f, t, _ in group:
        if t not in adj[f]:
            adj[f].add(t)
            indeg[t] += 1
    q = deque(sorted(n for n in nodes if indeg[n] == 0))
    topo = {}
    while q:
        n = q.popleft()
        topo[n] = len(topo)
        for m in sorted(adj[n]):
            indeg[m] -= 1
            if indeg[m] == 0:
                q.append(m)
    if len(topo) < len(nodes):  # 有环
        return sorted(group), True
    return sorted(group, key=lambda e: (topo[e[0]], topo[e[1]], e[0], e[1], e[2])), False


# ---------------- 正向模拟 ----------------

def simulate(edges_iter, Mset, ancestors, term_key, term_plen, policy, T_peak):
    """edges_iter: [(ts, f, t, amt)] 已按 ts 升序（同 ts 未排）。逐笔重演到数据末，
    跨过 T_peak 时拍峰值快照。返回 {"peak": vec, "current": vec,
    "gap_events": int, "same_ts_cycles": int, "n_edges": int}。
    （direct_upstream 进货单不在模拟中维护——它是毛流入事实清单，见 gross_upstream。）"""
    acc = {}

    def account(node):
        a = acc.get(node)
        if a is None:
            a = acc[node] = make_account(policy)
        return a

    peak_snap = None
    gap_events = same_ts_cycles = n_edges = 0

    def snap():
        ent = acc.get(ENTITY_NODE)
        return ent.snapshot() if ent else {}

    def flush_group(ts, group):
        nonlocal peak_snap, gap_events, same_ts_cycles, n_edges
        if peak_snap is None and ts > T_peak:
            peak_snap = snap()
        ordered, cyc = order_same_ts(group)
        if cyc:
            same_ts_cycles += 1
        for f, t, amt in ordered:
            n_edges += 1
            src = ENTITY_NODE if f in Mset else f
            dst = ENTITY_NODE if t in Mset else t
            if src == dst:
                continue  # 实体内部互转/自转：不记账（单一边界收缩）
            if f in term_key:
                comp, shortfall = {term_key[f]: float(amt)}, 0.0
            elif src == ENTITY_NODE or f in ancestors:
                comp, shortfall = account(src).take(float(amt))
            else:  # BFS 封闭性防御：不该到达
                comp, shortfall = {}, float(amt)
            if shortfall > EPS:
                gap_key = ("UNRESOLVED", "data_gap", None)
                comp[gap_key] = comp.get(gap_key, 0.0) + shortfall
                gap_events += 1
            if dst == ENTITY_NODE:
                account(ENTITY_NODE).add(comp)
            elif t in ancestors:
                account(dst).add(comp)
            # else：流出子图/burn——发送方已扣减，构成随币离场

    cur_ts, group = None, []
    for ts, f, t, amt in edges_iter:
        if ts != cur_ts:
            if group:
                flush_group(cur_ts, group)
            cur_ts, group = ts, []
        group.append((f, t, amt))
    if group:
        flush_group(cur_ts, group)
    if peak_snap is None:
        peak_snap = snap()
    return {"peak": peak_snap, "current": snap(),
            "gap_events": gap_events, "same_ts_cycles": same_ts_cycles, "n_edges": n_edges}


def gross_upstream(con, ph, T):
    """direct_upstream 进货单＝**毛流入事实清单**（≤T 全史直接上家聚合，零分摊假设、
    不随流出扣减）。W1 教训的本义：Q1 从 20 家进过货、9 家是 W1——这个事实与"那批币
    现在还在不在"无关；周转枢纽的现存库存构成会把早期藤蔓等比消耗殆尽（PYTHIA 实测
    Q1 峰值现存构成 EwUU 100%，W1 藤全部衰减不可见），故进货单必须用毛口径。
    分母＝毛流入总量（pct_of_gross_in），与锚点库存构成（composition）分母不同、各自成立。"""
    rows = con.execute(f"""
        SELECT f, SUM(amt) FROM e
        WHERE t IN ('{ph}') AND f NOT IN ('{ph}') AND ts <= {T}
        GROUP BY f ORDER BY 2 DESC""").fetchall()
    total_in = sum(int(v) for _, v in rows)
    if not total_in:
        return []
    return [{"addr": f, "pct_of_gross_in": round(int(v) * 100.0 / total_in, 4),
             "raw": str(int(v))} for f, v in rows]


# ---------------- 实体级组装 ----------------

def combined_series(con, addrs):
    ph = "', '".join(addrs)
    rows = con.execute(f"""
        WITH d AS (
            SELECT day, SUM(v) AS delta FROM (
                SELECT ts // 86400 AS day, amt AS v FROM e WHERE t IN ('{ph}')
                UNION ALL
                SELECT ts // 86400, -amt FROM e WHERE f IN ('{ph}')
            ) GROUP BY 1
        )
        SELECT day, SUM(delta) OVER (ORDER BY day) AS bal FROM d ORDER BY day""").fetchall()
    return [(int(d), int(b)) for d, b in rows]


def fetch_sim_edges(con, sim_nodes, T, edge_budget):
    """子图相关边（流入或流出任一端在 sim_nodes）≤T，按 ts 升序。超边预算 exit 2。"""
    con.execute("DROP TABLE IF EXISTS simn")
    con.execute("CREATE TEMP TABLE simn(a VARCHAR)")
    con.executemany("INSERT INTO simn VALUES (?)", [(x,) for x in sorted(sim_nodes)])
    n = con.execute(f"""
        SELECT COUNT(*) FROM e
        WHERE ts <= {T} AND (t IN (SELECT a FROM simn) OR f IN (SELECT a FROM simn))""").fetchone()[0]
    if int(n) > edge_budget:
        log(f"子图边数 {int(n):,} 超预算 {edge_budget:,}——降 --depth-limit 或用 --labels-file "
            "截断设施后重跑（fail-closed，不静默采样）")
        sys.exit(2)
    rows = con.execute(f"""
        SELECT ts, f, t, amt FROM e
        WHERE ts <= {T} AND (t IN (SELECT a FROM simn) OR f IN (SELECT a FROM simn))
        ORDER BY ts""").fetchall()
    return [(int(ts), f, t, int(v)) for ts, f, t, v in rows]


def comp_to_list(vec, term_plen, stock, labels):
    """向量 → composition 数组（按占比降序，全量零截断）。"""
    ev_map = {"mint": "onchain_pattern", "facility_candidate": "heuristic",
              "data_gap": "onchain_pattern", "depth_limit": "onchain_pattern",
              "budget_truncated": "onchain_pattern"}
    out = []
    for (kind, sub, via), amt in sorted(vec.items(), key=lambda kv: -kv[1]):
        if amt <= EPS:
            continue
        ev = "label_confirmed" if (via and via in labels and kind != "UNRESOLVED") \
            else ev_map.get(sub, "onchain_pattern")
        out.append({"kind": kind, "subkind": sub, "via": via,
                    "pct_of_anchor": round(amt * 100.0 / stock, 4), "raw": str(int(amt)),
                    "evidence_level": ev,
                    # via=None 的未决聚合条目（data_gap/depth_limit/budget_truncated）无单一
                    # 路径长度可言，诚实报 null 而非假值
                    "path_len": term_plen.get(via) if via else None})
    return out


def top_entry(vec):
    """敏感性比较对象：第一大构成条目的 (kind, sub, via)。空向量返回 None。"""
    best_k, best_v = None, 0.0
    for k, v in vec.items():
        if v > best_v:
            best_k, best_v = k, v
    return best_k


def trace_entity(con, classifier, eid, members, total, a):
    series = combined_series(con, members)
    if not series:
        return None, None
    peak = max(b for _, b in series)
    peak_day = next(d for d, b in series if b == peak)
    current = series[-1][1]
    T_cur = int(con.execute("SELECT MAX(ts) FROM e").fetchone()[0])
    T_peak = (peak_day + 1) * 86400 - 1
    ph = "', '".join(sorted(members))
    gross_in, gross_out = con.execute(f"""
        SELECT COALESCE(SUM(CASE WHEN t IN ('{ph}') AND f NOT IN ('{ph}') THEN amt END), 0),
               COALESCE(SUM(CASE WHEN f IN ('{ph}') AND t NOT IN ('{ph}') THEN amt END), 0)
        FROM e""").fetchone()

    Mset = set(members)
    ancestors, term_key, term_plen, n_depth, n_budget = build_ancestors(
        con, Mset, T_cur, classifier, a.depth_limit, a.node_budget)
    edges = fetch_sim_edges(con, ancestors | Mset, T_cur, a.edge_budget)
    log(f"  子图：祖先 {len(ancestors):,} / 终点 {len(term_key):,}"
        f"（深度截断 {n_depth}·预算截断 {n_budget}）/ 边 {len(edges):,}")

    runs = {}
    for policy in POLICIES:
        runs[policy] = simulate(edges, Mset, ancestors, term_key, term_plen, policy, T_peak)
    main = runs["pro_rata"]

    def build_anchor(snap_key, stock, T, date=None):
        vec = main[snap_key]
        if stock <= 0:
            out = {"stock_raw": "0", "composition": [],
                   "direct_upstream": gross_upstream(con, ph, T)}
        else:
            out = {"stock_raw": str(stock),
                   "composition": comp_to_list(vec, term_plen, stock, classifier.labels),
                   "direct_upstream": gross_upstream(con, ph, T)}
        if date:
            out["date"] = date
        return out

    a_peak = build_anchor("peak", peak, T_peak, day_str(peak_day))
    a_cur = build_anchor("current", current, T_cur)

    # 敏感性：stock>0 锚点的第一大条目三策略必须一致
    sens = {"stable": True, "anchors": {}}
    for snap_key, stock in (("peak", peak), ("current", current)):
        if stock <= 0:
            continue
        tops = {p: top_entry(runs[p][snap_key]) for p in POLICIES}
        agree = len({t for t in tops.values()}) == 1
        if not agree:
            sens["stable"] = False
        sens["anchors"][snap_key] = {
            "top_by_policy": {p: (list(t) if t else None) for p, t in tops.items()},
            "agree": agree}

    ent = {
        "entity_id": eid, "member_count": len(members),
        "members_sha256": members_sha256(members),
        "anchors": {"current": a_cur, "peak": a_peak},
        "turnover": {"gross_in_raw": str(int(gross_in)), "gross_out_raw": str(int(gross_out))},
        "closure_check": {
            "current_sum_pct": round(sum(c["pct_of_anchor"] for c in a_cur["composition"]), 3),
            "peak_sum_pct": round(sum(c["pct_of_anchor"] for c in a_peak["composition"]), 3)},
        "simulation": {"ancestors": len(ancestors), "terminals": len(term_key),
                       "depth_truncated": n_depth, "budget_truncated": n_budget,
                       "edges_simulated": main["n_edges"],
                       "same_ts_cycle_groups": main["same_ts_cycles"],
                       "data_gap_events": main["gap_events"]},
    }
    return ent, sens


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--edges-sol")
    src.add_argument("--edges-evm-v2")
    src.add_argument("--duckdb")
    ap.add_argument("--edges-table", default="edges")
    ap.add_argument("--total-supply", required=True)
    ap.add_argument("--entity-file", required=True, help="{entity_id:[addr…]}")
    ap.add_argument("--labels-file", help="{addr:{kind,name}} 确证标签（cex/dex_pool/facility/bridge/…）")
    ap.add_argument("--out", default="provenance_ledger.json")
    ap.add_argument("--mem-limit", default="8GB")
    ap.add_argument("--depth-limit", type=int, default=10, help="BFS 深度上限（距实体最短跳数）")
    ap.add_argument("--facility-min-degree", type=int, default=1000, help="设施启发式：双向对手方 ≥此数")
    ap.add_argument("--node-budget", type=int, default=200_000, help="单实体祖先节点上限（超出记 budget_truncated）")
    ap.add_argument("--edge-budget", type=int, default=3_000_000, help="单实体子图边数上限（超出 exit 2）")
    a = ap.parse_args()

    import duckdb
    total = int(a.total_supply)
    if total <= 0:
        log("参数错误：--total-supply 必须为正")
        sys.exit(2)
    entity_map = load_entity_map(a.entity_file)
    labels = load_labels(a.labels_file) if a.labels_file else {}

    con = duckdb.connect()
    con.execute(f"SET memory_limit='{a.mem_limit}'")
    t0 = datetime.now(timezone.utc)
    if a.edges_sol:
        n_edges = load_sol(con, a.edges_sol)
    elif a.edges_evm_v2:
        n_edges = load_evm_v2(con, a.edges_evm_v2)
    else:
        n_edges = attach_duckdb(con, a.duckdb, a.edges_table)
    log(f"边表就绪 {n_edges:,} 条——物化索引表 e(t)…")
    con.execute("CREATE TABLE e AS SELECT ts, f, t, amt FROM edges")
    con.execute("CREATE INDEX idx_e_t ON e(t)")

    classifier = Classifier(con, labels, a.facility_min_degree)
    entities, sens_all = [], {}
    for eid, members in entity_map.items():
        log(f"溯源 {eid}（{len(members)} 址，三策略模拟）…")
        ent, sens = trace_entity(con, classifier, eid, members, total, a)
        if ent is None:
            log(f"  {eid}: 无任何链上活动，跳过")
            continue
        # 闭合自检（正向模拟构造保证守恒；偏差＝实现 bug 或余额为负的数据缺失案）
        for anchor_name in ("current", "peak"):
            s = ent["closure_check"][f"{anchor_name}_sum_pct"]
            stock = int(ent["anchors"][anchor_name]["stock_raw"])
            if stock > 0 and abs(s - 100.0) > 0.5:
                log(f"闭合自检失败：{eid} {anchor_name} 锚点构成 Σ={s}% ≠ 100%"
                    "（实现守恒被破坏，或实体历史负余额＝数据缺失——exit 2）")
                sys.exit(2)
        entities.append(ent)
        sens_all[eid] = sens
        pk = ent["anchors"]["peak"]
        unres = sum(c["pct_of_anchor"] for c in pk["composition"] if c["kind"] == "UNRESOLVED")
        log(f"  峰值锚点 {pk['date']} 库存 {int(pk['stock_raw'])*100.0/total:.3f}%供应 | "
            f"终点 {len(pk['composition'])} 类 | 未决 {unres:.1f}% | 进货单 {len(pk['direct_upstream'])} 上家 | "
            f"敏感性 {'稳定' if sens['stable'] else '⚠ 翻转'}")

    unresolved_total = 0.0
    for e in entities:
        unresolved_total += sum(float(c["raw"]) for c in e["anchors"]["peak"]["composition"]
                                if c["kind"] == "UNRESOLVED")
    all_stable = all(s["stable"] for s in sens_all.values()) if sens_all else True
    report = {
        "schema": SCHEMA,
        "generated_at": t0.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "case": os.path.basename(os.path.dirname(os.path.abspath(a.out))) or None,
        "params": {k: v for k, v in vars(a).items() if k not in ("out",)},
        "total_supply_raw": str(total),
        "entities": entities,
        "unresolved_total_pct": round(unresolved_total * 100.0 / total, 4),
        "bounds_sensitivity": {
            "methods": list(POLICIES),
            "per_entity": {eid: s for eid, s in sens_all.items()},
            "conservative_vs_aggressive_verdict_stable": all_stable,
            "note": "三策略（等比/先进先出/后进先出）对每个 stock>0 锚点的第一大终点条目"
                    "逐一比对；任一翻转＝库存构成判断依赖消耗假设＝不稳，exit 2 阻断发布"},
    }
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    log(f"{len(entities)} 实体溯源完成 → {a.out}")
    if not all_stable:
        log("敏感性不稳：存在锚点的第一大终点条目随消耗策略翻转——结论不得发布（exit 2）；"
            "报告已落盘供诊断，先解决未决量/标签覆盖再重跑")
        sys.exit(2)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"[source_trace] 脚本自身错误（exit 1，修完重跑）: {e}", file=sys.stderr)
        raise SystemExit(1)
