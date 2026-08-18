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
LEGACY_WHITELIST = ROOT / "maintenance/repair-20260817-sqd-v4/grep_legacy_whitelist.md"
OLD_BATCH2_WORKORDER = ROOT / "maintenance/repair-20260817-sqd-v4/batch2_workorder.md"
SQD_COLLECTOR = ROOT / "scripts/solana/fetch_sqd_transfers_v2.py"

sys.path.insert(0, str(HERE))
import test_handoff_manifest as handoff_fixture  # noqa: E402
import test_audit_release_gate as release_fixture  # noqa: E402
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


def test_f04_non_formal_dormant_report_is_release_blocked() -> None:
    with tempfile.TemporaryDirectory(prefix="batch6-f04-", dir="/private/tmp") as raw:
        root = Path(raw)
        report = release_fixture.build_case(root, historical=False)
        baseline = release_fixture.gate.run(root, report)
        assert baseline == [], baseline

        dormant_path = root / "dormant_warehouse_audit.json"
        dormant = json.loads(dormant_path.read_text(encoding="utf-8"))
        dormant["non_formal"] = True
        dormant["order_ambiguous"] = True
        release_fixture.write_json(root, dormant_path.name, dormant)

        errors = release_fixture.gate.run(root, report)
        assert any("静置仓审计" in error and "non_formal" in error for error in errors), errors
        assert any("静置仓审计" in error and "order_ambiguous" in error for error in errors), errors


def test_f06_legacy_scan_covers_tuple_constructor() -> None:
    old_pattern = (
        r"len\([^\n]+\)\s*(==|!=)\s*5|ts,\s*slot,\s*(src|from|f),\s*"
        r"(dst|to|t),\s*(amt|amount)\s*="
    )
    fixed_pattern = (
        r"len\([^\n]+\)\s*(==|!=)\s*5|ts,\s*slot,\s*(src|from|f),\s*"
        r"(dst|to|t),\s*(amt|amount)\s*(=|\)\))"
    )
    missed = subprocess.run(
        ["rg", "-n", old_pattern, str(SQD_COLLECTOR)], capture_output=True, text=True
    )
    assert missed.returncode == 1, missed.stdout + missed.stderr
    covered = subprocess.run(
        ["rg", "-n", fixed_pattern, str(SQD_COLLECTOR)], capture_output=True, text=True
    )
    assert covered.returncode == 0 and "edges.append((ts, slot, f, t, amt))" in covered.stdout

    whitelist = LEGACY_WHITELIST.read_text(encoding="utf-8")
    assert fixed_pattern in whitelist, "白名单文档仍登记会漏掉 tuple constructor 的旧扫描正则"
    assert "HyperSyncFetcher.scan_area" in whitelist and "死代码豁免" in whitelist


def test_f07_old_124816_claim_points_to_correction() -> None:
    lines = OLD_BATCH2_WORKORDER.read_text(encoding="utf-8").splitlines()
    claims = [line for line in lines if "ARC 案 124,816 条" in line]
    assert len(claims) == 1, claims
    claim = claims[0]
    for marker in ("PLAN.md", "batch4_done.md §6.3", "混合口径", "11,502", "8,487"):
        assert marker in claim, f"旧 124,816 行缺勘误指向或校正口径: {marker}"


def main() -> int:
    test_f01_real_duckdb_wave_reaches_formal_gates()
    test_f02_missing_logical_evidence_is_not_backfilled()
    test_f03_padded_legacy_edges_cannot_claim_formal()
    test_f04_non_formal_dormant_report_is_release_blocked()
    test_f06_legacy_scan_covers_tuple_constructor()
    test_f07_old_124816_claim_points_to_correction()
    print("PASS: 批6 opus 盲审防回归")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
