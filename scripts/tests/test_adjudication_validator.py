#!/usr/bin/env python3
"""adjudication_validator 契约测试（离线合成，八类拒绝全覆盖 + freeze 接入）。

覆盖（schema references/scan-schemas.md §3；v6.8.1 codex 复核后加固）：
  0. template 生成：sha256/成员全集/机器 tier_impact 预填；已存在防覆盖
  1. 正例：全候选成员级填毕 → validate exit 0；freeze 全链路（完整 READY 案）放行
  2. ①缺文件（无裁决台账）→ freeze exit 2
  3. ②少裁/未知 ID → exit 2；源报告 schema 错版 → exit 2
  4. ③重复 ID → exit 2
  5. ④candidate_sha256 不符（源报告候选内容变）→ exit 2
  6. ⑤部分成员未裁 → exit 2
  7. ⑥tier_impact 伪造（could_change_tiering / nearest_tier_line 人工改）→ exit 2
  8. unresolved 且可达规模 ≥5% → exit 2；unresolved 且 <5% → 放行
  9. 源报告重跑（整册哈希不符）→ exit 2
 10. ⑦语义交叉约束：confirmed 全员 excluded / excluded 却收编成员 / excluded 缺
     reason / confirmed 无 evidence / adjudicated_at 未填 / candidate_kind 错 → 全拒
 11. ⑧实体名册绑定：confirmed 未传名册 / linked_entity 不在名册 / accepted 未落名册
     → 全拒；名册齐备的 confirmed 正例放行
用法：python3 scripts/tests/test_adjudication_validator.py   退出码 0=PASS / 1=FAIL
"""
import copy
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_handoff_manifest import make_case, setup_freezeable, FRZ, GEN  # noqa: E402

VALIDATOR = os.path.join(HERE, "..", "report", "adjudication_validator.py")
HANDOFF = os.path.join(HERE, "..", "report", "handoff_manifest.py")
FAILS = []


def check(name, cond):
    if not cond:
        FAILS.append(name)
        print(f"FAIL  {name}")
    else:
        print(f"ok    {name}")


def run(script, args):
    if os.path.realpath(script) == os.path.realpath(HANDOFF):
        from test_handoff_manifest import run as run_handoff
        return run_handoff(args)
    return subprocess.run([sys.executable, script] + args, capture_output=True, text=True)


