#!/usr/bin/env python3
"""持仓分布图数据契约、生产路径与 matplotlib fail-loud 回归。"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "scripts/report"
SCAN = REPORT_DIR / "holder_distribution_scan.py"
sys.path.insert(0, str(REPORT_DIR))
import holder_distribution_scan as distribution_scan


def check(name: str, ok: bool, details="") -> bool:
    print(("ok   " if ok else "FAIL ") + f"[{name}]" + (f" {details}" if details and not ok else ""))
    return ok


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def png_info(path: Path) -> tuple[bool, tuple[int, int] | None]:
    try:
        with Image.open(path) as image:
            size = image.size
            image.verify()
        return True, size
    except Exception:
        return False, None


def normal_scan() -> dict:
    rows = []
    upper = 1e-6
    for index in range(15):
        rows.append({
            "index": index,
            "upper_private_pct": upper,
            "owner_count": [4, 0, 7, 2, 0][index % 5],
            "expected_owner_count": [3.5, 3.0, 2.5, 2.0, 1.5][index % 5],
            "raw_balance": str([100, 0, 250, 50, 0][index % 5]),
        })
        upper *= math.sqrt(2)
    return {
        "stage": "final",
        "round": 2,
        "owner_count_private_main": 1234,
        "denominators": {"net_supply_raw": "1000"},
        "base_bins": rows,
    }


def make_low_sample_case(root: Path) -> None:
    snapshot = root / "data/holders_owners.json"
    balances = {f"owner-{index:02d}": 100 - index for index in range(12)}
    write_json(snapshot, [{"owner": owner, "balance_raw": str(raw)}
                          for owner, raw in balances.items()])
    total = sum(balances.values())
    write_json(root / "supply_truth.json", {
        "schema": "supply-truth-receipt/v3", "verdict": "PASS", "exit_code": 0,
        "chain": "bsc", "onchain_total_supply": str(total), "replay_net": str(total),
        "mint_total": str(total), "burn_total": "0", "decision_rule": "primary_form1",
        "total_supply_raw": str(total), "net_supply_raw": str(total),
    })
    write_json(root / "data_map.json", {
        "schema": "data-map/v1",
        "files": [{"path": "data/holders_owners.json", "sha256": sha(snapshot)}],
    })
    write_json(root / "candidate_screening.json", {
        "schema": "candidate-screening/v1", "auto_excluded_candidate": [],
    })


def file_entry(root: Path, rel: str) -> dict:
    path = root / rel
    return {"path": rel, "sha256": sha(path), "size": path.stat().st_size}


def add_final_inputs(root: Path) -> None:
    write_json(root / "facts.json", {"entities": {}, "metrics": {}})
    write_json(root / "analysis-state.json", {"chain": "bsc", "whale_groups": []})
    write_json(root / "evidence.json", {"source": "fixture"})
    claims = [{"id": "C1", "text": "普通命题", "files": ["evidence.json"],
               "report_locations": ["报告.md:1"]}]
    write_json(root / "a4_claims.json", {"schema": "a4-claims/v2", "claims": claims})
    write_json(root / "handoff_manifest.json", {
        "consumer_min_schema": "handoff/v3", "status": "READY", "run_id": "fixture",
    })
    write_json(root / "identity_snapshot_receipt.json", {
        "schema": "identity-snapshot-receipt/v1",
    })
    write_json(root / "entity_freeze.json", {"schema": "entity-freeze/v1", "revisions": []})
    for name in ("membership_ledger.json", "position_ledger.json",
                 "economic_control_ledger.json", "address_classification.json"):
        write_json(root / name, {"rows": []})
    sealed = [file_entry(root, rel) for rel in
              ("a4_claims.json", "facts.json", "analysis-state.json", "evidence.json")]
    write_json(root / "a4_seal.json", {
        "schema": "a4-seal/v4", "verdict": "PASS", "chain": "bsc",
        "workflow_type": "new-analysis", "revision": 1, "charts_dir": "charts/final",
        "registry": {"path": "a4_claims.json", "sha256": sha(root / "a4_claims.json")},
        "claims": [{"id": "C1", "verdict": "CONFIRMED"}],
        "sealed_files": sealed, "claim_files": ["evidence.json"],
    })


def run_scan(case: Path, stage: str, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCAN), "--case-dir", str(case), "--stage", stage, *extra],
        capture_output=True, text=True,
    )


def main() -> int:
    ok = True
    series_fn = getattr(distribution_scan, "_chart_series", None)
    ok &= check("_chart_series 已提供", callable(series_fn))

    scan = normal_scan()
    if callable(series_fn):
        series = series_fn(copy.deepcopy(scan))
        rows = scan["base_bins"]
        ok &= check("bars 按 index 保留零值档",
                    series.get("bars") == [row["owner_count"] for row in rows], str(series))
        ok &= check("expected 按 index 对齐",
                    series.get("expected") == [float(row["expected_owner_count"]) for row in rows],
                    str(series))
        expected_pct = [int(row["raw_balance"]) / 1000 * 100 for row in rows]
        ok &= check("right_pct 按净供应且保留零值档",
                    series.get("right_pct") == expected_pct, str(series))
        expected_ticks = []
        v0 = rows[0]["upper_private_pct"]
        ratio = rows[1]["upper_private_pct"] / v0
        for exponent in range(-6, 3):
            value = 10.0 ** exponent
            if v0 <= value <= rows[-1]["upper_private_pct"]:
                expected_ticks.append((math.log(value / v0) / math.log(ratio), f"{value:g}%"))
        actual_ticks = series.get("xticks", [])
        ticks_ok = len(actual_ticks) == len(expected_ticks) and all(
            math.isclose(actual["pos"], expected[0], rel_tol=1e-12, abs_tol=1e-12)
            and actual["label"] == expected[1]
            for actual, expected in zip(actual_ticks, expected_ticks)
        )
        ok &= check("x 刻度使用数据推导的对数位置", ticks_ok, str(actual_ticks))
        ok &= check("final 标题含轮次与私人主桶",
                    series.get("title") == "当前持仓分布(final·第2轮)——私人主桶 1,234 址",
                    str(series.get("title")))

    with tempfile.TemporaryDirectory(prefix="distribution_chart_") as td:
        root = Path(td)
        os.environ.setdefault("MPLCONFIGDIR", str(root / "matplotlib-cache"))

        direct_path = root / "direct.png"
        before = copy.deepcopy(scan)
        distribution_scan.write_png(direct_path, scan)
        valid, size = png_info(direct_path)
        ok &= check("normal 渲染合法 PNG 且 1800x840",
                    valid and size == (1800, 840), f"valid={valid}, size={size}")
        ok &= check("write_png 不修改 scan 对象", scan == before)

        case = root / "case"
        case.mkdir()
        make_low_sample_case(case)
        initial = run_scan(case, "initial")
        initial_scan_path = case / "distribution_scan.json"
        initial_chart = case / "charts/distribution_stage1.png"
        initial_scan = json.loads(initial_scan_path.read_text(encoding="utf-8")) \
            if initial_scan_path.is_file() else {}
        initial_valid, initial_size = png_info(initial_chart)
        ok &= check("initial 标准生产路径产 1800x840 PNG",
                    initial.returncode == 0 and initial_valid and initial_size == (1800, 840),
                    initial.stdout + initial.stderr + f" size={initial_size}")

        low_series = series_fn(copy.deepcopy(initial_scan)) if callable(series_fn) else {}
        ok &= check("无 base_bins 判为 low_sample",
                    "base_bins" not in initial_scan and low_series.get("mode") == "low_sample"
                    and low_series.get("bars") == [] and low_series.get("expected") == []
                    and low_series.get("right_pct") == [] and low_series.get("xticks") == [],
                    str(low_series))
        ok &= check("low_sample note 明示原因", "low_sample" in str(low_series.get("note")))

        add_final_inputs(case)
        final = run_scan(case, "final", "--round", "1")
        record = subprocess.run([
            sys.executable, str(SCAN), "record-round", "--case-dir", str(case),
            "--scan", "dist_rounds/round_1/distribution_scan.json",
        ], capture_output=True, text=True)
        round_chart = case / "dist_rounds/round_1/holder_distribution_round.png"
        final_chart = case / "charts/final/holder_distribution_current.png"
        round_valid, round_size = png_info(round_chart)
        final_valid, final_size = png_info(final_chart)
        ok &= check("final→record-round 标准拷贝链产终版图",
                    final.returncode == 0 and record.returncode == 0
                    and round_valid and final_valid
                    and round_size == (1800, 840) and final_size == (1800, 840)
                    and sha(round_chart) == sha(final_chart),
                    final.stdout + final.stderr + record.stdout + record.stderr)

        poison_out = root / "poison.png"
        poison_code = (
            "import sys\n"
            "from pathlib import Path\n"
            "sys.modules['matplotlib'] = None\n"
            f"sys.path.insert(0, {str(REPORT_DIR)!r})\n"
            "import holder_distribution_scan as module\n"
            f"module.write_png(Path({str(poison_out)!r}), {normal_scan()!r})\n"
        )
        poison = subprocess.run([sys.executable, "-c", poison_code], capture_output=True, text=True)
        ok &= check("matplotlib 缺失显式失败且不产降级图",
                    poison.returncode != 0 and not poison_out.exists(),
                    poison.stdout + poison.stderr)

    print("PASS: distribution chart contract" if ok else "FAIL: distribution chart contract")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
