#!/usr/bin/env python3
"""持仓分布形态硬闸的算法、输入防伪与 fail-closed 反例。"""
from __future__ import annotations

import hashlib
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCAN = ROOT / "scripts/report/holder_distribution_scan.py"
EXPLAIN = ROOT / "scripts/report/distribution_explanation_check.py"
ADJUDICATION = ROOT / "scripts/report/adjudication_validator.py"
sys.path.insert(0, str(ROOT / "scripts/report"))
import holder_distribution_scan as distribution_scan


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_case(root: Path, balances: dict[str, int], *, duplicate_partition=False) -> None:
    snap = root / "data/holders_owners.json"
    write_json(snap, [{"owner": owner, "balance_raw": str(raw)}
                      for owner, raw in balances.items()])
    total = sum(balances.values())
    write_json(root / "supply_truth.json", {
        "schema": "supply-truth/v1", "verdict": "PASS", "exit_code": 0,
        "total_supply_raw": str(total), "net_supply_raw": str(total),
    })
    write_json(root / "data_map.json", {
        "schema": "data-map/v1",
        "files": [{"path": "data/holders_owners.json", "sha256": sha(snap)}],
    })
    rows = []
    if duplicate_partition:
        first = next(iter(balances))
        rows = [{"address": first, "bucket": "public_facility"},
                {"address": first, "bucket": "burn_sentinel"}]
    write_json(root / "candidate_screening.json", {
        "schema": "candidate-screening/v1", "auto_excluded_candidate": rows,
    })


def run_scan(case: Path, stage="initial", *extra: str):
    cmd = [sys.executable, str(SCAN), "--case-dir", str(case), "--stage", stage, *extra]
    return subprocess.run(cmd, capture_output=True, text=True)


def check(name: str, ok: bool, details="") -> bool:
    print(("ok   " if ok else "FAIL ") + f"[{name}]" + (f" {details}" if details and not ok else ""))
    return ok


def smooth_balances(n=240) -> dict[str, int]:
    # 每个半档约 4 个 owner，质量随档位平滑递减，不造局部鼓包。
    return {f"owner-{i:04d}": max(1, int(2_000_000 / (1.035 ** i))) for i in range(n)}


def bump_balances() -> dict[str, int]:
    rows = smooth_balances(240)
    rows.update({f"equal-{i:03d}": 1_000_000 for i in range(46)})
    return rows


def head_balances() -> dict[str, int]:
    rows = {f"tail-{i:03d}": 75_000 for i in range(200)}
    rows["head"] = 5_000_000
    return rows


def file_entry(root: Path, rel: str) -> dict:
    path = root / rel
    return {"path": rel, "sha256": sha(path), "size": path.stat().st_size}


def add_final_inputs(root: Path, claims: list[dict]) -> None:
    write_json(root / "facts.json", {"entities": {}, "metrics": {}})
    write_json(root / "analysis-state.json", {"chain": "bsc", "whale_groups": []})
    write_json(root / "evidence.json", {"source": "fixture"})
    write_json(root / "a4_claims.json", {"schema": "a4-claims/v2", "claims": claims})
    write_json(root / "handoff_manifest.json", {"consumer_min_schema": "handoff/v3",
                                                  "status": "READY", "run_id": "fixture"})
    write_json(root / "identity_snapshot_receipt.json", {"schema": "identity-snapshot-receipt/v1"})
    write_json(root / "entity_freeze.json", {"schema": "entity-freeze/v1", "revisions": []})
    for name in ("membership_ledger.json", "position_ledger.json",
                 "economic_control_ledger.json", "address_classification.json"):
        write_json(root / name, {"rows": []})
    sealed = [file_entry(root, x) for x in ("a4_claims.json", "facts.json",
                                             "analysis-state.json", "evidence.json")]
    write_json(root / "a4_seal.json", {"schema": "a4-seal/v4", "verdict": "PASS", "chain": "bsc",
        "workflow_type": "new-analysis", "revision": 1, "charts_dir": "charts/final",
        "registry": {"path": "a4_claims.json", "sha256": sha(root / "a4_claims.json")},
        "claims": [{"id": x["id"], "verdict": "CONFIRMED"} for x in claims],
        "sealed_files": sealed, "claim_files": ["evidence.json"]})


