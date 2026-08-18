#!/usr/bin/env python3
"""Solana transaction-net shared edge core regressions."""
import importlib.util
import os


ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
FETCH = os.path.join(ROOT, "scripts", "solana", "fetch_sqd_transfers_v2.py")

_spec = importlib.util.spec_from_file_location("sqd_v2_pair_red", FETCH)
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)


def test_equal_amount_input_order_is_irrelevant():
    """原反例：等额多方换序后必须仍产出逐字节相同的边集合。"""
    first = {"A": -10, "B": -10, "C": 10, "D": 10}
    second = {"A": -10, "B": -10, "D": 10, "C": 10}
    left = M.pair_tx(first)
    right = M.pair_tx(second)
    assert left == right, f"同一 delta 集合因输入顺序漂移: {left!r} != {right!r}"


if __name__ == "__main__":
    test_equal_amount_input_order_is_irrelevant()
    print("PASS: pair_tx 等额多方输入顺序不影响输出")
