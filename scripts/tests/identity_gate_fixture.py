"""Test-only builder for identity_gate_v3 snapshot bindings."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_binding(root, balances, *, as_of_block=123):
    root = Path(root)
    snapshot = root / "identity_holders.json"
    snapshot.write_text(json.dumps(balances), encoding="utf-8")
    total = sum(balances.values())
    receipt = root / "identity_holders_receipt.json"
    receipt.write_text(json.dumps({
        "schema": "identity-holder-snapshot/v1", "status": "PASS",
        "complete_owner_universe": True, "as_of_block": as_of_block,
        "total_supply_raw": str(total),
        "snapshot": {"path": snapshot.name, "sha256": sha(snapshot)},
    }), encoding="utf-8")
    return str(total), {
        "snapshot_file": snapshot.name, "snapshot_sha256": sha(snapshot),
        "receipt_file": receipt.name, "receipt_sha256": sha(receipt),
        "as_of_block": as_of_block, "complete_owner_universe": True,
    }


def augment_gate(root, gate_obj, *, chain):
    gate = dict(gate_obj)
    rows = [dict(row) for row in gate.get("rows", [])]
    balances = {row["address"]: 100 for row in rows}
    if not balances:
        balances = {"0x" + "f" * 40: 100}
    total, binding = write_binding(root, balances)
    for row in rows:
        row["share_pct"] = round(balances[row["address"]] / int(total) * 100, 3)
    gate.update({"schema": "identity_gate_v3", "chain": chain,
                 "share_basis": "total_supply", "total_supply_raw": total,
                 "snapshot_binding": binding, "rows": rows})
    return gate
