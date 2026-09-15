"""只读复算四份既有账本；核对 Fable 全套日志并更新其结果 JSON，不运行 trace/run_all。"""
import ast
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
GAP = ("UNRESOLVED", "data_gap", None)
RES = ("UNRESOLVED", "fp_residual", None)
POLICIES = {"pro_rata", "fifo", "lifo"}


def rawmap(rows, policy=False):
    values = {}
    for row in rows:
        key = tuple(row["terminal"]) if policy else (row["kind"], row["subkind"], row["via"])
        assert key not in values, key
        values[key] = int(row["raw"])
    return values


def compare(before, after):
    delta = after.get(GAP, 0) + after.get(RES, 0) - before.get(GAP, 0)
    checks = {
        "nongap_equal": {k: v for k, v in before.items() if k not in (GAP, RES)} ==
                        {k: v for k, v in after.items() if k not in (GAP, RES)},
        "bounded_gap_delta": 0 <= delta <= after.get(RES, 0),
        "observed_sum_delta_zero": sum(after.values()) - sum(before.values()) == 0,
    }
    assert all(checks.values()), checks
    return {"old_sum_raw": str(sum(before.values())), "new_sum_raw": str(sum(after.values())),
            "old_gap_raw": str(before.get(GAP, 0)), "new_gap_raw": str(after.get(GAP, 0)),
            "fp_residual_raw": str(after.get(RES, 0)), "gap_delta_raw": str(delta),
            "sum_delta_raw": str(sum(after.values()) - sum(before.values())), "checks": checks}


old_code = subprocess.check_output(
    ["git", "show", "3b29e38:scripts/report/entity_source_trace.py"], cwd=ROOT)
algorithm_hashes = [hashlib.sha256(old_code).hexdigest(),
                    hashlib.sha256((ROOT / "scripts/report/entity_source_trace.py").read_bytes()).hexdigest()]
cases = {}
for case, paths, count in (
    ("APU", [".staging_eps/apu/provenance_ledger.json", ".staging_eps/apu/provenance_ledger_704.json"], 105),
    ("PYTHIA", [f".staging_eps/pythia/t7_compare/ledger_{v}.json" for v in (703, 704)], 7),
):
    blobs = [(ROOT / name).read_bytes() for name in paths]
    hashes = [hashlib.sha256(blob).hexdigest() for blob in blobs]
    old, new = [json.loads(blob) for blob in blobs]
    assert [x["input_binding"]["algorithm"]["script_sha256"] for x in (old, new)] == algorithm_hashes
    bindings = {key: old["input_binding"][key] == new["input_binding"][key]
                for key in ("source", "entity_file", "labels_file", "handoff_manifest", "data_map", "total_supply_raw")}
    assert all(bindings.values()), bindings
    a, b = [{e["entity_id"]: e for e in ledger["entities"]} for ledger in (old, new)]
    assert len(old["entities"]) == len(new["entities"]) == len(a) == len(b) == count
    assert a.keys() == b.keys()
    rows = []
    for eid in sorted(a):
        for anchor in ("current", "peak"):
            x, y = a[eid]["anchors"][anchor], b[eid]["anchors"][anchor]
            assert x["stock_raw"] == y["stock_raw"]
            row = {"entity_id": eid, "anchor": anchor, "stock_raw": x["stock_raw"],
                   "stock_equal": True, "composition": compare(rawmap(x["composition"]), rawmap(y["composition"]))}
            pd0, pd1 = [ledger["bounds_sensitivity"]["per_entity"][eid]["anchors"].get(anchor, {}).get("policy_details", {})
                        for ledger in (old, new)]
            assert pd0.keys() == pd1.keys() == (POLICIES if int(x["stock_raw"]) > 0 else set())
            row["policies"] = {p: compare(rawmap(pd0[p], True), rawmap(pd1[p], True)) for p in sorted(pd0)}
            row["policy_details_changed"] = pd0 != pd1
            row["old_policy_had_gap"] = any(GAP in rawmap(values, True) for values in pd0.values())
            rows.append(row)
    unchanged = hashes == [hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in paths]
    assert unchanged
    summary = {"entities": count, "anchors": len(rows), "zero_sum_delta_anchors": len(rows),
               "policy_comparisons": sum(len(r["policies"]) for r in rows), "failures": 0,
               "policy_details_changed_anchors": sum(r["policy_details_changed"] for r in rows),
               "changed_anchors_all_had_old_gap": all(r["old_policy_had_gap"] for r in rows if r["policy_details_changed"])}
    cases[case] = {"summary": summary, "input_binding_equal": bindings, "ledger_files_unchanged": unchanged,
                   "inputs": [{"path": name, "sha256": sha} for name, sha in zip(paths, hashes)], "rows": rows}
    print(case, json.dumps(summary, ensure_ascii=False))
assert sum(c["summary"]["anchors"] for c in cases.values()) == 224
assert cases["APU"]["summary"]["policy_details_changed_anchors"] == 118
assert cases["APU"]["summary"]["changed_anchors_all_had_old_gap"]
(OUT / "ledger_recheck_r2.json").write_text(json.dumps({"status": "PASS", "cases": cases}, ensure_ascii=False, indent=2) + "\n")

# 只解析 SUITE 的字面赋值，不 import 或执行 run_all.py。
suite = []
for node in ast.parse((ROOT / "scripts/tests/run_all.py").read_text()).body:
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "SUITE" for t in node.targets):
        suite = ast.literal_eval(node.value)
    elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) and node.target.id == "SUITE":
        assert isinstance(node.op, ast.Add)
        suite += ast.literal_eval(node.value)
expected = [item[0] if isinstance(item, list) else item for item in suite]
log_path = OUT / "run_all_fable.log"
log_bytes = log_path.read_bytes()
log = log_bytes.decode()
passed = re.findall(r"^\s+PASS\s+(\S+\.py)", log, re.M)
failed = re.findall(r"^\s*FAIL(?:\(rc=[^)]+\))?\s+(\S+\.py)", log, re.M)
assert passed == expected and len(passed) == 147 and not failed
assert log.strip().splitlines()[-1] == "全部通过"
result = json.loads((OUT / "run_all_fable_result.json").read_text())
result.update(status="PASS", passed=147, failed=0, log_file=str(log_path.relative_to(ROOT)),
              checked_at_utc=datetime.now(timezone.utc).isoformat(), exit_code=None,
              log_sha256=hashlib.sha256(log_bytes).hexdigest(), suite_order_matches=True,
              note="r2 只读核对调度方已提供的沙箱外日志：SUITE 顺序一致，147 PASS、0 FAIL，末行为全部通过。日志未单列进程退出码；本轮未重跑全套。")
result.update({"pass": 147, "fail": 0, "log": "run_all_fable.log"})
(OUT / "run_all_fable_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print("F3 PASS: 147 PASS, 0 FAIL; SUITE order matches; existing log only")
