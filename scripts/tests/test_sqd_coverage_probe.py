#!/usr/bin/env python3
"""Batch 2 offline regressions for the SQD coverage probe and validator."""
from __future__ import annotations

import gzip
import json
import os
import stat
import subprocess
import sys
import tempfile
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts/lib"), str(ROOT / "scripts/solana")]

from scripts.lib import solana_exact_validate as exact  # noqa: E402
from scripts.solana import sqd_coverage_probe as probe  # noqa: E402


PROBE = ROOT / "scripts/solana/sqd_coverage_probe.py"
FIXTURES = Path(__file__).with_name("fixtures") / "sqd_coverage"
MINT = "FixtureMint"


def run_cli(case, fixture, *extra):
    command = [
        sys.executable, str(PROBE), "--mint", MINT, "--case-root", str(case),
        "--from-slot", "100", "--to-slot", "103", "--full", "--workers", "2",
        "--transport-fixture", str(fixture), *extra,
    ]
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True)


def read_current(case):
    path = case / "data/sqd_coverage/CURRENT.json"
    pointer = json.loads(path.read_text(encoding="utf-8"))
    generation = case / "data/sqd_coverage" / pointer["probe_id"]
    coverage = json.loads((generation / "coverage_map.json").read_text(encoding="utf-8"))
    return pointer, generation, coverage


def test_batch1b_red_to_green_symbols():
    fixture = {
        "schema": exact.COVERAGE_SCHEMA, "version": 1, "chain": "solana",
        "mint": MINT, "probe_id": "", "era_params": dict(exact.ERA_PARAMS),
        "scan_ranges": [{"from_slot": 10, "to_slot": 14, "mode": "full"}],
        "sample_ranges": [{"from_slot": 15, "to_slot": 20}],
        "verdict": "INCONCLUSIVE",
    }
    fixture["probe_id"] = exact.compute_probe_id(fixture)
    result = probe.validate_coverage_map(
        fixture, case_from_slot=10, case_to_slot=20)
    assert not result["ok"] and any("scan_ranges union" in reason
                                    for reason in result["reasons"])
    print("GREEN 3 sample_ranges cannot fill formal scan_ranges gaps")

    base = bytes([1, 2, 3])
    cases = [
        (bytes([1, 0, 3]), 1, 3, [(1, 3)], [(1, 3)]),
        (bytes([1, 2]), 1, 3, [(1, 3)], [(1, 3)]),
        (base, 1, 3, [(1, 3)], [(1, 1), (3, 3)]),
    ]
    assert all(not probe.validate_slot_counts(*case)["ok"] for case in cases)
    print("GREEN 20 UNSCANNED/length/ledger holes fail closed")

    bitmap = exact.encode_bitmap([10, 12], 10, 12)
    good = {"from": 10, "to": 12, "response_ok": True,
            "array_monotonic_unique": True, "array_in_range": True,
            "reference_head_at_check": 12, "count": 2}
    assert probe.derive_getblocks_complete(good, bitmap, 10)
    mutations = [
        ({**good, "response_ok": False}, bitmap, 10),
        ({**good, "array_monotonic_unique": False}, bitmap, 10),
        ({**good, "array_in_range": False}, bitmap, 10),
        ({**good, "to": 500_010}, bitmap, 10),
        ({**good, "reference_head_at_check": 11}, bitmap, 10),
        ({**good, "to": 18, "count": 2}, b"", 10),
        ({**good, "count": 1}, bitmap, 10),
        ({**good, "count": 4}, bitmap, 10),
    ]
    assert all(not probe.derive_getblocks_complete(segment, raw, lower)
               for segment, raw, lower in mutations)
    padding_escape = {**good, "from": 12, "to": 15,
                      "reference_head_at_check": 15, "count": 1}
    assert probe.derive_getblocks_complete(padding_escape, bitmap, 10), \
        "pure conjunction intentionally lacks declared bitmap upper bound"
    print("GREEN 21 getBlocks complete eight-way conjunction")

    assert probe.validate_blocks_bitmap(bitmap, 10, 12)["ok"]
    assert not probe.validate_blocks_bitmap(b"", 10, 12)["ok"]
    assert not probe.validate_blocks_bitmap(b"\x82", 10, 12)["ok"]
    print("GREEN 28 bitmap length/popcount/range binding")

    assert hasattr(probe, "publish_probe_generation")
    print("GREEN 30 CAS/idempotence/directory fsync implementation present")


def test_four_states_and_integer_era():
    exact_boundary = bytes([3] * 9_900 + [2] * 100)
    classified = probe.classify_four_states(exact_boundary, 0)
    assert classified["summary"]["healthy"] == 9_900
    assert classified["summary"]["defect_candidate"] == 100
    assert classified["candidate_slots"] == list(range(9_900, 10_000))
    below = probe.classify_four_states(bytes([3] * 9_899 + [2] * 101), 0)
    assert below["summary"]["defect_candidate"] == 0
    assert below["summary"]["era_uncertain"] == 101

    bitmap = exact.encode_bitmap([0, 1, 3], 0, 3)
    confirmation = {
        "reference_head_at_check": 3,
        "blocks_bitmap": {"from_slot": 0},
        "ranges": [{"from": 0, "to": 3, "response_sha256": "0" * 64,
                    "count": 3, "response_ok": True,
                    "array_monotonic_unique": True, "array_in_range": True}],
    }
    states = probe.classify_four_states(bytes([3, 1, 1, 3]), 0,
                                        confirmation=confirmation,
                                        blocks_bitmap=bitmap)["states"]
    assert states == ["HEALTHY", "MISSING_BLOCK", "SKIPPED_CONFIRMED", "HEALTHY"]
    assert probe.classify_four_states(bytes([3, 1, 3]), 0)["states"][1] == "NO_HEADER"


def test_probe_id_and_canonical_float_rejection():
    payload = {"schema": exact.COVERAGE_SCHEMA, "probe_id": "ignored",
               "mint": MINT, "nested": {"n": 1}}
    first = exact.compute_probe_id(payload)
    payload["probe_id"] = first
    assert exact.compute_probe_id(payload) == first
    payload["nested"]["n"] = 2
    assert exact.compute_probe_id(payload) != first
    try:
        exact.canonical_json({"ratio": 0.99})
    except ValueError as exc:
        assert "float forbidden" in str(exc)
    else:
        raise AssertionError("canonical JSON accepted float")


def _pending(parent, probe_id, coverage=b"coverage"):
    path = parent / f"pending-{probe_id}"
    path.mkdir()
    for name, raw in {
        "coverage_map.json": coverage,
        "slot_counts.bin.gz": b"counts",
        "blocks.bin.gz": b"blocks",
        "ledger.jsonl": b"ledger\n",
    }.items():
        (path / name).write_bytes(raw)
    return path


def _pointer(parent, probe_id, supersedes):
    coverage = parent / f"pending-{probe_id}/coverage_map.json"
    return {"probe_id": probe_id, "supersedes": supersedes,
            "inputs": {"coverage_map": {"sha256": probe.sha256_file(coverage)}}}


def test_publish_protocol_cas_idempotence_and_three_directory_fsyncs():
    with tempfile.TemporaryDirectory(prefix="sqd-publish-") as td:
        case = Path(td)
        parent = case / "data/sqd_coverage"
        parent.mkdir(parents=True)
        probe_id = "1" * 16
        pending = _pending(parent, probe_id)
        pointer = _pointer(parent, probe_id, None)
        original_fsync = os.fsync
        directory_fsyncs = []

        def recording_fsync(fd):
            if stat.S_ISDIR(os.fstat(fd).st_mode):
                directory_fsyncs.append(fd)
            return original_fsync(fd)

        with mock.patch.object(probe.os, "fsync", side_effect=recording_fsync):
            action = probe.publish_probe_generation(
                case, pending, probe_id, pointer, observed_current=None)
        assert action == "published" and len(directory_fsyncs) == 3, directory_fsyncs
        current = json.loads((parent / "CURRENT.json").read_text())

        pending = _pending(parent, probe_id)
        pointer = _pointer(parent, probe_id, "wrong-but-idempotent")
        action = probe.publish_probe_generation(
            case, pending, probe_id, pointer, observed_current=current)
        assert action == "idempotent-republish" and not pending.exists()

        second = "2" * 16
        pending = _pending(parent, second, coverage=b"new coverage")
        bad = _pointer(parent, second, "not-current")
        try:
            probe.publish_probe_generation(
                case, pending, second, bad, observed_current=current)
        except RuntimeError as exc:
            assert "CAS failed" in str(exc)
        else:
            raise AssertionError("stale CAS overwrote CURRENT")
        assert (parent / second).is_dir(), "CAS orphan generation was not retained"
        assert json.loads((parent / "CURRENT.json").read_text())["probe_id"] == probe_id


