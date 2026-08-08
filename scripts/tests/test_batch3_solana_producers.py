#!/usr/bin/env python3
"""B3 Solana producer regressions; only transport adapters are replaced."""
from __future__ import annotations

import importlib.util
import base64
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SOL = ROOT / "scripts/solana"
sys.path.insert(0, str(ROOT / "scripts/lib"))
sys.path.insert(0, str(ROOT / "scripts/tests"))
from test_r9_batch3_solana_observation import (MINT, SolanaTransportFake)  # noqa: E402


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_main(module, argv):
    with mock.patch.object(sys, "argv", argv):
        try:
            value = module.main()
        except SystemExit as exc:
            return int(exc.code or 0)
    return int(value or 0)


def test_accounting_requires_and_emits_frozen_slot(root):
    scan = _load_solana_module(root, "scan_token_accounts.py", "b3_accounting_scan")
    old = Path.cwd(); os.chdir(root)
    try:
        rc = scan.main([MINT, "--program", "spl", "--rpc", "fixture://solana",
                        "--out", "snapshot.json", "--bundle", "bundle.json",
                        "--work-dir", "data"], request_json=SolanaTransportFake())
    finally:
        os.chdir(old)
    assert rc == 0
    observed_slot = json.loads((root / "bundle.json").read_text())["snapshot"]["slot"]
    module = load(SOL / "accounting_gate_sol.py", "b3_accounting_sol")
    out = root / "accounting.json"
    rc = run_main(module, ["accounting_gate_sol.py", "--mint", MINT,
                           "--bundle", str(root / "bundle.json"),
                           "--as-of-slot", str(observed_slot), "--out", str(out)])
    assert rc == 0
    receipt = json.loads(out.read_text())
    assert receipt["as_of_slot"] == observed_slot
    assert receipt["observation_bundle"]["sha256"]
    mismatch = root / "accounting-mismatch.json"
    rc = run_main(module, ["accounting_gate_sol.py", "--mint", MINT,
                           "--bundle", str(root / "bundle.json"),
                           "--as-of-slot", "77", "--out", str(mismatch)])
    assert rc != 0
    failed = json.loads(mismatch.read_text())
    assert failed["observed_context_slot"] == observed_slot
    assert failed["as_of_slot"] == observed_slot


def _load_solana_module(root, filename, name):
    (root / "config.json").write_text(json.dumps({"mint": "Mint"}))
    old = Path.cwd()
    os.chdir(root)
    try:
        return load(SOL / filename, name)
    finally:
        os.chdir(old)


def test_window_missing_timestamp_fails_without_pass(root):
    module = _load_solana_module(root, "window_fetch.py", "b3_window_ts")
    out = root / "window.jsonl"
    receipt = root / "window.receipt.json"
    result = mock.Mock(ok=True, value=[{
        "header": {"number": 10}, "transactions": [], "tokenBalances": [{
            "transactionIndex": 0, "preOwner": "A", "postOwner": "B",
            "preAmount": "1", "postAmount": "1"}]}])
    with mock.patch.object(module.net, "curl_json", return_value=result), \
            mock.patch.object(module.time, "sleep"):
        rc = module.main(["10", "10", str(out), "--receipt", str(receipt), "--conc", "1"])
    assert rc != 0
    if receipt.exists():
        assert json.loads(receipt.read_text()).get("verdict") != "PASS"


def _commit_requested_bytes(data_path, data, receipt_path, receipt):
    payload = data.data if hasattr(data, "data") else json.dumps(data).encode()
    Path(data_path).write_bytes(payload)
    Path(receipt_path).write_text(json.dumps(receipt), encoding="utf-8")


def _assert_committed_mismatch_was_withdrawn(root, out, receipt):
    assert not out.exists(), "self-check failure left data in the formal location"
    if receipt.exists():
        assert json.loads(receipt.read_text()).get("verdict") != "PASS"
    errors = list(root.glob(f"{receipt.stem}.error.*.json"))
    assert errors and json.loads(errors[-1].read_text())["verdict"] == "ERROR"


