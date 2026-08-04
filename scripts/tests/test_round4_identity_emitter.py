#!/usr/bin/env python3
import json,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent; REPORT=HERE.parent/"report"; sys.path[:0]=[str(REPORT),str(HERE.parent/"evm")]
def main():
 from identity_snapshot_receipt import emit_evm,emit_solana
 import entity_identity_gate as gate
 with tempfile.TemporaryDirectory() as td:
  d=Path(td); snap=d/"holders.json"; snap.write_text(json.dumps({"0xabc":"100"}))
  pf=d/"channels_preflight.json"; pf.write_text(json.dumps({"schema":"evm-channels-preflight/v1","status":"PASS","token":"0xtoken","expected_to":124}))
  stats=d/"replay_stats.json"; stats.write_text(json.dumps({"gate_pass":True,"supply_check_ok":True,"sum_balances_wei":"100"}))
  out=d/"receipt.json"; emit_evm("bsc","0xtoken",123,snap,pf,stats,100,out)
  assert gate.load_snapshot_binding(str(d/"analysis-state.json"),str(snap),str(out),100,chain="bsc")[1]==100
  old=d/"old.json"; old.write_text(json.dumps({"schema":"identity-holder-snapshot/v1","status":"PASS","complete_owner_universe":True,"as_of_block":123,"total_supply_raw":"100","snapshot":{"path":"holders.json","sha256":"x"}}))
  try: gate.load_snapshot_binding(str(d/"analysis-state.json"),str(snap),str(old),100,chain="bsc")
  except ValueError: pass
  else: raise AssertionError("handwritten v1 must block")
 with tempfile.TemporaryDirectory() as td:
  d=Path(td); snap=d/"holders_owners.json"; snap.write_text(json.dumps({"owner":"100"}))
  meta=d/"holders_snapshot_meta.json"; meta.write_text(json.dumps({"schema":"solana-holder-snapshot-v2","mint":"mint","supply_raw":"100","sum_accounts_raw":"100","closed":True,"scans":[]}))
  emit_solana("mint",123,snap,meta,100,d/"receipt.json")
 try: emit_evm("filecoin","x",1,Path("x"),Path("x"),Path("x"),1,Path("x"))
 except ValueError: pass
 else: raise AssertionError("unsupported chain must fail")
 print("PASS: production EVM/Solana identity emitters; handwritten/unsupported blocked")
 return 0
if __name__=="__main__": raise SystemExit(main())
