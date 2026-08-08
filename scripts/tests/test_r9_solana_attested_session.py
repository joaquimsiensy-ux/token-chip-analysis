#!/usr/bin/env python3
"""R9-05 batch-1 tests for the unattached Solana attested-session primitive."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/lib"))
import solana_attested_session as session_module
from solana_attested_session import (SOLANA_MAINNET_GENESIS_HASH,
                                     SolanaAttestedSession, SolanaRpcError)


SECRET_ENDPOINT = "https://mainnet.helius-rpc.com/v1?api-key=SECRET#private"


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


def test_expected_genesis_is_not_a_constructor_boundary():
    try:
        SolanaAttestedSession(
            "fork", expected_genesis="caller-controlled-genesis",
            request_json=lambda _endpoint, _payload, _timeout: {
                "result": "caller-controlled-genesis"})
    except TypeError:
        pass
    else:
        raise AssertionError("caller can override the Solana genesis trust root")


def test_certifi_and_system_ca_context_branches_and_reuse():
    calls = []

    def build_context(**kwargs):
        calls.append(kwargs)
        return object()

    fake_certifi = SimpleNamespace(where=lambda: "/fixture/certifi/cacert.pem")
    with mock.patch.object(session_module.ssl, "create_default_context",
                           side_effect=build_context):
        certifi_context = session_module._build_ssl_context(fake_certifi)
        system_context = session_module._build_ssl_context(None)
    assert certifi_context is not system_context
    assert calls == [{"cafile": "/fixture/certifi/cacert.pem"}, {}]

    seen = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({"result": "ok"}).encode()

    def urlopen(_request, *, timeout, context):
        seen.append((timeout, context))
        return Response()

    with mock.patch.object(session_module.urllib.request, "urlopen",
                           side_effect=urlopen):
        session_module._urllib_json("https://rpc.invalid", {"id": 1}, 7)
        session_module._urllib_json("https://rpc.invalid", {"id": 2}, 8)
    assert seen == [(7, session_module._SSL_CONTEXT),
                    (8, session_module._SSL_CONTEXT)]


def _assert_exception_chain_has_no_endpoint_secret(exc):
    seen = set()
    chain = []
    current = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        chain.append(str(current))
        current = current.__cause__ or (
            None if current.__suppress_context__ else current.__context__)
    rendered = " | ".join(chain)
    assert "api-key" not in rendered.lower(), rendered
    assert "SECRET" not in rendered, rendered
    assert "#private" not in rendered, rendered


def _captured_failure(transport, endpoints=SECRET_ENDPOINT):
    try:
        SolanaAttestedSession(endpoints, request_json=transport).call(
            "getTokenSupply", ["mint"])
    except SolanaRpcError as exc:
        _assert_exception_chain_has_no_endpoint_secret(exc)
        return str(exc)
    raise AssertionError("fixture failure was accepted")


def test_endpoint_secrets_redacted_from_four_failure_shapes():
    def transport_failure(endpoint, _payload, _timeout):
        raise OSError(f"transport rejected {endpoint}")

    _captured_failure(transport_failure)

    def rpc_error(endpoint, payload, _timeout):
        if payload["method"] == "getGenesisHash":
            return {"result": SOLANA_MAINNET_GENESIS_HASH}
        return {"error": {"message": f"upstream rejected {endpoint}"}}

    _captured_failure(rpc_error)

    _captured_failure(lambda _endpoint, _payload, _timeout: {
        "result": "wrong-genesis"})

    endpoints = [SECRET_ENDPOINT, SECRET_ENDPOINT.replace("SECRET", "SECRET2")]
    exhausted = _captured_failure(transport_failure, endpoints=endpoints)
    assert exhausted.count("https://mainnet.helius-rpc.com/v1") >= 2


def main():
    tests = (
        test_wrong_genesis_has_zero_business_calls,
        test_correct_genesis_precedes_business,
        test_wrong_endpoint_fails_over_and_reattests,
        test_business_failure_switches_endpoint_and_reattests,
        test_attestation_transport_and_shape_fail_closed,
        test_expected_genesis_is_not_a_constructor_boundary,
        test_certifi_and_system_ca_context_branches_and_reuse,
        test_endpoint_secrets_redacted_from_four_failure_shapes,
    )
    for test in tests:
        test()
    print(f"PASS R9 SolanaAttestedSession: {len(tests)}/{len(tests)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
