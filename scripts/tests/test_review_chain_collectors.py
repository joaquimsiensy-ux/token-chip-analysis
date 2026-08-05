#!/usr/bin/env python3
"""2026-08-02 review regression: H-10 overlap resume integrity."""
import gzip
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RH = ROOT / "robinhood"
sys.path.insert(0, str(RH))
from resume_guard import bind_output, overlap_state, require_fetch_success, require_progress


def test_h10(tmp):
    out = str(Path(tmp) / "events.jsonl.gz")
    identity = {"collector": "fixture", "token": "0x1", "query_schema": "q"}
    bind_output(out, identity)
    with gzip.open(out, "wt") as f:
        f.write(json.dumps({"block": 7, "tx": "a", "logi": 0}) + "\n")
        f.write(json.dumps({"block": 7, "tx": "b", "logi": 1}) + "\n")
    start, keys, count = overlap_state(out, ("block", "tx", "logi"))
    assert start == 7 and count == 2 and keys == {(7, "a", 0), (7, "b", 1)}
    try:
        require_progress(7, 7, 10)
    except RuntimeError:
        pass
    else:
        raise AssertionError("stalled next_block must reject")
    try:
        require_fetch_success(False, None)
    except RuntimeError:
        pass
    else:
        raise AssertionError("network failure must not become EMPTY/done")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        test_h10(tmp)
    print("PASS: H-10 overlap resume integrity")
    return 0


if __name__ == "__main__":
    sys.exit(main())
