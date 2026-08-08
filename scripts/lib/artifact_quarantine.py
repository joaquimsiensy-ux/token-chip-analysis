#!/usr/bin/env python3
"""Shared startup quarantine for prior canonical artifacts."""
from __future__ import annotations

import os
import time
from pathlib import Path


def quarantine_run_id() -> str:
    """Return a process-scoped, nanosecond run identifier for stale siblings."""
    return f"{time.time_ns()}.{os.getpid()}"


def quarantine_current(path, run_id=None):
    """Move one prior file/symlink out of its current formal location."""
    current = Path(os.path.abspath(os.path.expanduser(str(path))))
    if not os.path.lexists(current):
        return None
    if not current.is_file() and not current.is_symlink():
        raise RuntimeError(f"old canonical is not a regular file: {current}")
    suffix = run_id or quarantine_run_id()
    stale = current.with_name(f"{current.name}.stale.{suffix}")
    if os.path.lexists(stale):
        raise RuntimeError(f"stale destination already exists: {stale}")
    os.replace(current, stale)
    return stale
