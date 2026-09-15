"""只读复现 r4 原始标签逐键超界；重放最终压力测试的最大见证，退出 1 表示超界。"""
import hashlib
import importlib.util
import json
import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "scripts/tests"))
spec = importlib.util.spec_from_file_location("r4_replay", ROOT / "scripts/tests/test_entity_source_trace.py")
test = importlib.util.module_from_spec(spec)
spec.loader.exec_module(test)
receipt = json.loads((OUT / "t4_stress_summary_r4.json").read_text())
log = (OUT / receipt["source_log"]).read_bytes()
assert hashlib.sha256(log).hexdigest() == receipt["log_sha256"]
assert hashlib.sha256((ROOT / "scripts/tests/test_entity_source_trace.py").read_bytes()).hexdigest() == receipt["test_sha256"]
assert hashlib.sha256((ROOT / "scripts/report/entity_source_trace.py").read_bytes()).hexdigest() == "e85acee4e9a98a664d9b4881ca33177003aa9455261109a01e111e6faeda3cd1"
summary = receipt["summary"]
witness = summary["by_class"]["unresolved_key"]["max_witnesses"][0]
inputs = [json.loads(line[len("T4-stress failing input "):]) for line in log.decode().splitlines()
          if line.startswith("T4-stress failing input ")]
case = next(row for row in inputs if row["case"] == witness["case"])
edges, supply = case["edges"], int(summary["total_supply_raw"])
ledgers = [test.eps_memory_trace(model, edges, supply) for model in test.eps_models()]
bound = Fraction(4 * len(edges) * supply, 2 ** 52) + 2
rows = []
for anchor in ("current", "peak"):
    for policy in ("pro_rata", "fifo", "lifo"):
        maps = [{tuple(r["terminal"]): int(r["raw"]) for r in ledger["bounds_sensitivity"]
                 ["per_entity"]["D"]["anchors"][anchor]["policy_details"][policy]} for ledger in ledgers]
        gap, residual = ("UNRESOLVED", "data_gap", None), ("UNRESOLVED", "fp_residual", None)
        delta = maps[1].get(gap, 0) - maps[0].get(gap, 0)
        rows.append({"anchor": anchor, "policy": policy,
                     "gap_raw_703_704": [m.get(gap, 0) for m in maps],
                     "residual_raw_703_704": [m.get(residual, 0) for m in maps],
                     "original_gap_delta": delta, "original_gap_within_bound": abs(delta) <= bound,
                     "aligned_unresolved_delta": maps[1].get(gap, 0) + maps[1].get(residual, 0) - maps[0].get(gap, 0),
                     "stock_raw_703_704": [l["entities"][0]["anchors"][anchor]["stock_raw"] for l in ledgers]})
print(json.dumps({"case": case["case"], "edges": edges, "supply_raw": str(supply), "n": len(edges),
                  "bound_raw": str(bound), "rows": rows}, ensure_ascii=False, indent=2))
sys.exit(int(any(not row["original_gap_within_bound"] for row in rows)))
