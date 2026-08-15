#!/usr/bin/env python3
"""环境一致性校验：pyproject 直接依赖、lock、installed 与 Python 三层守卫。

受检包集合只从 pyproject.toml ``[project].dependencies`` 机械派生。每个直接
依赖必须在 requirements.lock 恰有一个 pin，pin 必须满足 pyproject 下限，已装
版本必须严格等于 pin；解释器同时必须满足 ``requires-python``。lock 多出的传递
依赖合法，不要求安装版本逐项对账。

说明符刻意只接受当前仓库受控语法（单个 ``>=`` 加纯数字点分版本）；任何新语法
先扩守卫与回归测试，不允许静默跳过。库升级的正规流程见 pyproject.toml 头注。
"""
from __future__ import annotations

import re
import sys
from importlib import metadata
from pathlib import Path
from typing import Callable

import tomllib


ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = ROOT / "pyproject.toml"
LOCK = ROOT / "requirements.lock"

NAME_PATTERN = r"[A-Za-z0-9]+(?:[-_.][A-Za-z0-9]+)*"
DEPENDENCY_RE = re.compile(
    rf"^(?P<name>{NAME_PATTERN})>=(?P<version>[0-9]+(?:\.[0-9]+)*)$"
)
REQUIRES_PYTHON_RE = re.compile(r"^>=(?P<version>[0-9]+(?:\.[0-9]+)*)$")
LOCK_RE = re.compile(rf"^(?P<name>{NAME_PATTERN})==(?P<version>[^\s=]+)$")
NUMERIC_VERSION_RE = re.compile(r"^[0-9]+(?:\.[0-9]+)*$")


def normalize_name(name: str) -> str:
    """按 PEP 503 统一 pyproject、lock 与 installed 的名称键。"""
    return re.sub(r"[-_.]+", "-", name).lower()


def numeric_version(value: str) -> tuple[int, ...]:
    if not NUMERIC_VERSION_RE.fullmatch(value):
        raise ValueError(value)
    return tuple(int(part) for part in value.split("."))


def version_at_least(actual: tuple[int, ...], minimum: tuple[int, ...]) -> bool:
    width = max(len(actual), len(minimum))
    return actual + (0,) * (width - len(actual)) >= minimum + (0,) * (width - len(minimum))


def _parse_project(path: Path) -> tuple[dict[str, tuple[str, str]], str | None,
                                        list[str]]:
    failures: list[str] = []
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        return {}, None, [f"pyproject 无法读取或解析：{path}: {exc}"]

    project = data.get("project")
    if not isinstance(project, dict):
        return {}, None, ["pyproject 缺少 [project] 表"]

    raw_dependencies = project.get("dependencies")
    dependencies: dict[str, tuple[str, str]] = {}
    if not isinstance(raw_dependencies, list):
        failures.append("pyproject [project].dependencies 必须是数组")
    else:
        for raw in raw_dependencies:
            if not isinstance(raw, str):
                failures.append(f"说明符语法超出受控白名单：{raw!r}")
                continue
            match = DEPENDENCY_RE.fullmatch(raw)
            if match is None:
                failures.append(f"说明符语法超出受控白名单：{raw}")
                continue
            name = normalize_name(match.group("name"))
            if name in dependencies:
                failures.append(f"{name}: pyproject 直接依赖重复")
                continue
            dependencies[name] = (match.group("version"), raw)

    requires_python = project.get("requires-python")
    if not isinstance(requires_python, str):
        failures.append("pyproject requires-python 缺失或不是字符串")
        requires_python = None
    elif REQUIRES_PYTHON_RE.fullmatch(requires_python) is None:
        failures.append(
            f"requires-python 语法超出受控白名单：{requires_python}"
        )
    return dependencies, requires_python, failures


def _parse_lock(path: Path) -> tuple[dict[str, str], set[str], list[str]]:
    failures: list[str] = []
    pins: dict[str, str] = {}
    duplicates: set[str] = set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        return {}, set(), [f"requirements.lock 无法读取：{path}: {exc}"]

    for number, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = LOCK_RE.fullmatch(line)
        if match is None:
            failures.append(f"requirements.lock:{number}: 非受控 name==version 行：{line}")
            continue
        name = normalize_name(match.group("name"))
        if name in pins:
            duplicates.add(name)
            failures.append(f"{name}: lock 重复 pin（规范化后同名）")
            continue
        pins[name] = match.group("version")
    return pins, duplicates, failures


def check_environment(pyproject_path: Path, lock_path: Path,
                      version_lookup: Callable[[str], str],
                      python_version: tuple[int, ...] | None = None) -> list[str]:
    """返回全部环境断层；不写文件，不因未知语法静默跳过。"""
    dependencies, requires_python, failures = _parse_project(pyproject_path)
    pins, duplicate_pins, lock_failures = _parse_lock(lock_path)
    failures.extend(lock_failures)

    actual_python = tuple(sys.version_info[:3]) if python_version is None else tuple(python_version)
    if requires_python is not None:
        match = REQUIRES_PYTHON_RE.fullmatch(requires_python)
        if match is not None:
            minimum_python = numeric_version(match.group("version"))
            if not version_at_least(actual_python, minimum_python):
                actual_text = ".".join(str(part) for part in actual_python)
                failures.append(
                    f"Python {actual_text} 不满足 requires-python {requires_python}"
                )

    for name, (minimum_text, declaration) in dependencies.items():
        if name in duplicate_pins:
            continue
        pin = pins.get(name)
        if pin is None:
            failures.append(f"{name}: lock 里没有（pyproject 直接依赖 {declaration}）")
            continue
        try:
            pin_version = numeric_version(pin)
        except ValueError:
            failures.append(f"{name}: lock pin 版本语法超出受控白名单：{pin}")
        else:
            minimum_version = numeric_version(minimum_text)
            if not version_at_least(pin_version, minimum_version):
                failures.append(
                    f"{name}: lock {pin} 不满足 pyproject >={minimum_text}"
                )
        try:
            installed = version_lookup(name)
        except metadata.PackageNotFoundError:
            failures.append(f"{name}: 未安装（lock 要求 {pin}）")
            continue
        except Exception as exc:  # metadata 后端异常也必须 fail-closed
            failures.append(f"{name}: installed 版本查询失败：{type(exc).__name__}: {exc}")
            continue
        if installed != pin:
            failures.append(f"{name}: 已装 {installed} ≠ lock {pin}")
    return failures


def main() -> int:
    failures = check_environment(PYPROJECT, LOCK, metadata.version)
    if failures:
        for failure in failures:
            print(f"- {failure}")
        print("FAIL: pyproject、requirements.lock、installed 或 Python 环境不一致")
        return 1

    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]
    dependency_count = len(project["dependencies"])
    python_text = ".".join(str(part) for part in sys.version_info[:3])
    print(
        f"PASS: {dependency_count} 个直接依赖逐项满足 pyproject→lock→installed；"
        f"Python {python_text} 满足 requires-python {project['requires-python']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
