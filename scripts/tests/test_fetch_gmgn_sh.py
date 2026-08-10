#!/usr/bin/env python3
"""F-06 回归：GMGN 仅在命令成功且 JSON 合法时原子发布。"""
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "evm" / "fetch_gmgn.sh"


FAKE_CLI = """#!/bin/sh
case "$GMGN_FIXTURE" in
  valid) printf '%s\\n' '{"ok":true}'; exit 0 ;;
  fail) printf '%s\\n' '{"partial":'; exit 1 ;;
  invalid) printf '%s\\n' 'not-json'; exit 0 ;;
esac
exit 2
"""


def run_case(root, scenario):
    work = root / scenario; work.mkdir()
    env = os.environ.copy()
    env["PATH"] = str(root / "bin") + os.pathsep + env["PATH"]
    env["GMGN_FIXTURE"] = scenario
    return work, subprocess.run(["bash", str(SCRIPT), "0x" + "1" * 40, "bsc"],
                                cwd=work, env=env, capture_output=True, text=True,
                                encoding="utf-8", errors="replace")


def run_in_work(root, work, scenario):
    env = os.environ.copy()
    env["PATH"] = str(root / "bin") + os.pathsep + env["PATH"]
    env["GMGN_FIXTURE"] = scenario
    return subprocess.run(["bash", str(SCRIPT), "0x" + "1" * 40, "bsc"],
                          cwd=work, env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td); bindir = root / "bin"; bindir.mkdir()
        cli = bindir / "gmgn-cli"; cli.write_text(FAKE_CLI, encoding="utf-8"); cli.chmod(0o755)
        sleeper = bindir / "sleep"; sleeper.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8"); sleeper.chmod(0o755)

        work, p = run_case(root, "valid")
        assert p.returncode == 0 and "GMGN DONE" in p.stderr, p.stdout + p.stderr
        assert (work / "gmgn" / "bsc_info.json").exists()

        work, p = run_case(root, "fail")
        assert p.returncode != 0 and "GMGN DONE" not in p.stderr, p.stdout + p.stderr
        assert not list((work / "gmgn").glob("*.json")), "命令失败仍残留正式 JSON"

        work, p = run_case(root, "invalid")
        assert p.returncode != 0 and "GMGN DONE" not in p.stderr, p.stdout + p.stderr
        assert not list((work / "gmgn").glob("*.json")), "非法 JSON 仍被正式发布"

        same = root / "same-run"; same.mkdir()
        p = run_in_work(root, same, "valid")
        assert p.returncode == 0 and (same / "gmgn" / "bsc_info.json").exists()
        p = run_in_work(root, same, "fail")
        assert p.returncode != 0
        assert not (same / "gmgn" / "bsc_info.json").exists(), \
            f"失败后旧正式文件仍在；files={sorted(x.name for x in (same / 'gmgn').iterdir())}; stderr={p.stderr}"
        assert (same / "gmgn" / "bsc_info.json.stale").exists(), "旧正式文件未标 stale"

        p = run_in_work(root, same, "valid")
        assert p.returncode == 0
        p = run_in_work(root, same, "invalid")
        assert p.returncode != 0 and (same / "gmgn" / "bsc_info.json.stale").exists()
    print("PASS: GMGN 临时文件、JSON 校验和失败聚合生效")


if __name__ == "__main__":
    main()
