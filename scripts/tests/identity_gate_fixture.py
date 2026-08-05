"""Test-only builder for identity_gate_v3 snapshot bindings."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_binding(root, balances, *, as_of_block=123, chain="bsc"):
    root = Path(root); token = "0x" + "e" * 40
    csv_path = root / "identity_events.csv"
    lines = ["block,ts,tx,log_index,from,to,value_raw,block_hash"]
    zero = "0x" + "0" * 40
    for i, (address, amount) in enumerate(balances.items()):
        lines.append(f"5,1,0xt{i},{i},{zero},{address},{amount},0xh")
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "evm"))
    from evm_channel_fixture import write_csv_channel_receipt
    channel_receipt = write_csv_channel_receipt(root, "identity", csv_path, token, 0, as_of_block + 1)
    manifest = root / "channels.json"
    manifest.write_text(json.dumps({"schema": "evm-channels/v2", "token": token,
        "expected_from": 0, "expected_to": as_of_block + 1, "channels": [{
        "tag": "identity", "path": str(csv_path), "format": "v1csv",
        "lo": 0, "hi": as_of_block + 1, "receipt": channel_receipt}]}))
    replay = Path(__file__).resolve().parent.parent / "evm" / "replay_pass1.py"
    proc = subprocess.run([sys.executable, str(replay), "--channels", str(manifest),
                           "--out-dir", str(root)], capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError(proc.stdout + proc.stderr)
    snapshot = root / "balances_final.json"
    total = sum(balances.values())
    receipt = root / "identity_holders_receipt.json"
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "report"))
    from identity_snapshot_receipt import emit_evm
    emit_evm(chain, token, as_of_block, snapshot, root / "channels_preflight.json",
             root / "replay_stats.json", total, receipt, replay_engine="replay_pass1.py")
    return str(total), {
        "snapshot_file": snapshot.name, "snapshot_sha256": sha(snapshot),
        "receipt_file": receipt.name, "receipt_sha256": sha(receipt),
        "as_of_block": as_of_block, "complete_owner_universe": True,
        "receipt_schema": "identity-holder-snapshot/v2", "adapter": chain,
    }


def augment_gate(root, gate_obj, *, chain):
    gate = dict(gate_obj)
    rows = [dict(row) for row in gate.get("rows", [])]
    balances = {row["address"]: 100 for row in rows}
    if not balances:
        balances = {"0x" + "f" * 40: 100}
    total, binding = write_binding(root, balances, chain=chain)
    for row in rows:
        row["share_pct"] = round(balances[row["address"]] / int(total) * 100, 3)
    gate.update({"schema": "identity_gate_v3", "chain": chain,
                 "share_basis": "total_supply", "total_supply_raw": total,
                 "snapshot_binding": binding, "rows": rows})
    return gate
