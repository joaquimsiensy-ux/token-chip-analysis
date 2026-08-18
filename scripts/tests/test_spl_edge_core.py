#!/usr/bin/env python3
"""Solana transaction-net shared edge core regressions."""
import hashlib
import os
import random
import sys
from pathlib import Path


ROOT = Path(os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
sys.path.insert(0, str(ROOT / "scripts" / "solana"))

from spl_edge_core import (EDGE_SCHEMA_FIELDS, EDGE_SEMANTICS,
                           INSTR_INDEX_TX_NET, ORDER_GRANULARITY_TX,
                           ZERO_OWNER, pair_tx, parse_owner_delta,
                           soltx_cache_paths)


def test_equal_amount_input_order_is_irrelevant():
    """原反例：等额多方换序后必须仍产出逐字节相同的边集合。"""
    first = {"A": -10, "B": -10, "C": 10, "D": 10}
    second = {"A": -10, "B": -10, "D": 10, "C": 10}
    left = pair_tx(first)
    right = pair_tx(second)
    assert left == right, f"同一 delta 集合因输入顺序漂移: {left!r} != {right!r}"
    assert left == [("A", "C", 10), ("B", "D", 10)], left


def _legacy_pair_tx(delta):
    pos = sorted(([owner, amount] for owner, amount in delta.items() if amount > 0),
                 key=lambda item: -item[1])
    neg = sorted(([owner, -amount] for owner, amount in delta.items() if amount < 0),
                 key=lambda item: -item[1])
    edges, i, j = [], 0, 0
    while i < len(pos) and j < len(neg):
        matched = min(pos[i][1], neg[j][1])
        edges.append((neg[j][0], pos[i][0], matched))
        pos[i][1] -= matched
        neg[j][1] -= matched
        if pos[i][1] == 0:
            i += 1
        if neg[j][1] == 0:
            j += 1
    edges.extend((ZERO_OWNER, owner, remaining) for owner, remaining in pos[i:] if remaining)
    edges.extend((owner, ZERO_OWNER, remaining) for owner, remaining in neg[j:] if remaining)
    return edges


def test_random_shuffle_is_byte_deterministic():
    rng = random.Random(20260817)
    values = (-10**30, -10, -1, 0, 1, 10, 10**30)
    for case in range(80):
        items = [(f"owner-{idx:02d}", rng.choice(values))
                 for idx in range(rng.randint(2, 12))]
        if not any(amount for _, amount in items):
            items[0] = (items[0][0], 1)
        expected = pair_tx(dict(items))
        for _ in range(20):
            shuffled = list(items)
            rng.shuffle(shuffled)
            assert pair_tx(dict(shuffled)) == expected, (case, items, shuffled)
    assert any(ZERO_OWNER in edge[:2] for edge in pair_tx({"minted": 10**30}))
    assert any(ZERO_OWNER in edge[:2] for edge in pair_tx({"burned": -(10**30)}))


def test_invalid_pair_input_fails_closed():
    bad = (
        {"A": "10"},
        {"A": True},
        {None: -1, "B": 1},
        [("A", 1)],
    )
    for value in bad:
        try:
            pair_tx(value)
        except TypeError:
            pass
        else:
            raise AssertionError(f"非法 pair_tx 输入未拒绝: {value!r}")


def test_migration_equivalence_and_legacy_owner_rule():
    fixture = {"A": -17, "B": -5, "C": 13, "D": 7, "E": 2}
    assert pair_tx(fixture) == _legacy_pair_tx(fixture)
    assert parse_owner_delta({
        "transactionIndex": 4,
        "preOwner": "PRE",
        "postOwner": "POST",
        "preAmount": "8",
        "postAmount": "11",
    }) == (4, "POST", 3)
    assert parse_owner_delta({
        "transactionIndex": 5,
        "preOwner": "PRE",
        "postOwner": None,
        "preAmount": "8",
        "postAmount": "3",
    }) == (5, "PRE", -5)
    assert parse_owner_delta({"transactionIndex": 6, "postAmount": "bad"}) is None


def test_cache_paths_and_semantic_constants():
    mint = "AbC"
    data_dir = Path("some-data")
    key = hashlib.sha256(mint.encode("utf-8")).hexdigest()
    assert soltx_cache_paths(mint, data_dir) == (
        data_dir / f"soltx-{key}.jsonl.gz",
        data_dir / f"soltx-{key}.meta.json",
        data_dir / f"soltx-{key}.parts",
    )
    assert soltx_cache_paths("AbC", data_dir) != soltx_cache_paths("aBc", data_dir)
    assert EDGE_SCHEMA_FIELDS == (
        "ts", "slot", "tx_index", "instr_index", "from", "to", "amt")
    assert EDGE_SEMANTICS == "owner-net-greedy"
    assert ORDER_GRANULARITY_TX == "transaction"
    assert INSTR_INDEX_TX_NET == -1


if __name__ == "__main__":
    test_equal_amount_input_order_is_irrelevant()
    test_random_shuffle_is_byte_deterministic()
    test_invalid_pair_input_fails_closed()
    test_migration_equivalence_and_legacy_owner_rule()
    test_cache_paths_and_semantic_constants()
    print("PASS: spl_edge_core T1 三件套 + T2 迁移等价 + T3 语义常量")
