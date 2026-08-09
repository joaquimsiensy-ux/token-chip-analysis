#!/usr/bin/env python3
"""Test-only executable R9 vertical evidence for formal-path fixtures.

Production now registers R9 vertical-slice evidence.  Older formal-path tests
still enter this restoring context to install a deterministic real, mounted
callable set without editing the immutable chain matrix or using a boolean switch.
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


@contextmanager
def test_vertical_slices():
    """Temporarily install real mounted slice callables, then restore exactly."""
    sys.path[:0] = [str(ROOT), str(LIB), str(REPORT)]
    import chain_registry
    import formal_capability_probes

    original = formal_capability_probes.VERTICAL_SLICE_EVIDENCE_TARGETS
    formal_capability_probes.VERTICAL_SLICE_EVIDENCE_TARGETS = MappingProxyType({
        "r9-eth-mainnet-vertical-slice": (
            "scripts.tests.test_batch3_evm_vertical_slice:test_r9_eth_mainnet_vertical_slice",),
        "r9-bsc-mainnet-vertical-slice": (
            "scripts.tests.test_batch3_evm_vertical_slice:test_r9_bsc_mainnet_vertical_slice",),
        "r9-base-mainnet-vertical-slice": (
            "scripts.tests.test_batch3_evm_vertical_slice:test_r9_base_mainnet_vertical_slice",),
        "r9-solana-pythia-mainnet-vertical-slice": (
            "scripts.tests.test_batch3_solana_vertical_slice:"
            "test_r9_solana_pythia_mainnet_vertical_slice",),
    })
    try:
        yield chain_registry
    finally:
        formal_capability_probes.VERTICAL_SLICE_EVIDENCE_TARGETS = original


def fixture_missing_formal_capabilities(record):
    """Explicit test-only record injection; production public APIs reject mappings."""
    import chain_registry
    return chain_registry._missing_formal_capabilities_from_record(record)


def run_formal_script(script, args, *, env=None, cwd=None):
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
        capture_output=True, text=True, env=child_env, cwd=cwd)