def test_fixture_cli_publish_validate_no_getblocks_and_redaction():
    secret = "ULTRA_SECRET_FIXTURE_KEY_123456789"
    with tempfile.TemporaryDirectory(prefix="sqd-cli-") as td:
        case = Path(td)
        completed = run_cli(case, FIXTURES / "happy", "--reference-rpc",
                            f"https://rpc.invalid/?api-key={secret}")
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        pointer, generation, coverage = read_current(case)
        checked = exact.validate_coverage(
            case, generation / "coverage_map.json",
            case / "data/sqd_coverage/CURRENT.json", 100, 103)
        assert checked["ok"], checked
        assert coverage["candidate_slots"] == []
        assert checked["recomputed"]["states"] == [
            "HEALTHY", "ERA_UNCERTAIN", "SKIPPED_CONFIRMED", "HEALTHY"]
        assert all(checked["recomputed"]["getblocks_complete"])
        assert set(pointer["inputs"]) == {
            "coverage_map", "slot_counts", "ledger", "blocks_bitmap"}
        bad_pointer = json.loads(json.dumps(pointer))
        bad_pointer["inputs"]["coverage_map"]["sha256"] = "0" * 64
        bad_path = case / "bad-pointer.json"
        bad_path.write_text(json.dumps(bad_pointer), encoding="utf-8")
        rejected = exact.validate_coverage(
            case, generation / "coverage_map.json", bad_path, 100, 103)
        assert not rejected["ok"] and any("coverage_map sha256 mismatch" in reason
                                          for reason in rejected["reasons"])
        bad_path.unlink()

        escaped = json.loads(json.dumps(coverage))
        escaped["skipped_confirmation"]["ranges"][0].update(
            {"from": 101, "to": 104, "count": 2})
        escaped["probe_id"] = exact.compute_probe_id(escaped)
        escaped_path = case / "escaped-coverage.json"
        escaped_path.write_text(json.dumps(escaped), encoding="utf-8")
        escaped_pointer = json.loads(json.dumps(pointer))
        escaped_pointer["probe_id"] = escaped["probe_id"]
        escaped_pointer["inputs"]["coverage_map"] = {
            "path": "escaped-coverage.json", "size": escaped_path.stat().st_size,
            "sha256": exact.sha256_file(escaped_path)}
        escaped_pointer_path = case / "escaped-pointer.json"
        escaped_pointer_path.write_text(json.dumps(escaped_pointer), encoding="utf-8")
        rejected = exact.validate_coverage(
            case, escaped_path, escaped_pointer_path, 100, 103)
        assert not rejected["ok"] and any("escapes blocks bitmap" in reason
                                          for reason in rejected["reasons"])
        escaped_pointer_path.unlink()
        escaped_path.unlink()

        old_probe_id = pointer["probe_id"]
        second = run_cli(case, FIXTURES / "happy")
        assert second.returncode == 0, (second.stdout, second.stderr)
        second_pointer, second_generation, _second_coverage = read_current(case)
        assert second_pointer["supersedes"] == old_probe_id
        assert (case / "data/sqd_coverage" / old_probe_id).is_dir()
        traced = exact.validate_coverage(
            case, second_generation / "coverage_map.json",
            case / "data/sqd_coverage/CURRENT.json", 100, 103)
        assert traced["ok"], traced
        all_bytes = completed.stdout.encode() + completed.stderr.encode()
        for path in case.rglob("*"):
            if path.is_file():
                all_bytes += path.read_bytes()
        assert secret.encode() not in all_bytes

    with tempfile.TemporaryDirectory(prefix="sqd-no-blocks-") as td:
        case = Path(td)
        completed = run_cli(case, FIXTURES / "happy", "--no-getblocks")
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        pointer, _generation, coverage = read_current(case)
        assert coverage["skipped_confirmation"] is None
        assert "blocks_bitmap" not in pointer["inputs"]
        assert coverage["summary"]["no_header_unconfirmed"] == 1
        assert coverage["verdict"] == "INCONCLUSIVE"


def test_unscanned_resume_and_quota_stopped_resume():
    with tempfile.TemporaryDirectory(prefix="sqd-resume-") as td:
        case = Path(td)
        first = run_cli(case, FIXTURES / "resume_fail")
        assert first.returncode == 2 and "UNSCANNED" in first.stderr
        assert not (case / "data/sqd_coverage/CURRENT.json").exists()
        pending = list((case / "data/sqd_coverage").glob("pending-*"))
        assert len(pending) == 1 and (pending[0] / "resume_state.json").is_file()
        second = run_cli(case, FIXTURES / "happy", "--resume")
        assert second.returncode == 0, (second.stdout, second.stderr)
        assert (case / "data/sqd_coverage/CURRENT.json").is_file()

    with tempfile.TemporaryDirectory(prefix="sqd-quota-") as td:
        case = Path(td)
        first = run_cli(case, FIXTURES / "quota")
        assert first.returncode == 3, (first.stdout, first.stderr)
        pending = list((case / "data/sqd_coverage").glob("pending-*"))
        assert len(pending) == 1
        stopped = json.loads((pending[0] / "STOPPED.json").read_text())
        assert stopped == {"reason": "reference-quota", "cursor": 100}
        assert not (case / "data/sqd_coverage/CURRENT.json").exists()
        second = run_cli(case, FIXTURES / "happy", "--resume")
        assert second.returncode == 0, (second.stdout, second.stderr)


