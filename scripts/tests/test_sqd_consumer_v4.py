#!/usr/bin/env python3
"""SQD v4 consumer split-mode regression tests (batch 3)."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
for sub in ("solana", "lib", "labels"):
    sys.path.insert(0, str(ROOT / "scripts" / sub))

import replay_edges  # noqa: E402
import curve_cost  # noqa: E402
import producer_history  # noqa: E402
from camp_series_provenance import registry_anchor_check  # noqa: E402
from spl_edge_core import (  # noqa: E402
    EDGE_SCHEMA_FIELDS,
    EDGE_SEMANTICS,
    ORDER_GRANULARITY_TX,
)


ZERO = "0x" + "0" * 40
MINT = "So1AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
OWNER = "So1BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
FETCH_SCRIPT = "scripts/solana/fetch_sqd_transfers_v2.py"
FETCH_PROTOCOL = "sqd-solana-cache/v4"
FETCH_SHA256 = "2589f6a396c262d0747343ef21dee2bc7ba814eaa59eebdfa782fe9253c32212"
FETCH_BATCH6_SHA256 = "a94b193b94ba8872e4d6aa4915ff7d89ef6cc438d7f2c6c0744ebc33212d9bae"
WINDOW_SCRIPT = "scripts/solana/window_fetch.py"
WINDOW_PROTOCOL = "solana-window-fetch-receipt/v3"
WINDOW_SHA256 = "56d94cbecf476b632c814a57b245c58397087dd105406e2538cac47c2fa6661c"


def _write_edges(path: Path, rows) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(list(row), ensure_ascii=False) + "\n")


def _logical_digest(rows) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(
            (json.dumps(list(row), ensure_ascii=False) + "\n").encode("utf-8")
        )
    return digest.hexdigest()


def _v4_meta(rows) -> dict:
    return {
        "schema": "sqd-solana-cache/v4",
        "version": 4,
        "mint": MINT,
        "endpoint": "https://portal.sqd.dev",
        "endpoint_sha256": "1" * 64,
        "collector": "fetch_sqd_transfers_v2.py/v4",
        "collector_sha256": FETCH_SHA256,
        "edge_schema": list(EDGE_SCHEMA_FIELDS),
        "edge_semantics": EDGE_SEMANTICS,
        "order_granularity": ORDER_GRANULARITY_TX,
        "order_exact": False,
        "dedupe_identity": "slot-txindex-digest/v1",
        "supply_delta_source": "tokenBalances-owner-net",
        "from_slot": min(row[1] for row in rows),
        "finalized_upper_slot": max(row[1] for row in rows),
        "edge_logical_sha256": _logical_digest(rows),
        "edge_rows": len(rows),
    }


def _paths() -> tuple[Path, Path]:
    key = hashlib.sha256(MINT.encode("utf-8")).hexdigest()
    return (Path(f"data/soltx-{key}.jsonl.gz"),
            Path(f"data/soltx-{key}.meta.json"))


def _expect_reject(call, needle: str) -> None:
    try:
        call()
    except (SystemExit, ValueError) as exc:
        assert needle in str(exc), str(exc)
    else:
        raise AssertionError(f"expected rejection containing {needle!r}")


def test_replay_edges_v4_and_legacy_split() -> None:
    rows = [
        [100, 1, 0, -1, ZERO, MINT, 100],
        [101, 2, 0, -1, MINT, OWNER, 25],
    ]
    edge_path, meta_path = _paths()
    _write_edges(edge_path, rows)
    meta_path.write_text(json.dumps(_v4_meta(rows)), encoding="utf-8")

    loaded, loaded_meta = replay_edges.load_edges(MINT)
    assert loaded == rows and loaded_meta == meta_path

    original_history = producer_history.PRODUCER_HISTORY
    producer_history.PRODUCER_HISTORY = original_history + ({
        "script": "test-only-other.py",
        "sha256": FETCH_SHA256,
        "commit": "0" * 40,
        "protocol": "test-only/v1",
        "status": "REVOKED",
        "reason": "test-only hash-wide revocation",
    },)
    try:
        _expect_reject(lambda: replay_edges.load_edges(MINT), "producer 登记")
    finally:
        producer_history.PRODUCER_HISTORY = original_history

    forged = _v4_meta(rows)
    forged["collector_sha256"] = "2" * 64
    meta_path.write_text(json.dumps(forged), encoding="utf-8")
    _expect_reject(lambda: replay_edges.load_edges(MINT), "producer 登记")
    meta_path.write_text(json.dumps(_v4_meta(rows)), encoding="utf-8")

    mixed = rows + [[102, 2, MINT, OWNER, 1]]
    _write_edges(edge_path, mixed)
    _expect_reject(lambda: replay_edges.load_edges(MINT), "七元组")

    legacy_rows = [[100, 1, ZERO, MINT, 100]]
    _write_edges(edge_path, legacy_rows)
    meta_path.write_text(json.dumps({
        "schema": "sqd-solana-cache/v3",
        "mint": MINT,
        "from_slot": 1,
        "collection_upper_slot": 1,
    }), encoding="utf-8")
    _expect_reject(lambda: replay_edges.load_edges(MINT), "v4")
    loaded, _ = replay_edges.load_edges(MINT, legacy_sol5=True)
    assert loaded == [[100, 1, None, None, ZERO, MINT, 100]]

    old_argv = sys.argv
    try:
        sys.argv = ["replay_edges.py", "reconcile", "--mint", MINT,
                    "--legacy-sol5", "--no-labels"]
        assert replay_edges.main() == 2
    finally:
        sys.argv = old_argv
    assert not Path("data/reconcile_receipt.json").exists()


def test_reconcile_digest_matches_v4_meta() -> None:
    rows = [[100, 1, 0, -1, ZERO, MINT, 100]]
    edge_path, meta_path = _paths()
    _write_edges(edge_path, rows)
    meta_path.write_text(json.dumps(_v4_meta(rows)), encoding="utf-8")
    Path("data/holders_owners.json").write_text(
        json.dumps({MINT: 100}), encoding="utf-8")
    owners = Path("data/holders_owners.json")
    owners_ref = {
        "path": owners.name,
        "size": owners.stat().st_size,
        "sha256": hashlib.sha256(owners.read_bytes()).hexdigest(),
    }
    Path("data/holders_snapshot_meta.json").write_text(json.dumps({
        "schema": "solana-holder-snapshot-v2",
        "mint": MINT,
        "target": {"chain": "solana", "token": MINT, "as_of_block": 1},
        "closed": True,
        "supply_raw": "100",
        "outputs": {"holders_owners": owners_ref},
    }), encoding="utf-8")

    assert replay_edges.cmd_reconcile(
        rows, 1, mint=MINT, cache_meta_path=meta_path) is True
    assert json.loads(meta_path.read_text())["edge_logical_sha256"] == _logical_digest(rows)
    series_path = Path("data/camp_share_series.json")
    series_path.write_text("[]", encoding="utf-8")
    receipt_path = Path("data/reconcile_receipt.json")
    assert registry_anchor_check(
        {"series_format": "sol-rows"},
        {"inputs.reconcile_receipt": receipt_path},
        series_path,
        expected_chain="solana",
        expected_mint=MINT,
        expected_cutoff_slot=1,
    ) == receipt_path

    forged = json.loads(meta_path.read_text(encoding="utf-8"))
    forged["collector_sha256"] = "3" * 64
    meta_path.write_text(json.dumps(forged), encoding="utf-8")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["inputs"]["soltx_meta"]["size"] = meta_path.stat().st_size
    receipt["inputs"]["soltx_meta"]["sha256"] = hashlib.sha256(
        meta_path.read_bytes()).hexdigest()
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    _expect_reject(
        lambda: registry_anchor_check(
            {"series_format": "sol-rows"},
            {"inputs.reconcile_receipt": receipt_path},
            series_path,
            expected_chain="solana",
            expected_mint=MINT,
            expected_cutoff_slot=1,
        ),
        "producer 登记",
    )

    bad = _v4_meta(rows)
    bad["edge_logical_sha256"] = "0" * 64
    meta_path.write_text(json.dumps(bad), encoding="utf-8")
    _expect_reject(
        lambda: replay_edges.cmd_reconcile(
            rows, 1, mint=MINT, cache_meta_path=meta_path),
        "摘要",
    )


def test_curve_cost_is_v4_only() -> None:
    rows = [[100, 1, 0, -1, MINT, OWNER, 25]]
    edge_path, meta_path = _paths()
    _write_edges(edge_path, rows)
    meta_path.write_text(json.dumps(_v4_meta(rows)), encoding="utf-8")
    assert curve_cost.load_edges(MINT) == rows

    _write_edges(edge_path, rows + [[101, 2, MINT, OWNER, 1]])
    _expect_reject(lambda: curve_cost.load_edges(MINT), "第 2 行")


def test_solana_producer_history_entries() -> None:
    assert FETCH_SHA256 in producer_history.historical_producer_hashes(
        FETCH_SCRIPT, FETCH_PROTOCOL)
    assert FETCH_BATCH6_SHA256 in producer_history.historical_producer_hashes(
        FETCH_SCRIPT, FETCH_PROTOCOL)
    assert WINDOW_SHA256 in producer_history.historical_producer_hashes(
        WINDOW_SCRIPT, WINDOW_PROTOCOL)


def main() -> int:
    old = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="sqd-consumer-v4-",
                                     dir="/private/tmp") as raw:
        os.chdir(raw)
        try:
            Path("data").mkdir()
            test_replay_edges_v4_and_legacy_split()
            for path in Path("data").iterdir():
                if path.is_file():
                    path.unlink()
            test_reconcile_digest_matches_v4_meta()
            for path in Path("data").iterdir():
                if path.is_file():
                    path.unlink()
            test_curve_cost_is_v4_only()
            test_solana_producer_history_entries()
        finally:
            os.chdir(old)
    print("PASS: SQD v4 consumer split-mode regressions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
