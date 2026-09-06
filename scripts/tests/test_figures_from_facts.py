#!/usr/bin/env python3
"""图表同源化（figures_from_facts）离线测试（3.19，A8）：三模式契约。

契约：fig1 从 state 直出成图 / flow spec 宏渲染同源且宏错必炸 / check 图2终值对账。
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from copy import deepcopy
from datetime import datetime
from unittest.mock import patch

HERE = os.path.dirname(os.path.abspath(__file__))
FFF = os.path.join(HERE, "..", "report", "figures_from_facts.py")
REPORT_DIR = os.path.join(HERE, "..", "report")
LEGEND_RECEIPT = "fig1_legend_receipt.json"

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


def sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def write_state(root, name, series, dates=None):
    os.makedirs(root, exist_ok=True)
    path = os.path.join(root, name)
    json.dump({"token": {"symbol": "TT"}, "camp_share_series": {
        "dates": dates or ["2026-01-01"], "series": series,
    }}, open(path, "w"), ensure_ascii=False)
    return path


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
        receipt_p = os.path.join(td, LEGEND_RECEIPT)
        receipt = json.load(open(receipt_p))
        assert receipt["schema"] == "figure1-legend/v1"
        assert receipt["rendered_camps"] == ["大庄", "散户"]
        assert receipt["excluded_series"] == [] and receipt["overlays"] == []
        assert receipt["price_csv"] is None
        assert receipt["state"]["sha256"] == sha256(sp)
        assert receipt["output_png"]["sha256"] == sha256(out1)

        # F-01 原反例：旧实现接受未知阵营并报“2 阵营”，
        # plot_camp_evolution 却只画 CAMP_ORDER 交集中的“大庄”。修复后
        # fig1 入口必须 exit 2，且列出坏键与迁移口径。
        unknown_state = {
            "token": {"symbol": "TT"},
            "camp_share_series": {
                "dates": ["2026-01-01"],
                "series": {"大庄": [60.0], "未知阵营": [40.0]},
            },
        }
        unknown_sp = os.path.join(td, "unknown-state.json")
        json.dump(unknown_state, open(unknown_sp, "w"), ensure_ascii=False)
        unknown_out = os.path.join(td, "unknown.png")
        r = run(["fig1", "--state", unknown_sp, "--token", "TT",
                 "--out", unknown_out])
        assert r.returncode == 2 \
            and "未知阵营" in (r.stdout + r.stderr) \
            and "scan-schemas.md" in (r.stdout + r.stderr), \
            ("F-01 未知阵营应 exit 2 并列出坏键／迁移口径；"
             f" observed rc={r.returncode}: {r.stdout} {r.stderr}")
        assert not os.path.exists(unknown_out), "未知阵营拒绝时不得出 PNG"

        # F-01 legacy 绿例：EVM legacy 分母模式真实产出的“销毁”
        # 是显式可绘键，必须有配色并进图例收据实绘集合。
        legacy_dir = os.path.join(td, "legacy")
        legacy_sp = write_state(legacy_dir, "state.json", {
            "大庄": [60.0], "销毁": [40.0],
        })
        legacy_out = os.path.join(legacy_dir, "fig1.png")
        r = run(["fig1", "--state", legacy_sp, "--out", legacy_out])
        assert r.returncode == 0 and os.path.getsize(legacy_out) > 10_000, \
            f"销毁 legacy 键应可画: {r.stdout} {r.stderr}"
        legacy_receipt = json.load(open(os.path.join(legacy_dir, LEGEND_RECEIPT)))
        assert legacy_receipt["rendered_camps"] == ["大庄", "销毁"]
        sys.path.insert(0, REPORT_DIR)
        import standard_charts
        assert "销毁" in standard_charts.CAMP_COLORS

        # burn_cum_pct 在场：验长度/有限值后结构化豁免；不在场
        # 已由基准用例证明 excluded_series=[]。
        burn_dir = os.path.join(td, "burn")
        burn_sp = write_state(burn_dir, "state.json", {
            "大庄": [60.0], "散户": [40.0], "burn_cum_pct": [5.0],
        })
        burn_out = os.path.join(burn_dir, "fig1.png")
        r = run(["fig1", "--state", burn_sp, "--out", burn_out])
        assert r.returncode == 0, r.stdout + r.stderr
        burn_receipt = json.load(open(os.path.join(burn_dir, LEGEND_RECEIPT)))
        assert burn_receipt["rendered_camps"] == ["大庄", "散户"]
        assert burn_receipt["excluded_series"] == [
            {"key": "burn_cum_pct", "reason": "non_stacked_metric"},
        ]

        nonfinite_dir = os.path.join(td, "burn-nonfinite")
        nonfinite_sp = write_state(nonfinite_dir, "state.json", {
            "大庄": [100.0], "burn_cum_pct": [float("nan")],
        })
        nonfinite_out = os.path.join(nonfinite_dir, "fig1.png")
        r = run(["fig1", "--state", nonfinite_sp, "--out", nonfinite_out])
        assert r.returncode != 0 and "burn_cum_pct" in (r.stdout + r.stderr) \
            and "非有限" in (r.stdout + r.stderr), r.stdout + r.stderr
        assert not os.path.exists(nonfinite_out)
        assert not os.path.exists(os.path.join(nonfinite_dir, LEGEND_RECEIPT))

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
        overlay_receipt = json.load(open(receipt_p))
        assert overlay_receipt["overlays"] == [
            {"label": "合并", "camps": ["大庄", "散户"]},
        ]
        # SystemExit 的消息走 stderr（与 mode_fig1 内其他 fail 一致），两路都收
        r = run(["fig1", "--state", sp, "--out", os.path.join(td, "x.png"),
                 "--overlay", "X=大庄+查无此阵营"])
        assert r.returncode != 0 and "不存在的阵营" in (r.stdout + r.stderr), \
            f"引用不存在阵营应 fail-closed: {r.stdout} {r.stderr}"
        r = run(["fig1", "--state", sp, "--out", os.path.join(td, "y.png"),
                 "--overlay", "缺等号"])
        assert r.returncode != 0 and "格式应为" in (r.stdout + r.stderr), \
            f"格式错应 fail-closed: {r.stdout} {r.stderr}"

        # 价格轴输入必须以 path/size/sha256 三元组绑定。
        price_dir = os.path.join(td, "price")
        price_sp = write_state(price_dir, "state.json", {"大庄": [100.0]})
        price_csv = os.path.join(price_dir, "price.csv")
        with open(price_csv, "w", encoding="utf-8") as fh:
            fh.write("date,close\n2026-01-01,1.25\n")
        price_out = os.path.join(price_dir, "fig1.png")
        r = run(["fig1", "--state", price_sp, "--out", price_out,
                 "--price-csv", price_csv])
        assert r.returncode == 0, r.stdout + r.stderr
        price_receipt = json.load(open(os.path.join(price_dir, LEGEND_RECEIPT)))
        assert price_receipt["price_csv"] == {
            "path": "price.csv", "sha256": sha256(price_csv),
            "size": os.path.getsize(price_csv),
        }

        test_series_format(Path(td) / "series-format")

    print("PASS: figures_from_facts fig1白名单/legacy销毁键/legend receipt/"
          "burn豁免/overlay组成/价格绑定/flow宏同源/check终值对账全过")
    return 0


def test_series_format(root):
    """三修 B：格式分家直出、纯函数与两个真实消费方交叉核验。"""
    sys.path.insert(0, REPORT_DIR)
    sys.path.insert(0, str(Path(HERE).parent / "lib"))
    import standard_charts as charts
    import a5_report_seal as a5
    import audit_release_gate as gate
    from camp_series_provenance import SeriesProvenanceError

    series = {"大庄": [60.0, 60.0], "散户": [40.0, 40.0], "锁仓/销毁": [5.0, 5.0]}
    cases = {}
    for fmt in ("sol-rows", "evm-dict"):
        case = root / fmt
        case.mkdir(parents=True)
        state = {"token": {"symbol": "TT"}, "camp_share_series": {
            "dates": ["2026-01-01", "2026-01-02"], "series": deepcopy(series)},
            "provenance": {"camp_series_sidecar": {"series_format": fmt}}}
        sp = case / "analysis-state.json"
        sp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        png = case / "fig1.png"
        r = run(["fig1", "--state", str(sp), "--out", str(png)])
        assert r.returncode == 0 and png.stat().st_size > 0, r.stdout + r.stderr
        receipt = json.loads((case / LEGEND_RECEIPT).read_text(encoding="utf-8"))
        expected = ["大庄", "散户"] if fmt == "sol-rows" else ["大庄", "散户", "锁仓/销毁"]
        excluded = [{"key": "锁仓/销毁", "reason": "non_stacked_metric"}] if fmt == "sol-rows" else []
        assert receipt["rendered_camps"] == expected, receipt
        assert receipt["excluded_series"] == excluded, receipt
        # 捕获真正交给 matplotlib 的数值、标签和分母，防止收据正确但实绘错误。
        # 保留上方 CLI 真实 PNG 正例；这里也调用原始绘图方法并自动恢复补丁。
        from matplotlib.axes import Axes
        actual_stacks, actual_ylabels = [], []
        original_stackplot, original_ylabel = Axes.stackplot, Axes.set_ylabel

        def record_stackplot(ax, xs, ys, *args, **kwargs):
            actual_stacks.append((list(kwargs["labels"]), [list(y) for y in ys]))
            return original_stackplot(ax, xs, ys, *args, **kwargs)

        def record_ylabel(ax, label, *args, **kwargs):
            actual_ylabels.append(label)
            return original_ylabel(ax, label, *args, **kwargs)

        note_supply = "占净供应量" if fmt == "sol-rows" else "占总供应量"
        with patch.object(Axes, "stackplot", record_stackplot), \
                patch.object(Axes, "set_ylabel", record_ylabel):
            charts.plot_camp_evolution(
                {"ts": [datetime(2026, 1, 1), datetime(2026, 1, 2)], **deepcopy(series)},
                str(case / "plot-layer.png"), "TT", series_format=fmt,
                note_supply=note_supply)
        assert actual_stacks == [(expected, [series[c] for c in expected])], actual_stacks
        assert f"{note_supply} %" in actual_ylabels, actual_ylabels
        assert Axes.stackplot is original_stackplot and Axes.set_ylabel is original_ylabel
        cases[fmt] = (case, state, receipt, [a5.entry(case, png)])
        print(f"ok series_format={fmt}: rendered={expected}, excluded={excluded}")

    assert charts.select_fig1_series(series, series_format="sol-rows") == (
        ["大庄", "散户"], ["锁仓/销毁"], [])
    for invalid in ("", "bogus", 7, False, [], {}):
        try:
            charts.select_fig1_series(series, series_format=invalid)
        except SeriesProvenanceError:
            pass
        else:
            raise AssertionError(f"非法 format 未拒: {invalid!r}")
    for sidecar in ([], "sol-rows", None, 1):
        try:
            charts.fig1_series_format({"provenance": {"camp_series_sidecar": sidecar}})
        except SeriesProvenanceError:
            pass
        else:
            raise AssertionError(f"非对象 sidecar 未拒: {sidecar!r}")
    for invalid in (7, False, [], {}):
        try:
            charts.fig1_series_format({"provenance": {"camp_series_sidecar": {
                "series_format": invalid}}})
        except SeriesProvenanceError:
            pass
        else:
            raise AssertionError(f"非字符串 format 未拒: {invalid!r}")
    assert charts.fig1_series_format({}) is None
    assert charts.fig1_series_format({"provenance": []}) is None
    assert charts.fig1_series_format({"provenance": {"camp_series_sidecar": {}}}) is None
    fallback = charts.fig1_excluded_series()
    assert fallback == charts.FIG1_EXCLUDED_SERIES and fallback is not charts.FIG1_EXCLUDED_SERIES

    case, state, receipt, images = cases["sol-rows"]
    _, rendered, excluded, _ = a5._fig1_expected_from_state(case)
    assert rendered == receipt["rendered_camps"] and excluded == receipt["excluded_series"]
    assert a5._fig1_legend_errors(case, receipt, images) == []
    errors = []
    gate.check_figure1_legend_receipt(case, receipt, state, errors)
    assert errors == [], errors
    for label in ("rendered", "missing-exemption", "overlay"):
        bad_receipt, bad_state = deepcopy(receipt), deepcopy(state)
        if label == "rendered":
            bad_receipt["rendered_camps"].append("锁仓/销毁")
        elif label == "missing-exemption":
            bad_receipt["excluded_series"] = []
        else:
            bad_receipt["overlays"] = [{"label": "坏线", "camps": ["锁仓/销毁"]}]
        sp = case / "analysis-state.json"
        sp.write_text(json.dumps(bad_state, ensure_ascii=False), encoding="utf-8")
        # 同步物理绑定，确保反例由键集合/overlay 契约拒绝。
        bad_receipt["state"] = a5.entry(case, sp)
        a5_errors = a5._fig1_legend_errors(case, bad_receipt, images)
        gate_errors = []
        gate.check_figure1_legend_receipt(case, bad_receipt, bad_state, gate_errors)
        assert a5_errors and gate_errors, (label, a5_errors, gate_errors)
        print(f"ok 两消费方拒绝 {label}: {a5_errors}; {gate_errors}")
    # 用户裁决：消费方只重算键集合；非有限数值由 fig1 既有校验把关。
    for label, value in (("nan", float("nan")), ("inf", float("inf")),
                         ("non-numeric", "bad")):
        bad_state = deepcopy(state)
        bad_state["camp_share_series"]["series"]["锁仓/销毁"][0] = value
        sp.write_text(json.dumps(bad_state, ensure_ascii=False), encoding="utf-8")
        out = case / f"{label}.png"
        r = run(["fig1", "--state", str(sp), "--out", str(out)])
        assert r.returncode != 0 and "非有限数值" in r.stdout + r.stderr, r.stdout + r.stderr
        assert not out.exists()
        print(f"ok fig1 拒绝豁免桶 {label}: rc={r.returncode}")
    (case / "analysis-state.json").write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