def test_periodic_checkpoint_kill_resume_at_batch_boundary():
    start_slot = 100
    end_slot = start_slot + probe.SQD_PAGE_SLOTS * 5 - 1
    with tempfile.TemporaryDirectory(prefix="sqd-checkpoint-") as td:
        root = Path(td)
        fixture = root / "fixture"
        fixture.mkdir()
        responses = {
            probe.request_digest("sqd-head", {}): {
                "ok": True,
                "value": {"dataset_id": "solana-mainnet", "start_block": 0,
                          "real_time": True, "number": end_slot + 100},
            },
        }
        for lower, upper in probe._partition(
                start_slot, end_slot, probe.SQD_PAGE_SLOTS):
            body = probe.sqd_query_body(lower, upper)
            responses[probe.request_digest("sqd-stream", body)] = {
                "ok": True,
                "value": [{"header": {"number": upper},
                           "instructions": [{"transactionIndex": 0}]}],
            }
        head_body = probe.rpc_body("getSlot", [{"commitment": "finalized"}], 1)
        responses[probe.request_digest("rpc-getSlot", head_body)] = {
            "ok": True,
            "value": {"jsonrpc": "2.0", "id": 1, "result": end_slot + 100},
        }
        blocks_body = probe.rpc_body(
            "getBlocks", [start_slot, end_slot, {"commitment": "finalized"}], 2)
        responses[probe.request_digest("rpc-getBlocks", blocks_body)] = {
            "ok": True,
            "value": {"jsonrpc": "2.0", "id": 2,
                      "result": list(range(start_slot, end_slot + 1))},
        }
        (fixture / "responses.json").write_text(json.dumps({
            "format": "sqd-coverage-transport-fixture-v1",
            "responses": responses,
        }), encoding="utf-8")

        def argv(case, *extra):
            return [
                "--mint", MINT, "--case-root", str(case),
                "--from-slot", str(start_slot), "--to-slot", str(end_slot),
                "--full", "--workers", "1",
                "--reference-rpc", "https://rpc.fixture.invalid/",
                "--transport-fixture", str(fixture), *extra,
            ]

        uninterrupted_case = root / "uninterrupted"
        assert probe.main(argv(uninterrupted_case)) == 0
        uninterrupted_pointer, uninterrupted_generation, uninterrupted_coverage = (
            read_current(uninterrupted_case))
        assert not (uninterrupted_generation / "resume_state.json").exists(), \
            "default checkpoint interval fired in a five-page fixture"

        interrupted_case = root / "interrupted"
        original_transport = probe.FixtureTransport
        transport_instances = []

        class RecordingFixtureTransport(original_transport):
            def __init__(self, directory):
                super().__init__(directory)
                transport_instances.append(self)

        original_write_resume = probe._write_resume
        checkpoint_writes = []

        def write_checkpoint_then_kill(*args, **kwargs):
            original_write_resume(*args, **kwargs)
            checkpoint_writes.append(args[0])
            raise RuntimeError("injected-kill")

        with mock.patch.object(probe, "FixtureTransport",
                               RecordingFixtureTransport), \
                mock.patch.object(probe, "_write_resume",
                                  side_effect=write_checkpoint_then_kill):
            first_rc = probe.main(argv(
                interrupted_case, "--checkpoint-every", "1"))
        assert first_rc == 2
        assert len(checkpoint_writes) == 1
        first_stream_calls = [call for call in transport_instances[-1].calls
                              if call["kind"] == "sqd-stream"]
        assert len(first_stream_calls) == 4, first_stream_calls
        pending = list((interrupted_case / "data/sqd_coverage").glob("pending-*"))
        assert len(pending) == 1
        resume_state = json.loads(
            (pending[0] / "resume_state.json").read_text(encoding="utf-8"))
        assert resume_state["format"] == "sqd-coverage-resume-v1"
        checkpoint_counts = gzip.decompress(
            (pending[0] / "slot_counts.bin.gz").read_bytes())
        assert sum(value != 0 for value in checkpoint_counts) \
            == probe.SQD_PAGE_SLOTS * 4

        transport_instances.clear()
        with mock.patch.object(probe, "FixtureTransport",
                               RecordingFixtureTransport):
            resumed_rc = probe.main(argv(
                interrupted_case, "--checkpoint-every", "1", "--resume"))
        assert resumed_rc == 0
        resumed_stream_calls = [call for call in transport_instances[-1].calls
                                if call["kind"] == "sqd-stream"]
        assert len(resumed_stream_calls) == 1, resumed_stream_calls

        resumed_pointer, resumed_generation, resumed_coverage = read_current(
            interrupted_case)
        assert probe.sha256_file(uninterrupted_generation / "slot_counts.bin.gz") \
            == probe.sha256_file(resumed_generation / "slot_counts.bin.gz")
        assert probe.sha256_file(uninterrupted_generation / "blocks.bin.gz") \
            == probe.sha256_file(resumed_generation / "blocks.bin.gz")
        assert uninterrupted_coverage["summary"] == resumed_coverage["summary"]
        assert uninterrupted_pointer["probe_id"] != resumed_pointer["probe_id"]
        assert resumed_coverage["ledger"]["requests"] \
            == uninterrupted_coverage["ledger"]["requests"] + 1

        ledger = [json.loads(line) for line in (
            resumed_generation / "ledger.jsonl").read_text(
                encoding="utf-8").splitlines() if line.strip()]
        assert [row["seq"] for row in ledger] == list(range(len(ledger)))
        successful = [probe._successful_coverage_range(row) for row in ledger
                      if row.get("mode") == "full"]
        assert exact.merge_ranges(item for item in successful if item is not None) \
            == [(start_slot, end_slot)]


def test_dry_run_has_no_artifacts():
    with tempfile.TemporaryDirectory(prefix="sqd-dry-") as td:
        case = Path(td) / "case"
        completed = run_cli(case, FIXTURES / "happy", "--dry-run")
        assert completed.returncode == 0, completed.stderr
        payload = json.loads(completed.stdout)
        assert payload["slots"] == 4
        assert payload["estimated_sqd_requests_lower_bound"] == 1
        assert payload["sqd_request_estimate"] == {
            "empirical_slots_per_page_upper_bound": 450,
            "uncertain": True,
            "reason": "SQD stream pages can truncate before the requested end",
        }
        assert not case.exists()


def test_sqd_cursor_pagination_regressions():
    """Cursor pages, empty success, and malformed pages are fail-closed."""
    counts = bytearray(4)
    ledger = []
    probe._scan_ranges(
        probe.FixtureTransport(FIXTURES / "pagination"), counts, 100,
        [(100, 103)], 1, ledger, ["fixture://sqd"])
    assert counts == bytes([1, 2, 4, 3]), (
        "RED B2B-PAGE-01 truncated page tail was classified NO_HEADER", counts)
    assert len(ledger) == 2
    assert [row["from"] for row in ledger] == [100, 102]
    assert sum(row["slots_covered"] for row in ledger) == 4
    assert [(row["returned_from"], row["returned_to"], row["n_blocks"])
            for row in ledger] == [(101, 101, 1), (102, 103, 2)]
    assert all(row["empty_response"] is False for row in ledger)
    reasons = []
    actual_ranges, empty_count = exact._success_ranges(ledger, reasons)
    assert actual_ranges == [(100, 101), (102, 103)]
    assert empty_count == 0 and reasons == []

    empty_counts = bytearray(4)
    empty_ledger = []
    probe._scan_ranges(
        probe.FixtureTransport(FIXTURES / "empty"), empty_counts, 100,
        [(100, 103)], 1, empty_ledger, ["fixture://sqd"])
    assert empty_counts == bytes([1, 1, 1, 1])
    assert len(empty_ledger) == 1
    assert empty_ledger[0]["empty_response"] is True
    assert empty_ledger[0]["slots_covered"] == 4
    assert empty_ledger[0]["returned_from"] is None
    assert empty_ledger[0]["returned_to"] is None
    assert empty_ledger[0]["n_blocks"] == 0
    reasons = []
    actual_ranges, empty_count = exact._success_ranges(empty_ledger, reasons)
    assert actual_ranges == [(100, 103)]
    assert empty_count == 1 and reasons == []

    forged = dict(ledger[0], slots_covered=4)
    reasons = []
    exact._success_ranges([forged], reasons)
    assert "nonempty SQD response cursor facts inconsistent" in reasons

    for start in (100, 200, 300):
        invalid_counts = bytearray(4)
        invalid_ledger = []
        probe._scan_ranges(
            probe.FixtureTransport(FIXTURES / "invalid_pages"),
            invalid_counts, start, [(start, start + 3)], 1,
            invalid_ledger, ["fixture://sqd"])
        assert invalid_counts == bytes(4)
        assert len(invalid_ledger) == 1
        assert invalid_ledger[0]["ok"] is False
        assert invalid_ledger[0]["slots_covered"] == 0

    with tempfile.TemporaryDirectory(prefix="sqd-page-invalid-") as td:
        case = Path(td)
        completed = run_cli(case, FIXTURES / "invalid_pages", "--no-getblocks")
        assert completed.returncode == 2 and "UNSCANNED" in completed.stderr
        assert not (case / "data/sqd_coverage/CURRENT.json").exists()

    for fixture_name, expected_empty in (("pagination", 0), ("empty", 1)):
        with tempfile.TemporaryDirectory(prefix=f"sqd-page-{fixture_name}-") as td:
            case = Path(td)
            completed = run_cli(case, FIXTURES / fixture_name, "--no-getblocks")
            assert completed.returncode == 0, (completed.stdout, completed.stderr)
            _pointer, generation, _coverage = read_current(case)
            checked = exact.validate_coverage(
                case, generation / "coverage_map.json",
                case / "data/sqd_coverage/CURRENT.json", 100, 103)
            assert checked["ok"], checked
            assert checked["recomputed"]["empty_response_count"] == expected_empty

    class BoundedPageTransport:
        def call(self, kind, body):
            assert kind == "sqd-stream"
            start, end = body["fromBlock"], body["toBlock"]
            page_end = min(end, start + 99)
            return probe.net.Result(ok=True, value=[
                {"header": {"number": slot}, "instructions": []}
                for slot in range(start, page_end + 1)])

    parallel_counts = bytearray(904)
    parallel_ledger = []
    probe._scan_ranges(
        BoundedPageTransport(), parallel_counts, 1_000,
        [(1_000, 1_903)], 4, parallel_ledger, ["fixture://sqd"])
    assert parallel_counts == bytes([2]) * 904
    assert len(parallel_ledger) == 11
    reasons = []
    parallel_ranges, _empty = exact._success_ranges(parallel_ledger, reasons)
    assert exact.merge_ranges(parallel_ranges) == [(1_000, 1_903)]
    assert reasons == []


