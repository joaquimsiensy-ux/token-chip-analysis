#!/usr/bin/env python3
"""W2 closeout offline contract tests; real A4/distribution fixture producers."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path[:0] = [str(HERE), str(REPO / "scripts/report"), str(REPO / "scripts/lib"), str(REPO / "scripts/prices")]
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("MPLCONFIGDIR", tempfile.mkdtemp(prefix="w2-mpl-"))
import test_a4_gate as fixture
from test_audit_release_gate import build_case, build_facts_from_ledgers, gate
from identity_gate_fixture import augment_gate
from formal_ready_test_harness import run_formal_script, test_vertical_slices


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def add_provenance_ledger(case):
    path = case / "provenance_ledger.json"
    ledger = read(path) if path.exists() else {
        "schema": "provenance-ledger/v2", "total_supply_raw": "100", "entities": []}
    files = {}
    for name, source in (("entity_source_trace.py", REPO / "scripts/report/entity_source_trace.py"),
                         ("wave_scan.py", REPO / "scripts/report/wave_scan.py"),
                         ("sqd_cache_identity.py", REPO / "scripts/solana/sqd_cache_identity.py")):
        files[name] = {"path": str(source.resolve()), "bytes": source.stat().st_size, "sha256": sha(source)}
    ledger.setdefault("input_binding", {})["algorithm"] = {
        "script_sha256": files["entity_source_trace.py"]["sha256"], "files": files}
    write(path, ledger)


def build_release_case(root):
    root = Path(root)
    source = root / "source"
    source.mkdir(parents=True)
    build_case(source)
    case = root / "case"
    # Omit the six clean-room-only artifacts while copying; no bulk deletion.
    shutil.copytree(source, case, ignore=shutil.ignore_patterns(
        "audit_input_manifest.json", "claim_registry.json", "reproduce_audit.py",
        "reproduce_receipt.json", "reproduce_output.json", "a5_report_seal.json"))
    fixture.rebind_case_inputs(source, case)
    (case / "findings.md").write_text("# findings\n复核后终版结论\n", encoding="utf-8")
    state = {"chain": "bsc", "token": {"chain": "bsc"}, "whale_groups": [
        {"entity_id": "e1", "label": "大庄#1", "addresses": ["0xabc"]}],
        "provenance": {"schema_version": "2", "skill_commit": "test", "data_sources": ["fixture"]}}
    write(case / "analysis-state.json", state)
    identity = augment_gate(str(case), {"chain": "bsc", "state_file": "analysis-state.json",
        "state_sha256": sha(case / "analysis-state.json"), "n_addresses": 1, "n_flags": 0,
        "rows": [{"address": "0xabc", "entity": "e1", "share_pct": None,
                  "label": {"name": "fixture", "category": "other", "tier": "identity", "source": "test"},
                  "on_curve": None, "flag": "", "resolution": ""}]}, chain="bsc")
    write(case / "identity_gate.json", identity)
    write(case / "v_ok.json", [{"id": "C1", "verdict": "CONFIRMED"}])
    fixture.add_distribution_initial(str(case))
    fixture.add_camp_series(str(case))
    add_provenance_ledger(case)   # reseal prereq 同款，先于 facts build 落盘（facts.provenance.inputs 绑它）
    build_facts_from_ledgers(case, labels={"e1": "大庄#1"})
    proc = fixture.run(fixture.GATE, ["finalize", "--case-dir", str(case),
        "--workflow-type", "new-analysis", "--seal-files", "findings.md,analysis-state.json",
        "--verdicts-file", str(case / "v_ok.json")])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    fixture.finish_distribution_normal(str(case))
    return case


CLOSEOUT = REPO / "scripts/report/stage2_closeout.py"
FIGURES = REPO / "scripts/report/figures_from_facts.py"


def cli(case, command="check", *args):
    return run_formal_script(CLOSEOUT, [command, "--case-dir", str(case), "--report", "report.md", *args])


def write_price_receipt(case, second_price, out="price_checks.json", prices="price_series.json"):
    """F05：收据由真实 price_check.py 生成（第二源离线 stub），不手写 PASS。返回退出码（PASS/WARN 0、FAIL 2、ALL_SKIP 3、fatal 1）。"""
    import price_check
    from unittest import mock
    argv = ["price_check.py", "--price-file", str(case / prices), "--source", "coingecko",
            "--chain", "bsc", "--addr", "0x" + "1" * 40, "--out", str(case / out)]
    with mock.patch.object(sys, "argv", argv), mock.patch.object(
            price_check, "second_llama", return_value=(second_price, "offline")):
        try:
            price_check.main()
            return 0
        except SystemExit as exc:
            return int(exc.code) if isinstance(exc.code, int) else 1


def build_closeout_case(root) -> Path:
    case = build_release_case(root)
    write(case / "entity_series.json", {"dates": ["2026-01-01"], "e1": [100.0]})
    proc = run_formal_script(FIGURES, ["fig2-series", "--entity-series", str(case / "entity_series.json"),
        "--keys", "e1", "--labels-from", str(case / "facts.json"), "--out", str(case / "whale_series.json")])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    write(case / "flow_e1.json", {"title": "{{e1.label}}", "nodes": [], "edges": []})
    write(case / "price_series.json", [[1767225600, 1.0], [1767312000, 1.0], [1767398400, 1.0]])
    write(case / "volume_series.json", [[1767225600, 10]])
    assert write_price_receipt(case, second_price=1.0) == 0
    report = case / "report.md"
    report.write_text(report.read_text(encoding="utf-8") +
        "\n私人主桶 100.00%，私人尘埃 0.00%，公共设施 0.00%，未识别合约 0.00%，销毁哨兵 0.00%；"
        "top1/3/5/10 100.00% / 100.00% / 100.00% / 100.00%；HHI 1.0000。\n\n机械措辞甲。\n",
        encoding="utf-8")
    proc = cli(case, "fill-workorder")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    obj = read(case / "a5_assembly_workorder.json")
    def ref(rel, **extra):
        return {"path": rel, "sha256": sha(case / rel), **extra}
    obj["note"] = "W2 离线夹具"
    obj["bindings"]["price_source"] = ref("price_series.json")
    obj["bindings"]["price_source_checks"] = ref("price_checks.json")
    obj["fig1"] = {"state": "analysis-state.json", "price_csv": None, "overlay": None,
                   "out": "charts/final/fig1.png"}
    obj["fig2"] = {"lines": [{"entity_id": "e1", "display_label": "大庄#1",
                             "series_source": ref("entity_series.json", key="e1")}],
                   "required_entity_ids": ["e1"], "price_source": "price_series.json",
                   "out": "charts/final/fig2.png"}
    obj["fig3"] = {"price": ref("price_series.json"), "volume": ref("volume_series.json"),
                   "events_input": {"path": "a5_assembly_workorder.json", "key": "fig3.events", "sha256": None},
                   "events": [{"date": "2026-01-01", "label": "夹具事件"}], "out": "charts/final/fig3.png"}
    obj["flow"] = {"eligible_entity_ids": ["e1"], "charts": [{"entity_id": "e1",
                   "spec": ref("flow_e1.json"), "out": "charts/final/flow_e1.png"}]}
    write(case / "a5_assembly_workorder.json", obj)
    return case


def check_result(case, expected=0):
    proc = cli(case)
    assert proc.returncode == expected, proc.stdout + proc.stderr
    receipt = read(case / "stage2_closeout_receipt.json")
    assert len(receipt["checks"]) == 12, receipt
    assert receipt["verdict"] == ("PASS" if expected == 0 else "BLOCK"), receipt
    return {row["name"]: row for row in receipt["checks"]}


def detail(check):
    return "\n".join(check["detail"])


def update(case, rel, fn):
    obj = read(case / rel)
    fn(obj)
    write(case / rel, obj)


def add_amendment(case, before="机械措辞甲", after="机械措辞乙", *, extra=False):
    report = case / "report.md"
    old = report.read_bytes()
    new = old.replace(before.encode(), after.encode(), 1)
    if extra:
        new += b"\nUNAPPROVED\n"
    report.write_bytes(new)
    row = {"before_sha256": hashlib.sha256(old).hexdigest(), "after_sha256": sha(report),
           "trigger": "模板机械措辞修正", "exact_change": {"before": before, "after": after},
           "approved_by": "fixture dispatcher"}
    update(case, "a5_assembly_workorder.json", lambda obj: obj["amendments"].append(row))
    return old


class Cases:
    def __init__(self, root, seed):
        self.root, self.seed, self.n = root, seed, 0

    def fresh(self):
        self.n += 1
        case = self.root / f"variant-{self.n:03d}"
        shutil.copytree(self.seed, case)
        fixture.rebind_case_inputs(self.seed, case)
        check_result(case)  # Every mutation starts from a proven positive case.
        return case


def dryrun_profile_exempts_stage3_artifacts(cases):
    case = cases.fresh()
    for rel in ("a5_report_seal.json", "fig1_legend_receipt.json", "figure2_check_receipt.json"):
        assert not (case / rel).exists(), rel
    receipt = read(case / "stage2_closeout_receipt.json")
    assert "a5_report_seal" in receipt["pending_for_stage3"]
    assert cli(case, "check", "--receipt-only").returncode == 0


def only_findings_changed_is_rejected(cases):
    case = cases.fresh()
    with (case / "findings.md").open("ab") as stream:
        stream.write("改".encode())
    row = check_result(case, 2)["a4_seal_integrity"]
    assert row["status"] == "BLOCK" and "封口后被改动" in detail(row), row


def stale_registry_sha_detected(cases):
    case = cases.fresh()
    update(case, "a4_claims.json", lambda obj: obj.update(registered_at_utc="changed"))
    row = check_result(case, 2)["downstream_stale"]
    assert row["status"] == "BLOCK" and "adversarial_review" in detail(row), row


def stale_a4_seal_sha_detected(cases):
    case = cases.fresh()
    with (case / "a4_seal.json").open("ab") as stream:
        stream.write(b" ")
    row = check_result(case, 2)["downstream_stale"]
    assert row["status"] == "BLOCK" and "rounds.a4_seal_sha" in detail(row), row


def old_receipt_new_report_rejected(cases):
    case = cases.fresh()
    with (case / "report.md").open("ab") as stream:
        stream.write("改".encode())
    proc = cli(case, "check", "--receipt-only")
    assert proc.returncode == 2 and "report_md.sha256" in proc.stdout, proc.stdout


def receipt_only_checks_whale_series_and_commit(cases):
    case = cases.fresh()
    update(case, "whale_series.json", lambda rows: rows[0]["pct"].__setitem__(0, 99.0))
    proc = cli(case, "check", "--receipt-only")
    assert proc.returncode == 2 and "whale_series" in proc.stdout, proc.stdout
    case = cases.fresh()
    update(case, "stage2_closeout_receipt.json", lambda obj: obj.update(skill_commit="different-commit"))
    proc = cli(case, "check", "--receipt-only")
    assert proc.returncode == 2 and "skill 已换版，重跑 stage2_closeout" in proc.stdout, proc.stdout


def fig2_entity_id_must_be_facts_key(cases):
    case = cases.fresh()
    update(case, "a5_assembly_workorder.json", lambda obj: obj["fig2"]["lines"][0].update(entity_id="大庄#1"))
    row = check_result(case, 2)["workorder"]
    assert row["status"] == "BLOCK" and "fig2.lines[0].entity_id: facts 键 != 展示名" in detail(row), row


def fig2_required_from_label(cases):
    import stage2_closeout as closeout
    case = cases.fresh()
    obj = read(case / "a5_assembly_workorder.json")
    errors, notes = closeout.fig2_selection_errors(read(case / "facts.json"), obj["fig2"])
    assert not errors and "['e1']" in " ".join(notes), (errors, notes)
    update(case, "a5_assembly_workorder.json", lambda obj: obj["fig2"].update(lines=[]))
    row = check_result(case, 2)["workorder"]
    assert row["status"] == "BLOCK" and "fig2.lines" in detail(row), row
    case = cases.fresh()
    update(case, "a5_assembly_workorder.json", lambda obj: obj["fig2"].update(merge_groups=[]))
    row = check_result(case, 2)["workorder"]
    assert row["status"] == "BLOCK" and "本版不支持合并线" in detail(row), row


def flow_items_compat_and_extra_allowed(cases):
    import stage2_closeout as closeout
    case = cases.fresh()
    obj = read(case / "a5_assembly_workorder.json")
    obj["flow"]["items"] = obj["flow"].pop("charts")
    write(case / "a5_assembly_workorder.json", obj)
    row = check_result(case)["workorder"]
    assert "NOTE: 未声明流通量" in detail(row), row
    facts = read(case / "facts.json")
    facts["entities"]["e_extra"] = {"label": "观察实体", "current_raw": "0", "peak_raw": "0"}
    extra = copy.deepcopy(obj)
    extra["flow"]["eligible_entity_ids"].append("e_extra")
    chart = copy.deepcopy(extra["flow"]["items"][0]); chart["entity_id"] = "e_extra"
    extra["flow"]["items"].append(chart)
    errors, _notes = closeout.workorder_errors(case, "report.md", obj=extra, facts=facts)
    assert not errors, errors
    missing = copy.deepcopy(obj); missing["flow"]["items"] = []
    errors, _notes = closeout.workorder_errors(case, "report.md", obj=missing)
    assert any("等于 eligible" in error for error in errors), errors
    # Integer threshold also accepts 20% of declared circulating supply.
    lower = copy.deepcopy(facts); lower["token"]["circulating_supply_raw"] = "50"
    lower["entities"]["e1"]["current_raw"] = "10"
    errors, _ = closeout.flow_selection_errors(lower, {"eligible_entity_ids": [], "charts": []})
    assert any("包含下限 ['e1']" in error for error in errors), errors


def caption_mismatch_rejected(cases):
    case = cases.fresh()
    report = case / "report.md"
    text = report.read_text(encoding="utf-8").replace("100.00%", "99.00%")
    assert "100.00%" not in text
    report.write_text(text, encoding="utf-8")
    row = check_result(case, 2)["caption_same_source"]
    assert row["status"] == "BLOCK" and "图注与终态 scan 不同源: private_main" in detail(row), row


def caption_btw_style_tiny_values_accepted(cases):
    import stage2_closeout as closeout
    case = cases.fresh()
    scan = closeout.terminal_scan(case)
    scan["bucket_coverage"]["unresolved_contract"] = {"raw": "56", "net_supply_pct": 0.0056}
    scan["bucket_coverage"]["burn_sentinel"] = {"raw": "1", "net_supply_pct": 0.000002}
    text = (case / "report.md").read_text(encoding="utf-8").replace("未识别合约 0.00%", "未识别合约 0.0056%").replace("销毁哨兵 0.00%", "销毁哨兵 0.0%")
    errors, notes = closeout.caption_same_source(text, scan)
    assert not errors, errors
    assert "存在性检查，非逐桶配对" in notes
    text = text[:text.index("top1")] + "\n"
    errors, notes = closeout.caption_same_source(text, scan)
    assert not errors and "NOTE: 图注未披露集中度数字" in notes, (errors, notes)
    # Select #7 through the full runner as well; modified scan may block other checks.
    terminal = read(case / "distribution_rounds.json")["terminal"]
    write(case / terminal["final_scan_path"], scan)
    (case / "report.md").write_text(text, encoding="utf-8")
    row = check_result(case, 2)["caption_same_source"]
    assert row["status"] == "NOTE", row


def amend_chain_updates_receipt(cases):
    case = cases.fresh()
    add_amendment(case)
    proc = cli(case, "amend")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    receipt = read(case / "stage2_closeout_receipt.json")
    assert len(receipt["amendment_chain"]) == 1
    assert cli(case, "check", "--receipt-only").returncode == 0
    update(case, "a5_assembly_workorder.json", lambda obj: obj["fig2"].update(required_entity_ids=[]))
    old_receipt = (case / "stage2_closeout_receipt.json").read_bytes()
    proc = cli(case, "amend")
    assert proc.returncode == 2 and "frozen_sha256" in proc.stdout, proc.stdout
    assert (case / "stage2_closeout_receipt.json").read_bytes() == old_receipt


def amend_replay_mismatch_rejected(cases):
    case = cases.fresh()
    add_amendment(case, extra=True)
    old_receipt = (case / "stage2_closeout_receipt.json").read_bytes()
    proc = cli(case, "amend")
    assert proc.returncode == 2 and "未获准改动" in proc.stdout, proc.stdout
    assert (case / "stage2_closeout_receipt.json").read_bytes() == old_receipt
    case = cases.fresh()
    old = add_amendment(case, after="")
    proc = cli(case, "amend")
    assert proc.returncode == 2 and "--previous" in proc.stdout, proc.stdout
    (case / "before.md").write_bytes(old)
    proc = cli(case, "amend", "--previous", "before.md")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    # Newline normalization must never hide an additional byte-level edit.
    case = cases.fresh()
    add_amendment(case)
    report = case / "report.md"
    report.write_bytes(report.read_bytes().replace(b"\n", b"\r\n"))
    update(case, "a5_assembly_workorder.json", lambda obj: obj["amendments"][-1].update(after_sha256=sha(report)))
    proc = cli(case, "amend")
    assert proc.returncode == 2 and "未获准改动" in proc.stdout, proc.stdout


def old_amendment_rewritten_rejected(cases):
    case = cases.fresh(); add_amendment(case)
    proc = cli(case, "amend"); assert proc.returncode == 0, proc.stdout + proc.stderr
    update(case, "a5_assembly_workorder.json", lambda obj: obj["amendments"][0].update(approved_by="rewritten"))
    proc = cli(case, "check", "--receipt-only")
    assert proc.returncode == 2 and "amendments_sha256" in proc.stdout, proc.stdout
    add_amendment(case, before="机械措辞乙", after="机械措辞丙")
    proc = cli(case, "amend")
    assert proc.returncode == 2 and "旧前缀已变" in proc.stdout, proc.stdout


def amend_passes_with_note(cases):
    case = cases.fresh()
    assert "dual_basis" not in read(case / "facts.json")
    add_amendment(case)
    proc = cli(case, "amend")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    checks = read(case / "stage2_closeout_receipt.json")["checks"]
    assert len(checks) == 12 and next(row for row in checks if row["name"] == "dual_basis")["status"] == "NOTE"


def fill_never_overwrites_report_anchor(cases):
    case = cases.fresh()
    old = {"path": "old.md", "sha256": "old-anchor"}
    update(case, "a5_assembly_workorder.json", lambda obj: obj["bindings"].update(report_md=old))
    proc = cli(case, "fill-workorder")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert read(case / "a5_assembly_workorder.json")["bindings"]["report_md"] == old


def low_sample_terminal_not_blocked(cases):
    case = cases.fresh()
    checks = check_result(case)
    assert checks["a5_distribution"]["status"] == "PASS" and "LOW_SAMPLE" in detail(checks["a5_distribution"])
    assert checks["caption_same_source"]["status"] == "PASS"
    scan = read(case / read(case / "distribution_rounds.json")["terminal"]["final_scan_path"])
    assert "concentration" not in scan and "top_k" in scan["small_sample_mode"]


def waived_terminal_not_blocked(cases):
    import stage2_closeout as closeout
    import test_distribution_gate as distribution_fixture
    import holder_distribution_scan as distribution
    # The standard case is first proved positive; the waiver uses real ABNORMAL producers.
    cases.fresh()
    case = cases.root / "waiver"
    case.mkdir()
    _cluster, proc = distribution_fixture.prepare_explanation_case(case)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    proc = run_formal_script(fixture.DIST, ["record-round", "--case-dir", str(case),
        "--scan", "dist_rounds/round_1/distribution_scan.json"])
    assert proc.returncode == 0 and "UNEXPLAINED" in proc.stdout, proc.stdout + proc.stderr
    proc = distribution_fixture.run_scan(case, "final", "--round", "2")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    scan_rel = "dist_rounds/round_2/distribution_scan.json"
    scan = read(case / scan_rel)
    assert scan["verdict"] == "ABNORMAL_SHAPE"
    waiver = {"schema": "distribution-exception-receipt/v1", "user_decided_at_utc": "2026-09-16T00:00:00Z",
              "round_n": 2, "unexplained_clusters": [row["cluster_id"] for row in scan["abnormal_clusters"]],
              "unexplained_raw": "5000000", "a4_seal_sha256": sha(case / "a4_seal.json"),
              "final_scan_sha256": sha(case / scan_rel), "rounds_sha256": sha(case / "distribution_rounds.json")}
    assert not distribution.validate_waiver(case, waiver, case / scan_rel, waiver["rounds_sha256"], 2)
    write(case / "waiver.json", waiver)
    proc = run_formal_script(fixture.DIST, ["record-round", "--case-dir", str(case), "--scan", scan_rel, "--waiver", "waiver.json"])
    assert proc.returncode == 0 and "WAIVED" in proc.stdout, proc.stdout + proc.stderr
    (case / "report.md").write_text("# 未解释分布异常\n\n![分布](charts/final/holder_distribution_current.png)\n", encoding="utf-8")
    checks = closeout.run_checks(case, "report.md")
    row = next(row for row in checks if row["name"] == "a5_distribution")
    assert row["status"] == "PASS" and "WAIVED" in detail(row), row


def fig2_series_replay_binds_workorder(cases):
    case = cases.fresh()
    update(case, "whale_series.json", lambda lines: lines[0]["pct"].__setitem__(0, 99.0))
    row = check_result(case, 2)["fig2_series"]
    assert row["status"] == "BLOCK" and "重放字节不符" in detail(row), row
    case = cases.fresh()
    update(case, "a5_assembly_workorder.json", lambda obj: obj["fig2"]["lines"].append({
        "entity_id": "missing", "display_label": "missing", "series_source": {
            "path": "entity_series.json", "sha256": sha(case / "entity_series.json"), "key": "missing"}}))
    row = check_result(case, 2)["fig2_series"]
    assert row["status"] == "BLOCK" and "entity_id 集合" in detail(row), row


def fig2_sidecar_substitution_rejected(cases):
    case = cases.fresh()
    proc = run_formal_script(FIGURES, ["fig2-series", "--entity-series", str(case / "entity_series.json"),
        "--keys", "e1", "--labels-from", str(case / "facts.json"), "--out", str(case / "whale_series_alt.json")])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    row = check_result(case, 2)["fig2_series"]
    assert row["status"] == "BLOCK" and "旁车 out" in detail(row), row
    case = cases.fresh()
    shutil.copyfile(case / "entity_series.json", case / "entity_series_copy.json")
    update(case, "whale_series.provenance.json", lambda obj: obj["entity_series"].update(path="entity_series_copy.json"))
    row = check_result(case, 2)["fig2_series"]
    assert row["status"] == "BLOCK" and "series_source.path" in detail(row), row


def fig2_duplicate_and_label_rejected(cases):
    import stage2_closeout as closeout
    case = cases.fresh()
    update(case, "a5_assembly_workorder.json", lambda obj: obj["fig2"]["lines"].append(copy.deepcopy(obj["fig2"]["lines"][0])))
    row = check_result(case, 2)["fig2_series"]
    assert row["status"] == "BLOCK" and "entity_id 重复" in detail(row), row
    case = cases.fresh()
    update(case, "a5_assembly_workorder.json", lambda obj: obj["fig2"]["lines"][0].update(display_label=""))
    row = check_result(case, 2)["fig2_series"]
    assert row["status"] == "BLOCK" and "display_label" in detail(row), row
    case = cases.fresh()
    update(case, "a5_assembly_workorder.json", lambda obj: obj["fig2"]["lines"][0].update(display_label="缩写"))
    row = check_result(case)["fig2_series"]
    assert row["status"] == "PASS" and "展示名为缩写" in detail(row), row
    case = cases.fresh()
    update(case, "facts.json", lambda obj: obj["entities"].update(e2={"label": "观察实体", "current_raw": "0"}))
    update(case, "entity_series.json", lambda obj: obj.update(e2=[0.0]))
    proc = run_formal_script(FIGURES, ["fig2-series", "--entity-series", str(case / "entity_series.json"),
        "--keys", "e1,e2", "--labels-from", str(case / "facts.json"), "--out", str(case / "whale_series.json")])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    obj = read(case / "a5_assembly_workorder.json")
    obj["fig2"]["lines"][0]["series_source"]["sha256"] = sha(case / "entity_series.json")
    obj["fig2"]["lines"].append({"entity_id": "e2", "display_label": "观察实体",
        "series_source": {"path": "entity_series.json", "sha256": sha(case / "entity_series.json"), "key": "e2"}})
    write(case / "a5_assembly_workorder.json", obj)
    errors, _ = closeout.fig2_series_errors(case)
    assert not errors, errors
    obj["fig2"]["lines"][0]["series_source"]["key"] = "e2"
    obj["fig2"]["lines"][1]["series_source"]["key"] = "e1"
    write(case / "a5_assembly_workorder.json", obj)
    errors, _ = closeout.fig2_series_errors(case)
    assert any("逐行错配" in error for error in errors), errors


def downstream_check_cli_exit3(cases):
    case = cases.fresh()
    update(case, "a4_claims.json", lambda obj: obj.update(registered_at_utc="changed"))
    proc = run_formal_script(fixture.GATE, ["downstream-check", "--case-dir", str(case), "--json-out", "downstream.json"])
    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert any("adversarial_review" in row["item"] and row["status"] == "stale" for row in read(case / "downstream.json"))


def amendments_chain_gap_rejected(cases):
    case = cases.fresh()
    obj = read(case / "a5_assembly_workorder.json")
    anchor = obj["bindings"]["report_md"]["sha256"]
    obj["amendments"] = [{"before_sha256": anchor, "after_sha256": "1" * 64, "trigger": "机械修改",
        "exact_change": {"before": "甲", "after": "乙"}, "approved_by": "fixture"},
        {"before_sha256": "2" * 64, "after_sha256": sha(case / "report.md"), "trigger": "机械修改",
        "exact_change": {"before": "乙", "after": "丙"}, "approved_by": "fixture"}]
    write(case / "a5_assembly_workorder.json", obj)
    row = check_result(case, 2)["workorder"]
    assert row["status"] == "BLOCK" and "amendments[1].before_sha256" in detail(row), row


def workorder_reference_contracts(cases):
    import stage2_closeout as closeout
    case = cases.fresh()
    original = read(case / "a5_assembly_workorder.json")
    mutations = [
        ("bindings.price_source", lambda obj: obj["bindings"].pop("price_source")),
        ("fig2.price_source|price", lambda obj: obj["fig2"].pop("price_source")),
        ("fig2.price_source|price", lambda obj: obj["fig2"].update(price_source="volume_series.json")),
        ("price_source_checks", lambda obj: obj["bindings"].pop("price_source_checks")),
        ("bindings.price_source", lambda obj: obj["bindings"]["price_source"].pop("sha256")),
        ("fig2.lines[0].series_source", lambda obj: obj["fig2"]["lines"][0]["series_source"].pop("sha256")),
        ("flow.charts[0].spec", lambda obj: obj["flow"]["charts"][0]["spec"].update(sha256=None)),
        ("fig3.volume", lambda obj: obj["fig3"].pop("volume")),
        ("fig3.events_input", lambda obj: obj["fig3"]["events_input"].update(key="other")),
        ("bindings.bad_self", lambda obj: obj["bindings"].update(bad_self={"path": "a5_assembly_workorder.json", "sha256": None})),
        ("fig1.overlay", lambda obj: obj["fig1"].pop("overlay")),
        ("fig1.state", lambda obj: obj["fig1"].update(state="facts.json")),
        ("fig1.price_csv", lambda obj: obj["fig1"].update(price_csv="findings.md")),
        ("fig2.out", lambda obj: obj["fig2"].pop("out")),
        ("fig3.events", lambda obj: obj["fig3"].update(events=[])),
        ("bindings.report_md.path", lambda obj: obj["bindings"]["report_md"].update(path="findings.md")),
        ("report_image_refs", lambda obj: obj["report_image_refs"].append(obj["report_image_refs"][0])),
        ("fig2.out", lambda obj: obj["fig2"].update(out="charts/../escape.png")),
        ("bindings.price_source.path", lambda obj: obj["bindings"]["price_source"].update(path=str(case / "price_series.json"))),
    ]
    for field, mutate in mutations:
        obj = copy.deepcopy(original); mutate(obj)
        errors, _ = closeout.workorder_errors(case, "report.md", obj=obj)
        assert errors and all(error.startswith("WORKORDER BLOCK: ") for error in errors), (field, errors)
        assert any(field in error for error in errors), (field, errors)
    # BTW aliases retain price binding, inline dual-source object, and verified CSV input.
    obj = copy.deepcopy(original)
    for old, new in (("final_distribution_scan", "final_scan"), ("final_distribution_png", "terminal_distribution_chart")):
        obj["bindings"][new] = obj["bindings"].pop(old)
    obj["bindings"].pop("price_source_checks")
    obj["bindings"]["price_source"]["dual_source_check"] = {
        "receipt": {"path": "price_checks.json", "sha256": sha(case / "price_checks.json")}, "verdict": "PASS"}
    obj["fig2"]["price"] = {"path": obj["fig2"].pop("price_source")}
    obj["fig3"]["price_input"] = obj["fig3"].pop("price")
    obj["fig3"]["volume_input"] = obj["fig3"].pop("volume")
    obj["fig1"]["price_csv"] = "price_series.json"
    errors, _ = closeout.workorder_errors(case, "report.md", obj=obj)
    assert not errors, errors
    (case / "price_link.json").symlink_to(case / "price_series.json")
    obj = copy.deepcopy(original); obj["bindings"]["price_source"]["path"] = "price_link.json"
    errors, _ = closeout.workorder_errors(case, "report.md", obj=obj)
    assert any("符号链接" in error for error in errors), errors


def receipt_shape_and_fill_nulls(cases):
    case = cases.fresh()
    receipt_path = case / "stage2_closeout_receipt.json"
    original = receipt_path.read_bytes()
    for key, value in (("schema", "wrong/v1"), ("amendment_chain", ["malformed"]), ("workorder", ["malformed"]), ("whale_series", "malformed")):
        receipt = json.loads(original); receipt[key] = value; write(receipt_path, receipt)
        proc = cli(case, "check", "--receipt-only")
        assert proc.returncode == 2 and key in proc.stdout, proc.stdout + proc.stderr
    receipt_path.write_bytes(original)
    update(case, "a5_assembly_workorder.json", lambda obj: obj.pop("fig2"))
    proc = cli(case, "fill-workorder")
    assert proc.returncode == 0 and "fig2.lines" in proc.stdout, proc.stdout + proc.stderr
    assert read(case / "a5_assembly_workorder.json")["fig2"]["lines"] is None


def caption_raw_rounding_and_pure_series_errors(cases):
    import stage2_closeout as closeout
    import figures_from_facts as figures
    case = cases.fresh()
    scan = closeout.terminal_scan(case)
    for pct in (0.009999, 0.01, 0.00005, 0.000049, 2.675):
        scan["bucket_coverage"]["private_main"]["net_supply_pct"] = pct
        value = f"{pct:.2f}%" if pct >= 0.01 else f"{pct:.4f}%"
        text = f"![分布](charts/final/holder_distribution_current.png)\n\n私人主桶 {value}；其余桶 0.00%。\n"
        errors, _ = closeout.caption_same_source(text, scan)
        assert not errors, (pct, errors)
    series = case / "bad_series.json"; series.write_bytes(b"{}")
    errors, count = figures.fig2_check_errors(case / "facts.json", series, figures.DEFAULT_TOL_PP)
    assert count == 0 and errors == ["--series 应为图 2 whale_series JSON（list of lines）"]
    for data in (b"{invalid", None):
        if data is None:
            path = case / "absent-series.json"
        else:
            path = series; path.write_bytes(data)
        try:
            figures.fig2_check_errors(case / "facts.json", path, figures.DEFAULT_TOL_PP)
        except ValueError:
            pass
        else:
            raise AssertionError("missing/invalid JSON must raise ValueError")


def amend_rechecks_all_and_is_atomic(cases):
    case = cases.fresh()
    add_amendment(case)
    old_receipt = (case / "stage2_closeout_receipt.json").read_bytes()
    with (case / "findings.md").open("ab") as stream:
        stream.write("另一处封口件变动".encode())
    proc = cli(case, "amend")
    assert proc.returncode == 2 and "a4_seal_integrity" in proc.stdout and "封口后被改动" in proc.stdout, proc.stdout
    assert (case / "stage2_closeout_receipt.json").read_bytes() == old_receipt
    # A failing check cannot short-circuit the other eleven checks or receipt emission.
    case = cases.fresh()
    (case / "facts.json").write_bytes(b"not-json")
    checks = check_result(case, 2)
    assert len(checks) == 12 and checks["facts_gate"]["status"] == "BLOCK"


def price_receipt_content_enforced(cases):
    """F05：真实 price_check 收据的结论/绑定被 closeout 语义消费；纯申报对象不放行。"""
    import stage2_closeout as closeout
    case = cases.fresh()

    def rebind():
        obj = read(case / "a5_assembly_workorder.json")
        obj["bindings"]["price_source_checks"]["sha256"] = sha(case / "price_checks.json")
        write(case / "a5_assembly_workorder.json", obj)
        return closeout.workorder_errors(case, "report.md")

    # 1 真实 FAIL 收据（主 1.0/副 2.0 → 66.67%）退出 2；绑定后 workorder 与完整 check 均 BLOCK
    assert write_price_receipt(case, second_price=2.0) == 2
    errors, _ = rebind()
    assert any("price_source_checks.verdict" in e for e in errors), errors
    row = check_result(case, 2)["workorder"]
    assert "price_source_checks.verdict" in detail(row), row
    # 2 手改 verdict=PASS 但 points 含 FAIL → 重算不一致
    update(case, "price_checks.json", lambda r: r.update(verdict="PASS"))
    errors, _ = rebind()
    assert any("重算一致" in e for e in errors), errors
    # 3 WARN 收据（主 1.0/副 1.08 → 7.69%）放行并记 NOTE
    assert write_price_receipt(case, second_price=1.08) == 0
    errors, notes = rebind()
    assert not errors, errors
    assert any("WARN 点 3" in n for n in notes), notes
    # 4 price_file_sha256 与工单主源不一致
    update(case, "price_checks.json", lambda r: r.update(price_file_sha256="0" * 64))
    errors, _ = rebind()
    assert any("price_file_sha256" in e and "= bindings.price_source.sha256" in e for e in errors), errors
    # 5 旧收据（无 price_file_sha256）
    update(case, "price_checks.json", lambda r: r.pop("price_file_sha256"))
    errors, _ = rebind()
    assert any("price_file_sha256" in e and "在场" in e for e in errors), errors
    # 6 全 SKIP → ALL_SKIP 退出 3；绑定后 BLOCK
    assert write_price_receipt(case, second_price=None) == 3
    errors, _ = rebind()
    assert any("ALL_SKIP" in e for e in errors), errors
    # 7 内联纯申报对象拒；内联带 receipt（ARC 形态）放行
    assert write_price_receipt(case, second_price=1.0) == 0
    obj = read(case / "a5_assembly_workorder.json")
    obj["bindings"].pop("price_source_checks")
    obj["bindings"]["price_source"]["dual_source_check"] = {"status": "PASS"}
    write(case / "a5_assembly_workorder.json", obj)
    errors, _ = closeout.workorder_errors(case, "report.md")
    assert any("dual_source_check.receipt" in e for e in errors), errors
    obj["bindings"]["price_source"]["dual_source_check"] = {
        "receipt": {"path": "price_checks.json", "sha256": sha(case / "price_checks.json")}, "verdict": "PASS"}
    write(case / "a5_assembly_workorder.json", obj)
    errors, _ = closeout.workorder_errors(case, "report.md")
    assert not errors, errors
    check_result(case)


def facts_vs_ledgers_rejects_hand_edit(cases):
    case = cases.fresh()
    update(case, "facts.json", lambda obj: obj["entities"]["e1"].update(current_raw="90"))
    checks = check_result(case, 2)
    assert checks["facts_vs_ledgers"]["status"] == "BLOCK" and "e1" in "".join(checks["facts_vs_ledgers"]["detail"]), checks
    case = cases.fresh()
    update(case, "facts.json", lambda obj: obj.pop("provenance"))
    checks = check_result(case, 2)
    assert checks["facts_vs_ledgers"]["status"] == "BLOCK" and "provenance" in "".join(checks["facts_vs_ledgers"]["detail"]), checks
    case = cases.fresh()
    update(case, "facts.json", lambda obj: obj["provenance"].update(mode="exploration"))
    checks = check_result(case, 2)
    assert checks["facts_vs_ledgers"]["status"] == "BLOCK" and "exploration" in "".join(checks["facts_vs_ledgers"]["detail"]), checks


TESTS = [dryrun_profile_exempts_stage3_artifacts, only_findings_changed_is_rejected,
         stale_registry_sha_detected, stale_a4_seal_sha_detected, old_receipt_new_report_rejected,
         receipt_only_checks_whale_series_and_commit, fig2_entity_id_must_be_facts_key,
         fig2_required_from_label, flow_items_compat_and_extra_allowed, caption_mismatch_rejected,
         caption_btw_style_tiny_values_accepted, amend_chain_updates_receipt, amend_replay_mismatch_rejected,
         old_amendment_rewritten_rejected, amend_passes_with_note, fill_never_overwrites_report_anchor,
         low_sample_terminal_not_blocked, waived_terminal_not_blocked, fig2_series_replay_binds_workorder,
         fig2_sidecar_substitution_rejected, fig2_duplicate_and_label_rejected,
         downstream_check_cli_exit3, amendments_chain_gap_rejected,
         workorder_reference_contracts, receipt_shape_and_fill_nulls,
         caption_raw_rounding_and_pure_series_errors, amend_rechecks_all_and_is_atomic,
         facts_vs_ledgers_rejects_hand_edit, price_receipt_content_enforced]


def main():
    root = Path(tempfile.mkdtemp(prefix="test-stage2-closeout-")).resolve()
    print("fixtures: " + str(root), flush=True)
    seed = build_closeout_case(root / "baseline")
    check_result(seed)
    cases = Cases(root, seed)
    failures = []
    for test in TESTS:
        try:
            with test_vertical_slices():
                test(cases)
            print("ok    " + test.__name__, flush=True)
        except Exception as exc:
            failures.append(test.__name__)
            print(f"FAIL  {test.__name__}: {type(exc).__name__}: {exc}", flush=True)
    print(f"stage2_closeout: {len(TESTS) - len(failures)}/{len(TESTS)} PASS", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
