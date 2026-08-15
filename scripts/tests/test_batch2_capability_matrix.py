#!/usr/bin/env python3
"""B2-D regressions for the derived chain capability matrix."""
from __future__ import annotations

import copy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/lib"))

from chain_registry import (  # noqa: E402
    CHAIN_REGISTRY, RELEASE_TIERS, REQUIRED_FORMAL_CAPABILITIES,
    attested_evm_chains, executable_evm_chains,
    executable_reconciliation_chains, formal_evm_chains, formal_ready,
    formal_ready_chains, formal_reconciliation_chains, formal_tier_chains,
    missing_formal_capabilities, release_tier_for, resolve_execution_mode,
)
from formal_ready_test_harness import (fixture_missing_formal_capabilities,
                                       test_vertical_slices)  # noqa: E402


def mutable_record(chain):
    record = CHAIN_REGISTRY[chain]
    return {**record, "capabilities": dict(record["capabilities"])}


def test_no_manual_formal_switch():
    assert RELEASE_TIERS == frozenset({"formal", "exploration", "unsupported"})
    assert all("formal" not in record and "exploration" not in record
               for record in CHAIN_REGISTRY.values())
    try:
        CHAIN_REGISTRY["eth"]["formal"] = True
    except TypeError:
        pass
    else:
        raise AssertionError("manual formal=True assignment remained possible")


def test_each_missing_capability_blocks_readiness():
    complete = mutable_record("eth")
    with test_vertical_slices():
        assert not fixture_missing_formal_capabilities(complete)
        for key in REQUIRED_FORMAL_CAPABILITIES:
            broken = copy.deepcopy(complete)
            broken["capabilities"][key] = None
            assert key in fixture_missing_formal_capabilities(broken), (key, broken)
        broken = copy.deepcopy(complete)
        broken["evm_chain_id"] = None
        assert "chain_attestation" in fixture_missing_formal_capabilities(broken)


def test_verified_formal_chains_and_choices_are_derived():
    assert formal_tier_chains() == {"eth", "bsc", "base", "sol"}
    assert formal_ready_chains() == {"eth", "bsc", "base", "sol"}
    assert all(formal_ready(chain) for chain in formal_tier_chains())
    assert release_tier_for("robinhood") == "exploration"
    assert CHAIN_REGISTRY["robinhood"]["evm_chain_id"] is None
    assert formal_evm_chains("accounting_adapter") == {"eth", "bsc", "base"}
    assert formal_evm_chains("balance_producer") == {"eth", "bsc", "base"}
    assert formal_evm_chains("time_producer") == {"eth", "bsc", "base"}
    assert formal_reconciliation_chains("supply") == {"eth", "bsc", "base", "sol"}
    assert executable_evm_chains("accounting_adapter") == {
        "eth", "bsc", "base", "arbitrum"}
    assert executable_evm_chains("balance_producer") == {
        "eth", "bsc", "base", "arbitrum"}
    assert executable_evm_chains("time_producer") == {
        "eth", "bsc", "base", "arbitrum"}
    assert executable_reconciliation_chains("supply") == {
        "eth", "bsc", "base", "arbitrum", "sol"}
    assert attested_evm_chains() == {"eth", "bsc", "base", "arbitrum"}


def test_execution_mode_policy_is_centralized():
    assert resolve_execution_mode("bsc", False, "balance") == "formal"
    assert resolve_execution_mode("bsc", True, "balance") == "exploration"
    assert resolve_execution_mode("arbitrum", True, "balance") == "exploration"
    assert resolve_execution_mode("solana", False, "supply") == "formal"
    try:
        resolve_execution_mode("arbitrum", False, "balance")
    except ValueError as exc:
        assert "探索档链必须显式 --exploration" in str(exc), exc
    else:
        raise AssertionError("exploration-tier chain ran without explicit --exploration")


def test_cli_sources_use_matrix_choices():
    expected = {
        "scripts/evm/accounting_gate.py": 'executable_evm_chains("accounting_adapter")',
        "scripts/evm/verify_recon.py": 'executable_evm_chains("balance_producer")',
        "scripts/lib/supply_truth_gate.py": 'executable_reconciliation_chains("supply")',
        "scripts/lib/time_spotcheck.py": 'executable_evm_chains("time_producer")',
    }
    for rel, needle in expected.items():
        source = (ROOT / rel).read_text(encoding="utf-8")
        assert needle in source, f"{rel} does not derive --chain choices from registry"
        assert "resolve_execution_mode(" in source, f"{rel} bypasses centralized mode policy"
    for rel in (
        "scripts/evm/fetch_alchemy.py", "scripts/evm/lp_positions.py",
        "scripts/evm/multicall_balances.py", "scripts/evm/pierce_stake.py",
        "scripts/evm/scan_bloxroute_seg.py", "scripts/lib/rpc_batch.py",
    ):
        source = (ROOT / rel).read_text(encoding="utf-8")
        assert "attested_evm_chains()" in source, rel


def main():
    test_no_manual_formal_switch()
    test_each_missing_capability_blocks_readiness()
    test_verified_formal_chains_and_choices_are_derived()
    test_execution_mode_policy_is_centralized()
    test_cli_sources_use_matrix_choices()
    print("PASS B2-D: immutable release tier + capability closure + derived CLI choices")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
