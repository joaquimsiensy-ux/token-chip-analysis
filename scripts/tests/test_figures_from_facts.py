#!/usr/bin/env python3
"""图表同源化（figures_from_facts）离线测试（3.19，A8）：三模式契约。

契约：fig1 从 state 直出成图 / flow spec 宏渲染同源且宏错必炸 / check 图2终值对账。
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
        "e1": {"label": "大庄#1",
               "addresses": ["0xAA00000000000000000000000000000000000001"],
               "current_raw": str(278_400_000 * 10**18),
               "peak_raw": str(687_000_000 * 10**18),
               "merge_evidence_earliest": "2026-05-03"},
    },
    "metrics": {},
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
    "footnote": "归并证据最早 {{e1.merged_since}}",
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

        # 2) flow：宏渲染同源出图；lifecycle_flow 的 nodes/edges 结构由绘图函数
        #    自行校验，这里核心契约=宏全渲染（数字同源）
        spec_p = os.path.join(td, "spec.json")
        json.dump(SPEC, open(spec_p, "w"))
        out2 = os.path.join(td, "flow.png")
        r = run(["flow", "--facts", fp, "--spec", spec_p, "--out", out2])
        assert r.returncode == 0 and os.path.getsize(out2) > 5_000, \
            f"flow 渲染出图失败: {r.stdout} {r.stderr}"

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

    print("PASS: figures_from_facts fig1直出/flow宏同源/宏错必炸/check终值对账/"
          "overlay合并线(含双fail-closed)，五契约全过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