def test_window_has_no_post_commit_failure_surface(root):
    """R9 B3: publish_txn is the final fallible data+receipt operation."""
    module = _load_solana_module(root, "window_fetch.py", "b3_window_post_commit")
    out = root / "window.jsonl"
    receipt = root / "window.receipt.json"
    original = Path.read_bytes

    def reject_post_commit_read(path):
        if Path(path) == out and out.exists():
            raise AssertionError("post-commit data self-check executed")
        return original(path)

    with mock.patch.object(module, "scan_seg", return_value=([], True, [1735689600])), \
            mock.patch.object(module, "publish_txn", side_effect=_commit_requested_bytes), \
            mock.patch.object(Path, "read_bytes", reject_post_commit_read):
        rc = module.main(["10", "10", str(out), "--receipt", str(receipt), "--conc", "1"])
    assert rc == 0
    assert out.exists() and json.loads(receipt.read_text())["verdict"] == "PASS"


def test_anchor_has_no_post_commit_failure_surface(root):
    """R9 B3: anchor returns immediately after the kernel transaction commits."""
    module = _load_solana_module(root, "anchor_sampler.py", "b3_anchor_post_commit")
    out = root / "anchors.jsonl"
    receipt = root / "anchor.receipt.json"
    old = Path.cwd()
    os.chdir(root)
    original = Path.read_bytes

    def reject_post_commit_read(path):
        if Path(path) == out and out.exists():
            raise AssertionError("post-commit data self-check executed")
        return original(path)

    try:
        with mock.patch.object(module, "fetch_window", return_value=[]), \
                mock.patch.object(module, "publish_txn", side_effect=_commit_requested_bytes), \
                mock.patch.object(Path, "read_bytes", reject_post_commit_read):
            rc = module.main(["--start", "2025-01-01", "--end", "2025-01-01",
                              "--ref-slot", "100", "--ref-ts", "1735689600",
                              "--as-of-slot", "1000", "--out", str(out),
                              "--receipt", str(receipt)])
    finally:
        os.chdir(old)
    assert rc == 0
    assert out.exists() and json.loads(receipt.read_text())["verdict"] == "PASS"


def test_window_complete_segment_requires_timestamp_evidence(root):
    """B3F-TS-01: a complete segment with no timestamp evidence is not PASS."""
    module = _load_solana_module(root, "window_fetch.py", "b3_window_empty_timestamps")
    out = root / "window.jsonl"
    receipt = root / "window.receipt.json"
    with mock.patch.object(module, "scan_seg", return_value=([], True, [])):
        rc = module.main(["10", "10", str(out), "--receipt", str(receipt), "--conc", "1"])
    assert rc != 0
    if receipt.exists():
        assert json.loads(receipt.read_text()).get("verdict") != "PASS"


def test_anchor_and_window_reject_same_or_alias_paths(root):
    anchor = _load_solana_module(root, "anchor_sampler.py", "b3_anchor_alias")
    shared = root / "same.json"
    failed = mock.Mock(ok=False, value=None)
    anchor_calls = mock.Mock(return_value=failed)
    with mock.patch.object(anchor.net, "curl_json", anchor_calls), \
            mock.patch.object(anchor.time, "sleep"):
        rc = anchor.main(["--start", "2025-01-01", "--end", "2025-01-01",
                          "--ref-slot", "100", "--ref-ts", "1735689600",
                          "--as-of-slot", "1000", "--out", str(shared),
                          "--receipt", str(shared)])
    assert rc != 0
    assert anchor_calls.call_count == 0
    window = _load_solana_module(root, "window_fetch.py", "b3_window_alias")
    window_calls = mock.Mock(return_value=failed)
    with mock.patch.object(window.net, "curl_json", window_calls), \
            mock.patch.object(window.time, "sleep"):
        rc = window.main(["10", "10", str(shared), "--receipt", str(shared), "--conc", "1"])
    assert rc != 0
    assert window_calls.call_count == 0
    real = root / "real"
    real.mkdir()
    alias = root / "alias"
    alias.symlink_to(real, target_is_directory=True)
    with mock.patch.object(anchor.net, "curl_json", anchor_calls), \
            mock.patch.object(anchor.time, "sleep"):
        rc = anchor.main(["--start", "2025-01-01", "--end", "2025-01-01",
                          "--ref-slot", "100", "--ref-ts", "1735689600",
                          "--as-of-slot", "1000", "--out", str(real / "data.json"),
                          "--receipt", str(alias / "receipt.json")])
    assert rc != 0 and anchor_calls.call_count == 0