def test_shared_map_lifecycle_rechecks_all_known_and_canary():
    with tempfile.TemporaryDirectory(prefix="sqd-map-") as td:
        root = Path(td)
        counts = bytes([3] * 64)
        counts_path = root / "map.counts.bin.gz"
        counts_path.write_bytes(gzip.compress(counts, mtime=0))
        blocks_path = root / "map.blocks.bin.gz"
        blocks_path.write_bytes(gzip.compress(exact.encode_bitmap(
            range(200, 264), 200, 263), mtime=0))
        metadata = {"dataset_id": "solana-mainnet", "start_block": 0,
                    "real_time": True, "finalized_head": 1000,
                    "number": 1000, "hash": "fixture-anchor-1000"}
        fixture_fingerprint = probe.endpoint_fingerprint("fixture://sqd")["sha256"]
        asset = {
            "schema": "sqd-solana-shared-coverage-map/v1", "version": "20260823",
            "generated_at": datetime.now(timezone.utc).isoformat(), "ttl_days": 30,
            "supersedes": None,
            "sqd": {"dataset": "solana-mainnet",
                    "endpoint_fingerprint": fixture_fingerprint,
                    "finalized_head_at_scan": 1000,
                    "metadata_normalized": metadata,
                    "metadata_sha256": exact.sha256_bytes(
                        exact.canonical_json(metadata)),
                    "query_body_sha256": probe.sqd_query_template_sha256()},
            "slot_counts": {"path": counts_path.name,
                            "size": counts_path.stat().st_size,
                            "sha256": exact.sha256_file(counts_path),
                            "from_slot": 200, "to_slot": 263,
                            "encoding": exact.COUNT_ENCODING},
            "blocks_bitmap": {"path": blocks_path.name,
                              "size": blocks_path.stat().st_size,
                              "sha256": exact.sha256_file(blocks_path),
                              "from_slot": 200, "to_slot": 263,
                              "encoding": exact.BITMAP_ENCODING},
            "candidate_slots": [], "refuted_slots": [],
            "canary": {"slots": list(range(200, 264)), "counts": [3] * 64},
        }
        asset_path = root / "map.json"
        asset_path.write_text(json.dumps(asset), encoding="utf-8")
        responses = {}
        responses[probe.request_digest("sqd-head", {})] = {
            "ok": True, "value": metadata}
        anchor_body = probe.sqd_identity_anchor_body(1000)
        responses[probe.request_digest("sqd-stream", anchor_body)] = {
            "ok": True, "value": [{"header": {
                "number": 1000, "hash": "fixture-anchor-1000"}}]}
        range_body = probe.sqd_query_body(200, 263)
        responses[probe.request_digest("sqd-stream", range_body)] = {
            "ok": True, "value": [
                {"header": {"number": slot},
                 "instructions": [{"transactionIndex": 0}]}
                for slot in range(200, 264)]}
        for slot in range(200, 264):
            body = probe.sqd_query_body(slot, slot)
            responses[probe.request_digest("sqd-stream", body)] = {
                "ok": True, "value": [{"header": {"number": slot},
                                         "instructions": [{"transactionIndex": 0}]}]}
        fixture_dir = root / "transport"
        fixture_dir.mkdir()
        (fixture_dir / "responses.json").write_text(json.dumps({
            "format": "sqd-coverage-transport-fixture-v1",
            "responses": responses}), encoding="utf-8")
        ledger = []
        info, reused, lower, upper = probe._load_known_map(
            asset_path, 200, 263, fixture_fingerprint, metadata,
            probe.FixtureTransport(fixture_dir), ledger, ["fixture://sqd"])
        assert reused == counts and (lower, upper) == (200, 263)
        assert len(ledger) == 2 and "fallback_reason" not in info
        assert [(row["mode"], row["from"], row["to"])
                for row in ledger] == [
            ("identity-anchor", 1000, 1000), ("recheck", 200, 263)]
        assert len(info["canary"]["slots"]) == 64

        case = root / "case"
        rc = probe.main([
            "--mint", MINT, "--case-root", str(case),
            "--from-slot", "200", "--to-slot", "263",
            "--known-map", str(asset_path), "--no-getblocks",
            "--transport-fixture", str(fixture_dir),
        ])
        assert rc == 0
        pointer = json.loads((case / "data/sqd_coverage/CURRENT.json").read_text())
        coverage = json.loads((case / "data/sqd_coverage" / pointer["probe_id"]
                               / "coverage_map.json").read_text())
        assert {item["mode"] for item in coverage["scan_ranges"]} == {
            "map-reuse", "recheck"}
        assert coverage["shared_map"]["reused_ranges"] == [
            {"from_slot": 200, "to_slot": 263}]

        info, reused, _lower, _upper = probe._load_known_map(
            asset_path, 200, 263, "changed", metadata,
            probe.FixtureTransport(fixture_dir), [], ["fixture://sqd"])
        assert reused is None and info["fallback_reason"] == "endpoint-fingerprint-changed"


def test_guard_fixture_budget_and_no_run_threshold_detector():
    source = PROBE.read_text(encoding="utf-8").lower()
    for banned in ("run_length", "defect_run", "gap_threshold", "consecutive_zero"):
        assert banned not in source
    fixture_bytes = sum(path.stat().st_size for path in FIXTURES.rglob("*")
                        if path.is_file())
    assert fixture_bytes <= 200 * 1024, fixture_bytes
    hook = ROOT / "scripts/hooks/guard_file_ops.py"
    for rel in (
        "/case/data/sqd_coverage/CURRENT.json",
        "/case/data/sqd_coverage/0123456789abcdef/coverage_map.json",
        "/case/data/sqd_coverage/pending-0123456789abcdef/STOPPED.json",
    ):
        completed = subprocess.run(
            [sys.executable, str(hook)], input=json.dumps({
                "tool_name": "Write", "tool_input": {"file_path": rel}}),
            capture_output=True, text=True)
        assert completed.returncode == 0 and "deny" in completed.stdout, rel


def test_export_shared_map_roundtrip_and_tamper_rejection():
    """Group 12: published probe -> deterministic export -> known-map round trip."""
    with tempfile.TemporaryDirectory(prefix="sqd-export-map-") as td:
        root = Path(td)
        fixture = root / "transport"
        fixture.mkdir()
        lower, upper = 200, 263
        metadata = {"dataset_id": "solana-mainnet", "start_block": 0,
                    "real_time": True, "number": 1000,
                    "hash": "fixture-export-anchor-1000"}
        responses = {probe.request_digest("sqd-head", {}): {
            "ok": True, "value": metadata}}
        full_body = probe.sqd_query_body(lower, upper)
        responses[probe.request_digest("sqd-stream", full_body)] = {
            "ok": True, "value": [
                {"header": {"number": slot},
                 "instructions": [{"transactionIndex": 0}]}
                for slot in range(lower, upper + 1)]}
        anchor_body = probe.sqd_identity_anchor_body(1000)
        responses[probe.request_digest("sqd-stream", anchor_body)] = {
            "ok": True, "value": [{"header": {
                "number": 1000, "hash": "fixture-export-anchor-1000"}}]}
        for slot in range(lower, upper + 1):
            body = probe.sqd_query_body(slot, slot)
            responses[probe.request_digest("sqd-stream", body)] = {
                "ok": True, "value": [{"header": {"number": slot},
                                         "instructions": [{"transactionIndex": 0}]}]}
        head_body = probe.rpc_body("getSlot", [{"commitment": "finalized"}], 1)
        responses[probe.request_digest("rpc-getSlot", head_body)] = {
            "ok": True, "value": {"jsonrpc": "2.0", "id": 1, "result": 1000}}
        blocks_body = probe.rpc_body(
            "getBlocks", [lower, upper, {"commitment": "finalized"}], 2)
        responses[probe.request_digest("rpc-getBlocks", blocks_body)] = {
            "ok": True, "value": {"jsonrpc": "2.0", "id": 2,
                                    "result": list(range(lower, upper + 1))}}
        (fixture / "responses.json").write_text(json.dumps({
            "format": "sqd-coverage-transport-fixture-v1",
            "responses": responses}), encoding="utf-8")

        first_case = root / "first"
        base_args = [
            "--mint", MINT, "--case-root", str(first_case),
            "--from-slot", str(lower), "--to-slot", str(upper), "--full",
            "--reference-rpc", "https://rpc.fixture.invalid/",
            "--transport-fixture", str(fixture),
        ]
        assert probe.main(base_args) == 0
        pointer, _generation, first_coverage = read_current(first_case)
        out = root / "assets"
        export_args = ["export-shared-map", "--case-root", str(first_case),
                       "--probe-id", pointer["probe_id"], "--out", str(out),
                       "--version", "20260823"]
        assert probe.main(export_args) == 0
        triplet = [out / "20260823.json", out / "20260823.counts.bin.gz",
                   out / "20260823.blocks.bin.gz"]
        first_bytes = [path.read_bytes() for path in triplet]
        assert exact.validate_shared_map(triplet[0])["ok"]
        assert probe.main(export_args) == 0
        assert [path.read_bytes() for path in triplet] == first_bytes

        responses[probe.request_digest("sqd-head", {})] = {
            "ok": True, "value": {
                "dataset_id": "solana-mainnet", "start_block": 0,
                "real_time": True, "number": 1010,
                "hash": "fixture-current-head-1010"}}
        (fixture / "responses.json").write_text(json.dumps({
            "format": "sqd-coverage-transport-fixture-v1",
            "responses": responses}), encoding="utf-8")
        second_case = root / "second"
        roundtrip = [
            "--mint", MINT, "--case-root", str(second_case),
            "--from-slot", str(lower), "--to-slot", str(upper),
            "--known-map", str(triplet[0]), "--no-getblocks",
            "--transport-fixture", str(fixture),
        ]
        assert probe.main(roundtrip) == 0
        _pointer2, _generation2, second_coverage = read_current(second_case)
        assert second_coverage["shared_map"]["reused_ranges"]
        assert second_coverage["shared_map"]["canary"]["slots"] \
            == json.loads(triplet[0].read_text())["canary"]["slots"]
        assert second_coverage["verdict"] == first_coverage["verdict"]

        damaged = bytearray(triplet[1].read_bytes())
        damaged[-1] ^= 1
        triplet[1].write_bytes(damaged)
        rejected = exact.validate_shared_map(triplet[0])
        assert not rejected["ok"] and any("counts" in reason
                                          for reason in rejected["reasons"])


