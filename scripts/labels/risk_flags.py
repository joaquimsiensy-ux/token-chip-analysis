#!/usr/bin/env python3
"""Canonical parser for the labels ``risk_flags`` decision field."""
from __future__ import annotations


def parse_risk_flags(raw) -> tuple[str, ...]:
    """Return the unique, trimmed, non-empty flags in deterministic order."""
    if raw is None:
        return ()
    return tuple(sorted({part.strip() for part in str(raw).split("|") if part.strip()}))


def canonical_risk_flags(raw) -> str:
    """Return the only permitted serialization for newly written rows."""
    return "|".join(parse_risk_flags(raw))


def merge_risk_flags(*values) -> str:
    """Union one or more raw fields and serialize the canonical set."""
    merged = set()
    for value in values:
        merged.update(parse_risk_flags(value))
    return "|".join(sorted(merged))
