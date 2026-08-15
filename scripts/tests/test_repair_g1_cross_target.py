#!/usr/bin/env python3
"""F-03 test-only：正式案跨分区 target 等式反例与防误伤例。"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
GATE_PATH = HERE.parent / "report" / "audit_release_gate.py"
BASE_TEST_PATH = HERE / "test_audit_release_gate.py"
sys.path.insert(0, str(HERE))

from formal_ready_test_harness import test_vertical_slices


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


gate = _load_module("repair_g1_cross_target_gate", GATE_PATH)
fixture = _load_module("repair_g1_cross_target_fixture", BASE_TEST_PATH)
_gate_run = gate.run


def _run_with_test_vertical_slices(*args, **kwargs):
    with test_vertical_slices():
        return _gate_run(*args, **kwargs)


gate.run = _run_with_test_vertical_slices

CASE_TOKEN = fixture.CASE_TOKEN
ALT_TOKEN = "0x" + "b" * 40
SOL_MINT = "So11111111111111111111111111111111111111112"
SOL_MINT_CASE_VARIANT = "so11111111111111111111111111111111111111112"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    return path


def file_ref(root: Path, path: Path) -> dict:
    return {
        "path": path.relative_to(root).as_posix(),
        "size": path.stat().st_size,
        "sha256": sha(path),
    }


def refresh_identity_bindings(root: Path) -> None:
    """Keep the hand-written schema fixture's state/receipt byte bindings exact."""
    gate_path = root / "identity_gate.json"
    if not gate_path.is_file():
        return
    identity = read_json(gate_path)
    state_path = root / identity["state_file"]
    receipt_path = root / identity["snapshot_binding"]["receipt_file"]
    identity["state_sha256"] = sha(state_path)
    identity["snapshot_binding"]["receipt_sha256"] = sha(receipt_path)
    receipt = read_json(receipt_path)
    identity["snapshot_binding"]["as_of_block"] = receipt["as_of_block"]
    identity["snapshot_binding"]["adapter"] = receipt["adapter"]
    write_json(gate_path, identity)


def refresh_a5_a4_binding(root: Path) -> None:
    a5_path = root / "a5_report_seal.json"
    if not a5_path.is_file():
        return
    a5 = read_json(a5_path)
    a5["a4_seal"] = file_ref(root, root / "a4_seal.json")
    write_json(a5_path, a5)


def add_conclusion_partition(root: Path, report: Path, *, chain="bsc",
                             token=CASE_TOKEN, as_of_block=123) -> None:
    """Add unit-schema fixtures whose byte bindings mirror the real producers.

    These are deliberately hand-written release-gate fixtures.  They test how
    audit_release_gate interprets bytes; they do not impersonate a successful
    end-to-end identity replay or A5 compilation.
    """
    state = {
        "chain": chain,
        "token": {"chain": chain, "address": token},
        "whale_groups": [],
    }
    state_path = write_json(root / "analysis-state.json", state)
    snapshot_path = write_json(root / "identity_holders.json", {
        "0x" + "c" * 40: "100",
    })
    receipt_path = write_json(root / "identity_holders_receipt.json", {
        "schema": "identity-holder-snapshot/v2",
        "status": "PASS",
        "complete_owner_universe": True,
        "producer": {
            "path": "identity_snapshot_receipt.py",
            "sha256": sha(REPO / "scripts/report/identity_snapshot_receipt.py"),
        },
        "adapter": chain,
        "token": token,
        "as_of_block": as_of_block,
        "total_supply_raw": "100",
        "snapshot": {"path": snapshot_path.name, "sha256": sha(snapshot_path)},
        "source": {"kind": "unit-schema-fixture"},
    })
    write_json(root / "identity_gate.json", {
        "schema": "identity_gate_v3",
        "chain": chain,
        "state_file": state_path.name,
        "state_sha256": sha(state_path),
        "share_basis": "total_supply",
        "total_supply_raw": "100",
        "snapshot_binding": {
            "snapshot_file": snapshot_path.name,
            "snapshot_sha256": sha(snapshot_path),
            "receipt_file": receipt_path.name,
            "receipt_sha256": sha(receipt_path),
            "as_of_block": as_of_block,
            "complete_owner_universe": True,
            "receipt_schema": "identity-holder-snapshot/v2",
            "adapter": chain,
        },
        "rows": [{
            "address": "0x" + "c" * 40,
            "entity": "(non-entity big holder)",
            "share_pct": 100.0,
            "label": "unit schema fixture",
            "on_curve": None,
            "flag": "",
            "resolution": "",
        }],
    })
    a4_path = write_json(root / "a4_seal.json", {
        "schema": "a4-seal/v4",
        "verdict": "PASS",
        "chain": chain,
        "workflow_type": "new-analysis",
        "revision": 1,
        "previous_seal": None,
        "charts_dir": "charts/final",
        "claims": [{"id": "C1", "verdict": "CONFIRMED"}],
    })
    write_json(root / "a5_report_seal.json", {
        "schema": "a5-report-seal/v3",
        "status": "PASS",
        "producer": "a5_report_seal.py/v3",
        "chain": chain,
        "workflow_type": "new-analysis",
        "a4_seal": file_ref(root, a4_path),
        "report": file_ref(root, report),
        "images": [],
        "fig1_legend_receipt": {},
        "distribution": {},
        "provenance_flips": {},
    })

    # Supply the new-analysis profile names so the tested run reaches every
    # optional target claimant.  Their deep validators are outside F-03.
    write_json(root / "distribution_scan.json", {})
    write_json(root / "distribution_rounds.json", {})
    write_json(root / "fig1_legend_receipt.json", {})
    write_json(root / "figure2_check_receipt.json", {})


