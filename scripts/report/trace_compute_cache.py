"""Confirmation-free trace computations and separately authenticated P4 replay.

Neither namespace stores a publishable/PASS verdict. Source hashes must be built
from the current files before lookup and checked again before saving a result.
P4 may only populate its namespace after a real cache-disabled replay.
"""
import ast
import copy
import hashlib
import types
import os
from pathlib import Path
import sys

LIB = Path(__file__).resolve().parent.parent / "lib"
sys.path.insert(0, str(LIB))
from content_cache import CacheIntegrityError, CacheStore, canonical_bytes, emit_metric

COMPUTE_SCHEMA = "trace-computation/v1"
PRODUCER_NAMESPACE = "trace-computation-v1"
INDEPENDENT_NAMESPACE = "trace-independent-replay-v1"


def algorithm_dependency_paths():
    report = Path(__file__).resolve().parent
    scripts = report.parent
    return {
        "entity_source_trace.py": report / "entity_source_trace.py",
        "wave_scan.py": report / "wave_scan.py",
        "handoff_manifest.py": report / "handoff_manifest.py",
        "trace_compute_cache.py": report / "trace_compute_cache.py",
        "content_cache.py": scripts / "lib" / "content_cache.py",
        "solana_edge_store.py": scripts / "lib" / "solana_edge_store.py",
        "wave_contract.py": scripts / "lib" / "wave_contract.py",
        "sqd_cache_identity.py": scripts / "solana" / "sqd_cache_identity.py",
        "spl_edge_core.py": scripts / "solana" / "spl_edge_core.py",
        "producer_history.py": scripts / "lib" / "producer_history.py",
    }



class AlgorithmRuntimeDriftError(ValueError):
    """The loaded algorithm cannot truthfully bind the current disk version."""


# Capture bytes during import, before any caller can build its first cache key.
# An unchanged mtime, a new key, or --compute-cache-mode off cannot repair stale
# function objects. Restart the process instead of rebinding them to new bytes.
_IMPORTED_ALGORITHM_BYTES = {
    str(path.resolve()): path.read_bytes()
    for path in algorithm_dependency_paths().values()
}
_IMPORTED_ALGORITHM_SHA = {
    path: hashlib.sha256(data).hexdigest()
    for path, data in _IMPORTED_ALGORITHM_BYTES.items()
}
_LOADED_ALGORITHMS = {}


def _live_algorithm_state(namespace):
    """Process-local guard for functions, class methods and public constants."""
    state = {}
    for name, value in tuple(namespace.items()):
        if isinstance(value, types.FunctionType) and value.__module__ == namespace["__name__"]:
            state[name] = (value.__code__, repr(value.__defaults__),
                           repr(value.__kwdefaults__))
        elif isinstance(value, type) and value.__module__ == namespace["__name__"]:
            methods = {}
            for key, member in vars(value).items():
                if isinstance(member, (staticmethod, classmethod)):
                    member = member.__func__
                if isinstance(member, types.FunctionType):
                    methods[key] = (member.__code__, repr(member.__defaults__),
                                    repr(member.__kwdefaults__))
            state[name] = (tuple(base.__qualname__ for base in value.__bases__), methods)
        elif name.isupper() and not name.startswith("_"):
            state[name] = repr(value)
    return state


def register_loaded_algorithm(namespace, module_code):
    """Register at module end, before main; compilation is read-only, never exec."""
    path = str(Path(namespace["__file__"]).resolve())
    source = _IMPORTED_ALGORITHM_BYTES[path]
    expected = compile(source, module_code.co_filename, "exec", dont_inherit=True,
                       optimize=sys.flags.optimize)
    # Full module code also binds constants and catches source changes between
    # Python compiling this module and the shared import snapshot being made.
    _LOADED_ALGORITHMS[path] = {
        "namespace": namespace,
        # Code equality compares bytecode/constants structurally. Marshal's
        # reference encoding can differ between separately compiled objects.
        "source_matches_loaded_module": expected == module_code,
        "live_state": _live_algorithm_state(namespace),
    }


_SNAPSHOT_CODE = {}
_SNAPSHOT_AST = {}


def _snapshot_metadata(path, filename):
    key = (path, filename)
    if key not in _SNAPSHOT_CODE:
        code = compile(_IMPORTED_ALGORITHM_BYTES[path], filename, "exec",
                       dont_inherit=True, optimize=sys.flags.optimize)
        codes = {}
        def collect(item):
            codes.setdefault((item.co_name, item.co_firstlineno), []).append(item)
            for value in item.co_consts:
                if isinstance(value, types.CodeType):
                    collect(value)
        collect(code)
        _SNAPSHOT_CODE[key] = codes
    if path not in _SNAPSHOT_AST:
        tree = ast.parse(_IMPORTED_ALGORITHM_BYTES[path], filename=filename)
        definitions = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                line = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
                definitions[(getattr(node, "name", "<lambda>"), line)] = node
        _SNAPSHOT_AST[path] = (tree, definitions)
    return _SNAPSHOT_CODE[key], _SNAPSHOT_AST[path]


