"""Content-bound raw-row reuse for the unchanged deep edge contract.

This layer never computes balances, repair maps, or a validation result. It first
tries the independently authenticated main raw materialization for the exact
requested source path. Otherwise it stores only successfully decoded original
rows in Arrow columns. Decimal-text integer columns avoid fixed-width narrowing;
binary owner columns preserve even lone Unicode surrogates; an explicit type bit
preserves the old parser's distinction between instr=-1 and instr=-1.0.
"""
from __future__ import annotations

import contextlib
import contextvars
import hashlib
import os
import re
import sys
import time
import uuid
from itertools import chain
from pathlib import Path

try:
    from content_cache import CacheStore, CacheIntegrityError, canonical_bytes, sha256_file, ResidentCodeGuard
    from deep_validation_cache import (TrackingPath, _metric, capture_reads,
                                       current_case_root, record_verified_reads,
                                       force_deep_validation)
except ModuleNotFoundError:
    from .content_cache import CacheStore, CacheIntegrityError, canonical_bytes, sha256_file, ResidentCodeGuard
    from .deep_validation_cache import (TrackingPath, _metric, capture_reads,
                                        current_case_root, record_verified_reads,
                                        force_deep_validation)

SCHEMA = 'deep-original-edge-columns/v1'
_RAW_FORCE = contextvars.ContextVar('deep_raw_edge_force', default=None)
_BATCH_SIZE = 100_000
_DECODER_GUARDS = {}
_LIB = Path(__file__).resolve().parent
_CORE_AT_IMPORT = {str(p): sha256_file(p) for p in (
    Path(__file__).resolve(), _LIB / 'content_cache.py', _LIB / 'deep_validation_cache.py',
    _LIB / 'solana_exact_validate.py')}


@contextlib.contextmanager
def force_raw_edge_parsing(reason='independent_raw_decoder'):
    """Bypass both raw materializations, independently of force-deep mode."""
    token = _RAW_FORCE.set(str(reason))
    try:
        # An explicit raw decoder check must not be skipped by a cached deep
        # result. The reverse is intentionally false: force-deep shares raw rows.
        with force_deep_validation(reason):
            yield
    finally:
        _RAW_FORCE.reset(token)


def _fingerprint(path):
    path = TrackingPath(path).resolve(strict=True)
    digest, size = hashlib.sha256(), 0
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b''):
            digest.update(block)
            size += len(block)
    return {'path': str(path), 'bytes': size, 'sha256': digest.hexdigest()}


def _schema(pa):
    return pa.schema([
        ('ts_decimal', pa.string()), ('slot_decimal', pa.string()),
        ('tx_decimal', pa.string()), ('instr_is_float', pa.bool_()),
        ('source_utf8_surrogatepass', pa.binary()),
        ('target_utf8_surrogatepass', pa.binary()), ('amount_decimal', pa.string()),
    ], metadata={b'raw_contract': SCHEMA.encode()})


def register_raw_decoder(parser, validator):
    """Register the actual audited decoder/contract after their definitions."""
    _DECODER_GUARDS[parser] = (ResidentCodeGuard(parser),
                               ResidentCodeGuard(validator), validator.__name__)


def _decoder_fingerprint(parser):
    if parser not in _DECODER_GUARDS:
        raise CacheIntegrityError('unregistered resident raw decoder')
    parser_guard, validator_guard, validator_name = _DECODER_GUARDS[parser]
    parser_guard.check(parser)
    validator_guard.check(parser.__globals__.get(validator_name))
    return parser_guard.sha256


def _input_key(source, parser, pa):
    lib = Path(__file__).resolve().parent
    algorithms = [Path(__file__), Path(parser.__code__.co_filename),
                  lib / 'deep_validation_cache.py', lib / 'content_cache.py',
                  lib / 'solana_exact_validate.py']
    algorithm = {str(p.resolve()): _fingerprint(p)['sha256']
                 for p in sorted(set(algorithms), key=str)}
    if any(algorithm[path] != expected for path, expected in _CORE_AT_IMPORT.items()):
        raise CacheIntegrityError('raw cache algorithm changed since import')
    return {'schema': SCHEMA, 'source': source, 'algorithm': algorithm,
            'parser_code_sha256': _decoder_fingerprint(parser),
            'runtime': {'python': sys.version, 'cache_tag': sys.implementation.cache_tag,
                        'pyarrow': pa.__version__, 'byteorder': sys.byteorder}}


def _verified_main(path, case_root):
    try:
        from solana_materialization_reader import verified_rows
    except ModuleNotFoundError:
        from .solana_materialization_reader import verified_rows
    return verified_rows(path, case_root)


