#!/usr/bin/env python3
"""Canonical parser for the labels ``risk_flags`` decision field."""
from __future__ import annotations

import re
import unicodedata


def _strip_invisible_space(value: str) -> str:
    """Strip Unicode whitespace and invisible format characters at boundaries."""
    def invisible(char: str) -> bool:
        return char.isspace() or unicodedata.category(char) in {
            "Cf", "Zl", "Zp", "Zs",
        }

    start, end = 0, len(value)
    while start < end and invisible(value[start]):
        start += 1
    while end > start and invisible(value[end - 1]):
        end -= 1
    return value[start:end]


def parse_risk_flags(raw) -> tuple[str, ...]:
    """Return the unique, trimmed, non-empty flags in deterministic order."""
    if raw is None:
        return ()
    if not isinstance(raw, str):
        raise TypeError("risk_flags must be a string or None")
    flags = set()
    for part in raw.split("|"):
        cleaned = _strip_invisible_space(part)
        if not cleaned:
            continue
        if re.fullmatch(r"[a-z0-9-]+", cleaned) is None:
            raise ValueError(f"risk_flags token 含非法字符: {cleaned!r}")
        flags.add(cleaned)
    return tuple(sorted(flags))


def canonical_risk_flags(raw) -> str:
    """Return the only permitted serialization for newly written rows."""
    return "|".join(parse_risk_flags(raw))


def merge_risk_flags(*values) -> str:
    """Union one or more raw fields and serialize the canonical set."""
    merged = set()
    for value in values:
        merged.update(parse_risk_flags(value))
    return "|".join(sorted(merged))
