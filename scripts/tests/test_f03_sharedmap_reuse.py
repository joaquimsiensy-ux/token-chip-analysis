#!/usr/bin/env python3
"""F-03 shared-map identity, anchor, recheck, validator, and producer regressions."""
from __future__ import annotations

import copy
import gzip
import inspect
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/lib"))
sys.path.insert(0, str(ROOT / "scripts/solana"))

import producer_history  # noqa: E402
import solana_exact_validate as exact  # noqa: E402
import sqd_coverage_probe as probe  # noqa: E402


MINT = "11111111111111111111111111111111"
OLD_HEAD = 1_000
NEW_HEAD = 1_010
LOWER = 100
UPPER = 199
ANCHOR_HASH = "anchor-hash-at-1000"
OLD_PRODUCER = "bccf1802b6a5c9d9bbbdb12e19354ad761416c631e3cdfde2449f7fe1794f176"


def _anchor_body(slot=OLD_HEAD):
    return {
        "type": "solana", "fromBlock": slot, "toBlock": slot,
        "includeAllBlocks": True,
        "fields": {"block": {"number": True, "hash": True}},
    }


def _metadata(head=OLD_HEAD, block_hash=ANCHOR_HASH):
    return {
        "dataset_id": "solana-mainnet", "start_block": 0,
        "real_time": True, "finalized_head": head,
        "number": head, "hash": block_hash,
    }


def _write_asset(root, *, counts=None):
    counts = bytearray([3] * (UPPER - LOWER + 1)) if counts is None else bytearray(counts)
    counts[70] = 1  # getBlocks says slot 170 exists, so it recomputes as a candidate.
    counts_path = root / "map.counts.bin.gz"
    counts_path.write_bytes(gzip.compress(bytes(counts), mtime=0))
    blocks_path = root / "map.blocks.bin.gz"
    blocks_path.write_bytes(gzip.compress(
        exact.encode_bitmap(range(LOWER, UPPER + 1), LOWER, UPPER), mtime=0))
    metadata = _metadata()
    asset = {
        "schema": "sqd-solana-shared-coverage-map/v1", "version": "20260827",
        "generated_at": datetime.now(timezone.utc).isoformat(), "ttl_days": 30,
        "supersedes": None,
        "sqd": {
            "dataset": "solana-mainnet",
            "endpoint_fingerprint": probe.endpoint_fingerprint("fixture://sqd")["sha256"],
            "finalized_head_at_scan": OLD_HEAD,
            "metadata_normalized": metadata,
            "metadata_sha256": exact.sha256_bytes(exact.canonical_json(metadata)),
            "query_body_sha256": probe.sqd_query_template_sha256(),
        },
        "slot_counts": {
            "path": counts_path.name, "size": counts_path.stat().st_size,
            "sha256": exact.sha256_file(counts_path), "from_slot": LOWER,
            "to_slot": UPPER, "encoding": exact.COUNT_ENCODING,
        },
        "blocks_bitmap": {
            "path": blocks_path.name, "size": blocks_path.stat().st_size,
            "sha256": exact.sha256_file(blocks_path), "from_slot": LOWER,
            "to_slot": UPPER, "encoding": exact.BITMAP_ENCODING,
        },
        "candidate_slots": [170], "refuted_slots": [171, 180],
        "canary": {"slots": list(range(LOWER, LOWER + 64)),
                   "counts": list(counts[:64])},
    }
    asset_path = root / "map.json"
    asset_path.write_text(json.dumps(asset), encoding="utf-8")
    return asset_path, asset, bytes(counts)


def _block(slot, count, *, block_hash=None):
    header = {"number": slot}
    if block_hash is not None:
        header["hash"] = block_hash
    return {"header": header,
            "instructions": [{"transactionIndex": index}
                             for index in range(max(0, count - 2))]}


def _request_failure(status=529):
    return {"ok": False, "category": "http", "message": f"fixture {status}",
            "http_status": status, "retryable": True}


def _success_range(counts, start, end, *, overrides=None):
    overrides = overrides or {}
    return {"ok": True, "value": [
        _block(slot, overrides.get(slot, counts[slot - LOWER]))
        for slot in range(start, end + 1)
        if overrides.get(slot, counts[slot - LOWER]) > 1
    ]}


def _responses(counts, *, anchor_hash=ANCHOR_HASH, fail_range=None,
               mismatch_slot=None):
    responses = {
        probe.request_digest("sqd-head", {}): {
            "ok": True, "value": _metadata(NEW_HEAD, "new-head-hash")},
        probe.request_digest("sqd-stream", _anchor_body()): {
            "ok": True,
            "value": [_block(OLD_HEAD, 2, block_hash=anchor_hash)]},
    }
    # Baseline single-slot calls and repaired contiguous-range calls coexist.
    ranges = [(LOWER, LOWER + 63), (170, 171), (180, 180)]
    for start, end in ranges:
        body = probe.sqd_query_body(start, end)
        if fail_range == (start, end):
            responses[probe.request_digest("sqd-stream", body)] = {
                "ok": False, "category": "timeout", "message": "fixture timeout",
                "retryable": True,
            }
        else:
            values = []
            for slot in range(start, end + 1):
                count = counts[slot - LOWER]
                if slot == mismatch_slot:
                    count = min(255, count + 1)
                if count > 1:
                    values.append(_block(slot, count))
            responses[probe.request_digest("sqd-stream", body)] = {
                "ok": True, "value": values}
    for slot in sorted(set(range(LOWER, LOWER + 64)) | {170, 171, 180}):
        body = probe.sqd_query_body(slot, slot)
        count = counts[slot - LOWER]
        responses[probe.request_digest("sqd-stream", body)] = {
            "ok": True, "value": [] if count == 1 else [_block(slot, count)]}
    return responses


