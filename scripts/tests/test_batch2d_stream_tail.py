#!/usr/bin/env python3
"""Batch 2d: SQD HTTP-200 empty-body stream-tail semantics."""
from __future__ import annotations

import gzip
import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts/lib"),
                str(ROOT / "scripts/solana")]

from scripts.solana import sqd_coverage_probe as probe  # noqa: E402
from scripts.lib import solana_exact_validate as exact  # noqa: E402


EMPTY_STDOUT = "curl returned empty stdout"
MINT = "Batch2dFixtureMint"


def failed_result(category, message, status, *, retryable=True):
    return probe.net.Result(ok=False, error={
        "category": category,
        "message": message,
        "http_status": status,
        "retryable": retryable,
    })


class SequenceTransport:
    def __init__(self, *results):
        self.results = list(results)
        self.calls = []

    def call(self, kind, body):
        self.calls.append((kind, body))
        if not self.results:
            raise AssertionError("unexpected transport call")
        return self.results.pop(0)


def block(slot, instruction_count=0):
    return {"header": {"number": slot},
            "instructions": [{"transactionIndex": index}
                             for index in range(instruction_count)]}


def test_stream_tail_after_nonempty_page_is_complete_no_header():
    transport = SequenceTransport(
        probe.net.Result(ok=True, value=[block(101)]),
        failed_result("decode", EMPTY_STDOUT, 200),
    )
    pages = probe._scan_partition(
        transport, 100, 103, ["fixture://sqd"], mode="full")
    assert len(pages) == 2
    _cursor, row, counts = pages[1]
    assert row["ok"] is True
    assert row["empty_response"] is True
    assert row["slots_covered"] == 2
    assert row["response_sha256"] == probe.sha256_bytes(probe.canonical_json([]))
    assert counts == bytes([1, 1])
    assert probe._successful_coverage_range(row) == (102, 103)


def test_nonmatching_transport_failures_stay_failed():
    cases = [
        failed_result("decode", EMPTY_STDOUT, 529),
        failed_result("decode", "invalid JSON response: fixture", 200),
        failed_result("transport", EMPTY_STDOUT, 200),
    ]
    for result in cases:
        row, counts = probe._scan_request(
            SequenceTransport(result), 200, 202, 0,
            ["fixture://sqd"], mode="full")
        assert row["ok"] is False
        assert row["slots_covered"] == 0
        assert row["empty_response"] is False
        assert counts is None


def test_normal_block_array_counts_are_unchanged():
    value = [block(300, 1), block(302, 2)]
    row, counts = probe._scan_request(
        SequenceTransport(probe.net.Result(ok=True, value=value)),
        300, 303, 0, ["fixture://sqd"], mode="full")
    assert row["ok"] is True
    assert row["empty_response"] is False
    assert row["returned_from"] == 300
    assert row["returned_to"] == 302
    assert row["n_blocks"] == 2
    assert row["slots_covered"] == 3
    assert counts == bytes([3, 1, 4])


def test_small_interval_cli_has_no_unscanned_tail():
    lower, upper = 400, 403
    with tempfile.TemporaryDirectory(prefix="batch2d-tail-") as td:
        root = Path(td)
        fixture = root / "fixture"
        case = root / "case"
        fixture.mkdir()
        responses = {
            probe.request_digest("sqd-head", {}): {
                "ok": True,
                "value": {"dataset_id": "solana-mainnet", "start_block": 0,
                          "real_time": True, "number": 1000},
            },
            probe.request_digest(
                "sqd-stream", probe.sqd_query_body(lower, upper)): {
                    "ok": True, "value": [block(401)],
            },
            probe.request_digest(
                "sqd-stream", probe.sqd_query_body(402, upper)): {
                    "ok": False, "category": "decode",
                    "message": EMPTY_STDOUT, "http_status": 200,
                    "retryable": True,
            },
        }
        (fixture / "responses.json").write_text(json.dumps({
            "format": "sqd-coverage-transport-fixture-v1",
            "responses": responses,
        }), encoding="utf-8")
        rc = probe.main([
            "--mint", MINT, "--case-root", str(case),
            "--from-slot", str(lower), "--to-slot", str(upper),
            "--full", "--workers", "1", "--no-getblocks",
            "--transport-fixture", str(fixture),
        ])
        assert rc == 0
        pointer = json.loads(
            (case / "data/sqd_coverage/CURRENT.json").read_text(encoding="utf-8"))
        generation = case / "data/sqd_coverage" / pointer["probe_id"]
        counts = gzip.decompress(
            (generation / "slot_counts.bin.gz").read_bytes())
        assert counts == bytes([1, 2, 1, 1])
        assert 0 not in counts
        ledger = [json.loads(line) for line in
                  (generation / "ledger.jsonl").read_text(
                      encoding="utf-8").splitlines() if line.strip()]
        tail = [row for row in ledger
                if row.get("provider") == "SQD" and row.get("from") == 402]
        assert len(tail) == 1
        assert tail[0]["ok"] is True and tail[0]["empty_response"] is True
        checked = exact.validate_coverage(
            case, generation / "coverage_map.json",
            case / "data/sqd_coverage/CURRENT.json", lower, upper)
        assert checked["ok"], checked


def main():
    tests = [
        test_stream_tail_after_nonempty_page_is_complete_no_header,
        test_nonmatching_transport_failures_stay_failed,
        test_normal_block_array_counts_are_unchanged,
        test_small_interval_cli_has_no_unscanned_tail,
    ]
    for test in tests:
        test()
    print(f"PASS batch2d SQD stream tail: {len(tests)}/{len(tests)} groups")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
