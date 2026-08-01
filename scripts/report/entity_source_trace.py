#!/usr/bin/env python3
"""entity_source_trace.py — 已知实体币源溯源闸（provenance-ledger/v1，v6.8.0）。

背景：W1 波次二次漏检复盘第一道防线——PYTHIA 案 Q1 的 20 个直接上家里 9 个是 W1、
3yMk 的 11 个上家里 10 个是 W1，19 根藤裸露在进货单上却因"找到并入证据就收工"的溯源
习惯无人彻查。本闸把"每个已知实体的币从哪来"变成机器义务：溯源到可证来源/边界终点
为止，未决量显式记账，不许静默收工。

记账口径（codex 复核修订，schema 权威定义 references/scan-schemas.md §4）：
  - 分母＝两锚点库存（当前快照库存 ＋ 历史峰值时刻库存），不对全史毛流入归一化
    （周转会重复计源）；毛流转另记 turnover。
  - 实体成员先收缩单一边界：内部互转不追溯不重复计源。
  - pro-rata 主法：地址在时刻 T 持有的任意数量，按其 ≤T 全部流入等比例构成
    （流出按当时构成等比消耗 → 余额构成比例＝累计流入构成比例，递归定义自洽）。
  - direct_upstream＝锚点第一跳构成（"进货单"）单列——直接上家是中间节点会被穿透，
    终点构成里不可见，而 W1 教训恰恰藏在进货单上。

终点三类：
  PROVEN_ORIGIN：mint哨兵 / labels 确证 launch_alloc·airdrop·vesting
  BOUNDARY：labels 确证 DEX 池·CEX·设施·桥（evidence=label_confirmed）
    ——"DEX 池流出"只能记 dex_pool 边界，不得写成"swap 买入"（无对价腿数据）
  UNRESOLVED：data_gap（<T 无流入却有币）/ depth_limit（默认 10 跳）/
    same_slot_scc（递归路径回环，含跨时回环——保守归未决不强行归类）/
    prune_residual（低于剪枝线的尾量，全部入账不静默丢弃）/
    facility_candidate（启发式命中：对手方 ≥1000 且双向——标签库未确证前只记候选）

硬规则（复核翻案教训）：
  - 支路级停止：设施来的支路停，同一钱包其他支路必须继续穿透
    （3yMk 教训：EwUU8oi 来的 8.77% 停、10 条 W1 支路继续）——递归天然按支路独立。
  - 黑箱不得翻译成"用户买入/提币"；清零地址来源必须穿透（peak 锚点对零现仓实体仍有意义）。

输入：--entity-file {entity_id:[addr…]}（临时实体表或冻结表）；--labels-file 可选
{addr:{"kind":"cex|dex_pool|facility|bridge|launch_alloc|airdrop|vesting","name":…}}；
边表三通道同 wave_scan（--edges-sol/--edges-evm-v2/--duckdb）。
输出：--out provenance_ledger.json。

退出码：0=溯源完成且闭合；2=数据/参数错误或闭合校验失败（fail-closed）；1=脚本自身错误。

回测基线（装闸必附原案回测；fixtures/pythia_anchors.json）：
  - Q1 峰值锚点 direct_upstream 中 ≥9 个 W1 名单地址现形；
  - 3yMk：EwUU8oi 设施支路停（facility_candidate/confirmed）而 10 条 W1 支路穿透（path_len ≥2）。
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wave_scan import Z, DEAD, load_sol, load_evm_v2, attach_duckdb, day_str  # noqa: E402

SCHEMA = "provenance-ledger/v1"
LABEL_KIND_MAP = {
    "cex": ("BOUNDARY", "cex_confirmed"), "dex_pool": ("BOUNDARY", "dex_pool"),
    "facility": ("BOUNDARY", "facility_confirmed"), "bridge": ("BOUNDARY", "bridge"),
    "launch_alloc": ("PROVEN_ORIGIN", "launch_alloc"), "airdrop": ("PROVEN_ORIGIN", "proven_airdrop"),
    "vesting": ("PROVEN_ORIGIN", "proven_vesting"),
}


def log(msg):
    print(f"[source_trace] {msg}", flush=True)


class Tracer:
    def __init__(self, con, labels, depth_limit, facility_min_degree, node_budget):
        self.con = con
        self.labels = labels
        self.depth_limit = depth_limit
        self.node_budget = node_budget
        self.nodes_used = 0
        self._in_cache = {}
        # 设施启发式：全局对手方数（双向）一次物化
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

    def in_edges(self, addr):
        if addr not in self._in_cache:
            self._in_cache[addr] = [(int(ts), f, int(v)) for ts, f, v in self.con.execute(
                "SELECT ts, f, amt FROM e WHERE t = ? ORDER BY ts", [addr]).fetchall()]
            if len(self._in_cache) > 50_000:  # 缓存保护
                self._in_cache.clear()
        return self._in_cache[addr]

    def classify(self, addr):
        """终点判定（不含递归性终点 depth/prune/scc）。返回 (kind, subkind, evidence) 或 None。"""
        if addr == Z:
            return ("PROVEN_ORIGIN", "mint", "onchain_pattern")
        lb = self.labels.get(addr)
        if lb:
            kind = LABEL_KIND_MAP.get(lb.get("kind"))
            if kind:
                return (kind[0], kind[1], "label_confirmed")
        od, ind = self.degree.get(addr, (0, 0))
        if od >= self.facility_min_degree and ind >= self.facility_min_degree:
            return ("UNRESOLVED", "facility_candidate", "heuristic")
        return None

    def decompose(self, addr, T, amount, prune_abs, path, depth=1):
        """addr 在时刻 ≤T 持有的 amount 的来源构成 → [(kind, subkind, via, amt, path_len)]。
        支路级停止：终点判定逐支路独立——设施支路停在设施，其他支路继续。"""
        out = []
        self.nodes_used += 1
        if self.nodes_used > self.node_budget:
            return [("UNRESOLVED", "prune_residual", addr, amount, depth)]
        cls = self.classify(addr)
        if cls:
            return [(cls[0], cls[1], addr, amount, depth)]
        if depth > self.depth_limit:
            return [("UNRESOLVED", "depth_limit", addr, amount, depth)]
        if addr in path:
            # 递归路径回环（同 slot 环及跨时回环一并保守归未决——无 tx 内序号不强行归类）
            return [("UNRESOLVED", "same_slot_scc", addr, amount, depth)]
        ins = [e for e in self.in_edges(addr) if e[0] <= T]
        if not ins:
            return [("UNRESOLVED", "data_gap", addr, amount, depth)]
        total_in = sum(v for _, _, v in ins)
        residual = 0
        path2 = path | {addr}
        for ts_e, src, amt_e in ins:
            share = amount * amt_e / total_in
            if share < prune_abs:
                residual += share
                continue
            out.extend(self.decompose(src, ts_e, share, prune_abs, path2, depth + 1))
        if residual > 0:
            out.append(("UNRESOLVED", "prune_residual", addr, residual, depth))
        return out


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


def trace_entity(tracer, con, eid, members, total, depth_limit, prune_pct):
    ph = "', '".join(sorted(members))
    series = combined_series(con, sorted(members))
    if not series:
        return None
    peak = max(b for _, b in series)
    peak_day = next(d for d, b in series if b == peak)
    current = series[-1][1]
    gross_in, gross_out = con.execute(f"""
        SELECT COALESCE(SUM(CASE WHEN t IN ('{ph}') AND f NOT IN ('{ph}') THEN amt END), 0),
               COALESCE(SUM(CASE WHEN f IN ('{ph}') AND t NOT IN ('{ph}') THEN amt END), 0)
        FROM e""").fetchone()

    def anchor(T, stock):
        """实体超级节点在时刻 T 的库存构成（边界流入 pro-rata）＋第一跳进货单。"""
        if stock <= 0:
            return {"stock_raw": "0", "composition": [], "direct_upstream": []}
        ins = [(int(ts), f, int(v)) for ts, f, v in con.execute(f"""
            SELECT ts, f, amt FROM e
            WHERE t IN ('{ph}') AND f NOT IN ('{ph}') AND ts <= {T}
            ORDER BY ts""").fetchall()]
        total_in = sum(v for _, _, v in ins)
        if not total_in:
            return {"stock_raw": str(stock),
                    "composition": [{"kind": "UNRESOLVED", "subkind": "data_gap", "via": None,
                                     "pct_of_anchor": 100.0, "raw": str(stock),
                                     "evidence_level": "onchain_pattern", "path_len": 0}],
                    "direct_upstream": []}
        prune_abs = stock * prune_pct / 100.0
        # 第一跳进货单（直接上家聚合，pro-rata 折算到锚点库存）
        up = {}
        for ts_e, src, amt_e in ins:
            up[src] = up.get(src, 0) + stock * amt_e / total_in
        direct = sorted(({"addr": s, "pct_of_anchor": round(v * 100.0 / stock, 4),
                          "raw": str(int(v))} for s, v in up.items()),
                        key=lambda x: -x["pct_of_anchor"])
        # 终点构成（逐支路递归）
        terms = []
        for ts_e, src, amt_e in ins:
            share = stock * amt_e / total_in
            if share < prune_abs:
                terms.append(("UNRESOLVED", "prune_residual", None, share, 1))
                continue
            terms.extend(tracer.decompose(src, ts_e, share, prune_abs, frozenset(members)))
        agg = {}
        for kind, sub, via, amt, plen in terms:
            key = (kind, sub, via if kind != "UNRESOLVED" or sub == "facility_candidate" else None)
            if key not in agg:
                agg[key] = [0.0, plen, {"label_confirmed": 0, "onchain_pattern": 0, "heuristic": 0}]
            agg[key][0] += amt
            agg[key][1] = min(agg[key][1], plen)
        ev_map = {"mint": "onchain_pattern", "facility_candidate": "heuristic"}
        comp = []
        for (kind, sub, via), (amt, plen, _) in sorted(agg.items(), key=lambda kv: -kv[1][0]):
            lb = tracer.labels.get(via) if via else None
            ev = "label_confirmed" if (lb and kind != "UNRESOLVED") else ev_map.get(sub, "onchain_pattern")
            comp.append({"kind": kind, "subkind": sub, "via": via,
                         "pct_of_anchor": round(amt * 100.0 / stock, 4), "raw": str(int(amt)),
                         "evidence_level": ev, "path_len": plen})
        return {"stock_raw": str(stock), "composition": comp, "direct_upstream": direct}

    cutoff_T = con.execute("SELECT MAX(ts) FROM e").fetchone()[0]
    a_cur = anchor(int(cutoff_T), current)
    a_peak = anchor((peak_day + 1) * 86400 - 1, peak)
    a_peak["date"] = day_str(peak_day)
    return {
        "entity_id": eid, "member_count": len(members),
        "anchors": {"current": a_cur, "peak": a_peak},
        "turnover": {"gross_in_raw": str(int(gross_in)), "gross_out_raw": str(int(gross_out))},
        "closure_check": {
            "current_sum_pct": round(sum(c["pct_of_anchor"] for c in a_cur["composition"]), 3),
            "peak_sum_pct": round(sum(c["pct_of_anchor"] for c in a_peak["composition"]), 3)},
    }


def bounds_sensitivity(entities):
    """简版敏感性（完整 FIFO/LIFO 列补齐项）：UNRESOLVED 极端摆动下峰值锚点主导终点
    类别是否翻转——unresolved 并入第二大类后仍不超过第一大类 → stable。"""
    stable = True
    for e in entities:
        comp = e["anchors"]["peak"]["composition"]
        resolved = [c for c in comp if c["kind"] != "UNRESOLVED"]
        unres = sum(c["pct_of_anchor"] for c in comp if c["kind"] == "UNRESOLVED")
        if len(resolved) >= 2:
            top1, top2 = resolved[0]["pct_of_anchor"], resolved[1]["pct_of_anchor"]
            if top2 + unres > top1:
                stable = False
        elif len(resolved) <= 1 and unres > (resolved[0]["pct_of_anchor"] if resolved else 0):
            stable = False
    return stable


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
    ap.add_argument("--depth-limit", type=int, default=10)
    ap.add_argument("--prune-pct", type=float, default=0.2, help="剪枝线：单支路 <锚点×此%%入 prune_residual")
    ap.add_argument("--facility-min-degree", type=int, default=1000, help="设施启发式：双向对手方 ≥此数")
    ap.add_argument("--node-budget", type=int, default=2_000_000, help="单案分解调用上限（防路径爆炸）")
    a = ap.parse_args()

    import duckdb
    total = int(a.total_supply)
    if total <= 0:
        log("参数错误：--total-supply 必须为正")
        sys.exit(2)
    with open(a.entity_file, encoding="utf-8") as fh:
        entity_map = json.load(fh)
    if not isinstance(entity_map, dict) or not entity_map:
        log("参数错误：--entity-file 需为非空 {entity_id:[addr…]}")
        sys.exit(2)
    labels = {}
    if a.labels_file:
        with open(a.labels_file, encoding="utf-8") as fh:
            labels = json.load(fh)

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

    tracer = Tracer(con, labels, a.depth_limit, a.facility_min_degree, a.node_budget)
    entities = []
    for eid, members in entity_map.items():
        members = set(members)
        log(f"溯源 {eid}（{len(members)} 址）…")
        ent = trace_entity(tracer, con, eid, members, total, a.depth_limit, a.prune_pct)
        if ent is None:
            log(f"  {eid}: 无任何链上活动，跳过")
            continue
        for anchor_name in ("current", "peak"):
            s = ent["closure_check"][f"{anchor_name}_sum_pct"]
            stock = int(ent["anchors"][anchor_name]["stock_raw"])
            if stock > 0 and abs(s - 100.0) > 0.5:
                log(f"闭合校验失败：{eid} {anchor_name} 锚点构成 Σ={s}% ≠ 100%（守恒被破坏，exit 2）")
                sys.exit(2)
        entities.append(ent)
        pk = ent["anchors"]["peak"]
        unres = sum(c["pct_of_anchor"] for c in pk["composition"] if c["kind"] == "UNRESOLVED")
        log(f"  峰值锚点 {pk['date']} 库存 {int(pk['stock_raw'])*100.0/total:.3f}%供应 | "
            f"终点 {len(pk['composition'])} 类 | 未决 {unres:.1f}% | 进货单 {len(pk['direct_upstream'])} 上家")

    unresolved_total = 0.0
    for e in entities:
        stock = int(e["anchors"]["peak"]["stock_raw"])
        unresolved_total += sum(float(c["raw"]) for c in e["anchors"]["peak"]["composition"]
                                if c["kind"] == "UNRESOLVED")
    report = {
        "schema": SCHEMA,
        "generated_at": t0.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "case": os.path.basename(os.path.dirname(os.path.abspath(a.out))) or None,
        "params": {k: v for k, v in vars(a).items() if k not in ("out",)},
        "total_supply_raw": str(total),
        "entities": entities,
        "unresolved_total_pct": round(unresolved_total * 100.0 / total, 4),
        "bounds_sensitivity": {"method": "pro-rata",
                               "conservative_vs_aggressive_verdict_stable": bounds_sensitivity(entities),
                               "note": "完整 FIFO/LIFO 敏感性为实现阶段补齐项；stable=false 时结论发布须"
                                       "在报告中列示上下界并说明判级不受翻转影响，否则阻断"},
        "node_budget_used": tracer.nodes_used,
    }
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    log(f"{len(entities)} 实体溯源完成（分解调用 {tracer.nodes_used:,}）→ {a.out}")
    if not report["bounds_sensitivity"]["conservative_vs_aggressive_verdict_stable"]:
        log("⚠ 敏感性不稳：存在实体的未决量足以翻转主导终点类别——发布前须列示上下界")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"[source_trace] 脚本自身错误（exit 1，修完重跑）: {e}", file=sys.stderr)
        raise SystemExit(1)
