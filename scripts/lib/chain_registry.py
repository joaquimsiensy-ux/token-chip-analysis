#!/usr/bin/env python3
"""Immutable chain release tiers and executable capability facts.

``release_tier`` expresses policy intent.  It is not a readiness switch.
``formal_ready`` is derived from the complete capability closure below; Batch 2
deliberately leaves ``vertical_slice_verified`` false for every chain.
"""
from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType


RELEASE_TIERS = frozenset({"formal", "exploration", "unsupported"})
REQUIRED_FORMAL_CAPABILITIES = frozenset({
    "accounting_adapter",
    "balance_producer",
    "supply_producer",
    "time_producer",
    "controlled_runner",
    "reconciliation_consumer",
    "identity_adapter",
    "labels_table",
    "handoff",
    "audit_release",
    "chain_attestation",
    "vertical_slice_verified",
})


def _capabilities(**overrides):
    facts = {
        "accounting_adapter": None,
        "balance_producer": False,
        "supply_producer": False,
        "time_producer": False,
        "controlled_runner": False,
        "reconciliation_consumer": False,
        "identity_adapter": None,
        "labels_table": False,
        "handoff": False,
        "audit_release": False,
        "chain_attestation": None,
        "vertical_slice_verified": False,
    }
    facts.update(overrides)
    if set(facts) != REQUIRED_FORMAL_CAPABILITIES:
        raise ValueError("invalid capability fact set")
    return MappingProxyType(facts)


def _record(canonical, *, aliases=(), release_tier="unsupported",
            capture_evm_family=False, evm_chain_id=None, **capabilities):
    if release_tier not in RELEASE_TIERS:
        raise ValueError(f"invalid release tier: {release_tier}")
    return MappingProxyType({
        "canonical": canonical,
        "aliases": tuple(aliases),
        "release_tier": release_tier,
        "capture_evm_family": bool(capture_evm_family),
        "evm_chain_id": evm_chain_id,
        "capabilities": _capabilities(**capabilities),
    })


_FORMAL_EVM = dict(
    release_tier="formal", capture_evm_family=True,
    accounting_adapter="evm", balance_producer=True, supply_producer=True,
    time_producer=True, controlled_runner=True,
    reconciliation_consumer=True, identity_adapter="evm", labels_table=True,
    handoff=True, audit_release=True, chain_attestation="evm-chain-id",
)


CHAIN_REGISTRY = MappingProxyType({
    "eth": _record("eth", aliases=("ethereum",), evm_chain_id=1, **_FORMAL_EVM),
    "bsc": _record("bsc", evm_chain_id=56, **_FORMAL_EVM),
    "base": _record("base", evm_chain_id=8453, **_FORMAL_EVM),
    "arbitrum": _record(
        "arbitrum", aliases=("arbitrum one", "arbitrum-one", "arb"),
        release_tier="exploration", capture_evm_family=True,
        evm_chain_id=42161, accounting_adapter="evm", balance_producer=True,
        supply_producer=True, time_producer=True, controlled_runner=True,
        reconciliation_consumer=True, identity_adapter="evm", labels_table=False,
        handoff=False, audit_release=False, chain_attestation="evm-chain-id",
    ),
    "polygon": _record(
        "polygon", capture_evm_family=True, accounting_adapter="evm",
        reconciliation_consumer=True,
    ),
    "optimism": _record(
        "optimism", capture_evm_family=True, accounting_adapter="evm",
        reconciliation_consumer=True,
    ),
    "robinhood": _record(
        "robinhood", release_tier="exploration", capture_evm_family=True,
        evm_chain_id=None, accounting_adapter="robinhood",
        identity_adapter="evm", labels_table=True,
    ),
    "opbnb": _record(
        "opbnb", capture_evm_family=True, accounting_adapter="evm",
        reconciliation_consumer=True,
    ),
    "avalanche": _record(
        "avalanche", capture_evm_family=True, accounting_adapter="evm",
        reconciliation_consumer=True,
    ),
    "fantom": _record(
        "fantom", capture_evm_family=True, accounting_adapter="evm",
        reconciliation_consumer=True,
    ),
    "cronos": _record(
        "cronos", capture_evm_family=True, accounting_adapter="evm",
        reconciliation_consumer=True,
    ),
    "linea": _record(
        "linea", capture_evm_family=True, accounting_adapter="evm",
        reconciliation_consumer=True,
    ),
    "scroll": _record(
        "scroll", capture_evm_family=True, accounting_adapter="evm",
        reconciliation_consumer=True,
    ),
    "blast": _record(
        "blast", capture_evm_family=True, accounting_adapter="evm",
        reconciliation_consumer=True,
    ),
    "zksync": _record(
        "zksync", capture_evm_family=True, accounting_adapter="evm",
        reconciliation_consumer=True,
    ),
    "sol": _record(
        "sol", aliases=("solana",), release_tier="formal",
        accounting_adapter="solana", balance_producer=True, supply_producer=True,
        time_producer=True, controlled_runner=True,
        reconciliation_consumer=True, identity_adapter="solana", labels_table=True,
        handoff=True, audit_release=True, chain_attestation="solana-cluster",
    ),
})


