#!/usr/bin/env python3
"""a4_gate + build_html G9 契约测试（离线，黑盒 subprocess 调 CLI）。

覆盖（A4→A5 顺序闸的反例集，6.7.0）：
  1. register 正例 → exit 0，a4_claims.json 落盘
  2. register 空数组 / 重复 id → exit 2
  3. finalize 未 register → exit 2
  4. finalize 正例（全覆盖裁决+封口）→ exit 0，a4_seal.json verdict=PASS
  5. finalize 缺一条裁决 / 多一条未登记裁决 → exit 2
  6. finalize verdict 非法 / WEAKENED 无 revision_note → exit 2
  7. finalize charts/final 非空 → exit 2；清空后 → exit 0
  8. G9 正例：seal PASS + 图在 charts/final/ → build_html exit 0 且 HTML 写出
  9. G9 封口后改结论文件 → exit 1 且 HTML **未写出**（gate 前置，不再先落盘再报错）
 10. G9 报告图不在 charts/final/ → exit 1 不写出
 11. --skip-a4-gate-reason → exit 0 写出且 HTML 注释含理由
 12. 不传 --a4-seal（update 流程场景）→ G9 不触发照常编译
用法：python3 scripts/tests/test_a4_gate.py   退出码 0=PASS / 1=FAIL
"""
import base64
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(HERE, "..", "report", "a4_gate.py")
BUILD = os.path.join(HERE, "..", "report", "build_html.py")
FAILS = []

# 1x1 透明 png（最小合法图片，供 embed_img 读取）
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")


def check(name, cond):
    if not cond:
        FAILS.append(name)
        print(f"FAIL  {name}")
    else:
        print(f"ok    {name}")


def run(script, args):
    return subprocess.run([sys.executable, script] + args, capture_output=True, text=True)


