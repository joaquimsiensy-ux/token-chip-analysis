#!/usr/bin/env python3
"""Independent performance-contract acceptance tests; offline synthetic inputs.

All test fixtures and run receipts are retained. This file does not modify native
source, read sealed material, run ARC's active pipeline, or claim full-workflow
performance from a microbenchmark. Run with CHIP_BLIND_SERIAL=1.
"""
from __future__ import annotations

import copy
from contextlib import contextmanager, redirect_stdout, redirect_stderr
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import hashlib
import importlib
import inspect
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import unittest
import zlib
from unittest.mock import patch

os.environ['CHIP_BLIND_SERIAL'] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
REVIEW = (Path(os.environ['CHIP_PERF_TEST_ROOT']).expanduser().resolve()/'codex_performance_contract'
          if os.environ.get('CHIP_PERF_TEST_ROOT')
          else Path(tempfile.mkdtemp(prefix='token-chip-performance-')).resolve())
REVIEW.mkdir(parents=True, exist_ok=True)
for subdir in ('scripts/lib', 'scripts/solana', 'scripts/report', 'scripts/tests'):
    sys.path.insert(0, str(ROOT/subdir))

import duckdb
import wave_scan
import entity_source_trace
import content_cache
import solana_edge_store
import trace_compute_cache
import handoff_manifest
import deep_validation_cache
import solana_exact_validate
import deep_edge_rows_cache
import solana_materialization_reader
import pyarrow as pa
from sqd_v4_test_fixture import formal_cli_args, MINT
import sqd_cache_identity

TIMINGS = []
AUDIT_READS = None
AUDIT_DIRECTORY_OPENS = []
AUDIT_AUTH_KEY_OPENS = []
AUDIT_GENERATED_OUTPUTS = []
AUDIT_REENTRANT = False


def independent_open_audit(event, args):
    global AUDIT_REENTRANT
    # Observation only, limited to the actual validator body. This does not
    # replace Path/open or trust the implementation's list of observed leaves.
    if event != 'open' or AUDIT_READS is None or AUDIT_REENTRANT or not deep_validation_cache._READERS.get():
        return
    path, mode, flags = args
    if isinstance(path, (str, bytes)) and not (int(flags) & (os.O_WRONLY | os.O_RDWR)):
        normalized = os.path.abspath(os.fsdecode(path))
        if os.path.isdir(normalized):
            # tempfile's rmtree opens its scratch directory descriptor read-only;
            # this is not a source-file read. Preserve it separately for review.
            AUDIT_DIRECTORY_OPENS.append(normalized)
        elif normalized == str(Path(os.environ['CHIP_PERF_CACHE_ROOT'])/'.local-trust-key'):
            # This key authenticates receipts and has its own private-file and
            # HMAC checks. It is not analysis evidence and its bytes stay secret.
            AUDIT_AUTH_KEY_OPENS.append(normalized)
        elif Path(normalized).parent == Path(os.environ['CHIP_PERF_CACHE_ROOT'])/'solana-deep-raw-rows' \
                and Path(normalized).name.startswith('.pending-') and normalized.endswith('.arrow'):
            # Hash a generated output before its atomic rename, then require the
            # same complete bytes to be bound under the final path in the proof.
            AUDIT_REENTRANT = True
            try:
                AUDIT_GENERATED_OUTPUTS.append({'path': normalized, 'bytes': Path(normalized).stat().st_size,
                                                'sha256': file_sha(normalized)})
            finally:
                AUDIT_REENTRANT = False
        else:
            AUDIT_READS.append(normalized)


sys.addaudithook(independent_open_audit)
EXPECTED_COLUMNS = ['ts', 'f', 't', 'amt', 'chain_pos1', 'chain_pos2',
                    'chain_pos3', 'order_exact', 'ingest_seq']
WATCHED = [ROOT/'scripts/report/wave_scan.py', ROOT/'scripts/report/entity_source_trace.py',
           ROOT/'scripts/report/handoff_manifest.py', ROOT/'scripts/lib/content_cache.py',
           ROOT/'scripts/lib/solana_edge_store.py', ROOT/'scripts/report/trace_compute_cache.py',
           ROOT/'scripts/lib/deep_validation_cache.py', ROOT/'scripts/lib/solana_exact_validate.py',
           ROOT/'scripts/lib/deep_edge_rows_cache.py', ROOT/'scripts/lib/solana_materialization_reader.py',
           ROOT/'scripts/lib/producer_history.py',
           ROOT/'scripts/solana/spl_edge_core.py',
           ROOT/'scripts/lib/camp_series_provenance.py', ROOT/'scripts/solana/sqd_cache_identity.py',
           Path(__file__).resolve()]


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_binding_snapshot():
    return {str(p): file_sha(p) for p in WATCHED if p.is_file()}


SOURCE_START = source_binding_snapshot()


@contextmanager
def observe_calls(functions, *, forbidden=()):
    """Count actual calls without replacing identity-guarded function objects."""
    counts = {name: 0 for name in functions}
    codes = {function.__code__: name for name, function in functions.items()}
    def observe(frame, event, arg):
        if event == 'call' and frame.f_code in codes:
            name = codes[frame.f_code]
            counts[name] += 1
            if name in forbidden:
                raise AssertionError('forbidden arithmetic call: ' + name)
    previous = sys.getprofile()
    try:
        sys.setprofile(observe)
        yield counts
    finally:
        sys.setprofile(previous)


class ContractCase(unittest.TestCase):
    def setUp(self):
        # Deliberately no TemporaryDirectory cleanup: retain every failure input.
        self.case = Path(tempfile.mkdtemp(prefix=self._testMethodName+'_', dir=REVIEW))
        self.metrics = self.case/'performance_metrics.jsonl'
        self.env = patch.dict(os.environ, {'CHIP_BLIND_SERIAL': '1',
                    'CHIP_PERF_CACHE_ROOT': str(self.case/'runtime-cache'),
                    'CHIP_PERF_METRICS': str(self.metrics)})
        self.env.start()
        self.addCleanup(self.env.stop)

    def make_edges(self, rows):
        source = self.case/'source.jsonl'
        source.write_text(''.join(json.dumps(row, ensure_ascii=False)+'\n' for row in rows), encoding='utf-8')
        argv = formal_cli_args(source)
        values = dict(zip(argv[::2], argv[1::2]))
        self.edge = Path(values['--edges-sol'])
        self.meta = Path(values['--sol-cache-meta'])
        self.kwargs = {'expected_mint': values['--mint'], 'case_root': values['--case-root'],
                       'cache_meta_path': values['--sol-cache-meta']}
        return source

    def load_edges(self, *, label='load', kwargs=None, edge=None):
        con = duckdb.connect()
        started = time.perf_counter()
        try:
            count, binding = wave_scan.load_sol(con, str(edge or self.edge), **(self.kwargs if kwargs is None else kwargs))
            result = con.execute('SELECT * FROM edges ORDER BY ingest_seq').fetchall()
            description = con.execute('DESCRIBE edges').fetchall()
            TIMINGS.append({'test': self.id(), 'phase': label, 'seconds': time.perf_counter()-started,
                            'rows': count, 'fixture': str(self.case), 'kind': 'synthetic_loader_measurement'})
            return count, binding, result, description
        finally:
            con.close()

    def expect_loader_rejection(self, **kwargs):
        with self.assertRaises((SystemExit, content_cache.CacheIntegrityError)) as caught:
            self.load_edges(**kwargs)
        if isinstance(caught.exception, SystemExit):
            self.assertEqual(caught.exception.code, 2)


