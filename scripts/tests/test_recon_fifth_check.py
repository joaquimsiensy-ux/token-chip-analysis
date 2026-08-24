#!/usr/bin/env python3
"""Batch 1b semantic expected-red tests for the fifth reconciliation check."""

from __future__ import annotations

import json
from argparse import Namespace
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts/tests"), str(ROOT / "scripts/report"),
                str(ROOT / "scripts/lib")]

import audit_release_gate  # noqa: E402
import handoff_manifest  # noqa: E402
from formal_ready_test_harness import run_formal_script  # noqa: E402
from sqd_v4_test_fixture import MINT  # noqa: E402
from test_handoff_manifest import make_case  # noqa: E402


HANDOFF = ROOT / "scripts/report/handoff_manifest.py"


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def handoff(args, cwd):
    return run_formal_script(str(HANDOFF), args, cwd=cwd)


def build_solana_case(case):
    make_case(str(case), chain="solana", token=MINT, as_of_block=77)
    balances = json.loads((case / "data/holders_owners.json").read_text(encoding="utf-8"))
    total = sum(balances.values())
    slot = 77

    # Current v5/v3 reports carry a stale binding that differs from the
    # exact-like receipt; binding equality itself remains Batch 5.
    stale = {"cache_kind": "base", "gid": None,
             "soltx_edges_sha256": "1" * 64, "soltx_meta_sha256": "2" * 64,
             "edge_logical_sha256": "3" * 64}
    current = {**stale, "soltx_edges_sha256": "4" * 64}
    for name in ("wave_scan_report.json", "flow_anomaly_report.json"):
        path = case / name
        obj = json.loads(path.read_text(encoding="utf-8"))
        obj["edge_source_binding"] = stale
        write_json(path, obj)

    exact = case / "data/reconcile_receipt.json"
    write_json(exact, {"schema": "solana-reconcile/v4", "gate_pass": False,
                       "edge_source_binding": current})
    curve = case / "data/curve_costs.json"
    closed = case / f"data/closed_audit-{MINT.lower()}.json"
    write_json(curve, {"schema": "curve-cost/v1", "edge_source_binding": stale})
    write_json(closed, {"schema": "closed-account-audit/v1", "edge_source_binding": stale})
    data_map = json.loads((case / "data_map.json").read_text(encoding="utf-8"))
    data_map["files"].extend([
        {"path": "data/reconcile_receipt.json", "source": "batch1b semantic fixture"},
        {"path": "data/curve_costs.json", "source": "batch1b semantic fixture"},
        {"path": f"data/{closed.name}", "source": "batch1b semantic fixture"},
    ])
    write_json(case / "data_map.json", data_map)

    scan = run_formal_script(
        str(ROOT / "scripts/report/holder_distribution_scan.py"),
        ["--case-dir", str(case), "--stage", "initial"], cwd=case)
    if scan.returncode != 0:
        raise AssertionError(scan.stdout + scan.stderr)
    return total, slot


def current_verify_accepts(case):
    """Run current verify core while isolating unrelated legacy Solana receipts.

    make_case intentionally carries EVM-shaped deep reconciliation fixtures even
    when its scope is Solana.  Stub only those pre-existing deep checks; all
    handoff manifest/hash/gate/wave/flow checks under test remain current code.
    """
    original_recon = handoff_manifest.validate_reconciliation_report
    original_accounting = handoff_manifest.validate_accounting_receipt
    original_source = handoff_manifest.validate_evm_observation_source_chain

    target = {"chain": "solana", "token": MINT, "as_of_block": 77}
    exact = json.loads((case / "data/reconcile_receipt.json").read_text())

    def fake_recon(_case_dir, return_receipts=False):
        receipts = {"supply_truth": {}, "exact_reconcile": {
            "edge_source_binding": exact["edge_source_binding"], "inputs": {}}}
        return (target, receipts) if return_receipts else target

    def fake_accounting(_case_dir, expected_target=None):
        assert expected_target == target
        return target, {}, None

    try:
        handoff_manifest.validate_reconciliation_report = fake_recon
        handoff_manifest.validate_accounting_receipt = fake_accounting
        handoff_manifest.validate_evm_observation_source_chain = lambda *_args, **_kwargs: None
        fails, _manifest, _legacy = handoff_manifest.verify_case(str(case))
        return fails
    finally:
        handoff_manifest.validate_reconciliation_report = original_recon
        handoff_manifest.validate_accounting_receipt = original_accounting
        handoff_manifest.validate_evm_observation_source_chain = original_source


