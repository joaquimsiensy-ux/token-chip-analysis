#!/usr/bin/env python3
"""批 6 opus 盲审防回归：必须真跑 producer，再进入正式消费闸。"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import duckdb

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WAVE = ROOT / "scripts/report/wave_scan.py"
ADJUDICATION = ROOT / "scripts/report/adjudication_validator.py"

sys.path.insert(0, str(HERE))
import test_handoff_manifest as handoff_fixture  # noqa: E402


def run_checked(label: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise AssertionError(
            f"{label} rc={result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def test_f01_real_duckdb_wave_reaches_formal_gates() -> None:
    with tempfile.TemporaryDirectory(prefix="batch6-f01-", dir="/private/tmp") as raw:
        root = Path(raw)
        case = root / "case"
        case.mkdir()
        handoff_fixture.make_case(str(case))

        db = root / "edges.duckdb"
        con = duckdb.connect(str(db))
        try:
            con.execute("CREATE TABLE edges(ts BIGINT, f VARCHAR, t VARCHAR, amt HUGEINT)")
            con.execute(
                "INSERT INTO edges VALUES (?, ?, ?, ?)",
                [0, "0x0000000000000000000000000000000000000000", "0xabc", 100],
            )
        finally:
            con.close()

        wave_path = case / "wave_scan_report.json"
        run_checked(
            "真实 duckdb wave producer",
            [
                sys.executable,
                str(WAVE),
                "--duckdb",
                str(db),
                "--edges-table",
                "edges",
                "--total-supply",
                "100",
                "--out",
                str(wave_path),
            ],
        )
        wave = json.loads(wave_path.read_text(encoding="utf-8"))
        assert wave["edge_order_granularity"] == "source-defined"
        assert wave["non_formal"] is False

        run_checked(
            "真实 duckdb wave 进入 adjudication formal 闸",
            [
                sys.executable,
                str(ADJUDICATION),
                "template",
                "--case-dir",
                str(case),
                "--force",
            ],
        )

        generated = handoff_fixture.run(
            ["generate", "--case-dir", str(case), "--status", "READY"]
            + handoff_fixture.GEN
        )
        if generated.returncode != 0:
            raise AssertionError(
                "真实 duckdb wave 进入 handoff generate formal 闸失败\n"
                + generated.stdout
                + generated.stderr
            )
        verified = handoff_fixture.run(["verify", "--case-dir", str(case)])
        if verified.returncode != 0:
            raise AssertionError(
                "真实 duckdb wave 进入 handoff verify formal 闸失败\n"
                + verified.stdout
                + verified.stderr
            )


def main() -> int:
    test_f01_real_duckdb_wave_reaches_formal_gates()
    print("PASS: 批6 opus 盲审防回归")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