class SolLoaderContract(ContractCase):
    def test_loaded_modules_belong_to_current_test_root(self):
        for module in (wave_scan, entity_source_trace, content_cache, sqd_cache_identity):
            self.assertTrue(Path(module.__file__).resolve().is_relative_to(ROOT))
        self.assertEqual(os.environ['CHIP_BLIND_SERIAL'], '1')

    def test_preflight_api_exists_before_cache_acceptance(self):
        self.assertTrue(callable(getattr(wave_scan, 'preflight_sol', None)),
                        'Pending implementation: formal preflight must run before accepting a raw-load cache.')

    def test_integer_extremes_exact_on_first_and_repeat_load(self):
        amounts = [1, 2**53-1, 2**53+1, 2**63-1, 2**63, 2**64-1, 2**64+1, 2**127-1]
        rows = [[100+i, 10+i, i, -1 if i % 2 else 0, 'OwnerA', 'OwnerB', amount]
                for i, amount in enumerate(amounts)]
        self.make_edges(rows)
        want = [(r[0], r[4], r[5], r[6], r[1], r[2], r[3], r[3] >= 0, i) for i, r in enumerate(rows)]
        cold = self.load_edges(label='first')
        warm = self.load_edges(label='repeat')
        self.assertEqual(cold[:3], warm[:3])
        self.assertEqual(cold[0], len(rows))
        self.assertEqual(cold[2], want)
        self.assertTrue(all(type(r[3]) is int for r in cold[2]))
        self.assertEqual([r[0] for r in cold[3]], EXPECTED_COLUMNS)
        self.assertEqual(dict((r[0], r[1]) for r in cold[3])['amt'], 'HUGEINT')

    def test_complete_order_and_transaction_ambiguity_survive(self):
        rows = [[100, 11, 2, 0, 'A', 'B', 9], [100, 11, 1, -1, 'B', 'C', 8],
                [100, 10, 7, 2, 'C', 'D', 7], [100, 10, 7, 1, 'D', 'A', 6],
                [100, 10, 7, 1, 'D', 'A', 6], [99, 12, 0, 0, 'A', 'C', 5]]
        self.make_edges(rows)
        _, _, got, _ = self.load_edges()
        self.assertEqual([r[-1] for r in got], list(range(len(rows))))
        self.assertEqual([r[7] for r in got], [True, False, True, True, True, True])
        con = duckdb.connect()
        try:
            wave_scan.load_sol(con, str(self.edge), **self.kwargs)
            con.execute('CREATE VIEW e AS SELECT * FROM edges')
            actual = entity_source_trace.fetch_sim_edges(con, {'A', 'B', 'C', 'D'}, 100, 100)
            indexed = list(enumerate(rows))
            ordered = sorted(indexed, key=lambda ir: (ir[1][0], ir[1][1], ir[1][2], ir[1][3], ir[0]))
            expected = [(r[0], r[1], r[2], r[3], r[3] >= 0, i, r[4], r[5], r[6]) for i, r in ordered]
            self.assertEqual(actual, expected)
            self.assertEqual(len(actual), len(rows))  # Duplicate source rows must not disappear.
        finally:
            con.close()

    def test_strings_round_trip_without_delimiter_corruption(self):
        rows = [[100, 10, 0, -1, 'comma,quote"slash\\', 'tab\tline\nUnicode汉字', 2**64-1]]
        self.make_edges(rows)
        got = self.load_edges()[2]
        self.assertEqual(got[0][1:4], (rows[0][4], rows[0][5], rows[0][6]))

    def test_binding_is_real_current_resolver_binding_on_repeat(self):
        self.make_edges([[100, 10, 0, -1, 'A', 'B', 100]])
        first = self.load_edges()
        expected = sqd_cache_identity.resolve_formal_cache(MINT, self.case)[4]
        self.assertEqual(first[1], expected)
        self.assertEqual(set(expected), {'cache_kind', 'gid', 'soltx_edges_sha256',
                                         'soltx_meta_sha256', 'edge_logical_sha256'})
        with patch.object(wave_scan, 'resolve_formal_cache', wraps=sqd_cache_identity.resolve_formal_cache) as resolver:
            second = self.load_edges(label='repeat_current_resolver')
        self.assertGreaterEqual(resolver.call_count, 1)
        self.assertEqual(second[1], expected)

    def test_wrong_mint_and_wrong_meta_rejected_after_warm_seed(self):
        self.make_edges([[100, 10, 0, -1, 'A', 'B', 100]])
        self.load_edges()
        bad = dict(self.kwargs, expected_mint='So2AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA')
        self.expect_loader_rejection(kwargs=bad)
        other = self.case/'other-meta.json'
        shutil.copyfile(self.meta, other)
        self.expect_loader_rejection(kwargs=dict(self.kwargs, cache_meta_path=str(other)))

    def test_invalid_current_must_not_fall_back_to_warm_base(self):
        self.make_edges([[100, 10, 0, -1, 'A', 'B', 100]])
        self.load_edges()
        parent, pointer, _ = sqd_cache_identity.sqd_repair_paths(self.case, MINT)
        parent.mkdir(parents=True, exist_ok=True)
        pointer.write_text('{"schema":"invalid-current"}', encoding='utf-8')
        self.expect_loader_rejection()

    def test_current_change_after_preflight_is_rejected(self):
        self.make_edges([[100, 10, 0, -1, 'A', 'B', 100]])
        self.load_edges()
        prepared = wave_scan.preflight_sol(str(self.edge), **self.kwargs)
        parent, pointer, _ = sqd_cache_identity.sqd_repair_paths(self.case, MINT)
        parent.mkdir(parents=True, exist_ok=True)
        pointer.write_text('{"schema":"changed-after-preflight"}', encoding='utf-8')
        self.expect_loader_rejection(kwargs=dict(self.kwargs, preflight=prepared))

    def test_preflight_cannot_be_forwarded_to_other_request(self):
        self.make_edges([[100, 10, 0, -1, 'A', 'B', 100]])
        prepared = wave_scan.preflight_sol(str(self.edge), **self.kwargs)
        different = dict(self.kwargs, preflight=prepared, expected_mint='So2AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA')
        self.expect_loader_rejection(kwargs=different)

    def test_warm_load_uses_verified_database_without_parsing_again(self):
        self.make_edges([[100, 10, 0, -1, 'A', 'B', 100]])
        first = self.load_edges(label='first')
        with observe_calls({'build': solana_edge_store._build}, forbidden=('build',)) as build:
            second = self.load_edges(label='verified_warm')
        self.assertEqual(build['build'], 0)
        self.assertEqual(first[:3], second[:3])
        events = [json.loads(line) for line in self.metrics.read_text().splitlines()]
        self.assertEqual(sum(e['event'] == 'raw_load_complete' for e in events), 1)
        self.assertEqual(sum(e['event'] == 'raw_load_reuse' for e in events), 1)

    def test_materialized_database_corruption_is_rejected(self):
        self.make_edges([[100, 10, 0, -1, 'A', 'B', 100]])
        self.load_edges()
        store = content_cache.CacheStore(self.case, 'solana-edges')
        paths = list(store.directory.glob('*.duckdb'))
        self.assertEqual(len(paths), 1)
        database = paths[0]
        before = database.stat()
        data = bytearray(database.read_bytes())
        data[len(data)//2] ^= 1
        database.write_bytes(data)
        os.utime(database, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.expect_loader_rejection()

    def test_real_database_and_its_manifest_forgery_is_rejected(self):
        self.make_edges([[100, 10, 0, -1, 'A', 'B', 100]])
        self.load_edges()
        store = content_cache.CacheStore(self.case, 'solana-edges')
        database = next(store.directory.glob('*.duckdb'))
        con = duckdb.connect(str(database))
        try:
            con.execute('UPDATE edges SET amt = amt + 1 WHERE ingest_seq = 0')
            con.execute('CHECKPOINT')
        finally:
            con.close()
        manifest = next(store.directory.glob('*.json'))
        envelope = json.loads(manifest.read_text())
        envelope['body']['payload']['database_sha256'] = file_sha(database)
        manifest.write_text(json.dumps(envelope))
        self.expect_loader_rejection()

    def test_position_bigint_extremes_remain_exact(self):
        rows = [[2**63-1, 2**63-1, 2**63-1, 2**63-1, 'A', 'B', 1],
                [2**53+1, 2**53+1, 2**53+1, -1, 'A', 'B', 1]]
        self.make_edges(rows)
        got = self.load_edges()[2]
        self.assertEqual([(r[0], r[4], r[5], r[6]) for r in got], [tuple(r[:4]) for r in rows])

    def test_amount_overflow_never_publishes_a_trusted_materialization(self):
        self.make_edges([[100, 10, 0, -1, 'A', 'B', 2**127]])
        with self.assertRaises((SystemExit, ValueError, OverflowError, duckdb.Error)):
            self.load_edges()
        store = content_cache.CacheStore(self.case, 'solana-edges')
        self.assertEqual(list(store.directory.glob('*.json')), [])

    def test_raw_changed_same_size_and_mtime_changes_binding(self):
        self.make_edges([[100, 10, 0, -1, 'A', 'B', 100]])
        first = self.load_edges()
        st = self.edge.stat()
        data = bytearray(self.edge.read_bytes())
        data[4] ^= 1  # Valid gzip header mtime byte; logical rows unchanged.
        self.edge.write_bytes(data)
        os.utime(self.edge, ns=(st.st_atime_ns, st.st_mtime_ns))
        second = self.load_edges(label='raw_physical_change')
        self.assertEqual(self.edge.stat().st_size, st.st_size)
        self.assertEqual(second[2], first[2])
        self.assertNotEqual(second[1]['soltx_edges_sha256'], first[1]['soltx_edges_sha256'])
        self.assertEqual(second[1]['edge_logical_sha256'], first[1]['edge_logical_sha256'])

    def test_meta_bytes_change_is_not_mtime_only_reuse(self):
        self.make_edges([[100, 10, 0, -1, 'A', 'B', 100]])
        first = self.load_edges()
        meta = json.loads(self.meta.read_text())
        self.meta.write_text(json.dumps(meta, sort_keys=True, indent=2)+'\n')
        second = self.load_edges(label='meta_physical_change')
        self.assertEqual(second[2], first[2])
        self.assertNotEqual(second[1]['soltx_meta_sha256'], first[1]['soltx_meta_sha256'])

    def test_collector_digest_mismatch_rejected_even_after_success(self):
        self.make_edges([[100, 10, 0, -1, 'A', 'B', 100]])
        self.load_edges()
        meta = json.loads(self.meta.read_text())
        meta['edge_logical_sha256'] = '0'*64
        self.meta.write_text(json.dumps(meta))
        self.expect_loader_rejection()

    def test_invalid_row_types_rejected_not_coerced(self):
        valid = [100, 10, 0, -1, 'A', 'B', 100]
        mutations = [(0, True), (1, -1), (2, 1.0), (3, -2), (4, ''), (6, True), (6, 0), (6, -1), (6, 1.0)]
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                row = list(valid)
                row[field] = value
                self.make_edges([row])
                self.expect_loader_rejection()


class AuthenticatedCacheContract(ContractCase):
    def store(self, namespace='independent-contract'):
        return content_cache.CacheStore(self.case, namespace)

    def test_cold_miss_and_authenticated_hit(self):
        store = self.store()
        key = {'raw_sha256': '1'*64, 'algorithm_sha256': '2'*64, 'params': {'limit': 3}}
        self.assertIsNone(store.load(key))
        value = {'exact_integer': 2**127-1, 'order': [3, 1, 2]}
        store.save(key, value)
        self.assertEqual(store.load(key), value)
        self.assertEqual(store.key_path.stat().st_mode & 0o777, 0o600)

    def test_concurrent_first_writers_share_one_initialized_key(self):
        def work(i):
            store = self.store('concurrent-'+str(i))
            key = {'source': i}
            store.save(key, {'result': i})
            return store.load(key)
        with ThreadPoolExecutor(max_workers=8) as executor:
            values = list(executor.map(work, range(8)))
        self.assertEqual(values, [{'result': i} for i in range(8)])
        self.assertEqual(self.store().key_path.stat().st_size, 32)

    def test_dependency_changes_are_misses(self):
        store = self.store()
        key = {'raw_sha256': '1'*64, 'meta_sha256': '2'*64, 'algorithm_sha256': '3'*64,
               'params': {'depth': 10, 'ordering': ['slot', 'tx', 'instruction', 'ingest_seq']}}
        store.save(key, {'marker': 'current'})
        for field in ('raw_sha256', 'meta_sha256', 'algorithm_sha256', 'params'):
            changed = copy.deepcopy(key)
            changed[field] = {'depth': 11} if field == 'params' else '9'*64
            with self.subTest(field=field):
                self.assertIsNone(store.load(changed))
        self.assertEqual(store.key({'x': 1, 'y': 2}), store.key({'y': 2, 'x': 1}))
        self.assertNotEqual(store.key({'x': 1}), store.key({'x': True}))

    def test_cache_and_manifest_tampering_without_secret_rejected(self):
        store = self.store()
        key = {'raw_sha256': '1'*64, 'algorithm': '2'*64}
        artifact = self.case/'artifact.bin'
        artifact.write_bytes(b'original arithmetic')
        store.save(key, {'artifact': str(artifact), 'sha256': file_sha(artifact), 'result': 100})
        artifact.write_bytes(b'forged arithmetic!')
        envelope = json.loads(store.path(key).read_text())
        envelope['body']['payload']['sha256'] = file_sha(artifact)
        envelope['body']['payload']['result'] = 101
        store.path(key).write_text(json.dumps(envelope))
        with self.assertRaises(content_cache.CacheIntegrityError):
            store.load(key)

    def test_missing_key_cannot_authenticate_old_receipt_or_mint_replacement(self):
        store = self.store()
        key = {'source': 'original'}
        store.save(key, {'result': 1})
        saved_key = store.key_path.with_name('.local-trust-key.preserved-test-only')
        store.key_path.rename(saved_key)
        with self.assertRaises(content_cache.CacheIntegrityError):
            store.load(key)
        with self.assertRaises(content_cache.CacheIntegrityError):
            store.save(key, {'result': 2})
        self.assertFalse(store.key_path.exists())

    def test_namespace_copy_cannot_reuse_authentic_other_receipt(self):
        first, second = self.store('first'), self.store('second')
        key = {'source': 'same'}
        first.save(key, {'result': 1})
        shutil.copyfile(first.path(key), second.path(key))
        with self.assertRaises(content_cache.CacheIntegrityError):
            second.load(key)

    def test_corrupt_receipt_and_nonprivate_secret_fail_closed(self):
        store = self.store()
        key = {'source': 'first'}
        store.save(key, {'result': 1})
        store.path(key).write_bytes(b'{invalid JSON')
        with self.assertRaises(content_cache.CacheIntegrityError):
            store.load(key)
        # A separate authentic row tests key permissions, without deleting evidence.
        other = {'source': 'second'}
        store.save(other, {'result': 2})
        store.key_path.chmod(0o644)
        with self.assertRaises(content_cache.CacheIntegrityError):
            store.load(other)

    def test_receipt_symlink_and_namespace_escape_rejected(self):
        store = self.store()
        key = {'source': 'first'}
        outside = self.case/'external-receipt.json'
        outside.write_text('{}')
        store.path(key).symlink_to(outside)
        with self.assertRaises(content_cache.CacheIntegrityError):
            store.load(key)
        for namespace in ('../escape', 'bad/name', ''):
            with self.subTest(namespace=namespace), self.assertRaises(ValueError):
                self.store(namespace)



class TraceAndP4Contract(ContractCase):
    def trace_fixture(self, flip=False):
        z = '0x' + '0'*40
        events = [(1700000000, z, 'X', 10000)]
        if flip:
            events += [(1700000001, z, 'DEX', 50000),
                       (1700086400, 'DEX', 'X', 10000),
                       (1700172800, 'X', 'GONE', 10000)]
        self.make_edges([[ts, i+1, i, 0, f, t, n]
                         for i, (ts, f, t, n) in enumerate(events)])
        self.entities = self.case/'entities.json'
        self.entities.write_text(json.dumps({'test_entity': ['X']}))
        self.labels = self.case/'labels.json'
        self.labels.write_text(json.dumps({'DEX': {'kind': 'dex_pool', 'name': 'Synthetic only'}}))
        self.manifest = {'run_id': 'synthetic-performance-contract',
                         'scope': {'chain': 'solana', 'token': MINT,
                                   'cutoff_utc': '2026-08-20T00:24:05Z',
                                   'frozen_block': 100,
                                   'denominators': {'total_supply_raw': '1000000'}},
                         'artifacts': [{'path': str(p.relative_to(self.case))}
                                       for p in (self.edge, self.meta)]}
        (self.case/'handoff_manifest.json').write_text(json.dumps(self.manifest))
        (self.case/'data_map.json').write_text(json.dumps({'files': self.manifest['artifacts']}))
        self.ledger = self.case/'ledger.json'
        self.argv = ['entity_source_trace.py', '--edges-sol', str(self.edge),
                     '--sol-cache-meta', str(self.meta), '--case-root', str(self.case),
                     '--mint', MINT, '--total-supply', '1000000',
                     '--entity-file', str(self.entities), '--labels-file', str(self.labels),
                     '--out', str(self.ledger)]

    def run_trace(self, label, extra=(), omit_meta=False, forbidden=False):
        args = list(self.argv)
        if omit_meta:
            index = args.index('--sol-cache-meta')
            del args[index:index+2]
        args += list(extra)
        output, errors = io.StringIO(), io.StringIO()
        start = time.perf_counter()
        codes = {getattr(entity_source_trace, name).__code__: name
                 for name in ('compute_from_edges', 'load_sol', 'trace_entity')}
        counts = {name: 0 for name in codes.values()}
        def observe(frame, event, arg):
            if event == 'call' and frame.f_code in codes:
                counts[codes[frame.f_code]] += 1
                if forbidden:
                    raise AssertionError('confirmation/repeat performed raw arithmetic')
        # Read-only profiling leaves the guarded live function objects intact.
        previous_profile = sys.getprofile()
        with patch.object(sys, 'argv', args), redirect_stdout(output), redirect_stderr(errors):
            try:
                sys.setprofile(observe)
                rc = entity_source_trace.main()
            except SystemExit as exc:
                rc = exc.code
            finally:
                sys.setprofile(previous_profile)
                (self.case/(label+'.log')).write_text(output.getvalue()+errors.getvalue())
                TIMINGS.append({'test': self.id(), 'phase': label, 'seconds': time.perf_counter()-start,
                                'kind': 'synthetic_actual_trace_entry', 'fixture': str(self.case),
                                'observed_calls': counts})
        report = json.loads(self.ledger.read_text()) if self.ledger.is_file() else None
        if report is not None:
            (self.case/(label+'.ledger.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2))
        return rc, report, counts

    def make_confirmation(self, report):
        flips = handoff_manifest.ledger_real_flips(report)
        self.assertTrue(flips, 'fixture must actually trigger a non-dust policy flip')
        evidence = self.case/'synthetic-confirmation-evidence.txt'
        evidence.write_text('SYNTHETIC TEST FIXTURE ONLY. No real user adjudication or report approval.')
        ref = lambda p: {'path': p.name, 'size': p.stat().st_size, 'sha256': file_sha(p)}
        rows = []
        for (eid, anchor), flip in sorted(flips.items()):
            rows.append({'entity_id': eid, 'anchor': anchor,
                         'reason': 'Synthetic fixture confirms parallel policy disclosure only.',
                         'flip_fingerprint': flip['fingerprint'],
                         'disclosure': {'top_by_policy': {
                             p: {'terminal': flip['tops'][p], 'share_pct': flip['shares'][p]}
                             for p in handoff_manifest.FLIP_POLICIES},
                             'report_locations': ['synthetic fixture, no publishable report']}})
        path = self.case/'synthetic-flip-adjudications.json'
        path.write_text(json.dumps({'schema': 'flip-adjudications/v1',
                                    'approved_by': 'synthetic-test-only',
                                    'user_decided_at_utc': '2026-09-01T00:00:00Z',
                                    'entity_file': ref(self.entities), 'evidence_refs': [ref(evidence)],
                                    'adjudications': rows}))
        return path, evidence

    def p4(self, report):
        return handoff_manifest.validate_and_replay_provenance(
            str(self.case), report, str(self.ledger), str(self.entities), self.manifest)

    def test_algorithm_dependency_paths_are_real_clone_files(self):
        for name, path in trace_compute_cache.algorithm_dependency_paths().items():
            with self.subTest(name=name):
                self.assertTrue(path.is_file(), str(path))
                self.assertTrue(path.resolve().is_relative_to(ROOT))

    def test_new_loader_runtime_and_algorithm_fingerprints_are_computational(self):
        self.trace_fixture()
        self.load_edges(label='baseline')
        fingerprint = solana_edge_store.code_fingerprint
        original_build = solana_edge_store._build
        def changed_algorithm(paths):
            result = fingerprint(paths)
            # Controlled dependency-fingerprint mutation, without changing source.
            result[str(ROOT/'scripts/lib/solana_edge_store.py')] = 'f'*64
            return result
        with patch.object(solana_edge_store, 'code_fingerprint', side_effect=changed_algorithm), \
             observe_calls({'build': original_build}) as build:
            self.expect_loader_rejection()
            self.assertEqual(build['build'], 0)
        with patch.object(solana_edge_store.zlib, 'ZLIB_RUNTIME_VERSION', 'synthetic-different-runtime'), \
             observe_calls({'build': original_build}) as build:
            self.load_edges(label='runtime_fingerprint_changed')
            self.assertEqual(build['build'], 1)

    def test_current_change_during_materialized_load_is_rejected_before_return(self):
        self.trace_fixture()
        self.load_edges(label='baseline')
        parent, current, _ = sqd_cache_identity.sqd_repair_paths(self.case, MINT)
        parent.mkdir(parents=True, exist_ok=True)
        original = solana_edge_store.load_materialized
        def change_after_attach(*args, **kwargs):
            value = original(*args, **kwargs)
            current.write_text(json.dumps({'schema': 'invalid-current-during-load'}))
            return value
        with patch.object(solana_edge_store, 'load_materialized', side_effect=change_after_attach):
            self.expect_loader_rejection()

    def test_optional_meta_uses_formal_resolver_without_request_conflict(self):
        self.trace_fixture()
        rc, report, calls = self.run_trace('meta_omitted', omit_meta=True)
        self.assertEqual(rc, 0)
        self.assertEqual(report['input_binding']['edge_source_binding']['cache_kind'], 'base')
        self.assertEqual(calls['compute_from_edges'], 1)


    def test_formal_loader_rejects_resident_module_after_source_edit(self):
        self.trace_fixture()
        clone_lib = self.case/'isolated-loaded-module/scripts/lib'
        clone_sol = clone_lib.parent/'solana'
        clone_lib.mkdir(parents=True)
        clone_sol.mkdir()
        for original, destination in (
            (ROOT/'scripts/lib/solana_edge_store.py', clone_lib/'solana_edge_store.py'),
            (ROOT/'scripts/lib/content_cache.py', clone_lib/'content_cache.py'),
            (ROOT/'scripts/solana/spl_edge_core.py', clone_sol/'spl_edge_core.py')):
            shutil.copyfile(original, destination)
        module_path = clone_lib/'solana_edge_store.py'
        spec = importlib.util.spec_from_file_location('codex_resident_edge_store', module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.dict(sys.modules, {'solana_edge_store': module}):
            self.load_edges(label='resident_copy_initial')
            before, stat = module_path.read_bytes(), module_path.stat()
            (self.case/'resident_loader_source_original.preserved').write_bytes(before)
            changed = before.replace(b'integer-exact', b'integer-Exact', 1)
            self.assertEqual(len(changed), len(before))
            self.assertNotEqual(changed, before)
            module_path.write_bytes(changed)
            os.utime(module_path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
            self.expect_loader_rejection()
        # A genuinely re-imported implementation may compute its new cache key.
        spec = importlib.util.spec_from_file_location('codex_restarted_edge_store', module_path)
        restarted = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(restarted)
        with patch.dict(sys.modules, {'solana_edge_store': restarted}), \
             observe_calls({'build': restarted._build}) as build:
            self.load_edges(label='restarted_after_algorithm_edit')
            self.assertEqual(build['build'], 1)

    def test_trace_rejects_resident_module_after_source_edit(self):
        self.trace_fixture()
        isolated = self.case/'isolated-trace-tree'
        for source in trace_compute_cache.algorithm_dependency_paths().values():
            target = isolated/source.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        config = self.case/'resident_trace_config.json'
        config.write_text(json.dumps({'root': str(ROOT), 'isolated': str(isolated),
                                      'argv': self.argv}))
        driver = self.case/'resident_trace_driver.py'
        driver.write_text("""import hashlib, json, os, sys
from pathlib import Path
base = Path(__file__).resolve().parent
cfg = json.loads((base/'resident_trace_config.json').read_text())
phase = sys.argv[1]
for root in (Path(cfg['root']), Path(cfg['isolated'])):
    for sub in ('scripts/lib', 'scripts/solana', 'scripts/report'):
        sys.path.insert(0, str(root/sub))
import entity_source_trace as trace
def call():
    counts = {name: 0 for name in ('compute_from_edges', 'load_sol', 'trace_entity')}
    codes = {getattr(trace, name).__code__: name for name in counts}
    def observe(frame, event, arg):
        if event == 'call' and frame.f_code in codes:
            counts[codes[frame.f_code]] += 1
    sys.argv = cfg['argv']
    previous = sys.getprofile()
    try:
        sys.setprofile(observe)
        try: rc = trace.main()
        except SystemExit as exc: rc = exc.code
    finally:
        sys.setprofile(previous)
    return {'returncode': rc, 'observed_calls': counts}
result = {'phase': phase, 'first': call()}
if phase == 'first_edit':
    path = Path(trace.__file__)
    original, stat = path.read_bytes(), path.stat()
    (base/'resident_trace_source_original.preserved').write_bytes(original)
    changed = original.replace(b'full hashes', b'Full hashes', 1)
    assert changed != original and len(changed) == len(original)
    ledger = Path(cfg['argv'][cfg['argv'].index('--out')+1])
    old_ledger_sha = hashlib.sha256(ledger.read_bytes()).hexdigest()
    path.write_bytes(changed)
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    result['after_edit'] = call()
    result['rejection_left_ledger_unchanged'] = hashlib.sha256(ledger.read_bytes()).hexdigest() == old_ledger_sha
(base/('resident_outcomes_'+phase+'.json')).write_text(json.dumps(result, indent=2))
""")
        for phase in ('first_edit', 'restart'):
            started = time.perf_counter()
            process = handoff_manifest.subprocess.run(
                [sys.executable, str(driver), phase], capture_output=True, text=True,
                env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', CHIP_BLIND_SERIAL='1'))
            (self.case/('resident_trace_'+phase+'.log')).write_text(process.stdout+process.stderr)
            self.assertEqual(process.returncode, 0, process.stdout+process.stderr)
            result = json.loads((self.case/('resident_outcomes_'+phase+'.json')).read_text())
            self.assertEqual(result['first']['returncode'], 0, result)
            self.assertEqual(result['first']['observed_calls']['compute_from_edges'], 1)
            if phase == 'first_edit':
                self.assertEqual(result['after_edit']['returncode'], 2, result)
                self.assertEqual(sum(result['after_edit']['observed_calls'].values()), 0)
                self.assertTrue(result['rejection_left_ledger_unchanged'])
            TIMINGS.append({'test': self.id(), 'phase': 'resident_trace_'+phase,
                            'kind': 'synthetic_subprocess_resident_algorithm', 'fixture': str(self.case),
                            'seconds': time.perf_counter()-started, 'observed': result})


    def test_preimported_helper_edit_cannot_bind_stale_code_to_new_source(self):
        self.trace_fixture()
        isolated = self.case/'isolated-preimport-tree'
        for source in trace_compute_cache.algorithm_dependency_paths().values():
            target = isolated/source.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        (self.case/'preimport_config.json').write_text(json.dumps(
            {'root': str(ROOT), 'isolated': str(isolated), 'argv': self.argv}))
        driver = self.case/'preimport_driver.py'
        driver.write_text("""import hashlib, json, os, sys
from pathlib import Path
from datetime import datetime, timezone
base = Path(__file__).resolve().parent
cfg = json.loads((base/'preimport_config.json').read_text())
phase = sys.argv[1]
for root in (Path(cfg['root']), Path(cfg['isolated'])):
    for sub in ('scripts/lib', 'scripts/solana', 'scripts/report'):
        sys.path.insert(0, str(root/sub))
# This is an ordinary module import, before the shared trace guard exists.
import wave_scan
path = Path(wave_scan.__file__)
result = {'phase': phase, 'loaded_wave_day_20000': wave_scan.day_str(20000),
          'expected_modified_day_20000': datetime.fromtimestamp(20000*86000, timezone.utc).strftime('%Y-%m-%d'),
          'observed_calls': {'compute_from_edges': 0, 'load_sol': 0, 'trace_entity': 0}}
if phase == 'preimport_edit':
    original, stat = path.read_bytes(), path.stat()
    (base/'preimport_wave_source_original.preserved').write_bytes(original)
    changed = original.replace(b'day * 86400', b'day * 86000', 1)
    assert changed != original and len(changed) == len(original)
    path.write_bytes(changed)
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    result['same_size_and_mtime'] = path.stat().st_size == stat.st_size and path.stat().st_mtime_ns == stat.st_mtime_ns
result['wave_disk_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
try:
    import entity_source_trace as trace
except Exception as exc:
    if type(exc).__name__ != 'AlgorithmRuntimeDriftError': raise
    result.update(returncode=2, import_rejection=str(exc))
else:
    result['loaded_trace_day_20000'] = trace.day_str(20000)
    codes = {getattr(trace, name).__code__: name for name in result['observed_calls']}
    def observe(frame, event, arg):
        if event == 'call' and frame.f_code in codes:
            result['observed_calls'][codes[frame.f_code]] += 1
    sys.argv = cfg['argv']
    previous = sys.getprofile()
    try:
        sys.setprofile(observe)
        try: result['returncode'] = trace.main()
        except SystemExit as exc: result['returncode'] = exc.code
    finally:
        sys.setprofile(previous)
ledger = Path(cfg['argv'][cfg['argv'].index('--out')+1])
result['ledger_exists'] = ledger.is_file()
if ledger.is_file():
    result['ledger_bound_wave_sha256'] = json.loads(ledger.read_text())['input_binding']['algorithm']['files']['wave_scan.py']['sha256']
(base/('preimport_outcomes_'+phase+'.json')).write_text(json.dumps(result, indent=2))
""")
        outcomes = {}
        for phase in ('preimport_edit', 'fresh_restart'):
            started = time.perf_counter()
            process = handoff_manifest.subprocess.run(
                [sys.executable, str(driver), phase], capture_output=True, text=True,
                env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', CHIP_BLIND_SERIAL='1'))
            (self.case/('preimport_'+phase+'.log')).write_text(process.stdout+process.stderr)
            self.assertEqual(process.returncode, 0, process.stdout+process.stderr)
            result = json.loads((self.case/('preimport_outcomes_'+phase+'.json')).read_text())
            outcomes[phase] = result
            TIMINGS.append({'test': self.id(), 'phase': phase,
                            'kind': 'synthetic_preimported_dependency_probe', 'fixture': str(self.case),
                            'seconds': time.perf_counter()-started, 'observed': result})
        stale, restarted = outcomes['preimport_edit'], outcomes['fresh_restart']
        self.assertTrue(stale['same_size_and_mtime'])
        self.assertNotEqual(stale['loaded_wave_day_20000'], stale['expected_modified_day_20000'])
        self.assertEqual(stale['returncode'], 2,
                         'a helper loaded before the guard must not bind old code to new disk source')
        self.assertEqual(sum(stale['observed_calls'].values()), 0)
        self.assertFalse(stale['ledger_exists'])
        self.assertEqual(restarted['returncode'], 0, restarted)
        self.assertEqual(restarted['loaded_trace_day_20000'], restarted['expected_modified_day_20000'])
        self.assertEqual(restarted['observed_calls']['compute_from_edges'], 1)

    def test_trace_raw_physical_change_recomputes_even_when_logical_rows_same(self):
        self.trace_fixture()
        self.assertEqual(self.run_trace('initial')[0], 0)
        raw = bytearray(self.edge.read_bytes())
        raw[4] ^= 1  # valid gzip header-only byte mutation; logical rows unchanged
        self.edge.write_bytes(raw)
        rc, _, calls = self.run_trace('raw_physical_bytes')
        self.assertEqual(rc, 0)
        self.assertEqual(calls['compute_from_edges'], 1)

    def test_initial_repeat_confirmation_and_parameter_change_real_calls(self):
        self.trace_fixture(flip=True)
        rc, first, calls = self.run_trace('initial')
        self.assertEqual(rc, 2)
        self.assertFalse(first['bounds_sensitivity']['publishable'])
        self.assertEqual(calls, {'compute_from_edges': 1, 'load_sol': 1, 'trace_entity': 1})
        rc, repeat, calls = self.run_trace('repeat', forbidden=True)
        self.assertEqual(rc, 2)
        self.assertFalse(repeat['bounds_sensitivity']['publishable'])
        self.assertEqual(sum(calls.values()), 0)
        receipt, evidence = self.make_confirmation(first)
        rc, confirmed, calls = self.run_trace('confirmation', ['--acknowledge-flip', str(receipt)], forbidden=True)
        self.assertEqual(rc, 0)
        self.assertTrue(confirmed['bounds_sensitivity']['publishable'])
        self.assertEqual(sum(calls.values()), 0)
        self.assertEqual(trace_compute_cache.computation_output(first),
                         trace_compute_cache.computation_output(confirmed))
        # Confirmation is not a stored PASS: returning to absent receipt blocks.
        rc, unconfirmed, calls = self.run_trace('confirmation_removed', forbidden=True)
        self.assertEqual(rc, 2)
        self.assertFalse(unconfirmed['bounds_sensitivity']['publishable'])
        self.assertEqual(sum(calls.values()), 0)
        rc, changed, calls = self.run_trace('parameter_changed',
                              ['--depth-limit', '9', '--acknowledge-flip', str(receipt)])
        self.assertEqual(rc, 0)
        self.assertEqual(calls, {'compute_from_edges': 1, 'load_sol': 1, 'trace_entity': 1})
        # Current confirmation evidence is re-read before any arithmetic/cache use.
        evidence.write_text('MUTATED synthetic test evidence; receipt hash is intentionally stale.')
        rc, _, calls = self.run_trace('stale_confirmation',
                         ['--depth-limit', '9', '--acknowledge-flip', str(receipt)], forbidden=True)
        self.assertEqual(rc, 2)
        self.assertEqual(sum(calls.values()), 0)

    def test_semantic_input_changes_recompute_while_bookkeeping_rebinds(self):
        self.trace_fixture()
        self.assertEqual(self.run_trace('initial')[0], 0)
        self.manifest['run_id'] = 'different-synthetic-bookkeeping-run'
        (self.case/'handoff_manifest.json').write_text(json.dumps(self.manifest))
        rc, rebound, calls = self.run_trace('bookkeeping', forbidden=True)
        self.assertEqual(rc, 0)
        self.assertEqual(rebound['input_binding']['handoff_manifest']['run_id'], self.manifest['run_id'])
        self.assertEqual(sum(calls.values()), 0)
        changes = [
            ('labels', self.labels, {'DEX': {'kind': 'cex', 'name': 'Changed synthetic label'}}),
            ('members', self.entities, {'test_entity': ['X', 'UNUSED']}),
        ]
        for phase, path, payload in changes:
            path.write_text(json.dumps(payload))
            rc, _, calls = self.run_trace(phase)
            self.assertEqual(rc, 0)
            self.assertEqual(calls['compute_from_edges'], 1)
        self.manifest['scope']['frozen_block'] = 99
        (self.case/'handoff_manifest.json').write_text(json.dumps(self.manifest))
        rc, _, calls = self.run_trace('scope')
        self.assertEqual(rc, 0)
        self.assertEqual(calls['compute_from_edges'], 1)
        # Meta formatting changes bytes even with unchanged source semantics.
        self.meta.write_text(json.dumps(json.loads(self.meta.read_text()), indent=2))
        rc, _, calls = self.run_trace('meta_bytes')
        self.assertEqual(rc, 0)
        self.assertEqual(calls['compute_from_edges'], 1)

    def test_p4_first_replay_forces_compute_off_and_cannot_use_producer_cache(self):
        self.trace_fixture()
        rc, report, _ = self.run_trace('initial')
        self.assertEqual(rc, 0)
        # An authentic producer cache exists, but no independent receipt exists.
        independent = content_cache.CacheStore(self.case, trace_compute_cache.INDEPENDENT_NAMESPACE)
        self.assertFalse(list(independent.directory.glob('*.json')))
        original = handoff_manifest.subprocess.run
        with patch.object(handoff_manifest.subprocess, 'run', wraps=original) as subprocess_call:
            failures = self.p4(report)
        self.assertEqual(failures, [])
        self.assertEqual(subprocess_call.call_count, 1)
        command = subprocess_call.call_args.args[0]
        self.assertEqual(command[command.index('--compute-cache-mode')+1], 'off')
        self.assertTrue(list(independent.directory.glob('*.json')))
        # A later valid independent-result receipt may be reused, never its PASS.
        with patch.object(handoff_manifest.subprocess, 'run',
                          side_effect=AssertionError('unchanged independent receipt unexpectedly recomputed')):
            self.assertEqual(self.p4(report), [])
        with patch.dict(os.environ, {'CHIP_FORCE_INDEPENDENT_TRACE': '1'}), \
             patch.object(handoff_manifest.subprocess, 'run', wraps=original) as forced:
            self.assertEqual(self.p4(report), [])
            self.assertEqual(forced.call_count, 1)

    def test_forged_candidate_with_authentic_producer_cache_still_fails_p4(self):
        self.trace_fixture()
        rc, report, _ = self.run_trace('initial')
        self.assertEqual(rc, 0)
        producer = content_cache.CacheStore(self.case, trace_compute_cache.PRODUCER_NAMESPACE)
        key = trace_compute_cache.computation_inputs(report['input_binding'])
        payload = producer.load(key)
        payload['entities'][0]['anchors']['current']['direct_upstream'][0]['addr'] = 'FORGED_TEST_SOURCE'
        producer.save(key, payload)  # models the result producer under review, not an HMAC attack
        rc, forged, calls = self.run_trace('candidate_from_producer_cache', forbidden=True)
        self.assertEqual(rc, 0)
        self.assertEqual(sum(calls.values()), 0)
        original = handoff_manifest.subprocess.run
        with patch.object(handoff_manifest.subprocess, 'run', wraps=original) as subprocess_call:
            failures = self.p4(forged)
        self.assertEqual(subprocess_call.call_count, 1)
        self.assertTrue(any('摘要' in x for x in failures), failures)
        independent = content_cache.CacheStore(self.case, trace_compute_cache.INDEPENDENT_NAMESPACE)
        self.assertFalse(list(independent.directory.glob('*.json')))


class DeepReadClosureContract(ContractCase):
    def deep_fixture(self):
        # Existing native v4 fixture, with genuine coverage and reconcile producer.
        from test_reconcile_v4_receipt import prepare_complete_case, make_reconcile
        # Initialize the library adapter before auditing evidence reads. Runtime
        # package imports are separate from the validator's case dependencies.
        pa.array(['initialize Arrow adapter'], type=pa.string())
        with patch.dict(os.environ, {'CHIP_DEEP_CACHE': '0'}):
            rows, edge, meta = prepare_complete_case(self.case)
            receipt, _, _, _, result = make_reconcile(self.case, rows, edge, meta)
        self.assertIs(result, True)
        self.deep_receipt = receipt
        return receipt

    def validate(self, phase, force=False):
        context = deep_validation_cache.force_deep_validation if force else None
        start = time.perf_counter()
        original = solana_exact_validate._stream_reconcile_summary
        with patch.object(solana_exact_validate, '_stream_reconcile_summary', wraps=original) as replay:
            if context:
                with context('codex independent acceptance'):
                    result = solana_exact_validate.validate_reconcile_receipt_deep(
                        self.deep_receipt, case_root=self.case)
            else:
                result = solana_exact_validate.validate_reconcile_receipt_deep(
                    self.deep_receipt, case_root=self.case)
        TIMINGS.append({'test': self.id(), 'phase': phase, 'seconds': time.perf_counter()-start,
                        'fixture': str(self.case), 'kind': 'synthetic_actual_deep_validator',
                        'observed_edge_replays': replay.call_count})
        return result, replay.call_count

    def proof(self):
        store = content_cache.CacheStore(self.case, 'solana-deep-validation')
        receipts = list(store.directory.glob('*.json'))
        self.assertEqual(len(receipts), 1)
        body = json.loads(receipts[0].read_text())['body']
        return body['payload']['read_proof'], body, receipts[0]

    def test_actual_read_closure_includes_transitive_coverage_and_producer(self):
        global AUDIT_READS
        self.deep_fixture()
        AUDIT_READS = []
        AUDIT_DIRECTORY_OPENS.clear()
        AUDIT_AUTH_KEY_OPENS.clear()
        AUDIT_GENERATED_OUTPUTS.clear()
        try:
            first, replays = self.validate('first')
            observed = sorted(set(AUDIT_READS))
        finally:
            AUDIT_READS = None
        self.assertTrue(first['ok'], first['reasons'])
        self.assertGreater(replays, 0)
        proof, body, path = self.proof()
        proven = {row['path'] for row in proof['files']}
        bound_algorithms = set(body['inputs']['algorithm'])
        missing = sorted(set(observed)-proven-bound_algorithms)
        for output in AUDIT_GENERATED_OUTPUTS:
            self.assertTrue(any(row['bytes'] == output['bytes'] and row['sha256'] == output['sha256']
                                for row in proof['files']), output)
        (self.case/'independent-read-closure.json').write_text(json.dumps(
            {'observed_open_paths': observed, 'proof_paths': sorted(proven), 'missing': missing,
             'authentication_key_opens_not_analysis_evidence': list(AUDIT_AUTH_KEY_OPENS),
             'runtime_adapter_initialized_before_evidence_capture': True,
             'algorithm_paths_bound_separately': sorted(bound_algorithms),
             'generated_output_reads_rebound_by_sha_under_final_paths': list(AUDIT_GENERATED_OUTPUTS),
             'scope': 'actual reconcile base fixture including nested coverage; not all repair branches',
             'proof_receipt': str(path), 'proof_sha256': file_sha(path)}, indent=2))
        self.assertTrue(observed)
        self.assertEqual(missing, [])
        self.assertIn(str(ROOT/'scripts/solana/sqd_coverage_probe.py'), proven)
        self.assertTrue(any(p.endswith('CURRENT.json') for p in proven))
        self.assertTrue(any(p.endswith('.jsonl.gz') for p in proven))
        second, replays = self.validate('repeat')
        self.assertEqual(first, second)
        self.assertEqual(replays, 0)
        forced, replays = self.validate('forced_independent', force=True)
        self.assertEqual(first, forced)
        self.assertGreater(replays, 0)

    def test_each_fixture_leaf_mutation_invalidates_deep_reuse(self):
        self.deep_fixture()
        first, _ = self.validate('first')
        self.assertTrue(first['ok'], first['reasons'])
        proof, _, _ = self.proof()
        leaves = [Path(row['path']) for row in proof['files']
                  if Path(row['path']).is_relative_to(self.case)
                  and not Path(row['path']).is_relative_to(self.case/'runtime-cache')]
        self.assertGreaterEqual(len(leaves), 8)
        for index, path in enumerate(leaves):
            with self.subTest(path=path):
                before, stat = path.read_bytes(), path.stat()
                mutated = bytearray(before)
                mutated[len(mutated)//2] ^= 1
                # Preserve all original test evidence explicitly; no deletions.
                (self.case/f'leaf_{index}_original.bin').write_bytes(before)
                path.write_bytes(mutated)
                os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
                counters = deep_validation_cache.cache_counters()
                try:
                    result, _ = self.validate(f'mutate_leaf_{index}')
                    self.assertFalse(result['ok'], path)
                except (ValueError, OSError, UnicodeDecodeError, zlib.error):
                    pass  # malformed input must never turn into a reusable PASS
                finally:
                    path.write_bytes(before)
                    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
                after = deep_validation_cache.cache_counters()
                self.assertGreater(after['deep_runs'], counters['deep_runs'])
                self.assertEqual(after['reuses'], counters['reuses'])
        restored, replays = self.validate('restored')
        self.assertEqual(first, restored)
        self.assertEqual(replays, 0)


    def test_repair_generation_read_closure_and_canary_forces_independence(self):
        global AUDIT_READS
        import test_sqd_gap_repair as fixtures
        from scripts.solana import sqd_gap_repair as repair
        slot = 15000
        root = self.case/'repair-fixture-build'
        z = '0x' + '0'*40
        # Independent entirely synthetic nonce transfer; never reads staged ARC txs.
        alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
        number, nonce_data = int.from_bytes(b'\x04\x00\x00\x00', 'big'), ''
        while number:
            number, remainder = divmod(number, 58)
            nonce_data = alphabet[remainder]+nonce_data
        balance = lambda index, owner, amount: {
            'accountIndex': index, 'mint': MINT, 'owner': owner,
            'uiTokenAmount': {'amount': str(amount), 'decimals': 6}}
        tx = {'transaction': {
                  'signatures': ['SyntheticMissingNonceSignature'],
                  'message': {'accountKeys': ['TokenA', 'TokenB', '11111111111111111111111111111111'],
                              'instructions': [{'programIdIndex': 2, 'accounts': [], 'data': nonce_data}]}},
              'meta': {'err': None, 'loadedAddresses': {},
                       'preTokenBalances': [balance(0, 'OwnerA', 100), balance(1, 'OwnerB', 0)],
                       'postTokenBalances': [balance(0, 'OwnerA', 93), balance(1, 'OwnerB', 7)]}}
        self.assertTrue(repair.is_nonce_transaction(tx))
        captured = io.StringIO()
        with redirect_stdout(captured), redirect_stderr(captured), \
             patch.dict(os.environ, {'CHIP_DEEP_CACHE': '0'}):
            case = fixtures.build_batch3b_case(root, {slot},
                       [[1700000000, 12000, 0, -1, z, 'OwnerA', 100]])
            responses = fixtures.repair_slot_responses(repair, slot, tx, nonce_count=0)
            transport = fixtures.write_repair_fixture(root/'transport', responses)
            rc = repair.main(['repair', '--mint', MINT, '--case-root', str(case),
                              '--transport-fixture', str(transport)])
        (self.case/'repair_fixture_creation.log').write_text(captured.getvalue())
        self.assertEqual(rc, 0, captured.getvalue())
        parent, pointer, _ = sqd_cache_identity.sqd_repair_paths(case, MINT)
        generation = parent/('gen-'+json.loads(pointer.read_text())['gid'])
        bundle = generation/'bundle.json'
        bundle_json = json.loads(bundle.read_text())
        base = {'edge_sha256': file_sha(case/bundle_json['base']['edge_file'])}
        raw_replay = solana_exact_validate._iter_edge_rows
        AUDIT_READS = []
        AUDIT_DIRECTORY_OPENS.clear()
        AUDIT_AUTH_KEY_OPENS.clear()
        AUDIT_GENERATED_OUTPUTS.clear()
        try:
            with patch.object(solana_exact_validate, '_iter_edge_rows', wraps=raw_replay) as replay:
                first = solana_exact_validate.validate_repair_bundle_deep(
                    bundle, case_root=case, current_base=base)
                first_replays = replay.call_count
            observed = sorted(set(AUDIT_READS))
        finally:
            AUDIT_READS = None
        self.assertTrue(first['ok'], first['reasons'])
        self.assertGreater(first_replays, 0)
        store = content_cache.CacheStore(case, 'solana-deep-validation')
        receipts = list(store.directory.glob('*.json'))
        self.assertEqual(len(receipts), 1)
        body = json.loads(receipts[0].read_text())['body']
        payload = body['payload']
        proven = {row['path'] for row in payload['read_proof']['files']}
        bound_algorithms = set(body['inputs']['algorithm'])
        missing = sorted(set(observed)-proven-bound_algorithms)
        for output in AUDIT_GENERATED_OUTPUTS:
            self.assertTrue(any(row['bytes'] == output['bytes'] and row['sha256'] == output['sha256']
                                for row in payload['read_proof']['files']), output)
        self.assertEqual(missing, [])
        self.assertTrue(any(p.endswith('evidence_manifest.json') for p in proven))
        self.assertTrue(any(p.endswith('rpc_ledger.jsonl') for p in proven))
        self.assertTrue(any('/evidence/' in p for p in proven))
        (self.case/'repair-independent-read-closure.json').write_text(json.dumps({
            'observed_open_paths': observed, 'proof_paths': sorted(proven), 'missing': missing,
            'scratch_directory_opens_not_evidence_files': list(AUDIT_DIRECTORY_OPENS),
            'authentication_key_opens_not_analysis_evidence': list(AUDIT_AUTH_KEY_OPENS),
            'algorithm_paths_bound_separately': sorted(bound_algorithms),
            'generated_output_reads_rebound_by_sha_under_final_paths': list(AUDIT_GENERATED_OUTPUTS),
            'proof_receipt': str(receipts[0]), 'proof_sha256': file_sha(receipts[0]),
            'scope': 'synthetic formal coverage-triggered repair; no beta/shared-map or fallback-sort branch'}, indent=2))
        with patch.object(solana_exact_validate, '_iter_edge_rows',
                          side_effect=AssertionError('unchanged repair unexpectedly replayed')):
            second = solana_exact_validate.validate_repair_bundle_deep(
                bundle, case_root=case, current_base=base)
        self.assertEqual(first, second)
        rpc_key = repair.request_digest('reference-getBlock', repair._rpc_body(slot))
        actual_block = responses[rpc_key]['value']['result']
        canary = unittest.mock.Mock(return_value=actual_block)
        with patch.object(solana_exact_validate, '_iter_edge_rows', wraps=raw_replay) as replay:
            checked = solana_exact_validate.validate_repair_bundle_deep(
                bundle, case_root=case, current_base=base, live_canary=1, live_canary_fetch=canary)
        self.assertTrue(checked['ok'], checked['reasons'])
        self.assertGreater(replay.call_count, 0)
        canary.assert_called_once_with(slot)
        # This coverage evidence is read transitively by the real repair helper.
        leaf = next(Path(p) for p in proven if '/evidence/' in p and p.endswith('.json'))
        before, stat = leaf.read_bytes(), leaf.stat()
        data = bytearray(before)
        data[len(data)//2] ^= 1
        (self.case/'repair_evidence_original.bin').write_bytes(before)
        leaf.write_bytes(data)
        os.utime(leaf, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        counters = deep_validation_cache.cache_counters()
        try:
            changed = solana_exact_validate.validate_repair_bundle_deep(
                bundle, case_root=case, current_base=base)
            self.assertFalse(changed['ok'])
        finally:
            leaf.write_bytes(before)
            os.utime(leaf, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        after = deep_validation_cache.cache_counters()
        self.assertGreater(after['deep_runs'], counters['deep_runs'])
        self.assertEqual(after['reuses'], counters['reuses'])


    def test_deep_payload_and_manifest_joint_forgery_cannot_reuse_pass(self):
        self.deep_fixture()
        first, _ = self.validate('first')
        self.assertTrue(first['ok'], first['reasons'])
        _, _, path = self.proof()
        envelope = json.loads(path.read_text())
        payload = envelope['body']['payload']
        payload['result'] = deep_validation_cache._pack({'ok': True, 'reasons': [], 'forged': True})
        payload['result_sha256'] = hashlib.sha256(content_cache.canonical_bytes(payload['result'])).hexdigest()
        path.write_text(json.dumps(envelope))
        result, replays = self.validate('forged_cache_and_receipt')
        self.assertTrue(result['ok'], result['reasons'])
        self.assertGreater(replays, 0)
        self.assertNotIn('forged', result)



class DeepRawRowsContract(ContractCase):
    def deep_rows(self, path, *, force=False):
        token = deep_validation_cache._CASE_ROOT.set(str(self.case))
        try:
            # Retain the real parser.__code__ dependency and instrument its
            # gzip reader, so a counter does not alter the cache identity.
            with patch.object(solana_exact_validate, 'tracked_gzip_text',
                              wraps=solana_exact_validate.tracked_gzip_text) as read:
                if force:
                    with deep_edge_rows_cache.force_raw_edge_parsing('codex decoder independence'):
                        value = list(solana_exact_validate._iter_edge_rows(path))
                else:
                    value = list(solana_exact_validate._iter_edge_rows(path))
                return value, read.call_count
        finally:
            deep_validation_cache._CASE_ROOT.reset(token)

    def test_arrow_raw_decoder_keeps_python_integer_and_original_tuple_contract(self):
        source = self.case/'independent-deep-only-source.jsonl.gz'
        rows = [[-(2**140), 2**140, -(2**130), -1.0, '', '\ud800', 2**200+123],
                [0, -1, 2**63, -1, 'tab\tnew\nline', '尾址', 2**64+1],
                [0, -1, 2**63, -1, 'tab\tnew\nline', '尾址', 2**64+1]]
        # These values test the pre-existing deep decoder, not formal loader acceptance.
        source.write_bytes(gzip.compress(''.join(json.dumps(r)+'\n' for r in rows).encode(), mtime=0))
        first, parses = self.deep_rows(source)
        self.assertGreater(parses, 0)
        second, parses = self.deep_rows(source)
        self.assertEqual(parses, 0)
        self.assertEqual(first, [tuple(r) for r in rows])
        self.assertEqual(first, second)
        self.assertIs(type(first[0][3]), float)
        self.assertIs(type(second[0][3]), float)
        self.assertIs(type(second[1][3]), int)
        fresh, parses = self.deep_rows(source, force=True)
        self.assertGreater(parses, 0)
        self.assertEqual(fresh, first)


    def test_raw_parser_loaded_code_change_cannot_reuse_old_rows_under_new_disk_sha(self):
        source = self.case/'raw.jsonl.gz'
        source.write_bytes(gzip.compress((json.dumps([100, 10, 0, -1, 'A', 'B', 100])+'\n').encode(), mtime=0))
        parser_file = self.case/'independent_parser.py'
        template = ("import json\nfrom deep_validation_cache import tracked_gzip_text\n"
                    "def parser(path, *, reason=None):\n"
                    "    with tracked_gzip_text(path) as handle:\n"
                    "        for line in handle:\n"
                    "            row = json.loads(line)\n"
                    "            row[6] += {increment}\n"
                    "            yield tuple(row)\n")
        parser_file.write_text(template.format(increment=0))
        (self.case/'parser_before.py.preserved').write_bytes(parser_file.read_bytes())
        spec = importlib.util.spec_from_file_location('codex_original_parser', parser_file)
        old_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(old_module)
        # Simulates editing algorithm source while an earlier import is resident.
        parser_file.write_text(template.format(increment=1))
        token = deep_validation_cache._CASE_ROOT.set(str(self.case))
        try:
            old_rows = list(deep_edge_rows_cache.reusable_edge_rows(
                source, old_module.parser, solana_exact_validate._validated_edge))
            spec = importlib.util.spec_from_file_location('codex_updated_parser', parser_file)
            new_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(new_module)
            actual_new_rows = list(deep_edge_rows_cache.reusable_edge_rows(
                source, new_module.parser, solana_exact_validate._validated_edge))
            independent_new_rows = list(new_module.parser(source))
        finally:
            deep_validation_cache._CASE_ROOT.reset(token)
        (self.case/'loaded_algorithm_identity.json').write_text(json.dumps({
            'old_rows': old_rows, 'new_cached_rows': actual_new_rows,
            'new_independent_rows': independent_new_rows,
            'current_parser_file_sha256': file_sha(parser_file),
            'scope': 'synthetic parser identity at actual raw-cache API; no native module edited'}, indent=2))
        self.assertNotEqual(old_rows, independent_new_rows)
        self.assertEqual(actual_new_rows, independent_new_rows,
                         'old in-memory parser signed rows under new disk SHA; updated parser reused stale rows')


    def test_raw_arrow_artifact_and_receipt_forgery_reparse_original(self):
        source = self.case/'raw.jsonl.gz'
        expected = [(100, 10, 0, -1, 'A', 'B', 2**100+1)]
        source.write_bytes(gzip.compress((json.dumps(expected[0])+'\n').encode(), mtime=0))
        self.assertEqual(self.deep_rows(source)[0], expected)
        store = content_cache.CacheStore(self.case, 'solana-deep-raw-rows')
        manifest = next(store.directory.glob('*.json'))
        envelope = json.loads(manifest.read_text())
        artifact = store.directory/envelope['body']['payload']['artifact']
        before, stat = artifact.read_bytes(), artifact.stat()
        data = bytearray(before); data[len(data)//2] ^= 1
        artifact.write_bytes(data)
        os.utime(artifact, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        # The attacker knows checksums but not the independent key.
        envelope['body']['payload']['artifact_file']['sha256'] = file_sha(artifact)
        manifest.write_text(json.dumps(envelope))
        result, parses = self.deep_rows(source)
        self.assertEqual(result, expected)
        self.assertGreater(parses, 0)

    def test_deep_validation_consumes_main_materialization_but_recomputes_accounting(self):
        helper = DeepReadClosureContract('test_actual_read_closure_includes_transitive_coverage_and_producer')
        helper.case, helper.metrics = self.case, self.metrics
        helper.deep_fixture()
        data = self.case/'data'
        edge = next(data.glob('soltx-*.jsonl.gz'))
        meta = next(data.glob('soltx-*.meta.json'))
        from test_reconcile_v4_receipt import MINT as fixture_mint
        con = duckdb.connect()
        try:
            wave_scan.load_sol(con, str(edge), cache_meta_path=str(meta),
                               expected_mint=fixture_mint, case_root=str(self.case))
        finally:
            con.close()
        # Raw decoder prohibited, while the real ledger/accounting helper must run.
        original = solana_exact_validate._stream_reconcile_summary
        with observe_calls({'parser': solana_exact_validate._parse_edge_rows,
                            'account': original}, forbidden=('parser',)) as account:
            result, _ = helper.validate('main_materialization_independent_deep', force=True)
        self.assertTrue(result['ok'], result['reasons'])
        self.assertGreater(account['account'], 0)
        events = [json.loads(line) for line in self.metrics.read_text().splitlines()]
        self.assertTrue(any(e['event'] == 'raw_materialization_shared' for e in events))
        # Unlike a stale PASS cache, main rows are revalidated with deep's own rule.
        db_store = content_cache.CacheStore(self.case, 'solana-edges')
        manifest = next(db_store.directory.glob('*.json'))
        envelope = json.loads(manifest.read_text())
        database = db_store.directory/(manifest.stem+'.duckdb')
        changed = bytearray(database.read_bytes()); changed[len(changed)//2] ^= 1
        database.write_bytes(changed)
        envelope['body']['payload']['database_sha256'] = file_sha(database)
        manifest.write_text(json.dumps(envelope))
        with patch.object(solana_exact_validate, 'tracked_gzip_text',
                          wraps=solana_exact_validate.tracked_gzip_text) as parse:
            repaired, _ = helper.validate('rejected_main_cache_fresh_deep', force=True)
        self.assertTrue(repaired['ok'], repaired['reasons'])
        self.assertGreater(parse.call_count, 0)
        self.assertEqual(result, repaired)


def main():
    selected = sys.argv[1:]
    suite = (unittest.defaultTestLoader.loadTestsFromNames(selected, sys.modules[__name__])
             if selected else unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sources_end = source_binding_snapshot()
    stable = SOURCE_START == sources_end
    receipt = {'schema': 'codex-performance-contract-run/v1',
               'created_at_utc': datetime.now(timezone.utc).isoformat(),
               'status': 'PASS_FOR_IMPLEMENTED_BOUNDED_TESTS' if result.wasSuccessful() and stable else 'FAIL_OR_IMPLEMENTATION_PENDING',
               'tests': result.testsRun, 'selected_tests': selected or None,
               'failures': [{'test': str(t), 'traceback': e} for t, e in result.failures],
               'errors': [{'test': str(t), 'traceback': e} for t, e in result.errors],
               'skipped': [{'test': str(t), 'reason': e} for t, e in result.skipped],
               'source_start': SOURCE_START, 'source_end': sources_end, 'source_stable_during_run': stable,
               'timings': TIMINGS, 'blind_serial': os.environ.get('CHIP_BLIND_SERIAL'),
               'noncoverage': ['No live ARC pipeline, production edits, full native suite or complete workflow performance verdict.',
                               'Dynamic deep read-closure covers base reconcile and coverage-triggered repair, not every beta/shared-map/fallback branch.',
                               'Native libraries are trusted by runtime version; HMAC does not resist control of the host, process or private key.',
                               'These small synthetic timings cannot establish representative full-corpus acceleration.']}
    path = REVIEW/('run_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'receipt': str(path), 'sha256': file_sha(path), 'status': receipt['status'],
                      'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors)}, ensure_ascii=False))
    return 0 if result.wasSuccessful() and stable else 1


if __name__ == '__main__':
    raise SystemExit(main())
