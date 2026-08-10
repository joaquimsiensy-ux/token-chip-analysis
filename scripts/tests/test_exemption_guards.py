#!/usr/bin/env python3
"""Exemption anti-regression guards (maintenance/repair-20260806/exemptions.md).

EX-01 full-F-03: multicall_balances.py is exempt ONLY while it stays outside
every formal publication path.  Each auto-expiry condition in the ledger entry
is enforced here as a machine check; any hit must turn this suite red so the
exemption dies with the fact that granted it.
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXEMPT_MODULE = "multicall_balances"
EXEMPT_REL = "scripts/evm/multicall_balances.py"


def _production_files():
    for path in sorted((ROOT / "scripts").rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith("scripts/tests/"):
            continue
        if rel == EXEMPT_REL:
            continue
        yield path, rel


def exemption_violations(scripts_root=None):
    """Return violations of EX-01 auto-expiry conditions (empty == exempt holds)."""
    violations = []
    files = (_production_files() if scripts_root is None else
             ((p, p.relative_to(scripts_root).as_posix())
              for p in sorted(Path(scripts_root).rglob("*.py"))))
    for path, rel in files:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for item in node.names:
                    if EXEMPT_MODULE in item.name:
                        violations.append(f"{rel}: import {item.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if EXEMPT_MODULE in module:
                    violations.append(f"{rel}: from {module} import ...")
            elif (isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and EXEMPT_MODULE in node.value):
                violations.append(f"{rel}: string reference {node.value!r}")
    return violations


def test_no_production_reachability():
    violations = exemption_violations()
    assert violations == [], violations
    print("PASS EX-01: no production import/string reference to multicall_balances")


def test_not_in_formal_registries():
    for rel in ("scripts/report/reconciliation_report.py",
                "scripts/tests/invariant_scan.py",
                "scripts/lib/formal_capability_probes.py"):
        source = (ROOT / rel).read_text(encoding="utf-8")
        assert EXEMPT_MODULE not in source, f"{rel} references {EXEMPT_MODULE}"
    print("PASS EX-01: absent from formal producer registry / evidence targets")


def test_stays_in_exploration_choice_group():
    source = (ROOT / EXEMPT_REL).read_text(encoding="utf-8")
    assert "attested_evm_chains()" in source, "exploration choices marker missing"
    for formal_marker in ("formal_reconciliation_chains", "formal_evm_chains"):
        assert formal_marker not in source, (
            f"{EXEMPT_REL} switched to formal choice derivation: {formal_marker}")
    print("PASS EX-01: --chain choices remain exploration-derived")


def test_injection_production_import_turns_red(tmp_root):
    """INJECT EX-01-RED: a production file importing the module must be caught."""
    sample = tmp_root / "fake_producer.py"
    sample.write_text(
        "import multicall_balances\n"
        "def main():\n    return 0\n", encoding="utf-8")
    violations = exemption_violations(scripts_root=tmp_root)
    assert violations, "guard failed to flag a production import"
    print("INJECT EX-01-RED production import -> RED")


def main():
    import tempfile
    test_no_production_reachability()
    test_not_in_formal_registries()
    test_stays_in_exploration_choice_group()
    with tempfile.TemporaryDirectory() as tmp:
        test_injection_production_import_turns_red(Path(tmp))
    print("PASS: exemption guards (EX-01 full-F-03)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
