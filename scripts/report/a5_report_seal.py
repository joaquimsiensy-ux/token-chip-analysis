#!/usr/bin/env python3
"""A5 报告封口：绑定 A4 v4、Markdown、报告图和分布终态链。

v2 -> v3 迁移：已经生成的旧 HTML 不受影响，但 v2 seal 不能冒充 v3 通过
正式验证。存量案若要维持正式身份，必须重出 ``fig1_legend_receipt.json`` 和
v3 seal；无法重出的只能走带可见水印的 ``legacy-recompile``。
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

SCHEMA="a5-report-seal/v3"
FIG1_LEGEND_NAME="fig1_legend_receipt.json"
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
 # abs 入参为 build_html resolve 后传入的合法调用形态，案根围栏由下方 relative_to 强制；
 # 2026-08-16 用户裁决豁免定性（r10_ledger.md 状态节），审查勿再报收紧候选。
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


def _fig1_expected_from_state(root):
 state=safe_file(root,"analysis-state.json","标准 analysis-state")
 state_obj=json.loads(state.read_text(encoding="utf-8"))
 series=((state_obj.get("camp_share_series") or {}).get("series"))
 if not isinstance(series,dict) or not series:
  raise ValueError("analysis-state 缺 camp_share_series.series，无法重算图 1 实绘集合")
 import standard_charts
 series_format=standard_charts.fig1_series_format(state_obj)
 exemption=standard_charts.fig1_excluded_series(series_format)
 rendered,excluded,rejected=standard_charts.select_fig1_series(series,series_format=series_format)
 if rejected:
  raise ValueError(f"analysis-state 图 1 series 含白名单外键: {rejected}")
 expected_excluded=[{"key":key,"reason":exemption[key]}
                    for key in excluded]
 return state,rendered,expected_excluded,set(exemption)


def _fig1_legend_errors(root,receipt,images):
 """Cross-check the v1 legend receipt against current state and report images."""
 errors=[]
 from figures_from_facts import FIG1_LEGEND_RECEIPT_SCHEMA
 if not isinstance(receipt,dict) or receipt.get("schema")!=FIG1_LEGEND_RECEIPT_SCHEMA:
  return [f"图 1 legend receipt schema 必须是 {FIG1_LEGEND_RECEIPT_SCHEMA}"]
 try:
  state_path,rendered,excluded,excluded_whitelist=_fig1_expected_from_state(root)
 except Exception as exc:
  return [f"图 1 legend 无法从当前 state 重算: {exc}"]

 state_ref=receipt.get("state")
 state_shown=Path(str((state_ref or {}).get("path") or "")) if isinstance(state_ref,dict) else Path("")
 if not isinstance(state_ref,dict) or state_shown.is_absolute() \
       or state_shown.as_posix()!="analysis-state.json":
  errors.append("图 1 legend 未绑定标准 analysis-state.json")
 else:
  if state_ref.get("sha256")!=sha(state_path):
   errors.append("图 1 legend state sha256 与当前 analysis-state.json 不一致")
  if state_ref.get("size")!=state_path.stat().st_size:
   errors.append("图 1 legend state size 与当前 analysis-state.json 不一致")

 png_ref=receipt.get("output_png")
 if not isinstance(png_ref,dict) or not png_ref.get("path"):
  errors.append("图 1 legend 缺 output_png 绑定")
 else:
  shown=Path(str(png_ref["path"]))
  if shown.is_absolute() or shown.name!=shown.as_posix():
   errors.append("图 1 legend output_png.path 必须是 producer 写出的安全 basename")
  candidates=[item for item in images
              if isinstance(item,dict) and Path(str(item.get("path") or "")).name==shown.name]
  if len(candidates)!=1:
   errors.append("图 1 legend 绑定的 PNG 不属于报告 images 唯一集合")
  else:
   current=candidates[0]
   if png_ref.get("sha256")!=current.get("sha256"):
    errors.append("图 1 legend PNG sha256 与当前报告 PNG 不一致")
   if png_ref.get("size")!=current.get("size"):
    errors.append("图 1 legend PNG size 与当前报告 PNG 不一致")

 if receipt.get("rendered_camps")!=rendered:
  errors.append(f"图 1 legend rendered_camps 与当前 state 重算不一致（期望 {rendered}）")
 declared_excluded=receipt.get("excluded_series")
 if not isinstance(declared_excluded,list):
  errors.append("图 1 legend excluded_series 必须是列表")
 else:
  outside=[row.get("key") if isinstance(row,dict) else f"<non-object:{i}>"
           for i,row in enumerate(declared_excluded)
           if not isinstance(row,dict) or row.get("key") not in excluded_whitelist]
  if outside:
   errors.append(f"图 1 legend 排除键超出 FIG1_EXCLUDED_SERIES 白名单: {outside}")
  if declared_excluded!=excluded:
   errors.append(f"图 1 legend excluded_series 与当前 state 重算不一致（期望 {excluded}）")

 overlays=receipt.get("overlays")
 if not isinstance(overlays,list):
  errors.append("图 1 legend overlays 必须是列表")
 else:
  for i,row in enumerate(overlays):
   if not isinstance(row,dict) or set(row)!={"label","camps"}:
    errors.append(f"图 1 legend overlay[{i}] 必须只含 label/camps")
    continue
   camps=row.get("camps")
   if not isinstance(row.get("label"),str) or not row["label"].strip() \
          or not isinstance(camps,list) or not camps or len(camps)!=len(set(camps)):
    errors.append(f"图 1 legend overlay[{i}] 标签或组成 camps 非法")
    continue
   outside=[camp for camp in camps if camp not in rendered]
   if outside:
    errors.append(f"图 1 legend overlay[{i}] 含当前 state 非实绘 camp: {outside}")
 return errors


def fig1_legend_bundle(root,a4obj,images):
 """Freeze the receipt for new analysis; record structured N/A for audits."""
 workflow=a4obj.get("workflow_type")
 if workflow=="independent-audit":
  return {"status":"NOT_APPLICABLE",
          "reason":"independent-audit profile does not require figure 1 legend receipt"}
 if workflow!="new-analysis": raise ValueError("A4 workflow_type 非法")
 receipt=safe_file(root,FIG1_LEGEND_NAME,"图 1 legend receipt")
 obj=json.loads(receipt.read_text(encoding="utf-8"))
 errors=_fig1_legend_errors(root,obj,images)
 if errors: raise ValueError("图 1 legend receipt 交叉核对失败: "+"; ".join(errors))
 return entry(root,receipt)


def _disclosure_slice(report_text,locations):
 """F-D1：report_locations 的消费者——把披露核对锚定到收据声明的章节切片。

 约定：每个 location 串必须命中报告中某一行 Markdown 标题（该行含此子串）；
 切片＝命中标题行至下一个任意级标题行之前。返回 (切片文本, 命中的 location)。
 一个 location 都定位不到＝收据声称的披露位置在报告中不存在，拒。"""
 lines=report_text.splitlines()
 heads=[(i,line) for i,line in enumerate(lines) if re.match(r"^#{1,6}\s",line)]
 for loc in locations:
  needle=str(loc).strip()
  if not needle: continue
  # 容忍 "report.md §xx" 形态：取最后一个空格后的段名再试一次
  candidates=[needle]
  if " " in needle: candidates.append(needle.rsplit(" ",1)[-1])
  for cand in candidates:
   for pos,(i,line) in enumerate(heads):
    if cand and cand in line:
     end=heads[pos+1][0] if pos+1<len(heads) else len(lines)
     return "\n".join(lines[i:end]),loc
 raise ValueError(f"flip 披露位置在报告中不存在（report_locations={locations!r} 未命中任何 Markdown 标题行）")


def provenance_flip_bundle(root,report_text,a4obj):
 """F-06 批 D（消化轮 1 强化）：溯源翻转披露锚定核对＋ledger/freeze/收据三方绑定（new-analysis）。

 ①entity_freeze 记录了 provenance_ledger_sha256 时，案根 ledger 必须在场且哈希一致
 （封死**单边改动**——改/删 ledger 而 freeze 记录在场必拒；freeze 自身无上位 sha 锚，
 "连 freeze 一起改写"属批 C 终验定性的自洽小件残余边界，见 scan-schemas §13 与 r10 台账）。
 ②ledger 存在真实翻转锚点时：收据按 **ledger input_binding 绑定的那份**定位（path＋sha
 三验，与 freeze 前置 3 同一实物——F-D7 封"甲收据过 freeze、乙收据过 A5"）；披露核对
 锚定到 report_locations 声明的章节切片内（F-D1）：该切片须同时含三策略名、每策略的
 top 终点标识串与份额数字——同段并列披露，全文他处的偶然同串不作数。"""
 if a4obj.get("workflow_type")!="new-analysis":
  return {"status":"NOT_APPLICABLE","reason":"independent-audit 单段流程暂不承载溯源披露链"}
 import handoff_manifest
 ledger_path=Path(root)/"provenance_ledger.json"
 freeze_path=Path(root)/"entity_freeze.json"
 recorded=None
 if freeze_path.is_file() and not freeze_path.is_symlink():
  freeze=json.loads(freeze_path.read_text(encoding="utf-8"))
  recorded=freeze.get("provenance_ledger_sha256")
 if recorded:
  if not ledger_path.is_file() or ledger_path.is_symlink():
   raise ValueError("entity_freeze 记录了 provenance_ledger_sha256 但案根 ledger 缺失——freeze 后删/换 ledger 的单边改动拒绝")
  _,actual,_=handoff_manifest.sha256_file(ledger_path)
  if actual!=recorded:
   raise ValueError("provenance_ledger.json 与 entity_freeze 记录的哈希不一致——freeze 后换 ledger 拒绝")
 if not ledger_path.is_file():
  return {"status":"NO_LEDGER"}
 pl=json.loads(ledger_path.read_text(encoding="utf-8"))
 if pl.get("schema")!="provenance-ledger/v2":
  raise ValueError(f"provenance_ledger schema 非法: {pl.get('schema')!r}")
 real=handoff_manifest.ledger_real_flips(pl)
 if not real:
  return {"status":"NO_FLIPS","ledger":entry(root,ledger_path)}
 # F-D7：收据实物＝ledger input_binding 绑定的那份（path 相对案根解析＋sha/size 三验），
 # 不再硬编码案根文件名——与 freeze 前置 3 消费同一实物，改名案不误伤、换收据必失配。
 flips_ref=((pl.get("input_binding") or {}).get("algorithm_params") or {}).get("flip_adjudications")
 if not isinstance(flips_ref,dict) or not flips_ref.get("path"):
  raise ValueError("溯源存在真实翻转锚点但 ledger input_binding 未绑定 flip-adjudications 裁决收据"
                   "（须 --acknowledge-flip <收据> 重跑 trace）")
 shown=Path(str(flips_ref["path"]))
 receipt_path=(shown if shown.is_absolute() else Path(root)/shown).resolve()
 try: receipt_path.relative_to(Path(root).resolve())
 except ValueError as exc:
  raise ValueError("ledger 绑定的 flip 裁决收据不在案根内") from exc
 if receipt_path.is_symlink() or not receipt_path.is_file():
  raise ValueError("ledger 绑定的 flip 裁决收据实物缺失或非普通文件")
 _,receipt_sha,receipt_size=handoff_manifest.sha256_file(receipt_path)
 if receipt_sha!=flips_ref.get("sha256") or receipt_size!=flips_ref.get("bytes"):
  raise ValueError("flip 裁决收据实物与 ledger 绑定的 sha256/size 不符（换收据/改写后必须重跑 trace）")
 entity_ref=(pl.get("input_binding") or {}).get("entity_file") or {}
 entity_rel=entity_ref.get("path")
 current_entity=None
 if isinstance(entity_rel,str) and entity_rel:
  cand=Path(entity_rel)
  cand=cand if cand.is_absolute() else Path(root)/cand
  if cand.is_file(): current_entity=cand
 _,rows=handoff_manifest.load_flip_adjudications(receipt_path,current_entity_file=current_entity)
 fails=handoff_manifest.verify_flip_receipt_against_ledger(rows,real)
 if fails:
  raise ValueError("flip 裁决收据与 ledger 明细对账失败: "+"; ".join(fails))
 anchors=[]
 for key in sorted(real):
  info=real[key]
  row=rows.get(key) or {}
  locations=((row.get("disclosure") or {}).get("report_locations")) or []
  section,matched_loc=_disclosure_slice(report_text,locations)
  for policy in handoff_manifest.FLIP_POLICIES:
   terminal=info["tops"].get(policy) or []
   share=info["shares"].get(policy)
   ident=str(terminal[2] if len(terminal)>2 and terminal[2] else (terminal[1] if len(terminal)>1 else ""))
   if not ident:
    raise ValueError(f"翻转锚点 {key} {policy} top 终点无可核标识串")
   # F-D1：三项都必须落在**同一披露切片**内——策略名（并列披露的骨架）、终点标识、份额。
   # N-D1：策略名按中英文别名族匹配（pro_rata|按比例 等），中文真实披露写法不误伤。
   aliases=handoff_manifest.FLIP_POLICY_ALIASES.get(policy,(policy,))
   if not any(alias in section for alias in aliases):
    raise ValueError(f"报告披露段（{matched_loc}）缺策略名 {policy}"
                     f"（可写 {' / '.join(aliases)} 任一）: {key[0]} {key[1]} 须按多策略并列披露")
   if ident not in section:
    raise ValueError(f"报告披露段（{matched_loc}）缺 {policy} 终点标识 {ident!r}: {key[0]} {key[1]}")
   if share and share not in section:
    raise ValueError(f"报告披露段（{matched_loc}）缺 {policy} 份额数字 {share!r}: {key[0]} {key[1]}")
  anchors.append({"entity_id":key[0],"anchor":key[1],"flip_fingerprint":info["fingerprint"],
                  "report_location":matched_loc})
 return {"status":"DISCLOSED","ledger":entry(root,ledger_path),
         "receipt":entry(root,receipt_path),"anchors":anchors}


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
 payload={"schema":SCHEMA,"status":"PASS","producer":"a5_report_seal.py/v3",
  "chain":a4obj.get("chain"),"workflow_type":a4obj.get("workflow_type"),
  "a4_seal":entry(root,a4),
  "report":entry(root,report),"images":images,
  "fig1_legend_receipt":fig1_legend_bundle(root,a4obj,images),
  "distribution":distribution_bundle(root,report,a4obj),
  "provenance_flips":provenance_flip_bundle(root,report.read_text(encoding="utf-8"),a4obj)}
 target=Path(out).resolve()
 if target.parent!=root: raise ValueError("A5 seal 必须写在案目录根")
 target.parent.mkdir(parents=True,exist_ok=True); tmp=target.with_name(f".{target.name}.tmp.{os.getpid()}")
 with tmp.open("x") as f: json.dump(payload,f,ensure_ascii=False,indent=2); f.write("\n"); f.flush(); os.fsync(f.fileno())
 os.replace(tmp,target); return payload


def validate_seal(seal_path,report_path,a4_path):
 errors=[]
 try:
  seal=Path(seal_path).resolve(); root=seal.parent; d=json.loads(seal.read_text()); report=safe_file(root,report_path,"Markdown"); a4=safe_file(root,a4_path,"A4 seal")
  if d.get("schema")!=SCHEMA or d.get("status")!="PASS" \
       or d.get("producer")!="a5_report_seal.py/v3":
   return ["A5 report seal schema/status/producer 非 v3 PASS"]
  a4obj=json.loads(a4.read_text())
  if d.get("chain")!=a4obj.get("chain"): errors.append("A5 seal chain 未绑定当前 A4 seal")
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
   actual_legend=fig1_legend_bundle(root,a4obj,d.get("images",[]))
   if d.get("fig1_legend_receipt")!=actual_legend:
    errors.append("A5 seal 图 1 legend receipt 实物绑定变化")
  except Exception as exc: errors.append(f"A5 seal 图 1 legend receipt 不可重验: {exc}")
  try:
   actual_distribution=distribution_bundle(root,report,a4obj)
   if d.get("distribution")!=actual_distribution: errors.append("A5 seal 分布终态绑定变化")
  except Exception as exc: errors.append(f"A5 seal 分布终态不可重验: {exc}")
  try:
   actual_flips=provenance_flip_bundle(root,report.read_text(encoding="utf-8"),a4obj)
   if d.get("provenance_flips")!=actual_flips: errors.append("A5 seal 溯源翻转披露绑定变化")
  except Exception as exc: errors.append(f"A5 seal 溯源翻转披露不可重验: {exc}")
 except Exception as exc: errors.append(f"A5 report seal 不可验证: {exc}")
 return errors


def main(argv=None):
 ap=argparse.ArgumentParser(); ap.add_argument("--case-dir",required=True); ap.add_argument("--report",required=True); ap.add_argument("--a4-seal",required=True); ap.add_argument("--out",required=True); a=ap.parse_args(argv)
 try: create_seal(a.case_dir,a.report,a.a4_seal,a.out)
 except Exception as exc: ap.exit(2,f"BLOCK: {exc}\n")
 return 0
if __name__=="__main__": raise SystemExit(main())
