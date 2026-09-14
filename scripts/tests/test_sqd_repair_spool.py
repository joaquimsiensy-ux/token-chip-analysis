#!/usr/bin/env python3
"""Disk spool equivalence, publication failure and bounded-memory contracts."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/solana'))
from sqd_repair_core import canonical_json, compute_gid
from sqd_repair_spool import RepairSpool, publish_jsonl_exclusive


def mapping(slot):
    return {'slot': slot, 'map': [[0, 1, 'signature']], 'blockhash': 'block',
            'sqd_count': 1, 'ref_nonvote_count': 2}


def layer(slot, signature='same', amount=10**25):
    return {'slot': slot, 'signature': signature, 'reference_position': 1,
            'nonvote_ordinal': 1, 'nonce': True, 'class': 'nonce',
            'edges': [[10, slot, 1, -1, 'A', 'B', amount]], 'evidence': {}}


class SpoolTests(unittest.TestCase):
    def test_empty_and_canonical_gid_exclusions(self):
        with tempfile.TemporaryDirectory() as directory, RepairSpool(directory) as spool:
            material = {'kind': 'wrong', 'gid': 'ignored', 'generated_at': 'ignored',
                        'rpc_ledger': [1.2], 'bundle_sha256': 'ignored',
                        'reference': {'source': 'live'}, 'census': [], 'supersedes': None}
            expected = dict(material, transactions=[], slot_index_map=[])
            self.assertEqual(spool.compute_gid(material), compute_gid(expected))
            self.assertEqual(list(spool.slot_maps), [])
            self.assertEqual(spool.slot_maps.get(1), None)
            self.assertEqual(spool.edge_count, 0)
            with self.assertRaises(ValueError):
                spool.compute_gid({'extra': float('nan')})

    def test_sort_ties_duplicates_large_amount_and_mapping(self):
        with tempfile.TemporaryDirectory() as directory, RepairSpool(directory) as spool:
            maps = [mapping(20), mapping(10)]
            layers = [layer(20), layer(20), layer(10, 'a')]
            layers[1]['edges'][0][0] = 999
            spool.add(maps[0], layers[:2]); spool.add(maps[1], layers[2:])
            expected = sorted(layers, key=lambda row: row['signature'])
            self.assertEqual(list(spool.iter_layer()), expected)
            self.assertEqual(list(spool.iter_maps()), sorted(maps, key=lambda row: row['slot']))
            self.assertEqual(list(spool.iter_repair_edges()),
                             [tuple(edge) for row in expected for edge in row['edges']])
            self.assertEqual(list(spool.slot_maps), [10, 20])
            self.assertTrue(20 in spool.slot_maps)
            self.assertEqual(spool.slot_maps.get(20), maps[0]['map'])
            self.assertEqual((spool.map_count, spool.transaction_count, spool.edge_count), (2, 3, 3))
            material = {'plan_digest': 'p', 'census': [], 'reference': {'source': 'live'}}
            self.assertEqual(spool.compute_gid(material), compute_gid(dict(
                material, transactions=expected, slot_index_map=sorted(maps, key=lambda r: r['slot']))))
            target = Path(directory) / 'layer.jsonl'
            spool.publish_layer(target, {'schema': 'header'})
            self.assertEqual(target.read_bytes(), b''.join(
                canonical_json(row) + b'\n' for row in [{'schema': 'header'}, *expected]))
            spool.publish_layer(target, {'schema': 'header'})

    def test_invalid_numbers_and_duplicate_slot_are_atomic(self):
        for mutate in [lambda m, rows: rows[0]['edges'][0].__setitem__(3, -1.0),
                       lambda m, rows: m.__setitem__('slot', True),
                       lambda m, rows: m['map'][0].__setitem__(0, 0.1),
                       lambda m, rows: rows[0].__setitem__('slot', 12),
                       lambda m, rows: rows[0]['edges'][0].__setitem__(6, '100')]:
            with tempfile.TemporaryDirectory() as directory, RepairSpool(directory) as spool:
                m, rows = mapping(10), [layer(10)]; mutate(m, rows)
                with self.assertRaises(ValueError): spool.add(m, rows)
                self.assertEqual((spool.map_count, spool.transaction_count), (0, 0))
                spool.add(mapping(10), [layer(10)])
                with self.assertRaises(ValueError): spool.add(mapping(10), [])
                self.assertEqual(spool.transaction_count, 1)

    def test_failed_stream_rolls_back_and_numeric_context_is_not_lost(self):
        with tempfile.TemporaryDirectory() as directory, RepairSpool(directory) as spool:
            def broken():
                yield layer(10)
                raise RuntimeError('input failed after valid row')
            with self.assertRaises(RuntimeError): spool.add(mapping(10), broken())
            self.assertEqual(list(spool.iter_layer()), [])
            self.assertEqual(list(spool.slot_maps), [])
            spool.add(mapping(10**30), [layer(10**30, '\U0001f680')])
            spool.add(mapping(1), [layer(1, '\ue000')])
            self.assertEqual(list(spool.slot_maps), [1, 10**30])
            self.assertEqual([r['signature'] for r in spool.iter_layer()], ['\ue000', '\U0001f680'])
            with self.assertRaises(ValueError): spool.compute_gid({'slot': '1'})
            with self.assertRaises(ValueError): spool.compute_gid({'transactions': []})
            pending = Path(directory) / 'pending'; pending.mkdir()
            spool.publish_maps(pending / 'maps.jsonl', {'schema': 'header'})
            self.assertEqual([p.name for p in pending.iterdir()], ['maps.jsonl'])

    def test_publication_conflict_symlink_and_interruption(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'result.jsonl'
            path.write_bytes(b'original\n')
            with self.assertRaises(ValueError): publish_jsonl_exclusive(path, [{'a': 1}])
            self.assertEqual(path.read_bytes(), b'original\n')
            link = Path(directory) / 'link'; link.symlink_to(path)
            with self.assertRaises(ValueError): publish_jsonl_exclusive(link, [{'a': 1}])
            fresh = Path(directory) / 'fresh'
            def broken():
                yield {'a': 1}
                raise RuntimeError('interrupted')
            with self.assertRaises(RuntimeError): publish_jsonl_exclusive(fresh, broken())
            self.assertFalse(fresh.exists())

    def test_million_transactions_memory_bound(self):
        program = '''
import resource, tempfile
from sqd_repair_spool import RepairSpool
before=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
with tempfile.TemporaryDirectory() as directory, RepairSpool(directory) as spool:
    for slot in range(1000):
        rows=({'slot':slot,'signature':str(999999-slot*1000-j),'edges':
               [[1,slot,0,-1,'A','B',10**25+j]]} for j in range(1000))
        spool.add({'slot':slot,'map':[[j,j,'s'+str(j)] for j in range(1000)]}, rows)
    assert spool.transaction_count==1000000
    assert sum(1 for _ in spool.iter_layer())==1000000
    assert sum(len(rows) for rows in spool.slot_maps.values())==1000000
    assert len(spool.compute_gid({'census':[]}))==16
peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
scale=1 if __import__('sys').platform=='darwin' else 1024
assert (peak-before)*scale<128*1024**2, (before,peak)
print('million_rows_peak_growth_bytes', (peak-before)*scale)
'''
        environment = dict(os.environ, PYTHONPATH=str(ROOT / 'scripts/solana'))
        result = subprocess.run([sys.executable, '-c', program], env=environment,
                                capture_output=True, text=True, timeout=240)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        print(result.stdout.strip())


if __name__ == '__main__':
    unittest.main()
