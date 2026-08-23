#!/usr/bin/env python3
"""Batch 1b expected-red contract tests for the future SQD coverage probe."""

from __future__ import annotations

import importlib
import os
import stat
import sys


TARGET = "scripts.solana.sqd_coverage_probe"


def merged_ranges_cover(ranges, lower, upper):
    cursor = lower
    for start, end in sorted((int(a), int(b)) for a, b in ranges):
        if start > cursor:
            return False
        cursor = max(cursor, end + 1)
        if cursor > upper:
            return True
    return cursor > upper


def coverage_ok(fixture):
    counts = fixture["slot_counts"]
    expected = fixture["to_slot"] - fixture["from_slot"] + 1
    ledger = fixture["ledger_ranges"]
    return (
        len(counts) == expected
        and all(value != 0 for value in counts)
        and merged_ranges_cover(fixture["scan_ranges"], fixture["from_slot"], fixture["to_slot"])
        and merged_ranges_cover(ledger, fixture["from_slot"], fixture["to_slot"])
    )


def getblocks_complete(segment):
    width = segment["to"] - segment["from"] + 1
    bitmap = segment["bitmap"]
    return (
        segment["response_ok"] is True
        and segment["array_monotonic_unique"] is True
        and segment["array_in_range"] is True
        and width <= 500_000
        and segment["reference_head_at_check"] >= segment["to"]
        and len(bitmap) == width
        and sum(bitmap) == segment["count"]
        and segment["count"] <= width
    )


def pointer_cas(current, candidate):
    if current and current["probe_id"] == candidate["probe_id"]:
        return current["coverage_sha256"] == candidate["coverage_sha256"]
    current_id = None if current is None else current["probe_id"]
    return candidate["supersedes"] == current_id


def directory_fsync_complete(events):
    return events == ["probe_dir", "coverage_parent", "pointer_parent"]


def expected_red(item, symbol, detail):
    try:
        module = importlib.import_module(TARGET)
        if not hasattr(module, symbol):
            raise AttributeError(symbol)
    except (ImportError, AttributeError):
        print(f"EXPECTED_RED: {TARGET}/{symbol} 未实现")
        print(f"RED {item} missing-mechanism {detail}")
        return 1
    print(f"GREEN {item} implemented {symbol} 已实现")
    return 0


def main():
    red = 0

    # (3) sample_ranges cannot repair a gap in the formal scan_ranges union.
    fixture = {"scan_ranges": [(10, 14)], "sample_ranges": [(15, 20)]}
    assert not merged_ranges_cover(fixture["scan_ranges"], 10, 20)
    assert merged_ranges_cover(fixture["scan_ranges"] + fixture["sample_ranges"], 10, 20)
    red += expected_red("3", "validate_coverage_map", "sample_ranges 仍可能冒充 formal 全覆盖")

    # (20) Each independent structural defect must fail the oracle.
    base = {"from_slot": 1, "to_slot": 3, "slot_counts": [1, 2, 3],
            "scan_ranges": [(1, 3)], "ledger_ranges": [(1, 3)]}
    cases = [
        {**base, "slot_counts": [1, 0, 3]},
        {**base, "slot_counts": [1, 2]},
        {**base, "ledger_ranges": [(1, 1), (3, 3)]},
    ]
    assert all(not coverage_ok(case) for case in cases)
    red += expected_red("20", "validate_slot_counts", "UNSCANNED、长度错误或 ledger 洞尚无正式拒绝器")

    # (21) The errata E2 conjunction is required; flip each relevant predicate.
    good = {"from": 10, "to": 12, "response_ok": True,
            "array_monotonic_unique": True, "array_in_range": True,
            "reference_head_at_check": 12, "bitmap": [1, 0, 1], "count": 2}
    assert getblocks_complete(good)
    bad = []
    for key, value in [("response_ok", False), ("array_monotonic_unique", False),
                       ("array_in_range", False), ("reference_head_at_check", 11),
                       ("count", 4)]:
        bad.append({**good, key: value})
    bad.append({**good, "to": 500_010, "bitmap": [0] * 500_001, "count": 0})
    assert all(not getblocks_complete(case) for case in bad)
    red += expected_red("21", "derive_getblocks_complete", "getBlocks complete 合取式尚未实现")

    # (28) Bitmap length, popcount and interval binding are separate failures.
    bitmap_bad = [
        {**good, "bitmap": [1, 0]},
        {**good, "bitmap": [1, 0, 1], "count": 1},
        {**good, "from": 11, "to": 13, "reference_head_at_check": 13,
         "bitmap": [1, 0, 1], "count": 2, "array_in_range": False},
    ]
    assert all(not getblocks_complete(case) for case in bitmap_bad)
    red += expected_red("28", "validate_blocks_bitmap", "位图长度、popcount、范围绑定尚无正式拒绝器")

    # (30) CAS, same-id idempotence and the three directory fsyncs.
    current = {"probe_id": "p1", "coverage_sha256": "a"}
    assert not pointer_cas(current, {"probe_id": "p2", "coverage_sha256": "b", "supersedes": "old"})
    assert pointer_cas(current, {"probe_id": "p1", "coverage_sha256": "a", "supersedes": "old"})
    assert not pointer_cas(current, {"probe_id": "p1", "coverage_sha256": "changed", "supersedes": "p1"})
    assert directory_fsync_complete(["probe_dir", "coverage_parent", "pointer_parent"])
    assert not directory_fsync_complete(["probe_dir", "pointer_parent"])
    red += expected_red("30", "publish_probe_generation", "探针 CAS、幂等补发与三次目录 fsync 尚未实现")

    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main())
