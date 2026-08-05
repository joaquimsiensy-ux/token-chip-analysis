#!/usr/bin/env python3
"""Known-chain identity-holder-snapshot/v2 emitters for formal or exploratory replay."""
from __future__ import annotations
import argparse,hashlib,json,os,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent; EVM=HERE.parent/"evm"; SOL=HERE.parent/"solana"
sys.path.insert(0, str(EVM))
sys.path.insert(0, str(SOL))
from channels_preflight import validate_preflight_artifact
from scan_token_accounts import parse_gpa_response, parse_supply_response, parse_token_accounts
EVM_CHAINS={"eth","base","bsc","arbitrum","robinhood"}
KNOWN_CHAINS=EVM_CHAINS|{"sol"}
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(Path(p).read_text())
def total_snapshot(p):
 d=load(p)
 if not isinstance(d,dict) or not d: raise ValueError("snapshot must be nonempty owner map")
 vals=[]
 for v in d.values():
  if isinstance(v,bool) or not str(v).isdigit(): raise ValueError("snapshot amount must be nonnegative raw integer")
  vals.append(int(v))
 return sum(vals)
def ref(root,p):
 raw=Path(p)
 if raw.is_symlink(): raise ValueError("source must be regular case file")
 p=raw.resolve(); root=Path(root).resolve(); p.relative_to(root)
 if not p.is_file(): raise ValueError("source must be regular case file")
 return {"path":p.name,"sha256":sha(p)}
def write(payload,out):
 out=Path(out).resolve(); tmp=out.with_name(f".{out.name}.tmp.{os.getpid()}")
 with tmp.open("x") as f: json.dump(payload,f,ensure_ascii=False,indent=2); f.write("\n"); f.flush(); os.fsync(f.fileno())
 os.replace(tmp,out); return payload
def base(chain,token,block,snapshot,total,source):
 snapshot=Path(snapshot).resolve(); total=int(total)
 if chain not in KNOWN_CHAINS: raise ValueError(f"chain {chain} has no known identity emitter")
 if total_snapshot(snapshot)!=total or total<=0: raise ValueError("snapshot does not close to total supply")
 return {"schema":"identity-holder-snapshot/v2","status":"PASS","complete_owner_universe":True,
  "producer":{"path":"identity_snapshot_receipt.py","sha256":sha(__file__)},
  "adapter":chain,"token":str(token),"as_of_block":int(block),"total_supply_raw":str(total),
  "snapshot":{"path":snapshot.name,"sha256":sha(snapshot)},"source":source}
def validate_evm_sources(snapshot,preflight,stats,total,replay_engine,token,block):
 if any(Path(p).is_symlink() for p in (snapshot,preflight,stats)):
  raise ValueError("EVM identity source must not be a symlink")
 root=Path(snapshot).resolve().parent
 if Path(preflight).resolve().parent!=root or Path(stats).resolve().parent!=root:
  raise ValueError("EVM snapshot/preflight/stats must share one case output directory")
 pf=validate_preflight_artifact(preflight); st=load(stats)
 if str(pf.get("token")).lower()!=str(token).lower() or pf.get("expected_to")!=int(block)+1:
  raise ValueError("EVM preflight does not bind token/as-of block")
 if replay_engine not in {"replay_stream.py","replay_duck.py","replay_pass1.py"}:
  raise ValueError("unsupported replay engine")
 engine=(EVM/replay_engine).resolve()
 if st.get("producer")!={"path":replay_engine,"sha256":sha(engine)}:
  raise ValueError("replay stats producer is not the selected current engine")
 if st.get("preflight")!={"path":Path(preflight).name,"sha256":sha(preflight)}:
  raise ValueError("replay stats do not bind current preflight")
 if st.get("inputs")!=pf.get("inputs"):
  raise ValueError("replay stats inputs differ from collector-backed preflight inputs")
 expected_output={"path":Path(snapshot).name,"size":Path(snapshot).stat().st_size,"sha256":sha(snapshot)}
 if (st.get("outputs") or {}).get("balances_final")!=expected_output:
  raise ValueError("replay stats do not bind the owner snapshot")
 if st.get("gate_pass") is not True or st.get("supply_check_ok") is not True or str(st.get("sum_balances_wei"))!=str(total):
  raise ValueError("EVM replay stats do not prove closed owner universe")
 return pf,st,engine

