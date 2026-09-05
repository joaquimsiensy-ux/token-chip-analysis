"""Authenticated reuse of complete, actually-read deep-validation dependencies.

This is deliberately separate from DeepReconciliationWitness's first-level
frontier. No frontier/witness/old PASS is accepted here. The audited validator
uses TrackingPath and tracked_gzip_text for every evidence read. Successful
issuance binds the bytes actually consumed, existence/path-resolution probes,
arguments, algorithm code, runtime, and the typed result. Every reuse rehashes
every leaf. The filesystem can of course change after verification returns.
"""
from __future__ import annotations

import contextlib
import contextvars
import functools
import gzip
import hashlib
import inspect
import io
import json
import os
import sqlite3
import sys
import threading
import time
import zlib
from pathlib import Path as PlainPath

try:
    from content_cache import CacheStore, CacheIntegrityError, canonical_bytes, emit_metric, sha256_file, ResidentCodeGuard
except ModuleNotFoundError:
    from .content_cache import CacheStore, CacheIntegrityError, canonical_bytes, emit_metric, sha256_file, ResidentCodeGuard

SCHEMA = 'complete-deep-read-proof/v1'
_READERS = contextvars.ContextVar('deep_validation_readers', default=())
_FORCE = contextvars.ContextVar('deep_validation_force', default=None)
_CASE_ROOT = contextvars.ContextVar('deep_validation_case_root', default=None)
_LOCK = threading.Lock()
_COUNTS = {'deep_runs': 0, 'reuses': 0, 'rejects': 0,
           'edge_parse_runs': 0, 'edge_reuses': 0}


def cache_counters():
    with _LOCK:
        return dict(_COUNTS)


def _metric(event, **fields):
    with _LOCK:
        if event == 'deep_validate_start': _COUNTS['deep_runs'] += 1
        elif event == 'deep_validate_reuse': _COUNTS['reuses'] += 1
        elif event == 'deep_validate_reject': _COUNTS['rejects'] += 1
        elif event == 'deep_edge_parse_start': _COUNTS['edge_parse_runs'] += 1
        elif event == 'deep_edge_reuse': _COUNTS['edge_reuses'] += 1
        counts = dict(_COUNTS)
    try:
        emit_metric(event, **counts, **fields)
    except OSError as exc:
        # An optional telemetry destination must not change validation semantics.
        print(f'[performance] metric destination unavailable: {exc}', file=sys.stderr)


@contextlib.contextmanager
def force_deep_validation(reason='independent_final'):
    """Recompute this call tree; authenticated raw loading remains shareable.

    Use CHIP_DEEP_RAW_CACHE=0 separately when testing the raw JSON decoder.
    """
    token = _FORCE.set(str(reason))
    try:
        yield
    finally:
        _FORCE.reset(token)


def current_case_root():
    return _CASE_ROOT.get()


@contextlib.contextmanager
def capture_reads():
    """Capture actual raw reads for a subordinate materialization issuer."""
    reader = _Reads()
    token = _READERS.set((*_READERS.get(), reader))
    try:
        yield reader
    finally:
        _READERS.reset(token)


def record_verified_reads(records):
    """Import full file hashes just checked by the authenticated raw reader.

    This is only used for the audited materialization reader, whose DuckDB I/O
    cannot pass through TrackingPath. The reader hashes each whole input before
    returning it; the outer deep proof checks all these bytes again on issuance.
    """
    for row in records:
        if (set(row) != {'path', 'bytes', 'sha256'}
                or not isinstance(row['bytes'], int) or row['bytes'] < 0
                or len(row['sha256']) != 64):
            raise CacheIntegrityError('malformed verified materialization dependency')
        for reader in _READERS.get():
            reader.file(_absolute(row['path']), row['bytes'], row['sha256'])


def _pack(value):
    # Tag every value so a user JSON object cannot impersonate a serialized Path.
    if isinstance(value, PlainPath): return ['path', str(value)]
    if isinstance(value, dict): return ['dict', [[k, _pack(v)] for k, v in value.items()]]
    if isinstance(value, list): return ['list', [_pack(v) for v in value]]
    if isinstance(value, tuple): return ['tuple', [_pack(v) for v in value]]
    if isinstance(value, (str, int, float, bool)) or value is None: return ['value', value]
    raise TypeError(f'unsupported deep result/argument type: {type(value).__name__}')


