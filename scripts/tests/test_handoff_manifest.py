#!/usr/bin/env python3
"""handoff_manifest 契约测试（离线，黑盒 subprocess 调 CLI）。

覆盖（split-run §2 交接契约的反例集）：
  1. READY 正例全链路：generate → verify exit 0
  2. BLOCKED 拒收：status=BLOCKED → verify exit 2
  3. 哈希漂移：产物被改 → verify exit 2
  4. schema 不兼容：consumer_min_schema 超出支持集 → verify exit 2
  5. freeze 前揭盲拒绝：--check-unseal 无 entity_freeze.json → exit 2；freeze 后 → exit 0
  6. gate 语义漂移：accounting_mode.json verdict 被改 → verify exit 2
  7. blocking 异常未解决却报 READY → verify exit 2
  8. generate READY 缺必备契约件 → exit 2
  9. receipt 追加两条且 blind_mode 跟随环境变量
 10. supersede：二次 generate 归档旧 manifest
 12. READY 缺 wave_scan_report.json 即拒（W1 漏检复盘 2026-08-01：波次扫描是 READY 必产件）
 13. wave_scan_report.json 空壳（缺 requires_adjudication 等字段）→ verify exit 2
用法：python3 scripts/tests/test_handoff_manifest.py   退出码 0=PASS / 1=FAIL
"""
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
    write_json(d, "wave_scan_report.json", {"schema": "wave-scan/v1", "cleared_layer_count": 0,
                                            "waves": [], "equal_amount_groups": [],
                                            "requires_adjudication": False})
    os.makedirs(os.path.join(d, "sealed"), exist_ok=True)
    with open(os.path.join(d, "sealed", "stage1_hypotheses.sealed.md"), "w") as f:
        f.write("> −2 实体冻结前禁读\n假说：无\n")


GEN = ["--mode", "easy", "--producer-model", "test-model", "--chain", "bsc", "--contract", "0x0"]


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
        check("manifest 自动 gate 两个", set(m["gates"]) == {"accounting_gate", "supply_truth_gate"})
        p = run(["verify", "--case-dir", d])
        check("verify READY exit 0", p.returncode == 0)

        # 9. receipt（在正例目录顺手验）
        p = run(["receipt", "--case-dir", d, "--step", "A1", "--cmd", "collect", "--exit", "0",
                 "--artifacts", "data/transfers.csv"], env={"CHIP_BLIND_SERIAL": "1"})
        p2 = run(["receipt", "--case-dir", d, "--step", "A2", "--cmd", "recon", "--exit", "0"])
        rows = json.load(open(os.path.join(d, "stage1_receipts.json")))
        check("receipt 追加两条", p.returncode == 0 and p2.returncode == 0 and len(rows) == 2)
        check("receipt blind_mode 跟随环境", rows[0]["blind_mode"] is True and rows[1]["blind_mode"] is False)

        # 5. freeze 前揭盲拒绝 → freeze → 放行
        p = run(["freeze", "--case-dir", d, "--check-unseal"])
        check("freeze 前揭盲拒绝 exit 2", p.returncode == 2)
        write_json(d, "analysis-state.json", {"whale_groups": [{"id": "E1", "members": ["0xabc"]}]})
        p = run(["freeze", "--case-dir", d, "--members", "analysis-state.json", "--pending", "c2 待裁决"])
        check("freeze 初次 exit 0", p.returncode == 0)
        p = run(["freeze", "--case-dir", d, "--check-unseal"])
        check("freeze 后揭盲放行 exit 0", p.returncode == 0)
        write_json(d, "analysis-state.json", {"whale_groups": [{"id": "E1", "members": ["0xabc", "0xdef"]}]})
        p = run(["freeze", "--case-dir", d, "--members", "analysis-state.json"])
        fz = json.load(open(os.path.join(d, "entity_freeze.json")))
        check("freeze 变更走 revision 追加", p.returncode == 0 and len(fz["revisions"]) == 1)

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

        # 3. 哈希漂移
        d3 = os.path.join(root, "case_drift")
        os.makedirs(d3)
        make_case(d3)
        run(["generate", "--case-dir", d3, "--status", "READY"] + GEN)
        with open(os.path.join(d3, "data", "transfers.csv"), "a") as f:
            f.write("3,4\n")
        p = run(["verify", "--case-dir", d3])
        check("哈希漂移拒收 exit 2", p.returncode == 2 and "漂移" in p.stdout)

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
        write_json(d13, "wave_scan_report.json", {"schema": "wave-scan/v1"})
        run(["generate", "--case-dir", d13, "--status", "READY"] + GEN)
        p = run(["verify", "--case-dir", d13])
        check("wave_scan_report 空壳 verify 拒收 exit 2", p.returncode == 2 and "wave_scan_report" in p.stdout)
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
