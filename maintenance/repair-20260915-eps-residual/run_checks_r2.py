"""按 r2 白名单运行指定检查，保存原始输出、退出码与被测文件哈希。"""
import hashlib
import json
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
CHECKS = [
    ("test_entity_source_trace", ["python3", "-B", "scripts/tests/test_entity_source_trace.py"]),
    ("test_version_consistency", ["python3", "-B", "scripts/tests/test_version_consistency.py"]),
    ("changelog_lint", ["python3", "-B", "scripts/tests/changelog_lint.py"]),
    ("docs_lint", ["python3", "-B", "scripts/tests/docs_lint.py", "--all"]),
    ("invariant_scan", ["python3", "-B", "scripts/tests/invariant_scan.py"]),
    ("fixtures_lint", ["python3", "-B", "scripts/tests/fixtures_lint.py"]),
    ("git_diff_check", ["git", "diff", "--check"]),
]
env = os.environ.copy()
env["PYTHONDONTWRITEBYTECODE"] = "1"
results = []
for name, args in CHECKS:
    start = time.monotonic()
    log_path = OUT / f"{name}_r2.log"
    with log_path.open("w") as log:
        p = subprocess.run(args, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, text=True)
    result = {"command": shlex.join(args), "exit_code": p.returncode,
              "elapsed_seconds": round(time.monotonic() - start, 3), "log": log_path.name}
    results.append(result)
    print(json.dumps(result), flush=True)
    (OUT / "check_results_r2.json").write_text(json.dumps({
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {"PYTHONDONTWRITEBYTECODE": "1"},
        "files": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in (
            "scripts/report/entity_source_trace.py", "scripts/tests/test_entity_source_trace.py",
            "CHANGELOG.md", "references/scan-schemas.md")},
        "results": results,
    }, ensure_ascii=False, indent=2) + "\n")
sys.exit(int(any(r["exit_code"] for r in results)))
