#!/usr/bin/env python3
"""Central proxy resolution for active token-chip-analysis scripts.

Precedence: explicit CLI value, CHIP_PROXY, local listener probe, direct.
An explicit empty string or ``none`` means direct and suppresses lower layers.
"""
from __future__ import annotations

import os
import socket
import sys
from urllib.parse import urlsplit, urlunsplit


_ALLOWED_SCHEMES = {"http", "https", "socks5"}
_PROBE_HOST = "127.0.0.1"
_PROBE_PORTS = (6152, 7897)
_PROBE_TIMEOUT = 0.2


def redact_proxy(value: str | None) -> str | None:
    """Return a log-safe proxy URL with any userinfo replaced."""
    if value is None:
        return None
    text = str(value).strip()
    try:
        parsed = urlsplit(text)
    except ValueError:
        return "<invalid-proxy>"
    if parsed.username is None and parsed.password is None:
        return text
    host = parsed.hostname or ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    try:
        port = f":{parsed.port}" if parsed.port is not None else ""
    except ValueError:
        port = ""
    return urlunsplit((parsed.scheme, f"***:***@{host}{port}",
                       parsed.path, parsed.query, parsed.fragment))


def _normalize(value: str, source: str) -> str | None:
    if not isinstance(value, str):
        raise ValueError(f"{source} 代理非法：必须是字符串")
    candidate = value.strip()
    if not candidate or candidate.lower() == "none":
        return None
    try:
        parsed = urlsplit(candidate)
        valid = parsed.scheme.lower() in _ALLOWED_SCHEMES and bool(parsed.netloc)
        if parsed.hostname is None:
            valid = False
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            valid = False
    except ValueError:
        valid = False
    if not valid:
        raise ValueError(
            f"{source} 非法代理（值 {redact_proxy(candidate)}）；"
            "仅支持 http://、https://、socks5:// URL")
    return candidate


def _port_open(port: int) -> bool:
    try:
        connection = socket.create_connection(
            (_PROBE_HOST, port), timeout=_PROBE_TIMEOUT)
    except OSError:
        return False
    try:
        return True
    finally:
        connection.close()


def resolve_proxy(cli_value: str | None = None) -> str | None:
    """Resolve one explicit proxy value without consulting trust_env.

    ``None`` means the CLI option was omitted.  ``""`` and ``"none"`` are
    explicit direct-connect requests and therefore beat environment/probing.
    """
    if cli_value is not None:
        return _normalize(cli_value, "--proxy")
    if "CHIP_PROXY" in os.environ:
        return _normalize(os.environ["CHIP_PROXY"], "CHIP_PROXY")
    for port in _PROBE_PORTS:
        if _port_open(port):
            selected = f"http://{_PROBE_HOST}:{port}"
            print(f"经端口探测选用 {selected}，建议固化 CHIP_PROXY 环境变量",
                  file=sys.stderr)
            return selected
    return None

