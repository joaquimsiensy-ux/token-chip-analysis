#!/usr/bin/env python3
"""F-14：现役 tracked 文本行尾空白守卫及三层反证自测。"""

from __future__ import annotations

import struct
import tempfile
from pathlib import Path, PurePosixPath


REPO = Path(__file__).resolve().parents[2]

# br104 裁决：证据字节保真优先，不为守卫清洗历史材料。
EXEMPT_PREFIXES = ("maintenance", "blind-reviews", "archive")
# br104 裁决：日志/文本/JSON 多为证据或机器产物，无现役渲染语义。
EXEMPT_SUFFIXES = (".log", ".txt", ".json")


class HygieneGuardError(RuntimeError):
    pass


def _git_dir(root: Path) -> Path:
    """Resolve the read-only worktree index without invoking any git command."""
    marker = root / ".git"
    if marker.is_dir():
        return marker.resolve()
    if marker.is_file():
        text = marker.read_text(encoding="utf-8").strip()
        if not text.startswith("gitdir: "):
            raise HygieneGuardError(f"无法解析 .git 指针: {marker}")
        raw = Path(text.removeprefix("gitdir: "))
        return (raw if raw.is_absolute() else marker.parent / raw).resolve()
    raise HygieneGuardError(f"找不到 tracked 文件索引: {marker}")


