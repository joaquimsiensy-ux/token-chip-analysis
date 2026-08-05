#!/usr/bin/env python3
"""fixtures_lint.py — 回测锚点文件结构守卫（v6.8.1，codex 复核 P2 建议落地）。

背景：fixtures/pythia_anchors.json 此前不被任何测试读取——损坏/漂移/漏键不会让
run_all 失败，"锚点文件"实际是无守护的人工备忘。本 lint 把它的**结构**纳入守护：
必填键齐全、类型正确、ID 前缀合法、溯源段必须是 v2（正向模拟版——v1 数字出自
pro-rata 数学错误算法，不得再被引用）。

数值本身不在此校验——锚点数值的权威就是该文件（重跑回测后人工更新），lint 防的是
结构性腐坏与"引用了不存在的键"。
用法：python3 scripts/tests/fixtures_lint.py   退出码 0=PASS / 1=FAIL
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures", "pythia_anchors.json")
FAILS = []


def check(name, cond):
    if not cond:
        FAILS.append(name)
        print(f"FAIL  {name}")


def need(obj, path, typ):
    cur = obj
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur:
            check(f"缺键 {path}", False)
            return None
        cur = cur[k]
    if typ is float:
        ok = isinstance(cur, (int, float)) and not isinstance(cur, bool)
    else:
        ok = isinstance(cur, typ) and not (typ is int and isinstance(cur, bool))
    check(f"{path} 类型应为 {typ.__name__}（实为 {type(cur).__name__}）", ok)
    return cur


def main():
    if not os.path.isfile(FIX):
        print(f"FAIL  锚点文件不存在: {FIX}")
        return 1
    try:
        r = json.load(open(FIX, encoding="utf-8"))
    except Exception as e:
        print(f"FAIL  锚点文件 JSON 解析失败: {e}")
        return 1

    need(r, "case", str)
    need(r, "total_supply_raw", str)
    # wave_scan_v2 段
    need(r, "wave_scan_v2.scan_universe_count", int)
    need(r, "wave_scan_v2.retention_buckets", dict)
    wid = need(r, "wave_scan_v2.w1_wave.id", str)
    check("w1_wave.id 前缀 wave-", isinstance(wid, str) and wid.startswith("wave-"))
    need(r, "wave_scan_v2.w1_wave.member_count", int)
    need(r, "wave_scan_v2.w1_wave.combined_peak_pct", float)
    need(r, "wave_scan_v2.w1_wave.seed_window.member_count", int)
    need(r, "wave_scan_v2.w1_wave.seed_window.combined_peak_pct", float)
    need(r, "wave_scan_v2.w1_wave.w1_coverage", str)
    need(r, "wave_scan_v2.equal_amount_groups.count", int)
    gid = need(r, "wave_scan_v2.equal_amount_groups.top.id", str)
    check("D top 组 id 前缀 eqg-", isinstance(gid, str) and gid.startswith("eqg-"))
    need(r, "wave_scan_v2.equal_amount_groups.top.amount_raw", str)
    need(r, "wave_scan_v2.equal_amount_groups.top.group_total_pct", float)
    need(r, "wave_scan_v2.equal_amount_groups.top.recipients", int)
    need(r, "wave_scan_v2.equal_amount_groups.top.top_sender_global_out_degree", int)
    # flow_anomaly_v2 段（v1→v2 2026-08-02：三口径多命中；v2 补强——三派发器/Q1 的 mode
    # 也入锚，旧版锚点 mode 写错 run_all 照样全绿的盲区堵上）
    need(r, "flow_anomaly_v2.sink_count", int)
    need(r, "flow_anomaly_v2.spray_count", int)
    need(r, "flow_anomaly_v2.q1_sink.best_window.inflow_pct", float)
    need(r, "flow_anomaly_v2.q1_sink.best_window.source_count", int)
    disp_pfx = need(r, "flow_anomaly_v2.dispatchers_spray.prefixes", list)
    disp_modes = need(r, "flow_anomaly_v2.dispatchers_spray.modes", list)
    SPRAY_MODES = {"pulse", "pulse_all", "slow_spray"}
    check("dispatchers_spray.modes 与 prefixes 等长且值合法",
          isinstance(disp_pfx, list) and isinstance(disp_modes, list)
          and len(disp_modes) == len(disp_pfx) and all(m in SPRAY_MODES for m in disp_modes))
    q1s_mode = need(r, "flow_anomaly_v2.q1_pulse_spray.mode", str)
    check("q1_pulse_spray.mode == pulse（灌新仓锚）", q1s_mode == "pulse")
    need(r, "flow_anomaly_v2.pulse_all_anchor", dict)
    # 溯源段必须 v2（正向模拟）——v1 数字出自数学错误算法，引用即事故
    check("溯源段必须为 provenance_v2（v1=pro-rata 数学错误版，禁止引用）",
          "provenance_v2" in r and "provenance_v1" not in r)
    if "provenance_v2" in r:
        need(r, "provenance_v2.q1_peak_anchor.direct_upstream_count", int)
        need(r, "provenance_v2.q1_peak_anchor.w1_upstream_count", int)
        need(r, "provenance_v2.3ymk_peak_anchor.w1_upstream_count", int)
        need(r, "provenance_v2.sensitivity_stable", bool)

    if FAILS:
        print(f"\nFAIL：{len(FAILS)} 项结构问题——锚点文件是回测权威，先修复再收工")
        return 1
    print("fixtures_lint PASS：pythia_anchors.json 结构完整（数值以文件为权威，回测后人工更新）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
