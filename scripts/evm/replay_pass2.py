#!/usr/bin/env python3
"""第二遍重放：merged.csv + camps.json → 每日阵营占比序列 + 实体序列（供 standard_charts 三图与演变解读用）。
来源：PING(Base) 分析会话实战产物，2026-07-17（v2.26 收编参数化）。

用法：python3 replay_pass2.py camps.json [--data-dir data]
camps.json 格式：{"camps": {"阵营名": [地址...]}, "entities": {"实体标签": [地址...]}}
  阵营互斥（一地址只归一个阵营，含"流动性池/锁仓/销毁"等单列阵营）；实体可与阵营重叠（用于图2实体线）。
分母：{data-dir}/replay_stats.json 的 mint_total_wei（replay_pass1 输出的总铸量口径）。
输出：{data-dir}/camp_series.json {"dates":[...], "阵营名":[pct...], "散户":[...]}、{data-dir}/entity_series.json
  散户 = 100 − 已知阵营合计。
烧毁处理（v3.9 修复）：烧入 0x0 的量自动计入"销毁"阵营（camps.json 无需配置 0x0；未配置"销毁"
  阵营且确有烧毁时自动增列）。修复前烧毁量残留在散户残差里（SQD 案散户虚高 2.65pp）。
  mint（from=0x0）不记账；全程无烧毁时"销毁"曲线不输出。0xdead 类烧毁地址仍需在 camps.json 显式归入"销毁"。
"""
import csv, json, argparse, os, sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from camp_spec import validate_camp_spec

