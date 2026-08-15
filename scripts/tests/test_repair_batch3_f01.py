#!/usr/bin/env python3
"""批3工单 F01：A4 blocker 联动、文本门槛、entrypoint 身份与迁移回归。"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path[:0] = [str(HERE), str(HERE.parent / "report"), str(HERE.parent / "lib")]

from test_repair_batch2_f02 import (  # noqa: E402
    claim_artifact,
    critic_artifact,
    entrypoint,
    finalize,
    make_case,
    rejected,
    rejection_message,
    residue,
    result,
    run_existing_role,
    run_role,
    sha,
    write_json,
)


FAILS: list[str] = []
TARGET = {"chain": "bsc", "token": "0xtoken", "as_of_block": 123}


def check(name, condition, detail=""):
    if condition:
        print(f"ok    {name}")
    else:
        print(f"FAIL  {name}  {detail}")
        FAILS.append(name)


def blocker(kind="manual", ref="fixture manual", *, ident="B1", resolved=True,
            resolution="已完成逐项核查并修正该缺口"):
    item = {"id": ident, "resolved": resolved,
            "source": {"kind": kind, "ref": ref}}
    if resolved:
        item["resolution"] = resolution
    return item


def artifact_ref(path: Path):
    return {"path": path.name, "size": path.stat().st_size, "sha256": sha(path)}


def assemble_aggregate(root: Path, receipts, blockers, *, schema=None):
    import adversarial_review_runner as runner

    reviews = []
    for receipt_path in receipts:
        execution = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
        reviews.append({
            "role": execution["role"], "exit_code": 0,
            "artifact": execution["artifact"], "runner": execution["producer"],
            "execution_receipt": artifact_ref(Path(receipt_path)),
        })
    registry = root / "a4_claims.json"
    aggregate = {
        "schema": schema or getattr(runner, "AGGREGATE_SCHEMA", "adversarial-review/v4"),
        "target": TARGET, "producer": runner.repo_producer(),
        "claim_registry": {"path": registry.name, "size": registry.stat().st_size,
                           "sha256": sha(registry), "schema": "a4-claims/v2"},
        "reviews": reviews, "blocking_findings": blockers,
        "release_decision": "PASS",
    }
    ledger_validator = getattr(runner, "validate_review_ledger", None)
    if callable(ledger_validator):
        aggregate["review_ledger"] = ledger_validator(root)[0]
    write_json(root / "adversarial_review.json", aggregate)
    return aggregate


def rebind_artifact(root: Path, aggregate: dict, index: int, mutate):
    """改 artifact 后重绑 execution 与 aggregate；不调用 producer。"""
    review = aggregate["reviews"][index]
    artifact_path = root / review["artifact"]["path"]
    data = json.loads(artifact_path.read_text(encoding="utf-8"))
    mutate(data)
    write_json(artifact_path, data)
    new_artifact = artifact_ref(artifact_path)
    execution_path = root / review["execution_receipt"]["path"]
    execution = json.loads(execution_path.read_text(encoding="utf-8"))
    execution["artifact"] = new_artifact
    write_json(execution_path, execution)
    review["artifact"] = new_artifact
    review["execution_receipt"] = artifact_ref(execution_path)
    write_json(root / "adversarial_review.json", aggregate)


def run_reviews(root: Path, claim_payloads, critic_payloads):
    receipts = []
    procs = []
    for index, payload in enumerate(claim_payloads):
        proc, _, receipt = run_role(
            root, "entity_attribution_skeptic", payload, stem=f"skeptic_{index}")
        procs.append(proc)
        receipts.append(receipt)
    for index, payload in enumerate(critic_payloads):
        proc, _, receipt = run_role(
            root, "completeness_critic", payload, stem=f"critic_{index}")
        procs.append(proc)
        receipts.append(receipt)
    return procs, receipts


def consume(root: Path):
    import audit_release_gate as audit
    import shared_release_receipt as shared

    message = rejection_message(lambda: shared.validate_adversarial_review(root, TARGET))
    errors = []
    data = json.loads((root / "adversarial_review.json").read_text(encoding="utf-8"))
    audit.check_adversarial(root, data, errors, TARGET)
    return message, errors


def t_a_linkage():
    cases = (
        ("finding 无账", ["UNRESOLVED REAL GAP"], [], "CONFIRMED"),
        ("non_covered 无账", [], ["OUTSIDE COVERAGE"], "CONFIRMED"),
        ("REFUTED 无账", [], [], "REFUTED"),
    )
    for label, findings, non_covered, verdict in cases:
        with tempfile.TemporaryDirectory(prefix="f01-link-red-") as td:
            root = Path(td)
            registry_sha = make_case(root, ("C1",))
            critic = critic_artifact(registry_sha)
            critic.update(findings=findings, non_covered=non_covered)
            procs, receipts = run_reviews(
                root, [claim_artifact(registry_sha, [result("C1", verdict)])], [critic])
            proc = finalize(root, receipts) if all(p.returncode == 0 for p in procs) else procs[0]
            check(f"A 联动：{label} → finalize rc2、不落盘、零残留",
                  proc.returncode == 2 and not (root / "adversarial_review.json").exists()
                  and residue(root) == [], (proc.returncode, proc.stderr[-220:], residue(root)))

    with tempfile.TemporaryDirectory(prefix="f01-link-green-") as td:
        root = Path(td)
        registry_sha = make_case(root, ("C1",))
        critic = critic_artifact(registry_sha)
        critic["findings"] = ["UNRESOLVED REAL GAP"]
        procs, receipts = run_reviews(
            root, [claim_artifact(registry_sha, [result("C1")])], [critic])
        write_json(root / "blockers.json", [
            blocker("completeness_finding", "critic_0.json#/findings/0")])
        proc = finalize(root, receipts) if all(p.returncode == 0 for p in procs) else procs[0]
        if proc.returncode == 0:
            message, errors = consume(root)
        else:
            message, errors = proc.stderr[-220:], ["finalize failed"]
        check("A 联动绿例：定位 blocker 关闭后 runner/shared/audit 全链 PASS",
              proc.returncode == 0 and message == "" and errors == [], (message, errors))

    with tempfile.TemporaryDirectory(prefix="f01-link-blocked-") as td:
        root = Path(td)
        registry_sha = make_case(root, ("C1",))
        critic = critic_artifact(registry_sha)
        critic["findings"] = ["OPEN GAP"]
        procs, receipts = run_reviews(
            root, [claim_artifact(registry_sha, [result("C1")])], [critic])
        write_json(root / "blockers.json", [
            blocker("completeness_finding", "critic_0.json#/findings/0", resolved=False)])
        proc = finalize(root, receipts) if all(p.returncode == 0 for p in procs) else procs[0]
        decision = None
        if proc.returncode == 0:
            decision = json.loads((root / "adversarial_review.json").read_text())["release_decision"]
            message, errors = consume(root)
        else:
            message, errors = proc.stderr[-220:], []
        check("A 未决：账全则落盘 BLOCKED，两个消费侧均拒",
              proc.returncode == 0 and decision == "BLOCKED" and bool(message) and bool(errors),
              (decision, message, errors))

    variants = (
        ("幽灵账", [blocker("non_covered", "critic_0.json#/non_covered/0")]),
        ("同对象重复记账", [blocker("completeness_finding", "critic_0.json#/findings/0",
                                  ident="B1"),
                          blocker("completeness_finding", "critic_0.json#/findings/0",
                                  ident="B2")]),
    )
    for label, rows in variants:
        with tempfile.TemporaryDirectory(prefix="f01-link-badbook-") as td:
            root = Path(td)
            registry_sha = make_case(root, ("C1",))
            critic = critic_artifact(registry_sha)
            critic["findings"] = ["REAL GAP"] if label != "幽灵账" else []
            procs, receipts = run_reviews(
                root, [claim_artifact(registry_sha, [result("C1")])], [critic])
            write_json(root / "blockers.json", rows)
            proc = finalize(root, receipts) if all(p.returncode == 0 for p in procs) else procs[0]
            check(f"A 账本：{label}拒绝", proc.returncode == 2
                  and not (root / "adversarial_review.json").exists(), proc.stderr[-220:])

    multi_cases = (
        ("两 critic 不同 finding 缺一账",
         ["finding one"], ["finding two"],
         [blocker("completeness_finding", "critic_0.json#/findings/0")]),
        ("两 critic 同文 finding 仍按路径逐项记账",
         ["same finding"], ["same finding"],
         [blocker("completeness_finding", "critic_0.json#/findings/0")]),
    )
    for label, first, second, rows in multi_cases:
        with tempfile.TemporaryDirectory(prefix="f01-link-multicritic-") as td:
            root = Path(td)
            registry_sha = make_case(root, ("C1",))
            critics = []
            for findings in (first, second):
                item = critic_artifact(registry_sha)
                item["findings"] = findings
                critics.append(item)
            procs, receipts = run_reviews(
                root, [claim_artifact(registry_sha, [result("C1")])], critics)
            write_json(root / "blockers.json", rows)
            proc = finalize(root, receipts) if all(p.returncode == 0 for p in procs) else procs[0]
            check(f"A 多 artifact：{label}", proc.returncode == 2, proc.stderr[-240:])

    with tempfile.TemporaryDirectory(prefix="f01-link-multireviewer-") as td:
        root = Path(td)
        registry_sha = make_case(root, ("C1",))
        claims = [
            claim_artifact(registry_sha, [result("C1", "REFUTED", evidence=["hard evidence one"])]),
            claim_artifact(registry_sha, [result("C1", "REFUTED", evidence=["hard evidence two"])]),
        ]
        procs, receipts = run_reviews(root, claims, [critic_artifact(registry_sha)])
        write_json(root / "blockers.json", [
            blocker("refuted_claim", "skeptic_0.json#/results/0:C1")])
        proc = finalize(root, receipts) if all(p.returncode == 0 for p in procs) else procs[0]
        check("A 多 artifact：两个 reviewer 同 claim REFUTED 仍需两项处置",
              proc.returncode == 2, proc.stderr[-240:])

    with tempfile.TemporaryDirectory(prefix="f01-link-allmulti-") as td:
        root = Path(td)
        registry_sha = make_case(root, ("C1",))
        critics = []
        rows = []
        for index, text in enumerate(("first gap", "second gap")):
            item = critic_artifact(registry_sha)
            item["findings"] = [text]
            critics.append(item)
            rows.append(blocker("completeness_finding", f"critic_{index}.json#/findings/0",
                                ident=f"B{index + 1}"))
        procs, receipts = run_reviews(
            root, [claim_artifact(registry_sha, [result("C1")])], critics)
        write_json(root / "blockers.json", rows)
        proc = finalize(root, receipts) if all(p.returncode == 0 for p in procs) else procs[0]
        check("A 多 artifact：全量累积而非只保留循环末份",
              proc.returncode == 0, proc.stderr[-240:])

    with tempfile.TemporaryDirectory(prefix="f01-link-manual-") as td:
        root = Path(td)
        registry_sha = make_case(root, ("C1",))
        procs, receipts = run_reviews(
            root, [claim_artifact(registry_sha, [result("C1")])],
            [critic_artifact(registry_sha)])
        write_json(root / "blockers.json", [blocker()])
        proc = finalize(root, receipts) if all(p.returncode == 0 for p in procs) else procs[0]
        check("A manual blocker 不进双向对账且已决可 PASS", proc.returncode == 0,
              proc.stderr[-220:])

    import adversarial_review_runner as runner
    structural = (
        ("多余 note 键", {**blocker(), "note": "forbidden"}),
        ("缺 source", {"id": "B1", "resolved": False}),
        ("source 坏 kind", blocker("unknown", "ref")),
        ("source 零宽 ref", blocker("manual", "\u200b")),
        ("source 多余键", {**blocker(), "source": {"kind": "manual", "ref": "x", "x": 1}}),
    )
    for label, row in structural:
        check(f"A blocker 结构：{label}拒绝",
              rejected(lambda row=row: runner.validate_blocking_findings([row])))

    for mutation in ("delete", "manual"):
        with tempfile.TemporaryDirectory(prefix="f01-consumer-book-") as td:
            root = Path(td)
            registry_sha = make_case(root, ("C1",))
            critic = critic_artifact(registry_sha)
            critic["findings"] = ["consumer must rebuild"]
            procs, receipts = run_reviews(
                root, [claim_artifact(registry_sha, [result("C1")])], [critic])
            rows = [blocker("completeness_finding", "critic_0.json#/findings/0")]
            write_json(root / "blockers.json", rows)
            proc = finalize(root, receipts) if all(p.returncode == 0 for p in procs) else procs[0]
            if proc.returncode == 0:
                aggregate = json.loads((root / "adversarial_review.json").read_text())
                if mutation == "delete":
                    aggregate["blocking_findings"] = []
                else:
                    aggregate["blocking_findings"][0]["source"]["kind"] = "manual"
                write_json(root / "adversarial_review.json", aggregate)
                message, errors = consume(root)
            else:
                message, errors = proc.stderr, []
            check(f"A 消费侧独立重建：手抄 {mutation} 账仍被 shared/audit 拒",
                  proc.returncode == 0 and bool(message) and bool(errors), (message, errors))


def t_b_thresholds():
    evidence_cases = (
        ("ASCII 9", "abcdefghi", False), ("ASCII 10", "abcdefghij", True),
        ("汉字 9", "一二三四五六七八九", False), ("汉字 10", "一二三四五六七八九十", True),
        ("9 实义+20 零宽", "abcdefghi" + "\u200b" * 20, False),
        ("10 实义+零宽", "abcdefghij\u200b", True),
        ("纯 10 标点", "!!!!!!!!!!", True),
        ("ab 七空格 cd", "ab       cd", False),
    )
    for label, evidence, expected_ok in evidence_cases:
        with tempfile.TemporaryDirectory(prefix="f01-evidence-") as td:
            root = Path(td)
            registry_sha = make_case(root, ("C1",))
            proc, artifact, receipt = run_role(
                root, "entity_attribution_skeptic",
                claim_artifact(registry_sha, [result("C1", evidence=[evidence])]), stem="probe")
            check(f"B evidence 边界：{label}", (proc.returncode == 0) is expected_ok,
                  (proc.returncode, proc.stderr[-180:], artifact.exists(), receipt.exists()))

    import adversarial_review_runner as runner
    resolution_cases = (
        ("resolved=true 9", blocker(resolution="abcdefghi"), False),
        ("resolved=true 10", blocker(resolution="abcdefghij"), True),
        ("resolved=false 但写 9", {**blocker(resolved=False), "resolution": "abcdefghi"}, False),
    )
    for label, row, expected_ok in resolution_cases:
        accepted = not rejected(lambda row=row: runner.validate_blocking_findings([row]))
        check(f"B resolution 边界：{label}", accepted is expected_ok, accepted)

    with tempfile.TemporaryDirectory(prefix="f01-alt-short-") as td:
        root = Path(td)
        registry_sha = make_case(root, ("C1",))
        proc, _, _ = run_role(
            root, "entity_attribution_skeptic",
            claim_artifact(registry_sha, [result("C1", alternatives=["OTC"])]), stem="alt")
        check("B alternative_explanations 短文本不误伤", proc.returncode == 0,
              proc.stderr[-180:])

    with tempfile.TemporaryDirectory(prefix="f01-consumer-evidence-") as td:
        root = Path(td)
        registry_sha = make_case(root, ("C1",))
        procs, receipts = run_reviews(
            root, [claim_artifact(registry_sha, [result("C1", evidence=["abcdefghij"])])],
            [critic_artifact(registry_sha)])
        proc = finalize(root, receipts) if all(p.returncode == 0 for p in procs) else procs[0]
        if proc.returncode == 0:
            aggregate = json.loads((root / "adversarial_review.json").read_text())
            skeptic_index = next(i for i, row in enumerate(aggregate["reviews"])
                                 if row["role"] == "entity_attribution_skeptic")
            rebind_artifact(root, aggregate, skeptic_index,
                            lambda data: data["results"][0].update(evidence=["abcdefghi"]))
            message, _ = consume(root)
        else:
            message = proc.stderr
        check("B 消费侧独立门槛：重绑后 9 实义 evidence 仍拒",
              proc.returncode == 0 and bool(message), message)


def t_c_entrypoint_identity():
    shared_body = (
        "import json, os\nfrom pathlib import Path\n"
        "role=os.environ['CHIP_REVIEW_ROLE']\n"
        "payload={'schema':'adversarial-review-artifact/v2','role':role,"
        "'registry_sha256':os.environ['CHIP_REVIEW_REGISTRY_SHA256']}\n"
        "payload.update({'findings':[],'non_covered':[]}) if role == 'completeness_critic' "
        "else payload.update({'results':[{'claim_id':'C1','verdict':'CONFIRMED',"
        "'evidence':['abcdefghij'],'alternative_explanations':[]}]})\n"
        "Path(os.environ['CHIP_REVIEW_OUTPUT']).write_text(json.dumps(payload))\n"
    )
    with tempfile.TemporaryDirectory(prefix="f01-entry-twin-") as td:
        root = Path(td)
        make_case(root, ("C1",))
        entry = root / "shared.py"
        entry.write_text(shared_body, encoding="utf-8")
        p1, _, r1 = run_existing_role(root, "entity_attribution_skeptic", entry, "skeptic")
        p2, _, r2 = run_existing_role(root, "completeness_critic", entry, "critic")
        proc = finalize(root, [r1, r2]) if p1.returncode == p2.returncode == 0 else p1
        check("C 两角色同字节 entrypoint → finalize rc2",
              proc.returncode == 2 and not (root / "adversarial_review.json").exists(),
              proc.stderr[-220:])
        if p1.returncode == p2.returncode == 0:
            assemble_aggregate(root, [r1, r2], [])
            message, _ = consume(root)
        else:
            message = p1.stderr + p2.stderr
        check("C 消费侧孪生：手抄 PASS 聚合仍拒同字节 entrypoint", bool(message), message)

    with tempfile.TemporaryDirectory(prefix="f01-entry-distinct-") as td:
        root = Path(td)
        registry_sha = make_case(root, ("C1",))
        procs, receipts = run_reviews(
            root, [claim_artifact(registry_sha, [result("C1", evidence=["abcdefghij"])])],
            [critic_artifact(registry_sha)])
        proc = finalize(root, receipts) if all(p.returncode == 0 for p in procs) else procs[0]
        check("C 两角色分叉 body → finalize 绿", proc.returncode == 0, proc.stderr[-220:])


def t_d_migration():
    with tempfile.TemporaryDirectory(prefix="f01-v3-") as td:
        root = Path(td)
        make_case(root, ("C1",))
        write_json(root / "adversarial_review.json", {
            "schema": "adversarial-review/v3", "target": TARGET,
            "reviews": [], "blocking_findings": [], "release_decision": "PASS",
        })
        message, errors = consume(root)
        joined = message + " " + " ".join(errors)
        check("D v3 旧聚合 shared/audit 均拒且提示 v4 重跑",
              bool(message) and bool(errors) and "v4" in joined and "重跑" in joined, joined)


def t_e_documentation():
    protocol = (REPO / "references/independent-audit-protocol.md").read_text(encoding="utf-8")
    workflow = (REPO / "references/analyze-workflow.md").read_text(encoding="utf-8")
    research = (REPO / "references/research-workflows.md").read_text(encoding="utf-8")
    check("E protocol 文档含 source/refuted_claim/10 门槛/v4 重跑",
          all(needle in protocol for needle in
              ("source", "refuted_claim", "10 个实义白名单字符", "v4", "重跑")))
    check("E analyze-workflow 文档含 evidence 10 门槛与 v4",
          "10 个实义白名单字符" in workflow and "adversarial-review/v4" in workflow)
    check("E research-workflows 文档含 artifact/v2 与联动越界",
          "adversarial-review-artifact/v2" in research and "联动" in research)


def _ledger_lines(root: Path) -> list[bytes]:
    path = root / "adversarial_review_ledger.jsonl"
    return path.read_bytes().splitlines(keepends=True) if path.is_file() else []


def _run_exact_review(root: Path, role: str, review_entrypoint: Path,
                      artifact_name: str, receipt_name: str):
    return subprocess.run([
        sys.executable, str(REPO / "scripts/report/adversarial_review_runner.py"),
        str(root), "--role", role, "--entrypoint", review_entrypoint.name,
        "--artifact", artifact_name, "--receipt", receipt_name,
    ], capture_output=True, text=True)


def _write_manual_ledger_aggregate(root: Path, receipts: list[Path]) -> dict:
    """手抄旧式聚合，专测 shared/audit 不得依赖 finalize 代挡。"""
    import adversarial_review_runner as runner

    reviews = []
    for receipt_path in receipts:
        execution = json.loads(receipt_path.read_text(encoding="utf-8"))
        reviews.append({
            "role": execution["role"], "exit_code": execution["exit_code"],
            "artifact": execution["artifact"], "runner": execution["producer"],
            "execution_receipt": artifact_ref(receipt_path),
        })
    ledger_lines = _ledger_lines(root)
    active_names = {
        json.loads(raw_line.decode("utf-8"))["receipt_path"]
        for raw_line in ledger_lines
    }
    registry = root / "a4_claims.json"
    aggregate = {
        "schema": runner.AGGREGATE_SCHEMA,
        "target": TARGET,
        "producer": runner.repo_producer(),
        "claim_registry": {
            "path": registry.name, "size": registry.stat().st_size,
            "sha256": sha(registry), "schema": "a4-claims/v2",
        },
        "reviews": reviews,
        "review_ledger": {
            "entries": len(ledger_lines),
            "active": len(active_names),
            "tip_sha": hashlib.sha256(ledger_lines[-1]).hexdigest(),
        },
        "blocking_findings": [],
        "release_decision": "PASS",
    }
    write_json(root / "adversarial_review.json", aggregate)
    return aggregate


def t_f_execution_ledger():
    with tempfile.TemporaryDirectory(prefix="f01-ledger-omit-") as td:
        root = Path(td)
        registry_sha = make_case(root, ("C1",))
        p1, _, r1 = run_role(
            root, "entity_attribution_skeptic",
            claim_artifact(registry_sha, [result("C1", evidence=["abcdefghij"])]),
            stem="claim")
        p2, _, r2 = run_role(
            root, "completeness_critic", critic_artifact(registry_sha), stem="clean")
        bad = critic_artifact(registry_sha)
        bad["findings"] = ["UNFAVORABLE FINDING"]
        p3, bad_artifact, r3 = run_role(
            root, "completeness_critic", bad, stem="bad")
        proc = finalize(root, [r1, r2]) if p1.returncode == p2.returncode == p3.returncode == 0 else p1
        check("F ledger 本尊：三路已落账但 finalize 省略不利 receipt → rc2 不落盘",
              p1.returncode == p2.returncode == p3.returncode == 0
              and bad_artifact.is_file() and r3.is_file()
              and proc.returncode == 2 and not (root / "adversarial_review.json").exists(),
              (p1.returncode, p2.returncode, p3.returncode, proc.returncode,
               proc.stderr[-260:], _ledger_lines(root)))

    for mutation in ("delete-middle", "edit-line"):
        with tempfile.TemporaryDirectory(prefix="f01-ledger-chain-") as td:
            root = Path(td)
            registry_sha = make_case(root, ("C1",))
            p1, _, r1 = run_role(
                root, "entity_attribution_skeptic",
                claim_artifact(registry_sha, [result("C1")]), stem="claim")
            critic_a = critic_artifact(registry_sha)
            critic_a["fixture_nonce"] = "a"
            critic_b = critic_artifact(registry_sha)
            critic_b["fixture_nonce"] = "b"
            p2, _, r2 = run_role(
                root, "completeness_critic", critic_a, stem="critic_a")
            p3, _, r3 = run_role(
                root, "completeness_critic", critic_b, stem="critic_b")
            lines = _ledger_lines(root)
            if len(lines) == 3:
                if mutation == "delete-middle":
                    changed = [lines[0], lines[2]]
                else:
                    row = json.loads(lines[0])
                    old = row["artifact_sha"]
                    row["artifact_sha"] = ("0" if old[0] != "0" else "1") + old[1:]
                    changed = [
                        (json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n").encode(),
                        lines[1], lines[2],
                    ]
                (root / "adversarial_review_ledger.jsonl").write_bytes(b"".join(changed))
            proc = finalize(root, [r1, r2, r3]) if all(
                item.returncode == 0 for item in (p1, p2, p3)) else p1
            label = "手删中间行" if mutation == "delete-middle" else "手改前行内容未重算后继 prev"
            check(f"F ledger 链：{label} → rc2", len(lines) == 3 and proc.returncode == 2,
                  (len(lines), proc.returncode, proc.stderr[-260:]))

    with tempfile.TemporaryDirectory(prefix="f01-ledger-unregistered-") as td:
        root = Path(td)
        registry_sha = make_case(root, ("C1",))
        p1, _, r1 = run_role(
            root, "entity_attribution_skeptic",
            claim_artifact(registry_sha, [result("C1")]), stem="claim")
        critic_a = critic_artifact(registry_sha)
        critic_a["fixture_nonce"] = "registered"
        critic_b = critic_artifact(registry_sha)
        critic_b["fixture_nonce"] = "unregistered"
        p2, _, r2 = run_role(
            root, "completeness_critic", critic_a, stem="critic")
        p3, _, r3 = run_role(
            root, "completeness_critic", critic_b, stem="unregistered")
        lines = _ledger_lines(root)
        if len(lines) == 3:
            (root / "adversarial_review_ledger.jsonl").write_bytes(b"".join(lines[:-1]))
        proc = finalize(root, [r1, r2, r3]) if all(
            item.returncode == 0 for item in (p1, p2, p3)) else p1
        check("F ledger 集合：传入格式合法但 ledger 未登记的 receipt → rc2",
              len(lines) == 3 and proc.returncode == 2,
              (len(lines), proc.returncode, proc.stderr[-260:]))

    with tempfile.TemporaryDirectory(prefix="f01-ledger-rerun-") as td:
        root = Path(td)
        registry_sha = make_case(root, ("C1",))
        p1, _, r1 = run_role(
            root, "entity_attribution_skeptic",
            claim_artifact(registry_sha, [result("C1")]), stem="claim")
        bad = critic_artifact(registry_sha)
        bad["findings"] = ["REPLACED BAD FINDING"]
        p2, _, _ = run_role(root, "completeness_critic", bad, stem="critic")
        p3, _, r3 = run_role(
            root, "completeness_critic", critic_artifact(registry_sha), stem="critic")
        proc = finalize(root, [r1, r3]) if p1.returncode == p2.returncode == p3.returncode == 0 else p3
        aggregate = (json.loads((root / "adversarial_review.json").read_text())
                     if proc.returncode == 0 else {})
        check("F ledger 重跑：同 receipt_path clean 覆盖 bad，末行有效且全链绿",
              p1.returncode == p2.returncode == p3.returncode == proc.returncode == 0
              and aggregate.get("review_ledger", {}).get("entries") == 3
              and aggregate.get("review_ledger", {}).get("active") == 2
              and consume(root) == ("", []),
              (p1.returncode, p2.returncode, p3.returncode, proc.returncode,
               aggregate.get("review_ledger"), p3.stderr[-260:]))

    with tempfile.TemporaryDirectory(prefix="f01-ledger-missing-") as td:
        root = Path(td)
        registry_sha = make_case(root, ("C1",))
        p1, _, r1 = run_role(
            root, "entity_attribution_skeptic",
            claim_artifact(registry_sha, [result("C1")]), stem="claim")
        p2, _, r2 = run_role(
            root, "completeness_critic", critic_artifact(registry_sha), stem="critic")
        ledger = root / "adversarial_review_ledger.jsonl"
        if ledger.is_file():
            ledger.unlink()
        proc = finalize(root, [r1, r2]) if p1.returncode == p2.returncode == 0 else p1
        check("F ledger 缺失：finalize rc2 不落盘",
              proc.returncode == 2 and not (root / "adversarial_review.json").exists(),
              (proc.returncode, proc.stderr[-260:]))

    for mutation in ("aggregate-tip", "ledger-tip"):
        with tempfile.TemporaryDirectory(prefix="f01-ledger-consumer-") as td:
            root = Path(td)
            registry_sha = make_case(root, ("C1",))
            p1, _, r1 = run_role(
                root, "entity_attribution_skeptic",
                claim_artifact(registry_sha, [result("C1")]), stem="claim")
            p2, _, r2 = run_role(
                root, "completeness_critic", critic_artifact(registry_sha), stem="critic")
            proc = finalize(root, [r1, r2]) if p1.returncode == p2.returncode == 0 else p1
            ready = proc.returncode == 0
            if ready and mutation == "aggregate-tip":
                aggregate = json.loads((root / "adversarial_review.json").read_text())
                tip = aggregate.get("review_ledger", {}).get("tip_sha", "")
                if tip:
                    aggregate["review_ledger"]["tip_sha"] = (
                        ("0" if tip[0] != "0" else "1") + tip[1:])
                    write_json(root / "adversarial_review.json", aggregate)
            elif ready:
                lines = _ledger_lines(root)
                if lines:
                    lines[-1] = lines[-1].rstrip(b"\n") + b" \n"
                    (root / "adversarial_review_ledger.jsonl").write_bytes(b"".join(lines))
            if ready:
                message, errors = consume(root)
            else:
                message, errors = proc.stderr, []
            label = "aggregate review_ledger.tip_sha 改一位" if mutation == "aggregate-tip" else "ledger 末行字节改写"
            check(f"F ledger 消费独立性：{label} → shared/audit 双拒",
                  ready and bool(message) and bool(errors),
                  (proc.returncode, message, errors))

    with tempfile.TemporaryDirectory(prefix="f01-ledger-green-") as td:
        root = Path(td)
        registry_sha = make_case(root, ("C1",))
        p1, _, r1 = run_role(
            root, "entity_attribution_skeptic",
            claim_artifact(registry_sha, [result("C1")]), stem="claim")
        p2, _, r2 = run_role(
            root, "completeness_critic", critic_artifact(registry_sha), stem="critic")
        proc = finalize(root, [r1, r2]) if p1.returncode == p2.returncode == 0 else p1
        aggregate = (json.loads((root / "adversarial_review.json").read_text())
                     if proc.returncode == 0 else {})
        check("F ledger 绿例：全传全登记，aggregate 绑定且双消费全绿",
              proc.returncode == 0 and set(aggregate.get("review_ledger", {}))
              == {"entries", "active", "tip_sha"} and consume(root) == ("", []),
              (proc.returncode, aggregate.get("review_ledger"), proc.stderr[-260:]))


def t_f_ledger_identity_and_cardinality():
    with tempfile.TemporaryDirectory(prefix="f01-ledger-alias-") as td:
        root = Path(td)
        probe = root / "CaseProbe"
        probe.write_text("probe", encoding="utf-8")
        case_insensitive = (root / "caseprobe").exists() and os.path.samefile(
            probe, root / "caseprobe")
        probe.unlink()

        registry_sha = make_case(root, ("C1",))
        p1, _, claim_receipt = run_role(
            root, "entity_attribution_skeptic",
            claim_artifact(registry_sha, [result("C1", evidence=["abcdefghij"])]),
            stem="claim")
        critic_entrypoint = entrypoint(
            root, "critic.py", payload=critic_artifact(registry_sha))
        upper_name = "Critic_execution.json"
        lower_name = "critic_execution.json"
        p2 = _run_exact_review(
            root, "completeness_critic", critic_entrypoint, "critic.json", upper_name)
        p3 = _run_exact_review(
            root, "completeness_critic", critic_entrypoint, "critic.json", lower_name)
        upper_receipt = root / upper_name
        lower_receipt = root / lower_name
        same_inode = (upper_receipt.is_file() and lower_receipt.is_file()
                      and os.path.samefile(upper_receipt, lower_receipt))
        proc = finalize(root, [claim_receipt, lower_receipt]) if all(
            item.returncode == 0 for item in (p1, p2, p3)) else p1
        check("F ledger 路径身份：大小写别名/独立实物均不得以 SHA set 折叠过闸",
              p1.returncode == p2.returncode == p3.returncode == 0
              and same_inode is case_insensitive and proc.returncode == 2
              and not (root / "adversarial_review.json").exists(),
              (case_insensitive, same_inode, p1.returncode, p2.returncode,
               p3.returncode, proc.returncode, proc.stderr[-320:]))
        if all(item.returncode == 0 for item in (p1, p2, p3)):
            _write_manual_ledger_aggregate(root, [claim_receipt, lower_receipt])
            message, errors = consume(root)
        else:
            message, errors = p1.stderr + p2.stderr + p3.stderr, []
        check("F ledger 路径身份：手抄 aggregate 后 shared/audit 双拒",
              bool(message) and bool(errors), (message, errors))
        if case_insensitive:
            joined = proc.stderr + message + " ".join(errors)
            check("F ledger 路径身份：别名拒绝消息同时列出两个路径名",
                  upper_name in joined and lower_name in joined, joined[-500:])

    with tempfile.TemporaryDirectory(prefix="f01-ledger-cardinality-") as td:
        root = Path(td)
        registry_sha = make_case(root, ("C1",))
        p1, _, claim_receipt = run_role(
            root, "entity_attribution_skeptic",
            claim_artifact(registry_sha, [result("C1")]), stem="claim")
        p2, critic_artifact_path, critic_receipt = run_role(
            root, "completeness_critic", critic_artifact(registry_sha), stem="critic")
        duplicate_receipt = root / "critic_duplicate_execution.json"
        shutil.copyfile(critic_receipt, duplicate_receipt)
        import adversarial_review_runner as runner
        runner.append_review_ledger_entry(
            root, duplicate_receipt, "completeness_critic", sha(critic_artifact_path))
        proc = finalize(root, [claim_receipt, critic_receipt]) if (
            p1.returncode == p2.returncode == 0) else p1
        check("F ledger 基数：active=3/SHA=2/receipts=2 必须拒绝",
              p1.returncode == p2.returncode == 0
              and not os.path.samefile(critic_receipt, duplicate_receipt)
              and proc.returncode == 2,
              (p1.returncode, p2.returncode, proc.returncode, proc.stderr[-320:]))
        if p1.returncode == p2.returncode == 0:
            _write_manual_ledger_aggregate(root, [claim_receipt, critic_receipt])
            message, errors = consume(root)
        else:
            message, errors = p1.stderr + p2.stderr, []
        check("F ledger 基数：手抄 aggregate 后 shared/audit 双拒",
              bool(message) and bool(errors), (message, errors))

    with tempfile.TemporaryDirectory(prefix="f01-ledger-path-syntax-") as td:
        root = Path(td)
        registry_sha = make_case(root, ("C1",))
        proc, artifact, receipt = run_role(
            root, "completeness_critic", critic_artifact(registry_sha), stem="critic")
        spaced_receipt = root / "critic execution copy.json"
        shutil.copyfile(receipt, spaced_receipt)
        append_rejected = rejected(lambda: runner.append_review_ledger_entry(
            root, spaced_receipt, "completeness_critic", sha(artifact)))
        row = json.loads(_ledger_lines(root)[0])
        row["receipt_path"] = spaced_receipt.name
        raw_line = (json.dumps(
            row, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        parse_rejected = rejected(lambda: runner._parse_review_ledger_bytes(raw_line))
        check("F ledger receipt_path：append 与 ledger parser 均拒空格 basename",
              proc.returncode == 0 and append_rejected and parse_rejected,
              (proc.returncode, append_rejected, parse_rejected))


def main():
    t_a_linkage()
    t_b_thresholds()
    t_c_entrypoint_identity()
    t_d_migration()
    t_e_documentation()
    t_f_execution_ledger()
    t_f_ledger_identity_and_cardinality()
    if FAILS:
        print(f"\n{len(FAILS)} failures: " + "; ".join(FAILS))
        return 1
    print("\nall batch3 F01 tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
