#!/usr/bin/env python3
"""Run one fixed adversarial-review role and bind the fresh artifact to an execution receipt."""
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


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def contained_regular(root, path, label):
    root = Path(root).resolve()
    item = Path(path)
    raw = (root / item) if not item.is_absolute() else item
    if raw.is_symlink():
        raise ValueError(f"{label} must be a regular file inside case root")
    item = raw.resolve()
    item.relative_to(root)
    if not item.is_file():
        raise ValueError(f"{label} must be a regular file inside case root")
    return item


def repo_producer():
    return {"path": "scripts/report/adversarial_review_runner.py", "sha256": sha(__file__)}


def ref(root, path):
    path = contained_regular(root, path, "artifact")
    return {"path": str(path.relative_to(Path(root).resolve())),
            "size": path.stat().st_size, "sha256": sha(path)}


def run_review(case_dir, role, entrypoint, artifact, receipt):
    root = Path(case_dir).resolve()
    if role not in ROLES:
        raise ValueError(f"unsupported adversarial role: {role}")
    entry = contained_regular(root, entrypoint, "review entrypoint")
    final = (root / artifact).resolve()
    final.relative_to(root)
    if final.exists() or final.is_symlink():
        raise ValueError("review artifact must be absent before controlled execution")
    receipt_path = (root / receipt).resolve()
    receipt_path.relative_to(root)
    if receipt_path.exists() or receipt_path.is_symlink():
        raise ValueError("review execution receipt must be absent before controlled execution")
    staging = root / f".review-{role}-{secrets.token_hex(12)}.staging"
    env = os.environ.copy()
    env["CHIP_REVIEW_OUTPUT"] = str(staging)
    env["CHIP_REVIEW_ROLE"] = role
    proc = subprocess.run([sys.executable, str(entry)], cwd=root, env=env,
                          capture_output=True, text=True)
    if proc.returncode != 0:
        if staging.is_file():
            staging.unlink()
        raise ValueError(f"review entrypoint failed rc={proc.returncode}: {(proc.stderr or proc.stdout)[-300:]}")
    if staging.is_symlink() or not staging.is_file() or staging.stat().st_size == 0:
        raise ValueError("review entrypoint did not create a non-empty controlled artifact")
    os.replace(staging, final)
    payload = {
        "schema": "adversarial-review-execution/v1", "status": "PASS", "exit_code": 0,
        "role": role, "producer": repo_producer(),
        "entrypoint": {"path": str(entry.relative_to(root)), "sha256": sha(entry)},
        "artifact": ref(root, final),
    }
    tmp = receipt_path.with_name(f".{receipt_path.name}.tmp.{os.getpid()}")
    with tmp.open("x", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, receipt_path)
    return payload


def validate_review_receipt(case_dir, receipt, role, artifact_ref):
    root = Path(case_dir).resolve()
    receipt_path = contained_regular(root, receipt, "review execution receipt")
    data = json.loads(receipt_path.read_text(encoding="utf-8"))
    if (data.get("schema") != "adversarial-review-execution/v1"
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
    artifact_path = contained_regular(root, artifact_ref.get("path", ""), "review artifact")
    if (artifact_ref.get("size") != artifact_path.stat().st_size
            or artifact_ref.get("sha256") != sha(artifact_path)):
        raise ValueError("review artifact binding invalid")
    return data


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("case_dir")
    ap.add_argument("--role", required=True, choices=sorted(ROLES))
    ap.add_argument("--entrypoint", required=True)
    ap.add_argument("--artifact", required=True)
    ap.add_argument("--receipt", required=True)
    args = ap.parse_args(argv)
    try:
        run_review(args.case_dir, args.role, args.entrypoint, args.artifact, args.receipt)
    except Exception as exc:
        ap.exit(2, f"BLOCK: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
