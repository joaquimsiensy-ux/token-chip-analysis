#!/usr/bin/env python3
"""Round4b F-01: identity receipts require real collector/replay or holder-scan chains."""
import base64,hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent; EVM=HERE.parent/"evm"; SOL=HERE.parent/"solana"; REPORT=HERE.parent/"report"; LIB=HERE.parent/"lib"
sys.path[:0]=[str(EVM),str(REPORT),str(SOL),str(LIB),str(HERE)]
TOKEN="0x"+"a"*40; OWNER="0x"+"b"*40; ZERO="0x"+"0"*40
def run_evm(root):
 import fetch_hypersync as fetch
 class R:
  status_code=200; text=""
  def json(self): return {"data":[{"blocks":[{"number":5,"timestamp":1}],"logs":[{
   "block_number":5,"block_hash":"0xh","log_index":0,"transaction_hash":"0xt",
   "topic1":"0x"+"0"*64,"topic2":"0x"+"0"*24+OWNER[2:],"data":hex(100)}]}],
   "next_block":10,"archive_height":10}
 fetch.requests.post=lambda *a,**k:R(); old=sys.argv
 csv=root/"events.csv"; native=root/"collector.json"
 token_file=root/"hypersync.token"; token_file.write_text("secret\n")
 sys.argv=["fetch_hypersync.py","0","--token-file",str(token_file),"--url","https://fixture/query","--token-addr",TOKEN,
           "--out",str(csv),"--to-block","10","--receipt",str(native),"--sleep","0"]
 try: fetch.main()
 finally: sys.argv=old
 from make_channel_receipt import make_receipt
 channel=root/"channel.json"; channel.write_text(json.dumps(make_receipt(csv,"v1csv",TOKEN,0,10,"p0",collector_receipt=native)))
 manifest=root/"channels.json"; manifest.write_text(json.dumps({"schema":"evm-channels/v2","token":TOKEN,"expected_from":0,"expected_to":10,"channels":[{"tag":"p0","path":str(csv),"format":"v1csv","lo":0,"hi":10,"receipt":str(channel)}]}))
 p=subprocess.run([sys.executable,str(EVM/"replay_pass1.py"),"--channels",str(manifest),"--out-dir",str(root)],capture_output=True,text=True)
 assert p.returncode==0,p.stdout+p.stderr
 return root/"balances_final.json",root/"channels_preflight.json",root/"replay_stats.json"
def run_solana(root):
 import scan_token_accounts as scan
 from test_r9_batch3_solana_observation import SolanaTransportFake
 old_cwd=os.getcwd(); os.chdir(root)
 try:
  rc=scan.main(["mint","--program","spl","--rpc","fixture://solana",
                "--out","snapshot.json","--bundle","snapshot_receipt.json",
                "--work-dir","data"],request_json=SolanaTransportFake())
  assert rc==0
 finally: os.chdir(old_cwd)
 return root/"data"/"holders_owners.json",root/"data"/"holders_snapshot_meta.json"
def main():
 from identity_snapshot_receipt import emit_evm,emit_solana
 import entity_identity_gate as gate
 with tempfile.TemporaryDirectory() as td:
  d=Path(td); snap,pf,stats=run_evm(d); out=d/"identity.json"
  emit_evm("bsc",TOKEN,9,snap,pf,stats,100,out,replay_engine="replay_pass1.py")
  assert gate.load_snapshot_binding(str(d/"analysis-state.json"),str(snap),str(out),100,chain="bsc")[1]==100
  forged=d/"forged_pf.json"; forged.write_text(json.dumps({"schema":"evm-channels-preflight/v1","status":"PASS","token":TOKEN,"expected_to":10,"producer":{"path":"channels_preflight.py","sha256":hashlib.sha256((EVM/"channels_preflight.py").read_bytes()).hexdigest()}}))
  try: emit_evm("bsc",TOKEN,9,snap,forged,stats,100,d/"bad.json",replay_engine="replay_pass1.py")
  except ValueError: pass
  else: raise AssertionError("isolated copied-hash preflight must block")
 with tempfile.TemporaryDirectory() as td:
  d=Path(td); snap,meta=run_solana(d); out=snap.parent/"identity.json"
  emit_solana("mint",123,snap,meta,100,out)
  m=json.loads(meta.read_text()); m["producer"]["sha256"]=hashlib.sha256((SOL/"scan_token_accounts.py").read_bytes()).hexdigest(); m["scans"]=[]; meta.write_text(json.dumps(m))
  try: emit_solana("mint",123,snap,meta,100,snap.parent/"bad.json")
  except ValueError: pass
  else: raise AssertionError("isolated Solana meta without scan artifacts must block")
 print("PASS: real EVM collector+preflight+replay and Solana scan chains; copied-hash self-reports blocked")
 return 0
if __name__=="__main__": raise SystemExit(main())