def _same_literal(actual, expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(actual, (tuple, list)):
        return len(actual) == len(expected) and all(
            _same_literal(a, b) for a, b in zip(actual, expected))
    if isinstance(actual, dict):
        return actual.keys() == expected.keys() and all(
            _same_literal(actual[k], expected[k]) for k in actual)
    return actual == expected


def _snapshot_constant(node, known):
    """Evaluate only declarative literals; never execute a module or arbitrary call."""
    if isinstance(node, ast.Name) and node.id in known:
        return known[node.id]
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        values = [_snapshot_constant(x, known) for x in node.elts]
        return {ast.Tuple: tuple, ast.List: list, ast.Set: set}[type(node)](values)
    if isinstance(node, ast.Dict) and all(k is not None for k in node.keys):
        return {_snapshot_constant(k, known): _snapshot_constant(v, known)
                for k, v in zip(node.keys, node.values)}
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mult)):
        left, right = _snapshot_constant(node.left, known), _snapshot_constant(node.right, known)
        return left + right if isinstance(node.op, ast.Add) else left * right
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
            and node.func.id in ("frozenset", "set", "tuple") \
            and len(node.args) == 1 and not node.keywords:
        return {"frozenset": frozenset, "set": set, "tuple": tuple}[node.func.id](
            _snapshot_constant(node.args[0], known))
    return ast.literal_eval(node)


def _assert_dependency_function(function, label, checked):
    """Validate every wrapper layer, including aliases retained after re-import."""
    chain = set()
    while True:
        if not isinstance(function, types.FunctionType) or id(function) in chain:
            raise AlgorithmRuntimeDriftError(f"unverifiable decorated dependency: {label}")
        chain.add(id(function))
        if id(function) not in checked:
            path = str(Path(function.__code__.co_filename).resolve())
            if path not in _IMPORTED_ALGORITHM_BYTES:
                raise AlgorithmRuntimeDriftError(f"dependency wrapper is outside bound algorithms: {label}")
            codes, (_, definitions) = _snapshot_metadata(path, function.__code__.co_filename)
            identity = (function.__code__.co_name, function.__code__.co_firstlineno)
            if not any(candidate == function.__code__ for candidate in codes.get(identity, ())):
                raise AlgorithmRuntimeDriftError(f"preimported dependency code differs from snapshot: {label}")
            node = definitions.get(identity)
            if node is None:
                raise AlgorithmRuntimeDriftError(f"dependency definition cannot be proved: {label}")
            try:
                defaults = tuple(ast.literal_eval(d) for d in node.args.defaults) or None
                kwdefaults = {arg.arg: ast.literal_eval(d)
                              for arg, d in zip(node.args.kwonlyargs, node.args.kw_defaults)
                              if d is not None} or None
            except (ValueError, TypeError) as exc:
                raise AlgorithmRuntimeDriftError(f"dependency defaults cannot be proved: {label}") from exc
            if not _same_literal(function.__defaults__, defaults) \
                    or not _same_literal(function.__kwdefaults__, kwdefaults):
                raise AlgorithmRuntimeDriftError(f"preimported dependency defaults differ from snapshot: {label}")
            checked.add(id(function))
        wrapped = getattr(function, "__wrapped__", None)
        if wrapped is None:
            return
        function = wrapped


def _assert_dependency_members(namespace, owner, checked, *, class_members=False):
    for name, value in tuple(namespace.items()):
        label = f"{owner}.{name}"
        functions = []
        if isinstance(value, (staticmethod, classmethod)):
            functions = [value.__func__]
        elif isinstance(value, property):
            functions = [f for f in (value.fget, value.fset, value.fdel) if f is not None]
        elif isinstance(value, types.FunctionType):
            path = str(Path(value.__code__.co_filename).resolve())
            if class_members or path in _IMPORTED_ALGORITHM_BYTES or value.__module__ == owner:
                functions = [value]
        elif isinstance(value, type):
            module = sys.modules.get(value.__module__)
            module_path = getattr(module, "__file__", None)
            if module_path and str(Path(module_path).resolve()) in _IMPORTED_ALGORITHM_BYTES:
                marker = ("class", id(value))
                if marker not in checked:
                    checked.add(marker)
                    _assert_dependency_members(vars(value), value.__module__ + "." + value.__qualname__,
                                               checked, class_members=True)
        for function in functions:
            _assert_dependency_function(function, label, checked)