def emit_evm(chain,token,block,snapshot,preflight,stats,total,out,replay_engine="replay_stream.py"):
 if chain not in EVM_CHAINS: raise ValueError(f"chain {chain} has no EVM identity emitter")
 root=Path(snapshot).resolve().parent
 pf,st,engine=validate_evm_sources(snapshot,preflight,stats,total,replay_engine,token,block)
 source={"kind":"evm-replay","preflight":ref(root,preflight),"replay_stats":ref(root,stats),
         "collector":{"path":replay_engine,"sha256":sha(engine)},
         "inputs":pf["inputs"]}
 return write(base(chain,token,block,snapshot,total,source),out)

def validate_solana_source(mint,snapshot,meta,total):
 if Path(snapshot).is_symlink() or Path(meta).is_symlink():
  raise ValueError("Solana identity source must not be a symlink")
 root=Path(snapshot).resolve().parent; m=load(meta); collector=SOL/"scan_token_accounts.py"
 if Path(meta).resolve().parent!=root:
  raise ValueError("Solana snapshot/meta must share one collector output directory")
 if m.get("schema")!="solana-holder-snapshot-v2" or m.get("closed") is not True or m.get("mint")!=mint or str(m.get("supply_raw"))!=str(total) or str(m.get("sum_accounts_raw"))!=str(total):
  raise ValueError("Solana holder meta does not prove closed owner universe")
 if m.get("producer")!={"path":"scan_token_accounts.py","sha256":sha(collector)}:
  raise ValueError("Solana holder meta producer is not current scan_token_accounts.py")
 outputs=m.get("outputs") or {}
 owners_path=ref_with_size(root,outputs.get("holders_owners"),"holders_owners")
 accounts_path=ref_with_size(root,outputs.get("holders_accounts"),"holders_accounts")
 if owners_path!=Path(snapshot).resolve():
  raise ValueError("Solana holder meta does not bind owner snapshot")
 supply_path=ref_with_size(root,m.get("supply_receipt"),"supply_receipt")
 try:
  supply_slot,decimals,supply_raw=parse_supply_response(load(supply_path))
 except Exception as exc:
  raise ValueError(f"Solana supply receipt content invalid: {exc}") from exc
 if supply_raw!=int(total) or decimals!=m.get("decimals"):
  raise ValueError("Solana supply receipt does not match snapshot supply/decimals")
 scans=m.get("scans") or []
 if not scans:
  raise ValueError("Solana holder meta lacks bound GPA scan artifacts")
 raw_accounts=[]
 for i,scan in enumerate(scans):
  if not isinstance(scan,dict): raise ValueError(f"scan[{i}] must be an object")
  raw_path=ref_with_size(root,scan.get("raw_artifact"),f"scan[{i}].raw")
  scan_meta_path=ref_with_size(root,scan.get("meta_artifact"),f"scan[{i}].meta")
  scan_claim={k:v for k,v in scan.items() if k not in {"raw_artifact","meta_artifact"}}
  if load(scan_meta_path)!=scan_claim:
   raise ValueError(f"scan[{i}] metadata artifact differs from snapshot claim")
  try:
   batch,gpa_slot=parse_gpa_response(load(raw_path))
  except Exception as exc:
   raise ValueError(f"scan[{i}] raw GPA response invalid: {exc}") from exc
  if (scan_claim.get("mint")!=mint or scan_claim.get("program")!=m.get("program")
      or scan_claim.get("account_count")!=len(batch)
      or scan_claim.get("gpa_response_slot")!=gpa_slot
      or scan_claim.get("supply_observed_slot")!=supply_slot):
   raise ValueError(f"scan[{i}] metadata does not match raw GPA response/target")
  raw_accounts.extend(batch)
 try:
  _,computed_rows,computed_owners,malformed=parse_token_accounts(raw_accounts)
 except Exception as exc:
  raise ValueError(f"Solana raw GPA account decode invalid: {exc}") from exc
 if malformed:
  raise ValueError(f"Solana raw GPA replay found {malformed} malformed accounts")
 if load(accounts_path)!=computed_rows:
  raise ValueError("holders_accounts does not match offline replay of raw GPA responses")
 if load(owners_path)!=computed_owners:
  raise ValueError("holders_owners does not match offline replay of raw GPA responses")
 computed_total=sum(computed_owners.values())
 if computed_total!=int(m["sum_accounts_raw"]) or computed_total!=supply_raw:
  raise ValueError("offline replay total does not close to snapshot/supply receipt")
 return m,collector