def tracked_paths_from_index(root: Path) -> list[PurePosixPath]:
    """Read Git index v2/v3 entries; this guard never shells out to git."""
    index = _git_dir(root) / "index"
    try:
        data = index.read_bytes()
    except OSError as exc:
        raise HygieneGuardError(f"tracked 文件索引不可读: {index}: {exc}") from exc
    if len(data) < 12 or data[:4] != b"DIRC":
        raise HygieneGuardError(f"tracked 文件索引头非法: {index}")
    version, count = struct.unpack(">II", data[4:12])
    if version not in {2, 3}:
        raise HygieneGuardError(f"不支持的 tracked 文件索引版本: {version}")
    offset = 12
    paths = []
    for entry_no in range(count):
        start = offset
        if offset + 62 > len(data) - 20:
            raise HygieneGuardError(f"tracked 文件索引截断于 entry {entry_no}")
        flags = struct.unpack(">H", data[offset + 60:offset + 62])[0]
        offset += 62
        if version == 3 and flags & 0x4000:
            if offset + 2 > len(data) - 20:
                raise HygieneGuardError(f"tracked 扩展 flags 截断于 entry {entry_no}")
            offset += 2
        end = data.find(b"\0", offset, len(data) - 20)
        if end < 0:
            raise HygieneGuardError(f"tracked 文件名未终止于 entry {entry_no}")
        raw_name = data[offset:end]
        try:
            name = raw_name.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HygieneGuardError(f"tracked 文件名非 UTF-8: entry {entry_no}") from exc
        paths.append(PurePosixPath(name))
        consumed = end + 1 - start
        offset = start + ((consumed + 7) // 8) * 8
    return paths


def is_exempt(rel: PurePosixPath) -> bool:
    return ((rel.parts and rel.parts[0] in EXEMPT_PREFIXES)
            or rel.suffix.lower() in EXEMPT_SUFFIXES)


def in_denominator(rel: PurePosixPath) -> bool:
    if rel.is_absolute() or ".." in rel.parts or is_exempt(rel):
        return False
    parts = rel.parts
    if len(parts) == 1 and rel.suffix.lower() == ".md":
        return True
    if len(parts) >= 2 and parts[0] == "references" \
            and rel.suffix.lower() == ".md":
        return True
    if len(parts) == 2 and parts[0] == "commands-staging" \
            and rel.suffix.lower() == ".md":
        return True
    if len(parts) >= 2 and parts[0] == "scripts" \
            and rel.suffix.lower() == ".py":
        return True
    return rel.suffix.lower() in {".sh", ".toml"}


def enumerate_denominator(root: Path, tracked_paths=None) -> list[PurePosixPath]:
    root = root.resolve()
    if not root.is_dir():
        raise HygieneGuardError(f"扫描根不存在或不是目录: {root}")
    candidates = (tracked_paths_from_index(root)
                  if tracked_paths is None else [PurePosixPath(p) for p in tracked_paths])
    denominator = sorted({path for path in candidates if in_denominator(path)},
                         key=str)
    if not denominator:
        raise HygieneGuardError("文本卫生分母为空，拒绝把零枚举伪装成零命中")
    return denominator


def trailing_whitespace_hits(root: Path, tracked_paths=None) -> tuple[list[PurePosixPath], list[str]]:
    root = root.resolve()
    denominator = enumerate_denominator(root, tracked_paths)
    hits = []
    for rel in denominator:
        path = root / rel
        if not path.is_file() or path.is_symlink():
            raise HygieneGuardError(f"tracked 分母文件不存在或为符号链接: {rel}")
        try:
            lines = path.read_bytes().splitlines()
        except OSError as exc:
            raise HygieneGuardError(f"分母文件不可读: {rel}: {exc}") from exc
        for line_no, line in enumerate(lines, 1):
            if line.endswith((b" ", b"\t")):
                hits.append(f"{rel.as_posix()}:{line_no}")
    return denominator, hits


def h1_injected_bad_examples() -> None:
    with tempfile.TemporaryDirectory(prefix="repair-g1-h1-") as td:
        root = Path(td)
        samples = {
            "references/trailing-space.md": b"bad space \n",
            "scripts/trailing-tab.py": b"bad tab\t\n",
            "guard.sh": b"ok\n \t\n",
        }
        for rel, payload in samples.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        _, hits = trailing_whitespace_hits(root, samples)
        expected = {
            "references/trailing-space.md:1",
            "scripts/trailing-tab.py:1",
            "guard.sh:2",
        }
        if set(hits) != expected:
            raise AssertionError(f"h1 坏例子未逐个检出: hits={hits!r}")


def h2_exempt_evidence_paths() -> None:
    with tempfile.TemporaryDirectory(prefix="repair-g1-h2-") as td:
        root = Path(td)
        samples = {
            "maintenance/evidence.md": b"preserve \n",
            "blind-reviews/review.md": b"preserve\t\n",
            "archive/history.md": b"preserve \n",
            "references/machine.json": b"{ } \n",
            "references/run.log": b"preserve \n",
            "references/note.txt": b"preserve\t\n",
            "references/live.md": b"clean\n",
        }
        for rel, payload in samples.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        denominator, hits = trailing_whitespace_hits(root, samples)
        if denominator != [PurePosixPath("references/live.md")] or hits:
            raise AssertionError(
                f"h2 豁免边界错误: denominator={denominator!r} hits={hits!r}")


def h3_empty_denominator_fails() -> None:
    missing = Path(tempfile.gettempdir()) / "repair-g1-h3-does-not-exist"
    try:
        enumerate_denominator(missing)
    except HygieneGuardError as exc:
        if "不存在" not in str(exc):
            raise AssertionError(f"h3 错误原因失真: {exc}") from exc
    else:
        raise AssertionError("h3 不存在目录被当成零命中 PASS")

    with tempfile.TemporaryDirectory(prefix="repair-g1-h3-empty-") as td:
        try:
            enumerate_denominator(Path(td), tracked_paths=[])
        except HygieneGuardError as exc:
            if "分母为空" not in str(exc):
                raise AssertionError(f"h3 空分母错误原因失真: {exc}") from exc
        else:
            raise AssertionError("h3 空 tracked 分母被当成零命中 PASS")


def main() -> int:
    h1_injected_bad_examples()
    print("PASS h1: 行尾空格、行尾 tab、全空白行逐个检出")
    h2_exempt_evidence_paths()
    print("PASS h2: br104 证据路径与 log/txt/json 后缀反向豁免")
    h3_empty_denominator_fails()
    print("PASS h3: 不存在扫描根与空分母均 fail-closed")
    denominator, hits = trailing_whitespace_hits(REPO)
    if hits:
        print(f"FAIL real repository: {len(hits)} trailing-whitespace hit(s)")
        for item in hits:
            print(f"- {item}")
        return 1
    print(f"PASS real repository: {len(denominator)} tracked active files, zero hits")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
