#!/usr/bin/env python3
"""Complete-leaf cache tests. CHIP_PERF_TEST_ROOT selects a retained fixture root.

Fixtures are retained for review; this runner does not delete directories.
"""
from __future__ import annotations
import concurrent.futures
import gzip
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), *(str(ROOT / 'scripts' / d) for d in ('lib', 'tests', 'solana', 'report'))]
import deep_validation_cache as cache
from content_cache import CacheStore
from deep_validation_cache import TrackingPath as TP


@cache.cached_deep_validation('test_recursive_leaf')
def check_leaf(receipt, *, case_root):
    root = TP(case_root).resolve()
    outer = json.loads(TP(receipt).read_text())
    manifest = json.loads((root / outer['manifest']).read_text())
    data = (root / manifest['leaf']).read_bytes()
    return {'ok': hashlib.sha256(data).hexdigest() == manifest['sha256'],
            'reasons': [], 'leaf': root / manifest['leaf'], 'bytes': len(data)}


@cache.cached_deep_validation('test_outer')
def check_outer(receipt, *, case_root):
    return check_leaf(receipt, case_root=case_root)


@cache.cached_deep_validation('test_negative_observation')
def check_optional(receipt, *, case_root):
    selected = TP(case_root) / 'optional'
    if not selected.is_file(): selected = TP(receipt)
    return {'ok': True, 'value': selected.read_text(), 'resolved': selected.resolve()}


@cache.cached_deep_validation('test_partial')
def check_partial(receipt, *, case_root):
    with TP(receipt).open('rb', buffering=0) as f:
        return {'ok': True, 'first': f.read(1).hex()}


@cache.cached_deep_validation('test_live')
def check_live(receipt, *, case_root, live_canary=0, live_canary_fetch=None):
    value = TP(receipt).read_text()
    if live_canary: live_canary_fetch(1)
    return {'ok': True, 'value': value}


