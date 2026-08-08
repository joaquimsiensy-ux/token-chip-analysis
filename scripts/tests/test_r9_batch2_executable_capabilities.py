#!/usr/bin/env python3
"""R9-05 B2-G2: formal readiness is six executable probes, not declarations."""
from __future__ import annotations

import sys
from pathlib import Path
from types import MappingProxyType


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts/lib"), str(ROOT / "scripts/tests")]

import chain_registry  # noqa: E402
from formal_ready_test_harness import fixture_missing_formal_capabilities  # noqa: E402


EXPECTED = frozenset({
    "chain_attestation",
    "freeze_target_adapter",
    "accounting_supply_adapter",
    "vertical_slice_evidence",
    "wrong_chain_test",
    "failure_artifact_gate",
})


def mutable_record(chain):
    record = chain_registry.CHAIN_REGISTRY[chain]
    return {**record, "capabilities": dict(record["capabilities"])}


def test_exact_six_capabilities_and_natural_not_ready():
    assert chain_registry.REQUIRED_FORMAL_CAPABILITIES == EXPECTED
    assert chain_registry.formal_tier_chains() == {"eth", "bsc", "base", "sol"}
    assert chain_registry.formal_ready_chains() == {"eth", "bsc", "base", "sol"}
    for chain in sorted(chain_registry.formal_tier_chains()):
        assert chain_registry.missing_formal_capabilities(chain) == (), chain


def test_deleting_one_evidence_target_drops_only_its_chain():
    import formal_capability_probes

    original = formal_capability_probes.VERTICAL_SLICE_EVIDENCE_TARGETS
    key_to_chain = {
        "r9-eth-mainnet-vertical-slice": "eth",
        "r9-bsc-mainnet-vertical-slice": "bsc",
        "r9-base-mainnet-vertical-slice": "base",
        "r9-solana-pythia-mainnet-vertical-slice": "sol",
    }
    try:
        for key, chain in key_to_chain.items():
            formal_capability_probes.VERTICAL_SLICE_EVIDENCE_TARGETS = MappingProxyType(
                {name: targets for name, targets in original.items() if name != key})
            assert chain_registry.formal_ready_chains() \
                == {"eth", "bsc", "base", "sol"} - {chain}
    finally:
        formal_capability_probes.VERTICAL_SLICE_EVIDENCE_TARGETS = original


def test_five_non_slice_probes_resolve_to_callables():
    from formal_capability_probes import resolve_formal_capability

    for chain in sorted(chain_registry.formal_tier_chains()):
        record = chain_registry.CHAIN_REGISTRY[chain]
        for capability in sorted(EXPECTED - {"vertical_slice_evidence"}):
            resolved = resolve_formal_capability(record, capability)
            assert resolved and all(callable(item) for item in resolved), (
                chain, capability, resolved)


def test_bool_vertical_slice_claim_does_not_satisfy_probe():
    forged = mutable_record("eth")
    forged["capabilities"]["vertical_slice_evidence"] = True
    forged["capabilities"]["vertical_slice_verified"] = True
    missing = fixture_missing_formal_capabilities(forged)
    assert "vertical_slice_evidence" in missing, missing


def test_unknown_probe_key_is_missing_not_truthy():
    for capability in EXPECTED:
        forged = mutable_record("eth")
        forged["capabilities"][capability] = "does-not-exist"
        assert capability in fixture_missing_formal_capabilities(forged), capability


def main():
    test_exact_six_capabilities_and_natural_not_ready()
    test_deleting_one_evidence_target_drops_only_its_chain()
    test_five_non_slice_probes_resolve_to_callables()
    test_bool_vertical_slice_claim_does_not_satisfy_probe()
    test_unknown_probe_key_is_missing_not_truthy()
    print("PASS R9 B3-G3/G4: six probes ready; deleting one slice drops its chain")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
