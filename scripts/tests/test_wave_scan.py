#!/usr/bin/env python3
"""wave_scan v2 契约测试（离线合成数据，不依赖真库）。

覆盖（schema 权威定义 references/scan-schemas.md；PYTHIA 真库锚点另见
fixtures/pythia_anchors.json，须真库在位时手动回测比对）：
  1. A 正例：7 日窗内 ≥20 员且合并峰 ≥10% → 报波次（含 seed_window 字段）
  2. A 负例：21 员同窗但合并峰 <10%（种子验证失败）→ 不报；19 员窗不进候选
  3. C v2 口径：峰→30% 峰值 10 天 → hit=true 且 days 准确
  4. D 正例：四条合一全过 → 报等额组（top_sender/全局出度/densest 窗准确）
  5. D 负例 ×3：收方 <20 / 单笔 <0.001% / 组合计 <1% → 各自不报
  6. 零截断闭合：members 长度 == member_count / recipients
  7. 稳定 ID：同输入两跑 ID 逐字相同（内容派生）
  8. 负余额达实质线 → exit 2（fail-closed）
  9. D 二轮复收（v6.8.1 codex 复核修复的回归）：同批收方先零散收过该面额、后同窗
     集中复收 → 必须命中（旧实现按"每收方首收时间"去重会把第二轮全部吞掉）
 10. 负余额"先负后回正"（v6.8.1）：期末余额为正但历史最低点为负 → 仍 exit 2
用法：python3 scripts/tests/test_wave_scan.py   退出码 0=PASS / 1=FAIL
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "report", "wave_scan.py")
FAILS = []
TOTAL = 10 ** 12  # 合成总供应，1% = 1e10
Z = "0x0000000000000000000000000000000000000000"


def check(name, cond):
    if not cond:
        FAILS.append(name)
        print(f"FAIL  {name}")
    else:
        print(f"ok    {name}")


def run(edges, out, extra=None):
    d = os.path.dirname(out)
    ep = os.path.join(d, "edges.jsonl")
    with open(ep, "w", encoding="utf-8") as f:
        for ts, frm, to, amt in edges:
            f.write(json.dumps([ts, 0, frm, to, amt]) + "\n")
    args = [sys.executable, SCRIPT, "--edges-sol", ep,
            "--total-supply", str(TOTAL), "--out", out] + (extra or [])
    return subprocess.run(args, capture_output=True, text=True)


def day(n):
    return n * 86400


def main():
    d = tempfile.mkdtemp(prefix="wave_scan_test_")

    # ---- 合成主场景 ----
    edges = []
    F, F2 = "FeederMain", "FeederD"
    edges.append((day(0), Z, F, 6 * 10 ** 11))          # Z→F 60%
    edges.append((day(0), Z, F2, 10 ** 11))             # Z→F2 10%
    # A 正例：25 址 3 天内各建 ~0.5%（合并峰 ~12.5% ≥10%、25 员 ≥20）；
    # 金额逐址微差——防止 25 笔同面额自己构成合法等额组干扰 D 断言
    W = [f"WaveAddr{i:02d}" for i in range(25)]
    for i, w in enumerate(W):
        edges.append((day(10 + i % 3), F, w, 5 * 10 ** 9 + i * 10 ** 6))
    # C 正例：峰值日 day12 → day22 全清（10 天 ≤30 → hit）
    for i, w in enumerate(W):
        edges.append((day(22), w, F, 5 * 10 ** 9 + i * 10 ** 6))
    # A 负例（种子峰不足）＝ D 正例共用：F2→21 收方各 0.3%（合并峰 6.3% <10% 不成波；
    # D 四条：单笔 0.3%≥0.001% ✓、7 日窗 21 收方 ≥20 ✓、组合计 6.3%≥1% ✓ → 报等额组）
    D_recv = [f"DenomAddr{i:02d}" for i in range(21)]
    for i, r in enumerate(D_recv):
        edges.append((day(30 + i % 4), F2, r, 3 * 10 ** 9))
    # A 负例（员数不足）：19 址同窗各 0.5%（<20 员不进候选窗）
    for i in range(19):
        edges.append((day(50 + i % 3), F, f"NarrowAddr{i:02d}", 5 * 10 ** 9))
    # D 负例（组合计不足）：20 收方各 0.012%（单笔过线、组 0.24% <1%）
    for i in range(20):
        edges.append((day(60 + i % 3), F, f"SmallGrp{i:02d}", 12 * 10 ** 7))
    # D 负例（单笔不足）：25 收方各 0.0005% < 0.001%
    for i in range(25):
        edges.append((day(70), F, f"DustGrp{i:02d}", 5 * 10 ** 6))

    out1 = os.path.join(d, "r1.json")
    p = run(edges, out1)
    check("主场景 exit 0", p.returncode == 0)
    if p.returncode != 0:
        print(p.stdout, p.stderr)
        return finish()
    r = json.load(open(out1))

    check("schema=wave-scan/v2", r.get("schema") == "wave-scan/v2")
    waves = r["waves"]
    check("A 正例：恰报 1 个波次（负例窗未混入）", len(waves) == 1)
    if waves:
        w = waves[0]
        mem = {m["addr"] for m in w["members"]}
        check("A 波次成员=25 址 W 系", mem == set(W))
        check("A seed_window 员数 ≥20", w["seed_window"]["member_count"] >= 20)
        check("A seed_window 合并峰 ≥10%", w["seed_window"]["combined_peak_pct"] >= 10.0)
        check("C hit=true 且 days=10", w["fingerprints"]["C_peak_to_30pct"] == {"days": 10, "hit": True})
        check("三桶：25 员全 cleared", w["retention_buckets"] == {"cleared": 25, "partial_exit": 0, "retained": 0})
        check("零截断：members 长度==member_count", len(w["members"]) == w["member_count"])
        check("成员含 first_meaningful 与 retention_bucket 字段",
              all("first_meaningful" in m and "retention_bucket" in m for m in w["members"]))

    eqs = r["equal_amount_groups"]
    check("D：恰报 1 个等额组（三负例全被挡）", len(eqs) == 1)
    if eqs:
        g = eqs[0]
        check("D 面额=3e9、收方=21", g["amount_raw"] == str(3 * 10 ** 9) and g["recipients"] == 21)
        check("D densest 7 日窗 ≥20", g["densest_7d_window"]["recipients"] >= 20)
        check("D top_sender=F2 且全局出度=21", g["top_sender"] == F2 and g["top_sender_global_out_degree"] == 21)
        check("D 零截断：members==recipients", len(g["members"]) == g["recipients"])

    check("requires_adjudication=true", r["requires_adjudication"] is True)
    check("负余额=0", r["negative_balance_addrs"] == 0)

    # ---- 稳定 ID：同输入重跑 ----
    out2 = os.path.join(d, "r2.json")
    p2 = run(edges, out2)
    r2 = json.load(open(out2))
    check("稳定 ID：波次与等额组 ID 两跑一致",
          [w["id"] for w in r["waves"]] == [w["id"] for w in r2["waves"]]
          and [g["id"] for g in r["equal_amount_groups"]] == [g["id"] for g in r2["equal_amount_groups"]])

    # ---- 负余额 exit 2 ----
    d2 = tempfile.mkdtemp(prefix="wave_scan_neg_")
    neg_edges = [(day(0), Z, "SomeAddr", 10 ** 11),
                 (day(1), "GhostAddr", "SomeAddr", 5 * 10 ** 10)]  # Ghost 无来源 → final=-5%
    p3 = run(neg_edges, os.path.join(d2, "r.json"))
    check("负余额达实质线 → exit 2", p3.returncode == 2)

    # ---- 10. 负余额"先负后回正"：期末正但历史最低点负 → 仍 exit 2 ----
    d3 = tempfile.mkdtemp(prefix="wave_scan_negheal_")
    heal_edges = [(day(0), Z, "SomeAddr", 10 ** 11),
                  (day(1), "Ghost2", "SomeAddr", 5 * 10 ** 10),   # 先凭空转出（min=-5%）
                  (day(2), "SomeAddr", "Ghost2", 6 * 10 ** 10)]   # 后收币回正（final=+1%）
    p4 = run(heal_edges, os.path.join(d3, "r.json"))
    check("先负后回正（数据缺失自愈假象）→ 仍 exit 2", p4.returncode == 2)

    # ---- 9. D 二轮复收：同批收方先零散收过、后同窗集中复收 → 必须命中 ----
    d4 = tempfile.mkdtemp(prefix="wave_scan_recoll_")
    re_edges = [(day(0), Z, "F3", 2 * 10 ** 11)]
    RR = [f"ReRecv{i:02d}" for i in range(20)]
    for i, rr in enumerate(RR):
        re_edges.append((day(100 + 2 * i), "F3", rr, 2 * 10 ** 9))   # 第一轮：38 天零散
    for rr in RR:
        re_edges.append((day(150), "F3", rr, 2 * 10 ** 9))           # 第二轮：同日集中复收
    p5 = run(re_edges, os.path.join(d4, "r.json"))
    r5 = json.load(open(os.path.join(d4, "r.json")))
    hit = [g for g in r5["equal_amount_groups"] if g["amount_raw"] == str(2 * 10 ** 9)]
    check("D 二轮复收命中（旧实现按首收去重必漏）", p5.returncode == 0 and len(hit) == 1)
    if hit:
        check("D 二轮复收：tx_count=40 且 densest 窗 ≥20",
              hit[0]["tx_count"] == 40 and hit[0]["densest_7d_window"]["recipients"] >= 20)

    return finish()


def finish():
    print(f"\n{'PASS' if not FAILS else 'FAIL'}：{len(FAILS)} 项失败")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
