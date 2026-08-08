#!/usr/bin/env python3
"""Batch 4 destructive injections for invariant scanner denominators."""
from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCAN_PATH = ROOT / "scripts/tests/invariant_scan.py"


def load_scan():
    spec = importlib.util.spec_from_file_location("batch4_invariant_scan", SCAN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bare_rpc_pool_injection(scan, root):
    """B4-RPC-01: only net.attested_rpc_pool may construct RpcPool."""
    sample = root / "scripts/lib/bare_pool.py"
    sample.parent.mkdir(parents=True)
    sample.write_text("from net import RpcPool\npool = RpcPool('http://wrong')\n")
    errors = scan.bare_rpc_pool_errors(files=[sample], root=root)
    assert any("bare RpcPool" in error for error in errors), errors
    assert scan.bare_rpc_pool_errors() == []
    print("INJECT B4-RPC-01 bare RpcPool -> RED")


def _copy_label_surfaces(scan, root):
    for rel, _kind, _locator in scan.LABEL_CHAIN_SURFACES:
        src = ROOT / rel
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)


def test_label_surface_injections(scan, root):
    """B4-LABEL-01/02 and B4F-LABEL-03: labels surfaces stay aligned."""
    _copy_label_surfaces(scan, root)
    resolver = root / "scripts/labels/labels_resolver.py"
    resolver.write_text(resolver.read_text().replace(
        "KNOWN_CHAINS = ('eth', 'base', 'bsc', 'arbitrum', 'sol', 'robinhood')",
        "KNOWN_CHAINS = ('eth', 'base', 'bsc', 'arbitrum', 'sol', 'robinhood', 'ghost')"))
    errors = scan.label_chain_surface_errors(root=root)
    assert any("unregistered" in error and "ghost" in error for error in errors), errors

    _copy_label_surfaces(scan, root)
    builder = root / "scripts/labels/build_labels.py"
    builder.write_text(builder.read_text().replace(
        "BUILD_CHAINS = {'eth', 'bsc', 'base', 'sol', 'robinhood'}",
        "BUILD_CHAINS = {'eth', 'bsc', 'base', 'sol'}"))
    errors = scan.label_chain_surface_errors(root=root)
    assert any("missing labels_table chains" in error and "robinhood" in error
               for error in errors), errors

    _copy_label_surfaces(scan, root)
    offenders = root / "scripts/labels/accumulate_offenders.py"
    offenders.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "scripts/labels/accumulate_offenders.py", offenders)
    offenders.write_text(offenders.read_text().replace(
        "('eth', 'bsc', 'base', 'sol', 'robinhood')",
        "('eth', 'bsc', 'base', 'sol', 'robinhood', 'polygon')"))
    errors = scan.label_chain_surface_errors(root=root)
    assert any("accumulate_offenders.py" in error and "unregistered" in error
               and "polygon" in error for error in errors), errors
    assert scan.label_chain_surface_errors() == []
    print("INJECT B4-LABEL-01/02 + B4F-LABEL-03 extra/missing/eighth surface -> RED")


def test_formal_entrypoint_source_diagnostic(scan, root):
    """B4F-FORMAL-01: empty producer registry yields a scanner diagnostic."""
    shared = root / "shared_release_receipt.py"
    text = (ROOT / "scripts/report/shared_release_receipt.py").read_text()
    start = text.index("ACCOUNTING_PRODUCERS = {")
    end = text.index("\nRECON_PRODUCERS =", start)
    shared.write_text(text[:start] + "ACCOUNTING_PRODUCERS = {}\n" + text[end + 1:])
    actual = scan.scan_actual(shared_path=shared)
    assert any("ACCOUNTING_PRODUCERS" in error for error in actual["_scanner_errors"])
    manifest = json.loads(scan.DEFAULT_MANIFEST.read_text())
    errors = scan.validate_manifest(manifest, actual)
    assert any("ACCOUNTING_PRODUCERS" in error and "registry" in error
               and "shared_release_receipt" in error for error in errors), errors
    print("INJECT B4F-FORMAL-01 empty ACCOUNTING_PRODUCERS -> RED with diagnostic")


def test_vertical_slice_double_binding_injections(scan, root):
    """B4-VS-01/02: verified chains bind both file existence and SUITE."""
    suite = root / "run_all.py"
    text = (ROOT / "scripts/tests/run_all.py").read_text()
    suite.write_text(text.replace("         'test_batch3_evm_vertical_slice.py',\n", ""))
    errors = scan.vertical_slice_errors(
        mapping={"eth": "test_batch3_evm_vertical_slice.py"}, suite_path=suite)
    assert any("not mounted in run_all.SUITE" in error for error in errors), errors

    mapping = {"sol": "test_does_not_exist.py"}
    errors = scan.vertical_slice_errors(mapping=mapping)
    assert any("test file missing" in error and "sol" in error for error in errors), errors
    assert scan.vertical_slice_errors() == []
    print("INJECT B4-VS-01/02 missing SUITE + missing file -> RED")


def test_scanner_denominator_injections(scan, root):
    """B4-INV17-01/02 and B4-RH-COUNT-01: census cannot silently shrink."""
    urllib_sample = root / "urllib_backend.py"
    urllib_sample.write_text(
        "import urllib.request\n"
        "def call(url):\n    return urllib.request.urlopen(url)\n")
    assert "urllib" in scan.scan_python(urllib_sample)[2]

    curl_sample = root / "variable_curl.py"
    curl_sample.write_text(
        "import subprocess\n"
        "def call():\n    cmd = ['curl', 'http://fixture']\n    return subprocess.run(cmd)\n")
    assert "curl" in scan.scan_python(curl_sample)[2]

    manifest = json.loads(scan.DEFAULT_MANIFEST.read_text())
    actual = scan.scan_actual()
    shrunken = copy.deepcopy(manifest)
    shrunken["formal_entrypoints"].pop()
    errors = scan.validate_manifest(shrunken, actual)
    assert any("denominator" in error or "formal_entrypoints" in error for error in errors), errors

    mandatory = set(scan.registered_formal_entrypoints())
    for rel in ("scripts/evm/verify_recon.py", "scripts/solana/anchor_sampler.py",
                "scripts/solana/scan_token_accounts.py"):
        assert rel in mandatory

    doc = root / "data-pipeline-robinhood.md"
    doc.write_text((ROOT / "references/data-pipeline-robinhood.md").read_text().replace(
        "当前 16 个普通文件：15 个 Python", "当前 15 个普通文件：14 个 Python"))
    errors = scan.robinhood_inventory_errors(doc_path=doc)
    assert any("Robinhood inventory" in error for error in errors), errors
    assert scan.robinhood_inventory_errors() == []
    print("INJECT B4-INV17-01/02 urllib + variable curl + denominator shrink -> RED")
    print("INJECT B4-RH-COUNT-01 documented 15/14 vs disk 16/15 -> RED")


def main():
    scan = load_scan()
    with tempfile.TemporaryDirectory(prefix="batch4-invariant-") as td:
        root = Path(td)
        cases = (
            test_bare_rpc_pool_injection,
            test_label_surface_injections,
            test_formal_entrypoint_source_diagnostic,
            test_vertical_slice_double_binding_injections,
            test_scanner_denominator_injections,
        )
        for index, case in enumerate(cases):
            work = root / str(index)
            work.mkdir()
            case(scan, work)
    print("PASS B4-G1: bare pool / labels / vertical slice / denominator injections")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
