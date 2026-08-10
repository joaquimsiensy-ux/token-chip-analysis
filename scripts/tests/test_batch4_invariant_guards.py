#!/usr/bin/env python3
"""Batch 4 destructive injections for invariant scanner denominators."""
from __future__ import annotations

import ast
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


def test_main_exit_propagation_injection(scan, root):
    """R9-B4-MAIN-01: an integer-returning main may not be called bare."""
    sample = root / "scripts/bare_main.py"
    sample.parent.mkdir(parents=True, exist_ok=True)
    sample.write_text(
        "def main():\n    return 1\n\n"
        "if __name__ == '__main__':\n    main()\n",
        encoding="utf-8")
    errors = scan.main_exit_propagation_errors(files=[sample], root=root)
    assert any("does not propagate" in error for error in errors), errors
    assert scan.main_exit_propagation_errors() == []
    print("INJECT R9-B4-MAIN-01 bare integer main() -> RED")


def test_top_level_main_exit_propagation_injection(scan, root):
    """B4F2-MAIN-02: a top-level bare main call also drops the exit code."""
    sample = root / "scripts/top_level_bare_main.py"
    sample.parent.mkdir(parents=True, exist_ok=True)
    sample.write_text(
        "def main():\n"
        "    return 1\n\n"
        "main()\n",
        encoding="utf-8")
    errors = scan.main_exit_propagation_errors(files=[sample], root=root)
    assert any("does not propagate" in error for error in errors), errors
    assert scan.main_exit_propagation_errors() == []
    print("INJECT B4F2-MAIN-02 top-level bare integer main() -> RED")


def test_handwritten_e2e_provenance_injection(scan, root):
    """R9-B4-E2E-01: hand-written PASS bytes do not count as a formal slice."""
    sample = root / "test_handwritten_slice.py"
    sample.write_text(
        "import json\nfrom pathlib import Path\n\n"
        "def test_fake_vertical_slice():\n"
        "    claimed = (\n"
        "        'scripts/report/reconciliation_report.py',\n"
        "        'scripts/solana/scan_token_accounts.py',\n"
        "        'scripts/solana/anchor_sampler.py',\n"
        "        'scripts/lib/supply_truth_gate.py',\n"
        "        'scripts/solana/accounting_gate_sol.py',\n"
        "        'scripts/solana/window_fetch.py',\n"
        "    )\n"
        "    Path('solana_observation_bundle.json').write_text("
        "json.dumps({'verdict': 'PASS', 'claimed': claimed}))\n\n"
        "def main():\n"
        "    test_fake_vertical_slice()\n",
        encoding="utf-8")
    errors = scan.formal_e2e_provenance_errors(targets={
        "sol": (sample, "test_fake_vertical_slice"),
    })
    assert any("registered producer" in error or "reconciliation runner" in error
               for error in errors), errors
    assert scan.formal_e2e_provenance_errors() == []
    print("INJECT R9-B4-E2E-01 hand-written observation bundle -> RED")


def test_fake_local_run_provenance_injection(scan, root):
    """B4F2-E2E-02: a locally named no-op run is not execution evidence."""
    sample = root / "test_fake_run_slice.py"
    sample.write_text(
        "def run(*_args, **_kwargs):\n"
        "    return None\n\n"
        "def test_fake_vertical_slice():\n"
        "    run(['python3', 'scripts/report/reconciliation_report.py'])\n"
        "    run(['python3', 'scripts/solana/scan_token_accounts.py'])\n"
        "    run(['python3', 'scripts/solana/anchor_sampler.py'])\n"
        "    run(['python3', 'scripts/lib/supply_truth_gate.py'])\n"
        "    run(['python3', 'scripts/solana/accounting_gate_sol.py'])\n"
        "    run(['python3', 'scripts/solana/window_fetch.py'])\n\n"
        "def main():\n"
        "    test_fake_vertical_slice()\n",
        encoding="utf-8")
    errors = scan.formal_e2e_provenance_errors(targets={
        "sol": (sample, "test_fake_vertical_slice"),
    })
    assert any("real reconciliation runner" in error for error in errors), errors
    assert any("registered producer execution" in error for error in errors), errors
    assert scan.formal_e2e_provenance_errors() == []
    print("INJECT B4F2-E2E-02 local no-op run wrapper -> RED")


