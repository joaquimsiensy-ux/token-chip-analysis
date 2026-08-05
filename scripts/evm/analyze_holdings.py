#!/usr/bin/env python3
"""筹码核心分析：对账 / CEX 净流 / 金库流出账本 / 大额边 / 关键地址余额时序 / 吸筹普查。
来源：OPN(BSC) 分析会话实战产物, 2026-07。

用法（工作目录含 config.json 与扫链产物）：
  python3 analyze_holdings.py <chain>            # 全套分析（chain 对应 <chain>_part_*.csv）
  python3 analyze_holdings.py <chain> --eth-csv  # 该链数据来自 eth_transfers.csv（Etherscan 格式，自带 ts）

产物：<chain>_cex_daily.json、<chain>_edges.json、<chain>_key_balances.json，其余打印到 stdout。
分析纪律：对账 10/10 不过不许下结论；金库要同时统计流入（做市回笼会让余额对不上）；
吸筹普查标准=累计提币≥总量0.02%且现持≥提币量60%（链上唯一能证实的囤仓形态）。
"""
import csv, json, glob, os, sys, bisect, datetime
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "labels"))
try:
    from labels_resolver import LabelResolver, append_misses   # 批量标签库共享内核（默认启用，--no-labels 关闭）
except Exception:
    LabelResolver = None
    append_misses = None
try:
    from labels_resolver import blind_serial_env, seal_serial_hits, blind_notice   # A2–A3 盲化、A4 揭盲
except Exception:
    blind_serial_env = lambda: False
    seal_serial_hits = blind_notice = None

DIR = os.getcwd()
CFG = json.load(open(os.path.join(DIR, "config.json")))
DEC = 10 ** CFG.get("decimals", 18)
Z = "0x0000000000000000000000000000000000000000"

LABELS = {}
for group in ("cex_wallets", "team_wallets", "mm_wallets"):
    for a, v in CFG.get(group, {}).items():
        if a.startswith("0x") and "|" in v:
            typ, name = v.split("|", 1)
            LABELS[a.lower()] = (name, typ)
CEX_TYPES = {t for _, t in LABELS.values() if t.startswith("cex_")}

def load(chain, eth_csv=False):
    rows, seen = [], set()
    if eth_csv:
        for r in csv.DictReader(open(os.path.join(DIR, "eth_transfers.csv"))):
            rows.append((int(r["block"]), r["tx"], 0, r["from"].lower(), r["to"].lower(), int(r["value_raw"]), int(r["ts"])))
        return rows, None
    for p in sorted(glob.glob(os.path.join(DIR, f"{chain}_part_*.csv"))):
        for line in open(p):
            parts = line.strip().split(",")
            if len(parts) != 6 or parts[0] == "block":
                continue
            k = (parts[1], parts[2])
            if k in seen: continue
            seen.add(k)
            rows.append((int(parts[0]), parts[1], int(parts[2]), parts[3].lower(), parts[4].lower(), int(parts[5]), None))
    rows.sort(key=lambda r: (r[0], r[2]))
    anchors = json.load(open(os.path.join(DIR, f"{chain}_ts_anchors.json")))
    ks = sorted(int(k) for k in anchors); vs = [anchors[str(k)] for k in ks]
    def ts_fn(b):
        i = max(0, min(bisect.bisect_right(ks, b) - 1, len(ks) - 2))
        return vs[i] + (vs[i+1] - vs[i]) * (b - ks[i]) / (ks[i+1] - ks[i])
    return rows, ts_fn

def day(t): return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y-%m-%d")

