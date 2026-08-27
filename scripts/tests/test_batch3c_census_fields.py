#!/usr/bin/env python3
"""Batch 3c guard for the SQD census request field contract."""
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.solana import sqd_gap_repair as repair  # noqa: E402


# SQD's HTTP 400 response enumerated these block fields; the repaired request
# was also verified live by the workorder author.
SQD_BLOCK_FIELDS = {
    "number", "hash", "parentNumber", "parentHash", "height", "timestamp",
}

# Keep this conservative: these are the three transaction fields consumed by
# census and confirmed by the workorder's live response.
REQUIRED_TRANSACTION_FIELDS = {"transactionIndex", "signatures", "err"}


def test_census_fields_match_sqd_contract():
    fields = repair._census_body(326_000_396)["fields"]
    block_fields = set(fields["block"])
    transaction_fields = set(fields["transaction"])

    assert block_fields <= SQD_BLOCK_FIELDS, (
        f"unsupported SQD block fields: {sorted(block_fields - SQD_BLOCK_FIELDS)}"
    )
    assert block_fields == {"number", "hash"}, block_fields
    assert transaction_fields == REQUIRED_TRANSACTION_FIELDS, transaction_fields


def main():
    test_census_fields_match_sqd_contract()
    print("PASS batch3c census fields match the SQD contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
