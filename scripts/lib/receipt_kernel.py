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
import stat
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
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


@dataclass(frozen=True)
class RawBytes:
    data: bytes


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
    if ".." in path.parts:
        raise ReceiptKernelError(f"producer path invalid: {producer_file}")
    with _secure_target(path, create_parents=False) as producer:
        if _target_stat(producer) is None:
            raise ReceiptKernelError(f"producer is not a file: {producer_file}")
        path = producer.path.resolve(strict=True)
    try:
        rel = path.relative_to(REPO).as_posix()
    except ValueError as exc:
        raise ReceiptKernelError(f"producer escapes repository: {producer_file}") from exc
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
    if isinstance(payload, RawBytes):
        return payload.data
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    return f"{stamp}.{os.getpid()}"


@dataclass
class _SecureTarget:
    path: Path
    parent_fd: int
    name: str
    parent_identity: tuple[int, int]


def _lexical_path(raw_path) -> Path:
    if not isinstance(raw_path, (str, os.PathLike)) or not str(raw_path):
        raise ReceiptKernelError("output path must be a non-empty path")
    shown = Path(raw_path).expanduser()
    if ".." in shown.parts:
        raise ReceiptKernelError(f"output path traversal rejected: {raw_path}")
    absolute = Path(os.path.abspath(os.fspath(shown)))
    if absolute == Path(absolute.anchor) or absolute.name in {"", ".", ".."}:
        raise ReceiptKernelError(f"output path must name a file: {raw_path}")
    return absolute


def _checked_entry_stat(parent_fd: int, name: str, shown: Path):
    try:
        info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(info.st_mode):
        raise ReceiptKernelError(f"output path contains symlink: {shown}")
    if not stat.S_ISREG(info.st_mode):
        raise ReceiptKernelError(f"output destination is not a regular file: {shown}")
    return info


