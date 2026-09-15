"""r4b 白名单、既有具体断言、生产/输入哈希和最终七项日志核验；不修改被测文件。"""
import ast
import collections
import difflib
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PREFIX = str(OUT.relative_to(ROOT)) + "/"
ALLOWED = {"CHANGELOG.md", "references/scan-schemas.md", "scripts/tests/test_entity_source_trace.py"}
ALLOWED.add(PREFIX + "done.md")


def digest(path):
    data = os.readlink(path).encode() if path.is_symlink() else path.read_bytes()
    return hashlib.sha256(data).hexdigest()


def checks(source):
    return collections.Counter(ast.dump(n) for n in ast.walk(ast.parse(source))
                               if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "check")


def functions(source):
    return {n.name: ast.dump(n) for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)}


before = json.loads((OUT / "scope_before_r4b.json").read_text())
names = set(subprocess.check_output(
    ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT).decode().split("\0")) - {""}
changed, removed = {}, []
for name, record in before["files"].items():
    p = ROOT / name
    if not p.exists() and not p.is_symlink():
        removed.append(name)
    elif digest(p) != record["sha256"]:
        changed[name] = {"before_sha256": record["sha256"], "after_sha256": digest(p)}
added = sorted(names - before["files"].keys())
unexpected_changes = sorted(changed.keys() - ALLOWED)
unexpected_additions = [name for name in added if not (name.startswith(PREFIX) and Path(name).stem.endswith("_r4b"))]
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
new_source = (ROOT / "scripts/tests/test_entity_source_trace.py").read_text()
old_source = (OUT / "test_entity_source_trace_before_r4b.txt").read_text()
new_checks, old_checks = checks(new_source), checks(old_source)
original_checks = checks((OUT / "test_entity_source_trace_before_r2.txt").read_text())
replaced = list((old_checks - new_checks).elements())
authorized_replacements = not replaced
old_functions, new_functions = functions(old_source), functions(new_source)
specific_functions = ("test_eps_residual", "test_eps_residual_mixed", "test_eps_residual_mixed_b",
                      "test_eps_residual_mixed_c", "test_eps_residual_mixed_d")
specific_preserved = {name: old_functions[name] == new_functions[name] for name in specific_functions}
log_path = OUT / "test_entity_source_trace_r4b.log"
log_text = log_path.read_text()
original_passes = collections.Counter(line[6:] for line in (OUT / "test_entity_source_trace.log").read_text().splitlines()
                                     if line.startswith("ok    "))
new_passes = collections.Counter(line[6:] for line in log_text.splitlines() if line.startswith("ok    "))
failures = [line[6:] for line in log_text.splitlines() if line.startswith("FAIL  ")]
assertion_ok = (authorized_replacements and not (original_checks - new_checks)
                and all(specific_preserved.values()) and not (original_passes - new_passes))
assertion_report = {"status": "PASS" if assertion_ok else "FAIL",
                    "original_check_calls": sum(original_checks.values()), "r4_check_calls": sum(old_checks.values()),
                    "r4b_check_calls": sum(new_checks.values()), "authorized_replacements": replaced,
                    "specific_test_functions_unchanged": specific_preserved,
                    "original_check_calls_missing": list((original_checks - new_checks).elements()),
                    "original_executed_checks": sum(original_passes.values()),
                    "original_executed_checks_missing": list((original_passes - new_passes).elements()),
                    "r4b_passes": sum(new_passes.values()), "r4b_failures": len(failures), "failure_names": failures}
(OUT / "assertion_preservation_r4b.json").write_text(json.dumps(assertion_report, ensure_ascii=False, indent=2) + "\n")
(OUT / "test_change_r4b.patch").write_text("".join(difflib.unified_diff(
    old_source.splitlines(True), new_source.splitlines(True), fromfile="before_r4b/test_entity_source_trace.py",
    tofile="after_r4b/test_entity_source_trace.py")))
receipt = json.loads((OUT / "check_results_r4b.json").read_text())
receipt_checks = {
    "seven_results": len(receipt["results"]) == 7,
    "dispatch_matches": receipt["results"] == [json.loads(line) for line in (OUT / "run_checks_r4b.log").read_text().splitlines()],
    "log_hashes_match": all(digest(OUT / r["log"]) == r["log_sha256"] for r in receipt["results"]),
    "tested_file_hashes_match": all(digest(ROOT / name) == sha for name, sha in receipt["files"].items()),
}
stress = [json.loads(line.split(" ", 1)[1]) for line in log_text.splitlines() if line.startswith("T4_STRESS_SUMMARY ")]
counterexamples = [json.loads(line.split(" ", 1)[1]) for line in log_text.splitlines() if line.startswith("T4_COUNTEREXAMPLE ")]
assert len(stress) == 1 and len(counterexamples) == 2
binding = {"source_log": log_path.name, "log_sha256": digest(log_path),
           "test_sha256": digest(ROOT / "scripts/tests/test_entity_source_trace.py")}
