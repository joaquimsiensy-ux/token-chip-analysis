#!/usr/bin/env python3
"""P1-05: new analysis and clean-room audit have distinct mandatory profiles."""
from __future__ import annotations

import importlib.util
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_TEST = HERE / "test_audit_release_gate.py"
spec = importlib.util.spec_from_file_location("audit_fixture_profiles", BASE_TEST)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
from formal_ready_test_harness import run_formal_script

AUDIT_ONLY = (
    "audit_input_manifest.json", "claim_registry.json",
    "reproduce_audit.py", "reproduce_receipt.json", "reproduce_output.json",
)


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bind_balance_receipt_to_snapshot(root: Path, snap: Path) -> None:
    """把四查 balance 收据的 inputs.balances 绑到同一份 owner 快照。

    对应 −1 工作流口径：verify_recon 与 initial 分布扫描必须吃同一个快照文件，
    否则发布闸的 F-03 第二层交叉检查（快照 sha 对四查 balance 输入）无从对起。
    """
    receipt_path = root / "balance_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["inputs"]["balances"] = {"path": str(snap.resolve()),
                                     "size": snap.stat().st_size, "sha256": sha(snap)}
    write_json(receipt_path, receipt)
    recon = json.loads((root / "reconciliation_report.json").read_text(encoding="utf-8"))
    recon["checks"]["balance"]["receipt"]["sha256"] = sha(receipt_path)
    write_json(root / "reconciliation_report.json", recon)
    sys.path.insert(0, str(HERE.parent / "report"))
    from shared_release_receipt import create_bundle
    create_bundle(root)


def add_new_analysis_distribution(root: Path, report: Path) -> None:
    balances = {f"owner-{i:03d}": max(1, int(2_000_000 / (1.035 ** i))) for i in range(240)}
    snap = root / "data/holders_owners.json"; write_json(snap, balances)
    bind_balance_receipt_to_snapshot(root, snap)
    # B-7（批 D）：三账 balance_source 与四查快照等值绑定后，夹具三账须落在同一 owner 世界
    from test_audit_release_gate import align_ledgers_to_owner_snapshot
    align_ledgers_to_owner_snapshot(root, snap)
    total = sum(balances.values())
    write_json(root / "supply_truth.json", {"verdict": "PASS", "exit_code": 0,
                                                "chain": "bsc", "onchain_total_supply": str(total),
                                                "replay_net": str(total), "mint_total": str(total),
                                                "burn_total": "0", "decision_rule": "primary_form1",
                                                "total_supply_raw": str(total),
                                                "net_supply_raw": str(total)})
    write_json(root / "data_map.json", {"files": [{"path": "data/holders_owners.json",
                                                        "sha256": sha(snap)}]})
    write_json(root / "candidate_screening.json", {"auto_excluded_candidate": []})
    dist = HERE.parent / "report/holder_distribution_scan.py"
    p = run_formal_script(dist, ["--case-dir", str(root), "--stage", "initial"])
    assert p.returncode == 0, p.stdout + p.stderr
    for name, value in {
        "handoff_manifest.json": {"consumer_min_schema": "handoff/v3", "status": "READY", "run_id": "fixture"},
        "identity_snapshot_receipt.json": {"schema": "identity-snapshot-receipt/v1"},
        "entity_freeze.json": {"schema": "entity-freeze/v1", "revisions": []},
        "analysis-state.json": {"chain": "bsc", "whale_groups": []},
        # facts 带最小 token（figure2 check 真跑需要 total_supply_raw>0）
        "facts.json": {"token": {"symbol": "FX", "decimals": 0,
                                 "total_supply_raw": "1"}, "entities": {}},
        "evidence.json": {"source": "fixture"},
        "a4_claims.json": {"schema": "a4-claims/v2", "claims": [{"id": "C1"}]},
    }.items():
        write_json(root / name, value)
    # a4_claims 是对抗复核 v3 的权威锚；夹具改 registry 后必须真重跑 runner/finalize，
    # 不得手补 aggregate 的 sha 自证。
    fixture.refresh_adversarial(root)
    from shared_release_receipt import create_bundle
    create_bundle(root)
    # F-C5：figure2 对账收据由真实生产者产出（figures_from_facts check 真跑，
    # 防手搓影子形态假绿）——空 whale_series 对空 entities 合法 PASS
    write_json(root / "whale_series.json", [])
    fff = HERE.parent / "report/figures_from_facts.py"
    p = subprocess.run([sys.executable, str(fff), "check", "--facts", "facts.json",
                        "--series", "whale_series.json"], cwd=root,
                       capture_output=True, text=True)
    assert p.returncode == 0 and (root / "figure2_check_receipt.json").is_file(), \
        f"figure2 check 收据生成失败: {p.stdout} {p.stderr}"
    write_json(root / "a4_seal.json", {"schema": "a4-seal/v4", "verdict": "PASS", "chain": "bsc",
        "workflow_type": "new-analysis", "revision": 1, "previous_seal": None,
        "charts_dir": "charts/final", "claims": [{"id": "C1", "verdict": "CONFIRMED"}]})
    p = run_formal_script(dist, ["--case-dir", str(root), "--stage", "final", "--round", "1"])
    assert p.returncode == 0, p.stdout + p.stderr
    p = run_formal_script(dist, ["record-round", "--case-dir", str(root),
                                 "--scan", "dist_rounds/round_1/distribution_scan.json"])
    assert p.returncode == 0, p.stdout + p.stderr
    report.write_text(report.read_text(encoding="utf-8")
        + "\n当前快照呈正常形态;这只表示本闸未检出结构性畸形,不等于没有庄。\n"
        + "\n![持仓分布](charts/final/holder_distribution_current.png)\n", encoding="utf-8")
    a5 = HERE.parent / "report/a5_report_seal.py"
    p = run_formal_script(a5, ["--case-dir", str(root), "--report", str(report),
                               "--a4-seal", str(root / "a4_seal.json"),
                               "--out", str(root / "a5_report_seal.json")])
    assert p.returncode == 0, p.stdout + p.stderr


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        report = fixture.build_case(root, historical=False)
        for name in AUDIT_ONLY:
            (root / name).unlink(missing_ok=True)
        add_new_analysis_distribution(root, report)
        assert not fixture.gate.run(root, report, profile="new-analysis")
        audit_errors = fixture.gate.run(root, report, profile="independent-audit")
        assert any("audit_input_manifest.json" in x for x in audit_errors)
        assert any("claim_registry.json" in x for x in audit_errors)

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        report = fixture.build_case(root, historical=False)
        assert not fixture.gate.run(root, report, profile="independent-audit")

    print("PASS: P1-05 mandatory new-analysis vs independent-audit release profiles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