def ref_with_size(root,item,label):
 if not isinstance(item,dict): raise ValueError(f"{label} artifact missing")
 raw=Path(root)/str(item.get("path",""))
 if raw.is_symlink(): raise ValueError(f"{label} artifact binding invalid")
 p=raw.resolve(); p.relative_to(Path(root).resolve())
 if not p.is_file() or item.get("size")!=p.stat().st_size or item.get("sha256")!=sha(p):
  raise ValueError(f"{label} artifact binding invalid")
 return p

def emit_solana(mint,block,snapshot,meta,total,out):
 root=Path(snapshot).resolve().parent; m,collector=validate_solana_source(mint,snapshot,meta,total)
 source={"kind":"solana-token-accounts","snapshot_meta":ref(root,meta),
         "collector":{"path":"scan_token_accounts.py","sha256":sha(collector)},
         "scan_artifacts":[{"raw_artifact":x["raw_artifact"],"meta_artifact":x["meta_artifact"]}
                           for x in m["scans"]]}
 return write(base("sol",mint,block,snapshot,total,source),out)

def validate_receipt(receipt,snapshot,total,chain):
 r=load(receipt); root=Path(receipt).resolve().parent; errors=[]
 try:
  if r.get("schema")!="identity-holder-snapshot/v2" or r.get("status")!="PASS" or r.get("adapter")!=chain: raise ValueError("receipt schema/status/adapter invalid")
  if r.get("producer")!={"path":"identity_snapshot_receipt.py","sha256":sha(__file__)}: raise ValueError("receipt producer is not current production emitter")
  if r.get("snapshot")!={"path":Path(snapshot).name,"sha256":sha(snapshot)} or str(r.get("total_supply_raw"))!=str(total): raise ValueError("receipt snapshot/supply binding mismatch")
  src=r.get("source") or {}
  if chain=="sol":
   meta=(root/str((src.get("snapshot_meta") or {}).get("path",""))).resolve()
   validate_solana_source(r.get("token"),snapshot,meta,total)
  else:
   preflight=(root/str((src.get("preflight") or {}).get("path",""))).resolve()
   stats=(root/str((src.get("replay_stats") or {}).get("path",""))).resolve()
   validate_evm_sources(snapshot,preflight,stats,total,(src.get("collector") or {}).get("path"),r.get("token"),r.get("as_of_block"))
  for key in (("snapshot_meta",) if chain=="sol" else ("preflight","replay_stats")):
   item=src.get(key) or {}; raw=root/str(item.get("path",""))
   if raw.is_symlink(): raise ValueError(f"identity source {key} changed")
   path=raw.resolve(); path.relative_to(root)
   if not path.is_file() or item.get("sha256")!=sha(path): raise ValueError(f"identity source {key} changed")
 except Exception as exc: errors.append(str(exc))
 return errors

def main(argv=None):
 ap=argparse.ArgumentParser()
 ap.add_argument("--chain",required=True,choices=sorted(KNOWN_CHAINS))
 ap.add_argument("--token",required=True)
 ap.add_argument("--as-of-block",required=True,type=int)
 ap.add_argument("--snapshot",required=True)
 ap.add_argument("--total-supply-raw",required=True)
 ap.add_argument("--source-receipt",required=True)
 ap.add_argument("--replay-stats")
 ap.add_argument("--replay-engine",default="replay_stream.py")
 ap.add_argument("--out",required=True)
 a=ap.parse_args(argv)
 try:
  if a.chain=="sol": emit_solana(a.token,a.as_of_block,a.snapshot,a.source_receipt,a.total_supply_raw,a.out)
  elif not a.replay_stats: ap.error("EVM requires --replay-stats")
  else: emit_evm(a.chain,a.token,a.as_of_block,a.snapshot,a.source_receipt,a.replay_stats,a.total_supply_raw,a.out,a.replay_engine)
 except ValueError as exc: ap.exit(2,f"BLOCK: {exc}\n")
 return 0
if __name__=="__main__": raise SystemExit(main())