def _assert_loaded_dependencies():
    checked = set()
    for module in tuple(sys.modules.values()):
        filename = getattr(module, "__file__", None)
        if not isinstance(filename, str):
            continue
        path = str(Path(filename).resolve())
        if path not in _IMPORTED_ALGORITHM_BYTES:
            continue
        if getattr(getattr(module, "__spec__", None), "_initializing", False):
            raise AlgorithmRuntimeDriftError(f"algorithm dependency is still initializing: {path}")
        codes, (tree, _) = _snapshot_metadata(path, filename)
        namespace = vars(module)
        # A deleted or non-function replacement must not disappear from a scan.
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _assert_dependency_function(namespace.get(node.name), module.__name__ + "." + node.name, checked)
            elif isinstance(node, ast.ClassDef):
                cls = namespace.get(node.name)
                if not isinstance(cls, type):
                    raise AlgorithmRuntimeDriftError(f"dependency class cannot be proved: {path}:{node.name}")
                for member in node.body:
                    if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        value = vars(cls).get(member.name)
                        if not isinstance(value, (types.FunctionType, staticmethod, classmethod, property)):
                            raise AlgorithmRuntimeDriftError(f"dependency method cannot be proved: {path}:{node.name}.{member.name}")
        _assert_dependency_members(namespace, module.__name__, checked)
        # Registered modules already prove their full module code and live state.
        # Older helper modules need their declarative public constants proved too.
        if path not in _LOADED_ALGORITHMS:
            known = {}
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    names = [t.id for t in node.targets if isinstance(t, ast.Name)]
                elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                    names = [node.target.id]
                else:
                    continue
                names = [name for name in names if name.isupper() and not name.startswith("_")]
                if not names:
                    continue
                try:
                    expected = _snapshot_constant(node.value, known)
                except (ValueError, TypeError, KeyError) as exc:
                    raise AlgorithmRuntimeDriftError(f"dependency constant cannot be proved: {path}:{names}") from exc
                for name in names:
                    if name not in namespace or not _same_literal(namespace[name], expected):
                        raise AlgorithmRuntimeDriftError(f"preimported dependency constant differs from snapshot: {path}:{name}")
                    known[name] = expected


def assert_algorithm_runtime():
    try:
        current = {path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
                   for path in _IMPORTED_ALGORITHM_SHA}
    except OSError as exc:
        raise AlgorithmRuntimeDriftError("algorithm input unavailable; restart required") from exc
    if current != _IMPORTED_ALGORITHM_SHA:
        raise AlgorithmRuntimeDriftError("algorithm changed since import; restart required")
    _assert_loaded_dependencies()
    for path, loaded in _LOADED_ALGORITHMS.items():
        if not loaded["source_matches_loaded_module"]:
            raise AlgorithmRuntimeDriftError(f"loaded module differs from import snapshot: {path}")
        if _live_algorithm_state(loaded["namespace"]) != loaded["live_state"]:
            raise AlgorithmRuntimeDriftError(f"live algorithm changed since registration: {path}")


def runtime_fingerprint():
    import duckdb
    import zlib
    try:
        import pyarrow
        pyarrow_version = pyarrow.__version__
    except ModuleNotFoundError:
        pyarrow_version = None
    return {"python": list(sys.version_info[:3]), "duckdb": duckdb.__version__,
            "pyarrow": pyarrow_version, "zlib": zlib.ZLIB_RUNTIME_VERSION}


def computation_inputs(binding):
    """Actual computational dependencies, not approval or bookkeeping state.

    The complete current binding remains in each newly assembled ledger. Manifest
    scope is computational (target/cutoff/position/denominator); its file hash and
    run ID and the data-map registration are checked by the formal consumer but
    are not inputs to the trace simulation. Confirmation is never a cache key.
    """
    result = copy.deepcopy(binding)
    params = result.get("algorithm_params") or {}
    params.pop("flip_adjudications", None)
    result["algorithm_params"] = params
    manifest = result.pop("handoff_manifest", None)
    result["scope"] = (manifest or {}).get("scope")
    result.pop("data_map", None)
    return {"schema": COMPUTE_SCHEMA, "inputs": result}


def computation_digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def computation_output(report):
    """Audit comparison excludes the current user's confirmation disposition."""
    sensitivity = report.get("bounds_sensitivity") or {}
    return {
        "schema": report.get("schema"),
        "total_supply_raw": report.get("total_supply_raw"),
        "entities": report.get("entities"),
        "unresolved_total_pct": report.get("unresolved_total_pct"),
        "bounds_sensitivity": {k: v for k, v in sensitivity.items()
                               if k not in ("acknowledged_flips", "publishable")},
    }


