#!/usr/bin/env python3
"""聚类质量三件套离线测试（A4/A5/A7 2026-07-22）。

  T1  label_lookup --blind-serial：serial 命中不进主输出（文本+JSONL），封存文件完整；
      不盲化时 [SERIAL] 正常出现（回归）；--unseal 能打印封存内容；
      环境变量 CHIP_BLIND_SERIAL=1 与参数等价；设施类输出不受盲化影响。
  T2  accumulate_offenders 冲突检测阳性构造：候选庄家地址在主库是 cex →
      conflicts 报告（json+md）生成、severity=primary、两侧证据在场、不阻塞候选产出。
  T3  cluster_sensitivity 迷你账本冒烟：单源边移除报敏感 + 门槛±10% 判级翻转报敏感。

全部在临时目录构造数据，不触碰真实标签库/案目录。
"""
import csv
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
LOOKUP = os.path.join(HERE, "..", "labels", "label_lookup.py")
ACCUM = os.path.join(HERE, "..", "labels", "accumulate_offenders.py")
SENS = os.path.join(HERE, "..", "evm", "cluster_sensitivity.py")

SERIAL_ADDR = "0x" + "a1" * 20
CEX_ADDR = "0x" + "b2" * 20
PLAIN_ADDR = "0x" + "c3" * 20

FIELDS = ["address", "chain", "name", "category", "tier", "source", "added_date",
          "evidence", "risk_flags", "merge_policy", "balance_policy",
          "source_snapshot_at", "verified_at", "status", "raw_labels"]


