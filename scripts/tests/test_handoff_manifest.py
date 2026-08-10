#!/usr/bin/env python3
"""handoff_manifest 契约测试（离线，黑盒 subprocess 调 CLI）。

覆盖（split-run §2 交接契约的反例集）：
  1. READY 正例全链路：generate → verify exit 0
  2. BLOCKED 拒收：status=BLOCKED → verify exit 2；freeze 对 BLOCKED 案同拒（前置 0）
  3. 哈希漂移：产物被改 → verify exit 2；freeze 同拒（前置 0 内联 verify）
  4. schema 不兼容：consumer_min_schema 超出支持集 → verify exit 2
  5. freeze 前揭盲拒绝：--check-unseal 无 entity_freeze.json → exit 2；freeze 后 → exit 0
  6. gate 语义漂移：accounting_mode.json verdict 被改 → verify exit 2
  7. blocking 异常未解决却报 READY → verify exit 2
  8. generate READY 缺必备契约件 → exit 2
  9. receipt 追加两条且 blind_mode 跟随环境变量
 10. supersede：二次 generate 归档旧 manifest
 12. READY 缺 wave_scan_report.json 即拒（W1 漏检复盘 2026-08-01：波次扫描是 READY 必产件）
 13. wave_scan_report.json 空壳（缺 requires_adjudication 等字段）→ verify exit 2
  18+. freeze 溯源闸内容级反例集（v6.8.1 codex 复核 P0-2/P0-7 修复——旧版把空壳台账当
      正例是在给漏洞背书，本版全部翻成必拒）：v1 schema 拒／空 composition 拒／closure
      自报造假（按 composition 重算）拒／成员哈希错配拒／实体集不一致拒／敏感性不稳拒／
      与边表脱离的人工台账拒／策略明细翻转但 stable=true 拒／重放语义漂移拒／
      provenance-only 变化追加 revision／check-unseal 全绑定哈希复核／
      READY 必备件被手改出 manifest 拒／legacy receipt 机器落盘
用法：python3 scripts/tests/test_handoff_manifest.py   退出码 0=PASS / 1=FAIL
"""
import hashlib
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from formal_ready_test_harness import run_formal_script

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "report", "handoff_manifest.py")
DIST_SCAN = os.path.join(HERE, "..", "report", "holder_distribution_scan.py")
FAILS = []
CHECKS = []


def check(name, cond):
    CHECKS.append(name)
    if not cond:
        FAILS.append(name)
        print(f"FAIL  {name}")
    else:
        print(f"ok    {name}")


def run(args, env=None):
    """Run handoff inside the backward-compatible immutable registry context."""
    return run_formal_script(SCRIPT, args, env=env)


