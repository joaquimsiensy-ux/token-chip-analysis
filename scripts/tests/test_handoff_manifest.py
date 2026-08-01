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
      READY 必备件被手改出 manifest 拒／legacy receipt 机器落盘
用法：python3 scripts/tests/test_handoff_manifest.py   退出码 0=PASS / 1=FAIL
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "report", "handoff_manifest.py")
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
    e = os.environ.copy()
    if env:
        e.update(env)
    return subprocess.run([sys.executable, SCRIPT] + args, capture_output=True, text=True, env=e)


def write_json(d, name, obj):
    with open(os.path.join(d, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def make_case(d):
    """最小合法 −1 案目录。"""
    write_json(d, "candidate_universe.json", {"candidates": [
        {"id": "c1", "address": "0xabc", "reasons": ["threshold_current"]},
        {"id": "c2", "address": "0xdef", "reasons": ["dormant"]}]})
    write_json(d, "candidate_screening.json", {"screened": [
        {"id": "c1", "observed_type": "contract", "source": "getCode", "conflict_flags": []},
        {"id": "c2", "observed_type": None, "source": None, "conflict_flags": [], "needs_adjudication": True}]})
    write_json(d, "identity_preflight.json", {"addresses": [{"address": "0xabc", "labels": [], "code": True}]})
    write_json(d, "anomalies.json", [])
    write_json(d, "data_map.json", {"files": [{"path": "data/transfers.csv", "rows": 2, "source": "test"}]})
    os.makedirs(os.path.join(d, "data"), exist_ok=True)
    with open(os.path.join(d, "data", "transfers.csv"), "w") as f:
        f.write("a,b\n1,2\n")
    write_json(d, "accounting_mode.json", {"schema": "accounting-gate/v1", "verdict": "PASS", "exit_code": 0})
    write_json(d, "supply_truth.json", {"verdict": "PASS", "exit_code": 0})
    write_json(d, "wave_scan_report.json", {"schema": "wave-scan/v2", "scan_universe_count": 0,
                                            "retention_buckets": {"cleared": 0, "partial_exit": 0, "retained": 0},
                                            "negative_balance_addrs": 0,
                                            "waves": [], "equal_amount_groups": [],
                                            "requires_adjudication": False})
    write_json(d, "flow_anomaly_report.json", {"schema": "flow-anomaly/v1", "eligible_universe_count": 0,
                                               "sinks": [], "sprays": [],
                                               "requires_adjudication": False})
    write_json(d, "time_spotcheck.json", {"gate": "time_spotcheck", "schema": "time-spotcheck/v1",
                                          "points": 2, "exact_match": 2, "mismatch": 0,
                                          "rpc_err": 0, "verdict": "PASS", "exit_code": 0})
    os.makedirs(os.path.join(d, "sealed"), exist_ok=True)
    with open(os.path.join(d, "sealed", "stage1_hypotheses.sealed.md"), "w") as f:
        f.write("> −2 实体冻结前禁读\n假说：无\n")


GEN = ["--mode", "easy", "--producer-model", "test-model", "--chain", "bsc", "--contract", "0x0"]
Z = "0x0000000000000000000000000000000000000000"


def members_sha(addrs):
    return hashlib.sha256(",".join(sorted(set(addrs))).encode()).hexdigest()


def make_provenance(entity_map, stock=100, schema="provenance-ledger/v2", stable=True,
                    hollow=False, bad_closure=False, wrong_sha=False):
    """合法 v2 溯源台账 fixture（或按开关损坏成对应反例）。"""
    ents = []
    for eid, addrs in entity_map.items():
        comp = [] if hollow else [
            {"kind": "PROVEN_ORIGIN", "subkind": "mint", "via": Z,
             "pct_of_anchor": 100.0, "raw": str(stock if not bad_closure else stock // 2),
             "evidence_level": "onchain_pattern", "path_len": 1}]
        ents.append({
            "entity_id": eid, "member_count": len(addrs),
            "members_sha256": ("0" * 64) if wrong_sha else members_sha(addrs),
            "anchors": {
                "current": {"stock_raw": str(stock), "composition": comp, "direct_upstream": []},
                "peak": {"date": "2026-01-01", "stock_raw": str(stock),
                         "composition": comp, "direct_upstream": []}},
            "turnover": {"gross_in_raw": str(stock), "gross_out_raw": "0"},
            # closure_check 故意恒填 100——freeze 必须按 composition 重算而不是信这个自报值
            "closure_check": {"current_sum_pct": 100.0, "peak_sum_pct": 100.0},
            "simulation": {"ancestors": 0, "terminals": 1, "depth_truncated": 0,
                           "budget_truncated": 0, "edges_simulated": 1,
                           "same_ts_cycle_groups": 0, "data_gap_events": 0},
        })
    return {"schema": schema, "entities": ents,
            "bounds_sensitivity": {"methods": ["pro_rata", "fifo", "lifo"], "per_entity": {},
                                   "conservative_vs_aggressive_verdict_stable": stable}}


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
    write_json(d, "provenance_ledger.json", make_provenance(entity_map))
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
        check("manifest 自动 gate 三个", set(m["gates"]) == {"accounting_gate", "supply_truth_gate",
                                                            "time_spotcheck"})
        p = run(["verify", "--case-dir", d])
        check("verify READY exit 0", p.returncode == 0)

        # 14. EVM 链缺 time_spotcheck.json 拒 READY；solana 链豁免（6.7.0 时间抽查收编）
        d14 = os.path.join(root, "case_no_spotcheck")
        os.makedirs(d14)
        make_case(d14)
        os.unlink(os.path.join(d14, "time_spotcheck.json"))
        p = run(["generate", "--case-dir", d14, "--status", "READY"] + GEN)
        check("EVM 链缺 time_spotcheck 拒 READY exit 2", p.returncode == 2)
        p = run(["generate", "--case-dir", d14, "--status", "READY", "--mode", "easy",
                 "--producer-model", "test-model", "--chain", "solana", "--contract", "0x0"])
        check("solana 链无 time_spotcheck 豁免 exit 0", p.returncode == 0)

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
        p = run(["freeze", "--case-dir", d] + FRZ + ["--pending", "c2 待裁决"])
        check("四重前置齐备 freeze 初次 exit 0", p.returncode == 0)
        fz0 = json.load(open(os.path.join(d, "entity_freeze.json")))
        check("冻结记录绑定三份哈希",
              fz0.get("entity_file_sha256") and fz0.get("provenance_ledger_sha256")
              and fz0.get("members_sha256"))
        p = run(["freeze", "--case-dir", d, "--check-unseal"])
        check("freeze 后揭盲放行 exit 0", p.returncode == 0)
        # 名册变更 → 溯源台账逐实体哈希失配 → 拒；重跑溯源（fixture 同步）后 revision 放行
        write_json(d, "analysis-state.json", {"whale_groups": [{"id": "E1", "members": ["0xabc", "0xdef"]}]})
        write_json(d, "s2_entity_members.json", {"E1": ["0xabc", "0xdef"]})
        p = run(["freeze", "--case-dir", d] + FRZ)
        check("名册改动后复用旧溯源台账 freeze 拒 exit 2",
              p.returncode == 2 and "哈希不符" in (p.stderr + p.stdout))
        write_json(d, "provenance_ledger.json", make_provenance({"E1": ["0xabc", "0xdef"]}))
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
        p = run(["generate", "--case-dir", d2, "--status", "BLOCKED_E0B",
                 "--status-reason", "CEX 黑箱超线用户中止"] + GEN)
        check("generate BLOCKED_E0B exit 0", p.returncode == 0)
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
        write_json(d13, "wave_scan_report.json", {"schema": "wave-scan/v2"})
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
        check("wave-scan/v1 旧版产物 verify 拒收 exit 2", p.returncode == 2 and "v6.6.1" in p.stdout)

        # 17. handoff/v1 旧 manifest：默认拒；--legacy-read-only 显式降级放行（只读警告）
        d17 = os.path.join(root, "case_legacy")
        os.makedirs(d17)
        make_case(d17)
        run(["generate", "--case-dir", d17, "--status", "READY"] + GEN)
        mp17 = os.path.join(d17, "handoff_manifest.json")
        m17 = json.load(open(mp17))
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
        write_json(d18, "provenance_ledger.json", make_provenance(emap, schema="provenance-ledger/v1"))
        p = run(["freeze", "--case-dir", d18] + FRZ)
        check("溯源台账 v1（数学错误版）freeze 拒 exit 2",
              p.returncode == 2 and "v2" in (p.stderr + p.stdout))
        write_json(d18, "provenance_ledger.json", make_provenance(emap, hollow=True))
        p = run(["freeze", "--case-dir", d18] + FRZ)
        check("stock>0 而 composition 空壳 freeze 拒 exit 2",
              p.returncode == 2 and "空壳" in (p.stderr + p.stdout))
        write_json(d18, "provenance_ledger.json", make_provenance(emap, bad_closure=True))
        p = run(["freeze", "--case-dir", d18] + FRZ)
        check("closure 自报 100 但按 composition 重算不闭合 freeze 拒 exit 2",
              p.returncode == 2 and "重算" in (p.stderr + p.stdout))
        write_json(d18, "provenance_ledger.json", make_provenance(emap, wrong_sha=True))
        p = run(["freeze", "--case-dir", d18] + FRZ)
        check("成员集哈希错配 freeze 拒 exit 2", p.returncode == 2 and "哈希不符" in (p.stderr + p.stdout))
        write_json(d18, "provenance_ledger.json",
                   make_provenance({"E1": ["0xabc"], "E_ghost": ["0xffff"]}))
        p = run(["freeze", "--case-dir", d18] + FRZ)
        check("台账实体集与名册不一致 freeze 拒 exit 2",
              p.returncode == 2 and "实体集" in (p.stderr + p.stdout))
        write_json(d18, "provenance_ledger.json", make_provenance(emap, stable=False))
        p = run(["freeze", "--case-dir", d18] + FRZ)
        check("敏感性不稳 freeze 拒 exit 2", p.returncode == 2 and "敏感性" in (p.stderr + p.stdout))
        write_json(d18, "provenance_ledger.json", make_provenance(emap))
        p = run(["freeze", "--case-dir", d18] + FRZ)
        check("台账修复后 freeze 放行 exit 0", p.returncode == 0)

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