def test_dead_execution_primitive_injection(scan, root):
    """B4F2-E2E-03: an execution primitive in dead code is not evidence."""
    sample = root / "test_dead_run_slice.py"
    sample.write_text(
        "import subprocess\n\n"
        "def run(command):\n"
        "    if False:\n"
        "        subprocess.run(command)\n"
        "    return None\n\n"
        "def test_fake_vertical_slice():\n"
        "    run(['python3', 'scripts/report/reconciliation_report.py'])\n"
        "    run(['python3', 'scripts/solana/scan_token_accounts.py'])\n"
        "    run(['python3', 'scripts/solana/anchor_sampler.py'])\n"
        "    run(['python3', 'scripts/lib/supply_truth_gate.py'])\n"
        "    run(['python3', 'scripts/solana/accounting_gate_sol.py'])\n"
        "    run(['python3', 'scripts/solana/window_fetch.py'])\n\n"
        "def main():\n"
        "    test_fake_vertical_slice()\n",
        encoding="utf-8")
    errors = scan.formal_e2e_provenance_errors(targets={
        "sol": (sample, "test_fake_vertical_slice"),
    })
    assert any("real reconciliation runner" in error for error in errors), errors
    assert scan.formal_e2e_provenance_errors() == []
    print("INJECT B4F2-E2E-03 dead subprocess primitive -> RED")


def _fake_sol_slice_source(call_prefix, *, imports="", shadow=""):
    scripts = (
        "scripts/report/reconciliation_report.py",
        "scripts/solana/scan_token_accounts.py",
        "scripts/solana/anchor_sampler.py",
        "scripts/lib/supply_truth_gate.py",
        "scripts/solana/accounting_gate_sol.py",
        "scripts/solana/window_fetch.py",
    )
    calls = "".join(call_prefix.format(script=script) for script in scripts)
    return (
        imports
        + "def test_fake_vertical_slice():\n"
        + shadow
        + calls
        + "\ndef main():\n"
        + "    test_fake_vertical_slice()\n"
    )


def _assert_fake_sol_slice_rejected(scan, sample):
    errors = scan.formal_e2e_provenance_errors(targets={
        "sol": (sample, "test_fake_vertical_slice"),
    })
    assert any("real reconciliation runner" in error for error in errors), errors
    assert any("registered producer execution" in error for error in errors), errors


def test_unimported_subprocess_primitive_injection(scan, root):
    """B4F2C2-E2E-04/M6: an unbound qualified name is not execution."""
    sample = root / "test_unimported_subprocess_slice.py"
    sample.write_text(_fake_sol_slice_source(
        "    subprocess.run(['python3', '{script}'])\n"), encoding="utf-8")
    _assert_fake_sol_slice_rejected(scan, sample)
    print("INJECT B4F2C2-E2E-04 unimported subprocess.run -> RED")


def test_unimported_os_exec_primitive_injection(scan, root):
    """B4F2C2-E2E-05/M7: an unbound os.exec name is not execution."""
    sample = root / "test_unimported_os_exec_slice.py"
    sample.write_text(_fake_sol_slice_source(
        "    os.execv('python3', ['python3', '{script}'])\n"), encoding="utf-8")
    _assert_fake_sol_slice_rejected(scan, sample)
    print("INJECT B4F2C2-E2E-05 unimported os.execv -> RED")


def test_unimported_harness_primitive_injection(scan, root):
    """B4F2C2-E2E-06/M8: an unbound harness name is not execution."""
    sample = root / "test_unimported_harness_slice.py"
    sample.write_text(_fake_sol_slice_source(
        "    formal_ready_test_harness.run_formal_script('{script}', [])\n"),
        encoding="utf-8")
    _assert_fake_sol_slice_rejected(scan, sample)
    print("INJECT B4F2C2-E2E-06 unimported harness primitive -> RED")


def test_shadowed_subprocess_primitive_injection(scan, root):
    """B4F2C2-E2E-07/M10: a locally rebound import is not execution."""
    sample = root / "test_shadowed_subprocess_slice.py"
    sample.write_text(_fake_sol_slice_source(
        "    subprocess.run(['python3', '{script}'])\n",
        imports="import subprocess\n\n",
        shadow="    subprocess = None\n"), encoding="utf-8")
    _assert_fake_sol_slice_rejected(scan, sample)
    print("INJECT B4F2C2-E2E-07 locally shadowed subprocess -> RED")


