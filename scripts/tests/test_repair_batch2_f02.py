#!/usr/bin/env python3
"""工单 B / F-02：对抗复核 v3 结构、覆盖、绑定与失败原子性回归。"""
from __future__ import annotations

import hashlib
import json
import shutil
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


def run_existing_role(root: Path, role: str, entry: Path, stem: str):
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


def rejected(callable_):
    try:
        callable_()
    except (OSError, ValueError):
        return True
    return False


def rejection_message(callable_):
    try:
        callable_()
    except (OSError, ValueError) as exc:
        return str(exc)
    return ""


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


def rewrite_aggregate_claim_id(root: Path, old: str, new: str):
    """Rebind a valid aggregate after changing one id, without invoking the producer."""
    aggregate_path = root / "adversarial_review.json"
    aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
    registry_path = root / "a4_claims.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    for claim in registry["claims"]:
        if claim.get("id") == old:
            claim["id"] = new
            break
    write_json(registry_path, registry)
    registry_sha = sha(registry_path)
    aggregate["claim_registry"] = {
        "path": registry_path.name,
        "size": registry_path.stat().st_size,
        "sha256": registry_sha,
        "schema": "a4-claims/v2",
    }

    for review in aggregate["reviews"]:
        artifact_path = root / review["artifact"]["path"]
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        artifact["registry_sha256"] = registry_sha
        for item in artifact.get("results", []):
            if item.get("claim_id") == old:
                item["claim_id"] = new
                break
        write_json(artifact_path, artifact)
        artifact_ref = {
            "path": artifact_path.name,
            "size": artifact_path.stat().st_size,
            "sha256": sha(artifact_path),
        }

        execution_path = root / review["execution_receipt"]["path"]
        execution = json.loads(execution_path.read_text(encoding="utf-8"))
        execution["registry_sha256"] = registry_sha
        execution["artifact"] = artifact_ref
        write_json(execution_path, execution)
        review["artifact"] = artifact_ref
        review["execution_receipt"] = {
            "path": execution_path.name,
            "size": execution_path.stat().st_size,
            "sha256": sha(execution_path),
        }
    write_json(aggregate_path, aggregate)


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


