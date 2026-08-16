#!/usr/bin/env python3
"""批3工单 F04/F05/F07：部署同步、环境覆盖与 R10 台账回归。"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import pwd
import re
import subprocess
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
FAILS: list[str] = []
COMMANDS = ("token-analyze-1.md", "token-analyze-2.md", "token-analyze.md")
R10_LEDGER = REPO / "maintenance" / "repair-20260813-sixlens" / "r10_ledger.md"
R10_ROW_CANDIDATE_RE = re.compile(r"^\|[ \t　]*R10-")
R10_ROW_RE = re.compile(r"^\|[ \t]*(R10-(\d+))(?:（[^|\n]+）)?[ \t]*\|")
R10_STATUS_RE = re.compile(
    r"【(?:CLOSED \d+\.\d+\.\d+|FIXED_PENDING_REVIEW \d+\.\d+\.\d+ 批\d+)】"
)
R10_STATUS_CARRIER_RE = re.compile(r"【[^】]*】")
R10_STATUSISH_RE = re.compile(
    r"【[ \t　]*(?:CLOSED|FIXED_PENDING_REVIEW)\b[^】]*】"
)
R10_BARE_STATUS_RE = re.compile(
    r"(?<!【)(?<![A-Za-z_])(?:CLOSED[ \t　]+\d+\.\d+\.\d+|"
    r"FIXED_PENDING_REVIEW[ \t　]+\d+\.\d+\.\d+"
    r"(?:[ \t　]+批\d+)?)"
)
ACTIVE_DECLARATION_RE = re.compile(
    r"当前现役[ \t]*=.*?=[ \t]*\*\*(\d+)\*\*"
)
R10_SECTION_LAYOUTS = {
    "## 一、": {"cell_count": 6, "status_cell_index": 2},
    "## 二、": {"cell_count": 5, "status_cell_index": 2},
    "## 三、": {"cell_count": 5, "status_cell_index": 2},
    "## 四、": {"cell_count": 5, "status_cell_index": 2},
    "## 四b、": {"cell_count": 5, "status_cell_index": 2},
    "## 五、": {"cell_count": 5, "status_cell_index": 3},
}
R10_TABLE_HEADER_RE = re.compile(r"^\|[ \t]*#[ \t]*\|")
R10_TABLE_SEPARATOR_RE = re.compile(r"^\|[ \t]*---")


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
        "token-analyze-2.md": "a4-seal/v4 a5-report-seal/v3 G11 只支持 full\n",
        "token-analyze.md": "full command\n",
    }
    for name, content in contents.items():
        (staging / name).write_text(content, encoding="utf-8")
        (deployed / name).write_text(content, encoding="utf-8")
    manifest = root / "scripts/tests/contract_manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({
        "schema": "contract-manifest/v2",
        "contracts": [
            {"id": "CT-TEST-REQUIRED-01", "kind": "required",
             "authority_file": "commands-staging/token-analyze-2.md",
             "needle": "a5-report-seal/v3", "stages": ["A3-A5"]},
            {"id": "CT-TEST-BANNED-01", "kind": "banned",
             "authority_file": "commands-staging/token-analyze-2.md",
             "needle": "A5 seal v2", "stages": ["A3-A5"]},
        ],
    }), encoding="utf-8")


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

        # F-11 主变异：双侧字节完全相同但都回退旧语义，SHA 层为绿、语义层必须红。
        old_text = "a4-seal/v4 A5 seal v2 G11 只支持 full\n"
        for side in (root / "commands-staging", deployed):
            (side / "token-analyze-2.md").write_text(old_text, encoding="utf-8")
        failures, _, _ = deploy_failures(root, deployed, base / "home")
        check("F11 双侧同旧文本 SHA 相等仍被语义层拒绝",
              not any("SHA-256 不一致" in item for item in failures)
              and any("required needle 缺失" in item for item in failures)
              and any("banned needle 回捡" in item for item in failures), failures)
        clean_text = "a4-seal/v4 a5-report-seal/v3 G11 只支持 full\n"
        for side in (root / "commands-staging", deployed):
            (side / "token-analyze-2.md").write_text(clean_text, encoding="utf-8")

        # 同族变体：deployed 单侧回捡 banned，SHA 与语义两层都不得被豁免。
        (deployed / "token-analyze-2.md").write_text(old_text, encoding="utf-8")
        failures, _, _ = deploy_failures(root, deployed, base / "home")
        check("F11 deployed banned 与 SHA 双层同时拒绝",
              any("SHA-256 不一致" in item for item in failures)
              and any("banned needle 回捡" in item and "deployed" in item
                      for item in failures), failures)
        (deployed / "token-analyze-2.md").write_text(clean_text, encoding="utf-8")

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
        check("F04 manifest 缺失不得借非 canonical SKIP",
              rc == 1 and "契约注册表" in output
              and "SKIP_NON_CANONICAL_CHECKOUT:" not in output, (rc, output))

        home = base / "canonical-home"
        canonical = home / ".claude" / "skills" / "token-chip-analysis"
        canonical.mkdir(parents=True)
        seed_commands(canonical, base / "unused-deployed")
        canonical_predicate = getattr(DEPLOY, "is_canonical_checkout", None)
        check("F04 canonical 精确判定纯函数可参数化",
              callable(canonical_predicate)
              and canonical_predicate(canonical, home)
              and not canonical_predicate(root, home))
        rc, output = invoke_deploy_main(canonical, missing, home)
        check("F04 canonical 部署机缺部署目录 FAIL rc1",
              rc == 1 and "FAIL:" in output and str(missing) in output, (rc, output))

    with tempfile.TemporaryDirectory(prefix="batch3-f04-shadow-home-") as fake_home:
        account_home = Path(pwd.getpwuid(os.getuid()).pw_dir)
        deployed = account_home / ".claude" / "commands"
        expected_failures = DEPLOY.check_deploy_sync(REPO, deployed)
        env = os.environ.copy()
        env["HOME"] = fake_home
        proc = subprocess.run(
            [sys.executable, str(HERE / "test_commands_deploy_sync.py")],
            cwd=REPO, env=env, capture_output=True, text=True, check=False)
        expected_rc = 1 if expected_failures else 0
        check("F04 真实 canonical checkout 不受伪 HOME 改写",
              "SKIP_NON_CANONICAL_CHECKOUT" not in proc.stdout
              and proc.returncode == expected_rc,
              (proc.returncode, expected_rc, proc.stdout, proc.stderr))


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


def r10_ledger_failures(path: Path) -> list[str]:
    """机械核对 R10 条目唯一性、状态枚举和第六节现役数。"""
    text = path.read_text(encoding="utf-8")
    failures: list[str] = []
    entries: list[tuple[str, str]] = []
    section = ""
    layout = None
    for lineno, line in enumerate(text.splitlines(), start=1):
        if line.startswith("## "):
            section = line
            layout = next(
                (item for prefix, item in R10_SECTION_LAYOUTS.items()
                 if section.startswith(prefix)),
                None,
            )
        if layout is not None and (
                R10_TABLE_HEADER_RE.match(line)
                or R10_TABLE_SEPARATOR_RE.match(line)):
            if (not line.endswith("|")
                    or len(line.split("|")) != layout["cell_count"]):
                failures.append(
                    f"第 {lineno} 行表头/分隔行列数与所在节表结构不符")
            continue
        if R10_ROW_CANDIDATE_RE.match(line) is None:
            continue
        match = R10_ROW_RE.match(line)
        if match is None:
            failures.append(f"第 {lineno} 行 R10 条目格式无法识别")
            continue
        entry_id = match.group(1)
        cells = line.split("|")
        if r"\|" in line:
            failures.append(f"{entry_id} cell 内竖线不受支持")
        if layout is None:
            failures.append(f"{entry_id} 所在节无受控表结构")
            entries.append((entry_id, "OPEN"))
            continue
        expected_cell_count = layout["cell_count"]
        status_cell_index = layout["status_cell_index"]
        carriers_by_cell = [
            (index, carrier)
            for index, cell in enumerate(cells)
            for carrier in R10_STATUS_CARRIER_RE.findall(cell)
        ]
        carrier_open = False
        carrier_brackets_malformed = False
        for character in line:
            if character == "【":
                if carrier_open:
                    carrier_brackets_malformed = True
                carrier_open = True
            elif character == "】":
                if not carrier_open:
                    carrier_brackets_malformed = True
                carrier_open = False
        if carrier_open or carrier_brackets_malformed:
            failures.append(f"{entry_id} 状态载体括号不配对")
        for _, carrier in carriers_by_cell:
            if R10_STATUS_RE.fullmatch(carrier) is None:
                failures.append(
                    f"{entry_id} 状态载体无法识别为枚举：{carrier!r}")
        statusish_by_cell = [
            (index, marker)
            for index, cell in enumerate(cells)
            for marker in R10_STATUSISH_RE.findall(cell)
        ]
        body_statusish = [
            marker for index, marker in statusish_by_cell
            if index != status_cell_index
        ]
        if body_statusish:
            failures.append(
                f"{entry_id} 正文列出现状态样式标记：{body_statusish}")
        if (not line.startswith("|") or not line.endswith("|")
                or len(cells) != expected_cell_count):
            failures.append(f"{entry_id} 列数与所在节表结构不符")
            bare_markers = R10_BARE_STATUS_RE.findall(line)
            if bare_markers:
                failures.append(
                    f"{entry_id} 状态字样未按枚举格式：{bare_markers}")
            entries.append((entry_id, "OPEN"))
            continue
        status_cell = cells[status_cell_index]
        status_markers = [
            carrier for index, carrier in carriers_by_cell
            if index == status_cell_index
            and R10_STATUS_RE.fullmatch(carrier) is not None
        ]
        statusish = R10_STATUSISH_RE.findall(status_cell)
        if len(status_markers) > 1:
            failures.append(f"{entry_id} 状态标记不唯一：{status_markers}")
        elif statusish != status_markers:
            failures.append(f"{entry_id} 状态标记不属于枚举：{statusish}")
        bare_markers = R10_BARE_STATUS_RE.findall(line)
        if bare_markers:
            failures.append(
                f"{entry_id} 状态字样未按枚举格式：{bare_markers}")
        status = status_markers[0] if status_markers else "OPEN"
        entries.append((entry_id, status))

    ids = [entry_id for entry_id, _ in entries]
    duplicate_ids = sorted({entry_id for entry_id in ids if ids.count(entry_id) > 1})
    if duplicate_ids:
        failures.append(f"R10 条目 ID 重复：{duplicate_ids}")
    expected_ids = {f"R10-{number}" for number in range(1, 28)}
    actual_ids = set(ids)
    if actual_ids != expected_ids:
        failures.append(
            f"R10 条目集合不完整：缺失={sorted(expected_ids - actual_ids)}，"
            f"多出={sorted(actual_ids - expected_ids)}"
        )

    declared_active = [int(match.group(1))
                       for match in ACTIVE_DECLARATION_RE.finditer(text)]
    if len(declared_active) != 1:
        failures.append(f"第六节当前现役声明必须恰好一条：实际 {len(declared_active)} 条")
    else:
        closed_count = sum(status.startswith("【CLOSED ") for _, status in entries)
        computed_active = len(entries) - closed_count
        if declared_active[-1] != computed_active:
            failures.append(
                f"当前现役数不一致：台账声明 {declared_active[-1]}，"
                f"机械计算 {computed_active}"
            )
    return failures


def t_f07_r10_ledger() -> None:
    real_failures = r10_ledger_failures(R10_LEDGER)
    check("F07 真实 R10 台账自洽 PASS", real_failures == [], real_failures)

    source = R10_LEDGER.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="batch3-f07-") as td:
        root = Path(td)

        duplicate_copy = root / "r10_ledger_duplicate.md"
        duplicate_text, replacements = re.subn(
            r"^\| R10-27 ", "| R10-1 ", source, count=1, flags=re.MULTILINE
        )
        check("F07 重复 ID 反例成功注入", replacements == 1)
        duplicate_copy.write_text(duplicate_text, encoding="utf-8")
        duplicate_failures = r10_ledger_failures(duplicate_copy)
        check("F07 重复 ID 反例 FAIL",
              any("ID 重复" in item for item in duplicate_failures),
              duplicate_failures)

        count_copy = root / "r10_ledger_bad_count.md"
        matches = list(ACTIVE_DECLARATION_RE.finditer(source))
        declared = int(matches[-1].group(1)) if matches else -1
        count_text = (
            source[:matches[-1].start(1)] + str(declared + 1)
            + source[matches[-1].end(1):]
            if matches else source
        )
        check("F07 计数不一致反例成功注入", declared >= 0)
        count_copy.write_text(count_text, encoding="utf-8")
        count_failures = r10_ledger_failures(count_copy)
        check("F07 计数不一致反例 FAIL",
              any("当前现役数不一致" in item for item in count_failures),
              count_failures)

        body_copy = root / "r10_ledger_body_marker.md"
        body_text = source.replace(
            "建议把字段名改为不承载",
            "代码示例 `【CLOSED 9.9.9】`，不是状态；建议把字段名改为不承载",
            1,
        ).replace("当前现役 = 23 − 4 = **19**", "当前现役 = 23 − 4 = **18**", 1)
        body_copy.write_text(body_text, encoding="utf-8")
        body_failures = r10_ledger_failures(body_copy)
        check("F07 正文列状态样式标记不得冒充条目状态",
              any("正文列出现状态样式标记" in item for item in body_failures),
              body_failures)

        bare_copy = root / "r10_ledger_bare_status.md"
        bare_text = source.replace("【CLOSED 6.41.0】", "CLOSED 6.41.0", 1).replace(
            "当前现役 = 23 − 4 = **19**", "当前现役 = 23 − 4 = **20**", 1)
        bare_copy.write_text(bare_text, encoding="utf-8")
        bare_failures = r10_ledger_failures(bare_copy)
        check("F07 裸 CLOSED/FIXED_PENDING_REVIEW 版本状态 fail-closed",
              any("状态字样未按枚举格式" in item for item in bare_failures),
              bare_failures)

        duplicate_active_copy = root / "r10_ledger_duplicate_active.md"
        duplicate_active_copy.write_text(
            source + "\n- 当前现役 = 重复伪造 = **18**\n", encoding="utf-8")
        duplicate_active_failures = r10_ledger_failures(duplicate_active_copy)
        check("F07 当前现役声明重复即 FAIL",
              any("当前现役声明必须恰好一条" in item
                  for item in duplicate_active_failures),
              duplicate_active_failures)

        combined_copy = root / "r10_ledger_pipe_fullwidth_combo.md"
        combined_text = source.replace(
            "图 1 对未知阵营静默漏画【CLOSED 6.41.0】",
            "图 1 对未知阵营静默漏画 | 【CLOSED　6.41.0】",
            1,
        ).replace(
            "当前现役 = 23 − 4 = **19**",
            "当前现役 = 23 − 4 = **20**",
            1,
        )
        combined_copy.write_text(combined_text, encoding="utf-8")
        combined_failures = r10_ledger_failures(combined_copy)
        check("F07 BR2-02 竖线推列＋全角状态组合必须 FAIL",
              any("列数与所在节表结构不符" in item
                  for item in combined_failures), combined_failures)

        escaped_pipe_copy = root / "r10_ledger_escaped_pipe.md"
        escaped_pipe_copy.write_text(source.replace(
            "F-12 改名降权（GPT-F-10 修法）",
            r"F-12 改名降权\|（GPT-F-10 修法）",
            1,
        ), encoding="utf-8")
        escaped_pipe_failures = r10_ledger_failures(escaped_pipe_copy)
        check("F07 cell 内转义竖线不受支持必须 FAIL",
              any("cell 内竖线" in item for item in escaped_pipe_failures),
              escaped_pipe_failures)

        fullwidth_structure_copy = root / "r10_ledger_fullwidth_structure.md"
        fullwidth_structure_copy.write_text(
            source.replace("| R10-1 |", "|　R10-1　|", 1), encoding="utf-8")
        fullwidth_structure_failures = r10_ledger_failures(fullwidth_structure_copy)
        check("F07 ID cell 结构位全角空格必须 fail-closed",
              any("条目格式无法识别" in item
                  for item in fullwidth_structure_failures),
              fullwidth_structure_failures)

        raw_body_pipe_copy = root / "r10_ledger_raw_body_pipe.md"
        raw_body_pipe_copy.write_text(source.replace(
            "消除\"名字看起来像证明\"的误导面",
            "消除\"名字看起来像证明\" | 的误导面",
            1,
        ), encoding="utf-8")
        raw_body_pipe_failures = r10_ledger_failures(raw_body_pipe_copy)
        check("F07 正文格原始竖线改变列数必须 FAIL",
              any("列数与所在节表结构不符" in item
                  for item in raw_body_pipe_failures), raw_body_pipe_failures)

        body_statusish_copy = root / "r10_ledger_body_statusish.md"
        body_statusish_copy.write_text(source.replace(
            "消除\"名字看起来像证明\"的误导面",
            "消除\"名字看起来像证明\"的误导面【CLOSED　6.41.0】",
            1,
        ), encoding="utf-8")
        body_statusish_failures = r10_ledger_failures(body_statusish_copy)
        check("F07 所有非状态列扫描宽松 statusish 变体",
              any("正文列出现状态样式标记" in item
                  for item in body_statusish_failures), body_statusish_failures)

        carrier_cases = {
            "零宽字符插词": "【CLO\u200bSED 6.41.0】",
            "未知状态关键字": "【CLOSED_PENDING 6.41.0】",
            "HTML 实体": "【CLO&#83;ED 6.41.0】",
        }
        for case_name, carrier in carrier_cases.items():
            carrier_copy = root / f"r10_ledger_bad_carrier_{case_name}.md"
            carrier_text = source.replace(
                "【CLOSED 6.41.0】", carrier, 1,
            ).replace(
                "当前现役 = 23 − 4 = **19**",
                "当前现役 = 23 − 4 = **20**",
                1,
            )
            carrier_copy.write_text(carrier_text, encoding="utf-8")
            carrier_failures = r10_ledger_failures(carrier_copy)
            check(f"F07 BR3-01 {case_name}状态载体必须 FAIL",
                  any("状态载体无法识别为枚举" in item
                      for item in carrier_failures), carrier_failures)

        unclosed_copy = root / "r10_ledger_unclosed_carrier.md"
        unclosed_text = source.replace(
            "【CLOSED 6.41.0】", "【CLOSED 6.41.0", 1,
        ).replace(
            "当前现役 = 23 − 4 = **19**",
            "当前现役 = 23 − 4 = **20**",
            1,
        )
        unclosed_copy.write_text(unclosed_text, encoding="utf-8")
        unclosed_failures = r10_ledger_failures(unclosed_copy)
        check("F07 BR3-01 未闭合状态载体括号必须 FAIL",
              any("状态载体括号不配对" in item
                  for item in unclosed_failures), unclosed_failures)

        nested_copy = root / "r10_ledger_nested_carrier.md"
        nested_copy.write_text(source.replace(
            "【CLOSED 6.41.0】", "【CLO【SED 6.41.0】】", 1,
        ), encoding="utf-8")
        nested_failures = r10_ledger_failures(nested_copy)
        check("F07 BR3-01 嵌套状态载体括号必须 FAIL",
              any("状态载体括号不配对" in item
                  for item in nested_failures), nested_failures)


def main() -> int:
    t_f04_deploy_sync()
    t_f05_env_check()
    t_f07_r10_ledger()
    if FAILS:
        print(f"FAIL: {len(FAILS)} 项批3 gates 回归失败：{FAILS}")
        return 1
    print("PASS: 批3 deploy-sync/env-check/R10-ledger gates 回归全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
