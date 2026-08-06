#!/usr/bin/env python3
"""退役 EVM Par 路线的 M-01 durable progress 历史回归。"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from fetch_hypersync_par import (_progress_identity, atomic_json, load_progress,
                                 require_next_block)


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


def main():
    with tempfile.TemporaryDirectory() as tmp:
        test_m01(tmp)
    print("PASS: archived M-01 durable bound progress")
    return 0


if __name__ == "__main__":
    sys.exit(main())
