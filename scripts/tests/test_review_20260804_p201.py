#!/usr/bin/env python3
"""P2-01 + supplement: total-supply shares and Arbitrum identity-gate support."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "report"))
import entity_identity_gate as gate

A = "0x" + "a" * 40
B = "0x" + "b" * 40


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture(root, *, complete=True, receipt_supply="100"):
    state = root / "analysis-state.json"
    state.write_text(json.dumps({"chain": "arbitrum", "whale_groups": [
        {"entity_id": "e1", "addresses": [A]}]}))
    from identity_gate_fixture import write_binding
    total, binding = write_binding(root, {A: 50, B: 50}, chain="arbitrum")
    snapshot = root / binding["snapshot_file"]
    receipt = root / binding["receipt_file"]
    if not complete or receipt_supply != "100":
        obj = json.loads(receipt.read_text())
        obj["complete_owner_universe"] = complete
        obj["total_supply_raw"] = receipt_supply
        receipt.write_text(json.dumps(obj))
    return state, snapshot, receipt


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        state, snapshot, receipt = fixture(root)
        built = gate.build(str(state), "arbitrum", str(snapshot), str(root / "gate.json"),
                           total_supply_raw="100", snapshot_receipt_path=str(receipt))
        rows = {x["address"]: x for x in built["rows"]}
        assert rows[A]["share_pct"] == 50.0 and rows[B]["share_pct"] == 50.0
        assert built["share_basis"] == "total_supply" and built["total_supply_raw"] == "100"
        for row in built["rows"]:
            if row["flag"]:
                row["resolution"] = "fixture: checked Arbitrum identity"
        (root / "gate.json").write_text(json.dumps(built))
        assert not gate.validate_gate(str(root / "gate.json"), str(state))

    for complete, receipt_supply in ((False, "100"), (True, "99")):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            state, snapshot, receipt = fixture(
                root, complete=complete, receipt_supply=receipt_supply)
            try:
                gate.build(str(state), "arbitrum", str(snapshot), str(root / "gate.json"),
                           total_supply_raw="100", snapshot_receipt_path=str(receipt))
            except ValueError:
                pass
            else:
                raise AssertionError("incomplete/mismatched snapshot receipt must block")
    print("PASS: P2-01 total-supply share binding + Arbitrum G8 support")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
