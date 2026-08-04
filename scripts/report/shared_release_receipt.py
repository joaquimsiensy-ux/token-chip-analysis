#!/usr/bin/env python3
"""Production aggregator and validator for shared formal release evidence."""
from __future__ import annotations
import argparse,hashlib,json,os
from pathlib import Path
FILES=("accounting_mode.json","reconciliation_report.json","adversarial_review.json")
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def regular(root,rel):
 p=(Path(root)/str(rel)).resolve(); p.relative_to(Path(root).resolve())
 if p.is_symlink() or not p.is_file(): raise ValueError(f"evidence file invalid: {rel}")
 return p
def ref_ok(root,ref):
 if not isinstance(ref,dict): raise ValueError("evidence ref missing")
 p=regular(root,ref.get("path"));
 if ref.get("sha256")!=sha(p): raise ValueError(f"evidence hash mismatch: {p.name}")
 return p
def validate_sources(root):
 root=Path(root).resolve(); a=json.loads(regular(root,"accounting_mode.json").read_text()); r=json.loads(regular(root,"reconciliation_report.json").read_text()); v=json.loads(regular(root,"adversarial_review.json").read_text())
 if a.get("schema")!="accounting-gate/v1" or a.get("exit_code")!=0 or str(a.get("verdict","")).upper() not in {"PASS","WARN"} or not a.get("chain") or not a.get("token") or not isinstance(a.get("checks"),dict) or not a["checks"]: raise ValueError("accounting evidence is not a production gate receipt")
 target={"chain":a["chain"],"token":str(a["token"]).lower(),"as_of_block":a.get("as_of_block")}
 if r.get("schema")!="reconciliation-report/v2" or r.get("target")!=target: raise ValueError("reconciliation target/schema mismatch")
 for key in ("balance","supply","supply_truth","time"):
  item=(r.get("checks") or {}).get(key)
  if not isinstance(item,dict) or item.get("status")!="PASS" or item.get("exit_code")!=0: raise ValueError(f"reconciliation {key} lacks PASS execution receipt")
  ref_ok(root,item.get("receipt")); ref_ok(root,item.get("producer"))
 if v.get("schema")!="adversarial-review/v2" or v.get("target")!=target or v.get("release_decision")!="PASS": raise ValueError("adversarial target/schema/decision invalid")
 roles=set()
 for item in v.get("reviews") or []:
  if not isinstance(item,dict) or item.get("exit_code")!=0: raise ValueError("review lacks successful execution receipt")
  roles.add(str(item.get("role","")).lower()); ref_ok(root,item.get("artifact")); ref_ok(root,item.get("runner"))
 if not any("completeness" in x for x in roles) or not any("entity" in x or "attribution" in x for x in roles): raise ValueError("required adversarial roles missing")
 if any(not isinstance(x,dict) or not x.get("resolved") for x in v.get("blocking_findings",[])): raise ValueError("unresolved adversarial blocker")
 return target
def create_bundle(root,out=None):
 root=Path(root).resolve(); target=validate_sources(root); out=Path(out or root/"shared_release_receipt.json").resolve()
 if out.parent!=root: raise ValueError("shared receipt must be in case root")
 payload={"schema":"shared-release-receipt/v1","status":"PASS",
          "producer":{"path":"shared_release_receipt.py","sha256":sha(__file__)},
          "target":target,"inputs":{n:{"path":n,"sha256":sha(root/n)} for n in FILES}}
 tmp=out.with_name(f".{out.name}.tmp.{os.getpid()}")
 with tmp.open("x") as f: json.dump(payload,f,ensure_ascii=False,indent=2); f.write("\n"); f.flush(); os.fsync(f.fileno())
 os.replace(tmp,out); return payload
def validate_bundle(root):
 errors=[]; root=Path(root).resolve()
 try:
  d=json.loads(regular(root,"shared_release_receipt.json").read_text()); target=validate_sources(root)
  if d.get("schema")!="shared-release-receipt/v1" or d.get("status")!="PASS" or d.get("target")!=target: raise ValueError("shared receipt schema/target invalid")
  if d.get("producer")!={"path":"shared_release_receipt.py","sha256":sha(__file__)}: raise ValueError("shared receipt producer mismatch")
  expected={n:{"path":n,"sha256":sha(root/n)} for n in FILES}
  if d.get("inputs")!=expected: raise ValueError("shared receipt input hashes changed")
 except Exception as exc: errors.append(str(exc))
 return errors
def main(argv=None):
 ap=argparse.ArgumentParser(); ap.add_argument("case_dir"); a=ap.parse_args(argv)
 try: create_bundle(a.case_dir)
 except Exception as exc: ap.exit(2,f"BLOCK: {exc}\n")
 return 0
if __name__=="__main__": raise SystemExit(main())
