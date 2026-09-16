#!/usr/bin/env python3
"""W1 limits-extract：黑盒离线测试，负例先验证同夹具正例可用。"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

GATE = Path(__file__).resolve().parents[1] / "report/a4_gate.py"
FAILS = []


def check(name, cond, details=""):
    if not cond:
        FAILS.append(name)
        print(f"FAIL  {name}\n{details}")
    else:
        print(f"ok    {name}")


def write(root, text):
    (root / "findings.md").write_text(text, encoding="utf-8")


def run(root, *extra):
    return subprocess.run([sys.executable, str(GATE), "limits-extract", "--case-dir", str(root),
                           *extra], capture_output=True, text=True)


def require(p, rc=0, *messages):
    detail = f"exit={p.returncode}\n{p.stdout}{p.stderr}"
    assert p.returncode == rc, detail
    for message in messages:
        assert message in p.stderr, detail
    return p


def load(root):
    return json.loads((root / "limits.json").read_text(encoding="utf-8"))


def positive(root):
    write(root, "# 报告\n## 10 观测边界\n1. 已知局限\n")
    require(run(root))


def numbered_continuation_and_determinism(root):
    write(root, "# 报告\n## 10 观测边界与未决（测试）\n"
                "1. **数据边界**。\n2. **无法归属**。\n   这是第二条续行。\n"
                "   - 缩进子列表仍是续行\n3. 第三项。\n## 11 附录\n不是条目也不影响局限节\n")
    p = require(run(root))
    obj = load(root)
    assert "[limits-extract] 3 条" in p.stdout
    assert obj["schema"] == "a4-limits/v1" and len(obj["items"]) == 3
    assert obj["heading"] == {"line": 2, "level": 2, "text": "10 观测边界与未决（测试）"}
    assert obj["items"][1] == {
        "id": "LIM-02", "index": 2, "written_marker": "2.", "line": 4,
        "text": "**无法归属**。 这是第二条续行。 - 缩进子列表仍是续行"}
    assert obj["findings"] == {"path": "findings.md", "sha256": hashlib.sha256(
        (root / "findings.md").read_bytes()).hexdigest()}
    before = (root / "limits.json").read_bytes()
    require(run(root))
    assert (root / "limits.json").read_bytes() == before


def bullet_markers(root):
    write(root, "## 局限\n- 第一条\n* 第二条\n")
    require(run(root))
    assert [x["written_marker"] for x in load(root)["items"]] == ["-", "*"]


def numbering_from_zero(root):
    write(root, "## 局限\n0. 第零条\n4. 非连续作者编号\n")
    require(run(root))
    items = load(root)["items"]
    assert [(x["id"], x["index"], x["written_marker"]) for x in items] == [
        ("LIM-01", 1, "0."), ("LIM-02", 2, "4.")]


def ambiguous_heading(root):
    write(root, "# 报告\n## 10 局限\n1. 第一条\n## 11 局限补充\n- 第二条\n")
    require(run(root, "--heading", "^10 "))
    require(run(root), 2, "用 --heading 精确指定", "第 2 行", "第 4 行")


def missing_heading(root):
    positive(root)
    write(root, "# 报告\n## 数据说明\n1. 数据说明\n")
    require(run(root), 2, "用 --heading 精确指定", "第 2 行", "数据说明")


def empty_section(root):
    positive(root)
    write(root, "## 局限\n\n## 下一节\n1. 不属于局限\n")
    require(run(root), 2, "提取为空")


def orphan_after_blank(root):
    positive(root)
    write(root, "## 局限\n1. 有效条目\n\n孤立段落\n")
    require(run(root), 2, "局限节第 4 行无法归属到条目")
    write(root, "## 局限\n先于首条的孤立文本\n1. 有效条目\n")
    require(run(root), 2, "局限节第 2 行无法归属到条目")


def path_fences(root):
    positive(root)
    require(run(root, "--out", "../x.json"), 2, "非法段")
    (root / "linked.md").symlink_to(root / "findings.md")
    require(run(root, "--findings", "linked.md"), 2, "符号链接")


def end_of_file(root):
    write(root, "## 局限\n- 第一条\n\n- 第二条")
    require(run(root))
    assert [x["text"] for x in load(root)["items"]] == ["第一条", "第二条"]


def unindented_non_items(root):
    positive(root)
    for line in ("+ x", "2) x", "### 子标题"):
        write(root, "## 局限\n1. 有效条目\n" + line + "\n")
        require(run(root), 2, "局限节第 3 行既非条目也非缩进续行")


def fenced_headings_and_items(root):
    write(root, "```markdown\n## 局限\n1. 伪条目\n```\n"
                "## 局限\n1. 真条目\n   ```text\n## 局限\n1. x\n   ```\n2. 第二条\n")
    require(run(root))
    obj = load(root)
    assert obj["heading"]["line"] == 5
    assert len(obj["items"]) == 2
    assert [x["line"] for x in obj["items"]] == [6, 11]
    assert obj["items"][1]["text"] == "第二条"


def output_cannot_overwrite_input(root):
    positive(root)
    before = (root / "findings.md").read_bytes()
    require(run(root, "--out", "findings.md"), 2, "同一文件")
    assert (root / "findings.md").read_bytes() == before
    # 同一实物的硬链接也不能绕过输入保护。
    os.link(root / "findings.md", root / "alias.md")
    require(run(root, "--out", "alias.md"), 2, "同一文件")
    assert (root / "findings.md").read_bytes() == before


def main():
    tests = [numbered_continuation_and_determinism, bullet_markers, numbering_from_zero,
             ambiguous_heading, missing_heading, empty_section, orphan_after_blank, path_fences,
             end_of_file, unindented_non_items, fenced_headings_and_items, output_cannot_overwrite_input]
    for test in tests:
        with tempfile.TemporaryDirectory(prefix="w1-limits-") as td:
            try:
                test(Path(td))
            except Exception as exc:
                check(test.__name__, False, f"{type(exc).__name__}: {exc}")
            else:
                check(test.__name__, True)
    print(f"limits-extract: {len(tests) - len(FAILS)}/{len(tests)} PASS")
    return int(bool(FAILS))


if __name__ == "__main__":
    raise SystemExit(main())