def t_meaningful_text_and_claim_identity():
    import adversarial_review_runner as runner
    import shared_release_receipt as shared
    import supply_truth_gate as supply

    check("runner 人工文本判定单源复用 supply_truth_gate._meaningful_text",
          getattr(runner, "_meaningful_text", None) is supply._meaningful_text
          and not hasattr(runner, "_nonempty_string"))

    for label, invisible in (("U+200B", "\u200b"), ("U+3164", "\u3164"),
                             ("U+2800", "\u2800")):
        with tempfile.TemporaryDirectory(prefix="f02-meaningful-") as td:
            root = Path(td)
            registry_sha = make_case(root)
            proc, artifact, receipt = run_role(
                root, "entity_attribution_skeptic",
                claim_artifact(registry_sha, [result("C1", evidence=[invisible]), result("C2")]),
                stem="invisible")
            check(f"{label} evidence 端到端拒绝且零残留",
                  proc.returncode == 2 and not artifact.exists() and not receipt.exists()
                  and residue(root) == [], (proc.returncode, proc.stderr[-180:], residue(root)))

    critic_variants = (("findings", {"findings": ["\u3164"], "non_covered": []}),
                       ("non_covered", {"findings": [], "non_covered": ["\u2800"]}))
    for label, fields in critic_variants:
        with tempfile.TemporaryDirectory(prefix="f02-critic-text-") as td:
            root = Path(td)
            registry_sha = make_case(root)
            payload = critic_artifact(registry_sha)
            payload.update(fields)
            proc, artifact, receipt = run_role(
                root, "completeness_critic", payload, stem="critic_bad")
            check(f"critic {label} 元素须含实义字符",
                  proc.returncode == 2 and not artifact.exists() and not receipt.exists(),
                  (proc.returncode, proc.stderr[-180:]))

    for label, invisible in (("U+2060", "\u2060"), ("U+3164", "\u3164")):
        with tempfile.TemporaryDirectory(prefix="f02-resolution-") as td:
            root = Path(td)
            p1, p2, _, r1, r2 = build_valid(root)
            (root / "adversarial_review.json").unlink(missing_ok=True)
            write_json(root / "bad_blockers.json", [
                {"id": "B1", "resolved": True, "resolution": invisible},
            ])
            proc = finalize(root, [r1, r2], blockers="bad_blockers.json") \
                if p1.returncode == p2.returncode == 0 else p1
            check(f"resolved blocker 的 {label} 空壳 resolution 端到端拒绝",
                  proc.returncode == 2 and not (root / "adversarial_review.json").exists(),
                  (proc.returncode, proc.stderr[-180:]))

    id_variants = (("U+200B", "C1\u200b"), ("U+3164", "C1\u3164"),
                   ("U+0591", "C1\u0591"))
    for label, invalid_id in id_variants:
        registry_message = rejection_message(lambda invalid_id=invalid_id:
            runner.validate_claim_registry_data({
                "schema": "a4-claims/v2", "claims": [{"id": invalid_id}],
            }))
        artifact_message = rejection_message(lambda invalid_id=invalid_id:
            runner.validate_review_artifact(
                claim_artifact("registry", [result(invalid_id)]),
                "entity_attribution_skeptic", "registry"))
        blocker_message = rejection_message(lambda invalid_id=invalid_id:
            runner.validate_blocking_findings([
                {"id": invalid_id, "resolved": False},
            ]))
        check(f"runner {label} claim/blocker id 按 all 语义判非法",
              all("id is invalid" in message for message in
                  (registry_message, artifact_message, blocker_message)),
              (registry_message, artifact_message, blocker_message))

        with tempfile.TemporaryDirectory(prefix="f02-consumer-id-") as td:
            root = Path(td)
            p1, p2, proc, _, _ = build_valid(root)
            if p1.returncode == p2.returncode == 0 and proc is not None \
                    and proc.returncode == 0:
                rewrite_aggregate_claim_id(root, "C1", invalid_id)
                shared_message = rejection_message(lambda:
                    shared.validate_adversarial_review(
                        root, {"chain": "bsc", "token": "0xtoken", "as_of_block": 123}))
            else:
                shared_message = "fixture build failed"
            check(f"shared {label} claim_id 按消费侧 all 语义判非法",
                  "id is invalid" in shared_message, shared_message)

        with tempfile.TemporaryDirectory(prefix="f02-consumer-blocker-id-") as td:
            root = Path(td)
            p1, p2, proc, _, _ = build_valid(root)
            if p1.returncode == p2.returncode == 0 and proc is not None \
                    and proc.returncode == 0:
                aggregate_path = root / "adversarial_review.json"
                aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
                aggregate["blocking_findings"] = [{
                    "id": invalid_id, "resolved": True, "resolution": "closed",
                }]
                write_json(aggregate_path, aggregate)
                shared_blocker_message = rejection_message(lambda:
                    shared.validate_adversarial_review(
                        root, {"chain": "bsc", "token": "0xtoken", "as_of_block": 123}))
            else:
                shared_blocker_message = "fixture build failed"
            check(f"shared {label} blocker id 按消费侧 all 语义判非法",
                  "id is invalid" in shared_blocker_message, shared_blocker_message)

    duplicate_registry = {
        "schema": "a4-claims/v2",
        "claims": [{"id": "C1"}, {"id": "C1\u0591"}],
    }
    duplicate_message = rejection_message(
        lambda: runner.validate_claim_registry_data(duplicate_registry))
    check("registry 的 C1 与 C1+U+0591 因后者 id 非法拒绝而非判重复",
          "id is invalid" in duplicate_message and "duplicate" not in duplicate_message,
          duplicate_message)

    stripped_duplicate_message = rejection_message(
        lambda: runner.validate_claim_registry_data({
            "schema": "a4-claims/v2",
            "claims": [{"id": "C1"}, {"id": " C1 "}],
        }))
    check("registry 重复检测仅按 strip 后精确相等",
          "duplicate claim id" in stripped_duplicate_message,
          stripped_duplicate_message)

    normal_ids = tuple(f"C{index}" for index in range(1, 100)) + ("C-1", "C_1")
    check("正常 C1-C99 及含连字符/下划线 id 照常通过",
          runner.validate_claim_registry_data({
              "schema": "a4-claims/v2",
              "claims": [{"id": claim_id} for claim_id in normal_ids],
          }) == set(normal_ids))

    import a4_gate
    semantic_pairs = (
        ("数学关系符", "净流入 ≥ 10%", "净流入 ≤ 10%"),
        ("方向箭头", "持仓 ↑", "持仓 ↓"),
        ("近似/不等", "误差 ≈ 0", "误差 ≠ 0"),
        ("俄文实义", "Статус подтверждён", "Статус опровергнут"),
    )
    for label, left, right in semantic_pairs:
        check(f"a4_gate 对账键保留{label}差异", a4_gate._norm_text(left) != a4_gate._norm_text(right),
              (a4_gate._norm_text(left), a4_gate._norm_text(right)))
    for label, left, right in (
            ("显式零渲染点名集", "claim\u3164\u115f\u1160\uffa0\u2800 text", "claim text"),
            ("Cf", "claim\u200b text", "claim text"),
            ("NFC 后残留 Mn", "claim\u0591 text", "claim text"),
            ("NFC/NFD", "á", "a\u0301"),
            ("Zs 折叠", "claim\u00a0\u3000text", "claim text")):
        check(f"a4_gate 对账键归一：{label}", a4_gate._norm_text(left) == a4_gate._norm_text(right),
              (a4_gate._norm_text(left), a4_gate._norm_text(right)))

    with tempfile.TemporaryDirectory(prefix="f02-a4-symbol-e2e-") as td:
        root = Path(td)
        write_json(root / "claim_registry.json", {"claims": [{
            "claim_id": "C1", "statement": "净流入 ≤ 10%",
            "evidence_files": [], "report_locations": [], "verdict": "confirmed",
        }]})
        fails = []
        a4_gate.check_audit_registry_alignment(
            root, {"claims": [{"id": "C1", "text": "净流入 ≥ 10%", "files": [],
                               "report_locations": []}]},
            [{"id": "C1", "verdict": "CONFIRMED"}], fails)
        check("check_audit_registry_alignment 端到端拒绝 ≥/≤ 命题反转",
              any("命题文本不一致" in failure for failure in fails), fails)

    with tempfile.TemporaryDirectory(prefix="f02-a4-normalize-") as td:
        root = Path(td)
        write_json(root / "claim_registry.json", {"claims": [{
            "claim_id": "C1", "statement": "claim\u0591 text",
            "evidence_files": [], "report_locations": [], "verdict": "confirmed",
        }]})
        fails = []
        a4_gate.check_audit_registry_alignment(
            root, {"claims": [{"id": "C1", "text": "claim text", "files": [],
                               "report_locations": []}]},
            [{"id": "C1", "verdict": "CONFIRMED"}], fails)
        check("a4_gate 自由文本比较键逐字符过滤 U+0591",
              fails == [], fails)

    for label, invalid_id in id_variants:
        with tempfile.TemporaryDirectory(prefix="f02-a4-invalid-id-") as td:
            root = Path(td)
            write_json(root / "claim_registry.json", {"claims": [{
                "claim_id": invalid_id, "statement": "claim text",
                "evidence_files": [], "report_locations": [], "verdict": "confirmed",
            }]})
            fails = []
            a4_gate.check_audit_registry_alignment(
                root, {"claims": [{"id": "C1", "text": "claim text", "files": [],
                                   "report_locations": []}]},
                [{"id": "C1", "verdict": "CONFIRMED"}], fails)
            check(f"a4_gate {label} claim_id 按 all 语义拒绝",
                  any("claim id 非法" in failure for failure in fails), fails)


