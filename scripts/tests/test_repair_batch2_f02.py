#!/usr/bin/env python3
"""工单 B / F-02：对抗复核 v3 结构、覆盖、绑定与失败原子性回归。"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
RUNNER = REPO / "scripts/report/adversarial_review_runner.py"
sys.path[:0] = [str(HERE), str(HERE.parent / "report"), str(HERE.parent / "lib")]

FAILS: list[str] = []


def check(name, condition, detail=""):
    if condition:
        print(f"ok    {name}")
    else:
        print(f"FAIL  {name}  {detail}")
        FAILS.append(name)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value) -> Path:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def make_case(root: Path, claim_ids=("C1", "C2")) -> str:
    write_json(root / "a4_claims.json", {
        "schema": "a4-claims/v2",
        "claims": [{"id": cid, "text": f"claim {cid}", "files": []}
                   for cid in claim_ids],
    })
    write_json(root / "accounting_mode.json", {
        "chain": "bsc", "token": "0xtoken", "as_of_block": 123,
    })
    write_json(root / "blockers.json", [])
    return sha(root / "a4_claims.json")


def entrypoint(root: Path, name: str, payload=None, raw=None) -> Path:
    path = root / name
    if raw is None:
        raw = json.dumps(payload, ensure_ascii=False)
    path.write_text(
        "import os\nfrom pathlib import Path\n"
        f"Path(os.environ['CHIP_REVIEW_OUTPUT']).write_text({raw!r}, encoding='utf-8')\n",
        encoding="utf-8",
    )
    return path


def claim_artifact(registry_sha: str, results, role="entity_attribution_skeptic"):
    return {
        "schema": "adversarial-review-artifact/v1",
        "role": role,
        "registry_sha256": registry_sha,
        "results": results,
    }


def result(cid="C1", verdict="CONFIRMED", evidence=None, alternatives=None):
    return {
        "claim_id": cid,
        "verdict": verdict,
        "evidence": ["recomputed row 1"] if evidence is None else evidence,
        "alternative_explanations": [] if alternatives is None else alternatives,
    }


def critic_artifact(registry_sha: str):
    return {
        "schema": "adversarial-review-artifact/v1",
        "role": "completeness_critic",
        "registry_sha256": registry_sha,
        "findings": [],
        "non_covered": [],
    }


def run_role(root: Path, role: str, payload=None, raw=None, stem=None):
    stem = stem or role
    entry = entrypoint(root, f"{stem}.py", payload=payload, raw=raw)
    artifact = root / f"{stem}.json"
    receipt = root / f"{stem}_execution.json"
    proc = subprocess.run([
        sys.executable, str(RUNNER), str(root), "--role", role,
        "--entrypoint", entry.name, "--artifact", artifact.name,
        "--receipt", receipt.name,
    ], capture_output=True, text=True)
    return proc, artifact, receipt


def finalize(root: Path, receipts, *, blockers="blockers.json", out="adversarial_review.json"):
    argv = [sys.executable, str(RUNNER), "finalize", str(root),
            "--claim-registry", "a4_claims.json"]
    for receipt in receipts:
        argv += ["--receipt", Path(receipt).name]
    argv += ["--blockers", blockers, "--out", out]
    return subprocess.run(argv, capture_output=True, text=True)


def residue(root: Path):
    return sorted(p.name for p in root.iterdir()
                  if ".staging" in p.name or ".tmp." in p.name)


def build_valid(root: Path):
    registry_sha = make_case(root)
    p1, _, r1 = run_role(
        root, "entity_attribution_skeptic",
        claim_artifact(registry_sha, [result("C1"), result("C2", "WEAKENED")]),
        stem="skeptic",
    )
    p2, _, r2 = run_role(root, "completeness_critic", critic_artifact(registry_sha),
                         stem="critic")
    proc = finalize(root, [r1, r2]) if p1.returncode == p2.returncode == 0 else None
    return p1, p2, proc, r1, r2


def t_original_two_byte_shell():
    with tempfile.TemporaryDirectory(prefix="f02-ok-") as td:
        root = Path(td)
        make_case(root)
        proc, artifact, receipt = run_role(
            root, "entity_attribution_skeptic", raw="ok", stem="two_byte")
        check("原反例：2 字节 ok 必须被 runner 拒绝且正式位/暂存位零残留",
              proc.returncode == 2 and not artifact.exists() and not receipt.exists()
              and residue(root) == [],
              (proc.returncode, proc.stderr[-160:], artifact.exists(), receipt.exists(), residue(root)))


def t_runner_variants_and_cleanup():
    variants = {
        "非法 verdict": claim_artifact("REG", [result(verdict="MAYBE")]),
        "evidence 空数组": claim_artifact("REG", [result(evidence=[])]),
        "evidence 空串": claim_artifact("REG", [result(evidence=[""])]),
        "evidence 字符串类型": claim_artifact("REG", [result(evidence="ok")]),
        "同 artifact 重复 claim_id": claim_artifact(
            "REG", [result("C1"), result("C1")]),
        "registry 外 claim_id": claim_artifact("REG", [result("OUTSIDE")]),
    }
    for label, payload in variants.items():
        with tempfile.TemporaryDirectory(prefix="f02-runner-") as td:
            root = Path(td)
            registry_sha = make_case(root)
            payload["registry_sha256"] = registry_sha
            proc, artifact, receipt = run_role(root, "entity_attribution_skeptic", payload,
                                               stem="bad")
            check(f"runner 失败分支：{label} exit 2＋零残留",
                  proc.returncode == 2 and not artifact.exists() and not receipt.exists()
                  and residue(root) == [],
                  (proc.returncode, proc.stderr[-160:], residue(root)))
    with tempfile.TemporaryDirectory(prefix="f02-json-") as td:
        root = Path(td)
        make_case(root)
        proc, artifact, receipt = run_role(root, "completeness_critic", raw="{bad-json",
                                           stem="broken")
        check("runner 失败分支：artifact JSON 损坏 exit 2＋staging/正式位零残留",
              proc.returncode == 2 and not artifact.exists() and not receipt.exists()
              and residue(root) == [],
              (proc.returncode, proc.stderr[-160:], residue(root)))


def t_finalize_failures():
    # 合规单路先生成 receipt，供缺件/撕裂/覆盖类聚合负测复用。
    with tempfile.TemporaryDirectory(prefix="f02-final-") as td:
        root = Path(td)
        registry_sha = make_case(root)
        p1, a1, r1 = run_role(root, "entity_attribution_skeptic",
                              claim_artifact(registry_sha, [result("C1")]), stem="skeptic")
        p2, a2, r2 = run_role(root, "completeness_critic", critic_artifact(registry_sha),
                              stem="critic")
        if p1.returncode or p2.returncode:
            check("finalize 前置合规 runner", False, (p1.stderr, p2.stderr))
            return

        proc = finalize(root, [r1, r2])
        check("并集缺一条 claim → finalize exit 2 零半成品",
              proc.returncode == 2 and not (root / "adversarial_review.json").exists()
              and residue(root) == [], (proc.returncode, proc.stderr[-180:], residue(root)))

        a1.unlink()
        proc = finalize(root, [r1, r2])
        check("finalize 缺 artifact → exit 2 零半成品",
              proc.returncode == 2 and not (root / "adversarial_review.json").exists()
              and residue(root) == [], (proc.returncode, proc.stderr[-180:], residue(root)))

    with tempfile.TemporaryDirectory(prefix="f02-missing-") as td:
        root = Path(td)
        make_case(root)
        proc = finalize(root, [root / "missing_execution.json"])
        check("finalize 缺 execution receipt → exit 2 零半成品",
              proc.returncode == 2 and not (root / "adversarial_review.json").exists()
              and residue(root) == [], (proc.returncode, proc.stderr[-180:], residue(root)))
        (root / "a4_claims.json").unlink()
        proc = finalize(root, [root / "missing_execution.json"])
        check("finalize registry 不在场 → exit 2 零半成品",
              proc.returncode == 2 and not (root / "adversarial_review.json").exists()
              and residue(root) == [], (proc.returncode, proc.stderr[-180:], residue(root)))


def t_finalize_variants():
    # registry 外 claim。
    with tempfile.TemporaryDirectory(prefix="f02-extra-") as td:
        root = Path(td)
        registry_sha = make_case(root, ("C1",))
        p1, _, r1 = run_role(root, "entity_attribution_skeptic",
                             claim_artifact(registry_sha, [result("C1"), result("OUTSIDE")]),
                             stem="skeptic")
        p2, _, r2 = run_role(root, "completeness_critic", critic_artifact(registry_sha),
                             stem="critic")
        proc = finalize(root, [r1, r2]) if p1.returncode == p2.returncode == 0 else p1
        check("artifact 含 registry 外 claim → finalize 拒绝",
              proc.returncode == 2 and not (root / "adversarial_review.json").exists(),
              (proc.returncode, proc.stderr[-180:]))

    # execution receipt 的 registry sha 与 artifact/registry 撕裂。
    with tempfile.TemporaryDirectory(prefix="f02-tear-") as td:
        root = Path(td)
        registry_sha = make_case(root, ("C1",))
        p1, _, r1 = run_role(root, "entity_attribution_skeptic",
                             claim_artifact(registry_sha, [result("C1")]), stem="skeptic")
        p2, _, r2 = run_role(root, "completeness_critic", critic_artifact(registry_sha),
                             stem="critic")
        if p1.returncode == p2.returncode == 0:
            receipt = json.loads(r1.read_text())
            receipt["registry_sha256"] = "0" * 64
            write_json(r1, receipt)
            proc = finalize(root, [r1, r2])
        else:
            proc = p1
        check("registry_sha256 与 execution receipt 撕裂 → finalize 拒绝",
              proc.returncode == 2 and not (root / "adversarial_review.json").exists(),
              (proc.returncode, proc.stderr[-180:]))

    blockers = [
        ("blocker 空 id", [{"id": "", "resolved": False}]),
        ("blocker 重复 id", [{"id": "B1", "resolved": False},
                             {"id": "B1", "resolved": False}]),
        ("resolved=true 缺 resolution", [{"id": "B1", "resolved": True}]),
    ]
    for label, rows in blockers:
        with tempfile.TemporaryDirectory(prefix="f02-blocker-") as td:
            root = Path(td)
            p1, p2, _, r1, r2 = build_valid(root)
            if (root / "adversarial_review.json").exists():
                (root / "adversarial_review.json").unlink()
            write_json(root / "bad_blockers.json", rows)
            proc = finalize(root, [r1, r2], blockers="bad_blockers.json") \
                if p1.returncode == p2.returncode == 0 else p1
            check(f"{label} → finalize 拒绝", proc.returncode == 2
                  and not (root / "adversarial_review.json").exists(),
                  (proc.returncode, proc.stderr[-180:]))


def t_consumer_and_green_chain():
    try:
        from shared_release_receipt import validate_adversarial_review
        from audit_release_gate import check_adversarial
    except (ImportError, AttributeError) as exc:
        check("消费侧公开等深验证入口在场", False, exc)
        return

    with tempfile.TemporaryDirectory(prefix="f02-green-") as td:
        root = Path(td)
        p1, p2, proc, _, _ = build_valid(root)
        ok = p1.returncode == p2.returncode == 0 and proc is not None and proc.returncode == 0
        errors = []
        target = {"chain": "bsc", "token": "0xtoken", "as_of_block": 123}
        if ok:
            try:
                validate_adversarial_review(root, target)
            except Exception as exc:
                ok = False
                detail = str(exc)
            else:
                detail = ""
            check_adversarial(root, json.loads((root / "adversarial_review.json").read_text()), errors)
        else:
            detail = ((p1.stderr if p1.returncode else "") +
                      (p2.stderr if p2.returncode else "") +
                      (proc.stderr if proc is not None else ""))[-300:]
        check("绿例：两角色 runner→finalize→shared consumer→audit consumer 全链绿",
              ok and errors == [], (detail, errors))

        if ok:
            # 同字节的案内替身也不能冒充固定权威路径 a4_claims.json。
            (root / "alternate_claims.json").write_bytes((root / "a4_claims.json").read_bytes())
            aggregate = json.loads((root / "adversarial_review.json").read_text())
            aggregate["claim_registry"]["path"] = "alternate_claims.json"
            write_json(root / "adversarial_review.json", aggregate)
            alternate_rejected = False
            try:
                validate_adversarial_review(root, target)
            except ValueError:
                alternate_rejected = True
            check("同字节案内替身不能取代固定权威路径 a4_claims.json",
                  alternate_rejected, alternate_rejected)
            aggregate["claim_registry"]["path"] = "a4_claims.json"
            write_json(root / "adversarial_review.json", aggregate)

            registry = json.loads((root / "a4_claims.json").read_text())
            registry["claims"][0]["text"] = "rewritten after runner"
            write_json(root / "a4_claims.json", registry)
            shared_rejected = False
            try:
                validate_adversarial_review(root, target)
            except ValueError:
                shared_rejected = True
            errors = []
            check_adversarial(root, json.loads((root / "adversarial_review.json").read_text()), errors)
            check("runner 后改写 a4_claims.json → 两个消费侧独立重算 sha 后均拒",
                  shared_rejected and bool(errors), (shared_rejected, errors))

    with tempfile.TemporaryDirectory(prefix="f02-v2-") as td:
        root = Path(td)
        make_case(root)
        write_json(root / "adversarial_review.json", {
            "schema": "adversarial-review/v2", "target": {
                "chain": "bsc", "token": "0xtoken", "as_of_block": 123},
            "reviews": [], "blocking_findings": [], "release_decision": "PASS",
        })
        shared_msg = ""
        try:
            validate_adversarial_review(root, {
                "chain": "bsc", "token": "0xtoken", "as_of_block": 123})
        except ValueError as exc:
            shared_msg = str(exc)
        errors = []
        check_adversarial(root, json.loads((root / "adversarial_review.json").read_text()), errors)
        joined = shared_msg + " " + " ".join(errors)
        check("v2 旧件 fail-closed 且错误信息含 v3 重跑指引",
              bool(shared_msg) and bool(errors) and "v3" in joined and "重跑" in joined,
              joined)


def main():
    t_original_two_byte_shell()
    t_runner_variants_and_cleanup()
    t_finalize_failures()
    t_finalize_variants()
    t_consumer_and_green_chain()
    if FAILS:
        print(f"FAIL workorder B F-02 regressions: {len(FAILS)}")
        return 1
    print("PASS workorder B F-02 regressions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