def _unpack(value):
    kind, item = value
    if kind == 'path': return PlainPath(item)
    if kind == 'dict': return {k: _unpack(v) for k, v in item}
    if kind == 'list': return [_unpack(v) for v in item]
    if kind == 'tuple': return tuple(_unpack(v) for v in item)
    if kind == 'value': return item
    raise CacheIntegrityError('unknown deep result value tag')


def _absolute(path):
    # No symlink resolution here: lexical-path observations must survive retargeting.
    return str(PlainPath(os.path.abspath(os.fspath(path))))


def _observe(operation, path, value):
    for reader in _READERS.get(): reader.observe(operation, _absolute(path), value)


class _Reads:
    def __init__(self):
        self.files = {}
        self.observations = {}
        self.incomplete = []
        self.read_operations = 0
        self.read_bytes = 0

    def observe(self, operation, path, value):
        key = (operation, path)
        if key in self.observations and self.observations[key] != value:
            self.incomplete.append(f'changed observation: {operation} {path}')
        self.observations[key] = value

    def file(self, path, size, digest):
        self.read_operations += 1
        self.read_bytes += size
        record = {'path': path, 'bytes': size, 'sha256': digest}
        if path in self.files and self.files[path] != record:
            self.incomplete.append(f'changed bytes during validation: {path}')
        self.files[path] = record

    def merge(self, proof):
        for record in proof['files']:
            self.file(record['path'], record['bytes'], record['sha256'])
        for row in proof['observations']:
            self.observe(row['operation'], row['path'], row['value'])

    def proof(self):
        if self.incomplete or not self.files:
            raise CacheIntegrityError('; '.join(self.incomplete) or 'empty actual-read dependency set')
        return {'files': [self.files[k] for k in sorted(self.files)],
                'observations': [{'operation': op, 'path': path, 'value': value}
                                 for (op, path), value in sorted(self.observations.items())]}


class _HashingRaw(io.RawIOBase):
    """Hash raw bytes while the validator consumes them, including gzip sources."""
    def __init__(self, handle, path, readers):
        super().__init__()
        self.handle, self.path, self.readers = handle, path, readers
        self.digest, self.count, self.sequential = hashlib.sha256(), 0, True

    def readable(self): return True
    def seekable(self): return self.handle.seekable()
    def fileno(self): return self.handle.fileno()
    def tell(self): return self.handle.tell()

    def seek(self, offset, whence=0):
        self.sequential = False
        return self.handle.seek(offset, whence)

    def readinto(self, buffer):
        n = self.handle.readinto(buffer)
        if n:
            self.digest.update(memoryview(buffer)[:n])
            self.count += n
        return n

    def close(self):
        if not self.closed:
            try:
                complete = (self.sequential and self.count == os.fstat(self.handle.fileno()).st_size
                            and self.handle.tell() == self.count)
                for reader in self.readers:
                    if complete: reader.file(self.path, self.count, self.digest.hexdigest())
                    else:
                        reader.read_operations += 1
                        reader.read_bytes += self.count
                        reader.incomplete.append(f'partial or nonsequential evidence read: {self.path}')
            finally:
                self.handle.close()
                super().close()


class TrackingPath(type(PlainPath())):
    """Local validator Path type, never a monkeypatch of pathlib or builtins."""
    def resolve(self, strict=False):
        try:
            result = super().resolve(strict=strict)
        except OSError:
            for reader in _READERS.get(): reader.incomplete.append(f'failed strict resolution: {self}')
            raise
        _observe('resolve', self, str(result))
        return result

    def is_file(self):
        value = super().is_file()
        _observe('is_file', self, value)
        return value

    def is_dir(self):
        value = super().is_dir()
        _observe('is_dir', self, value)
        return value

    def is_symlink(self):
        value = super().is_symlink()
        _observe('is_symlink', self, value)
        return value

    def open(self, mode='r', buffering=-1, encoding=None, errors=None, newline=None):
        readers = _READERS.get()
        if not readers:
            return super().open(mode, buffering, encoding, errors, newline)
        if mode not in ('r', 'rt', 'rb'):
            for reader in readers: reader.incomplete.append(f'non-read-only evidence stream: {self}')
            return super().open(mode, buffering, encoding, errors, newline)
        # Opening these inputs is always read-only; SQLite scratch files do not use this hook.
        path = _absolute(self)
        try:
            handle = io.FileIO(path, 'r')
        except OSError:
            for reader in readers: reader.incomplete.append(f'unreadable evidence: {path}')
            raise
        stream = _HashingRaw(handle, path, readers)
        if buffering == 0:
            if 'b' not in mode:
                stream.close()
                raise ValueError("can't have unbuffered text I/O")
            return stream
        buffered = io.BufferedReader(stream, buffer_size=buffering if buffering > 0 else io.DEFAULT_BUFFER_SIZE)
        if 'b' in mode: return buffered
        return io.TextIOWrapper(buffered, encoding=encoding, errors=errors, newline=newline)