def independent_inputs(binding, report):
    return {"schema": "trace-independent-replay/v1",
            "computation_inputs": computation_inputs(binding),
            "candidate_computation_sha256": computation_digest(computation_output(report))}


def validate_computation(payload):
    expected = {"schema", "entities", "sensitivity", "unresolved_total_pct", "counts"}
    if not isinstance(payload, dict) or set(payload) != expected \
            or payload.get("schema") != COMPUTE_SCHEMA:
        raise CacheIntegrityError("trace cache is not a confirmation-free computation")
    entities, sensitivity = payload["entities"], payload["sensitivity"]
    if not isinstance(entities, list) or not isinstance(sensitivity, dict):
        raise CacheIntegrityError("trace computation structure invalid")
    try:
        ids = [e["entity_id"] for e in entities]
        if len(ids) != len(set(ids)) or set(ids) != set(sensitivity):
            raise ValueError("entity coverage mismatch")
        for ent in entities:
            for anchor in ("current", "peak"):
                row = ent["anchors"][anchor]
                stock = int(row["stock_raw"])
                comp = row["composition"]
                # Preserve the producer's existing percentage closure rule.
                # Integer display rounding on tiny synthetic stocks is not a
                # cache-integrity failure; freeze retains its stricter raw check.
                if stock > 0 and (not comp or
                        abs(sum(float(c["pct_of_anchor"]) for c in comp) - 100) > 0.5):
                    raise ValueError("cached anchor does not close")
        counts = payload["counts"]
        for key in ("source_edges", "kept_edges"):
            if not isinstance(counts[key], int) or isinstance(counts[key], bool) \
                    or counts[key] <= 0:
                raise ValueError("invalid edge count")
    except (KeyError, TypeError, ValueError) as exc:
        raise CacheIntegrityError(f"trace computation malformed: {exc}") from exc
    return payload


def load_computation(case_dir, binding, mode):
    assert_algorithm_runtime()
    if mode == "off":
        return None, "independent_or_explicit_cache_off"
    try:
        cached = CacheStore(case_dir, PRODUCER_NAMESPACE).load(computation_inputs(binding))
        if cached is None:
            return None, "no_matching_computation_inputs"
        assert_algorithm_runtime()
        return validate_computation(cached), None
    except (CacheIntegrityError, OSError) as exc:
        emit_metric("trace_cache_reject", reason=str(exc))
        return None, "cache_integrity_rejected"


def save_computation(case_dir, binding, payload, mode):
    assert_algorithm_runtime()
    if mode == "off":
        return
    validate_computation(payload)
    try:
        CacheStore(case_dir, PRODUCER_NAMESPACE).save(computation_inputs(binding), payload)
    except (CacheIntegrityError, OSError) as exc:
        # A fresh computation remains usable; its damaged cache does not.
        emit_metric("trace_cache_write_reject", reason=str(exc))


def load_independent_replay(case_dir, binding, report):
    assert_algorithm_runtime()
    if os.environ.get("CHIP_FORCE_INDEPENDENT_TRACE") == "1":
        return False, "explicit_independent_replay_requested"
    expected = computation_output(report)
    try:
        payload = CacheStore(case_dir, INDEPENDENT_NAMESPACE).load(independent_inputs(binding, report))
        if payload is None:
            return False, "no_independent_result_for_inputs_and_candidate"
        if not isinstance(payload, dict) or set(payload) != {"independent_computation"} \
                or canonical_bytes(payload["independent_computation"]) != canonical_bytes(expected):
            raise CacheIntegrityError("independent result differs from candidate computation")
        assert_algorithm_runtime()
        return True, None
    except (CacheIntegrityError, OSError) as exc:
        emit_metric("independent_trace_cache_reject", reason=str(exc))
        return False, "independent_cache_integrity_rejected"


def save_independent_replay(case_dir, binding, candidate, independently_replayed):
    assert_algorithm_runtime()
    actual = computation_output(independently_replayed)
    if canonical_bytes(actual) != canonical_bytes(computation_output(candidate)):
        raise ValueError("independent replay computation differs from candidate")
    try:
        CacheStore(case_dir, INDEPENDENT_NAMESPACE).save(
            independent_inputs(binding, candidate), {"independent_computation": actual})
    except (CacheIntegrityError, OSError) as exc:
        emit_metric("independent_trace_cache_write_reject", reason=str(exc))


register_loaded_algorithm(globals(), sys._getframe().f_code)
