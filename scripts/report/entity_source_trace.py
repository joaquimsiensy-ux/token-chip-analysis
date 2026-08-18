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
    2. 正向重演：子图内全部 ≤T 转账按可证链上位置
       (ts, slot/block, transaction_index, log/instruction_index) 逐笔处理。每个节点维护
       "来源构成账户"：流入按发送方账户当时构成转移入账（发送方是终点则记终点构成），
       流出等比扣减；实体成员集收缩为单一超级账户（内部互转不记账）。
    3. 锚点读数：处理完 ≤T 边后超级账户的向量＝库存终点构成；direct_upstream 进货单
       另以**毛流入事实清单**口径单列（≤T 全史直接上家聚合，零分摊、不随流出扣减——
       周转枢纽的现存库存构成会把早期藤蔓等比消耗殆尽，PYTHIA 实测 Q1 峰值现存构成
       EwUU 100%、W1 藤全部衰减不可见；而 W1 教训的本义是"从谁进过货"这个事实本身）。
  正向模拟下总量守恒是构造保证（每笔进出都过账），closure_check 降级为实现自检；
  回环（含跨时回环）天然良定义（构成随币流动，无需 SCC 概念——v1 的 same_slot_scc
  终点类别废除）。禁止按地址拓扑重排同秒事件：EVM 的 block+log_index、Solana 扩展
  7 元组的 slot+tx+instruction 可恢复精确序；旧 Solana 5 元组只有 slot，或 DuckDB 缺
  索引列时，同一最细粒度桶内“既收又发”的整笔来源记
  UNRESOLVED/order_ambiguous，超过锚点库存 0.5% 即独立阻断。

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
正式模式强制 --labels-file {addr:{"kind":"cex|dex_pool|facility|bridge|launch_alloc|airdrop|vesting",…}}；
仅显式 --allow-no-labels 可作探索运行，ledger 标 exploration 且 freeze 必拒；
边表三通道同 wave_scan（--edges-sol/--edges-evm-v2/--duckdb）。
输出：--out provenance_ledger.json。实体条目含 members_sha256；台账另记录原始边/标签/
实体文件完整哈希、total supply、manifest run/cutoff/block/denominators、算法哈希与参数。
freeze 不仅比对绑定，还以当前代码从当前原始边真实重放并比较语义摘要。

退出码：0=溯源完成且闭合且敏感性稳定；2=数据/参数错误、闭合自检失败或敏感性翻转
（fail-closed）；1=脚本自身错误。

回测基线（装闸必附原案回测；fixtures/pythia_anchors.json，v2 重算后数字以新实测为准）：
  - Q1 峰值锚点 direct_upstream 中 ≥9 个 W1 名单地址现形；
  - 3yMk：EwUU8oi 设施支路停（facility_candidate/confirmed）而 W1 支路穿透（path_len ≥2）。
"""
import argparse
import glob
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
ORDER_AMBIGUOUS_KEY = ("UNRESOLVED", "order_ambiguous", None)
EPS = 1e-6
ORDER_MATERIAL_PCT = 0.5
# 尘埃锚点线：锚点库存 < 总供应的 0.01% 时，构成"第一大来源"不承载任何结论，
# 三策略翻转不入稳定性判定（明细照记并标 negligible_stock）。清零实体的残渣
# 库存曾把整案 freeze 卡死（MOG 2026-08-11：0.00003% 残渣的来源排序翻转）。
NEGLIGIBLE_STOCK_PCT = 0.01


def log(msg):
    print(f"[source_trace] {msg}", flush=True)


def members_sha256(addrs):
    return hashlib.sha256(",".join(sorted(addrs)).encode()).hexdigest()


def full_file_record(path, case_dir):
    """完整 SHA-256（不是大文件头尾抽样）；freeze 以此绑定当前原始输入。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(blk)
    ap = os.path.abspath(path)
    try:
        rel = os.path.relpath(ap, case_dir)
        shown = rel if rel != ".." and not rel.startswith(".." + os.sep) else ap
    except ValueError:
        shown = ap
    return {"path": shown, "bytes": os.path.getsize(ap), "sha256": h.hexdigest()}


