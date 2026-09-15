"""Offline native scanner reuse: raw replay, immutable inputs, and alias rejection."""
import contextlib,copy,gzip,hashlib,importlib.util,io,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/lib'),str(ROOT/'scripts/tests')]
from test_r9_batch3_solana_observation import SolanaTransportFake,MINT,PROGRAM
from solana_observation import validate_observation_bundle
spec=importlib.util.spec_from_file_location('reuse_scanner',ROOT/'scripts/solana/scan_token_accounts.py')
scanner=importlib.util.module_from_spec(spec);spec.loader.exec_module(scanner)

class ReuseTests(unittest.TestCase):
 def setUp(self):
  self.prev=Path.cwd();self.root=Path(tempfile.mkdtemp());os.chdir(self.root)
  self.addCleanup(lambda:os.chdir(self.prev))
  # New private fixtures are deliberately retained, never recursively deleted.
  self.source=Path('source/bundle.json');self.out=Path('new/snapshot.json');self.marker=Path('new/bundle.json')
  with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
   rc=scanner.main([MINT,'--program','spl','--rpc','fixture://solana','--out','source/snapshot.json','--bundle',str(self.source),'--work-dir','source/raw'],request_json=SolanaTransportFake(activity='zero'))
  self.assertEqual(rc,0)
  self.slot=json.loads(self.source.read_text())['target']['as_of_block']
 def invoke(self,extra=(),mint=MINT,out=None,marker=None,work='new/raw'):
  args=[mint,'--reuse-observation-bundle',str(self.source),'--out',str(out or self.out),'--bundle',str(marker or self.marker),'--work-dir',work,*extra]
  with patch.object(scanner,'SolanaAttestedSession',side_effect=AssertionError('network session forbidden')),patch.object(scanner,'_default_rpc',side_effect=AssertionError('credential access forbidden')),contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
   return scanner.main(args)
 def source_hashes(self):
  return {str(p):(p.stat().st_ino,hashlib.sha256(p.read_bytes()).hexdigest()) for p in Path('source').rglob('*') if p.is_file()}
 def test_positive_offline_later_slot_native_bundle(self):
  before=self.source_hashes();self.assertEqual(self.invoke(['--min-context-slot',str(self.slot-1),'--as-of-slot',str(self.slot)]),0)
  result=json.loads(self.marker.read_text());validate_observation_bundle(result,bundle_path=self.marker,expected_mint=MINT)
  self.assertEqual(result['target']['as_of_block'],self.slot)
  self.assertEqual(result['observation_reuse']['mode'],'verified-offline-reuse')
  self.assertEqual(json.loads(self.out.read_text())['owners'],json.loads(Path('source/snapshot.json').read_text())['owners'])
  self.assertEqual(self.source_hashes(),before)
 def test_wrong_identity_program_slot_and_lower_bound(self):
  for args,mint in [([],MINT+'x'),(['--program','token2022'],MINT),(['--as-of-slot',str(self.slot-1)],MINT),(['--min-context-slot',str(self.slot+1)],MINT)]:
   with self.subTest(args=args,mint=mint):self.assertNotEqual(self.invoke(args,mint=mint),0);self.assertFalse(self.marker.exists())
 def test_missing_and_tampered_raw_fail_without_pass(self):
  raw=Path('source/raw/_gpa_raw_all.json');original=raw.read_bytes()
  raw.write_bytes(original+b' ')
  self.assertNotEqual(self.invoke(),0);self.assertFalse(self.marker.exists())
  raw.unlink();self.assertNotEqual(self.invoke(),0);self.assertFalse(self.marker.exists())
 def test_rehashed_raw_still_must_match_snapshot(self):
  raw=Path('source/raw/_gpa_raw_all.json');obj=json.loads(raw.read_text());obj['result']['value']=[];raw.write_text(json.dumps(obj))
  bundle=json.loads(self.source.read_text());ref=bundle['inputs']['gpa_rpc'];ref['size']=raw.stat().st_size;ref['sha256']=scanner.sha256_file(raw);self.source.write_text(json.dumps(bundle))
  self.assertNotEqual(self.invoke(),0);self.assertFalse(self.marker.exists())
 def test_wrong_or_missing_source_snapshot(self):
  snapshot=Path('source/snapshot.json');snapshot.write_text('{}')
  self.assertNotEqual(self.invoke(),0);self.assertFalse(self.marker.exists())
 def test_external_source_bundle_with_internal_inputs_rejected(self):
  before=self.source_hashes();external=Path(tempfile.mkdtemp())/'bundle.json'
  external.write_bytes(self.source.read_bytes());self.source=external
  self.assertNotEqual(self.invoke(),0);self.assertFalse(self.marker.exists())
  self.assertEqual(self.source_hashes(),before)
 def test_external_snapshot_dependency_rejected(self):
  external=Path(tempfile.mkdtemp())/'snapshot.json'
  external.write_bytes(Path('source/snapshot.json').read_bytes())
  bundle=json.loads(self.source.read_text());bundle['output']['path']=str(external);self.source.write_text(json.dumps(bundle))
  self.assertNotEqual(self.invoke(),0);self.assertFalse(self.marker.exists())
 def test_output_cannot_alias_source_bundle_or_each_dependency(self):
  before=self.source_hashes()
  for source in [self.source,Path('source/snapshot.json'),*Path('source/raw').iterdir()]:
   with self.subTest(source=str(source)):
    self.assertNotEqual(self.invoke(out=source),0)
    self.assertEqual(self.source_hashes(),before)
  self.assertNotEqual(self.invoke(marker=self.source),0);self.assertEqual(self.source_hashes(),before)
  self.assertNotEqual(self.invoke(work='source/raw'),0);self.assertEqual(self.source_hashes(),before)
 def test_symlink_and_hardlink_output_alias_rejected(self):
  Path('new').mkdir();before=self.source_hashes();link=Path('new/link')
  link.symlink_to(Path('../source/raw/_gpa_raw_all.json'))
  self.assertNotEqual(self.invoke(out=link),0);self.assertTrue(link.is_symlink());self.assertEqual(self.source_hashes(),before)
  hard=Path('new/hard');os.link(self.source,hard)
  self.assertNotEqual(self.invoke(marker=hard),0);self.assertTrue(hard.exists());self.assertEqual(self.source_hashes(),before)
 def test_auxiliary_outputs_distinct_from_snapshot_and_bundle(self):
  self.assertNotEqual(self.invoke(out=Path('new/raw/holders_owners.json')),0);self.assertFalse(self.marker.exists())
 def test_reuse_chain_protects_ancestor_dependencies(self):
  self.assertEqual(self.invoke(),0);before=self.source_hashes();self.source=self.marker
  self.assertNotEqual(self.invoke(out=Path('source/raw/holders_owners.json'),marker=Path('third/bundle.json'),work='third/raw'),0)
  self.assertEqual(self.source_hashes(),before)
  self.assertEqual(self.invoke(out=Path('third/snapshot.json'),marker=Path('third/bundle.json'),work='third/raw'),0)
 def test_invalid_source_quarantines_previous_safe_pass(self):
  self.assertEqual(self.invoke(),0);raw=Path('source/raw/_supply.json');raw.write_bytes(raw.read_bytes()+b' ')
  self.assertNotEqual(self.invoke(),0)
  self.assertFalse(self.marker.exists());self.assertFalse(self.out.exists())
  self.assertTrue(list(Path('new').glob('*.ERROR*.json')) or list(Path('new').glob('*.error*.json')))
 def test_live_entry_stays_live(self):
  fake=SolanaTransportFake(activity='zero')
  with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
   rc=scanner.main([MINT,'--rpc','fixture://solana','--out','live/snapshot.json','--bundle','live/bundle.json','--work-dir','live/raw'],request_json=fake)
  self.assertEqual(rc,0);self.assertTrue(fake.calls);self.assertNotIn('observation_reuse',json.loads(Path('live/bundle.json').read_text()))

if __name__=='__main__':unittest.main()