(OUT / "t4_stress_summary_r4b.json").write_text(json.dumps({**binding, "summary": stress[0]}, ensure_ascii=False, indent=2) + "\n")
(OUT / "t4_counterexamples_r4b.json").write_text(json.dumps({**binding, "cases": counterexamples}, ensure_ascii=False, indent=2) + "\n")
ledger_checks = {name: digest(ROOT / name) == sha for name, sha in before["ledgers"].items()}
production_hash = digest(ROOT / "scripts/report/entity_source_trace.py")
expected_hash = "e85acee4e9a98a664d9b4881ca33177003aa9455261109a01e111e6faeda3cd1"
ok = (not removed and not unexpected_changes and not unexpected_additions and assertion_ok
      and head == before["head"] and branch == before["branch"] == "main"
      and (ROOT / "VERSION").read_text().strip() == before["version"] == "7.0.4"
      and all(ledger_checks.values()) and all(receipt_checks.values())
      and production_hash == expected_hash == before["files"]["scripts/report/entity_source_trace.py"]["sha256"])
report = {"scope_status": "PASS" if ok else "FAIL", "head": head, "branch": branch,
          "initial_files_checked": len(before["files"]), "changed_files": changed,
          "removed_files": removed, "unexpected_changes": unexpected_changes,
          "added_files": added, "unexpected_additions": unexpected_additions,
          "assertions_preserved": assertion_ok, "ledger_files_unchanged": ledger_checks,
          "production_sha256": production_hash, "check_receipts": receipt_checks,
          "seven_exit_codes": {r["log"]: r["exit_code"] for r in receipt["results"]},
          "stress_out_of_bound_count": stress[0]["out_of_bound_count"]}
(OUT / "scope_after_r4b.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({k: report[k] for k in ("scope_status", "head", "branch", "initial_files_checked", "removed_files",
                                       "unexpected_changes", "unexpected_additions", "seven_exit_codes", "stress_out_of_bound_count")}, ensure_ascii=False))
print("changed files:", ", ".join(sorted(changed)))
print("specific assertions:", specific_preserved, "original checks retained:", not (original_checks - new_checks))
print("ledger hashes unchanged:", all(ledger_checks.values()), "production:", production_hash)
assert ok, report

# 下方进一步核验勘误的记录范围、全部旧判界与固定输入。
from fractions import Fraction


def stress_prefix(source):
    node = next(n for n in ast.parse(source).body
                if isinstance(n, ast.FunctionDef) and n.name == "test_eps_residual_stress")
    prefix = []
    for statement in node.body:
        if isinstance(statement, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "maximum"
                                                    for t in statement.targets):
            break
        prefix.append(statement)
    return [ast.dump(n) for n in prefix]


old_log_path = OUT / "test_entity_source_trace_r4.log"
old_log = old_log_path.read_text()
assert digest(old_log_path) == before["files"][PREFIX + old_log_path.name]["sha256"]
old_label_names = collections.Counter(line[6:] for line in old_log.splitlines()
                                      if line.startswith(("ok    ", "FAIL  "))
                                      and " 构成 ('UNRESOLVED'," in line)
retained_passes = collections.Counter(line[6:] for line in old_log.splitlines()
                                     if line.startswith("ok    ") and " 构成 ('UNRESOLVED'," not in line)
migrations = [json.loads(line.split(" ", 1)[1]) for line in log_text.splitlines()
              if line.startswith("T4_LABEL_MIGRATION ")]
recorded_names = collections.Counter()
for row in migrations:
    key = tuple(row["key"])
    where = row["where"].removesuffix("/" + str(key))
    recorded_names[f"{where} 构成 {key} raw 在界内"] += 1
    assert key[0] == "UNRESOLVED" and row["scope"] == "label_migration_record_only"
    assert row["bound_checked"] is False and "within_bound" not in row
    assert int(row["delta"]) == int(row["new_raw"]) - int(row["old_raw"])
old_summary = json.loads((OUT / "t4_stress_summary_r4.json").read_text())["summary"]
new_summary = stress[0]
same_metrics = all(new_summary["by_class"][key][field] == value[field]
                   for key, value in old_summary["by_class"].items()
                   for field in ("comparisons", "max_abs_delta", "unit"))
