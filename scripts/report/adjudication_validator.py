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

_LIB = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
sys.path.insert(0, _LIB)
from case_paths import safe_case_file
from wave_contract import WAVE_SCHEMA, has_formal_wave_semantics

SCHEMA = "candidate-adjudications/v1"
DISTRIBUTION_SCHEMA = "distribution-adjudications/v1"
VERDICTS = {"pattern_confirmed", "excluded", "unresolved"}
# 判级相关线（%总供应）：最低档小庄 5%（tiering 权威值）——候选可达规模 ≥此线即
# "可能改变庄数/判级"，机器判定人工不得覆盖
TIER_MIN_LINE_PCT = 5.0
DISTRIBUTION_UNRESOLVED_LINE_PCT = 2.0


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


FLOW_SCHEMA = "flow-anomaly/v2"
SPRAY_MODES = ("pulse", "pulse_all", "slow_spray")


def check_source_schemas(wave, flow):
    """源报告 schema 检查（v6.8.1：错版/空壳报告不得形成"零候选已闭环"）。"""
    fails = []
    if wave.get("schema") != WAVE_SCHEMA:
        fails.append(f"wave_scan_report schema 异常: {wave.get('schema')}（需要 {WAVE_SCHEMA}——旧版重跑 wave_scan.py v4）")
    elif not has_formal_wave_semantics(wave):
        fails.append("wave_scan_report v4 缺 formal 边顺序语义，legacy-sol5 诊断产物不得裁决")
    if flow.get("schema") != FLOW_SCHEMA:
        fails.append(f"flow_anomaly_report schema 异常: {flow.get('schema')}"
                     f"（需要 {FLOW_SCHEMA}——旧 v1 产物重跑 flow_anomaly_scan.py v2）")
    else:
        # high-3：sink 只看单一最佳窗会系统性低估多窗口累计影响——
        # 缺历史峰值/当前余额/全史净流入的产物一律拒绝重跑。
        for s in flow.get("sinks", []):
            required = ((s.get("balance") or {}).get("historical_peak_pct"),
                        (s.get("balance") or {}).get("current_balance_pct"),
                        (s.get("all_time") or {}).get("net_inflow_pct"))
            if any(not isinstance(v, (int, float)) for v in required):
                fails.append(f"flow sink {s.get('id')} 缺 historical_peak/current_balance/"
                             "all_time.net_inflow——旧产物必须重跑")
        # v2：spray 对称校验（v1 时代 spray 零字段检查——mode 写错/结构空壳照样过闸）。
        for s in flow.get("sprays", []):
            sid = s.get("id")
            if s.get("id") != f"spray-{s.get('addr')}":
                fails.append(f"flow spray {sid} 的 id 与 addr 不对应——扫描器产物异常")
            mode = s.get("mode")
            hits = s.get("mode_hits")
            if mode not in SPRAY_MODES or not isinstance(hits, dict) \
                    or set(hits) != set(SPRAY_MODES):
                fails.append(f"flow spray {sid} 缺 mode/mode_hits 三口径结构"
                             f"（v2 必备；mode={mode!r}）——旧产物必须重跑")
                continue
            if not (hits.get(mode) or {}).get("hit"):
                fails.append(f"flow spray {sid} 顶层 mode={mode} 但 mode_hits 中未命中——自相矛盾")
            bw = s.get("best_window")
            if mode == "slow_spray":
                if bw is not None:
                    fails.append(f"flow spray {sid} slow_spray 主模式不应带 best_window")
            else:
                need_key = "fresh_recipient_count" if mode == "pulse" else "recipient_count"
                n_recv = (bw or {}).get(need_key)
                recips = s.get("recipients")
                if not isinstance(bw, dict) or not isinstance(recips, list) \
                        or not isinstance(n_recv, int) or len(recips) != n_recv \
                        or len(set(recips)) != len(recips):
                    fails.append(f"flow spray {sid} {mode} 的 recipients 与 "
                                 f"best_window.{need_key} 不闭合或含重复——零截断纪律，旧产物必须重跑")
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
        scale = max(float(s.get("best_window", {}).get("inflow_pct", 0) or 0),
                    float(s.get("balance", {}).get("historical_peak_pct", 0) or 0),
                    float(s.get("balance", {}).get("current_balance_pct", 0) or 0),
                    float(s.get("all_time", {}).get("net_inflow_pct", 0) or 0))
        put(s["id"], {"obj": s, "kind": "sink", "members": {s["addr"]},
                      "scale_pct": scale})
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


