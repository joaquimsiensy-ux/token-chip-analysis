#!/usr/bin/env python3
"""2026-08-02 review regressions: B-10/H-01."""
import gzip
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
RH = os.path.join(HERE, "..", "robinhood")
sys.path.insert(0, RH)
from amounts import raw_to_units, v3_quote_per_token


def digest(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main():
    for dec in (6, 8, 9, 18):
        assert raw_to_units(10**dec, dec) == Decimal(1)
    q96 = 2**96
    assert v3_quote_per_token(q96, False, 6, 18) == Decimal("0.000000000001")
    assert v3_quote_per_token(q96, True, 18, 6) == Decimal("1000000000000")

    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "transfers.jsonl.gz")
        with gzip.open(src, "wt") as f:
            f.write(json.dumps({"block": 1, "logi": 0, "ts": 1}) + "\n")
        raw = open(src, "rb").read()
        with open(src, "wb") as f:
            f.write(raw[:-4])
        before = digest(src)
        rpc = os.path.join(tmp, "rpc.jsonl")
        open(rpc, "w").write("")
        anchors = os.path.join(tmp, "anchors.json")
        json.dump({"1": 1}, open(anchors, "w"))
        out = os.path.join(tmp, "merged.jsonl.gz")
        p = subprocess.run([sys.executable, os.path.join(RH, "merge_hs_rpc.py"),
                            "--input", src, "--rpc", rpc, "--anchors", anchors,
                            "--output", out], capture_output=True, text=True)
        assert p.returncode != 0 and digest(src) == before and not os.path.exists(out), p.stdout + p.stderr

    print("PASS: B-10 decimal conversions/V3 scaling and H-01 truncated gzip preservation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
