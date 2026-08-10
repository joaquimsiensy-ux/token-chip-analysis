#!/usr/bin/env python3
"""Fail-closed Solana JSON-RPC session with per-endpoint genesis attestation."""
from __future__ import annotations

import json
import ssl
import threading
import urllib.request

from endpoint_identity import public_endpoint, redact_endpoint_text

try:
    import certifi as _certifi
except ImportError:  # Optional: system CA remains the zero-dependency fallback.
    _certifi = None


SOLANA_MAINNET_GENESIS_HASH = "5eykt4UsFv8P8NJdTREpY1vzqKqZKvdpKuc147dw2N9d"


class SolanaAttestationError(RuntimeError):
    pass


class SolanaRpcError(RuntimeError):
    pass


def _build_ssl_context(certifi_module):
    if certifi_module is not None:
        try:
            return ssl.create_default_context(cafile=certifi_module.where())
        except (OSError, ssl.SSLError, AttributeError):
            pass
    return ssl.create_default_context()


_SSL_CONTEXT = _build_ssl_context(_certifi)


def _urllib_json(endpoint, payload, timeout):
    request = urllib.request.Request(
        endpoint, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(
            request, timeout=timeout, context=_SSL_CONTEXT) as response:
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
        display = public_endpoint(endpoint)
        try:
            response = self._request_json(
                endpoint, self._payload(method, params), self._timeout)
        except Exception as exc:
            detail = redact_endpoint_text(
                f"{type(exc).__name__}: {exc}", [endpoint])
            raise SolanaRpcError(
                f"{method} transport failed for {display}: {detail}") from None
        if not isinstance(response, dict):
            raise SolanaRpcError(
                f"{method} response is not an object for {display}")
        if response.get("error") is not None:
            detail = redact_endpoint_text(response["error"], [endpoint])
            raise SolanaRpcError(
                f"{method} RPC error for {display}: {detail}")
        if "result" not in response:
            raise SolanaRpcError(
                f"{method} response missing result for {display}")
        return response["result"]

    def _attest(self, endpoint):
        display = public_endpoint(endpoint)
        observed = self._request(endpoint, "getGenesisHash", [])
        if not isinstance(observed, str) or not observed:
            raise SolanaAttestationError(
                f"getGenesisHash returned invalid result for {display}")
        if observed != SOLANA_MAINNET_GENESIS_HASH:
            safe_observed = redact_endpoint_text(observed, [endpoint])
            raise SolanaAttestationError(
                f"Solana genesis mismatch for {display}: expected "
                f"{SOLANA_MAINNET_GENESIS_HASH}, observed {safe_observed}")
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
