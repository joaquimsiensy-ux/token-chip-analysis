"""核对 r2 相对施工前的文件边界、原断言执行覆盖及既有账本未变。"""
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
ALLOWED.update(PREFIX + name for name in ("done.md", "apu_regression.md", "pythia_regression.md", "run_all_fable_result.json"))
before = json.loads((OUT / "scope_before_r2.json").read_text())
names = set(subprocess.check_output(
    ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT).decode().split("\0")) - {""}
changed, removed = {}, []
for name, record in before["files"].items():
    p = ROOT / name
    if not p.exists() and not p.is_symlink():
        removed.append(name)
        continue
    data = os.readlink(p).encode() if p.is_symlink() else p.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != record["sha256"]:
        changed[name] = {"before_sha256": record["sha256"], "after_sha256": digest}
added = sorted(names - before["files"].keys())
unexpected_changes = sorted(changed.keys() - ALLOWED)
unexpected_additions = [name for name in added if not (name.startswith(PREFIX) and Path(name).stem.endswith("_r2"))]
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()

def passed_names(name):
    return collections.Counter(line[6:] for line in (OUT / name).read_text().splitlines() if line.startswith("ok    "))

previous = passed_names("test_entity_source_trace.log")
current = passed_names("test_entity_source_trace_r2.log")
missing_assertions = list((previous - current).elements())
assertion_report = json.loads((OUT / "assertion_preservation_r2.json").read_text())
assertion_report.update(previous_executed_checks=sum(previous.values()), r2_executed_checks=sum(current.values()),
                        missing_previous_executed_checks=missing_assertions)
(OUT / "assertion_preservation_r2.json").write_text(json.dumps(assertion_report, ensure_ascii=False, indent=2) + "\n")
ledger_checks = {}
for case in json.loads((OUT / "ledger_recheck_r2.json").read_text())["cases"].values():
    for record in case["inputs"]:
        ledger_checks[record["path"]] = hashlib.sha256((ROOT / record["path"]).read_bytes()).hexdigest() == record["sha256"]
ok = (not removed and not unexpected_changes and not unexpected_additions
      and head == before["head"] and branch == before["branch"] == "main"
      and not missing_assertions and assertion_report["status"] == "PASS" and all(ledger_checks.values()))
report = {"status": "PASS" if ok else "FAIL", "head": head, "branch": branch,
          "initial_files_checked": len(before["files"]), "changed_files": changed,
          "removed_files": removed, "unexpected_changes": unexpected_changes,
          "added_files": added, "unexpected_additions": unexpected_additions,
          "existing_assertions_preserved": not missing_assertions, "ledger_files_unchanged": ledger_checks,
          "production_sha256_unchanged": before["files"]["scripts/report/entity_source_trace.py"]["sha256"]}
(OUT / "scope_after_r2.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({k: report[k] for k in ("status", "head", "branch", "initial_files_checked", "removed_files", "unexpected_changes", "unexpected_additions")}, ensure_ascii=False))
print("changed files:", ", ".join(sorted(changed)))
print(f"existing assertions: {sum(previous.values())} retained; r2 checks: {sum(current.values())}; missing: {len(missing_assertions)}")
print("ledger hashes unchanged:", all(ledger_checks.values()))
assert ok, report
