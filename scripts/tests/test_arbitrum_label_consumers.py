#!/usr/bin/env python3
"""Arbitrum 标签表在 lookup/cluster 消费侧直接命中并执行 CEX 策略。"""
from __future__ import annotations

import csv
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LABELS = ROOT / "scripts" / "labels"
LOOKUP = LABELS / "label_lookup.py"
CLUSTER = ROOT / "scripts" / "evm" / "cluster.py"
FIELDS = ["address", "chain", "name", "category", "tier", "source", "added_date",
          "evidence", "risk_flags", "merge_policy", "balance_policy", "source_snapshot_at",
          "verified_at", "status", "raw_labels"]
CEX = "0x" + "a" * 40
PLAIN = "0x" + "b" * 40


def write_labels(path: Path):
    row = dict.fromkeys(FIELDS, "")
    row.update({"address": CEX, "chain": "arbitrum", "name": "Fixture CEX hot wallet",
                "category": "cex", "tier": "exclude", "source": "fixture",
                "merge_policy": "no_merge", "balance_policy": "exclude",
                "source_snapshot_at": "2026-08-12"})
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader(); writer.writerow(row)


def main():
    sys.path.insert(0, str(LABELS))
    from labels_resolver import LabelResolver

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        labels_dir = root / "labels"; labels_dir.mkdir()
        write_labels(labels_dir / "labels-arbitrum.csv")
        resolver = LabelResolver("arbitrum", labels_dir=str(labels_dir))
        row = resolver.get(CEX)
        assert row and not row["cross_chain"] and not resolver.degraded, row
        assert resolver.no_merge(CEX) and resolver.is_exclude(CEX), row

        proc = subprocess.run(
            [sys.executable, str(LOOKUP), "--chain", "arbitrum", "--labels-dir",
             str(labels_dir), "--no-evm-common", CEX], capture_output=True, text=True)
        assert proc.returncode == 0 and "Fixture CEX hot wallet" in proc.stdout, proc.stdout + proc.stderr
        assert "同址联查自 eth 表" not in proc.stdout, proc.stdout

        case = root / "case"; case.mkdir()
        (case / "config.json").write_text(json.dumps({
            "symbol": "FIX", "decimals": 0, "total_supply_m": 1,
            "cex_wallets": {}, "team_wallets": {}, "mm_wallets": {},
        }), encoding="utf-8")
        (case / "arbitrum_part_000.csv").write_text(
            f"1,0x01,0,{CEX},{PLAIN},1000\n", encoding="utf-8")
        old_cwd = Path.cwd()
        try:
            os.chdir(case)
            spec = importlib.util.spec_from_file_location("arb_cluster_consumer", CLUSTER)
            cluster = importlib.util.module_from_spec(spec); spec.loader.exec_module(cluster)
            cluster.LabelResolver = lambda chain: LabelResolver(chain, labels_dir=str(labels_dir))
            cluster.append_misses = lambda *args, **kwargs: 0
            cluster.funnel_scan = None; cluster.scan_profiles = None
            cluster.main("arbitrum")
        finally:
            os.chdir(old_cwd)
        result = json.loads((case / "arbitrum_clusters.json").read_text(encoding="utf-8"))
        assert result["labels_meta"]["degraded"] is False, result["labels_meta"]
        blocked = {item["addr"] for item in result["label_excluded_nodes"]}
        assert CEX in blocked, result["label_excluded_nodes"]
        assert all(CEX not in {m["addr"] for m in group["members"]}
                   for group in result["clusters"]), result["clusters"]
    print("PASS: Arbitrum lookup/cluster 直接命中；CEX no_merge/exclude 生效且非跨链推导")


if __name__ == "__main__":
    main()