W1_SLOTS = [500, 700]


def _w1_run(root, *, asset_path=None, lower=0, upper=9999, changes=None, extra=(), expected_exit=0):
    root.mkdir(parents=True, exist_ok=True)
    fixture = root / "transport"
    fixture.mkdir(exist_ok=True)
    counts = bytes(2 if slot in W1_SLOTS else 3 for slot in range(10000))
    metadata = {"dataset_id": "solana-mainnet", "start_block": 0,
                "real_time": True, "number": 10010, "hash": "w1-head"}
    responses = {probe.request_digest("sqd-head", {}): {"ok": True, "value": metadata}}

    def response(start, end):
        return {"ok": True, "value": [
            {"header": {"number": slot}, "instructions": [
                {"transactionIndex": 0}] if counts[slot] == 3 else []}
            for slot in range(start, end + 1)]}

    ranges = list(probe._partition(lower, upper, 450))
    if asset_path:
        asset = json.loads(asset_path.read_text())
        ranges += probe._contiguous_ranges(sorted(set(
            asset["canary"]["slots"] + asset["candidate_slots"] + asset["refuted_slots"])))
        head = asset["sqd"]["finalized_head_at_scan"]
        responses[probe.request_digest("sqd-stream", probe.sqd_identity_anchor_body(head))] = {
            "ok": True, "value": [{"header": {
                "number": head, "hash": asset["sqd"]["metadata_normalized"]["hash"]}}]}
    for start, end in ranges:
        responses[probe.request_digest("sqd-stream", probe.sqd_query_body(start, end))] = response(start, end)
    for (start, end), kind in (changes or {}).items():
        good = response(start, end)
        failure = {"ok": False, "category": "http", "http_status": 429, "message": "fixture"}
        if kind == "retry":
            value = [failure, good]
        elif kind == "unverified":
            value = [failure, failure, good]
        elif kind == "mismatch":
            value = deepcopy(good)
            value["value"][0]["instructions"] = [{"transactionIndex": 0}]
        else:
            value = failure
        responses[probe.request_digest("sqd-stream", probe.sqd_query_body(start, end))] = value
    responses[probe.request_digest("rpc-getSlot", probe.rpc_body(
        "getSlot", [{"commitment": "finalized"}], 1))] = {"ok": True, "value": 10010}
    responses[probe.request_digest("rpc-getBlocks", probe.rpc_body(
        "getBlocks", [lower, upper, {"commitment": "finalized"}], 2))] = {
            "ok": True, "value": list(range(lower, upper + 1))}
    (fixture / "responses.json").write_bytes(exact.canonical_json({
        "format": "sqd-coverage-transport-fixture-v1", "responses": responses}))
    case = root / "case"
    argv = ["--mint", MINT, "--case-root", str(case), "--from-slot", str(lower),
            "--to-slot", str(upper), "--transport-fixture", str(fixture), "--workers", "2"]
    argv += ["--known-map", str(asset_path)] if asset_path else ["--full"]
    assert probe.main(argv + list(extra)) == expected_exit
    if expected_exit:
        return case, None
    return case, read_current(case)


def _w1_export(case, out, *options):
    pointer, _, _ = read_current(case)
    args = probe.build_export_parser().parse_args([
        "--case-root", str(case), "--probe-id", pointer["probe_id"],
        "--out", str(out), "--version", "20260924", *options])
    probe.export_shared_map(args)
    path = out / "20260924.json"
    checked = exact.validate_shared_map(path)
    assert checked["ok"], checked
    return path, checked["asset"]


def _w1_asset(root):
    case, _ = _w1_run(root / "source")
    path, asset = _w1_export(case, root / "asset", "--no-repair")
    asset.update(refuted_slots=W1_SLOTS[:], refuted_origin=[0, 0], refuted_evidence=[{
        "kind": "repair-census", "source_mint": MINT, "probe_id": "1" * 16,
        "repair_gid": "2" * 16, "plan_digest": "3" * 16,
        "resolution_sha256": "4" * 64, "bundle_sha256": "5" * 64,
        "producer": {"path": "scripts/solana/sqd_gap_repair.py", "sha256": "6" * 64},
        "refuted_count": 2, "origin_generated_at": asset["generated_at"],
        "origin_asset_sha256": None, "asset_sha256": None}])
    asset["canary"] = {"slots": list(range(64)), "counts": [3] * 64}
    path.write_bytes(exact.canonical_json(asset))
    assert exact.validate_shared_map(path)["ok"]
    return path, asset


def _w1_check(case):
    _, generation, coverage = read_current(case)
    return exact.validate_coverage(case, generation / "coverage_map.json",
                                   case / "data/sqd_coverage/CURRENT.json",
                                   coverage["slot_counts"]["from_slot"],
                                   coverage["slot_counts"]["to_slot"])


def _w1_reseal(case, coverage, rows=None, *, classify=False):
    pointer, generation, _ = read_current(case)
    if rows is not None:
        for index, row in enumerate(rows):
            row["seq"] = index
        (generation / "ledger.jsonl").write_bytes(probe._ledger_bytes(rows))
        coverage["ledger"].update(probe._sha_ref(generation / "ledger.jsonl", "ledger.jsonl"))
        ranges, _ = exact._success_ranges(rows, [])
        coverage["ledger"].update(requests=len(rows), success_ranges_sha256=exact.sha256_bytes(
            exact.canonical_json([list(pair) for pair in exact.merge_ranges(ranges)])))
    if classify:
        counts = gzip.decompress((generation / "slot_counts.bin.gz").read_bytes())
        bitmap = gzip.decompress((generation / "blocks.bin.gz").read_bytes())
        result = exact.classify_four_states(counts, coverage["slot_counts"]["from_slot"],
            confirmation=coverage["skipped_confirmation"], blocks_bitmap=bitmap,
            inherited_refuted=frozenset((coverage.get("shared_map") or {}).get(
                "inherited_refuted", {}).get("slots", [])))
        for name in ("summary", "candidate_slots", "verdict"):
            coverage[name] = result[name]
    coverage["probe_id"] = exact.compute_probe_id(coverage)
    (generation / "coverage_map.json").write_bytes(exact.canonical_json(coverage))
    pointer["probe_id"] = coverage["probe_id"]
    pointer["producer"] = coverage["producer"]
    for key, filename in (("coverage_map", "coverage_map.json"), ("ledger", "ledger.jsonl")):
        pointer["inputs"][key] = probe._sha_ref(
            generation / filename, str((generation / filename).relative_to(case)))
    # read_current follows probe_id; retain the mutated generation under its new identity.
    new_generation = generation.parent / coverage["probe_id"]
    if new_generation != generation:
        if new_generation.exists():
            raise AssertionError("mutation identity collision")
        generation.rename(new_generation)
        for ref in pointer["inputs"].values():
            ref["path"] = str((new_generation / Path(ref["path"]).name).relative_to(case))
    (case / "data/sqd_coverage/CURRENT.json").write_bytes(exact.canonical_json(pointer))