def distribution_candidates(case_dir, scan_rel):
    scan_path = str(safe_case_file(case_dir, scan_rel))
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "holder_distribution_scan.py")
    import subprocess
    pv = subprocess.run([sys.executable, script, "validate", "--case-dir", case_dir,
                         "--scan", scan_rel, "--expected-stage", "final"],
                        capture_output=True, text=True)
    if pv.returncode != 0:
        raise ValueError("final distribution scan 独立重算失败: " + (pv.stdout + pv.stderr)[-800:])
    scan = load_json(scan_path)
    out = {}
    for row in scan.get("abnormal_clusters", []):
        trigger = str(row.get("trigger"))
        if trigger not in {"bin_count_bump", "head_concentration"}:
            raise ValueError(f"未知 distribution candidate type: {trigger}")
        cid = f"dist-{row.get('cluster_id')}"
        members = {str(x.get("owner")) for x in row.get("members", []) if isinstance(x, dict)}
        if not members or cid in out:
            raise ValueError("distribution 候选成员为空或 ID 重复")
        out[cid] = {"obj": row, "members": members,
                    "kind": f"distribution_{trigger}",
                    "raw": int(row.get("raw_balance", 0)),
                    "scale_pct": float(row.get("net_supply_pct", 0))}
    return scan_path, scan, out


def cmd_distribution_template(a):
    case_dir = os.path.abspath(a.case_dir)
    try:
        scan_path, _, cands = distribution_candidates(case_dir, a.scan)
    except ValueError as exc:
        return _report([str(exc)])
    try:
        out_path = str(safe_case_file(case_dir, a.out, must_exist=False))
    except ValueError as exc:
        return _report([str(exc)])
    if os.path.isfile(out_path) and not a.force:
        return _report([f"{a.out} 已存在，防止覆盖已填裁决"])
    obj = {"schema": DISTRIBUTION_SCHEMA, "case": os.path.basename(case_dir),
           "adjudicated_at": None,
           "source_scan": {"path": a.scan, "sha256": file_sha(scan_path)},
           "adjudications": [{"candidate_id": cid, "candidate_kind": row["kind"],
              "candidate_sha256": canon_sha(row["obj"]), "candidate_verdict": None,
              "accepted_members": [], "excluded_members": [], "linked_entity_id": None,
              "evidence": [], "raw_balance": str(row["raw"]),
              "net_supply_pct": row["scale_pct"], "_members_total": sorted(row["members"])}
              for cid, row in sorted(cands.items())]}
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
    log(f"distribution 模板 {len(cands)} 条 → {out_path}")
    return 0


