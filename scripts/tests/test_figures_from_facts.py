#!/usr/bin/env python3
"""图表同源化（figures_from_facts）离线测试（3.19，A8）：三模式契约。

契约：fig1 从 state 直出成图 / flow spec 宏渲染同源且宏错必炸 /
check 图2终值对账并守住临时托管期间的经济归属连续性。
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FFF = os.path.join(HERE, "..", "report", "figures_from_facts.py")

FACTS = {
    "token": {"symbol": "TT", "decimals": 18, "total_supply_raw": str(10**9 * 10**18)},
    "entities": {
        "e1": {"label": "大庄#1", "tier": "P0",
               "addresses": ["0xAA00000000000000000000000000000000000001"],
               "current_raw": str(278_400_000 * 10**18),
               "peak_raw": str(687_000_000 * 10**18),
               "merge_evidence_earliest": "2026-05-03"},
    },
    "metrics": {
        "beneficiary_count": {"value": 903, "unit": " 个受益地址"},
        "event_date": {"value": "2026-03-21", "unit": ""},
    },
}
STATE = {
    "token": {"symbol": "TT"},
    "camp_share_series": {
        "dates": ["2026-01-01", "2026-01-02", "2026-01-03"],
        "series": {"大庄": [10.0, 20.0, 27.84], "散户": [50.0, 40.0, 30.0]},
    },
}
SPEC = {
    "title": "{{e1.label}} 全周期流转",
    "nodes": [{"id": "n1", "col": 0, "title": "{{e1.label}}", "kind": "whale",
               "lines": ["现持 {{e1.amount_share}}"]},
              {"id": "n2", "col": 1, "title": "交易所", "kind": "cex",
               "lines": ["充入若干"]}],
    "edges": [{"src": "n1", "dst": "n2", "label": "峰值 {{e1.peak_share}}",
               "color": "cex"}],
    "subtitle": "{{e1.naddr}} 个成员；{{m:beneficiary_count}}",
    "footnote": "归并证据最早 {{e1.merged_since}}；事件日 {{m:event_date}}",
}


def run(args):
    return subprocess.run([sys.executable, FFF] + args,
                          capture_output=True, text=True)


def main():
    with tempfile.TemporaryDirectory() as td:
        fp = os.path.join(td, "facts.json")
        sp = os.path.join(td, "state.json")
        json.dump(FACTS, open(fp, "w"))
        json.dump(STATE, open(sp, "w"))

        # 1) fig1：从 state 直出成图
        out1 = os.path.join(td, "fig1.png")
        r = run(["fig1", "--state", sp, "--token", "TT", "--out", out1])
        assert r.returncode == 0 and os.path.getsize(out1) > 10_000, \
            f"fig1 直出失败: {r.stdout} {r.stderr}"

        # 1b) schema 契约：旧的逐日对象列表必须可读地失败，不能抛 AttributeError
        bad_state = {
            "token": {"symbol": "TT"},
            "camp_share_series": [
                {"ts": "2026-01-01", "大庄": 10.0, "散户": 50.0},
            ],
        }
        bad_sp = os.path.join(td, "bad-state.json")
        json.dump(bad_state, open(bad_sp, "w"))
        r = run(["fig1", "--state", bad_sp, "--token", "TT",
                 "--out", os.path.join(td, "bad-fig1.png")])
        assert r.returncode != 0 and "必须是" in (r.stdout + r.stderr), \
            f"逐日对象列表应按契约失败: {r.stdout} {r.stderr}"

        # 2) flow：宏渲染同源出图；lifecycle_flow 的 nodes/edges 结构由绘图函数
        #    自行校验，这里核心契约=宏全渲染（数字同源）
        spec_p = os.path.join(td, "spec.json")
        json.dump(SPEC, open(spec_p, "w"))
        out2 = os.path.join(td, "flow.png")
        r = run(["flow", "--facts", fp, "--spec", spec_p, "--out", out2])
        assert r.returncode == 0 and os.path.getsize(out2) > 5_000, \
            f"flow 渲染出图失败: {r.stdout} {r.stderr}"

        # 2b) strict：用户可见案情数字必须走 facts 宏；实体标签 #1 / V3 等固定号豁免
        r = run(["flow", "--facts", fp, "--spec", spec_p, "--out", out2,
                 "--strict-text-numbers"])
        assert r.returncode == 0, f"全宏 spec 的 strict 应过: {r.stdout} {r.stderr}"
        literal = json.loads(json.dumps(SPEC))
        literal["subtitle"] = "行为同群；1044 个地址"
        json.dump(literal, open(spec_p, "w"))
        r = run(["flow", "--facts", fp, "--spec", spec_p,
                 "--out", os.path.join(td, "literal.png"), "--strict-text-numbers"])
        assert r.returncode != 0 and "未走 facts 宏" in (r.stdout + r.stderr), \
            f"硬编码成员数应被 strict 拒绝: {r.stdout} {r.stderr}"

        # 3) flow 宏名打错必炸（不许静默画出带 {{...}} 的图）
        bad = json.loads(json.dumps(SPEC))
        bad["nodes"][0]["label"] = "{{e1.shrae}}"
        json.dump(bad, open(spec_p, "w"))
        r = run(["flow", "--facts", fp, "--spec", spec_p,
                 "--out", os.path.join(td, "bad.png")])
        assert r.returncode != 0, "拼错宏应失败"

        # 4) check：末点与 facts 一致 → PASS；偏 0.5pp → FAIL
        ser_p = os.path.join(td, "ws.json")
        json.dump([{"entity_id": "e1", "label": "大庄#1",
                    "ts": ["2026-01-01", "2026-01-03"], "pct": [10.0, 27.84]}],
                  open(ser_p, "w"))
        r = run(["check", "--facts", fp, "--series", ser_p])
        assert r.returncode == 0 and "PASS" in r.stdout, f"终值一致应过: {r.stdout}"
        json.dump([{"entity_id": "e1", "ts": ["2026-01-03"], "pct": [28.34]}],
                  open(ser_p, "w"))
        r = run(["check", "--facts", fp, "--series", ser_p])
        assert r.returncode != 0 and "不同源" in r.stdout, f"偏 0.5pp 应挂: {r.stdout}"

        # 4b) 临时托管区间：末点即使对，锁仓中途掉到 0 也必须失败；
        #     经济归属线维持在可归属本金以上才通过。
        custody = {
            "label": "测试锁仓本金",
            "start_date": "2026-01-02",
            "end_date": "2026-01-03",
            "minimum_raw": str(200_000_000 * 10**18),
        }
        bad_custody = [{
            "entity_id": "e1",
            "ts": ["2026-01-01", "2026-01-02", "2026-01-03"],
            "pct": [20.0, 0.0, 27.84],
            "temporary_custody_checks": [custody],
        }]
        json.dump(bad_custody, open(ser_p, "w"))
        r = run(["check", "--facts", fp, "--series", ser_p])
        assert r.returncode != 0 and "临时托管误画成清仓" in r.stdout, \
            f"锁仓中途归零应挂: {r.stdout}"
        good_custody = json.loads(json.dumps(bad_custody))
        good_custody[0]["pct"] = [20.0, 20.0, 27.84]
        json.dump(good_custody, open(ser_p, "w"))
        r = run(["check", "--facts", fp, "--series", ser_p])
        assert r.returncode == 0 and "连续性检查 1 条通过" in r.stdout, \
            f"锁仓经济归属连续应过: {r.stdout}"

        # 5) fig1 --overlay 合并口径线（v3.33）：正常出图 + 两条 fail-closed
        out5 = os.path.join(td, "fig1_ov.png")
        r = run(["fig1", "--state", sp, "--token", "TT", "--out", out5,
                 "--overlay", "合并=大庄+散户"])
        assert r.returncode == 0 and os.path.getsize(out5) > 10_000, \
            f"overlay 出图失败: {r.stdout} {r.stderr}"
        assert os.path.getsize(out5) != os.path.getsize(out1), "带 overlay 的图应与不带的不同"
        # SystemExit 的消息走 stderr（与 mode_fig1 内其他 fail 一致），两路都收
        r = run(["fig1", "--state", sp, "--out", os.path.join(td, "x.png"),
                 "--overlay", "X=大庄+查无此阵营"])
        assert r.returncode != 0 and "不存在的阵营" in (r.stdout + r.stderr), \
            f"引用不存在阵营应 fail-closed: {r.stdout} {r.stderr}"
        r = run(["fig1", "--state", sp, "--out", os.path.join(td, "y.png"),
                 "--overlay", "缺等号"])
        assert r.returncode != 0 and "格式应为" in (r.stdout + r.stderr), \
            f"格式错应 fail-closed: {r.stdout} {r.stderr}"

    print("PASS: figures_from_facts fig1直出/schema拒绝旧列表/flow宏同源/"
          "strict拒绝硬编码图内数字/宏错必炸/check终值对账+临时托管连续性/"
          "overlay合并线(含双fail-closed)，八契约全过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