def _validate_registry():
    aliases = {}
    required = {
        "canonical", "aliases", "release_tier", "capture_evm_family",
        "evm_chain_id", "capabilities",
    }
    for key, record in CHAIN_REGISTRY.items():
        if set(record) != required or record["canonical"] != key:
            raise ValueError(f"invalid chain registry record: {key}")
        if record["release_tier"] not in RELEASE_TIERS:
            raise ValueError(f"invalid release tier: {key}")
        if set(record["capabilities"]) != REQUIRED_FORMAL_CAPABILITIES:
            raise ValueError(f"invalid capability facts: {key}")
        for raw in (key, *record["aliases"]):
            alias = str(raw).strip().lower()
            if alias in aliases and aliases[alias] != key:
                raise ValueError(f"duplicate chain alias: {alias}")
            aliases[alias] = key
    return MappingProxyType(aliases)


_ALIASES = _validate_registry()


def resolve_alias(value):
    normalized = str(value or "").strip().lower()
    return _ALIASES.get(normalized, normalized)


def get_chain_config(value):
    return CHAIN_REGISTRY.get(resolve_alias(value))


def release_tier_for(value):
    record = get_chain_config(value)
    return record.get("release_tier") if record else None


def _record_from(value):
    if isinstance(value, Mapping):
        return value
    return get_chain_config(value)


def missing_formal_capabilities(value):
    record = _record_from(value)
    if not isinstance(record, Mapping):
        return ("registry_record",)
    missing = []
    if record.get("release_tier") != "formal":
        missing.append("release_tier")
    facts = record.get("capabilities")
    if not isinstance(facts, Mapping):
        return tuple(missing + ["capabilities"])
    missing.extend(sorted(key for key in REQUIRED_FORMAL_CAPABILITIES
                          if not facts.get(key)))
    if record.get("capture_evm_family") and record.get("evm_chain_id") is None:
        missing.append("evm_chain_id")
    return tuple(missing)


def record_is_formal_ready(record):
    return not missing_formal_capabilities(record)


def formal_ready(value):
    return record_is_formal_ready(get_chain_config(value))


def formal_tier_chains():
    return {key for key, record in CHAIN_REGISTRY.items()
            if record["release_tier"] == "formal"}


def formal_ready_chains():
    return {key for key in CHAIN_REGISTRY if formal_ready(key)}


def formal_chains():
    """Backward-compatible name: formal means executable readiness, not intent."""
    return formal_ready_chains()


def known_chains_for_release():
    return {key for key, record in CHAIN_REGISTRY.items()
            if record["release_tier"] in {"formal", "exploration"}}


def capability_chains(name, *, release_tiers=None):
    if name not in REQUIRED_FORMAL_CAPABILITIES:
        raise ValueError(f"unknown capability: {name}")
    tiers = set(release_tiers or RELEASE_TIERS)
    return {key for key, record in CHAIN_REGISTRY.items()
            if record["release_tier"] in tiers and record["capabilities"].get(name)}


def formal_evm_chains(capability):
    return {key for key in capability_chains(capability, release_tiers={"formal"})
            if CHAIN_REGISTRY[key]["capture_evm_family"]
            and CHAIN_REGISTRY[key]["evm_chain_id"] is not None}


def formal_reconciliation_chains(kind):
    fact = {"balance": "balance_producer", "supply": "supply_producer",
            "time": "time_producer"}.get(kind)
    if fact is None:
        raise ValueError(f"unknown reconciliation producer kind: {kind}")
    return capability_chains(fact, release_tiers={"formal"})


def attested_evm_chains():
    return {key for key, record in CHAIN_REGISTRY.items()
            if record["capture_evm_family"]
            and record["evm_chain_id"] is not None
            and record["capabilities"].get("chain_attestation")}


def evm_family():
    return {key for key, record in CHAIN_REGISTRY.items()
            if record["capture_evm_family"]}


def identity_evm_chains():
    return {key for key, record in CHAIN_REGISTRY.items()
            if record["capabilities"].get("identity_adapter") == "evm"}


def identity_chains():
    return {key for key, record in CHAIN_REGISTRY.items()
            if record["capabilities"].get("identity_adapter") is not None}


def recon_adapter_for(value):
    record = get_chain_config(value)
    return record["capabilities"].get("accounting_adapter") if record else None


def evm_chain_id_for(value):
    record = get_chain_config(value)
    return record.get("evm_chain_id") if record else None
