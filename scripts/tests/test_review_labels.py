#!/usr/bin/env python3
"""2026-08-02 review regression: B-09 chain-scoped address book."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "labels"))
from labels_resolver import LabelResolver, norm_addr
from check_manual_sync import runtime_keys, source_keys


def main():
    bsc_only = "0x73d8bd54f7cf5fab43fe4ef40a62d390644946db"
    bsc = LabelResolver("bsc").get(bsc_only)
    eth = LabelResolver("eth").get(bsc_only)
    base = LabelResolver("base").get(bsc_only)
    assert bsc and not bsc["cross_chain"] and bsc["balance_policy"] == "exclude"
    assert eth is None, f"BSC-only address must not direct-hit ETH: {eth}"
    assert base is None or base["cross_chain"], f"BSC-only address must not direct-hit Base: {base}"
    if base:
        assert LabelResolver("base").balance_policy(bsc_only) == "count"

    invalid = "0x" + "g" * 40
    assert norm_addr(invalid, "eth") is None

    # 同址跨链必须作为不同键闭合；旧 address-only 集合会漏掉其中任一链行。
    zero = "0x0000000000000000000000000000000000000000"
    expected_zero_keys = {(chain, zero) for chain in ("eth", "bsc", "base", "robinhood")}
    assert expected_zero_keys <= source_keys()
    assert source_keys() == runtime_keys()
    print("PASS: B-09 manual address-book rows are chain-scoped; composite sync keys and invalid EVM hex verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
