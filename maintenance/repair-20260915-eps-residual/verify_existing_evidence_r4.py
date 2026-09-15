"""r4：只读四份账本的 224 锚点全部键；独立有理数判界，不运行 APU/PYTHIA trace。"""
import hashlib
import json
import subprocess
import sys
from fractions import Fraction
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


def measurement(delta, numerator):
    return {"delta": str(delta), "within_bound": abs(delta) * DENOMINATOR <= numerator}


def compare(before, after, numerator, stock):
    key_rows = []
    for key in sorted(before.keys() | after.keys(), key=str):
        a, b = before.get(key, 0), after.get(key, 0)
        key_rows.append({"key": key, "old_raw": str(a), "new_raw": str(b),
                         **measurement(b - a, numerator)})
    # 原始 gap/residual 标签迁移单列；对齐来源数量时把新版 residual 合入 gap。
    # 原始每条 raw 和合桶后每条 raw 都判界，不用合计代替逐键检查。
    assert RES not in before
    aligned = dict(after)
    if RES in aligned:
        aligned[GAP] = aligned.get(GAP, 0) + aligned.pop(RES)
    aligned_rows = [{"key": key, **measurement(aligned.get(key, 0) - before.get(key, 0), numerator)}
                    for key in sorted(before.keys() | aligned.keys(), key=str)]
    sum_delta = sum(after.values()) - sum(before.values())
    raw_pct = Fraction(sum_delta * 100, stock) if stock > 0 else None
    return {"old_sum_raw": str(sum(before.values())), "new_sum_raw": str(sum(after.values())),
            "keys": key_rows, "aligned_keys": aligned_rows,
            "unresolved_total": measurement(after.get(GAP, 0) + after.get(RES, 0) - before.get(GAP, 0), numerator),
            "sum_raw": measurement(sum_delta, numerator),
            "closure_pct": {"delta": str(raw_pct) if raw_pct is not None else None,
                            "applicable": stock > 0,
                            "within_bound": (abs(raw_pct) * stock * DENOMINATOR <= numerator * 100)
                            if stock > 0 else None}}


def summarize_measurements(rows):
    return {"comparisons": len(rows),
            "max_abs_delta": str(max((abs(Fraction(r["delta"])) for r in rows), default=Fraction(0))),
            "changed_count": sum(Fraction(r["delta"]) != 0 for r in rows),
            "out_of_bound_count": sum(not r["within_bound"] for r in rows)}


old_code = subprocess.check_output(["git", "show", "3b29e38:scripts/report/entity_source_trace.py"], cwd=ROOT)
algorithm_hashes = [hashlib.sha256(old_code).hexdigest(),
                    hashlib.sha256((ROOT / "scripts/report/entity_source_trace.py").read_bytes()).hexdigest()]
assert algorithm_hashes[1] == "e85acee4e9a98a664d9b4881ca33177003aa9455261109a01e111e6faeda3cd1"
frozen = json.loads((OUT / "scope_before_r4.json").read_text())["ledgers"]
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
            stock = int(x["stock_raw"])
            pct0, pct1 = [Fraction(str(e["closure_check"][f"{anchor}_sum_pct"])) for e in (a[eid], b[eid])]
            pct_delta = pct1 - pct0
            row = {"entity_id": eid, "anchor": anchor, "stock_raw_703_704": [x["stock_raw"], y["stock_raw"]],
                   "stock_equal": x["stock_raw"] == y["stock_raw"],
                   "display_pct": {"delta": str(pct_delta), "applicable": stock > 0,
                                   "within_bound": abs(pct_delta) * stock * DENOMINATOR <= numerator * 100
                                   if stock > 0 else None},
                   "n": n, "total_supply_raw": str(supply), "bound_numerator": str(numerator),
                   "bound_denominator": str(DENOMINATOR),
                   "composition": compare(rawmap(x["composition"]), rawmap(y["composition"]), numerator, stock)}
            pd0, pd1 = [ledger["bounds_sensitivity"]["per_entity"][eid]["anchors"].get(anchor, {}).get("policy_details", {})
                        for ledger in (old, new)]
            assert pd0.keys() == pd1.keys() == (POLICIES if stock > 0 else set())
            row["policies"] = {p: compare(rawmap(pd0[p], True), rawmap(pd1[p], True), numerator, stock)
                               for p in sorted(pd0)}
            rows.append(row)
    unchanged = hashes == [hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in paths]
    assert unchanged
    comparisons = [r["composition"] for r in rows] + [p for r in rows for p in r["policies"].values()]
    keys = [key for c in comparisons for key in c["keys"]]
    by_class = {
        "all_original_keys": summarize_measurements(keys),
        "non_unresolved_key": summarize_measurements([r for r in keys if r["key"][0] != "UNRESOLVED"]),
        "unresolved_key": summarize_measurements([r for r in keys if r["key"][0] == "UNRESOLVED"]),
        "all_aligned_keys": summarize_measurements([r for c in comparisons for r in c["aligned_keys"]]),
        "unresolved_total": summarize_measurements([c["unresolved_total"] for c in comparisons]),
        "sum_raw": summarize_measurements([c["sum_raw"] for c in comparisons]),
        "closure_pct": summarize_measurements([c["closure_pct"] for c in comparisons if c["closure_pct"]["applicable"]]),
        "display_pct": summarize_measurements([r["display_pct"] for r in rows if r["display_pct"]["applicable"]]),
    }
    # all_original_keys 已含两类键；总超界数不重复计数。
    out_of_bound = sum(by_class[k]["out_of_bound_count"] for k in (
        "all_original_keys", "all_aligned_keys", "unresolved_total", "sum_raw", "closure_pct", "display_pct"))
    stock_failures = sum(not r["stock_equal"] for r in rows)
    summary = {"entities": count, "anchors": len(rows), "policy_comparisons": sum(len(r["policies"]) for r in rows),
               "zero_stock_anchors": sum(int(r["stock_raw_703_704"][0]) == 0 for r in rows),
               "by_class": by_class, "out_of_bound_count": out_of_bound, "stock_failures": stock_failures,
               "n_min": min(r["n"] for r in rows), "n_max": max(r["n"] for r in rows),
               "bound_over_supply_max": str(Fraction(4 * max(r["n"] for r in rows), DENOMINATOR) + Fraction(2, supply))}
    cases[case] = {"summary": summary, "input_binding_equal": bindings, "ledger_files_unchanged": unchanged,
                   "inputs": [{"path": name, "sha256": sha} for name, sha in zip(paths, hashes)], "rows": rows}
    print(case, json.dumps(summary, ensure_ascii=False))
assert sum(c["summary"]["anchors"] for c in cases.values()) == 224
assert sum(c["summary"]["policy_comparisons"] for c in cases.values()) == 666
passed = all(c["summary"]["out_of_bound_count"] == c["summary"]["stock_failures"] == 0 for c in cases.values())
report = {"status": "PASS" if passed else "FAIL", "bound": "abs(delta) * 2**52 <= 4 * n * S + 2 * 2**52",
          "n_source": "per-entity simulation.edges_simulated, equal across both existing ledgers",
          "all_keys_scope": "Every original raw key is checked; gap/residual label migration is also aligned as one gap key.",
          "shortfall_scope": "Existing ledgers do not contain per-edge shortfall traces; those are tested in T4.",
          "zero_stock_pct_scope": "B/stock is undefined for stock=0; raw checks still cover those two anchors.",
          "cases": cases}
(OUT / "ledger_recheck_r4.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
sys.exit(0 if passed else 1)
