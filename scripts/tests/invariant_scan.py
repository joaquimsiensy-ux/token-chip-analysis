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
import importlib.util
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
DENOMINATOR_KEYS = {
    "receipt_producers", "receipt_consumers", "transport_calls",
    "atomic_writes", "formal_entrypoints",
}
LABEL_CHAIN_SURFACES = (
    ("scripts/labels/labels_resolver.py", "known", "assign:KNOWN_CHAINS"),
    ("scripts/labels/gen_manual_from_addressbook.py", "known", "assign:CHAINS"),
    ("scripts/labels/build_labels.py", "table", "assign:BUILD_CHAINS"),
    ("scripts/labels/benchmark_labels.py", "table", "assign:EXPECTED_CHAINS"),
    ("scripts/labels/roundtrip_check.py", "table", "assign:CHAINS"),
    ("scripts/labels/goplus_check.py", "table", "argparse:--chain"),
    ("scripts/labels/build_goldset.py", "table", "membership:chain:2"),
    # serial-offender accumulation consumes the same labels-table asset surface.
    ("scripts/labels/accumulate_offenders.py", "table", "membership:chain:1"),
)
VERTICAL_SLICE_TESTS = {
    "eth": "test_batch3_evm_vertical_slice.py",
    "bsc": "test_batch3_evm_vertical_slice.py",
    "base": "test_batch3_evm_vertical_slice.py",
    "sol": "test_batch3_solana_vertical_slice.py",
}
FORMAL_E2E_REQUIRED_PRODUCERS = {
    "eth": frozenset({
        "scripts/lib/anchor_plan.py", "scripts/evm/accounting_gate.py",
        "scripts/evm/verify_recon.py", "scripts/lib/supply_truth_gate.py",
        "scripts/lib/time_spotcheck.py",
    }),
    "bsc": frozenset({
        "scripts/lib/anchor_plan.py", "scripts/evm/accounting_gate.py",
        "scripts/evm/verify_recon.py", "scripts/lib/supply_truth_gate.py",
        "scripts/lib/time_spotcheck.py",
    }),
    "base": frozenset({
        "scripts/lib/anchor_plan.py", "scripts/evm/accounting_gate.py",
        "scripts/evm/verify_recon.py", "scripts/lib/supply_truth_gate.py",
        "scripts/lib/time_spotcheck.py",
    }),
    "sol": frozenset({
        "scripts/solana/scan_token_accounts.py",
        "scripts/solana/anchor_sampler.py",
        "scripts/lib/supply_truth_gate.py",
        "scripts/solana/accounting_gate_sol.py",
        "scripts/solana/window_fetch.py",
    }),
}
FAILURE_ARTIFACT_CONTRACTS = (
    {"script": "scripts/evm/fetch_pool_swaps.py", "entrypoint": "main",
     "canonical_artifacts": 2},
    {"script": "scripts/lib/anchor_plan.py", "entrypoint": "main",
     "canonical_artifacts": 2},
    {"script": "scripts/solana/scan_token_accounts.py", "entrypoint": "main",
     "canonical_artifacts": 2},
)
FAILURE_ARTIFACT_COVERAGE = {
    "scripts/evm/accounting_gate.py": {
        "canonical": "accounting status receipt", "marker": "verdict+exit_code",
        "error": "same-path FAIL status receipt", "protections": ("fresh_status_receipt",)},
    "scripts/solana/accounting_gate_sol.py": {
        "canonical": "accounting status receipt", "marker": "verdict+exit_code",
        "error": "same-path FAIL status receipt", "protections": ("fresh_status_receipt",)},
    "scripts/evm/verify_recon.py": {
        "canonical": "reconciliation check receipt", "marker": "runner wrapper",
        "error": "unique ERROR side receipt", "protections": ("runner_fresh_receipt",)},
    "scripts/lib/supply_truth_gate.py": {
        "canonical": "supply-truth check receipt", "marker": "runner wrapper",
        "error": "unique ERROR side receipt", "protections": ("runner_fresh_receipt",)},
    "scripts/lib/time_spotcheck.py": {
        "canonical": "time check receipt", "marker": "runner wrapper",
        "error": "unique ERROR side receipt", "protections": ("runner_fresh_receipt",)},
    "scripts/solana/anchor_sampler.py": {
        "canonical": "anchor data", "marker": "anchor check receipt",
        "error": "unique ERROR side receipt", "protections": ("runner_fresh_receipt",)},
    "scripts/solana/scan_token_accounts.py": {
        "canonical": "holder snapshot", "marker": "observation bundle",
        "error": "unique ERROR side receipt",
        "protections": ("runner_fresh_receipt", "self_quarantine")},
    "scripts/lib/anchor_plan.py": {
        "canonical": "anchor plan", "marker": "anchor-plan receipt",
        "error": "unique ERROR side receipt", "protections": ("self_quarantine",)},
    "scripts/evm/fetch_pool_swaps.py": {
        "canonical": "pool swap CSV", "marker": "pool collector receipt",
        "error": "unique ERROR side receipt", "protections": ("self_quarantine",)},
    "scripts/solana/window_fetch.py": {
        "canonical": "window data", "marker": "window receipt",
        "error": "unique ERROR side receipt", "protections": ("manual_stale_move",)},
}
CAPABILITY_ENTRYPOINTS = {
    "controlled_runner": "scripts/report/reconciliation_report.py",
    "reconciliation_consumer": "scripts/report/shared_release_receipt.py",
    "identity_adapter": "scripts/report/identity_snapshot_receipt.py",
    "handoff": "scripts/report/handoff_manifest.py",
    "audit_release": "scripts/report/audit_release_gate.py",
}
FORMAL_RELEASE_ENTRYPOINTS = {
    "scripts/report/a4_gate.py",
    "scripts/report/a5_report_seal.py",
    "scripts/report/build_html.py",
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


def _load_chain_registry():
    path = ROOT / "scripts/lib/chain_registry.py"
    spec = importlib.util.spec_from_file_location("invariant_chain_registry", path)
    module = importlib.util.module_from_spec(spec)
    original_path = list(sys.path)
    try:
        sys.path.insert(0, str(path.parent))
        sys.path.insert(0, str(ROOT))
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = original_path
    return module


def _literal_assignments(path: Path, names) -> dict:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    wanted = set(names)
    found = {}
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if isinstance(target, ast.Name) and target.id in wanted:
                found[target.id] = ast.literal_eval(node.value)
    return found


class FormalEntrypointSourceError(ValueError):
    pass


def registered_formal_entrypoints(*, shared_path=None):
    registry = _load_chain_registry()
    shared_path = Path(shared_path or ROOT / "scripts/report/shared_release_receipt.py")
    required = {"ACCOUNTING_PRODUCERS", "RECON_PRODUCERS", "RECON_RUNNERS",
                "ADVERSARIAL_RUNNERS"}
    shared = _literal_assignments(
        shared_path, required,
    )
    missing_keys = sorted(required - set(shared))
    if missing_keys:
        raise FormalEntrypointSourceError(
            "formal entrypoint derived source shared_release_receipt missing keys "
            f"{missing_keys}; registry and shared_release_receipt are out of sync")
    families = {
        record["capabilities"]["accounting_adapter"]
        for chain, record in registry.CHAIN_REGISTRY.items()
        if record["release_tier"] == "formal"
    }
    paths = set(FORMAL_RELEASE_ENTRYPOINTS)
    accounting = shared["ACCOUNTING_PRODUCERS"]
    producers = shared["RECON_PRODUCERS"]
    missing_accounting = sorted(families - set(accounting))
    missing_producers = sorted(families - set(producers))
    if missing_accounting or missing_producers:
        details = []
        if missing_accounting:
            details.append(f"ACCOUNTING_PRODUCERS missing families {missing_accounting}")
        if missing_producers:
            details.append(f"RECON_PRODUCERS missing families {missing_producers}")
        raise FormalEntrypointSourceError(
            "formal entrypoint derived source " + "; ".join(details)
            + "; registry and shared_release_receipt are out of sync")
    for name in ("RECON_RUNNERS", "ADVERSARIAL_RUNNERS"):
        if not shared[name]:
            raise FormalEntrypointSourceError(
                f"formal entrypoint derived source {name} is empty; "
                "registry and shared_release_receipt are out of sync")
    for family in families:
        paths.add(accounting[family])
        for allowed in producers[family].values():
            paths.update(allowed)
    paths.update(shared["RECON_RUNNERS"])
    paths.update(shared["ADVERSARIAL_RUNNERS"])
    for chain, record in registry.CHAIN_REGISTRY.items():
        if record["release_tier"] != "formal":
            continue
        for fact, rel in CAPABILITY_ENTRYPOINTS.items():
            if record["capabilities"].get(fact):
                paths.add(rel)
    return sorted(paths)


class BareRpcPoolVisitor(ast.NodeVisitor):
    def __init__(self):
        self.stack = ["<module>"]
        self.calls = []

    def visit_FunctionDef(self, node):
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node):
        name = _call_name(node.func)
        if name == "RpcPool" or name.endswith(".RpcPool"):
            self.calls.append((self.stack[-1], node.lineno))
        self.generic_visit(node)


