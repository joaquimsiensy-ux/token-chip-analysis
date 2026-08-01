#!/usr/bin/env python3
"""adjudication_validator.py — 候选裁决闭环校验器（candidate-adjudications/v1，v6.8.0）。

背景：W1 波次二次漏检复盘——v6.6.0 的 wave_scan 是"高召回报警器 v1、裁决未闭环"：
候选报出来没人管照样能冻结实体。本校验器把"每个候选都被成员级裁决"变成 freeze 的
机器前置：handoff_manifest.py freeze 在物化 entity_freeze.json 前强制调用本脚本，
任何缺漏即 exit 2（fail-closed，无跳过通道）。

子命令：
  template  读 wave_scan_report.json + flow_anomaly_report.json 生成裁决模板
            candidate_adjudications.json（id/candidate_sha256/成员全集/机器 tier_impact
            预填，verdict 留空待 −2 逐条填写——candidate_sha256 不必手算）
  validate  校验裁决台账（freeze 前置；六类拒绝全 exit 2）

拒绝规则（schema 权威定义 references/scan-schemas.md §3；v6.8.1 codex 复核后加固）：
  ①缺文件（wave/flow 报告或裁决台账任一缺）——fail-open 修复：漏跑生产器不得静默过闸
  ②源报告候选 ID 集 ≠ 裁决 ID 集（少裁/多裁/未知 ID）；源报告 schema 错版/重复候选 ID 同拒
  ③重复裁决 ID
  ④candidate_sha256 与当前源报告候选不符（候选内容已变，旧裁决自动失效）
  ⑤accepted_members ∪ excluded_members ≠ 候选成员全集或有交集（部分成员未裁/重复处置）
     ——wave 候选按 members[].addr、eqg 按收方 members[]、sink/spray 按 {addr} 单元素集
  ⑥tier_impact 伪造：max_possible_impact 三字段（combined_peak_pct/nearest_tier_line/
     could_change_tiering）逐一与机器重算比对，任一不符即拒；
     另：verdict=unresolved 且机器判 could_change_tiering=true → 拒（未决但可能改判级，
     不许带病冻结）
  ⑦verdict 语义交叉约束（防"形式全覆盖、语义自相矛盾"的敷衍裁决）：
     pattern_confirmed → accepted_members 非空 ＋ linked_entity_id 必填 ＋ evidence 非空；
     excluded / unresolved → accepted_members 必须为空（没定性/已排除不得收编成员）；
     excluded_members 逐条必须有非空 reason；candidate_kind 必须与机器一致；
     adjudicated_at 必须已填
  ⑧实体名册绑定（--entity-file {entity_id:[addr…]}，freeze 调用时强制传入）：
     linked_entity_id 必须存在于名册；accepted_members 必须全部属于该实体名册——
     "裁决说并入实体 X"却没真并，或乱填实体 ID，全部机器拒。
     未传 --entity-file 时：存在任何 pattern_confirmed 裁决即拒（绑定校验不可跳过）。

退出码：0=闭环完成；2=校验不通过（硬停）；1=脚本自身错误。
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

SCHEMA = "candidate-adjudications/v1"
VERDICTS = {"pattern_confirmed", "excluded", "unresolved"}
# 判级相关线（%总供应）：最低档小庄 5%（tiering 权威值）——候选可达规模 ≥此线即
# "可能改变庄数/判级"，机器判定人工不得覆盖
TIER_MIN_LINE_PCT = 5.0


def log(msg):
    print(f"[adjudication] {msg}", flush=True)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def canon_sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(blk)
    return h.hexdigest()


WAVE_SCHEMA = "wave-scan/v2"
FLOW_SCHEMA = "flow-anomaly/v1"


def check_source_schemas(wave, flow):
    """源报告 schema 检查（v6.8.1：错版/空壳报告不得形成"零候选已闭环"）。"""
    fails = []
    if wave.get("schema") != WAVE_SCHEMA:
        fails.append(f"wave_scan_report schema 异常: {wave.get('schema')}（需要 {WAVE_SCHEMA}——旧版重跑 v2）")
    if flow.get("schema") != FLOW_SCHEMA:
        fails.append(f"flow_anomaly_report schema 异常: {flow.get('schema')}（需要 {FLOW_SCHEMA}）")
    return fails


def collect_candidates(wave, flow):
    """全部候选 → ({id: {"obj", "members", "kind", "scale_pct"}}, dup_source_ids)。
    成员全集口径：wave=members[].addr；eqg=members[]；sink/spray={addr}。
    scale_pct＝机器算 max_possible_impact 用的可达规模。
    源报告内重复候选 ID 不得静默覆盖（v6.8.1）——返回 dup 集由调用方拒。"""
    out, dups = {}, set()

    def put(cid, entry):
        if cid in out:
            dups.add(cid)
        out[cid] = entry

    for w in wave.get("waves", []):
        put(w["id"], {"obj": w, "kind": "wave",
                      "members": {m["addr"] for m in w.get("members", [])},
                      "scale_pct": float(w.get("combined_peak_pct", 0))})
    for g in wave.get("equal_amount_groups", []):
        put(g["id"], {"obj": g, "kind": "eqg",
                      "members": set(g.get("members", [])),
                      "scale_pct": float(g.get("group_total_pct", 0))})
    for s in flow.get("sinks", []):
        put(s["id"], {"obj": s, "kind": "sink", "members": {s["addr"]},
                      "scale_pct": float(s.get("best_window", {}).get("inflow_pct", 0))})
    for s in flow.get("sprays", []):
        bw = s.get("best_window") or {}
        scale = max(float(bw.get("outflow_pct", 0) or 0),
                    float(s.get("all_time", {}).get("outflow_pct", 0) or 0))
        put(s["id"], {"obj": s, "kind": "spray", "members": {s["addr"]}, "scale_pct": scale})
    return out, dups


def load_entity_map_strict(path):
    """--entity-file {entity_id:[addr…]}（与 entity_source_trace/flow 同格式）。格式坏→None＋报错文本。"""
    try:
        with open(path, encoding="utf-8") as fh:
            obj = json.load(fh)
    except Exception as e:
        return None, f"--entity-file 读取失败: {e}"
    if not isinstance(obj, dict) or not obj:
        return None, "--entity-file 需为非空 {entity_id:[addr…]}"
    out = {}
    for eid, addrs in obj.items():
        if (not isinstance(eid, str) or not eid or not isinstance(addrs, list)
                or not all(isinstance(x, str) and x for x in addrs)):
            return None, f"--entity-file 实体 {eid!r} 格式错误（成员必须是非空字符串数组）"
        out[eid] = set(addrs)
    return out, None


def machine_tier_impact(scale_pct):
    return {"combined_peak_pct": round(scale_pct, 4),
            "nearest_tier_line": f"{TIER_MIN_LINE_PCT}%",
            "could_change_tiering": scale_pct >= TIER_MIN_LINE_PCT}


# ---------------- template ----------------

def cmd_template(a):
    case_dir = os.path.abspath(a.case_dir)
    wp = os.path.join(case_dir, "wave_scan_report.json")
    fp = os.path.join(case_dir, "flow_anomaly_report.json")
    for p in (wp, fp):
        if not os.path.isfile(p):
            log(f"缺 {os.path.basename(p)}——先跑对应扫描器")
            return 2
    wave, flow = load_json(wp), load_json(fp)
    schema_fails = check_source_schemas(wave, flow)
    if schema_fails:
        return _report(schema_fails)
    cands, dups = collect_candidates(wave, flow)
    if dups:
        return _report([f"源报告含重复候选 ID: {sorted(dups)[:5]}——扫描器产物异常，先排查"])
    out_path = os.path.join(case_dir, a.out)
    if os.path.isfile(out_path) and not a.force:
        log(f"{a.out} 已存在（防覆盖已填裁决；确要重生成加 --force）")
        return 2
    tpl = {
        "schema": SCHEMA,
        "case": os.path.basename(case_dir),
        "adjudicated_at": None,
        "source_reports": {"wave_scan_report.json": file_sha(wp),
                           "flow_anomaly_report.json": file_sha(fp)},
        "adjudications": [{
            "candidate_id": cid,
            "candidate_kind": c["kind"],
            "candidate_sha256": canon_sha(c["obj"]),
            "candidate_verdict": None,   # ← −2 填：pattern_confirmed|excluded|unresolved
            "accepted_members": [],
            "excluded_members": [],      # ← 全体成员必须落入两桶之一：[{"addr","reason"}]
            "linked_entity_id": None,
            "evidence": [],
            "tier_impact": {"max_possible_impact": machine_tier_impact(c["scale_pct"]),
                            "note": None},
            "_members_total": sorted(c["members"]),
        } for cid, c in sorted(cands.items())],
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(tpl, f, ensure_ascii=False, indent=1)
    log(f"模板 {len(tpl['adjudications'])} 条候选 → {out_path}（成员级逐条填写后跑 validate）")
    return 0


# ---------------- validate ----------------

def cmd_validate(a):
    case_dir = os.path.abspath(a.case_dir)
    wp = os.path.join(case_dir, "wave_scan_report.json")
    fp = os.path.join(case_dir, "flow_anomaly_report.json")
    jp = os.path.join(case_dir, a.adjudications)
    fails = []
    # ① 缺文件
    for p, hint in ((wp, "wave_scan.py"), (fp, "flow_anomaly_scan.py"),
                    (jp, "adjudication_validator.py template 后由 −2 填写")):
        if not os.path.isfile(p):
            fails.append(f"缺 {os.path.basename(p)}（{hint}）——fail-open 修复：缺件不得静默过闸")
    if fails:
        return _report(fails)

    wave, flow = load_json(wp), load_json(fp)
    adj = load_json(jp)
    if adj.get("schema") != SCHEMA:
        fails.append(f"裁决台账 schema 异常: {adj.get('schema')}（需要 {SCHEMA}）")
        return _report(fails)
    # ② 源报告 schema（错版/空壳不得形成"零候选已闭环"）
    fails.extend(check_source_schemas(wave, flow))
    if fails:
        return _report(fails)
    # 源报告整册哈希（报告重跑后整册裁决过期）
    srcs = adj.get("source_reports") or {}
    for name, p in (("wave_scan_report.json", wp), ("flow_anomaly_report.json", fp)):
        if srcs.get(name) != file_sha(p):
            fails.append(f"source_reports.{name} 哈希不符——源报告已重跑，裁决台账整册过期，重出 template 再裁")

    # ⑧ 实体名册（linked_entity 绑定校验；freeze 强制传入）
    entity_map = None
    if a.entity_file:
        entity_map, err = load_entity_map_strict(
            a.entity_file if os.path.isabs(a.entity_file) else os.path.join(case_dir, a.entity_file))
        if err:
            fails.append(err)
            return _report(fails)

    cands, dup_src = collect_candidates(wave, flow)
    if dup_src:
        fails.append(f"源报告含重复候选 ID: {sorted(dup_src)[:5]}——扫描器产物异常，先排查")
    rows = adj.get("adjudications") or []
    if not isinstance(adj.get("adjudicated_at"), str) or not adj.get("adjudicated_at"):
        fails.append("adjudicated_at 未填——裁决完成时间必须落账")
    ids = [r.get("candidate_id") for r in rows]
    # ③ 重复
    dup = {x for x in ids if ids.count(x) > 1}
    if dup:
        fails.append(f"重复裁决 ID: {sorted(dup)}")
    # ② ID 集相等
    idset, candset = set(ids), set(cands)
    if idset != candset:
        missing = sorted(candset - idset)
        unknown = sorted(idset - candset)
        if missing:
            fails.append(f"候选未裁决（少裁 {len(missing)}）: {missing[:5]}{'…' if len(missing) > 5 else ''}")
        if unknown:
            fails.append(f"裁决了不存在的候选（未知 ID {len(unknown)}）: {unknown[:5]}")

    for r in rows:
        cid = r.get("candidate_id")
        if cid not in cands:
            continue
        c = cands[cid]
        # ④ 内容哈希
        if r.get("candidate_sha256") != canon_sha(c["obj"]):
            fails.append(f"{cid}: candidate_sha256 不符——候选内容已变，本条裁决失效")
            continue
        verdict = r.get("candidate_verdict")
        if verdict not in VERDICTS:
            fails.append(f"{cid}: candidate_verdict 非法: {verdict}（需 {sorted(VERDICTS)}）")
            continue
        if r.get("candidate_kind") != c["kind"]:
            fails.append(f"{cid}: candidate_kind {r.get('candidate_kind')!r} 与机器判定 {c['kind']!r} 不符")
        # ⑤ 成员全覆盖且不相交
        acc = set(r.get("accepted_members") or [])
        exc_rows = r.get("excluded_members") or []
        exc = {e.get("addr") for e in exc_rows}
        if acc & exc:
            fails.append(f"{cid}: 成员同时出现在 accepted 与 excluded: {sorted(acc & exc)[:3]}")
        uncovered = c["members"] - acc - exc
        alien = (acc | exc) - c["members"]
        if uncovered:
            fails.append(f"{cid}: {len(uncovered)} 个成员未裁（accepted∪excluded 未覆盖全集）: "
                         f"{sorted(uncovered)[:3]}{'…' if len(uncovered) > 3 else ''}")
        if alien:
            fails.append(f"{cid}: accepted/excluded 含非本候选成员: {sorted(alien)[:3]}")
        # ⑦ verdict 语义交叉约束（防敷衍裁决：形式全覆盖但语义自相矛盾）
        no_reason = [e.get("addr") for e in exc_rows
                     if not isinstance(e.get("reason"), str) or not e.get("reason").strip()]
        if no_reason:
            fails.append(f"{cid}: {len(no_reason)} 个 excluded 成员缺排除理由: {no_reason[:3]}")
        if verdict == "pattern_confirmed":
            if not acc:
                fails.append(f"{cid}: pattern_confirmed 但 accepted_members 为空——确认了协同却不收编任何成员，自相矛盾")
            if not r.get("linked_entity_id"):
                fails.append(f"{cid}: pattern_confirmed 但缺 linked_entity_id（判入哪个实体？）")
            ev = r.get("evidence")
            if not isinstance(ev, list) or not [x for x in ev if isinstance(x, str) and x.strip()]:
                fails.append(f"{cid}: pattern_confirmed 但 evidence 为空——确认必须给证据引用")
            # ⑧ 实体名册绑定
            if entity_map is None:
                fails.append(f"{cid}: pattern_confirmed 但本次校验未传 --entity-file——"
                             "linked_entity 绑定校验不可跳过（freeze 会强制传入实体名册）")
            elif r.get("linked_entity_id"):
                lid = r["linked_entity_id"]
                if lid not in entity_map:
                    fails.append(f"{cid}: linked_entity_id={lid} 不存在于实体名册——乱填实体或名册没更新")
                else:
                    stray = acc - entity_map[lid]
                    if stray:
                        fails.append(f"{cid}: {len(stray)} 个 accepted 成员未落入实体 {lid} 名册: "
                                     f"{sorted(stray)[:3]}——裁决说并入却没真并")
        elif acc:
            fails.append(f"{cid}: verdict={verdict} 但 accepted_members 非空——未确认/已排除的候选不得收编成员")
        # ⑥ tier_impact 机器重算（三字段逐一比对，nearest_tier_line 同样不得伪造）
        mi = machine_tier_impact(c["scale_pct"])
        got = ((r.get("tier_impact") or {}).get("max_possible_impact")) or {}
        mismatch = (got.get("could_change_tiering") != mi["could_change_tiering"]
                    or got.get("nearest_tier_line") != mi["nearest_tier_line"]
                    or abs(float(got.get("combined_peak_pct", -1)) - mi["combined_peak_pct"]) > 1e-6)
        if mismatch:
            fails.append(f"{cid}: tier_impact 与机器重算不符（机器 {mi}，台账 {got}）——数值不得人工覆盖")
        elif verdict == "unresolved" and mi["could_change_tiering"]:
            fails.append(f"{cid}: unresolved 且可达规模 {mi['combined_peak_pct']}% ≥{TIER_MIN_LINE_PCT}% "
                         "可能改变庄数/判级——不许带病冻结，查清或给出排除证据")

    if fails:
        return _report(fails)
    n_conf = sum(1 for r in rows if r.get("candidate_verdict") == "pattern_confirmed")
    n_unres = sum(1 for r in rows if r.get("candidate_verdict") == "unresolved")
    log(f"PASS  {len(rows)} 条候选全部成员级闭环（confirmed {n_conf} / unresolved {n_unres}——"
        "unresolved 均在判级线下）")
    return 0


def _report(fails):
    log("FAIL（fail-closed，逐条修复）:")
    for x in fails:
        print(f"  ✗ {x}")
    return 2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="subcmd", required=True)
    t = sub.add_parser("template", help="生成裁决模板（sha256/成员全集/机器 tier_impact 预填）")
    t.add_argument("--case-dir", required=True)
    t.add_argument("--out", default="candidate_adjudications.json")
    t.add_argument("--force", action="store_true")
    v = sub.add_parser("validate", help="校验裁决台账（freeze 前置，八类拒绝）")
    v.add_argument("--case-dir", required=True)
    v.add_argument("--adjudications", default="candidate_adjudications.json")
    v.add_argument("--entity-file", default=None,
                   help="实体名册 {entity_id:[addr…]}——linked_entity 绑定校验；"
                        "存在 pattern_confirmed 裁决时必传（freeze 强制传入）")
    a = ap.parse_args()
    try:
        return {"template": cmd_template, "validate": cmd_validate}[a.subcmd](a)
    except Exception as e:
        print(f"[adjudication] 脚本自身错误（exit 1，修完重跑）: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
