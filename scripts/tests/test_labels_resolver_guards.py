#!/usr/bin/env python3
"""2026-08-02 review regression M-02: strict labels and empty-file schema."""
import csv
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "labels"))

from labels_resolver import BASE_FIELDS, norm_addr
from validate_labels import validate_file


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
        test_m02(tmp)
    print("PASS: M-02 strict addresses and empty-file schema")
    return 0


if __name__ == "__main__":
    sys.exit(main())