@contextlib.contextmanager
def tracked_gzip_text(path):
    with TrackingPath(path).open('rb') as raw:
        with gzip.open(raw, 'rt', encoding='utf-8') as handle:
            yield handle


def _probe(row):
    p, operation = PlainPath(row['path']), row['operation']
    if operation == 'resolve': return str(p.resolve())
    if operation in ('is_file', 'is_dir', 'is_symlink'): return getattr(p, operation)()
    raise CacheIntegrityError('unknown dependency observation')


def _verify_proof(proof):
    if not isinstance(proof, dict) or set(proof) != {'files', 'observations'} or not proof['files']:
        raise CacheIntegrityError('incomplete actual-read proof')
    for row in proof['observations']:
        if _probe(row) != row['value']:
            raise CacheIntegrityError(f'dependency observation changed: {row["operation"]} {row["path"]}')
    seen, total_bytes = set(), 0
    for row in proof['files']:
        path = row['path']
        if path in seen or set(row) != {'path', 'bytes', 'sha256'}:
            raise CacheIntegrityError('duplicate/malformed read dependency')
        seen.add(path)
        p = PlainPath(path)
        if not p.is_file() or p.stat().st_size != row['bytes'] or sha256_file(p) != row['sha256']:
            raise CacheIntegrityError(f'dependency content changed or missing: {path}')
        total_bytes += row['bytes']
    # Check lexical resolution again after reading bytes, rather than trusting old paths.
    for row in proof['observations']:
        if _probe(row) != row['value']:
            raise CacheIntegrityError(f'dependency observation changed during verification: {row["path"]}')
    return total_bytes


def _algorithm_files(function):
    module = PlainPath(function.__code__.co_filename).resolve()
    lib = PlainPath(__file__).resolve().parent
    # These are the only local executable imports in the audited deep validator.
    return tuple(sorted({module, PlainPath(__file__).resolve(), lib / 'content_cache.py',
                         lib / 'producer_history.py', lib / 'deep_edge_rows_cache.py',
                         lib / 'solana_materialization_reader.py', lib / 'solana_edge_store.py',
                         lib.parent / 'solana' / 'spl_edge_core.py'}, key=str))


def _runtime_versions():
    versions = {'python': sys.version, 'cache_tag': sys.implementation.cache_tag,
                'byteorder': sys.byteorder, 'sqlite': sqlite3.sqlite_version,
                'zlib': zlib.ZLIB_RUNTIME_VERSION}
    for name in ('pyarrow', 'duckdb'):
        try:
            module = __import__(name)
            versions[name] = module.__version__
        except ImportError:
            versions[name] = None
    return versions


