#!/usr/bin/env python3
"""R9-05 B2-G2: formal readiness is six executable probes, not declarations."""
from __future__ import annotations

import ast
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


def test_evm_accounting_supply_v2_resolves_observation_producer():
    import formal_capability_probes

    key = "evm-accounting-supply-v2"
    assert formal_capability_probes.ACCOUNTING_SUPPLY_ADAPTER_TARGETS[key] == (
        "scripts.evm.observe_supply:main",
        "scripts.evm.accounting_gate:main",
        "scripts.lib.supply_truth_gate:main",
    )
    for chain in ("eth", "bsc", "base"):
        assert chain_registry.CHAIN_REGISTRY[chain]["capabilities"][
            "accounting_supply_adapter"] == key


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


def test_solana_evidence_function_has_no_same_named_shadow():
    import formal_capability_probes

    target = formal_capability_probes.VERTICAL_SLICE_EVIDENCE_TARGETS[
        "r9-solana-pythia-mainnet-vertical-slice"][0]
    _module, function = target.split(":", 1)
    shadow_path = ROOT / "scripts/tests/test_r9_batch3_solana_observation.py"
    tree = ast.parse(shadow_path.read_text(encoding="utf-8"))
    defined = {node.name for node in ast.walk(tree)
               if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert function not in defined, (
        f"registered evidence function {function} is shadowed by {shadow_path.name}")


def test_unrelated_callable_cannot_replace_vertical_evidence():
    """R9-B4-CAP-01: importable/callable is not executable chain evidence."""
    import formal_capability_probes

    original = formal_capability_probes.VERTICAL_SLICE_EVIDENCE_TARGETS
    try:
        forged = dict(original)
        forged["r9-eth-mainnet-vertical-slice"] = (
            "scripts.lib.endpoint_identity:public_endpoint",)
        formal_capability_probes.VERTICAL_SLICE_EVIDENCE_TARGETS = MappingProxyType(forged)
        assert "eth" not in chain_registry.formal_ready_chains(), (
            "unrelated helper was accepted as executable vertical evidence")
    finally:
        formal_capability_probes.VERTICAL_SLICE_EVIDENCE_TARGETS = original


def test_each_formal_target_executes_registered_wrong_identity_probe():
    from formal_capability_probes import run_attestation_negative_probe

    for chain in sorted(chain_registry.formal_tier_chains()):
        evidence = run_attestation_negative_probe(chain)
        assert evidence["chain"] == chain
        expected = "getGenesisHash" if chain == "sol" else "eth_chainId"
        assert evidence["calls"] == (expected,), evidence


def main():
    test_exact_six_capabilities_and_natural_not_ready()
    test_deleting_one_evidence_target_drops_only_its_chain()
    test_five_non_slice_probes_resolve_to_callables()
    test_evm_accounting_supply_v2_resolves_observation_producer()
    test_bool_vertical_slice_claim_does_not_satisfy_probe()
    test_unknown_probe_key_is_missing_not_truthy()
    test_solana_evidence_function_has_no_same_named_shadow()
    test_unrelated_callable_cannot_replace_vertical_evidence()
    test_each_formal_target_executes_registered_wrong_identity_probe()
    print("PASS R9 B3-G3/G4: six probes ready; deleting one slice drops its chain")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