@contextmanager
def _secure_target(raw_path, *, create_parents=True):
    """Open a lexical parent chain with lstat/openat and never follow a symlink.

    The returned directory fd pins the checked directory for staging, link,
    replace and rollback operations.  Every component is lstat'ed before open;
    fstat then proves the opened directory is the same object that was checked.
    """
    path = _lexical_path(raw_path)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path.anchor, flags | nofollow)
    try:
        for part in path.parent.parts[1:]:
            try:
                before = os.stat(part, dir_fd=fd, follow_symlinks=False)
            except FileNotFoundError:
                if not create_parents:
                    raise ReceiptKernelError(f"output parent does not exist: {path.parent}")
                try:
                    os.mkdir(part, mode=0o755, dir_fd=fd)
                except FileExistsError:
                    pass
                before = os.stat(part, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISLNK(before.st_mode):
                raise ReceiptKernelError(f"output parent contains symlink: {path}")
            if not stat.S_ISDIR(before.st_mode):
                raise ReceiptKernelError(f"output parent component is not a directory: {path}")
            try:
                next_fd = os.open(part, flags | nofollow, dir_fd=fd)
            except OSError as exc:
                raise ReceiptKernelError(f"output parent cannot be opened safely: {path}") from exc
            after = os.fstat(next_fd)
            if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
                os.close(next_fd)
                raise ReceiptKernelError(f"output parent changed while opening: {path}")
            os.close(fd)
            fd = next_fd
        _checked_entry_stat(fd, path.name, path)
        parent_stat = os.fstat(fd)
        target = _SecureTarget(
            path=path, parent_fd=fd, name=path.name,
            parent_identity=(parent_stat.st_dev, parent_stat.st_ino))
        fd = -1
        try:
            yield target
        finally:
            os.close(target.parent_fd)
    finally:
        if fd >= 0:
            os.close(fd)


def _target_stat(target: _SecureTarget):
    return _checked_entry_stat(target.parent_fd, target.name, target.path)


def _assert_distinct(*targets: _SecureTarget):
    # casefold is deliberately conservative: macOS deployments commonly use a
    # case-insensitive filesystem even though POSIX normcase() is a no-op.
    lexical = [os.path.normpath(str(target.path)).casefold() for target in targets]
    if len(lexical) != len(set(lexical)):
        raise ReceiptKernelError("publication paths must be lexically distinct")
    physical = []
    for target in targets:
        info = _target_stat(target)
        if info is not None:
            physical.append((info.st_dev, info.st_ino))
    if len(physical) != len(set(physical)):
        raise ReceiptKernelError("publication paths alias the same physical file")


def _unlink_at(target: _SecureTarget, name: str):
    try:
        os.unlink(name, dir_fd=target.parent_fd)
    except FileNotFoundError:
        pass


def _existing_json(target: _SecureTarget):
    if _target_stat(target) is None:
        return None
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(target.name, flags, dir_fd=target.parent_fd)
    try:
        with os.fdopen(fd, "rb", closefd=False) as handle:
            try:
                return json.load(handle)
            except (TypeError, ValueError):
                return None
    finally:
        os.close(fd)


def _reject_pass_downgrade(target: _SecureTarget, payload):
    old = _existing_json(target)
    if (isinstance(old, Mapping) and old.get("verdict") == "PASS"
            and isinstance(payload, Mapping) and payload.get("verdict") != "PASS"):
        raise ReceiptKernelError(f"existing PASS artifact cannot be downgraded: {target.path}")


def _stage(target: _SecureTarget, payload) -> str:
    tmp_name = f".{target.name}.tmp.{_run_id()}"
    flags = (os.O_WRONLY | os.O_CREAT | os.O_EXCL
             | getattr(os, "O_NOFOLLOW", 0))
    try:
        fd = os.open(tmp_name, flags, 0o600, dir_fd=target.parent_fd)
        with os.fdopen(fd, "wb") as handle:
            handle.write(_json_bytes(payload))
            handle.flush()
            os.fsync(handle.fileno())
        return tmp_name
    except BaseException:
        _unlink_at(target, tmp_name)
        raise


def publish_exclusive(path, payload) -> Path:
    """Publish a new file atomically; an existing destination is always an error."""
    with _secure_target(path) as out:
        tmp = _stage(out, payload)
        try:
            if _target_stat(out) is not None:
                raise ReceiptKernelError(f"exclusive receipt already exists: {out.path}")
            os.link(tmp, out.name, src_dir_fd=out.parent_fd,
                    dst_dir_fd=out.parent_fd, follow_symlinks=False)
        except FileExistsError as exc:
            raise ReceiptKernelError(f"exclusive receipt already exists: {out.path}") from exc
        finally:
            _unlink_at(out, tmp)
        return out.path


def publish_overwrite(path, payload) -> Path:
    """Atomically replace one file; no multi-file guarantee is implied."""
    with _secure_target(path) as out:
        _reject_pass_downgrade(out, payload)
        tmp = _stage(out, payload)
        try:
            _target_stat(out)
            os.replace(tmp, out.name,
                       src_dir_fd=out.parent_fd, dst_dir_fd=out.parent_fd)
        finally:
            _unlink_at(out, tmp)
        return out.path


def assert_distinct_paths(*paths) -> None:
    with ExitStack() as stack:
        targets = [stack.enter_context(_secure_target(path)) for path in paths]
        for index, left in enumerate(targets):
            for right in targets[index + 1:]:
                _assert_distinct(left, right)


def publish_txn(data_path, data_payload, receipt_path, receipt_payload) -> tuple[Path, Path]:
    """Publish data+receipt as one rollback unit; any failure restores both old files."""
    with _secure_target(data_path) as data_out, _secure_target(receipt_path) as receipt_out:
        _assert_distinct(data_out, receipt_out)
        _reject_pass_downgrade(data_out, data_payload)
        _reject_pass_downgrade(receipt_out, receipt_payload)
        staged = []
        backups = {}
        published = set()
        committed = False
        try:
            data_tmp = _stage(data_out, data_payload); staged.append((data_out, data_tmp))
            receipt_tmp = _stage(receipt_out, receipt_payload); staged.append((receipt_out, receipt_tmp))
            for out in (data_out, receipt_out):
                if _target_stat(out) is not None:
                    backup = f".{out.name}.rollback.{_run_id()}"
                    os.replace(out.name, backup,
                               src_dir_fd=out.parent_fd, dst_dir_fd=out.parent_fd)
                    backups[id(out)] = (out, backup)
            _target_stat(data_out)
            os.replace(data_tmp, data_out.name,
                       src_dir_fd=data_out.parent_fd, dst_dir_fd=data_out.parent_fd)
            published.add(id(data_out)); staged.remove((data_out, data_tmp))
            _target_stat(receipt_out)
            os.replace(receipt_tmp, receipt_out.name,
                       src_dir_fd=receipt_out.parent_fd, dst_dir_fd=receipt_out.parent_fd)
            published.add(id(receipt_out)); staged.remove((receipt_out, receipt_tmp))
            committed = True
            for out, backup in backups.values():
                try:
                    _unlink_at(out, backup)
                except OSError as exc:
                    backup_path = out.path.with_name(backup)
                    raise ReceiptKernelError(
                        f"transaction committed but backup cleanup failed; "
                        f"backup preserved at {backup_path}: {exc}"
                    ) from exc
            return data_out.path, receipt_out.path
        except BaseException as primary:
            if committed:
                raise
            rollback_failures = []
            for out, backup in backups.values():
                try:
                    os.stat(backup, dir_fd=out.parent_fd, follow_symlinks=False)
                except FileNotFoundError:
                    continue
                try:
                    _target_stat(out)
                    os.replace(backup, out.name,
                               src_dir_fd=out.parent_fd, dst_dir_fd=out.parent_fd)
                except BaseException as exc:
                    rollback_failures.append((out, backup, exc))
            for out in (data_out, receipt_out):
                if id(out) in published and id(out) not in backups:
                    try:
                        _target_stat(out)
                        _unlink_at(out, out.name)
                    except BaseException as exc:
                        rollback_failures.append((out, None, exc))
            if rollback_failures:
                preserved = [str(out.path.with_name(backup))
                             for out, backup, _ in rollback_failures
                             if backup is not None]
                affected = [str(out.path) for out, _, _ in rollback_failures]
                detail = ", ".join(str(exc) for _, _, exc in rollback_failures)
                raise ReceiptKernelError(
                    f"transaction publish failed ({primary}); rollback also failed for {affected}; "
                    f"backups preserved at {preserved}: {detail}"
                ) from rollback_failures[0][2]
            raise
        finally:
            for out, tmp in staged:
                _unlink_at(out, tmp)


def publish_restore_on_fail(path, payload, validate: Callable[[Path], bool] | None = None) -> Path:
    """Replace one formal artifact and restore its prior bytes if post-publish validation fails."""
    with _secure_target(path) as out:
        _reject_pass_downgrade(out, payload)
        tmp = _stage(out, payload)
        backup = None
        published = False
        committed = False
        try:
            if _target_stat(out) is not None:
                backup = f".{out.name}.rollback.{_run_id()}"
                os.replace(out.name, backup,
                           src_dir_fd=out.parent_fd, dst_dir_fd=out.parent_fd)
            _target_stat(out)
            os.replace(tmp, out.name,
                       src_dir_fd=out.parent_fd, dst_dir_fd=out.parent_fd); published = True
            if validate is not None and validate(out.path) is not True:
                raise ReceiptKernelError("post-publish validation failed")
            committed = True
            if backup:
                try:
                    _unlink_at(out, backup)
                except OSError as exc:
                    backup_path = out.path.with_name(backup)
                    raise ReceiptKernelError(
                        f"publish committed but backup cleanup failed; "
                        f"backup preserved at {backup_path}: {exc}"
                    ) from exc
            return out.path
        except BaseException as primary:
            if committed:
                raise
            if backup:
                try:
                    os.stat(backup, dir_fd=out.parent_fd, follow_symlinks=False)
                except FileNotFoundError:
                    backup_exists = False
                else:
                    backup_exists = True
                if backup_exists:
                    try:
                        _target_stat(out)
                        os.replace(backup, out.name,
                                   src_dir_fd=out.parent_fd, dst_dir_fd=out.parent_fd)
                    except BaseException as exc:
                        backup_path = out.path.with_name(backup)
                        raise ReceiptKernelError(
                            f"publish failed ({primary}); rollback also failed; "
                            f"backup preserved at {backup_path}: {exc}"
                        ) from exc
            elif published:
                try:
                    _target_stat(out)
                    _unlink_at(out, out.name)
                except BaseException as exc:
                    raise ReceiptKernelError(
                        f"publish failed ({primary}); rollback cleanup also failed for "
                        f"{out.path}: {exc}"
                    ) from exc
            raise
        finally:
            _unlink_at(out, tmp)


def publish_error_receipt(receipt_path, envelope, error, *, run_id=None) -> Path:
    """Publish ERROR to a unique side path; never replace the canonical receipt."""
    canonical = _lexical_path(receipt_path)
    with _secure_target(canonical):
        pass
    suffix = canonical.suffix or ".json"
    stem = canonical.name[:-len(suffix)] if canonical.name.endswith(suffix) else canonical.name
    unique = run_id or _run_id()
    error_path = canonical.with_name(f"{stem}.error.{unique}{suffix}")
    payload = finalize_envelope(envelope, "ERROR", 1, error=str(error))
    return publish_exclusive(error_path, payload)
