#!/usr/bin/env python3
"""Raw materialization tests; CHIP_PERF_TEST_ROOT selects retained fixtures."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), *(str(ROOT / 'scripts' / d) for d in ('lib', 'tests', 'solana', 'report'))]
import deep_validation_cache as deep
import deep_edge_rows_cache as raw
import solana_exact_validate as exact


@deep.cached_deep_validation('test_original_rows_once')
def check_once(path, *, case_root):
    reasons = []
    rows = list(exact._iter_edge_rows(path, reasons, 'test edges'))
    return {'ok': not reasons, 'reasons': reasons, 'rows': rows}


@deep.cached_deep_validation('test_original_rows_twice')
def check_twice(path, *, case_root):
    reasons = []
    first = list(exact._iter_edge_rows(path, reasons, 'first pass'))
    second = list(exact._iter_edge_rows(path, reasons, 'second pass'))
    return {'ok': not reasons and first == second, 'reasons': reasons, 'rows': first}


def native_rows(path):
    """Literal pre-cache parser contract, independent of the new row validator."""
    result, reasons = [], []
    try:
        with gzip.open(path, 'rt', encoding='utf-8') as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                if not isinstance(row, list) or len(row) != 7:
                    raise ValueError('edge must contain seven fields')
                ts, slot, txi, instr, source, target, amount = row
                if any(not (isinstance(x, int) and not isinstance(x, bool))
                       for x in (ts, slot, txi, amount)) or instr != -1 or amount <= 0 \
                        or not isinstance(source, str) or not isinstance(target, str):
                    raise ValueError('edge field contract invalid')
                result.append(tuple(row))
    except (OSError, EOFError, ValueError, json.JSONDecodeError) as exc:
        reasons.append(f'test edges invalid: {exc}')
    return result, reasons


class RawRowsTests(unittest.TestCase):
    def setUp(self):
        parent = Path(os.environ.get('CHIP_PERF_TEST_ROOT') or
                      Path(tempfile.gettempdir()) / 'token-chip-performance')
        parent.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix='raw-', dir=parent))
        keys = ('CHIP_PERF_CACHE_ROOT', 'CHIP_PERF_METRICS', 'CHIP_FORCE_DEEP_VALIDATION',
                'CHIP_DEEP_CACHE', 'CHIP_DEEP_RAW_CACHE')
        self.old_env = {k: os.environ.get(k) for k in keys}
        os.environ['CHIP_PERF_CACHE_ROOT'] = str(self.root / 'cache')
        os.environ['CHIP_PERF_METRICS'] = str(self.root / 'metrics.jsonl')
        for key in keys[2:]:
            os.environ.pop(key, None)
        self.old_tempdir = tempfile.tempdir
        scratch = self.root / 'scratch'; scratch.mkdir()
        tempfile.tempdir = str(scratch)
        self.path = self.root / 'source.jsonl.gz'
        self.rows = [[1, 2, 3, -1, 'a', 'b', 5], [4, 2, 4, -1, 'b', 'a', 3]]
        self.write(self.rows)

    def tearDown(self):
        tempfile.tempdir = self.old_tempdir
        for k, v in self.old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def write(self, rows, path=None):
        data = ''.join(json.dumps(row, ensure_ascii=True) + '\n' for row in rows).encode()
        (path or self.path).write_bytes(gzip.compress(data, mtime=0))

    def events(self, event=None):
        path = self.root / 'metrics.jsonl'
        rows = [json.loads(s) for s in path.read_text().splitlines()] if path.exists() else []
        return [r for r in rows if event is None or r['event'] == event]

    def receipts(self):
        return sorted((self.root / 'cache/solana-deep-raw-rows').glob('*.json'))

    def payload(self):
        return json.loads(self.receipts()[0].read_text())['body']['payload']

    def test_01_same_deep_two_passes_parse_once_and_full_proof_reuses(self):
        a = check_twice(self.path, case_root=self.root)
        self.assertTrue(a['ok']); self.assertEqual(len(self.events('deep_edge_parse_start')), 1)
        self.assertEqual(len(self.events('deep_edge_reuse')), 1)
        self.assertEqual(check_twice(self.path, case_root=self.root), a)
        self.assertEqual(len(self.events('deep_validate_reuse')), 1)
        proofs = list((self.root / 'cache/solana-deep-validation').glob('*.json'))
        leaves = json.loads(proofs[0].read_text())['body']['payload']['read_proof']['files']
        self.assertTrue(any(r['path'].endswith('.arrow') for r in leaves))
        self.assertTrue(any('solana-deep-raw-rows' in r['path'] and r['path'].endswith('.json') for r in leaves))
        self.assertFalse(any('/.pending-' in r['path'] for r in leaves))

    def test_02_wide_native_contract_and_type_preservation(self):
        rows = [[-1, -2, -(2 ** 200), -1.0, '', '', 2 ** 300],
                [0, 0, 0, -1, '\ud800', '漢字\udfff', 1]]
        self.write(rows)
        expected, errors = native_rows(self.path); self.assertFalse(errors)
        a = check_once(self.path, case_root=self.root)
        with deep.force_deep_validation():
            b = check_once(self.path, case_root=self.root)
        self.assertEqual(a['rows'], expected); self.assertEqual(b['rows'], expected)
        self.assertIs(type(b['rows'][0][3]), float); self.assertIs(type(b['rows'][1][3]), int)
        self.assertEqual(len(self.events('deep_edge_parse_start')), 1)
        self.assertEqual(len(self.receipts()), 1)

    def test_03_invalid_contract_prefix_and_error_parity(self):
        invalid = [None, {}, 'row', [], [1, 2], self.rows[0] + [1]]
        for index in (0, 1, 2, 6):
            for value in (True, None, 1.0, '1'):
                row = self.rows[0].copy(); row[index] = value; invalid.append(row)
        for value in (0, -3):
            row = self.rows[0].copy(); row[6] = value; invalid.append(row)
        for value in (0, True, None, '-1', float('nan')):
            row = self.rows[0].copy(); row[3] = value; invalid.append(row)
        for index in (4, 5):
            for value in (None, 1, []):
                row = self.rows[0].copy(); row[index] = value; invalid.append(row)
        for i, row in enumerate(invalid):
            path = self.root / f'invalid-{i}.gz'
            self.write([self.rows[0], row, self.rows[1]], path)
            expected, errors = native_rows(path)
            for _ in range(2):
                value = check_once(path, case_root=self.root)
                self.assertEqual(value['rows'], expected)
                self.assertEqual(value['reasons'], errors)
                self.assertFalse(value['ok'])
        self.assertEqual(self.receipts(), [])
        self.assertEqual(len(self.events('deep_edge_parse_start')), 2 * len(invalid))

    def test_04_malformed_json_utf8_and_gzip_eof_keep_original_behavior(self):
        prefix = (json.dumps(self.rows[0]) + '\n').encode()
        raw_values = [prefix + b'{broken}\n', prefix + b'\xff\n']
        files = []
        for i, value in enumerate(raw_values):
            p = self.root / f'malformed-{i}.gz'; p.write_bytes(gzip.compress(value, mtime=0)); files.append(p)
        p = self.root / 'truncated.gz'; p.write_bytes(gzip.compress(prefix, mtime=0)[:-5]); files.append(p)
        for p in files:
            expected, errors = native_rows(p)
            a = check_once(p, case_root=self.root)
            self.assertEqual(a['rows'], expected); self.assertEqual(a['reasons'], errors)
        self.assertEqual(self.receipts(), [])

    def test_05_changed_source_with_restored_mtime_reparses(self):
        a = check_once(self.path, case_root=self.root)
        stamp = self.path.stat()
        rows = [r.copy() for r in self.rows]; rows[0][6] = 6
        self.write(rows); os.utime(self.path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        b = check_once(self.path, case_root=self.root)
        self.assertNotEqual(a['rows'], b['rows'])
        self.assertEqual(len(self.events('deep_edge_parse_start')), 2)

    def test_06_corrupt_columns_rejected_then_actual_raw_reparse(self):
        a = check_once(self.path, case_root=self.root)
        p = Path(self.payload()['artifact_file']['path'])
        data = bytearray(p.read_bytes()); data[len(data) // 2] ^= 1; p.write_bytes(data)
        with deep.force_deep_validation():
            b = check_once(self.path, case_root=self.root)
        self.assertEqual(a, b)
        self.assertEqual(len(self.events('deep_edge_parse_start')), 2)
        self.assertTrue(any('artifact content mismatch' in r['reason']
                            for r in self.events('deep_edge_cache_reject')))

    def test_07_forged_columns_plus_manifest_cannot_self_resign(self):
        a = check_once(self.path, case_root=self.root)
        receipt = self.receipts()[0]; entry = json.loads(receipt.read_text())
        payload = entry['body']['payload']
        p = Path(payload['artifact_file']['path']); p.write_bytes(b'forged artifact')
        payload['artifact_file']['sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
        payload['artifact_file']['bytes'] = p.stat().st_size
        receipt.write_text(json.dumps(entry))
        with deep.force_deep_validation():
            self.assertEqual(check_once(self.path, case_root=self.root), a)
        self.assertEqual(len(self.events('deep_edge_parse_start')), 2)
        self.assertTrue(any('authentication mismatch' in r['reason']
                            for r in self.events('deep_edge_cache_reject')))

    def test_08_force_deep_shares_raw_but_force_raw_recomputes_both(self):
        check_once(self.path, case_root=self.root)
        with deep.force_deep_validation():
            check_once(self.path, case_root=self.root)
        self.assertEqual(len(self.events('deep_edge_parse_start')), 1)
        with raw.force_raw_edge_parsing('test_raw_independence'):
            check_once(self.path, case_root=self.root)
        self.assertEqual(len(self.events('deep_edge_parse_start')), 2)
        os.environ['CHIP_DEEP_RAW_CACHE'] = '0'
        check_once(self.path, case_root=self.root)
        self.assertEqual(len(self.events('deep_edge_parse_start')), 3)

    def test_09_partial_iterator_never_issues_raw_columns(self):
        token = deep._CASE_ROOT.set(self.root)
        try:
            rows = exact._iter_edge_rows(self.path)
            self.assertEqual(next(rows), tuple(self.rows[0]))
            rows.close()
        finally:
            deep._CASE_ROOT.reset(token)
        self.assertEqual(self.receipts(), [])

    def build_main(self, path, rows):
        import duckdb
        from solana_edge_store import load_materialized
        self.write(rows, path)
        logical = hashlib.sha256(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows).encode()).hexdigest()
        meta_path = path.with_name(path.name + '.meta.json')
        meta = {'edge_rows': len(rows), 'edge_logical_sha256': logical}
        meta_path.write_text(json.dumps(meta))
        binding = {'cache_kind': 'base', 'gid': None,
                   'soltx_edges_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                   'soltx_meta_sha256': hashlib.sha256(meta_path.read_bytes()).hexdigest(),
                   'edge_logical_sha256': logical}
        preflight = {'files': [str(path)], 'cache_meta': meta,
                     'meta_path': str(meta_path), 'edge_source_binding': binding}
        con = duckdb.connect()
        try:
            load_materialized(con, preflight, case_root=self.root, mint='test-mint')
        finally:
            con.close()

    def test_10_main_materialization_exact_path_does_not_replace_base(self):
        self.build_main(self.path, self.rows)
        a = check_once(self.path, case_root=self.root)
        self.assertTrue(a['ok']); self.assertEqual(a['rows'], [tuple(r) for r in self.rows])
        self.assertEqual(len(self.events('deep_edge_parse_start')), 0)
        self.assertEqual(self.events('deep_edge_reuse')[0]['layer'], 'main_raw_columns')
        base = self.root / 'different-base.gz'
        base_rows = [[-9, -8, -7, -1.0, '', 'base', 2 ** 160]]
        self.write(base_rows, base)
        value = check_twice(base, case_root=self.root)
        self.assertEqual(value['rows'], [tuple(r) for r in base_rows])
        self.assertEqual(len(self.events('deep_edge_parse_start')), 1)
        self.assertEqual(self.events('deep_edge_parse_start')[0]['path'], str(base))

    def test_11_main_rows_still_apply_native_instr_contract(self):
        rows = [self.rows[0], [5, 6, 7, 0, 'instruction', 'target', 9], self.rows[1]]
        self.build_main(self.path, rows)
        expected, errors = native_rows(self.path)
        a = check_once(self.path, case_root=self.root)
        self.assertEqual(a['rows'], expected); self.assertEqual(a['reasons'], errors)
        self.assertFalse(a['ok']); self.assertEqual(len(self.events('deep_edge_parse_start')), 0)

    def test_12_cross_process_raw_materialization_reuse(self):
        check_once(self.path, case_root=self.root)
        code = ('import sys,json;from pathlib import Path;sys.path.insert(0,sys.argv[1]);'
                'import test_deep_edge_rows_cache as t;'
                'scope=t.deep.force_deep_validation();scope.__enter__();'
                'v=t.check_once(Path(sys.argv[2]),case_root=Path(sys.argv[3]));'
                'scope.__exit__(None,None,None);'
                'print(json.dumps({"ok":v["ok"],"counts":t.deep.cache_counters()}))')
        p = subprocess.run([sys.executable, '-c', code, str(ROOT / 'scripts/tests'),
                            str(self.path), str(self.root)], capture_output=True, text=True, check=True)
        result = json.loads(p.stdout.splitlines()[-1])
        self.assertTrue(result['ok']); self.assertEqual(result['counts']['edge_parse_runs'], 0)
        self.assertEqual(result['counts']['edge_reuses'], 1)
        self.assertEqual(result['counts']['deep_runs'], 1)

    def test_13_empty_original_stream_is_valid_and_reusable(self):
        self.write([])
        a = check_twice(self.path, case_root=self.root)
        self.assertTrue(a['ok']); self.assertEqual(a['rows'], [])
        self.assertEqual(len(self.events('deep_edge_parse_start')), 1)
        self.assertEqual(self.payload()['rows'], 0)

    def test_14_cache_setup_failure_keeps_original_decoder_available(self):
        with mock.patch.object(raw, '_verified_main', side_effect=OSError('test unavailable')), \
                mock.patch.object(raw, 'CacheStore', side_effect=OSError('test cache unavailable')):
            a = check_once(self.path, case_root=self.root)
        self.assertTrue(a['ok']); self.assertEqual(a['rows'], [tuple(r) for r in self.rows])
        self.assertEqual(len(self.events('deep_edge_parse_start')), 1)

    def test_15_interleaved_generators_issue_separate_sources_without_context_leak(self):
        other = self.root / 'other.gz'
        self.write(self.rows[:1], other)
        @deep.cached_deep_validation('test_interleaved_raw_generators')
        def consume(path, *, case_root):
            reasons, seen = [], []
            a = exact._iter_edge_rows(path, reasons, 'a')
            b = exact._iter_edge_rows(other, reasons, 'b')
            seen.append(next(a)); seen.append(next(b))
            seen.extend(a)  # The first iterator closes before the second.
            seen.extend(b)
            return {'ok': not reasons, 'rows': seen, 'reasons': reasons}
        before_readers = deep._READERS.get()
        a = consume(self.path, case_root=self.root)
        self.assertTrue(a['ok']); self.assertEqual(len(self.receipts()), 2)
        self.assertEqual(deep._READERS.get(), before_readers)
        self.assertEqual(len(self.events('deep_edge_parse_start')), 2)
        with deep.force_deep_validation():
            self.assertEqual(consume(self.path, case_root=self.root), a)
        self.assertEqual(len(self.events('deep_edge_parse_start')), 2)
        self.assertEqual(deep._READERS.get(), before_readers)

    def test_16_loaded_parser_disk_change_cannot_issue_future_raw_proof(self):
        mini = self.root / 'isolated-runtime'
        files = ['scripts/lib/solana_exact_validate.py', 'scripts/lib/content_cache.py',
                 'scripts/lib/deep_validation_cache.py', 'scripts/lib/deep_edge_rows_cache.py',
                 'scripts/lib/solana_materialization_reader.py', 'scripts/lib/solana_edge_store.py',
                 'scripts/lib/producer_history.py', 'scripts/solana/spl_edge_core.py']
        for name in files:
            target = mini / name; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / name).read_bytes())
        code = (
            'import sys,json;from pathlib import Path;'
            'sys.path.insert(0,sys.argv[1]);import solana_exact_validate as v;'
            'import deep_validation_cache as d;'
            'p=Path(v.__file__);p.write_text(p.read_text()+"\\n# changed after import\\n");'
            'token=d._CASE_ROOT.set(Path(sys.argv[3]));reasons=[];'
            'rows=list(v._iter_edge_rows(Path(sys.argv[2]),reasons,"test edges"));'
            'd._CASE_ROOT.reset(token);'
            'print(json.dumps({"rows":rows,"reasons":reasons,"counts":d.cache_counters()}))')
        p = subprocess.run([sys.executable, '-c', code, str(mini / 'scripts/lib'),
                            str(self.path), str(self.root)], capture_output=True, text=True, check=True)
        result = json.loads(p.stdout.splitlines()[-1])
        self.assertEqual(result['rows'], self.rows); self.assertFalse(result['reasons'])
        self.assertEqual(result['counts']['edge_parse_runs'], 1)
        self.assertEqual(self.receipts(), [])
        self.assertTrue(any('algorithm changed since import' in r['reason']
                            for r in self.events('deep_edge_cache_reject')))

    def test_17_receipt_symlink_is_rejected_before_following_target(self):
        a = check_once(self.path, case_root=self.root)
        manifest = self.receipts()[0]
        manifest.rename(manifest.with_suffix('.saved-original'))
        target = self.root / 'must-not-be-read'; target.write_bytes(b'not a receipt')
        manifest.symlink_to(target)
        original = raw._fingerprint
        def guarded(path):
            self.assertNotEqual(Path(path), manifest)
            self.assertNotEqual(Path(path), target)
            return original(path)
        with deep.force_deep_validation(), mock.patch.object(raw, '_fingerprint', side_effect=guarded):
            b = check_once(self.path, case_root=self.root)
        self.assertEqual(a, b)
        self.assertEqual(len(self.events('deep_edge_parse_start')), 2)
        self.assertTrue(any('non-symlink' in r['reason'] for r in self.events('deep_edge_cache_reject')))


if __name__ == '__main__':
    unittest.main(verbosity=2)