def wj(d, name, obj):
    p = os.path.join(d, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    return p


def main():
    root = tempfile.mkdtemp(prefix="a4_gate_test_")
    d = os.path.join(root, "case")
    os.makedirs(d)

    claims = [{"id": "C1", "text": "大庄A控盘30%"}, {"id": "C2", "text": "项目方已弃盘"}]
    cf = wj(d, "claims_in.json", claims)

    # 1/2. register
    p = run(GATE, ["register", "--case-dir", d, "--claims-file", cf])
    check("register 正例 exit 0", p.returncode == 0 and os.path.isfile(os.path.join(d, "a4_claims.json")))
    p = run(GATE, ["register", "--case-dir", d, "--claims-file", wj(d, "empty.json", [])])
    check("register 空数组 exit 2", p.returncode == 2)
    p = run(GATE, ["register", "--case-dir", d, "--claims-file",
                   wj(d, "dup.json", [{"id": "X", "text": "a"}, {"id": "X", "text": "b"}])])
    check("register 重复 id exit 2", p.returncode == 2)

    # 3. finalize 未 register（新目录）
    d3 = os.path.join(root, "case_noreg")
    os.makedirs(d3)
    p = run(GATE, ["finalize", "--case-dir", d3, "--verdicts-file", cf, "--seal-files", "x.md"])
    check("finalize 未 register exit 2", p.returncode == 2)

    # 准备终版结论文件
    with open(os.path.join(d, "findings.md"), "w") as f:
        f.write("# findings\n复核后终版结论\n")
    wj(d, "analysis-state.json", {"whale_groups": []})

    # 5/6. finalize 反例集
    p = run(GATE, ["finalize", "--case-dir", d, "--seal-files", "findings.md",
                   "--verdicts-file", wj(d, "v_miss.json", [{"id": "C1", "verdict": "CONFIRMED"}])])
    check("finalize 缺一条裁决 exit 2", p.returncode == 2)
    p = run(GATE, ["finalize", "--case-dir", d, "--seal-files", "findings.md",
                   "--verdicts-file", wj(d, "v_extra.json",
                                         [{"id": "C1", "verdict": "CONFIRMED"},
                                          {"id": "C2", "verdict": "CONFIRMED"},
                                          {"id": "C9", "verdict": "CONFIRMED"}])])
    check("finalize 多一条未登记裁决 exit 2", p.returncode == 2)
    p = run(GATE, ["finalize", "--case-dir", d, "--seal-files", "findings.md",
                   "--verdicts-file", wj(d, "v_bad.json",
                                         [{"id": "C1", "verdict": "MAYBE"},
                                          {"id": "C2", "verdict": "CONFIRMED"}])])
    check("finalize verdict 非法 exit 2", p.returncode == 2)
    p = run(GATE, ["finalize", "--case-dir", d, "--seal-files", "findings.md",
                   "--verdicts-file", wj(d, "v_nonote.json",
                                         [{"id": "C1", "verdict": "WEAKENED"},
                                          {"id": "C2", "verdict": "CONFIRMED"}])])
    check("finalize WEAKENED 无 revision_note exit 2", p.returncode == 2)

    good_verdicts = wj(d, "v_ok.json", [{"id": "C1", "verdict": "WEAKENED",
                                         "revision_note": "份额 30%→22%，重算修正"},
                                        {"id": "C2", "verdict": "CONFIRMED"}])

    # 7. charts/final 非空拒封
    os.makedirs(os.path.join(d, "charts", "final"))
    with open(os.path.join(d, "charts", "final", "premature.png"), "wb") as f:
        f.write(PNG)
    p = run(GATE, ["finalize", "--case-dir", d, "--seal-files", "findings.md,analysis-state.json",
                   "--verdicts-file", good_verdicts])
    check("finalize charts/final 非空 exit 2", p.returncode == 2)
    os.unlink(os.path.join(d, "charts", "final", "premature.png"))

    # 4. finalize 正例
    p = run(GATE, ["finalize", "--case-dir", d, "--seal-files", "findings.md,analysis-state.json",
                   "--verdicts-file", good_verdicts])
    seal_p = os.path.join(d, "a4_seal.json")
    check("finalize 正例 exit 0 且 seal PASS", p.returncode == 0 and os.path.isfile(seal_p)
          and json.load(open(seal_p))["verdict"] == "PASS")

    # 8. G9 正例：图在 charts/final/，编译过
    with open(os.path.join(d, "charts", "final", "fig1.png"), "wb") as f:
        f.write(PNG)
    with open(os.path.join(d, "报告.md"), "w") as f:
        f.write("# 测试报告\n\n![阵营演变](charts/final/fig1.png)\n\n正文。\n")
    out_html = os.path.join(d, "报告.html")
    p = run(BUILD, ["--md", os.path.join(d, "报告.md"), "--out", out_html, "--a4-seal", seal_p])
    check("G9 正例 exit 0 且 HTML 写出", p.returncode == 0 and os.path.isfile(out_html))

    # 9. 封口后改结论文件 → 编译拒且不写出
    os.unlink(out_html)
    with open(os.path.join(d, "findings.md"), "a") as f:
        f.write("封口后偷偷改了一句结论\n")
    p = run(BUILD, ["--md", os.path.join(d, "报告.md"), "--out", out_html, "--a4-seal", seal_p])
    check("G9 封口后改结论 exit 1", p.returncode == 1 and "封口后被改动" in p.stdout)
    check("G9 拒绝时 HTML 未写出（gate 前置）", not os.path.isfile(out_html))
    # 翻案重封的真实流程：旧图作废（基于被推翻的结论）→ 清空 charts/final → finalize → 重画
    p = run(GATE, ["finalize", "--case-dir", d, "--seal-files", "findings.md,analysis-state.json",
                   "--verdicts-file", good_verdicts])
    check("重封时 charts/final 留旧图被拒 exit 2（旧图必须作废）", p.returncode == 2)
    os.unlink(os.path.join(d, "charts", "final", "fig1.png"))
    p = run(GATE, ["finalize", "--case-dir", d, "--seal-files", "findings.md,analysis-state.json",
                   "--verdicts-file", good_verdicts])
    check("清旧图后重跑 finalize 重新封口 exit 0", p.returncode == 0)

    # 10. 图不在 charts/final/
    os.makedirs(os.path.join(d, "charts", "draft"), exist_ok=True)
    with open(os.path.join(d, "charts", "draft", "old.png"), "wb") as f:
        f.write(PNG)
    with open(os.path.join(d, "报告bad.md"), "w") as f:
        f.write("# 测试\n\n![旧图](charts/draft/old.png)\n")
    p = run(BUILD, ["--md", os.path.join(d, "报告bad.md"), "--out",
                    os.path.join(d, "bad.html"), "--a4-seal", seal_p])
    check("G9 图不在封口目录 exit 1 不写出", p.returncode == 1
          and not os.path.isfile(os.path.join(d, "bad.html")))

    # 11. skip reason 留痕
    p = run(BUILD, ["--md", os.path.join(d, "报告bad.md"), "--out", os.path.join(d, "skip.html"),
                    "--skip-a4-gate-reason", "历史报告重编译测试"])
    html_txt = open(os.path.join(d, "skip.html"), encoding="utf-8").read() \
        if os.path.isfile(os.path.join(d, "skip.html")) else ""
    check("skip reason exit 0 且理由入 HTML 注释", p.returncode == 0 and "历史报告重编译测试" in html_txt)

    # 12. 不传 --a4-seal 不触发 G9（update 流程）
    p = run(BUILD, ["--md", os.path.join(d, "报告bad.md"), "--out", os.path.join(d, "noseal.html")])
    check("无 --a4-seal 不触发 G9 照常编译", p.returncode == 0)

    print("=" * 40)
    if FAILS:
        print(f"a4_gate 契约测试 {len(FAILS)} 项失败")
        return 1
    print("a4_gate 契约测试全部通过（18 项）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
