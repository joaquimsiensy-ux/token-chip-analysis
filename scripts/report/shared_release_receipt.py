#!/usr/bin/env python3
"""Production aggregator and validator for shared formal release evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from adversarial_review_runner import validate_review_receipt

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
FILES = ("accounting_mode.json", "reconciliation_report.json", "adversarial_review.json")
ACCOUNTING_PRODUCERS = {
    "evm": "scripts/evm/accounting_gate.py",
    "solana": "scripts/solana/accounting_gate_sol.py",
}
RECON_PRODUCERS = {
    "evm": {
        "balance": {"scripts/evm/verify_recon.py"},
        "supply": {"scripts/evm/verify_recon.py"},
        "supply_truth": {"scripts/lib/supply_truth_gate.py"},
        "time": {"scripts/lib/time_spotcheck.py"},
    },
    "solana": {
        "balance": {"scripts/solana/anchor_sampler.py"},
        "supply": {"scripts/solana/scan_token_accounts.py"},
        "supply_truth": {"scripts/lib/supply_truth_gate.py"},
        "time": {"scripts/solana/anchor_sampler.py"},
    },
}
ADVERSARIAL_RUNNERS = {"scripts/report/adversarial_review_runner.py"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def regular(root, rel):
    root = Path(root).resolve()
    raw = root / str(rel)
    if raw.is_symlink():
        raise ValueError(f"evidence file invalid: {rel}")
    path = raw.resolve()
    path.relative_to(root)
    if not path.is_file():
        raise ValueError(f"evidence file invalid: {rel}")
    return path


def ref_ok(root, ref):
    if not isinstance(ref, dict):
        raise ValueError("evidence ref missing")
    path = regular(root, ref.get("path"))
    if ref.get("sha256") != sha(path):
        raise ValueError(f"evidence hash mismatch: {path.name}")
    return path


def repo_ref_ok(ref, allowed, label):
    if not isinstance(ref, dict):
        raise ValueError(f"{label} producer/runner ref missing")
    rel = str(ref.get("path", ""))
    if rel not in allowed:
        raise ValueError(f"{label} producer/runner path is not whitelisted: {rel}")
    path = (REPO / rel).resolve()
    path.relative_to(REPO)
    if not path.is_file() or ref.get("sha256") != sha(path):
        raise ValueError(f"{label} producer/runner is not current repository script")
    return path


def chain_family(chain):
    return "solana" if str(chain).lower() in {"sol", "solana"} else "evm"


def validate_sources(root):
    root = Path(root).resolve()
    accounting = json.loads(regular(root, "accounting_mode.json").read_text())
    recon = json.loads(regular(root, "reconciliation_report.json").read_text())
    adversarial = json.loads(regular(root, "adversarial_review.json").read_text())
    if (accounting.get("schema") != "accounting-gate/v1" or accounting.get("exit_code") != 0
            or str(accounting.get("verdict", "")).upper() not in {"PASS", "WARN"}
            or not accounting.get("chain") or not (accounting.get("token") or accounting.get("mint"))
            or not isinstance(accounting.get("checks"), dict) or not accounting["checks"]):
        raise ValueError("accounting evidence is not a production gate receipt")
    family = chain_family(accounting["chain"])
    expected_accounting = ACCOUNTING_PRODUCERS[family]
    repo_ref_ok(accounting.get("producer"), {expected_accounting}, "accounting")
    token = accounting.get("token") or accounting.get("mint")
    target = {"chain": accounting["chain"], "token": str(token).lower(),
              "as_of_block": accounting.get("as_of_block")}
    if recon.get("schema") != "reconciliation-report/v2" or recon.get("target") != target:
        raise ValueError("reconciliation target/schema mismatch")
    for key in ("balance", "supply", "supply_truth", "time"):
        item = (recon.get("checks") or {}).get(key)
        if (not isinstance(item, dict) or item.get("status") != "PASS"
                or item.get("exit_code") != 0):
            raise ValueError(f"reconciliation {key} lacks PASS execution receipt")
        ref_ok(root, item.get("receipt"))
        repo_ref_ok(item.get("producer"), RECON_PRODUCERS[family][key], f"reconciliation {key}")
    if (adversarial.get("schema") != "adversarial-review/v2"
            or adversarial.get("target") != target
            or adversarial.get("release_decision") != "PASS"):
        raise ValueError("adversarial target/schema/decision invalid")
    roles = set()
    for item in adversarial.get("reviews") or []:
        if not isinstance(item, dict) or item.get("exit_code") != 0:
            raise ValueError("review lacks successful execution receipt")
        role = str(item.get("role", "")).lower()
        roles.add(role)
        artifact = item.get("artifact")
        ref_ok(root, artifact)
        repo_ref_ok(item.get("runner"), ADVERSARIAL_RUNNERS, f"adversarial {role}")
        execution = item.get("execution_receipt")
        ref_ok(root, execution)
        validate_review_receipt(root, execution.get("path"), role, artifact)
    if (not any("completeness" in role for role in roles)
            or not any("entity" in role or "attribution" in role for role in roles)):
        raise ValueError("required adversarial roles missing")
    if any(not isinstance(item, dict) or not item.get("resolved")
           for item in adversarial.get("blocking_findings", [])):
        raise ValueError("unresolved adversarial blocker")
    return target


def create_bundle(root, out=None):
    root = Path(root).resolve()
    target = validate_sources(root)
    out = Path(out or root / "shared_release_receipt.json").resolve()
    if out.parent != root:
        raise ValueError("shared receipt must be in case root")
    payload = {"schema": "shared-release-receipt/v1", "status": "PASS",
               "producer": {"path": "shared_release_receipt.py", "sha256": sha(__file__)},
               "target": target,
               "inputs": {name: {"path": name, "sha256": sha(root / name)} for name in FILES}}
    tmp = out.with_name(f".{out.name}.tmp.{os.getpid()}")
    with tmp.open("x") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, out)
    return payload


def validate_bundle(root):
    errors = []
    root = Path(root).resolve()
    try:
        data = json.loads(regular(root, "shared_release_receipt.json").read_text())
        target = validate_sources(root)
        if (data.get("schema") != "shared-release-receipt/v1"
                or data.get("status") != "PASS" or data.get("target") != target):
            raise ValueError("shared receipt schema/target invalid")
        expected_producer = {"path": "shared_release_receipt.py", "sha256": sha(__file__)}
        if data.get("producer") != expected_producer:
            raise ValueError("shared receipt producer mismatch")
        expected = {name: {"path": name, "sha256": sha(root / name)} for name in FILES}
        if data.get("inputs") != expected:
            raise ValueError("shared receipt input hashes changed")
    except Exception as exc:
        errors.append(str(exc))
    return errors


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("case_dir")
    args = ap.parse_args(argv)
    try:
        create_bundle(args.case_dir)
    except Exception as exc:
        ap.exit(2, f"BLOCK: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