def test_execution_import_binding_positive_controls(scan, root):
    """B4F2C2 positive controls: M4/M5 and all four live chains stay ready."""
    scripts = (
        "scripts/report/reconciliation_report.py",
        "scripts/solana/scan_token_accounts.py",
        "scripts/solana/anchor_sampler.py",
        "scripts/lib/supply_truth_gate.py",
        "scripts/solana/accounting_gate_sol.py",
        "scripts/solana/window_fetch.py",
    )
    calls = "".join(
        f"    run(['python3', '{script}'])\n" for script in scripts)
    m4 = root / "test_multilevel_real_run_slice.py"
    m4.write_text(
        "import subprocess\n\n"
        "def _r2(command):\n"
        "    subprocess.run(command)\n\n"
        "def run(command):\n"
        "    _r2(command)\n\n"
        "def test_fake_vertical_slice():\n"
        + calls
        + "\ndef main():\n"
        + "    test_fake_vertical_slice()\n",
        encoding="utf-8")
    assert scan.formal_e2e_provenance_errors(targets={
        "sol": (m4, "test_fake_vertical_slice"),
    }) == []

    m5 = root / "test_aliased_real_run_slice.py"
    m5.write_text(_fake_sol_slice_source(
        "    sp.run(['python3', '{script}'])\n",
        imports="import subprocess as sp\n\n"), encoding="utf-8")
    assert scan.formal_e2e_provenance_errors(targets={
        "sol": (m5, "test_fake_vertical_slice"),
    }) == []
    assert scan.formal_e2e_provenance_errors() == []
    assert scan._load_chain_registry().formal_ready_chains() == {
        "eth", "bsc", "base", "sol",
    }
    print("PASS B4F2C2 M4/M5 import bindings + four live ready chains")


def test_execution_local_binding_scope_contract(scan, _root):
    """B4F2C2 local binding census covers named forms but not child scopes."""
    tree = ast.parse(
        "def sample(param_shadow):\n"
        "    assign_shadow = 1\n"
        "    aug_shadow += 1\n"
        "    ann_shadow: int = 1\n"
        "    for for_shadow in ():\n"
        "        pass\n"
        "    with context() as with_shadow:\n"
        "        pass\n"
        "    try:\n"
        "        pass\n"
        "    except Exception as except_shadow:\n"
        "        pass\n"
        "    if (walrus_shadow := 1):\n"
        "        pass\n"
        "    def nested(nested_param):\n"
        "        nested_assign = 1\n"
        "    hidden = lambda nested_lambda: (nested_walrus := 1)\n")
    bindings = scan._function_local_bindings(tree.body[0])
    assert {
        "param_shadow", "assign_shadow", "aug_shadow", "ann_shadow",
        "for_shadow", "with_shadow", "except_shadow", "walrus_shadow",
    } <= bindings
    assert not {
        "nested_param", "nested_assign", "nested_lambda", "nested_walrus",
    } & bindings
    print("PASS B4F2C2 local binding forms + nested scope boundary")


def test_failure_artifact_contract_injection(scan, root):
    """R9-B4-STALE-01: registered producer cannot leave old current success."""
    sample = root / "scripts/stale_producer.py"
    sample.parent.mkdir(parents=True, exist_ok=True)
    sample.write_text(
        "from pathlib import Path\n\n"
        "def main():\n"
        "    out = Path('canonical.json')\n"
        "    try:\n"
        "        raise RuntimeError('injected')\n"
        "    except RuntimeError:\n"
        "        return 1\n\n"
        "if __name__ == '__main__':\n"
        "    raise SystemExit(main())\n",
        encoding="utf-8")
    contracts = ({
        "script": sample,
        "entrypoint": "main",
        "canonical_artifacts": 1,
    },)
    errors = scan.failure_artifact_contract_errors(contracts=contracts, root=root)
    assert any("quarantine" in error for error in errors), errors
    assert any("error receipt" in error for error in errors), errors
    assert scan.failure_artifact_contract_errors() == []
    print("INJECT R9-B4-STALE-01 failed producer leaves old canonical -> RED")