def main(chain, eth_csv):
    rows, ts_fn = load(chain, eth_csv)
    if eth_csv:
        get_ts = lambda r: r[6]
    else:
        assert ts_fn is not None
        get_ts = lambda r: ts_fn(r[0])
    print(f"{chain} transfers: {len(rows)}")

    bal = defaultdict(int)
    for r in rows:
        bal[r[3]] -= r[5]; bal[r[4]] += r[5]

    # ---- 1. 对账（若有 GMGN 数据）----
    gm_path = os.path.join(DIR, f"gmgn/{chain}_holders_top100.json")
    if os.path.exists(gm_path):
        print("\n=== 对账 vs GMGN top10（必须 10/10 OK）===")
        for h in (json.load(open(gm_path)).get("list") or [])[:10]:
            a = h["address"].lower(); g = float(h["balance"]); rb = bal.get(a, 0) / DEC
            print(f"{a[:14]} gmgn={g:,.0f} rebuilt={rb:,.0f} {'OK' if abs(g-rb) < max(g*0.01, 1000) else 'MISMATCH!'}")

    # ---- 2. mint/burn 闭合 ----
    mint = sum(r[5] for r in rows if r[3] == Z); burn = sum(r[5] for r in rows if r[4] == Z)
    print(f"\n=== 铸烧: mint={mint/DEC/1e6:.4f}M burn={burn/DEC/1e6:.4f}M net={(mint-burn)/DEC/1e6:.4f}M（跨链型需两链净和=总量）===")

    # 批量标签库兜底：config LABELS（本次分析人工核验）优先；库直接命中作补充。
    # cex→cex_lib 并入 CEX 净流口径；exclude 设施/locker→不再算 other（不进大额边/吸筹普查/聚类输入）
    resv = None
    if LabelResolver is not None and "--no-labels" not in sys.argv:
        resv = LabelResolver(chain)
        if not resv.warn_if_degraded():     # 降级=显式 stderr 警告（"没命中"≠"没加载"，v4）
            CEX_TYPES.add("cex_lib")
            print(f"批量标签库兜底: {chain} 表 {len(resv.table)} 条已加载（--no-labels 可关闭）")
    elif LabelResolver is None:
        print("[labels][degraded_mode] labels_resolver 导入失败——本次运行无标签兜底", file=sys.stderr)

    def typ(a):
        t = LABELS.get(a, ("", ""))[1]
        if t: return t
        if resv is not None:
            r = resv.get(a)
            if r and not r["cross_chain"]:
                if r["category"] == "cex": return "cex_lib"
                if r["category"] == "locker": return "locker_lib"
                if r["tier"] == "exclude": return "infra_lib"
        return "other"

    # ---- 3. 每日 CEX 净流 ----
    daily = defaultdict(lambda: defaultdict(float))
    for r in rows:
        ft, tt = typ(r[3]), typ(r[4])
        d = day(get_ts(r)); vm = r[5] / DEC / 1e6
        if tt in CEX_TYPES and ft not in CEX_TYPES and ft != "zero" and r[3] != Z:
            daily[d]["in"] += vm; daily[d]["in_" + tt] += vm
        if ft in CEX_TYPES and tt not in CEX_TYPES and r[4] != Z:
            daily[d]["out"] += vm; daily[d]["out_" + ft] += vm
    json.dump({d: dict(v) for d, v in sorted(daily.items())},
              open(os.path.join(DIR, f"{chain}_cex_daily.json"), "w"), indent=1)
    print("\n=== 每周 CEX 净流（百万枚，正=充入=潜在卖压）===")
    wk_in, wk_out = defaultdict(float), defaultdict(float)
    for d, v in daily.items():
        wk = d[:8] + "W" + str((int(d[8:10]) - 1) // 7 + 1)
        wk_in[wk] += v.get("in", 0); wk_out[wk] += v.get("out", 0)
    for wk in sorted(set(wk_in) | set(wk_out)):
        print(f"{wk}: in={wk_in[wk]:8.2f} out={wk_out[wk]:8.2f} net={wk_in[wk]-wk_out[wk]:+8.2f}")

    # ---- 4. 金库账本（team_wallets 中 type=team_treasury 的地址）----
    for tb, (name, t) in LABELS.items():
        if t != "team_treasury": continue
        tin = sum(r[5] for r in rows if r[4] == tb) / DEC / 1e6
        tout = sum(r[5] for r in rows if r[3] == tb) / DEC / 1e6
        print(f"\n=== 金库 {name} {tb}: 流入 {tin:.2f}M 流出 {tout:.2f}M 余 {bal.get(tb,0)/DEC/1e6:.2f}M ===")
        for r in rows:
            if r[3] == tb and r[5] > 0.05 * DEC * 1e6:
                lbl = LABELS.get(r[4], (r[4][:16], ""))[0]
                print(f"{day(get_ts(r))}  -> {lbl:<26} {r[5]/DEC/1e6:8.3f}M  {r[1][:20]}")
        for r in rows:
            if r[4] == tb and r[5] > 0.05 * DEC * 1e6 and r[3] != Z:
                print(f"{day(get_ts(r))}  <- {r[3][:16]} 回流 {r[5]/DEC/1e6:8.3f}M  {r[1][:20]}")

    # ---- 5. 非CEX 大额边（聚类输入）----
    deg = defaultdict(set); edges = defaultdict(float)
    for r in rows:
        deg[r[3]].add(r[4]); deg[r[4]].add(r[3])
    thresh = CFG.get("total_supply_m", 1000) * DEC * 1e6 / 10000  # 万分之一总量
    for r in rows:
        if typ(r[3]) == "other" and typ(r[4]) == "other" and r[5] > thresh and r[3] != Z and r[4] != Z:
            edges[(r[3], r[4])] += r[5] / DEC / 1e6
    json.dump([{"from": f, "to": t, "m": v} for (f, t), v in edges.items()],
              open(os.path.join(DIR, f"{chain}_edges.json"), "w"))
    print(f"\n=== 非CEX大额边 {len(edges)} 条, top20 ===")
    for (f, t), v in sorted(edges.items(), key=lambda x: -x[1])[:20]:
        print(f"{f[:14]} -> {t[:14]}  {v:8.3f}M  (deg {len(deg[f])}/{len(deg[t])})")

    # ---- 6. 吸筹普查：大额提币且囤着 ----
    wd = defaultdict(int)   # 从CEX提币累计
    for r in rows:
        if typ(r[3]) in CEX_TYPES and typ(r[4]) == "other" and r[4] != Z:
            wd[r[4]] += r[5]
    floor = CFG.get("total_supply_m", 1000) * DEC * 1e6 * 0.0002  # 总量0.02%
    print("\n=== 吸筹普查：累计提币≥总量0.02% 且现持≥提币60% ===")
    hits = 0
    for a, w in sorted(wd.items(), key=lambda x: -x[1]):
        if w >= floor and bal.get(a, 0) >= w * 0.6:
            print(f"{a}  提币 {w/DEC/1e6:.3f}M  现持 {bal[a]/DEC/1e6:.3f}M")
            hits += 1
    print(f"命中 {hits} 个（0 = 链上无囤仓型吸筹；注意所内吸筹不可见，措辞要留边界）")

    # ---- 7. 关键地址每日余额时序（画图用）----
    KEY = [a for a in LABELS if LABELS[a][1].startswith(("team", "mm", "cex"))]
    snap = defaultdict(dict); bal2 = defaultdict(int); cur = None
    for r in rows:
        d = day(get_ts(r))
        if cur and d != cur:
            for a in KEY: snap[cur][a] = bal2.get(a, 0) / DEC
        cur = d
        bal2[r[3]] -= r[5]; bal2[r[4]] += r[5]
    if cur:
        for a in KEY: snap[cur][a] = bal2.get(a, 0) / DEC
    json.dump(snap, open(os.path.join(DIR, f"{chain}_key_balances.json"), "w"))
    print(f"\nkey_balances 保存（{len(KEY)} 地址）")

    # ---- 8. 批量标签库扫描（v4）：serial 惯犯高亮 + 定性风险 + candidate/unknown 提示
    #      + 设施/桶类（balance_policy）提示 + 实战 miss 队列 + labels_meta 落盘 ----
    if resv is not None and resv.table:
        top = [(a, b) for a, b in sorted(bal.items(), key=lambda x: -x[1])[:200] if b > 0]
        blind = blind_serial_env()   # A2–A3：CHIP_BLIND_SERIAL=1 盲化惯犯层输出
        serials, warns, cands, unknowns, infra = [], [], [], [], []
        for a, b in top:
            r = resv.get(a)
            if not r or r["cross_chain"]: continue
            rp = resv.risk_partition(r)
            if r["serial"]:
                serials.append((a, b, r))
                if blind:
                    continue   # 盲化：serial 行不进任何段（其 serial-offender 旗标会经 RISK 段泄露）
            if rp["definitive"]:
                warns.append((a, b, r, rp))
            if rp["candidate"]:
                cands.append((a, b, r, rp))
            if rp["unknown"]:
                unknowns.append((a, b, r, rp))
            if r["balance_policy"] in ("exclude", "bucket") and not rp["definitive"]:
                infra.append((a, b, r))
        if blind and seal_serial_hits is not None:
            # A2–A3 盲化、A4 揭盲：详情封存案目录，主输出恒定提示（有无命中不可区分）
            sealed_path = seal_serial_hits(
                [{'chain': chain, 'address': a, 'balance_M': round(b / DEC / 1e6, 3),
                  **{k: v for k, v in r.items()}} for a, b, r in serials],
                DIR, f"{CFG.get('symbol') or os.path.basename(DIR)} analyze_holdings")
            blind_notice(sealed_path)
        elif serials:
            print("\n=== 🚨 惯犯庄家命中（SERIAL 级——历史分析实锤收割集团，立即调案源比对手法）===")
            for a, b, r in serials:
                print(f"{a}  持 {b/DEC/1e6:.3f}M  {r['name'][:60]} | {r.get('evidence','')[:60]}")
        if warns:
            print("\n=== ⚠ 批量标签库定性风险命中（RISK 级，必须写进报告）===")
            for a, b, r, rp in warns:
                print(f"{a}  持 {b/DEC/1e6:.3f}M  {r['name'][:44]}  risk:{'|'.join(rp['definitive'])}")
        else:
            print("\n批量标签库定性风险扫描: top200 持仓无命中")
        if cands:
            print("=== 批量标签库候选风险命中（CANDIDATE 级——社区单源，降权提示不作定性）===")
            for a, b, r, rp in cands[:10]:
                print(f"{a}  持 {b/DEC/1e6:.3f}M  {r['name'][:44]}  risk:{'|'.join(rp['candidate'])}")
        if unknowns:
            print("=== 批量标签库未识别旗标命中（UNKNOWN 级——人工核验后扩白名单或修数据）===")
            for a, b, r, rp in unknowns[:10]:
                print(f"{a}  持 {b/DEC/1e6:.3f}M  {r['name'][:44]}  risk:{'|'.join(rp['unknown'])}")
        if infra:
            print("=== 批量标签库设施/桶类命中（balance_policy=exclude 剔除 / bucket 单列桶）===")
            for a, b, r in infra[:15]:
                print(f"{a}  持 {b/DEC/1e6:.3f}M  {r['name'][:44]}  <{r['category']}|{r['balance_policy']}>")

        # 实战 miss 队列（v4）：top50 持仓未命中库 → 落盘（跨 token 反复出现的未命中大户
        # 是 MM/基金/设施的高概率候选，人工审核后回填 manual 层）
        if append_misses is not None:
            miss = [(a, round(b / DEC / 1e6, 3), "top50 持仓未命中")
                    for a, b in top[:50] if resv.get(a) is None]
            token_tag = CFG.get("symbol") or os.path.basename(DIR)
            n_miss = append_misses(chain, miss, f"{token_tag} holdings")
            if n_miss:
                print(f"\n实战 miss 队列: 新记 {n_miss} 个未命中 top 持仓（references/labels/miss-queue/{chain}.csv）")

        # labels_meta 落盘：本次分析用的标签库版本/行数/命中统计，产物可审计（v4）
        json.dump(resv.meta(), open(os.path.join(DIR, f"{chain}_labels_meta.json"), "w"),
                  ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main(sys.argv[1], "--eth-csv" in sys.argv)
