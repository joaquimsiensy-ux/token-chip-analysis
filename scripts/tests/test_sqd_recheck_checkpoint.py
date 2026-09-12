#!/usr/bin/env python3
"""Offline coverage recheck checkpoint regression tests.

Run directly or through scripts/tests/run_all.py.
The interrupted-commit test executes the real journal commit before a deliberate
BaseException, and replaces transport only for producer responses. No fake PASS
receipts or fabricated journal success state are used.
"""
import copy
import gzip
import importlib.util
import json
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

SKILL = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('review_probe', SKILL / 'scripts/solana/sqd_coverage_probe.py')
P = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(P)
IDENTITY = {'mint': 'review-mint', 'from_slot': 100, 'to_slot': 138,
            'sqd_fingerprint': P.endpoint_fingerprint('fixture://sqd')['sha256'],
            'known_map_sha256': '1' * 64,
            'query_body_sha256': P.sqd_query_template_sha256(),
            'producer_sha256': P.sha256_file(SKILL / 'scripts/solana/sqd_coverage_probe.py')}
SLOTS = list(range(100, 140, 2))
RANGES = [(x, x) for x in SLOTS]
COUNTS = bytes([3] * 39)


class Transport:
    def __init__(self, fail=False, banned=()):
        self.fail = fail
        self.banned = set(banned)
        self.calls = []
        self.lock = threading.Lock()

    def call(self, kind, body):
        assert kind == 'sqd-stream', kind
        interval = (body['fromBlock'], body['toBlock'])
        with self.lock:
            self.calls.append(interval)
        if interval in self.banned:
            raise AssertionError('committed request resent: ' + str(interval))
        if self.fail:
            return P.net.Result(ok=False, error={
                'category': 'transport', 'message': 'independent temporary failure',
                'http_status': 503, 'retryable': False})
        blocks = [{'header': {'number': slot},
                   'instructions': [{'transactionIndex': 0}]}
                  for slot in range(interval[0], interval[1] + 1)]
        return P.net.Result(ok=True, value=blocks)


def run(directory, transport, identity=None, ranges=RANGES, slots=SLOTS, counts=COUNTS):
    journal = P.RecheckJournal(directory, identity or IDENTITY, ranges)
    ledger = []
    result = P._recheck_known_slots(transport, slots, counts, 100, 1,
                                  ledger, ['fixture://sqd'], journal=journal)
    return result, ledger


class CutAfterCommit(BaseException):
    pass