def _artifact_path(store, key, payload):
    name = payload.get('artifact')
    if not isinstance(name, str) or re.fullmatch(
            re.escape(store.key(key)) + r'-[0-9a-f]{64}\.arrow', name) is None:
        raise CacheIntegrityError('invalid deep raw artifact path binding')
    path = store.directory / name
    if path.is_symlink() or not path.is_file():
        raise CacheIntegrityError('deep raw artifact missing or a symlink')
    return path


def _load(store, key, pa):
    # The authenticated primitive owns signature verification. Bracket its read
    # with tracked hashes so the outer deep proof also binds the receipt bytes.
    manifest = store.path(key)
    if not manifest.exists() and not manifest.is_symlink():
        return None
    if manifest.is_symlink() or not manifest.is_file():
        raise CacheIntegrityError('deep raw receipt must be a regular non-symlink file')
    before = _fingerprint(manifest)
    payload = store.load(key)
    if _fingerprint(manifest) != before:
        raise CacheIntegrityError('deep raw receipt changed while authenticated')
    if not isinstance(payload, dict) or payload.get('schema') != SCHEMA:
        raise CacheIntegrityError('unknown deep raw payload schema')
    path = _artifact_path(store, key, payload)
    observed = _fingerprint(path)
    if observed != payload.get('artifact_file'):
        raise CacheIntegrityError('deep raw artifact content mismatch')
    count = payload.get('rows')
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise CacheIntegrityError('invalid deep raw row count binding')
    # Check the Arrow footer/schema before exposing any rows.
    with pa.memory_map(str(path), 'r') as handle:
        reader = pa.ipc.open_file(handle)
        if not reader.schema.equals(_schema(pa), check_metadata=True):
            raise CacheIntegrityError('deep raw Arrow schema mismatch')
    return path, payload


def _column_rows(path, count, pa):
    total = 0
    with pa.memory_map(str(path), 'r') as handle:
        reader = pa.ipc.open_file(handle)
        for index in range(reader.num_record_batches):
            columns = [c.to_pylist() for c in reader.get_batch(index).columns]
            for ts, slot, txi, floating, source, target, amount in zip(*columns):
                total += 1
                yield (int(ts), int(slot), int(txi), -1.0 if floating else -1,
                       source.decode('utf-8', 'surrogatepass'),
                       target.decode('utf-8', 'surrogatepass'), int(amount))
    if total != count:
        raise CacheIntegrityError('deep raw Arrow row count mismatch')


def _finish_writer(writer, stream):
    if writer is not None:
        writer.close()
    if stream is not None:
        stream.close()


def _build_rows(path, parser, reason, store, key, source, pa):
    """Yield once while building; partial/invalid input never receives a receipt."""
    pending = store.directory / ('.pending-' + uuid.uuid4().hex + '.arrow')
    writer = stream = None
    columns = [[] for _ in range(7)]
    total, complete, started = 0, False, time.perf_counter()
    schema = _schema(pa)

    def abandon(exc):
        nonlocal writer, stream
        try:
            _finish_writer(writer, stream)
        except (OSError, ValueError):
            pass
        writer = stream = None
        for column in columns:
            column.clear()
        _metric('deep_edge_cache_reject', path=str(path),
                reason='raw_column_writer_unavailable: ' + str(exc))

    try:
        stream = pa.OSFile(str(pending), 'wb')
        writer = pa.ipc.new_file(
            stream, schema, options=pa.ipc.IpcWriteOptions(compression='lz4'))
    except (OSError, ValueError, TypeError) as exc:
        abandon(exc)

    def flush():
        batch = pa.RecordBatch.from_arrays(
            [pa.array(values, type=field.type) for values, field in zip(columns, schema)],
            schema=schema)
        writer.write_batch(batch)
        for column in columns:
            column.clear()

    decoded, sentinel = iter(parser(path, reason=reason)), object()
    try:
        # The audited parser opens one TrackingPath stream before its first row.
        # That stream keeps its reader references until close, so the collector
        # need only be active during opening. Never leave a contextvar scope
        # suspended across yield: repair interleaves base and merged iterators.
        with capture_reads() as actual_reads:
            first = next(decoded, sentinel)
        incoming = () if first is sentinel else chain((first,), decoded)
        for row in incoming:
            if writer is not None:
                try:
                    ts, slot, txi, instr, sender, receiver, amount = row
                    values = (str(ts), str(slot), str(txi), isinstance(instr, float),
                              sender.encode('utf-8', 'surrogatepass'),
                              receiver.encode('utf-8', 'surrogatepass'), str(amount))
                    for column, value in zip(columns, values):
                        column.append(value)
                    if len(columns[0]) >= _BATCH_SIZE:
                        flush()
                except (OSError, ValueError, TypeError, OverflowError) as exc:
                    abandon(exc)
            total += 1
            yield row
        complete = True
    finally:
        close = getattr(decoded, 'close', None)
        if close is not None:
            close()
        try:
            if complete and writer is not None and columns[0]:
                flush()
            _finish_writer(writer, stream)
        except (OSError, ValueError, TypeError) as exc:
            abandon(exc)

    if not complete or writer is None:
        return
    try:
        consumed = actual_reads.proof()
        if (len(consumed['files']) != 1
                or consumed['files'][0]['sha256'] != source['sha256']
                or consumed['files'][0]['bytes'] != source['bytes']
                or str(Path(consumed['files'][0]['path']).resolve()) != source['path']):
            raise CacheIntegrityError('raw parser bytes differ from initial source hash')
        if _fingerprint(path) != source:
            raise CacheIntegrityError('raw source changed during column materialization')
        if canonical_bytes(_input_key(source, parser, pa)) != canonical_bytes(key):
            raise CacheIntegrityError('deep raw decoder algorithm changed while materializing')
        # Hashing our unpublished generated output is not an input dependency:
        # its temporary name is removed by the atomic rename.
        generated_sha = sha256_file(pending)
        name = store.key(key) + '-' + generated_sha + '.arrow'
        final = store.directory / name
        os.replace(pending, final)
        # The pending name has ceased to exist; it is a generated output, not a
        # lasting input. Record the final file as a reusable proof dependency.
        output = _fingerprint(final)
        payload = {'schema': SCHEMA, 'rows': total, 'artifact': name,
                   'artifact_file': output}
        store.save(key, payload)
        _fingerprint(store.path(key))
        _metric('deep_edge_cache_issue', path=str(path), rows=total,
                source_bytes=source['bytes'], artifact_bytes=output['bytes'],
                elapsed_seconds=time.perf_counter() - started)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        _metric('deep_edge_cache_reject', path=str(path),
                reason='raw_columns_not_issued: ' + str(exc))


