"""r3：仅读取四份既有账本，按实体边数和供应量精确复算新界；不运行 trace。"""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
GAP = ("UNRESOLVED", "data_gap", None)
RES = ("UNRESOLVED", "fp_residual", None)
DENOMINATOR = 2 ** 52
POLICIES = {"pro_rata", "fifo", "lifo"}


def rawmap(rows, policy=False):
    values = {}
    for row in rows:
        key = tuple(row["terminal"]) if policy else (row["kind"], row["subkind"], row["via"])
        assert key not in values, key
        values[key] = int(row["raw"])
    return values


def compare(before, after, bound_numerator):
    delta = after.get(GAP, 0) + after.get(RES, 0) - before.get(GAP, 0)
    checks = {
        "nongap_equal": {k: v for k, v in before.items() if k not in (GAP, RES)} ==
                        {k: v for k, v in after.items() if k not in (GAP, RES)},
        "within_r3_bound": abs(delta) * DENOMINATOR <= bound_numerator,
        "observed_sum_delta_zero": sum(after.values()) == sum(before.values()),
    }
    assert all(checks.values()), (delta, checks)
    return {"old_sum_raw": str(sum(before.values())), "new_sum_raw": str(sum(after.values())),
            "old_gap_raw": str(before.get(GAP, 0)), "new_gap_raw": str(after.get(GAP, 0)),
            "fp_residual_raw": str(after.get(RES, 0)), "gap_delta_raw": str(delta), "checks": checks}


old_code = subprocess.check_output(
    ["git", "show", "3b29e38:scripts/report/entity_source_trace.py"], cwd=ROOT)
algorithm_hashes = [hashlib.sha256(old_code).hexdigest(),
                    hashlib.sha256((ROOT / "scripts/report/entity_source_trace.py").read_bytes()).hexdigest()]
assert algorithm_hashes[1] == "e85acee4e9a98a664d9b4881ca33177003aa9455261109a01e111e6faeda3cd1"
frozen = json.loads((OUT / "scope_before_r3.json").read_text())["ledgers"]
cases = {}
for case, paths, count in (
    ("APU", [".staging_eps/apu/provenance_ledger.json", ".staging_eps/apu/provenance_ledger_704.json"], 105),
    ("PYTHIA", [f".staging_eps/pythia/t7_compare/ledger_{v}.json" for v in (703, 704)], 7),
):
    blobs = [(ROOT / name).read_bytes() for name in paths]
    hashes = [hashlib.sha256(blob).hexdigest() for blob in blobs]
    assert hashes == [frozen[name] for name in paths]
    old, new = [json.loads(blob) for blob in blobs]
    assert [ledger["input_binding"]["algorithm"]["script_sha256"] for ledger in (old, new)] == algorithm_hashes
    bindings = {key: old["input_binding"][key] == new["input_binding"][key]
                for key in ("source", "entity_file", "labels_file", "handoff_manifest", "data_map", "total_supply_raw")}
    assert all(bindings.values()), bindings
    supply = int(new["input_binding"]["total_supply_raw"])
    assert supply > 0
    a, b = [{e["entity_id"]: e for e in ledger["entities"]} for ledger in (old, new)]
    assert len(old["entities"]) == len(new["entities"]) == len(a) == len(b) == count
    assert a.keys() == b.keys()
    rows = []
    for eid in sorted(a):
        n = a[eid]["simulation"]["edges_simulated"]
        assert isinstance(n, int) and n >= 0 and n == b[eid]["simulation"]["edges_simulated"]
        numerator = 4 * n * supply + 2 * DENOMINATOR
        for anchor in ("current", "peak"):
            x, y = a[eid]["anchors"][anchor], b[eid]["anchors"][anchor]
            assert x["stock_raw"] == y["stock_raw"]
            pct0, pct1 = [e["closure_check"][f"{anchor}_sum_pct"] for e in (a[eid], b[eid])]
            assert pct0 == pct1
            row = {"entity_id": eid, "anchor": anchor, "stock_raw": x["stock_raw"],
                   "stock_equal": True, "closure_pct_equal": True, "closure_pct": pct0,
                   "n": n, "total_supply_raw": str(supply), "bound_numerator": str(numerator),
                   "bound_denominator": str(DENOMINATOR),
                   "composition": compare(rawmap(x["composition"]), rawmap(y["composition"]), numerator)}
            pd0, pd1 = [ledger["bounds_sensitivity"]["per_entity"][eid]["anchors"].get(anchor, {}).get("policy_details", {})
                        for ledger in (old, new)]
            assert pd0.keys() == pd1.keys() == (POLICIES if int(x["stock_raw"]) > 0 else set())
            row["policies"] = {p: compare(rawmap(pd0[p], True), rawmap(pd1[p], True), numerator)
                               for p in sorted(pd0)}
            rows.append(row)
    unchanged = hashes == [hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in paths]
    assert unchanged
    comparisons = [r["composition"] for r in rows] + [p for r in rows for p in r["policies"].values()]
    summary = {"entities": count, "anchors": len(rows), "zero_sum_delta_anchors": len(rows),
               "policy_comparisons": sum(len(r["policies"]) for r in rows),
               "max_abs_delta_raw": max(abs(int(c["gap_delta_raw"])) for c in comparisons),
               "out_of_bound_count": 0, "failures": 0,
               "n_min": min(r["n"] for r in rows), "n_max": max(r["n"] for r in rows)}
    cases[case] = {"summary": summary, "input_binding_equal": bindings, "ledger_files_unchanged": unchanged,
                   "inputs": [{"path": name, "sha256": sha} for name, sha in zip(paths, hashes)], "rows": rows}
    print(case, json.dumps(summary, ensure_ascii=False))
assert sum(c["summary"]["anchors"] for c in cases.values()) == 224
assert sum(c["summary"]["policy_comparisons"] for c in cases.values()) == 666
report = {"status": "PASS", "bound": "abs(delta) * 2**52 <= 4 * n * S + 2 * 2**52",
          "n_source": "per-entity simulation.edges_simulated, equal across both existing ledgers",
          "shortfall_scope": "Existing ledgers do not contain per-edge shortfall traces; those are tested in T4.",
          "cases": cases}
(OUT / "ledger_recheck_r3.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
