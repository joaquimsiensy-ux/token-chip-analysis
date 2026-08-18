#!/usr/bin/env python3
"""flow_anomaly_scan 契约测试（离线合成数据，不依赖真库）。

覆盖（schema 权威定义 references/scan-schemas.md；PYTHIA 真库锚点另见
fixtures/pythia_anchors.json）：
  1. sink 正例：14 日窗内 6 来源合计 ≥2% → 报汇集点
  2. sink 同窗判定（Q1 型反例）：金额最大窗来源不足、另存在双达标窗 → 必须命中
     （防"先取金额最大窗再验来源数"的实现退化）
  3. sink 负例：来源 <5 / 合计 <2% → 不报
  4. spray 脉冲正例：14 日窗内 ≥20 新收方合计 ≥2% → mode=pulse，且 mode_hits.pulse_all
     同步命中（pulse ⊂ pulse_all 子集关系可见）
  5. spray 慢速正例：全史 ≥100 收方 ≥2%、无突出滑窗 → mode=slow_spray
  6. 实体内部流转抵消：--entity-file 后内部边不计
  7. 零截断闭合：pulse/pulse_all recipients==count；sink sources==source_count
  8. sink 多窗口累计反例：三个不重叠窗口各 4%，报告必须输出历史峰值/现仓/全史净流入 12%
  ——以下 v2（2026-08-02 两缝修复回归）——
  9. RefillSpray 正例（缝2）：收方先占位建仓再受灌 → fresh=0、mode=pulse_all
  10. LaunchSpray：pulse_all 第二正例＋launch_window 用其窗口起点（发射窗内 → true）
  11. 慢速线成对边界：99 收方不报 / 100 收方报 slow_spray（500→100 锁线）
  12. pulse 收方数边界：19 收方不报 / 恰 20 收方恰 2% 命中（≥ 语义）
  13. 金额边界负例：25 收方合计 1.975% <2% 不报
  14. 浓度反例：1 笔 1.99% 大额＋19 粉尘凑双线可命中，但浓度字段必须暴露
      （meaningful_recipient_count==1、top1_recipient_share_pct==1.99）
  15. v4 producer 不产零值边；仅 5 个真实收方不得凑过收方线
  16. MidSpray 残余缝负例：50 收方匀速 100 天三口径全不中（覆盖真空边界锚定）
用法：python3 scripts/tests/test_flow_anomaly.py   退出码 0=PASS / 1=FAIL
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "report", "flow_anomaly_scan.py")
FAILS = []
TOTAL = 10 ** 12
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
        for tx_index, (ts, frm, to, amt) in enumerate(edges):
            f.write(json.dumps([ts, 0, tx_index, -1, frm, to, amt]) + "\n")
    args = [sys.executable, SCRIPT, "--edges-sol", ep,
            "--total-supply", str(TOTAL), "--out", out] + (extra or [])
    return subprocess.run(args, capture_output=True, text=True)


def day(n):
    return n * 86400


def main():
    d = tempfile.mkdtemp(prefix="flow_test_")
    edges = []
    # 8 个合格来源（各峰值 ≥0.02%＝2e8）
    SRC = [f"Src{i}" for i in range(8)]
    for s in SRC:
        edges.append((day(0), Z, s, 8 * 10 ** 10))

    # 1. sink 正例：SinkA 在 day 10~12 从 6 来源各收 0.5%（合计 3% ≥2%、6 来源 ≥5）
    for i in range(6):
        edges.append((day(10 + i % 3), SRC[i], "SinkA", 5 * 10 ** 9))

    # 2. Q1 型反例：SinkB 金额最大窗＝day 40 单来源 5%（来源 1 <5）；
    #    另一窗 day 60~65 有 5 来源各 0.5%（合计 2.5% ≥2% 且 ≥5 来源）→ 必须命中后者
    edges.append((day(40), SRC[0], "SinkB", 5 * 10 ** 10))
    for i in range(5):
        edges.append((day(60 + i), SRC[i + 1], "SinkB", 5 * 10 ** 9))

    # 3. sink 负例：SinkC 4 来源合计 4%（来源不足）；SinkD 6 来源合计 1.2%（金额不足）
    for i in range(4):
        edges.append((day(80), SRC[i], "SinkC", 10 ** 10))
    for i in range(6):
        edges.append((day(90), SRC[i], "SinkD", 2 * 10 ** 9))

    # 8. 三个互不重叠的 14 日窗各 4%，单个最佳窗仍只有 4%，但库存累计峰值/现仓为 12%。
    for base in (200, 230, 260):
        for i in range(5):
            edges.append((day(base), SRC[i], "MultiWindowSink", 8 * 10 ** 9))

    # 4. spray 脉冲正例：PulseSpray 收 4%，day 100~102 向 22 个新地址各派 0.1%（2.2% ≥2%、22 ≥20）
    edges.append((day(99), Z, "PulseSpray", 4 * 10 ** 10))
    for i in range(22):
        edges.append((day(100 + i % 3), "PulseSpray", f"PulseRecv{i:02d}", 10 ** 9))

    # 5. spray 慢速正例：SlowSpray 收 3%，day 110 起每天向 6 个新地址各派 0.005%，
    #    100 天 600 收方合计 3%（无 14 日窗 ≥2%：14 日仅 84 收方 0.42%——pulse_all 金额线
    #    同样不达标，慢速兜底判定不受 v2 新口径干扰）
    edges.append((day(109), Z, "SlowSpray", 3 * 10 ** 10))
    n = 0
    for dd in range(100):
        for k in range(6):
            edges.append((day(110 + dd), "SlowSpray", f"SlowRecv{n:03d}", 5 * 10 ** 7))
            n += 1

    # 9. RefillSpray（缝2 复现）：30 收方先在 day 150 从 Seeder 占位建仓 8e7
    #    （占位/终仓峰值 8.8e8 = 9.1% ≥ first-meaningful-ratio 5%，首建日锁定在占位日），
    #    day 155~157 受灌各 8e8（合计 2.4% ≥2%、30 ≥20）——fresh 计数=0，旧 pulse 全盲，
    #    必须由 pulse_all 抓到
    edges.append((day(0), Z, "Seeder", 10 ** 10))
    edges.append((day(154), Z, "RefillSpray", 3 * 10 ** 10))
    for i in range(30):
        edges.append((day(150), "Seeder", f"RefillRecv{i:02d}", 8 * 10 ** 7))
        edges.append((day(155 + i % 3), "RefillSpray", f"RefillRecv{i:02d}", 8 * 10 ** 8))

    # 10. LaunchSpray：pulse_all 第二正例＋launch_window 正侧——20 收方 day 0 占位、
    #     day 2~3 受灌各 1.05e9（合计 2.1%），窗起 day 2 ≤ 数据首日+3 → launch_window=true
    edges.append((day(0), Z, "Seeder3", 2 * 10 ** 9))
    edges.append((day(1), Z, "LaunchSpray", 3 * 10 ** 10))
    for i in range(20):
        edges.append((day(0), "Seeder3", f"LRecv{i:02d}", 8 * 10 ** 7))
        edges.append((day(2 + i % 2), "LaunchSpray", f"LRecv{i:02d}", 105 * 10 ** 7))

    # 11. 慢速线成对边界（500→100）：Slow99=99 收方 2.079% 不报；Slow100=100 收方 2.1% 报。
    #     两者每天 3 收方各 2.1e8，任何 14 日窗 42 收方 0.88% <2% 金额不达 → 脉冲双口径都不中
    edges.append((day(299), Z, "Slow99", 3 * 10 ** 10))
    edges.append((day(399), Z, "Slow100", 3 * 10 ** 10))
    for i in range(99):
        edges.append((day(300 + i // 3), "Slow99", f"S99R{i:02d}", 21 * 10 ** 7))
    for i in range(100):
        edges.append((day(400 + i // 3), "Slow100", f"S100R{i:03d}", 21 * 10 ** 7))

    # 12. pulse 收方数边界：Pulse19=19 新收方各 1.1e9（2.09% 金额达标、收方 19<20）不报；
    #     Pulse20=恰 20 新收方各恰 1e9（恰 2.0%、恰 20）命中（判据为 ≥ 非 >）
    edges.append((day(499), Z, "Pulse19", 3 * 10 ** 10))
    for i in range(19):
        edges.append((day(500 + i % 3), "Pulse19", f"P19R{i:02d}", 11 * 10 ** 8))
    edges.append((day(519), Z, "Pulse20", 3 * 10 ** 10))
    for i in range(20):
        edges.append((day(520 + i % 3), "Pulse20", f"P20R{i:02d}", 10 ** 9))

    # 13. 金额边界负例：PulseUnder=25 新收方各 7.9e8，合计 1.975% <2% → 三口径全不中
    edges.append((day(539), Z, "PulseUnder", 3 * 10 ** 10))
    for i in range(25):
        edges.append((day(540 + i % 3), "PulseUnder", f"PUR{i:02d}", 79 * 10 ** 7))

    # 14. 浓度反例：FakeSpray=1 笔 2.0% 大额＋19 笔粉尘 1e6 同日——金额/收方双线都过，
    #     但 meaningful（≥0.001%=1e7）只有大额收方 1 个，浓度字段必须暴露伪分发
    edges.append((day(559), Z, "FakeSpray", 3 * 10 ** 10))
    edges.append((day(560), "FakeSpray", "BigRecv", 2 * 10 ** 10))
    for i in range(19):
        edges.append((day(560), "FakeSpray", f"DustR{i:02d}", 10 ** 6))

    # 15. v4 producer 不产零值边：ZeroSpray 只有 5 个真实收方各 4.2e9（2.1% 金额
    #     达标但真实收方仅 5 <20、全史 5 <100）→ 不报。
    edges.append((day(579), Z, "ZeroSpray", 3 * 10 ** 10))
    for i in range(5):
        edges.append((day(580), "ZeroSpray", f"ZReal{i}", 42 * 10 ** 8))

    # 16. MidSpray 残余缝负例：50 收方每天 1 个各 6e8（合计 3%），14 日窗 14 收方 <20、
    #     全史 50 <100 → 三口径全不中（v2 后仍存在的覆盖真空，文档如实声明）
    edges.append((day(599), Z, "MidSpray", 4 * 10 ** 10))
    for i in range(50):
        edges.append((day(600 + i), "MidSpray", f"MidR{i:02d}", 6 * 10 ** 8))

    out1 = os.path.join(d, "r1.json")
    p = run(edges, out1)
    check("主场景 exit 0", p.returncode == 0)
    if p.returncode != 0:
        print(p.stdout, p.stderr)
        return finish()
    r = json.load(open(out1))
    check("schema=flow-anomaly/v2", r.get("schema") == "flow-anomaly/v2")

    sids = {s["addr"]: s for s in r["sinks"]}
    check("sink 正例 SinkA 命中", "SinkA" in sids)
    check("Q1 型反例 SinkB 命中（双达标窗）", "SinkB" in sids)
    if "SinkB" in sids:
        bw = sids["SinkB"]["best_window"]
        check("SinkB 命中的是多来源窗（≥5 来源）", bw["source_count"] >= 5)
    check("sink 负例 SinkC/SinkD 未报", "SinkC" not in sids and "SinkD" not in sids)
    mw = sids.get("MultiWindowSink")
    check("多窗口 sink 命中且单窗仅 4%", mw is not None and mw["best_window"]["inflow_pct"] == 4.0)
    if mw:
        check("多窗口 sink 输出历史峰值/现仓/全史净流入 12%",
              mw["balance"]["historical_peak_pct"] == 12.0
              and mw["balance"]["current_balance_pct"] == 12.0
              and mw["all_time"]["net_inflow_pct"] == 12.0)
    for s in r["sinks"]:
        check(f"sink {s['addr']} sources 闭合", len(s["sources"]) == s["best_window"]["source_count"])

    sp = {s["addr"]: s for s in r["sprays"]}
    # ---- 4. pulse 正例＋子集关系＋闭合 ----
    check("spray 脉冲正例命中且 mode=pulse",
          "PulseSpray" in sp and sp["PulseSpray"]["mode"] == "pulse")
    if "PulseSpray" in sp:
        ps = sp["PulseSpray"]
        check("pulse recipients 闭合（fresh 口径）",
              len(ps["recipients"]) == ps["best_window"]["fresh_recipient_count"] == 22)
        check("pulse ⊂ pulse_all：mode_hits.pulse_all 同步命中",
              ps["mode_hits"]["pulse"]["hit"] and ps["mode_hits"]["pulse_all"]["hit"])
        check("pulse 窗浓度：22 收方全部有意义",
              ps["best_window"]["meaningful_recipient_count"] == 22)
    # ---- 5. slow_spray 正例（新口径不干扰） ----
    check("spray 慢速正例命中且 mode=slow_spray",
          "SlowSpray" in sp and sp["SlowSpray"]["mode"] == "slow_spray")
    if "SlowSpray" in sp:
        ss = sp["SlowSpray"]
        check("slow_spray 全史收方数=600", ss["all_time"]["recipient_count"] == 600)
        check("slow_spray 主模式不带 best_window 且 pulse_all 未中（窗金额不达）",
              ss["best_window"] is None and not ss["mode_hits"]["pulse_all"]["hit"])
    # ---- 9. RefillSpray（缝2）：老收方补货只有 pulse_all 能抓 ----
    check("RefillSpray 命中且 mode=pulse_all（旧 pulse 口径全盲）",
          "RefillSpray" in sp and sp["RefillSpray"]["mode"] == "pulse_all")
    if "RefillSpray" in sp:
        rs = sp["RefillSpray"]
        check("RefillSpray fresh 收方精确为 0",
              rs["best_window"]["fresh_recipient_count"] == 0
              and not rs["mode_hits"]["pulse"]["hit"])
        check("RefillSpray recipients 闭合（全体口径 30）",
              len(rs["recipients"]) == rs["best_window"]["recipient_count"] == 30)
        check("RefillSpray 窗流出 2.4%", rs["best_window"]["outflow_pct"] == 2.4)
        check("RefillSpray 非发射窗（launch_window=false）", rs["launch_window"] is False)
    # ---- 10. LaunchSpray：pulse_all 的 launch_window 用窗口起点 ----
    check("LaunchSpray 命中 pulse_all 且 launch_window=true（窗起 day2 在发射窗内）",
          "LaunchSpray" in sp and sp["LaunchSpray"]["mode"] == "pulse_all"
          and sp["LaunchSpray"]["launch_window"] is True)
    # ---- 11. 慢速线 100 成对边界 ----
    check("Slow99（99 收方）不报——慢速线下界", "Slow99" not in sp)
    check("Slow100（100 收方）报 slow_spray",
          "Slow100" in sp and sp["Slow100"]["mode"] == "slow_spray"
          and sp["Slow100"]["all_time"]["recipient_count"] == 100)
    # ---- 12/13. 脉冲边界 ----
    check("Pulse19（19 收方金额达标）不报——收方线", "Pulse19" not in sp)
    check("Pulse20（恰 20 收方恰 2%）命中 pulse——判据为 ≥",
          "Pulse20" in sp and sp["Pulse20"]["mode"] == "pulse")
    check("PulseUnder（25 收方 1.975%）不报——金额线", "PulseUnder" not in sp)
    # ---- 14. 浓度字段暴露伪分发 ----
    check("FakeSpray（1 大额＋19 粉尘）命中双线", "FakeSpray" in sp)
    if "FakeSpray" in sp:
        fs = sp["FakeSpray"]
        check("FakeSpray 浓度暴露：meaningful=1、top1=2.0%",
              fs["best_window"]["meaningful_recipient_count"] == 1
              and fs["best_window"]["top1_recipient_share_pct"] == 2.0)
    # ---- 15/16. 正式 v4 边与残余缝 ----
    check("ZeroSpray（仅 5 个真实收方）不报", "ZeroSpray" not in sp)
    check("MidSpray（50 收方匀速）不报——残余缝如实存在", "MidSpray" not in sp)

    # 6. 实体内部抵消：SinkA 与其 6 来源同实体 → 内部边不计 → SinkA 不再命中
    ef = os.path.join(d, "entity.json")
    with open(ef, "w") as f:
        json.dump({"e_test": ["SinkA"] + SRC[:6]}, f)
    out2 = os.path.join(d, "r2.json")
    p2 = run(edges, out2, ["--entity-file", ef])
    r2 = json.load(open(out2))
    check("实体内部流转抵消后 SinkA 不报",
          p2.returncode == 0 and "SinkA" not in {s["addr"] for s in r2["sinks"]})

    # 8. 跨实体转账保留（v6.8.1 codex 复核修复的回归）：SinkA 归实体 eA、6 来源归实体 eB
    #    ——不同实体间的真实转账不得被抵消，SinkA 必须仍命中
    ef2 = os.path.join(d, "entity2.json")
    with open(ef2, "w") as f:
        json.dump({"eA": ["SinkA"], "eB": SRC[:6]}, f)
    out3 = os.path.join(d, "r3.json")
    p3 = run(edges, out3, ["--entity-file", ef2])
    r3 = json.load(open(out3))
    check("跨实体转账保留：SinkA 仍命中（拍平抵消是旧 bug）",
          p3.returncode == 0 and "SinkA" in {s["addr"] for s in r3["sinks"]})

    # 9. 同址跨实体名册冲突 → exit 2
    ef3 = os.path.join(d, "entity3.json")
    with open(ef3, "w") as f:
        json.dump({"eA": ["SinkA"], "eB": ["SinkA"]}, f)
    p4 = run(edges, os.path.join(d, "r4.json"), ["--entity-file", ef3])
    check("同址跨实体名册冲突 exit 2", p4.returncode == 2)

    p5 = run(edges, os.path.join(d, "r5.json"), ["--legacy-sol5"])
    check("正式 anomaly 链显式拒绝 legacy-sol5",
          p5.returncode == 2
          and "正式 anomaly 链拒绝 legacy-sol5" in (p5.stdout + p5.stderr))

    return finish()


def finish():
    print(f"\n{'PASS' if not FAILS else 'FAIL'}：{len(FAILS)} 项失败")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
