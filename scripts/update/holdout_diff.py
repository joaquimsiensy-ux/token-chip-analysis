#!/usr/bin/env python3
"""A10 封存对比器——封存重跑版 vs 全量定案版 analysis-state.json 的实体级 diff。

用途背景：时间封存测试的后半段（前半段=truncate_dataset.py 出截断副本重跑分析）。
对比两份 state 的 whale_groups：实体集合差异 / 成员差异 / 判级差异 / 份额差异表，
回答"只看前 70-80% 历史时识别的实体，在全量数据下是否依然成立"——
  · 封存版实体在全量版有稳定配对且成员/判级一致 → 方法无"后见拟合"嫌疑；
  · 封存版实体在全量版消失（仅封存有）→ 疑似过拟合前段噪音；
  · 全量版实体在封存版缺失（仅全量有）→ 正常（实体可在尾段才形成），但若其建仓
    期明明在封存段内仍没被识别，则是召回问题，人工看备注栏。

实体配对逻辑：label 全等直接配；否则按地址集合贪心配对（交集/较小集 ≥ 0.5 或
Jaccard ≥ 0.3），配不上的进"仅一方"名单。地址统一小写比较。

用法:
  python3 holdout_diff.py --holdout 封存重跑/analysis-state.json \
      --full 全量定案/analysis-state.json [--out holdout_diff.md]
退出码：0=全配对且无判级差异；1=存在未配对实体或判级变化（人工审）。
（来源：A10 小工程件，2026-07-22）"""
import argparse
import datetime
import json
import sys


def grade_of(label, legacy_tier):
    """v5.0 判级=标签前缀（大庄/小庄/离场庄/项目方/刷量）；旧 state 兜底 tier 字段。"""
    for pfx in ("大庄", "小庄", "离场庄", "项目方", "刷量", "狙击集团"):
        if str(label).startswith(pfx):
            return pfx
    return legacy_tier or "?"


def load_groups(path):
    d = json.load(open(path))
    out = []
    for g in d.get("whale_groups") or []:
        out.append({"label": g.get("label", "?"),
                    "tier": grade_of(g.get("label", ""), g.get("tier")),
                    "status": g.get("status", ""),
                    "addrs": {str(x).lower() for x in (g.get("addresses") or [])},
                    "cur": g.get("current_share_pct"),
                    "peak": g.get("peak_share_pct")})
    return d, out


def pair_up(hold, full):
    """贪心配对：label 全等优先，其余按地址重叠度降序。返回 (pairs, 仅hold, 仅full)。"""
    pairs, used_h, used_f = [], set(), set()
    for i, h in enumerate(hold):          # 第一轮：label 全等
        for j, f in enumerate(full):
            if j in used_f:
                continue
            if h["label"] == f["label"]:
                pairs.append((i, j, "label 全等"))
                used_h.add(i)
                used_f.add(j)
                break
    cands = []                            # 第二轮：地址重叠
    for i, h in enumerate(hold):
        if i in used_h or not h["addrs"]:
            continue
        for j, f in enumerate(full):
            if j in used_f or not f["addrs"]:
                continue
            inter = len(h["addrs"] & f["addrs"])
            if not inter:
                continue
            small = min(len(h["addrs"]), len(f["addrs"]))
            jac = inter / len(h["addrs"] | f["addrs"])
            if inter / small >= 0.5 or jac >= 0.3:
                cands.append((inter, jac, i, j))
    for inter, jac, i, j in sorted(cands, reverse=True):
        if i in used_h or j in used_f:
            continue
        pairs.append((i, j, f"地址重叠 {inter} 个(Jaccard {jac:.2f})"))
        used_h.add(i)
        used_f.add(j)
    only_h = [i for i in range(len(hold)) if i not in used_h]
    only_f = [j for j in range(len(full)) if j not in used_f]
    return pairs, only_h, only_f


def fmt_pct(x):
    return "?" if x is None else f"{x:g}%"


