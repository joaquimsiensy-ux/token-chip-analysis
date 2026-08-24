"""Shared case-root containment helpers for regular-file and directory references."""

from __future__ import annotations

import os
from pathlib import Path


def safe_case_file(case_root, rel, *, must_exist=True) -> Path:
    """Return a contained regular-file path for an unmodified relative string.

    The raw string is validated before ``Path`` can normalize dot or empty
    segments.  Every lexical component is then checked for symlinks, followed
    by a realpath containment check against the case root.
    """
    if not isinstance(rel, str) or not rel or not rel.strip():
        raise ValueError(f"路径必须是案根内非空相对文件路径: {rel!r}")
    if os.path.isabs(rel):
        raise ValueError(f"路径不得是绝对路径: {rel!r}")
    parts = rel.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"路径含空段、. 或 .. 非法段: {rel!r}")

    root = Path(case_root)
    lexical = root
    try:
        for part in parts:
            lexical = lexical / part
            if lexical.is_symlink():
                raise ValueError(f"路径不得经过符号链接: {rel!r}")

        root_real = Path(os.path.realpath(root))
        target = Path(os.path.realpath(lexical))
        if os.path.commonpath((str(target), str(root_real))) != str(root_real):
            raise ValueError(f"路径越出案根: {rel!r}")
        if target.exists():
            if not target.is_file():
                raise ValueError(f"路径不是常规文件: {rel!r}")
        elif must_exist:
            raise ValueError(f"文件不存在: {rel!r}")
        return target
    except ValueError:
        raise
    except (OSError, TypeError) as exc:
        raise ValueError(f"路径校验失败: {rel!r}: {exc}") from exc


def safe_case_dir(case_root, rel) -> Path:
    """Return an existing contained directory for an unmodified relative string.

    This deliberately mirrors the file helper without calling or refactoring it:
    callers of ``safe_case_file`` retain its exact exception and existence
    semantics while directory-valued arguments receive the same lexical,
    symlink, and realpath containment checks.
    """
    if not isinstance(rel, str) or not rel or not rel.strip():
        raise ValueError(f"路径必须是案根内非空相对目录路径: {rel!r}")
    if os.path.isabs(rel):
        raise ValueError(f"路径不得是绝对路径: {rel!r}")
    parts = rel.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"路径含空段、. 或 .. 非法段: {rel!r}")

    root = Path(case_root)
    lexical = root
    try:
        for part in parts:
            lexical = lexical / part
            if lexical.is_symlink():
                raise ValueError(f"路径不得经过符号链接: {rel!r}")

        root_real = Path(os.path.realpath(root))
        target = Path(os.path.realpath(lexical))
        if os.path.commonpath((str(target), str(root_real))) != str(root_real):
            raise ValueError(f"路径越出案根: {rel!r}")
        if not target.exists():
            raise ValueError(f"目录不存在: {rel!r}")
        if not target.is_dir():
            raise ValueError(f"路径不是目录: {rel!r}")
        return target
    except ValueError:
        raise
    except (OSError, TypeError) as exc:
        raise ValueError(f"路径校验失败: {rel!r}: {exc}") from exc