def bare_rpc_pool_errors(*, files=None, root=ROOT):
    errors = []
    for path in files or production_files():
        if path.suffix != ".py":
            continue
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            rel = path.as_posix()
        visitor = BareRpcPoolVisitor()
        visitor.visit(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        for locator, line in visitor.calls:
            if rel == "scripts/lib/net.py" and locator == "attested_rpc_pool":
                continue
            errors.append(f"bare RpcPool construction: {rel}:{line} ({locator})")
    return errors


def _direct_value_returns(function):
    """Return value-bearing Return nodes, excluding nested functions/lambdas."""
    found = []

    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            if node is function:
                self.generic_visit(node)

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Lambda(self, _node):
            return

        def visit_Return(self, node):
            if node.value is not None:
                found.append(node)

    Visitor().visit(function)
    return found


def _is_main_guard(node):
    if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
        return False
    values = [node.test.left, *node.test.comparators]
    has_name = any(isinstance(value, ast.Name) and value.id == "__name__"
                   for value in values)
    has_main = any(isinstance(value, ast.Constant) and value.value == "__main__"
                   for value in values)
    return has_name and has_main


def _exit_propagates(call, parents):
    parent = parents.get(call)
    return (isinstance(parent, ast.Call)
            and _call_name(parent.func) in {"exit", "sys.exit", "SystemExit"}
            and call in parent.args)


def main_exit_propagation_errors(*, files=None, root=ROOT):
    """Find value-returning main calls whose process exit value is discarded."""
    paths = files if files is not None else sorted((ROOT / "scripts").rglob("*.py"))
    errors = []
    for path in paths:
        path = Path(path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        main = next((node for node in tree.body
                     if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                     and node.name == "main"), None)
        if main is None or not _direct_value_returns(main):
            continue
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            rel = path.as_posix()
        # A bare module-level expression executes on import as well as CLI use;
        # it still discards main's value even though it sits outside the usual
        # __main__ guard that the original R9-B4 check inspected.
        for statement in (node for node in tree.body if isinstance(node, ast.Expr)):
            parents = {child: parent for parent in ast.walk(statement)
                       for child in ast.iter_child_nodes(parent)}
            for call in (node for node in ast.walk(statement) if isinstance(node, ast.Call)
                         and _call_name(node.func) == "main"):
                if not _exit_propagates(call, parents):
                    errors.append(
                        f"integer/value-returning main does not propagate process exit: "
                        f"{rel}:{call.lineno}")
        for guard in (node for node in tree.body if _is_main_guard(node)):
            parents = {child: parent for parent in ast.walk(guard)
                       for child in ast.iter_child_nodes(parent)}
            for call in (node for node in ast.walk(guard) if isinstance(node, ast.Call)
                         and _call_name(node.func) == "main"):
                if not _exit_propagates(call, parents):
                    errors.append(
                        f"integer/value-returning main does not propagate process exit: "
                        f"{rel}:{call.lineno}")
    return errors


def _surface_values(path: Path, locator: str):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    if locator.startswith("assign:"):
        name = locator.split(":", 1)[1]
        value = _literal_assignments(path, {name}).get(name)
        return [set(value)] if isinstance(value, (list, tuple, set, frozenset)) else []
    if locator == "argparse:--chain":
        found = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not _call_name(node.func).endswith("add_argument"):
                continue
            if not any(isinstance(arg, ast.Constant) and arg.value == "--chain"
                       for arg in node.args):
                continue
            for keyword in node.keywords:
                if keyword.arg == "choices":
                    value = ast.literal_eval(keyword.value)
                    found.append(set(value))
        return found
    if locator.startswith("membership:chain:"):
        found = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare) or not isinstance(node.left, ast.Name) \
                    or node.left.id != "chain":
                continue
            for op, comparator in zip(node.ops, node.comparators):
                if isinstance(op, (ast.In, ast.NotIn)) \
                        and isinstance(comparator, (ast.Tuple, ast.List, ast.Set)):
                    found.append(set(ast.literal_eval(comparator)))
        return found
    return []


def label_chain_surface_errors(*, root=ROOT):
    registry = _load_chain_registry()
    expected = {
        "known": set(registry.known_chains_for_release()),
        "table": set(registry.capability_chains("labels_table")),
    }
    errors = []
    for rel, kind, locator in LABEL_CHAIN_SURFACES:
        values = _surface_values(root / rel, locator)
        expected_count = int(locator.rsplit(":", 1)[1]) \
            if locator.startswith("membership:chain:") else 1
        if len(values) != expected_count:
            errors.append(f"labels surface {rel}:{locator} expected {expected_count} list(s), got {len(values)}")
            continue
        for actual in values:
            extra = actual - expected[kind]
            missing = expected[kind] - actual
            if extra:
                errors.append(f"labels surface {rel}:{locator} has unregistered chains {sorted(extra)}")
            if missing:
                label = "labels_table chains" if kind == "table" else "known chains"
                errors.append(f"labels surface {rel}:{locator} missing {label} {sorted(missing)}")
    return errors


def _suite_entries(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    entries = set()
    for node in tree.body:
        value = None
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "SUITE" for target in node.targets):
            value = node.value
        elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) \
                and node.target.id == "SUITE":
            value = node.value
        if value is not None:
            entries.update(_string_values(value, {}))
    return entries


