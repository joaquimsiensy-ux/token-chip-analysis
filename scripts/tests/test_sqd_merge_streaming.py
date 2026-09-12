#!/usr/bin/env python3
"""Bounded external merge and registered-v4 resume regression tests."""
import gzip
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/tests'))
import test_sqd_collector_meta_v4 as C
M = C.collector
from producer_history import historical_producer_hashes
import producer_history


class StreamingMerge(unittest.TestCase):
    def test_same_complete_transaction_with_equal_sort_keys_and_reversed_sources(self):
        a=[100,100,0,-1,'A','B',1]
        b=[100+sys.hash_info.modulus,100,0,-1,'A','B',1]
        self.assertEqual(hash(tuple(a)),hash(tuple(b)))
        for cls in [M.MemMerger,M.ExtMerger]:
            with self.subTest(merger=cls.__name__),tempfile.TemporaryDirectory() as d:
                p=Path(d);parts=p/'parts';parts.mkdir();files=[parts/'one.jsonl',parts/'two.jsonl']
                for path,rows in zip(files,[[a,b],[b,a]]):
                    path.write_text(''.join(json.dumps(x)+'\n' for x in rows))
                self.assertEqual(cls(p/'cache.gz',parts,files,False).finalize()['rows'],2)

    def test_revoked_current_hash_is_not_resumable(self):
        current=M.collector_sha256()
        meta={**M.cache_identity(C.MINT,'fixture://sqd',current),'finalized_upper_slot':100}
        revoked={'script':'scripts/solana/fetch_sqd_transfers_v2.py','protocol':M.CACHE_SCHEMA,
                 'sha256':current,'status':'REVOKED','commit':'unit-negative','reason':'unit-negative'}
        with mock.patch.object(producer_history,'PRODUCER_HISTORY',producer_history.PRODUCER_HISTORY+(revoked,)):
            self.assertIsNone(M.normalize_cache_identity(meta,C.MINT,'fixture://sqd',current))

    def test_float_instruction_sentinel_rejected_by_both_mergers(self):
        for cls in [M.MemMerger,M.ExtMerger]:
            for spelling in ['-1.0','-1e0']:
                with self.subTest(merger=cls.__name__,spelling=spelling), tempfile.TemporaryDirectory() as d:
                    p=Path(d); parts=p/'parts';parts.mkdir();part=parts/'rows.jsonl'
                    part.write_text('[100,100,0,'+spelling+',"A","B",1]\n')
                    with self.assertRaises(ValueError):
                        cls(p/'cache.gz',parts,[part],False).finalize()

    def test_many_transactions_under_small_memory_limit(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); parts = p / 'parts'; parts.mkdir()
            part = parts / 'rows.jsonl'
            n = 1_000_000
            with part.open('w') as out:
                for i in range(n-1,-1,-1):
                    out.write(json.dumps([1700000000+i,100+i,0,-1,
                        'A'*43+str(i%10),'B'*43+str(i%10),10**25+i])+'\n')
            cache = p / 'cache.jsonl.gz'
            with mock.patch.object(M,'MERGE_MEM_LIMIT','256MB'), mock.patch.object(M,'MERGE_THREADS',1):
                result = M.ExtMerger(cache,parts,[part],False).finalize()
            self.assertEqual(result['rows'],n)
            with gzip.open(cache,'rt') as inp:
                count = 0
                for count,line in enumerate(inp,1):
                    row=json.loads(line); self.assertEqual(row[1],99+count)
                    self.assertEqual(row[-1],10**25+count-1)
                self.assertEqual(count,n)

    def test_gzip_history_and_200_parts_under_small_memory_limit(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); parts=p/'parts'; parts.mkdir(); cache=p/'cache.jsonl.gz'
            n=1_000_000; extra=200_000
            def row(i):
                return [1700000000+i,100+i,0,-1,'A'*43+str(i%10),
                        'B'*43+str(i%10),10**25+i]
            with gzip.open(cache,'wt',compresslevel=1) as out:
                for i in range(n-1,-1,-1): out.write(json.dumps(row(i))+'\n')
            files=[]
            for part_no in range(200):
                path=parts/f'{part_no}.jsonl'; files.append(path)
                with path.open('w') as out:
                    for i in range(n+part_no*1000,n+(part_no+1)*1000):
                        out.write(json.dumps(row(i))+'\n')
                    if part_no==0: out.write(json.dumps(row(0))+'\n')
            with mock.patch.object(M,'MERGE_MEM_LIMIT','256MB'), mock.patch.object(M,'MERGE_THREADS',4):
                result=M.ExtMerger(cache,parts,files,True).finalize()
            self.assertEqual(result['rows'],n+extra)
            with gzip.open(cache,'rt') as inp:
                for count,line in enumerate(inp,1):
                    actual=json.loads(line)
                    self.assertEqual(actual[1],99+count)
                    self.assertEqual(actual[-1],10**25+count-1)
                self.assertEqual(count,n+extra)
            self.assertTrue(all(path.is_file() for path in files))

    def test_source_materialization_failure_preserves_previous_cache(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); parts=p/'parts'; parts.mkdir(); cache=p/'cache.gz'
            with gzip.open(cache,'wt') as out:
                out.write(json.dumps([100,100,0,-1,'A','B',10])+'\n')
            original=cache.read_bytes()
            with self.assertRaises(M.duckdb.IOException):
                M.ExtMerger(cache,parts,[parts/'missing.jsonl'],True).finalize()
            self.assertEqual(cache.read_bytes(),original)
            self.assertFalse((p/'cache.gz.tmp').exists())

    def test_complete_transaction_conflict_preserves_previous_cache(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); parts=p/'parts';parts.mkdir(); cache=p/'cache.gz'
            base=[1700000000,100,0,-1,'A','B',10**25]
            with gzip.open(cache,'wt') as out: out.write(json.dumps(base)+'\n')
            original=cache.read_bytes(); part=parts/'new.jsonl'
            part.write_text(json.dumps(base)+'\n'+json.dumps([1700000000,100,0,-1,'B','C',2])+'\n')
            with self.assertRaisesRegex(RuntimeError,'conflicting transaction'):
                M.ExtMerger(cache,parts,[part],True).finalize()
            self.assertEqual(cache.read_bytes(),original)
            self.assertTrue(part.is_file())

    def test_registered_old_identity_only(self):
        current=M.collector_sha256()
        old=next(h for h in historical_producer_hashes('scripts/solana/fetch_sqd_transfers_v2.py',M.CACHE_SCHEMA) if h!=current)
        meta={**M.cache_identity(C.MINT,'fixture://sqd',old),'finalized_upper_slot':100}
        result=M.normalize_cache_identity(meta,C.MINT,'fixture://sqd',current)
        self.assertIsNotNone(result)
        self.assertEqual(result['collector_sha256'],old)
        for key,value in [('collector_sha256','f'*64),('mint','wrong'),('endpoint_sha256','e'*64),('edge_semantics','wrong')]:
            self.assertIsNone(M.normalize_cache_identity({**meta,key:value},C.MINT,'fixture://sqd',current))

    def test_completed_parts_resume_without_scan_and_resign_after_merge(self):
        with tempfile.TemporaryDirectory() as d:
            previous=Path.cwd();os.chdir(d)
            try:
                cache,meta_path,parts=M.cache_paths(C.MINT);parts.mkdir(parents=True)
                old=next(h for h in historical_producer_hashes('scripts/solana/fetch_sqd_transfers_v2.py',M.CACHE_SCHEMA) if h!=M.collector_sha256())
                first=[1700000000,100,0,-1,M.ZERO,C.OWNER,10]
                second=[1700000001,101,0,-1,C.OWNER,'C',3]
                with gzip.open(cache,'wt') as out:out.write(json.dumps(first)+'\n')
                (parts/'new.jsonl').write_text(json.dumps(second)+'\n')
                digest,count=M.logical_edge_evidence(cache)
                meta={**M.cache_identity(C.MINT,'fixture://sqd',old),'version':4,'from_slot':100,
                      'finalized_upper_slot':100,'launch_covered':True,'edge_rows':count,
                      'edge_logical_sha256':digest,'gaps':[],
                      'areas':[{'s':100,'e':100,'done':True},{'s':101,'e':101,'done':True}]}
                meta_path.write_text(json.dumps(meta))
                old_cache, old_meta = cache.read_bytes(), meta_path.read_bytes()
                with mock.patch.object(M.Fetcher,'head',return_value=101), mock.patch.object(M.Fetcher,'scan_area',side_effect=AssertionError('business rescan is forbidden')), mock.patch.object(M.ExtMerger,'finalize',side_effect=OSError('injected merge failure')):
                    failed, gap = M.run(C.MINT,None,1,1,1,'fixture://sqd',None,to_slot_cli=101,
                                        merge_max_rows=0,state_session=C._session(101),keep_parts=True)
                self.assertIn('merge-fail',gap)
                self.assertEqual(cache.read_bytes(),old_cache)
                self.assertEqual(meta_path.read_bytes(),old_meta)
                self.assertTrue((parts/'new.jsonl').is_file())
                with mock.patch.object(M.Fetcher,'head',return_value=101), mock.patch.object(M.Fetcher,'scan_area',side_effect=AssertionError('business rescan is forbidden')):
                    result,gap=M.run(C.MINT,None,1,1,1,'fixture://sqd',None,to_slot_cli=101,
                                     merge_max_rows=0,state_session=C._session(101),keep_parts=True)
                self.assertIsNone(gap);self.assertEqual(len(result),2)
                final=json.loads(meta_path.read_text())
                self.assertEqual(final['collector_sha256'],M.collector_sha256())
                self.assertEqual(final['finalized_upper_slot'],101)
                self.assertEqual(final['edge_rows'],2)
                self.assertTrue((parts/'new.jsonl').is_file())
                self.assertEqual(final['edge_logical_sha256'],M.logical_edge_evidence(cache)[0])
            finally:os.chdir(previous)


if __name__=='__main__':
    unittest.main()
