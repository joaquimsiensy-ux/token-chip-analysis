#!/usr/bin/env python3
"""Batch 17 G8 identity gate chain-alias normalization regressions."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [
    str(ROOT / "scripts/report"),
    str(ROOT / "scripts/solana"),
    str(ROOT / "scripts/lib"),
    str(ROOT / "scripts/tests"),
]

import entity_identity_gate as identity_gate  # noqa: E402
from identity_snapshot_receipt import emit_solana  # noqa: E402
from test_round4_identity_emitter import run_solana  # noqa: E402


MINT = "mint"
SLOT = 123
TOTAL_SUPPLY_RAW = 100
CHAIN_ERROR = "chain 与 state 不绑定: gate='sol' state='solana'"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def prepare_real_solana(root: Path) -> tuple[Path, Path]:
    snapshot, meta = run_solana(root)
    receipt = snapshot.parent / "identity_holders_receipt.json"
    emit_solana(MINT, SLOT, snapshot, meta, TOTAL_SUPPLY_RAW, receipt)
    return snapshot, receipt


def build_and_validate(
        snapshot: Path, receipt: Path, *, state_chain: str | None,
        token_chain: str) -> list[str]:
    case_dir = snapshot.parent
    state_path = case_dir / "analysis-state.json"
    state = {"token": {"chain": token_chain}, "whale_groups": []}
    if state_chain is not None:
        state["chain"] = state_chain
    write_json(state_path, state)

    gate_path = case_dir / "identity_gate.json"
    built = identity_gate.build(
        state_path, "sol", snapshot_path=snapshot, out_path=gate_path,
        total_supply_raw=TOTAL_SUPPLY_RAW,
        snapshot_receipt_path=receipt,
    )
    for row in built["rows"]:
        if row["flag"]:
            row["resolution"] = "批17夹具：已核对真实 Solana owner 身份来源"
    write_json(gate_path, built)
    return identity_gate.validate_gate(gate_path, state_path)


def test_r1_solana_alias_state_is_accepted() -> None:
    with tempfile.TemporaryDirectory(prefix="batch17-r1-", dir="/private/tmp") as raw:
        snapshot, receipt = prepare_real_solana(Path(raw))
        errors = build_and_validate(
            snapshot, receipt, state_chain="solana", token_chain="solana")
        if errors:
            assert errors == [CHAIN_ERROR], f"R1 出现非别名错误: {errors!r}"
            raise AssertionError(f"R1 errors 原文: {errors!r}")


def test_n1_canonical_state_stays_accepted() -> None:
    with tempfile.TemporaryDirectory(prefix="batch17-n1-", dir="/private/tmp") as raw:
        snapshot, receipt = prepare_real_solana(Path(raw))
        errors = build_and_validate(
            snapshot, receipt, state_chain="sol", token_chain="sol")
        assert errors == [], errors


def test_n2_wrong_chain_stays_rejected_with_raw_values() -> None:
    with tempfile.TemporaryDirectory(prefix="batch17-n2-", dir="/private/tmp") as raw:
        snapshot, receipt = prepare_real_solana(Path(raw))
        errors = build_and_validate(
            snapshot, receipt, state_chain="bsc", token_chain="bsc")
        expected = "chain 与 state 不绑定: gate='sol' state='bsc'"
        assert errors == [expected], errors


def test_n3_token_chain_fallback_accepts_alias() -> None:
    with tempfile.TemporaryDirectory(prefix="batch17-n3-", dir="/private/tmp") as raw:
        snapshot, receipt = prepare_real_solana(Path(raw))
        errors = build_and_validate(
            snapshot, receipt, state_chain=None, token_chain="solana")
        assert errors == [], errors


TESTS = [
    ("R1 Solana alias state", test_r1_solana_alias_state_is_accepted),
    ("N1 canonical state", test_n1_canonical_state_stays_accepted),
    ("N2 wrong chain", test_n2_wrong_chain_stays_rejected_with_raw_values),
    ("N3 token.chain fallback", test_n3_token_chain_fallback_accepts_alias),
]


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv not in ([], ["--r1"]):
        raise SystemExit("usage: test_batch17_identity_chain_alias.py [--r1]")
    selected = TESTS[:1] if argv == ["--r1"] else TESTS
    failed = []
    for name, test in selected:
        try:
            test()
            print(f"PASS {name}")
        except Exception as exc:  # noqa: BLE001 - standalone regression runner
            failed.append((name, exc))
            print(f"FAIL {name}: {exc}")
    if failed:
        print(f"FAIL batch17 identity chain alias: {len(failed)}/{len(selected)}")
        return 1
    print(f"PASS batch17 identity chain alias: {len(selected)}/{len(selected)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