def bound_path(path, case_dir):
    ap = os.path.abspath(path)
    rel = os.path.relpath(ap, case_dir)
    return rel if rel != ".." and not rel.startswith(".." + os.sep) else ap


def source_binding(a, case_dir):
    if a.edges_sol:
        kind, argument = "sol", a.edges_sol
        files = sorted(glob.glob(a.edges_sol))
    elif a.edges_evm_v2:
        kind, argument = "evm_v2", a.edges_evm_v2
        files = sorted(glob.glob(os.path.join(a.edges_evm_v2, "run_*", "logs.parquet")))
        files += sorted(glob.glob(os.path.join(a.edges_evm_v2, "run_*", "blocks.parquet")))
    else:
        kind, argument, files = "duckdb", a.duckdb, [a.duckdb]
    manifest_path = os.path.join(case_dir, "handoff_manifest.json")
    data_map_path = os.path.join(case_dir, "data_map.json")
    manifest = None
    if os.path.isfile(manifest_path):
        m = json.load(open(manifest_path, encoding="utf-8"))
        manifest = {"file": full_file_record(manifest_path, case_dir),
                    "run_id": m.get("run_id"), "scope": m.get("scope")}
    data_map = None
    if os.path.isfile(data_map_path):
        dm = json.load(open(data_map_path, encoding="utf-8"))
        data_map = {"file": full_file_record(data_map_path, case_dir),
                    "paths": sorted(x.get("path") for x in dm.get("files", [])
                                    if isinstance(x, dict) and isinstance(x.get("path"), str))}
    trace_rec = full_file_record(__file__, case_dir)
    loader_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wave_scan.py")
    loader_rec = full_file_record(loader_path, case_dir)
    return {
        "mode": "exploration" if a.allow_no_labels else "formal",
        "algorithm": {"script_sha256": trace_rec["sha256"],
                      "files": {"entity_source_trace.py": trace_rec,
                                "wave_scan.py": loader_rec},
                      "policies": list(POLICIES), "order_material_pct": ORDER_MATERIAL_PCT},
        "source": {"kind": kind, "argument": bound_path(argument, case_dir),
                   "edges_table": a.edges_table if kind == "duckdb" else None,
                   "files": [full_file_record(p, case_dir) for p in files]},
        "entity_file": full_file_record(a.entity_file, case_dir),
        "labels_file": full_file_record(a.labels_file, case_dir) if a.labels_file else None,
        "handoff_manifest": manifest,
        "data_map": data_map,
        "total_supply_raw": str(a.total_supply),
        "algorithm_params": {"depth_limit": a.depth_limit,
                             "facility_min_degree": a.facility_min_degree,
                             "node_budget": a.node_budget, "edge_budget": a.edge_budget,
                             # F-06：翻转裁决收据（flip-adjudications/v1）以文件引用随绑定
                             # 传递——freeze 重放用同一份收据实物还原同一 exit 语义；
                             # 收据内容一变（sha 失配）重放自动拒。
                             "flip_adjudications": (full_file_record(a.acknowledge_flip, case_dir)
                                                    if a.acknowledge_flip else None)},
    }


def semantic_payload(report):
    """重放比较唯一口径；排除 generated_at/case/展示 note 等非语义字段。"""
    return {k: report.get(k) for k in ("schema", "total_supply_raw", "input_binding",
                                        "entities", "unresolved_total_pct", "bounds_sensitivity")}


