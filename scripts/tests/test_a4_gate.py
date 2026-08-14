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
 11. legacy-recompile 用 mode 水印说明降级，且不存在任何 skip gate CLI
 12. 不传 --a4-seal 的正式流程拒绝；已删除的非正式旁路同样拒绝
 13. P0-01/D-06：analysis 拒绝 seal 外 facts/state/JSON，但允许已封口监控 JSON
用法：python3 scripts/tests/test_a4_gate.py   退出码 0=PASS / 1=FAIL
"""
import base64
import json
import os
import subprocess
import sys
import tempfile
import hashlib
import shutil
from pathlib import Path

from test_audit_release_gate import build_case, refresh_adversarial, sha
from formal_ready_test_harness import run_formal_script
from identity_gate_fixture import augment_gate

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(HERE, "..", "report", "a4_gate.py")
BUILD = os.path.join(HERE, "..", "report", "build_html.py")
A5 = os.path.join(HERE, "..", "report", "a5_report_seal.py")
DIST = os.path.join(HERE, "..", "report", "holder_distribution_scan.py")
FAILS = []
ENTITY_ADDR = "0x" + "a" * 40

# 1x1 透明 png（最小合法图片，供 embed_img 读取）
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")


def check(name, cond, details=""):
    if not cond:
        FAILS.append(name)
        print(f"FAIL  {name}")
        if details:
            print(details)
    else:
        print(f"ok    {name}")


def run(script, args):
    if script == GATE and args[:1] == ["finalize"] and "--workflow-type" not in args:
        args = args + ["--workflow-type", "independent-audit"]
    if script == BUILD and "--mode" in args and args[args.index("--mode") + 1] in {"analysis-new", "analysis-audit"} \
            and "--a5-seal" not in args and "--md" in args and "--a4-seal" in args:
        md = Path(args[args.index("--md") + 1]).resolve()
        a4 = Path(args[args.index("--a4-seal") + 1]).resolve()
        a5 = md.parent / "a5_report_seal.json"
        made = run_formal_script(A5, ["--case-dir", str(md.parent),
                                      "--report", str(md), "--a4-seal", str(a4),
                                      "--out", str(a5)])
        args = args + ["--a5-seal", str(a5)]
    return run_formal_script(script, args)


def wj(d, name, obj):
    p = os.path.join(d, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    return p


def rebind_case_inputs(old_root, new_root):
    """把 copytree 复制出来的案子的收据输入，重新指到它自己那份拷贝上。

    发布校验器要求 supply_truth 绑定的 replay_stats 实物落在**当前**案根内
    （见 shared_release_receipt._bound_replay_totals：案外实物人工翻案子时看不见，
    是伪造账本的天然藏身处）；同一个校验器对 Solana 的 observation bundle 和
    tolerance waiver 早就是这个要求。复制出来的案子照理该"重跑生产者"，
    这个帮手就是把重跑会得到的结果直接摆好：文件是逐字节拷贝，size/sha 都不变，
    只有收据里记的绝对路径要跟着搬家。
    """
    old_root = str(Path(old_root).resolve())
    new_root = str(Path(new_root).resolve())
    recon_path = Path(new_root, "reconciliation_report.json")
    recon = json.loads(recon_path.read_text(encoding="utf-8"))
    for item in recon["checks"].values():
        receipt_path = Path(new_root, item["receipt"]["path"])
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        moved = False
        for ref in (receipt.get("inputs") or {}).values():
            raw = str(ref.get("path", ""))
            if raw.startswith(old_root + os.sep):
                ref["path"] = new_root + raw[len(old_root):]
                moved = True
        if moved:
            receipt_path.write_text(json.dumps(receipt, ensure_ascii=False),
                                    encoding="utf-8")
            item["receipt"]["sha256"] = sha(receipt_path)
    recon_path.write_text(json.dumps(recon, ensure_ascii=False), encoding="utf-8")
    shared_path = Path(new_root, "shared_release_receipt.json")
    shared = json.loads(shared_path.read_text(encoding="utf-8"))
    shared["inputs"]["reconciliation_report.json"]["sha256"] = sha(recon_path)
    shared_path.write_text(json.dumps(shared, ensure_ascii=False), encoding="utf-8")


def bind_balance_receipt_to_snapshot(d, snap):
    """四查 balance 收据与分布扫描必须吃同一份 owner 快照（发布闸 F-03 第二层交叉检查）。"""
    receipt_path = Path(d, "balance_receipt.json")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["inputs"]["balances"] = {"path": str(snap.resolve()),
                                     "size": snap.stat().st_size, "sha256": sha(snap)}
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False), encoding="utf-8")
    recon_path = Path(d, "reconciliation_report.json")
    recon = json.loads(recon_path.read_text(encoding="utf-8"))
    recon["checks"]["balance"]["receipt"]["sha256"] = sha(receipt_path)
    recon_path.write_text(json.dumps(recon, ensure_ascii=False), encoding="utf-8")
    shared_path = Path(d, "shared_release_receipt.json")
    shared = json.loads(shared_path.read_text(encoding="utf-8"))
    shared["inputs"]["reconciliation_report.json"]["sha256"] = sha(recon_path)
    shared_path.write_text(json.dumps(shared, ensure_ascii=False), encoding="utf-8")


def add_distribution_initial(d):
    Path(d, "data").mkdir(exist_ok=True)
    # 分布快照必须与案根真实 replay 产物同源：这个案子的 replay_stats.json（mint=100）、
    # balances_final.json（sum=100）、identity_gate（total=100）是 audit 链真跑 replay_pass1
    # 得到的一整套自洽产物，G8 identity_gate 靠它们互证。分布闭合锚点走 replay 侧 mint_total，
    # 所以直接用案内 balances_final.json 当 owner 快照，全案同一个 100——不再另造 240-owner
    # 快照制造两套冲突的供给量。owner 少落 low_sample 是合法终态。
    bf = json.loads(Path(d, "balances_final.json").read_text(encoding="utf-8"))
    balances = bf if isinstance(bf, dict) else {r.get("owner", r.get("address")):
                                                r.get("balance_raw", r.get("raw")) for r in bf}
    total = sum(int(v) for v in balances.values())
    snap = Path(d, "data/holders_owners.json")
    snap.write_text(json.dumps(balances), encoding="utf-8")
    bind_balance_receipt_to_snapshot(d, snap)
    # B-7（批 D）：三账成员同步到本案真实 owner 世界（等值绑定后 0xabc 型编造成员必拦）
    from test_audit_release_gate import align_ledgers_to_owner_snapshot
    align_ledgers_to_owner_snapshot(Path(d), snap)
    wj(d, "candidate_screening.json", {"schema": "candidate-screening/v1",
                                         "auto_excluded_candidate": []})
    wj(d, "supply_truth.json", {"verdict": "PASS", "exit_code": 0,
                                  "chain": "bsc", "onchain_total_supply": str(total),
                                  "replay_net": str(total), "mint_total": str(total),
                                  "burn_total": "0", "decision_rule": "primary_form1",
                                  "total_supply_raw": str(total), "net_supply_raw": str(total)})
    wj(d, "data_map.json", {"files": [{"path": "data/holders_owners.json",
                                          "sha256": hashlib.sha256(snap.read_bytes()).hexdigest()}]})
    # 案根 replay_stats.json 保持不动（mint=100 与本快照同源），闭合锚点走它。
    p = run_formal_script(DIST, ["--case-dir", d, "--stage", "initial"])
    assert p.returncode == 0, p.stdout + p.stderr


def finish_distribution_normal(d):
    wj(d, "handoff_manifest.json", {"consumer_min_schema": "handoff/v3", "status": "READY",
                                      "run_id": "fixture-ready"})
    wj(d, "identity_snapshot_receipt.json", {"schema": "identity-snapshot-receipt/v1"})
    wj(d, "entity_freeze.json", {"schema": "entity-freeze/v1", "revisions": []})
    for name in ("membership_ledger.json", "position_ledger.json", "economic_control_ledger.json",
                 "address_classification.json"):
        if not Path(d, name).is_file():
            wj(d, name, {"rows": []})
    p = run_formal_script(DIST, ["--case-dir", d, "--stage", "final", "--round", "1"])
    assert p.returncode == 0, p.stdout + p.stderr
    p = run_formal_script(DIST, ["record-round", "--case-dir", d,
                                 "--scan", "dist_rounds/round_1/distribution_scan.json"])
    assert p.returncode == 0, p.stdout + p.stderr
    # 分布终态可能是 NORMAL_SHAPE 或 low_sample（本案 owner 少落 low_sample）——
    # A5 seal 对两者要求不同的强制披露句，按 final scan verdict 选对应句。
    final_scan = json.loads(Path(d, "dist_rounds/round_1/distribution_scan.json").read_text(encoding="utf-8"))
    sentence = ("形态统计因样本不足未做,以逐址集中度事实替代"
                if final_scan.get("not_evaluable_reason") == "low_sample"
                else "当前快照呈正常形态;这只表示本闸未检出结构性畸形,不等于没有庄。")
    report = Path(d, "report.md")
    report.write_text(report.read_text(encoding="utf-8")
                      + f"\n{sentence}\n"
                      + "\n![持仓分布](charts/final/holder_distribution_current.png)\n",
                      encoding="utf-8")


def main():
    root = tempfile.mkdtemp(prefix="a4_gate_test_")
    d = os.path.join(root, "case")
    os.makedirs(d)
    report_path = build_case(Path(d), historical=False)

    registry = json.load(open(os.path.join(d, "claim_registry.json")))
    registry["claims"] = [
        {"claim_id": "C1", "statement": "大庄A控盘30%", "claim_type": "snapshot_balance",
         "report_locations": ["report.md:1"], "verdict": "weakened",
         "evidence_files": ["raw_transfers.jsonl"]},
        {"claim_id": "C2", "statement": "项目方已弃盘", "claim_type": "snapshot_balance",
         "report_locations": ["report.md:1"], "verdict": "confirmed",
         "evidence_files": ["raw_transfers.jsonl"],
         "reproduce_receipt": "reproduce_receipt.json",
         "counter_hypotheses": ["暂时静置"], "blocking_unresolved": False},
    ]
    wj(d, "claim_registry.json", registry)
    claims = [{"id": "C1", "text": "大庄A控盘30%", "files": ["raw_transfers.jsonl"],
               "report_locations": ["report.md:1"]},
              {"id": "C2", "text": "项目方已弃盘", "files": ["raw_transfers.jsonl"],
               "report_locations": ["report.md:1"]}]
    cf = wj(d, "claims_in.json", claims)

    # 1/2. register
    p = run(GATE, ["register", "--case-dir", d, "--claims-file", cf])
    check("register 正例 exit 0", p.returncode == 0 and os.path.isfile(os.path.join(d, "a4_claims.json")))
    p = run(GATE, ["register", "--case-dir", d, "--claims-file", wj(d, "empty.json", [])])
    check("register 空数组 exit 2", p.returncode == 2)
    p = run(GATE, ["register", "--case-dir", d, "--claims-file",
                   wj(d, "dup.json", [{"id": "X", "text": "a"}, {"id": "X", "text": "b"}])])
    check("register 重复 id exit 2", p.returncode == 2)

    # Round4 P1-02：register 后磁盘 registry 被篡改，finalize 必须重跑同一验证器。
    reg_path = Path(d, "a4_claims.json")
    original_reg = reg_path.read_text(encoding="utf-8")
    tampered = json.loads(original_reg)
    tampered["claims"].append({"id": "C1", "text": "第二条同 ID 命题", "files": []})
    reg_path.write_text(json.dumps(tampered), encoding="utf-8")
    p = run(GATE, ["finalize", "--case-dir", d, "--verdicts-file",
                   wj(d, "v_dup_registry.json", [{"id": "C1", "verdict": "CONFIRMED"},
                                                   {"id": "C2", "verdict": "CONFIRMED"}]),
                   "--seal-files", "raw_transfers.jsonl"])
    check("Round4 P1-02 finalize 重验重复 claim id", p.returncode == 2 and "id 重复" in p.stderr)
    tampered = json.loads(original_reg)
    tampered["claims"][0]["text"] = ""
    reg_path.write_text(json.dumps(tampered), encoding="utf-8")
    p = run(GATE, ["finalize", "--case-dir", d, "--verdicts-file",
                   wj(d, "v_empty_registry.json", [{"id": "C1", "verdict": "CONFIRMED"},
                                                     {"id": "C2", "verdict": "CONFIRMED"}]),
                   "--seal-files", "raw_transfers.jsonl"])
    check("Round4 P1-02 同族空文本失败分支", p.returncode == 2 and "空 text" in p.stderr)
    reg_path.write_text(original_reg, encoding="utf-8")
    # register 已替换执行态权威表；重跑结构化复核及共享 receipt，保持真实 A4 顺序。
    refresh_adversarial(Path(d))
    from shared_release_receipt import create_bundle
    create_bundle(Path(d))

    # 3. finalize 未 register（新目录）
    d3 = os.path.join(root, "case_noreg")
    os.makedirs(d3)
    p = run(GATE, ["finalize", "--case-dir", d3, "--verdicts-file", cf, "--seal-files", "x.md"])
    check("finalize 未 register exit 2", p.returncode == 2)

    # 准备终版结论文件
    with open(os.path.join(d, "findings.md"), "w") as f:
        f.write("# findings\n复核后终版结论\n")
    state = {"chain": "bsc", "whale_groups": [
                 {"entity_id": "e1", "label": "实体1", "addresses": [ENTITY_ADDR]}],
             "provenance": {"schema_version": "2", "skill_commit": "test",
                            "data_sources": ["fixture"]}}
    state_path = wj(d, "analysis-state.json", state)
    wj(d, "facts.json", {"token": {"symbol": "TT", "decimals": 0, "total_supply_raw": "1000"},
                          "entities": {"e1": {"label": "实体1", "addresses": [ENTITY_ADDR],
                                                 "current_raw": "100", "peak_raw": "100",
                                                 "peak_date": "2026-01-01"}}, "metrics": {}})
    identity = augment_gate(d, {"chain": "bsc",
        "state_file": "analysis-state.json",
        "state_sha256": hashlib.sha256(Path(state_path).read_bytes()).hexdigest(),
        "n_addresses": 1, "n_flags": 0, "rows": [
        {"address": ENTITY_ADDR, "entity": "e1", "share_pct": None,
         "label": {"name": "fixture", "category": "other", "tier": "identity", "source": "test"},
         "on_curve": None, "flag": "", "resolution": ""}]}, chain="bsc")
    wj(d, "identity_gate.json", identity)

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

    # D-06：用户确认买入后，监控附录进入 seal 即可维持正式报告身份。
    sealed_appendix = wj(d, "appendix.json", {"chip_summary": {}, "addresses": [],
                                                "unlock_events": [], "source_line": "test"})
    p = run(GATE, ["finalize", "--case-dir", d,
                   "--seal-files", "findings.md,analysis-state.json,appendix.json",
                   "--verdicts-file", good_verdicts])
    sealed_json_out = os.path.join(d, "sealed_json.html")
    p_build = run(BUILD, ["--mode", "analysis-audit", "--md", str(report_path),
                          "--out", sealed_json_out, "--facts", os.path.join(d, "facts.json"),
                          "--state", os.path.join(d, "analysis-state.json"),
                          "--a4-seal", seal_p, "--json", sealed_appendix])
    check("D-06 已封口监控 JSON 可走正式构建",
          p.returncode == 0 and p_build.returncode == 0 and os.path.isfile(sealed_json_out))

    # P1-05：全新分析走共享门禁，不伪造净室资产；seal 轨道不可互换。
    new_d = os.path.join(root, "case_new")
    shutil.copytree(d, new_d)
    rebind_case_inputs(d, new_d)
    for name in ("audit_input_manifest.json", "claim_registry.json", "reproduce_audit.py",
                 "reproduce_receipt.json", "reproduce_output.json", "a5_report_seal.json"):
        Path(new_d, name).unlink(missing_ok=True)
    add_distribution_initial(new_d)
    p = run(GATE, ["finalize", "--case-dir", new_d,
                   "--seal-files", "findings.md,analysis-state.json",
                   "--verdicts-file", os.path.join(new_d, "v_ok.json"),
                   "--workflow-type", "new-analysis"])
    new_seal = os.path.join(new_d, "a4_seal.json")
    finish_distribution_normal(new_d)
    # F-C5（批 C 消化轮）：figure2 对账收据成为 new-analysis 必经资产——
    # 由真实生产者（figures_from_facts check）产出，空 whale_series 合法 PASS
    Path(new_d, "whale_series.json").write_text("[]", encoding="utf-8")
    p_chk = run(os.path.join(HERE, "..", "report", "figures_from_facts.py"),
                ["check", "--facts", os.path.join(new_d, "facts.json"),
                 "--series", os.path.join(new_d, "whale_series.json")])
    assert p_chk.returncode == 0 and os.path.isfile(
        os.path.join(new_d, "figure2_check_receipt.json")), \
        f"figure2 收据生成失败: {p_chk.stdout} {p_chk.stderr}"
    new_out = os.path.join(new_d, "new.html")
    p_build = run(BUILD, ["--mode", "analysis-new", "--md", os.path.join(new_d, "report.md"),
                          "--out", new_out, "--facts", os.path.join(new_d, "facts.json"),
                          "--state", os.path.join(new_d, "analysis-state.json"),
                          "--a4-seal", new_seal])
    check("P1-05 全新分析无净室资产仍过必经共享门禁",
          p.returncode == 0 and p_build.returncode == 0 and os.path.isfile(new_out),
          p.stdout + p.stderr + p_build.stdout + p_build.stderr)

    # 8. G9 正例：图在 charts/final/，编译过
    with open(report_path, "w") as f:
        f.write("# 测试报告\n\n![阵营演变](charts/final/fig1.png)\n\n正文。\n")
    registry = json.load(open(os.path.join(d, "claim_registry.json")))
    registry["report_sha256"] = hashlib.sha256(Path(report_path).read_bytes()).hexdigest()
    wj(d, "claim_registry.json", registry)
    p = run(GATE, ["finalize", "--case-dir", d,
                   "--seal-files", "findings.md,analysis-state.json",
                   "--verdicts-file", good_verdicts])
    check("P1-06 终版 claim registry 对账后重封口", p.returncode == 0)
    with open(os.path.join(d, "charts", "final", "fig1.png"), "wb") as f:
        f.write(PNG)
    out_html = os.path.join(d, "报告.html")
    analysis_args = ["--mode", "analysis-audit", "--md", str(report_path), "--out", out_html,
                     "--facts", os.path.join(d, "facts.json"), "--state", os.path.join(d, "analysis-state.json"),
                     "--a4-seal", seal_p]
    p = run(BUILD, analysis_args)
    check("G9 正例 exit 0 且 HTML 写出", p.returncode == 0 and os.path.isfile(out_html))
    mismatch_out = os.path.join(d, "workflow_mismatch.html")
    p = run(BUILD, [*analysis_args[:1], "analysis-new", *analysis_args[2:],
                    "--out", mismatch_out])
    check("P1-05 audit seal 不得降级当 new-analysis 构建",
          p.returncode != 0 and "workflow_type" in p.stdout and not os.path.exists(mismatch_out))

    # P0-01：G9 验的必须就是渲染用的。案外 facts 即使结构正常也不得替换 seal 内事实。
    external = os.path.join(root, "external")
    os.makedirs(external)
    external_facts = wj(external, "facts.json", {
        "token": {"symbol": "TT", "decimals": 0, "total_supply_raw": "1000"},
        "entities": {"e1": {"label": "实体1", "addresses": [ENTITY_ADDR],
                              "current_raw": "900", "peak_raw": "900",
                              "peak_date": "2026-01-01"}}, "metrics": {}})
    p0_out = os.path.join(d, "p0_external_facts.html")
    p = run(BUILD, ["--mode", "analysis-audit", "--md", str(report_path), "--out", p0_out,
                    "--facts", external_facts,
                    "--state", os.path.join(d, "analysis-state.json"),
                    "--a4-seal", seal_p])
    check("P0-01 seal 外 facts 拒绝且不落 HTML",
          p.returncode != 0 and not os.path.exists(p0_out))

    external_state = wj(external, "analysis-state.json", state)
    wj(external, "identity_gate.json", {"schema": "identity_gate_v2", "chain": "bsc",
        "state_file": "analysis-state.json",
        "state_sha256": hashlib.sha256(Path(external_state).read_bytes()).hexdigest(),
        "n_addresses": 1, "n_flags": 0, "rows": [
        {"address": ENTITY_ADDR, "entity": "e1", "share_pct": None,
         "label": {"name": "fixture", "category": "other", "tier": "identity", "source": "test"},
         "on_curve": None, "flag": "", "resolution": ""}]})
    p0_state_out = os.path.join(d, "p0_external_state.html")
    p = run(BUILD, ["--mode", "analysis-audit", "--md", str(report_path), "--out", p0_state_out,
                    "--facts", os.path.join(d, "facts.json"), "--state", external_state,
                    "--a4-seal", seal_p])
    check("P0-01 seal 外 state 拒绝且不落 HTML",
          p.returncode != 0 and not os.path.exists(p0_state_out))

    appendix = wj(d, "unsealed_appendix.json", {"chip_summary": {}, "addresses": [],
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
        p = run(BUILD, ["--mode", "analysis-audit", "--md", bad_md, "--out", bad_out,
                        "--facts", os.path.join(d, "facts.json"),
                        "--state", os.path.join(d, "analysis-state.json"),
                        "--a4-seal", seal_p])
        check(f"G9 {label} 图片越界拒绝", p.returncode == 1 and not os.path.exists(bad_out))
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
    p = run(BUILD, ["--mode", "analysis-audit", "--md", os.path.join(d, "报告bad.md"), "--out",
                    os.path.join(d, "bad.html"), "--facts", os.path.join(d, "facts.json"),
                    "--state", os.path.join(d, "analysis-state.json"), "--a4-seal", seal_p])
    check("G9 图不在封口目录 exit 1 不写出", p.returncode == 1
          and not os.path.isfile(os.path.join(d, "bad.html")))

    # 11. legacy 显式降级留痕
    p = run(BUILD, ["--mode", "legacy-recompile", "--degrade-reason", "历史报告重编译测试",
                    "--md", os.path.join(d, "报告bad.md"), "--out", os.path.join(d, "skip.html")])
    html_txt = open(os.path.join(d, "skip.html"), encoding="utf-8").read() \
        if os.path.isfile(os.path.join(d, "skip.html")) else ""
    check("legacy 降级理由入 HTML 注释", p.returncode == 0 and "历史报告重编译测试" in html_txt)

    # 12. analysis 不带 seal 必须拒；已删除的 update 模式必须拒绝
    p = run(BUILD, ["--mode", "analysis-audit", "--md", os.path.join(d, "报告bad.md"),
                    "--out", os.path.join(d, "noseal.html")])
    check("analysis 无 --a4-seal 拒绝", p.returncode != 0)
    p = run(BUILD, ["--mode", "update", "--degrade-reason", "已删除模式",
                    "--md", os.path.join(d, "报告bad.md"), "--out", os.path.join(d, "update.html")])
    check("已删除的 update 模式被拒绝", p.returncode != 0)

    help_text = run(BUILD, ["--help"]).stdout
    check("D-07 help 不再暴露不可达 skip gate 参数",
          "--skip-identity-gate" not in help_text and "--skip-a4-gate-reason" not in help_text)

    print("=" * 40)
    if FAILS:
        print(f"a4_gate 契约测试 {len(FAILS)} 项失败")
        return 1
    print("a4_gate 契约测试全部通过（23 项）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