label_class = new_summary["by_class"]["unresolved_key"]
bounded_classes = [value for key, value in new_summary["by_class"].items() if key != "unresolved_key"]
contract_checks = {
    "all_r4_check_calls_preserved": not replaced,
    "all_remaining_r4_passes_retained": not (retained_passes - new_passes),
    "all_original_label_checks_recorded": old_label_names == recorded_names,
    "stress_input_generator_unchanged": stress_prefix(old_source) == stress_prefix(new_source),
    "rounding_bound_function_unchanged": old_functions["eps_rounding_bound"] == new_functions["eps_rounding_bound"],
    "counterexample_values_unchanged": counterexamples == json.loads((OUT / "t4_counterexamples_r4.json").read_text())["cases"],
    "stress_comparison_counts_and_maxima_unchanged": same_metrics,
    "labels_recorded_without_bounds": label_class["bound_checked"] is False
                                     and label_class["bounded_comparisons"] == 0
                                     and label_class["out_of_bound_count"] is None,
    "remaining_classes_all_bounded": all(v["bound_checked"] is True
                                        and v["bounded_comparisons"] == v["comparisons"] for v in bounded_classes),
    "remaining_bounds_all_pass": new_summary["out_of_bound_count"] == 0
                                and all(v["out_of_bound_count"] == 0 for v in bounded_classes),
    "test_has_no_failures": not failures,
    "seven_checks_pass": len(receipt["results"]) == 7 and all(r["exit_code"] == 0 for r in receipt["results"]),
}

# 复用哈希冻结的 r4 逐键证据，按勘误重算允许判界的数量；不重跑真实案 trace。
ledger_path = OUT / "ledger_recheck_r4.json"
assert digest(ledger_path) == before["files"][PREFIX + ledger_path.name]["sha256"]
ledger_evidence = json.loads(ledger_path.read_text())
ledger_scope = {}
for case, data in ledger_evidence["cases"].items():
    quantities, labels = [], []
    stocks = 0
    for anchor in data["rows"]:
        n, supply = anchor["n"], int(anchor["total_supply_raw"])
        bound = Fraction(4 * n * supply, 2 ** 52) + 2
        assert anchor["stock_raw_703_704"][0] == anchor["stock_raw_703_704"][1]
        stock = int(anchor["stock_raw_703_704"][0])
        stocks += 1
        for comp in [anchor["composition"], *anchor["policies"].values()]:
            before_map = {tuple(row["key"]): int(row["old_raw"]) for row in comp["keys"]}
            after_map = {tuple(row["key"]): int(row["new_raw"]) for row in comp["keys"]}
            for row in comp["keys"]:
                delta = int(row["new_raw"]) - int(row["old_raw"])
                if row["key"][0] == "UNRESOLVED":
                    labels.append(delta)
                else:
                    quantities.append(delta)
                    assert abs(delta) <= bound
            gap, residual = ("UNRESOLVED", "data_gap", None), ("UNRESOLVED", "fp_residual", None)
            merged_delta = after_map.get(gap, 0) + after_map.get(residual, 0) - before_map.get(gap, 0)
            sum_delta = sum(after_map.values()) - sum(before_map.values())
            quantities.extend((merged_delta, sum_delta))
            assert abs(merged_delta) <= bound and abs(sum_delta) <= bound
            if stock > 0:
                assert abs(Fraction(sum_delta * 100, stock)) <= bound * 100 / stock
        if stock > 0:
            assert abs(Fraction(anchor["display_pct"]["delta"])) <= bound * 100 / stock
    ledger_scope[case] = {"anchors": stocks, "policies": data["summary"]["policy_comparisons"],
                          "bounded_raw_comparisons": len(quantities),
                          "bounded_max_abs_delta_raw": max(map(abs, quantities), default=0),
                          "out_of_bound_count": 0,
                          "original_unresolved_records": len(labels),
                          "label_migration_max_abs_delta_raw": max(map(abs, labels), default=0),
                          "label_migration_changed_count": sum(delta != 0 for delta in labels),
                          "label_migration_bound_checked": False}
assert sum(row["anchors"] for row in ledger_scope.values()) == 224
assert sum(row["policies"] for row in ledger_scope.values()) == 666
review = {"status": "PASS" if all(contract_checks.values()) else "FAIL", "checks": contract_checks,
          "r4_original_label_checks_now_recorded": sum(recorded_names.values()),
          "r4_historical_label_comparison_count_above_B": old_summary["by_class"]["unresolved_key"]["out_of_bound_count"],
          "r4b_stress_label_records": label_class,
          "r4b_stress_out_of_bound_count": new_summary["out_of_bound_count"],
          "ledger_scope_review": {"source": ledger_path.name, "source_sha256": digest(ledger_path),
                                  "inputs_sha256_unchanged": all(ledger_checks.values()), "cases": ledger_scope}}
(OUT / "ruling_scope_review_r4b.json").write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n")
print("r4b ruling scope:", json.dumps({"status": review["status"], "checks": contract_checks,
                                      "migration_records": len(migrations), "ledger_scope": ledger_scope}, ensure_ascii=False))
assert all(contract_checks.values()), contract_checks