def cached_deep_validation(kind):
    """Decorator for the two audited Solana validators; not a generic proof issuer."""
    def decorate(function):
        signature = inspect.signature(function)
        files = _algorithm_files(function)
        imported_code_hashes = {str(p): sha256_file(p) for p in files}
        function_guard = ResidentCodeGuard(function)
        function_hash = function_guard.sha256
        support_guards = {name: ResidentCodeGuard(function.__globals__[name])
                          for name in ("_parse_edge_rows", "_validated_edge")
                          if name in function.__globals__}

        def check_resident():
            function_guard.check(function)
            for name, guard in support_guards.items():
                guard.check(function.__globals__.get(name))

        @functools.wraps(function)
        def wrapped(*args, **kwargs):
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()
            start = time.perf_counter()
            force = (_FORCE.get() or ('environment_force' if os.environ.get('CHIP_FORCE_DEEP_VALIDATION') == '1' else None)
                     or ('cache_disabled' if os.environ.get('CHIP_DEEP_CACHE') == '0' else None)
                     or ('raw_decoder_requested' if os.environ.get('CHIP_DEEP_RAW_CACHE') == '0' else None))
            if bound.arguments.get('live_canary') or bound.arguments.get('live_canary_fetch') is not None:
                force = force or 'live_canary'
            store, key, miss_reason = None, None, force or 'no_complete_proof'
            try:
                try:
                    check_resident()
                except (ValueError, TypeError, OSError) as exc:
                    force = miss_reason = 'resident_algorithm_changed: ' + str(exc)
                current_code = {str(p): sha256_file(p) for p in files}
                if current_code != imported_code_hashes:
                    force = miss_reason = 'algorithm_changed_since_import'
                key = {'proof_schema': SCHEMA, 'validator': kind, 'arguments': _pack(dict(bound.arguments)),
                       'algorithm': current_code, 'function_code_sha256': function_hash,
                       'runtime': _runtime_versions()}
                canonical_bytes(key)
                if not force:
                    store = CacheStore(bound.arguments['case_root'], 'solana-deep-validation')
                    payload = store.load(key)
                    if payload is not None:
                        if not isinstance(payload, dict) or payload.get('schema') != SCHEMA:
                            raise CacheIntegrityError('unknown deep proof schema')
                        packed = payload['result']
                        if hashlib.sha256(canonical_bytes(packed)).hexdigest() != payload['result_sha256']:
                            raise CacheIntegrityError('deep result binding mismatch')
                        result = _unpack(packed)
                        if not isinstance(result, dict) or result.get('ok') is not True:
                            raise CacheIntegrityError('cached deep result is not successful')
                        read_bytes = _verify_proof(payload['read_proof'])
                        check_resident()
                        if {str(p): sha256_file(p) for p in files} != key['algorithm']:
                            raise CacheIntegrityError('algorithm changed during cached proof verification')
                        for reader in _READERS.get(): reader.merge(payload['read_proof'])
                        _metric('deep_validate_reuse', validator=kind, reason='complete_dependencies_unchanged',
                                dependency_files=len(payload['read_proof']['files']), rehashed_bytes=read_bytes,
                                unique_leaf_bytes=read_bytes, cumulative_read_bytes=read_bytes,
                                cumulative_file_reads=len(payload['read_proof']['files']),
                                elapsed_seconds=time.perf_counter() - start)
                        return result
            except (OSError, ValueError, TypeError, KeyError) as exc:
                miss_reason = str(exc)
                _metric('deep_validate_reject', validator=kind, reason=miss_reason,
                        elapsed_seconds=time.perf_counter() - start)

            _metric('deep_validate_start', validator=kind, reason=miss_reason)
            deep_start = time.perf_counter()
            reader = _Reads()
            token = _READERS.set((*_READERS.get(), reader))
            case_token = _CASE_ROOT.set(bound.arguments['case_root'])
            try:
                result = function(*args, **kwargs)
            except BaseException:
                _metric('deep_validate_finish', validator=kind, ok=False, reason='validator_exception',
                        cumulative_read_bytes=reader.read_bytes, cumulative_file_reads=reader.read_operations,
                        elapsed_seconds=time.perf_counter() - deep_start)
                raise
            finally:
                _CASE_ROOT.reset(case_token)
                _READERS.reset(token)
            _metric('deep_validate_finish', validator=kind, ok=result.get('ok') is True,
                    dependency_files=len(reader.files), unique_leaf_bytes=sum(r['bytes'] for r in reader.files.values()),
                    cumulative_read_bytes=reader.read_bytes, cumulative_file_reads=reader.read_operations,
                    reason=miss_reason, elapsed_seconds=time.perf_counter() - deep_start)
            if result.get('ok') is True and not force and key is not None:
                try:
                    proof = reader.proof()
                    read_bytes = _verify_proof(proof)
                    packed = _pack(result)
                    # Detect a concurrent algorithm edit as well as evidence changes.
                    check_resident()
                    if {str(p): sha256_file(p) for p in files} != key['algorithm']:
                        raise CacheIntegrityError('algorithm changed during deep validation')
                    if store is None:
                        store = CacheStore(bound.arguments['case_root'], 'solana-deep-validation')
                    store.save(key, {'schema': SCHEMA, 'read_proof': proof, 'result': packed,
                                     'result_sha256': hashlib.sha256(canonical_bytes(packed)).hexdigest()})
                    _metric('deep_validate_issue', validator=kind, dependency_files=len(proof['files']),
                            unique_leaf_bytes=read_bytes, rehashed_bytes=read_bytes,
                            validator_read_bytes=reader.read_bytes, validator_file_reads=reader.read_operations,
                            cumulative_read_bytes=reader.read_bytes + read_bytes,
                            cumulative_file_reads=reader.read_operations + len(proof['files']),
                            elapsed_seconds=time.perf_counter() - start)
                except (OSError, ValueError, TypeError, KeyError) as exc:
                    _metric('deep_validate_reject', validator=kind, reason='proof_not_issued: ' + str(exc),
                            elapsed_seconds=time.perf_counter() - start)
            return result
        return wrapped
    return decorate
