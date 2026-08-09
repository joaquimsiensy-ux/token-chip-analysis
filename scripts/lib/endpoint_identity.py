#!/usr/bin/env python3
"""Secret-safe endpoint display helpers for logs, receipts and exceptions."""
from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, unquote, urlsplit, urlunsplit


_CREDENTIAL_PREFIXES = frozenset({"v1", "v2", "v3", "key", "token", "apikey", "api-key"})
_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE)
_LONG_HEX = re.compile(r"^[0-9a-f]{24,}$", re.IGNORECASE)
_LONG_TOKEN = re.compile(r"^[A-Za-z0-9_+=-]{24,}$")


def _secret_path_segment(segment, previous):
    decoded = unquote(segment)
    if previous.lower() in _CREDENTIAL_PREFIXES and decoded:
        return True
    return bool(_UUID.fullmatch(decoded) or _LONG_HEX.fullmatch(decoded)
                or _LONG_TOKEN.fullmatch(decoded))


def _redacted_path(path):
    parts = path.split("/")
    safe = []
    previous = ""
    for part in parts:
        safe.append("[redacted]" if _secret_path_segment(part, previous) else part)
        if part:
            previous = unquote(part)
    return "/".join(safe)


def public_endpoint(endpoint: str) -> str:
    """Return a diagnostic origin/path with credentials removed."""
    if not isinstance(endpoint, str):
        return "<invalid-endpoint>"
    raw = endpoint.strip()
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return "<invalid-endpoint>"
    if parsed.scheme and parsed.netloc:
        netloc = parsed.netloc.rsplit("@", 1)[-1]
        return urlunsplit((parsed.scheme, netloc, _redacted_path(parsed.path), "", ""))
    return _redacted_path(parsed.path) or "<endpoint>"


def endpoint_fingerprint(endpoint: str) -> dict:
    """Return a secret-safe display value plus a stable private identity digest."""
    return {
        "public_origin": public_endpoint(endpoint),
        "sha256": hashlib.sha256(endpoint.encode("utf-8")).hexdigest(),
    }


def redact_endpoint_text(value, endpoints) -> str:
    """Remove endpoint query/fragment credentials from arbitrary error text."""
    text = str(value)
    unique = sorted({item for item in endpoints
                     if isinstance(item, str) and item}, key=len, reverse=True)
    for endpoint in unique:
        public = public_endpoint(endpoint)
        text = text.replace(endpoint, public)
        try:
            parsed = urlsplit(endpoint)
        except ValueError:
            continue
        for secret in (parsed.query, parsed.fragment):
            if secret:
                text = text.replace(secret, "[redacted]")
        for _key, secret in parse_qsl(parsed.query, keep_blank_values=True):
            if secret:
                text = text.replace(secret, "[redacted]")
        parts = parsed.path.split("/")
        previous = ""
        for part in parts:
            if _secret_path_segment(part, previous):
                text = text.replace(part, "[redacted]")
                decoded = unquote(part)
                if decoded != part:
                    text = text.replace(decoded, "[redacted]")
            if part:
                previous = unquote(part)
    return text