def test_w1_inheritance_and_partial_retry_fallback():
    with tempfile.TemporaryDirectory(prefix="w1-inherit-") as td:
        root = Path(td).resolve()
        path, asset = _w1_asset(root)
        for label, changes, inherited in (
            ("success", {}, W1_SLOTS),
            ("retry", {(500, 500): "retry"}, W1_SLOTS),
            ("partial", {(500, 500): "unverified"}, [700]),
            ("mismatch", {(500, 500): "mismatch"}, []),
            ("canary-failure", {(0, 63): "failure"}, []),
        ):
            case, (_, generation, coverage) = _w1_run(root / label, asset_path=path, changes=changes)
            checked = _w1_check(case)
            assert checked["ok"], checked
            claim = coverage["shared_map"].get("inherited_refuted", {})
            assert claim.get("slots", []) == inherited
            if inherited:
                assert coverage["summary"]["inherited_refuted"] == len(inherited)
                assert claim["refuted_evidence"] == asset["refuted_evidence"]
                assert exact.sha256_file(generation / "shared_map_source.json") == claim["asset_sha256"]
                assert all(checked["recomputed"]["states"][slot] == "INHERITED_REFUTED" for slot in inherited)
            else:
                assert "inherited_refuted" not in coverage["summary"]
                assert "inherited_refuted" not in coverage["shared_map"]
            if inherited == W1_SLOTS:
                assert coverage["candidate_slots"] == []
                assert coverage["verdict"] == "NO_KNOWN_NONCE_OMISSION_DETECTED"
            if label == "partial":
                assert coverage["candidate_slots"] == [500]
                assert coverage["shared_map"]["unverified_ranges"] == [{"from_slot": 500, "to_slot": 500}]
        case, (_, _, coverage) = _w1_run(root / "subset", asset_path=path, upper=600)
        assert coverage["shared_map"]["inherited_refuted"]["slots"] == [500]
        assert coverage["shared_map"]["inherited_refuted"]["refuted_evidence"][0]["refuted_count"] == 2
        assert _w1_check(case)["ok"]
        asset["canary"] = {"slots": list(range(61)) + [499, 500, 501],
                           "counts": [3] * 61 + [3, 2, 3]}
        path.write_bytes(exact.canonical_json(asset))
        case, (_, generation, _) = _w1_run(root / "cross-boundary", asset_path=path, upper=500)
        assert _w1_check(case)["ok"]
        rows = [json.loads(line) for line in (generation / "ledger.jsonl").read_text().splitlines()]
        assert any(row.get("mode") == "recheck" and row["from"] == 499 and row["to"] == 501
                   and row["counts_coverage"] is False for row in rows)


