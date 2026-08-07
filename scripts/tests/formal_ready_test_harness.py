#!/usr/bin/env python3
"""Test-only activation of formal-tier vertical-slice facts.

Production has no override: Batch 3 must write real evidence before any chain is
ready.  Older release-contract fixtures still need to exercise positive formal
branches, so tests run against copied registry records in an isolated process.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "scripts/lib"
REPORT = ROOT / "scripts/report"


def activate_test_vertical_slices():
    sys.path[:0] = [str(LIB), str(REPORT)]
    import chain_registry

    patched = {}
    for name, record in chain_registry.CHAIN_REGISTRY.items():
        item = dict(record)
        item["capabilities"] = dict(record["capabilities"])
        if item["release_tier"] == "formal":
            item["capabilities"]["vertical_slice_verified"] = True
        patched[name] = item
    chain_registry.CHAIN_REGISTRY = patched
    return chain_registry


def run_formal_script(script, args, *, env=None):
    """Run a CLI after test-only activation, without a production bypass flag."""
    harness = """
import runpy, sys
sys.path.insert(0, sys.argv.pop(1))
from formal_ready_test_harness import activate_test_vertical_slices
activate_test_vertical_slices()
script = sys.argv.pop(1)
sys.argv = [script] + sys.argv[1:]
runpy.run_path(script, run_name="__main__")
"""
    child_env = os.environ.copy()
    if env:
        child_env.update(env)
    return subprocess.run(
        [sys.executable, "-c", harness, str(Path(__file__).resolve().parent),
         str(Path(script).resolve()), *args],
        capture_output=True, text=True, env=child_env)
