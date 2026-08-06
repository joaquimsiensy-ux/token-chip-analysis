#!/usr/bin/env python3
"""Single source of truth for chain capabilities used by release tooling."""
from __future__ import annotations


CHAIN_REGISTRY = {
    "eth": {
        "canonical": "eth", "aliases": ("ethereum",), "formal": True,
        "exploration": False, "capture_evm_family": True,
        "has_labels_table": True, "recon_adapter": "evm",
        "identity_adapter": "evm",
    },
    "bsc": {
        "canonical": "bsc", "aliases": (), "formal": True,
        "exploration": False, "capture_evm_family": True,
        "has_labels_table": True, "recon_adapter": "evm",
        "identity_adapter": "evm",
    },
    "base": {
        "canonical": "base", "aliases": (), "formal": True,
        "exploration": False, "capture_evm_family": True,
        "has_labels_table": True, "recon_adapter": "evm",
        "identity_adapter": "evm",
    },
    "arbitrum": {
        "canonical": "arbitrum",
        "aliases": ("arbitrum one", "arbitrum-one", "arb"),
        "formal": False, "exploration": True, "capture_evm_family": True,
        "has_labels_table": False, "recon_adapter": "evm",
        "identity_adapter": "evm",
    },
    "polygon": {
        "canonical": "polygon", "aliases": (), "formal": False,
        "exploration": False, "capture_evm_family": True,
        "has_labels_table": False, "recon_adapter": "evm",
        "identity_adapter": None,
    },
    "optimism": {
        "canonical": "optimism", "aliases": (), "formal": False,
        "exploration": False, "capture_evm_family": True,
        "has_labels_table": False, "recon_adapter": "evm",
        "identity_adapter": None,
    },
    "robinhood": {
        "canonical": "robinhood", "aliases": (), "formal": True,
        "exploration": False, "capture_evm_family": True,
        "has_labels_table": True, "recon_adapter": "evm",
        "identity_adapter": "evm",
    },
    "opbnb": {
        "canonical": "opbnb", "aliases": (), "formal": False,
        "exploration": False, "capture_evm_family": True,
        "has_labels_table": False, "recon_adapter": "evm",
        "identity_adapter": None,
    },
    "avalanche": {
        "canonical": "avalanche", "aliases": (), "formal": False,
        "exploration": False, "capture_evm_family": True,
        "has_labels_table": False, "recon_adapter": "evm",
        "identity_adapter": None,
    },
    "fantom": {
        "canonical": "fantom", "aliases": (), "formal": False,
        "exploration": False, "capture_evm_family": True,
        "has_labels_table": False, "recon_adapter": "evm",
        "identity_adapter": None,
    },
    "cronos": {
        "canonical": "cronos", "aliases": (), "formal": False,
        "exploration": False, "capture_evm_family": True,
        "has_labels_table": False, "recon_adapter": "evm",
        "identity_adapter": None,
    },
    "linea": {
        "canonical": "linea", "aliases": (), "formal": False,
        "exploration": False, "capture_evm_family": True,
        "has_labels_table": False, "recon_adapter": "evm",
        "identity_adapter": None,
    },
    "scroll": {
        "canonical": "scroll", "aliases": (), "formal": False,
        "exploration": False, "capture_evm_family": True,
        "has_labels_table": False, "recon_adapter": "evm",
        "identity_adapter": None,
    },
    "blast": {
        "canonical": "blast", "aliases": (), "formal": False,
        "exploration": False, "capture_evm_family": True,
        "has_labels_table": False, "recon_adapter": "evm",
        "identity_adapter": None,
    },
    "zksync": {
        "canonical": "zksync", "aliases": (), "formal": False,
        "exploration": False, "capture_evm_family": True,
        "has_labels_table": False, "recon_adapter": "evm",
        "identity_adapter": None,
    },
    "sol": {
        "canonical": "sol", "aliases": ("solana",), "formal": True,
        "exploration": False, "capture_evm_family": False,
        "has_labels_table": True, "recon_adapter": "solana",
        "identity_adapter": "solana",
    },
}


def _alias_index():
    aliases = {}
    required = {
        "canonical", "aliases", "formal", "exploration", "capture_evm_family",
        "has_labels_table", "recon_adapter", "identity_adapter",
    }
    for key, record in CHAIN_REGISTRY.items():
        if set(record) != required or record["canonical"] != key:
            raise ValueError(f"invalid chain registry record: {key}")
        for raw in (key, *record["aliases"]):
            alias = str(raw).strip().lower()
            if alias in aliases and aliases[alias] != key:
                raise ValueError(f"duplicate chain alias: {alias}")
            aliases[alias] = key
    return aliases


_ALIASES = _alias_index()


def formal_chains():
    return {key for key, record in CHAIN_REGISTRY.items() if record["formal"]}


def known_chains_for_release():
    return {
        key for key, record in CHAIN_REGISTRY.items()
        if record["formal"] or record["exploration"]
    }


def evm_family():
    return {
        key for key, record in CHAIN_REGISTRY.items()
        if record["capture_evm_family"]
    }


def identity_evm_chains():
    return {
        key for key, record in CHAIN_REGISTRY.items()
        if record["identity_adapter"] == "evm"
    }


def identity_chains():
    return {
        key for key, record in CHAIN_REGISTRY.items()
        if record["identity_adapter"] is not None
    }


def resolve_alias(value):
    normalized = str(value or "").strip().lower()
    return _ALIASES.get(normalized, normalized)


def recon_adapter_for(value):
    record = CHAIN_REGISTRY.get(resolve_alias(value))
    return record.get("recon_adapter") if record else None