Z = '0x0000000000000000000000000000000000000000'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("camps", help="camps.json（阵营与实体定义）")
    ap.add_argument("--data-dir", default="data")
    a = ap.parse_args()
    stats_path = f"{a.data_dir}/replay_stats.json"
    try:
        stats = json.load(open(stats_path))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"[camp-series] {stats_path} 不可读或 JSON 损坏: {exc}——先重跑"
              " pass1 再跑 pass2", file=sys.stderr)
        sys.exit(2)
    # 信任边界：pass2 消费 pass1 的 gate_pass，不在此重算 merged.csv；防篡改由
    # camp-series provenance 对 replay_stats 的绑定及下游 supply_truth 哈希链兜底。
    gate_pass = stats.get("gate_pass") if isinstance(stats, dict) else None
    if type(gate_pass) is not bool:
        print(f"[camp-series] {stats_path} schema 故障：gate_pass 必须是布尔值，"
              f"实得 {gate_pass!r}——先重跑 pass1 再跑 pass2", file=sys.stderr)
        sys.exit(2)
    if gate_pass is False:
        print(f"[camp-series] {stats_path} gate_pass=false（pass1 对账 gate 未通过）"
              "——禁止编译正式阵营/实体序列", file=sys.stderr)
        sys.exit(4)
    try:
        total = int(stats["mint_total_wei"])
    except (KeyError, TypeError, ValueError) as exc:
        print(f"[camp-series] {stats_path} schema 故障：mint_total_wei 缺失或非法: "
              f"{exc}——先重跑 pass1 再跑 pass2", file=sys.stderr)
        sys.exit(2)
    spec = json.load(open(a.camps))
    # F-05：互斥校验（同营内+跨营重复硬拒 exit 2）在 set() 化之前、规范化之后做；
    # 校验实现四入口共享（scripts/lib/camp_spec.py），禁再各自手写
    camps_valid = validate_camp_spec(spec.get("camps", {}), chain_family="evm",
                                     source_label=a.camps)
    camps = {k: set(v) for k, v in camps_valid.items()}
    camps.setdefault("销毁", set())
    ents = {k: set(x.lower() for x in v) for k, v in spec.get("entities", {}).items()}
    addr2camp = {}
    for c, s in camps.items():
        for ad in s:
            addr2camp[ad] = c
    addr2ent = {}
    for e, s in ents.items():
        for ad in s:
            addr2ent.setdefault(ad, []).append(e)

    bal = defaultdict(int)
    camp_bal = defaultdict(int)
    ent_bal = defaultdict(int)
    dates = []
    series = defaultdict(list)
    eseries = defaultdict(list)
    cur_day = None

    # 【3.36 分母口径修复，与 replay_duck 同步】旧版固定用 mint_total（全史铸造总量）作分母，
    # 会把**尚未铸造**的代币提前计入残差桶「散户」——标的后期一旦大额增发，早期散户占比被
    # 系统性虚高，且各阵营加总仍是 100%，属静默的传播级错误（IQ(ETH) 2026-07-26 实证：
    # 2025-09 单月增发 181%，该月 25 日散户被算成 55.6%，真值 11.28%，虚高 44pp）。
    # 修复=分母改用当期净供应；旧口径用 CHIP_LEGACY_CAMP_DENOM=1 取回。
    legacy = os.environ.get("CHIP_LEGACY_CAMP_DENOM") == "1"
    st = {"supply": 0}
    stack = list(camps) if legacy else [c for c in camps if c != "销毁"]

    burn_pct = []

    def snap():
        dates.append(cur_day)
        denom = total if legacy else st["supply"]
        if denom <= 0:
            for c in stack:
                series[c].append(0.0)
            series["散户"].append(0.0)
            for e in ents:
                eseries[e].append(0.0)
            burn_pct.append(0.0)
            return
        known = 0
        for c in stack:
            v = camp_bal[c] / denom * 100
            series[c].append(round(v, 4))
            known += v
        series["散户"].append(round(max(0, 100 - known), 4))
        for e in ents:
            eseries[e].append(round(ent_bal[e] / denom * 100, 4))
        burn_pct.append(round(camp_bal["销毁"] / denom * 100, 4))

    def apply(ad, delta):
        if ad == Z:
            # Z 转出(delta<0)=mint→供应增；转入 Z(delta>0)=burn→供应减
            st["supply"] -= delta
            if delta > 0:  # 烧入 0x0 = 销毁；mint（Z 为 from、delta<0）不记账
                camp_bal["销毁"] += delta
            return
        bal[ad] += delta
        c = addr2camp.get(ad)
        if c:
            camp_bal[c] += delta
        for e in addr2ent.get(ad, []):
            ent_bal[e] += delta

    with open(f"{a.data_dir}/merged.csv") as f:
        r = csv.reader(f)
        next(r)
        for row in r:
            blk, ts, tx, li, frm, to, val = row
            day = ts[:10] if ts else None
            if day and day != cur_day:
                if cur_day is not None:
                    snap()
                cur_day = day
            v = int(val)
            apply(frm, -v)
            apply(to, v)
    snap()
    if "销毁" in series and all(v == 0 for v in series["销毁"]):
        del series["销毁"]
    out = {"dates": dates, **{k: v for k, v in series.items()}}
    if not legacy:                       # 与 replay_duck 输出契约保持逐字段一致
        out["_meta"] = {"denominator": "current_net_supply",
                        "note": "分母=当期净供应(累计mint−累计burn)；burn_cum_pct 不参与堆叠"}
        out["burn_cum_pct"] = burn_pct
    json.dump(out, open(f"{a.data_dir}/camp_series.json", "w"))
    json.dump({"dates": dates, **{k: v for k, v in eseries.items()}}, open(f"{a.data_dir}/entity_series.json", "w"))
    # F-04：producer sidecar——序列落盘即同步写 provenance（spec/输入/输出 sha 绑定），
    # state_from_facts --series-source 只认带 sidecar 的序列（camp_series_provenance.py）
    from camp_series_provenance import write_series_sidecar
    _den = "mint_total_legacy" if legacy else "current_net_supply"
    _sidecar_inputs = {"replay_stats": f"{a.data_dir}/replay_stats.json"}
    _fb = f"{a.data_dir}/balances_final.json"
    if not os.path.exists(_fb):
        # F-C6：缺终态快照当场硬拒（与缺 camps 同口径 fail-loud），不许静默少绑
        # sidecar 拖到编译期才炸——balances_final 与 replay_stats 同为 pass1 四件产物
        print(f"[camp-series] 缺 {_fb}（pass1 终态快照，末点对账的锚）——先跑"
              f" pass1/replay_duck 再跑 pass2", file=sys.stderr)
        sys.exit(2)
    write_series_sidecar(f"{a.data_dir}/camp_series.json",
                         producer="scripts/evm/replay_pass2.py",
                         series_format="evm-dict", denominator=_den,
                         camps_spec_path=a.camps,
                         final_balances_path=_fb,
                         inputs=_sidecar_inputs)
    write_series_sidecar(f"{a.data_dir}/entity_series.json",
                         producer="scripts/evm/replay_pass2.py",
                         series_format="evm-entity-dict", denominator=_den,
                         camps_spec_path=a.camps, inputs=_sidecar_inputs)
    print(f"天数={len(dates)} 阵营={[k for k in series]} 实体={list(ents)}")
    print("末日阵营占比:", {k: series[k][-1] for k in series})
    print("末日实体占比:", {k: eseries[k][-1] for k in eseries})


if __name__ == "__main__":
    main()
