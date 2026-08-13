#!/usr/bin/env python3
"""2026-08-13 修复批 A：F-01/F-02 先红后绿回归。"""
from __future__ import annotations

import contextlib
import hashlib
import importlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [
    str(ROOT / "scripts/lib"),
    str(ROOT / "scripts/report"),
    str(ROOT / "scripts/evm"),
    str(ROOT / "scripts/tests"),
]

import accounting_gate  # noqa: E402
import shared_release_receipt as shared  # noqa: E402
import supply_truth_gate as supply  # noqa: E402


TOKEN = "0x" + "9" * 40
TARGET = {"chain": "eth", "token": TOKEN, "as_of_block": 123}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_ref(root: Path, name: str) -> dict:
    path = root / name
    return {"path": name, "size": path.stat().st_size, "sha256": sha256(path)}


@contextlib.contextmanager
def chdir(path: Path):
    old = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


class SupplyPool:
    def __init__(self, total_supply: int):
        self.total_supply = total_supply

    def call(self, method, params):
        assert method == "eth_call", (method, params)
        return {"ok": True, "result": hex(self.total_supply)}


def write_waiver(root: Path, *, approved=10000, mutate=None) -> Path:
    (root / "evidence.txt").write_text("human adjudication evidence\n", encoding="utf-8")
    waiver = {
        "schema": "tolerance-waiver/v1",
        "approved_tolerance_bps": approved,
        "approved_by": "risk-committee@example.test",
        "user_decided_at_utc": "2026-08-13T12:00:00Z",
        "target": dict(TARGET),
        "replay_stats": file_ref(root, "replay_stats.json"),
        "evidence_refs": [file_ref(root, "evidence.txt")],
        "reason": "特殊迁移币已人工核对，批准本次供给真值容差。",
    }
    if mutate:
        mutate(waiver)
    path = root / "waiver.json"
    path.write_text(json.dumps(waiver, ensure_ascii=False), encoding="utf-8")
    return path


def run_supply(root: Path, *, tolerance=10000, waiver: Path | None = None,
               exploration=False):
    stats = root / "replay_stats.json"
    stats.write_text(json.dumps({"mint_total_raw": "1", "burn_total_raw": "0"}),
                     encoding="utf-8")
    out = root / "supply_truth.json"
    argv = [
        "--chain", "eth", "--token", TOKEN, "--as-of-block", "123",
        "--rpc", "offline://fixture", "--tolerance-bps", str(tolerance),
        "--out", str(out),
    ]
    if exploration:
        argv += ["--exploration", "--replay-net-raw", "1"]
    else:
        argv += ["--replay-stats", "replay_stats.json"]
    if waiver is not None:
        argv += ["--tolerance-waiver", str(waiver)]
    stderr = __import__("io").StringIO()
    with chdir(root), mock.patch.object(
            supply, "attested_rpc_pool", return_value=SupplyPool(100)), \
            contextlib.redirect_stderr(stderr):
        try:
            rc = supply.main(argv)
        except SystemExit as exc:
            rc = int(exc.code or 0)
    receipt = json.loads(out.read_text(encoding="utf-8")) if out.exists() else None
    return rc, receipt, stderr.getvalue()


def expect_waiver_rejection(root: Path, mutate, needle: str):
    stats = root / "replay_stats.json"
    stats.write_text(json.dumps({"mint_total_raw": "1", "burn_total_raw": "0"}),
                     encoding="utf-8")
    waiver = write_waiver(root, mutate=mutate)
    rc, receipt, stderr = run_supply(root, waiver=waiver)
    assert rc == 2 and receipt is None, (rc, receipt, stderr)
    assert needle.lower() in stderr.lower(), stderr


def test_f01_no_code_failure_receipt_keeps_tip():
    class NoCodeRpc:
        n_calls = 0

        def call(self, method, params):
            self.n_calls += 1
            if method == "eth_blockNumber":
                return hex(100)
            if method == "eth_getCode":
                return "0x"
            raise AssertionError((method, params))

    with tempfile.TemporaryDirectory(prefix="batch-a-f01-no-code-", dir="/private/tmp") as raw:
        root = Path(raw)
        out = root / "accounting_mode.json"
        argv = ["accounting_gate.py", "--chain", "eth", "--token", TOKEN,
                "--rpc", "offline://fixture", "--as-of-block", "1",
                "--out", str(out)]
        with mock.patch.object(accounting_gate, "Rpc", return_value=NoCodeRpc()), \
                mock.patch.object(accounting_gate.os.path, "exists", return_value=False), \
                mock.patch.object(sys, "argv", argv):
            try:
                accounting_gate.main()
            except SystemExit as exc:
                assert exc.code == 1
            else:
                raise AssertionError("无代码失败路径没有退出")
        receipt = json.loads(out.read_text(encoding="utf-8"))
        assert receipt["as_of_block"] == 1
        assert receipt["tip_block"] == 100
        assert receipt["model_probe_block"] == 100


