#!/usr/bin/env python3
"""v6.35 invariant manifest completeness guard.

The scanner answers one question: does the manifest still list the whole
implementation surface?  It inventories kernel/registry/net adoption points but
does not claim that every registered legacy point has already migrated.
"""
from __future__ import annotations

import argparse
import ast
import copy
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = Path(__file__).with_name("invariant_manifest.json")
SCOPE = (
    "scripts/report",
    "scripts/evm",
    "scripts/solana",
    "scripts/lib",
    "scripts/robinhood",
    "scripts/labels",
    "scripts/prices",
    "scripts/*.py",
)
ATOMIC_SEMANTICS = {
    "exclusive_new", "overwrite_single", "dual_file_txn", "restore_on_fail",
}


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def production_files():
    files = []
    for rel in SCOPE:
        if rel == "scripts/*.py":
            files.extend(p for p in (ROOT / "scripts").glob("*.py") if p.is_file())
            continue
        base = ROOT / rel
        files.extend(p for p in base.rglob("*") if p.is_file() and p.suffix in {".py", ".sh"})
    return sorted(set(files))


def _constants(tree: ast.AST) -> dict[str, str]:
    values = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value = node.value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                for target in targets:
                    if isinstance(target, ast.Name):
                        values[target.id] = value.value
    return values


def _string_values(node: ast.AST, constants: dict[str, str]) -> set[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return {node.value}
    if isinstance(node, ast.Name) and node.id in constants:
        return {constants[node.id]}
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        out = set()
        for item in node.elts:
            out.update(_string_values(item, constants))
        return out
    return set()


def _is_schema_access(node: ast.AST) -> bool:
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
            and node.func.attr == "get" and node.args:
        return isinstance(node.args[0], ast.Constant) and node.args[0].value == "schema"
    if isinstance(node, ast.Subscript):
        key = node.slice
        return isinstance(key, ast.Constant) and key.value == "schema"
    return False


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = _call_name(node.value)
        return f"{left}.{node.attr}" if left else node.attr
    return ""


class AtomicVisitor(ast.NodeVisitor):
    def __init__(self):
        self.stack = ["<module>"]
        self.locators = set()

    def visit_FunctionDef(self, node):
        calls = {_call_name(item.func) for item in ast.walk(node) if isinstance(item, ast.Call)}
        temp_stage = {"tempfile.NamedTemporaryFile", "tempfile.mkstemp"} & calls
        if temp_stage and "shutil.move" in calls:
            self.locators.add(node.name)
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node):
        if _call_name(node.func) in {"os.replace", "os.link"}:
            self.locators.add(self.stack[-1])
        self.generic_visit(node)