def main():
    ap = argparse.ArgumentParser(description="A10 封存对比器（两份 analysis-state 实体 diff）")
    ap.add_argument("--holdout", required=True, help="封存重跑版 analysis-state.json")
    ap.add_argument("--full", required=True, help="全量定案版 analysis-state.json")
    ap.add_argument("--out", default="holdout_diff.md")
    a = ap.parse_args()

    dh, hold = load_groups(a.holdout)
    df, full = load_groups(a.full)
    pairs, only_h, only_f = pair_up(hold, full)
    tier_changes = [(i, j) for i, j, _ in pairs if hold[i]["tier"] != full[j]["tier"]]

    tok = (df.get("token") or {})
    md = [f"# 时间封存测试 diff（{tok.get('symbol', '?')} · {tok.get('chain', '?')}）",
          f"生成 {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%dT%H:%M:%SZ}",
          f"- 封存版：`{a.holdout}`（实体 {len(hold)}）",
          f"- 全量版：`{a.full}`（实体 {len(full)}）",
          f"- 配对 {len(pairs)} / 仅封存有 {len(only_h)} / 仅全量有 {len(only_f)}"
          f" / 判级变化 {len(tier_changes)}",
          "", "## 一、实体集合差异"]
    if only_h:
        md.append("### 仅封存版有（⚠疑似过拟合前段——全量数据下该实体没被定案）")
        for i in only_h:
            h = hold[i]
            md.append(f"- {h['label']}（{h['tier']}，{len(h['addrs'])} 址，"
                      f"cur {fmt_pct(h['cur'])} / peak {fmt_pct(h['peak'])}）")
    if only_f:
        md.append("### 仅全量版有（实体可在尾段形成属正常；若建仓期在封存段内则是召回问题）")
        for j in only_f:
            f = full[j]
            md.append(f"- {f['label']}（{f['tier']}，{len(f['addrs'])} 址，"
                      f"cur {fmt_pct(f['cur'])} / peak {fmt_pct(f['peak'])}）")
    if not only_h and not only_f:
        md.append("- 无（两版实体一一配对）")
    md += ["", "## 二、配对实体明细",
           "| 封存版 | 全量版 | 配对依据 | 判级 | 成员 | current% | peak% |",
           "|---|---|---|---|---|---|---|"]
    for i, j, how in pairs:
        h, f = hold[i], full[j]
        tier = h["tier"] if h["tier"] == f["tier"] else f"**{h['tier']}→{f['tier']}**"
        add = sorted(f["addrs"] - h["addrs"])
        sub = sorted(h["addrs"] - f["addrs"])
        mem = f"{len(h['addrs'])}→{len(f['addrs'])}"
        if add:
            mem += f" (+{len(add)}: {', '.join(x[:10] for x in add[:3])}"
            mem += "…)" if len(add) > 3 else ")"
        if sub:
            mem += f" (-{len(sub)}: {', '.join(x[:10] for x in sub[:3])}"
            mem += "…)" if len(sub) > 3 else ")"
        cur = f"{fmt_pct(h['cur'])}→{fmt_pct(f['cur'])}"
        pk = f"{fmt_pct(h['peak'])}→{fmt_pct(f['peak'])}"
        md.append(f"| {h['label']} | {f['label']} | {how} | {tier} | {mem} | {cur} | {pk} |")
    md += ["", "## 三、结论指引",
           "- 封存版实体全部配对、判级一致、成员仅尾段自然增补 → 聚类判级无后见拟合嫌疑。",
           "- 『仅封存版有』非空或判级降档 → 该实体的定性依赖了尾段之外的想象，人工回查证据链。",
           "- 份额差异本身不是问题（封存点后仓位会变），看的是**实体存在性与成员构成**是否延续。"]
    with open(a.out, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    bad = bool(only_h or tier_changes)
    print(f"[{'REVIEW' if bad else 'OK'}] 配对 {len(pairs)} / 仅封存 {len(only_h)} / "
          f"仅全量 {len(only_f)} / 判级变化 {len(tier_changes)} -> {a.out}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
