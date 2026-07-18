#!/usr/bin/env python3
"""U3 增量分析主脚本（EVM）：
1) 旧实体逐组四态表（增持/减持/不变/清仓；组级合并口径）
2) 新庄候选扫描 —— 双口径：最新余额榜现仓 ≥ 阈值（U3a 主口径，防"旧仓+新吸跨线"漏检）
   ∪ 窗口净增 ≥ 阈值；排除旧实体∪设施∪池∪观察名单
3) 观察哨逐条核查（monitoring_advice mode-aware：any_out 查窗口动作 / threshold 算累计净变动）
4) 窗口买卖榜 —— 全窗净变化口径（毛买卖量作辅助列；"同 tx 净额"仍是毛口径、
   会把窗口内买回的往返客计成大卖家，NOXA 复盘 v2.7.0 教训固化）

来源：RAXOL(analyze_inc) / Pointless(watchpost_check) / TRASH(analyze_inc) /
VEX(analyze_inc) 四次 /token-update 实战合并参数化收编（v2.10.0）。

用法（工作目录含 config.json）：
  python3 analyze_inc.py --old-balances data/balances_now.json
                         [--balances data/balances_new.json] [--stats data/window_stats.json]
                         [--appendix appendix.json] [--inc data/transfers_inc.jsonl.gz]
                         [--cand-pct 0.3] [--state-eps 0.01] [--out data/inc_analysis.json]
--inc 给了才输出哨兵逐笔 moves 明细（默认给）。
--state-eps：四态判定阈（占总量百分点）；历史三战用过 0.005/0.01/0.02，默认 0.01。
新面孔候选溯源（首笔进货/gas 同源/关联聚类）仍需人工回查旧全量数据，本脚本只出候选与画像。
"""
import argparse, gzip, json, os
from collections import defaultdict
from datetime import datetime, timezone

ZERO = "0x" + "0" * 40


def load_cfg():
    with open("config.json") as f:
        cfg = json.load(f)
    dec = int(cfg.get("decimals", 18))
    total = int(cfg["total_supply_tokens"]) * 10 ** dec
    pools = {}
    for a, label in (cfg.get("pools") or {}).items():
        pools[a.lower()] = label
    for key, label in (("pool", "主池"), ("pool_manager", "V4-PoolManager")):
        if cfg.get(key):
            pools.setdefault(cfg[key].lower(), label)
    for p in cfg.get("v2_pairs") or []:
        pools.setdefault(p.lower(), "V2池")
    infra = set(a.lower() for a in cfg.get("infra_addresses") or [])
    return total, dec, pools, infra


def load_balances(path):
    with open(path) as f:
        d = json.load(f)
    if isinstance(d.get("balances"), dict):
        d = d["balances"]
    return {k.lower(): int(v) for k, v in d.items()}


