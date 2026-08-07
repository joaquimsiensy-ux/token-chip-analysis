#!/usr/bin/env python3
"""Backward-compatible immutable registry context for formal-path fixtures.

Batch 3 production facts now make the four verified chains ready.  Older tests
still enter this restoring context; it copies the registry without adding a
production override and preserves the three read-only layers.
"""
from __future__ import annotations

import os
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from types import MappingProxyType

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "scripts/lib"
REPORT = ROOT / "scripts/report"


def _readonly_registry(records):
    return MappingProxyType({
        name: MappingProxyType({
            **record,
            "capabilities": MappingProxyType(dict(record["capabilities"])),
        })
        for name, record in records.items()
    })


@contextmanager
def test_vertical_slices():
    """Temporarily satisfy fixture slices and restore the exact registry object."""
    sys.path[:0] = [str(LIB), str(REPORT)]
    import chain_registry

    patched = {}
    for name, record in chain_registry.CHAIN_REGISTRY.items():
        item = dict(record)
        item["capabilities"] = dict(record["capabilities"])
        if item["release_tier"] == "formal":
            item["capabilities"]["vertical_slice_verified"] = True
        patched[name] = item
    original = chain_registry.CHAIN_REGISTRY
    chain_registry.CHAIN_REGISTRY = _readonly_registry(patched)
    try:
        yield chain_registry
    finally:
        chain_registry.CHAIN_REGISTRY = original


def fixture_missing_formal_capabilities(record):
    """Explicit test-only record injection; production public APIs reject mappings."""
    import chain_registry
    return chain_registry._missing_formal_capabilities_from_record(record)


def run_formal_script(script, args, *, env=None):
    """Run a CLI after test-only activation, without a production bypass flag."""
    harness = """
import runpy, sys
sys.path.insert(0, sys.argv.pop(1))
from formal_ready_test_harness import test_vertical_slices
script = sys.argv.pop(1)
sys.argv = [script] + sys.argv[1:]
with test_vertical_slices():
    runpy.run_path(script, run_name="__main__")
"""
    child_env = os.environ.copy()
    if env:
        child_env.update(env)
    child_env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    return subprocess.run(
        [sys.executable, "-c", harness, str(Path(__file__).resolve().parent),
         str(Path(script).resolve()), *args],
        capture_output=True, text=True, env=child_env)