def cmd_distribution_validate(a):
    case_dir = os.path.abspath(a.case_dir); fails = []
    try:
        path = str(safe_case_file(case_dir, a.adjudications))
    except ValueError as exc:
        return _report([str(exc)])
    try:
        obj = load_json(path)
        if obj.get("schema") != DISTRIBUTION_SCHEMA:
            return _report([f"distribution 裁决 schema 必须 {DISTRIBUTION_SCHEMA}"])
        source = obj.get("source_scan") or {}; scan_rel = source.get("path")
        scan_path, scan, cands = distribution_candidates(case_dir, scan_rel)
        if source.get("sha256") != file_sha(scan_path):
            fails.append("distribution source_scan 哈希漂移")
    except Exception as exc:
        return _report([str(exc)])
    entity_map = None
    if a.entity_file:
        try:
            entity_path = safe_case_file(case_dir, a.entity_file)
        except ValueError as exc:
            fails.append(str(exc))
            entity_path = None
        entity_map, err = load_entity_map_strict(str(entity_path)) if entity_path else (None, None)
        if err: fails.append(err)
    rows = obj.get("adjudications")
    if not isinstance(rows, list) or not isinstance(obj.get("adjudicated_at"), str) \
            or not obj.get("adjudicated_at"):
        fails.append("distribution adjudications 数组或 adjudicated_at 缺失")
        rows = rows if isinstance(rows, list) else []
    ids = [str(x.get("candidate_id")) for x in rows if isinstance(x, dict)]
    if len(ids) != len(set(ids)):
        fails.append("distribution 裁决 ID 重复")
    if set(ids) != set(cands):
        fails.append(f"distribution 候选 ID 不闭合: missing={sorted(set(cands)-set(ids))} "
                     f"extra={sorted(set(ids)-set(cands))}")
    unresolved_raw = 0
    for row in rows:
        if not isinstance(row, dict) or row.get("candidate_id") not in cands: continue
        cid = row["candidate_id"]; cand = cands[cid]
        if row.get("candidate_kind") != cand["kind"]:
            fails.append(f"{cid}: candidate_kind 与机器类型不符")
        if row.get("candidate_sha256") != canon_sha(cand["obj"]):
            fails.append(f"{cid}: candidate_sha256 不符")
        verdict = row.get("candidate_verdict")
        if verdict not in VERDICTS:
            fails.append(f"{cid}: verdict 非法"); continue
        accepted = set(map(str, row.get("accepted_members") or []))
        excluded_rows = row.get("excluded_members") or []
        excluded = {str(x.get("addr")) for x in excluded_rows if isinstance(x, dict)}
        if accepted & excluded or accepted | excluded != cand["members"]:
            fails.append(f"{cid}: accepted/excluded 未零截断闭合")
        if any(not str(x.get("reason", "")).strip() for x in excluded_rows if isinstance(x, dict)):
            fails.append(f"{cid}: excluded member 缺 reason")
        if verdict == "pattern_confirmed":
            if not accepted or not row.get("linked_entity_id") or not row.get("evidence"):
                fails.append(f"{cid}: confirmed 缺 accepted/entity/evidence")
            elif entity_map is None:
                fails.append(f"{cid}: confirmed 必须传 --entity-file")
            elif row["linked_entity_id"] not in entity_map \
                    or not accepted <= entity_map[row["linked_entity_id"]]:
                fails.append(f"{cid}: linked entity 与名册不闭合")
        elif accepted:
            fails.append(f"{cid}: 非 confirmed 不得 accepted 成员")
        if str(row.get("raw_balance")) != str(cand["raw"]):
            fails.append(f"{cid}: raw_balance 自报不符")
        if verdict == "unresolved":
            unresolved_raw += cand["raw"]
    net = int((scan.get("denominators") or {}).get("net_supply_raw", 0))
    unresolved_pct = unresolved_raw * 100.0 / net if net else 100.0
    if unresolved_pct + 1e-12 >= DISTRIBUTION_UNRESOLVED_LINE_PCT:
        fails.append(f"distribution unresolved 合计 {unresolved_pct:.6f}% 达经济门 2%")
    if fails: return _report(fails)
    log(f"PASS distribution {len(rows)} 条，unresolved={unresolved_pct:.6f}%")
    return 0


