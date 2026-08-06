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


def invoke(mod, src, returncodes=(1,)):
    calls = []
    def fake_run(args, **kwargs):
        calls.append(args)
        idx = min(len(calls) - 1, len(returncodes) - 1)
        return subprocess.CompletedProcess(args, returncodes[idx])
    with mock.patch.object(sys, "argv", [str(SCRIPT), str(src)]), \
            mock.patch.object(subprocess, "run", side_effect=fake_run):
        try:
            mod.main()
        except SystemExit as exc:
            assert exc.code == 1
        else:
            if any(returncodes):
                raise AssertionError("门禁失败应退出 1")
    return calls


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
        additions_dir = root / "archived-additions"
        mod = load_module(); mod.DEFAULT_LABELS_DIR = str(labels); mod.ADDITIONS_DIR = str(additions_dir)
        invoke(mod, adds)
        assert old.read_bytes() == before, "原表未字节级恢复"

        fresh = root / "fresh.csv"
        new_row = dict(base, address="0x" + "2" * 40, chain="arbitrum", name="bad")
        write_csv(fresh, [new_row])
        mod = load_module(); mod.DEFAULT_LABELS_DIR = str(labels); mod.ADDITIONS_DIR = str(additions_dir)
        invoke(mod, fresh)
        assert not (labels / "labels-arbitrum.csv").exists(), "新建坏表校验失败后仍残留"

        # validate PASS、benchmark FAIL：必须恢复原表，且不能写 manifest。
        mod = load_module(); mod.DEFAULT_LABELS_DIR = str(labels); mod.ADDITIONS_DIR = str(additions_dir)
        calls = invoke(mod, adds, (0, 1))
        assert old.read_bytes() == before, "benchmark FAIL 未恢复原表"
        assert any("benchmark_labels.py" in " ".join(c) for c in calls), calls
        assert not any("labels_manifest.py" in " ".join(c) for c in calls), calls

        # manifest 写入失败：表和旧 manifest 都恢复。
        manifest = labels / "manifest.json"; manifest.write_text('{"old":true}\n')
        manifest_before = manifest.read_bytes()
        mod = load_module(); mod.DEFAULT_LABELS_DIR = str(labels); mod.ADDITIONS_DIR = str(additions_dir)
        calls = invoke(mod, adds, (0, 0, 1))
        assert old.read_bytes() == before and manifest.read_bytes() == manifest_before
        assert any("labels_manifest.py" in " ".join(c) and "--write" in c for c in calls)

        # 三闸全 PASS 才保留新表并清理备份。
        mod = load_module(); mod.DEFAULT_LABELS_DIR = str(labels); mod.ADDITIONS_DIR = str(additions_dir)
        calls = invoke(mod, adds, (0, 0, 0))
        assert old.read_bytes() != before and not Path(str(old) + ".bak").exists()
        assert [Path(c[1]).name for c in calls] == [
            "validate_labels.py", "benchmark_labels.py", "labels_manifest.py"]
    print("PASS: add_labels validate/benchmark/manifest 三闸与失败回滚")


if __name__ == "__main__":
    main()