def t_directory_cleanup_and_output_guards():
    with tempfile.TemporaryDirectory(prefix="f02-fifo-residue-") as td:
        root = Path(td)
        make_case(root)
        script = root / "fifo_output.py"
        script.write_text(
            "import os\nfrom pathlib import Path\n"
            "out = Path(os.environ['CHIP_REVIEW_OUTPUT'])\n"
            "os.mkfifo(out)\n"
            "os.mkfifo(out.parent / f'.fifo_execution.json.tmp.{os.getppid()}')\n",
            encoding="utf-8")
        proc = subprocess.run([
            sys.executable, str(RUNNER), str(root), "--role", "completeness_critic",
            "--entrypoint", script.name, "--artifact", "fifo.json",
            "--receipt", "fifo_execution.json",
        ], capture_output=True, text=True)
        check("entrypoint 建 staging/receipt tmp FIFO 后 rc=2 且零残留",
              proc.returncode == 2 and residue(root) == []
              and not (root / "fifo.json").exists()
              and not (root / "fifo_execution.json").exists(),
              (proc.returncode, proc.stderr[-180:], residue(root)))

    with tempfile.TemporaryDirectory(prefix="f02-dir-residue-") as td:
        root = Path(td)
        make_case(root)
        script = root / "mkdir_output.py"
        script.write_text(
            "import os\nfrom pathlib import Path\n"
            "out = Path(os.environ['CHIP_REVIEW_OUTPUT'])\n"
            "out.mkdir()\n"
            "(out.parent / f'.dir_execution.json.tmp.{os.getppid()}').mkdir()\n",
            encoding="utf-8")
        proc = subprocess.run([
            sys.executable, str(RUNNER), str(root), "--role", "completeness_critic",
            "--entrypoint", script.name, "--artifact", "dir.json",
            "--receipt", "dir_execution.json",
        ], capture_output=True, text=True)
        check("entrypoint 建 staging 目录＋receipt tmp 目录后 rc=2 且目录零残留",
              proc.returncode == 2 and residue(root) == []
              and not (root / "dir.json").exists() and not (root / "dir_execution.json").exists(),
              (proc.returncode, proc.stderr[-180:], residue(root)))

    with tempfile.TemporaryDirectory(prefix="f02-readonly-residue-") as td:
        root = Path(td)
        make_case(root)
        script = root / "readonly_output.py"
        script.write_text(
            "import os, sys\nfrom pathlib import Path\n"
            "out = Path(os.environ['CHIP_REVIEW_OUTPUT'])\n"
            "out.mkdir()\n"
            "(out / 'locked.txt').write_text('locked', encoding='utf-8')\n"
            "out.chmod(0o500)\n"
            "print('ORIGINAL_REVIEW_REJECTION', file=sys.stderr)\n"
            "raise SystemExit(7)\n",
            encoding="utf-8")
        proc = subprocess.run([
            sys.executable, str(RUNNER), str(root), "--role", "completeness_critic",
            "--entrypoint", script.name, "--artifact", "readonly.json",
            "--receipt", "readonly_execution.json",
        ], capture_output=True, text=True)
        staging = root / ".readonly.json.staging"
        clean = residue(root) == [] and not staging.exists()
        original_reason = ("review entrypoint failed rc=7" in proc.stderr
                           and "ORIGINAL_REVIEW_REJECTION" in proc.stderr)
        check("只读 staging 清理后 rc=2＋零残留＋保留原始拒绝理由",
              proc.returncode == 2 and clean and original_reason,
              (proc.returncode, proc.stderr[-240:], residue(root)))
        if staging.exists():
            staging.chmod(0o700)
            shutil.rmtree(staging)

    for label, link_name, victim_name in (
            ("artifact", "linked.json", "artifact_victim.json"),
            ("receipt", "linked_execution.json", "receipt_victim.json")):
        with tempfile.TemporaryDirectory(prefix="f02-output-link-") as td:
            root = Path(td)
            registry_sha = make_case(root)
            entry = entrypoint(root, "valid.py", critic_artifact(registry_sha))
            artifact = root / "linked.json"
            receipt = root / "linked_execution.json"
            selected = artifact if label == "artifact" else receipt
            selected.symlink_to(victim_name)
            proc = subprocess.run([
                sys.executable, str(RUNNER), str(root), "--role", "completeness_critic",
                "--entrypoint", entry.name, "--artifact", artifact.name,
                "--receipt", receipt.name,
            ], capture_output=True, text=True)
            check(f"{label} 输出位 symlink 必须拒绝且不得写 victim",
                  proc.returncode == 2 and selected.is_symlink()
                  and not (root / victim_name).exists(),
                  (proc.returncode, proc.stderr[-180:], (root / victim_name).exists()))

    for label in ("artifact", "receipt"):
        with tempfile.TemporaryDirectory(prefix="f02-preexisting-role-") as td:
            root = Path(td)
            registry_sha = make_case(root)
            entry = entrypoint(root, "valid.py", critic_artifact(registry_sha))
            artifact = root / "formal.json"
            receipt = root / "formal_execution.json"
            protected = artifact if label == "artifact" else receipt
            protected.write_text("sentinel", encoding="utf-8")
            proc = subprocess.run([
                sys.executable, str(RUNNER), str(root), "--role", "completeness_critic",
                "--entrypoint", entry.name, "--artifact", artifact.name,
                "--receipt", receipt.name,
            ], capture_output=True, text=True)
            check(f"run_review {label} 正式位预存在须拒绝且原件不覆盖",
                  proc.returncode == 2 and protected.read_text(encoding="utf-8") == "sentinel",
                  (proc.returncode, proc.stderr[-180:], protected.read_text(encoding="utf-8")))

    with tempfile.TemporaryDirectory(prefix="f02-preexisting-final-") as td:
        root = Path(td)
        p1, p2, proc, r1, r2 = build_valid(root)
        aggregate = root / "adversarial_review.json"
        before = aggregate.read_bytes() if aggregate.is_file() else b""
        again = finalize(root, [r1, r2]) if p1.returncode == p2.returncode == 0 else p1
        check("finalize 输出预存在须拒绝且原件不覆盖",
              proc is not None and proc.returncode == 0 and again.returncode == 2
              and aggregate.read_bytes() == before,
              (again.returncode, again.stderr[-180:]))