def semantic_sha256(report):
    return hashlib.sha256(json.dumps(semantic_payload(report), sort_keys=True,
                                     ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


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


# ---------------- 正向模拟 ----------------

def simulate(edges_iter, Mset, ancestors, term_key, term_plen, policy, T_peak):
    """edges_iter 带 chain_pos/order_exact/ingest_seq，按可证链上位置升序。
    精确位置缺失时绝不再按地址拓扑改写真实顺序：保留采集观察顺序，但同一最细粒度桶内
    若某节点既收又发，则该节点的流出来源无法证明，整笔记 UNRESOLVED/order_ambiguous。
    这样后到资金不会被反向归给先发生的流出；未决量达到 0.5% 锚点库存时由独立顺序
    敏感性维度阻断。

    逐笔重演到数据末，
    跨过 T_peak 时拍峰值快照。返回 {"peak": vec, "current": vec,
    "gap_events": int, "order_ambiguous_groups": int, "order_ambiguous_events": int,
    "n_edges": int}。
    （direct_upstream 进货单不在模拟中维护——它是毛流入事实清单，见 gross_upstream。）"""
    acc = {}

    def account(node):
        a = acc.get(node)
        if a is None:
            a = acc[node] = make_account(policy)
        return a

    peak_snap = None
    gap_events = ambiguous_groups = ambiguous_events = n_edges = 0

    def snap():
        ent = acc.get(ENTITY_NODE)
        return ent.snapshot() if ent else {}

    def flush_group(bucket, group):
        nonlocal peak_snap, gap_events, ambiguous_groups, ambiguous_events, n_edges
        ts = bucket[0]
        if peak_snap is None and ts > T_peak:
            peak_snap = snap()
        # group=(order_exact, ingest_seq, f, t, amt)。精确桶按位置在 fetch 阶段已排好；
        # 非精确桶只保留观察顺序，不能用地址拓扑臆造执行序。
        ordered = sorted(group, key=lambda e: e[1])
        exact = all(e[0] for e in ordered)
        causal_senders = set()
        if not exact and len(ordered) > 1:
            receivers = {e[3] for e in ordered}
            causal_senders = {e[2] for e in ordered if e[2] in receivers and e[2] not in term_key}
            if causal_senders:
                ambiguous_groups += 1
        for _, _, f, t, amt in ordered:
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
            if f in causal_senders:
                # 发送方同桶也有入账；现有字段不足以证明本笔花的是旧库存还是同桶后/先到资金。
                # 账户仍按观察序扣减以维持数量账，但来源整笔降级为独立未决桶。
                comp, shortfall = {ORDER_AMBIGUOUS_KEY: float(amt)}, 0.0
                ambiguous_events += 1
            elif shortfall > EPS:
                gap_key = ("UNRESOLVED", "data_gap", None)
                comp[gap_key] = comp.get(gap_key, 0.0) + shortfall
                gap_events += 1
            if dst == ENTITY_NODE:
                account(ENTITY_NODE).add(comp)
            elif t in ancestors:
                account(dst).add(comp)
            # else：流出子图/burn——发送方已扣减，构成随币离场

    cur_bucket, group = None, []
    for ts, p1, p2, p3, exact, seq, f, t, amt in edges_iter:
        bucket = (ts, p1, p2, p3)
        if bucket != cur_bucket:
            if group:
                flush_group(cur_bucket, group)
            cur_bucket, group = bucket, []
        group.append((bool(exact), int(seq), f, t, amt))
    if group:
        flush_group(cur_bucket, group)
    if peak_snap is None:
        peak_snap = snap()
    return {"peak": peak_snap, "current": snap(),
            "gap_events": gap_events, "order_ambiguous_groups": ambiguous_groups,
            "order_ambiguous_events": ambiguous_events, "n_edges": n_edges}


def gross_upstream(con, ph, T):
    """direct_upstream 进货单＝**毛流入事实清单**（≤T 全史直接上家聚合，零分摊假设、
    不随流出扣减）。W1 教训的本义：Q1 从 20 家进过货、9 家是 W1——这个事实与"那批币
    现在还在不在"无关；周转枢纽的现存库存构成会把早期藤蔓等比消耗殆尽（PYTHIA 实测
    Q1 峰值现存构成 EwUU 100%，W1 藤全部衰减不可见），故进货单必须用毛口径。
    分母＝毛流入总量（pct_of_gross_in），与锚点库存构成（composition）分母不同、各自成立。"""
    rows = con.execute(f"""
        SELECT f, SUM(amt) FROM e
        WHERE t IN ('{ph}') AND f NOT IN ('{ph}') AND ts <= {T}
        GROUP BY f ORDER BY 2 DESC, 1""").fetchall()
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
    """子图相关边（流入或流出任一端在 sim_nodes）≤T，按可证链上位置升序。
    非精确桶末位只用 ingest_seq 保留采集观察顺序，不宣称它是链上真序。"""
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
        SELECT ts, chain_pos1, chain_pos2, chain_pos3, order_exact, ingest_seq, f, t, amt FROM e
        WHERE ts <= {T} AND (t IN (SELECT a FROM simn) OR f IN (SELECT a FROM simn))
        ORDER BY ts, chain_pos1 NULLS FIRST, chain_pos2 NULLS FIRST,
                 chain_pos3 NULLS FIRST, ingest_seq""").fetchall()
    return [(int(ts), p1, p2, p3, bool(exact), int(seq), f, t, int(v))
            for ts, p1, p2, p3, exact, seq, f, t, v in rows]


def comp_to_list(vec, term_plen, stock, labels):
    """向量 → composition 数组（按占比降序，全量零截断）。"""
    ev_map = {"mint": "onchain_pattern", "facility_candidate": "heuristic",
              "data_gap": "onchain_pattern", "depth_limit": "onchain_pattern",
              "budget_truncated": "onchain_pattern", "order_ambiguous": "onchain_pattern"}
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
    rows = [(k, v) for k, v in vec.items() if v > EPS]
    return sorted(rows, key=lambda kv: (-kv[1], str(kv[0])))[0][0] if rows else None


def policy_detail(vec):
    """freeze 可独立重算 top/stability 的策略明细；不能只留下自报 stable 布尔值。"""
    return [{"terminal": list(k), "raw": str(int(v))}
            for k, v in sorted(vec.items(), key=lambda kv: (-kv[1], str(kv[0]))) if v > EPS]


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

    # 两个正交维度：①库存消耗策略；②输入事件顺序是否足够精确。
    # 第二维不能再被 FIFO/LIFO 的“第一大来源一致”掩盖。
    sens = {"stable": True, "consumption_stable": True, "ordering_stable": True,
            "anchors": {}}
    for snap_key, stock in (("peak", peak), ("current", current)):
        if stock <= 0:
            continue
        # 尘埃锚点（<总供应 0.01%）：构成排序不承载结论，翻转不入稳定性判定
        negligible = stock * 10000 < total
        tops = {p: top_entry(runs[p][snap_key]) for p in POLICIES}
        agree = len({t for t in tops.values()}) == 1
        if not agree and not negligible:
            sens["stable"] = sens["consumption_stable"] = False
        order_raw = float(main[snap_key].get(ORDER_AMBIGUOUS_KEY, 0.0))
        order_pct = order_raw * 100.0 / stock
        order_ok = order_pct <= ORDER_MATERIAL_PCT
        if not order_ok and not negligible:
            sens["stable"] = sens["ordering_stable"] = False
        sens["anchors"][snap_key] = {
            "top_by_policy": {p: (list(t) if t else None) for p, t in tops.items()},
            "policy_details": {p: policy_detail(runs[p][snap_key]) for p in POLICIES},
            "agree": agree,
            "negligible_stock": negligible,
            "ordering_sensitivity": {
                "status": "RESOLVED" if order_ok else "UNRESOLVED",
                "order_ambiguous_raw": str(int(order_raw)),
                "order_ambiguous_pct": round(order_pct, 4),
                "materiality_pct": ORDER_MATERIAL_PCT,
                "stable": order_ok}}

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
                       "order_ambiguous_groups": main["order_ambiguous_groups"],
                       "order_ambiguous_events": main["order_ambiguous_events"],
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
    ap.add_argument("--legacy-sol5", action="store_true",
                    help="保留显式诊断开关；本实体 provenance 正式链一律拒绝")
    ap.add_argument("--total-supply", required=True)
    ap.add_argument("--entity-file", required=True, help="{entity_id:[addr…]}")
    ap.add_argument("--labels-file", help="{addr:{kind,name}} 确证标签（cex/dex_pool/facility/bridge/…）")
    ap.add_argument("--allow-no-labels", action="store_true",
                    help="仅探索：允许无标签运行；产物带 exploration 标记且禁止 freeze")
    ap.add_argument("--out", default="provenance_ledger.json")
    ap.add_argument("--acknowledge-flip", metavar="RECEIPT.json",
                    help="flip-adjudications/v1 裁决收据文件路径（F-06 起唯一合法通道；"
                         "6.39.4 的 ENTITY:ANCHOR:REASON 字符串格式已废除）。收据必须含"
                         "裁决主体、UTC 决定时间、名册与证据 sha 绑定，且每锚点行携带"
                         "flip_fingerprint（该锚点三策略明细的规范化 sha）与三策略 top"
                         "名称/份额披露——本工具重算当前运行同款指纹并要求相等，底层数据"
                         "一变收据自动失效必须重裁。收据引用随 input_binding 传递，"
                         "freeze 重放同收据还原。")
    ap.add_argument("--mem-limit", default="8GB")
    ap.add_argument("--depth-limit", type=int, default=10, help="BFS 深度上限（距实体最短跳数）")
    ap.add_argument("--facility-min-degree", type=int, default=1000, help="设施启发式：双向对手方 ≥此数")
    ap.add_argument("--node-budget", type=int, default=200_000, help="单实体祖先节点上限（超出记 budget_truncated）")
    ap.add_argument("--edge-budget", type=int, default=3_000_000, help="单实体子图边数上限（超出 exit 2）")
    a = ap.parse_args()

    if a.legacy_sol5:
        log("正式 entity provenance 拒绝 legacy-sol5；旧数据没有可证交易内顺序")
        return 2

    if not a.labels_file and not a.allow_no_labels:
        log("正式模式必须给 --labels-file；仅探索可显式加 --allow-no-labels")
        sys.exit(2)
    if a.labels_file and a.allow_no_labels:
        log("--labels-file 与 --allow-no-labels 互斥；有标签时使用正式模式")
        sys.exit(2)

    import duckdb
    total = int(a.total_supply)
    if total <= 0:
        log("参数错误：--total-supply 必须为正")
        sys.exit(2)
    entity_map = load_entity_map(a.entity_file)
    labels = load_labels(a.labels_file) if a.labels_file else {}
    if a.labels_file and not labels:
        log("正式模式 --labels-file 有效标签数为 0——空标签快照禁止进入 provenance/freeze")
        return 2
    # F-06：裁决收据先行验证（文件不存在/结构不合法＝调用错误 exit 2，不落 exit 1）；
    # 覆盖判定在 ledger 组装后按当前明细重算指纹。
    from handoff_manifest import (ledger_real_flips, load_flip_adjudications,
                                  verify_flip_receipt_against_ledger)
    case_dir = os.path.dirname(os.path.abspath(a.out))
    receipt_rows = {}
    if a.acknowledge_flip:
        # F-D7：三处收据口径统一为"案根内＋sha 绑定"——trace 不收案外收据（案根检查
        # 先于结构验证：案外收据先报位置错，不报它同目录缺名册一类的次生错）。
        receipt_real = os.path.realpath(os.path.expanduser(a.acknowledge_flip))
        rel = os.path.relpath(receipt_real, os.path.realpath(case_dir))
        if rel == ".." or rel.startswith(".." + os.sep):
            log(f"--acknowledge-flip 裁决收据必须在案根（--out 所在目录）内: {a.acknowledge_flip}")
            sys.exit(2)
        try:
            _, receipt_rows = load_flip_adjudications(
                a.acknowledge_flip, current_entity_file=a.entity_file)
        except (OSError, ValueError, TypeError) as exc:
            log(f"--acknowledge-flip 裁决收据不合法: {exc}")
            sys.exit(2)
    binding = source_binding(a, case_dir)

    con = duckdb.connect()
    con.execute(f"SET memory_limit='{a.mem_limit}'")
    t0 = datetime.now(timezone.utc)
    if a.edges_sol:
        n_edges = load_sol(con, a.edges_sol)
    elif a.edges_evm_v2:
        n_edges = load_evm_v2(con, a.edges_evm_v2)
    else:
        n_edges = attach_duckdb(con, a.duckdb, a.edges_table)
    # handoff scope 若已冻结 cutoff/block，溯源必须实际应用同一边界；只把值写进台账不够。
    where = []
    hb = binding.get("handoff_manifest") or {}
    scope = hb.get("scope") or {}
    cutoff = scope.get("cutoff_utc")
    frozen_pos = scope.get("frozen_block")
    if cutoff:
        try:
            cutoff_ts = int(datetime.fromisoformat(str(cutoff).replace("Z", "+00:00")).timestamp())
            where.append(f"ts <= {cutoff_ts}")
        except (ValueError, TypeError):
            log(f"handoff cutoff_utc 无法解析: {cutoff!r}")
            sys.exit(2)
    if frozen_pos not in (None, ""):
        try:
            fp = int(frozen_pos)
            missing_pos = int(con.execute(
                "SELECT COUNT(*) FROM edges WHERE chain_pos1 IS NULL").fetchone()[0])
            if missing_pos:
                log(f"handoff frozen_block={fp} 但 {missing_pos:,} 条边缺 slot/block 位置——"
                    "不能声称已应用冻结区块")
                sys.exit(2)
            where.append(f"chain_pos1 <= {fp}")
        except (ValueError, TypeError):
            log(f"handoff frozen_block 不是整数: {frozen_pos!r}")
            sys.exit(2)
    wh = (" WHERE " + " AND ".join(where)) if where else ""
    log(f"边表就绪 {n_edges:,} 条——按 handoff cutoff/block 物化索引表 e(t)…")
    con.execute(f"""CREATE TABLE e AS
        SELECT ts, f, t, amt, chain_pos1, chain_pos2, chain_pos3,
               order_exact, ingest_seq FROM edges{wh}""")
    kept = int(con.execute("SELECT COUNT(*) FROM e").fetchone()[0])
    if not kept:
        log("cutoff/block 过滤后边表为空——边界或输入错误")
        sys.exit(2)
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
    ordering_bad = any(not s.get("ordering_stable", True) for s in sens_all.values())
    report = {
        "schema": SCHEMA,
        "exploration": bool(a.allow_no_labels),
        "generated_at": t0.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "case": os.path.basename(os.path.dirname(os.path.abspath(a.out))) or None,
        "params": {k: v for k, v in vars(a).items() if k not in ("out",)},
        "total_supply_raw": str(total),
        "input_binding": binding,
        "entities": entities,
        "unresolved_total_pct": round(unresolved_total * 100.0 / total, 4),
        "bounds_sensitivity": {
            "methods": list(POLICIES),
            "per_entity": {eid: s for eid, s in sens_all.items()},
            "conservative_vs_aggressive_verdict_stable": all_stable,
            "acknowledged_flips": [],
            "publishable": None,
            "note": "两维独立敏感性：三种库存消耗策略逐锚点比对完整明细；缺精确链上位置时，"
                    "同一最细粒度桶内既收又发的来源记 UNRESOLVED/order_ambiguous。尘埃锚点"
                    "（<总供应 0.01%）不入判定；真实消费翻转须 flip-adjudications/v1 裁决"
                    "收据（--acknowledge-flip <收据>）逐锚点指纹绑定覆盖且构成结论按多策略"
                    "并列披露（A5 对报告实文核对），顺序未决量 >0.5% 锚点库存无豁免，exit 2"},
    }
    # 真实翻转与覆盖判定走与 freeze 同一条重算路径（指纹/份额同函数），不留两份口径。
    real_flips = ledger_real_flips(report)
    flip_fails = verify_flip_receipt_against_ledger(receipt_rows, real_flips)
    covered = set(receipt_rows) & set(real_flips)
    report["bounds_sensitivity"]["acknowledged_flips"] = sorted(
        ({"entity_id": key[0], "anchor": key[1],
          "reason": str(receipt_rows[key].get("reason", "")).strip(),
          "flip_fingerprint": receipt_rows[key].get("flip_fingerprint"),
          "source": "flip-adjudications/v1"} for key in covered),
        key=lambda x: (x["entity_id"], x["anchor"]))
    publishable = (not ordering_bad) and not flip_fails
    report["bounds_sensitivity"]["publishable"] = publishable
    report["replay_semantic_sha256"] = semantic_sha256(report)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    log(f"{len(entities)} 实体溯源完成 → {a.out}")
    if not publishable:
        for x in flip_fails:
            log(f"  ✗ {x}")
        log("敏感性不稳：消费策略主导翻转未获合法裁决收据覆盖，或事件顺序未决量达到实质线"
            "——结论不得发布（exit 2）。真实多来源结构须造 flip-adjudications/v1 裁决收据"
            "（含逐锚点 flip_fingerprint 与三策略披露）后 --acknowledge-flip <收据> 重跑；"
            "顺序未决须补齐 block/slot + tx + log/instruction 序号")
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