def write_json(d, name, obj):
    with open(os.path.join(d, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def make_case(d, chain="bsc", token="0x0", as_of_block=999):
    """最小合法 −1 案目录。"""
    write_json(d, "candidate_universe.json", {"candidates": [
        {"id": "c1", "address": "0xabc", "reasons": ["threshold_current"]},
        {"id": "c2", "address": "0xdef", "reasons": ["dormant"]}]})
    write_json(d, "candidate_screening.json", {"screened": [
        {"id": "c1", "observed_type": "contract", "source": "getCode", "conflict_flags": []},
        {"id": "c2", "observed_type": None, "source": None, "conflict_flags": [], "needs_adjudication": True}]})
    write_json(d, "identity_preflight.json", {"addresses": [{"address": "0xabc", "labels": [], "code": True}]})
    write_json(d, "anomalies.json", [])
    os.makedirs(os.path.join(d, "data"), exist_ok=True)
    balances = {f"owner-{i:03d}": max(1, int(2_000_000 / (1.035 ** i))) for i in range(240)}
    total = sum(balances.values())
    write_json(d, "data/holders_owners.json", balances)
    snapshot_sha = hashlib.sha256(open(os.path.join(d, "data/holders_owners.json"), "rb").read()).hexdigest()
    write_json(d, "data_map.json", {"files": [
        {"path": "data/transfers.csv", "rows": 2, "source": "test"},
        {"path": "data/edges.jsonl", "rows": 2, "source": "test"},
        {"path": "data/holders_owners.json", "sha256": snapshot_sha, "source": "test"}]})
    with open(os.path.join(d, "data", "transfers.csv"), "w") as f:
        f.write("a,b\n1,2\n")
    with open(os.path.join(d, "data", "edges.jsonl"), "w") as f:
        f.write(json.dumps([86400, 1, 0, 0, Z, "0xabc", 100]) + "\n")
        f.write(json.dumps([86400, 1, 1, 0, Z, "0xdef", 100]) + "\n")
    write_json(d, "accounting_mode.json", {"schema": "accounting-gate/v1", "verdict": "PASS", "exit_code": 0})
    write_json(d, "supply_truth.json", {"verdict": "PASS", "exit_code": 0,
                                         "total_supply_raw": str(total), "net_supply_raw": str(total)})
    write_json(d, "wave_scan_report.json", {"schema": "wave-scan/v3", "scan_universe_count": 0,
                                            "scan_universe": [], "must_adjudicate_count": 0,
                                            "retention_buckets": {"cleared": 0, "partial_exit": 0, "retained": 0},
                                            "negative_balance_addrs": 0,
                                            "waves": [], "equal_amount_groups": [],
                                            "requires_adjudication": False})
    write_json(d, "flow_anomaly_report.json", {"schema": "flow-anomaly/v2", "eligible_universe_count": 0,
                                               "sinks": [], "sprays": [],
                                               "requires_adjudication": False})
    write_json(d, "time_spotcheck.json", {"gate": "time_spotcheck", "schema": "time-spotcheck/v2",
                                          "points": 2, "exact_match": 2, "mismatch": 0,
                                          "rpc_err": 0, "verdict": "PASS", "exit_code": 0})
    repo = Path(HERE).parents[1]
    input_path = Path(d, "data", "holders_owners.json").resolve()

    def file_sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def repo_ref(rel):
        return {"path": rel, "sha256": file_sha(repo / rel)}

    target = {"chain": chain, "token": token.lower(), "as_of_block": as_of_block}
    producers = {"balance": "scripts/evm/verify_recon.py",
                 "supply": "scripts/evm/verify_recon.py",
                 "supply_truth": "scripts/lib/supply_truth_gate.py",
                 "time": "scripts/lib/time_spotcheck.py"}
    bound_input = {"fixture": {"path": str(input_path), "size": input_path.stat().st_size,
                                "sha256": file_sha(input_path)}}
    recon_checks = {}
    for key in ("balance", "supply", "supply_truth", "time"):
        receipt_name = f"reconciliation_{key}_receipt.json"
        if key in {"balance", "supply"}:
            receipt = {"schema": "evm-reconciliation-receipt/v2", "target": target,
                       "observations": {
                           "supply_closure": {"closed": True, "negative_count": 0},
                           "balance_reconciliation": {"checked": 1, "matched": 1,
                                                       "mismatched": 0, "rpc_errors": 0}}}
        elif key == "supply_truth":
            receipt = {"schema": "supply-truth-receipt/v3", "target": target,
                       "gate": "supply_truth", "replay_net": "100",
                       "onchain_total_supply": "100", "diff": "0",
                       "decision_rule": "primary_form1", "burn_form": None,
                       "primary_verdict": "PASS", "sink_reconciliation": None}
        else:
            receipt = {"schema": "time-spotcheck/v2", "target": target,
                       "points": 1, "exact_match": 1, "mismatch": 0, "rpc_err": 0}
        receipt.update({"producer": repo_ref(producers[key]), "mode": "formal",
                        "inputs": bound_input, "verdict": "PASS", "exit_code": 0})
        write_json(d, receipt_name, receipt)
        recon_checks[key] = {"status": "PASS", "exit_code": 0,
                             "receipt": {"path": receipt_name,
                                         "sha256": file_sha(Path(d, receipt_name))},
                             "producer": repo_ref(producers[key])}
    write_json(d, "reconciliation_report.json", {
        "schema": "reconciliation-report/v2", "target": target,
        "producer": repo_ref("scripts/report/reconciliation_report.py"),
        "verdict": "PASS", "exit_code": 0, "checks": recon_checks})
    os.makedirs(os.path.join(d, "sealed"), exist_ok=True)
    with open(os.path.join(d, "sealed", "stage1_hypotheses.sealed.md"), "w") as f:
        f.write("> −2 实体冻结前禁读\n假说：无\n")
    p = subprocess.run([sys.executable, DIST_SCAN, "--case-dir", d, "--stage", "initial"],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"distribution fixture 生成失败: {p.stdout}{p.stderr}")


Z = "0x0000000000000000000000000000000000000000"
GEN = ["--mode", "full", "--producer-model", "test-model", "--chain", "bsc", "--contract", "0x0",
       "--cutoff", "2026-08-01T00:00:00Z", "--frozen-block", "999",
       "--denominators", json.dumps({"total_supply_raw": str(10 ** 12)})]


def members_sha(addrs):
    return hashlib.sha256(",".join(sorted(set(addrs))).encode()).hexdigest()


def make_provenance(d, entity_map, schema="provenance-ledger/v2", stable=True,
                    hollow=False, bad_closure=False, wrong_sha=False, depth_limit=10):
    """从 manifest 绑定的真实边重跑合法台账，再按开关损坏成对应反例。"""
    entity_path = os.path.join(d, "s2_entity_members.json")
    out = os.path.join(d, ".fixture_provenance.json")
    prior = open(entity_path, "rb").read() if os.path.isfile(entity_path) else None
    write_json(d, "s2_entity_members.json", entity_map)
    trace = os.path.join(HERE, "..", "report", "entity_source_trace.py")
    labels_path = os.path.join(d, "fixture_labels.json")
    write_json(d, "fixture_labels.json", {"0xfacility": {"kind": "facility", "name": "fixture"}})
    p = subprocess.run([sys.executable, trace, "--edges-sol", os.path.join(d, "data", "edges.jsonl"),
                        "--total-supply", str(10 ** 12), "--entity-file", entity_path,
                        "--labels-file", labels_path, "--out", out,
                        "--depth-limit", str(depth_limit)],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"fixture provenance 生成失败: {p.stdout}{p.stderr}")
    obj = json.load(open(out))
    os.unlink(out)
    if prior is not None:
        with open(entity_path, "wb") as f:
            f.write(prior)
    obj["schema"] = schema
    if not stable:
        obj["bounds_sensitivity"]["conservative_vs_aggressive_verdict_stable"] = False
    for ent in obj["entities"]:
        if wrong_sha:
            ent["members_sha256"] = "0" * 64
        for anchor in ent["anchors"].values():
            if hollow:
                anchor["composition"] = []
            elif bad_closure and anchor["composition"]:
                anchor["composition"][0]["raw"] = str(max(0, int(anchor["stock_raw"]) // 2))
    return obj


def setup_freezeable(d, entity_map=None):
    """把一个已 generate READY 的案目录补齐到可 freeze：空候选裁决台账＋合法溯源台账＋名册。"""
    entity_map = entity_map if entity_map is not None else {"E1": ["0xabc"]}
    validator = os.path.join(HERE, "..", "report", "adjudication_validator.py")
    subprocess.run([sys.executable, validator, "template", "--case-dir", d, "--force"],
                   capture_output=True)
    adj = json.load(open(os.path.join(d, "candidate_adjudications.json")))
    adj["adjudicated_at"] = "2026-08-01T00:00:00Z"
    write_json(d, "candidate_adjudications.json", adj)
    write_json(d, "s2_entity_members.json", entity_map)
    write_json(d, "provenance_ledger.json", make_provenance(d, entity_map))
    write_json(d, "analysis-state.json", {"whale_groups": [
        {"id": eid, "members": v} for eid, v in entity_map.items()]})


FRZ = ["--members", "analysis-state.json", "--entity-file", "s2_entity_members.json"]


def main():
    root = tempfile.mkdtemp(prefix="handoff_test_")
    try:
        # 1. READY 正例
        d = os.path.join(root, "case_ok")
        os.makedirs(d)
        make_case(d)
        p = run(["generate", "--case-dir", d, "--status", "READY"] + GEN)
        check("generate READY exit 0", p.returncode == 0)
        m = json.load(open(os.path.join(d, "handoff_manifest.json")))
        check("manifest 收录 data_map 索引文件", any(a["path"] == "data/transfers.csv" for a in m["artifacts"]))
        check("manifest sealed 只记哈希", m["sealed"] and "sha256" in m["sealed"][0])
        check("manifest 自动 gate 四个", set(m["gates"]) == {"accounting_gate", "supply_truth_gate",
                                                            "time_spotcheck", "reconciliation_four_checks"})
        p = run(["verify", "--case-dir", d])
        check("verify READY exit 0", p.returncode == 0)

        # accounting_gate.py 的契约明确规定 WARN + exit 0 放行（例如可升级代理）；
        # handoff 只能对 accounting_gate 接受该组合，其他自动 gate 仍须 PASS。
        dwarn = os.path.join(root, "case_accounting_warn")
        os.makedirs(dwarn)
        make_case(dwarn)
        write_json(dwarn, "accounting_mode.json", {
            "schema": "accounting-gate/v1", "mode": "upgradeable-proxy",
            "verdict": "WARN", "exit_code": 0})
        p = run(["generate", "--case-dir", dwarn, "--status", "READY"] + GEN)
        p_verify = run(["verify", "--case-dir", dwarn]) if p.returncode == 0 else p
        check("accounting WARN + exit 0 按记账 gate 契约放行", p_verify.returncode == 0)

        dscope = os.path.join(root, "case_scope_required"); os.makedirs(dscope); make_case(dscope)
        base_gen = ["generate", "--case-dir", dscope, "--status", "READY", "--mode", "full",
                    "--producer-model", "test-model"]
        p = run(base_gen + ["--contract", "0x0"])
        check("READY 缺 chain generate 拒", p.returncode == 2)
        p = run(base_gen + ["--chain", "bsc"])
        check("READY 缺 contract generate 拒", p.returncode == 2)
        p = run(base_gen + ["--chain", "unknown-chain", "--contract", "0x0"])
        check("READY 未知 chain generate 拒", p.returncode == 2)
        p = run(["generate", "--case-dir", dscope, "--status", "PARTIAL", "--mode", "full",
                 "--producer-model", "test-model"])
        check("PARTIAL 不强制正式 scope", p.returncode == 0)

        p = run(["generate", "--case-dir", dscope, "--status", "READY"] + GEN)
        check("scope 独立正例生成", p.returncode == 0)
        broken_scope = json.load(open(os.path.join(dscope, "handoff_manifest.json")))
        broken_scope["scope"]["chains"] = []
        write_json(dscope, "handoff_manifest.json", broken_scope)
        p = run(["verify", "--case-dir", dscope])
        check("verify 空 chains scope 拒", p.returncode == 2)

        # 14. EVM 链缺 time_spotcheck.json 拒 READY；错链 reconciliation 不得被豁免
        d14 = os.path.join(root, "case_no_spotcheck")
        os.makedirs(d14)
        make_case(d14)
        os.unlink(os.path.join(d14, "time_spotcheck.json"))
        p = run(["generate", "--case-dir", d14, "--status", "READY"] + GEN)
        check("EVM 链缺 time_spotcheck 拒 READY exit 2", p.returncode == 2)
        p = run(["generate", "--case-dir", d14, "--status", "READY", "--mode", "full",
                 "--producer-model", "test-model", "--chain", "solana", "--contract", "0x0"])
        p_verify = run(["verify", "--case-dir", d14]) if p.returncode == 0 else p
        check("solana 不得复用 bsc reconciliation", p_verify.returncode == 2)

        # READY 从本批起无条件要求 reconciliation wrapper 及四份绑定回执。
        drecon = os.path.join(root, "case_missing_reconciliation")
        os.makedirs(drecon)
        make_case(drecon)
        os.unlink(os.path.join(drecon, "reconciliation_report.json"))
        p = run(["generate", "--case-dir", drecon, "--status", "READY"] + GEN)
        check("READY 缺 reconciliation 拒", p.returncode == 2 and
              "reconciliation" in (p.stdout + p.stderr).lower())

        # 9. receipt（在正例目录顺手验）
        p = run(["receipt", "--case-dir", d, "--step", "A1", "--cmd", "collect", "--exit", "0",
                 "--artifacts", "data/transfers.csv"], env={"CHIP_BLIND_SERIAL": "1"})
        p2 = run(["receipt", "--case-dir", d, "--step", "A2", "--cmd", "recon", "--exit", "0"])
        rows = json.load(open(os.path.join(d, "stage1_receipts.json")))
        check("receipt 追加两条", p.returncode == 0 and p2.returncode == 0 and len(rows) == 2)
        check("receipt blind_mode 跟随环境", rows[0]["blind_mode"] is True and rows[1]["blind_mode"] is False)

        # 5. freeze 前揭盲拒绝 → 四重前置 → freeze → 放行
        p = run(["freeze", "--case-dir", d, "--check-unseal"])
        check("freeze 前揭盲拒绝 exit 2", p.returncode == 2)
        write_json(d, "analysis-state.json", {"whale_groups": [{"id": "E1", "members": ["0xabc"]}]})
        write_json(d, "s2_entity_members.json", {"E1": ["0xabc"]})
        p = run(["freeze", "--case-dir", d, "--members", "analysis-state.json"])
        check("freeze 缺 --entity-file 拒", p.returncode != 0)
        # v6.8.0：freeze 前置裁决闭环——先出裁决台账（候选为空 → 空台账即闭环）
        p = run(["freeze", "--case-dir", d] + FRZ + ["--pending", "c2 待裁决"])
        check("无裁决台账 freeze 拒 exit 2", p.returncode == 2)
        setup_freezeable(d)
        exploratory = json.load(open(os.path.join(d, "provenance_ledger.json")))
        exploratory["exploration"] = True
        exploratory["input_binding"]["mode"] = "exploration"
        exploratory["input_binding"]["labels_file"] = None
        write_json(d, "provenance_ledger.json", exploratory)
        p = run(["freeze", "--case-dir", d] + FRZ)
        check("exploration/null-label provenance freeze 拒", p.returncode == 2)
        write_json(d, "provenance_ledger.json", make_provenance(d, {"E1": ["0xabc"]}))
        p = run(["freeze", "--case-dir", d] + FRZ + ["--pending", "c2 待裁决"])
        check("四重前置齐备 freeze 初次 exit 0", p.returncode == 0)
        fz0 = json.load(open(os.path.join(d, "entity_freeze.json")))
        check("冻结记录绑定成员/名册/provenance/manifest/data_map 全套哈希",
              fz0.get("entity_file_sha256") and fz0.get("provenance_ledger_sha256")
              and fz0.get("members_sha256") and fz0.get("manifest_sha256")
              and fz0.get("data_map_sha256") and fz0.get("provenance_input_binding_sha256"))
        p = run(["freeze", "--case-dir", d, "--check-unseal"])
        check("freeze 后揭盲放行 exit 0", p.returncode == 0)
        # 名册变更 → 溯源台账逐实体哈希失配 → 拒；重跑溯源（fixture 同步）后 revision 放行
        write_json(d, "analysis-state.json", {"whale_groups": [{"id": "E1", "members": ["0xabc", "0xdef"]}]})
        write_json(d, "s2_entity_members.json", {"E1": ["0xabc", "0xdef"]})
        p = run(["freeze", "--case-dir", d] + FRZ)
        check("名册改动后复用旧溯源台账 freeze 拒 exit 2",
              p.returncode == 2 and "哈希不符" in (p.stderr + p.stdout))
        write_json(d, "provenance_ledger.json", make_provenance(d, {"E1": ["0xabc", "0xdef"]}))
        p = run(["freeze", "--case-dir", d] + FRZ)
        fz = json.load(open(os.path.join(d, "entity_freeze.json")))
        check("重跑溯源后 freeze 变更走 revision 追加", p.returncode == 0 and len(fz["revisions"]) == 1)

        # 10. supersede
        p = run(["generate", "--case-dir", d, "--status", "READY", "--run-id", "s1-second"] + GEN)
        arch = [f for f in os.listdir(d) if f.startswith("handoff_manifest.") and f.endswith(".superseded.json")]
        check("supersede 归档旧 manifest", p.returncode == 0 and len(arch) == 1)

        # 2. BLOCKED 拒收
        d2 = os.path.join(root, "case_blocked")
        os.makedirs(d2)
        make_case(d2)
        p = run(["generate", "--case-dir", d2, "--status", "BLOCKED_CEX_GATE",
                 "--status-reason", "CEX 黑箱超线用户中止"] + GEN)
        check("generate BLOCKED_CEX_GATE exit 0", p.returncode == 0)
        p = run(["verify", "--case-dir", d2])
        check("verify BLOCKED 拒收 exit 2", p.returncode == 2 and "READY" in p.stdout)
        # freeze 前置 0（内联 verify）：BLOCKED 案带齐全部台账也不得冻结
        setup_freezeable(d2)
        p = run(["freeze", "--case-dir", d2] + FRZ)
        check("BLOCKED 案 freeze 同拒 exit 2（前置 0 内联 verify）",
              p.returncode == 2 and "verify" in (p.stderr + p.stdout))

        # 3. 哈希漂移
        d3 = os.path.join(root, "case_drift")
        os.makedirs(d3)
        make_case(d3)
        run(["generate", "--case-dir", d3, "--status", "READY"] + GEN)
        with open(os.path.join(d3, "data", "transfers.csv"), "a") as f:
            f.write("3,4\n")
        p = run(["verify", "--case-dir", d3])
        check("哈希漂移拒收 exit 2", p.returncode == 2 and "漂移" in p.stdout)
        setup_freezeable(d3)
        p = run(["freeze", "--case-dir", d3] + FRZ)
        check("哈希漂移案 freeze 同拒 exit 2（前置 0）", p.returncode == 2)

        # 4. schema 不兼容
        d4 = os.path.join(root, "case_schema")
        os.makedirs(d4)
        make_case(d4)
        run(["generate", "--case-dir", d4, "--status", "READY"] + GEN)
        mp = os.path.join(d4, "handoff_manifest.json")
        m = json.load(open(mp))
        m["consumer_min_schema"] = "handoff/v9"
        json.dump(m, open(mp, "w"))
        p = run(["verify", "--case-dir", d4])
        check("schema 不兼容拒收 exit 2", p.returncode == 2 and "schema" in p.stdout)

        # 6. gate 语义漂移
        d6 = os.path.join(root, "case_gate")
        os.makedirs(d6)
        make_case(d6)
        run(["generate", "--case-dir", d6, "--status", "READY"] + GEN)
        write_json(d6, "accounting_mode.json", {"schema": "accounting-gate/v1", "verdict": "FAIL", "exit_code": 2})
        p = run(["verify", "--case-dir", d6])
        check("gate 语义漂移拒收 exit 2", p.returncode == 2)

        # 7. blocking 异常未解决却 READY
        d7 = os.path.join(root, "case_anom")
        os.makedirs(d7)
        make_case(d7)
        write_json(d7, "anomalies.json", [{"id": "AN-1", "severity": "high", "blocking": True,
                                           "stage": "A1", "status": "open", "evidence": "gap"}])
        run(["generate", "--case-dir", d7, "--status", "READY"] + GEN)
        p = run(["verify", "--case-dir", d7])
        check("blocking 异常未解决拒收 exit 2", p.returncode == 2 and "AN-1" in p.stdout)

        # 8. generate READY 缺必备件
        d8 = os.path.join(root, "case_missing")
        os.makedirs(d8)
        make_case(d8)
        os.unlink(os.path.join(d8, "candidate_universe.json"))
        p = run(["generate", "--case-dir", d8, "--status", "READY"] + GEN)
        check("READY 缺必备件 generate 即拒 exit 2", p.returncode == 2)
        p = run(["generate", "--case-dir", d8, "--status", "PARTIAL"] + GEN)
        check("同目录报 PARTIAL 可出 manifest", p.returncode == 0)

        # 11. READY 缺 gate 产物（supply_truth）即拒——A2 没跑完不得 READY
        d11 = os.path.join(root, "case_nogate")
        os.makedirs(d11)
        make_case(d11)
        os.unlink(os.path.join(d11, "supply_truth.json"))
        p = run(["generate", "--case-dir", d11, "--status", "READY"] + GEN)
        check("READY 缺 supply_truth gate 即拒 exit 2", p.returncode == 2)

        # 12. READY 缺 wave_scan_report 即拒（历史清零层波次扫描必产件）
        d12 = os.path.join(root, "case_nowave")
        os.makedirs(d12)
        make_case(d12)
        os.unlink(os.path.join(d12, "wave_scan_report.json"))
        p = run(["generate", "--case-dir", d12, "--status", "READY"] + GEN)
        check("READY 缺 wave_scan_report 即拒 exit 2", p.returncode == 2)

        # 13. wave_scan_report 空壳 → verify 拒收
        d13 = os.path.join(root, "case_wavehollow")
        os.makedirs(d13)
        make_case(d13)
        write_json(d13, "wave_scan_report.json", {"schema": "wave-scan/v3"})
        run(["generate", "--case-dir", d13, "--status", "READY"] + GEN)
        p = run(["verify", "--case-dir", d13])
        check("wave_scan_report 空壳 verify 拒收 exit 2", p.returncode == 2 and "wave_scan_report" in p.stdout)

        # 15. READY 缺 flow_anomaly_report 即拒（v6.8.0 资金流异常扫描必产件）
        d15 = os.path.join(root, "case_noflow")
        os.makedirs(d15)
        make_case(d15)
        os.unlink(os.path.join(d15, "flow_anomaly_report.json"))
        p = run(["generate", "--case-dir", d15, "--status", "READY"] + GEN)
        check("READY 缺 flow_anomaly_report 即拒 exit 2", p.returncode == 2)

        # 16. wave-scan/v1 旧版产物 → verify 拒收并提示重跑（fail-open 修复）
        d16 = os.path.join(root, "case_wavev1")
        os.makedirs(d16)
        make_case(d16)
        write_json(d16, "wave_scan_report.json", {"schema": "wave-scan/v1", "cleared_layer_count": 0,
                                                  "waves": [], "equal_amount_groups": [],
                                                  "requires_adjudication": False})
        run(["generate", "--case-dir", d16, "--status", "READY"] + GEN)
        p = run(["verify", "--case-dir", d16])
        check("wave-scan/v1 旧版产物 verify 拒收 exit 2",
              p.returncode == 2 and "旧版" in p.stdout and "v3" in p.stdout)

        # 16b. wave-scan/v2 旧版产物（缺 scan_universe 逐址全集）→ verify 同拒（6.9.2）
        d16b = os.path.join(root, "case_wavev2")
        os.makedirs(d16b)
        make_case(d16b)
        write_json(d16b, "wave_scan_report.json", {"schema": "wave-scan/v2", "scan_universe_count": 0,
                                                   "waves": [], "equal_amount_groups": [],
                                                   "requires_adjudication": False})
        run(["generate", "--case-dir", d16b, "--status", "READY"] + GEN)
        p = run(["verify", "--case-dir", d16b])
        check("wave-scan/v2 旧版产物 verify 拒收 exit 2",
              p.returncode == 2 and "旧版" in p.stdout and "scan_universe" in p.stdout)

        # 16c. v3 标签但缺 scan_universe 逐址全集（6.9.3：贴标签不带货同属空壳）
        d16c = os.path.join(root, "case_wavev3hollow")
        os.makedirs(d16c)
        make_case(d16c)
        write_json(d16c, "wave_scan_report.json", {"schema": "wave-scan/v3", "scan_universe_count": 3,
                                                   "waves": [], "equal_amount_groups": [],
                                                   "requires_adjudication": False})
        run(["generate", "--case-dir", d16c, "--status", "READY"] + GEN)
        p = run(["verify", "--case-dir", d16c])
        check("v3 标签缺 scan_universe 全集 verify 拒收 exit 2",
              p.returncode == 2 and "全集不完整" in p.stdout)

        # 16d. v3 count 与逐条标记矛盾（6.9.4：count=0 配 must=true 自相矛盾拒收）
        d16d = os.path.join(root, "case_wavev3contra")
        os.makedirs(d16d)
        make_case(d16d)
        write_json(d16d, "wave_scan_report.json", {
            "schema": "wave-scan/v3", "scan_universe_count": 1,
            "scan_universe": [{"addr": "DormantW", "must_adjudicate": True,
                               "must_reasons": ["dormant_ge_30d"]}],
            "must_adjudicate_count": 0,
            "waves": [], "equal_amount_groups": [], "requires_adjudication": False})
        run(["generate", "--case-dir", d16d, "--status", "READY"] + GEN)
        p = run(["verify", "--case-dir", d16d])
        check("v3 count 与逐条 must 标记矛盾 verify 拒收 exit 2",
              p.returncode == 2 and "内部矛盾" in p.stdout)

        # 17. handoff/v1 旧 manifest：默认拒；--legacy-read-only 显式降级放行（只读警告）
        d17 = os.path.join(root, "case_legacy")
        os.makedirs(d17)
        make_case(d17)
        run(["generate", "--case-dir", d17, "--status", "READY"] + GEN)
        mp17 = os.path.join(d17, "handoff_manifest.json")
        m17 = json.load(open(mp17))
        m17["consumer_min_schema"] = "handoff/v2"
        json.dump(m17, open(mp17, "w"))
        p = run(["verify", "--case-dir", d17])
        check("handoff/v2 默认拒收 exit 2", p.returncode == 2 and "legacy-read-only" in p.stdout)
        m17["consumer_min_schema"] = "handoff/v1"
        json.dump(m17, open(mp17, "w"))
        # manifest 内容变了但其不在 artifacts 自身清单（EXCLUDE_NAMES），哈希不受影响
        p = run(["verify", "--case-dir", d17])
        check("handoff/v1 默认拒收 exit 2", p.returncode == 2 and "legacy-read-only" in p.stdout)
        p = run(["verify", "--case-dir", d17, "--legacy-read-only"])
        check("handoff/v1 --legacy-read-only 放行且带只读警告",
              p.returncode == 0 and "LEGACY READ-ONLY" in p.stdout)
        rc17 = os.path.join(d17, "legacy_readonly_receipt.json")
        check("legacy 降级落机器 receipt", os.path.isfile(rc17)
              and json.load(open(rc17)).get("schema") == "legacy-readonly-receipt/v1")
        # legacy 案 freeze 必拒（严格 v2 verify 不认 --legacy-read-only）
        setup_freezeable(d17)
        p = run(["freeze", "--case-dir", d17] + FRZ)
        check("legacy 案 freeze 必拒 exit 2", p.returncode == 2)

        # 18. freeze 溯源闸内容级反例集（v6.8.1：空壳/自报值/错哈希全部必须被内容重查打回）
        d18 = os.path.join(root, "case_provgate")
        os.makedirs(d18)
        make_case(d18)
        run(["generate", "--case-dir", d18, "--status", "READY"] + GEN)
        setup_freezeable(d18)
        emap = {"E1": ["0xabc"]}
        write_json(d18, "provenance_ledger.json", make_provenance(d18, emap, schema="provenance-ledger/v1"))
        p = run(["freeze", "--case-dir", d18] + FRZ)
        check("溯源台账 v1（数学错误版）freeze 拒 exit 2",
              p.returncode == 2 and "v2" in (p.stderr + p.stdout))
        write_json(d18, "provenance_ledger.json", make_provenance(d18, emap, hollow=True))
        p = run(["freeze", "--case-dir", d18] + FRZ)
        check("stock>0 而 composition 空壳 freeze 拒 exit 2",
              p.returncode == 2 and "空壳" in (p.stderr + p.stdout))
        write_json(d18, "provenance_ledger.json", make_provenance(d18, emap, bad_closure=True))
        p = run(["freeze", "--case-dir", d18] + FRZ)
        check("closure 自报 100 但按 composition 重算不闭合 freeze 拒 exit 2",
              p.returncode == 2 and "重算" in (p.stderr + p.stdout))
        write_json(d18, "provenance_ledger.json", make_provenance(d18, emap, wrong_sha=True))
        p = run(["freeze", "--case-dir", d18] + FRZ)
        check("成员集哈希错配 freeze 拒 exit 2", p.returncode == 2 and "哈希不符" in (p.stderr + p.stdout))
        write_json(d18, "provenance_ledger.json",
                   make_provenance(d18, {"E1": ["0xabc"], "E_ghost": ["0xdef"]}))
        p = run(["freeze", "--case-dir", d18] + FRZ)
        check("台账实体集与名册不一致 freeze 拒 exit 2",
              p.returncode == 2 and "实体集" in (p.stderr + p.stdout))
        write_json(d18, "provenance_ledger.json", make_provenance(d18, emap, stable=False))
        p = run(["freeze", "--case-dir", d18] + FRZ)
        check("敏感性不稳 freeze 拒 exit 2", p.returncode == 2 and "敏感性" in (p.stderr + p.stdout))

        # high-2 核心反例：金额/成员/closure/stable 全合法、但完全没有原始数据绑定。
        # 旧 freeze 会把这类人工台账当“合法正例”；修复后必须在重放前 fail-closed。
        detached = make_provenance(d18, emap)
        detached.pop("input_binding", None)
        write_json(d18, "provenance_ledger.json", detached)
        p = run(["freeze", "--case-dir", d18] + FRZ)
        check("与边表脱离的人工合法台账 freeze 拒 exit 2",
              p.returncode == 2 and "input_binding" in (p.stderr + p.stdout))

        # stable 自报 true，但把 fifo 的策略明细主导终点改掉；freeze 必须从明细重算翻转。
        fake_stable = make_provenance(d18, emap)
        fa = fake_stable["bounds_sensitivity"]["per_entity"]["E1"]["anchors"]["current"]
        fa["policy_details"]["fifo"][0]["terminal"] = ["BOUNDARY", "dex_pool", "0xpool"]
        write_json(d18, "provenance_ledger.json", fake_stable)
        p = run(["freeze", "--case-dir", d18] + FRZ)
        check("策略明细翻转但 stable=true 仍由 freeze 重算拒绝",
              p.returncode == 2 and "机器从明细重算" in (p.stderr + p.stdout))

        # closure/敏感性都保持自洽，只篡改来源类别；唯有从当前原始边重放才能识别。
        stale = make_provenance(d18, emap)
        for anchor in stale["entities"][0]["anchors"].values():
            anchor["composition"][0]["subkind"] = "proven_airdrop"
        for anchor in stale["bounds_sensitivity"]["per_entity"]["E1"]["anchors"].values():
            for rows in anchor["policy_details"].values():
                rows[0]["terminal"] = ["PROVEN_ORIGIN", "proven_airdrop", Z]
            anchor["top_by_policy"] = {p: ["PROVEN_ORIGIN", "proven_airdrop", Z]
                                        for p in ("pro_rata", "fifo", "lifo")}
        write_json(d18, "provenance_ledger.json", stale)
        p = run(["freeze", "--case-dir", d18] + FRZ)
        check("内容自洽但与当前原始边重放不一致 freeze 拒",
              p.returncode == 2 and "重放语义摘要" in (p.stderr + p.stdout))

        valid = make_provenance(d18, emap)
        write_json(d18, "provenance_ledger.json", valid)
        p = run(["freeze", "--case-dir", d18] + FRZ)
        check("台账修复后 freeze 放行 exit 0", p.returncode == 0)

        # medium-4 自然并修：成员不变，仅 provenance 参数/摘要变化也必须追加 revision。
        valid2 = make_provenance(d18, emap, depth_limit=9)
        write_json(d18, "provenance_ledger.json", valid2)
        p = run(["freeze", "--case-dir", d18] + FRZ)
        fz18 = json.load(open(os.path.join(d18, "entity_freeze.json")))
        check("仅 provenance 变化也追加 freeze revision",
              p.returncode == 0 and len(fz18["revisions"]) == 1
              and fz18["provenance_ledger_sha256"] != fz18["revisions"][0]["provenance_ledger_sha256"])
        # check-unseal 不能再只看 members_sha256：当前 provenance 任一漂移都应拒揭盲。
        drifted = copy.deepcopy(valid2)
        drifted["generated_at"] = "2099-01-01T00:00:00Z"
        write_json(d18, "provenance_ledger.json", drifted)
        p = run(["freeze", "--case-dir", d18, "--check-unseal"])
        check("check-unseal 复核 provenance 当前哈希漂移并拒绝", p.returncode == 2)
        write_json(d18, "provenance_ledger.json", valid2)
        p = run(["freeze", "--case-dir", d18, "--check-unseal"])
        check("check-unseal 全绑定恢复后放行", p.returncode == 0)
        edge_path = os.path.join(d18, "data", "edges.jsonl")
        edge_before = open(edge_path, "rb").read()
        with open(edge_path, "ab") as f:
            f.write((json.dumps([172800, 2, 0, 0, Z, "0xabc", 1]) + "\n").encode())
        p = run(["freeze", "--case-dir", d18, "--check-unseal"])
        check("check-unseal 直接复核原始边绑定漂移并拒绝", p.returncode == 2)
        with open(edge_path, "wb") as f:
            f.write(edge_before)
        p = run(["freeze", "--case-dir", d18, "--check-unseal"])
        check("原始边恢复后 check-unseal 放行", p.returncode == 0)

        # 19. manifest artifacts 清单被手改（删掉必备件条目）→ verify 独立重算拒
        d19 = os.path.join(root, "case_handedit")
        os.makedirs(d19)
        make_case(d19)
        run(["generate", "--case-dir", d19, "--status", "READY"] + GEN)
        mp19 = os.path.join(d19, "handoff_manifest.json")
        m19 = json.load(open(mp19))
        m19["artifacts"] = [x for x in m19["artifacts"] if x["path"] != "wave_scan_report.json"]
        json.dump(m19, open(mp19, "w"))
        p = run(["verify", "--case-dir", d19])
        check("手改 manifest 摘掉必备件 verify 拒 exit 2",
              p.returncode == 2 and "必备件" in p.stdout)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print("=" * 40)
    if FAILS:
        print(f"{len(FAILS)} 项失败: {FAILS}")
        return 1
    print(f"handoff_manifest 契约测试全部通过（{len(CHECKS)} 项）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
