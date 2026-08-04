#!/usr/bin/env python3
"""Production A5 compiler receipt binding A4 seal, final Markdown, and report images."""
from __future__ import annotations
import argparse,hashlib,json,os,re,sys
from pathlib import Path
SCHEMA="a5-report-seal/v1"
IMG_RE=re.compile(r"!\[[^]]*\]\(([^)]+)\)")
def sha(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for b in iter(lambda:f.read(4*1024*1024),b""): h.update(b)
 return h.hexdigest()
def safe_file(root,value,label):
 root=Path(root).resolve(); raw=Path(value)
 if raw.is_absolute(): p=raw.resolve()
 else: p=(root/raw).resolve()
 try: p.relative_to(root)
 except ValueError: raise ValueError(f"{label} 越出案目录")
 if p.is_symlink() or not p.is_file(): raise ValueError(f"{label} 不存在或为符号链接")
 return p
def create_seal(case_dir,report,a4_seal,out):
 root=Path(case_dir).resolve(); report=safe_file(root,report,"Markdown"); a4=safe_file(root,a4_seal,"A4 seal")
 a4obj=json.loads(a4.read_text())
 if a4obj.get("schema")!="a4-seal/v3" or a4obj.get("verdict")!="PASS" or not a4obj.get("claims"):
  raise ValueError("A4 seal 非 PASS 或无 claims")
 charts=safe_dir=(root/str(a4obj.get("charts_dir","charts/final"))).resolve(); safe_dir.relative_to(root)
 images=[]
 for value in IMG_RE.findall(report.read_text(encoding="utf-8")):
  rel=value.split()[0].strip("<>")
  img=safe_file(root,rel,"报告图")
  try: img.relative_to(charts)
  except ValueError: raise ValueError(f"报告图不在 A4 charts_dir: {rel}")
  images.append({"path":img.relative_to(root).as_posix(),"size":img.stat().st_size,"sha256":sha(img)})
 payload={"schema":SCHEMA,"status":"PASS","producer":"a5_report_seal.py/v1",
  "a4_seal":{"path":a4.relative_to(root).as_posix(),"sha256":sha(a4)},
  "report":{"path":report.relative_to(root).as_posix(),"size":report.stat().st_size,"sha256":sha(report)},
  "images":images}
 target=Path(out).resolve()
 if target.parent != root: raise ValueError("A5 seal 必须写在案目录根")
 target.parent.mkdir(parents=True,exist_ok=True); tmp=target.with_name(f".{target.name}.tmp.{os.getpid()}")
 with tmp.open("x") as f: json.dump(payload,f,ensure_ascii=False,indent=2); f.write("\n"); f.flush(); os.fsync(f.fileno())
 os.replace(tmp,target); return payload
def validate_seal(seal_path,report_path,a4_path):
 errors=[]
 try:
  seal=Path(seal_path).resolve(); root=seal.parent; d=json.loads(seal.read_text()); report=safe_file(root,report_path,"Markdown"); a4=safe_file(root,a4_path,"A4 seal")
  if d.get("schema")!=SCHEMA or d.get("status")!="PASS": errors.append("A5 report seal schema/status 非 PASS"); return errors
  if d.get("a4_seal")!={"path":a4.relative_to(root).as_posix(),"sha256":sha(a4)}: errors.append("A5 seal 未绑定当前 A4 seal")
  actual={"path":report.relative_to(root).as_posix(),"size":report.stat().st_size,"sha256":sha(report)}
  if d.get("report")!=actual: errors.append("A5 seal 未绑定当前 Markdown")
  for item in d.get("images",[]):
   img=safe_file(root,item.get("path"),"报告图"); actual={"path":img.relative_to(root).as_posix(),"size":img.stat().st_size,"sha256":sha(img)}
   if item!=actual: errors.append(f"A5 seal 报告图哈希变化: {item.get('path')}")
  current={x.split()[0].strip("<>") for x in IMG_RE.findall(report.read_text(encoding="utf-8"))}
  if current!={x.get("path") for x in d.get("images",[])}: errors.append("A5 seal 报告图集合变化")
 except Exception as exc: errors.append(f"A5 report seal 不可验证: {exc}")
 return errors
def main(argv=None):
 ap=argparse.ArgumentParser(); ap.add_argument("--case-dir",required=True); ap.add_argument("--report",required=True); ap.add_argument("--a4-seal",required=True); ap.add_argument("--out",required=True); a=ap.parse_args(argv)
 try: create_seal(a.case_dir,a.report,a.a4_seal,a.out)
 except Exception as exc: ap.exit(2,f"BLOCK: {exc}\n")
 return 0
if __name__=="__main__": raise SystemExit(main())