def make_labels_dir(tmp):
    d = os.path.join(tmp, "labels")
    os.makedirs(d, exist_ok=True)
    rows = [
        {"address": SERIAL_ADDR, "chain": "bsc", "name": "惯犯庄家（X案·庄#1）",
         "category": "serial-actor", "tier": "identity", "source": "serial-offenders",
         "added_date": "2026-07-01", "evidence": "X案 whale_group「庄#1」",
         "risk_flags": "serial-offender", "verified_at": "2026-07-01"},
        {"address": CEX_ADDR, "chain": "bsc", "name": "TestCEX hot wallet",
         "category": "cex", "tier": "exclude", "source": "manual",
         "added_date": "2026-07-01", "evidence": "测试设施行", "risk_flags": "",
         "verified_at": "2026-07-01"},
    ]
    with open(os.path.join(d, "labels-bsc.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})
    return d


def run(cmd, env_extra=None, cwd=None):
    env = dict(os.environ)
    env.pop("CHIP_BLIND_SERIAL", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable] + cmd, capture_output=True, text=True,
                          env=env, cwd=cwd)


def t1_blind_serial():
    with tempfile.TemporaryDirectory() as tmp:
        ld = make_labels_dir(tmp)
        base = [LOOKUP, "--chain", "bsc", "--labels-dir", ld, "--no-evm-common",
                SERIAL_ADDR, CEX_ADDR, PLAIN_ADDR]

        # 回归：不盲化时 [SERIAL] 段与惯犯名正常出现
        p = run(base)
        assert p.returncode == 0, p.stderr
        assert "[SERIAL]" in p.stdout and "惯犯庄家" in p.stdout, "不盲化时 SERIAL 段必须在"

        # 盲化：主输出无 serial 痕迹；设施行照常；封存文件完整
        sd = os.path.join(tmp, "case")
        os.makedirs(sd)
        p = run(base + ["--blind-serial", "--sealed-dir", sd])
        assert p.returncode == 0, p.stderr
        for token in ("[SERIAL]", "惯犯", "serial-actor", SERIAL_ADDR):
            assert token not in p.stdout, f"盲化主输出泄露: {token}"
        assert "TestCEX" in p.stdout and "[EXCLUDE]" in p.stdout, "设施类输出不得受盲化影响"
        assert "blind-serial" in p.stderr, "盲化固定提示行应在 stderr"
        sealed_p = os.path.join(sd, "sealed_serial_hits.jsonl")
        assert os.path.exists(sealed_p), "封存文件缺失"
        recs = [json.loads(x) for x in open(sealed_p) if x.strip()]
        assert len(recs) == 1 and recs[0]["address"] == SERIAL_ADDR
        for k in ("name", "category", "evidence", "sealed_at", "context"):
            assert recs[0].get(k), f"封存记录缺字段 {k}"
        assert recs[0]["category"] == "serial-actor"

        # JSONL 盲化：serial 地址 hit:false（等同未命中），cex 照常 hit:true
        p = run(base + ["--json", "--blind-serial", "--sealed-dir", sd])
        rows = [json.loads(x) for x in p.stdout.splitlines() if x.strip()]
        by_addr = {r["address"]: r for r in rows}
        assert by_addr[SERIAL_ADDR]["hit"] is False, "JSONL 盲化下 serial 应呈现未命中"
        assert by_addr[CEX_ADDR]["hit"] is True
        assert "serial" not in json.dumps(by_addr[SERIAL_ADDR]), "JSONL 行不得带盲化标记泄露"

        # 环境变量等价
        p = run(base + ["--sealed-dir", sd], env_extra={"CHIP_BLIND_SERIAL": "1"})
        assert "[SERIAL]" not in p.stdout and "blind-serial" in p.stderr, "环境变量盲化未生效"

        # 揭盲
        p = run([LOOKUP, "--chain", "bsc", "--labels-dir", ld, "--unseal", "--sealed-dir", sd])
        assert p.returncode == 0, p.stderr
        assert SERIAL_ADDR in p.stdout and "惯犯庄家" in p.stdout, "--unseal 必须打印封存详情"
    print("T1 blind-serial: PASS")


def t2_conflict_positive():
    with tempfile.TemporaryDirectory() as tmp:
        ld = make_labels_dir(tmp)   # CEX_ADDR 在主库是 cex/exclude
        # goldset 设施金标：GOLD_ADDR 是设施（主库无行/已被覆盖也要能检出——QUQ 实案形态）
        gold_addr = "0x" + "d4" * 20
        os.makedirs(os.path.join(ld, "benchmark"))
        with open(os.path.join(ld, "benchmark", "goldset.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["chain", "address", "expected", "note", "source_analysis"])
            w.writerow(["bsc", gold_addr, "infrastructure", "测试设施金标", "manual-layer"])
        root = os.path.join(tmp, "root")
        case = os.path.join(root, "测试案分析")
        os.makedirs(case)
        json.dump({
            "token": {"symbol": "TT", "chain": "bsc",
                      "data_cutoff": {"utc": "2026-07-20T00:00:00Z"}},
            "whale_groups": [
                {"label": "大庄#1", "tier": "P0",
                 "addresses": [CEX_ADDR, PLAIN_ADDR, gold_addr]},   # CEX/goldset 双阳性
            ],
        }, open(os.path.join(case, "analysis-state.json"), "w"), ensure_ascii=False)
        out_csv = os.path.join(tmp, "serial_actors.csv")
        p = run([ACCUM, root, f"--labels-dir={ld}", f"--out={out_csv}"])
        assert p.returncode == 0, p.stderr + p.stdout
        assert "身份冲突" in p.stdout and "primary" in p.stdout, "stdout 必须报冲突"
        # 报告文件（json+md，带日期）
        reports = [f for f in os.listdir(tmp) if f.startswith("serial_conflicts_")]
        assert any(f.endswith(".json") for f in reports) and any(f.endswith(".md") for f in reports), \
            f"冲突报告缺失: {reports}"
        jp = os.path.join(tmp, [f for f in reports if f.endswith(".json")][0])
        rep = json.load(open(jp))
        assert rep["total"] >= 2 and rep["primary"] >= 2, rep["total"]
        by_sev = {c["severity"]: c for c in rep["conflicts"]}
        c = by_sev["primary"]
        assert c["address"] == CEX_ADDR
        assert c["label_side"]["category"] == "cex" and c["serial_side"]["evidence"], "两侧证据必须在场"
        cg = by_sev["goldset-infra"]
        assert cg["address"] == gold_addr, "goldset 设施金标冲突未检出（QUQ 覆盖实案形态）"
        # 3.19.1 硬闸：primary/goldset-infra 级冲突地址必须被拦在 CSV 外
        #（--apply 与手动 add_labels 两条入库路径一并挡住；QUQ 0x238a 覆盖事故的防线），
        # 且拦截是外科手术式——干净地址（PLAIN_ADDR）照常产出，不误伤。
        cand = list(csv.DictReader(open(out_csv)))
        assert all(r["address"] != CEX_ADDR for r in cand), "primary 冲突地址必须被硬闸拦在 CSV 外"
        assert all(r["address"] != gold_addr for r in cand), "goldset-infra 冲突地址必须被硬闸拦在 CSV 外"
        assert any(r["address"] == PLAIN_ADDR for r in cand), "干净地址不得被拦截误伤"
        assert "拦截" in p.stdout, "stdout 必须明示硬闸拦截"
        # 干净地址（PLAIN_ADDR 未在主库）不产生冲突
        assert all(cc["address"] != PLAIN_ADDR for cc in rep["conflicts"])
    print("T2 conflict-positive: PASS")


def t3_sensitivity_smoke():
    A, B, C = ("0x" + ch * 40 for ch in "abc")
    with tempfile.TemporaryDirectory() as tmp:
        case = os.path.join(tmp, "case")
        os.makedirs(os.path.join(case, "data"))
        os.makedirs(os.path.join(case, "gmgn"))
        # 供给 1000 枚（decimals=0 简化）；A-B 单源大额边；B-C R1+gas 双源
        json.dump({"decimals": 0}, open(os.path.join(case, "config.json"), "w"))
        json.dump({
            "token": {"symbol": "MINI", "chain": "bsc", "decimals": 0, "total_supply": "1000"},
            "whale_groups": [
                # share 5.2% 贴 P1=5% 线：门槛+10%→5.5% 翻"未达标"；-10%→4.5% 仍 P1
                {"label": "小庄#1", "tier": "P1", "current_share_pct": 5.2,
                 "addresses": [A, B, C]},
            ],
        }, open(os.path.join(case, "analysis-state.json"), "w"), ensure_ascii=False)
        with open(os.path.join(case, "data", "key_edges.csv"), "w") as f:
            f.write("block,ts,tx,from,to,value\n")
            zero = "0x" + "0" * 40
            f.write(f"1,1700000000,0xt0,{zero},{A},1000\n")     # mint
            f.write(f"2,1700000600,0xt1,{A},{B},400\n")          # A→B 40%供给 达标 单源
            f.write(f"3,1700001200,0xt2,{B},{C},20\n")           # B→C 2%供给 达标 + gas 双源
            # 终态: A=600 B=380 C=20；移除 A-B 单源边 → {B,C} 40% 实体持仓脱落 → 敏感
        json.dump({"list": [
            {"address": B, "native_transfer": {"from_address": "0x" + "f" * 40}},
            {"address": C, "native_transfer": {"from_address": "0x" + "f" * 40}},
        ]}, open(os.path.join(case, "gmgn", "bsc_holders_top100.json"), "w"))
        p = run([SENS, "--dir", case, "--no-labels", "--split-frac", "0.10"])
        assert p.returncode == 0, p.stderr + p.stdout
        rep = json.load(open(os.path.join(case, "sensitivity_report.json")))
        e = rep["entities"][0]
        kinds = [f["perturbation"] for f in e["findings"]]
        assert any(k.startswith("①") for k in kinds), f"单源边敏感未检出: {kinds}"
        assert any(k.startswith("③") for k in kinds), f"门槛翻转未检出: {kinds}"
        g = e["grades_under_jitter"]
        assert g["base"] == "P1" and g["threshold_+10%"] == "未达标", g
        assert "FRAGILE" in e["verdict"]
        # B-C 是双源边（R1+gas）：不应作为①单源边报告
        for f_ in e["findings"]:
            if f_["perturbation"] == "①单源边移除":
                assert sorted(f_["edge"]) != sorted([B, C]), "双源边被误报为单源"
    print("T3 sensitivity-smoke: PASS")


def main():
    t1_blind_serial()
    t2_conflict_positive()
    t3_sensitivity_smoke()
    print("PASS: test_cluster_quality 3/3（盲化/冲突阳性/敏感度冒烟）")


if __name__ == "__main__":
    main()
