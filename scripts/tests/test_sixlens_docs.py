#!/usr/bin/env python3
"""第六轮批⑤：SKILL 大小口径与 archive 路由文档契约。"""
from pathlib import Path
import ast
import os

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

    finding_map = (ROOT / "maintenance/repair-20260806/diff-finding-map.md").read_text(
        encoding="utf-8")
    for evidence in (
        "g3_preflight/g3_0b_pythia_gpa.json",
        "smoke-20260808/accounting_mode.json",
        "smoke-20260808/solana_observation_bundle.json",
        "smoke-20260808/supply_truth.json",
    ):
        assert evidence in finding_map, f"裁判 mainnet 证据未映射: {evidence}"
    assert "solana_sqd_dataset.py" in finding_map and "跨批" in finding_map, (
        "Solana SQD 批三 docstring hunk 缺跨批 owner 注记")

    ledger = (ROOT / "maintenance/repair-20260806/ledger.md").read_text(encoding="utf-8")
    r9_01 = ledger.split("### R9-01", 1)[1].split("### R9-02", 1)[0]
    for statement in ("不含 bundle 防伪", "批四 producer/consumer 通用守卫", "现场生成"):
        assert statement in r9_01, f"R9-01 闭合边界缺失: {statement}"

    docs = {}
    for relative in (
        "scripts/solana/accounting_gate_sol.py",
        "scripts/lib/supply_truth_gate.py",
        "scripts/solana/scan_token_accounts.py",
    ):
        source = (ROOT / relative).read_text(encoding="utf-8")
        docs[relative] = ast.get_docstring(ast.parse(source)) or ""
    assert "--bundle" in docs["scripts/solana/accounting_gate_sol.py"]
    assert "--min-context-slot" in docs["scripts/solana/accounting_gate_sol.py"]
    assert "--observation-bundle" in docs["scripts/lib/supply_truth_gate.py"]
    assert "--min-context-slot" in docs["scripts/lib/supply_truth_gate.py"]
    assert "--bundle" in docs["scripts/solana/scan_token_accounts.py"]
    assert "--min-context-slot" in docs["scripts/solana/scan_token_accounts.py"]
    probes = (ROOT / "scripts/lib/formal_capability_probes.py").read_text(encoding="utf-8")
    harness = (ROOT / "scripts/tests/formal_ready_test_harness.py").read_text(encoding="utf-8")
    assert "batch 3 must add real test targets" not in probes
    assert "batch 2 has no R9 vertical-slice evidence" not in harness
    observation_path = Path(os.environ.get(
        "R9_SOLANA_OBSERVATION_SOURCE", ROOT / "scripts/lib/solana_observation.py"))
    observation = observation_path.read_text(encoding="utf-8")
    assert "if not complete and not high_activity" not in observation
    print("PASS: 六视角批⑤大小口径与 archive 路由")


if __name__ == "__main__":
    main()
