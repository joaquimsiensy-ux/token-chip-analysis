#!/usr/local/bin/python3
"""Run the batch-7 full suite twice in a retained /private/tmp clone."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PYTHON = "/usr/local/bin/python3"
EXPECTED_HEAD = "f530f73b511a59053da2f14c7e3a4d7dd0cddd46"


def run(args, *, cwd: Path, env=None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def summarize(label: str, result: subprocess.CompletedProcess[str], log: Path) -> None:
    combined = result.stdout + result.stderr
    log.write_text(combined, encoding="utf-8")
    pass_count = len(re.findall(r"(?m)^\s*PASS\s+", result.stdout))
    fail_count = len(re.findall(r"(?m)^\s*FAIL(?:\([^\n]*\))?\s+", result.stdout))
    skip_lines = [
        line for line in combined.splitlines()
        if re.search(r"\b(?:skip|skipped)\b", line, flags=re.IGNORECASE)
        and re.search(r"\b0\s+skip", line, flags=re.IGNORECASE) is None
    ]
    summary = [
        line for line in result.stdout.splitlines()
        if line == "全部通过" or "项失败——修完再收工" in line
    ]
    assert result.returncode == 0, f"{label} rc={result.returncode}; see {log}"
    assert pass_count == 121, f"{label} pass_count={pass_count}; see {log}"
    assert fail_count == 0, f"{label} fail_count={fail_count}; see {log}"
    assert not skip_lines, f"{label} skip_lines={skip_lines}; see {log}"
    assert summary == ["全部通过"], f"{label} summary={summary}; see {log}"
    print(
        f"T5 {label}: rc={result.returncode} PASS={pass_count} FAIL={fail_count} "
        f"SKIP={len(skip_lines)} summary={summary[0]} log={log}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reuse-clone", type=Path)
    parser.add_argument("--minimal-only", action="store_true")
    args = parser.parse_args()
    if args.reuse_clone is None:
        evidence_root = Path(tempfile.mkdtemp(prefix="batch7-suite-", dir="/private/tmp"))
        clone = evidence_root / "repo"
        cloned = run(
            [
                "git", "clone", "--local", "--no-hardlinks", "--single-branch", "--branch",
                "fix/sqd-solana-v4", str(ROOT), str(clone),
            ],
            cwd=evidence_root,
        )
        assert cloned.returncode == 0, cloned.stderr
    else:
        clone = args.reuse_clone.resolve()
        evidence_root = clone.parent
    head = run(["git", "rev-parse", "HEAD"], cwd=clone)
    assert head.returncode == 0 and head.stdout.strip() == EXPECTED_HEAD, head.stdout
    print(f"suite_clone={clone} HEAD={head.stdout.strip()}")

    base_env = dict(os.environ)
    base_env["PYTHONDONTWRITEBYTECODE"] = "1"
    if not args.minimal_only:
        default = run(
            [PYTHON, "scripts/tests/run_all.py"], cwd=clone, env=base_env
        )
        summarize("default_PATH", default, evidence_root / "suite_default.log")

    minimal_env = dict(base_env)
    minimal_env["PATH"] = "/usr/bin:/bin"
    minimal = run(
        [PYTHON, "scripts/tests/run_all.py"], cwd=clone, env=minimal_env
    )
    summarize("PATH=/usr/bin:/bin", minimal, evidence_root / "suite_minpath.log")

    status = run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=clone
    )
    assert status.returncode == 0
    assert status.stdout == "", f"suite clone was modified:\n{status.stdout}"
    print("T5 clone_status=clean")
    print("RESULT T5 MINIMAL_PATH CONFIRMED" if args.minimal_only
          else "RESULT T5 CONFIRMED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
