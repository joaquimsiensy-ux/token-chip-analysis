#!/usr/bin/env python3
"""entity_source_trace 契约测试（离线合成数据，不依赖真库；v2 正向模拟版）。

覆盖（schema references/scan-schemas.md §4；PYTHIA 真库锚点另见 fixtures/pythia_anchors.json）：
  1. mint 直达 → PROVEN_ORIGIN/mint 100%
  2. 标签边界 → BOUNDARY/cex_confirmed（evidence=label_confirmed）
  3. 两来源 6:4 → 终点按比例、direct_upstream 准确
  4. codex P0-1 反例（v1 数学错误的判死场景）：中间节点先收 mint 100 → 转出 90 →
     再收 DEX 90 → 全转实体 ⇒ 必须得 mint 10% / dex 90%（v1 会错算 52.6/47.4）
  5. data_gap：上游凭空转出 → UNRESOLVED/data_gap
  6. 深度上限：12 层链 → UNRESOLVED/depth_limit
  7. 回环（跨时回流）→ 正向模拟下正确穿透为 mint 100%（v1 的 same_slot_scc 概念废除）
  8. 实体内部收缩：内部边不计流入
  9. 设施启发式（降门槛合成）→ UNRESOLVED/facility_candidate 支路停
 10. 全实体两锚点 Σ=100% 闭合＋members_sha256 在场且可复算
 11. FIFO/LIFO 敏感性翻转 → exit 2 阻断（报告落盘 stable=false）
 12. --entity-file 类型硬检查：成员跨实体重复 / 非字符串成员 → exit 2
用法：python3 scripts/tests/test_entity_source_trace.py   退出码 0=PASS / 1=FAIL
"""
import hashlib
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


def write_edges(d, edges, name="edges.jsonl"):
    ep = os.path.join(d, name)
    with open(ep, "w", encoding="utf-8") as f:
        for ts, frm, to, amt in edges:
            f.write(json.dumps([ts, 0, frm, to, amt]) + "\n")
    return ep


def run_trace(d, ep, entities, labels=None, extra=None):
    with open(os.path.join(d, "entities.json"), "w") as f:
        json.dump(entities, f)
    args = [sys.executable, SCRIPT, "--edges-sol", ep, "--total-supply", str(TOTAL),
            "--entity-file", os.path.join(d, "entities.json"),
            "--out", os.path.join(d, "ledger.json")]
    if labels is not None:
        with open(os.path.join(d, "labels.json"), "w") as f:
            json.dump(labels, f)
        args += ["--labels-file", os.path.join(d, "labels.json")]
    args += extra or []
    return subprocess.run(args, capture_output=True, text=True)


