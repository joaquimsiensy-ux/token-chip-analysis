#!/usr/bin/env python3
"""第二遍重放：merged.csv + camps.json → 每日阵营占比序列 + 实体序列（供 standard_charts 三图与演变解读用）。
来源：PING(Base) 分析会话实战产物，2026-07-17（v2.26 收编参数化）。

用法：python3 replay_pass2.py camps.json [--data-dir data]
camps.json 格式：{"camps": {"阵营名": [地址...]}, "entities": {"实体标签": [地址...]}}
  阵营互斥（一地址只归一个阵营，含"流动性池/锁仓/销毁"等单列阵营）；实体可与阵营重叠（用于图2实体线）。
分母：{data-dir}/replay_stats.json 的 mint_total_wei（replay_pass1 输出的总铸量口径）。
输出：{data-dir}/camp_series.json {"dates":[...], "阵营名":[pct...], "散户":[...]}、{data-dir}/entity_series.json
  散户 = 100 − 已知阵营合计。
"""
import csv, json, argparse
from collections import defaultdict

Z = '0x0000000000000000000000000000000000000000'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("camps", help="camps.json（阵营与实体定义）")
    ap.add_argument("--data-dir", default="data")
    a = ap.parse_args()
    spec = json.load(open(a.camps))
    total = int(json.load(open(f"{a.data_dir}/replay_stats.json"))["mint_total_wei"])
    camps = {k: set(x.lower() for x in v) for k, v in spec.get("camps", {}).items()}
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

    def snap():
        dates.append(cur_day)
        known = 0
        for c in camps:
            v = camp_bal[c] / total * 100
            series[c].append(round(v, 4))
            known += v
        series["散户"].append(round(max(0, 100 - known), 4))
        for e in ents:
            eseries[e].append(round(ent_bal[e] / total * 100, 4))

    def apply(ad, delta):
        if ad == Z:
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
    json.dump({"dates": dates, **{k: v for k, v in series.items()}}, open(f"{a.data_dir}/camp_series.json", "w"))
    json.dump({"dates": dates, **{k: v for k, v in eseries.items()}}, open(f"{a.data_dir}/entity_series.json", "w"))
    print(f"天数={len(dates)} 阵营={list(camps)+['散户']} 实体={list(ents)}")
    print("末日阵营占比:", {k: series[k][-1] for k in series})
    print("末日实体占比:", {k: eseries[k][-1] for k in eseries})


if __name__ == "__main__":
    main()
