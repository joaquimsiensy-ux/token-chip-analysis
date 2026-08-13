#!/usr/bin/env python3
"""批 C（F-04）可重放反例：伪序列双喂 source 与 --series-source。

场景 A（伪 sidecar 自洽攻击）：攻击者伪造序列末点并自造 sidecar——输出 sha 自洽、
  inputs 绑真 replay_stats（登记面命中）——必须被**末点对账**独立拦截（exit 2）。
场景 B（双源分叉攻击）：source 手填一份伪 camp_share_series，同时 --series-source
  给真序列——必须被"series 只有一个事实源"检查拦截（exit 2）。
场景 C（绿例防误伤）：未篡改全链 PASS（exit 0）。
退出码：0=三场景全符合预期；1=任一场景失守。
"""
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for sub in ("tests", "lib", "evm"):
    sys.path.insert(0, str(ROOT / "scripts" / sub))
from evm_channel_fixture import write_csv_channel_receipt  # noqa: E402
from camp_series_provenance import write_series_sidecar  # noqa: E402

Z = "0x" + "0" * 40
A = "0xa000000000000000000000000000000000000001"
B = "0xb000000000000000000000000000000000000002"


def run_compile(td, *extra):
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts/report/state_from_facts.py"),
         "--facts", "facts.json", "--source", "source.json",
         "--out", "analysis-state.json", *extra],
        cwd=td, capture_output=True, text=True)


def main():
    with tempfile.TemporaryDirectory() as s:
        td = Path(s)
        rows = [(100, "2026-01-01T10:00:00", "0x" + "1" * 64, Z, A, 1000),
                (105, "2026-01-02T10:00:00", "0x" + "2" * 64, A, B, 400),
                (115, "2026-01-04T10:00:00", "0x" + "4" * 64, B, Z, 50)]
        src = td / "transfers.csv"
        with src.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["block", "ts", "tx", "from", "to", "value", "uniqueId"])
            for i, (b, ts, tx, frm, to, v) in enumerate(rows):
                w.writerow([b, ts, tx, frm, to, v, f"{tx}:log:{i}"])
        write_csv_channel_receipt(td, "t", src, A, 0, 999999)
        (td / "channels.json").write_text(json.dumps(
            {"schema": "evm-channels/v2", "token": A, "expected_from": 0,
             "expected_to": 999999,
             "channels": [{"path": "transfers.csv", "lo": 0, "hi": 999999,
                           "tag": "t", "format": "v1csv",
                           "receipt": "t.receipt.json"}]}))
        (td / "camps.json").write_text(json.dumps(
            {"camps": {"项目方": [A], "大庄": [B]}, "entities": {}},
            ensure_ascii=False))
        p = subprocess.run(
            [sys.executable, str(ROOT / "scripts/evm/replay_duck.py"),
             "--channels", "channels.json", "--out-dir", "data",
             "--camps", "camps.json", "--no-merged"],
            cwd=td, capture_output=True, text=True)
        assert p.returncode == 0, p.stderr[-300:]
        stats = td / "data/replay_stats.json"
        (td / "supply_truth.json").write_text(json.dumps(
            {"schema": "supply-truth/v1", "verdict": "PASS", "exit_code": 0,
             "onchain_total_supply": "950", "replay_net": "950", "chain": "bsc",
             "inputs": {"replay_stats": {
                 "path": "data/replay_stats.json",
                 "sha256": hashlib.sha256(stats.read_bytes()).hexdigest(),
                 "size": stats.stat().st_size}}}))
        (td / "facts.json").write_text(json.dumps(
            {"token": {"symbol": "TT", "decimals": 0, "total_supply_raw": "950"},
             "entities": {"e1": {"label": "大庄#1", "addresses": [B],
                                 "current_raw": "350", "peak_raw": "400"}}}))
        (td / "source.json").write_text(json.dumps(
            {"schema": "analysis-state-source/v1",
             "token": {"chain": "bsc", "data_cutoff": "2026-01-04T23:59:59Z",
                       "skill_version": "6.39.5"},
             "entity_annotations": {"e1": {"type": "single",
                                           "status": "holding"}},
             "address_balances": {B: "350"}, "vault_addresses": [],
             "provenance": {"skill_commit": "ce", "data_sources": ["replay"]}}))
        failures = []

        # 场景 C 先证绿例（防"闸把一切都拒"的假阳性）
        p = run_compile(td, "--series-source", "data/camp_series.json")
        if p.returncode != 0:
            failures.append(f"绿例失守 rc={p.returncode}: {p.stdout[-200:]}")

        # 场景 A：伪造末点＋自造 sha 自洽 sidecar（登记面照样命中）
        series = td / "data/camp_series.json"
        original = series.read_text()
        fake = json.loads(original)
        fake["大庄"][-1] = 30.0
        fake["散户"][-1] = round(100 - fake["项目方"][-1] - 30.0, 4)
        series.write_text(json.dumps(fake, ensure_ascii=False))
        write_series_sidecar(series, producer="scripts/evm/replay_duck.py",
                             series_format="evm-dict",
                             denominator="current_net_supply",
                             camps_spec_path=td / "camps.json",
                             final_balances_path=td / "data/balances_final.json",
                             inputs={"replay_stats": stats})
        p = run_compile(td, "--series-source", "data/camp_series.json")
        if p.returncode != 2 or "末点对账失败" not in p.stdout:
            failures.append(f"场景A失守 rc={p.returncode}: {p.stdout[-200:]}")
        series.write_text(original)
        write_series_sidecar(series, producer="scripts/evm/replay_duck.py",
                             series_format="evm-dict",
                             denominator="current_net_supply",
                             camps_spec_path=td / "camps.json",
                             final_balances_path=td / "data/balances_final.json",
                             inputs={"replay_stats": stats})

        # 场景 B：source 手填伪序列＋真 --series-source（双源分叉）
        src_obj = json.loads((td / "source.json").read_text())
        src_obj["camp_share_series"] = {
            "dates": ["2026-01-01"], "series": {"大庄": [40.0], "散户": [60.0]}}
        (td / "source.json").write_text(json.dumps(src_obj, ensure_ascii=False))
        p = run_compile(td, "--series-source", "data/camp_series.json")
        if p.returncode != 2 or "只有一个事实源" not in p.stdout:
            failures.append(f"场景B失守 rc={p.returncode}: {p.stdout[-200:]}")

        if failures:
            print("FAIL:", *failures, sep="\n  ")
            return 1
        print("PASS: 伪序列双喂三场景全符合预期"
              "（末点对账拦A / 单一事实源拦B / 绿例C不误伤）")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
