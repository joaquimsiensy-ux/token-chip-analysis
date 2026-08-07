#!/usr/bin/env python3
"""B1-C regressions for the sole risk_flags canonical parser."""
from __future__ import annotations

import csv
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LABELS = ROOT / "scripts/labels"
sys.path.insert(0, str(LABELS))

from labels_resolver import LabelResolver
from risk_flags import canonical_risk_flags, merge_risk_flags, parse_risk_flags
from validate_labels import validate_file


FIELDS = ["address", "chain", "name", "category", "tier", "source", "added_date",
          "evidence", "risk_flags", "merge_policy", "balance_policy",
          "source_snapshot_at", "verified_at", "status", "raw_labels"]


def write_row(path, risk_flags, *, tier="exclude"):
    row = dict.fromkeys(FIELDS, "")
    row.update({"address": "0x" + "1" * 40, "chain": "eth", "name": "fixture",
                "category": "cex", "tier": tier, "source": "manual",
                "added_date": "2026-08-06", "evidence": "fixture",
                "risk_flags": risk_flags})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerow(row)


def test_original_counterexample(root):
    path = root / "labels-eth.csv"
    write_row(path, " tornado-user")
    errors, _, _ = validate_file(path)
    parsed = parse_risk_flags(" tornado-user")
    partition = LabelResolver.risk_partition({"risk_flags": " tornado-user"})
    assert parsed == ("tornado-user",), parsed
    assert partition["privacy"] == list(parsed), partition
    assert any("exclude" in error and "行为旗标" in error for error in errors), errors


def test_variants():
    variants = {
        "b|a|a": ("a", "b"),
        "a|| b |": ("a", "b"),
        " |  |": (),
        "": (),
        None: (),
    }
    for raw, expected in variants.items():
        assert parse_risk_flags(raw) == expected, raw
        assert canonical_risk_flags(raw) == "|".join(expected), raw
    assert merge_risk_flags(" b|a", "a||c ") == "a|b|c"


def test_legacy_and_live_tables(root):
    # Legacy non-canonical storage is read-compatible and reported as a warning,
    # while every consumer interprets the same canonical set.
    legacy = root / "labels-eth.csv"
    write_row(legacy, "tornado-user|exploit|tornado-user", tier="risk")
    errors, warnings, _ = validate_file(legacy, strict_canonical=False)
    assert not errors, errors
    assert any("risk_flags 非 canonical" in item for item in warnings), warnings
    strict_errors, _, _ = validate_file(legacy, strict_canonical=True)
    assert any("risk_flags 非 canonical" in item for item in strict_errors), strict_errors
    resolver = LabelResolver("eth", labels_dir=str(root), evm_fallback=False)
    row = resolver.get("0x" + "1" * 40)
    flattened = sorted(flag for values in resolver.risk_partition(row).values()
                       for flag in values)
    assert flattened == ["exploit", "tornado-user"], flattened

    # Full current tables: validation stays green and resolver parsing equals the
    # canonical parser even for the 59 historical non-canonical rows.
    live_dir = ROOT / "references/labels"
    checked = 0
    for path in sorted(live_dir.glob("labels-*.csv")):
        errors, _, count = validate_file(path)
        assert not errors, (path, errors[:5])
        with path.open(newline="", encoding="utf-8") as handle:
            for raw in csv.DictReader(handle):
                parsed = parse_risk_flags(raw.get("risk_flags"))
                partition = LabelResolver.risk_partition(raw)
                flattened = tuple(sorted(flag for values in partition.values()
                                         for flag in values))
                assert flattened == parsed, (path, raw.get("address"), parsed, flattened)
        checked += count
    assert checked > 300_000, checked


def main():
    with tempfile.TemporaryDirectory(prefix="batch1-risk-flags-") as td:
        root = Path(td).resolve()
        test_original_counterexample(root)
        test_variants()
        test_legacy_and_live_tables(root)
    print("PASS B1-C risk_flags: canonical parser + four-consumer/live-table agreement")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
