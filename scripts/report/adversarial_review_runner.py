#!/usr/bin/env python3
"""Run, validate and aggregate fixed adversarial-review roles."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import subprocess
import sys
from pathlib import Path

ROLES = {"entity_attribution_skeptic", "completeness_critic"}
CLAIM_REVIEW_ROLES = ROLES - {"completeness_critic"}
VERDICTS = {"CONFIRMED", "WEAKENED", "REFUTED"}
ARTIFACT_SCHEMA = "adversarial-review-artifact/v1"
REGISTRY_SCHEMA = "a4-claims/v2"
AGGREGATE_SCHEMA = "adversarial-review/v3"
EXECUTION_SCHEMA = "adversarial-review-execution/v1"
V3_RERUN_HINT = "存量 adversarial-review/v2 须按 v3 重跑对抗复核"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def contained_regular(root, path, label):
    root = Path(root).resolve()
    item = Path(path)
    raw = (root / item) if not item.is_absolute() else item
    if raw.is_symlink():
        raise ValueError(f"{label} must be a regular file inside case root")
    item = raw.resolve()
    try:
        item.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} must be a regular file inside case root") from exc
    if not item.is_file():
        raise ValueError(f"{label} must be a regular file inside case root")
    return item


def contained_output(root, path, label):
    root = Path(root).resolve()
    item = Path(path)
    raw = (root / item) if not item.is_absolute() else item
    if raw.is_symlink():
        raise ValueError(f"{label} must be a non-symlink path inside case root")
    item = raw.resolve()
    try:
        item.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} must be a path inside case root") from exc
    if item.parent != root:
        raise ValueError(f"{label} must be in case root")
    return item


def repo_producer():
    return {"path": "scripts/report/adversarial_review_runner.py", "sha256": sha(__file__)}


def ref(root, path):
    path = contained_regular(root, path, "artifact")
    return {"path": str(path.relative_to(Path(root).resolve())),
            "size": path.stat().st_size, "sha256": sha(path)}


def _nonempty_string(value):
    return isinstance(value, str) and bool(value.strip())


def _string_array(value, label, *, nonempty=False):
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError(f"{label} must be {'a non-empty ' if nonempty else 'an '}array")
    if any(not _nonempty_string(item) for item in value):
        raise ValueError(f"{label} must contain only non-empty strings")


def validate_claim_registry_data(data):
    """Pure validation of the A4 execution-time authority table."""
    if not isinstance(data, dict) or data.get("schema") != REGISTRY_SCHEMA:
        raise ValueError(f"claim registry must use {REGISTRY_SCHEMA}")
    claims = data.get("claims")
    if not isinstance(claims, list) or not claims:
        raise ValueError("claim registry claims must be a non-empty array")
    ids = []
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict) or not _nonempty_string(claim.get("id")):
            raise ValueError(f"claim registry claims[{index}].id must be non-empty")
        ids.append(claim["id"].strip())
    if len(ids) != len(set(ids)):
        raise ValueError("claim registry contains duplicate claim id")
    return set(ids)


def load_claim_registry(case_dir, registry="a4_claims.json"):
    path = contained_regular(case_dir, registry, "claim registry")
    if path.relative_to(Path(case_dir).resolve()).as_posix() != "a4_claims.json":
        raise ValueError("claim registry authority must be case-root a4_claims.json")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"claim registry JSON invalid: {exc}") from exc
    claim_ids = validate_claim_registry_data(data)
    registry_ref = ref(case_dir, path)
    registry_ref["schema"] = REGISTRY_SCHEMA
    return path, data, claim_ids, registry_ref


def validate_review_artifact(data, role, registry_sha256, claim_ids=None):
    """Pure role-specific artifact validator shared by runner and both consumers."""
    if role not in ROLES:
        raise ValueError(f"unsupported adversarial role: {role}")
    if not isinstance(data, dict) or data.get("schema") != ARTIFACT_SCHEMA:
        raise ValueError(f"review artifact must use {ARTIFACT_SCHEMA}")
    if data.get("role") != role:
        raise ValueError("review artifact role differs from controlled execution role")
    if data.get("registry_sha256") != registry_sha256:
        raise ValueError("review artifact registry_sha256 differs from claim registry")
    if role == "completeness_critic":
        if not isinstance(data.get("findings"), list):
            raise ValueError("completeness_critic findings array must be present")
        if not isinstance(data.get("non_covered"), list):
            raise ValueError("completeness_critic non_covered array must be present")
        return set()

    results = data.get("results")
    if not isinstance(results, list):
        raise ValueError("claim-review results array must be present")
    reviewed = []
    for index, item in enumerate(results):
        if not isinstance(item, dict):
            raise ValueError(f"results[{index}] must be an object")
        claim_id = item.get("claim_id")
        if not _nonempty_string(claim_id):
            raise ValueError(f"results[{index}].claim_id must be non-empty")
        claim_id = claim_id.strip()
        if item.get("verdict") not in VERDICTS:
            raise ValueError(f"results[{index}].verdict is outside the three-value enum")
        _string_array(item.get("evidence"), f"results[{index}].evidence", nonempty=True)
        _string_array(item.get("alternative_explanations"),
                      f"results[{index}].alternative_explanations")
        reviewed.append(claim_id)
    if len(reviewed) != len(set(reviewed)):
        raise ValueError("review artifact contains duplicate claim_id")
    reviewed_set = set(reviewed)
    if claim_ids is not None and reviewed_set - set(claim_ids):
        raise ValueError(
            f"review artifact contains claim_id outside registry: "
            f"{sorted(reviewed_set - set(claim_ids))}")
    return reviewed_set


def validate_blocking_findings(blockers):
    """Pure blocker structure validator; unresolved blockers are valid but not releasable."""
    if not isinstance(blockers, list):
        raise ValueError("blocking_findings must be an array")
    ids = []
    for index, item in enumerate(blockers):
        if not isinstance(item, dict) or not _nonempty_string(item.get("id")):
            raise ValueError(f"blocking_findings[{index}].id must be non-empty")
        if not isinstance(item.get("resolved"), bool):
            raise ValueError(f"blocking_findings[{index}].resolved must be bool")
        if item["resolved"] and not _nonempty_string(item.get("resolution")):
            raise ValueError(
                f"blocking_findings[{index}] resolved=true requires non-empty resolution")
        ids.append(item["id"].strip())
    if len(ids) != len(set(ids)):
        raise ValueError("blocking_findings id must be unique within aggregate")
    return blockers


def validate_union_coverage(claim_ids, reviewed_sets):
    """Pure registry-exact union validation (outside ids are never accepted)."""
    authority = set(claim_ids)
    covered = set().union(*reviewed_sets) if reviewed_sets else set()
    outside = covered - authority
    if outside:
        raise ValueError(f"review union contains claim outside registry: {sorted(outside)}")
    missing = authority - covered
    if missing:
        raise ValueError(f"review union does not cover registry claims: {sorted(missing)}")
    return covered


def _load_artifact(case_dir, artifact_ref, role, registry_sha256, claim_ids):
    if not isinstance(artifact_ref, dict):
        raise ValueError("review artifact ref missing")
    path = contained_regular(case_dir, artifact_ref.get("path", ""), "review artifact")
    if (artifact_ref.get("size") != path.stat().st_size
            or artifact_ref.get("sha256") != sha(path)):
        raise ValueError("review artifact binding invalid")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"review artifact JSON invalid: {exc}") from exc
    reviewed = validate_review_artifact(data, role, registry_sha256, claim_ids)
    return data, reviewed


def run_review(case_dir, role, entrypoint, artifact, receipt,
               claim_registry="a4_claims.json"):
    root = Path(case_dir).resolve()
    if role not in ROLES:
        raise ValueError(f"unsupported adversarial role: {role}")
    _, _, claim_ids, registry_ref = load_claim_registry(root, claim_registry)
    registry_sha256 = registry_ref["sha256"]
    entry = contained_regular(root, entrypoint, "review entrypoint")
    final = contained_output(root, artifact, "review artifact path")
    if final.exists():
        raise ValueError("review artifact must be absent before controlled execution")
    receipt_path = contained_output(root, receipt, "review execution receipt path")
    if receipt_path.exists():
        raise ValueError("review execution receipt must be absent before controlled execution")
    staging = root / f".review-{role}-{secrets.token_hex(12)}.staging"
    tmp = receipt_path.with_name(f".{receipt_path.name}.tmp.{os.getpid()}")
    artifact_published = False
    receipt_published = False
    try:
        env = os.environ.copy()
        env["CHIP_REVIEW_OUTPUT"] = str(staging)
        env["CHIP_REVIEW_ROLE"] = role
        env["CHIP_REVIEW_REGISTRY_SHA256"] = registry_sha256
        proc = subprocess.run([sys.executable, str(entry)], cwd=root, env=env,
                              capture_output=True, text=True)
        if proc.returncode != 0:
            raise ValueError(
                f"review entrypoint failed rc={proc.returncode}: "
                f"{(proc.stderr or proc.stdout)[-300:]}")
        if staging.is_symlink() or not staging.is_file() or staging.stat().st_size == 0:
            raise ValueError("review entrypoint did not create a non-empty controlled artifact")
        try:
            artifact_data = json.loads(staging.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"review artifact JSON invalid: {exc}") from exc
        validate_review_artifact(
            artifact_data, role, registry_sha256, claim_ids=claim_ids)
        os.replace(staging, final)
        artifact_published = True
        payload = {
            "schema": EXECUTION_SCHEMA, "status": "PASS", "exit_code": 0,
            "role": role, "registry_sha256": registry_sha256,
            "producer": repo_producer(),
            "entrypoint": {"path": str(entry.relative_to(root)), "sha256": sha(entry)},
            "artifact": ref(root, final),
        }
        with tmp.open("x", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, receipt_path)
        receipt_published = True
        return payload
    except Exception:
        if staging.is_file() or staging.is_symlink():
            staging.unlink()
        if tmp.is_file() or tmp.is_symlink():
            tmp.unlink()
        if artifact_published and not receipt_published and final.is_file():
            final.unlink()
        raise


def validate_review_receipt(case_dir, receipt, role, artifact_ref,
                            registry_sha256=None, claim_ids=None):
    root = Path(case_dir).resolve()
    receipt_path = contained_regular(root, receipt, "review execution receipt")
    try:
        data = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"review execution receipt JSON invalid: {exc}") from exc
    if (data.get("schema") != EXECUTION_SCHEMA
            or data.get("status") != "PASS" or data.get("exit_code") != 0
            or data.get("role") != role):
        raise ValueError("review execution receipt schema/status/role invalid")
    if data.get("producer") != repo_producer():
        raise ValueError("review execution receipt producer is not current runner")
    entry = data.get("entrypoint") or {}
    entry_path = contained_regular(root, entry.get("path", ""), "review entrypoint")
    if entry.get("sha256") != sha(entry_path):
        raise ValueError("review entrypoint hash changed")
    expected_artifact = data.get("artifact")
    if expected_artifact != artifact_ref:
        raise ValueError("review artifact differs from execution receipt")
    if registry_sha256 is None:
        registry_sha256 = data.get("registry_sha256")
    if data.get("registry_sha256") != registry_sha256:
        raise ValueError("review execution receipt registry_sha256 is torn")
    artifact_data, reviewed = _load_artifact(
        root, artifact_ref, role, registry_sha256, claim_ids)
    return data, artifact_data, reviewed


def _target_from_accounting(case_dir):
    path = contained_regular(case_dir, "accounting_mode.json", "accounting target")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"accounting target JSON invalid: {exc}") from exc
    chain = data.get("chain")
    token = data.get("token") or data.get("mint")
    block = data.get("as_of_block")
    if not _nonempty_string(chain) or not _nonempty_string(token) \
            or isinstance(block, bool) or not isinstance(block, int):
        raise ValueError("accounting target lacks chain/token/as_of_block")
    if str(chain).strip().lower() != "solana":
        token = str(token).lower()
    return {"chain": str(chain).strip(), "token": str(token), "as_of_block": block}


def finalize_review(case_dir, receipts, blockers="blockers.json",
                    out="adversarial_review.json", claim_registry="a4_claims.json"):
    root = Path(case_dir).resolve()
    final = contained_output(root, out, "adversarial aggregate output")
    if final.exists():
        raise ValueError("adversarial aggregate output must be absent before finalize")
    tmp = final.with_name(f".{final.name}.tmp.{os.getpid()}.{secrets.token_hex(6)}")
    try:
        _, _, claim_ids, registry_ref = load_claim_registry(root, claim_registry)
        blockers_path = contained_regular(root, blockers, "blocking findings input")
        try:
            blocking_findings = json.loads(blockers_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"blocking findings JSON invalid: {exc}") from exc
        validate_blocking_findings(blocking_findings)
        if not isinstance(receipts, list) or not receipts:
            raise ValueError("finalize requires at least one execution receipt")
        receipt_paths = [contained_regular(root, item, "review execution receipt")
                         for item in receipts]
        if len(receipt_paths) != len(set(receipt_paths)):
            raise ValueError("duplicate review execution receipt")
        reviews = []
        reviewed_sets = []
        roles = set()
        for receipt_path in receipt_paths:
            try:
                execution = json.loads(receipt_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"review execution receipt JSON invalid: {exc}") from exc
            role = execution.get("role")
            artifact_ref = execution.get("artifact")
            execution, _, reviewed = validate_review_receipt(
                root, receipt_path, role, artifact_ref,
                registry_sha256=registry_ref["sha256"], claim_ids=claim_ids)
            roles.add(role)
            if role in CLAIM_REVIEW_ROLES:
                reviewed_sets.append(reviewed)
            reviews.append({
                "role": role,
                "exit_code": execution["exit_code"],
                "artifact": artifact_ref,
                "runner": execution["producer"],
                "execution_receipt": ref(root, receipt_path),
            })
        if not ROLES.issubset(roles):
            raise ValueError(f"required adversarial roles missing: {sorted(ROLES - roles)}")
        validate_union_coverage(claim_ids, reviewed_sets)
        unresolved = [item for item in blocking_findings if not item["resolved"]]
        payload = {
            "schema": AGGREGATE_SCHEMA,
            "target": _target_from_accounting(root),
            "producer": repo_producer(),
            "claim_registry": registry_ref,
            "reviews": reviews,
            "blocking_findings": blocking_findings,
            "release_decision": "PASS" if not unresolved else "BLOCKED",
        }
        with tmp.open("x", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, final)
        return payload
    except Exception:
        if tmp.is_file() or tmp.is_symlink():
            tmp.unlink()
        raise


def _run_cli(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("case_dir")
    ap.add_argument("--role", required=True, choices=sorted(ROLES))
    ap.add_argument("--entrypoint", required=True)
    ap.add_argument("--artifact", required=True)
    ap.add_argument("--receipt", required=True)
    ap.add_argument("--claim-registry", default="a4_claims.json")
    args = ap.parse_args(argv)
    run_review(args.case_dir, args.role, args.entrypoint, args.artifact, args.receipt,
               claim_registry=args.claim_registry)


def _finalize_cli(argv):
    ap = argparse.ArgumentParser(prog="adversarial_review_runner.py finalize")
    ap.add_argument("case_dir")
    ap.add_argument("--claim-registry", default="a4_claims.json")
    ap.add_argument("--receipt", action="append", required=True)
    ap.add_argument("--blockers", required=True)
    ap.add_argument("--out", default="adversarial_review.json")
    args = ap.parse_args(argv)
    finalize_review(args.case_dir, args.receipt, blockers=args.blockers, out=args.out,
                    claim_registry=args.claim_registry)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        if argv and argv[0] == "finalize":
            _finalize_cli(argv[1:])
        else:
            _run_cli(argv)
    except Exception as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
