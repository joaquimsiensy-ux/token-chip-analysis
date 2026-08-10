#!/usr/bin/env python3
"""R9-05 B2-G1: chain-attestation keys must resolve to real factories."""
from __future__ import annotations

import sys
from pathlib import Path
from types import MappingProxyType


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts/lib"), str(ROOT / "scripts/tests")]

import chain_registry  # noqa: E402
from chain_registry import CHAIN_REGISTRY  # noqa: E402
from formal_ready_test_harness import (fixture_missing_formal_capabilities,
                                       test_vertical_slices)  # noqa: E402


def mutable_record(chain):
    record = CHAIN_REGISTRY[chain]
    return {**record, "capabilities": dict(record["capabilities"])}


def test_registered_factories_are_callable():
    from attestation_adapters import resolve_attestation_adapter

    evm = resolve_attestation_adapter("evm-chain-id")
    solana = resolve_attestation_adapter("solana-cluster")
    assert callable(evm) and evm.__name__ == "attested_rpc_pool"
    assert callable(solana) and solana.__name__ == "SolanaAttestedSession"


def test_missing_or_unknown_factory_blocks_capability():
    for chain in ("eth", "sol"):
        missing = mutable_record(chain)
        missing["capabilities"]["chain_attestation"] = None
        assert "chain_attestation" in fixture_missing_formal_capabilities(missing)

        forged = mutable_record(chain)
        forged["capabilities"]["chain_attestation"] = "does-not-exist"
        assert "chain_attestation" in fixture_missing_formal_capabilities(forged), (
            chain, "unresolvable declaration was accepted as executable capability")


def test_unknown_adapter_resolution_raises():
    from attestation_adapters import resolve_attestation_adapter

    try:
        resolve_attestation_adapter("does-not-exist")
    except LookupError:
        pass
    else:
        raise AssertionError("unknown adapter key did not raise")

    try:
        resolve_attestation_adapter(
            "broken", registry={"broken": "missing_factory_module:factory"})
    except ImportError:
        pass
    else:
        raise AssertionError("registered missing factory did not raise")


def _readonly_registry_with(chain, attestation):
    records = {}
    for name, record in chain_registry.CHAIN_REGISTRY.items():
        item = dict(record)
        capabilities = dict(record["capabilities"])
        if name == chain:
            capabilities["chain_attestation"] = attestation
        item["capabilities"] = MappingProxyType(capabilities)
        records[name] = MappingProxyType(item)
    return MappingProxyType(records)


def test_each_formal_chain_drops_from_ready_after_key_damage():
    with test_vertical_slices():
        original = chain_registry.CHAIN_REGISTRY
        for chain in sorted(chain_registry.formal_tier_chains()):
            assert chain_registry.formal_ready(chain), chain
            for damaged in (None, "does-not-exist"):
                chain_registry.CHAIN_REGISTRY = _readonly_registry_with(chain, damaged)
                try:
                    assert not chain_registry.formal_ready(chain), (chain, damaged)
                finally:
                    chain_registry.CHAIN_REGISTRY = original


def main():
    test_registered_factories_are_callable()
    test_missing_or_unknown_factory_blocks_capability()
    test_unknown_adapter_resolution_raises()
    test_each_formal_chain_drops_from_ready_after_key_damage()
    print("PASS R9 B2-G1: attestation keys resolve to callable factories")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