def build_new_analysis_case(root: Path) -> Path:
    report = fixture.build_case(root, historical=False)
    add_conclusion_partition(root, report)
    return report


def set_conclusion_chain(root: Path, chain: str) -> None:
    state = read_json(root / "analysis-state.json")
    state["chain"] = chain
    state["token"]["chain"] = chain
    write_json(root / "analysis-state.json", state)
    identity = read_json(root / "identity_gate.json")
    identity["chain"] = chain
    write_json(root / "identity_gate.json", identity)
    receipt = read_json(root / "identity_holders_receipt.json")
    receipt["adapter"] = chain
    write_json(root / "identity_holders_receipt.json", receipt)
    a4 = read_json(root / "a4_seal.json")
    a4["chain"] = chain
    write_json(root / "a4_seal.json", a4)
    a5 = read_json(root / "a5_report_seal.json")
    a5["chain"] = chain
    write_json(root / "a5_report_seal.json", a5)
    refresh_identity_bindings(root)
    refresh_a5_a4_binding(root)


def set_evidence_target(root: Path, *, chain: str, token: str,
                        as_of_block: int = 123) -> None:
    accounting = read_json(root / "accounting_mode.json")
    accounting.update({"chain": chain, "token": token, "as_of_block": as_of_block})
    write_json(root / "accounting_mode.json", accounting)
    reconciliation = read_json(root / "reconciliation_report.json")
    reconciliation["target"] = {
        "chain": chain, "token": token, "as_of_block": as_of_block,
    }
    write_json(root / "reconciliation_report.json", reconciliation)
    shared = read_json(root / "shared_release_receipt.json")
    shared["target"] = {
        "chain": chain, "token": token, "as_of_block": as_of_block,
    }
    shared["inputs"]["accounting_mode.json"]["sha256"] = sha(
        root / "accounting_mode.json")
    shared["inputs"]["reconciliation_report.json"]["sha256"] = sha(
        root / "reconciliation_report.json")
    write_json(root / "shared_release_receipt.json", shared)


def cross_target_errors(errors: list[str]) -> list[str]:
    """Recognize the dedicated F-03 error class, not existing local validators."""
    found = []
    for item in errors:
        mismatch = any(word in item for word in ("不一致", "矛盾", "漂移"))
        scope = ("跨分区" in item
                 or "正式发布 target" in item
                 or "正式发布目标" in item)
        if mismatch and scope:
            found.append(item)
    return found


def run_new(root: Path, report: Path) -> list[str]:
    return gate.run(root, report, profile="new-analysis")


def r1_conclusion_eth_evidence_bsc(root: Path, report: Path) -> list[str]:
    set_conclusion_chain(root, "eth")
    return run_new(root, report)


def r2_evidence_eth_conclusion_bsc(root: Path, report: Path) -> list[str]:
    set_evidence_target(root, chain="eth", token=CASE_TOKEN)
    return run_new(root, report)


def r3_identity_receipt_other_token(root: Path, report: Path) -> list[str]:
    receipt = read_json(root / "identity_holders_receipt.json")
    receipt["token"] = ALT_TOKEN
    write_json(root / "identity_holders_receipt.json", receipt)
    refresh_identity_bindings(root)
    return run_new(root, report)


def r4_identity_receipt_other_block(root: Path, report: Path) -> list[str]:
    receipt = read_json(root / "identity_holders_receipt.json")
    receipt["as_of_block"] = 456
    write_json(root / "identity_holders_receipt.json", receipt)
    refresh_identity_bindings(root)
    return run_new(root, report)


def r5_only_a5_chain_drifts(root: Path, report: Path) -> list[str]:
    a5 = read_json(root / "a5_report_seal.json")
    a5["chain"] = "eth"
    write_json(root / "a5_report_seal.json", a5)
    return run_new(root, report)


def r6_only_shared_chain_drifts(root: Path, report: Path) -> list[str]:
    shared = read_json(root / "shared_release_receipt.json")
    shared["target"]["chain"] = "eth"
    write_json(root / "shared_release_receipt.json", shared)
    return run_new(root, report)


def r7_state_dual_chain_conflict(root: Path, report: Path) -> list[str]:
    state = read_json(root / "analysis-state.json")
    state["chain"] = "bsc"
    state["token"]["chain"] = "eth"
    write_json(root / "analysis-state.json", state)
    refresh_identity_bindings(root)
    return run_new(root, report)