def _retarget_evm_case(root: Path, as_of: int, tip: int | None):
    accounting = json.loads((root / "accounting_mode.json").read_text())
    accounting["as_of_block"] = as_of
    accounting["model_probe_block"] = tip
    if tip is None:
        accounting.pop("tip_block", None)
    else:
        accounting["tip_block"] = tip
    (root / "accounting_mode.json").write_text(json.dumps(accounting), encoding="utf-8")

    target = {"chain": "bsc", "token": "0xtoken", "as_of_block": as_of}
    recon = json.loads((root / "reconciliation_report.json").read_text())
    recon["target"] = target
    for item in recon["checks"].values():
        receipt_path = root / item["receipt"]["path"]
        receipt = json.loads(receipt_path.read_text())
        receipt["target"] = target
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        item["receipt"]["sha256"] = sha256(receipt_path)
    (root / "reconciliation_report.json").write_text(json.dumps(recon), encoding="utf-8")
    adversarial = json.loads((root / "adversarial_review.json").read_text())
    adversarial["target"] = target
    (root / "adversarial_review.json").write_text(json.dumps(adversarial), encoding="utf-8")


def test_f01_shared_evm_timing_and_legal_dual_time():
    from test_audit_release_gate import build_case

    with tempfile.TemporaryDirectory(prefix="batch-a-f01-missing-tip-", dir="/private/tmp") as raw:
        root = Path(raw)
        build_case(root, historical=False)
        _retarget_evm_case(root, 123, None)
        try:
            shared.validate_sources(root)
        except ValueError as exc:
            assert "tip_block" in str(exc), exc
        else:
            raise AssertionError("缺 tip_block 的 EVM accounting 收据被接受")

    with tempfile.TemporaryDirectory(prefix="batch-a-f01-inverted-", dir="/private/tmp") as raw:
        root = Path(raw)
        build_case(root, historical=False)
        _retarget_evm_case(root, 101, 100)
        try:
            shared.validate_sources(root)
        except ValueError as exc:
            assert "tip_block" in str(exc), exc
        else:
            raise AssertionError("EVM as_of_block > tip_block 被接受")

    with tempfile.TemporaryDirectory(prefix="batch-a-f01-legal-", dir="/private/tmp") as raw:
        root = Path(raw)
        build_case(root, historical=False)
        _retarget_evm_case(root, 1, 100)
        assert shared.validate_sources(root)["as_of_block"] == 1


def test_f01_solana_not_subject_to_tip_check():
    from test_r9_batch3_release_guards import (
        AccountingPassed, build_case, validate_accounting_prefix,
    )

    with tempfile.TemporaryDirectory(prefix="batch-a-f01-solana-", dir="/private/tmp") as raw:
        root = Path(raw)
        build_case(root)
        accounting = json.loads((root / "accounting_mode.json").read_text())
        accounting.pop("tip_block", None)
        accounting.pop("model_probe_block", None)
        (root / "accounting_mode.json").write_text(json.dumps(accounting), encoding="utf-8")
        try:
            validate_accounting_prefix(shared, root)
        except AccountingPassed:
            pass
        else:
            raise AssertionError("Solana accounting 被错误套用 EVM tip_block 检查")


def test_f02_formal_cap_and_exploration():
    with tempfile.TemporaryDirectory(prefix="batch-a-f02-cap-", dir="/private/tmp") as raw:
        rc, receipt, stderr = run_supply(Path(raw))
        assert rc == 2 and receipt is None, (rc, receipt, stderr)
    with tempfile.TemporaryDirectory(prefix="batch-a-f02-negative-", dir="/private/tmp") as raw:
        rc, receipt, stderr = run_supply(Path(raw), tolerance=-1)
        assert rc == 2 and receipt is None and "0 <=" in stderr, (rc, receipt, stderr)
    with tempfile.TemporaryDirectory(prefix="batch-a-f02-explore-", dir="/private/tmp") as raw:
        rc, receipt, stderr = run_supply(Path(raw), exploration=True)
        assert rc == 0 and receipt["verdict"] == "PASS", (rc, receipt, stderr)


