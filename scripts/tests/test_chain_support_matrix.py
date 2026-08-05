#!/usr/bin/env python3
"""Frontmatter chain claim and both production identity gates must be identical."""
import ast
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


def frontmatter_chains():
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = text.split("---", 2)[1]
    description = re.search(r"^description:\s*(.+)$", frontmatter, re.M)
    assert description, "SKILL.md frontmatter lacks description"
    claim = re.search(r"正式深度管线覆盖\s*([^\uff1b]+)；", description.group(1))
    assert claim, "frontmatter lacks the canonical supported-chain claim"
    names = []
    for group in claim.group(1).split("、"):
        names.extend(part.strip() for part in group.split("/") if part.strip())
    unknown = sorted(set(names) - set(ALIASES))
    assert not unknown, f"unrecognized frontmatter chain names: {unknown}"
    return {ALIASES[name] for name in names}


def evaluated_sets(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    values = {}

    def evaluate(node):
        if isinstance(node, ast.Set):
            return {ast.literal_eval(item) for item in node.elts}
        if isinstance(node, ast.Name) and node.id in values:
            return values[node.id]
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return evaluate(node.left) | evaluate(node.right)
        raise ValueError(f"unsupported chain-set expression: {ast.dump(node)}")

    for statement in tree.body:
        if not isinstance(statement, ast.Assign):
            continue
        value = evaluate(statement.value) if any(
            isinstance(target, ast.Name) and target.id in {"EVM_CHAINS", "SUPPORTED", "CHAINS"}
            for target in statement.targets
        ) else None
        if value is not None:
            for target in statement.targets:
                if isinstance(target, ast.Name):
                    values[target.id] = value
    return values


def main():
    declared = frontmatter_chains()
    expected = {"eth", "bsc", "base", "arbitrum", "robinhood", "sol"}
    assert declared == expected, f"frontmatter chains drifted: {sorted(declared)}"

    receipt = evaluated_sets(ROOT / "scripts/report/identity_snapshot_receipt.py")
    gate = evaluated_sets(ROOT / "scripts/report/entity_identity_gate.py")
    supported = receipt.get("SUPPORTED")
    chains = gate.get("CHAINS")
    assert supported == declared, (
        f"identity_snapshot_receipt SUPPORTED={sorted(supported or [])} "
        f"!= frontmatter={sorted(declared)}"
    )
    assert chains == declared, (
        f"entity_identity_gate CHAINS={sorted(chains or [])} "
        f"!= frontmatter={sorted(declared)}"
    )
    print(f"PASS: chain support matrix is bidirectionally closed: {sorted(declared)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
