#!/usr/bin/env python3
"""A5 报告封口：绑定 A4 v4、Markdown、报告图和分布终态链。"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

SCHEMA="a5-report-seal/v2"
IMG_RE=re.compile(r"!\[[^]]*\]\(([^)]+)\)")
NORMAL_SENTENCE="当前快照呈正常形态;这只表示本闸未检出结构性畸形,不等于没有庄。"
ABNORMAL_SENTENCE="当前快照检出结构性畸形"
LOW_SAMPLE_SENTENCE="形态统计因样本不足未做,以逐址集中度事实替代"


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
 if (root/raw).is_symlink() or not p.is_file(): raise ValueError(f"{label} 不存在或为符号链接")
 return p


def entry(root,path):
 path=Path(path).resolve()
 return {"path":path.relative_to(Path(root).resolve()).as_posix(),"size":path.stat().st_size,"sha256":sha(path)}


def distribution_bundle(root,report,a4obj):
 if a4obj.get("workflow_type")=="independent-audit":
  return {"status":"NOT_APPLICABLE","reason":"analysis-audit single-stage distribution semantics pending"}
 if a4obj.get("workflow_type")!="new-analysis": raise ValueError("A4 workflow_type 非法")
 rounds=safe_file(root,"distribution_rounds.json","分布轮次台账")
 ledger=json.loads(rounds.read_text(encoding="utf-8"))
 import holder_distribution_scan
 ledger_errors=holder_distribution_scan.validate_rounds_ledger(ledger)
 if ledger_errors: raise ValueError("分布轮次台账断链: "+"; ".join(ledger_errors))
 if ledger.get("schema")!="distribution-rounds/v1" or not isinstance(ledger.get("rounds"),list) \
        or not ledger.get("terminal"):
  raise ValueError("分布轮次台账未到唯一终态")
 terminal=ledger["terminal"]; matches=[x for x in ledger["rounds"] if x.get("round_n")==terminal.get("round_n")]
 if len(matches)!=1: raise ValueError("分布 terminal 指针不唯一")
 row=matches[0]
 scan=safe_file(root,terminal.get("final_scan_path"),"终态 final scan")
 errors=holder_distribution_scan.validate_scan(Path(root),terminal.get("final_scan_path"),"final")
 if errors: raise ValueError("终态 final scan 重验失败: "+"; ".join(errors))
 scan_obj=json.loads(scan.read_text(encoding="utf-8"))
 if row.get("final_scan_sha")!=sha(scan) or row.get("a4_seal_sha")!=sha(Path(root)/"a4_seal.json"):
  raise ValueError("终态 row 未绑定当前 final scan 或 A4 seal")
 chart=safe_file(root,terminal.get("final_chart_path"),"终态分布图")
 if terminal.get("final_chart_path")!="charts/final/holder_distribution_current.png":
  raise ValueError("终态分布图路径不是唯一标准路径")
 text=report.read_text(encoding="utf-8")
 image_refs=[x.split()[0].strip("<>") for x in IMG_RE.findall(text)]
 if image_refs.count("charts/final/holder_distribution_current.png")!=1:
  raise ValueError("报告必须且只能引用一张终态持仓分布图")
 status=terminal.get("status")
 if status=="NORMAL":
  if scan_obj.get("verdict")!="NORMAL_SHAPE" or NORMAL_SENTENCE not in text:
   raise ValueError("NORMAL 终态缺固定报告句式")
 elif status=="LOW_SAMPLE":
  if scan_obj.get("not_evaluable_reason")!="low_sample" or not (scan_obj.get("small_sample_mode") or {}).get("complete") \
         or LOW_SAMPLE_SENTENCE not in text:
   raise ValueError("low_sample 集中度模式不完整或缺强制披露句")
 elif status=="EXPLAINED":
  if scan_obj.get("verdict")!="ABNORMAL_SHAPE" or ABNORMAL_SENTENCE not in text:
   raise ValueError("ABNORMAL 终态缺固定报告句式")
  ep=safe_file(root,row.get("explanation_path"),"分布解释")
  import distribution_explanation_check
  errs=distribution_explanation_check.validate_explanation(Path(root),row.get("explanation_path"))
  if errs: raise ValueError("分布解释重验失败: "+"; ".join(errs))
  if row.get("explanation_sha")!=sha(ep): raise ValueError("rounds 记录的分布解释哈希漂移")
  explanation=entry(root,ep)
 elif status=="WAIVED":
  wp=safe_file(root,row.get("explanation_path"),"分布 waiver")
  waiver=json.loads(wp.read_text(encoding="utf-8"))
  required=("user_decided_at_utc","round_n","unexplained_clusters","unexplained_raw",
            "a4_seal_sha256","final_scan_sha256","rounds_sha256")
  before={k:v for k,v in ledger.items() if k not in {"rounds","terminal"}}
  before.update({"rounds":[x for x in ledger["rounds"] if x.get("round_n")<terminal["round_n"]],
                 "terminal":None})
  waiver_errors=holder_distribution_scan.validate_waiver(
      Path(root),waiver,scan,holder_distribution_scan.formatted_json_sha(before),terminal["round_n"])
  if waiver.get("schema")!="distribution-exception-receipt/v1" \
       or any(waiver.get(k) in (None,"",[]) for k in required) or waiver_errors \
       or row.get("explanation_sha")!=sha(wp) or "未解释" not in text:
   raise ValueError("waiver 收据或报告强制披露不完整")
  explanation=entry(root,wp)
 else:
  raise ValueError(f"分布终态 status 非法: {status}")
 payload={"status":status,"round_n":terminal["round_n"],"rounds":entry(root,rounds),
          "final_scan":entry(root,scan),"final_chart":entry(root,chart)}
 if status in {"EXPLAINED","WAIVED"}: payload["explanation_or_waiver"]=explanation
 return payload


def create_seal(case_dir,report,a4_seal,out):
 root=Path(case_dir).resolve(); report=safe_file(root,report,"Markdown"); a4=safe_file(root,a4_seal,"A4 seal")
 a4obj=json.loads(a4.read_text())
 if a4obj.get("schema")!="a4-seal/v4" or a4obj.get("verdict")!="PASS" or not a4obj.get("claims"):
  raise ValueError("A4 seal 非 PASS a4-seal/v4 或无 claims")
 import a4_gate
 chain_errors=a4_gate.validate_revision_chain(root,a4obj)
 if chain_errors: raise ValueError("A4 revision 链无效: "+"; ".join(chain_errors))
 charts=(root/str(a4obj.get("charts_dir","charts/final"))).resolve(); charts.relative_to(root)
 images=[]
 for value in IMG_RE.findall(report.read_text(encoding="utf-8")):
  rel=value.split()[0].strip("<>"); img=safe_file(root,rel,"报告图")
  try: img.relative_to(charts)
  except ValueError: raise ValueError(f"报告图不在 A4 charts_dir: {rel}")
  images.append(entry(root,img))
 payload={"schema":SCHEMA,"status":"PASS","producer":"a5_report_seal.py/v2",
  "workflow_type":a4obj.get("workflow_type"),"a4_seal":entry(root,a4),
  "report":entry(root,report),"images":images,
  "distribution":distribution_bundle(root,report,a4obj)}
 target=Path(out).resolve()
 if target.parent!=root: raise ValueError("A5 seal 必须写在案目录根")
 target.parent.mkdir(parents=True,exist_ok=True); tmp=target.with_name(f".{target.name}.tmp.{os.getpid()}")
 with tmp.open("x") as f: json.dump(payload,f,ensure_ascii=False,indent=2); f.write("\n"); f.flush(); os.fsync(f.fileno())
 os.replace(tmp,target); return payload


def validate_seal(seal_path,report_path,a4_path):
 errors=[]
 try:
  seal=Path(seal_path).resolve(); root=seal.parent; d=json.loads(seal.read_text()); report=safe_file(root,report_path,"Markdown"); a4=safe_file(root,a4_path,"A4 seal")
  if d.get("schema")!=SCHEMA or d.get("status")!="PASS": return ["A5 report seal schema/status 非 PASS"]
  a4obj=json.loads(a4.read_text())
  if a4obj.get("schema")!="a4-seal/v4": errors.append("A5 seal 只接受 a4-seal/v4")
  else:
   import a4_gate
   errors.extend("A4 revision 链无效: "+x for x in a4_gate.validate_revision_chain(root,a4obj))
  if d.get("a4_seal")!=entry(root,a4): errors.append("A5 seal 未绑定当前 A4 seal")
  if d.get("report")!=entry(root,report): errors.append("A5 seal 未绑定当前 Markdown")
  for item in d.get("images",[]):
   img=safe_file(root,item.get("path"),"报告图")
   if item!=entry(root,img): errors.append(f"A5 seal 报告图哈希变化: {item.get('path')}")
  current={x.split()[0].strip("<>") for x in IMG_RE.findall(report.read_text(encoding="utf-8"))}
  if current!={x.get("path") for x in d.get("images",[])}: errors.append("A5 seal 报告图集合变化")
  try:
   actual_distribution=distribution_bundle(root,report,a4obj)
   if d.get("distribution")!=actual_distribution: errors.append("A5 seal 分布终态绑定变化")
  except Exception as exc: errors.append(f"A5 seal 分布终态不可重验: {exc}")
 except Exception as exc: errors.append(f"A5 report seal 不可验证: {exc}")
 return errors


def main(argv=None):
 ap=argparse.ArgumentParser(); ap.add_argument("--case-dir",required=True); ap.add_argument("--report",required=True); ap.add_argument("--a4-seal",required=True); ap.add_argument("--out",required=True); a=ap.parse_args(argv)
 try: create_seal(a.case_dir,a.report,a.a4_seal,a.out)
 except Exception as exc: ap.exit(2,f"BLOCK: {exc}\n")
 return 0
if __name__=="__main__": raise SystemExit(main())