def test_w1_inherited_tamper_rejection():
    with tempfile.TemporaryDirectory(prefix="w1-tamper-") as td:
        root = Path(td).resolve()
        path, _ = _w1_asset(root)
        for label in ("foreign", "asset-sha", "missing-recheck", "missing-copy", "copy-sha",
                      "outside", "negative", "bool", "duplicate", "unverified", "short",
                      "evidence", "expired", "fallback", "origin-time", "negative-origin",
                      "bool-origin", "outside-origin", "subset-count", "query", "response",
                      "response-rehashed", "bool-count", "recheck-status", "map-reuse-removed",
                      "expired-origin"):
            case, (_, generation, coverage) = _w1_run(root / label, asset_path=path, upper=600)
            claim = coverage["shared_map"]["inherited_refuted"]
            rows = [json.loads(line) for line in (generation / "ledger.jsonl").read_text().splitlines()]
            if label in {"foreign", "outside", "negative", "bool", "duplicate"}:
                claim["slots"] = {"foreign": [499], "outside": [10000], "negative": [-1],
                                  "bool": [True], "duplicate": [500, 500]}[label]
                claim["count"] = len(claim["slots"])
                claim["origin"] = [0] * claim["count"]
            elif label == "asset-sha": claim["asset_sha256"] = "0" * 64
            elif label == "missing-copy": (generation / "shared_map_source.json").unlink()
            elif label == "copy-sha": (generation / "shared_map_source.json").write_bytes(b"{}")
            elif label == "unverified": coverage["shared_map"]["unverified_ranges"] = [{"from_slot": 500, "to_slot": 500}]
            elif label in {"evidence", "subset-count"}: claim["refuted_evidence"][0]["refuted_count"] = 1
            elif label == "expired": claim["verified_at"] = (datetime.now(timezone.utc) + timedelta(days=31)).isoformat()
            elif label == "fallback": coverage["shared_map"]["fallback_reason"] = "recheck-mismatch:500"
            elif label == "origin-time": claim["refuted_evidence"][0]["origin_generated_at"] = "2000-01-01T00:00:00+00:00"
            elif label == "bool-count": claim["count"] = True
            elif label == "map-reuse-removed": rows = [row for row in rows if row.get("mode") != "map-reuse"]
            elif label == "expired-origin":
                source = generation / "shared_map_source.json"
                asset = json.loads(source.read_text())
                asset["refuted_evidence"][0]["origin_generated_at"] = (
                    datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
                source.write_bytes(exact.canonical_json(asset))
                ref = probe._sha_ref(source, source.name)
                claim.update(source_ref=ref, asset_sha256=ref["sha256"],
                             refuted_evidence=asset["refuted_evidence"])
                coverage["shared_map"]["sha256"] = ref["sha256"]
                for row in rows:
                    if row.get("mode") == "map-reuse":
                        row["query_body_sha256"] = exact.sha256_bytes(exact.canonical_json({"asset": ref["sha256"]}))
            elif label.endswith("-origin"):
                claim["origin"] = [{"negative-origin": -1, "bool-origin": True, "outside-origin": 1}[label]]
            else:
                row = next(row for row in rows if row.get("mode") == "recheck" and row["from"] == 500)
                if label == "missing-recheck": rows.remove(row)
                elif label == "short": row["slots_covered"] = 0; row["counts_coverage"] = False
                elif label == "query": row["query_body_sha256"] = "0" * 64
                elif label == "response": row["recheck_response"][0]["instructions"] = [{"transactionIndex": 0}]
                elif label == "recheck-status": row["http_status"] = 429
                elif label == "response-rehashed":
                    row["recheck_response"][0]["instructions"] = [{"transactionIndex": 0}]
                    raw = exact.canonical_json(row["recheck_response"])
                    row.update(bytes=len(raw), response_sha256=exact.sha256_bytes(raw))
            _w1_reseal(case, coverage, rows)
            checked = _w1_check(case)
            assert not checked["ok"] and any("inherited refuted" in reason for reason in checked["reasons"]), (label, checked)
            assert not any("pointer" in reason or "probe_id" in reason or "ledger seq" in reason
                           for reason in checked["reasons"]), (label, checked)


def _w1_repair(case, *, confirmed=(700,), beta=()):
    pointer, generation, coverage = read_current(case)
    checked = _w1_check(case)
    assert checked["ok"], checked
    counts = gzip.decompress((generation / "slot_counts.bin.gz").read_bytes())
    gid = "a" * 16
    parent, current, _ = probe.sqd_repair_paths(case, MINT)
    repair_generation = parent / f"gen-{gid}"
    repair_generation.mkdir(parents=True, exist_ok=True)
    census = []
    for slot in sorted(set(coverage["candidate_slots"]) | set(beta)):
        offset = slot - coverage["slot_counts"]["from_slot"]
        census.append({
            "slot": slot, "state_in_map": "DEFECT_CANDIDATE",
            "coverage_state": checked["recomputed"]["states"][offset],
            "result": "confirmed_other_defect" if slot in confirmed else "refuted",
            "sqd_nonce_count_at_repair": counts[offset] - 2,
            "sqd_tx_count": 1, "ref_tx_count": 1 + int(slot in confirmed),
            "ref_nonvote_count": 1 + int(slot in confirmed),
            "sqd_blockhash": f"hash-{slot}", "ref_blockhash": f"hash-{slot}",
            "missing_total": int(slot in confirmed), "missing_nonce": 0,
            "missing_err_excluded": 0,
        })
    resolution = {
        "schema": exact.REPAIR_RESOLUTION_SCHEMA, "mint": MINT, "plan_digest": "b" * 16,
        "coverage": {"probe_id": pointer["probe_id"], "map_sha256": exact.sha256_file(generation / "coverage_map.json")},
        "plan_candidates": {"coverage": coverage["candidate_slots"], "beta": list(beta)},
        "census": census, "effective_verdict": "DEFECTS_CONFIRMED",
    }
    bundle = {
        "schema": exact.REPAIR_BUNDLE_SCHEMA, "kind": "repair", "mint": MINT,
        "gid": gid, "mode": "formal", "reference": {"source": "live"},
        "plan_digest": resolution["plan_digest"],
        "producer": {"path": "scripts/solana/sqd_gap_repair.py",
                     "sha256": exact.sha256_file(ROOT / "scripts/solana/sqd_gap_repair.py")},
        "coverage": {"probe_id": pointer["probe_id"],
                     "map": probe._sha_ref(generation / "coverage_map.json",
                         str((generation / "coverage_map.json").relative_to(case)))},
    }
    repair_pointer = {"schema": exact.REPAIR_POINTER_SCHEMA,
                      "target": {"chain": "solana", "token": MINT},
                      "gid": gid, "mode": "formal", "verdict": "PASS", "exit_code": 0}
    _w1_bind_repair(case, repair_generation, bundle, resolution, repair_pointer)
    return repair_generation, bundle, resolution, repair_pointer


def _w1_bind_repair(case, generation, bundle, resolution, pointer):
    resolution_path = generation / "coverage_resolution.json"
    resolution_path.write_bytes(exact.canonical_json(resolution))
    bundle["coverage_resolution"] = probe._sha_ref(resolution_path, resolution_path.name)
    bundle_path = generation / "bundle.json"
    bundle_path.write_bytes(exact.canonical_json(bundle))
    pointer["inputs"] = {"bundle": probe._sha_ref(bundle_path, str(bundle_path.relative_to(case)))}
    (generation.parent / "CURRENT.json").write_bytes(exact.canonical_json(pointer))


def _w1_expect_export_error(case, out, *options):
    try:
        _w1_export(case, out, *options)
    except ValueError:
        return
    raise AssertionError("invalid repair source exported")


def test_w1_repair_export_binding_and_conflicts():
    with tempfile.TemporaryDirectory(prefix="w1-export-repair-") as td:
        root = Path(td).resolve()
        case, _ = _w1_run(root / "direct")
        _w1_expect_export_error(case, root / "unpublished", "--repair-gid", "a" * 16)
        _w1_expect_export_error(case, root / "empty-gid", "--repair-gid", "")
        generation, bundle, resolution, pointer = _w1_repair(case)
        path, asset = _w1_export(case, root / "valid", "--repair-gid", "a" * 16)
        assert asset["refuted_slots"] == [500] and asset["refuted_origin"] == [0]
        assert asset["refuted_evidence"][0]["kind"] == "repair-census"
        assert asset["refuted_evidence"][0]["producer"] == bundle["producer"]
        assert asset["refuted_evidence"][0]["origin_generated_at"] == read_current(case)[0]["published_at"]
        _w1_expect_export_error(case, root / "no-option")
        try:
            probe.build_export_parser().parse_args(["--case-root", str(case), "--probe-id", "1" * 16,
                "--out", str(root / "both"), "--repair-gid", "a" * 16, "--no-repair"])
        except SystemExit as exc:
            assert exc.code == 2
        else:
            raise AssertionError("mutually exclusive export options accepted")
        for label in ("pointer-path", "pointer-size", "pointer-hash", "pointer-mint", "pointer-gid",
                      "map-sha", "bundle-schema", "resolution-schema", "exploration", "duplicate",
                      "state", "producer", "nonce", "bool-slot", "missing", "blockhash", "plan-beta"):
            b, r, p = deepcopy(bundle), deepcopy(resolution), deepcopy(pointer)
            if label == "map-sha": r["coverage"]["map_sha256"] = "0" * 64
            elif label == "bundle-schema": b["schema"] = "invalid"
            elif label == "resolution-schema": r["schema"] = "invalid"
            elif label == "exploration": b["mode"] = "exploration"
            elif label == "duplicate": r["census"].append(deepcopy(r["census"][-1]))
            elif label == "state": r["census"][0]["coverage_state"] = "HEALTHY"
            elif label == "producer": b["producer"]["sha256"] = "0" * 64
            elif label == "nonce": r["census"][0]["sqd_nonce_count_at_repair"] = 1
            elif label == "bool-slot": r["census"][0]["slot"] = True
            elif label == "missing": r["census"][0]["missing_total"] = 1
            elif label == "blockhash": r["census"][0]["ref_blockhash"] = "wrong"
            elif label == "plan-beta": r["plan_candidates"]["beta"] = [900]
            _w1_bind_repair(case, generation, b, r, p)
            if label.startswith("pointer-"):
                if label == "pointer-path": p["inputs"]["bundle"]["path"] = str((generation / "wrong.json").relative_to(case))
                elif label == "pointer-size": p["inputs"]["bundle"]["size"] += 1
                elif label == "pointer-hash": p["inputs"]["bundle"]["sha256"] = "0" * 64
                elif label == "pointer-mint": p["target"]["token"] = "WrongMint"
                elif label == "pointer-gid": p["gid"] = "c" * 16
                (generation.parent / "CURRENT.json").write_bytes(exact.canonical_json(p))
            _w1_expect_export_error(case, root / label, "--repair-gid", "a" * 16)
            _w1_expect_export_error(case, root / (label + "-skip"), "--no-repair")
        _w1_bind_repair(case, generation, bundle, resolution, pointer)
        for label in ("refuted-count", "noncandidate", "counts-three"):
            mutated = deepcopy(asset)
            if label == "refuted-count": mutated["refuted_evidence"][0]["refuted_count"] = 2
            elif label == "noncandidate": mutated["refuted_slots"] = [499]
            else:
                binary = path.parent / mutated["slot_counts"]["path"]
                counts = bytearray(gzip.decompress(binary.read_bytes()))
                counts[500] = 3
                binary.write_bytes(gzip.compress(counts, mtime=0))
                mutated["slot_counts"].update(probe._sha_ref(binary, binary.name))
                mutated["candidate_slots"] = [700]
                mutated["canary"]["counts"] = [counts[slot] for slot in mutated["canary"]["slots"]]
            path.write_bytes(exact.canonical_json(mutated))
            checked = exact.validate_shared_map(path)
            assert not checked["ok"] and any("refuted" in reason for reason in checked["reasons"]), (label, checked)
        inherited_path, _ = _w1_asset(root / "inherited-source")
        inherited_case, _ = _w1_run(root / "inherited", asset_path=inherited_path)
        _w1_repair(inherited_case, confirmed=(500,), beta=(500,))
        for option in (("--repair-gid", "a" * 16), ("--no-repair",)):
            _, exported = _w1_export(inherited_case, root / option[0][2:], *option)
            assert exported["refuted_slots"] == [700]
            assert exported["refuted_evidence"][0]["refuted_count"] == 1


def test_w1_chain_origin_ttl_and_reindex():
    with tempfile.TemporaryDirectory(prefix="w1-chain-") as td:
        root = Path(td).resolve()
        case, _ = _w1_run(root / "direct")
        _w1_repair(case, confirmed=(900,), beta=(900,))
        first_path, first = _w1_export(case, root / "first", "--repair-gid", "a" * 16)
        assert first["refuted_slots"] == W1_SLOTS
        first["canary"] = {"slots": list(range(64)), "counts": [3] * 64}
        first_path.write_bytes(exact.canonical_json(first))
        origin_time = first["refuted_evidence"][0]["origin_generated_at"]
        first_sha = exact.sha256_file(first_path)
        prior_path = first_path
        for index, expected in enumerate((W1_SLOTS, [500])):
            changes = {} if index == 0 else {(700, 700): "unverified"}
            chain_case, (_, _, coverage) = _w1_run(root / f"chain-{index}", asset_path=prior_path, changes=changes)
            path, asset = _w1_export(chain_case, root / f"export-{index}", "--no-repair")
            assert asset["candidate_slots"] == W1_SLOTS
            assert asset["refuted_slots"] == expected
            assert asset["refuted_origin"] == [0] * len(expected)
            evidence = asset["refuted_evidence"][0]
            assert evidence["kind"] == "inherited" and evidence["refuted_count"] == len(expected)
            assert evidence["origin_generated_at"] == origin_time
            assert evidence["origin_asset_sha256"] == first_sha
            assert evidence["asset_sha256"] == exact.sha256_file(prior_path)
            assert evidence["producer"] == coverage["producer"] and evidence["probe_id"] == coverage["probe_id"]
            assert all(evidence[key] is None for key in ("repair_gid", "plan_digest", "resolution_sha256", "bundle_sha256"))
            if index == 0:
                asset["canary"] = {"slots": list(range(64)), "counts": [3] * 64}
                path.write_bytes(exact.canonical_json(asset))
            prior_path = path
        with mock.patch.object(probe, "datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime.now(timezone.utc) + timedelta(days=31)
            _, expired = _w1_export(chain_case, root / "expired", "--no-repair")
        assert expired["refuted_slots"] == []
        assert _w1_check(chain_case)["ok"], "later checking must use original verified_at"


def test_w1_compatibility_determinism_resume_and_copy_protocol():
    baseline = subprocess.run(["git", "show",
        "6b36dcdd043d0b2b51c03de9ab0bb555b25f436a:scripts/lib/solana_exact_validate.py"],
        cwd=ROOT, text=True, capture_output=True, check=True).stdout
    original = {"__name__": "w1_baseline_exact", "__file__": str(ROOT / "scripts/lib/solana_exact_validate.py")}
    exec(compile(baseline, original["__file__"], "exec"), original)
    for counts in (bytes([0, 1, 2, 3, 255]), bytes([3] * 9998 + [2, 2]),
                   bytes([3] * 62 + [2, 2])):
        assert exact.classify_four_states(counts, 0) == original["classify_four_states"](counts, 0)
        assert exact.classify_four_states(counts, 0, inherited_refuted=frozenset()) == original["classify_four_states"](counts, 0)
    with tempfile.TemporaryDirectory(prefix="w1-compat-") as td:
        root = Path(td).resolve()
        asset_path, asset = _w1_asset(root)
        now = datetime.now(timezone.utc).isoformat()
        with mock.patch.object(probe, "utc_now", return_value=now):
            first, (p1, g1, _) = _w1_run(root / "deterministic1", asset_path=asset_path)
            _, (p2, g2, _) = _w1_run(root / "deterministic2", asset_path=asset_path)
        assert p1["probe_id"] == p2["probe_id"]
        assert (g1 / "coverage_map.json").read_bytes() == (g2 / "coverage_map.json").read_bytes()
        legacy_case, (_, _, coverage) = _w1_run(root / "legacy")
        assert "inherited_refuted" not in coverage["summary"] and coverage["shared_map"] is None
        coverage["producer"]["sha256"] = "c4980c984b08d27f5a7e46db50f97c9c16e47ea491f37a459b3773f939218769"
        _w1_reseal(legacy_case, coverage)
        assert _w1_check(legacy_case)["ok"]
        _, legacy = _w1_export(legacy_case, root / "legacy-export", "--no-repair")
        assert legacy["refuted_slots"] == [] and "refuted_evidence" not in legacy
        with mock.patch.object(probe, "_confirm_getblocks", return_value=(
                None, None, {"reason": "reference-quota", "cursor": 0})):
            _w1_run(root / "resume", asset_path=asset_path, expected_exit=3)
        resumed, (_, _, coverage) = _w1_run(root / "resume", asset_path=asset_path, extra=("--resume",))
        assert _w1_check(resumed)["ok"]
        assert coverage["shared_map"] is None and "inherited_refuted" not in coverage["summary"]
        assert coverage["candidate_slots"] == W1_SLOTS
        asset["refuted_evidence"][0]["origin_generated_at"] = (
            datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
        asset_path.write_bytes(exact.canonical_json(asset))
        expired, (_, _, coverage) = _w1_run(root / "expired-probe", asset_path=asset_path)
        assert _w1_check(expired)["ok"]
        assert "inherited_refuted" not in coverage["shared_map"]
        assert coverage["candidate_slots"] == W1_SLOTS

        parent = root / "publication/data/sqd_coverage"
        parent.mkdir(parents=True)
        case = parent.parent.parent
        gid = "d" * 16
        pending = _pending(parent, gid)
        (pending / "shared_map_source.json").write_bytes(b"source bytes")
        pointer = _pointer(parent, gid, None)
        assert probe.publish_probe_generation(case, pending, gid, pointer, observed_current=None) == "published"
        for label in ("same", "missing", "different"):
            if label != "different":
                pending = _pending(parent, gid)
            if label != "missing":
                (pending / "shared_map_source.json").write_bytes(
                    b"source bytes" if label == "same" else b"changed")
            try:
                result = probe.publish_probe_generation(case, pending, gid, pointer, observed_current=pointer)
            except RuntimeError as exc:
                assert label != "same" and "generation collision" in str(exc)
            else:
                assert label == "same" and result == "idempotent-republish"


def test_w1_origin_membership_and_export_index_compaction():
    with tempfile.TemporaryDirectory(prefix="w1-origins-") as td:
        root = Path(td).resolve()
        path, asset = _w1_asset(root)
        second = deepcopy(asset["refuted_evidence"][0])
        second["origin_generated_at"] = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        second["refuted_count"] = asset["refuted_evidence"][0]["refuted_count"] = 1
        asset["refuted_evidence"].append(second)
        asset["refuted_origin"] = [0, 1]
        path.write_bytes(exact.canonical_json(asset))
        case, (_, _, coverage) = _w1_run(root / "mismatch", asset_path=path)
        coverage["shared_map"]["inherited_refuted"]["origin"] = [1, 0]
        _w1_reseal(case, coverage)
        checked = _w1_check(case)
        assert not checked["ok"] and "inherited refuted slot/origin" in ";".join(checked["reasons"])
        case, _ = _w1_run(root / "confirmed", asset_path=path)
        _w1_repair(case, confirmed=(500,), beta=(500,))
        for options in (("--repair-gid", "a" * 16), ("--no-repair",)):
            _, result = _w1_export(case, root / options[0][2:], *options)
            assert result["refuted_slots"] == [700] and result["refuted_origin"] == [0]
            assert len(result["refuted_evidence"]) == 1
            assert result["refuted_evidence"][0]["origin_generated_at"] == second["origin_generated_at"]
            assert result["refuted_evidence"][0]["refuted_count"] == 1


def main():
    tests = [
        test_batch1b_red_to_green_symbols,
        test_four_states_and_integer_era,
        test_probe_id_and_canonical_float_rejection,
        test_publish_protocol_cas_idempotence_and_three_directory_fsyncs,
        test_fixture_cli_publish_validate_no_getblocks_and_redaction,
        test_unscanned_resume_and_quota_stopped_resume,
        test_periodic_checkpoint_kill_resume_at_batch_boundary,
        test_dry_run_has_no_artifacts,
        test_sqd_cursor_pagination_regressions,
        test_shared_map_lifecycle_rechecks_all_known_and_canary,
        test_export_shared_map_roundtrip_and_tamper_rejection,
        test_guard_fixture_budget_and_no_run_threshold_detector,
        test_w1_inheritance_and_partial_retry_fallback,
        test_w1_inherited_tamper_rejection,
        test_w1_repair_export_binding_and_conflicts,
        test_w1_chain_origin_ttl_and_reindex,
        test_w1_compatibility_determinism_resume_and_copy_protocol,
        test_w1_origin_membership_and_export_index_compaction,
    ]
    for test in tests:
        test()
    print(f"PASS SQD coverage probe: {len(tests)}/{len(tests)} offline groups")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
