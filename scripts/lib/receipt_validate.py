#!/usr/bin/env python3
"""Independent validator for receipt_kernel envelopes.

This file intentionally does not import receipt_kernel and reimplements path,
hash and semantic checks so one emitter bug cannot mechanically validate itself.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[2]
REQUIRED_TARGET = ("chain", "token", "as_of_block")
ALLOWED_MODES = {"formal", "exploration"}
EXIT_BY_VERDICT = {"PASS": 0, "FAIL": 2, "ERROR": 1}


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            block = stream.read(131072)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _regular_file(shown, *, root=None):
    if not isinstance(shown, str) or not shown:
        raise ValueError("path is missing")
    raw = Path(shown).expanduser()
    if ".." in raw.parts:
        raise ValueError("path contains traversal")
    if root is not None:
        if raw.is_absolute():
            raise ValueError("repository path must be relative")
        candidate = root / raw
        if candidate.is_symlink():
            raise ValueError("path is a symlink")
        path = candidate.resolve(strict=True)
        path.relative_to(root)
    else:
        if raw.is_symlink():
            raise ValueError("path is a symlink")
        path = raw.resolve(strict=True)
    if not path.is_file():
        raise ValueError("path is not a regular file")
    return path


def validate_receipt(receipt, repo_root=None) -> list[str]:
    errors = []
    root = Path(repo_root or REPOSITORY).resolve()
    if not isinstance(receipt, dict):
        return ["receipt must be an object"]
    if not isinstance(receipt.get("schema"), str) or not receipt.get("schema", "").strip():
        errors.append("schema missing")
    target = receipt.get("target")
    if not isinstance(target, dict):
        errors.append("target missing")
    else:
        for key in REQUIRED_TARGET:
            if key not in target or target.get(key) in (None, ""):
                errors.append(f"target.{key} missing or empty")
    if receipt.get("mode") not in ALLOWED_MODES:
        errors.append("mode invalid")
    verdict = receipt.get("verdict")
    if verdict not in EXIT_BY_VERDICT or receipt.get("exit_code") != EXIT_BY_VERDICT.get(verdict):
        errors.append("verdict/exit_code inconsistent")

    producer = receipt.get("producer")
    if not isinstance(producer, dict):
        errors.append("producer missing")
    else:
        try:
            producer_path = _regular_file(producer.get("path"), root=root)
            if producer.get("sha256") != _hash_file(producer_path):
                errors.append("producer hash mismatch")
        except (OSError, ValueError, TypeError) as exc:
            errors.append(f"producer invalid: {exc}")

    inputs = receipt.get("inputs")
    if not isinstance(inputs, dict):
        errors.append("inputs must be an object")
    else:
        seen = set()
        for name, ref in inputs.items():
            if not isinstance(name, str) or not name or not isinstance(ref, dict):
                errors.append(f"input {name!r} invalid")
                continue
            try:
                path = _regular_file(ref.get("path"))
                canonical = str(path)
                if canonical in seen:
                    errors.append(f"input {name} duplicates another path")
                seen.add(canonical)
                if ref.get("size") != path.stat().st_size:
                    errors.append(f"input {name} size mismatch")
                if ref.get("sha256") != _hash_file(path):
                    errors.append(f"input {name} hash mismatch")
            except (OSError, ValueError, TypeError) as exc:
                errors.append(f"input {name} invalid: {exc}")
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt")
    args = parser.parse_args(argv)
    try:
        obj = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
        errors = validate_receipt(obj)
    except Exception as exc:
        errors = [f"receipt unreadable: {exc}"]
    if errors:
        for error in errors:
            print(f"FAIL {error}")
        return 1
    print("PASS receipt envelope and file bindings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
