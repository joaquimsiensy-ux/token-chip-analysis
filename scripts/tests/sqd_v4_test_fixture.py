"""正式 Solana SQD v4 consumer 测试的最小真实 provenance 夹具。"""

from __future__ import annotations

import hashlib
import gzip
import json
from pathlib import Path


MINT = "So1AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
FETCH_SHA256 = "2589f6a396c262d0747343ef21dee2bc7ba814eaa59eebdfa782fe9253c32212"
EDGE_SOURCE_BINDING = {
    "cache_kind": "base", "gid": None,
    "soltx_edges_sha256": "1" * 64,
    "soltx_meta_sha256": "2" * 64,
    "edge_logical_sha256": "3" * 64,
}


def write_v4_meta(edge_path, *, mint=MINT, meta_path=None):
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
    meta_path = Path(meta_path) if meta_path is not None \
        else edge_path.with_name(edge_path.name + ".meta.json")
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    return meta_path


def formal_cli_args(edge_path, *, mint=MINT):
    edge_path = Path(edge_path)
    opener = gzip.open if edge_path.name.endswith(".gz") else open
    with opener(edge_path, "rt", encoding="utf-8") as handle:
        raw = "".join(line for line in handle if line.strip()).encode("utf-8")
    root = (edge_path.parent.parent if edge_path.parent.name == "data"
            else edge_path.parent).resolve()
    data = root / "data"
    data.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(mint.encode("utf-8")).hexdigest()
    canonical_edge = data / f"soltx-{key}.jsonl.gz"
    canonical_edge.write_bytes(gzip.compress(raw, mtime=0))
    meta_path = write_v4_meta(
        canonical_edge, mint=mint,
        meta_path=data / f"soltx-{key}.meta.json")
    # Callers historically supplied --edges-sol before this helper.  Repeating
    # the scalar option here intentionally makes argparse use the canonical
    # resolver-selected path without duplicating fixture setup at every callsite.
    return ["--case-root", str(root), "--edges-sol", str(canonical_edge),
            "--sol-cache-meta", str(meta_path), "--mint", mint]