def iso(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()[:16] if ts else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-balances", required=True)
    ap.add_argument("--balances", default="data/balances_new.json")
    ap.add_argument("--stats", default="data/window_stats.json")
    ap.add_argument("--appendix", default="appendix.json")
    ap.add_argument("--inc", default="data/transfers_inc.jsonl.gz")
    ap.add_argument("--cand-pct", type=float, default=0.3, help="新庄候选粗筛线（%%总供应）")
    ap.add_argument("--state-eps", type=float, default=0.01, help="四态判定阈（占总量百分点）")
    ap.add_argument("--out", default="data/inc_analysis.json")
    args = ap.parse_args()

    total, dec, pools, infra = load_cfg()
    unit = 10 ** dec
    bal_old = load_balances(args.old_balances)
    bal_new = load_balances(args.balances)
    apath = args.appendix
    if not os.path.exists(apath) and apath == "appendix.json" and os.path.exists("analysis-state.json"):
        print("NOTE: 无 appendix.json（未买入标的无监控包），改读 analysis-state.json（U0 4c）")
        apath = "analysis-state.json"
    with open(apath) as f:
        app = json.load(f)
    with open(args.stats) as f:
        stats = {a.lower(): {k: (int(v) if k in ("buy", "sell", "t_in", "t_out", "burn") else v)
                             for k, v in s.items()} for a, s in json.load(f).items()}

    def wnet(a):
        s = stats.get(a)
        if not s:
            return 0
        return s["buy"] - s["sell"] + s["t_in"] - s["t_out"] - s["burn"]

    def pct(v):
        return v / total * 100

    # ── 已知集合 ──
    old_entity = {}
    for g in app.get("whale_groups", []):
        for a in g.get("addresses", []):
            old_entity[a.lower()] = g.get("label", f"实体#{g.get('id')}")
    vaults = {v["address"].lower(): v.get("label", "") for v in app.get("vault_addresses", [])}
    watch_addrs = {}
    for m in app.get("monitoring_advice", []):
        if str(m.get("watch", "")).startswith("0x"):
            watch_addrs[m["watch"].lower()] = m.get("label", "")
    for a in app.get("addresses", []):
        if a.get("watch"):
            watch_addrs.setdefault(a["address"].lower(), a.get("role", "")[:30])

    # ── 1) 旧实体组四态 ──
    eps_wei = total * args.state_eps / 100
    groups = []
    for g in app.get("whale_groups", []):
        addrs = [a.lower() for a in g.get("addresses", [])]
        old_v = sum(bal_old.get(a, 0) for a in addrs)
        new_v = sum(bal_new.get(a, 0) for a in addrs)
        net = sum(wnet(a) for a in addrs)
        buys = sum(stats.get(a, {}).get("buy", 0) for a in addrs)
        sells = sum(stats.get(a, {}).get("sell", 0) for a in addrs)
        if new_v <= eps_wei and old_v > eps_wei:
            state = "清仓"
        elif abs(net) <= eps_wei and abs(new_v - old_v) <= eps_wei:
            state = "不变"
        elif net > 0 or new_v > old_v:
            state = "增持"
        else:
            state = "减持"
        groups.append({"label": g.get("label"), "tier": g.get("tier"),
                       "old_share": round(pct(old_v), 3), "cur_share": round(pct(new_v), 3),
                       "win_net_pct": round(pct(net), 3),
                       "win_buy": round(buys / unit, 1), "win_sell": round(sells / unit, 1),
                       "state": state, "n_addr": len(addrs)})

    # ── 2) 新庄候选（双口径） ──
    known = set(old_entity) | set(vaults) | set(watch_addrs) | infra | set(pools) | {ZERO}
    cand_wei = total * args.cand_pct / 100
    cands = []
    cand_set = set()
    for a, v in bal_new.items():
        if a in known or v <= 0:
            continue
        net = wnet(a)
        if v >= cand_wei or net >= cand_wei:
            cand_set.add(a)
            s = stats.get(a, {})
            cands.append({"addr": a,
                          "now_pct": round(pct(v), 3), "old_pct": round(pct(bal_old.get(a, 0)), 3),
                          "win_net_pct": round(pct(net), 3),
                          "via": ("现仓" if v >= cand_wei else "") + ("+" if v >= cand_wei and net >= cand_wei else "")
                                 + ("窗口净增" if net >= cand_wei else ""),
                          "n_buy": s.get("n_buy", 0), "n_sell": s.get("n_sell", 0),
                          "first_ts": iso(s.get("first_ts")), "last_ts": iso(s.get("last_ts"))})
    cands.sort(key=lambda c: -c["now_pct"])

    # 候选画像（in/out 对手方）需要流水
    rows = []
    if args.inc and os.path.exists(args.inc):
        with gzip.open(args.inc, "rt") as f:
            for line in f:
                if line.strip():
                    rows.append(json.loads(line))
        rows.sort(key=lambda r: (r["block"], r["logi"]))
        for c in cands:
            a = c["addr"]
            in_src, out_dst = defaultdict(int), defaultdict(int)
            for r in rows:
                if r["to"].lower() == a:
                    in_src[r["from"].lower()] += int(r["amount"])
                elif r["from"].lower() == a:
                    out_dst[r["to"].lower()] += int(r["amount"])
            c["in_srcs"] = {k: round(v / unit) for k, v in sorted(in_src.items(), key=lambda x: -x[1])[:5]}
            c["out_dsts"] = {k: round(v / unit) for k, v in sorted(out_dst.items(), key=lambda x: -x[1])[:5]}

    # ── 3) 观察哨逐条核查 ──
    sentinels = []
    if not app.get("monitoring_advice"):
        print("NOTE: 无观察哨基线（monitoring_advice 缺失/为空）——简报 U3c 按'无基线'如实声明，本节跳过")
    for m in app.get("monitoring_advice", []):
        a = str(m.get("watch", "")).lower()
        if not a.startswith("0x"):
            sentinels.append({"watch": m.get("watch"), "label": m.get("label"),
                              "note": "非地址型哨兵，人工核查", "triggered": None})
            continue
        s = stats.get(a, {})
        net = wnet(a)
        out_amt = s.get("sell", 0) + s.get("t_out", 0) + s.get("burn", 0)
        mode = m.get("mode", "any_out")
        if mode == "any_out":
            triggered = out_amt > 0
            why = f"窗口转出 {out_amt/unit:,.0f}" if triggered else "窗口内零转出"
        else:
            thr = float(m.get("alert_threshold_pct", 1.0))
            triggered = pct(-net if net < 0 else 0) >= thr
            why = f"窗口净变动 {pct(net):+.3f}% vs 阈值 -{thr}%"
        moves = []
        if rows:
            for r in rows:
                if r["from"].lower() == a or r["to"].lower() == a:
                    d = "OUT" if r["from"].lower() == a else "IN"
                    peer = r["to"].lower() if d == "OUT" else r["from"].lower()
                    moves.append({"t": iso(r.get("ts")), "d": d, "peer": peer,
                                  "amt": round(int(r["amount"]) / unit), "tx": r["tx"]})
                    if len(moves) >= 40:
                        break
        sentinels.append({"watch": a, "label": m.get("label"), "mode": mode,
                          "cur_pct": round(pct(bal_new.get(a, 0)), 3),
                          "win_net_pct": round(pct(net), 4), "n_tx": s.get("n_tx", 0),
                          "triggered": bool(triggered), "why": why, "moves": moves})

    # ── 4) 窗口买卖榜（全窗净变化口径） ──
    net_rank = []
    for a, s in stats.items():
        if a in pools or a in infra or a == ZERO:
            continue
        net = wnet(a)
        if net:
            net_rank.append({"addr": a, "win_net_pct": round(pct(net), 3),
                             "gross_buy": round(s["buy"] / unit), "gross_sell": round(s["sell"] / unit),
                             "tag": old_entity.get(a) or vaults.get(a) or watch_addrs.get(a) or ""})
    buyers = sorted([x for x in net_rank if x["win_net_pct"] > 0], key=lambda x: -x["win_net_pct"])[:15]
    sellers = sorted([x for x in net_rank if x["win_net_pct"] < 0], key=lambda x: x["win_net_pct"])[:15]

    result = {"state_eps_pct": args.state_eps, "cand_pct": args.cand_pct,
              "old_entity_states": groups, "new_whale_candidates": cands,
              "sentinel_checks": sentinels,
              "window_net_buyers": buyers, "window_net_sellers": sellers}
    with open(args.out, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)

    # ── 摘要 ──
    print("=== 旧实体四态 ===")
    for g in groups:
        print(f"  [{g['state']}] {g['label']}: {g['old_share']}% → {g['cur_share']}% (窗口净 {g['win_net_pct']:+}%)")
    print(f"=== 新庄候选（≥{args.cand_pct}%，双口径，共 {len(cands)} 个）===")
    for c in cands[:12]:
        print(f"  {c['addr']} 现{c['now_pct']}% 旧{c['old_pct']}% 窗口净{c['win_net_pct']:+}% [{c['via']}]")
    trig = [s for s in sentinels if s.get("triggered")]
    print(f"=== 观察哨 {len(sentinels)} 条，触发 {len(trig)} 条 ===")
    for s in trig:
        print(f"  ⚠ {s['label']} {s['watch'][:12]}: {s['why']}")
    print("=== 窗口净买/卖 top5 ===")
    for x in buyers[:5]:
        print(f"  买 {x['addr'][:12]} 净{x['win_net_pct']:+}% (毛买{x['gross_buy']}/毛卖{x['gross_sell']}) {x['tag']}")
    for x in sellers[:5]:
        print(f"  卖 {x['addr'][:12]} 净{x['win_net_pct']:+}% (毛买{x['gross_buy']}/毛卖{x['gross_sell']}) {x['tag']}")
    print(f"落盘 {args.out}")


if __name__ == "__main__":
    main()