def scan_python(path: Path):
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    constants = _constants(tree)
    producers = set()
    consumers = set()
    has_requests = False
    has_net = False
    has_curl = False
    schema_vars = set()
    schema_dict_vars = {}

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value = node.value
        names = [target.id for target in targets if isinstance(target, ast.Name)]
        if _is_schema_access(value):
            schema_vars.update(names)
        if isinstance(value, ast.Dict):
            found = set()
            for key, item in zip(value.keys, value.values):
                if isinstance(key, ast.Constant) and key.value == "schema":
                    found.update(_string_values(item, constants))
            for name in names:
                if found:
                    schema_dict_vars[name] = found

    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and key.value == "schema":
                    producers.update(_string_values(value, constants))
        elif isinstance(node, ast.Call) and _call_name(node.func).endswith("build_envelope"):
            schema_node = node.args[0] if node.args else next(
                (kw.value for kw in node.keywords if kw.arg == "schema"), None)
            if schema_node is not None:
                producers.update(_string_values(schema_node, constants))
        elif isinstance(node, ast.Compare):
            sides = [node.left, *node.comparators]
            if any(_is_schema_access(side) or isinstance(side, ast.Name)
                   and side.id in schema_vars for side in sides):
                for side in sides:
                    if not _is_schema_access(side) and not (
                            isinstance(side, ast.Name) and side.id in schema_vars):
                        consumers.update(_string_values(side, constants))
            for side in sides:
                if isinstance(side, ast.Name) and side.id in schema_dict_vars:
                    consumers.update(schema_dict_vars[side.id])
                elif isinstance(side, ast.Dict):
                    for key, item in zip(side.keys, side.values):
                        if isinstance(key, ast.Constant) and key.value == "schema":
                            consumers.update(_string_values(item, constants))
        elif isinstance(node, ast.Import):
            has_requests |= any(alias.name == "requests" for alias in node.names)
            has_net |= any(alias.name == "net" for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            has_requests |= node.module == "requests"
            has_net |= node.module == "net"
        elif isinstance(node, ast.Call) and _call_name(node.func) in {
                "subprocess.run", "subprocess.Popen"} and node.args:
            first = node.args[0]
            if isinstance(first, (ast.List, ast.Tuple)) and first.elts:
                cmd = first.elts[0]
                has_curl |= isinstance(cmd, ast.Constant) and cmd.value == "curl"
    has_curl |= constants.get("REGISTERED_TRANSPORT_BACKEND") == "curl"

    atomic = AtomicVisitor()
    atomic.visit(tree)
    transports = set()
    if has_curl:
        transports.add("curl")
    if has_net:
        transports.add("net.py")
    if has_requests:
        transports.add("requests")
    return producers, consumers, transports, atomic.locators


def scan_actual():
    producer_map = {}
    consumer_map = {}
    transports = []
    atomic = []
    for path in production_files():
        rel = _rel(path)
        if path.suffix == ".sh":
            text = path.read_text(encoding="utf-8")
            if re.search(r"(?m)^[^#\n]*\bcurl\b", text):
                transports.append({"script": rel, "kind": "curl"})
            if ".tmp" in text and re.search(r"(?m)^[^#\n]*\bmv\b", text):
                atomic.append({"script": rel, "locator": "<module>"})
            continue
        producers, consumers, kinds, locators = scan_python(path)
        if producers:
            producer_map[rel] = sorted(producers)
        if consumers:
            consumer_map[rel] = sorted(consumers)
        transports.extend({"script": rel, "kind": kind} for kind in sorted(kinds))
        atomic.extend({"script": rel, "locator": name} for name in sorted(locators))
    docs = [ROOT / "SKILL.md"]
    docs.extend(p for p in (ROOT / "references").rglob("*.md")
                if "archive" not in p.parts and p.name != "attic.md")
    documented = "\n".join(p.read_text(encoding="utf-8") for p in docs)
    formal = []
    for path in production_files():
        rel = _rel(path)
        if rel not in documented:
            continue
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".sh" or "__main__" in text:
            formal.append(rel)
    return {
        "receipt_producers": [
            {"script": script, "schemas": schemas}
            for script, schemas in sorted(producer_map.items())
        ],
        "receipt_consumers": [
            {"script": script, "schemas": schemas}
            for script, schemas in sorted(consumer_map.items())
        ],
        "transport_calls": sorted(transports, key=lambda x: (x["script"], x["kind"])),
        "atomic_writes": sorted(atomic, key=lambda x: (x["script"], x["locator"])),
        "formal_entrypoints": sorted(formal),
    }


def _producer_key(item):
    return item.get("script"), tuple(sorted(item.get("schemas") or []))


def _point_key(item):
    return item.get("script"), item.get("kind") or item.get("locator")


def _diff(label, expected, actual, key):
    exp = {key(x) for x in expected}
    got = {key(x) for x in actual}
    errors = []
    for item in sorted(got - exp):
        errors.append(f"{label}: code point missing from manifest: {item}")
    for item in sorted(exp - got):
        errors.append(f"{label}: manifest point missing from code: {item}")
    if len(exp) != len(expected):
        errors.append(f"{label}: duplicate manifest entries")
    return errors


def validate_manifest(manifest, actual):
    errors = []
    if manifest.get("schema") != "invariant-manifest/v1":
        errors.append("manifest schema must be invariant-manifest/v1")
    if tuple(manifest.get("scope") or ()) != SCOPE:
        errors.append("manifest scope differs from scanner scope")
    errors += _diff("receipt_producers", manifest.get("receipt_producers", []),
                    actual["receipt_producers"], _producer_key)
    errors += _diff("receipt_consumers", manifest.get("receipt_consumers", []),
                    actual["receipt_consumers"], _producer_key)
    errors += _diff("transport_calls", manifest.get("transport_calls", []),
                    actual["transport_calls"], _point_key)
    errors += _diff("atomic_writes", manifest.get("atomic_writes", []),
                    actual["atomic_writes"], _point_key)
    errors += _diff("formal_entrypoints",
                    [{"script": x} for x in manifest.get("formal_entrypoints", [])],
                    [{"script": x} for x in actual["formal_entrypoints"]],
                    lambda x: x.get("script"))

    atomic_keys = {_point_key(x) for x in actual["atomic_writes"]}
    for item in manifest.get("atomic_writes", []):
        if item.get("semantics") not in ATOMIC_SEMANTICS:
            errors.append(f"atomic_writes: invalid semantics for {_point_key(item)}")
        if _point_key(item) not in atomic_keys:
            continue

    formal = manifest.get("formal_entrypoints", [])
    if len(set(formal)) != len(formal):
        errors.append("formal_entrypoints: duplicate entries")
    for rel in formal:
        path = ROOT / str(rel)
        if not path.is_file():
            errors.append(f"formal_entrypoints: missing file: {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".py" and "__main__" not in text:
            errors.append(f"formal_entrypoints: no CLI entrypoint: {rel}")

    required_exception = {"id", "script", "reason", "formal_reachable", "expiry_version"}
    exceptions = manifest.get("exceptions", [])
    ids = set()
    for item in exceptions:
        missing = required_exception - set(item)
        if missing:
            errors.append(f"exceptions: missing fields {sorted(missing)}")
        if item.get("id") in ids:
            errors.append(f"exceptions: duplicate id {item.get('id')}")
        ids.add(item.get("id"))
        if not re.fullmatch(r"\d+\.\d+\.\d+", str(item.get("expiry_version", ""))):
            errors.append(f"exceptions: invalid expiry_version for {item.get('id')}")
    return errors


def counts(manifest):
    return {
        "receipt_producers": sum(len(x["schemas"]) for x in manifest["receipt_producers"]),
        "receipt_consumers": sum(len(x["schemas"]) for x in manifest["receipt_consumers"]),
        "transport_calls": len(manifest["transport_calls"]),
        "atomic_writes": len(manifest["atomic_writes"]),
        "formal_entrypoints": len(manifest["formal_entrypoints"]),
        "exceptions": len(manifest["exceptions"]),
    }


def injection_selftest(manifest_path):
    baseline = json.loads(manifest_path.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="invariant-scan-selftest-") as td:
        root = Path(td)
        missing = copy.deepcopy(baseline)
        removed = missing["transport_calls"].pop(0)
        missing_path = root / "missing.json"
        missing_path.write_text(json.dumps(missing), encoding="utf-8")
        missing_run = subprocess.run(
            [sys.executable, __file__, "--manifest", str(missing_path)],
            capture_output=True, text=True)

        extra = copy.deepcopy(baseline)
        fake = {"script": "scripts/report/does_not_exist.py", "kind": "requests"}
        extra["transport_calls"].append(fake)
        extra_path = root / "extra.json"
        extra_path.write_text(json.dumps(extra), encoding="utf-8")
        extra_run = subprocess.run(
            [sys.executable, __file__, "--manifest", str(extra_path)],
            capture_output=True, text=True)

    missing_ok = missing_run.returncode == 1 and "code point missing from manifest" in missing_run.stdout
    extra_ok = extra_run.returncode == 1 and "manifest point missing from code" in extra_run.stdout
    print(f"SELFTEST delete {removed['script']}:{removed['kind']} -> "
          f"{'RED' if missing_ok else 'BROKEN'} (rc={missing_run.returncode})")
    print(f"SELFTEST add {fake['script']}:{fake['kind']} -> "
          f"{'RED' if extra_ok else 'BROKEN'} (rc={extra_run.returncode})")
    if not missing_ok:
        print(missing_run.stdout + missing_run.stderr)
    if not extra_ok:
        print(extra_run.stdout + extra_run.stderr)
    return 0 if missing_ok and extra_ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--dump-actual", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    actual = scan_actual()
    if args.dump_actual:
        print(json.dumps(actual, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.self_test:
        return injection_selftest(args.manifest)
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"FAIL invariant manifest unreadable: {exc}", file=sys.stderr)
        return 1
    errors = validate_manifest(manifest, actual)
    if errors:
        for error in errors:
            print(f"FAIL {error}")
        print(f"invariant manifest FAIL: {len(errors)} discrepancy(s)")
        return 1
    summary = counts(manifest)
    print("PASS invariant manifest: " + ", ".join(f"{k}={v}" for k, v in summary.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
