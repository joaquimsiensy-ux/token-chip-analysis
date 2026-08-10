#!/usr/bin/env python3
"""三个参数化工具的反例与 cadence 输入身份绑定回归。"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = [
    ROOT / "scripts/evm/cadence_rank.py",
    ROOT / "scripts/evm/multicall_balances.py",
    ROOT / "scripts/solana/probe_escrows.py",
]
FORBIDDEN = [
    "6d76e7bb743fee795a2f00a317760acf822ee2be",
    "5c952063c7fc8610ffdb798152d69f0b9550762b",
    "997a58129890bbda032231a52ed1ddc845fc18e1",
    "/02251dc4-",
    "8mdvt3hwUfZoP3CY4bcAEQ4aSDk4WakUqBBxsRZPf4pX",
    "3wxPkfjghd5emawiXKv6pi4ahc2CRMWcunZJpUzKpNjH",
    "9Ar3BuWUryoiPqj8c2ZTqgrucf7FMPq7roL1U3Eyg5So",
    "E1q5bq2AHwoD3dhUxCebxsTt3hBqdApTz8z5yhu1sn8S",
    "9igEyPWysUYTu7wM7k1fhpT4344pt2UM7Ww4PY62PHSz",
    "7kfVZ7a534jUu1C7keMtNxHM2jfgNbZhVnX8bD4HUeW7",
    "EviNYQP3c1dksnkFoU7yHhQ5NyBHCq4trUPpGZvc4Fk8",
]


def assert_no_arg_failures():
    for script in SCRIPTS:
        proc = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
        assert proc.returncode != 0, f"{script.name} 无参运行竟成功"
        assert "缺少必填参数" in proc.stderr, f"{script.name} 缺少中文参数错误：{proc.stderr}"


def assert_forbidden_literals_removed():
    combined = "\n".join(script.read_text() for script in SCRIPTS)
    for literal in FORBIDDEN:
        assert literal not in combined, f"现役脚本仍含旧案字面量：{literal}"


def assert_cadence_identity_binding():
    try:
        import duckdb
    except ImportError as exc:
        raise AssertionError("cadence 身份绑定回归需要 duckdb") from exc

    pool = "0x1111111111111111111111111111111111111111"
    holders = [
        "0x2222222222222222222222222222222222222222",
        "0x3333333333333333333333333333333333333333",
    ]
    supply = 1_000_000
    cutoff = "2026-01-02"
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        parquet = work / "mini.parquet"
        tier_file = work / "tier.txt"
        tier_file.write_text("\n".join(holders) + "\n")
        con = duckdb.connect()
        con.execute('''CREATE TABLE events(block BIGINT, ts VARCHAR, tx VARCHAR,
                     log_index BIGINT, "from" VARCHAR, "to" VARCHAR, value VARCHAR)''')
        con.executemany("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?)", [
            (1, "2026-01-01T00:00:00", "0xaaa", 0, pool, holders[0], "100"),
            (2, "2026-01-01T00:00:01", "0xbbb", 0, pool, holders[1], "200"),
        ])
        con.execute(f"COPY events TO '{parquet}' (FORMAT PARQUET)")
        con.close()
        expected = {"pools": [pool], "parquet": str(parquet),
                    "total_supply": supply, "formation_cutoff": cutoff}
        proc = subprocess.run([
            sys.executable, str(SCRIPTS[0]), "--pools", pool,
            "--tier-file", str(tier_file), "--parquet", str(parquet),
            "--total-supply", str(supply), "--formation-cutoff", cutoff,
        ], cwd=work, capture_output=True, text=True)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        artifact = json.loads((work / "tier_final.json").read_text())
        assert artifact["identity"] == expected, artifact["identity"]
        assert "[identity]" in proc.stdout
        for value in (pool, str(parquet), str(supply), cutoff):
            assert value in proc.stdout, f"stdout identity 缺少 {value}"


def main():
    assert_no_arg_failures()
    assert_forbidden_literals_removed()
    assert_cadence_identity_binding()
    print("PASS: 三脚本参数反例、旧案字面量与 cadence identity 绑定")


if __name__ == "__main__":
    main()