def _transport(root, responses):
    fixture = root / "transport"
    fixture.mkdir(exist_ok=True)
    (fixture / "responses.json").write_text(json.dumps({
        "format": "sqd-coverage-transport-fixture-v1", "responses": responses,
    }), encoding="utf-8")
    return probe.FixtureTransport(fixture)


def _load(asset_path, metadata, current_head_raw, transport, ledger, *, workers=4):
    args = [asset_path, LOWER, UPPER,
            probe.endpoint_fingerprint("fixture://sqd")["sha256"], metadata,
            transport, ledger, ["fixture://sqd"]]
    params = inspect.signature(probe._load_known_map).parameters
    kwargs = {}
    if "current_head_raw" in params:
        kwargs["current_head_raw"] = current_head_raw
    if "workers" in params:
        kwargs["workers"] = workers
    return probe._load_known_map(*args, **kwargs)


def _assert_case_bounded_rechecks(ledger, coverage, case_from, case_to, *,
                                  require_fully_outside_success=False,
                                  require_cross_boundary_success=False):
    outside_rows = [
        row for row in ledger
        if row.get("mode") == "recheck"
        and (row.get("from") < case_from or row.get("to") > case_to)
    ]
    assert outside_rows, ledger
    assert all(row.get("counts_coverage") is False for row in outside_rows), \
        outside_rows
    assert all(case_from <= row["from_slot"] <= row["to_slot"] <= case_to
               for row in coverage["scan_ranges"]), coverage["scan_ranges"]
    if require_fully_outside_success:
        assert any(
            row.get("ok") is True
            and (row["to"] < case_from or row["from"] > case_to)
            for row in outside_rows
        ), outside_rows
    if require_cross_boundary_success:
        assert any(
            row.get("ok") is True
            and ((row["from"] < case_from <= row["to"])
                 or (row["from"] <= case_to < row["to"]))
            for row in outside_rows
        ), outside_rows


def test_head_forward_anchor_and_gap_exact_rechecks():
    with tempfile.TemporaryDirectory(prefix="f03-head-forward-") as td:
        root = Path(td)
        asset_path, _asset, counts = _write_asset(root)
        raw = _metadata(NEW_HEAD, "new-head-hash")
        ledger = []
        info, reused, lower, upper = _load(
            asset_path, probe._normalize_metadata(raw), raw,
            _transport(root, _responses(counts)), ledger)
        assert reused == counts and (lower, upper) == (LOWER, UPPER), info
        assert "fallback_reason" not in info
        assert [(row["mode"], row["from"], row["to"], row["counts_coverage"])
                for row in ledger] == [
            ("identity-anchor", OLD_HEAD, OLD_HEAD, False),
            ("recheck", LOWER, LOWER + 63, True),
            ("recheck", 170, 171, True),
            ("recheck", 180, 180, True),
        ]


def test_anchor_mismatch_is_not_ignored():
    with tempfile.TemporaryDirectory(prefix="f03-anchor-mismatch-") as td:
        root = Path(td)
        asset_path, _asset, counts = _write_asset(root)
        raw = _metadata()
        info, reused, _lower, _upper = _load(
            asset_path, probe._normalize_metadata(raw), raw,
            _transport(root, _responses(counts, anchor_hash="wrong-history-hash")), [])
        assert reused is None
        assert info["fallback_reason"] == "identity-anchor-mismatch", info


def test_anchor_transport_exception_is_structured_and_audited():
    class RaisingAnchorTransport:
        def call(self, _kind, _payload):
            raise TimeoutError("fixture anchor timeout")

    with tempfile.TemporaryDirectory(prefix="f03-anchor-raise-") as td:
        root = Path(td)
        asset_path, _asset, _counts = _write_asset(root)
        raw = _metadata()
        ledger = []
        info, reused, _lower, _upper = _load(
            asset_path, probe._normalize_metadata(raw), raw,
            RaisingAnchorTransport(), ledger)
        assert reused is None
        assert info["fallback_reason"] == "identity-anchor-request-failed", info
        anchors = [row for row in ledger if row.get("mode") == "identity-anchor"]
        assert len(anchors) == 1, ledger
        assert anchors[0]["ok"] is False
        assert anchors[0]["counts_coverage"] is False


