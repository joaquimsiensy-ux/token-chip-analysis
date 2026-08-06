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

from chain_registry import (CHAIN_REGISTRY, evm_family, formal_chains, identity_chains,
                            identity_evm_chains, known_chains_for_release,
                            recon_adapter_for, resolve_alias)


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
        "canonical", "aliases", "formal", "exploration", "capture_evm_family",
        "has_labels_table", "recon_adapter", "identity_adapter",
    }
    assert CHAIN_REGISTRY and all(set(record) == expected_fields
                                  for record in CHAIN_REGISTRY.values())
    assert formal_chains() == {"eth", "bsc", "base", "robinhood", "sol"}
    assert known_chains_for_release() == formal_chains() | {"arbitrum"}
    assert CHAIN_REGISTRY["arbitrum"]["exploration"] is True
    assert CHAIN_REGISTRY["arbitrum"]["formal"] is False
    assert {"eth", "bsc", "base", "arbitrum", "polygon", "robinhood"} <= evm_family()
    assert "sol" not in evm_family()
    assert identity_evm_chains() == {"eth", "bsc", "base", "arbitrum", "robinhood"}
    assert identity_chains() == identity_evm_chains() | {"sol"}
    assert resolve_alias("Ethereum") == "eth"
    assert resolve_alias("solana") == "sol"
    assert resolve_alias("Arbitrum-One") == "arbitrum"

    audit = load(ROOT / "scripts/report/audit_release_gate.py", "registry_audit")
    handoff = load(ROOT / "scripts/report/handoff_manifest.py", "registry_handoff")
    identity_receipt = load(
        ROOT / "scripts/report/identity_snapshot_receipt.py", "registry_identity_receipt")
    identity_gate = load(
        ROOT / "scripts/report/entity_identity_gate.py", "registry_identity_gate")
    shared_receipt = load(
        ROOT / "scripts/report/shared_release_receipt.py", "registry_shared_receipt")
    assert audit.formal_chains() == formal_chains()
    assert handoff.READY_CHAINS == formal_chains()
    assert identity_receipt.identity_evm_chains() == identity_evm_chains()
    assert identity_receipt.identity_chains() == identity_chains()
    assert identity_gate.identity_chains() == identity_chains()
    assert shared_receipt.chain_family("solana") == recon_adapter_for("sol") == "solana"
    assert shared_receipt.chain_family("arbitrum") == recon_adapter_for("arbitrum") == "evm"

    original = CHAIN_REGISTRY["polygon"]["identity_adapter"]
    try:
        CHAIN_REGISTRY["polygon"]["identity_adapter"] = "evm"
        assert "polygon" in identity_receipt.identity_evm_chains()
        assert "polygon" in identity_receipt.identity_chains()
        assert "polygon" in identity_gate.identity_chains()
    finally:
        CHAIN_REGISTRY["polygon"]["identity_adapter"] = original

    original_recon = CHAIN_REGISTRY["polygon"]["recon_adapter"]
    try:
        CHAIN_REGISTRY["polygon"]["recon_adapter"] = "solana"
        assert shared_receipt.chain_family("polygon") == "solana"
    finally:
        CHAIN_REGISTRY["polygon"]["recon_adapter"] = original_recon

    forbidden = re.compile(r"^(?:FORMAL_CHAINS|KNOWN_CHAINS|EVM_CHAINS|CHAIN_ALIASES)\s*=", re.M)
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

    print("PASS: chain registry drives audit/handoff/identity consumers; mutation propagates; "
          "DEFAULT_RPC keys registered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