def main():
    d = tempfile.mkdtemp(prefix="trace_test_")
    E = []
    # 1. mint 直达
    E.append((day(1), Z, "A1", 100))
    # 2. 标签边界
    E.append((day(1), Z, "CEXL", 500))
    E.append((day(2), "CEXL", "A2", 100))
    # 3. 6:4 两来源，上游全 mint
    E.append((day(1), Z, "F1", 60))
    E.append((day(1), Z, "F2", 40))
    E.append((day(3), "F1", "A3", 60))
    E.append((day(3), "F2", "A3", 40))
    # 4. codex P0-1 反例：MID 先收 mint 100 → 转出 90 → 再收 DEXB 90 → 全转 A9
    E.append((day(1), Z, "MID", 100))
    E.append((day(2), "MID", "SOMEOUT", 90))
    E.append((day(3), "DEXB", "MID", 90))
    E.append((day(4), "MID", "A9", 100))
    # DEXB 自身要有币可转（labels 判终点，不展开上游）
    E.append((day(1), Z, "DEXB", 500))
    # 5. data_gap：GAP 凭空转出
    E.append((day(4), "GAP", "A4", 100))
    # 6. 12 层链 D12→…→D1→A5
    E.append((day(1), Z, "D12", 100))
    for i in range(12, 1, -1):
        E.append((day(14 - i), f"D{i}", f"D{i-1}", 100))
    E.append((day(13), "D1", "A5", 100))
    # 7. 跨时回环：mint→B6 100、B6→A6 60、A6→B6 50（回流）、B6→A6 90
    E.append((day(1), Z, "B6", 100))
    E.append((day(2), "B6", "A6", 60))
    E.append((day(3), "A6", "B6", 50))
    E.append((day(4), "B6", "A6", 90))
    # 8. 实体内部收缩：mint→B7→A7（B7→A7 是内部边）
    E.append((day(1), Z, "B7", 100))
    E.append((day(2), "B7", "A7", 100))
    # 9. 设施启发式（门槛降为 5）：FAC 5 入 5 出
    for i in range(5):
        E.append((day(1), Z, f"FIN{i}", 20))
        E.append((day(2), f"FIN{i}", "FAC", 20))
    for i in range(4):
        E.append((day(3), "FAC", f"FOUT{i}", 1))
    E.append((day(3), "FAC", "A8", 96))

    ep = write_edges(d, E)
    p = run_trace(d, ep,
                  {"e1": ["A1"], "e2": ["A2"], "e3": ["A3"], "e4": ["A4"], "e5": ["A5"],
                   "e6": ["A6"], "e7": ["A7", "B7"], "e8": ["A8"], "e9": ["A9"]},
                  labels={"CEXL": {"kind": "cex", "name": "TestCEX"},
                          "DEXB": {"kind": "dex_pool", "name": "TestPool"}},
                  extra=["--facility-min-degree", "5"])
    check("主场景 exit 0", p.returncode == 0)
    if p.returncode != 0:
        print(p.stdout, p.stderr)
        return finish()
    r = json.load(open(os.path.join(d, "ledger.json")))
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
    check("两来源 6:4 终点 mint 100%", c3.get(("PROVEN_ORIGIN", "mint")) == 100.0)
    up3 = {u["addr"]: u["pct_of_gross_in"] for u in ents["e3"]["anchors"]["peak"]["direct_upstream"]}
    check("direct_upstream 毛流入 6:4 准确", up3.get("F1") == 60.0 and up3.get("F2") == 40.0)
    # codex 反例：正确答案 mint 10 / dex 90；v1 错误算法会给 52.63/47.37
    c9 = peak_comp("e9")
    check("P0-1 反例：mint 10%（v1 会错算 52.6%）",
          abs((c9.get(("PROVEN_ORIGIN", "mint")) or 0) - 10.0) < 0.01)
    check("P0-1 反例：dex_pool 90%", abs((c9.get(("BOUNDARY", "dex_pool")) or 0) - 90.0) < 0.01)
    c4 = peak_comp("e4")
    check("data_gap 100%", c4.get(("UNRESOLVED", "data_gap")) == 100.0)
    c5 = peak_comp("e5")
    check("深度上限 → depth_limit", ("UNRESOLVED", "depth_limit") in c5)
    c6 = peak_comp("e6")
    check("跨时回环正确穿透 → mint 100%（same_slot_scc 概念废除）",
          c6.get(("PROVEN_ORIGIN", "mint")) == 100.0 and len(c6) == 1)
    c7 = peak_comp("e7")
    check("实体内部收缩：终点 mint 100%（内部边不计）", c7.get(("PROVEN_ORIGIN", "mint")) == 100.0)
    check("实体内部收缩：进货单只有 mint 一家",
          len(ents["e7"]["anchors"]["peak"]["direct_upstream"]) == 1)
    c8 = peak_comp("e8")
    check("设施启发式支路停 → facility_candidate", ("UNRESOLVED", "facility_candidate") in c8)
    ok_close = all(abs(e["closure_check"]["peak_sum_pct"] - 100.0) <= 0.5 for e in r["entities"])
    check("全实体峰值锚点 Σ=100% 闭合", ok_close)
    sha_ok = all(e.get("members_sha256") == hashlib.sha256(
        ",".join(sorted({"e1": ["A1"], "e2": ["A2"], "e3": ["A3"], "e4": ["A4"], "e5": ["A5"],
                         "e6": ["A6"], "e7": ["A7", "B7"], "e8": ["A8"], "e9": ["A9"]
                         }[e["entity_id"]])).encode()).hexdigest()
        for e in r["entities"])
    check("members_sha256 在场且可复算", sha_ok)
    check("敏感性稳定（主场景无消耗歧义）",
          r["bounds_sensitivity"]["conservative_vs_aggressive_verdict_stable"] is True)

    # 11. FIFO/LIFO 翻转 → exit 2（先收 mint 100、再收 dex 100、转出 100：
    #     current 锚点 pro_rata=50/50、fifo 剩 dex、lifo 剩 mint——主导条目翻转）
    d11 = tempfile.mkdtemp(prefix="trace_flip_")
    E11 = [(day(1), Z, "X", 100), (day(1), Z, "DEXQ", 500),
           (day(2), "DEXQ", "X", 100), (day(3), "X", "GONE", 100)]
    ep11 = write_edges(d11, E11)
    p = run_trace(d11, ep11, {"ex": ["X"]}, labels={"DEXQ": {"kind": "dex_pool"}})
    check("FIFO/LIFO 主导翻转 exit 2 阻断", p.returncode == 2)
    r11 = json.load(open(os.path.join(d11, "ledger.json")))
    check("翻转案报告落盘 stable=false",
          r11["bounds_sensitivity"]["conservative_vs_aggressive_verdict_stable"] is False)
    flip = r11["bounds_sensitivity"]["per_entity"]["ex"]["anchors"]["current"]
    check("翻转细节记录 top_by_policy 且 agree=false", flip["agree"] is False
          and flip["top_by_policy"]["fifo"] != flip["top_by_policy"]["lifo"])

    # 12. --entity-file 类型硬检查
    d12 = tempfile.mkdtemp(prefix="trace_badent_")
    ep12 = write_edges(d12, [(day(1), Z, "Y", 100)])
    p = run_trace(d12, ep12, {"ea": ["Y"], "eb": ["Y"]})
    check("成员跨实体重复 exit 2", p.returncode == 2)
    p = run_trace(d12, ep12, {"ea": [123]})
    check("成员非字符串 exit 2", p.returncode == 2)
    p = run_trace(d12, ep12, {"ea": []})
    check("成员空数组 exit 2", p.returncode == 2)

    return finish()


def finish():
    print(f"\n{'PASS' if not FAILS else 'FAIL'}：{len(FAILS)} 项失败")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
