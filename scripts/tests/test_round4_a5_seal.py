#!/usr/bin/env python3
import json,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent; sys.path.insert(0,str(HERE.parent/"report"))
def main():
 from a5_report_seal import create_seal, validate_seal
 with tempfile.TemporaryDirectory() as td:
  d=Path(td); (d/"charts/final").mkdir(parents=True)
  (d/"a4_seal.json").write_text(json.dumps({"schema":"a4-seal/v4","verdict":"PASS",
      "workflow_type":"independent-audit","revision":1,"previous_seal":None,
      "charts_dir":"charts/final","claims":[{"id":"C1"}]}))
  (d/"charts/final/x.png").write_bytes(b"png")
  report=d/"report.md"; report.write_text("# R\n![x](charts/final/x.png)\n")
  seal=d/"a5_report_seal.json"; create_seal(d,report,d/"a4_seal.json",seal)
  assert not validate_seal(seal,report,d/"a4_seal.json")
  original=json.loads(seal.read_text()); old=dict(original); old["schema"]="a5-report-seal/v1"
  seal.write_text(json.dumps(old)); assert any("schema" in x for x in validate_seal(seal,report,d/"a4_seal.json"))
  seal.write_text(json.dumps(original))
  a4_original=json.loads((d/"a4_seal.json").read_text()); a4_old=dict(a4_original); a4_old["schema"]="a4-seal/v3"
  (d/"a4_seal.json").write_text(json.dumps(a4_old))
  assert any("a4-seal/v4" in x or "A4" in x for x in validate_seal(seal,report,d/"a4_seal.json"))
  (d/"a4_seal.json").write_text(json.dumps(a4_original))
  report.write_text("swapped")
  assert any("Markdown" in x for x in validate_seal(seal,report,d/"a4_seal.json"))
  report.write_text("# R\n![x](charts/final/x.png)\n"); (d/"charts/final/x.png").write_bytes(b"tamper")
  assert any("图" in x for x in validate_seal(seal,report,d/"a4_seal.json"))
 print("PASS: A5 seal binds A4, Markdown and every report image")
 return 0
if __name__=="__main__": raise SystemExit(main())
