#!/usr/bin/env python3
"""flow_anomaly_scan 契约测试（离线合成数据，不依赖真库）。

覆盖（schema 权威定义 references/scan-schemas.md；PYTHIA 真库锚点另见
fixtures/pythia_anchors.json）：
  1. sink 正例：14 日窗内 6 来源合计 ≥2% → 报汇集点
  2. sink 同窗判定（Q1 型反例）：金额最大窗来源不足、另存在双达标窗 → 必须命中
     （防"先取金额最大窗再验来源数"的实现退化）
  3. sink 负例：来源 <5 / 合计 <2% → 不报
  4. spray 脉冲正例：14 日窗内 ≥20 新收方合计 ≥2% → mode=pulse
  5. spray 慢速正例：全史 ≥500 收方 ≥2%、无突出滑窗 → mode=slow_spray
  6. 实体内部流转抵消：--entity-file 后内部边不计
  7. 零截断闭合：pulse recipients==count；sink sources==source_count
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
        for ts, frm, to, amt in edges:
            f.write(json.dumps([ts, 0, frm, to, amt]) + "\n")
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

    # 4. spray 脉冲正例：PulseSpray 收 4%，day 100~102 向 22 个新地址各派 0.1%（2.2% ≥2%、22 ≥20）
    edges.append((day(99), Z, "PulseSpray", 4 * 10 ** 10))
    for i in range(22):
        edges.append((day(100 + i % 3), "PulseSpray", f"PulseRecv{i:02d}", 10 ** 9))

    # 5. spray 慢速正例：SlowSpray 收 3%，day 110 起每天向 6 个新地址各派 0.005%，
    #    100 天 600 收方合计 3%（无 14 日窗 ≥2%：14 日仅 84 收方 0.42%）
    edges.append((day(109), Z, "SlowSpray", 3 * 10 ** 10))
    n = 0
    for dd in range(100):
        for k in range(6):
            edges.append((day(110 + dd), "SlowSpray", f"SlowRecv{n:03d}", 5 * 10 ** 7))
            n += 1

    out1 = os.path.join(d, "r1.json")
    p = run(edges, out1)
    check("主场景 exit 0", p.returncode == 0)
    if p.returncode != 0:
        print(p.stdout, p.stderr)
        return finish()
    r = json.load(open(out1))
    check("schema=flow-anomaly/v1", r.get("schema") == "flow-anomaly/v1")

    sids = {s["addr"]: s for s in r["sinks"]}
    check("sink 正例 SinkA 命中", "SinkA" in sids)
    check("Q1 型反例 SinkB 命中（双达标窗）", "SinkB" in sids)
    if "SinkB" in sids:
        bw = sids["SinkB"]["best_window"]
        check("SinkB 命中的是多来源窗（≥5 来源）", bw["source_count"] >= 5)
    check("sink 负例 SinkC/SinkD 未报", "SinkC" not in sids and "SinkD" not in sids)
    for s in r["sinks"]:
        check(f"sink {s['addr']} sources 闭合", len(s["sources"]) == s["best_window"]["source_count"])

    sp = {s["addr"]: s for s in r["sprays"]}
    check("spray 脉冲正例命中且 mode=pulse",
          "PulseSpray" in sp and sp["PulseSpray"]["mode"] == "pulse")
    if "PulseSpray" in sp:
        check("pulse recipients 闭合",
              len(sp["PulseSpray"]["recipients"]) == sp["PulseSpray"]["best_window"]["new_recipient_count"])
    check("spray 慢速正例命中且 mode=slow_spray",
          "SlowSpray" in sp and sp["SlowSpray"]["mode"] == "slow_spray",)
    if "SlowSpray" in sp:
        check("slow_spray 全史收方数=600", sp["SlowSpray"]["all_time"]["recipient_count"] == 600)

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

    return finish()


def finish():
    print(f"\n{'PASS' if not FAILS else 'FAIL'}：{len(FAILS)} 项失败")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
