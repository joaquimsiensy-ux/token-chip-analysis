#!/usr/bin/env python3
"""Batch 11 frozen/live Solana observation-bundle binding regressions."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts/report"), str(ROOT / "scripts/lib")]

import handoff_manifest  # noqa: E402
import shared_release_receipt as shared  # noqa: E402
from solana_attested_session import SOLANA_MAINNET_GENESIS_HASH  # noqa: E402
from solana_observation import build_observation_bundle  # noqa: E402


MINT = "mintcasesensitive" + "1" * 15
FROZEN_SLOT = 500
LIVE_SLOT = 501
FROZEN_BUNDLE = "data/solana_observation_bundle_frozen.json"


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path: Path, value) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


def ref(path: Path, shown: str | None = None) -> dict:
    path = Path(path)
    return {"path": shown or str(path), "size": path.stat().st_size,
            "sha256": sha(path)}


def repo_ref(rel: str) -> dict:
    return {"path": rel, "sha256": sha(ROOT / rel)}


def build_bundle(root: Path, work_rel: str, slot: int, owners: dict,
                 bundle_rel: str) -> tuple[Path, Path]:
    work = root / work_rel
    work.mkdir(parents=True, exist_ok=True)
    owners_path = write_json(work / "holders_owners.json", owners)
    accounts = [
        {"account": f"acct-{index}", "owner": owner, "amount_raw": amount}
        for index, (owner, amount) in enumerate(owners.items(), 1)
    ]
    accounts_path = write_json(work / "holders_accounts.json", accounts)
    inputs = {
        name: write_json(work / name, {"fixture": name, "slot": slot})
        for name in ("_supply.json", "_gpa_raw_all.json", "_gpa_raw_all.meta.json")
    }
    snapshot = write_json(work / "supply_snapshot.json", {
        "schema": "solana-holder-snapshot/v3", "owners": owners,
    })
    total = sum(owners.values())
    core = {
        "schema": "solana-observation-core/v1",
        "canonical_target": {"chain": "solana", "token": MINT,
                             "as_of_block": slot},
        "as_of_slot": slot, "as_of_block": slot, "observed_context_slot": slot,
        "snapshot": {"slot": slot},
        "mint_pre": {"slot": slot - 2, "json_parsed_slot": slot - 1,
                     "raw_sha256": "f" * 64},
        "mint_post": {"slot": slot + 2, "raw_sha256": "f" * 64},
        "supply": {"slot": slot + 3, "amount": str(total), "decimals": 0},
        "closure": {"gpa_amount": str(total), "mint_raw_amount": str(total),
                    "token_supply_amount": str(total), "closed": True},
        "attestation": {"expected_genesis": SOLANA_MAINNET_GENESIS_HASH,
                        "observed_genesis": SOLANA_MAINNET_GENESIS_HASH},
        "activity": {"mode": "complete", "writable_hits": [], "sample_size": 0,
                     "rpc_calls": 3, "complete": True},
    }
    bundle = build_observation_bundle(
        core, "scripts/solana/scan_token_accounts.py", inputs=inputs,
        holder_outputs={
            "accounts": ref(accounts_path, accounts_path.name),
            "owners": ref(owners_path, owners_path.name),
        },
        closed=True, supply_raw=str(total), sum_accounts_raw=str(total),
        output=ref(snapshot, snapshot.relative_to(root).as_posix()),
    )
    return write_json(root / bundle_rel, bundle), owners_path


def build_case(root: Path):
    frozen_bundle, frozen_owners = build_bundle(
        root, "data", FROZEN_SLOT, {"owner-a": 60, "owner-b": 40}, FROZEN_BUNDLE)
    live_bundle, _live_owners = build_bundle(
        root, "data/observe_live", LIVE_SLOT, {"owner-a": 70, "owner-b": 30},
        "data/observe_live/solana_observation_bundle.json")
    dummy_exact = write_json(root / "data/exact_receipt.json", {"fixture": "exact"})
    exact_ref = ref(frozen_owners, "data/holders_owners.json")
    state = {"exact_ref": exact_ref}
    target = {"chain": "solana", "token": MINT, "as_of_block": LIVE_SLOT}
    producers = {
        "supply": "scripts/solana/scan_token_accounts.py",
        "balance": "scripts/solana/anchor_sampler.py",
        "supply_truth": "scripts/lib/supply_truth_gate.py",
        "time": "scripts/solana/anchor_sampler.py",
        "exact_reconcile": "scripts/solana/replay_edges.py",
    }
    checks = {}
    for key in shared.RECON_CHECK_KEYS["solana"]:
        receipt_path = dummy_exact if key == "exact_reconcile" else live_bundle
        checks[key] = {
            "status": "PASS", "exit_code": 0,
            "producer": repo_ref(producers[key]),
            "receipt": ref(receipt_path, receipt_path.relative_to(root).as_posix()),
        }
    wrapper = {
        "schema": "reconciliation-report/v3", "family": "solana", "target": target,
        "producer": repo_ref("scripts/report/reconciliation_report.py"),
        "verdict": "PASS", "exit_code": 0, "checks": checks,
    }
    write_json(root / "reconciliation_report.json", wrapper)

    live_doc = json.loads(live_bundle.read_text(encoding="utf-8"))

    def fake_check(_root, key, _item, check_target, family):
        assert family == "solana"
        if key == "exact_reconcile":
            return {
                "target": {"chain": "solana", "token": MINT,
                           "as_of_block": FROZEN_SLOT},
                "inputs": {"holders_owners": dict(state["exact_ref"])},
                "edge_source_binding": {"cache_kind": "base", "gid": None,
                                        "soltx_edges_sha256": "1" * 64,
                                        "soltx_meta_sha256": "2" * 64,
                                        "edge_logical_sha256": "3" * 64},
            }
        if key == "supply":
            return live_doc
        return {"target": dict(check_target)}

    return {
        "target": target, "state": state, "fake_check": fake_check,
        "frozen_bundle": frozen_bundle, "frozen_owners": frozen_owners,
        "live_bundle": live_bundle, "dummy_exact": dummy_exact,
    }


def validate_with_stub(root: Path, fixture):
    original = shared.validate_reconciliation_check
    try:
        shared.validate_reconciliation_check = fixture["fake_check"]
        return shared.validate_reconciliation_report(root, return_receipts=True)
    finally:
        shared.validate_reconciliation_check = original


def expect_reject(root: Path, fixture, needle: str):
    try:
        validate_with_stub(root, fixture)
    except ValueError as exc:
        assert needle in str(exc), str(exc)
        return str(exc)
    raise AssertionError(f"expected rejection containing {needle!r}")


def test_r1_dynamic_hash_binding(root: Path, fixture):
    validate_with_stub(root, fixture)
    print("GREEN R1/G1 冻结态 exact 快照与 frozen bundle sha256+size 一致时通过")


def test_n1_n2_n3_n4(root: Path, fixture):
    frozen_path = fixture["frozen_bundle"]
    saved = frozen_path.read_bytes()
    frozen_path.unlink()
    expect_reject(root, fixture, "冻结态第五查快照必须哈希绑定冻结观测 bundle")
    frozen_path.write_bytes(saved)
    print("GREEN N1 冻结态缺 frozen bundle 拒绝")

    bundle = json.loads(saved)
    bundle["target"]["as_of_block"] = FROZEN_SLOT - 1
    bundle["as_of_slot"] = bundle["as_of_block"] = FROZEN_SLOT - 1
    bundle["observed_context_slot"] = FROZEN_SLOT - 1
    bundle["snapshot"]["slot"] = FROZEN_SLOT - 1
    bundle["mint_pre"]["slot"] = FROZEN_SLOT - 3
    bundle["mint_pre"]["json_parsed_slot"] = FROZEN_SLOT - 2
    bundle["mint_post"]["slot"] = FROZEN_SLOT + 1
    bundle["supply"]["slot"] = FROZEN_SLOT + 2
    write_json(frozen_path, bundle)
    expect_reject(root, fixture, "target 必须与 exact_reconcile target 全等")
    frozen_path.write_bytes(saved)
    print("GREEN N2 frozen bundle target 与 exact target 不同即拒")

    alternate = write_json(root / "data/alternate_owners.json", {"owner-a": 50, "owner-b": 50})
    fixture["state"]["exact_ref"] = ref(alternate, "data/alternate_owners.json")
    expect_reject(root, fixture, "sha256+size 必须全等")
    fixture["state"]["exact_ref"] = ref(
        fixture["frozen_owners"], "data/holders_owners.json")
    print("GREEN N3 exact 快照与 frozen bundle 指纹不一致即拒")

    wrapper_path = root / "reconciliation_report.json"
    wrapper = json.loads(wrapper_path.read_text(encoding="utf-8"))
    wrapper["target"]["as_of_block"] = FROZEN_SLOT
    write_json(wrapper_path, wrapper)
    expect_reject(root, fixture, "不是同一文件")
    wrapper["target"]["as_of_block"] = LIVE_SLOT
    write_json(wrapper_path, wrapper)
    print("GREEN N4 静态态仍走原 holders_owners 同文件绑定")


def test_n5_handoff_required_frozen_bundle(root: Path, fixture):
    exact = fixture["fake_check"](
        root, "exact_reconcile", {}, fixture["target"], "solana")
    exact_path = fixture["dummy_exact"].relative_to(root).as_posix()
    exact_input = fixture["frozen_owners"].relative_to(root).as_posix()
    write_json(root / "candidate_universe.json", {
        "candidates": [{"id": "c1", "address": "owner-a", "reasons": ["fixture"]}],
    })
    write_json(root / "anomalies.json", [])
    write_json(root / "data_map.json", {
        "files": [{"path": exact_path}, {"path": exact_input}],
    })
    write_json(root / "wave_scan_report.json", {
        "schema": "wave-scan/v5", "edge_order_granularity": "transaction",
        "order_ambiguous": True, "non_formal": False, "waves": [],
        "equal_amount_groups": [], "requires_adjudication": False,
        "scan_universe": [], "scan_universe_count": 0, "must_adjudicate_count": 0,
    })
    write_json(root / "flow_anomaly_report.json", {
        "schema": "flow-anomaly/v3", "sinks": [], "sprays": [],
        "requires_adjudication": False,
    })
    manifest = {
        "scope": {"chains": ["solana"], "contract": MINT},
        "artifacts": [{"path": exact_path}, {"path": exact_input}],
    }
    fails = []
    originals = (
        handoff_manifest.validate_reconciliation_report,
        handoff_manifest.validate_solana_derived_bindings,
        handoff_manifest.validate_accounting_receipt,
        handoff_manifest.validate_evm_observation_source_chain,
        handoff_manifest.subprocess.run,
    )

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    try:
        handoff_manifest.validate_reconciliation_report = lambda *_a, **_k: (
            fixture["target"], {"exact_reconcile": exact, "supply_truth": {}})
        handoff_manifest.validate_solana_derived_bindings = lambda *_a, **_k: None
        handoff_manifest.validate_accounting_receipt = lambda *_a, **_k: (
            fixture["target"], {}, None)
        handoff_manifest.validate_evm_observation_source_chain = lambda *_a, **_k: None
        handoff_manifest.subprocess.run = lambda *_a, **_k: Completed()
        handoff_manifest._verify_light_schema(root, fails, manifest, legacy=False)
    finally:
        (handoff_manifest.validate_reconciliation_report,
         handoff_manifest.validate_solana_derived_bindings,
         handoff_manifest.validate_accounting_receipt,
         handoff_manifest.validate_evm_observation_source_chain,
         handoff_manifest.subprocess.run) = originals
    assert any(FROZEN_BUNDLE in failure and "data_map" in failure
               and "artifacts" in failure for failure in fails), fails
    print("GREEN N5 handoff READY 深验要求 frozen bundle 同进 data_map/artifacts")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    r1_only = argv == ["--r1"]
    if argv and not r1_only:
        raise SystemExit("usage: test_batch11_frozen_bundle_binding.py [--r1]")
    with tempfile.TemporaryDirectory(prefix="batch11-frozen-", dir="/private/tmp") as raw:
        root = Path(raw)
        fixture = build_case(root)
        try:
            test_r1_dynamic_hash_binding(root, fixture)
            if not r1_only:
                test_n1_n2_n3_n4(root, fixture)
                test_n5_handoff_required_frozen_bundle(root, fixture)
        except Exception as exc:
            print(f"FAIL batch11: {type(exc).__name__}: {exc}")
            return 1
    print("PASS batch11 frozen/live binding regressions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
