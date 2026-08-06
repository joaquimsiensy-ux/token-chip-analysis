#!/usr/bin/env python3
"""第六轮批⑤：SKILL 大小口径与 archive 路由文档契约。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    retrospective = (ROOT / "references/retrospective.md").read_text(encoding="utf-8")
    casebook = (ROOT / "references/casebook/README.md").read_text(encoding="utf-8")
    expected = "归档候选由复盘流程(retrospective.md 分流决策树)登记,分析会话不触 archive"
    assert expected in casebook, "casebook 未采用维护态归档路由"
    assert "archive/evals/README.md" not in casebook, "分析 casebook 仍直路由 archive/evals"
    assert "archive/evals/README.md" in retrospective, "复盘维护登记被误删"
    assert "7.5KB 预警、8192B 硬上限" in retrospective, "大小预算未收敛到双阈值"

    hits = []
    old_terms = ("10" + "KB", "10" + " KB", "102" + "40")
    for path in [ROOT / "SKILL.md", *sorted((ROOT / "references").rglob("*.md")),
                 *sorted((ROOT / "scripts").rglob("*.py"))]:
        if "archive" in path.parts or path.name == "CHANGELOG.md":
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if any(term in line for term in old_terms):
                hits.append(f"{path.relative_to(ROOT)}:{lineno}")
    assert not hits, f"现役旧大小口径残留: {hits}"
    print("PASS: 六视角批⑤大小口径与 archive 路由")


if __name__ == "__main__":
    main()
