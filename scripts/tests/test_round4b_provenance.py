#!/usr/bin/env python3
"""Round4b F-01/F-02 provenance boundary regressions."""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path[:0] = [str(HERE.parent / "report"), str(HERE)]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_identity_rejects_isolated_self_reports():
    from identity_snapshot_receipt import emit_evm
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        snapshot = root / "balances_final.json"
        snapshot.write_text(json.dumps({"0xabc": "100"}))
        preflight = root / "channels_preflight.json"
        preflight.write_text(json.dumps({
            "schema": "evm-channels-preflight/v1", "status": "PASS",
            "token": "0xtoken", "expected_to": 124,
            "producer": {"path": "channels_preflight.py",
                         "sha256": sha(HERE.parent / "evm" / "channels_preflight.py")}}))
        stats = root / "replay_stats.json"
        stats.write_text(json.dumps({
            "gate_pass": True, "supply_check_ok": True, "sum_balances_wei": "100",
            "producer": {"path": "replay_stream.py",
                         "sha256": sha(HERE.parent / "evm" / "replay_stream.py")},
            "inputs": []}))
        try:
            emit_evm("bsc", "0xtoken", 123, snapshot, preflight, stats, 100,
                     root / "receipt.json")
        except ValueError:
            return
        raise AssertionError("copied producer hashes cannot legitimize isolated EVM self-reports")


def test_shared_production_chain_and_copied_producer_rejection():
    from test_audit_release_gate import build_case
    from shared_release_receipt import validate_sources
    producers = {"accounting": "scripts/evm/accounting_gate.py",
                 "balance": "scripts/evm/verify_recon.py",
                 "supply": "scripts/evm/verify_recon.py",
                 "supply_truth": "scripts/lib/supply_truth_gate.py",
                 "time": "scripts/lib/time_spotcheck.py"}
    for label, rel in producers.items():
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build_case(root, historical=False)
            assert validate_sources(root)["chain"] == "bsc"
            current = ROOT / rel
            copied = root / f"copied_{Path(rel).name}"
            shutil.copyfile(current, copied)
            forged_ref = {"path": copied.name, "sha256": sha(current)}
            if label == "accounting":
                obj = json.loads((root / "accounting_mode.json").read_text())
                obj["producer"] = forged_ref
                (root / "accounting_mode.json").write_text(json.dumps(obj))
            else:
                obj = json.loads((root / "reconciliation_report.json").read_text())
                obj["checks"][label]["producer"] = forged_ref
                (root / "reconciliation_report.json").write_text(json.dumps(obj))
            try:
                validate_sources(root)
            except ValueError as exc:
                assert "whitelisted" in str(exc)
            else:
                raise AssertionError(f"case-local copied producer must be rejected: {label}")

def test_shared_copied_runner_rejection():
    from test_audit_release_gate import build_case
    from shared_release_receipt import validate_sources
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        build_case(root, historical=False)
        current = ROOT / "scripts/report/adversarial_review_runner.py"
        copied = root / "copied_review_runner.py"
        shutil.copyfile(current, copied)
        review = json.loads((root / "adversarial_review.json").read_text())
        review["reviews"][0]["runner"] = {"path": copied.name, "sha256": sha(current)}
        (root / "adversarial_review.json").write_text(json.dumps(review))
        try:
            validate_sources(root)
        except ValueError as exc:
            assert "whitelisted" in str(exc)
        else:
            raise AssertionError("case-local runner copy with correct hash must be rejected")


def test_adversarial_runner_failure_is_fail_closed():
    runner = ROOT / "scripts/report/adversarial_review_runner.py"
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "a4_claims.json").write_text(json.dumps({
            "schema": "a4-claims/v2", "claims": [{"id": "C1"}]}))
        entry = root / "fail_review.py"
        entry.write_text("raise SystemExit(7)\n")
        proc = subprocess.run([
            sys.executable, str(runner), str(root), "--role", "completeness_critic",
            "--entrypoint", entry.name, "--artifact", "review.md",
            "--receipt", "execution.json"], capture_output=True, text=True)
        assert proc.returncode == 2 and not (root / "execution.json").exists()
        assert not (root / "review.md").exists()
        good = root / "good_review.py"
        good.write_text("import os\nfrom pathlib import Path\nPath(os.environ['CHIP_REVIEW_OUTPUT']).write_text('ok')\n")
        linked = root / "linked_review.py"
        linked.symlink_to(good)
        proc = subprocess.run([
            sys.executable, str(runner), str(root), "--role", "completeness_critic",
            "--entrypoint", linked.name, "--artifact", "review.md",
            "--receipt", "execution.json"], capture_output=True, text=True)
        assert proc.returncode == 2 and not (root / "execution.json").exists()


def main():
    test_identity_rejects_isolated_self_reports()
    test_shared_production_chain_and_copied_producer_rejection()
    test_shared_copied_runner_rejection()
    test_adversarial_runner_failure_is_fail_closed()
    print("PASS: copied-hash identity self-reports, producers and runners blocked; real/failure paths verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