def vertical_slice_errors(*, mapping=None, suite_path=None):
    registry = _load_chain_registry()
    mapping = dict(mapping or VERTICAL_SLICE_TESTS)
    suite_path = Path(suite_path or ROOT / "scripts/tests/run_all.py")
    mounted = _suite_entries(suite_path)
    formal = registry.formal_tier_chains()
    errors = []
    for chain, test_name in sorted(mapping.items()):
        if chain not in formal:
            errors.append(f"vertical slice mapping has non-formal chain: {chain}")
            continue
        if not (ROOT / "scripts/tests" / test_name).is_file():
            errors.append(f"vertical slice test file missing for {chain}: {test_name}")
        if test_name not in mounted:
            errors.append(f"vertical slice test for {chain} not mounted in run_all.SUITE: {test_name}")
    return errors


def _local_function_closure(tree, start):
    functions = {node.name: node for node in tree.body
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    if start not in functions:
        return set(), functions
    seen = set()
    pending = [start]
    while pending:
        name = pending.pop()
        if name in seen or name not in functions:
            continue
        seen.add(name)
        for node in _reachable_calls(functions[name]):
            called = _call_name(node.func).rsplit(".", 1)[-1]
            if called in functions and called not in seen:
                pending.append(called)
    return seen, functions


def _execution_imports(tree):
    """Map local import names to execution-capable qualified symbols."""
    aliases = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for item in node.names:
                if item.name in {"subprocess", "os"}:
                    aliases[item.asname or item.name] = item.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            for item in node.names:
                aliases[item.asname or item.name] = f"{node.module}.{item.name}"
    return aliases


def _function_local_bindings(function):
    """Collect conservative local rebinding names without entering child scopes."""
    names = {
        arg.arg for arg in (
            *function.args.posonlyargs,
            *function.args.args,
            *function.args.kwonlyargs,
        )
    }
    if function.args.vararg:
        names.add(function.args.vararg.arg)
    if function.args.kwarg:
        names.add(function.args.kwarg.arg)

    class Visitor(ast.NodeVisitor):
        def visit_Name(self, node):
            if isinstance(node.ctx, (ast.Store, ast.Del)):
                names.add(node.id)

        def visit_FunctionDef(self, node):
            names.add(node.name)
            return

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Lambda(self, _node):
            return

        def visit_ClassDef(self, node):
            names.add(node.name)
            return

        def visit_Import(self, node):
            for item in node.names:
                names.add(item.asname or item.name.partition(".")[0])

        def visit_ImportFrom(self, node):
            for item in node.names:
                if item.name != "*":
                    names.add(item.asname or item.name)

        def visit_ExceptHandler(self, node):
            if isinstance(node.name, str):
                names.add(node.name)
            self.generic_visit(node)

    visitor = Visitor()
    for statement in function.body:
        visitor.visit(statement)
    return frozenset(names)


def _execution_call_bindings(tree):
    """Map each call to bindings in its directly enclosing function scope."""
    bindings = {}
    stack = []

    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            stack.append(_function_local_bindings(node))
            try:
                for statement in node.body:
                    self.visit(statement)
            finally:
                stack.pop()

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Lambda(self, _node):
            return

        def visit_ClassDef(self, _node):
            return

        def visit_Call(self, node):
            if stack:
                bindings[id(node)] = stack[-1]
            self.generic_visit(node)

    Visitor().visit(tree)
    return bindings


def _resolved_call_name(call, imports):
    name = _call_name(call.func)
    head, dot, tail = name.partition(".")
    if not head or head not in imports:
        return None
    return imports[head] + (dot + tail if dot else "")


def _is_execution_primitive(call, imports, local_bindings=frozenset()):
    head = _call_name(call.func).partition(".")[0]
    if not head or head not in imports or head in local_bindings:
        return False
    name = _resolved_call_name(call, imports)
    return (name in {
                "subprocess.run", "subprocess.Popen",
                "subprocess.check_call", "subprocess.check_output",
                "formal_ready_test_harness.run_formal_script",
            }
            or name.startswith("subprocess.check_")
            or name.startswith("os.exec"))


def _local_function_executes(name, functions, imports, call_bindings, visiting=None):
    """Prove a local wrapper reaches an imported process execution primitive."""
    visiting = set() if visiting is None else visiting
    if name in visiting or name not in functions:
        return False
    visiting.add(name)
    try:
        for node in _reachable_calls(functions[name]):
            if _is_execution_primitive(node, imports, call_bindings.get(id(node), frozenset())):
                return True
            if isinstance(node.func, ast.Name) and node.func.id in functions \
                    and _local_function_executes(
                        node.func.id, functions, imports, call_bindings, visiting):
                return True
        return False
    finally:
        visiting.remove(name)


def _reachable_execution_evidence(function_names, functions, tree):
    """Return scripts in actual run calls plus producer fields in reachable specs.

    Static proof stops at a call name that resolves through a real module import
    and is not rebound anywhere in the call's directly enclosing function.  It
    does not prove that a process launches at runtime: dynamic exec dispatch,
    ``importlib.import_module``/``getattr`` indirection, and module-load
    monkeypatching are outside this AST guard and remain covered by the SUITE's
    loopback E2E harness.  Producer fields count only behind that controlled
    runner call, which validates and executes every registered spec producer.
    """
    executed = set()
    producers = set()
    imports = _execution_imports(tree)
    call_bindings = _execution_call_bindings(tree)
    for name in function_names:
        function = functions[name]
        for node in _reachable_calls(function):
            called = _call_name(node.func)
            local_wrapper = (isinstance(node.func, ast.Name)
                             and called in functions)
            executes = (_local_function_executes(
                            called, functions, imports, call_bindings)
                        if local_wrapper else _is_execution_primitive(
                            node, imports, call_bindings.get(id(node), frozenset())))
            if executes:
                for item in ast.walk(node):
                    if (isinstance(item, ast.Constant)
                            and isinstance(item.value, str)
                            and item.value.startswith("scripts/")
                            and item.value.endswith(".py")):
                        executed.add(item.value)
        for node in ast.walk(function):
            if isinstance(node, ast.Dict):
                for key, value in zip(node.keys, node.values):
                    if isinstance(key, ast.Constant) and key.value == "producer" \
                            and isinstance(value, ast.Constant) \
                            and isinstance(value.value, str):
                        producers.add(value.value)
    return executed, producers


def _default_formal_e2e_targets():
    path = ROOT / "scripts/lib/formal_capability_probes.py"
    spec = importlib.util.spec_from_file_location("invariant_formal_probes", path)
    module = importlib.util.module_from_spec(spec)
    original_path = list(sys.path)
    try:
        sys.path[:0] = [str(path.parent), str(ROOT)]
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = original_path
    key_to_chain = {
        "r9-eth-mainnet-vertical-slice": "eth",
        "r9-bsc-mainnet-vertical-slice": "bsc",
        "r9-base-mainnet-vertical-slice": "base",
        "r9-solana-pythia-mainnet-vertical-slice": "sol",
    }
    targets = {}
    for key, chain in key_to_chain.items():
        registered = module.VERTICAL_SLICE_EVIDENCE_TARGETS.get(key, ())
        if len(registered) != 1 or registered[0].count(":") != 1:
            targets[chain] = (None, None)
            continue
        module_name, function = registered[0].split(":", 1)
        targets[chain] = (ROOT / (module_name.replace(".", "/") + ".py"), function)
    return targets


def formal_e2e_provenance_errors(*, targets=None):
    """Require formal E2E targets to reach the runner and real producer specs."""
    targets = dict(targets or _default_formal_e2e_targets())
    errors = []
    for chain, (path, function) in sorted(targets.items()):
        if path is None or not Path(path).is_file() or not isinstance(function, str):
            errors.append(f"formal E2E target missing for {chain}")
            continue
        path = Path(path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        reachable, functions = _local_function_closure(tree, function)
        if not reachable:
            errors.append(f"formal E2E target function missing for {chain}: {function}")
            continue
        main_reachable, _ = _local_function_closure(tree, "main")
        if function not in main_reachable:
            errors.append(f"formal E2E target is not executed by module main for {chain}: {function}")
        executed, producers = _reachable_execution_evidence(reachable, functions, tree)
        runner = "scripts/report/reconciliation_report.py"
        if runner not in executed:
            errors.append(f"formal E2E target lacks real reconciliation runner for {chain}")
        # Spec producer declarations become execution evidence only behind the
        # real runner command, whose production contract rejects pre-existing
        # receipts and launches every registered producer itself.
        observed = executed | (producers if runner in executed else set())
        missing = FORMAL_E2E_REQUIRED_PRODUCERS.get(chain, frozenset()) - observed
        if missing:
            errors.append(
                f"formal E2E target lacks registered producer execution for {chain}: "
                f"{sorted(missing)}")
    return errors


def _static_truth(node):
    """Return True/False for literal truth tests, otherwise None."""
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        value = _static_truth(node.operand)
        return None if value is None else not value
    if isinstance(node, ast.BoolOp):
        values = [_static_truth(item) for item in node.values]
        if isinstance(node.op, ast.And):
            return False if False in values else True if all(value is True for value in values) \
                else None
        if isinstance(node.op, ast.Or):
            return True if True in values else False if all(value is False for value in values) \
                else None
    if isinstance(node, ast.Compare):
        try:
            values = [ast.literal_eval(item) for item in (node.left, *node.comparators)]
            outcomes = []
            for left, op, right in zip(values, node.ops, values[1:]):
                if isinstance(op, ast.Eq):
                    outcomes.append(left == right)
                elif isinstance(op, ast.NotEq):
                    outcomes.append(left != right)
                elif isinstance(op, ast.Lt):
                    outcomes.append(left < right)
                elif isinstance(op, ast.LtE):
                    outcomes.append(left <= right)
                elif isinstance(op, ast.Gt):
                    outcomes.append(left > right)
                elif isinstance(op, ast.GtE):
                    outcomes.append(left >= right)
                elif isinstance(op, ast.Is):
                    outcomes.append(left is right)
                elif isinstance(op, ast.IsNot):
                    outcomes.append(left is not right)
                elif isinstance(op, ast.In):
                    outcomes.append(left in right)
                elif isinstance(op, ast.NotIn):
                    outcomes.append(left not in right)
                else:
                    return None
            return all(outcomes)
        except (ValueError, TypeError):
            return None
    try:
        value = ast.literal_eval(node)
    except (ValueError, TypeError):
        return None
    if isinstance(value, (bool, int, float, str, bytes, tuple, list, set, dict)) \
            or value is None:
        return bool(value)
    return None


def _always_terminates(statement):
    if isinstance(statement, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
        return True
    if isinstance(statement, ast.If) and statement.body and statement.orelse:
        truth = _static_truth(statement.test)
        if truth is True:
            return _always_terminates(statement.body[-1])
        if truth is False:
            return _always_terminates(statement.orelse[-1])
        return (_always_terminates(statement.body[-1])
                and _always_terminates(statement.orelse[-1]))
    return False


def _reachable_calls(function):
    """Collect calls on statically reachable paths, following local helpers."""
    local_functions = {
        node.name: node for node in ast.walk(function)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node is not function
    }
    calls = []
    visiting = set()

    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, _node):
            return

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Lambda(self, _node):
            return

        def visit_Call(self, node):
            calls.append(node)
            if isinstance(node.func, ast.Name) and node.func.id in local_functions:
                visit_function(local_functions[node.func.id])
            self.generic_visit(node)

        def visit_If(self, node):
            self.visit(node.test)
            truth = _static_truth(node.test)
            if truth is not False:
                visit_block(node.body)
            if truth is not True:
                visit_block(node.orelse)

        def visit_While(self, node):
            self.visit(node.test)
            truth = _static_truth(node.test)
            if truth is not False:
                visit_block(node.body)
            visit_block(node.orelse)

        def visit_For(self, node):
            self.visit(node.target)
            self.visit(node.iter)
            visit_block(node.body)
            visit_block(node.orelse)

        visit_AsyncFor = visit_For

        def visit_With(self, node):
            for item in node.items:
                self.visit(item.context_expr)
                if item.optional_vars:
                    self.visit(item.optional_vars)
            visit_block(node.body)

        visit_AsyncWith = visit_With

        def visit_Try(self, node):
            visit_block(node.body)
            for handler in node.handlers:
                self.visit(handler.type) if handler.type else None
                visit_block(handler.body)
            visit_block(node.orelse)
            visit_block(node.finalbody)

    visitor = Visitor()

    def visit_block(statements):
        for statement in statements:
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            visitor.visit(statement)
            if _always_terminates(statement):
                break

    def visit_function(node):
        identity = id(node)
        if identity in visiting:
            return
        visiting.add(identity)
        try:
            visit_block(node.body)
        finally:
            visiting.remove(identity)

    visit_function(function)
    return calls


def failure_artifact_contract_errors(*, contracts=None, root=ROOT):
    """Require stale-sensitive formal producers to quarantine and emit ERROR."""
    contracts = tuple(contracts or FAILURE_ARTIFACT_CONTRACTS)
    errors = []
    for contract in contracts:
        raw_script = contract.get("script")
        path = Path(raw_script)
        if not path.is_absolute():
            path = Path(root) / path
        entrypoint = contract.get("entrypoint")
        expected = contract.get("canonical_artifacts")
        label = path.as_posix()
        if not path.is_file() or not isinstance(entrypoint, str):
            errors.append(f"failure artifact contract missing producer: {label}")
            continue
        if isinstance(expected, bool) or not isinstance(expected, int) or expected < 1:
            errors.append(f"failure artifact contract has invalid canonical count: {label}")
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        function = next((node for node in tree.body
                         if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                         and node.name == entrypoint), None)
        if function is None:
            errors.append(f"failure artifact entrypoint missing: {label}:{entrypoint}")
            continue
        calls = [_call_name(node.func) for node in _reachable_calls(function)]
        quarantine_count = sum(name.endswith("quarantine_current") for name in calls)
        if quarantine_count < expected:
            errors.append(
                f"failure artifact quarantine incomplete: {label} "
                f"expected={expected} got={quarantine_count}")
        if not any(name.endswith("publish_error_receipt") for name in calls):
            errors.append(f"failure artifact error receipt missing: {label}")
    return errors


def standalone_failure_artifact_producers():
    """Derive standalone stale-sensitive publishers from production source.

    A candidate must be directly executable and its reachable module call graph
    must contain both a success publication primitive and an ERROR side-receipt
    primitive.  This intentionally replaces the original three-name allowlist:
    a newly added publisher with the same semantics joins the denominator.
    """
    found = set()
    success_primitives = {"publish_txn", "publish_overwrite", "os.replace"}
    for path in production_files():
        if path.suffix != ".py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if not any(_is_main_guard(node) for node in tree.body):
            continue
        reachable, functions = _local_function_closure(tree, "main")
        calls = {
            _call_name(call.func)
            for name in reachable
            for call in _reachable_calls(functions[name])
        }
        suffixes = {name.rsplit(".", 1)[-1] for name in calls}
        has_success = bool(success_primitives.intersection(calls | suffixes))
        if has_success and "publish_error_receipt" in suffixes:
            found.add(_rel(path))
    return found


def failure_artifact_coverage_errors(*, coverage=None, shared_path=None):
    """Keep every formal producer and standalone stale-sensitive producer registered."""
    coverage = dict(coverage or FAILURE_ARTIFACT_COVERAGE)
    shared_path = Path(shared_path or ROOT / "scripts/report/shared_release_receipt.py")
    shared = _literal_assignments(
        shared_path, {"ACCOUNTING_PRODUCERS", "RECON_PRODUCERS"})
    if set(shared) != {"ACCOUNTING_PRODUCERS", "RECON_PRODUCERS"}:
        return ["failure artifact coverage cannot derive formal producer registries"]
    accounting = set(shared["ACCOUNTING_PRODUCERS"].values())
    reconciliation = {
        script for family in shared["RECON_PRODUCERS"].values()
        for producers in family.values() for script in producers
    }
    # Formal producers are already in the two release registries.  Every other
    # executable success+ERROR publisher is a standalone stale-sensitive entry.
    standalone = standalone_failure_artifact_producers() - accounting - reconciliation
    expected = accounting | reconciliation | standalone
    errors = []
    for missing in sorted(expected - set(coverage)):
        errors.append(f"formal producer failure artifacts unregistered: {missing}")
    for extra in sorted(set(coverage) - expected):
        errors.append(f"failure artifact registry has non-producer entry: {extra}")
    required_fields = {"canonical", "marker", "error", "protections"}
    for script, contract in sorted(coverage.items()):
        if not isinstance(contract, dict) or set(contract) != required_fields:
            errors.append(f"failure artifact roles invalid: {script}")
            continue
        if any(not isinstance(contract[field], str) or not contract[field].strip()
               for field in ("canonical", "marker", "error")):
            errors.append(f"failure artifact role name missing: {script}")
        protections = contract["protections"]
        if not isinstance(protections, tuple) or not protections:
            errors.append(f"failure artifact protections missing: {script}")
            continue
        if script in accounting and "fresh_status_receipt" not in protections:
            errors.append(f"accounting failure status protection missing: {script}")
        if script in reconciliation and "runner_fresh_receipt" not in protections:
            errors.append(f"runner fresh-receipt protection missing: {script}")
        if script in standalone and not ({"self_quarantine", "manual_stale_move"}
                                         & set(protections)):
            errors.append(f"standalone stale protection missing: {script}")
    return errors


def robinhood_inventory_errors(*, doc_path=None):
    doc_path = Path(doc_path or ROOT / "references/data-pipeline-robinhood.md")
    text = doc_path.read_text(encoding="utf-8")
    match = re.search(r"scripts/robinhood/` 当前 (\d+) 个普通文件：(\d+) 个 Python", text)
    if not match:
        return ["Robinhood inventory statement missing from active pipeline document"]
    files = [path for path in (ROOT / "scripts/robinhood").iterdir() if path.is_file()]
    python_files = [path for path in files if path.suffix == ".py"]
    claimed = (int(match.group(1)), int(match.group(2)))
    actual = (len(files), len(python_files))
    if claimed != actual:
        return [f"Robinhood inventory mismatch: documented={claimed}, actual={actual}"]
    return []


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
        name = _call_name(node.func)
        if name in {"os.replace", "os.link"} or name.endswith("publish_txn"):
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
    has_urllib = False
    has_httpx = False
    has_aiohttp = False
    has_solana_session = False
    curl_vars = set()
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
        if isinstance(value, (ast.List, ast.Tuple)) and value.elts \
                and isinstance(value.elts[0], ast.Constant) and value.elts[0].value == "curl":
            curl_vars.update(names)

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
            has_httpx |= any(alias.name == "httpx" for alias in node.names)
            has_aiohttp |= any(alias.name == "aiohttp" for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            has_requests |= node.module == "requests"
            has_net |= node.module == "net"
            has_httpx |= node.module == "httpx"
            has_aiohttp |= node.module == "aiohttp"
            has_solana_session |= node.module == "solana_attested_session"
        elif isinstance(node, ast.Call) and (
                _call_name(node.func).endswith(".urlopen") or _call_name(node.func) == "urlopen"):
            has_urllib = True
        elif isinstance(node, ast.Call) and _call_name(node.func) in {
                "subprocess.run", "subprocess.Popen"} and node.args:
            first = node.args[0]
            if isinstance(first, (ast.List, ast.Tuple)) and first.elts:
                cmd = first.elts[0]
                has_curl |= isinstance(cmd, ast.Constant) and cmd.value == "curl"
            elif isinstance(first, ast.Name):
                has_curl |= first.id in curl_vars
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
    if has_urllib:
        transports.add("urllib")
    if has_httpx:
        transports.add("httpx")
    if has_aiohttp:
        transports.add("aiohttp")
    if has_solana_session:
        transports.add("solana-attested-session")
    return producers, consumers, transports, atomic.locators


def scan_actual(*, shared_path=None):
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
    source_errors = []
    try:
        formal_entrypoints = registered_formal_entrypoints(shared_path=shared_path)
    except FormalEntrypointSourceError as exc:
        formal_entrypoints = []
        source_errors.append(str(exc))
    actual = {
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
        "formal_entrypoints": formal_entrypoints,
    }
    if source_errors:
        actual["_scanner_errors"] = source_errors
    return actual


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
    errors = list(actual.get("_scanner_errors", []))
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
    registered_formal = set(manifest.get("formal_entrypoints", []))
    for rel in sorted(set(actual["formal_entrypoints"]) - registered_formal):
        errors.append(f"formal_entrypoints: capability/producer registry point missing: {rel}")

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

    floors = manifest.get("minimum_counts")
    if not isinstance(floors, dict) or set(floors) != DENOMINATOR_KEYS:
        errors.append("minimum_counts must contain the five scanner denominators")
    else:
        current = counts(manifest)
        for key in sorted(DENOMINATOR_KEYS):
            floor = floors.get(key)
            if isinstance(floor, bool) or not isinstance(floor, int) or floor < 0:
                errors.append(f"minimum_counts: invalid floor for {key}")
            elif current[key] < floor:
                errors.append(
                    f"{key}: denominator shrank below floor {floor} -> {current[key]}")

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
    errors += bare_rpc_pool_errors()
    errors += main_exit_propagation_errors()
    errors += label_chain_surface_errors()
    errors += vertical_slice_errors()
    errors += formal_e2e_provenance_errors()
    errors += failure_artifact_contract_errors()
    errors += failure_artifact_coverage_errors()
    errors += robinhood_inventory_errors()
    return errors


def counts(manifest):
    return {
        "receipt_producers": sum(len(x["schemas"]) for x in manifest.get("receipt_producers", [])),
        "receipt_consumers": sum(len(x["schemas"]) for x in manifest.get("receipt_consumers", [])),
        "transport_calls": len(manifest.get("transport_calls", [])),
        "atomic_writes": len(manifest.get("atomic_writes", [])),
        "formal_entrypoints": len(manifest.get("formal_entrypoints", [])),
        "exceptions": len(manifest.get("exceptions", [])),
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
