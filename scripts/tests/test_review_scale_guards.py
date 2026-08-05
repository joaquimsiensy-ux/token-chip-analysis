#!/usr/bin/env python3
"""M-04: legacy helpers are bounded and every result binds its inputs."""
import csv
import inspect
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "evm"))

import transfers_lib

ZERO = "0x" + "0" * 40
A = "0x" + "a" * 40


def write_csv(path, rows=2):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(transfers_lib.STD_COLS)
        for i in range(rows):
            w.writerow([i + 1, "", f"0xtx{i}", 0, ZERO, A, i + 1, f"0xhash{i}"])


def run(script, cwd, *args):
    return subprocess.run([sys.executable, str(script), *map(str, args)], cwd=cwd,
                          capture_output=True, text=True)


def test_transfers(tmp):
    src = Path(tmp) / "src.csv"
    out = Path(tmp) / "out.csv"
    write_csv(src, 2)
    try:
        transfers_lib.merge_sources([str(src)], str(out), max_rows=1)
    except SystemExit as e:
        assert e.code == 4
    else:
        raise AssertionError("small-sample merge accepted oversized input")
    assert not out.exists()
    transfers_lib.merge_sources([str(src)], str(out), max_rows=2)
    manifest = json.loads(Path(str(out) + ".input_manifest.json").read_text())
    assert manifest["small_sample_only"] is True
    assert manifest["inputs"][0]["rows"] == 2 and len(manifest["inputs"][0]["sha256"]) == 64
    parquet_reader = inspect.getsource(transfers_lib._iter_parquet_dir)
    assert "iter_batches" in parquet_reader and "read_table" not in parquet_reader


def test_build_evolution(tmp):
    tmp = Path(tmp)
    script = ROOT / "scripts/solana/build_evolution.py"
    p = run(script, tmp)
    assert p.returncode != 0 and "缺 config.json" in (p.stdout + p.stderr)
    (tmp / "config.json").write_text(json.dumps({"total_supply": 0, "decimals": 0,
                                                  "launch_ts": 1, "data_cutoff_ts": 10}))
    p = run(script, tmp)
    assert p.returncode != 0
    (tmp / "config.json").write_text(json.dumps({"total_supply": 100, "decimals": 0,
                                                  "launch_ts": 1, "data_cutoff_ts": 10,
                                                  "max_entities": 2, "max_anchor_rows": 2}))
    data = tmp / "data"
    data.mkdir()
    (data / "whale_deep.json").write_text(json.dumps({"A": {"rows": [
        {"blockTime": 2, "delta_raw": 10}]}}))
    (data / "entity_camps.json").write_text(json.dumps({"A": "camp"}))
    (data / "decoded_anchors.jsonl").write_text(json.dumps(
        {"ts": 2, "pool_balance_raw": "5", "pool_balance": 5}) + "\n")
    p = run(script, tmp)
    assert p.returncode == 0, p.stdout + p.stderr
    manifest = json.loads((data / "camp_series.input_manifest.json").read_text())
    assert manifest["small_sample_only"] is True
    assert manifest["counts"] == {"anchor_rows": 1, "camps": 1, "deep_rows": 1,
                                   "entities": 1, "usable_pool_anchors": 1}
    assert len(manifest["inputs"]) == 3 and manifest["output"]["rows"] == 400


def main():
    with tempfile.TemporaryDirectory() as tmp:
        test_transfers(tmp)
    with tempfile.TemporaryDirectory() as tmp:
        test_build_evolution(tmp)
    print("PASS: M-04 bounded helpers, streaming parquet batches, and bound input manifests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