def r8_solana_mint_case_is_semantic(root: Path, report: Path) -> list[str]:
    set_conclusion_chain(root, "sol")
    state = read_json(root / "analysis-state.json")
    state["token"]["address"] = SOL_MINT_CASE_VARIANT
    write_json(root / "analysis-state.json", state)
    receipt = read_json(root / "identity_holders_receipt.json")
    receipt["token"] = SOL_MINT_CASE_VARIANT
    write_json(root / "identity_holders_receipt.json", receipt)
    refresh_identity_bindings(root)
    set_evidence_target(root, chain="solana", token=SOL_MINT)
    return run_new(root, report)


def g1_solana_alias_is_equal(root: Path, report: Path) -> list[str]:
    set_conclusion_chain(root, "sol")
    state = read_json(root / "analysis-state.json")
    state["token"]["address"] = SOL_MINT
    write_json(root / "analysis-state.json", state)
    receipt = read_json(root / "identity_holders_receipt.json")
    receipt["token"] = SOL_MINT
    write_json(root / "identity_holders_receipt.json", receipt)
    refresh_identity_bindings(root)
    set_evidence_target(root, chain="solana", token=SOL_MINT)
    return run_new(root, report)


def g2_independent_audit_absence(root: Path, report: Path) -> list[str]:
    return gate.run(root, report, profile="independent-audit")


def g3_a4_requires_identity(root: Path, report: Path) -> list[str]:
    (root / "identity_gate.json").unlink()
    (root / "identity_holders_receipt.json").unlink()
    (root / "identity_holders.json").unlink()
    return run_new(root, report)


NEGATIVE_CASES = (
    ("r1", "结论分区 eth、证据分区 bsc", r1_conclusion_eth_evidence_bsc),
    ("r2", "证据分区 eth、结论分区 bsc", r2_evidence_eth_conclusion_bsc),
    ("r3", "identity receipt 同链换 token", r3_identity_receipt_other_token),
    ("r4", "identity receipt 冻结块漂移到 456", r4_identity_receipt_other_block),
    ("r5", "仅 A5 seal.chain 漂移", r5_only_a5_chain_drifts),
    ("r6", "仅 shared receipt target.chain 漂移", r6_only_shared_chain_drifts),
    ("r7", "state.chain 与 state.token.chain 矛盾", r7_state_dual_chain_conflict),
    ("r8", "Solana mint 仅大小写不同", r8_solana_mint_case_is_semantic),
)


def main() -> int:
    failures = []
    for case_id, description, mutate_and_run in NEGATIVE_CASES:
        with tempfile.TemporaryDirectory(prefix=f"repair-g1-{case_id}-") as td:
            root = Path(td)
            report = build_new_analysis_case(root)
            errors = mutate_and_run(root, report)
            matched = cross_target_errors(errors)
            if matched:
                print(f"PASS {case_id}: {description}: {matched[0]}")
            else:
                detail = f"errors={errors[:4]!r}"
                print(f"FAIL {case_id}: 缺跨分区 target 不一致类错误; {detail}")
                failures.append((case_id, description, detail))

    with tempfile.TemporaryDirectory(prefix="repair-g1-g1-") as td:
        root = Path(td)
        report = build_new_analysis_case(root)
        errors = g1_solana_alias_is_equal(root, report)
        matched = cross_target_errors(errors)
        if matched:
            print(f"FAIL g1: solana/sol 归一后被误报: {matched!r}")
            failures.append(("g1", "Solana chain alias 防误伤", repr(matched)))
        else:
            print("PASS g1: accounting.chain=solana 与 identity.chain=sol 未误报")

    with tempfile.TemporaryDirectory(prefix="repair-g1-g2-") as td:
        root = Path(td)
        report = fixture.build_case(root, historical=False)
        errors = g2_independent_audit_absence(root, report)
        if errors:
            print(f"FAIL g2: independent-audit 缺席可选结论资产被误伤: {errors[:4]!r}")
            failures.append(("g2", "independent-audit 缺席不硬要", repr(errors[:4])))
        else:
            print("PASS g2: independent-audit 无 state/identity/A4 仍通过")

    with tempfile.TemporaryDirectory(prefix="repair-g1-g3-") as td:
        root = Path(td)
        report = build_new_analysis_case(root)
        errors = g3_a4_requires_identity(root, report)
        matched = cross_target_errors(errors)
        if matched:
            print(f"PASS g3: A4 在场而 identity 缺席被阻断: {matched[0]}")
        else:
            detail = f"errors={errors[:4]!r}"
            print(f"FAIL g3: A4 在场仍可删除 identity 旁路; {detail}")
            failures.append(("g3", "A4 implies identity receipt", detail))

    if failures:
        print(f"EXPECTED TEST-ONLY RED: {len(failures)} case(s) missing F-03 enforcement")
        return 1
    print("PASS: F-03 cross-partition target equality and absence policy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
