#!/usr/bin/env python3
"""B2F-G2 regressions for registry API and reversible immutable test fixtures."""
from __future__ import annotations

import importlib
import inspect
import sys
from pathlib import Path
from types import MappingProxyType


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "scripts/lib"), str(HERE)]

import chain_registry  # noqa: E402
import formal_ready_test_harness as harness  # noqa: E402


def assert_three_layers_read_only(registry):
    assert isinstance(registry, MappingProxyType)
    assert isinstance(registry["eth"], MappingProxyType)
    assert isinstance(registry["eth"]["capabilities"], MappingProxyType)
    for mutate in (
        lambda: registry.__setitem__("fake", registry["eth"]),
        lambda: registry["eth"].__setitem__("release_tier", "exploration"),
        lambda: registry["eth"]["capabilities"].__setitem__(
            "vertical_slice_verified", False),
    ):
        try:
            mutate()
        except (TypeError, AttributeError):
            pass
        else:
            raise AssertionError("patched registry layer remained mutable")


def test_public_record_api_rejects_self_report():
    forged = {"release_tier": "formal", "capabilities": {
        key: True for key in chain_registry.REQUIRED_FORMAL_CAPABILITIES
    }}
    for function in (
        chain_registry.record_is_formal_ready,
        chain_registry.missing_formal_capabilities,
        chain_registry.formal_ready,
    ):
        try:
            function(forged)
        except TypeError:
            pass
        else:
            raise AssertionError(f"{function.__name__} accepted caller-supplied Mapping")


def test_activation_is_reversible_and_immutable():
    assert hasattr(harness, "test_vertical_slices"), "missing reversible fixture context"
    original = chain_registry.CHAIN_REGISTRY
    with harness.test_vertical_slices():
        assert chain_registry.formal_ready_chains() == {"eth", "bsc", "base", "sol"}
        assert_three_layers_read_only(chain_registry.CHAIN_REGISTRY)
    assert chain_registry.CHAIN_REGISTRY is original
    assert chain_registry.formal_ready_chains() == set()
    assert_three_layers_read_only(chain_registry.CHAIN_REGISTRY)


def test_alphabetical_import_does_not_leak_readiness():
    for name in ("test_audit_release_gate", "test_round4_a5_seal"):
        importlib.import_module(name)
    assert chain_registry.formal_ready_chains() == set()


def test_child_bytecode_guard_is_explicit():
    source = inspect.getsource(harness.run_formal_script)
    assert 'child_env.setdefault("PYTHONDONTWRITEBYTECODE", "1")' in source


def main():
    failures = []
    for test in (
        test_public_record_api_rejects_self_report,
        test_activation_is_reversible_and_immutable,
        test_alphabetical_import_does_not_leak_readiness,
        test_child_bytecode_guard_is_explicit,
    ):
        try:
            test()
        except Exception as exc:
            failures.append(f"{test.__name__}: {exc}")
    if failures:
        raise AssertionError("\n".join(failures))
    print("PASS B2F-G2: string-only readiness API + reversible immutable harness")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
