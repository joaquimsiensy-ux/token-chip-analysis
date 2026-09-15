"""r3 白名单、断言保留、检查证据及四份输入账本的最终核验。"""
import ast
import collections
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


def checks(text):
    return collections.Counter(ast.dump(n) for n in ast.walk(ast.parse(text))
                               if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "check")


before = json.loads((OUT / "scope_before_r3.json").read_text())
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
unexpected_additions = [name for name in added if not (name.startswith(PREFIX) and Path(name).stem.endswith("_r3"))]
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
new_checks = checks((ROOT / "scripts/tests/test_entity_source_trace.py").read_text())
old_checks = checks((OUT / "test_entity_source_trace_before_r3.txt").read_text())
original_checks = checks((OUT / "test_entity_source_trace_before_r2.txt").read_text())
replaced = list((old_checks - new_checks).elements())
authorized_replacements = len(replaced) == 2 and all("0 <= gap 差 <= residual raw" in expr for expr in replaced)


def passed(name):
    return collections.Counter(line[6:] for line in (OUT / name).read_text().splitlines() if line.startswith("ok    "))


original_passes, r2_passes, r3_passes = [passed(name) for name in (
    "test_entity_source_trace.log", "test_entity_source_trace_r2.log", "test_entity_source_trace_r3.log")]
retained_r2 = collections.Counter({name: n for name, n in r2_passes.items() if "0 <= gap 差 <= residual raw" not in name})
assertion_report = {
    "status": "PASS" if authorized_replacements and not (original_checks - new_checks)
              and not (original_passes - r3_passes) and not (retained_r2 - r3_passes) else "FAIL",
    "original_check_calls": sum(original_checks.values()), "r2_check_calls": sum(old_checks.values()),
    "r3_check_calls": sum(new_checks.values()), "authorized_replacements": replaced,
    "missing_original_check_calls": list((original_checks - new_checks).elements()),
    "original_executed_checks": sum(original_passes.values()), "r2_executed_checks": sum(r2_passes.values()),
    "r2_checks_retained_except_replaced_bound": sum(retained_r2.values()),
    "r3_executed_checks": sum(r3_passes.values()),
    "missing_original_executed_checks": list((original_passes - r3_passes).elements()),
    "missing_retained_r2_executed_checks": list((retained_r2 - r3_passes).elements()),
}
(OUT / "assertion_preservation_r3.json").write_text(json.dumps(assertion_report, ensure_ascii=False, indent=2) + "\n")
receipt = json.loads((OUT / "check_results_r3.json").read_text())
assert receipt["results"] == [json.loads(line) for line in (OUT / "run_checks_r3.log").read_text().splitlines()]
assert len(receipt["results"]) == 7 and all(r["exit_code"] == 0 for r in receipt["results"])
assert all(digest(OUT / r["log"]) == r["log_sha256"] for r in receipt["results"])
assert all(digest(ROOT / name) == sha for name, sha in receipt["files"].items())
ledger_checks = {name: digest(ROOT / name) == sha for name, sha in before["ledgers"].items()}
production_hash = digest(ROOT / "scripts/report/entity_source_trace.py")
expected_hash = "e85acee4e9a98a664d9b4881ca33177003aa9455261109a01e111e6faeda3cd1"
ok = (not removed and not unexpected_changes and not unexpected_additions
      and head == before["head"] and branch == before["branch"] == "main"
      and assertion_report["status"] == "PASS" and all(ledger_checks.values())
      and production_hash == expected_hash == before["files"]["scripts/report/entity_source_trace.py"]["sha256"])
report = {"status": "PASS" if ok else "FAIL", "head": head, "branch": branch,
          "initial_files_checked": len(before["files"]), "changed_files": changed,
          "removed_files": removed, "unexpected_changes": unexpected_changes,
          "added_files": added, "unexpected_additions": unexpected_additions,
          "existing_assertions_preserved": assertion_report["status"] == "PASS", "ledger_files_unchanged": ledger_checks,
          "production_sha256": production_hash}
(OUT / "scope_after_r3.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({k: report[k] for k in ("status", "head", "branch", "initial_files_checked", "removed_files", "unexpected_changes", "unexpected_additions")}, ensure_ascii=False))
print("changed files:", ", ".join(sorted(changed)))
print("assertions:", json.dumps({k: v for k, v in assertion_report.items() if k != "authorized_replacements"}, ensure_ascii=False))
print("ledger hashes unchanged:", all(ledger_checks.values()), "production:", production_hash)
assert ok, report