def test_recheck_mismatch_still_falls_back():
    with tempfile.TemporaryDirectory(prefix="f03-recheck-fail-") as td:
        root = Path(td)
        asset_path, _asset, counts = _write_asset(root)
        raw = _metadata(NEW_HEAD, "new-head-hash")
        info, reused, _lower, _upper = _load(
            asset_path, probe._normalize_metadata(raw), raw,
            _transport(root, _responses(counts, mismatch_slot=170)), [])
        assert reused is None and info["fallback_reason"] == "recheck-mismatch:170", info


def test_partial_request_failure_reuses_verified_ranges():
    """F-03b RED: a persistent non-canary failure must not discard the map."""
    with tempfile.TemporaryDirectory(prefix="f03b-partial-fail-") as td:
        root = Path(td)
        asset_path, _asset, counts = _write_asset(root)
        raw = _metadata(NEW_HEAD, "new-head-hash")
        ledger = []
        info, reused, lower, upper = _load(
            asset_path, probe._normalize_metadata(raw), raw,
            _transport(root, _responses(counts, fail_range=(170, 171))), ledger)
        assert reused is not None, info
        assert (lower, upper) == (LOWER, UPPER)
        assert info["unverified_ranges"] == [
            {"from_slot": 170, "to_slot": 171},
        ]
        target_rows = [row for row in ledger if row.get("mode") == "recheck"
                       and row.get("from") == 170]
        assert len(target_rows) == 2
        assert all(row["counts_coverage"] is False for row in target_rows)
        assert info["recheck_stats"] == {
            "verified": 2, "unverified": 1, "retried": 1,
        }


def test_partial_rate_limit_end_to_end_full_repairs_failed_ranges():
    with tempfile.TemporaryDirectory(prefix="f03b-partial-e2e-") as td:
        root = Path(td)
        asset_path, _asset, counts = _write_asset(root)
        responses = _responses(counts)
        case_from, case_to = 120, 175
        fresh = {170: 7, 171: 8}
        digest = probe.request_digest(
            "sqd-stream", probe.sqd_query_body(170, 171))
        responses[digest] = [
            _request_failure(529), _request_failure(529),
            _success_range(counts, 170, 171, overrides=fresh),
        ]
        _transport(root, responses)
        case = root / "case"
        assert probe.main([
            "--mint", MINT, "--case-root", str(case),
            "--from-slot", str(case_from), "--to-slot", str(case_to),
            "--known-map", str(asset_path), "--no-getblocks",
            "--transport-fixture", str(root / "transport"),
        ]) == 0
        pointer_path = case / "data/sqd_coverage/CURRENT.json"
        pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
        generation = case / "data/sqd_coverage" / pointer["probe_id"]
        coverage_path = generation / "coverage_map.json"
        coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
        checked = exact.validate_coverage(
            case, coverage_path, pointer_path, case_from, case_to)
        assert checked["ok"], checked
        assert coverage["shared_map"]["unverified_ranges"] == [
            {"from_slot": 170, "to_slot": 171},
        ]
        assert coverage["shared_map"]["recheck_stats"] == {
            "verified": 2, "unverified": 1, "retried": 1,
        }
        expected_reused = [
            {"from_slot": 120, "to_slot": 169},
            {"from_slot": 172, "to_slot": 175},
        ]
        assert coverage["shared_map"]["reused_ranges"] == expected_reused
        ledger = [json.loads(line) for line in
                  (generation / "ledger.jsonl").read_text(
                      encoding="utf-8").splitlines() if line.strip()]
        map_rows = [row for row in ledger if row.get("mode") == "map-reuse"]
        assert [(row["from"], row["to"]) for row in map_rows] == [
            (120, 169), (172, 175),
        ]
        for row in map_rows:
            part = counts[row["from"] - LOWER:row["to"] - LOWER + 1]
            assert row["response_sha256"] == exact.sha256_bytes(part)
        assert all(not (row["from"] <= 170 <= row["to"])
                   for row in map_rows)
        full_rows = [row for row in ledger if row.get("mode") == "full"
                     and row.get("counts_coverage") is True]
        assert [(row["from"], row["to"]) for row in full_rows] == [
            (170, 171),
        ]
        failed_rechecks = [row for row in ledger
                           if row.get("mode") == "recheck"
                           and row.get("from") == 170]
        assert len(failed_rechecks) == 2
        assert all(row["counts_coverage"] is False for row in failed_rechecks)
        _assert_case_bounded_rechecks(
            ledger, coverage, case_from, case_to,
            require_fully_outside_success=True,
            require_cross_boundary_success=True,
        )
        final_counts = gzip.decompress(
            (generation / coverage["slot_counts"]["path"]).read_bytes())
        for slot, value in fresh.items():
            assert final_counts[slot - case_from] == value