def prepare_explanation_case(root: Path, *, forged=False) -> tuple[dict, subprocess.CompletedProcess]:
    make_case(root, head_balances())
    p = run_scan(root); assert p.returncode == 0, p.stdout + p.stderr
    initial = json.loads((root / "distribution_scan.json").read_text())
    cluster = next(x for x in initial["abnormal_clusters"] if x["trigger"] == "head_concentration")
    claims = []
    for current in initial["abnormal_clusters"]:
        members = [x["owner"] for x in current["members"]]
        explained = [] if forged and current["cluster_id"] == cluster["cluster_id"] else members
        explained_raw = sum(int(x["raw"]) for x in current["members"] if x["owner"] in explained)
        claims.append({"id": f"dist-{current['cluster_id']}", "text": "终判分布异常解释",
             "files": ["evidence.json"], "report_locations": ["报告.md:1"],
             "distribution_explanation": {"cluster_ids": [current["cluster_id"]],
                 "members": explained, "explained_raw": str(explained_raw),
                 "evidence_refs": ["evidence.json"], "propagation": {}}})
    add_final_inputs(root, claims)
    for claim in claims:
        claim["distribution_explanation"]["propagation"] = {
            "facts_sha256": sha(root / "facts.json"),
            "analysis_state_sha256": sha(root / "analysis-state.json")}
    write_json(root / "a4_claims.json", {"schema": "a4-claims/v2", "claims": claims})
    seal = json.loads((root / "a4_seal.json").read_text())
    seal["registry"]["sha256"] = sha(root / "a4_claims.json")
    seal["sealed_files"] = [file_entry(root, x) for x in
                             ("a4_claims.json", "facts.json", "analysis-state.json", "evidence.json")]
    write_json(root / "a4_seal.json", seal)
    final = run_scan(root, "final", "--round", "1")
    return cluster, final