class DeepCacheTests(unittest.TestCase):
    def setUp(self):
        parent = Path(os.environ.get('CHIP_PERF_TEST_ROOT') or
                      Path(tempfile.gettempdir()) / 'token-chip-performance')
        parent.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix='case-', dir=parent))
        self.old_env = {k: os.environ.get(k) for k in ('CHIP_PERF_CACHE_ROOT', 'CHIP_PERF_METRICS', 'CHIP_FORCE_DEEP_VALIDATION', 'CHIP_DEEP_CACHE', 'CHIP_DEEP_RAW_CACHE')}
        os.environ['CHIP_PERF_CACHE_ROOT'] = str(self.root / 'cache')
        os.environ['CHIP_PERF_METRICS'] = str(self.root / 'metrics.jsonl')
        os.environ.pop('CHIP_FORCE_DEEP_VALIDATION', None)
        os.environ.pop('CHIP_DEEP_CACHE', None)
        os.environ.pop('CHIP_DEEP_RAW_CACHE', None)
        self.old_tempdir = tempfile.tempdir
        scratch = self.root / 'scratch'; scratch.mkdir()
        tempfile.tempdir = str(scratch)
        self.receipt = self.root / 'receipt.json'
        self.receipt.write_text(json.dumps({'manifest': 'manifest.json'}))
        self.leaf = self.root / 'leaf.raw'; self.leaf.write_bytes(b'original')
        (self.root / 'manifest.json').write_text(json.dumps({'leaf': 'leaf.raw', 'sha256': hashlib.sha256(b'original').hexdigest()}))

    def tearDown(self):
        tempfile.tempdir = self.old_tempdir
        for k, v in self.old_env.items():
            if v is None: os.environ.pop(k, None)
            else: os.environ[k] = v

    def events(self):
        p = self.root / 'metrics.jsonl'
        return [json.loads(s) for s in p.read_text().splitlines()] if p.exists() else []

    def receipts(self):
        return list((self.root / 'cache' / 'solana-deep-validation').glob('*.json'))

    def test_01_three_level_dependency_hit_preserves_result_types(self):
        before = cache.cache_counters()
        a = check_leaf(self.receipt, case_root=self.root)
        b = check_leaf(self.receipt, case_root=self.root)
        self.assertEqual(a, b); self.assertIsInstance(b['leaf'], Path)
        self.assertEqual(cache.cache_counters()['deep_runs'] - before['deep_runs'], 1)
        self.assertEqual(cache.cache_counters()['reuses'] - before['reuses'], 1)
        payload = json.loads(self.receipts()[0].read_text())['body']['payload']
        names = {Path(r['path']).name for r in payload['read_proof']['files']}
        self.assertEqual(names, {'receipt.json', 'manifest.json', 'leaf.raw'})

    def test_02_grandchild_mutation_same_size_and_mtime_rejects(self):
        self.assertTrue(check_leaf(self.receipt, case_root=self.root)['ok'])
        stamp = self.leaf.stat()
        self.leaf.write_bytes(b'corrupt!')
        os.utime(self.leaf, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        self.assertFalse(check_leaf(self.receipt, case_root=self.root)['ok'])
        self.assertTrue(any(e['event'] == 'deep_validate_reject' and 'leaf.raw' in e['reason'] for e in self.events()))

    def test_03_new_negative_dependency_forces_replay(self):
        a = check_optional(self.receipt, case_root=self.root)
        (self.root / 'optional').write_text('new preferred input')
        b = check_optional(self.receipt, case_root=self.root)
        self.assertNotEqual(a['value'], b['value'])
        self.assertEqual(b['value'], 'new preferred input')

    def test_04_nested_hit_dependencies_propagate_and_force_is_recursive(self):
        check_leaf(self.receipt, case_root=self.root)
        check_outer(self.receipt, case_root=self.root)
        before = cache.cache_counters()['deep_runs']
        with cache.force_deep_validation('test_independent_final'):
            self.assertTrue(check_outer(self.receipt, case_root=self.root)['ok'])
        self.assertEqual(cache.cache_counters()['deep_runs'] - before, 2)
        self.leaf.write_bytes(b'corrupt!')
        self.assertFalse(check_outer(self.receipt, case_root=self.root)['ok'])

    def test_05_replacing_payload_and_digest_cannot_resign(self):
        check_leaf(self.receipt, case_root=self.root)
        p = self.receipts()[0]; entry = json.loads(p.read_text())
        payload = entry['body']['payload']; payload['result'] = cache._pack({'ok': True, 'forged': True})
        payload['result_sha256'] = hashlib.sha256(cache.canonical_bytes(payload['result'])).hexdigest()
        p.write_text(json.dumps(entry))
        result = check_leaf(self.receipt, case_root=self.root)
        self.assertNotIn('forged', result)
        self.assertTrue(any('authentication mismatch' in e.get('reason', '') for e in self.events()))

    def test_06_missing_trust_key_does_not_trust_old_proof(self):
        check_leaf(self.receipt, case_root=self.root)
        key = self.root / 'cache/.local-trust-key'; key.rename(key.with_name('held-old-trust-key'))
        before = cache.cache_counters()['deep_runs']
        self.assertTrue(check_leaf(self.receipt, case_root=self.root)['ok'])
        self.assertEqual(cache.cache_counters()['deep_runs'] - before, 1)
        self.assertFalse(key.exists())

    def test_07_partial_read_is_never_issued(self):
        before = cache.cache_counters()['deep_runs']
        check_partial(self.receipt, case_root=self.root)
        check_partial(self.receipt, case_root=self.root)
        self.assertEqual(cache.cache_counters()['deep_runs'] - before, 2)
        self.assertEqual(self.receipts(), [])

    def test_08_live_canary_runs_each_time(self):
        seen = []
        for _ in range(2): check_live(self.receipt, case_root=self.root, live_canary=1, live_canary_fetch=seen.append)
        self.assertEqual(seen, [1, 1]); self.assertEqual(self.receipts(), [])

    def test_09_cross_process_authentication_and_content_recheck(self):
        check_leaf(self.receipt, case_root=self.root)
        code = ('import sys,json; from pathlib import Path; '
                'sys.path.insert(0,sys.argv[1]); import test_deep_validation_cache as t; '
                'print(json.dumps(t.check_leaf(Path(sys.argv[2]),case_root=Path(sys.argv[3])),default=str)); '
                'print(json.dumps(t.cache.cache_counters()))')
        result = subprocess.run([sys.executable, '-c', code, str(ROOT / 'scripts/tests'), str(self.receipt), str(self.root)],
                                capture_output=True, text=True, check=True)
        counts = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(counts['deep_runs'], 0); self.assertEqual(counts['reuses'], 1)

    def test_10_algorithm_change_requires_new_deep(self):
        algorithm = self.root / 'algorithm.py'; algorithm.write_text('version = 1\n')
        with mock.patch.object(cache, '_algorithm_files', return_value=(algorithm,)):
            @cache.cached_deep_validation('test_changed_algorithm')
            def validate(path, *, case_root):
                return {'ok': True, 'data': TP(path).read_text()}
        validate(self.receipt, case_root=self.root)
        algorithm.write_text('version = 2\n')
        before = cache.cache_counters()['deep_runs']
        validate(self.receipt, case_root=self.root)
        self.assertEqual(cache.cache_counters()['deep_runs'] - before, 1)
        self.assertTrue(any(e.get('reason') == 'algorithm_changed_since_import' for e in self.events()))

    def test_11_contextvars_keep_parallel_read_sets_separate(self):
        barrier = threading.Barrier(2)
        CacheStore(self.root, 'seed').save({'seed': True}, {})
        @cache.cached_deep_validation('test_threads')
        def validate(path, *, case_root):
            with TP(path).open('rb') as f:
                barrier.wait(timeout=10)
                value = f.read()
            return {'ok': True, 'value': value.hex()}
        a = self.root / 'a'; b = self.root / 'b'; a.write_bytes(b'A'); b.write_bytes(b'B')
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda p: validate(p, case_root=self.root), (a, b)))
        self.assertEqual([x['value'] for x in results], ['41', '42'])
        manifests = [json.loads(p.read_text())['body']['payload']['read_proof']['files'] for p in self.receipts()]
        self.assertEqual(sorted([Path(rows[0]['path']).name for rows in manifests]), ['a', 'b'])
        self.assertTrue(all(len(rows) == 1 for rows in manifests))

    def test_12_real_reconcile_same_result_hit_then_owners_damage_rejected(self):
        from test_reconcile_v4_receipt import prepare_complete_case, make_reconcile
        import solana_exact_validate as exact
        case = self.root / 'real-base'; case.mkdir()
        rows, edge, meta = prepare_complete_case(case)
        before_cwd = Path.cwd()
        try:
            os.chdir(case)
            receipt, *_ = make_reconcile(case, rows, edge, meta, snapshot_slot=1, as_of_slot=1)
        finally:
            os.chdir(before_cwd)
        a = exact.validate_reconcile_receipt_deep(receipt, case_root=case)
        self.assertTrue(a['ok'], a)
        before = cache.cache_counters()
        b = exact.validate_reconcile_receipt_deep(receipt, case_root=case)
        self.assertEqual(a, b)
        self.assertEqual(cache.cache_counters()['deep_runs'], before['deep_runs'])
        self.assertEqual(cache.cache_counters()['reuses'], before['reuses'] + 1)
        owners = case / 'data/holders_owners.json'; owners.write_text('{}')
        c = exact.validate_reconcile_receipt_deep(receipt, case_root=case)
        self.assertFalse(c['ok'])

    def test_13_real_repair_full_rpc_leaf_dependency_rejects_damage(self):
        from test_batch7_validator_coverage_gaps import _build_formal_generation
        import solana_exact_validate as exact
        case, parent, generation = _build_formal_generation(self.root / 'real-repair')
        bundle = json.loads((generation / 'bundle.json').read_text())
        current_base = {'edge_sha256': hashlib.sha256((case / bundle['base']['edge_file']).read_bytes()).hexdigest()}
        args = (generation / 'bundle.json',)
        a = exact.validate_repair_bundle_deep(*args, case_root=case, current_base=current_base)
        self.assertTrue(a['ok'], a)
        parsed = [r for r in self.events() if r['event'] == 'deep_edge_parse_start']
        self.assertEqual(len(parsed), 2)  # Exactly one base and one merged parse.
        self.assertEqual(len({r['path'] for r in parsed}), 2)
        raw_receipts = list((self.root / 'cache/solana-deep-raw-rows').glob('*.json'))
        self.assertEqual(len(raw_receipts), 2)
        before = cache.cache_counters()['deep_runs']
        b = exact.validate_repair_bundle_deep(*args, case_root=case, current_base=current_base)
        self.assertEqual(a, b); self.assertEqual(cache.cache_counters()['deep_runs'], before)
        from deep_edge_rows_cache import force_raw_edge_parsing
        before_parses = cache.cache_counters()['edge_parse_runs']
        with force_raw_edge_parsing('independent_native_decoder_fixture'):
            independent = exact.validate_repair_bundle_deep(
                *args, case_root=case, current_base=current_base)
        self.assertEqual(independent, a)
        self.assertEqual(cache.cache_counters()['edge_parse_runs'] - before_parses, 3)
        proof_leaves = {r['path'] for p in self.receipts()
                        for r in json.loads(p.read_text())['body']['payload']['read_proof']['files']}
        evidence = json.loads((generation / 'evidence_manifest.json').read_text())
        for item in evidence: self.assertIn(str(generation / item['path']), proof_leaves)
        leaf = next(generation.glob('evidence/*.ref.json')); original_bytes = leaf.read_bytes()
        leaf.write_bytes(original_bytes.replace(b'blockhash', b'blockHash', 1))
        c = exact.validate_repair_bundle_deep(*args, case_root=case, current_base=current_base)
        self.assertFalse(c['ok'])

    def test_14_content_changed_after_read_never_issues_proof(self):
        @cache.cached_deep_validation('test_concurrent_change')
        def validate(path, *, case_root):
            data = TP(path).read_bytes()
            Path(path).write_bytes(data + b'!')  # Controlled concurrent-writer surrogate.
            return {'ok': True, 'value': data.hex()}
        validate(self.leaf, case_root=self.root)
        self.assertEqual(self.receipts(), [])
        self.assertTrue(any('proof_not_issued' in e.get('reason', '') for e in self.events()))

    def test_15_streaming_gzip_proof_hashes_compressed_original_bytes(self):
        @cache.cached_deep_validation('test_gzip')
        def validate(path, *, case_root):
            with cache.tracked_gzip_text(path) as f:
                value = f.read()
            return {'ok': True, 'value': value}
        path = self.root / 'source.gz'; path.write_bytes(gzip.compress(b'original\n', mtime=0))
        a = validate(path, case_root=self.root)
        b = validate(path, case_root=self.root); self.assertEqual(a, b)
        proof = json.loads(self.receipts()[0].read_text())['body']['payload']['read_proof']['files']
        self.assertEqual(proof[0]['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
        path.write_bytes(gzip.compress(b'changed!\n', mtime=0))
        self.assertNotEqual(validate(path, case_root=self.root)['value'], a['value'])

    def test_16_metric_destination_failure_does_not_skip_deep(self):
        os.environ['CHIP_PERF_METRICS'] = str(self.root / 'missing-parent' / 'metrics.jsonl')
        self.assertTrue(check_leaf(self.receipt, case_root=self.root)['ok'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
