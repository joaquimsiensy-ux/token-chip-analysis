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
    raw_balances = json.loads(snap.read_text(encoding="utf-8"))
    if isinstance(raw_balances, dict) and isinstance(raw_balances.get("balances"), dict):
        raw_balances = raw_balances["balances"]
    assert isinstance(raw_balances, dict) and raw_balances, raw_balances
    balances = {str(address).lower(): int(str(raw))
                for address, raw in raw_balances.items()}
    total = sum(balances.values())
    target = receipt["target"]
    requested = receipt["observations"]["balance_reconciliation"].get(
        "requested_top_n", 1)
    sinks = {"0x" + "0" * 40, "0x000000000000000000000000000000000000dead"}
    selected = [address for address, _ in
                sorted(balances.items(), key=lambda item: (-item[1], item[0]))[:requested]
                if address not in sinks]
    assert selected, "fixture owner snapshot must contain a non-sink balance"

    # v3 三查强制同源 replay_stats；换绑 owner 世界时必须把 balance/supply/
    # supply_truth 与 accounting bundle 一起机械重建，不能只给 balance 私造旁路账本。
    receipt, time_receipt = fixture.write_deep_recon_fixtures(
        root, target, root / "raw_transfers.jsonl", total=total,
        address=selected[0])
    transcript = root / "fixture_recon_transcript.json"
    gmgn = root / "fixture_gmgn.csv"
    rows = [{"address": address, "replay_raw": str(balances[address]),
             "chain_raw": str(balances[address]), "diff_raw": "0", "status": "OK"}
            for address in selected]
    calls = [{"seq": seq, "method": "eth_call",
              "params": [{"to": target["token"].lower(),
                          "data": "0x70a08231" + "0" * 24
                                  + address.replace("0x", "")},
                         hex(target["as_of_block"])],
              "result": hex(balances[address])}
             for seq, address in enumerate(selected)]
    write_json(transcript, calls)
    gmgn.write_text("address,pct\n", encoding="utf-8")

    receipt["inputs"].update({
        "balances": {"path": str(snap.resolve()), "size": snap.stat().st_size,
                     "sha256": sha(snap)},
        "transcript": {"path": transcript.name, "size": transcript.stat().st_size,
                       "sha256": sha(transcript)},
        "gmgn": {"path": gmgn.name, "size": gmgn.stat().st_size,
                 "sha256": sha(gmgn)},
    })
    observations = receipt["observations"]
    observations["supply_closure"] = {
        "mint_total_raw": str(total), "burn_total_raw": "0",
        "nominal_supply_raw": str(total), "balance_sum_raw": str(total),
        "negative_count": 0, "negative_addresses": [], "closed": True,
    }
    observations["balance_reconciliation"] = {
        "requested_top_n": requested, "selection": "top_n_then_skip_sinks",
        "checked": len(rows), "matched": len(rows), "mismatched": 0,
        "rpc_errors": 0, "rows": rows,
    }
    observations["gmgn_comparison"] = {
        "checked": 0, "diff_count": 0, "tolerance_pp": 0.15, "rows": [],
    }

    bundle_path = fixture.write_evm_bundle(
        root, token=target["token"], chain=target["chain"],
        as_of=target["as_of_block"], total=total, zero=0, dead=0)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    bundle_rel = {"path": bundle_path.name, "size": bundle_path.stat().st_size,
                  "sha256": sha(bundle_path)}
    bundle_abs = {**bundle_rel, "path": str(bundle_path.resolve())}

    recon = json.loads((root / "reconciliation_report.json").read_text(encoding="utf-8"))
    for key in ("balance", "supply"):
        path = root / recon["checks"][key]["receipt"]["path"]
        write_json(path, receipt)
        recon["checks"][key]["receipt"]["sha256"] = sha(path)
    time_path = root / recon["checks"]["time"]["receipt"]["path"]
    write_json(time_path, time_receipt)
    recon["checks"]["time"]["receipt"]["sha256"] = sha(time_path)

    truth_path = root / recon["checks"]["supply_truth"]["receipt"]["path"]
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    truth.update({"target": target, "replay_net": str(total),
                  "onchain_total_supply": str(total), "diff": "0",
                  "observation_bundle": bundle_abs})
    truth["inputs"]["replay_stats"] = receipt["inputs"]["replay_stats"]
    truth["inputs"]["observation_bundle"] = bundle_rel
    write_json(truth_path, truth)
    recon["checks"]["supply_truth"]["receipt"]["sha256"] = sha(truth_path)
    write_json(root / "reconciliation_report.json", recon)

    accounting_path = root / "accounting_mode.json"
    accounting = json.loads(accounting_path.read_text(encoding="utf-8"))
    accounting["observation_bundle"] = bundle_abs
    accounting["observed_anchor"] = {
        "block": target["as_of_block"], "block_hash": bundle["anchor"]["block_hash"]}
    write_json(accounting_path, accounting)
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
    stats = root / "camp_replay_stats.json"
    write_json(stats, {"mint_total_raw": str(total), "burn_total_raw": "0"})
    write_json(root / "channels_preflight.json", {"token": "0xtoken"})
    write_json(root / "supply_truth.json", {
        "schema": "supply-truth-receipt/v3",
        "target": {"chain": "bsc", "token": "0xtoken", "as_of_block": 123},
        "verdict": "PASS", "exit_code": 0, "chain": "bsc",
        "onchain_total_supply": str(total), "replay_net": str(total),
        "mint_total": str(total), "burn_total": "0",
        "decision_rule": "primary_form1", "total_supply_raw": str(total),
        "net_supply_raw": str(total),
        "inputs": {"replay_stats": {
            "path": stats.name, "size": stats.stat().st_size, "sha256": sha(stats),
        }},
    })
    write_json(root / "data_map.json", {"files": [{"path": "data/holders_owners.json",
                                                        "sha256": sha(snap)}]})
    write_json(root / "candidate_screening.json", {"auto_excluded_candidate": []})
    dist = HERE.parent / "report/holder_distribution_scan.py"
    p = run_formal_script(dist, ["--case-dir", str(root), "--stage", "initial"])
    assert p.returncode == 0, p.stdout + p.stderr
    write_json(root / "camps.json", {"camps": {}, "entities": {}})
    series_path = root / "data/camp_series.json"
    write_json(series_path, {"dates": ["2026-01-01"], "散户": [100.0]})
    sys.path.insert(0, str(HERE.parent / "lib"))
    from camp_series_provenance import series_to_state_form, write_series_sidecar
    sidecar_path = write_series_sidecar(
        series_path, producer="scripts/tests/test_review_20260804_p105.py",
        series_format="evm-dict", denominator="current_net_supply",
        camps_spec_path=root / "camps.json", final_balances_path=snap,
        inputs={"replay_stats": stats},
    )
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    state = {
        "chain": "bsc", "whale_groups": [],
        "camp_share_series": series_to_state_form(
            json.loads(series_path.read_text(encoding="utf-8")), "evm-dict"),
        "provenance": {"series_binding": "producer-sidecar",
                       "camp_series_sidecar": {
                           "producer": sidecar["producer"],
                           "series_file": sidecar["series_file"],
                           "series_sha256": sidecar["series_sha256"],
                           "series_format": sidecar["series_format"],
                       }},
    }
    for name, value in {
        "handoff_manifest.json": {"consumer_min_schema": "handoff/v3", "status": "READY", "run_id": "fixture"},
        "identity_snapshot_receipt.json": {"schema": "identity-snapshot-receipt/v1"},
        "entity_freeze.json": {"schema": "entity-freeze/v1", "revisions": []},
        "analysis-state.json": state,
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
    p = subprocess.run([sys.executable, str(fff), "fig1", "--state",
                        "analysis-state.json", "--out", "charts/final/fig1.png"],
                       cwd=root, capture_output=True, text=True)
    assert p.returncode == 0 and (root / "fig1_legend_receipt.json").is_file(), \
        f"fig1 legend 收据生成失败: {p.stdout} {p.stderr}"
    report.write_text(report.read_text(encoding="utf-8")
                      + "\n![阵营演变](charts/final/fig1.png)\n", encoding="utf-8")
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
