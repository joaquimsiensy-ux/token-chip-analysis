#!/usr/bin/env python3
"""Batch 18 shared reconciliation witness/provider regressions."""
from __future__ import annotations

import inspect
import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts/report"), str(ROOT / "scripts/lib"),
                str(ROOT / "scripts/tests")]

import audit_release_gate as gate  # noqa: E402
import shared_release_receipt as shared  # noqa: E402
from test_audit_release_gate import build_case as build_evm_case  # noqa: E402
from test_batch15_three_ledgers_frozen import (  # noqa: E402
    build_dynamic_integration_case,
    write_json,
)


RECON_MUTATION_ERRORS = [
    "共享发布 receipt: shared receipt input hashes changed",
]
OWNERS_MUTATION_ERRORS = [
    "正式发布跨分区 target 不一致: as_of_block 声明矛盾: "
    "accounting_mode.json.as_of_block=500, "
    "reconciliation_report.json.target.as_of_block=501, "
    "shared_release_receipt.json.target.as_of_block=500, "
    "identity_bridge/data/identity_holders_receipt.json.as_of_block=500",
    "共享发布 receipt: observation bundle holder_outputs.owners "
    "sha256/size mismatch: holders_owners.json",
    "记账模型公共 validator 未通过: observation bundle holder_outputs.owners "
    "sha256/size mismatch: holders_owners.json",
    "受控对账公共深验失败: reconciliation exact_reconcile receipt envelope invalid: "
    "input holders_owners size mismatch；存量案例须重跑对应生产者获取当前回执",
    "发布期序列 cutoff 目标: accounting as_of_block=500/wrapper 501："
    "冻结态深验未通过，无法确定对账时点: reconciliation exact_reconcile receipt "
    "envelope invalid: input holders_owners size mismatch；"
    "存量案例须重跑对应生产者获取当前回执",
]


def test_r1_validate_bundle_accepts_provider_keyword() -> None:
    with tempfile.TemporaryDirectory(prefix="batch18-witness-r1-", dir="/private/tmp") as raw:
        errors = shared.validate_bundle(
            Path(raw), reconciliation_provider=lambda: None)
        assert isinstance(errors, list), errors


def test_n1_public_alias_and_no_runtime_replacement() -> None:
    assert shared.bound_case_ref is shared._bound_case_ref
    source = inspect.getsource(gate)
    assert "_bound_case_ref" not in source
    assert "shared_release_receipt.validate_reconciliation_report =" not in source


def test_n2_dynamic_provider_and_default_each_deep_validate_once() -> None:
    for injected in (True, False):
        with tempfile.TemporaryDirectory(
                prefix=f"batch18-witness-n2-{int(injected)}-",
                dir="/private/tmp") as raw:
            root = Path(raw)
            build_dynamic_integration_case(root)
            original = shared.validate_reconciliation_report
            calls = 0

            def counted(*args, **kwargs):
                nonlocal calls
                calls += 1
                return original(*args, **kwargs)

            try:
                shared.validate_reconciliation_report = counted
                if injected:
                    errors = shared.validate_bundle(
                        root,
                        reconciliation_provider=lambda: (
                            shared.witness_reconciliation_report(root)),
                    )
                else:
                    errors = shared.validate_bundle(root)
            finally:
                shared.validate_reconciliation_report = original
            assert errors == [], errors
            assert calls == 1, (injected, calls)


def test_n3_evm_ignores_solana_provider_and_still_deep_validates() -> None:
    with tempfile.TemporaryDirectory(prefix="batch18-witness-n3-", dir="/private/tmp") as raw:
        root = Path(raw)
        build_evm_case(root)
        original = shared.validate_reconciliation_report
        calls = 0
        provider_calls = 0

        def counted(*args, **kwargs):
            nonlocal calls
            calls += 1
            return original(*args, **kwargs)

        def forbidden_provider():
            nonlocal provider_calls
            provider_calls += 1
            raise AssertionError("EVM 不得消费 Solana reconciliation provider")

        try:
            shared.validate_reconciliation_report = counted
            errors = shared.validate_bundle(
                root, reconciliation_provider=forbidden_provider)
        finally:
            shared.validate_reconciliation_report = original
        assert errors == [], errors
        assert calls == 1, calls
        assert provider_calls == 0, provider_calls


