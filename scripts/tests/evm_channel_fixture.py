"""Test-only builder for collector-native CSV receipts consumed by production validators."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
EVM = HERE.parent / "evm"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_csv_channel_receipt(root, tag, data_path, token, lo, hi):
    from channels_preflight import _csv_stats
    from make_channel_receipt import make_receipt
    data = Path(data_path).resolve()
    rows, min_block, max_block = _csv_stats(data)
    source = Path(root) / f"{tag}.collector.json"
    source.write_text(json.dumps({
        "schema": "evm-collector-run/v1", "status": "PASS",
        "producer": "fetch_hypersync.py/v2",
        "collector": {"path": "fetch_hypersync.py",
                      "sha256": sha(EVM / "fetch_hypersync.py")},
        "query": {"token": token.lower(), "query_schema": "erc20-transfer-fields/v2",
                  "provider_url": "https://fixture.hypersync.xyz/query",
                  "requested_from": lo, "requested_to": hi},
        "completion": {"reason": "requested_bound_reached", "next_block": hi},
        "output": {"path": str(data), "size": data.stat().st_size,
                   "sha256": sha(data), "rows": rows,
                   "min_block": min_block, "max_block": max_block},
    }), encoding="utf-8")
    receipt = Path(root) / f"{tag}.receipt.json"
    receipt.write_text(json.dumps(make_receipt(
        data, "v1csv", token, lo, hi, tag, collector_receipt=source)), encoding="utf-8")
    return str(receipt)