def test_supply_cli_has_runner_bound_outputs(root):
    module = _load_solana_module(root, "scan_token_accounts.py", "b3_supply_cli")
    out = root / "snapshot.json"
    receipt = root / "supply.receipt.json"
    old = Path.cwd()
    os.chdir(root)
    try:
        rc = module.main([MINT, "--program", "spl", "--rpc", "fixture://solana",
                          "--out", str(out), "--bundle", str(receipt),
                          "--work-dir", "data"], request_json=SolanaTransportFake())
    finally:
        os.chdir(old)
    assert int(rc or 0) == 0
    payload = json.loads(receipt.read_text())
    assert payload["schema"] == "solana-observation-bundle/v1"
    assert payload["target"]["token"] == MINT.lower()
    assert payload["target"]["as_of_block"] == payload["snapshot"]["slot"]
    assert payload["closed"] is True
    assert json.loads(out.read_text())["target"] == payload["target"]


def test_supply_truth_declared_slot_is_assertion(root):
    scan = _load_solana_module(root, "scan_token_accounts.py", "b3_truth_scan")
    old = Path.cwd(); os.chdir(root)
    try:
        assert scan.main([MINT, "--program", "spl", "--rpc", "fixture://solana",
                          "--out", "snapshot.json", "--bundle", "bundle.json",
                          "--work-dir", "data"], request_json=SolanaTransportFake()) == 0
    finally:
        os.chdir(old)
    module = load(ROOT / "scripts/lib/supply_truth_gate.py", "b3_supply_truth_slot")
    stats = root / "stats.json"
    stats.write_text(json.dumps({"mint_total_raw": 100, "burn_total_raw": 0}))
    out = root / "truth.json"
    argv = ["supply_truth_gate.py", "--chain", "solana", "--mint", MINT,
            "--observation-bundle", str(root / "bundle.json"),
            "--as-of-block", "77", "--replay-stats", str(stats), "--out", str(out)]
    rc = module.main(argv[1:])
    assert rc != 0
    assert not out.exists()
    errors = list(root.glob("truth.error.*.json"))
    assert errors
    failed = json.loads(errors[-1].read_text())
    assert failed["target"]["as_of_block"] == json.loads(
        (root / "bundle.json").read_text())["snapshot"]["slot"]


def test_runner_rejects_none_target_before_producer(root):
    sys.path.insert(0, str(ROOT / "scripts/report"))
    module = load(ROOT / "scripts/report/reconciliation_report.py", "b3_none_target")
    producers = {
        "balance": "scripts/solana/anchor_sampler.py",
        "supply": "scripts/solana/scan_token_accounts.py",
        "supply_truth": "scripts/lib/supply_truth_gate.py",
        "time": "scripts/solana/anchor_sampler.py",
    }
    spec = {"family": "solana", "case_dir": str(root),
            "target": {"chain": "solana", "token": "mint", "as_of_block": None},
            "checks": {key: {"producer": producer,
                              "argv": ["--receipt", f"{key}.json"],
                              "receipt": f"{key}.json"}
                       for key, producer in producers.items()}}
    with mock.patch.object(module.subprocess, "run") as launched:
        rc = module.run_job(spec)
    assert rc != 0 and launched.call_count == 0


def main():
    with tempfile.TemporaryDirectory(prefix="b3-solana-") as td:
        root = Path(td).resolve()
        tests = (
            test_accounting_requires_and_emits_frozen_slot,
            test_window_missing_timestamp_fails_without_pass,
            test_window_has_no_post_commit_failure_surface,
            test_anchor_has_no_post_commit_failure_surface,
            test_window_complete_segment_requires_timestamp_evidence,
            test_anchor_and_window_reject_same_or_alias_paths,
            test_supply_cli_has_runner_bound_outputs,
            test_supply_truth_declared_slot_is_assertion,
            test_runner_rejects_none_target_before_producer,
        )
        failures = []
        for index, test in enumerate(tests):
            case = root / str(index)
            case.mkdir()
            try:
                test(case)
            except Exception as exc:
                failures.append(f"{test.__name__}: {exc}")
        if failures:
            raise AssertionError("\n".join(failures))
    print("PASS B3-G2: Solana slot/envelope/txn/timestamp producer guards")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
