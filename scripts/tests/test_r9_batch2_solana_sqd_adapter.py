#!/usr/bin/env python3
"""R9-05 B2-G3: Solana SQD dataset scope is mainnet-anchored."""
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/lib"))

from solana_attested_session import (SOLANA_MAINNET_GENESIS_HASH,
                                     SolanaAttestedSession, SolanaRpcError)  # noqa: E402

MINT = "Pythia11111111111111111111111111111111111"


def session_with(genesis=SOLANA_MAINNET_GENESIS_HASH, head=250):
    calls = []

    def transport(endpoint, payload, _timeout):
        calls.append((endpoint, payload["method"]))
        if payload["method"] == "getGenesisHash":
            return {"result": genesis}
        if payload["method"] == "getSlot":
            return {"result": head}
        raise AssertionError(f"unexpected RPC: {payload}")

    return SolanaAttestedSession("fixture", request_json=transport), calls


def test_scope_is_fixed_and_rpc_anchored():
    from solana_sqd_dataset import SolanaSqdDatasetAdapter

    session, calls = session_with()
    adapter = SolanaSqdDatasetAdapter(
        dataset_id="solana-mainnet", mint=MINT, from_slot=100, to_slot=200,
        state_session=session)
    scope = adapter.attest_state_anchor()
    assert scope == {
        "dataset_id": "solana-mainnet", "mint": MINT,
        "from_slot": 100, "to_slot": 200, "state_anchor_slot": 250,
        "state_genesis": SOLANA_MAINNET_GENESIS_HASH,
    }
    assert calls == [("fixture", "getGenesisHash"), ("fixture", "getSlot")]


def test_dataset_mint_and_slot_identity_fail_closed():
    from solana_sqd_dataset import SolanaSqdDatasetAdapter

    session, _ = session_with()
    bad = (
        {"dataset_id": "solana-devnet", "mint": MINT, "from_slot": 1, "to_slot": 2},
        {"dataset_id": "solana-mainnet", "mint": "", "from_slot": 1, "to_slot": 2},
        {"dataset_id": "solana-mainnet", "mint": MINT, "from_slot": 3, "to_slot": 2},
        {"dataset_id": "solana-mainnet", "mint": MINT, "from_slot": True, "to_slot": 2},
    )
    for kwargs in bad:
        try:
            SolanaSqdDatasetAdapter(state_session=session, **kwargs)
        except (TypeError, ValueError):
            pass
        else:
            raise AssertionError(f"invalid SQD identity accepted: {kwargs}")


def test_wrong_genesis_and_uncovered_range_never_anchor():
    from solana_sqd_dataset import SolanaSqdDatasetAdapter

    wrong, calls = session_with(genesis="wrong")
    adapter = SolanaSqdDatasetAdapter(
        dataset_id="solana-mainnet", mint=MINT, from_slot=100, to_slot=200,
        state_session=wrong)
    try:
        adapter.attest_state_anchor()
    except SolanaRpcError:
        pass
    else:
        raise AssertionError("wrong-genesis RPC anchored SQD scope")
    assert calls == [("fixture", "getGenesisHash")]

    behind, _ = session_with(head=199)
    adapter = SolanaSqdDatasetAdapter(
        dataset_id="solana-mainnet", mint=MINT, from_slot=100, to_slot=200,
        state_session=behind)
    try:
        adapter.attest_state_anchor()
    except ValueError:
        pass
    else:
        raise AssertionError("RPC anchor below dataset range was accepted")


def test_only_real_attested_session_is_accepted():
    from solana_sqd_dataset import SolanaSqdDatasetAdapter

    fake = type("SelfReportedSession", (), {
        "observed_genesis": SOLANA_MAINNET_GENESIS_HASH,
        "call": lambda self, *_args: 999,
    })()
    try:
        SolanaSqdDatasetAdapter(
            dataset_id="solana-mainnet", mint=MINT, from_slot=1, to_slot=2,
            state_session=fake)
    except TypeError:
        pass
    else:
        raise AssertionError("self-reported session accepted as mainnet anchor")


def main():
    test_scope_is_fixed_and_rpc_anchored()
    test_dataset_mint_and_slot_identity_fail_closed()
    test_wrong_genesis_and_uncovered_range_never_anchor()
    test_only_real_attested_session_is_accepted()
    print("PASS R9 B2-G3: SQD dataset scope fixed and Solana mainnet RPC anchored")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
