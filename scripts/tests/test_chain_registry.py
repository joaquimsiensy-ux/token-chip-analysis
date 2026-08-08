#!/usr/bin/env python3
"""Chain capability registry is the only release/handoff chain source."""
from __future__ import annotations

import ast
import importlib.util
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/lib"))
sys.path.insert(0, str(ROOT / "scripts/report"))

from chain_registry import (ALL_CAPABILITY_FIELDS, CHAIN_REGISTRY,
                            REQUIRED_FORMAL_CAPABILITIES, evm_family,
                            formal_chains, formal_ready_chains, formal_tier_chains,
                            identity_chains, identity_evm_chains, known_chains_for_release,
                            recon_adapter_for, release_tier_for,
                            resolve_alias, evm_chain_id_for)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def literal_dict_keys(path, name):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return set(ast.literal_eval(node.value))
    raise AssertionError(f"{path.relative_to(ROOT)} lacks literal dict {name}")


def main():
    expected_fields = {
        "canonical", "aliases", "release_tier", "capture_evm_family",
        "evm_chain_id", "capabilities",
    }
    assert CHAIN_REGISTRY and all(set(record) == expected_fields
                                  for record in CHAIN_REGISTRY.values())
    assert all(set(record["capabilities"]) == ALL_CAPABILITY_FIELDS
               for record in CHAIN_REGISTRY.values())
    assert formal_tier_chains() == {"eth", "bsc", "base", "sol"}
    assert formal_ready_chains() == formal_chains() == set()
    assert known_chains_for_release() == formal_tier_chains() | {"arbitrum", "robinhood"}
    assert release_tier_for("arbitrum") == "exploration"
    assert release_tier_for("robinhood") == "exploration"
    assert {"eth", "bsc", "base", "arbitrum", "polygon", "robinhood"} <= evm_family()
    assert "sol" not in evm_family()
    assert identity_evm_chains() == {"eth", "bsc", "base", "arbitrum", "robinhood"}
    assert identity_chains() == identity_evm_chains() | {"sol"}
    assert resolve_alias("Ethereum") == "eth"
    assert resolve_alias("solana") == "sol"
    assert resolve_alias("Arbitrum-One") == "arbitrum"
    assert {chain: evm_chain_id_for(chain) for chain in ("eth", "bsc", "base", "arbitrum")} == {
        "eth": 1, "bsc": 56, "base": 8453, "arbitrum": 42161}

    audit = load(ROOT / "scripts/report/audit_release_gate.py", "registry_audit")
    handoff = load(ROOT / "scripts/report/handoff_manifest.py", "registry_handoff")
    identity_receipt = load(
        ROOT / "scripts/report/identity_snapshot_receipt.py", "registry_identity_receipt")
    identity_gate = load(
        ROOT / "scripts/report/entity_identity_gate.py", "registry_identity_gate")
    shared_receipt = load(
        ROOT / "scripts/report/shared_release_receipt.py", "registry_shared_receipt")
    assert handoff.READY_CHAINS == formal_ready_chains() == set()
    assert identity_receipt.identity_evm_chains() == identity_evm_chains()
    assert identity_receipt.identity_chains() == identity_chains()
    assert identity_gate.identity_chains() == identity_chains()
    assert shared_receipt.chain_family("solana") == recon_adapter_for("sol") == "solana"
    assert shared_receipt.chain_family("arbitrum") == recon_adapter_for("arbitrum") == "evm"

    assert audit.formal_chain_error("bsc") is not None
    copied = {**CHAIN_REGISTRY["bsc"],
              "capabilities": dict(CHAIN_REGISTRY["bsc"]["capabilities"])}
    copied["capabilities"]["vertical_slice_evidence"] = True
    from formal_ready_test_harness import (fixture_missing_formal_capabilities,
                                           test_vertical_slices)
    assert "vertical_slice_evidence" in fixture_missing_formal_capabilities(copied)
    with test_vertical_slices():
        assert not fixture_missing_formal_capabilities({
            **CHAIN_REGISTRY["bsc"],
            "capabilities": dict(CHAIN_REGISTRY["bsc"]["capabilities"]),
        })
        assert audit.formal_chain_error("bsc") is None
    try:
        CHAIN_REGISTRY["polygon"] = copied
        raise AssertionError("registry accepted manual assignment")
    except TypeError:
        pass

    forbidden = re.compile(
        r"^(?:FORMAL_CHAINS|KNOWN_CHAINS|EVM_CHAINS|CHAIN_ALIASES)\s*=|\bformal\s*=\s*(?:True|False)",
        re.M)
    for rel in ("scripts/report/audit_release_gate.py", "scripts/report/handoff_manifest.py",
                "scripts/report/identity_snapshot_receipt.py",
                "scripts/report/entity_identity_gate.py"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert not forbidden.search(text), f"local chain capability set remains in {rel}"

    for rel, name in (("scripts/evm/accounting_gate.py", "DEFAULT_RPC"),
                      ("scripts/lib/supply_truth_gate.py", "DEFAULT_RPC")):
        unknown = literal_dict_keys(ROOT / rel, name) - set(CHAIN_REGISTRY)
        # supply_truth uses the public CLI alias; aliases must also resolve to a registry chain.
        unknown = {key for key in unknown if resolve_alias(key) not in CHAIN_REGISTRY}
        assert not unknown, f"{rel} {name} has unregistered chains: {sorted(unknown)}"

    print("PASS: six executable probes drive release/identity consumers; "
          "R9 vertical evidence absent until batch 3; DEFAULT_RPC keys registered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