def test_n4_forged_stale_and_throwing_providers_fail_closed() -> None:
    with tempfile.TemporaryDirectory(prefix="batch18-witness-n4a-", dir="/private/tmp") as raw_a, \
            tempfile.TemporaryDirectory(prefix="batch18-witness-n4b-", dir="/private/tmp") as raw_b:
        root = Path(raw_a)
        other = Path(raw_b)
        report_path, _ = build_dynamic_integration_case(root)
        build_dynamic_integration_case(other)
        witness = shared.witness_reconciliation_report(root)
        other_witness = shared.witness_reconciliation_report(other)

        naked = shared.validate_bundle(
            root, reconciliation_provider=lambda: (witness.target, witness.receipts))
        wrong_root = shared.validate_bundle(
            root, reconciliation_provider=lambda: other_witness)
        assert any("reconciliation witness 无效/过期" in item for item in naked), naked
        assert any("reconciliation witness 无效/过期" in item for item in wrong_root), wrong_root

        sentinel = "batch18-provider-sentinel"
        original = shared.validate_reconciliation_report

        def explode(*_args, **_kwargs):
            raise RuntimeError(sentinel)

        try:
            shared.validate_reconciliation_report = explode
            default_errors = shared.validate_bundle(root)
            gate_errors = gate.run(root, report_path, profile="new-analysis")
        finally:
            shared.validate_reconciliation_report = original
        provider_errors = shared.validate_bundle(
            root, reconciliation_provider=lambda: explode())
        assert default_errors == provider_errors == [sentinel], (
            default_errors, provider_errors)
        assert f"共享发布 receipt: {sentinel}" in gate_errors, gate_errors

        report = root / "reconciliation_report.json"
        report.write_text(report.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        stale = shared.validate_bundle(
            root, reconciliation_provider=lambda: witness)
        assert any("reconciliation witness 无效/过期" in item for item in stale), stale


def test_n11_gate_errors_are_byte_for_byte_unchanged() -> None:
    for mutation, expected in (
            ("reconciliation_report", RECON_MUTATION_ERRORS),
            ("holders_owners", OWNERS_MUTATION_ERRORS)):
        with tempfile.TemporaryDirectory(
                prefix=f"batch18-witness-n11-{mutation}-",
                dir="/private/tmp") as raw:
            root = Path(raw)
            report, _ = build_dynamic_integration_case(root)
            assert gate.run(root, report, profile="new-analysis") == []
            if mutation == "reconciliation_report":
                path = root / "reconciliation_report.json"
                path.write_text(path.read_text(encoding="utf-8") + "\n",
                                encoding="utf-8")
            else:
                write_json(root / "data/holders_owners.json",
                           {"ownersol1": 61, "ownersol2": 39})
            errors = gate.run(root, report, profile="new-analysis")
            assert errors == expected, json.dumps(errors, ensure_ascii=False)
            assert all(item.startswith("共享发布 receipt: ")
                       for item in errors[:1] if mutation == "reconciliation_report")


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv not in ([], ["--r1"]):
        raise SystemExit("usage: test_batch18_shared_bundle_witness.py [--r1]")
    tests = [test_r1_validate_bundle_accepts_provider_keyword]
    if not argv:
        tests += [
            test_n1_public_alias_and_no_runtime_replacement,
            test_n2_dynamic_provider_and_default_each_deep_validate_once,
            test_n3_evm_ignores_solana_provider_and_still_deep_validates,
            test_n4_forged_stale_and_throwing_providers_fail_closed,
            test_n11_gate_errors_are_byte_for_byte_unchanged,
        ]
    failed = []
    for test in tests:
        try:
            test()
        except Exception as exc:
            failed.append((test.__name__, exc))
            print(f"FAIL {test.__name__}: {type(exc).__name__}: {exc}")
        else:
            print(f"PASS {test.__name__}")
    if failed:
        print(f"FAIL batch18 shared bundle witness: {len(failed)}/{len(tests)}")
        return 1
    print(f"PASS batch18 shared bundle witness: {len(tests)}/{len(tests)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
