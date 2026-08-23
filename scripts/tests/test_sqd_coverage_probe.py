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
from datetime import datetime, timezone
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
                    "real_time": True, "finalized_head": 1000}
        fixture_fingerprint = probe.endpoint_fingerprint("fixture://sqd")["sha256"]
        asset = {
            "schema": "sqd-solana-shared-coverage-map/v1", "version": "fixture",
            "generated_at": datetime.now(timezone.utc).isoformat(), "ttl_days": 30,
            "supersedes": None,
            "sqd": {"endpoint_fingerprint": fixture_fingerprint,
                    "metadata_normalized": metadata},
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
            "candidate_slots": [200], "refuted_slots": [201],
            "canary": {"slots": list(range(200, 264)), "counts": [3] * 64},
        }
        asset_path = root / "map.json"
        asset_path.write_text(json.dumps(asset), encoding="utf-8")
        responses = {}
        responses[probe.request_digest("sqd-head", {})] = {
            "ok": True, "value": metadata}
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
        assert len(ledger) == 64 and "fallback_reason" not in info
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
        test_guard_fixture_budget_and_no_run_threshold_detector,
    ]
    for test in tests:
        test()
    print(f"PASS SQD coverage probe: {len(tests)}/{len(tests)} offline groups")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
