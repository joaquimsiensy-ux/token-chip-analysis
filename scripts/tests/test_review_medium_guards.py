#!/usr/bin/env python3
"""2026-08-02 review regressions: M-01 and M-02."""
import csv
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "evm"))
sys.path.insert(0, str(HERE.parent / "labels"))

from fetch_hypersync_par import (_progress_identity, atomic_json, load_progress,
                                 require_next_block)
from labels_resolver import BASE_FIELDS, norm_addr
from validate_labels import validate_file


def test_m01(tmp):
    csv_path = Path(tmp) / "part_00.csv"
    csv_path.write_text("block,ts,tx,log_index,from,to,value_raw,block_hash\n", encoding="utf-8")
    prog = Path(tmp) / "part_00.prog"
    ident = _progress_identity("0x" + "a" * 40, "https://example/query", (0, 10, 20))
    atomic_json(str(prog), {**ident, "next_block": 15, "csv_size": csv_path.stat().st_size})
    assert load_progress(str(prog), str(csv_path), ident) == 15
    csv_path.write_text(csv_path.read_text() + "16,x,x,0,x,x,1,x\n")
    try:
        load_progress(str(prog), str(csv_path), ident)
    except RuntimeError as e:
        assert "extent mismatch" in str(e)
    else:
        raise AssertionError("checkpoint ahead/behind durable CSV must reject")
    for payload in ({}, {"next_block": 10}, {"next_block": 21}, {"next_block": "11"}):
        try:
            require_next_block(payload, 10, 20)
        except RuntimeError:
            pass
        else:
            raise AssertionError(f"unsafe next_block accepted: {payload}")


def test_m02(tmp):
    assert norm_addr("0x" + "g" * 40, "eth") is None
    bad = Path(tmp) / "labels-eth.csv"
    bad.write_text("address,chain\n", encoding="utf-8")
    errs, _, n = validate_file(str(bad))
    assert n == 0 and any("表头异常" in e for e in errs), errs
    good = Path(tmp) / "labels-eth.csv"
    with good.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=BASE_FIELDS)
        writer.writeheader()
    errs, _, n = validate_file(str(good))
    assert n == 0 and not errs, errs


def main():
    with tempfile.TemporaryDirectory() as tmp:
        test_m01(tmp)
    with tempfile.TemporaryDirectory() as tmp:
        test_m02(tmp)
    print("PASS: M-01 durable bound progress; M-02 strict addresses and empty-file schema")
    return 0


if __name__ == "__main__":
    sys.exit(main())
