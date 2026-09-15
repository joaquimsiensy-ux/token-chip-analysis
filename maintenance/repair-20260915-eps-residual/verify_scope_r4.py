"""r4 白名单、既有具体断言、生产/输入哈希和最终七项日志核验；不修改被测文件。"""
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
ALLOWED.update(PREFIX + name for name in ("done.md", "apu_regression.md", "pythia_regression.md"))


def digest(path):
    data = os.readlink(path).encode() if path.is_symlink() else path.read_bytes()
    return hashlib.sha256(data).hexdigest()


def checks(source):
    return collections.Counter(ast.dump(n) for n in ast.walk(ast.parse(source))
                               if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "check")


def functions(source):
    return {n.name: ast.dump(n) for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)}


before = json.loads((OUT / "scope_before_r4.json").read_text())
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
unexpected_additions = [name for name in added if not (name.startswith(PREFIX) and Path(name).stem.endswith("_r4"))]
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
new_source = (ROOT / "scripts/tests/test_entity_source_trace.py").read_text()
old_source = (OUT / "test_entity_source_trace_before_r4.txt").read_text()
new_checks, old_checks = checks(new_source), checks(old_source)
original_checks = checks((OUT / "test_entity_source_trace_before_r2.txt").read_text())
replaced = list((old_checks - new_checks).elements())
authorized_replacements = len(replaced) == 5 and all(any(text in expr for text in (
    "逐笔短缺入桶数量精确相同", "闭合 pct 展示值精确相同", "非 gap 来源逐条相同",
    "T4-stress 固定种子 200 组且三策略两锚点齐全")) for expr in replaced)
old_functions, new_functions = functions(old_source), functions(new_source)
specific_functions = ("test_eps_residual", "test_eps_residual_mixed", "test_eps_residual_mixed_b")
specific_preserved = {name: old_functions[name] == new_functions[name] for name in specific_functions}
log_path = OUT / "test_entity_source_trace_r4.log"
log_text = log_path.read_text()
original_passes = collections.Counter(line[6:] for line in (OUT / "test_entity_source_trace.log").read_text().splitlines()
                                     if line.startswith("ok    "))
new_passes = collections.Counter(line[6:] for line in log_text.splitlines() if line.startswith("ok    "))
failures = [line[6:] for line in log_text.splitlines() if line.startswith("FAIL  ")]
assertion_ok = (authorized_replacements and not (original_checks - new_checks)
                and all(specific_preserved.values()) and not (original_passes - new_passes))
assertion_report = {"status": "PASS" if assertion_ok else "FAIL",
                    "original_check_calls": sum(original_checks.values()), "r3_check_calls": sum(old_checks.values()),
                    "r4_check_calls": sum(new_checks.values()), "authorized_replacements": replaced,
                    "specific_test_functions_unchanged": specific_preserved,
                    "original_check_calls_missing": list((original_checks - new_checks).elements()),
                    "original_executed_checks": sum(original_passes.values()),
                    "original_executed_checks_missing": list((original_passes - new_passes).elements()),
                    "r4_passes": sum(new_passes.values()), "r4_failures": len(failures), "failure_names": failures}
(OUT / "assertion_preservation_r4.json").write_text(json.dumps(assertion_report, ensure_ascii=False, indent=2) + "\n")
(OUT / "test_change_r4.patch").write_text("".join(difflib.unified_diff(
    old_source.splitlines(True), new_source.splitlines(True), fromfile="before_r4/test_entity_source_trace.py",
    tofile="after_r4/test_entity_source_trace.py")))
receipt = json.loads((OUT / "check_results_r4.json").read_text())
receipt_checks = {
    "seven_results": len(receipt["results"]) == 7,
    "dispatch_matches": receipt["results"] == [json.loads(line) for line in (OUT / "run_checks_r4.log").read_text().splitlines()],
    "log_hashes_match": all(digest(OUT / r["log"]) == r["log_sha256"] for r in receipt["results"]),
    "tested_file_hashes_match": all(digest(ROOT / name) == sha for name, sha in receipt["files"].items()),
}
stress = [json.loads(line.split(" ", 1)[1]) for line in log_text.splitlines() if line.startswith("T4_STRESS_SUMMARY ")]
counterexamples = [json.loads(line.split(" ", 1)[1]) for line in log_text.splitlines() if line.startswith("T4_COUNTEREXAMPLE ")]
assert len(stress) == 1 and len(counterexamples) == 2
binding = {"source_log": log_path.name, "log_sha256": digest(log_path),
           "test_sha256": digest(ROOT / "scripts/tests/test_entity_source_trace.py")}
(OUT / "t4_stress_summary_r4.json").write_text(json.dumps({**binding, "summary": stress[0]}, ensure_ascii=False, indent=2) + "\n")
(OUT / "t4_counterexamples_r4.json").write_text(json.dumps({**binding, "cases": counterexamples}, ensure_ascii=False, indent=2) + "\n")
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
(OUT / "scope_after_r4.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({k: report[k] for k in ("scope_status", "head", "branch", "initial_files_checked", "removed_files",
                                       "unexpected_changes", "unexpected_additions", "seven_exit_codes", "stress_out_of_bound_count")}, ensure_ascii=False))
print("changed files:", ", ".join(sorted(changed)))
print("specific assertions:", specific_preserved, "original checks retained:", not (original_checks - new_checks))
print("ledger hashes unchanged:", all(ledger_checks.values()), "production:", production_hash)
assert ok, report
