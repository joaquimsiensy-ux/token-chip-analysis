"""正式 Solana SQD v4 consumer 测试的最小真实 provenance 夹具。"""

from __future__ import annotations

import hashlib
import gzip
import json
from pathlib import Path


MINT = "So1AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
FETCH_SHA256 = "2589f6a396c262d0747343ef21dee2bc7ba814eaa59eebdfa782fe9253c32212"


def write_v4_meta(edge_path, *, mint=MINT):
    edge_path = Path(edge_path)
    opener = gzip.open if edge_path.name.endswith(".gz") else open
    with opener(edge_path, "rt", encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    if not rows:
        raise ValueError("SQD v4 fixture edge file is empty")
    digest = hashlib.sha256()
    for row in rows:
        digest.update(
            (json.dumps(list(row), ensure_ascii=False) + "\n").encode("utf-8")
        )
    meta = {
        "schema": "sqd-solana-cache/v4",
        "version": 4,
        "mint": mint,
        "collector": "fetch_sqd_transfers_v2.py/v4",
        "collector_sha256": FETCH_SHA256,
        "edge_schema": ["ts", "slot", "tx_index", "instr_index", "from", "to", "amt"],
        "edge_semantics": "owner-net-greedy",
        "order_granularity": "transaction",
        "order_exact": False,
        "from_slot": min(row[1] for row in rows),
        "finalized_upper_slot": max(row[1] for row in rows),
        "edge_logical_sha256": digest.hexdigest(),
        "edge_rows": len(rows),
    }
    meta_path = edge_path.with_name(edge_path.name + ".meta.json")
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    return meta_path


def formal_cli_args(edge_path, *, mint=MINT):
    meta_path = write_v4_meta(edge_path, mint=mint)
    return ["--sol-cache-meta", str(meta_path), "--mint", mint]