def reusable_edge_rows(path, parser, validate, *, reason=None):
    """Share original rows while retaining the caller's exact validation rule."""
    path = TrackingPath(path)
    root = current_case_root()
    forced = _RAW_FORCE.get() or (
        'raw_cache_disabled' if os.environ.get('CHIP_DEEP_RAW_CACHE') == '0' else None)
    if root is None or forced:
        yield from parser(path, reason=forced or reason or 'no_case_context')
        return
    try:
        _decoder_fingerprint(parser)
    except (ValueError, TypeError, OSError) as exc:
        _metric('deep_edge_cache_reject', path=str(path),
                reason='resident_decoder_changed: ' + str(exc))
        yield from parser(path, reason='resident_decoder_changed')
        return
    started = time.perf_counter()
    main_rejected = False
    try:
        # This resolution is a tracked dependency even though the reader itself
        # uses ordinary pathlib and its own full-file verification.
        path.resolve(strict=True)
        main = _verified_main(path, root)
    except (OSError, ValueError, TypeError, KeyError, ImportError) as exc:
        main, main_rejected = None, True
        _metric('deep_edge_cache_reject', path=str(path),
                reason='main_materialization_rejected: ' + str(exc))
    if main is not None:
        record_verified_reads(main['dependency_files'])
        for algorithm in main['algorithm_files']:
            _fingerprint(algorithm)
        rows = iter(main['rows'])
        _metric('deep_edge_reuse', path=str(path), layer='main_raw_columns',
                source_sha256=main['source_sha256'], reason=reason or 'exact_source_match',
                elapsed_seconds=time.perf_counter() - started)
        try:
            for row in rows:
                yield validate(list(row))
        finally:
            close = getattr(rows, 'close', None)
            if close is not None:
                close()
        return

    try:
        import pyarrow as pa
        source = _fingerprint(path)
        key = _input_key(source, parser, pa)
        store = CacheStore(root, 'solana-deep-raw-rows')
        loaded = None if main_rejected else _load(store, key, pa)
    except (OSError, ValueError, TypeError, KeyError, ImportError) as exc:
        _metric('deep_edge_cache_reject', path=str(path), reason=str(exc))
        yield from parser(path, reason='raw_cache_unavailable: ' + str(exc))
        return
    if loaded is not None:
        artifact, payload = loaded
        _metric('deep_edge_reuse', path=str(path), layer='deep_raw_columns',
                source_sha256=source['sha256'], rows=payload['rows'],
                reason=reason or 'source_and_columns_content_unchanged',
                elapsed_seconds=time.perf_counter() - started)
        for row in _column_rows(artifact, payload['rows'], pa):
            yield validate(list(row))
        return
    yield from _build_rows(path, parser, reason or 'no_verified_raw_materialization',
                           store, key, source, pa)