def t_content_identity_and_consumer_bindings():
    from shared_release_receipt import validate_adversarial_review
    target = {"chain": "bsc", "token": "0xtoken", "as_of_block": 123}

    with tempfile.TemporaryDirectory(prefix="f02-entrypoint-repeat-") as td:
        root = Path(td)
        registry_sha = make_case(root)
        repeated_payload = claim_artifact(
            registry_sha, [result("C1"), result("C2", "WEAKENED")])
        payloads = {
            "review_a.json": repeated_payload,
            "review_b.json": repeated_payload,
        }
        entry = root / "same_reviewer.py"
        entry.write_text(
            "import json, os\nfrom pathlib import Path\n"
            f"payloads = {payloads!r}\n"
            "out = Path(os.environ['CHIP_REVIEW_OUTPUT'])\n"
            "marker = out.parent / '.same-reviewer-second'\n"
            "key = 'review_b.json' if marker.exists() else 'review_a.json'\n"
            "out.write_text(json.dumps(payloads[key], ensure_ascii=False, "
            "indent=2 if marker.exists() else None), encoding='utf-8')\n"
            "marker.touch(exist_ok=True)\n",
            encoding="utf-8")
        p1, _, r1 = run_existing_role(root, "entity_attribution_skeptic", entry, "review_a")
        p2, _, r2 = run_existing_role(root, "entity_attribution_skeptic", entry, "review_b")
        p3, _, r3 = run_role(root, "completeness_critic", critic_artifact(registry_sha),
                             stem="critic")
        proc = finalize(root, [r1, r2, r3]) if not any(
            p.returncode for p in (p1, p2, p3)) else p1
        (root / ".same-reviewer-second").unlink(missing_ok=True)
        check("finalize 拒绝同 role+同 entrypoint sha 的重排版语义副本",
              proc.returncode == 2 and not (root / "adversarial_review.json").exists(),
              (proc.returncode, proc.stderr[-180:]))

    with tempfile.TemporaryDirectory(prefix="f02-entrypoint-distinct-") as td:
        root = Path(td)
        registry_sha = make_case(root)
        p1, _, r1 = run_role(root, "entity_attribution_skeptic",
                             claim_artifact(registry_sha, [result("C1")]), stem="review_a")
        p2, _, r2 = run_role(root, "entity_attribution_skeptic",
                             claim_artifact(registry_sha, [result("C2")]),
                             raw=json.dumps(claim_artifact(registry_sha, [result("C2")]),
                                            ensure_ascii=False, indent=2), stem="review_b")
        p3, _, r3 = run_role(root, "completeness_critic", critic_artifact(registry_sha),
                             stem="critic")
        proc = finalize(root, [r1, r2, r3]) if not any(
            p.returncode for p in (p1, p2, p3)) else p1
        check("绿例：同 role 的两个不同 entrypoint 真两路照常通过",
              proc.returncode == 0 and (root / "adversarial_review.json").is_file(),
              (proc.returncode, proc.stderr[-180:]))

    with tempfile.TemporaryDirectory(prefix="f02-critic-entrypoint-repeat-") as td:
        root = Path(td)
        registry_sha = make_case(root)
        p1, _, r1 = run_role(
            root, "entity_attribution_skeptic",
            claim_artifact(registry_sha, [result("C1"), result("C2")]),
            stem="skeptic")
        critic_payloads = [
            {**critic_artifact(registry_sha), "findings": ["finding a"]},
            {**critic_artifact(registry_sha), "findings": ["finding b"]},
            {**critic_artifact(registry_sha), "findings": ["finding c"]},
        ]
        critic_entry = root / "same_critic.py"
        critic_entry.write_text(
            "import json, os\nfrom pathlib import Path\n"
            f"payloads = {critic_payloads!r}\n"
            "out = Path(os.environ['CHIP_REVIEW_OUTPUT'])\n"
            "counter = out.parent / '.critic-entrypoint-count'\n"
            "index = int(counter.read_text()) if counter.exists() else 0\n"
            "out.write_text(json.dumps(payloads[index], ensure_ascii=False), encoding='utf-8')\n"
            "counter.write_text(str(index + 1))\n",
            encoding="utf-8")
        critic_runs = [run_existing_role(
            root, "completeness_critic", critic_entry, f"critic_{suffix}")
                       for suffix in ("a", "b", "c")]
        receipts = [item[2] for item in critic_runs]
        runs_ok = p1.returncode == 0 and all(
            item[0].returncode == 0 for item in critic_runs)
        proc = finalize(root, [r1, *receipts]) if runs_ok else next(
            (item[0] for item in critic_runs if item[0].returncode), p1)
        check("finalize 拒绝同一 completeness_critic entrypoint 三次注水",
              proc.returncode == 2 and not (root / "adversarial_review.json").exists(),
              (proc.returncode, proc.stderr[-220:]))

        # 绕过 producer 手抄聚合，消费侧仍须独立拒绝同一 critic entrypoint 注水。
        if runs_ok and proc.returncode == 0:
            aggregate = json.loads((root / "adversarial_review.json").read_text())
        elif runs_ok:
            aggregate = {
                "schema": "adversarial-review/v3",
                "target": target,
                "producer": {"path": "scripts/report/adversarial_review_runner.py",
                             "sha256": sha(RUNNER)},
                "claim_registry": {"path": "a4_claims.json",
                                   "size": (root / "a4_claims.json").stat().st_size,
                                   "sha256": registry_sha, "schema": "a4-claims/v2"},
                "reviews": [], "blocking_findings": [], "release_decision": "PASS",
            }
            for receipt_path in [r1, *receipts]:
                execution = json.loads(receipt_path.read_text())
                aggregate["reviews"].append({
                    "role": execution["role"], "exit_code": 0,
                    "artifact": execution["artifact"], "runner": execution["producer"],
                    "execution_receipt": {"path": receipt_path.name,
                                          "size": receipt_path.stat().st_size,
                                          "sha256": sha(receipt_path)},
                })
            write_json(root / "adversarial_review.json", aggregate)
        else:
            aggregate = None
        shared_rejected = aggregate is not None and rejected(
            lambda: validate_adversarial_review(root, target))
        audit_errors = []
        if aggregate is not None:
            from audit_release_gate import check_adversarial
            check_adversarial(root, aggregate, audit_errors, target)
        check("消费侧独立拒绝同一 completeness_critic entrypoint 三次注水",
              shared_rejected and bool(audit_errors),
              (shared_rejected, audit_errors))

    with tempfile.TemporaryDirectory(prefix="f02-consumer-entrypoint-repeat-") as td:
        root = Path(td)
        registry_sha = make_case(root)
        p1, _, r1 = run_role(root, "entity_attribution_skeptic",
                             claim_artifact(registry_sha, [result("C1")]), stem="review_a")
        p2, _, r2 = run_role(root, "entity_attribution_skeptic",
                             claim_artifact(registry_sha, [result("C2")]),
                             raw=json.dumps(claim_artifact(registry_sha, [result("C2")]),
                                            ensure_ascii=False, indent=2), stem="review_b")
        p3, _, r3 = run_role(root, "completeness_critic", critic_artifact(registry_sha),
                             stem="critic")
        proc = finalize(root, [r1, r2, r3]) if not any(
            p.returncode for p in (p1, p2, p3)) else p1
        if proc.returncode == 0:
            aggregate_path = root / "adversarial_review.json"
            aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
            first, second = aggregate["reviews"][:2]
            second_receipt_path = root / second["execution_receipt"]["path"]
            second_receipt = json.loads(second_receipt_path.read_text(encoding="utf-8"))
            first_receipt = json.loads(
                (root / first["execution_receipt"]["path"]).read_text(encoding="utf-8"))
            second_receipt["entrypoint"] = first_receipt["entrypoint"]
            write_json(second_receipt_path, second_receipt)
            second["execution_receipt"] = {
                "path": second_receipt_path.name,
                "size": second_receipt_path.stat().st_size,
                "sha256": sha(second_receipt_path),
            }
            write_json(aggregate_path, aggregate)
        check("消费侧拒绝手抄同 role+同 entrypoint sha 的重复路数",
              proc.returncode == 0 and rejected(
                  lambda: validate_adversarial_review(root, target)),
              (proc.returncode, proc.stderr[-180:]))

    with tempfile.TemporaryDirectory(prefix="f02-receipt-copy-") as td:
        root = Path(td)
        p1, p2, proc, r1, r2 = build_valid(root)
        (root / "adversarial_review.json").unlink(missing_ok=True)
        copied = root / "skeptic_execution_copy.json"
        shutil.copyfile(r1, copied)
        injected = finalize(root, [r1, r2, copied]) if p1.returncode == p2.returncode == 0 else p1
        check("finalize 按 execution receipt 内容 sha 去重复本注水",
              proc is not None and proc.returncode == 0 and injected.returncode == 2
              and not (root / "adversarial_review.json").exists(),
              (injected.returncode, injected.stderr[-180:]))

    with tempfile.TemporaryDirectory(prefix="f02-artifact-copy-") as td:
        root = Path(td)
        registry_sha = make_case(root)
        payload = claim_artifact(registry_sha, [result("C1"), result("C2")])
        p1, _, r1 = run_role(root, "entity_attribution_skeptic", payload, stem="skeptic_a")
        p2, _, r2 = run_role(root, "entity_attribution_skeptic", payload, stem="skeptic_b")
        p3, _, r3 = run_role(root, "completeness_critic", critic_artifact(registry_sha),
                             stem="critic")
        proc = finalize(root, [r1, r2, r3]) if not any(
            p.returncode for p in (p1, p2, p3)) else p1
        check("finalize 按 artifact 内容 sha 去重复读注水",
              proc.returncode == 2 and not (root / "adversarial_review.json").exists(),
              (proc.returncode, proc.stderr[-180:]))

    with tempfile.TemporaryDirectory(prefix="f02-consumer-injection-") as td:
        root = Path(td)
        p1, p2, proc, _, _ = build_valid(root)
        aggregate = json.loads((root / "adversarial_review.json").read_text())
        aggregate["reviews"] = aggregate["reviews"] * 3
        write_json(root / "adversarial_review.json", aggregate)
        check("消费侧拒绝手抄六路同内容 reviews 注水",
              p1.returncode == p2.returncode == 0 and proc is not None
              and proc.returncode == 0
              and rejected(lambda: validate_adversarial_review(root, target)))

    with tempfile.TemporaryDirectory(prefix="f02-consumer-ref-") as td:
        root = Path(td)
        p1, p2, proc, _, _ = build_valid(root)
        aggregate = json.loads((root / "adversarial_review.json").read_text())
        aggregate["claim_registry"].update(sha256="0" * 64, size=1)
        write_json(root / "adversarial_review.json", aggregate)
        check("消费侧聚合 claim_registry 自报假 ref 必须拒绝",
              p1.returncode == p2.returncode == 0 and proc is not None
              and proc.returncode == 0
              and rejected(lambda: validate_adversarial_review(root, target)))

    with tempfile.TemporaryDirectory(prefix="f02-consumer-size-") as td:
        root = Path(td)
        p1, p2, proc, _, _ = build_valid(root)
        aggregate = json.loads((root / "adversarial_review.json").read_text())
        aggregate["reviews"][0]["execution_receipt"]["size"] = 999999
        write_json(root / "adversarial_review.json", aggregate)
        check("消费侧 execution receipt ref 的 size=999999 必须拒绝",
              p1.returncode == p2.returncode == 0 and proc is not None
              and proc.returncode == 0
              and rejected(lambda: validate_adversarial_review(root, target)))


