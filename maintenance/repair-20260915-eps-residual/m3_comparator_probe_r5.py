"""r5 M3 comparator probe: move raw between unresolved keys while holding totals fixed."""
import contextlib
import copy
import importlib.util
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts/tests"))
BEFORE = json.loads((OUT / "scope_before_r5.json").read_text())


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    model = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(model)
    return model


models = [load("before_r5", Path(BEFORE["baseline_copy_dir"]) / "scripts/tests/test_entity_source_trace.py"),
          load("after_r5", ROOT / "scripts/tests/test_entity_source_trace.py")]
policies = ("pro_rata", "fifo", "lifo")
subkinds = ("order_ambiguous", "depth_limit", "budget_truncated", "facility_candidate")


def ledger(parts):
    composition = [{"kind": "UNRESOLVED", "subkind": subkind, "via": via, "raw": str(raw)}
                   for subkind, via, raw in parts]
    details = [{"terminal": [c["kind"], c["subkind"], c["via"]], "raw": c["raw"]} for c in composition]
    return {"input_binding": {"total_supply_raw": "1000000"},
            "test_shortfalls": {p: [] for p in policies},
            "entities": [{"entity_id": "D", "anchors": {a: {"stock_raw": "1000", "composition": copy.deepcopy(composition)}
                          for a in ("current", "peak")}, "closure_check": {"current_sum_pct": 100.0, "peak_sum_pct": 100.0}}],
            "bounds_sensitivity": {"per_entity": {"D": {"anchors": {a: {"policy_details": {p: copy.deepcopy(details) for p in policies}}
                                    for a in ("current", "peak")}}}}}


def compare(model, old, new, name):
    model.FAILS.clear()
    measurements = []
    with contextlib.redirect_stdout(io.StringIO()):
        model.eps_compare_quantities(old, new, name, [(86400, "X", "D", 1000)],
                                     expect_equal=False, measurements=measurements)
    return {"accepted": not model.FAILS, "failed_assertions": list(model.FAILS),
            "bounded_unresolved_comparisons": sum(r["category"] == "unresolved_key" and r["bound_checked"] for r in measurements),
            "migration_records": sum(not r["bound_checked"] for r in measurements)}


results = []
for i, subkind in enumerate(subkinds):
    partner = subkinds[(i + 1) % len(subkinds)]
    for delta in (2, 3, -3):
        old = ledger([(subkind, "A", 500), (partner, "B", 500)])
        new = ledger([(subkind, "A", 500 + delta), (partner, "B", 500 - delta)])
        name = f"{subkind} delta={delta}"
        before, after = [compare(model, old, new, name) for model in models]
        assert before["accepted"], (name, "baseline should reproduce missing per-key check")
        assert after["accepted"] == (abs(delta) <= 2), (name, after)
        assert after["bounded_unresolved_comparisons"] == 16 and after["migration_records"] == 0
        results.append({"case": name, "expected_acceptance": abs(delta) <= 2, "before": before, "after": after})
old = ledger([("data_gap", None, 1000)])
new = ledger([("data_gap", None, 0), ("fp_residual", None, 1000)])
for model in models:
    result = compare(model, old, new, "gap/residual label migration")
    assert result["accepted"] and result["migration_records"] == 16
results.append({"case": "gap/residual label migration", "after": result})
print(json.dumps({"status": "PASS", "scope": "synthetic comparator acceptance/rejection probe; injected out-of-bound inputs are expected rejections", "bound_raw": "2 + 4000000/2**52", "cases": results}, ensure_ascii=False, indent=2))
