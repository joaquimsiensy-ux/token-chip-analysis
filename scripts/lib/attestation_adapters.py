#!/usr/bin/env python3
"""Executable chain-attestation adapter registry.

Registry values are import targets, never readiness facts.  Resolution imports
the target and returns the live callable; an unknown key, missing module,
missing attribute, or non-callable target raises instead of satisfying a gate.
"""
from __future__ import annotations

import importlib
from collections.abc import Mapping
from types import MappingProxyType


ATTESTATION_ADAPTER_TARGETS = MappingProxyType({
    "evm-chain-id": "net:attested_rpc_pool",
    "solana-cluster": "solana_attested_session:SolanaAttestedSession",
})


def _resolve_callable(target):
    if not isinstance(target, str) or target.count(":") != 1:
        raise TypeError(f"invalid adapter import target: {target!r}")
    module_name, attribute = target.split(":", 1)
    if not module_name or not attribute:
        raise TypeError(f"invalid adapter import target: {target!r}")
    module = importlib.import_module(module_name)
    factory = getattr(module, attribute)
    if not callable(factory):
        raise TypeError(f"adapter target is not callable: {target}")
    return factory


def resolve_attestation_adapter(key, *, registry=None):
    """Return the imported session factory registered by ``key``.

    ``registry`` is an explicit destructive-test seam; production callers use
    the immutable module registry.
    """
    adapters = ATTESTATION_ADAPTER_TARGETS if registry is None else registry
    if not isinstance(adapters, Mapping):
        raise TypeError("attestation adapter registry must be a mapping")
    if key not in adapters:
        raise LookupError(f"unknown chain-attestation adapter: {key!r}")
    return _resolve_callable(adapters[key])
