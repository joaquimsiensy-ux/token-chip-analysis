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


def write_coverage_fixture(case_root, *, mint=MINT, from_slot, to_slot):
    """Publish a minimal current all-HAS_DATA coverage generation for v4 tests."""
    import solana_exact_validate as exact

    case_root = Path(case_root).resolve()
    parent = case_root / "data/sqd_coverage"
    parent.mkdir(parents=True, exist_ok=True)
    counts_raw = bytes([3]) * (to_slot - from_slot + 1)
    counts_bytes = gzip.compress(counts_raw, mtime=0)
    ledger_row = {
        "seq": 0, "ok": True, "counts_coverage": True,
        "from": from_slot, "to": to_slot,
        "slots_covered": to_slot - from_slot + 1,
        "provider": "SQD", "empty_response": False,
        "returned_from": from_slot, "returned_to": to_slot,
        "n_blocks": to_slot - from_slot + 1,
    }
    ledger_bytes = (json.dumps(ledger_row, sort_keys=True) + "\n").encode()
    repo = Path(__file__).resolve().parents[2]
    producer_path = repo / "scripts/solana/sqd_coverage_probe.py"
    producer = {"path": "scripts/solana/sqd_coverage_probe.py",
                "sha256": hashlib.sha256(producer_path.read_bytes()).hexdigest()}
    metadata = {"dataset_id": "solana-mainnet", "start_block": 0,
                "real_time": True}
    classified = exact.classify_four_states(counts_raw, from_slot)
    coverage = {
        "schema": exact.COVERAGE_SCHEMA, "version": 1, "chain": "solana",
        "mint": mint, "producer": producer,
        "sqd": {"endpoint_fingerprint": "1" * 64,
                "dataset": "solana-mainnet", "metadata_normalized": metadata,
                "metadata_sha256": exact.sha256_bytes(exact.canonical_json(metadata)),
                "finalized_head_at_scan": to_slot,
                "query_body_sha256": "2" * 64},
        "scan_ranges": [{"from_slot": from_slot, "to_slot": to_slot,
                         "mode": "full"}],
        "sample_ranges": [], "era_params": dict(exact.ERA_PARAMS),
        "slot_counts": {"path": "slot_counts.bin.gz", "size": len(counts_bytes),
                        "sha256": hashlib.sha256(counts_bytes).hexdigest(),
                        "from_slot": from_slot, "to_slot": to_slot,
                        "encoding": exact.COUNT_ENCODING},
        "skipped_confirmation": None, "shared_map": None,
        "ledger": {"path": "ledger.jsonl", "size": len(ledger_bytes),
                   "sha256": hashlib.sha256(ledger_bytes).hexdigest(),
                   "requests": 1,
                   "success_ranges_sha256": exact.sha256_bytes(
                       exact.canonical_json([[from_slot, to_slot]]))},
        "summary": classified["summary"],
        "candidate_slots": classified["candidate_slots"],
        "verdict": classified["verdict"], "probe_id": "",
    }
    coverage["probe_id"] = exact.compute_probe_id(coverage)
    generation = parent / coverage["probe_id"]
    generation.mkdir(exist_ok=True)
    counts_path = generation / "slot_counts.bin.gz"
    ledger_path = generation / "ledger.jsonl"
    coverage_path = generation / "coverage_map.json"
    counts_path.write_bytes(counts_bytes)
    ledger_path.write_bytes(ledger_bytes)
    coverage_path.write_text(json.dumps(coverage), encoding="utf-8")

    def ref(path):
        return {"path": path.relative_to(case_root).as_posix(),
                "size": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    pointer = {
        "schema": exact.COVERAGE_POINTER_SCHEMA,
        "target": {"chain": "solana", "token": mint, "as_of_block": to_slot},
        "mode": "formal", "verdict": "PASS", "exit_code": 0,
        "producer": producer,
        "inputs": {"coverage_map": ref(coverage_path),
                   "slot_counts": ref(counts_path), "ledger": ref(ledger_path)},
        "probe_id": coverage["probe_id"], "supersedes": None,
        "published_at": "2026-08-23T00:00:00Z",
    }
    pointer_path = parent / "CURRENT.json"
    pointer_path.write_text(json.dumps(pointer), encoding="utf-8")
    checked = exact.validate_coverage(
        case_root, coverage_path, pointer_path, from_slot, to_slot)
    if not checked["ok"]:
        raise AssertionError(checked["reasons"])
    return pointer_path
