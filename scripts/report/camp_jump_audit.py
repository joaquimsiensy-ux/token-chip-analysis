#!/usr/bin/env python3
"""camp_jump_audit.py — 阵营序列骤变点清单（骤变归因义务的机械供给侧）。

背景：PYTHIA 案阵营序列里"历史大户单日 -12pp"“+7.2pp”两个强信号都到过分析者眼前、
都无强制处置义务兜住，W1 波次因此两度漏检（2026-08-01 复盘措施 3）。本脚本把
"发现骤变点"机械化：序列生成后必跑，输出待归因清单——逐条归因到具体实体/地址群
（写入 facts）是 −2/A3 的判断活；无法归因的点必须在报告"局限性"显式列出。

输入两种 schema 自动识别：
  {"points": [{"date": "...", "<阵营>": pct, ...}]}   案序列（camp-share-series/v1）
  {"dates": [...], "series": {"<阵营>": [...]}}       引擎 schema（figures_from_facts fig1）
  裸 list [{date, ...}] 亦可（analysis-state camp_share_series）。

用法：python3 camp_jump_audit.py <序列.json> [--threshold 3.0] [--out camp_jump_audit.json]
退出码：0=跑完（有无骤变都算，requires_attribution 字段表达）；1=输入解析失败。
"""
import argparse
import json
import sys


def load_points(path):
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    if isinstance(d, dict) and "points" in d:
        rows = d["points"]
    elif isinstance(d, dict) and "dates" in d and "series" in d:
        rows = [{"date": dt, **{c: v[i] for c, v in d["series"].items()}}
                for i, dt in enumerate(d["dates"])]
    elif isinstance(d, list):
        rows = d
    else:
        raise ValueError("无法识别的序列 schema（需 points / dates+series / 裸 list）")
    if not rows:
        raise ValueError("序列为空")
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("series", help="阵营序列 JSON 路径")
    ap.add_argument("--threshold", type=float, default=3.0, help="单日 |Δ| ≥ 此百分点即骤变（默认 3pp）")
    ap.add_argument("--out", default="camp_jump_audit.json")
    a = ap.parse_args()

    try:
        rows = load_points(a.series)
    except Exception as e:
        print(f"[camp_jump_audit] 输入解析失败: {e}", file=sys.stderr)
        return 1

    camps = [k for k in rows[0] if k != "date"]
    jumps = []
    for prev, cur in zip(rows, rows[1:]):
        for c in camps:
            v0, v1 = prev.get(c), cur.get(c)
            if v0 is None or v1 is None:
                continue
            delta = float(v1) - float(v0)
            if abs(delta) >= a.threshold:
                jumps.append({"date": cur["date"], "camp": c, "delta_pp": round(delta, 2),
                              "from_pct": round(float(v0), 2), "to_pct": round(float(v1), 2),
                              "attribution": None})
    jumps.sort(key=lambda j: -abs(j["delta_pp"]))
    report = {
        "schema": "camp-jump-audit/v1",
        "source": a.series,
        "threshold_pp": a.threshold,
        "points": len(rows),
        "jumps": jumps,
        "requires_attribution": bool(jumps),
        "note": "每条骤变必须归因到具体实体/地址群（attribution 由判断层回填进 facts）；"
                "无法归因的点必须在报告局限性显式列出（2026-08-01 W1 复盘措施 3）。",
    }
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    print(f"[camp_jump_audit] {len(rows)} 点 / 骤变 {len(jumps)} 条（|Δ|≥{a.threshold}pp）→ {a.out}")
    for j in jumps[:20]:
        print(f"  {j['date']}  {j['camp']:<8} {j['delta_pp']:+7.2f}pp  ({j['from_pct']}→{j['to_pct']})")
    if len(jumps) > 20:
        print(f"  …另 {len(jumps) - 20} 条见输出文件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
