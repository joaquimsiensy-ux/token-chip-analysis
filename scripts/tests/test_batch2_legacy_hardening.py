#!/usr/bin/env python3
"""B2F-G1 regressions for legacy handoff admission and formal-release blocking."""
from __future__ import annotations

import importlib
import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import test_handoff_manifest as handoff_fixture  # noqa: E402


def rewrite_legacy(case_dir: Path, schema: str, *, keep_reconciliation: bool) -> dict:
    path = case_dir / "handoff_manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["consumer_min_schema"] = schema
    if not keep_reconciliation:
        manifest["artifacts"] = [
            item for item in manifest["artifacts"]
            if item.get("path") != "reconciliation_report.json"
        ]
        manifest["gates"].pop("reconciliation_four_checks", None)
        (case_dir / "reconciliation_report.json").unlink()
    path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return manifest


def generate_case(case_dir: Path, *, chain="bsc", token="0x0") -> dict:
    handoff_fixture.make_case(str(case_dir), chain=chain, token=token)
    result = handoff_fixture.run([
        "generate", "--case-dir", str(case_dir), "--status", "READY",
        *handoff_fixture.GEN,
    ])
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads((case_dir / "handoff_manifest.json").read_text(encoding="utf-8"))


def test_b2f_lg_01_robinhood_legacy_rejected(root: Path):
    case_dir = root / "lg01"
    case_dir.mkdir()
    generate_case(case_dir)
    manifest = rewrite_legacy(case_dir, "handoff/v2", keep_reconciliation=False)
    manifest["scope"]["chains"] = ["robinhood"]
    (case_dir / "handoff_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    result = handoff_fixture.run([
        "verify", "--case-dir", str(case_dir), "--legacy-read-only",
    ])
    assert result.returncode != 0, "B2F-LG-01: Robinhood legacy READY bypassed admission"
    for index, (chains, contract) in enumerate((
            ([], "0x0"), (["bsc", "eth"], "0x0"), (["bsc"], "")), start=1):
        invalid = root / f"lg01-scope-{index}"
        invalid.mkdir()
        generate_case(invalid)
        bad = rewrite_legacy(invalid, "handoff/v2", keep_reconciliation=False)
        bad["scope"].update({"chains": chains, "contract": contract})
        (invalid / "handoff_manifest.json").write_text(
            json.dumps(bad, ensure_ascii=False), encoding="utf-8")
        rejected = handoff_fixture.run([
            "verify", "--case-dir", str(invalid), "--legacy-read-only",
        ])
        assert rejected.returncode != 0, (chains, contract, rejected.stdout)


def test_b2f_lg_02_triple_mismatch_rejected(root: Path):
    case_dir = root / "lg02"
    case_dir.mkdir()
    generate_case(case_dir)
    manifest = rewrite_legacy(case_dir, "handoff/v2", keep_reconciliation=True)
    manifest["scope"]["chains"] = ["robinhood"]
    manifest["scope"]["contract"] = "0xwrong-token"
    (case_dir / "handoff_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    result = handoff_fixture.run([
        "verify", "--case-dir", str(case_dir), "--legacy-read-only",
    ])
    assert result.returncode != 0, "B2F-LG-02: chain/token/wrapper triple mismatch passed"


def test_b2f_lg_03_valid_frozen_v1_v2_stay_readable(root: Path):
    for schema in ("handoff/v1", "handoff/v2"):
        case_dir = root / schema.replace("/", "-")
        case_dir.mkdir()
        generate_case(case_dir)
        rewrite_legacy(case_dir, schema, keep_reconciliation=False)
        result = handoff_fixture.run([
            "verify", "--case-dir", str(case_dir), "--legacy-read-only",
        ])
        assert result.returncode == 0, (schema, result.stdout, result.stderr)


def test_b2f_lg_04_strict_paths_do_not_fall_back(root: Path):
    case_dir = root / "lg04"
    case_dir.mkdir()
    generate_case(case_dir)
    rewrite_legacy(case_dir, "handoff/v2", keep_reconciliation=False)
    strict = handoff_fixture.run(["verify", "--case-dir", str(case_dir)])
    assert strict.returncode != 0 and "legacy-read-only" in strict.stdout
    handoff_fixture.setup_freezeable(str(case_dir))
    frozen = handoff_fixture.run([
        "freeze", "--case-dir", str(case_dir), *handoff_fixture.FRZ,
    ])
    assert frozen.returncode != 0, "B2F-LG-04: freeze accepted legacy manifest"


def test_oba_legacy_receipt_blocks_formal_audit(root: Path):
    audit_fixture = importlib.import_module("test_audit_release_gate")
    case_dir = root / "oba"
    case_dir.mkdir()
    report = audit_fixture.build_case(case_dir)
    (case_dir / "legacy_readonly_receipt.json").write_text(
        json.dumps({"schema": "legacy-readonly-receipt/v1"}), encoding="utf-8")
    errors = audit_fixture.gate.run(case_dir, report)
    assert any("legacy" in item.lower() or "只读降级" in item for item in errors), errors


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        tests = (
            test_b2f_lg_01_robinhood_legacy_rejected,
            test_b2f_lg_02_triple_mismatch_rejected,
            test_b2f_lg_03_valid_frozen_v1_v2_stay_readable,
            test_b2f_lg_04_strict_paths_do_not_fall_back,
            test_oba_legacy_receipt_blocks_formal_audit,
        )
        failures = []
        for test in tests:
            try:
                test(root)
            except Exception as exc:  # collect all red/green evidence in one run
                failures.append(f"{test.__name__}: {exc}")
        if failures:
            raise AssertionError("\n".join(failures))
    print("PASS B2F-G1: B2F-LG-01..04 + OB-A legacy formal-release guard")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
