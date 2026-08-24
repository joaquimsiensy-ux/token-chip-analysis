#!/usr/bin/env python3
"""Batch 4 T1: collector-issued logical edge evidence must match replay."""
from __future__ import annotations

import gzip
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
for sub in ("solana", "lib", "labels"):
    sys.path.insert(0, str(ROOT / "scripts" / sub))


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


collector = _load(
    ROOT / "scripts/solana/fetch_sqd_transfers_v2.py", "batch4_sqd_collector")
replay = _load(ROOT / "scripts/solana/replay_edges.py", "batch4_sqd_replay")

from solana_attested_session import (  # noqa: E402
    SOLANA_MAINNET_GENESIS_HASH,
    SolanaAttestedSession,
)


MINT = "So1AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
OWNER = "So1BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"


def _session(slot: int) -> SolanaAttestedSession:
    def request_json(_endpoint, payload, _timeout):
        method = payload["method"]
        if method == "getGenesisHash":
            return {"result": SOLANA_MAINNET_GENESIS_HASH}
        if method == "getSlot":
            return {"result": slot}
        raise AssertionError(f"unexpected RPC method: {method}")

    return SolanaAttestedSession("fixture://solana", request_json=request_json)


def _paths() -> tuple[Path, Path]:
    return collector.cache_paths(MINT)[:2]


def test_collector_meta_matches_replay_and_tamper_rejects() -> None:
    edge = (1700000000, 10, 0, -1, collector.ZERO, OWNER, 5)
    with (mock.patch.object(collector.Fetcher, "head", return_value=10),
          mock.patch.object(collector.Fetcher, "scan_area",
                            return_value=([edge], 10, True))):
        edges, gap = collector.run(
            MINT, None, 1, 1, 1, "fixture://sqd", None,
            from_slot_cli=10, dataset_id="solana-mainnet",
            state_session=_session(10))
    assert gap is None, gap
    assert len(edges) == 1

    edge_path, meta_path = _paths()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    rows, loaded_meta_path = replay.load_edges(MINT)
    replay_digest = replay._replay_with_evidence(rows)[3]
    assert loaded_meta_path == meta_path
    assert meta.get("edge_rows") == len(rows) == 1, meta
    assert meta.get("edge_logical_sha256") == replay_digest, meta

    tampered = list(rows[0])
    tampered[-1] += 1
    with gzip.open(edge_path, "wt", encoding="utf-8") as handle:
        handle.write(json.dumps(tampered) + "\n")
    tampered_rows, _ = replay.load_edges(MINT)
    try:
        replay.cmd_reconcile(
            tampered_rows, 0, mint=MINT, cache_meta_path=meta_path,
            case_root=Path.cwd(), as_of_slot=10)
    except ValueError as exc:
        assert "摘要" in str(exc), str(exc)
    else:
        raise AssertionError("tampered edge row was accepted against collector meta")


def test_collector_logical_scan_rejects_bad_final_row() -> None:
    edge_path, _meta_path = _paths()
    edge_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(edge_path, "wt", encoding="utf-8") as handle:
        handle.write(json.dumps([1700000000, 10, "bad", -1,
                                 collector.ZERO, OWNER, 5]) + "\n")
    try:
        collector.logical_edge_evidence(edge_path)
    except (TypeError, ValueError) as exc:
        assert "tx_index" in str(exc), str(exc)
    else:
        raise AssertionError("invalid finalized edge row was included in logical evidence")


def main() -> int:
    old = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="sqd-collector-meta-v4-",
                                     dir="/private/tmp") as raw:
        os.chdir(raw)
        try:
            test_collector_meta_matches_replay_and_tamper_rejects()
            for path in Path("data").glob("*"):
                if path.is_file():
                    path.unlink()
            test_collector_logical_scan_rejects_bad_final_row()
        finally:
            os.chdir(old)
    print("PASS: SQD v4 collector meta logical evidence matches replay")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
