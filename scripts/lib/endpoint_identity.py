#!/usr/bin/env python3
"""Secret-safe endpoint display helpers for logs, receipts and exceptions."""
from __future__ import annotations

from urllib.parse import parse_qsl, urlsplit, urlunsplit


def public_endpoint(endpoint: str) -> str:
    """Return scheme://host/path without credentials, query or fragment."""
    if not isinstance(endpoint, str):
        return "<invalid-endpoint>"
    raw = endpoint.strip()
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return "<invalid-endpoint>"
    if parsed.scheme and parsed.netloc:
        netloc = parsed.netloc.rsplit("@", 1)[-1]
        return urlunsplit((parsed.scheme, netloc, parsed.path, "", ""))
    return parsed.path or "<endpoint>"


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
        for key, secret in parse_qsl(parsed.query, keep_blank_values=True):
            if secret:
                text = text.replace(secret, "[redacted]")
            if key:
                text = text.replace(key, "[redacted-key]")
    return text
