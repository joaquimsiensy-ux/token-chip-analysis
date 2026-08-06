#!/usr/bin/env python3
"""F-05 回归：校验失败时原表字节恢复，新建表不残留。"""
import csv
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "labels" / "add_labels.py"
FIELDS = ["address", "chain", "name", "category", "tier", "source", "added_date",
          "evidence", "risk_flags", "merge_policy", "balance_policy", "source_snapshot_at",
          "verified_at", "status", "raw_labels"]


def load_module():
    spec = importlib.util.spec_from_file_location("add_labels_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)


def invoke(mod, src):
    with mock.patch.object(sys, "argv", [str(SCRIPT), str(src)]), \
            mock.patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 1)):
        try:
            mod.main()
        except SystemExit as exc:
            assert exc.code == 1
        else:
            raise AssertionError("校验失败应退出 1")


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td); labels = root / "labels"; labels.mkdir()
        old = labels / "labels-eth.csv"
        base = dict.fromkeys(FIELDS, "")
        base.update({"address": "0x" + "1" * 40, "chain": "eth", "name": "old",
                     "category": "kol", "tier": "identity", "source": "manual"})
        write_csv(old, [base]); before = old.read_bytes()
        adds = root / "existing.csv"
        changed = dict(base, name="new", source="curation")
        write_csv(adds, [changed])
        mod = load_module(); mod.DEFAULT_LABELS_DIR = str(labels)
        invoke(mod, adds)
        assert old.read_bytes() == before, "原表未字节级恢复"

        fresh = root / "fresh.csv"
        new_row = dict(base, address="0x" + "2" * 40, chain="arbitrum", name="bad")
        write_csv(fresh, [new_row])
        mod = load_module(); mod.DEFAULT_LABELS_DIR = str(labels)
        invoke(mod, fresh)
        assert not (labels / "labels-arbitrum.csv").exists(), "新建坏表校验失败后仍残留"
    print("PASS: add_labels 校验失败完整回滚")


if __name__ == "__main__":
    main()
