#!/usr/bin/env python3
"""Formal chain claims must close across frontmatter, release gates and label capability."""
import ast
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ALIASES = {
    "Ethereum": "eth",
    "BSC": "bsc",
    "Base": "base",
    "Arbitrum": "arbitrum",
    "Robinhood EVM": "robinhood",
    "Solana": "sol",
}


def frontmatter_description():
    lines = (ROOT / "SKILL.md").read_text(encoding="utf-8").split("---", 2)[1].splitlines()
    for index, line in enumerate(lines):
        match = re.match(r"^description:\s*(.*)$", line)
        if not match:
            continue
        value = match.group(1).strip()
        if value in {">", ">-", "|", "|-"}:
            folded = []
            for continuation in lines[index + 1:]:
                if continuation.startswith((" ", "\t")):
                    folded.append(continuation.strip())
                else:
                    break
            return " ".join(folded)
        return value
    raise AssertionError("SKILL.md frontmatter lacks description")


def frontmatter_chains():
    description = frontmatter_description()
    claim = re.search(r"正式深度管线覆盖\s*([^；]+)；", description)
    assert claim, "frontmatter lacks the canonical supported-chain claim"
    names = []
    for group in claim.group(1).split("、"):
        names.extend(part.strip() for part in group.split("/") if part.strip())
    unknown = sorted(set(names) - set(ALIASES))
    assert not unknown, f"unrecognized frontmatter chain names: {unknown}"
    return {ALIASES[name] for name in names}


def named_set(path, name):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for statement in tree.body:
        if not isinstance(statement, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == name
               for target in statement.targets):
            return {ast.literal_eval(item) for item in statement.value.elts}
    raise AssertionError(f"{path.relative_to(ROOT)} lacks literal {name}")


def csv_has_rows(path):
    if not path.is_file() or path.stat().st_size == 0:
        return False
    with path.open(newline="", encoding="utf-8") as handle:
        return next(csv.DictReader(handle), None) is not None


def main():
    declared = frontmatter_chains()
    formal = named_set(ROOT / "scripts/report/audit_release_gate.py", "FORMAL_CHAINS")
    buildable = named_set(ROOT / "scripts/labels/build_labels.py", "BUILD_CHAINS")
    assert formal == declared, (
        f"release-gate FORMAL_CHAINS={sorted(formal)} != frontmatter={sorted(declared)}"
    )
    assert buildable == declared, (
        f"build_labels BUILD_CHAINS={sorted(buildable)} != frontmatter={sorted(declared)}"
    )

    sys.path.insert(0, str(ROOT / "scripts/labels"))
    from labels_resolver import LabelResolver

    failures = []
    for chain in sorted(declared):
        csv_path = ROOT / "references/labels" / f"labels-{chain}.csv"
        if not csv_has_rows(csv_path):
            failures.append(f"{chain}: {csv_path.name} missing, empty, or header-only")
            continue
        resolver = LabelResolver(chain)
        if resolver.degraded or not resolver.table:
            failures.append(f"{chain}: labels_resolver loaded in degraded mode or returned 0 rows")
    assert not failures, "formal label capability is not closed:\n- " + "\n- ".join(failures)

    known_gate = named_set(ROOT / "scripts/report/entity_identity_gate.py", "KNOWN_CHAINS")
    known_receipt = named_set(ROOT / "scripts/report/identity_snapshot_receipt.py", "EVM_CHAINS")
    assert declared <= known_gate and "arbitrum" in known_gate - declared
    assert "arbitrum" in known_receipt, "exploratory Arbitrum identity receipt capability was removed"
    print("PASS: formal chain matrix closes frontmatter + release gate + non-degraded labels: "
          f"{sorted(declared)}; arbitrum remains exploratory-known")
    return 0


if __name__ == "__main__":
    sys.exit(main())
