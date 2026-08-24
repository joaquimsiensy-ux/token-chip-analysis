#!/usr/bin/env python3
"""additions 重放的 source_snapshot_at 新行、优先覆盖、低优先补空三路回归。"""
from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "scripts" / "labels" / "build_labels.py"
FIELDS = ["address", "chain", "name", "category", "tier", "source", "added_date",
          "evidence", "risk_flags", "merge_policy", "balance_policy", "source_snapshot_at",
          "verified_at", "status", "raw_labels"]


def write_csv(path: Path, fields, rows=()):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def main():
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        write_csv(work / "accounts.csv", ["chainId", "label", "nameTag", "address"])
        write_csv(work / "tokens.csv", ["chainId", "label", "name", "symbol", "address"])
        rows = [
            {"address": "0x" + "a" * 40, "chain": "arbitrum", "name": "Fixture CEX",
             "category": "cex", "tier": "exclude", "source": "dune-cex-addresses",
             "source_snapshot_at": "2026-08-12"},
            {"address": "0x" + "b" * 40, "chain": "arbitrum", "name": "Default snapshot",
             "category": "cex", "tier": "exclude", "source": "dune-cex-addresses",
             "source_snapshot_at": ""},
            # 同键：先到低优先级旧值，后到 curation 高优先级行值必须覆盖。
            {"address": "0x" + "c" * 40, "chain": "arbitrum", "name": "Old snapshot",
             "category": "cex", "tier": "exclude", "source": "gmgn",
             "source_snapshot_at": "2026-01-01"},
            {"address": "0x" + "c" * 40, "chain": "arbitrum", "name": "Curated snapshot",
             "category": "cex", "tier": "exclude", "source": "curation",
             "source_snapshot_at": "2026-08-12"},
            # 同键：先到高优先级旧行 snapshot 为空，后到较低优先级行值只补空。
            {"address": "0x" + "d" * 40, "chain": "arbitrum", "name": "Empty snapshot",
             "category": "cex", "tier": "exclude", "source": "manual",
             "source_snapshot_at": ""},
            {"address": "0x" + "d" * 40, "chain": "arbitrum", "name": "Fill snapshot",
             "category": "cex", "tier": "exclude", "source": "gmgn",
             "source_snapshot_at": "2026-08-13"},
        ]
        write_csv(work / "additions" / "snapshot.csv", FIELDS, rows)
        proc = subprocess.run([sys.executable, str(BUILD)], cwd=work,
                              capture_output=True, text=True)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        with (work / "out" / "labels-arbitrum.csv").open(newline="", encoding="utf-8") as fh:
            by_addr = {row["address"]: row for row in csv.DictReader(fh)}
        assert by_addr[rows[0]["address"]]["source_snapshot_at"] == "2026-08-12", by_addr
        assert by_addr[rows[1]["address"]]["source_snapshot_at"] == "2026-07-16", by_addr
        assert by_addr[rows[2]["address"]]["source_snapshot_at"] == "2026-08-12", by_addr
        assert by_addr[rows[4]["address"]]["source_snapshot_at"] == "2026-08-13", by_addr
    print("PASS: source_snapshot_at 新行透传、默认回落、高优先覆盖、低优先补空")


if __name__ == "__main__":
    main()
