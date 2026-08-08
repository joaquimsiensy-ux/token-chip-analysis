#!/usr/bin/env python3
"""Fail-closed Solana JSON-RPC session with per-endpoint genesis attestation."""
from __future__ import annotations

import json
import threading
import urllib.request


SOLANA_MAINNET_GENESIS_HASH = "5eykt4UsFv8P8NJdTREpY1vzqKqZKvdpKuc147dw2N9d"


class SolanaAttestationError(RuntimeError):
    pass


class SolanaRpcError(RuntimeError):
    pass


def _urllib_json(endpoint, payload, timeout):
    request = urllib.request.Request(
        endpoint, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


class SolanaAttestedSession:
    """Attest the active endpoint as Solana mainnet before its first business RPC.

    ``request_json`` is the only test injection boundary.  It receives
    ``(endpoint, payload, timeout)`` and must return a decoded JSON object.
    """

    def __init__(self, endpoints, *, request_json=None, timeout=30):
        if isinstance(endpoints, str):
            endpoints = [endpoints]
        unique = []
        for endpoint in endpoints or []:
            if not isinstance(endpoint, str) or not endpoint.strip():
                raise ValueError("Solana endpoint must be a non-empty string")
            endpoint = endpoint.strip()
            if endpoint not in unique:
                unique.append(endpoint)
        if not unique:
            raise ValueError("at least one Solana endpoint is required")
        self._endpoints = tuple(unique)
        self._request_json = request_json or _urllib_json
        self._timeout = timeout
        self._index = 0
        self._attested_endpoint = None
        self._observed_genesis = None
        self._request_id = 0
        self._lock = threading.RLock()

    @property
    def endpoint(self):
        return self._endpoints[self._index]

    @property
    def observed_genesis(self):
        return self._observed_genesis

    def _payload(self, method, params):
        self._request_id += 1
        return {"jsonrpc": "2.0", "id": self._request_id,
                "method": method, "params": list(params or [])}

    def _request(self, endpoint, method, params):
        try:
            response = self._request_json(
                endpoint, self._payload(method, params), self._timeout)
        except Exception as exc:
            raise SolanaRpcError(f"{method} transport failed for {endpoint}: {exc}") from exc
        if not isinstance(response, dict):
            raise SolanaRpcError(f"{method} response is not an object for {endpoint}")
        if response.get("error") is not None:
            raise SolanaRpcError(f"{method} RPC error for {endpoint}: {response['error']}")
        if "result" not in response:
            raise SolanaRpcError(f"{method} response missing result for {endpoint}")
        return response["result"]

    def _attest(self, endpoint):
        observed = self._request(endpoint, "getGenesisHash", [])
        if not isinstance(observed, str) or not observed:
            raise SolanaAttestationError(
                f"getGenesisHash returned invalid result for {endpoint}")
        if observed != SOLANA_MAINNET_GENESIS_HASH:
            raise SolanaAttestationError(
                f"Solana genesis mismatch for {endpoint}: expected "
                f"{SOLANA_MAINNET_GENESIS_HASH}, observed {observed}")
        self._attested_endpoint = endpoint
        self._observed_genesis = observed

    def _advance(self):
        self._index = (self._index + 1) % len(self._endpoints)
        self._attested_endpoint = None
        self._observed_genesis = None

    def call(self, method, params=None):
        if not isinstance(method, str) or not method:
            raise ValueError("Solana RPC method must be a non-empty string")
        if method == "getGenesisHash":
            raise ValueError("getGenesisHash is reserved for session attestation")
        failures = []
        with self._lock:
            for _ in self._endpoints:
                endpoint = self.endpoint
                try:
                    if self._attested_endpoint != endpoint:
                        self._attest(endpoint)
                    return self._request(endpoint, method, params or [])
                except (SolanaAttestationError, SolanaRpcError) as exc:
                    failures.append(str(exc))
                    self._advance()
            raise SolanaRpcError(
                f"all Solana endpoints failed for {method}: " + " | ".join(failures))
