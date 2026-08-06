#!/usr/bin/env python3
"""Small receipt envelope and publication kernel.

This module deliberately does not know any receipt family's business fields.  It
only binds identity, inputs and verdict semantics, then provides four explicit
publication primitives.  Validation lives in receipt_validate.py and shares no
normalisation or hashing helpers with this emitter.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping


REPO = Path(__file__).resolve().parents[2]
TARGET_KEYS = ("chain", "token", "as_of_block")
MODES = {"formal", "exploration"}
VERDICT_EXITS = {"PASS": 0, "FAIL": 2, "ERROR": 1}
RESERVED_FIELDS = {"schema", "target", "producer", "mode", "inputs",
                   "verdict", "exit_code"}


class ReceiptKernelError(ValueError):
    pass


def _digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _resolved_input(raw_path) -> Path:
    if not isinstance(raw_path, (str, os.PathLike)) or not str(raw_path):
        raise ReceiptKernelError("input path must be a non-empty path")
    shown = Path(raw_path).expanduser()
    if ".." in shown.parts:
        raise ReceiptKernelError(f"input path escape rejected: {raw_path}")
    if shown.is_absolute():
        if shown.is_symlink():
            raise ReceiptKernelError(f"input symlink rejected: {raw_path}")
        path = shown.resolve(strict=True)
    else:
        base = Path.cwd().resolve()
        lexical = base
        for part in shown.parts:
            if part in {"", "."}:
                raise ReceiptKernelError(f"unsafe relative input path: {raw_path}")
            lexical = lexical / part
            if lexical.is_symlink():
                raise ReceiptKernelError(f"input path contains symlink: {raw_path}")
        path = lexical.resolve(strict=True)
        try:
            path.relative_to(base)
        except ValueError as exc:
            raise ReceiptKernelError(f"input path escape rejected: {raw_path}") from exc
    if not path.is_file():
        raise ReceiptKernelError(f"input is not a regular file: {raw_path}")
    return path


def _file_ref(raw_path) -> dict:
    path = _resolved_input(raw_path)
    return {"path": str(path), "size": path.stat().st_size, "sha256": _digest(path)}


def _producer_ref(producer_file) -> dict:
    path = Path(producer_file).expanduser()
    if not path.is_absolute():
        path = REPO / path
    if ".." in path.parts or path.is_symlink():
        raise ReceiptKernelError(f"producer path invalid: {producer_file}")
    path = path.resolve(strict=True)
    try:
        rel = path.relative_to(REPO).as_posix()
    except ValueError as exc:
        raise ReceiptKernelError(f"producer escapes repository: {producer_file}") from exc
    if not path.is_file():
        raise ReceiptKernelError(f"producer is not a file: {producer_file}")
    return {"path": rel, "sha256": _digest(path)}


def _checked_target(target) -> dict:
    if not isinstance(target, Mapping):
        raise ReceiptKernelError("target must be an object")
    missing = [key for key in TARGET_KEYS if key not in target]
    empty = [key for key in TARGET_KEYS if target.get(key) in (None, "")]
    if missing or empty:
        raise ReceiptKernelError(
            f"target requires non-empty chain/token/as_of_block; missing={missing}, empty={empty}"
        )
    return dict(target)


def build_envelope(schema, target, producer_file, mode, inputs=None) -> dict:
    """Build identity/input layers only; verdict fields are added by finalize_envelope."""
    if not isinstance(schema, str) or not schema.strip():
        raise ReceiptKernelError("schema must be non-empty")
    if mode not in MODES:
        raise ReceiptKernelError(f"mode must be one of {sorted(MODES)}")
    if inputs is None:
        input_refs = {}
    elif isinstance(inputs, Mapping):
        input_refs = {}
        seen = set()
        for name, raw_path in inputs.items():
            if not isinstance(name, str) or not name:
                raise ReceiptKernelError("input names must be non-empty strings")
            ref = _file_ref(raw_path)
            if ref["path"] in seen:
                raise ReceiptKernelError(f"duplicate input path: {ref['path']}")
            seen.add(ref["path"])
            input_refs[name] = ref
    else:
        raise ReceiptKernelError("inputs must be a name->path object")
    return {
        "schema": schema,
        "target": _checked_target(target),
        "producer": _producer_ref(producer_file),
        "mode": mode,
        "inputs": input_refs,
    }


def finalize_envelope(envelope, verdict, exit_code, **fields) -> dict:
    """Return a finalized copy and reject contradictory verdict/exit pairs."""
    if verdict not in VERDICT_EXITS or exit_code != VERDICT_EXITS[verdict]:
        raise ReceiptKernelError(
            f"verdict/exit_code inconsistent: {verdict!r}/{exit_code!r}"
        )
    if not isinstance(envelope, Mapping):
        raise ReceiptKernelError("envelope must be an object")
    if "verdict" in envelope or "exit_code" in envelope:
        raise ReceiptKernelError("envelope was already finalized")
    conflicts = sorted(RESERVED_FIELDS.intersection(fields))
    if conflicts:
        raise ReceiptKernelError(
            f"finalize fields conflict with reserved envelope keys: {conflicts}"
        )
    payload = copy.deepcopy(dict(envelope))
    payload.update(fields)
    payload["verdict"] = verdict
    payload["exit_code"] = exit_code
    return payload


def _json_bytes(payload) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    return f"{stamp}.{os.getpid()}"


def _stage(path: Path, payload) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{_run_id()}")
    try:
        with tmp.open("xb") as handle:
            handle.write(_json_bytes(payload))
            handle.flush()
            os.fsync(handle.fileno())
        return tmp
    except BaseException:
        if tmp.exists():
            tmp.unlink()
        raise


def publish_exclusive(path, payload) -> Path:
    """Publish a new file atomically; an existing destination is always an error."""
    out = Path(path).resolve()
    tmp = _stage(out, payload)
    try:
        os.link(tmp, out)
    except FileExistsError as exc:
        raise ReceiptKernelError(f"exclusive receipt already exists: {out}") from exc
    finally:
        if tmp.exists():
            tmp.unlink()
    return out


def publish_overwrite(path, payload) -> Path:
    """Atomically replace one file; no multi-file guarantee is implied."""
    out = Path(path).resolve()
    tmp = _stage(out, payload)
    try:
        os.replace(tmp, out)
    finally:
        if tmp.exists():
            tmp.unlink()
    return out


def publish_txn(data_path, data_payload, receipt_path, receipt_payload) -> tuple[Path, Path]:
    """Publish data+receipt as one rollback unit; any failure restores both old files."""
    data_out, receipt_out = Path(data_path).resolve(), Path(receipt_path).resolve()
    if data_out == receipt_out:
        raise ReceiptKernelError("transaction paths must be distinct")
    staged = []
    backups = {}
    published = set()
    committed = False
    try:
        data_tmp = _stage(data_out, data_payload); staged.append(data_tmp)
        receipt_tmp = _stage(receipt_out, receipt_payload); staged.append(receipt_tmp)
        for out in (data_out, receipt_out):
            if out.is_symlink():
                raise ReceiptKernelError(f"transaction destination is symlink: {out}")
            if out.exists():
                backup = out.with_name(f".{out.name}.rollback.{_run_id()}")
                os.replace(out, backup)
                backups[out] = backup
        os.replace(data_tmp, data_out); published.add(data_out); staged.remove(data_tmp)
        os.replace(receipt_tmp, receipt_out); published.add(receipt_out); staged.remove(receipt_tmp)
        committed = True
        for backup in backups.values():
            if backup.exists():
                try:
                    backup.unlink()
                except OSError as exc:
                    raise ReceiptKernelError(
                        f"transaction committed but backup cleanup failed; "
                        f"backup preserved at {backup}: {exc}"
                    ) from exc
        return data_out, receipt_out
    except BaseException as primary:
        if committed:
            raise
        rollback_failures = []
        for out, backup in backups.items():
            if backup.exists():
                try:
                    os.replace(backup, out)
                except BaseException as exc:
                    rollback_failures.append((backup, out, exc))
        for out in published - set(backups):
            if out.exists():
                try:
                    out.unlink()
                except BaseException as exc:
                    rollback_failures.append((None, out, exc))
        if rollback_failures:
            preserved = [str(backup) for backup, _, _ in rollback_failures
                         if backup is not None and backup.exists()]
            affected = [str(out) for _, out, _ in rollback_failures]
            detail = ", ".join(str(exc) for _, _, exc in rollback_failures)
            raise ReceiptKernelError(
                f"transaction publish failed ({primary}); rollback also failed for {affected}; "
                f"backups preserved at {preserved}: {detail}"
            ) from rollback_failures[0][2]
        raise
    finally:
        for tmp in staged:
            if tmp.exists():
                tmp.unlink()


def publish_restore_on_fail(path, payload, validate: Callable[[Path], bool] | None = None) -> Path:
    """Replace one formal artifact and restore its prior bytes if post-publish validation fails."""
    out = Path(path).resolve()
    if out.is_symlink():
        raise ReceiptKernelError(f"restore destination is symlink: {out}")
    tmp = _stage(out, payload)
    backup = None
    published = False
    committed = False
    try:
        if out.exists():
            backup = out.with_name(f".{out.name}.rollback.{_run_id()}")
            os.replace(out, backup)
        os.replace(tmp, out); published = True
        if validate is not None and validate(out) is not True:
            raise ReceiptKernelError("post-publish validation failed")
        committed = True
        if backup and backup.exists():
            try:
                backup.unlink()
            except OSError as exc:
                raise ReceiptKernelError(
                    f"publish committed but backup cleanup failed; "
                    f"backup preserved at {backup}: {exc}"
                ) from exc
        return out
    except BaseException as primary:
        if committed:
            raise
        if backup and backup.exists():
            try:
                os.replace(backup, out)
            except BaseException as exc:
                raise ReceiptKernelError(
                    f"publish failed ({primary}); rollback also failed; "
                    f"backup preserved at {backup}: {exc}"
                ) from exc
        elif published and out.exists():
            try:
                out.unlink()
            except BaseException as exc:
                raise ReceiptKernelError(
                    f"publish failed ({primary}); rollback cleanup also failed for {out}: {exc}"
                ) from exc
        raise
    finally:
        if tmp.exists():
            tmp.unlink()


def publish_error_receipt(receipt_path, envelope, error, *, run_id=None) -> Path:
    """Publish ERROR to a unique side path; never replace the canonical receipt."""
    canonical = Path(receipt_path).resolve()
    suffix = canonical.suffix or ".json"
    stem = canonical.name[:-len(suffix)] if canonical.name.endswith(suffix) else canonical.name
    unique = run_id or _run_id()
    error_path = canonical.with_name(f"{stem}.error.{unique}{suffix}")
    payload = finalize_envelope(envelope, "ERROR", 1, error=str(error))
    return publish_exclusive(error_path, payload)
