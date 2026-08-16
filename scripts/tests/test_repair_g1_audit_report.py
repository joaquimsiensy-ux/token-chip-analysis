#!/usr/bin/env python3
"""AI-1 F-02：independent-audit 缺报告实物必须 fail-closed。"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
GATE_PATH = ROOT / "scripts/report/audit_release_gate.py"
FIXTURE_PATH = HERE / "test_audit_release_gate.py"
FAILURES: list[str] = []

sys.path.insert(0, str(HERE))
from formal_ready_test_harness import test_vertical_slices  # noqa: E402


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载测试模块：{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fixture = load_module("repair_g1_audit_fixture", FIXTURE_PATH)
gate = load_module("repair_g1_audit_gate", GATE_PATH)
_gate_run = gate.run


def run_gate(*args, **kwargs):
    with test_vertical_slices():
        return _gate_run(*args, **kwargs)


def check(name: str, condition: bool, detail="") -> None:
    if condition:
        print(f"ok    {name}")
    else:
        print(f"FAIL  {name}  {detail}")
        FAILURES.append(name)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="repair-g1-f02-") as td:
        case = Path(td)
        report = fixture.build_case(case)
        registry_path = case / "claim_registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["report_sha256"] = "0" * 64
        registry_path.write_text(
            json.dumps(registry, ensure_ascii=False), encoding="utf-8")

        errors = run_gate(case, None, profile="independent-audit")
        check(
            "F-02 白盒：independent-audit 缺 report 必须 BLOCK",
            bool(errors),
            errors,
        )

        proc = subprocess.run(
            [sys.executable, str(GATE_PATH), str(case)],
            capture_output=True,
            text=True,
            check=False,
        )
        check(
            "F-02 CLI：省略 --report 必须 rc=2 且不得打印 PASS",
            proc.returncode == 2 and "PASS" not in proc.stdout,
            (proc.returncode, proc.stdout, proc.stderr),
        )

        mismatch = run_gate(case, report, profile="independent-audit")
        check(
            "F-02 防退化：传 report 且 sha 不符继续 BLOCK",
            any("report_sha256" in item and "不一致" in item for item in mismatch),
            mismatch,
        )

        (case / "a5_report_seal.json").write_text("{}\n", encoding="utf-8")
        new_analysis = run_gate(case, None, profile="new-analysis")
        check(
            "F-02 防误伤：new-analysis None 保留自有 fail-closed 文案",
            any("new-analysis 发布必须带 --report" in item for item in new_analysis),
            new_analysis,
        )

    if FAILURES:
        print(f"FAIL: F-02 共 {len(FAILURES)} 项未满足")
        return 1
    print("PASS: F-02 independent-audit --report fail-closed 四件套")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