def main():
    red = 0

    # (14) Current audit release checker trusts wrapper status and ignores child refs.
    wrapper = {"schema": "reconciliation-report/v2",
               "target": {"chain": "solana", "token": MINT, "as_of_block": 1},
               "checks": {key: {"status": "PASS", "receipt": {
                   "path": f"{key}.json", "sha256": "bad"}}
                          for key in ("balance", "supply", "supply_truth", "time")}}
    errors = []
    with tempfile.TemporaryDirectory(prefix="batch5-audit-") as raw:
        audit_release_gate.check_reconciliation(Path(raw), wrapper, errors)
    assert errors and "公共深验失败" in errors[0]
    print("GREEN 14 audit_release 复用公共深验拒绝坏子 receipt")

    with tempfile.TemporaryDirectory(prefix="batch1b-fifth-", dir="/private/tmp") as raw:
        case = Path(raw)
        total, slot = build_solana_case(case)
        args = ["generate", "--case-dir", str(case), "--status", "READY",
                "--mode", "full", "--producer-model", "batch1b",
                "--chain", "solana", "--contract", MINT,
                "--cutoff", "2025-01-01T00:00:00Z", "--frozen-block", str(slot),
                "--denominators", json.dumps({"total_supply_raw": str(total)})]
        generated = handoff(args, case)
        assert generated.returncode == 2, generated.stdout + generated.stderr
        print("GREEN 1 handoff generate 对旧 wrapper/exact gate_pass=false fail-closed")

        # Build a baseline manifest through the same core while isolating the
        # deliberately malformed old wrapper.  Verification below restores the
        # real derived-binding validator and must reject stale artifacts.
        target = {"chain": "solana", "token": MINT, "as_of_block": 77}
        current = json.loads((case / "data/reconcile_receipt.json").read_text())[
            "edge_source_binding"]
        original_recon = handoff_manifest.validate_reconciliation_report
        original_bindings = handoff_manifest.validate_solana_derived_bindings

        def fake_recon(_case_dir, return_receipts=False):
            receipts = {"supply_truth": {}, "exact_reconcile": {
                "edge_source_binding": current, "inputs": {}}}
            return (target, receipts) if return_receipts else target

        ns = Namespace(
            case_dir=str(case), status="READY", mode="full", producer_model="batch5",
            chain="solana", contract=MINT, cutoff="2025-01-01T00:00:00Z",
            frozen_block="77", denominators=json.dumps({"total_supply_raw": str(total)}),
            status_reason=None, case_id=None, run_id=None, gate=None, include=None)
        try:
            handoff_manifest.validate_reconciliation_report = fake_recon
            handoff_manifest.validate_solana_derived_bindings = lambda *_a, **_k: True
            assert handoff_manifest.cmd_generate(ns) == 0
        finally:
            handoff_manifest.validate_reconciliation_report = original_recon
            handoff_manifest.validate_solana_derived_bindings = original_bindings

        failures = current_verify_accepts(case)
        assert any("curve_costs" in failure or "closed_audit" in failure
                   for failure in failures), "\n".join(failures)
        print("GREEN 24 handoff verify 拒绝 curve/audit_closed stale binding")

        for path in (case / "data/curve_costs.json",
                     case / f"data/closed_audit-{MINT.lower()}.json"):
            value = json.loads(path.read_text())
            value["edge_source_binding"] = current
            write_json(path, value)
        try:
            handoff_manifest.validate_reconciliation_report = fake_recon
            handoff_manifest.validate_solana_derived_bindings = lambda *_a, **_k: True
            assert handoff_manifest.cmd_generate(ns) == 0
        finally:
            handoff_manifest.validate_reconciliation_report = original_recon
            handoff_manifest.validate_solana_derived_bindings = original_bindings
        wave_failures = current_verify_accepts(case)
        assert any("wave_scan_report" in failure or "flow_anomaly_report" in failure
                   for failure in wave_failures), "\n".join(wave_failures)
        print("GREEN 19 handoff verify 拒绝 wave/flow stale binding")

        wave_path = case / "wave_scan_report.json"
        flow_path = case / "flow_anomaly_report.json"
        wave = json.loads(wave_path.read_text(encoding="utf-8"))
        flow = json.loads(flow_path.read_text(encoding="utf-8"))
        wave["schema"] = "wave-scan/v4"
        flow["schema"] = "flow-anomaly/v2"
        write_json(wave_path, wave)
        write_json(flow_path, flow)
        old_failures = current_verify_accepts(case)
        assert any("旧版" in failure and "wave" in failure for failure in old_failures)
        assert any("flow-anomaly/v3" in failure for failure in old_failures)
        print("GREEN 22 wave-scan/v4 与 flow-anomaly/v2 旧产物被 v5/v3 验收拒收")

    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main())
