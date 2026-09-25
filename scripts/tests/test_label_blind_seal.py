#!/usr/bin/env python3
"""CLI 惯犯结构化标记封存回归；只使用临时合成标签，不读取真实案目录。"""
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

LABELS = Path(__file__).resolve().parents[1] / "labels"
sys.path.insert(0, str(LABELS))
import label_lookup

MIXED = "0x" + "a1" * 20
CLEAN = "0x" + "b2" * 20
MIXED_ROW = {
    "address": MIXED, "chain": "bsc", "name": "Synthetic mixed facility",
    "category": "infra", "tier": "exclude",
    "risk_flags": "serial-offender", "source": "serial-offenders+curation",
    "evidence": "Synthetic sealed evidence", "added_date": "2026-09-25",
    "merge_policy": "no_merge", "balance_policy": "exclude",
}
CLEAN_ROW = {
    **MIXED_ROW, "address": CLEAN, "name": "Synthetic clean facility",
    "risk_flags": "", "source": "curation", "evidence": "Clean fixture",
}


class SerialMarkedTests(unittest.TestCase):
    def test_structured_markers(self):
        positives = [
            {"serial": True},
            {"category": "serial-actor"},
            {"category": " serial-actor \t"},
            {"serial": False, "risk_flags": "serial-offender"},
            {"risk_flags": "a|serial-offender|b"},
            {"risk_flags": " a | serial-offender | b "},
            {"risk_flags": ["a", " serial-offender ", "b"]},
            {"source": "serial-offenders+curation"},
            {"source": " curation + serial-offenders "},
            {"risk_flags": {"unexpected": "value"}},
            {"risk_flags": 1},
            {"risk_flags": ("unexpected",)},
        ]
        negatives = [
            {}, CLEAN_ROW, {"serial": False}, {"serial": 1}, {"serial": "True"},
            {"category": "not-serial-actor"}, {"category": None},
            {"risk_flags": None}, {"risk_flags": ""}, {"risk_flags": " | "},
            {"risk_flags": []}, {"risk_flags": [" not-serial-offender "]},
            {"risk_flags": "not-serial-offender"},
            {"risk_flags": "serial-offender-extra"},
            {"source": "non-serial-offenders"},
            {"source": "serial-offenders-extra+curation"},
            {"source": None}, {"source": ""},
        ]
        for expected, rows in ((True, positives), (False, negatives)):
            for row in rows:
                with self.subTest(row=row, expected=expected):
                    self.assertIs(label_lookup.serial_marked(row), expected)


class BlindSealCLITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.labels = self.root / "labels"
        self.labels.mkdir()
        with (self.labels / "labels-bsc.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(MIXED_ROW))
            writer.writeheader()
            writer.writerows([MIXED_ROW, CLEAN_ROW])

    def run_cli(self, *flags, env_blind=False, chain="bsc"):
        env = dict(os.environ)
        env.pop("CHIP_BLIND_SERIAL", None)
        if env_blind:
            env["CHIP_BLIND_SERIAL"] = "1"
        proc = subprocess.run(
            [sys.executable, str(LABELS / "label_lookup.py"), "--chain", chain,
             "--labels-dir", str(self.labels), "--no-evm-common",
             "--sealed-dir", str(self.root), *flags, MIXED, CLEAN],
            cwd=self.root, env=env, capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc

    def check_sealed(self, proc):
        records = [json.loads(line) for line in
                   (self.root / "sealed_serial_hits.jsonl").read_text().splitlines()]
        self.assertEqual(len(records), 1)
        record = records[0]
        for key, value in MIXED_ROW.items():
            self.assertEqual(record[key], value, key)
        self.assertIs(record["serial"], False)
        self.assertTrue(record["sealed_at"])
        self.assertTrue(record["context"])
        for secret in (MIXED_ROW["name"], MIXED_ROW["evidence"],
                       "serial-offender", "serial-offenders", "[SERIAL]"):
            self.assertNotIn(secret, proc.stdout)
        self.assertIn("blind-serial", proc.stderr)

    def check_blind_json(self, proc):
        rows = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual(len(rows), 2)
        by_address = {row["address"]: row for row in rows}
        # 精确键集合：不允许 name/category/risk_flags/source/sections 等任何标签字段。
        self.assertEqual(by_address[MIXED], {"chain": "bsc", "address": MIXED, "hit": False})
        self.assertIs(by_address[CLEAN]["hit"], True)
        self.assertEqual(by_address[CLEAN]["name"], CLEAN_ROW["name"])
        self.assertEqual(by_address[CLEAN]["sections"], ["exclude"])
        self.check_sealed(proc)

    def test_blind_json_flag(self):
        self.check_blind_json(self.run_cli("--blind-serial", "--json"))

    def test_blind_environment(self):
        self.check_blind_json(self.run_cli("--json", env_blind=True))

    def test_blind_text(self):
        proc = self.run_cli("--blind-serial")
        self.assertIn("1/2 地址命中标签库", proc.stdout)
        self.assertIn(CLEAN_ROW["name"], proc.stdout)
        self.assertIn("[EXCLUDE]", proc.stdout)
        self.assertNotIn(MIXED, proc.stdout)
        self.check_sealed(proc)

    def test_nonblind_control(self):
        proc = self.run_cli("--json")
        rows = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual(len(rows), 2)
        by_address = {row["address"]: row for row in rows}
        self.assertIs(by_address[CLEAN]["hit"], True)
        mixed = by_address[MIXED]
        self.assertIs(mixed["hit"], True)
        self.assertIs(mixed["serial"], False)
        for key in ("name", "category", "tier", "risk_flags", "source", "evidence"):
            self.assertEqual(mixed[key], MIXED_ROW[key])
        self.assertEqual(mixed["sections"], ["risk", "exclude"])
        self.assertFalse((self.root / "sealed_serial_hits.jsonl").exists())

    def test_all_chains_keeps_existing_no_miss_behavior(self):
        proc = self.run_cli("--blind-serial", "--json", chain="all")
        rows = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["address"], CLEAN)
        self.assertIs(rows[0]["hit"], True)
        self.assertNotIn(MIXED, proc.stdout)
        self.check_sealed(proc)


if __name__ == "__main__":
    unittest.main(verbosity=2)