def test_dead_failure_contract_injection(scan, root):
    """B4F2-STALE-03: calls hidden in statically dead code do not count."""
    sample = root / "scripts/dead_contract.py"
    sample.parent.mkdir(parents=True, exist_ok=True)
    sample.write_text(
        "def main():\n"
        "    if False:\n"
        "        quarantine_current('canonical.json', 'run')\n"
        "        publish_error_receipt('receipt.json', {}, 'error')\n"
        "    return 1\n",
        encoding="utf-8")
    contracts = ({
        "script": sample,
        "entrypoint": "main",
        "canonical_artifacts": 1,
    },)
    errors = scan.failure_artifact_contract_errors(contracts=contracts, root=root)
    assert any("quarantine" in error for error in errors), errors
    assert any("error receipt" in error for error in errors), errors
    assert scan.failure_artifact_contract_errors() == []
    print("INJECT B4F2-STALE-03 dead quarantine/error calls -> RED")


def test_constant_false_failure_contract_injection(scan, root):
    """B4F2-STALE-03B: a literal false comparison is also dead code."""
    sample = root / "scripts/constant_false_contract.py"
    sample.parent.mkdir(parents=True, exist_ok=True)
    sample.write_text(
        "def main():\n"
        "    if 1 == 0:\n"
        "        quarantine_current('canonical.json', 'run')\n"
        "        publish_error_receipt('receipt.json', {}, 'error')\n"
        "    return 1\n",
        encoding="utf-8")
    contracts = ({
        "script": sample,
        "entrypoint": "main",
        "canonical_artifacts": 1,
    },)
    errors = scan.failure_artifact_contract_errors(contracts=contracts, root=root)
    assert any("quarantine" in error for error in errors), errors
    assert any("error receipt" in error for error in errors), errors
    print("INJECT B4F2-STALE-03B constant-false contract calls -> RED")


def test_failure_artifact_registry_completeness(scan, _root):
    """R9-B4-STALE-02: every formal/standalone producer has named artifacts."""
    coverage = copy.deepcopy(scan.FAILURE_ARTIFACT_COVERAGE)
    coverage.pop("scripts/solana/scan_token_accounts.py")
    errors = scan.failure_artifact_coverage_errors(coverage=coverage)
    assert any("scan_token_accounts.py" in error for error in errors), errors
    assert scan.failure_artifact_coverage_errors() == []
    print("INJECT R9-B4-STALE-02 remove formal producer artifact registration -> RED")


def test_new_standalone_producer_requires_registration(scan, root):
    """B4F2-STALE-04: a newly enumerable standalone producer cannot be omitted."""
    sample = root / "scripts/evm/new_stale_producer.py"
    sample.parent.mkdir(parents=True, exist_ok=True)
    sample.write_text(
        "def main():\n"
        "    quarantine_current('canonical.json', 'run')\n"
        "    publish_error_receipt('marker.json', {}, 'error')\n"
        "    publish_txn('canonical.json', b'data', 'marker.json', {})\n"
        "    return 0\n\n"
        "if __name__ == '__main__':\n"
        "    raise SystemExit(main())\n",
        encoding="utf-8")
    original_files = scan.production_files
    original_rel = scan._rel
    scan.production_files = lambda: [sample]
    scan._rel = lambda path: Path(path).relative_to(root).as_posix()
    try:
        errors = scan.failure_artifact_coverage_errors()
    finally:
        scan.production_files = original_files
        scan._rel = original_rel
    assert any("new_stale_producer.py" in error and "unregistered" in error
               for error in errors), errors
    assert scan.failure_artifact_coverage_errors() == []
    print("INJECT B4F2-STALE-04 newly added standalone producer -> RED")


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
            test_main_exit_propagation_injection,
            test_top_level_main_exit_propagation_injection,
            test_handwritten_e2e_provenance_injection,
            test_fake_local_run_provenance_injection,
            test_dead_execution_primitive_injection,
            test_unimported_subprocess_primitive_injection,
            test_unimported_os_exec_primitive_injection,
            test_unimported_harness_primitive_injection,
            test_shadowed_subprocess_primitive_injection,
            test_execution_import_binding_positive_controls,
            test_execution_local_binding_scope_contract,
            test_failure_artifact_contract_injection,
            test_dead_failure_contract_injection,
            test_constant_false_failure_contract_injection,
            test_failure_artifact_registry_completeness,
            test_new_standalone_producer_requires_registration,
        )
        for index, case in enumerate(cases):
            work = root / str(index)
            work.mkdir()
            case(scan, work)
    print("PASS B4-G1: bare pool / labels / vertical slice / denominator injections")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