def test_retry_rescues_range_and_retry_mismatch_falls_back():
    with tempfile.TemporaryDirectory(prefix="f03b-retry-rescue-") as td:
        root = Path(td)
        asset_path, _asset, counts = _write_asset(root)
        raw = _metadata(NEW_HEAD, "new-head-hash")
        responses = _responses(counts)
        digest = probe.request_digest(
            "sqd-stream", probe.sqd_query_body(170, 171))
        responses[digest] = [
            _request_failure(), _success_range(counts, 170, 171),
        ]
        ledger = []
        info, reused, lower, upper = _load(
            asset_path, probe._normalize_metadata(raw), raw,
            _transport(root, responses), ledger)
        assert reused == counts and (lower, upper) == (LOWER, UPPER), info
        assert info["unverified_ranges"] == []
        assert info["recheck_stats"] == {
            "verified": 3, "unverified": 0, "retried": 1,
        }
        target_rows = [row for row in ledger if row.get("mode") == "recheck"
                       and row.get("from") == 170]
        assert len(target_rows) == 2
        assert [row["counts_coverage"] for row in target_rows] == [False, True]

    with tempfile.TemporaryDirectory(prefix="f03b-retry-mismatch-") as td:
        root = Path(td)
        asset_path, _asset, counts = _write_asset(root)
        responses = _responses(counts)
        digest = probe.request_digest(
            "sqd-stream", probe.sqd_query_body(170, 171))
        responses[digest] = [
            _request_failure(),
            _success_range(counts, 170, 171, overrides={170: 4}),
        ]
        ledger = []
        info, reused, _lower, _upper = _load(
            asset_path, probe._normalize_metadata(raw), raw,
            _transport(root, responses), ledger)
        assert reused is None
        assert info["fallback_reason"] == "recheck-mismatch:170", info
        assert info["unverified_ranges"] == []
        assert info["recheck_stats"] == {
            "verified": 2, "unverified": 0, "retried": 1,
        }
        assert all(row["counts_coverage"] is False
                   for row in ledger if row.get("mode") == "recheck")

    with tempfile.TemporaryDirectory(prefix="f03b-mismatch-plus-retry-") as td:
        root = Path(td)
        asset_path, _asset, counts = _write_asset(root)
        responses = _responses(counts, mismatch_slot=170)
        digest = probe.request_digest(
            "sqd-stream", probe.sqd_query_body(180, 180))
        responses[digest] = [
            _request_failure(), _success_range(counts, 180, 180),
        ]
        ledger = []
        info, reused, _lower, _upper = _load(
            asset_path, probe._normalize_metadata(raw), raw,
            _transport(root, responses), ledger)
        assert reused is None
        assert info["fallback_reason"] == "recheck-mismatch:170", info
        retried_rows = [row for row in ledger if row.get("mode") == "recheck"
                        and row.get("from") == 180]
        assert len(retried_rows) == 2
        assert info["recheck_stats"]["retried"] == 1


def test_canary_unavailable_and_canary_counts_changed_fall_back():
    with tempfile.TemporaryDirectory(prefix="f03b-canary-unavailable-") as td:
        root = Path(td)
        asset_path, _asset, counts = _write_asset(root)
        raw = _metadata(NEW_HEAD, "new-head-hash")
        responses = _responses(counts)
        digest = probe.request_digest(
            "sqd-stream", probe.sqd_query_body(LOWER, LOWER + 63))
        responses[digest] = [_request_failure(), _request_failure()]
        info, reused, _lower, _upper = _load(
            asset_path, probe._normalize_metadata(raw), raw,
            _transport(root, responses), [])
        assert reused is None
        assert info["fallback_reason"] == "canary-recheck-unavailable", info

    with tempfile.TemporaryDirectory(prefix="f03b-canary-changed-") as td:
        root = Path(td)
        asset_path, _asset, counts = _write_asset(root)
        original_validate = probe.validate_shared_map
        original_read = probe._read_json
        try:
            probe.validate_shared_map = lambda _path: {"ok": True, "reasons": []}

            def changed_canary(path):
                asset = original_read(path)
                asset["canary"]["counts"][0] += 1
                return asset

            probe._read_json = changed_canary
            info, reused, _lower, _upper = _load(
                asset_path, probe._normalize_metadata(raw), raw,
                _transport(root, _responses(counts)), [])
        finally:
            probe.validate_shared_map = original_validate
            probe._read_json = original_read
        assert reused is None
        assert info["fallback_reason"] == "canary-counts-changed", info


