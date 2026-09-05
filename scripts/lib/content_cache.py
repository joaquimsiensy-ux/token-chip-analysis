"""Content-bound local computation receipts. Never a substitute for independent review.

Each receipt authenticates both its dependency key and payload with a local secret
outside the individual cache namespaces. This detects accidental corruption and
replacement of an artifact together with its checksum receipt. It does not protect
against an actor controlling this process or the local trust key. Every consumer
must freshly hash its actual dependencies and separately verify binary outputs.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import stat
import sys
import tempfile
import time
from pathlib import Path


class CacheIntegrityError(ValueError):
    pass


def canonical_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def code_fingerprint(paths):
    return {str(Path(p).resolve()): sha256_file(p) for p in sorted(paths, key=str)}


def emit_metric(event, **fields):
    record = {"event": event, "pid": os.getpid(), "time_unix": time.time(), **fields}
    output = os.environ.get("CHIP_PERF_METRICS")
    if output:
        # Single append while holding an advisory lock supports concurrent consumers.
        import fcntl
        with open(output, "a", encoding="utf-8") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            handle.write(canonical_bytes(record).decode("utf-8") + "\n")
            handle.flush()
    else:
        print("[performance] " + json.dumps(record, ensure_ascii=False), file=sys.stderr)


def _safe_directory(path):
    path = Path(path).absolute()
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise CacheIntegrityError(f"cache path contains a symlink: {parent}")
    path.mkdir(parents=True, exist_ok=True)
    if not path.is_dir():
        raise CacheIntegrityError(f"cache path is not a directory: {path}")
    return path


class CacheStore:
    SCHEMA = "content-computation-receipt/v1"

    def __init__(self, case_root, namespace):
        if re.fullmatch(r"[a-z0-9_-]+", namespace) is None:
            raise ValueError("invalid cache namespace")
        self.case_root = str(Path(case_root).resolve(strict=True))
        base = Path(os.environ.get("CHIP_PERF_CACHE_ROOT") or
                    Path(self.case_root) / ".runtime-cache" / "codex-performance-v1")
        self.base = _safe_directory(base)
        self.directory = _safe_directory(self.base / namespace)
        self.namespace = namespace
        self.key_path = self.base / ".local-trust-key"

    def key(self, inputs):
        return hashlib.sha256(canonical_bytes({"schema": self.SCHEMA,
            "case_root": self.case_root, "namespace": self.namespace,
            "inputs": inputs})).hexdigest()

    def _secret(self, *, create=False):
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        if create:
            import fcntl
            with open(self.base / ".trust-initialize.lock", "a+b") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                if not self.key_path.exists():
                    # A lost key cannot bless pre-existing receipts.
                    if any(self.base.glob("*/*.json")):
                        raise CacheIntegrityError("local cache trust key missing with existing receipts")
                    fd = os.open(self.key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                                 getattr(os, "O_NOFOLLOW", 0), 0o600)
                    with os.fdopen(fd, "wb") as handle:
                        handle.write(os.urandom(32))
                        handle.flush()
                        os.fsync(handle.fileno())
        try:
            fd = os.open(self.key_path, flags)
            with os.fdopen(fd, "rb") as handle:
                st = os.fstat(handle.fileno())
                if not stat.S_ISREG(st.st_mode) or st.st_mode & 0o077:
                    raise CacheIntegrityError("local cache trust key must be a private regular file")
                secret = handle.read()
            if len(secret) != 32:
                raise CacheIntegrityError("invalid local cache trust key")
            return secret
        except OSError as exc:
            raise CacheIntegrityError(f"local cache trust key unavailable: {exc}") from exc

    def path(self, inputs):
        return self.directory / (self.key(inputs) + ".json")

    def load(self, inputs):
        path = self.path(inputs)
        if not path.exists() and not path.is_symlink():
            return None
        try:
            if path.is_symlink() or not path.is_file():
                raise CacheIntegrityError("cache receipt must be a regular non-symlink file")
            envelope = json.loads(path.read_text(encoding="utf-8"))
            body = envelope["body"]
            signature = hmac.new(self._secret(), canonical_bytes(body), hashlib.sha256).hexdigest()
            if not isinstance(envelope.get("mac"), str) or not hmac.compare_digest(signature, envelope["mac"]):
                raise CacheIntegrityError("cache receipt authentication mismatch")
            if (body.get("schema") != self.SCHEMA or body.get("case_root") != self.case_root
                    or body.get("namespace") != self.namespace or body.get("key") != self.key(inputs)
                    or canonical_bytes(body.get("inputs")) != canonical_bytes(inputs)):
                raise CacheIntegrityError("cache receipt dependency binding mismatch")
            return body["payload"]
        except (OSError, KeyError, TypeError, ValueError) as exc:
            emit_metric("cache_reject", namespace=self.namespace, reason=str(exc))
            if isinstance(exc, CacheIntegrityError):
                raise
            raise CacheIntegrityError(f"invalid cache receipt: {exc}") from exc

    def save(self, inputs, payload):
        body = {"schema": self.SCHEMA, "case_root": self.case_root,
                "namespace": self.namespace, "key": self.key(inputs),
                "inputs": inputs, "payload": payload}
        envelope = {"body": body, "mac": hmac.new(self._secret(create=True),
                    canonical_bytes(body), hashlib.sha256).hexdigest()}
        fd, tmp = tempfile.mkstemp(prefix=".pending-", dir=self.directory)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(canonical_bytes(envelope) + b"\n")
                handle.flush(); os.fsync(handle.fileno())
            os.replace(tmp, self.path(inputs))
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)


# Stable executable-code bindings; independent of marshal reference encoding.
import struct
import types

_CODE_SCHEMA = 'python-code-content/v1'
_CODE_FIELDS = (
    'co_argcount', 'co_posonlyargcount', 'co_kwonlyargcount', 'co_nlocals',
    'co_stacksize', 'co_flags', 'co_code', 'co_consts', 'co_names',
    'co_varnames', 'co_freevars', 'co_cellvars', 'co_filename', 'co_name',
    'co_qualname', 'co_firstlineno', 'co_linetable', 'co_exceptiontable',
)


def _code_canonical_bytes(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('ascii')


def _code_typed(value, active):
    if value is None:
        return ['none']
    if value is Ellipsis:
        return ['ellipsis']
    if type(value) is bool:
        return ['bool', value]
    if type(value) is int:
        return ['int_hex', hex(value)]
    if type(value) is float:
        return ['float_ieee754', struct.pack('>d', value).hex()]
    if type(value) is complex:
        return ['complex_ieee754', struct.pack('>dd', value.real, value.imag).hex()]
    if type(value) is str:
        return ['str_utf8_surrogatepass', value.encode('utf-8', 'surrogatepass').hex()]
    if type(value) is bytes:
        return ['bytes', value.hex()]
    if type(value) not in (tuple, frozenset, slice, types.CodeType):
        raise TypeError('unsupported code constant: ' + type(value).__name__)
    identity = id(value)
    if identity in active:
        raise ValueError('cyclic code constant graph')
    active.add(identity)
    try:
        if type(value) is tuple:
            return ['tuple', [_code_typed(item, active) for item in value]]
        if type(value) is frozenset:
            items = [_code_typed(item, active) for item in value]
            return ['frozenset', sorted(items, key=_code_canonical_bytes)]
        if type(value) is slice:
            return ['slice', [_code_typed(item, active) for item in (
                value.start, value.stop, value.step)]]
        # Python records the importer's lexical spelling (e.g. report/../lib)
        # in co_filename. Bind the same resolved source file across importers;
        # all executable fields and complete source SHA remain in the binding.
        return ['code', [[name, _code_typed(
            str(Path(value.co_filename).resolve()) if name == 'co_filename'
            and not value.co_filename.startswith('<') else getattr(value, name), active)]
                         for name in _CODE_FIELDS]]
    finally:
        active.remove(identity)


def stable_code_bytes(code):
    if not isinstance(code, types.CodeType):
        raise TypeError('CodeType required')
    return _code_canonical_bytes({'schema': _CODE_SCHEMA, 'code': _code_typed(code, set())})


def stable_code_sha256(code):
    return hashlib.sha256(stable_code_bytes(code)).hexdigest()


def _find_qualname(code, qualname):
    if code.co_qualname == qualname:
        yield code
    for item in code.co_consts:
        if isinstance(item, types.CodeType):
            yield from _find_qualname(item, qualname)


def assert_source_matches(code):
    """Catch old code compiled before a newer import-time disk snapshot.

    compile() does not execute the module. The caller must retain its existing
    pre/post complete source hash checks to detect concurrent disk changes.
    """
    path = Path(code.co_filename)
    module_code = compile(path.read_bytes(), code.co_filename, 'exec',
                          dont_inherit=True, optimize=sys.flags.optimize)
    if not any(candidate == code for candidate in _find_qualname(
            module_code, code.co_qualname)):
        raise ValueError('loaded code differs from current compiled source')


class ResidentCodeGuard:
    """Capture the actual callable and immutable code, not a later disk claim."""
    def __init__(self, function, *, verify_source=True):
        if not isinstance(function, types.FunctionType):
            raise TypeError('Python function required')
        if verify_source:
            assert_source_matches(function.__code__)
        self.function = function
        self.code = function.__code__
        self.defaults = _code_typed(function.__defaults__, set())
        self.kwdefaults = _code_canonical_bytes([
            [k, _code_typed(v, set())] for k, v in sorted(
                (function.__kwdefaults__ or {}).items())])
        self.sha256 = stable_code_sha256(self.code)
        self.verify_source = verify_source

    def check(self, actual_function):
        if (actual_function is not self.function
                or actual_function.__code__ != self.code
                or _code_typed(actual_function.__defaults__, set()) != self.defaults
                or _code_canonical_bytes([[k, _code_typed(v, set())] for k, v in sorted(
                    (actual_function.__kwdefaults__ or {}).items())]) != self.kwdefaults):
            raise ValueError('resident callable/code/defaults changed since capture')
        if self.verify_source:
            assert_source_matches(actual_function.__code__)
        return self.sha256