def _poison_object(path: Path):
    text = path.read_text(encoding="utf-8").rstrip()
    if not text.endswith("}"):
        raise AssertionError(path)
    path.write_text(text[:-1] + ', "poison": NaN}\n', encoding="utf-8")


def t_nonfinite_json_mounts_and_constant_sources():
    import adversarial_review_runner as runner
    import audit_release_gate as audit
    import shared_release_receipt as shared

    check("shared/audit 的 v3 schema 与迁移提示均从 runner 单源导入",
          shared.AGGREGATE_SCHEMA == runner.AGGREGATE_SCHEMA
          and shared.V3_RERUN_HINT == runner.V3_RERUN_HINT
          and getattr(audit, "AGGREGATE_SCHEMA", None) == runner.AGGREGATE_SCHEMA
          and getattr(audit, "V3_RERUN_HINT", None) == runner.V3_RERUN_HINT)

    with tempfile.TemporaryDirectory(prefix="f02-nan-registry-") as td:
        root = Path(td)
        make_case(root)
        _poison_object(root / "a4_claims.json")
        proc, artifact, receipt = run_role(
            root, "completeness_critic", critic_artifact(sha(root / "a4_claims.json")),
            stem="nan_registry")
        check("NaN claim registry 解析点拒绝", proc.returncode == 2
              and not artifact.exists() and not receipt.exists(), proc.stderr[-180:])

        registry = root / "a4_claims.json"
        write_json(root / "adversarial_review.json", {
            "schema": runner.AGGREGATE_SCHEMA,
            "target": {"chain": "bsc", "token": "0xtoken", "as_of_block": 123},
            "producer": runner.repo_producer(),
            "claim_registry": {"path": registry.name, "size": registry.stat().st_size,
                               "sha256": sha(registry), "schema": runner.REGISTRY_SCHEMA},
            "reviews": [], "blocking_findings": [], "release_decision": "PASS",
        })
        original_reject = shared._reject_constant

        def consumer_marker(value):
            raise ValueError(f"consumer-side reject marker: {value}")

        shared._reject_constant = consumer_marker
        try:
            try:
                shared.validate_adversarial_review(
                    root, {"chain": "bsc", "token": "0xtoken", "as_of_block": 123})
            except ValueError as exc:
                marker = str(exc)
            else:
                marker = ""
        finally:
            shared._reject_constant = original_reject
        check("shared 深层 registry 解析显式使用消费侧 reject_constant",
              "consumer-side reject marker" in marker, marker)

    with tempfile.TemporaryDirectory(prefix="f02-nan-staging-") as td:
        root = Path(td)
        registry_sha = make_case(root)
        raw = json.dumps(critic_artifact(registry_sha), ensure_ascii=False)[:-1] \
            + ', "poison": NaN}'
        proc, artifact, receipt = run_role(
            root, "completeness_critic", raw=raw, stem="nan_artifact")
        check("NaN controlled artifact 解析点拒绝", proc.returncode == 2
              and not artifact.exists() and not receipt.exists(), proc.stderr[-180:])

    with tempfile.TemporaryDirectory(prefix="f02-nan-finalize-") as td:
        root = Path(td)
        p1, p2, _, r1, r2 = build_valid(root)
        (root / "adversarial_review.json").unlink(missing_ok=True)
        _poison_object(root / "accounting_mode.json")
        proc = finalize(root, [r1, r2]) if p1.returncode == p2.returncode == 0 else p1
        check("NaN accounting target 解析点拒绝", proc.returncode == 2, proc.stderr[-180:])

    with tempfile.TemporaryDirectory(prefix="f02-nan-blockers-") as td:
        root = Path(td)
        p1, p2, _, r1, r2 = build_valid(root)
        (root / "adversarial_review.json").unlink(missing_ok=True)
        (root / "blockers.json").write_text('[{"id":"B1","resolved":false,"poison":NaN}]\n',
                                             encoding="utf-8")
        proc = finalize(root, [r1, r2]) if p1.returncode == p2.returncode == 0 else p1
        check("NaN blockers 解析点拒绝", proc.returncode == 2, proc.stderr[-180:])

    with tempfile.TemporaryDirectory(prefix="f02-nan-receipt-") as td:
        root = Path(td)
        registry_sha = make_case(root)
        p1, artifact, receipt = run_role(
            root, "entity_attribution_skeptic",
            claim_artifact(registry_sha, [result("C1"), result("C2")]), stem="skeptic")
        receipt_data = json.loads(receipt.read_text()) if p1.returncode == 0 else {}
        _poison_object(receipt) if p1.returncode == 0 else None
        artifact_ref = receipt_data.get("artifact")
        direct_rejected = rejected(lambda: runner.validate_review_receipt(
            root, receipt.name, "entity_attribution_skeptic", artifact_ref,
            registry_sha256=registry_sha, claim_ids={"C1", "C2"}))
        p2, _, r2 = run_role(root, "completeness_critic", critic_artifact(registry_sha),
                             stem="critic")
        proc = finalize(root, [receipt, r2]) if p1.returncode == p2.returncode == 0 else p1
        check("NaN execution receipt 的直接校验与 finalize 预解析点均拒绝",
              direct_rejected and proc.returncode == 2,
              (direct_rejected, proc.returncode, proc.stderr[-180:]))

    with tempfile.TemporaryDirectory(prefix="f02-nan-artifact-load-") as td:
        root = Path(td)
        registry_sha = make_case(root)
        artifact = write_json(root / "artifact.json", claim_artifact(
            registry_sha, [result("C1"), result("C2")]))
        _poison_object(artifact)
        artifact_ref = {"path": artifact.name, "size": artifact.stat().st_size,
                        "sha256": sha(artifact)}
        check("NaN bound artifact 重载解析点拒绝",
              rejected(lambda: runner._load_artifact(
                  root, artifact_ref, "entity_attribution_skeptic",
                  registry_sha, {"C1", "C2"})))

    with tempfile.TemporaryDirectory(prefix="f02-nan-consumers-") as td:
        root = Path(td)
        p1, p2, proc, _, _ = build_valid(root)
        _poison_object(root / "adversarial_review.json")
        target = {"chain": "bsc", "token": "0xtoken", "as_of_block": 123}
        shared_rejected = rejected(lambda: shared.validate_adversarial_review(root, target))
        errors = []
        audit.check_adversarial(
            root, json.loads((root / "adversarial_review.json").read_text()), errors, target)
        audit_load_errors = []
        audit_loaded = audit.load_adversarial_json(
            root / "adversarial_review.json", audit_load_errors)
        check("NaN aggregate 在 shared 与 audit 两消费解析点均拒绝",
              p1.returncode == p2.returncode == 0 and proc is not None
              and proc.returncode == 0 and shared_rejected and bool(errors)
              and audit_loaded == {} and bool(audit_load_errors),
              (shared_rejected, errors, audit_load_errors))