def test_truncated_and_worker_exception_ranges_are_unverified():
    with tempfile.TemporaryDirectory(prefix="f03b-truncated-") as td:
        root = Path(td)
        asset_path, _asset, counts = _write_asset(root)
        raw = _metadata(NEW_HEAD, "new-head-hash")
        responses = _responses(counts)
        digest = probe.request_digest(
            "sqd-stream", probe.sqd_query_body(170, 171))
        truncated = _success_range(counts, 170, 170, overrides={170: 3})
        responses[digest] = [truncated, truncated]
        ledger = []
        info, reused, _lower, _upper = _load(
            asset_path, probe._normalize_metadata(raw), raw,
            _transport(root, responses), ledger)
        assert reused is not None
        assert info["unverified_ranges"] == [
            {"from_slot": 170, "to_slot": 171},
        ]
        rows = [row for row in ledger if row.get("mode") == "recheck"
                and row.get("from") == 170]
        assert len(rows) == 2 and all(row["ok"] is True for row in rows)
        assert all(row["slots_covered"] == 1 for row in rows)
        assert all(row["counts_coverage"] is False for row in rows)

    with tempfile.TemporaryDirectory(prefix="f03b-worker-exception-") as td:
        root = Path(td)
        asset_path, _asset, counts = _write_asset(root)
        base = _transport(root, _responses(counts))
        target = probe.request_digest(
            "sqd-stream", probe.sqd_query_body(170, 171))

        class RaisingRangeTransport:
            def call(self, kind, body):
                if probe.request_digest(kind, body) == target:
                    raise TimeoutError("fixture worker timeout")
                return base.call(kind, body)

        ledger = []
        info, reused, _lower, _upper = _load(
            asset_path, probe._normalize_metadata(raw), raw,
            RaisingRangeTransport(), ledger)
        assert reused is not None
        assert info["unverified_ranges"] == [
            {"from_slot": 170, "to_slot": 171},
        ]
        rows = [row for row in ledger if row.get("mode") == "recheck"
                and row.get("from") == 170]
        assert len(rows) == 2 and all(row["ok"] is False for row in rows)
        assert all(row["counts_coverage"] is False for row in rows)


def test_exclusion_failure_falls_back_and_case_can_degrade_to_pure_full():
    with tempfile.TemporaryDirectory(prefix="f03b-exclusion-fail-") as td:
        root = Path(td)
        asset_path, _asset, counts = _write_asset(root)
        raw = _metadata(NEW_HEAD, "new-head-hash")
        original = probe._reuse_ranges_excluding
        try:
            probe._reuse_ranges_excluding = lambda *_args: (_ for _ in ()).throw(
                ValueError("fixture-exclusion-failed"))
            ledger = []
            info, reused, _lower, _upper = _load(
                asset_path, probe._normalize_metadata(raw), raw,
                _transport(root, _responses(counts)), ledger)
        finally:
            probe._reuse_ranges_excluding = original
        assert reused is None
        assert info["fallback_reason"] == "fixture-exclusion-failed", info
        assert all(row["counts_coverage"] is False
                   for row in ledger if row.get("mode") == "recheck")

    with tempfile.TemporaryDirectory(prefix="f03b-pure-full-") as td:
        root = Path(td)
        asset_path, _asset, counts = _write_asset(root)
        responses = _responses(counts)
        digest = probe.request_digest(
            "sqd-stream", probe.sqd_query_body(170, 171))
        fresh = {170: 6, 171: 7}
        responses[digest] = [
            _request_failure(), _request_failure(),
            _success_range(counts, 170, 171, overrides=fresh),
        ]
        _transport(root, responses)
        case = root / "case"
        assert probe.main([
            "--mint", MINT, "--case-root", str(case),
            "--from-slot", "170", "--to-slot", "171",
            "--known-map", str(asset_path), "--no-getblocks",
            "--transport-fixture", str(root / "transport"),
        ]) == 0
        pointer_path = case / "data/sqd_coverage/CURRENT.json"
        pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
        generation = case / "data/sqd_coverage" / pointer["probe_id"]
        coverage_path = generation / "coverage_map.json"
        coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
        checked = exact.validate_coverage(
            case, coverage_path, pointer_path, 170, 171)
        assert checked["ok"], checked
        assert coverage["shared_map"]["reused_ranges"] == []
        ledger = [json.loads(line) for line in
                  (generation / "ledger.jsonl").read_text(
                      encoding="utf-8").splitlines() if line.strip()]
        assert not [row for row in ledger if row.get("mode") == "map-reuse"]
        _assert_case_bounded_rechecks(
            ledger, coverage, 170, 171,
            require_fully_outside_success=True,
        )
        final_counts = gzip.decompress(
            (generation / coverage["slot_counts"]["path"]).read_bytes())
        assert list(final_counts) == [fresh[170], fresh[171]]


