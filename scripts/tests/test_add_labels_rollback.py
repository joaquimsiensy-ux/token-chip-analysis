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
            rc = mod.main()
        except SystemExit as exc:
            rc = exc.code
        assert rc == (1 if any(returncodes) else 0), (rc, returncodes)
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

        # additions staging 复制失败：三闸前失败，发布表/manifest 均不动且无临时残留。
        mod = load_module(); mod.DEFAULT_LABELS_DIR = str(labels); mod.ADDITIONS_DIR = str(additions_dir)
        real_copy = mod.shutil.copy
        def fail_stage(src_path, dst_path, *args, **kwargs):
            if Path(dst_path).parent == additions_dir:
                raise OSError("archive staging injected")
            return real_copy(src_path, dst_path, *args, **kwargs)
        with mock.patch.object(sys, "argv", [str(SCRIPT), str(adds)]), \
                mock.patch.object(mod.shutil, "copy", side_effect=fail_stage):
            assert mod.main() == 1
        assert old.read_bytes() == before and manifest.read_bytes() == manifest_before
        assert not list(additions_dir.glob(".*.staging-*.tmp"))

        # 原名冲突后采用时分秒后缀；后缀仍冲突则拒绝，绝不覆盖两份既有归档。
        additions_dir.mkdir(exist_ok=True)
        archived = additions_dir / adds.name; archived.write_text("first\n", encoding="utf-8")
        second = additions_dir / "existing_20260806_120000.csv"
        second.write_text("second\n", encoding="utf-8")
        mod = load_module(); mod.DEFAULT_LABELS_DIR = str(labels); mod.ADDITIONS_DIR = str(additions_dir)
        with mock.patch.object(sys, "argv", [str(SCRIPT), str(adds)]), \
                mock.patch.object(mod, "archive_stamp", return_value="20260806_120000"):
            assert mod.main() == 1
        assert archived.read_text() == "first\n" and second.read_text() == "second\n"
        archived.unlink(); second.unlink()

        # 三闸全绿但 staging 独占发布失败：主表/manifest 回滚，临时 staging 清理。
        mod = load_module(); mod.DEFAULT_LABELS_DIR = str(labels); mod.ADDITIONS_DIR = str(additions_dir)
        with mock.patch.object(sys, "argv", [str(SCRIPT), str(adds)]), \
                mock.patch.object(mod.subprocess, "run",
                                  return_value=subprocess.CompletedProcess([], 0)), \
                mock.patch.object(mod.os, "link", side_effect=FileExistsError("race")):
            assert mod.main() == 1
        assert old.read_bytes() == before and manifest.read_bytes() == manifest_before
        assert not list(additions_dir.glob(".*.staging-*.tmp"))

        # 三闸全 PASS 才保留新表并清理备份。
        mod = load_module(); mod.DEFAULT_LABELS_DIR = str(labels); mod.ADDITIONS_DIR = str(additions_dir)
        calls = invoke(mod, adds, (0, 0, 0))
        assert old.read_bytes() != before and not Path(str(old) + ".bak").exists()
        assert [Path(c[1]).name for c in calls] == [
            "validate_labels.py", "benchmark_labels.py", "labels_manifest.py"]
    print("PASS: add_labels validate/benchmark/manifest 三闸与失败回滚")


if __name__ == "__main__":
    main()
