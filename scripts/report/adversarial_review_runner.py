#!/usr/bin/env python3
"""Run, validate and aggregate fixed adversarial-review roles."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import secrets
import shutil
import stat
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
from supply_truth_gate import _meaningful_text, _reject_constant

ROLES = {"entity_attribution_skeptic", "completeness_critic"}
CLAIM_REVIEW_ROLES = ROLES - {"completeness_critic"}
VERDICTS = {"CONFIRMED", "WEAKENED", "REFUTED"}
BLOCKER_REQUIRED_KEYS = frozenset({"id", "resolved", "source"})
BLOCKER_ALLOWED_KEYS = BLOCKER_REQUIRED_KEYS | {"resolution"}
BLOCKER_SOURCE_KINDS = frozenset(
    {"completeness_finding", "non_covered", "refuted_claim", "manual"})
MIN_MEANINGFUL_CHARS = 10
ARTIFACT_SCHEMA = "adversarial-review-artifact/v2"
REGISTRY_SCHEMA = "a4-claims/v2"
AGGREGATE_SCHEMA = "adversarial-review/v4"
EXECUTION_SCHEMA = "adversarial-review-execution/v1"
LEDGER_SCHEMA = "review-ledger/v1"
LEDGER_FILENAME = "adversarial_review_ledger.jsonl"
LEDGER_KEYS = frozenset({
    "schema", "seq", "prev_line_sha", "receipt_path", "receipt_sha", "role",
    "artifact_sha",
})
V4_RERUN_HINT = "存量 adversarial-review/v2、v3 须按 v4 重跑对抗复核"


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


def _valid_sha256(value):
    return (isinstance(value, str) and len(value) == 64
            and all(char in "0123456789abcdef" for char in value))


def _parse_review_ledger_bytes(data):
    if not data:
        raise ValueError("adversarial review ledger is missing or empty")
    rows = []
    predecessor = "GENESIS"
    for expected_seq, raw_line in enumerate(data.splitlines(keepends=True), start=1):
        if not raw_line.strip():
            raise ValueError(f"review ledger line {expected_seq} is empty")
        try:
            item = _loads_json(raw_line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"review ledger line {expected_seq} JSON invalid: {exc}") from exc
        if not isinstance(item, dict) or set(item) != LEDGER_KEYS:
            raise ValueError(f"review ledger line {expected_seq} keys invalid")
        if item.get("schema") != LEDGER_SCHEMA:
            raise ValueError(f"review ledger line {expected_seq} schema invalid")
        if isinstance(item.get("seq"), bool) or item.get("seq") != expected_seq:
            raise ValueError(
                f"review ledger seq is not contiguous: expected {expected_seq}, "
                f"got {item.get('seq')!r}")
        if item.get("prev_line_sha") != predecessor:
            raise ValueError(f"review ledger prev_line_sha mismatch at seq {expected_seq}")
        receipt_name = item.get("receipt_path")
        if (not isinstance(receipt_name, str) or not receipt_name
                or Path(receipt_name).name != receipt_name):
            raise ValueError(f"review ledger receipt_path invalid at seq {expected_seq}")
        if not _valid_sha256(item.get("receipt_sha")):
            raise ValueError(f"review ledger receipt_sha invalid at seq {expected_seq}")
        if item.get("role") not in ROLES:
            raise ValueError(f"review ledger role invalid at seq {expected_seq}")
        if not _valid_sha256(item.get("artifact_sha")):
            raise ValueError(f"review ledger artifact_sha invalid at seq {expected_seq}")
        line_sha = hashlib.sha256(raw_line).hexdigest()
        rows.append((item, line_sha))
        predecessor = line_sha
    return rows


def validate_review_ledger(case_dir):
    """Validate the append-only ledger and bind every active row to current bytes."""
    root = Path(case_dir).resolve()
    ledger_path = contained_regular(root, LEDGER_FILENAME, "adversarial review ledger")
    rows = _parse_review_ledger_bytes(ledger_path.read_bytes())
    active = {}
    for item, _ in rows:
        active[item["receipt_path"]] = item
    for receipt_name, item in active.items():
        receipt_path = contained_regular(root, receipt_name, "ledger review receipt")
        if sha(receipt_path) != item["receipt_sha"]:
            raise ValueError(f"review ledger active receipt bytes changed: {receipt_name}")
        try:
            execution = _loads_json(receipt_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"ledger review receipt JSON invalid: {receipt_name}: {exc}") from exc
        artifact = execution.get("artifact") if isinstance(execution, dict) else None
        if (execution.get("role") != item["role"] or not isinstance(artifact, dict)
                or artifact.get("sha256") != item["artifact_sha"]):
            raise ValueError(f"review ledger row differs from active receipt: {receipt_name}")
    binding = {
        "entries": len(rows),
        "active": len(active),
        "tip_sha": rows[-1][1],
    }
    return binding, active


def append_review_ledger_entry(case_dir, receipt, role, artifact_sha):
    """Append one hash-chained JSONL row with a single O_APPEND write."""
    root = Path(case_dir).resolve()
    receipt_path = contained_regular(root, receipt, "review execution receipt")
    receipt_name = receipt_path.relative_to(root).as_posix()
    if Path(receipt_name).name != receipt_name:
        raise ValueError("review execution receipt must be in case root")
    if role not in ROLES or not _valid_sha256(artifact_sha):
        raise ValueError("review ledger role/artifact binding invalid")
    ledger_path = root / LEDGER_FILENAME
    if ledger_path.is_symlink() or (ledger_path.exists() and not ledger_path.is_file()):
        raise ValueError("adversarial review ledger must be a regular case-root file")
    flags = os.O_RDWR | os.O_CREAT | os.O_APPEND
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(ledger_path, flags, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("adversarial review ledger must be a regular file")
        os.lseek(fd, 0, os.SEEK_SET)
        chunks = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        existing = b"".join(chunks)
        rows = _parse_review_ledger_bytes(existing) if existing else []
        payload = {
            "schema": LEDGER_SCHEMA,
            "seq": len(rows) + 1,
            "prev_line_sha": rows[-1][1] if rows else "GENESIS",
            "receipt_path": receipt_name,
            "receipt_sha": sha(receipt_path),
            "role": role,
            "artifact_sha": artifact_sha,
        }
        raw_line = (json.dumps(
            payload, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        written = os.write(fd, raw_line)
        if written != len(raw_line):
            raise OSError(f"short review ledger append: {written}/{len(raw_line)}")
        os.fsync(fd)
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
    return payload


def remove_any(path):
    """Remove any existing path shape, including broken symlinks and special files."""
    path = Path(path)
    if os.path.lexists(path):
        if path.is_dir() and not path.is_symlink():
            def repair_and_retry(func, failed_name, _exc):
                failed = Path(failed_name)
                writable = failed if failed.is_dir() else failed.parent
                writable.chmod(writable.stat().st_mode | 0o700)
                func(failed_name)

            shutil.rmtree(path, onexc=repair_and_retry)
        else:
            path.unlink()


def _valid_identifier(value, meaningful_text=_meaningful_text):
    if not isinstance(value, str):
        return False
    stripped = value.strip()
    return bool(stripped) and all(meaningful_text(char) for char in stripped)


def _loads_json(text, reject_constant=_reject_constant):
    return json.loads(text, parse_constant=reject_constant)


def _has_min_meaningful_chars(value, minimum=MIN_MEANINGFUL_CHARS, *,
                              meaningful_text=_meaningful_text):
    if not isinstance(value, str):
        return False
    return sum(1 for char in value if meaningful_text(char)) >= minimum


def _string_array(value, label, *, nonempty=False, min_meaningful=None,
                  meaningful_text=_meaningful_text):
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError(f"{label} must be {'a non-empty ' if nonempty else 'an '}array")
    if any(not meaningful_text(item) for item in value):
        raise ValueError(f"{label} must contain only non-empty strings")
    if min_meaningful is not None and any(
            not _has_min_meaningful_chars(
                item, min_meaningful, meaningful_text=meaningful_text)
            for item in value):
        raise ValueError(
            f"{label} entries require at least {min_meaningful} meaningful characters")


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
                      min_meaningful=MIN_MEANINGFUL_CHARS,
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
    booked_sources = set()
    for index, item in enumerate(blockers):
        if not isinstance(item, dict) \
                or not _valid_identifier(item.get("id"), meaningful_text):
            raise ValueError(f"blocking_findings[{index}].id is invalid")
        if not isinstance(item.get("resolved"), bool):
            raise ValueError(f"blocking_findings[{index}].resolved must be bool")
        unknown = set(item) - BLOCKER_ALLOWED_KEYS
        missing = BLOCKER_REQUIRED_KEYS - set(item)
        if unknown:
            raise ValueError(
                f"blocking_findings[{index}] contains unsupported keys: {sorted(unknown)}")
        if missing:
            raise ValueError(
                f"blocking_findings[{index}] missing required keys: {sorted(missing)}")
        source = item.get("source")
        if not isinstance(source, dict) or set(source) != {"kind", "ref"}:
            raise ValueError(
                f"blocking_findings[{index}].source must contain exactly kind and ref")
        kind = source.get("kind")
        if kind not in BLOCKER_SOURCE_KINDS:
            raise ValueError(f"blocking_findings[{index}].source.kind is invalid")
        ref_value = source.get("ref")
        if not meaningful_text(ref_value):
            raise ValueError(f"blocking_findings[{index}].source.ref is invalid")
        if item["resolved"] and "resolution" not in item:
            raise ValueError(
                f"blocking_findings[{index}] resolved=true requires resolution")
        if "resolution" in item and not _has_min_meaningful_chars(
                item.get("resolution"), meaningful_text=meaningful_text):
            raise ValueError(
                f"blocking_findings[{index}].resolution requires at least "
                f"{MIN_MEANINGFUL_CHARS} meaningful characters")
        ids.append(item["id"].strip())
        if kind != "manual":
            source_key = (kind, ref_value)
            if source_key in booked_sources:
                raise ValueError("blocking_findings contains duplicate non-manual source")
            booked_sources.add(source_key)
    if len(ids) != len(set(ids)):
        raise ValueError("blocking_findings id must be unique within aggregate")
    return blockers


def build_required_refs(review_entries):
    """Build every mechanically required blocker source from validated artifacts."""
    required = {}
    for role, artifact_relpath, artifact_data in review_entries:
        if role == "completeness_critic":
            for field, kind in (("findings", "completeness_finding"),
                                ("non_covered", "non_covered")):
                for index, text in enumerate(artifact_data[field]):
                    required[(kind, f"{artifact_relpath}#/{field}/{index}")] = text
        elif role in CLAIM_REVIEW_ROLES:
            for index, item in enumerate(artifact_data["results"]):
                if item["verdict"] == "REFUTED":
                    claim_id = item["claim_id"].strip()
                    required[("refuted_claim",
                              f"{artifact_relpath}#/results/{index}:{claim_id}")] = claim_id
    return required


def validate_blocker_linkage(blockers, required_refs):
    """Require exact two-way agreement between artifact-derived refs and blocker rows."""
    required = set(required_refs)
    booked = {
        (item["source"]["kind"], item["source"]["ref"])
        for item in blockers if item["source"]["kind"] != "manual"
    }
    missing = required - booked
    ghost = booked - required
    if missing or ghost:
        details = []
        if missing:
            rendered = [
                f"{kind}:{ref} ({required_refs.get((kind, ref), '')})"
                for kind, ref in sorted(missing)
            ]
            details.append(f"missing blocker refs: {rendered}")
        if ghost:
            details.append(f"ghost blocker refs: {sorted(ghost)}")
        raise ValueError("blocker linkage mismatch；" + "；".join(details))
    return booked


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
    receipt_path = contained_output(root, receipt, "review execution receipt path")
    if final.exists() != receipt_path.exists():
        raise ValueError("review rerun requires the prior artifact and receipt to both exist")
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
        append_review_ledger_entry(root, receipt_path, role, payload["artifact"]["sha256"])
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
        review_entrypoints = set()
        review_entries = []
        for receipt_path in receipt_paths:
            try:
                execution = _loads_json(receipt_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"review execution receipt JSON invalid: {exc}") from exc
            role = execution.get("role")
            artifact_ref = execution.get("artifact")
            execution, artifact_data, reviewed = validate_review_receipt(
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
            entrypoint_key = execution["entrypoint"]["sha256"]
            if entrypoint_key in review_entrypoints:
                raise ValueError("duplicate review entrypoint content")
            review_entrypoints.add(entrypoint_key)
            review_entries.append((role, artifact_ref["path"], artifact_data))
            if role in CLAIM_REVIEW_ROLES:
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
        required_refs = build_required_refs(review_entries)
        validate_blocker_linkage(blocking_findings, required_refs)
        ledger_binding, active_ledger = validate_review_ledger(root)
        active_receipt_sha256s = {
            item["receipt_sha"] for item in active_ledger.values()
        }
        if active_receipt_sha256s != execution_sha256s:
            raise ValueError(
                "review ledger active receipt set differs from finalize receipts: "
                f"ledger_only={sorted(active_receipt_sha256s - execution_sha256s)} "
                f"finalize_only={sorted(execution_sha256s - active_receipt_sha256s)}")
        unresolved = [item for item in blocking_findings if not item["resolved"]]
        payload = {
            "schema": AGGREGATE_SCHEMA,
            "target": _target_from_accounting(root),
            "producer": repo_producer(),
            "claim_registry": registry_ref,
            "reviews": reviews,
            "review_ledger": ledger_binding,
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