def t_documentation_contract():
    protocol = (REPO / "references/independent-audit-protocol.md").read_text(encoding="utf-8")
    workflow = (REPO / "references/analyze-workflow.md").read_text(encoding="utf-8")
    required = (
        "公开可算的完整性锚，不是签名",
        "finalize 不是唯一物理路径",
        "删除该角色 artifact",
        "execution receipt",
        "entrypoint 脚本必须随案保留",
        "review_completeness.py",
        '"resolved": bool',
    )
    check("独立复核协议补齐免责、TOCTOU、entrypoint、critic 命令与 blockers 结构",
          all(item in protocol for item in required),
          [item for item in required if item not in protocol])
    scope_terms = ("ASCII 可打印", "拉丁补充与扩展", "通用标点", "CJK", "假名",
                   "韩文音节", "全角", "俄文", "阿拉伯文", "纯 emoji", "claim_id 不得含空格")
    check("两份协议写清实义白名单覆盖、拒绝边界与 claim_id 空格禁令",
          all(term in workflow and term in protocol for term in scope_terms),
          [term for term in scope_terms if term not in workflow or term not in protocol])


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


def t_reproduce_output_strict_loader_mount():
    import audit_release_gate as gate

    with tempfile.TemporaryDirectory(prefix="f02-reproduce-nan-") as td:
        root = Path(td).resolve()
        entry = root / "reproduce_audit.py"
        entry.write_text("raise SystemExit(0)\n", encoding="utf-8")
        manifest = write_json(root / "audit_input_manifest.json", {"inputs": []})
        output = root / "reproduce_output.json"
        summary = {"claim": "C1", "value": 1}
        output.write_text(
            '{"summary":{"claim":"C1","value":1},"unused_probe":NaN}\n',
            encoding="utf-8")
        write_json(root / "reproduce_receipt.json", {
            "schema": "reproduce-receipt/v2", "status": "PASS", "exit_code": 0,
            "freshness": {"nonce": "n", "staging_created_by_controller": True,
                          "inode_preserved": True, "output_absent_before_run": True},
            "started_at_utc": "2026-08-14T00:00:00Z",
            "finished_at_utc": "2026-08-14T00:00:01Z",
            "entrypoint": {"path": "reproduce_audit.py", "sha256": sha(entry)},
            "input_manifest": {"path": "audit_input_manifest.json",
                               "sha256": sha(manifest)},
            "args": [],
            "output": {"path": "reproduce_output.json", "size": output.stat().st_size,
                       "sha256": sha(output)},
            "summary_sha256": gate.canonical_json_sha(summary),
        })
        errors = []
        gate.check_reproduce_receipt(root, "reproduce_receipt.json", "C1", errors)
        check("reproduce output 严格 loader 接线拒绝未消费字段 NaN",
              any("JSON无法读取 reproduce_output.json" in item
                  and ("non-finite" in item or "非有限" in item)
                  for item in errors), errors)


def main():
    t_original_two_byte_shell()
    t_runner_variants_and_cleanup()
    t_meaningful_text_and_claim_identity()
    t_directory_cleanup_and_output_guards()
    t_finalize_failures()
    t_finalize_variants()
    t_content_identity_and_consumer_bindings()
    t_nonfinite_json_mounts_and_constant_sources()
    t_consumer_and_green_chain()
    t_reproduce_output_strict_loader_mount()
    t_documentation_contract()
    if FAILS:
        print(f"FAIL workorder B F-02 regressions: {len(FAILS)}")
        return 1
    print("PASS workorder B F-02 regressions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
