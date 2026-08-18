#!/usr/bin/env python3
"""Solana transaction-net shared edge core regressions."""
import hashlib
import os
import random
import sys
from pathlib import Path


ROOT = Path(os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
sys.path.insert(0, str(ROOT / "scripts" / "solana"))

import spl_edge_core as _core
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


def _balance(ti, account, pre_owner, post_owner, pre_amount, post_amount,
             pre_mint="MINT", post_mint="MINT"):
    return {"transactionIndex": ti, "account": account,
            "preOwner": pre_owner, "postOwner": post_owner,
            "preAmount": pre_amount, "postAmount": post_amount,
            "preMint": pre_mint, "postMint": post_mint}


def test_migration_equivalence_and_owner_authority():
    fixture = {"A": -17, "B": -5, "C": 13, "D": 7, "E": 2}
    assert pair_tx(fixture) == _legacy_pair_tx(fixture)
    # T2a 原反例：换 owner 时两侧必须分别记账，不能只把差额记到 postOwner。
    assert parse_owner_delta(
        _balance(4, "acct-4", "A", "B", "10", "12"), "MINT") == (
            4, "acct-4", (("A", -10), ("B", 12)))
    # 同额换 owner仍是 A 全额退出、B 全额进入。
    assert parse_owner_delta(
        _balance(5, "acct-5", "A", "B", "10", "10"), "MINT") == (
            5, "acct-5", (("A", -10), ("B", 10)))
    # close + reinit 到另一 mint：只计目标 mint 的 pre 侧。
    assert parse_owner_delta(
        _balance(6, "acct-6", "A", "B", "10", "99",
                 pre_mint="MINT", post_mint="OTHER"), "MINT") == (
            6, "acct-6", (("A", -10),))


def test_owner_aggregation_and_token2022_fee_fixture():
    rows = [
        _balance(8, "sender", "S", "S", "100", "88"),
        _balance(8, "receiver", "R", "R", "0", "10"),
        _balance(8, "withheld", "FEE", "FEE", "0", "2"),
    ]
    ledger = _core.owner_deltas_by_tx(rows, "MINT")
    assert ledger == {8: {"S": -12, "R": 10, "FEE": 2}}, ledger
    assert pair_tx(ledger[8]) == [("S", "R", 10), ("S", "FEE", 2)]
    # owner 变更叠加同交易另一 token account。
    mixed = _core.owner_deltas_by_tx([
        _balance(9, "authority-change", "A", "B", "10", "12"),
        _balance(9, "other", "C", "C", "7", "5"),
    ], "MINT")
    assert mixed == {9: {"A": -10, "B": 12, "C": -2}}, mixed


def test_owner_input_failures_are_controlled():
    bad = (
        _balance(10, "missing-pre", None, "B", "1", "2"),
        _balance(10, "missing-post", "A", None, "1", "2"),
        _balance(10, "negative", "A", "A", "-1", "0"),
        _balance(10, "invalid", "A", "A", "bad", "0"),
    )
    for row in bad:
        try:
            parse_owner_delta(row, "MINT")
        except (TypeError, ValueError):
            pass
        else:
            raise AssertionError(f"非法 owner balance 未拒绝: {row!r}")
    duplicate = _balance(11, "same-account", "A", "A", "1", "0")
    try:
        _core.owner_deltas_by_tx([duplicate, dict(duplicate)], "MINT")
    except ValueError:
        pass
    else:
        raise AssertionError("同 (tx_index, account) 重复记录未拒绝")
    for value in (None, True, -1, "7"):
        row = _balance(value, "bad-tx-index", "A", "A", "1", "0")
        try:
            parse_owner_delta(row, "MINT")
        except (TypeError, ValueError):
            pass
        else:
            raise AssertionError(f"非法 transactionIndex 未拒绝: {value!r}")
    for records in (
        [{"transactionIndex": 1}],
        [{"transactionIndex": True, "err": None}],
        [{"transactionIndex": 1, "err": None},
         {"transactionIndex": 1, "err": "duplicate"}],
    ):
        try:
            _core.transaction_status_by_index(records)
        except (TypeError, ValueError):
            pass
        else:
            raise AssertionError(f"非法 transaction 状态表未拒绝: {records!r}")


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
    test_migration_equivalence_and_owner_authority()
    test_owner_aggregation_and_token2022_fee_fixture()
    test_owner_input_failures_are_controlled()
    test_cache_paths_and_semantic_constants()
    print("PASS: spl_edge_core T1 三件套 + T2 迁移等价 + T3 语义常量")
