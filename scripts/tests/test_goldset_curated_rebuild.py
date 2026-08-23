#!/usr/bin/env python3
"""裁决金标必须由构建器真实消费，重建后逐语义保留且 Arbitrum 非弱门禁。"""
from __future__ import annotations

import csv
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "scripts" / "labels" / "build_goldset.py"
BENCHMARK = ROOT / "scripts" / "labels" / "benchmark_labels.py"
CURATED = ROOT / "references" / "labels" / "benchmark" / "goldset_curated.csv"
LABELS = ROOT / "references" / "labels"
GOLD_FIELDS = ("chain", "address", "expected", "note", "source_analysis")


def load_builder():
    spec = importlib.util.spec_from_file_location("curated_goldset_builder", BUILD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    curated_rows = list(csv.DictReader(CURATED.open(newline="", encoding="utf-8")))
    curated = {(row["chain"], row["address"]): row for row in curated_rows}
    assert len(curated_rows) == len(curated) == 18, "裁决真源必须恰为 18 个唯一键"
    assert all(row["decision_ref"] == "T3-F-01" for row in curated_rows), curated_rows

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        analysis_root = root / "empty-analysis-root"
        analysis_root.mkdir()
        out_dir = root / "benchmark"
        builder = load_builder()
        builder.OUT_DIR = str(out_dir)
        old_argv = sys.argv
        try:
            sys.argv = [str(BUILD), str(analysis_root)]
            builder.main()
        finally:
            sys.argv = old_argv

        rebuilt_path = out_dir / "goldset.csv"
        rebuilt_rows = list(csv.DictReader(rebuilt_path.open(newline="", encoding="utf-8")))
        rebuilt = {(row["chain"], row["address"]): row for row in rebuilt_rows}
        for key, expected in curated.items():
            assert key in rebuilt, f"重建丢失裁决键: {key}"
            assert {field: rebuilt[key][field] for field in GOLD_FIELDS} == \
                   {field: expected[field] for field in GOLD_FIELDS}, \
                   f"重建改变裁决语义: {key}: {rebuilt[key]} != {expected}"

        proc = subprocess.run(
            [sys.executable, str(BENCHMARK), str(rebuilt_path), f"--labels-dir={LABELS}"],
            capture_output=True, text=True)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        arb_line = next(line for line in proc.stdout.splitlines() if line.startswith("[arbitrum]"))
        assert "random-eoa 10" in arb_line and "弱门禁" not in arb_line, arb_line

    print("PASS: curated 金标真实重建 18/18 逐语义保留，Arbitrum weak_gate=false")


if __name__ == "__main__":
    main()
