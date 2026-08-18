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
import test_sqd_consumer_v4 as sqd_fixture  # noqa: E402


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


def test_f02_missing_logical_evidence_is_not_backfilled() -> None:
    old = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="batch6-f02-", dir="/private/tmp") as raw:
        os.chdir(raw)
        try:
            Path("data").mkdir()
            rows = [[100, 1, 0, -1, sqd_fixture.ZERO, sqd_fixture.MINT, 100]]
            edge_path, meta_path = sqd_fixture._paths()
            sqd_fixture._write_edges(edge_path, rows)
            meta = sqd_fixture._v4_meta(rows)
            del meta["edge_logical_sha256"]
            del meta["edge_rows"]
            meta_path.write_text(json.dumps(meta), encoding="utf-8")

            try:
                sqd_fixture.replay_edges._validate_cache_meta(
                    meta, sqd_fixture.MINT, legacy_sol5=False
                )
            except ValueError as exc:
                assert "edge_logical_sha256" in str(exc) and "edge_rows" in str(exc)
            else:
                raise AssertionError("缺逻辑摘要/行数的 v4 meta 通过了前置身份闸")

            Path("data/holders_owners.json").write_text(
                json.dumps({sqd_fixture.MINT: 100}), encoding="utf-8"
            )
            owners = Path("data/holders_owners.json")
            import hashlib

            owners_ref = {
                "path": owners.name,
                "size": owners.stat().st_size,
                "sha256": hashlib.sha256(owners.read_bytes()).hexdigest(),
            }
            Path("data/holders_snapshot_meta.json").write_text(
                json.dumps(
                    {
                        "schema": "solana-holder-snapshot-v2",
                        "mint": sqd_fixture.MINT,
                        "target": {
                            "chain": "solana",
                            "token": sqd_fixture.MINT,
                            "as_of_block": 1,
                        },
                        "closed": True,
                        "supply_raw": "100",
                        "outputs": {"holders_owners": owners_ref},
                    }
                ),
                encoding="utf-8",
            )
            try:
                sqd_fixture.replay_edges.cmd_reconcile(
                    rows, 1, mint=sqd_fixture.MINT, cache_meta_path=meta_path
                )
            except ValueError as exc:
                assert "edge_logical_sha256" in str(exc) and "edge_rows" in str(exc)
            else:
                raise AssertionError("reconcile 回填缺失证据并签出了正式结果")
            assert not Path("data/reconcile_receipt.json").exists()
        finally:
            os.chdir(old)


def test_f03_padded_legacy_edges_cannot_claim_formal() -> None:
    with tempfile.TemporaryDirectory(prefix="batch6-f03-", dir="/private/tmp") as raw:
        root = Path(raw)
        edge_path = root / "padded-legacy.jsonl"
        padded = [
            0,
            1,
            0,
            -1,
            "0x0000000000000000000000000000000000000000",
            "LegacyOwner",
            100,
        ]
        edge_path.write_text(json.dumps(padded) + "\n", encoding="utf-8")
        out = root / "wave.json"
        result = subprocess.run(
            [
                sys.executable,
                str(WAVE),
                "--edges-sol",
                str(edge_path),
                "--total-supply",
                "100",
                "--out",
                str(out),
            ],
            capture_output=True,
            text=True,
        )
        combined = result.stdout + result.stderr
        assert result.returncode == 2, combined
        assert "v4 meta" in combined and "collector" in combined, combined
        assert not out.exists()


def main() -> int:
    test_f01_real_duckdb_wave_reaches_formal_gates()
    test_f02_missing_logical_evidence_is_not_backfilled()
    test_f03_padded_legacy_edges_cannot_claim_formal()
    print("PASS: 批6 opus 盲审防回归")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