def test_fallback_rechecks_removed_from_published_coverage():
    with tempfile.TemporaryDirectory(prefix="f03-stale-recheck-") as td:
        root = Path(td)
        asset_path, _asset, asset_counts = _write_asset(root)
        target_slot = 180
        assert asset_counts[target_slot - LOWER] == 3

        raw = {"number": NEW_HEAD, "hash": "new-head-hash"}
        responses = {
            probe.request_digest("sqd-head", {}): {"ok": True, "value": raw},
            probe.request_digest("sqd-stream", _anchor_body()): {
                "ok": True,
                "value": [_block(OLD_HEAD, 2, block_hash=ANCHOR_HASH)],
            },
        }
        for start, end in ((LOWER, LOWER + 63), (170, 171), (180, 180)):
            values = []
            for slot in range(start, end + 1):
                count = asset_counts[slot - LOWER]
                if slot == target_slot:
                    count = 4
                if count > 1:
                    values.append(_block(slot, count))
            responses[probe.request_digest(
                "sqd-stream", probe.sqd_query_body(start, end))] = {
                    "ok": True, "value": values}
        responses[probe.request_digest(
            "sqd-stream", probe.sqd_query_body(LOWER, UPPER))] = {
                "ok": True,
                "value": [_block(slot, 5) for slot in range(LOWER, UPPER + 1)],
            }
        fixture = root / "transport"
        fixture.mkdir()
        (fixture / "responses.json").write_text(json.dumps({
            "format": "sqd-coverage-transport-fixture-v1",
            "responses": responses,
        }), encoding="utf-8")

        case = root / "case"
        assert probe.main([
            "--mint", MINT, "--case-root", str(case),
            "--from-slot", str(LOWER), "--to-slot", str(UPPER),
            "--known-map", str(asset_path), "--no-getblocks",
            "--transport-fixture", str(fixture),
        ]) == 0
        pointer_path = case / "data/sqd_coverage/CURRENT.json"
        pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
        generation = case / "data/sqd_coverage" / pointer["probe_id"]
        coverage_path = generation / "coverage_map.json"
        coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
        checked = exact.validate_coverage(
            case, coverage_path, pointer_path, LOWER, UPPER)
        assert checked["ok"], checked
        ledger = [json.loads(line) for line in
                  (generation / "ledger.jsonl").read_text(
                      encoding="utf-8").splitlines() if line.strip()]
        target_rows = [row for row in ledger
                       if row.get("mode") == "recheck"
                       and row.get("from") == target_slot]
        assert len(target_rows) == 1 and target_rows[0]["ok"] is True, ledger
        assert target_rows[0]["counts_coverage"] is False, target_rows[0]
        assert all(row["mode"] != "recheck" for row in coverage["scan_ranges"]), \
            coverage["scan_ranges"]
        final_counts = gzip.decompress(
            (generation / coverage["slot_counts"]["path"]).read_bytes())
        assert final_counts[target_slot - LOWER] == 5


def _identity(asset, raw, *, metadata=None, fingerprint=None):
    metadata = probe._normalize_metadata(raw) if metadata is None else metadata
    fingerprint = (probe.endpoint_fingerprint("fixture://sqd")["sha256"]
                   if fingerprint is None else fingerprint)
    return probe._validate_known_map_identity(
        asset, fingerprint, metadata, raw)


def test_identity_reason_matrix_and_tracked_asset_json_only():
    with tempfile.TemporaryDirectory(prefix="f03-identity-") as td:
        root = Path(td)
        _asset_path, asset, _counts = _write_asset(root)
        good_raw = _metadata(NEW_HEAD, "new-head-hash")
        assert _identity(asset, good_raw)["ok"]

        changed = copy.deepcopy(good_raw)
        changed["dataset_id"] = "other-dataset"
        assert _identity(asset, changed)["reason"] == "metadata-identity-changed"
        for unknown in (7, ["not-normalized"]):
            changed = copy.deepcopy(good_raw)
            changed["unknown_field"] = unknown
            assert _identity(asset, changed)["reason"] == "metadata-identity-changed"
        conflict = copy.deepcopy(good_raw)
        conflict["height"] = NEW_HEAD - 1
        assert _identity(asset, conflict)["reason"] == "metadata-alias-conflict"
        for bad in (True, -1, "1010"):
            changed = copy.deepcopy(good_raw)
            changed["number"] = bad
            changed.pop("finalized_head", None)
            assert _identity(asset, changed, metadata=_metadata(NEW_HEAD))["reason"] \
                == "head-invalid"

        regressed = _metadata(OLD_HEAD - 1)
        assert _identity(asset, regressed)["reason"] == "head-regressed"
        changed_asset = copy.deepcopy(asset)
        changed_asset["sqd"].pop("finalized_head_at_scan")
        assert _identity(changed_asset, good_raw)["reason"] == "head-at-scan-missing"
        changed_asset = copy.deepcopy(asset)
        changed_asset["slot_counts"]["to_slot"] = OLD_HEAD + 1
        assert _identity(changed_asset, good_raw)["reason"] == "map-exceeds-scan-head"
        changed_asset = copy.deepcopy(asset)
        changed_asset["sqd"].pop("query_body_sha256")
        assert _identity(changed_asset, good_raw)["reason"] == "query-template-missing"
        changed_asset = copy.deepcopy(asset)
        changed_asset["sqd"]["query_body_sha256"] = "0" * 64
        assert _identity(changed_asset, good_raw)["reason"] == "query-template-changed"
        changed_asset = copy.deepcopy(asset)
        changed_asset["sqd"]["metadata_normalized"].pop("hash")
        assert _identity(changed_asset, good_raw)["reason"] == "identity-anchor-unavailable"
        changed_asset = copy.deepcopy(asset)
        changed_asset["sqd"]["metadata_normalized"]["unknown_asset_field"] = 1
        assert _identity(changed_asset, good_raw)["reason"] == "metadata-identity-changed"
        assert _identity(asset, good_raw, fingerprint="0" * 64)["reason"] \
            == "endpoint-fingerprint-changed"

    tracked = json.loads((ROOT / "assets/sqd-solana-coverage-map/20260827.json")
                         .read_text(encoding="utf-8"))
    tracked_raw = copy.deepcopy(tracked["sqd"]["metadata_normalized"])
    result = probe._validate_known_map_identity(
        tracked, tracked["sqd"]["endpoint_fingerprint"], tracked_raw, tracked_raw)
    assert result["ok"], result


