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
    module = load(SOL / "accounting_gate_sol.py", "b3_accounting_sol")
    response = mock.Mock()
    response.json.return_value = {"result": {"value": {
        "owner": module.SPL_TOKEN,
        "data": {"parsed": {"type": "mint", "info": {
            "mintAuthority": None, "freezeAuthority": None,
            "supply": "100", "decimals": 0}}}}}}
    out = root / "accounting.json"
    with mock.patch.object(module.requests, "post", return_value=response), \
            mock.patch.object(module.time, "sleep"):
        rc = run_main(module, ["accounting_gate_sol.py", "--mint", "Mint",
                               "--rpc", "http://fixture", "--as-of-slot", "77",
                               "--out", str(out)])
    assert rc == 0
    receipt = json.loads(out.read_text())
    assert receipt["as_of_slot"] == 77


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


def _commit_mismatched_bytes(data_path, _data, receipt_path, receipt):
    Path(data_path).write_bytes(b"committed-but-not-requested\n")
    Path(receipt_path).write_text(json.dumps(receipt), encoding="utf-8")


def _assert_committed_mismatch_was_withdrawn(root, out, receipt):
    assert not out.exists(), "self-check failure left data in the formal location"
    if receipt.exists():
        assert json.loads(receipt.read_text()).get("verdict") != "PASS"
    errors = list(root.glob(f"{receipt.stem}.error.*.json"))
    assert errors and json.loads(errors[-1].read_text())["verdict"] == "ERROR"


def test_window_post_commit_selfcheck_withdraws_formal_artifacts(root):
    """B3F-TXN-01: post-commit mismatch cannot leave formal data plus PASS."""
    module = _load_solana_module(root, "window_fetch.py", "b3_window_post_commit")
    out = root / "window.jsonl"
    receipt = root / "window.receipt.json"
    with mock.patch.object(module, "scan_seg", return_value=([], True, [1735689600])), \
            mock.patch.object(module, "publish_txn", side_effect=_commit_mismatched_bytes):
        rc = module.main(["10", "10", str(out), "--receipt", str(receipt), "--conc", "1"])
    assert rc != 0
    _assert_committed_mismatch_was_withdrawn(root, out, receipt)


def test_anchor_post_commit_selfcheck_withdraws_formal_artifacts(root):
    """B3F-TXN-02: anchor matches window withdrawal depth after commit."""
    module = _load_solana_module(root, "anchor_sampler.py", "b3_anchor_post_commit")
    out = root / "anchors.jsonl"
    receipt = root / "anchor.receipt.json"
    old = Path.cwd()
    os.chdir(root)
    try:
        with mock.patch.object(module, "fetch_window", return_value=[]), \
                mock.patch.object(module, "publish_txn", side_effect=_commit_mismatched_bytes):
            rc = module.main(["--start", "2025-01-01", "--end", "2025-01-01",
                              "--ref-slot", "100", "--ref-ts", "1735689600",
                              "--as-of-slot", "1000", "--out", str(out),
                              "--receipt", str(receipt)])
    finally:
        os.chdir(old)
    assert rc != 0
    _assert_committed_mismatch_was_withdrawn(root, out, receipt)


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
    raw = bytes(32) + (100).to_bytes(8, "little")

    def fake_rpc(_url, payload, out_file, _timeout=120):
        method = payload["method"]
        if method == "getTokenSupply":
            result = {"context": {"slot": 77},
                      "value": {"amount": "100", "decimals": 0}}
        elif method == "getProgramAccounts":
            result = {"context": {"slot": 77}, "value": [{
                "pubkey": "Account1",
                "account": {"data": [base64.b64encode(raw).decode(), "base64"]},
            }]}
        else:
            raise AssertionError(method)
        Path(out_file).write_text(json.dumps({"result": result}))
        return True

    out = root / "snapshot.json"
    receipt = root / "supply.receipt.json"
    old = Path.cwd()
    os.chdir(root)
    try:
        with mock.patch.object(module, "rpc_call", side_effect=fake_rpc), \
                mock.patch.object(sys, "argv", [
                "scan_token_accounts.py", "Mint", "--program", "spl",
                "--rpc", "http://fixture", "--as-of-slot", "77",
                "--out", str(out), "--receipt", str(receipt)]):
            rc = module.main()
    finally:
        os.chdir(old)
    assert int(rc or 0) == 0
    payload = json.loads(receipt.read_text())
    assert payload["schema"] == "solana-holder-snapshot-receipt/v3"
    assert payload["target"] == {"chain": "solana", "token": "mint", "as_of_block": 77}
    assert payload["closed"] is True
    assert json.loads(out.read_text())["target"] == payload["target"]


def test_supply_truth_requires_exact_frozen_slot(root):
    module = load(ROOT / "scripts/lib/supply_truth_gate.py", "b3_supply_truth_slot")
    stats = root / "stats.json"
    stats.write_text(json.dumps({"mint_total_raw": 100, "burn_total_raw": 0}))
    out = root / "truth.json"
    argv = ["supply_truth_gate.py", "--chain", "solana", "--mint", "Mint",
            "--as-of-block", "77", "--replay-stats", str(stats), "--out", str(out)]
    with mock.patch.object(module, "fetch_onchain_supply", return_value=(100, 78)):
        rc = run_main(module, argv)
    assert rc != 0
    assert not out.exists()


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
            test_window_post_commit_selfcheck_withdraws_formal_artifacts,
            test_anchor_post_commit_selfcheck_withdraws_formal_artifacts,
            test_window_complete_segment_requires_timestamp_evidence,
            test_anchor_and_window_reject_same_or_alias_paths,
            test_supply_cli_has_runner_bound_outputs,
            test_supply_truth_requires_exact_frozen_slot,
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
