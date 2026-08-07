#!/usr/bin/env python3
"""R9-05 batch-1 tests for the unattached Solana attested-session primitive."""
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/lib"))
from solana_attested_session import (SOLANA_MAINNET_GENESIS_HASH,
                                     SolanaAttestedSession, SolanaRpcError)


def methods(calls, endpoint=None):
    return [payload["method"] for ep, payload in calls
            if endpoint is None or ep == endpoint]


def test_wrong_genesis_has_zero_business_calls():
    calls = []

    def transport(endpoint, payload, _timeout):
        calls.append((endpoint, payload))
        return {"result": "wrong-genesis"}

    session = SolanaAttestedSession("wrong", request_json=transport)
    try:
        session.call("getBalance", ["address"])
    except SolanaRpcError:
        pass
    else:
        raise AssertionError("wrong genesis accepted")
    assert methods(calls) == ["getGenesisHash"], calls


def test_correct_genesis_precedes_business():
    calls = []

    def transport(endpoint, payload, _timeout):
        calls.append((endpoint, payload))
        if payload["method"] == "getGenesisHash":
            return {"result": SOLANA_MAINNET_GENESIS_HASH}
        return {"result": {"value": 7}}

    session = SolanaAttestedSession("mainnet", request_json=transport)
    assert session.call("getBalance", ["address"]) == {"value": 7}
    assert methods(calls) == ["getGenesisHash", "getBalance"]
    assert session.observed_genesis == SOLANA_MAINNET_GENESIS_HASH


def test_wrong_endpoint_fails_over_and_reattests():
    calls = []

    def transport(endpoint, payload, _timeout):
        calls.append((endpoint, payload))
        if payload["method"] == "getGenesisHash":
            return {"result": "wrong" if endpoint == "fork" else SOLANA_MAINNET_GENESIS_HASH}
        return {"result": "business-ok"}

    session = SolanaAttestedSession(["fork", "mainnet"], request_json=transport)
    assert session.call("getTokenSupply", ["mint"]) == "business-ok"
    assert methods(calls, "fork") == ["getGenesisHash"]
    assert methods(calls, "mainnet") == ["getGenesisHash", "getTokenSupply"]


def test_business_failure_switches_endpoint_and_reattests():
    calls = []
    failed_once = {"value": False}

    def transport(endpoint, payload, _timeout):
        calls.append((endpoint, payload))
        method = payload["method"]
        if method == "getGenesisHash":
            return {"result": SOLANA_MAINNET_GENESIS_HASH}
        if endpoint == "a" and method == "getTokenSupply" and not failed_once["value"]:
            failed_once["value"] = True
            raise OSError("injected endpoint failure")
        return {"result": endpoint + "-ok"}

    session = SolanaAttestedSession(["a", "b"], request_json=transport)
    assert session.call("getBalance", ["address"]) == "a-ok"
    assert session.call("getTokenSupply", ["mint"]) == "b-ok"
    assert methods(calls, "a") == ["getGenesisHash", "getBalance", "getTokenSupply"]
    assert methods(calls, "b") == ["getGenesisHash", "getTokenSupply"]


def test_attestation_transport_and_shape_fail_closed():
    business = []

    def transport(endpoint, payload, _timeout):
        if payload["method"] != "getGenesisHash":
            business.append((endpoint, payload))
        if endpoint == "network":
            raise OSError("offline")
        return {"not_result": True}

    session = SolanaAttestedSession(["network", "malformed"], request_json=transport)
    try:
        session.call("getProgramAccounts", [])
    except SolanaRpcError:
        pass
    else:
        raise AssertionError("failed attestation reached business RPC")
    assert business == []


def main():
    tests = (
        test_wrong_genesis_has_zero_business_calls,
        test_correct_genesis_precedes_business,
        test_wrong_endpoint_fails_over_and_reattests,
        test_business_failure_switches_endpoint_and_reattests,
        test_attestation_transport_and_shape_fail_closed,
    )
    for test in tests:
        test()
    print(f"PASS R9 SolanaAttestedSession: {len(tests)}/{len(tests)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