def test_stable_identity_types_and_real_head_shape():
    with tempfile.TemporaryDirectory(prefix="f03-stable-types-") as td:
        root = Path(td)
        _asset_path, asset, _counts = _write_asset(root)

        raw = _metadata(NEW_HEAD, "new-head-hash")
        raw["start_block"] = False
        assert _identity(asset, raw)["reason"] == "metadata-identity-changed"

        raw = _metadata(NEW_HEAD, "new-head-hash")
        raw["real_time"] = "false"
        assert _identity(asset, raw)["reason"] == "metadata-identity-changed"

        changed_asset = copy.deepcopy(asset)
        changed_asset["sqd"]["metadata_normalized"]["real_time"] = 1
        assert _identity(changed_asset, _metadata(NEW_HEAD))["reason"] \
            == "metadata-identity-changed"

        changed_asset = copy.deepcopy(asset)
        changed_asset["sqd"]["metadata_normalized"].pop("dataset_id")
        assert _identity(changed_asset, _metadata(NEW_HEAD))["reason"] \
            == "metadata-identity-changed"

        # Real SQD /head only exposes number/hash; stable configuration keys may
        # be absent from the raw response and must not be made mandatory here.
        raw = {"number": NEW_HEAD, "hash": "new-head-hash"}
        assert _identity(asset, raw)["ok"]


def _write_asset_json(root, asset, name):
    path = root / name
    path.write_text(json.dumps(asset), encoding="utf-8")
    return exact.validate_shared_map(path)


def test_shared_map_validator_depth_and_malformed_inputs():
    with tempfile.TemporaryDirectory(prefix="f03-validator-") as td:
        root = Path(td)
        _asset_path, asset, counts = _write_asset(root)

        bad_counts = bytearray(counts)
        bad_counts[5] = 0
        bad_path = root / "bad-zero.counts.bin.gz"
        bad_path.write_bytes(gzip.compress(bytes(bad_counts), mtime=0))
        changed = copy.deepcopy(asset)
        changed["slot_counts"].update(
            path=bad_path.name, size=bad_path.stat().st_size,
            sha256=exact.sha256_file(bad_path))
        checked = _write_asset_json(root, changed, "zero.json")
        assert "shared map counts contains UNSCANNED" in checked["reasons"], checked

        mutations = []
        changed = copy.deepcopy(asset)
        changed["candidate_slots"] = [True]
        mutations.append((changed, "shared map candidate_slots invalid"))
        changed = copy.deepcopy(asset)
        changed["candidate_slots"] = ["170"]
        mutations.append((changed, "shared map candidate_slots invalid"))
        changed = copy.deepcopy(asset)
        changed["candidate_slots"] = [UPPER + 1]
        mutations.append((changed, "shared map candidate_slots invalid"))
        changed = copy.deepcopy(asset)
        changed["sqd"]["metadata_sha256"] = "0" * 64
        mutations.append((changed, "shared map SQD metadata sha256 mismatch"))
        changed = copy.deepcopy(asset)
        changed["sqd"]["dataset"] = "other-dataset"
        mutations.append((changed, "shared map SQD dataset differs from metadata dataset_id"))
        changed = copy.deepcopy(asset)
        changed["sqd"]["finalized_head_at_scan"] += 1
        mutations.append((changed, "shared map SQD finalized head differs from metadata"))
        changed = copy.deepcopy(asset)
        changed["sqd"]["metadata_normalized"]["number"] += 1
        changed["sqd"]["metadata_sha256"] = exact.sha256_bytes(
            exact.canonical_json(changed["sqd"]["metadata_normalized"]))
        mutations.append((changed, "shared map SQD metadata aliases conflict"))
        changed = copy.deepcopy(asset)
        changed["sqd"]["metadata_normalized"]["real_time"] = 1
        mutations.append((changed, "shared map SQD stable identity invalid"))
        changed = copy.deepcopy(asset)
        changed["sqd"]["metadata_normalized"].pop("dataset_id")
        mutations.append((changed, "shared map SQD stable identity invalid"))
        changed = copy.deepcopy(asset)
        changed["sqd"] = None
        mutations.append((changed, "shared map SQD identity missing"))
        changed = copy.deepcopy(asset)
        changed["canary"] = "not-an-object"
        mutations.append((changed, "shared map canary must contain 64 slots and counts"))
        changed = copy.deepcopy(asset)
        changed["canary"]["slots"][1] = "101"
        mutations.append((changed, "shared map canary slots invalid"))
        for index, (changed, reason) in enumerate(mutations):
            checked = _write_asset_json(root, changed, f"mutation-{index}.json")
            assert not checked["ok"] and reason in checked["reasons"], checked


