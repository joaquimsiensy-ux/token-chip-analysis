#!/usr/bin/env python3
"""Run, validate and aggregate fixed adversarial-review roles."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
from supply_truth_gate import _meaningful_text, _reject_constant

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


def remove_any(path):
    """Remove any existing path shape, including broken symlinks and special files."""
    path = Path(path)
    if os.path.lexists(path):
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()


def _valid_identifier(value, meaningful_text=_meaningful_text):
    if not isinstance(value, str):
        return False
    stripped = value.strip()
    return bool(stripped) and all(meaningful_text(char) for char in stripped)


def _loads_json(text, reject_constant=_reject_constant):
    return json.loads(text, parse_constant=reject_constant)


def _string_array(value, label, *, nonempty=False, meaningful_text=_meaningful_text):
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError(f"{label} must be {'a non-empty ' if nonempty else 'an '}array")
    if any(not meaningful_text(item) for item in value):
        raise ValueError(f"{label} must contain only non-empty strings")


def validate_claim_registry_data(data, *, meaningful_text=_meaningful_text):
    """Pure validation of the A4 execution-time authority table."""
    if not isinstance(data, dict) or data.get("schema") != REGISTRY_SCHEMA:
        raise ValueError(f"claim registry must use {REGISTRY_SCHEMA}")
    claims = data.get("claims")
    if not isinstance(claims, list) or not claims:
        raise ValueError("claim registry claims must be a non-empty array")
    ids = []
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict) \
                or not _valid_identifier(claim.get("id"), meaningful_text):
            raise ValueError(f"claim registry claims[{index}].id is invalid")
        ids.append(claim["id"].strip())
    if len(ids) != len(set(ids)):
        raise ValueError("claim registry contains duplicate claim id")
    return set(ids)


def load_claim_registry(case_dir, registry="a4_claims.json", *,
                        meaningful_text=_meaningful_text,
                        reject_constant=_reject_constant):
    path = contained_regular(case_dir, registry, "claim registry")
    if path.relative_to(Path(case_dir).resolve()).as_posix() != "a4_claims.json":
        raise ValueError("claim registry authority must be case-root a4_claims.json")
    try:
        data = _loads_json(path.read_text(encoding="utf-8"), reject_constant)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"claim registry JSON invalid: {exc}") from exc
    claim_ids = validate_claim_registry_data(data, meaningful_text=meaningful_text)
    registry_ref = ref(case_dir, path)
    registry_ref["schema"] = REGISTRY_SCHEMA
    return path, data, claim_ids, registry_ref


def validate_review_artifact(data, role, registry_sha256, claim_ids=None, *,
                             meaningful_text=_meaningful_text):
    """Pure role-specific artifact validator shared by runner and both consumers."""
    if not meaningful_text(role) or role not in ROLES:
        raise ValueError(f"unsupported adversarial role: {role}")
    if not isinstance(data, dict) or data.get("schema") != ARTIFACT_SCHEMA:
        raise ValueError(f"review artifact must use {ARTIFACT_SCHEMA}")
    if data.get("role") != role:
        raise ValueError("review artifact role differs from controlled execution role")
    if data.get("registry_sha256") != registry_sha256:
        raise ValueError("review artifact registry_sha256 differs from claim registry")
    if role == "completeness_critic":
        _string_array(data.get("findings"), "completeness_critic findings",
                      meaningful_text=meaningful_text)
        _string_array(data.get("non_covered"), "completeness_critic non_covered",
                      meaningful_text=meaningful_text)
        return set()

    results = data.get("results")
    if not isinstance(results, list):
        raise ValueError("claim-review results array must be present")
    reviewed = []
    for index, item in enumerate(results):
        if not isinstance(item, dict):
            raise ValueError(f"results[{index}] must be an object")
        claim_id = item.get("claim_id")
        if not _valid_identifier(claim_id, meaningful_text):
            raise ValueError(f"results[{index}].claim_id is invalid")
        claim_id = claim_id.strip()
        if item.get("verdict") not in VERDICTS:
            raise ValueError(f"results[{index}].verdict is outside the three-value enum")
        _string_array(item.get("evidence"), f"results[{index}].evidence", nonempty=True,
                      meaningful_text=meaningful_text)
        _string_array(item.get("alternative_explanations"),
                      f"results[{index}].alternative_explanations",
                      meaningful_text=meaningful_text)
        reviewed.append(claim_id)
    if len(reviewed) != len(set(reviewed)):
        raise ValueError("review artifact contains duplicate claim_id")
    reviewed_set = set(reviewed)
    if claim_ids is not None and reviewed_set - set(claim_ids):
        raise ValueError(
            f"review artifact contains claim_id outside registry: "
            f"{sorted(reviewed_set - set(claim_ids))}")
    return reviewed_set


def validate_blocking_findings(blockers, *, meaningful_text=_meaningful_text):
    """Pure blocker structure validator; unresolved blockers are valid but not releasable."""
    if not isinstance(blockers, list):
        raise ValueError("blocking_findings must be an array")
    ids = []
    for index, item in enumerate(blockers):
        if not isinstance(item, dict) \
                or not _valid_identifier(item.get("id"), meaningful_text):
            raise ValueError(f"blocking_findings[{index}].id is invalid")
        if not isinstance(item.get("resolved"), bool):
            raise ValueError(f"blocking_findings[{index}].resolved must be bool")
        if item["resolved"] and not meaningful_text(item.get("resolution")):
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


def _load_artifact(case_dir, artifact_ref, role, registry_sha256, claim_ids, *,
                   meaningful_text=_meaningful_text,
                   reject_constant=_reject_constant):
    if not isinstance(artifact_ref, dict):
        raise ValueError("review artifact ref missing")
    path = contained_regular(case_dir, artifact_ref.get("path", ""), "review artifact")
    if (artifact_ref.get("size") != path.stat().st_size
            or artifact_ref.get("sha256") != sha(path)):
        raise ValueError("review artifact binding invalid")
    try:
        data = _loads_json(path.read_text(encoding="utf-8"), reject_constant)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"review artifact JSON invalid: {exc}") from exc
    reviewed = validate_review_artifact(
        data, role, registry_sha256, claim_ids, meaningful_text=meaningful_text)
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
            artifact_data = _loads_json(staging.read_text(encoding="utf-8"))
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
        remove_any(staging)
        remove_any(tmp)
        if artifact_published and not receipt_published and final.is_file():
            final.unlink()
        raise


def validate_review_receipt(case_dir, receipt, role, artifact_ref,
                            registry_sha256=None, claim_ids=None, *,
                            meaningful_text=_meaningful_text,
                            reject_constant=_reject_constant):
    root = Path(case_dir).resolve()
    receipt_path = contained_regular(root, receipt, "review execution receipt")
    try:
        data = _loads_json(receipt_path.read_text(encoding="utf-8"), reject_constant)
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
        root, artifact_ref, role, registry_sha256, claim_ids,
        meaningful_text=meaningful_text, reject_constant=reject_constant)
    return data, artifact_data, reviewed


def _target_from_accounting(case_dir):
    path = contained_regular(case_dir, "accounting_mode.json", "accounting target")
    try:
        data = _loads_json(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"accounting target JSON invalid: {exc}") from exc
    chain = data.get("chain")
    token = data.get("token") or data.get("mint")
    block = data.get("as_of_block")
    if not _meaningful_text(chain) or not _meaningful_text(token) \
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
            blocking_findings = _loads_json(blockers_path.read_text(encoding="utf-8"))
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
        execution_sha256s = set()
        artifact_sha256s = set()
        claim_review_entrypoints = set()
        for receipt_path in receipt_paths:
            try:
                execution = _loads_json(receipt_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"review execution receipt JSON invalid: {exc}") from exc
            role = execution.get("role")
            artifact_ref = execution.get("artifact")
            execution, _, reviewed = validate_review_receipt(
                root, receipt_path, role, artifact_ref,
                registry_sha256=registry_ref["sha256"], claim_ids=claim_ids)
            execution_ref = ref(root, receipt_path)
            execution_sha256 = execution_ref["sha256"]
            artifact_sha256 = artifact_ref.get("sha256")
            if execution_sha256 in execution_sha256s:
                raise ValueError("duplicate review execution receipt content")
            if artifact_sha256 in artifact_sha256s:
                raise ValueError("duplicate review artifact content")
            execution_sha256s.add(execution_sha256)
            artifact_sha256s.add(artifact_sha256)
            roles.add(role)
            if role in CLAIM_REVIEW_ROLES:
                entrypoint_key = (role, execution["entrypoint"]["sha256"])
                if entrypoint_key in claim_review_entrypoints:
                    raise ValueError("duplicate claim-review role and entrypoint content")
                claim_review_entrypoints.add(entrypoint_key)
                reviewed_sets.append(reviewed)
            reviews.append({
                "role": role,
                "exit_code": execution["exit_code"],
                "artifact": artifact_ref,
                "runner": execution["producer"],
                "execution_receipt": execution_ref,
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
        remove_any(tmp)
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
