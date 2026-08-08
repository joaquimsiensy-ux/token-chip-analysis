#!/usr/bin/env python3
"""Executable probes that derive formal chain readiness.

Each matrix key resolves to live callables.  Test-backed capabilities also
require their test file to be mounted in ``scripts/tests/run_all.py``.  R9
vertical-slice evidence is intentionally unregistered in batch 2; batch 3 must
add real test targets before an individual chain can become formal-ready.
"""
from __future__ import annotations

import ast
import importlib
import sys
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType

from attestation_adapters import resolve_attestation_adapter


ROOT = Path(__file__).resolve().parents[2]
RUN_ALL = ROOT / "scripts/tests/run_all.py"

FREEZE_TARGET_ADAPTER_TARGETS = MappingProxyType({
    "entity-freeze-v2": ("scripts.report.handoff_manifest:cmd_freeze",),
})
ACCOUNTING_SUPPLY_ADAPTER_TARGETS = MappingProxyType({
    "evm-accounting-supply-v1": (
        "scripts.evm.accounting_gate:main",
        "scripts.lib.supply_truth_gate:main",
    ),
    "solana-accounting-supply-v1": (
        "scripts.solana.accounting_gate_sol:main",
        "scripts.lib.supply_truth_gate:main",
    ),
})
WRONG_CHAIN_TEST_TARGETS = MappingProxyType({
    "evm-chain-id-zero-business-r9": (
        "scripts.tests.test_batch1_rpc_attestation:"
        "test_each_formal_callsite_wrong_chain_zero_business",
    ),
    "solana-genesis-zero-business-r9": (
        "scripts.tests.test_r9_solana_attested_session:"
        "test_wrong_genesis_has_zero_business_calls",
    ),
})
FAILURE_ARTIFACT_GATE_TARGETS = MappingProxyType({
    "formal-failure-artifact-v1": (
        "scripts.lib.receipt_validate:validate_receipt",
        "scripts.report.shared_release_receipt:validate_bundle",
    ),
})

VERTICAL_SLICE_EVIDENCE_TARGETS = MappingProxyType({
    "r9-eth-mainnet-vertical-slice": (
        "scripts.tests.test_batch3_evm_vertical_slice:test_r9_eth_mainnet_vertical_slice",
    ),
    "r9-bsc-mainnet-vertical-slice": (
        "scripts.tests.test_batch3_evm_vertical_slice:test_r9_bsc_mainnet_vertical_slice",
    ),
    "r9-base-mainnet-vertical-slice": (
        "scripts.tests.test_batch3_evm_vertical_slice:test_r9_base_mainnet_vertical_slice",
    ),
    "r9-solana-pythia-mainnet-vertical-slice": (
        "scripts.tests.test_batch3_solana_vertical_slice:"
        "test_r9_solana_pythia_mainnet_vertical_slice",
    ),
})


def _flatten_suite(value):
    if isinstance(value, str):
        return {value}
    if isinstance(value, (list, tuple)):
        found = set()
        for item in value:
            found.update(_flatten_suite(item))
        return found
    return set()


def mounted_suite_tests(path=RUN_ALL):
    tree = ast.parse(Path(path).read_text(encoding="utf-8"), filename=str(path))
    entries = set()
    for node in tree.body:
        value = None
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "SUITE"
                for target in node.targets):
            value = node.value
        elif (isinstance(node, ast.AugAssign)
              and isinstance(node.target, ast.Name)
              and node.target.id == "SUITE"):
            value = node.value
        if value is not None:
            entries.update(_flatten_suite(ast.literal_eval(value)))
    return entries


def _resolve_target(target):
    if not isinstance(target, str) or target.count(":") != 1:
        raise TypeError(f"invalid capability target: {target!r}")
    module_name, attribute = target.split(":", 1)
    if not module_name or not attribute:
        raise TypeError(f"invalid capability target: {target!r}")
    search = [
        str(ROOT), str(ROOT / "scripts/lib"), str(ROOT / "scripts/report"),
        str(ROOT / "scripts/evm"), str(ROOT / "scripts/solana"),
        str(ROOT / "scripts/tests"),
    ]
    original_path = list(sys.path)
    try:
        sys.path[:0] = [item for item in search if item not in sys.path]
        module = importlib.import_module(module_name)
    finally:
        sys.path[:] = original_path
    implementation = getattr(module, attribute)
    if not callable(implementation):
        raise TypeError(f"capability target is not callable: {target}")
    if module_name.startswith("scripts.tests."):
        test_name = module_name.rsplit(".", 1)[-1] + ".py"
        if test_name not in mounted_suite_tests():
            raise LookupError(f"capability test is not mounted in run_all.SUITE: {test_name}")
    return implementation


def _resolve_registry_key(key, registry, capability):
    if not isinstance(key, str) or not key:
        raise TypeError(f"{capability} key must be a non-empty string")
    if key not in registry:
        raise LookupError(f"unknown {capability} key: {key!r}")
    targets = registry[key]
    if not isinstance(targets, tuple) or not targets:
        raise TypeError(f"{capability} target list must be a non-empty tuple")
    return tuple(_resolve_target(target) for target in targets)


def resolve_formal_capability(record, capability):
    """Resolve one chain record capability to its live callable tuple."""
    if not isinstance(record, Mapping):
        raise TypeError("formal capability probe requires a registry record")
    facts = record.get("capabilities")
    if not isinstance(facts, Mapping):
        raise TypeError("registry record lacks capability mapping")
    key = facts.get(capability)
    if capability == "chain_attestation":
        factory = resolve_attestation_adapter(key)
        if record.get("capture_evm_family"):
            chain_id = record.get("evm_chain_id")
            if isinstance(chain_id, bool) or not isinstance(chain_id, int) or chain_id <= 0:
                raise ValueError("EVM chain attestation requires a positive registry chain id")
        return (factory,)
    registries = {
        "freeze_target_adapter": FREEZE_TARGET_ADAPTER_TARGETS,
        "accounting_supply_adapter": ACCOUNTING_SUPPLY_ADAPTER_TARGETS,
        "vertical_slice_evidence": VERTICAL_SLICE_EVIDENCE_TARGETS,
        "wrong_chain_test": WRONG_CHAIN_TEST_TARGETS,
        "failure_artifact_gate": FAILURE_ARTIFACT_GATE_TARGETS,
    }
    if capability not in registries:
        raise LookupError(f"unknown formal capability: {capability!r}")
    return _resolve_registry_key(key, registries[capability], capability)


def missing_executable_capabilities(record, required):
    missing = []
    for capability in sorted(required):
        try:
            resolve_formal_capability(record, capability)
        except (ImportError, AttributeError, LookupError, TypeError, ValueError):
            missing.append(capability)
    return tuple(missing)