def cmd_pattern_validate(a):
    case_dir = os.path.abspath(a.case_dir); fails = []
    try:
        path = str(safe_case_file(case_dir, a.resolutions))
    except ValueError as exc:
        return _report([str(exc)])
    obj = load_json(path)
    if obj.get("schema") != "pattern-resolutions/v1":
        return _report(["pattern resolutions schema 必须 pattern-resolutions/v1"])
    if not str(obj.get("resolved_at_utc", "")).strip() \
            or not str(obj.get("path_a_excluded_reason", "")).strip():
        fails.append("pattern resolutions 缺完成时间或排除路径 A 的书面理由")
    source = obj.get("source_scan") or {}
    try:
        scan_path, _, cands = distribution_candidates(case_dir, source.get("path"))
        if source.get("sha256") != file_sha(scan_path): fails.append("pattern source_scan 哈希漂移")
    except Exception as exc:
        return _report([str(exc)])
    allowed = {"cex_occlusion", "dust_poisoning", "quota_airdrop", "accounting_mechanism",
               "unidentified_facility", "other"}
    rows = obj.get("resolutions")
    if not isinstance(rows, list): rows = []; fails.append("resolutions 必须是数组")
    ids = [str(x.get("cluster_id")) for x in rows if isinstance(x, dict)]
    expected = {cid.removeprefix("dist-") for cid in cands}
    if len(ids) != len(set(ids)) or set(ids) != expected:
        fails.append("pattern cluster ID 集不闭合或重复")
    for row in rows:
        if not isinstance(row, dict): continue
        cid = str(row.get("cluster_id")); cand = cands.get(f"dist-{cid}")
        if not cand: continue
        code = row.get("mechanism_code"); verdict = row.get("verdict")
        if code not in allowed or verdict not in {"CONFIRMED", "REFUTED", "UNRESOLVED"}:
            fails.append(f"{cid}: mechanism_code 或 verdict 非法")
        members = set(map(str, row.get("affected_members") or []))
        if not members or not members <= cand["members"]:
            fails.append(f"{cid}: affected_members 为空或越出异常簇")
        raw_map = {str(x.get("owner")): int(x.get("raw")) for x in cand["obj"].get("members", [])}
        if str(sum(raw_map[x] for x in members if x in raw_map)) != str(row.get("raw_balance")):
            fails.append(f"{cid}: raw_balance 与成员重算不符")
        refs = row.get("evidence_refs")
        if not isinstance(refs, list) or not refs:
            fails.append(f"{cid}: evidence_refs 为空")
        else:
            for rel in refs:
                try:
                    safe_case_file(case_dir, str(rel))
                except ValueError as exc:
                    fails.append(f"{cid}: evidence_refs 存在非法路径或缺件: {exc}")
                    break
        if verdict == "UNRESOLVED": fails.append(f"{cid}: pattern mechanism 仍 UNRESOLVED")
    return _report(fails) if fails else (log(f"PASS pattern resolutions {len(rows)} 条") or 0)


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
    try:
        out_path = str(safe_case_file(case_dir, a.out, must_exist=False))
    except ValueError as exc:
        return _report([str(exc)])
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
    fails = []
    try:
        jp = str(safe_case_file(case_dir, a.adjudications))
    except ValueError as exc:
        return _report([str(exc)])
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
        try:
            entity_path = safe_case_file(case_dir, a.entity_file)
        except ValueError as exc:
            fails.append(str(exc))
            return _report(fails)
        entity_map, err = load_entity_map_strict(str(entity_path))
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
    dt = sub.add_parser("distribution-template", help="由 final scan 生成分布异常成员级裁决模板")
    dt.add_argument("--case-dir", required=True)
    dt.add_argument("--scan", required=True)
    dt.add_argument("--out", default="distribution_adjudications.json")
    dt.add_argument("--force", action="store_true")
    dv = sub.add_parser("distribution-validate", help="校验分布异常成员级裁决与 2%% 未决线")
    dv.add_argument("--case-dir", required=True)
    dv.add_argument("--adjudications", default="distribution_adjudications.json")
    dv.add_argument("--entity-file", default=None)
    pr = sub.add_parser("pattern-validate", help="校验盘面级解释并拒绝未决机制")
    pr.add_argument("--case-dir", required=True)
    pr.add_argument("--resolutions", default="pattern_resolutions.json")
    a = ap.parse_args()
    try:
        return {"template": cmd_template, "validate": cmd_validate,
                "distribution-template": cmd_distribution_template,
                "distribution-validate": cmd_distribution_validate,
                "pattern-validate": cmd_pattern_validate}[a.subcmd](a)
    except Exception as e:
        print(f"[adjudication] 脚本自身错误（exit 1，修完重跑）: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