def main() -> int:
    ok = True
    help_run = subprocess.run([sys.executable, str(SCAN), "--help"], capture_output=True, text=True)
    ok &= check("CLI 不暴露 skip/阈值/自由披露绕过", help_run.returncode == 0
                and "skip" not in help_run.stdout.lower()
                and "threshold" not in help_run.stdout.lower()
                and "disclosure-reason" not in help_run.stdout.lower(), help_run.stdout + help_run.stderr)
    explain_help = subprocess.run([sys.executable, str(EXPLAIN), "--help"], capture_output=True, text=True)
    ok &= check("解释五判据无绕过参数", explain_help.returncode == 0
                and "skip" not in explain_help.stdout.lower(), explain_help.stdout + explain_help.stderr)
    relevant_source = "\n".join((ROOT / rel).read_text(encoding="utf-8") for rel in (
        "scripts/report/holder_distribution_scan.py",
        "scripts/report/distribution_explanation_check.py",
        "scripts/report/a5_report_seal.py"))
    ok &= check("源码不接受自由披露理由", "distribution-disclosure-reason" not in relevant_source)

    contracts = {
        ROOT / "scripts/report/handoff_manifest.py": ('SCHEMA_VERSION = "handoff/v3"',
                                                        'SUPPORTED_SCHEMAS = {"handoff/v3"}'),
        ROOT / "scripts/report/a4_gate.py": ('"schema": "a4-seal/v4"',),
        ROOT / "scripts/report/a5_report_seal.py": ('SCHEMA="a5-report-seal/v2"',),
    }
    for path, needles in contracts.items():
        text = path.read_text(encoding="utf-8")
        ok &= check(f"{path.name} 新契约已升版且默认旧版拒收", all(x in text for x in needles), text[:400])

    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "smooth"; d.mkdir(); make_case(d, smooth_balances())
        p = run_scan(d)
        out = json.loads((d / "distribution_scan.json").read_text()) if (d / "distribution_scan.json").is_file() else {}
        ok &= check("正常长尾不误报", p.returncode == 0 and out.get("verdict") == "NORMAL_SHAPE", p.stdout + p.stderr)
        frozen = out.get("thresholds", {})
        ok &= check("候选阈值已冻结", frozen.get("bin_ratio") == "sqrt(2)"
                    and frozen.get("bin_min_private_pct") == 0.000001
                    and frozen.get("bin_max_private_pct") == 100.0
                    and frozen.get("economic_gate_net_pct") == 2.0
                    and frozen.get("minimum_bin_owner_count") == 5
                    and frozen.get("shift_jaccard_min") == 0.8
                    and frozen.get("sample_line") == 100
                    and frozen.get("unresolved_contract_disclosure_net_pct") == 1.0, str(frozen))

    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "bump"; d.mkdir(); make_case(d, bump_balances())
        p = run_scan(d); out = json.loads((d / "distribution_scan.json").read_text()) if (d / "distribution_scan.json").is_file() else {}
        ok &= check("等额鼓包触发", p.returncode == 0 and out.get("verdict") == "ABNORMAL_SHAPE"
                    and any(x.get("trigger") == "bin_count_bump" for x in out.get("abnormal_clusters", [])), p.stdout + p.stderr)

    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "borderline"; d.mkdir()
        rows = smooth_balances(); rows.update({f"small-equal-{i:03d}": 10_000 for i in range(46)})
        make_case(d, rows); p = run_scan(d); out = json.loads((d / "distribution_scan.json").read_text())
        ok &= check("等额组未达 2% 经济门不触发鼓包", p.returncode == 0
                    and not any(x.get("trigger") == "bin_count_bump"
                                for x in out.get("abnormal_clusters", [])), p.stdout + p.stderr)

    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "dust"; d.mkdir()
        rows = {k: v * 1_000_000_000 for k, v in smooth_balances().items()}
        rows.update({f"dust-{i:04d}": 1 for i in range(1_000)})
        make_case(d, rows); p = run_scan(d); out = json.loads((d / "distribution_scan.json").read_text())
        ok &= check("dust 假长尾被隔离且不进入主箱统计", p.returncode == 0
                    and out.get("partition_check", {}).get("bucket_owner_counts", {}).get("private_dust") == 1_000
                    and out.get("owner_count_private_main") == 240, p.stdout + p.stderr)

    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "facility"; d.mkdir(); rows = smooth_balances()
        rows.update({"cex-large": sum(rows.values()), "unknown-contract": sum(rows.values()) // 2})
        make_case(d, rows)
        write_json(d / "candidate_screening.json", {"schema": "candidate-screening/v1",
            "auto_excluded_candidate": [
                {"address": "cex-large", "bucket": "public_facility"},
                {"address": "unknown-contract", "bucket": "unresolved_contract"}]})
        p = run_scan(d); out = json.loads((d / "distribution_scan.json").read_text())
        ok &= check("CEX 大额不污染主箱且未识别合约达到 1% 强制披露", p.returncode == 0
                    and out.get("disclosure_required") is True
                    and out.get("partition_check", {}).get("bucket_owner_counts", {}).get("public_facility") == 1
                    and out.get("partition_check", {}).get("bucket_owner_counts", {}).get("unresolved_contract") == 1,
                    p.stdout + p.stderr)

    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "head"; d.mkdir(); make_case(d, head_balances())
        p = run_scan(d); out = json.loads((d / "distribution_scan.json").read_text()) if (d / "distribution_scan.json").is_file() else {}
        ok &= check("头部集中触发", p.returncode == 0 and out.get("verdict") == "ABNORMAL_SHAPE"
                    and any(x.get("trigger") == "head_concentration" for x in out.get("abnormal_clusters", [])), p.stdout + p.stderr)
        ok &= check("同一快照多个异常簇分别保留", len(out.get("abnormal_clusters", [])) >= 2, str(out.get("abnormal_clusters")))

        # 真实重算必须戳穿手改 verdict，不能只验自报 schema/hash。
        out["verdict"] = "NORMAL_SHAPE"
        write_json(d / "distribution_scan.json", out)
        pv = subprocess.run([sys.executable, str(SCAN), "validate", "--case-dir", str(d),
                             "--scan", "distribution_scan.json"], capture_output=True, text=True)
        ok &= check("手改 verdict 被重算拒绝", pv.returncode == 2, pv.stdout + pv.stderr)

    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "binding"; d.mkdir(); make_case(d, smooth_balances()); run_scan(d)
        out = json.loads((d / "distribution_scan.json").read_text())
        out["input_binding"]["exclusion_derivation_sha256"] = "0" * 64
        write_json(d / "distribution_scan.json", out)
        pv = subprocess.run([sys.executable, str(SCAN), "validate", "--case-dir", str(d),
                             "--scan", "distribution_scan.json"], capture_output=True, text=True)
        ok &= check("手写排除派生哈希被独立重算拒绝", pv.returncode == 2, pv.stdout + pv.stderr)

    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "snapshot-drift"; d.mkdir(); make_case(d, smooth_balances()); run_scan(d)
        snap = d / "data/holders_owners.json"; rows = json.loads(snap.read_text()); rows[0]["balance_raw"] = "7"
        write_json(snap, rows)
        pv = subprocess.run([sys.executable, str(SCAN), "validate", "--case-dir", str(d),
                             "--scan", "distribution_scan.json"], capture_output=True, text=True)
        ok &= check("快照内容漂移被绑定哈希拒绝", pv.returncode == 2, pv.stdout + pv.stderr)

    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "duplicate-owner"; d.mkdir(); make_case(d, smooth_balances())
        snap = d / "data/holders_owners.json"; rows = json.loads(snap.read_text()); rows.append(dict(rows[0]))
        write_json(snap, rows)
        data_map = json.loads((d / "data_map.json").read_text()); data_map["files"][0]["sha256"] = sha(snap)
        write_json(d / "data_map.json", data_map)
        p = run_scan(d)
        ok &= check("重复 owner 快照 fail-closed", p.returncode == 2 and "重复" in p.stderr, p.stdout + p.stderr)

    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "low"; d.mkdir(); make_case(d, {f"o{i}": 1_000 for i in range(99)})
        p = run_scan(d); out = json.loads((d / "distribution_scan.json").read_text()) if (d / "distribution_scan.json").is_file() else {}
        low = out.get("small_sample_mode", {})
        ok &= check("sample_line-1 切小样本集中度模式", p.returncode == 0
                    and out.get("verdict") == "NOT_EVALUABLE"
                    and out.get("not_evaluable_reason") == "low_sample"
                    and low.get("complete") is True
                    and isinstance(low.get("owner_classifications"), list)
                    and len(low.get("owner_classifications")) == 99
                    and low.get("top_k") and low.get("hhi") is not None, p.stdout + p.stderr)
        out["small_sample_mode"]["complete"] = False; write_json(d / "distribution_scan.json", out)
        pc = subprocess.run([sys.executable, str(SCAN), "validate", "--case-dir", str(d),
                             "--scan", "distribution_scan.json"], capture_output=True, text=True)
        ok &= check("小样本集中度结果不完整被拒", pc.returncode == 2, pc.stdout + pc.stderr)

        pv = subprocess.run([sys.executable, str(SCAN), "validate", "--case-dir", str(d),
                             "--scan", "distribution_scan.json", "--expected-stage", "final"],
                            capture_output=True, text=True)
        ok &= check("initial 冒充 final 被拒", pv.returncode == 2, pv.stdout + pv.stderr)

    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "terminal"; d.mkdir(); make_case(d, smooth_balances()); run_scan(d)
        add_final_inputs(d, [{"id": "C1", "text": "普通命题", "files": ["evidence.json"],
                              "report_locations": ["报告.md:1"]}])
        p1 = run_scan(d, "final", "--round", "1")
        pr = subprocess.run([sys.executable, str(SCAN), "record-round", "--case-dir", str(d),
                             "--scan", "dist_rounds/round_1/distribution_scan.json"],
                            capture_output=True, text=True)
        p2 = run_scan(d, "final", "--round", "2")
        ok &= check("唯一 terminal 后禁止再生成轮次", p1.returncode == 0 and pr.returncode == 0
                    and p2.returncode == 2 and "terminal" in p2.stderr,
                    p1.stdout + p1.stderr + pr.stdout + pr.stderr + p2.stdout + p2.stderr)

    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "broken"; d.mkdir(); make_case(d, smooth_balances(), duplicate_partition=True)
        p = run_scan(d)
        out = json.loads((d / "distribution_scan.json").read_text()) if (d / "distribution_scan.json").is_file() else {}
        ok &= check("分区冲突 data_broken 且 exit 2", p.returncode == 2
                    and out.get("verdict") == "NOT_EVALUABLE"
                    and out.get("not_evaluable_reason") == "data_broken", p.stdout + p.stderr)

    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "claim-closure"; d.mkdir(); make_case(d, head_balances()); run_scan(d)
        import a4_gate
        fails = []
        source = a4_gate.distribution_claim_source(str(d), "new-analysis", [], fails)
        ok &= check("漏登 dist-claims 被 A4 双向闭合拒绝", source is not None
                    and any("不闭合" in x for x in fails), str(fails))

    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "explained"; d.mkdir(); _, final = prepare_explanation_case(d)
        p = subprocess.run([sys.executable, str(EXPLAIN), "--case-dir", str(d),
                            "--scan", "dist_rounds/round_1/distribution_scan.json",
                            "--out", "distribution_explanation.json"], capture_output=True, text=True)
        out = json.loads((d / "distribution_explanation.json").read_text()) if (d / "distribution_explanation.json").is_file() else {}
        ok &= check("五判据真实闭合才 EXPLAINED", final.returncode == 0 and p.returncode == 0
                    and out.get("verdict") == "EXPLAINED"
                    and all(out["cluster_results"][0]["checks"].values()), p.stdout + p.stderr)
        seal = json.loads((d / "a4_seal.json").read_text()); seal["revision"] = 2
        write_json(d / "a4_seal.json", seal)
        pv = subprocess.run([sys.executable, str(EXPLAIN), "validate", "--case-dir", str(d),
                             "--explanation", "distribution_explanation.json"],
                            capture_output=True, text=True)
        ok &= check("解释绑定过期 A4 seal 被拒", pv.returncode == 2, pv.stdout + pv.stderr)

    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "forged"; d.mkdir(); _, final = prepare_explanation_case(d, forged=True)
        p = subprocess.run([sys.executable, str(EXPLAIN), "--case-dir", str(d),
                            "--scan", "dist_rounds/round_1/distribution_scan.json",
                            "--out", "distribution_explanation.json"], capture_output=True, text=True)
        out = json.loads((d / "distribution_explanation.json").read_text()) if (d / "distribution_explanation.json").is_file() else {}
        failed_checks = [x.get("checks", {}) for x in out.get("cluster_results", [])
                         if x.get("verdict") == "UNEXPLAINED"]
        ok &= check("手搓 EXPLAINED 成员不闭合拒绝", final.returncode == 0 and p.returncode == 2
                    and out.get("verdict") == "UNEXPLAINED"
                    and any(x.get("members") is False and x.get("quantity") is False
                            for x in failed_checks),
                    p.stdout + p.stderr)

    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "new-cluster"; d.mkdir()
        tail = smooth_balances(240); tail_total = sum(tail.values()); tail["head-new"] = tail_total // 3
        make_case(d, tail)
        write_json(d / "candidate_screening.json", {"schema": "candidate-screening/v1",
            "auto_excluded_candidate": [{"address": "head-new", "bucket": "public_facility"}]})
        p0 = run_scan(d); initial = json.loads((d / "distribution_scan.json").read_text())
        add_final_inputs(d, [{"id": "C1", "text": "普通命题", "files": ["evidence.json"],
                              "report_locations": ["报告.md:1"]}])
        p1 = run_scan(d, "final", "--round", "1")
        pr = subprocess.run([sys.executable, str(SCAN), "record-round", "--case-dir", str(d),
                             "--scan", "dist_rounds/round_1/distribution_scan.json"],
                            capture_output=True, text=True)
        ledger = json.loads((d / "distribution_rounds.json").read_text()) if (d / "distribution_rounds.json").is_file() else {}
        ok &= check("initial NORMAL 到 final ABNORMAL 新簇强制回流且 final 图仍空",
                    p0.returncode == 0 and initial.get("verdict") == "NORMAL_SHAPE"
                    and p1.returncode == 0 and pr.returncode == 0
                    and ledger.get("terminal") is None
                    and ledger.get("rounds", [{}])[-1].get("status") == "REQUIRES_A4_REFLOW"
                    and not (d / "charts/final/holder_distribution_current.png").exists(),
                    p1.stdout + p1.stderr + pr.stdout + pr.stderr)
        # 台账删除后从 round 2 续跑必须失败，不能归零重计。
        (d / "distribution_rounds.json").unlink()
        p2 = run_scan(d, "final", "--round", "2")
        pr2 = subprocess.run([sys.executable, str(SCAN), "record-round", "--case-dir", str(d),
                              "--scan", "dist_rounds/round_2/distribution_scan.json"],
                             capture_output=True, text=True)
        ok &= check("删 rounds 台账后不可从非首轮归零", p2.returncode == 2 and pr2.returncode == 2,
                    p2.stdout + p2.stderr + pr2.stdout + pr2.stderr)

    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "adj"; d.mkdir(); _, final = prepare_explanation_case(d)
        pt = subprocess.run([sys.executable, str(ADJUDICATION), "distribution-template",
                             "--case-dir", str(d), "--scan", "dist_rounds/round_1/distribution_scan.json"],
                            capture_output=True, text=True)
        adj = json.loads((d / "distribution_adjudications.json").read_text()) if (d / "distribution_adjudications.json").is_file() else {}
        adj["adjudicated_at"] = "2026-08-05T00:00:00Z"
        for row in adj.get("adjudications", []):
            row["candidate_verdict"] = "excluded"
            row["excluded_members"] = [{"addr": x, "reason": "合成排除证据"}
                                       for x in row.pop("_members_total", [])]
        write_json(d / "distribution_adjudications.json", adj)
        valid = subprocess.run([sys.executable, str(ADJUDICATION), "distribution-validate",
                                "--case-dir", str(d)], capture_output=True, text=True)
        ok &= check("distribution 新候选类型合法裁决通过", valid.returncode == 0,
                    valid.stdout + valid.stderr)
        mutations = []
        bad = copy.deepcopy(adj); bad["schema"] = "distribution-adjudications/v0"; mutations.append(("旧 schema", bad))
        bad = copy.deepcopy(adj); bad["source_scan"]["sha256"] = "0" * 64; mutations.append(("来源哈希", bad))
        bad = copy.deepcopy(adj); bad["adjudications"].append(copy.deepcopy(bad["adjudications"][0])); mutations.append(("重复 ID", bad))
        bad = copy.deepcopy(adj); bad["adjudications"] = bad["adjudications"][1:]; mutations.append(("候选集漏项", bad))
        bad = copy.deepcopy(adj); bad["adjudications"][0]["candidate_kind"] = "distribution_fake"; mutations.append(("候选类型", bad))
        bad = copy.deepcopy(adj); bad["adjudications"][0]["candidate_sha256"] = "0" * 64; mutations.append(("候选哈希", bad))
        bad = copy.deepcopy(adj); bad["adjudications"][0]["excluded_members"] = []; mutations.append(("成员闭合", bad))
        bad = copy.deepcopy(adj); bad["adjudications"][0]["excluded_members"][0]["reason"] = ""; mutations.append(("排除理由", bad))
        bad = copy.deepcopy(adj); bad["adjudications"][0]["raw_balance"] = "0"; mutations.append(("raw 重算", bad))
        rejected = True; details = []
        for label, bad in mutations:
            write_json(d / "distribution_adjudications.json", bad)
            check_bad = subprocess.run([sys.executable, str(ADJUDICATION), "distribution-validate",
                                        "--case-dir", str(d)], capture_output=True, text=True)
            rejected &= check_bad.returncode == 2; details.append(f"{label}={check_bad.returncode}")
        ok &= check("distribution validator 九类反例全部拒绝", rejected, ", ".join(details))

        unresolved = copy.deepcopy(adj)
        for row in unresolved.get("adjudications", []):
            row["candidate_verdict"] = "unresolved"
            for item in row.get("excluded_members", []):
                item["reason"] = "尚未查清"
        write_json(d / "distribution_adjudications.json", unresolved)
        pv = subprocess.run([sys.executable, str(ADJUDICATION), "distribution-validate",
                             "--case-dir", str(d)], capture_output=True, text=True)
        ok &= check("distribution unresolved 达 2% 经济门即拒", final.returncode == 0
                    and pt.returncode == 0 and pv.returncode == 2 and "2%" in pv.stdout,
                    pv.stdout + pv.stderr)

    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "waiver"; d.mkdir()
        write_json(d / "scan.json", {"schema": "distribution-scan/v1"})
        write_json(d / "a4_seal.json", {"schema": "a4-seal/v4"})
        errors = distribution_scan.validate_waiver(d, {"schema": "distribution-exception-receipt/v1"},
                                                    d / "scan.json", "0" * 64, 2)
        ok &= check("waiver 缺用户决定与绑定字段必拒", bool(errors), str(errors))

    print("PASS: distribution gate red-green contract" if ok else "FAIL: distribution gate contract")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
