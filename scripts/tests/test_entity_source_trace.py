#!/usr/bin/env python3
"""entity_source_trace 契约测试（离线合成数据，不依赖真库）。

覆盖（schema references/scan-schemas.md §4；PYTHIA 真库锚点另见 fixtures/pythia_anchors.json）：
  1. mint 直达 → PROVEN_ORIGIN/mint 100%
  2. 标签边界 → BOUNDARY/cex_confirmed（evidence=label_confirmed）
  3. pro-rata 两来源 6:4 → 终点按比例、direct_upstream 准确
  4. data_gap：上游凭空转出 → UNRESOLVED/data_gap
  5. 深度上限：12 层链 → UNRESOLVED/depth_limit
  6. 回环 → UNRESOLVED/same_slot_scc（保守归未决）
  7. 实体内部收缩：内部边不计流入
  8. 设施启发式（降门槛合成）→ UNRESOLVED/facility_candidate 支路停
  9. 全实体两锚点 Σ=100% 闭合
用法：python3 scripts/tests/test_entity_source_trace.py   退出码 0=PASS / 1=FAIL
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "report", "entity_source_trace.py")
FAILS = []
TOTAL = 10 ** 12
Z = "0x0000000000000000000000000000000000000000"


def check(name, cond):
    if not cond:
        FAILS.append(name)
        print(f"FAIL  {name}")
    else:
        print(f"ok    {name}")


def day(n):
    return n * 86400


def main():
    d = tempfile.mkdtemp(prefix="trace_test_")
    E = []
    # 1. mint 直达
    E.append((day(1), Z, "A1", 100))
    # 2. 标签边界
    E.append((day(1), Z, "CEXL", 500))
    E.append((day(2), "CEXL", "A2", 100))
    # 3. pro-rata 6:4，上游全 mint
    E.append((day(1), Z, "F1", 60))
    E.append((day(1), Z, "F2", 40))
    E.append((day(3), "F1", "A3", 60))
    E.append((day(3), "F2", "A3", 40))
    # 4. data_gap：GAP 凭空转出
    E.append((day(4), "GAP", "A4", 100))
    # 5. 12 层链 D12→…→D1→A5
    E.append((day(1), Z, "D12", 100))
    for i in range(12, 1, -1):
        E.append((day(14 - i), f"D{i}", f"D{i-1}", 100))
    E.append((day(13), "D1", "A5", 100))
    # 6. 回环：B6←mint 100、B6←A6 50（回流）、B6→A6 150
    E.append((day(1), Z, "B6", 100))
    E.append((day(2), "B6", "A6", 60))
    E.append((day(3), "A6", "B6", 50))
    E.append((day(4), "B6", "A6", 90))
    # 7. 实体内部收缩：mint→B7→A7（B7→A7 是内部边）
    E.append((day(1), Z, "B7", 100))
    E.append((day(2), "B7", "A7", 100))
    # 8. 设施启发式（门槛降为 5）：FAC 5 入 5 出
    for i in range(5):
        E.append((day(1), Z, f"FIN{i}", 20))
        E.append((day(2), f"FIN{i}", "FAC", 20))
    for i in range(4):
        E.append((day(3), "FAC", f"FOUT{i}", 1))
    E.append((day(3), "FAC", "A8", 96))

    ep = os.path.join(d, "edges.jsonl")
    with open(ep, "w", encoding="utf-8") as f:
        for ts, frm, to, amt in E:
            f.write(json.dumps([ts, 0, frm, to, amt]) + "\n")
    with open(os.path.join(d, "entities.json"), "w") as f:
        json.dump({"e1": ["A1"], "e2": ["A2"], "e3": ["A3"], "e4": ["A4"],
                   "e5": ["A5"], "e6": ["A6"], "e7": ["A7", "B7"], "e8": ["A8"]}, f)
    with open(os.path.join(d, "labels.json"), "w") as f:
        json.dump({"CEXL": {"kind": "cex", "name": "TestCEX"}}, f)

    out = os.path.join(d, "ledger.json")
    p = subprocess.run([sys.executable, SCRIPT, "--edges-sol", ep,
                        "--total-supply", str(TOTAL),
                        "--entity-file", os.path.join(d, "entities.json"),
                        "--labels-file", os.path.join(d, "labels.json"),
                        "--facility-min-degree", "5", "--prune-pct", "0.001",
                        "--out", out], capture_output=True, text=True)
    check("主场景 exit 0", p.returncode == 0)
    if p.returncode != 0:
        print(p.stdout, p.stderr)
        return finish()
    r = json.load(open(out))
    ents = {e["entity_id"]: e for e in r["entities"]}

    def peak_comp(eid):
        return {(c["kind"], c["subkind"]): c["pct_of_anchor"]
                for c in ents[eid]["anchors"]["peak"]["composition"]}

    c1 = peak_comp("e1")
    check("mint 直达 100%", c1.get(("PROVEN_ORIGIN", "mint")) == 100.0)
    c2 = peak_comp("e2")
    check("标签 CEX 边界 100%", c2.get(("BOUNDARY", "cex_confirmed")) == 100.0)
    ev2 = ents["e2"]["anchors"]["peak"]["composition"][0]["evidence_level"]
    check("标签边界 evidence=label_confirmed", ev2 == "label_confirmed")
    c3 = peak_comp("e3")
    check("pro-rata 6:4 终点 mint 100%", c3.get(("PROVEN_ORIGIN", "mint")) == 100.0)
    up3 = {u["addr"]: u["pct_of_anchor"] for u in ents["e3"]["anchors"]["peak"]["direct_upstream"]}
    check("direct_upstream 6:4 准确", up3.get("F1") == 60.0 and up3.get("F2") == 40.0)
    c4 = peak_comp("e4")
    check("data_gap 100%", c4.get(("UNRESOLVED", "data_gap")) == 100.0)
    c5 = peak_comp("e5")
    check("深度上限 → depth_limit", ("UNRESOLVED", "depth_limit") in c5)
    c6 = peak_comp("e6")
    check("回环 → same_slot_scc 出现", ("UNRESOLVED", "same_slot_scc") in c6)
    c7 = peak_comp("e7")
    check("实体内部收缩：终点 mint 100%（内部边不计）", c7.get(("PROVEN_ORIGIN", "mint")) == 100.0)
    check("实体内部收缩：进货单只有 mint 一家",
          len(ents["e7"]["anchors"]["peak"]["direct_upstream"]) == 1)
    c8 = peak_comp("e8")
    check("设施启发式支路停 → facility_candidate", ("UNRESOLVED", "facility_candidate") in c8)
    ok_close = all(abs(e["closure_check"]["peak_sum_pct"] - 100.0) <= 0.5 for e in r["entities"])
    check("全实体峰值锚点 Σ=100% 闭合", ok_close)

    return finish()


def finish():
    print(f"\n{'PASS' if not FAILS else 'FAIL'}：{len(FAILS)} 项失败")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
