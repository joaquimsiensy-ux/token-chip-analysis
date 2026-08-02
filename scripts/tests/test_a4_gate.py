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
 13. P0-01：analysis 模式拒绝 seal 外 facts/state/JSON，且不落 HTML
用法：python3 scripts/tests/test_a4_gate.py   退出码 0=PASS / 1=FAIL
"""
import base64
import json
import os
import subprocess
import sys
import tempfile
import hashlib
from pathlib import Path

from test_audit_release_gate import build_case

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
    report_path = build_case(Path(d), historical=False)

    claims = [{"id": "C1", "text": "大庄A控盘30%", "files": ["raw_transfers.jsonl"]},
              {"id": "C2", "text": "项目方已弃盘"}]
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
    state = {"whale_groups": [{"entity_id": "e1", "label": "实体1", "addresses": ["0xabc"]}],
             "provenance": {"schema_version": "2", "skill_commit": "test",
                            "data_sources": ["fixture"]}}
    wj(d, "analysis-state.json", state)
    wj(d, "facts.json", {"token": {"symbol": "TT", "decimals": 0, "total_supply_raw": "1000"},
                          "entities": {"e1": {"label": "实体1", "addresses": ["0xabc"],
                                                 "current_raw": "100", "peak_raw": "100",
                                                 "peak_date": "2026-01-01"}}, "metrics": {}})
    wj(d, "identity_gate.json", {"schema": "identity_gate_v1", "rows": [
        {"address": "0xabc", "entity": "e1", "flag": "", "resolution": ""}]})

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
    with open(report_path, "w") as f:
        f.write("# 测试报告\n\n![阵营演变](charts/final/fig1.png)\n\n正文。\n")
    registry = json.load(open(os.path.join(d, "claim_registry.json")))
    registry["report_sha256"] = hashlib.sha256(Path(report_path).read_bytes()).hexdigest()
    wj(d, "claim_registry.json", registry)
    out_html = os.path.join(d, "报告.html")
    analysis_args = ["--mode", "analysis", "--md", str(report_path), "--out", out_html,
                     "--facts", os.path.join(d, "facts.json"), "--state", os.path.join(d, "analysis-state.json"),
                     "--a4-seal", seal_p]
    p = run(BUILD, analysis_args)
    check("G9 正例 exit 0 且 HTML 写出", p.returncode == 0 and os.path.isfile(out_html))

    # P0-01：G9 验的必须就是渲染用的。案外 facts 即使结构正常也不得替换 seal 内事实。
    external = os.path.join(root, "external")
    os.makedirs(external)
    external_facts = wj(external, "facts.json", {
        "token": {"symbol": "TT", "decimals": 0, "total_supply_raw": "1000"},
        "entities": {"e1": {"label": "实体1", "addresses": ["0xabc"],
                              "current_raw": "900", "peak_raw": "900",
                              "peak_date": "2026-01-01"}}, "metrics": {}})
    p0_out = os.path.join(d, "p0_external_facts.html")
    p = run(BUILD, ["--mode", "analysis", "--md", str(report_path), "--out", p0_out,
                    "--facts", external_facts,
                    "--state", os.path.join(d, "analysis-state.json"),
                    "--a4-seal", seal_p])
    check("P0-01 seal 外 facts 拒绝且不落 HTML",
          p.returncode != 0 and not os.path.exists(p0_out))

    external_state = wj(external, "analysis-state.json", state)
    wj(external, "identity_gate.json", {"schema": "identity_gate_v1", "rows": [
        {"address": "0xabc", "entity": "e1", "flag": "", "resolution": ""}]})
    p0_state_out = os.path.join(d, "p0_external_state.html")
    p = run(BUILD, ["--mode", "analysis", "--md", str(report_path), "--out", p0_state_out,
                    "--facts", os.path.join(d, "facts.json"), "--state", external_state,
                    "--a4-seal", seal_p])
    check("P0-01 seal 外 state 拒绝且不落 HTML",
          p.returncode != 0 and not os.path.exists(p0_state_out))

    appendix = wj(d, "appendix.json", {"chip_summary": {}, "addresses": [],
                                        "unlock_events": [], "source_line": "test"})
    p0_json_out = os.path.join(d, "p0_unsealed_json.html")
    p = run(BUILD, analysis_args + ["--json", appendix, "--out", p0_json_out])
    check("P0-01 analysis 禁止未封口 JSON 附录",
          p.returncode != 0 and not os.path.exists(p0_json_out))

    # B-04：registry / verdicts / claim 引用文件任一漂移都必须拒。
    for label, path in [("registry", os.path.join(d, "a4_claims.json")),
                        ("verdicts", good_verdicts),
                        ("claim file", os.path.join(d, "raw_transfers.jsonl"))]:
        original = Path(path).read_bytes()
        Path(path).write_bytes(original + b"\n")
        if os.path.exists(out_html):
            os.unlink(out_html)
        p = run(BUILD, analysis_args)
        check(f"G9 {label} 封口后漂移拒绝", p.returncode == 1 and "封口后被改动" in p.stdout)
        Path(path).write_bytes(original)

    # B-04：字符串前缀不能替代 resolve containment；绝对路径和 symlink 同拒。
    secret = os.path.join(d, "secret.png")
    Path(secret).write_bytes(PNG)
    escape_cases = [
        ("dotdot", "charts/final/../../secret.png"),
        ("absolute", secret),
    ]
    link = os.path.join(d, "charts", "final", "link.png")
    os.symlink(secret, link)
    escape_cases.append(("symlink", "charts/final/link.png"))
    for label, image_path in escape_cases:
        bad_md = os.path.join(d, f"escape_{label}.md")
        Path(bad_md).write_text(f"# escape\n\n![x]({image_path})\n", encoding="utf-8")
        bad_out = os.path.join(d, f"escape_{label}.html")
        p = run(BUILD, ["--mode", "analysis", "--md", bad_md, "--out", bad_out,
                        "--facts", os.path.join(d, "facts.json"),
                        "--state", os.path.join(d, "analysis-state.json"),
                        "--a4-seal", seal_p])
        check(f"G9 {label} 图片越界拒绝", p.returncode == 1 and "路径非法或越界" in p.stdout
              and not os.path.exists(bad_out))
    os.unlink(link)

    # 9. 封口后改结论文件 → 编译拒且不写出
    if os.path.exists(out_html):
        os.unlink(out_html)
    with open(os.path.join(d, "findings.md"), "a") as f:
        f.write("封口后偷偷改了一句结论\n")
    p = run(BUILD, analysis_args)
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
    p = run(BUILD, ["--mode", "analysis", "--md", os.path.join(d, "报告bad.md"), "--out",
                    os.path.join(d, "bad.html"), "--facts", os.path.join(d, "facts.json"),
                    "--state", os.path.join(d, "analysis-state.json"), "--a4-seal", seal_p])
    check("G9 图不在封口目录 exit 1 不写出", p.returncode == 1
          and not os.path.isfile(os.path.join(d, "bad.html")))

    # 11. legacy 显式降级留痕
    p = run(BUILD, ["--mode", "legacy-recompile", "--degrade-reason", "历史报告重编译测试",
                    "--md", os.path.join(d, "报告bad.md"), "--out", os.path.join(d, "skip.html")])
    html_txt = open(os.path.join(d, "skip.html"), encoding="utf-8").read() \
        if os.path.isfile(os.path.join(d, "skip.html")) else ""
    check("skip reason exit 0 且理由入 HTML 注释", p.returncode == 0 and "历史报告重编译测试" in html_txt)

    # 12. analysis 不带 seal 必须拒；update 模式可显式降级无 seal 编译
    p = run(BUILD, ["--mode", "analysis", "--md", os.path.join(d, "报告bad.md"),
                    "--out", os.path.join(d, "noseal.html")])
    check("analysis 无 --a4-seal 拒绝", p.returncode != 0)
    p = run(BUILD, ["--mode", "update", "--degrade-reason", "增量更新不重跑 A4",
                    "--md", os.path.join(d, "报告bad.md"), "--out", os.path.join(d, "update.html")])
    check("update 显式降级无 seal 可编译", p.returncode == 0)

    print("=" * 40)
    if FAILS:
        print(f"a4_gate 契约测试 {len(FAILS)} 项失败")
        return 1
    print("a4_gate 契约测试全部通过（21 项）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
