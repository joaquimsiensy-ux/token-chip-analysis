#!/usr/bin/env python3
"""F-008: evm_v2 provenance directory and pre-replay set gate regressions.

Run with ``--red-only`` before the production fix to preserve the original
directory-as-file regression.  The full run covers containment, set equality,
pre-spawn rejection, source-pattern AST drift, and real multi-run parquet replay.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
REPORT = REPO / "scripts" / "report"
LIB = REPO / "scripts" / "lib"
sys.path.insert(0, str(REPORT))
sys.path.insert(0, str(LIB))

import handoff_manifest as handoff  # noqa: E402
import case_paths  # noqa: E402


CHECKS: list[str] = []
FAILS: list[str] = []
ZERO = "0x0000000000000000000000000000000000000000"
ENTITY = "0x00000000000000000000000000000000000000aa"
OTHER = "0x00000000000000000000000000000000000000bb"


def check(name: str, condition: bool, detail: str = "") -> None:
    CHECKS.append(name)
    if condition:
        print(f"PASS: {name}")
        return
    FAILS.append(name)
    suffix = f": {detail}" if detail else ""
    print(f"FAIL: {name}{suffix}")


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def file_record(path: Path, case: Path) -> dict:
    return {
        "path": path.relative_to(case).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def topic(address: str) -> str:
    return address[2:].lower().rjust(64, "0")


def amount(value: int) -> str:
    return "0x" + f"{value:064x}"


def write_run(run_dir: Path, block: int, sender: str, receiver: str, value: int) -> None:
    import duckdb

    run_dir.mkdir(parents=True)
    con = duckdb.connect()
    try:
        con.execute("""CREATE TABLE logs(
            transaction_hash VARCHAR, log_index BIGINT, block_number BIGINT,
            topic1 VARCHAR, topic2 VARCHAR, data VARCHAR)""")
        con.execute("INSERT INTO logs VALUES (?, ?, ?, ?, ?, ?)", [
            f"0x{block:064x}", 0, block, topic(sender), topic(receiver), amount(value)])
        con.execute("CREATE TABLE blocks(number BIGINT, timestamp VARCHAR)")
        con.execute("INSERT INTO blocks VALUES (?, ?)", [block, str(1_700_000_000 + block)])
        con.execute(f"COPY logs TO '{run_dir / 'logs.parquet'}' (FORMAT PARQUET)")
        con.execute(f"COPY blocks TO '{run_dir / 'blocks.parquet'}' (FORMAT PARQUET)")
    finally:
        con.close()


def make_real_case(case: Path) -> tuple[dict, dict, Path]:
    edge_dir = case / "data" / "ethereum" / "v2"
    write_run(edge_dir / "run_1", 1, ZERO, ENTITY, 100)
    write_run(edge_dir / "run_2", 2, ENTITY, OTHER, 10)
    (edge_dir / "run_1" / "README").write_text("pattern-external file is allowed\n", encoding="utf-8")

    entity_file = case / "s2_entity_members.json"
    labels_file = case / "fixture_labels.json"
    write_json(entity_file, {"E1": [ENTITY]})
    write_json(labels_file, {OTHER: {"kind": "facility", "name": "fixture"}})

    source_paths = sorted(
        [p for p in edge_dir.glob("run_*/logs.parquet")]
        + [p for p in edge_dir.glob("run_*/blocks.parquet")])
    data_map = {"files": [{"path": p.relative_to(case).as_posix()} for p in source_paths]}
    write_json(case / "data_map.json", data_map)
    manifest = {
        "run_id": "f008-fixture",
        "scope": {"cutoff_utc": "2026-08-24T00:00:00Z", "frozen_block": 10,
                  "denominators": {"total_supply_raw": "1000"}},
        "artifacts": [{"path": p.relative_to(case).as_posix()} for p in source_paths],
    }
    write_json(case / "handoff_manifest.json", manifest)

    ledger_path = case / "provenance_ledger.json"
    cmd = [
        sys.executable, str(REPORT / "entity_source_trace.py"),
        "--edges-evm-v2", "data/ethereum/v2",
        "--total-supply", "1000",
        "--entity-file", str(entity_file),
        "--labels-file", str(labels_file),
        "--out", str(ledger_path),
    ]
    proc = subprocess.run(cmd, cwd=case, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"fixture provenance failed exit={proc.returncode}: {proc.stdout}{proc.stderr}")
    return json.loads(ledger_path.read_text(encoding="utf-8")), manifest, entity_file


def validate(case: Path, ledger: dict, manifest: dict, entity_file: Path) -> list[str]:
    return handoff.validate_and_replay_provenance(
        str(case), ledger, str(case / "provenance_ledger.json"),
        str(entity_file), manifest)


def test_real_multi_run(root: Path) -> tuple[Path, dict, dict, Path]:
    case = root / "real_positive"
    case.mkdir()
    ledger, manifest, entity_file = make_real_case(case)
    failures = validate(case, ledger, manifest, entity_file)
    check("real multi-run evm_v2 provenance replay", failures == [], repr(failures))
    return case, ledger, manifest, entity_file


def clone_fixture(root: Path, name: str, base: Path, ledger: dict, manifest: dict):
    case = root / name
    shutil.copytree(base, case, symlinks=True)
    return case, copy.deepcopy(ledger), copy.deepcopy(manifest), case / "s2_entity_members.json"


def reject_before_replay(case: Path, ledger: dict, manifest: dict, entity_file: Path):
    calls = {"mkstemp": 0, "run": 0}
    old_mkstemp = handoff.tempfile.mkstemp
    old_run = handoff.subprocess.run
    before = set(case.glob(".provenance-replay-*"))

    def forbidden_mkstemp(*args, **kwargs):
        calls["mkstemp"] += 1
        raise AssertionError("replay tempfile created before rejection")

    def forbidden_run(*args, **kwargs):
        calls["run"] += 1
        raise AssertionError("replay subprocess started before rejection")

    handoff.tempfile.mkstemp = forbidden_mkstemp
    handoff.subprocess.run = forbidden_run
    try:
        failures = validate(case, ledger, manifest, entity_file)
    except AssertionError as exc:
        failures = [str(exc)]
    finally:
        handoff.tempfile.mkstemp = old_mkstemp
        handoff.subprocess.run = old_run
    after = set(case.glob(".provenance-replay-*"))
    clean = calls == {"mkstemp": 0, "run": 0} and before == after
    return failures, clean


def add_bound_record(case: Path, ledger: dict, manifest: dict, path: Path) -> dict:
    rec = file_record(path, case)
    ledger["input_binding"]["source"]["files"].append(rec)
    ledger["input_binding"]["data_map"]["paths"].append(rec["path"])
    manifest["artifacts"].append({"path": rec["path"]})
    return rec


def check_rejection(name: str, fixture, mutate) -> None:
    case, ledger, manifest, entity_file = fixture
    mutate(case, ledger, manifest)
    failures, pre_spawn = reject_before_replay(case, ledger, manifest, entity_file)
    check(name, bool(failures) and pre_spawn, repr(failures))


def test_set_and_argument_attacks(root: Path, base: Path, ledger: dict, manifest: dict) -> None:
    def fixture(name):
        return clone_fixture(root, name, base, ledger, manifest)

    extra_case, extra_ledger, extra_manifest, extra_entity = fixture("extra_hit")
    (extra_case / "data/ethereum/v2/run_evil").mkdir()
    shutil.copy2(extra_case / "data/ethereum/v2/run_1/logs.parquet",
                 extra_case / "data/ethereum/v2/run_evil/logs.parquet")
    failures, clean = reject_before_replay(
        extra_case, extra_ledger, extra_manifest, extra_entity)
    check("unregistered run_evil/logs.parquet rejected pre-spawn", bool(failures) and clean, repr(failures))

    case, led, man, ep = fixture("symlink_run")
    outside = root / "outside_run"
    outside.mkdir()
    shutil.copy2(case / "data/ethereum/v2/run_1/logs.parquet", outside / "logs.parquet")
    os.symlink(outside, case / "data/ethereum/v2/run_evil")
    failures, clean = reject_before_replay(case, led, man, ep)
    check("symlink run directory rejected pre-spawn", bool(failures) and clean, repr(failures))

    def delete_registered(c, l, _m):
        (c / l["input_binding"]["source"]["files"][0]["path"]).unlink()
    check_rejection("deleted registered file rejected pre-spawn", fixture("deleted"), delete_registered)

    case, led, man, ep = fixture("descendant_symlink")
    victim = case / led["input_binding"]["source"]["files"][0]["path"]
    outside_file = root / "outside.parquet"
    shutil.copy2(victim, outside_file)
    victim.unlink()
    os.symlink(outside_file, victim)
    failures, clean = reject_before_replay(case, led, man, ep)
    check("descendant parquet symlink rejected pre-spawn", bool(failures) and clean, repr(failures))

    argument_cases = {
        "absolute": str((base / "data/ethereum/v2").resolve()),
        "dotdot": "data/ethereum/../ethereum/v2",
        "ordinary-file": "data/ethereum/v2/run_1/logs.parquet",
        "empty": "",
        "dot": ".",
        "asterisk": "data/ethereum/v2/*",
        "question": "data/ethereum/v2?",
        "left-bracket": "data/ethereum/[v2",
        "right-bracket": "data/ethereum/v2]",
        "single-quote": "data/ethereum/v2'",
        "backslash": "data\\ethereum\\v2",
        "newline": "data/ethereum/v2\n",
        "control": "data/ethereum/v2\x01",
    }
    for label, argument in argument_cases.items():
        def mutate(_c, l, _m, value=argument):
            l["input_binding"]["source"]["argument"] = value
        check_rejection(f"argument {label} rejected pre-spawn", fixture(f"arg_{label}"), mutate)

    case, led, man, ep = fixture("arg_c1_control")
    led["input_binding"]["source"]["argument"] = "data/ethereum/v2\u0085"
    failures, clean = reject_before_replay(case, led, man, ep)
    check(
        "argument C1 U+0085 rejected by character gate pre-spawn",
        clean and any("含 glob/SQL/控制字符" in failure for failure in failures),
        repr(failures),
    )

    case, led, man, ep = fixture("arg_mid_symlink")
    os.symlink(case / "data/ethereum", case / "linked")
    led["input_binding"]["source"]["argument"] = "linked/v2"
    failures, clean = reject_before_replay(case, led, man, ep)
    check("argument middle symlink rejected pre-spawn", bool(failures) and clean, repr(failures))

    def duplicate(_c, l, _m):
        l["input_binding"]["source"]["files"].append(
            copy.deepcopy(l["input_binding"]["source"]["files"][0]))
    check_rejection("duplicate source.files path rejected pre-spawn", fixture("duplicate"), duplicate)

    def non_object(_c, l, _m):
        l["input_binding"]["source"]["files"].append("not-an-object")
    check_rejection("non-object source.files record rejected pre-spawn",
                    fixture("non_object"), non_object)

    def non_string_path(_c, l, _m):
        l["input_binding"]["source"]["files"][0]["path"] = 7
    check_rejection("non-string source.files path rejected pre-spawn",
                    fixture("non_string_path"), non_string_path)

    def outside_pattern(c, l, m):
        extra = c / "data/ethereum/v2/run_1/README"
        add_bound_record(c, l, m, extra)
    check_rejection("registered pattern-external file rejected pre-spawn",
                    fixture("registered_readme"), outside_pattern)


def test_safe_case_dir(root: Path) -> None:
    safe_case_dir = getattr(case_paths, "safe_case_dir", None)
    check("safe_case_dir exported", callable(safe_case_dir))
    if not callable(safe_case_dir):
        return
    case = root / "safe_dir"
    (case / "a/b").mkdir(parents=True)
    (case / "a/file").write_text("x", encoding="utf-8")
    outside = root / "safe_outside"
    outside.mkdir()
    os.symlink(outside, case / "linked")
    check("safe_case_dir legal directory", safe_case_dir(case, "a/b") == (case / "a/b").resolve())
    invalid = ["", " ", str((case / "a/b").resolve()), "a//b", "a/./b", "a/../b",
               "linked", "a/file", "missing"]
    for rel in invalid:
        try:
            safe_case_dir(case, rel)
        except ValueError:
            rejected = True
        else:
            rejected = False
        check(f"safe_case_dir rejects {rel!r}", rejected)
    check("safe_case_file still accepts regular file",
          case_paths.safe_case_file(case, "a/file") == (case / "a/file").resolve())
    try:
        case_paths.safe_case_file(case, "a/b")
    except ValueError:
        file_rejects_dir = True
    else:
        file_rejects_dir = False
    check("safe_case_file still rejects directory", file_rejects_dir)


def join_shape(node: ast.AST, context: str):
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
        raise AssertionError(f"{context}: glob argument is not os.path.join(...)")
    func = node.func
    if func.attr != "join" or not isinstance(func.value, ast.Attribute):
        raise AssertionError(f"{context}: glob argument is not os.path.join(...)")
    if not isinstance(func.value.value, ast.Name) or func.value.value.id != "os" \
            or func.value.attr != "path":
        raise AssertionError(f"{context}: glob argument is not os.path.join(...)")
    if node.keywords or len(node.args) != 3 \
            or not all(isinstance(x, ast.Constant) and isinstance(x.value, str)
                       for x in node.args[1:]):
        raise AssertionError(f"{context}: os.path.join shape is not frozen")
    return node.args[0], node.args[1].value, node.args[2].value


def function_node(path: Path, name: str) -> ast.FunctionDef:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    matches = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]
    if len(matches) != 1:
        raise AssertionError(f"{path.name}.{name} AST shape changed")
    return matches[0]


def glob_calls(function: ast.FunctionDef) -> list[ast.Call]:
    return [
        node for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "glob"
        and node.func.attr == "glob"
    ]


def expected_patterns() -> set[tuple[str, str]]:
    prefix = handoff.EVM_V2_RUN_PREFIX + "*"
    return {(prefix, name) for name in handoff.EVM_V2_EDGE_NAMES}


def guard_trace_globs(trace: ast.FunctionDef) -> None:
    calls = glob_calls(trace)
    if len(calls) != 3:
        raise AssertionError(f"source_binding glob.glob count changed: {len(calls)}")
    sol_count = 0
    evm_shapes = []
    for index, call in enumerate(calls):
        if call.keywords or len(call.args) != 1:
            raise AssertionError(f"source_binding glob[{index}] call shape changed")
        argument = call.args[0]
        if isinstance(argument, ast.Attribute) \
                and isinstance(argument.value, ast.Name) \
                and argument.value.id == "a" and argument.attr == "edges_sol":
            sol_count += 1
            continue
        shape = join_shape(argument, f"source_binding glob[{index}]")
        base, prefix, name = shape
        if not isinstance(base, ast.Attribute) \
                or not isinstance(base.value, ast.Name) or base.value.id != "a" \
                or base.attr != "edges_evm_v2":
            raise AssertionError(f"source_binding glob[{index}] base changed")
        evm_shapes.append((prefix, name))
    if sol_count != 1 or len(evm_shapes) != 2 \
            or set(evm_shapes) != expected_patterns():
        raise AssertionError(
            f"source_binding frozen glob set changed: sol={sol_count}, evm={evm_shapes!r}"
        )


def reject_string_bindings(wave: ast.FunctionDef, protected: set[str]) -> None:
    """Reject binding forms whose identifier is not represented by ast.Name."""
    for node in ast.walk(wave):
        names: list[str] = []
        if isinstance(node, ast.arg):
            names = [node.arg]
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                and node is not wave:
            names = [node.name]
        elif isinstance(node, ast.alias):
            names = [node.asname or node.name.split(".", 1)[0]]
        elif isinstance(node, ast.ExceptHandler) and isinstance(node.name, str):
            names = [node.name]
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            names = list(node.names)
        elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and isinstance(node.name, str):
            names = [node.name]
        elif isinstance(node, ast.MatchMapping) and isinstance(node.rest, str):
            names = [node.rest]
        elif type(node).__name__ in {"TypeVar", "ParamSpec", "TypeVarTuple"}:
            name = getattr(node, "name", None)
            if isinstance(name, str):
                names = [name]
        collision = protected.intersection(names)
        if collision:
            raise AssertionError(
                "load_evm_v2 unexpected identifier binding/declaration: "
                f"{type(node).__name__} {sorted(collision)}"
            )


def assign_target_signature(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, (ast.Tuple, ast.List)):
        return ",".join(assign_target_signature(item) for item in node.elts)
    raise AssertionError(
        f"load_evm_v2 protected read belongs to unsupported assignment target: "
        f"{type(node).__name__}"
    )


def owning_statement(node: ast.AST,
                     parents: dict[ast.AST, ast.AST]) -> ast.stmt:
    current = node
    while current in parents:
        current = parents[current]
        if isinstance(current, ast.stmt):
            return current
    raise AssertionError("load_evm_v2 protected read has no owning statement")


def call_signature(call: ast.Call) -> str:
    func = call.func
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        return f"{func.value.id}.{func.attr}"
    raise AssertionError(
        f"load_evm_v2 protected read belongs to unsupported call: {ast.dump(func)}"
    )


def read_parquet_signature(node: ast.Name,
                           parents: dict[ast.AST, ast.AST]) -> tuple[str, ...]:
    formatted = parents.get(node)
    joined = parents.get(formatted)
    if not isinstance(formatted, ast.FormattedValue) \
            or formatted.value is not node \
            or formatted.conversion != -1 \
            or formatted.format_spec is not None \
            or not isinstance(joined, ast.JoinedStr):
        raise AssertionError(
            f"load_evm_v2 {node.id} read is not a frozen SQL f-string slot"
        )
    try:
        value_index = joined.values.index(formatted)
    except ValueError:
        raise AssertionError(
            f"load_evm_v2 {node.id} formatted value is detached from its f-string"
        )
    if value_index == 0 or value_index + 1 >= len(joined.values):
        raise AssertionError(
            f"load_evm_v2 {node.id} SQL f-string slot lacks frozen neighbors"
        )
    before = joined.values[value_index - 1]
    after = joined.values[value_index + 1]
    if not isinstance(before, ast.Constant) or not isinstance(before.value, str) \
            or not before.value.endswith("read_parquet('") \
            or not isinstance(after, ast.Constant) or not isinstance(after.value, str) \
            or not after.value.startswith("',"):
        raise AssertionError(
            f"load_evm_v2 {node.id} read is outside a frozen read_parquet slot"
        )
    formatted_values = [value for value in joined.values if isinstance(value, ast.FormattedValue)]
    formatted_index = formatted_values.index(formatted)

    statement = owning_statement(node, parents)
    if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
        raise AssertionError(
            f"load_evm_v2 {node.id} SQL read statement changed: "
            f"{type(statement).__name__}"
        )
    statement_shape = f"Assign[{assign_target_signature(statement.targets[0])}]"

    joined_parent = parents.get(joined)
    if isinstance(joined_parent, ast.Call):
        if joined_parent.keywords or joined not in joined_parent.args:
            raise AssertionError(
                f"load_evm_v2 {node.id} SQL call argument shape changed"
            )
        call_shape = call_signature(joined_parent)
        slot_shape = f"arg[{joined_parent.args.index(joined)}]"
    elif joined_parent is statement and statement.value is joined:
        call_shape = "direct-fstring"
        slot_shape = "value"
    else:
        raise AssertionError(
            f"load_evm_v2 {node.id} SQL f-string owner changed: "
            f"{type(joined_parent).__name__}"
        )
    return (
        node.id,
        statement_shape,
        call_shape,
        slot_shape,
        f"fstring[{formatted_index}]",
    )


def consumption_signature(node: ast.Name, glob_argument: ast.Name,
                          parents: dict[ast.AST, ast.AST]) -> tuple[str, ...]:
    if node is glob_argument:
        call = parents.get(node)
        statement = owning_statement(node, parents)
        if not isinstance(call, ast.Call) or call.keywords \
                or len(call.args) != 1 or call.args[0] is not node \
                or call_signature(call) != "glob.glob" \
                or not isinstance(statement, ast.If):
            raise AssertionError("load_evm_v2 glob.glob logs consumption slot changed")
        return (node.id, "If", "glob.glob", "arg[0]")
    return read_parquet_signature(node, parents)


def guard_wave_globs(wave: ast.FunctionDef) -> None:
    protected = {"logs", "blocks"}
    parents = {child: node for node in ast.walk(wave) for child in ast.iter_child_nodes(node)}
    reject_string_bindings(wave, protected)

    joins = [
        node for node in ast.walk(wave)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "join"
        and isinstance(node.func.value, ast.Attribute)
        and isinstance(node.func.value.value, ast.Name)
        and node.func.value.value.id == "os"
        and node.func.value.attr == "path"
    ]
    if len(joins) != 2:
        raise AssertionError(f"load_evm_v2 os.path.join count changed: {len(joins)}")
    assignments: dict[str, tuple[ast.AST, str, str]] = {}
    reads: dict[str, list[ast.Name]] = {name: [] for name in protected}
    for node in ast.walk(wave):
        if not isinstance(node, ast.Name) or node.id not in protected:
            continue
        parent = parents.get(node)
        if isinstance(node.ctx, ast.Load):
            reads[node.id].append(node)
            continue
        if isinstance(node.ctx, ast.Store) \
                and isinstance(parent, ast.Assign) \
                and parent in wave.body \
                and len(parent.targets) == 1 \
                and parent.targets[0] is node \
                and parent.type_comment is None:
            if node.id in assignments:
                raise AssertionError(f"load_evm_v2 duplicate {node.id} definition")
            assignments[node.id] = join_shape(
                parent.value, f"load_evm_v2 {node.id} definition"
            )
            continue
        raise AssertionError(
            f"load_evm_v2 unexpected {node.id} binding/context: "
            f"{type(parent).__name__}/{type(node.ctx).__name__}"
        )
    if set(assignments) != {"logs", "blocks"}:
        raise AssertionError(f"load_evm_v2 pattern definitions changed: {sorted(assignments)}")
    expected_definitions = {
        "logs": ("run_*", "logs.parquet"),
        "blocks": ("run_*", "blocks.parquet"),
    }
    for name, expected in expected_definitions.items():
        base, prefix, edge_name = assignments[name]
        if not isinstance(base, ast.Name) or base.id != "dir_":
            raise AssertionError(f"load_evm_v2 {name} base changed")
        if (prefix, edge_name) != expected:
            raise AssertionError(
                f"load_evm_v2 {name} pattern mapping changed: "
                f"{(prefix, edge_name)!r} != {expected!r}"
            )

    calls = glob_calls(wave)
    if len(calls) != 1 or calls[0].keywords or len(calls[0].args) != 1 \
            or not isinstance(calls[0].args[0], ast.Name) \
            or calls[0].args[0].id != "logs":
        raise AssertionError("load_evm_v2 glob.glob consumers changed")

    glob_argument = calls[0].args[0]
    actual_consumptions = [
        consumption_signature(node, glob_argument, parents)
        for name in ("logs", "blocks")
        for node in reads[name]
    ]
    expected_consumptions = [
        ("logs", "If", "glob.glob", "arg[0]"),
        ("logs", "Assign[n_hi,mx]", "con.execute", "arg[0]", "fstring[0]"),
        ("logs", "Assign[body]", "direct-fstring", "value", "fstring[1]"),
        ("logs", "Assign[spans]", "con.execute", "arg[0]", "fstring[0]"),
        ("blocks", "Assign[body]", "direct-fstring", "value", "fstring[2]"),
    ]
    if sorted(actual_consumptions) != sorted(expected_consumptions):
        raise AssertionError(
            "load_evm_v2 exact consumption signatures changed: "
            f"{actual_consumptions!r}"
        )


def mutated_wave(injection: str) -> ast.FunctionDef:
    path = REPORT / "wave_scan.py"
    source = path.read_text(encoding="utf-8")
    wave = function_node(path, "load_evm_v2")
    definitions = [
        node for node in wave.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id in {"logs", "blocks"}
    ]
    if len(definitions) != 2 or any(node.end_lineno is None for node in definitions):
        raise AssertionError("load_evm_v2 mutation anchor changed")
    lines = source.splitlines()
    insert_after = max(node.end_lineno for node in definitions)
    lines.insert(insert_after, "    " + injection)
    mutated = ast.parse("\n".join(lines) + "\n", filename=f"{path}:{injection}")
    matches = [
        node for node in mutated.body
        if isinstance(node, ast.FunctionDef) and node.name == "load_evm_v2"
    ]
    if len(matches) != 1:
        raise AssertionError("mutated load_evm_v2 AST shape changed")
    return matches[0]


def wave_negative_rejected(injection: str) -> bool:
    try:
        guard_wave_globs(mutated_wave(injection))
    except AssertionError:
        return True
    return False


def mutated_wave_ast(mutate) -> ast.FunctionDef:
    wave = copy.deepcopy(function_node(REPORT / "wave_scan.py", "load_evm_v2"))
    mutate(wave)
    return wave


def swap_wave_file_mapping(wave: ast.FunctionDef) -> None:
    definitions = {
        node.targets[0].id: node
        for node in wave.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id in {"logs", "blocks"}
    }
    if set(definitions) != {"logs", "blocks"}:
        raise AssertionError("load_evm_v2 file-mapping mutation anchor changed")
    for name, other in (("logs", "blocks.parquet"), ("blocks", "logs.parquet")):
        value = definitions[name].value
        if not isinstance(value, ast.Call) or len(value.args) != 3 \
                or not isinstance(value.args[2], ast.Constant):
            raise AssertionError("load_evm_v2 file-mapping mutation shape changed")
        value.args[2].value = other


def swap_wave_body_sql_slots(wave: ast.FunctionDef) -> None:
    bodies = [
        node for node in wave.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "body"
        and isinstance(node.value, ast.JoinedStr)
    ]
    if len(bodies) != 1:
        raise AssertionError("load_evm_v2 body SQL mutation anchor changed")
    slots = [
        value.value for value in bodies[0].value.values
        if isinstance(value, ast.FormattedValue)
        and isinstance(value.value, ast.Name)
        and value.value.id in {"logs", "blocks"}
    ]
    if [node.id for node in slots] != ["logs", "blocks"]:
        raise AssertionError("load_evm_v2 body SQL slots changed")
    slots[0].id, slots[1].id = slots[1].id, slots[0].id


def wave_ast_mutation_rejected(mutate) -> bool:
    try:
        guard_wave_globs(mutated_wave_ast(mutate))
    except AssertionError:
        return True
    return False


def test_ast_source_guard() -> None:
    try:
        wave = function_node(REPORT / "wave_scan.py", "load_evm_v2")
        guard_wave_globs(wave)
        check("AST source guard wave_scan.load_evm_v2 frozen definitions and consumers", True)

        trace = function_node(REPORT / "entity_source_trace.py", "source_binding")
        guard_trace_globs(trace)
        check("AST source guard entity_source_trace.source_binding all glob calls", True)

        negative = ast.parse("""
