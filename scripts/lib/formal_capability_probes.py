#!/usr/bin/env python3
"""Executable probes that derive formal chain readiness.

Each matrix key resolves to live callables.  Test-backed capabilities also
require their test file to be mounted in ``scripts/tests/run_all.py``.  R9
batch 3 registers the four real vertical-slice targets; removing a target or
its mounted test makes the corresponding chain not ready.
"""
from __future__ import annotations

import ast
import functools
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
    "evm-accounting-supply-v2": (
        "scripts.evm.observe_supply:main",
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
VERTICAL_EVIDENCE_CHAINS = MappingProxyType({
    "r9-eth-mainnet-vertical-slice": "eth",
    "r9-bsc-mainnet-vertical-slice": "bsc",
    "r9-base-mainnet-vertical-slice": "base",
    "r9-solana-pythia-mainnet-vertical-slice": "sol",
})


def run_attestation_negative_probe(chain):
    """Exercise the registered identity adapter against a wrong-chain fake.

    This is deliberately transport-only and runs before every formal evidence
    target.  A mismatch must stop at identity attestation with zero business
    calls; no external endpoint is contacted.
    """
    import chain_registry

    record = chain_registry.CHAIN_REGISTRY[chain]
    key = record["capabilities"]["chain_attestation"]
    factory = resolve_attestation_adapter(key)
    calls = []
    if record.get("capture_evm_family"):
        from unittest import mock
        import net

        async def wrong_chain(_client, _bucket, _method, _url, *, json_body=None,
                              attempts=6):
            calls.append(json_body["method"])
            if json_body["method"] != "eth_chainId":
                raise AssertionError("business RPC reached after wrong chain id")
            return {"jsonrpc": "2.0", "id": 1, "result": "0x7fffffff"}

        with mock.patch.object(net, "_request_json", side_effect=wrong_chain):
            pool = factory("http://wrong-chain.invalid", chain, formal=True,
                           attempts=1, rps=1000)
            try:
                pool.call("eth_blockNumber", [])
            except net.RpcChainMismatch:
                pass
            else:
                raise AssertionError(f"{chain}: wrong chain id was accepted")
        if calls != ["eth_chainId"]:
            raise AssertionError(f"{chain}: wrong-chain probe calls={calls}")
        return {"chain": chain, "adapter": key, "calls": tuple(calls)}

    from solana_attested_session import SolanaRpcError

    def wrong_genesis(_endpoint, payload, _timeout):
        calls.append(payload["method"])
        if payload["method"] != "getGenesisHash":
            raise AssertionError("business RPC reached after wrong genesis")
        return {"result": "wrong-genesis"}

    session = factory("wrong-genesis.invalid", request_json=wrong_genesis)
    try:
        session.call("getBalance", ["address"])
    except SolanaRpcError:
        pass
    else:
        raise AssertionError(f"{chain}: wrong genesis was accepted")
    if calls != ["getGenesisHash"]:
        raise AssertionError(f"{chain}: wrong-genesis probe calls={calls}")
    return {"chain": chain, "adapter": key, "calls": tuple(calls)}


def formal_evidence_target(chain):
    """Make the attestation negative probe a mandatory prelude to one target."""
    if chain not in set(VERTICAL_EVIDENCE_CHAINS.values()):
        raise ValueError(f"unknown formal evidence chain: {chain!r}")

    def decorate(function):
        @functools.wraps(function)
        def guarded(*args, **kwargs):
            run_attestation_negative_probe(chain)
            return function(*args, **kwargs)

        guarded.__formal_evidence_chain__ = chain
        return guarded
    return decorate


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
    resolved = tuple(_resolve_target(target) for target in targets)
    if capability == "vertical_slice_evidence":
        expected_chain = VERTICAL_EVIDENCE_CHAINS.get(key)
        if expected_chain is None:
            raise LookupError(f"vertical evidence key has no chain contract: {key!r}")
        for implementation in resolved:
            if getattr(implementation, "__formal_evidence_chain__", None) != expected_chain:
                raise TypeError(
                    f"vertical evidence target does not execute the {expected_chain} "
                    "attestation contract")
    return resolved


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
