#!/usr/bin/env python3
"""adjudication_validator 契约测试（离线合成，六类拒绝全覆盖 + freeze 接入）。

覆盖（schema references/scan-schemas.md §3）：
  0. template 生成：sha256/成员全集/机器 tier_impact 预填；已存在防覆盖
  1. 正例：全候选成员级填毕 → validate exit 0 → freeze 放行
  2. ①缺文件（无裁决台账）→ freeze exit 2
  3. ②少裁/未知 ID → exit 2
  4. ③重复 ID → exit 2
  5. ④candidate_sha256 不符（源报告候选内容变）→ exit 2
  6. ⑤部分成员未裁 → exit 2
  7. ⑥tier_impact 伪造（could_change_tiering 人工改假）→ exit 2
  8. unresolved 且可达规模 ≥5% → exit 2；unresolved 且 <5% → 放行
  9. 源报告重跑（整册哈希不符）→ exit 2
用法：python3 scripts/tests/test_adjudication_validator.py   退出码 0=PASS / 1=FAIL
"""
import copy
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
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
    return subprocess.run([sys.executable, script] + args, capture_output=True, text=True)


def wj(d, name, obj):
    with open(os.path.join(d, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def make_reports(d, wave_peak=12.0, eqg_pct=3.0):
    """两候选：1 个 wave（3 成员、峰 wave_peak%）+ 1 个 eqg（2 收方、组 eqg_pct%）。"""
    wj(d, "wave_scan_report.json", {
        "schema": "wave-scan/v2", "scan_universe_count": 5,
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
        "schema": "flow-anomaly/v1", "eligible_universe_count": 5,
        "sinks": [{"id": "sink-HubX", "addr": "HubX",
                   "best_window": {"inflow_pct": 2.5, "source_count": 6},
                   "sources": []}],
        "sprays": [], "requires_adjudication": True})


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
    check("template 生成 exit 0 且 3 条候选", pt.returncode == 0 and len(adj["adjudications"]) == 3)
    check("template 预填 sha256 与机器 tier_impact",
          all(r["candidate_sha256"] and "max_possible_impact" in r["tier_impact"]
              for r in adj["adjudications"]))
    p = run(VALIDATOR, ["template", "--case-dir", d])
    check("template 已存在防覆盖 exit 2", p.returncode == 2)
    p = run(VALIDATOR, ["validate", "--case-dir", d])
    check("正例 validate exit 0", p.returncode == 0)

    # freeze 接入：裁决闭环但缺溯源台账 → 拒；补台账 → 放行（v6.8.0 三重门禁）
    wj(d, "analysis-state.json", {"entities": []})
    p = run(HANDOFF, ["freeze", "--case-dir", d, "--members", "analysis-state.json"])
    check("裁决闭环但缺溯源台账 freeze exit 2",
          p.returncode == 2 and "provenance" in (p.stderr + p.stdout))
    wj(d, "provenance_ledger.json", {
        "schema": "provenance-ledger/v1",
        "entities": [{"entity_id": "e_test", "member_count": 1,
                      "anchors": {"current": {"stock_raw": "0", "composition": []},
                                  "peak": {"stock_raw": "100", "composition": []}},
                      "closure_check": {"current_sum_pct": 0, "peak_sum_pct": 100.0}}]})
    p = run(HANDOFF, ["freeze", "--case-dir", d, "--members", "analysis-state.json"])
    check("裁决＋溯源双闭环后 freeze 放行 exit 0", p.returncode == 0)
    # 溯源闭合破坏 → freeze 拒
    wj(d, "provenance_ledger.json", {
        "schema": "provenance-ledger/v1",
        "entities": [{"entity_id": "e_test", "member_count": 1,
                      "anchors": {"current": {"stock_raw": "0", "composition": []},
                                  "peak": {"stock_raw": "100", "composition": []}},
                      "closure_check": {"current_sum_pct": 0, "peak_sum_pct": 63.0}}]})
    wj(d, "analysis-state.json", {"entities": ["changed"]})
    p = run(HANDOFF, ["freeze", "--case-dir", d, "--members", "analysis-state.json"])
    check("溯源闭合失败 freeze exit 2", p.returncode == 2 and "闭合" in (p.stderr + p.stdout))

    # 2. ①缺台账 → freeze 拒
    d2 = os.path.join(root, "nofile")
    os.makedirs(d2)
    make_reports(d2)
    wj(d2, "analysis-state.json", {"entities": []})
    p = run(HANDOFF, ["freeze", "--case-dir", d2, "--members", "analysis-state.json"])
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

    # 9. 源报告重跑（整册哈希不符）
    d9 = os.path.join(root, "stale")
    os.makedirs(d9)
    make_reports(d9)
    fill_all(d9)
    make_reports(d9, eqg_pct=3.5)  # 重跑源报告，台账未更新
    p = run(VALIDATOR, ["validate", "--case-dir", d9])
    check("源报告重跑整册过期 exit 2", p.returncode == 2 and "source_reports" in p.stdout)

    print(f"\n{'PASS' if not FAILS else 'FAIL'}：{len(FAILS)} 项失败")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
