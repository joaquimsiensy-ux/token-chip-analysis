#!/usr/bin/env python3
"""Production aggregator and validator for shared formal release evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE.parent / "lib"))

from adversarial_review_runner import validate_review_receipt
from chain_registry import recon_adapter_for, resolve_alias
from receipt_validate import validate_receipt

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
RECON_RUNNERS = {"scripts/report/reconciliation_report.py"}
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
    family = recon_adapter_for(chain)
    if family not in RECON_PRODUCERS:
        raise ValueError(f"chain has no registered reconciliation adapter: {chain!r}")
    return family


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical_target(target):
    if not isinstance(target, dict) or set(target) != {"chain", "token", "as_of_block"}:
        raise ValueError("target must contain exactly chain/token/as_of_block")
    slot = target.get("as_of_block")
    if isinstance(slot, bool) or not isinstance(slot, int) or slot < 0:
        raise ValueError("target as_of_block/slot must be a non-negative integer")
    chain = resolve_alias(target.get("chain"))
    token = str(target.get("token") or "").strip().lower()
    if not chain or not token:
        raise ValueError("target chain/token must be non-empty")
    return {"chain": chain, "token": token, "as_of_block": slot}


def validate_reconciliation_check(root, key, item, target, family):
    """Validate one producer receipt semantically; wrapper fields are comparisons, not truth."""
    if not isinstance(item, dict):
        raise ValueError(f"reconciliation {key} item missing")
    path = ref_ok(root, item.get("receipt"))
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"reconciliation {key} receipt JSON invalid: {exc}") from exc
    migration = "存量案例须重跑对应生产者获取当前回执"
    envelope_errors = validate_receipt(receipt)
    if envelope_errors:
        raise ValueError(
            f"reconciliation {key} receipt envelope invalid: {envelope_errors[0]}；{migration}")
    _require(canonical_target(receipt.get("target")) == canonical_target(target),
             f"reconciliation {key} receipt target mismatch；{migration}")
    _require(receipt.get("verdict") == item.get("status")
             and receipt.get("exit_code") == item.get("exit_code"),
             f"reconciliation {key} wrapper/receipt verdict mismatch")
    _require(receipt.get("verdict") == "PASS" and receipt.get("exit_code") == 0,
             f"reconciliation {key} receipt is not PASS/0")

    schema = receipt.get("schema")
    obs = receipt.get("observations") or {}
    if family == "evm" and key in {"balance", "supply"}:
        _require(schema == "evm-reconciliation-receipt/v2",
                 f"reconciliation {key} unknown schema {schema!r}；{migration}")
        if key == "balance":
            bal = obs.get("balance_reconciliation") or {}
            _require(isinstance(bal.get("checked"), int) and bal["checked"] > 0
                     and bal.get("matched") == bal["checked"]
                     and bal.get("mismatched") == 0 and bal.get("rpc_errors") == 0,
                     "balance receipt observations incomplete or non-PASS")
        else:
            supply = obs.get("supply_closure") or {}
            _require(supply.get("closed") is True and supply.get("negative_count") == 0,
                     "supply receipt observations incomplete or non-closed")
    elif family == "solana" and key in {"balance", "time"}:
        _require(schema == "solana-anchor-sampler-receipt/v2",
                 f"reconciliation {key} unknown schema {schema!r}；{migration}")
        coverage = receipt.get("coverage") or {}
        _require(isinstance(coverage.get("requested_days"), int)
                 and coverage["requested_days"] > 0
                 and coverage.get("covered_days") == coverage["requested_days"]
                 and coverage.get("failed_days") == 0 and receipt.get("failures") == [],
                 "anchor receipt coverage incomplete")
    elif family == "solana" and key == "supply":
        _require(schema == "solana-observation-bundle/v1",
                 f"reconciliation supply unknown schema {schema!r}；{migration}")
        _require(receipt.get("closed") is True
                 and str(receipt.get("supply_raw")) == str(receipt.get("sum_accounts_raw"))
                 and isinstance(receipt.get("output"), dict),
                 "solana supply receipt is not a closed snapshot")
        from solana_observation import validate_observation_bundle
        validate_observation_bundle(receipt, expected_mint=target["token"])
        ref_ok(root, receipt["output"])
    elif key == "supply_truth":
        _require(schema == "supply-truth-receipt/v3",
                 f"reconciliation supply_truth unknown schema {schema!r}；{migration}")
        _require(receipt.get("gate") == "supply_truth"
                 and receipt.get("replay_net") is not None
                 and receipt.get("onchain_total_supply") is not None
                 and receipt.get("diff") is not None
                 and all(field in receipt for field in (
                     "decision_rule", "burn_form", "primary_verdict",
                     "sink_reconciliation")),
                 "supply_truth receipt observations incomplete")
        rule = receipt.get("decision_rule")
        _require(rule in {"primary_form1", "sink_fallback_form2"},
                 "supply_truth decision_rule invalid")
        if rule == "primary_form1":
            _require(receipt.get("primary_verdict") == "PASS"
                     and receipt.get("burn_form") is None
                     and receipt.get("sink_reconciliation") is None,
                     "primary_form1 receipt semantics invalid")
        else:
            sink = receipt.get("sink_reconciliation")
            _require(family == "evm" and receipt.get("primary_verdict") == "FAIL"
                     and receipt.get("burn_form") == "dead_sink"
                     and isinstance(sink, dict) and set(sink) == {"zero", "dead"},
                     "sink_fallback_form2 receipt semantics invalid")
            for address in ("zero", "dead"):
                row = sink.get(address)
                _require(isinstance(row, dict)
                         and set(row) == {"replay_raw", "onchain_raw"}
                         and isinstance(row.get("replay_raw"), str)
                         and row.get("replay_raw") == row.get("onchain_raw"),
                         f"sink_fallback_form2 {address} reconciliation invalid")
            try:
                mint_raw = int(str(receipt["mint_total"]))
                burn_raw = int(str(receipt["burn_total"]))
                onchain_raw = int(str(receipt["onchain_total_supply"]))
                sink_raw = sum(int(sink[address]["replay_raw"])
                               for address in ("zero", "dead"))
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("sink_fallback_form2 scalar fields invalid") from exc
            _require(mint_raw == onchain_raw and sink_raw == burn_raw,
                     "sink_fallback_form2 scalar/sink closure invalid")
        _require(receipt.get("mode") == "formal" and isinstance(receipt.get("inputs"), dict)
                 and bool(receipt["inputs"]),
                 "supply_truth receipt must be formal and bind replay_stats input")
        if family == "solana":
            bundle_ref = (receipt.get("inputs") or {}).get("observation_bundle")
            _require(isinstance(bundle_ref, dict),
                     "solana supply_truth does not bind observation bundle")
            bundle_path = Path(bundle_ref.get("path", "")).resolve()
            bundle_path.relative_to(root)
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            from solana_observation import validate_observation_bundle
            validate_observation_bundle(bundle, bundle_path=bundle_path,
                                        expected_mint=target["token"])
            _require(isinstance(receipt.get("observed_context_slot"), int)
                     and receipt["observed_context_slot"] == bundle["supply"]["slot"]
                     and bundle["snapshot"]["slot"]
                     == canonical_target(target)["as_of_block"],
                     "solana supply_truth observation/bundle slots are not bound")
    elif family == "evm" and key == "time":
        _require(schema == "time-spotcheck/v2",
                 f"reconciliation time unknown schema {schema!r}；{migration}")
        _require(isinstance(receipt.get("points"), int) and receipt["points"] > 0
                 and receipt.get("exact_match") == receipt["points"]
                 and receipt.get("mismatch") == 0 and receipt.get("rpc_err") == 0,
                 "time receipt observations incomplete or non-PASS")
    else:
        raise ValueError(f"reconciliation {key} has no validator for family={family}；{migration}")
    return receipt


def validate_reconciliation_report(root, expected_target=None):
    """Deeply validate the controlled wrapper and all four bound receipts."""
    root = Path(root).resolve()
    recon = json.loads(regular(root, "reconciliation_report.json").read_text())
    target = recon.get("target")
    if (recon.get("schema") != "reconciliation-report/v2"
            or not isinstance(target, dict)
            or set(target) != {"chain", "token", "as_of_block"}
            or not target.get("chain") or not target.get("token")
            or recon.get("verdict") != "PASS" or recon.get("exit_code") != 0):
        raise ValueError("reconciliation target/schema/verdict invalid")
    if expected_target is not None and canonical_target(target) != canonical_target(expected_target):
        raise ValueError("reconciliation target/schema mismatch")
    family = chain_family(target["chain"])
    repo_ref_ok(recon.get("producer"), RECON_RUNNERS, "reconciliation wrapper")
    checks = recon.get("checks")
    if not isinstance(checks, dict) or set(checks) != {"balance", "supply", "supply_truth", "time"}:
        raise ValueError("reconciliation wrapper must contain exactly four checks")
    for key in ("balance", "supply", "supply_truth", "time"):
        item = checks[key]
        if (not isinstance(item, dict) or item.get("status") != "PASS"
                or item.get("exit_code") != 0):
            raise ValueError(f"reconciliation {key} lacks PASS execution receipt")
        repo_ref_ok(item.get("producer"), RECON_PRODUCERS[family][key],
                    f"reconciliation {key}")
        validate_reconciliation_check(root, key, item, target, family)
    return target


def validate_sources(root):
    root = Path(root).resolve()
    accounting = json.loads(regular(root, "accounting_mode.json").read_text())
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
    if family == "solana":
        _require(accounting.get("execution_mode") == "formal",
                 "solana accounting exploration evidence is not releasable")
        bundle_ref = accounting.get("observation_bundle")
        _require(isinstance(bundle_ref, dict),
                 "solana accounting does not bind observation bundle")
        bundle_path = Path(bundle_ref.get("path", "")).resolve()
        bundle_path.relative_to(root)
        _require(bundle_path.is_file() and bundle_ref.get("size") == bundle_path.stat().st_size
                 and bundle_ref.get("sha256") == sha(bundle_path),
                 "solana accounting observation bundle ref invalid")
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        from solana_observation import validate_observation_bundle
        validate_observation_bundle(bundle, bundle_path=bundle_path,
                                    expected_mint=token)
        _require(accounting.get("observed_context_slot") == bundle["snapshot"]["slot"],
                 "solana accounting slot is not bundle snapshot slot")
    validate_reconciliation_report(root, target)
    if (adversarial.get("schema") != "adversarial-review/v2"
            or canonical_target(adversarial.get("target")) != canonical_target(target)
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