def source_binding(a, case_dir, edge_source_binding=None):
    if a.edges_sol:
        files = sorted(glob.glob(a.edges_sol))
    elif a.edges_evm_v2:
        files = sorted(glob.glob(os.path.join(a.edges_evm_v2, "run_*", "logs.parquet")))
        files += sorted(glob.glob(os.path.join(a.edges_evm_v2, "run_*", "blocks.parquet")))
        files += sorted(glob.glob(a.edges_evm_v2 + "/run_*/extra.parquet"))
""").body[0]
        try:
            guard_trace_globs(negative)
        except AssertionError:
            negative_rejected = True
        else:
            negative_rejected = False
        check("AST source guard rejects concatenated third glob self-negative", negative_rejected)
        check("AST wave guard rejects logs AugAssign self-negative",
              wave_negative_rejected('logs += "/unexpected"'))
        check("AST wave guard rejects blocks alias consumption self-negative",
              wave_negative_rejected("b2 = blocks"))
        check("AST wave guard rejects swapped logs/blocks file mapping self-negative",
              wave_ast_mutation_rejected(swap_wave_file_mapping))
        check("AST wave guard rejects swapped logs/blocks SQL slots self-negative",
              wave_ast_mutation_rejected(swap_wave_body_sql_slots))
    except (AssertionError, AttributeError, OSError, SyntaxError, TypeError) as exc:
        check("AST source guard fail-closed", False, str(exc))


def test_mock_legacy_kinds(root: Path, base: Path, ledger: dict, manifest: dict) -> None:
    for kind in ("sol", "duckdb"):
        case, led, man, ep = clone_fixture(root, f"mock_{kind}", base, ledger, manifest)
        source = led["input_binding"]["source"]
        source["kind"] = kind
        source["argument"] = source["files"][0]["path"]
        if kind == "sol":
            source["cache_meta"] = source["files"][1]["path"]
            source["mint"] = "fixture-mint"
        old_run = handoff.subprocess.run
        calls = []

        def fake_run(cmd, **_kwargs):
            calls.append(cmd)
            out = Path(cmd[cmd.index("--out") + 1])
            write_json(out, led)
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        handoff.subprocess.run = fake_run
        try:
            failures = validate(case, led, man, ep)
        finally:
            handoff.subprocess.run = old_run
        check(f"{kind} replay dispatch remains green", failures == [] and len(calls) == 1,
              repr(failures))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--red-only", action="store_true")
    args = ap.parse_args()
    with tempfile.TemporaryDirectory(prefix="f008_") as tmp:
        root = Path(tmp)
        base, ledger, manifest, _ = test_real_multi_run(root)
        if not args.red_only:
            test_set_and_argument_attacks(root, base, ledger, manifest)
            test_safe_case_dir(root)
            test_ast_source_guard()
            test_mock_legacy_kinds(root, base, ledger, manifest)
    print(f"SUMMARY: {len(CHECKS) - len(FAILS)}/{len(CHECKS)} PASS")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
