#!/usr/bin/env python3
"""F-02 回归：五张主表必须齐全非空，manual 设施必须 100% 命中。"""
import csv
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "labels" / "benchmark_labels.py"
REAL_LABELS = ROOT / "references" / "labels"
CHAINS = ("eth", "bsc", "base", "sol", "robinhood")
FIELDS = ["address", "chain", "name", "category", "tier", "source", "added_date",
          "evidence", "risk_flags", "merge_policy", "balance_policy", "source_snapshot_at",
          "verified_at", "status", "raw_labels"]


def address(chain, digit="1"):
    return digit * 32 if chain == "sol" else "0x" + digit * 40


def write_labels(root, chain, rows):
    with (root / f"labels-{chain}.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for row in rows:
            base = dict.fromkeys(FIELDS, "")
            base.update({"address": row["address"], "chain": chain, "name": "fixture",
                         "category": "cex", "tier": "exclude", "source": "manual",
                         "merge_policy": "no_merge", "balance_policy": "exclude"})
            w.writerow(base)


def write_goldset(path, manual=False):
    with path.open("w", newline="", encoding="utf-8") as f:
        fields = ["chain", "address", "expected", "note", "source_analysis"]
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for chain in CHAINS:
            w.writerow({"chain": chain, "address": address(chain),
                        "expected": "infrastructure" if manual else "random-eoa",
                        "note": "fixture", "source_analysis": "manual-layer" if manual else "fixture"})


def run(labels, goldset):
    return subprocess.run([sys.executable, str(SCRIPT), str(goldset),
                           f"--labels-dir={labels}"], capture_output=True, text=True)


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td); labels = root / "labels"; labels.mkdir()
        gold = root / "goldset.csv"; write_goldset(gold)

        write_labels(labels, "eth", [{"address": address("eth")}])
        p = run(labels, gold)
        assert p.returncode != 0, p.stdout + p.stderr

        for chain in CHAINS:
            write_labels(labels, chain, [{"address": address(chain)}])
        write_labels(labels, "base", [])
        p = run(labels, gold)
        assert p.returncode != 0, p.stdout + p.stderr

        write_labels(labels, "base", [{"address": address("base")}])
        write_goldset(gold, manual=True)
        write_labels(labels, "eth", [{"address": address("eth", "2")}])
        p = run(labels, gold)
        assert p.returncode != 0 and "manual" in (p.stdout + p.stderr), p.stdout + p.stderr

    p = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    print("PASS: benchmark 五表完整性与 manual 召回硬闸生效")


if __name__ == "__main__":
    main()