class IndependentJournal(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='arc-journal-review-', dir=str(Path(tempfile.gettempdir()).resolve()))
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_real_commit_interruption_then_zero_resend(self):
        real = P.RecheckJournal.commit
        first = Transport()
        commits = []

        def cut(journal, records):
            answer = real(journal, records)
            commits.append(copy.deepcopy(records))
            raise CutAfterCommit()

        with mock.patch.object(P.RecheckJournal, 'commit', cut):
            with self.assertRaises(CutAfterCommit):
                run(self.root, first)
        self.assertEqual(len(commits), 1)
        committed = {(x['from'], x['to']) for x in commits[0]}
        self.assertTrue(committed)
        self.assertLessEqual(len(first.calls), 4, 'initial scheduling must remain bounded')
        second = Transport(banned=committed)
        (actual, failure, unverified, stats), ledger = run(self.root, second)
        self.assertIsNone(failure)
        self.assertEqual(unverified, [])
        self.assertEqual(actual, {x: 3 for x in SLOTS})
        self.assertFalse(committed.intersection(second.calls))
        self.assertEqual(stats['verified'], len(RANGES))
        self.assertEqual([r['seq'] for r in ledger], list(range(len(ledger))))
        third = Transport(banned=RANGES)
        repeated, _ = run(self.root, third)
        self.assertEqual(third.calls, [])
        self.assertEqual(repeated, (actual, failure, unverified, stats))

    def test_two_failed_rounds_are_not_reset_by_resume(self):
        first = Transport(fail=True)
        initial, _ = run(self.root, first)
        self.assertEqual(len(first.calls), 2 * len(RANGES))
        self.assertEqual(initial[2], RANGES)
        second = Transport(banned=RANGES)
        resumed, _ = run(self.root, second)
        self.assertEqual(second.calls, [])
        self.assertEqual(resumed, initial)

    def test_identity_drift_rejects_before_business_transport(self):
        run(self.root, Transport())
        changed = dict(IDENTITY, known_map_sha256='2' * 64)
        transport = Transport()
        with self.assertRaises(P.RecheckCheckpointError):
            run(self.root, transport, identity=changed)
        self.assertEqual(transport.calls, [])

    def test_committed_batch_byte_damage_rejects(self):
        run(self.root, Transport())
        head = self.root / 'HEAD.json'
        self.assertTrue(head.is_file())
        candidates = [p for p in self.root.glob('batch-*.json') if p.is_file()]
        self.assertTrue(candidates)
        victim = candidates[0]
        victim.write_bytes(victim.read_bytes() + b'\ncorruption')
        transport = Transport()
        with self.assertRaises(P.RecheckCheckpointError):
            run(self.root, transport)
        self.assertEqual(transport.calls, [])

    def test_missing_committed_batch_rejects(self):
        run(self.root, Transport())
        head = self.root / 'HEAD.json'
        victim = next(p for p in self.root.glob('batch-*.json') if p.is_file())
        victim.unlink()
        transport = Transport()
        with self.assertRaises(P.RecheckCheckpointError):
            run(self.root, transport)
        self.assertEqual(transport.calls, [])

    def test_unreferenced_orphan_does_not_create_success(self):
        (self.root / 'orphan-uncommitted.json').write_text('{"invalid":"orphan"}')
        transport = Transport()
        (actual, failure, unverified, stats), _ = run(self.root, transport)
        self.assertEqual(len(transport.calls), len(RANGES))
        self.assertEqual(actual, {x: 3 for x in SLOTS})
        self.assertIsNone(failure)
        self.assertEqual(unverified, [])
        self.assertTrue((self.root / 'orphan-uncommitted.json').is_file())

    def test_stale_writer_cannot_overwrite_committed_head(self):
        left = P.RecheckJournal(self.root, IDENTITY, RANGES)
        right = P.RecheckJournal(self.root, IDENTITY, RANGES)
        left.commit([P._fetch_recheck_record(Transport(), 100, 100, 0, [])])
        head = (self.root / 'HEAD.json').read_bytes()
        with self.assertRaises(P.RecheckCheckpointError):
            right.commit([P._fetch_recheck_record(Transport(), 102, 102, 0, [])])
        self.assertEqual((self.root / 'HEAD.json').read_bytes(), head)
        self.assertIsNotNone(P.RecheckJournal(self.root, IDENTITY, RANGES).lookup(0, 100, 100))

    def test_rebound_hash_does_not_bypass_raw_response_replay(self):
        for mode in ['counts', 'row', 'response', 'duplicate', 'scope']:
            with self.subTest(mode=mode):
                root = self.root / mode
                journal = P.RecheckJournal(root, IDENTITY, RANGES)
                journal.commit([P._fetch_recheck_record(Transport(), 100, 100, 0, [])])
                head = json.loads((root / 'HEAD.json').read_text())
                ref = head['batches'][0]
                batch = json.loads((root / ref['path']).read_text())
                record = batch['records'][0]
                if mode == 'counts': record['counts_hex'] = 'ff'
                elif mode == 'row': record['row']['query_body_sha256'] = '0' * 64
                elif mode == 'response': record['response']['value'][0]['instructions'] = []
                elif mode == 'duplicate': batch['records'].append(copy.deepcopy(record))
                else: record['from'] = 999
                payload = P.canonical_json(batch) + b'\n'
                sha = P.sha256_bytes(payload)
                ref.update(path='batch-' + sha + '.json', sha256=sha, size=len(payload))
                (root / ref['path']).write_bytes(payload)
                (root / 'HEAD.json').write_text(json.dumps(head))
                with mock.patch.object(P, '_scan_result', wraps=P._scan_result) as replay:
                    with self.assertRaises(P.RecheckCheckpointError):
                        P.RecheckJournal(root, IDENTITY, RANGES)
                    if mode in ['counts', 'row', 'response']:
                        self.assertGreater(replay.call_count, 0)

    def _shared_map(self):
        counts_path = self.root / 'map.counts.gz'
        counts_path.write_bytes(gzip.compress(bytes([3]) * 64, mtime=0))
        blocks_path = self.root / 'map.blocks.gz'
        blocks_path.write_bytes(gzip.compress(P.encode_bitmap(range(200, 264), 200, 263), mtime=0))
        metadata = {'dataset_id': 'solana-mainnet', 'start_block': 0, 'real_time': True,
                    'finalized_head': 1000, 'number': 1000, 'hash': 'fixture-anchor-1000'}
        asset = {'schema': 'sqd-solana-shared-coverage-map/v1', 'version': '20260823',
                 'generated_at': datetime.now(timezone.utc).isoformat(), 'ttl_days': 30, 'supersedes': None,
                 'sqd': {'dataset': 'solana-mainnet', 'endpoint_fingerprint': P.endpoint_fingerprint('fixture://sqd')['sha256'],
                         'finalized_head_at_scan': 1000, 'metadata_normalized': metadata,
                         'metadata_sha256': P.sha256_bytes(P.canonical_json(metadata)),
                         'query_body_sha256': P.sqd_query_template_sha256()},
                 'slot_counts': {'path': counts_path.name, 'size': counts_path.stat().st_size,
                                 'sha256': P.sha256_file(counts_path), 'from_slot': 200, 'to_slot': 263,
                                 'encoding': P.COUNT_ENCODING},
                 'blocks_bitmap': {'path': blocks_path.name, 'size': blocks_path.stat().st_size,
                                   'sha256': P.sha256_file(blocks_path), 'from_slot': 200, 'to_slot': 263,
                                   'encoding': P.BITMAP_ENCODING},
                 'candidate_slots': [], 'refuted_slots': [],
                 'canary': {'slots': list(range(200, 264)), 'counts': [3] * 64}}
        path = self.root / 'shared-map.json'; path.write_text(json.dumps(asset))
        return path, metadata

    def test_post_map_resume_preserves_full_prefix_and_rechecks_anchor(self):
        asset_path, metadata = self._shared_map()
        case = self.root / 'case'
        calls = []
        anchor_changed = False

        class FullTransport:
            def call(self, kind, body):
                if kind == 'sqd-head': return P.net.Result(ok=True, value=metadata)
                calls.append((body['fromBlock'], body['toBlock']))
                if body['fromBlock'] == 1000:
                    return P.net.Result(ok=True, value=[{'header': {'number': 1000,
                        'hash': 'different' if anchor_changed else 'fixture-anchor-1000'}}])
                return Transport().call(kind, body)

        argv = ['--mint', 'FixtureMint', '--case-root', str(case), '--from-slot', '200', '--to-slot', '295',
                '--known-map', str(asset_path), '--no-getblocks', '--workers', '1',
                '--checkpoint-every', '1', '--transport-fixture', str(self.root)]
        real_write = P._write_resume
        def cut(*args, **kwargs):
            real_write(*args, **kwargs)
            raise CutAfterCommit()
        with mock.patch.object(P, 'FixtureTransport', lambda path: FullTransport()), \
             mock.patch.object(P, 'SQD_PAGE_SLOTS', 4):
            with mock.patch.object(P, '_write_resume', cut):
                with self.assertRaises(CutAfterCommit): P.main(argv)
            self.assertFalse((case / 'data/sqd_coverage/CURRENT.json').exists())
            committed_full = {item for item in calls if 264 <= item[0] <= 279}
            self.assertEqual(len(committed_full), 4)
            calls.clear()
            class ExpiredDatetime(datetime):
                @classmethod
                def now(cls, tz=None): return datetime.now(tz) + timedelta(days=31)
            with mock.patch.object(P, 'datetime', ExpiredDatetime):
                self.assertNotEqual(P.main(argv + ['--resume']), 0)
            self.assertEqual(calls, [], 'expired map must fail before business rechecks')
            anchor_changed = True
            self.assertNotEqual(P.main(argv + ['--resume']), 0)
            self.assertEqual(calls, [(1000, 1000)])
            self.assertFalse((case / 'data/sqd_coverage/CURRENT.json').exists())
            calls.clear()
            anchor_changed = False
            self.assertEqual(P.main(argv + ['--resume']), 0)
            self.assertIn((1000, 1000), calls)
            self.assertFalse(committed_full.intersection(calls))
            self.assertNotIn((200, 263), calls, 'committed recheck response must also be reused')
        pointer = json.loads((case / 'data/sqd_coverage/CURRENT.json').read_text())
        generation = case / 'data/sqd_coverage' / pointer['probe_id']
        self.assertEqual(gzip.decompress((generation / 'slot_counts.bin.gz').read_bytes()), bytes([3]) * 96)

    def test_known_map_resume_rejects_damaged_or_nonregular_state(self):
        from types import SimpleNamespace
        args = SimpleNamespace(resume=True, known_map='fixture', mint='M', from_slot=100, to_slot=200)
        for mode in ['invalid-json', 'missing-schema', 'dangling-link', 'directory']:
            with self.subTest(mode=mode):
                parent = self.root / mode
                pending = parent / 'pending-example'; pending.mkdir(parents=True)
                path = pending / 'resume_state.json'
                if mode == 'invalid-json': path.write_text('{')
                elif mode == 'missing-schema': path.write_text('{}')
                elif mode == 'dangling-link': path.symlink_to(pending / 'missing')
                else: path.mkdir()
                with self.assertRaises(P.RecheckCheckpointError): P._pending_state(parent, args, 'fingerprint')

    def test_failed_head_commit_leaves_only_uncommitted_orphan(self):
        journal = P.RecheckJournal(self.root, IDENTITY, RANGES)
        with mock.patch.object(P, 'publish_overwrite', side_effect=OSError('injected HEAD failure')):
            with self.assertRaises(P.RecheckCheckpointError):
                journal.commit([P._fetch_recheck_record(Transport(), 100, 100, 0, [])])
        self.assertEqual(journal.index, {})
        self.assertFalse((self.root / 'HEAD.json').exists())
        orphan = next(self.root.glob('batch-*.json'))
        transport = Transport()
        run(self.root, transport)
        self.assertEqual(len(transport.calls), len(RANGES))
        self.assertTrue(orphan.is_file())


if __name__ == '__main__':
    unittest.main(verbosity=2)