def wj(d, name, obj):
    with open(os.path.join(d, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def make_reports(d, wave_peak=12.0, eqg_pct=3.0, sink_window=2.5,
                 sink_peak=2.5, sink_current=2.5, sink_net=2.5):
    """两候选：1 个 wave（3 成员、峰 wave_peak%）+ 1 个 eqg（2 收方、组 eqg_pct%）。"""
    wj(d, "wave_scan_report.json", {
        "schema": "wave-scan/v5", "edge_order_granularity": "transaction",
        "order_ambiguous": True, "non_formal": False,
        "params": {"edges_evm_v2": "data/v2"}, "scan_universe_count": 5,
        "scan_universe": [{"addr": a, "must_adjudicate": False, "must_reasons": []}
                          for a in ("W1a", "W1b", "W1c", "Ea", "Eb")],
        "must_adjudicate_count": 0,
        "retention_buckets": {"cleared": 3, "partial_exit": 1, "retained": 1},
        "negative_balance_addrs": 0,
        "waves": [{"id": "wave-abc123def456", "member_count": 3,
                   "combined_peak_pct": wave_peak,
                   "members": [{"addr": "W1a"}, {"addr": "W1b"}, {"addr": "W1c"}]}],
        "equal_amount_groups": [{"id": "eqg-1000-deadbeef", "amount_raw": "1000",
                                 "recipients": 2, "group_total_pct": eqg_pct,
                                 "members": ["Ea", "Eb"]}],
        "requires_adjudication": True})
    wj(d, "flow_anomaly_report.json", {
        "schema": "flow-anomaly/v3", "eligible_universe_count": 5,
        "sinks": [{"id": "sink-HubX", "addr": "HubX",
                   "best_window": {"inflow_pct": sink_window, "source_count": 6},
                   "balance": {"historical_peak_pct": sink_peak,
                               "current_balance_pct": sink_current},
                   "all_time": {"net_inflow_pct": sink_net,
                                "qualified_inflow_pct": sink_peak},
                   "sources": []}],
        # v2 起 spray 有对称校验（mode/mode_hits/闭合）——补一个合法 slow_spray 保正向覆盖
        "sprays": [{"id": "spray-SprayY", "addr": "SprayY", "mode": "slow_spray",
                    "mode_hits": {"pulse": {"hit": False}, "pulse_all": {"hit": False},
                                  "slow_spray": {"hit": True}},
                    "all_time": {"outflow_pct": 2.5, "recipient_count": 150,
                                 "fresh_recipient_count": 30},
                    "best_window": None, "recipients_top": ["R1", "R2"],
                    "launch_window": False}],
        "requires_adjudication": True})


def fill_all(d, unresolved_ids=None):
    """template → 全部候选填合法裁决。"""
    p = run(VALIDATOR, ["template", "--case-dir", d, "--force"])
    adj = json.load(open(os.path.join(d, "candidate_adjudications.json")))
    for r in adj["adjudications"]:
        members = r.pop("_members_total")
        if unresolved_ids and r["candidate_id"] in unresolved_ids:
            r["candidate_verdict"] = "unresolved"
            r["excluded_members"] = [{"addr": m, "reason": "身份待查"} for m in members]
        else:
            r["candidate_verdict"] = "excluded"
            r["excluded_members"] = [{"addr": m, "reason": "独立地址，无协同证据"} for m in members]
        r["evidence"] = ["test"]
    adj["adjudicated_at"] = "2026-08-01T00:00:00Z"
    wj(d, "candidate_adjudications.json", adj)
    return adj, p


def main():
    root = tempfile.mkdtemp(prefix="adj_test_")

    # 0+1. template + 正例
    d = os.path.join(root, "ok")
    os.makedirs(d)
    make_reports(d)
    adj, pt = fill_all(d)
    check("template 生成 exit 0 且 4 条候选（wave+eqg+sink+spray）",
          pt.returncode == 0 and len(adj["adjudications"]) == 4)
    check("template 预填 sha256 与机器 tier_impact",
          all(r["candidate_sha256"] and "max_possible_impact" in r["tier_impact"]
              for r in adj["adjudications"]))
    p = run(VALIDATOR, ["template", "--case-dir", d])
    check("template 已存在防覆盖 exit 2", p.returncode == 2)
    p = run(VALIDATOR, ["validate", "--case-dir", d])
    check("正例 validate exit 0", p.returncode == 0)

    # freeze 全链路（v6.8.1：freeze 前置 0 是内联 verify——接入测试须用完整 READY 案）
    from test_handoff_manifest import make_provenance
    dfz = os.path.join(root, "ok_freeze")
    os.makedirs(dfz)
    make_case(dfz)
    make_reports(dfz)          # 覆盖为有候选版本（3 候选）
    run(HANDOFF, ["generate", "--case-dir", dfz, "--status", "READY"] + GEN)
    fill_all(dfz)
    emap = {"E1": ["0xabc"]}
    wj(dfz, "s2_entity_members.json", emap)
    wj(dfz, "analysis-state.json", {"whale_groups": []})
    p = run(HANDOFF, ["freeze", "--case-dir", dfz] + FRZ)
    check("裁决闭环但缺溯源台账 freeze exit 2",
          p.returncode == 2 and "provenance" in (p.stderr + p.stdout))
    wj(dfz, "provenance_ledger.json", make_provenance(dfz, emap))
    p = run(HANDOFF, ["freeze", "--case-dir", dfz] + FRZ)
    check("裁决＋溯源双闭环后 freeze 放行 exit 0", p.returncode == 0)

    # 2. ①缺台账 → freeze 拒（完整 READY 案，其余台账齐备，只缺裁决）
    d2 = os.path.join(root, "nofile")
    os.makedirs(d2)
    make_case(d2)
    make_reports(d2)
    run(HANDOFF, ["generate", "--case-dir", d2, "--status", "READY"] + GEN)
    wj(d2, "s2_entity_members.json", emap)
    wj(d2, "analysis-state.json", {"entities": []})
    wj(d2, "provenance_ledger.json", make_provenance(d2, emap))
    p = run(HANDOFF, ["freeze", "--case-dir", d2] + FRZ)
    check("缺裁决台账 freeze exit 2", p.returncode == 2 and "裁决闭环" in (p.stderr + p.stdout))

    # 3. ②少裁
    d3 = os.path.join(root, "missing")
    os.makedirs(d3)
    make_reports(d3)
    adj, _ = fill_all(d3)
    adj["adjudications"] = adj["adjudications"][:2]
    wj(d3, "candidate_adjudications.json", adj)
    p = run(VALIDATOR, ["validate", "--case-dir", d3])
    check("少裁 exit 2", p.returncode == 2 and "未裁决" in p.stdout)

    # 4. ③重复 ID
    d4 = os.path.join(root, "dup")
    os.makedirs(d4)
    make_reports(d4)
    adj, _ = fill_all(d4)
    adj["adjudications"].append(copy.deepcopy(adj["adjudications"][0]))
    wj(d4, "candidate_adjudications.json", adj)
    p = run(VALIDATOR, ["validate", "--case-dir", d4])
    check("重复 ID exit 2", p.returncode == 2 and "重复" in p.stdout)

    # 5. ④候选内容变（改源报告一个数值但保持文件哈希登记同步失效）
    d5 = os.path.join(root, "shadrift")
    os.makedirs(d5)
    make_reports(d5)
    adj, _ = fill_all(d5)
    make_reports(d5, wave_peak=13.0)  # 源报告重写：wave 候选内容变
    # 同步 source_reports 哈希（只测 candidate_sha256 这一层）
    import hashlib
    for name in ("wave_scan_report.json", "flow_anomaly_report.json"):
        adj["source_reports"][name] = hashlib.sha256(
            open(os.path.join(d5, name), "rb").read()).hexdigest()
    wj(d5, "candidate_adjudications.json", adj)
    p = run(VALIDATOR, ["validate", "--case-dir", d5])
    check("候选内容变 sha256 失效 exit 2", p.returncode == 2 and "candidate_sha256" in p.stdout)

    # 6. ⑤部分成员未裁
    d6 = os.path.join(root, "uncov")
    os.makedirs(d6)
    make_reports(d6)
    adj, _ = fill_all(d6)
    for r in adj["adjudications"]:
        if r["candidate_id"].startswith("wave-"):
            r["excluded_members"] = r["excluded_members"][:2]  # 3 成员只裁 2
    wj(d6, "candidate_adjudications.json", adj)
    p = run(VALIDATOR, ["validate", "--case-dir", d6])
    check("部分成员未裁 exit 2", p.returncode == 2 and "未裁" in p.stdout)

    # 7. ⑥tier_impact 伪造
    d7 = os.path.join(root, "fake")
    os.makedirs(d7)
    make_reports(d7)  # wave 12% ≥5% → 机器 could_change_tiering=true
    adj, _ = fill_all(d7)
    for r in adj["adjudications"]:
        if r["candidate_id"].startswith("wave-"):
            r["tier_impact"]["max_possible_impact"]["could_change_tiering"] = False
    wj(d7, "candidate_adjudications.json", adj)
    p = run(VALIDATOR, ["validate", "--case-dir", d7])
    check("tier_impact 伪造 exit 2", p.returncode == 2 and "机器重算" in p.stdout)

    # 8. unresolved 分档：wave 12% unresolved → 拒；eqg 3% unresolved → 放行
    d8 = os.path.join(root, "unres_big")
    os.makedirs(d8)
    make_reports(d8)
    fill_all(d8, unresolved_ids={"wave-abc123def456"})
    p = run(VALIDATOR, ["validate", "--case-dir", d8])
    check("unresolved 且 ≥5% exit 2", p.returncode == 2 and "unresolved" in p.stdout)
    d8b = os.path.join(root, "unres_small")
    os.makedirs(d8b)
    make_reports(d8b)
    fill_all(d8b, unresolved_ids={"eqg-1000-deadbeef"})
    p = run(VALIDATOR, ["validate", "--case-dir", d8b])
    check("unresolved 且 <5% 放行 exit 0", p.returncode == 0)

    # high-3 反例：三个不重叠窗口各 4%，单个 best_window<5%，但累计库存历史峰值/现仓/净流入
    # 已达 12%。旧 validator 只取 best_window=4% 会放行；修复后机器影响=12% 必须阻断。
    d8c = os.path.join(root, "unres_sink_multiwindow")
    os.makedirs(d8c)
    make_reports(d8c, sink_window=4.0, sink_peak=12.0, sink_current=12.0, sink_net=12.0)
    fill_all(d8c, unresolved_ids={"sink-HubX"})
    p = run(VALIDATOR, ["validate", "--case-dir", d8c])
    check("sink 多窗口累计 12%（单窗 4%）unresolved 必须 exit 2",
          p.returncode == 2 and "unresolved" in p.stdout)

    # 9. 源报告重跑（整册哈希不符）
    d9 = os.path.join(root, "stale")
    os.makedirs(d9)
    make_reports(d9)
    fill_all(d9)
    make_reports(d9, eqg_pct=3.5)  # 重跑源报告，台账未更新
    p = run(VALIDATOR, ["validate", "--case-dir", d9])
    check("源报告重跑整册过期 exit 2", p.returncode == 2 and "source_reports" in p.stdout)

    # 10. ⑦语义交叉约束（v6.8.1：形式全覆盖但语义自相矛盾的敷衍裁决全拒）
    WMEM = ["W1a", "W1b", "W1c"]

    def set_confirm(dx, accepted, excluded, eid="EW", evidence=None, mutate=None):
        adj, _ = fill_all(dx)
        for r in adj["adjudications"]:
            if r["candidate_id"].startswith("wave-"):
                r["candidate_verdict"] = "pattern_confirmed"
                r["accepted_members"] = accepted
                r["excluded_members"] = excluded
                r["linked_entity_id"] = eid
                r["evidence"] = ["边证据: 定向喂币"] if evidence is None else evidence
                if mutate:
                    mutate(r)
        wj(dx, "candidate_adjudications.json", adj)
        wj(dx, "ents.json", {"EW": WMEM})
        return adj

    d10 = os.path.join(root, "semantic")
    os.makedirs(d10)
    make_reports(d10)
    set_confirm(d10, [], [{"addr": m, "reason": "查无协同"} for m in WMEM])
    p = run(VALIDATOR, ["validate", "--case-dir", d10, "--entity-file", "ents.json"])
    check("confirmed 但全员 excluded（矛盾裁决）exit 2",
          p.returncode == 2 and "自相矛盾" in p.stdout)
    set_confirm(d10, WMEM, [], evidence=[])
    p = run(VALIDATOR, ["validate", "--case-dir", d10, "--entity-file", "ents.json"])
    check("confirmed 但 evidence 空 exit 2", p.returncode == 2 and "证据" in p.stdout)
    adj, _ = fill_all(d10)
    for r in adj["adjudications"]:
        if r["candidate_id"].startswith("wave-"):
            r["accepted_members"] = ["W1a"]          # excluded verdict 却收编成员
            r["excluded_members"] = [{"addr": m, "reason": "独立"} for m in WMEM[1:]]
    wj(d10, "candidate_adjudications.json", adj)
    p = run(VALIDATOR, ["validate", "--case-dir", d10])
    check("excluded 却收编成员 exit 2", p.returncode == 2 and "收编" in p.stdout)
    adj, _ = fill_all(d10)
    for r in adj["adjudications"]:
        if r["candidate_id"].startswith("wave-"):
            r["excluded_members"] = [{"addr": m} for m in WMEM]   # 缺 reason
    wj(d10, "candidate_adjudications.json", adj)
    p = run(VALIDATOR, ["validate", "--case-dir", d10])
    check("excluded 成员缺排除理由 exit 2", p.returncode == 2 and "理由" in p.stdout)
    adj, _ = fill_all(d10)
    adj["adjudicated_at"] = None
    wj(d10, "candidate_adjudications.json", adj)
    p = run(VALIDATOR, ["validate", "--case-dir", d10])
    check("adjudicated_at 未填 exit 2", p.returncode == 2 and "adjudicated_at" in p.stdout)
    adj, _ = fill_all(d10)
    for r in adj["adjudications"]:
        if r["candidate_id"].startswith("wave-"):
            r["candidate_kind"] = "spray"
    wj(d10, "candidate_adjudications.json", adj)
    p = run(VALIDATOR, ["validate", "--case-dir", d10])
    check("candidate_kind 与机器不符 exit 2", p.returncode == 2 and "candidate_kind" in p.stdout)
    adj, _ = fill_all(d10)
    for r in adj["adjudications"]:
        if r["candidate_id"].startswith("wave-"):
            r["tier_impact"]["max_possible_impact"]["nearest_tier_line"] = "50%"
    wj(d10, "candidate_adjudications.json", adj)
    p = run(VALIDATOR, ["validate", "--case-dir", d10])
    check("nearest_tier_line 伪造 exit 2", p.returncode == 2 and "机器重算" in p.stdout)

    # 11. ⑧实体名册绑定
    d11 = os.path.join(root, "binding")
    os.makedirs(d11)
    make_reports(d11)
    set_confirm(d11, WMEM, [])
    p = run(VALIDATOR, ["validate", "--case-dir", d11])
    check("confirmed 未传 --entity-file exit 2", p.returncode == 2 and "entity-file" in p.stdout)
    set_confirm(d11, WMEM, [], eid="E_nonexist")
    p = run(VALIDATOR, ["validate", "--case-dir", d11, "--entity-file", "ents.json"])
    check("linked_entity 不在名册 exit 2", p.returncode == 2 and "不存在于实体名册" in p.stdout)
    set_confirm(d11, WMEM, [])
    wj(d11, "ents.json", {"EW": ["W1a", "W1b"]})    # 名册少 W1c
    p = run(VALIDATOR, ["validate", "--case-dir", d11, "--entity-file", "ents.json"])
    check("accepted 成员未落名册 exit 2", p.returncode == 2 and "没真并" in p.stdout)
    set_confirm(d11, WMEM, [])
    p = run(VALIDATOR, ["validate", "--case-dir", d11, "--entity-file", "ents.json"])
    check("confirmed＋名册齐备正例 exit 0", p.returncode == 0)

    # 3b. 源报告 schema 错版 → 拒（空壳/旧版不得形成"零候选已闭环"）
    d3b = os.path.join(root, "srcschema")
    os.makedirs(d3b)
    make_reports(d3b)
    fill_all(d3b)
    ws = json.load(open(os.path.join(d3b, "wave_scan_report.json")))
    ws["schema"] = "wave-scan/v1"
    wj(d3b, "wave_scan_report.json", ws)
    p = run(VALIDATOR, ["validate", "--case-dir", d3b])
    check("源报告 schema 错版 exit 2", p.returncode == 2 and "schema" in p.stdout)

    print(f"\n{'PASS' if not FAILS else 'FAIL'}：{len(FAILS)} 项失败")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
