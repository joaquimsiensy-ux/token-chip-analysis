#!/usr/bin/env python3
"""F-01 回归：round-trip 必须缺表失败，并比对同键行内决策字段。"""
import csv
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "labels" / "roundtrip_check.py"
CHAINS = ("eth", "bsc", "base", "sol", "robinhood")
FIELDS = ["address", "chain", "name", "category", "tier", "merge_policy",
          "balance_policy", "status", "risk_flags", "source", "evidence", "added_date",
          "verified_at", "source_snapshot_at", "raw_labels"]


def address(chain):
    return "1" * 32 if chain == "sol" else "0x" + "1" * 40


def write_table(root, chain, **changes):
    row = {"address": address(chain), "chain": chain, "name": "设施", "category": "cex",
           "tier": "exclude", "merge_policy": "no_merge", "balance_policy": "exclude",
           "status": "", "risk_flags": "", "source": "manual", "evidence": "fixture",
           "added_date": "2026-01-01", "verified_at": "2026-01-01",
           "source_snapshot_at": "2026-01-01", "raw_labels": "fixture"}
    row.update(changes)
    path = root / f"labels-{chain}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerow(row)


def run(pub, out, *extra):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--pub-dir", str(pub), "--out-dir", str(out),
         "--dump-dir", str(out), *extra],
        capture_output=True, text=True)


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        pub, out = root / "pub", root / "out"
        pub.mkdir(); out.mkdir()
        for chain in CHAINS:
            write_table(pub, chain)
            write_table(out, chain)

        p = run(pub, root / "missing-out")
        assert p.returncode != 0 and "可安全发布" not in p.stdout, p.stdout + p.stderr

        (out / "labels-bsc.csv").unlink()
        p = run(pub, out)
        assert p.returncode != 0 and "可安全发布" not in p.stdout, p.stdout + p.stderr
        write_table(out, "bsc")

        write_table(out, "eth", tier="identity")
        p = run(pub, out)
        assert p.returncode != 0 and "行内退化" in p.stdout, p.stdout + p.stderr
        write_table(out, "eth")

        write_table(out, "eth", risk_flags="exploit")
        p = run(pub, out)
        assert p.returncode != 0 and "risk_flags" in p.stdout, p.stdout + p.stderr
        write_table(out, "eth")

        # 序不同语义同：规范化后必须放行（存量 privacy 表未排序串的真实场景）
        write_table(pub, "eth", risk_flags="wazirx-exploit|tornado-user")
        write_table(out, "eth", risk_flags="tornado-user|wazirx-exploit")
        p = run(pub, out)
        assert p.returncode == 0 and "行内退化" not in p.stdout, p.stdout + p.stderr
        # 空段变体（"a||b"）同样规范化；真实子集差异仍必须 FAIL
        write_table(out, "eth", risk_flags="tornado-user||wazirx-exploit")
        p = run(pub, out)
        assert p.returncode == 0 and "行内退化" not in p.stdout, p.stdout + p.stderr
        write_table(out, "eth", risk_flags="tornado-user")
        p = run(pub, out)
        assert p.returncode != 0 and "risk_flags" in p.stdout, p.stdout + p.stderr
        write_table(pub, "eth")
        write_table(out, "eth")

        for field in ("source", "evidence", "added_date", "verified_at",
                      "source_snapshot_at", "raw_labels"):
            write_table(out, "eth", **{field: "different"})
            p = run(pub, out)
            assert p.returncode == 0 and "[WARN]" in p.stdout and field in p.stdout, \
                p.stdout + p.stderr
        write_table(out, "eth")

        write_table(out, "base", merge_policy="")
        p = run(pub, out, "--dump")
        assert p.returncode != 0 and "行内退化" in p.stdout, p.stdout + p.stderr
        assert (out / "roundtrip_diff_base.csv").exists(), "--dump 未落盘退化行"
        write_table(out, "base")

        p = run(pub, out)
        assert p.returncode == 0 and "可安全发布" in p.stdout, p.stdout + p.stderr
    print("PASS: round-trip 缺表与行内退化均 fail-closed")


if __name__ == "__main__":
    main()