def _full_case(root):
    fixture = root / "full-transport"
    fixture.mkdir()
    raw = _metadata(NEW_HEAD, "new-head-hash")
    full_body = probe.sqd_query_body(LOWER, UPPER)
    responses = {
        probe.request_digest("sqd-head", {}): {"ok": True, "value": raw},
        probe.request_digest("sqd-stream", full_body): {
            "ok": True, "value": [_block(slot, 3)
                                  for slot in range(LOWER, UPPER + 1)]},
    }
    (fixture / "responses.json").write_text(json.dumps({
        "format": "sqd-coverage-transport-fixture-v1", "responses": responses,
    }), encoding="utf-8")
    case = root / "case"
    assert probe.main([
        "--mint", MINT, "--case-root", str(case),
        "--from-slot", str(LOWER), "--to-slot", str(UPPER), "--full",
        "--no-getblocks", "--transport-fixture", str(fixture),
    ]) == 0
    pointer_path = case / "data/sqd_coverage/CURRENT.json"
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    coverage_path = case / "data/sqd_coverage" / pointer["probe_id"] / "coverage_map.json"
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    return case, coverage_path, pointer_path, coverage, pointer


def _set_producer(coverage_path, pointer_path, coverage, pointer, sha):
    coverage = copy.deepcopy(coverage)
    pointer = copy.deepcopy(pointer)
    producer = {"path": "scripts/solana/sqd_coverage_probe.py", "sha256": sha}
    coverage["producer"] = producer
    coverage["probe_id"] = exact.compute_probe_id(coverage)
    coverage_path.write_bytes(exact.canonical_json(coverage) + b"\n")
    pointer["producer"] = producer
    pointer["probe_id"] = coverage["probe_id"]
    pointer["inputs"]["coverage_map"].update(
        size=coverage_path.stat().st_size, sha256=exact.sha256_file(coverage_path))
    pointer_path.write_bytes(exact.canonical_json(pointer) + b"\n")


def test_validate_coverage_historical_producer_matrix():
    with tempfile.TemporaryDirectory(prefix="f03-producer-") as td:
        case, coverage_path, pointer_path, coverage, pointer = _full_case(Path(td))

        _set_producer(coverage_path, pointer_path, coverage, pointer, OLD_PRODUCER)
        checked = exact.validate_coverage(case, coverage_path, pointer_path, LOWER, UPPER)
        assert checked["ok"], checked

        random_hash = "1" * 64
        _set_producer(coverage_path, pointer_path, coverage, pointer, random_hash)
        checked = exact.validate_coverage(case, coverage_path, pointer_path, LOWER, UPPER)
        assert "coverage producer sha256 mismatch" in checked["reasons"], checked

        original = producer_history.PRODUCER_HISTORY
        try:
            revoked_hash = "2" * 64
            producer_history.PRODUCER_HISTORY = (
                {"script": "scripts/solana/sqd_coverage_probe.py",
                 "sha256": revoked_hash, "protocol": exact.COVERAGE_SCHEMA,
                 "status": "ACTIVE"},
                {"script": "other.py", "sha256": revoked_hash,
                 "protocol": "other/v1", "status": "REVOKED"},
            )
            _set_producer(coverage_path, pointer_path, coverage, pointer, revoked_hash)
            checked = exact.validate_coverage(
                case, coverage_path, pointer_path, LOWER, UPPER)
            assert "coverage producer sha256 mismatch" in checked["reasons"], checked

            mismatch_hash = "3" * 64
            producer_history.PRODUCER_HISTORY = ({
                "script": "scripts/solana/sqd_coverage_probe.py",
                "sha256": mismatch_hash, "protocol": exact.COVERAGE_SCHEMA,
                "status": "ACTIVE",
            },)
            _set_producer(coverage_path, pointer_path, coverage, pointer, mismatch_hash)
            checked = exact.validate_coverage(
                case, coverage_path, pointer_path, LOWER, UPPER)
            assert "coverage producer sha256 mismatch" in checked["reasons"], checked
        finally:
            producer_history.PRODUCER_HISTORY = original


def main():
    tests = [
        test_head_forward_anchor_and_gap_exact_rechecks,
        test_anchor_mismatch_is_not_ignored,
        test_anchor_transport_exception_is_structured_and_audited,
        test_recheck_mismatch_still_falls_back,
        test_partial_request_failure_reuses_verified_ranges,
        test_partial_rate_limit_end_to_end_full_repairs_failed_ranges,
        test_retry_rescues_range_and_retry_mismatch_falls_back,
        test_canary_unavailable_and_canary_counts_changed_fall_back,
        test_truncated_and_worker_exception_ranges_are_unverified,
        test_exclusion_failure_falls_back_and_case_can_degrade_to_pure_full,
        test_fallback_rechecks_removed_from_published_coverage,
        test_identity_reason_matrix_and_tracked_asset_json_only,
        test_stable_identity_types_and_real_head_shape,
        test_shared_map_validator_depth_and_malformed_inputs,
        test_validate_coverage_historical_producer_matrix,
    ]
    for test in tests:
        test()
    print(f"PASS F-03 shared-map reuse: {len(tests)}/{len(tests)} groups")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