def test_f02_waiver_negatives_and_failures():
    variants = [
        (lambda w: w.pop("approved_by"), "必填"),
        (lambda w: w.update(approved_tolerance_bps=9999), "批准"),
        (lambda w: w["target"].update(token="0xwrong"), "target"),
        (lambda w: w["replay_stats"].update(sha256="0" * 64), "replay_stats"),
        (lambda w: w["evidence_refs"][0].update(sha256="0" * 64), "evidence"),
    ]
    for index, (mutate, needle) in enumerate(variants):
        with tempfile.TemporaryDirectory(
                prefix=f"batch-a-f02-waiver-{index}-", dir="/private/tmp") as raw:
            expect_waiver_rejection(Path(raw), mutate, needle)

    with tempfile.TemporaryDirectory(prefix="batch-a-f02-missing-", dir="/private/tmp") as raw:
        root = Path(raw)
        rc, receipt, stderr = run_supply(root, waiver=root / "missing.json")
        assert rc == 2 and receipt is None and "不存在" in stderr, (rc, stderr)

    with tempfile.TemporaryDirectory(prefix="batch-a-f02-json-", dir="/private/tmp") as raw:
        root = Path(raw)
        broken = root / "broken.json"
        broken.write_text("{broken", encoding="utf-8")
        rc, receipt, stderr = run_supply(root, waiver=broken)
        assert rc == 2 and receipt is None and "JSON" in stderr, (rc, stderr)


def test_f02_valid_waiver_and_shared_recompute():
    with tempfile.TemporaryDirectory(prefix="batch-a-f02-valid-", dir="/private/tmp") as raw:
        root = Path(raw)
        (root / "replay_stats.json").write_text(
            json.dumps({"mint_total_raw": "1", "burn_total_raw": "0"}), encoding="utf-8")
        waiver = write_waiver(root)
        rc, receipt, stderr = run_supply(root, waiver=waiver)
        assert rc == 0 and receipt["verdict"] == "PASS", (rc, receipt, stderr)
        assert "tolerance_waiver" in receipt["inputs"]
        item = {"status": "PASS", "exit_code": 0,
                "receipt": {"path": "supply_truth.json", "size": (root / "supply_truth.json").stat().st_size,
                            "sha256": sha256(root / "supply_truth.json")}}
        shared.validate_reconciliation_check(root, "supply_truth", item, TARGET, "evm")

        without_waiver = json.loads(json.dumps(receipt))
        without_waiver["inputs"].pop("tolerance_waiver")
        (root / "supply_truth.json").write_text(json.dumps(without_waiver), encoding="utf-8")
        item["receipt"]["size"] = (root / "supply_truth.json").stat().st_size
        item["receipt"]["sha256"] = sha256(root / "supply_truth.json")
        try:
            shared.validate_reconciliation_check(root, "supply_truth", item, TARGET, "evm")
        except ValueError as exc:
            assert "waiver" in str(exc).lower(), exc
        else:
            raise AssertionError("共享校验接受了未绑定 waiver 的高容差收据")

        receipt["tolerance_bps"] = 10
        (root / "supply_truth.json").write_text(json.dumps(receipt), encoding="utf-8")
        item["receipt"]["size"] = (root / "supply_truth.json").stat().st_size
        item["receipt"]["sha256"] = sha256(root / "supply_truth.json")
        try:
            shared.validate_reconciliation_check(root, "supply_truth", item, TARGET, "evm")
        except ValueError as exc:
            assert "重算" in str(exc), exc
        else:
            raise AssertionError("共享校验接受了与重算值矛盾的 primary_verdict")


def test_f02_waiver_swap_integrity_counterexample():
    script = (ROOT / "maintenance/repair-20260813-sixlens/counterexamples"
              / "waiver_swap_integrity.py")
    completed = subprocess.run(
        [sys.executable, str(script)], cwd=ROOT, text=True,
        capture_output=True, check=False,
    )
    assert completed.returncode == 0, (completed.stdout, completed.stderr)
    # 变长替换命中 size 一项；等长替换（字节数分毫不差）只能由 sha256 拦下。
    assert "input tolerance_waiver size mismatch" in completed.stdout, completed.stdout
    assert "input tolerance_waiver hash mismatch" in completed.stdout, completed.stdout


def test_f02_tolerance_cap_uses_producer_constant():
    assert (shared.FORMAL_TOLERANCE_BPS_MAX
            == supply.FORMAL_TOLERANCE_BPS_MAX)


def main():
    tests = [
        test_f01_no_code_failure_receipt_keeps_tip,
        test_f01_shared_evm_timing_and_legal_dual_time,
        test_f01_solana_not_subject_to_tip_check,
        test_f02_formal_cap_and_exploration,
        test_f02_waiver_negatives_and_failures,
        test_f02_valid_waiver_and_shared_recompute,
        test_f02_waiver_swap_integrity_counterexample,
        test_f02_tolerance_cap_uses_producer_constant,
    ]
    failed = []
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001 - 测试汇总需继续跑完两条 finding。
            failed.append((test.__name__, f"{type(exc).__name__}: {exc}"))
            print(f"FAIL {test.__name__}: {type(exc).__name__}: {exc}")
        else:
            print(f"PASS {test.__name__}")
    if failed:
        print(f"BATCH A FAIL {len(failed)}/{len(tests)}")
        return 1
    print(f"PASS batch A F-01/F-02 regressions {len(tests)}/{len(tests)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
