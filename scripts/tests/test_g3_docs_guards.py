#!/usr/bin/env python3
"""Guard the G3 documentation consistency and machine-boundary statements."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ANALYZE = ROOT / "references" / "analyze-workflow.md"
RESEARCH = ROOT / "references" / "research-workflows.md"


def section(text, marker):
    """Return marker through the next level-two Markdown heading."""
    start = text.index(marker)
    end = text.find("\n## ", start)
    return text[start:] if end == -1 else text[start:end]


def paragraph(text, marker):
    """Return the non-empty Markdown paragraph containing marker."""
    for candidate in text.split("\n\n"):
        if marker in candidate:
            return candidate.strip()
    raise ValueError(f"paragraph marker not found: {marker}")


def check_f08_a0(analyze):
    a0 = section(analyze, "记账模型准入 gate")
    command = (
        "python3 scripts/evm/accounting_gate.py --token 0x… --chain <链> "
        "--exploration --out accounting_mode.exploration.json"
    )
    assert command in a0, "A0 EVM exploration command must match the canonical command"
    inline_code = a0.split("`")
    evm_commands = [
        value for index, value in enumerate(inline_code)
        if index % 2 == 1 and "scripts/evm/accounting_gate.py" in value
    ]
    assert evm_commands, "A0 EVM accounting gate inline command is missing"
    assert all("--out accounting_mode.json" not in value for value in evm_commands), (
        "A0 must not write the formal accounting_mode.json filename"
    )
    assert "--bundle" not in a0, "A0 must not document bundle mode"


def check_f08_a2(analyze):
    a2 = section(analyze, "## A2 对账关卡")
    observe = "scripts/evm/observe_supply.py"
    formal = (
        "scripts/evm/accounting_gate.py --token 0x… --chain <链> "
        "--bundle evm_observation_bundle.json --as-of-block <冻结块> "
        "--out accounting_mode.json"
    )
    assert observe in a2, "A2 observe_supply command is missing"
    assert formal in a2, "A2 formal accounting rerun command is missing"
    assert a2.index(observe) < a2.index(formal), (
        "observe_supply must precede the formal accounting rerun"
    )


def check_f13(research):
    schema = paragraph(research, "[输出 JSON schema")
    assert "逐字写入" in schema, "entrypoint write responsibility is missing from schema paragraph"
    assert "不会静默覆盖或补入" in schema, "runner boundary statement is missing from schema paragraph"
    assert "由受控 runner 补入 role" not in research, "stale runner wording remains"


def check_f05(analyze, research):
    for path, text in ((ANALYZE, analyze), (RESEARCH, research)):
        boundary = paragraph(text, "**机器化边界**")
        assert boundary.startswith("**机器化边界**"), (
            f"machine-boundary paragraph must start with its heading: {path}"
        )
        for needle in ("机器已强制", "机器未强制", "路数与异构性"):
            assert needle in boundary, f"{needle} missing from machine-boundary paragraph: {path}"


def main():
    analyze = ANALYZE.read_text(encoding="utf-8")
    research = RESEARCH.read_text(encoding="utf-8")
    checks = (
        ("F-08 A0 exploration command", lambda: check_f08_a0(analyze)),
        ("F-08 A2 formal rerun order", lambda: check_f08_a2(analyze)),
        ("F-13 runner injection boundary", lambda: check_f13(research)),
        ("F-05 machine boundary", lambda: check_f05(analyze, research)),
    )
    failed = False
    for name, check in checks:
        try:
            check()
        except (AssertionError, OSError, ValueError) as exc:
            failed = True
            print(f"FAIL: {name}: {exc}")
        else:
            print(f"PASS: {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
