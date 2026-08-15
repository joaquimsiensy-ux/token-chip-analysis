#!/usr/bin/env python3
"""批3工单 F04/F05：部署同步与环境覆盖回归。"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import re
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
FAILS: list[str] = []
COMMANDS = ("token-analyze-1.md", "token-analyze-2.md", "token-analyze.md")


def check(name: str, condition: bool, detail="") -> None:
    if condition:
        print(f"ok    {name}")
    else:
        print(f"FAIL  {name}  {detail}")
        FAILS.append(name)


def load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载测试目标：{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DEPLOY = load_script("batch3_commands_deploy_sync", HERE / "test_commands_deploy_sync.py")
ENV = load_script("batch3_env_check", HERE / "env_check.py")
LEGACY_KEY_PKGS = (
    "duckdb", "pyarrow", "pandas", "numpy", "hypersync", "requests",
    "networkx", "rustworkx", "hypothesis", "psutil", "matplotlib",
    "httpx", "tenacity", "msgspec",
)


def seed_commands(root: Path, deployed: Path) -> None:
    staging = root / "commands-staging"
    staging.mkdir(parents=True)
    deployed.mkdir(parents=True)
    contents = {
        "token-analyze-1.md": "distribution_scan.json handoff/v3\n",
        "token-analyze-2.md": "a4-seal/v4 G11 只支持 full\n",
        "token-analyze.md": "full command\n",
    }
    for name, content in contents.items():
        (staging / name).write_text(content, encoding="utf-8")
        (deployed / name).write_text(content, encoding="utf-8")


def invoke_deploy_main(root: Path, deployed: Path, home: Path) -> tuple[int, str]:
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        try:
            rc = DEPLOY.main(root=root, deployed=deployed, home=home)
        except TypeError:
            original = DEPLOY.ROOT, DEPLOY.STAGING, DEPLOY.DEPLOYED
            DEPLOY.ROOT = root
            DEPLOY.STAGING = root / "commands-staging"
            DEPLOY.DEPLOYED = deployed
            try:
                rc = DEPLOY.main()
            finally:
                DEPLOY.ROOT, DEPLOY.STAGING, DEPLOY.DEPLOYED = original
    return rc, stream.getvalue()


def deploy_failures(root: Path, deployed: Path, home: Path) -> tuple[list[str], int, str]:
    if hasattr(DEPLOY, "check_deploy_sync"):
        failures = DEPLOY.check_deploy_sync(root, deployed)
        rc, output = invoke_deploy_main(root, deployed, home)
        return failures, rc, output
    rc, output = invoke_deploy_main(root, deployed, home)
    return ([] if rc == 0 else [output]), rc, output


def t_f04_deploy_sync() -> None:
    with tempfile.TemporaryDirectory(prefix="batch3-f04-") as td:
        base = Path(td)
        root = base / "checkout"
        deployed = base / "deployed"
        seed_commands(root, deployed)

        failures, rc, output = deploy_failures(root, deployed, base / "home")
        check("F04 三文件逐字节一致 PASS", failures == [] and rc == 0,
              (failures, rc, output))

        (deployed / "token-analyze.md").unlink()
        failures, _, _ = deploy_failures(root, deployed, base / "home")
        check("F04 deployed 缺一文件 FAIL",
              any("部署版缺失" in item and "token-analyze.md" in item for item in failures),
              failures)
        (deployed / "token-analyze.md").write_text("full command\n", encoding="utf-8")

        (deployed / "token-analyze.md").write_text("full commane\n", encoding="utf-8")
        failures, _, _ = deploy_failures(root, deployed, base / "home")
        check("F04 普通命令改一字节 FAIL",
              any("SHA-256 不一致" in item and "token-analyze.md" in item
                  for item in failures), failures)
        (deployed / "token-analyze.md").write_text("full command\n", encoding="utf-8")

        (deployed / "token-analyze-1.md").write_bytes(b"STALE")
        failures, rc, output = deploy_failures(root, deployed, base / "home")
        check("F04 原迁移豁免文件陈旧字节也必须 FAIL",
              any("SHA-256 不一致" in item and "token-analyze-1.md" in item
                  for item in failures), (failures, rc, output))

    with tempfile.TemporaryDirectory(prefix="batch3-f04-missing-") as td:
        base = Path(td)
        root = base / "checkout"
        (root / "commands-staging").mkdir(parents=True)
        missing = base / "missing-commands"
        rc, output = invoke_deploy_main(root, missing, base / "home")
        check("F04 非 canonical checkout 缺部署目录明确 SKIP rc0",
              rc == 0 and "SKIP_NON_CANONICAL_CHECKOUT:" in output, (rc, output))

        home = base / "canonical-home"
        canonical = home / ".claude" / "skills" / "token-chip-analysis"
        canonical.mkdir(parents=True)
        canonical_predicate = getattr(DEPLOY, "is_canonical_checkout", None)
        check("F04 canonical 精确判定纯函数可参数化",
              callable(canonical_predicate)
              and canonical_predicate(canonical, home)
              and not canonical_predicate(root, home))
        rc, output = invoke_deploy_main(canonical, missing, home)
        check("F04 canonical 部署机缺部署目录 FAIL rc1",
              rc == 1 and "FAIL:" in output and str(missing) in output, (rc, output))


def normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def make_env_case(root: Path, dependencies: list[str], *,
                  requires_python: str = ">=3.14",
                  pins: dict[str, str] | None = None,
                  extra_lock_lines: tuple[str, ...] = ()) -> tuple[Path, Path, dict[str, str]]:
    pyproject = root / "pyproject.toml"
    lock = root / "requirements.lock"
    dep_text = ",\n    ".join(json.dumps(item, ensure_ascii=False) for item in dependencies)
    pyproject.write_text(
        "[project]\n"
        f"requires-python = {json.dumps(requires_python)}\n"
        "dependencies = [\n"
        f"    {dep_text}\n"
        "]\n",
        encoding="utf-8",
    )
    merged_pins = {name: "1.0" for name in LEGACY_KEY_PKGS}
    if pins:
        for name, version in pins.items():
            for existing in tuple(merged_pins):
                if normalize_name(existing) == normalize_name(name):
                    del merged_pins[existing]
            merged_pins[name] = version
    lines = [f"{name}=={version}" for name, version in merged_pins.items()]
    lines.extend(extra_lock_lines)
    lock.write_text("\n".join(lines) + "\n", encoding="utf-8")
    installed = {normalize_name(name): version for name, version in merged_pins.items()}
    return pyproject, lock, installed


def invoke_env_check(pyproject: Path, lock: Path, installed: dict[str, str],
                     python_version: tuple[int, ...] = (3, 14, 6)) -> tuple[list[str], int, str]:
    def lookup(name: str) -> str:
        normalized = normalize_name(name)
        if normalized not in installed:
            raise ENV.metadata.PackageNotFoundError(name)
        return installed[normalized]

    checker = getattr(ENV, "check_environment", None)
    if callable(checker):
        failures = checker(pyproject, lock, lookup, python_version)
        return failures, 0 if not failures else 1, "\n".join(failures)

    original_lock = ENV.LOCK
    original_version = ENV.metadata.version
    ENV.LOCK = str(lock)
    ENV.metadata.version = lookup
    stream = io.StringIO()
    try:
        with contextlib.redirect_stdout(stream):
            rc = ENV.main()
    finally:
        ENV.LOCK = original_lock
        ENV.metadata.version = original_version
    output = stream.getvalue()
    return ([] if rc == 0 else [output]), rc, output


def t_f05_env_check() -> None:
    with tempfile.TemporaryDirectory(prefix="batch3-f05-") as td:
        root = Path(td)

        pyproject, lock, installed = make_env_case(root, ["fakepkg>=1.0"])
        failures, rc, output = invoke_env_check(pyproject, lock, installed)
        check("F05 pyproject 直接依赖漏 lock FAIL",
              rc == 1 and any("fakepkg" in item and "lock 里没有" in item
                              for item in failures), (failures, output))

        pyproject, lock, installed = make_env_case(
            root, ["duckdb>=1.0"], pins={"duckdb": "1.0"})
        installed["duckdb"] = "1.1"
        failures, rc, output = invoke_env_check(pyproject, lock, installed)
        check("F05 installed 与 lock 漂移 FAIL",
              rc == 1 and any("duckdb" in item and "已装 1.1" in item
                              and "lock 1.0" in item for item in failures),
              (failures, output))

        pyproject, lock, installed = make_env_case(
            root, ["duckdb>=2.0"], pins={"duckdb": "1.0"})
        failures, rc, output = invoke_env_check(pyproject, lock, installed)
        check("F05 lock pin 低于 pyproject 下限 FAIL",
              rc == 1 and any("duckdb" in item and "不满足" in item
                              and ">=2.0" in item for item in failures),
              (failures, output))

        pyproject, lock, installed = make_env_case(
            root, ["x>=1.0"], pins={"X": "1.0"}, extra_lock_lines=("x==2.0",))
        failures, rc, output = invoke_env_check(pyproject, lock, installed)
        check("F05 PEP503 规范化后重复 lock 行 FAIL",
              rc == 1 and any("x" in item and "lock 重复" in item for item in failures),
              (failures, output))

        invalid_specs = (
            "pkg~=1.0",
            "pkg[extra]>=1.0",
            'pkg>=1.0; python_version<"4"',
        )
        for dependency in invalid_specs:
            pyproject, lock, installed = make_env_case(
                root, [dependency], pins={"pkg": "1.0"})
            failures, rc, output = invoke_env_check(pyproject, lock, installed)
            check(f"F05 非白名单说明符拒绝：{dependency}",
                  rc == 1 and any("说明符语法超出受控白名单" in item
                                  for item in failures), (failures, output))

        pyproject, lock, installed = make_env_case(
            root, ["PyMuPDF>=1.27.2"], pins={"pymupdf": "1.27.2.3"})
        failures, rc, output = invoke_env_check(pyproject, lock, installed)
        check("F05 PEP503 名称规范化与右补零版本比较 PASS",
              failures == [] and rc == 0, (failures, output))

        pyproject, lock, installed = make_env_case(
            root, ["x>=1.0"], pins={"x": "1.0", "transitive-only": "9.0"})
        failures, rc, output = invoke_env_check(pyproject, lock, installed)
        check("F05 lock 多出传递依赖不影响 PASS",
              failures == [] and rc == 0, (failures, output))

        pyproject, lock, installed = make_env_case(
            root, ["duckdb>=1.0"], pins={"duckdb": "1.0"})
        failures, rc, output = invoke_env_check(
            pyproject, lock, installed, python_version=(3, 13, 0))
        check("F05 低版本 Python FAIL",
              rc == 1 and any("Python 3.13.0" in item and "requires-python >=3.14" in item
                              for item in failures), (failures, output))

        pyproject, lock, installed = make_env_case(
            root, ["duckdb>=1.0"], requires_python="~=3.14", pins={"duckdb": "1.0"})
        failures, rc, output = invoke_env_check(pyproject, lock, installed)
        check("F05 非白名单 requires-python FAIL",
              rc == 1 and any("requires-python 语法超出受控白名单" in item
                              for item in failures), (failures, output))


def main() -> int:
    t_f04_deploy_sync()
    t_f05_env_check()
    if FAILS:
        print(f"FAIL: {len(FAILS)} 项批3 gates 回归失败：{FAILS}")
        return 1
    print("PASS: 批3 deploy-sync/env-check gates 回归全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
