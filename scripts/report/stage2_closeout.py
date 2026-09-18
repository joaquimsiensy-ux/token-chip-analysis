#!/usr/bin/env python3
"""−2 收口（new-analysis）：check / fill-workorder / amend / reseal。

只闭合案根 whale_series.json ↔ 工单选材 ↔ entity_series 实物；不能证明
−3 渲染的 PNG 使用该序列，figure2_check_receipt 同样不能证明 PNG 消费来源。
time_range 本版不消费；图注数字为存在性检查，非逐桶配对。
exit 0=PASS，2=BLOCK，3=reseal 人工停点，1=脚本错。
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path[:0] = [str(HERE), str(REPO / "scripts/lib")]
sys.dont_write_bytecode = True
from case_paths import safe_case_file
import a4_gate
import a5_report_seal
import audit_release_gate
import entity_identity_gate
import facts_gate

SCHEMA = "stage2-closeout/v1"
RECEIPT = "stage2_closeout_receipt.json"
WORKORDER = "a5_assembly_workorder.json"
PENDING = ["fig1/fig2/fig3/流转图渲染", "fig1_legend_receipt", "figure2_check_receipt",
           "a5_report_seal", "build_html"]
PASS_MESSAGE = "PASS: −2 可进入装配；待 −3 执行项：" + "、".join(PENDING)
SERIES_BOUNDARY = ("只闭合案根 whale_series.json ↔ 工单选材 ↔ entity_series 实物；"
                   "不能证明 −3 渲染的 PNG 用的是这份序列；plot_whale_vs_price 接受调用方任意数组，"
                   "figure2_check_receipt 也只绑定被检查的序列文件，同样不能证明 PNG 用了它")
DRYRUN_BOUNDARY = ("允许 A5 缺席；在场 A5 仍由 check_formal_case_chain 核 chain。"
                   "不装载 claim_registry.json，check_claims 不执行，claim_types 为空，"
                   "historical-chart 检查跳过。dryrun 的 report 参数只检查非 None；"
                   "报告内容与 sha 由 closeout #2/#5/#6/#7/#10/#11 承担")


def canon(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(case, rel):
    return digest(safe_case_file(case, rel).read_bytes())


def load(case, rel):
    return json.loads(safe_case_file(case, rel).read_bytes())


def image_refs(text):
    return [value.split()[0].strip("<>") for value in a5_report_seal.IMG_RE.findall(text)]


def skill_commit():
    try:
        proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True)
    except OSError:
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


def freeze_revision(case):
    return len(load(case, "entity_freeze.json")["revisions"]) + 1


def frozen_workorder(obj):
    return {key: value for key, value in obj.items()
            if key not in {"stage2_selfcheck", "amendments", "report_image_refs"}}


def workorder_hashes(obj):
    return {"frozen_sha256": digest(canon(frozen_workorder(obj))),
            "report_image_refs_sha256": digest(canon(obj.get("report_image_refs"))),
            "amendments_sha256": digest(canon(obj.get("amendments"))),
            "amendments_count": len(obj["amendments"])}


def _atomic_json(case, rel, obj):
    target = safe_case_file(case, rel, must_exist=False)
    fd, tmp = tempfile.mkstemp(prefix=".stage2-closeout-", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(canon(obj) + b"\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def terminal_scan(case):
    rounds = load(case, "distribution_rounds.json")
    terminal = rounds["terminal"]
    return load(case, terminal["final_scan_path"])


def caption_same_source(md_text, scan):
    """E2 pure rule: return errors and honest limitations/notes."""
    errors, notes = [], ["存在性检查，非逐桶配对"]
    matches = [match for match in a5_report_seal.IMG_RE.finditer(md_text)
               if match.group(1).split()[0].strip("<>") == "charts/final/holder_distribution_current.png"]
    if len(matches) != 1:
        return ["报告终态分布图片行须唯一"], notes
    line_end = md_text.find("\n", matches[0].end())
    tail = md_text[line_end + 1:] if line_end >= 0 else ""
    paragraph = []
    for line in tail.splitlines():
        if line.strip():
            paragraph.append(line)
        elif paragraph:
            break
    caption = "\n".join(paragraph)
    for name in ("private_main", "private_dust", "public_facility", "unresolved_contract", "burn_sentinel"):
        bucket = scan["bucket_coverage"][name]
        pct = bucket["net_supply_pct"]
        if str(bucket["raw"]) == "0":
            accepted = {"0", "0.0%", "0.00%"}
            notes.append(f"NOTE: {name} raw=0，退化为数字存在性检查")
        elif pct >= 0.01:
            accepted = {f"{pct:.2f}%"}
        elif pct >= 0.00005:
            accepted = {f"{pct:.4f}%"}
        elif pct > 0:
            accepted = {f"{pct:.4f}%", "0.0%", "0.00%", "0"}
            notes.append(f"NOTE: {name} 极小值，退化为数字存在性检查")
        else:
            accepted = set()
        if not any(value in caption for value in accepted):
            errors.append(f"图注与终态 scan 不同源: {name} 期望 {sorted(accepted)} 未出现")
    if re.search(r"HHI|top", caption, re.I):
        small = scan.get("small_sample_mode") or {}
        concentration = scan.get("concentration") or {}
        top = small["top_k"] if scan.get("not_evaluable_reason") == "low_sample" else concentration["top_k_net_pct"]
        hhi = small["hhi"] if scan.get("not_evaluable_reason") == "low_sample" else concentration["hhi"]
        for key in ("1", "3", "5", "10"):
            expected = f"{top[key]:.2f}%"
            if expected not in caption:
                errors.append(f"图注与终态 scan 不同源: top{key} 期望 {expected} 未出现")
        expected = f"{hhi:.4f}"
        if expected not in caption:
            errors.append(f"图注与终态 scan 不同源: HHI 期望 {expected} 未出现")
    else:
        notes.append("NOTE: 图注未披露集中度数字")
    return errors, notes


def workorder_error(field, expected, actual):
    return f"WORKORDER BLOCK: {field}: {expected} != {actual}"


def fig2_selection_errors(facts, fig2):
    errors, notes = [], []
    entities = facts["entities"]
    for entity_id, entity in entities.items():
        label = entity.get("label")
        if not isinstance(label, str) or not label.strip():
            errors.append(workorder_error(f"facts.entities.{entity_id}.label",
                                         f"实体 {entity_id} 无标签，无法判定必画", label))
    import figures_from_facts
    required = figures_from_facts.fig2_required_entity_ids(entities)
    lines = fig2.get("lines")
    declared = fig2.get("required_entity_ids")
    if not isinstance(lines, list) or not lines:
        errors.append(workorder_error("fig2.lines", "非空 list", lines))
        lines = []
    if not isinstance(declared, list):
        errors.append(workorder_error("fig2.required_entity_ids", "list", declared))
        declared = []
    drawn = set()
    for i, line in enumerate(lines):
        entity_id = line.get("entity_id")
        if entity_id not in entities:
            errors.append(workorder_error(f"fig2.lines[{i}].entity_id", "facts 键", "展示名"))
        drawn.add(entity_id)
    if not required <= set(declared):
        errors.append(workorder_error("fig2.required_entity_ids", f"包含下限 {sorted(required)}", declared))
    if not set(declared) <= drawn:
        errors.append(workorder_error("fig2.lines", f"覆盖 required {declared}", sorted(drawn)))
    if "merge_groups" in fig2:
        errors.append(workorder_error("fig2.merge_groups", "本版不支持合并线（范围调整，见 §0 第 6 条）", fig2["merge_groups"]))
    notes.append(f"fig2 required 下限: {sorted(required)}")
    return errors, notes


def flow_selection_errors(facts, flow):
    errors, notes = [], []
    total = facts_gate.Facts(facts).total_raw
    circulating = facts.get("token", {}).get("circulating_supply_raw")
    if circulating is None:
        notes.append("NOTE: 未声明流通量，门槛仅按总供应判")
    else:
        circulating = int(circulating)
        src = facts.get("token", {}).get("circulating_supply_source") or {}
        notes.append(f"NOTE: 流通量 {circulating}（口径 {src.get('source')}，{src.get('asof')}）")
    required = set()
    for entity_id, entity in facts["entities"].items():
        if str(entity.get("label") or "").strip().startswith(("项目方", "大庄")):
            current = int(entity.get("current_raw", "0"))
            if (total > 0 and current * 5 >= total) or (circulating and circulating > 0 and current * 5 >= circulating):
                required.add(entity_id)
    eligible = flow.get("eligible_entity_ids")
    if not isinstance(eligible, list):
        errors.append(workorder_error("flow.eligible_entity_ids", "list", eligible))
        eligible = []
    charts = []
    if "charts" not in flow and "items" not in flow:
        errors.append(workorder_error("flow.charts|items", "至少一键", "均缺失"))
    for key in ("charts", "items"):
        if key in flow:
            if not isinstance(flow[key], list):
                errors.append(workorder_error(f"flow.{key}", "list", flow[key]))
            else:
                charts.extend(flow[key])
    drawn = {row.get("entity_id") for row in charts}
    if not required <= set(eligible):
        errors.append(workorder_error("flow.eligible_entity_ids", f"包含下限 {sorted(required)}", eligible))
    if drawn != set(eligible):
        errors.append(workorder_error("flow.charts|items.entity_id", f"等于 eligible {eligible}", sorted(drawn, key=str)))
    notes.append(f"flow 下限: {sorted(required)}；图中实体: {sorted(drawn, key=str)}")
    return errors, notes


PRICE_POINT_STATUSES = ("PASS", "WARN", "SKIP", "FAIL")


def price_receipt_errors(case, bindings):
    """F05：价格双源收据必须是 price_check.py 产物且结论可放行——从 points 按 price_check 同规则
    重算 verdict 并要求一致；只放行 PASS/WARN（WARN 记 NOTE）；price_file_sha256 须等于
    bindings.price_source.sha256；引用取 bindings.price_source_checks，否则取内联
    price_source.dual_source_check.receipt；两者皆无＝纯申报对象，拒。返回 (errors, notes, ref)。"""
    errors, notes = [], []
    price_source = bindings.get("price_source") if isinstance(bindings.get("price_source"), dict) else {}
    ref = bindings.get("price_source_checks")
    if ref is None:
        inline = price_source.get("dual_source_check")
        ref = inline.get("receipt") if isinstance(inline, dict) else None
    if not (isinstance(ref, dict) and isinstance(ref.get("path"), str)
            and isinstance(ref.get("sha256"), str) and ref["sha256"]):
        errors.append(workorder_error("bindings.price_source_checks|price_source.dual_source_check.receipt",
                                      "price_check.py 收据引用 {path,sha256}（纯申报对象不放行）", ref))
        return errors, notes, None
    try:
        receipt = load(case, ref["path"])
    except (OSError, ValueError) as exc:
        errors.append(workorder_error("bindings.price_source_checks.path", "可读取的收据 JSON", str(exc)))
        return errors, notes, ref
    points = receipt.get("points") if isinstance(receipt, dict) else None
    if not isinstance(points, list) or not points:
        errors.append(workorder_error("bindings.price_source_checks.points", "非空 list", points))
        return errors, notes, ref
    statuses = [(p.get("status") if isinstance(p, dict) else None) for p in points]
    expected = ("FAIL" if any(s not in PRICE_POINT_STATUSES or s == "FAIL" for s in statuses)
                else "ALL_SKIP" if all(s == "SKIP" for s in statuses)
                else "WARN" if "WARN" in statuses else "PASS")
    if receipt.get("verdict") != expected:
        errors.append(workorder_error("bindings.price_source_checks.verdict",
                                      f"与 points 重算一致（{expected}）", receipt.get("verdict")))
    if expected not in ("PASS", "WARN"):
        errors.append(workorder_error("bindings.price_source_checks.verdict",
                                      "PASS|WARN（FAIL/ALL_SKIP 禁入装配：换源或人工裁决后重跑 price_check）", expected))
    for key in ("main_source", "second_source"):
        if not isinstance(receipt.get(key), str) or not receipt[key].strip():
            errors.append(workorder_error(f"bindings.price_source_checks.{key}", "非空字符串", receipt.get(key)))
    bound = receipt.get("price_file_sha256")
    if not isinstance(bound, str) or not bound:
        errors.append(workorder_error("bindings.price_source_checks.price_file_sha256",
                                      "在场（旧收据无此字段：用当前 price_check.py 重跑）", bound))
    elif bound != price_source.get("sha256"):
        errors.append(workorder_error("bindings.price_source_checks.price_file_sha256",
                                      f"= bindings.price_source.sha256 {price_source.get('sha256')}", bound))
    if not errors and expected == "WARN":
        notes.append(f"NOTE: 价格双源 WARN 点 {statuses.count('WARN')} 个（>5% 过目口径，见 report-template 2b）")
    return errors, notes, ref


def amendment_errors(row, field):
    errors = []
    if not isinstance(row, dict):
        return [workorder_error(field, "amendment 对象", row)]
    for key in ("before_sha256", "after_sha256", "trigger", "approved_by"):
        if not isinstance(row.get(key), str) or not row[key].strip():
            errors.append(workorder_error(f"{field}.{key}", "非空字符串", row.get(key)))
    change = row.get("exact_change")
    if not isinstance(change, dict) or any(not isinstance(change.get(key), str) for key in ("before", "after")):
        errors.append(workorder_error(f"{field}.exact_change", "before/after 字符串", change))
    if "approval_text" in row and not str(row["approval_text"] or "").strip():
        errors.append(workorder_error(f"{field}.approval_text", "非空", row["approval_text"]))
    return errors


def walk_objects(obj, prefix=""):
    if isinstance(obj, dict):
        yield prefix, obj
        for key, value in obj.items():
            field = f"{prefix}.{key}" if prefix else key
            if field not in {"stage2_selfcheck", "bindings.report_md"}:
                yield from walk_objects(value, field)
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            yield from walk_objects(value, f"{prefix}[{i}]")


def workorder_errors(case, report_rel, workorder_rel=WORKORDER, *, obj=None, facts=None, md_text=None):
    """E3 selection rules and current on-disk bindings; no writes."""
    obj = load(case, workorder_rel) if obj is None else obj
    facts = load(case, "facts.json") if facts is None else facts
    md_text = safe_case_file(case, report_rel).read_bytes().decode("utf-8") if md_text is None else md_text
    errors, notes = [], []

    def need(field, expected, actual, condition):
        if not condition:
            errors.append(workorder_error(field, expected, actual))

    for key in ("note", "meta", "bindings", "report_image_refs", "fig1", "fig2", "fig3", "flow", "amendments"):
        need(key, "必备顶层键", "缺失", key in obj)
    bindings = obj.get("bindings") or {}
    terminal = load(case, "distribution_rounds.json")["terminal"]
    anchor = bindings.get("report_md") or {}
    need("bindings.report_md.path", report_rel, anchor.get("path"), anchor.get("path") == report_rel)
    safe_case_file(case, report_rel)
    report_sha = file_sha(case, report_rel)
    amendments = obj.get("amendments")
    need("amendments", "list", amendments, isinstance(amendments, list))
    amendments = amendments if isinstance(amendments, list) else []
    prior = anchor.get("sha256")
    for i, row in enumerate(amendments):
        errors.extend(amendment_errors(row, f"amendments[{i}]"))
        if not isinstance(row, dict):
            continue
        need(f"amendments[{i}].before_sha256", prior, row.get("before_sha256"), row.get("before_sha256") == prior)
        prior = row.get("after_sha256")
    need("amendments[-1].after_sha256" if amendments else "bindings.report_md.sha256",
         report_sha, prior, prior == report_sha)
    for key, expected in (("a4_seal_sha256", file_sha(case, "a4_seal.json")),
                          ("entity_freeze_revision", freeze_revision(case))):
        need(f"bindings.{key}", expected, bindings.get(key), bindings.get(key) == expected)
    required_refs = []
    for key, expected in (("facts", "facts.json"), ("state", "analysis-state.json"), ("rounds", "distribution_rounds.json")):
        ref = bindings.get(key)
        required_refs.append((f"bindings.{key}", ref))
        actual = ref.get("path") if isinstance(ref, dict) else None
        need(f"bindings.{key}.path", expected, actual, actual == expected)
    for key in ("final_scan_path", "final_chart_path"):
        matches = [(field, ref) for field, ref in walk_objects(bindings, "bindings") if ref.get("path") == terminal[key]]
        need(f"bindings.{key}", f"存在 path={terminal[key]} 的绑定", matches, bool(matches))
        required_refs.extend(matches)
    bound_terminal = bindings.get("distribution_terminal") or {}
    for key in ("status", "round_n"):
        need(f"bindings.distribution_terminal.{key}", terminal[key], bound_terminal.get(key), bound_terminal.get(key) == terminal[key])
    refs = image_refs(md_text)
    need("report_image_refs", refs, obj.get("report_image_refs"), obj.get("report_image_refs") == refs)
    fig1, fig2, fig3, flow = (obj.get(key) for key in ("fig1", "fig2", "fig3", "flow"))
    for key, value in (("fig1", fig1), ("fig2", fig2), ("fig3", fig3), ("flow", flow)):
        need(key, "对象", value, isinstance(value, dict))
    fig1, fig2, fig3, flow = (value if isinstance(value, dict) else {} for value in (fig1, fig2, fig3, flow))
    for key, value in (("fig1", fig1), ("fig2", fig2), ("fig3", fig3)):
        need(f"{key}.out", "str", value.get("out"), isinstance(value.get("out"), str))
    for key in ("state", "price_csv", "overlay", "out"):
        need(f"fig1.{key}", "键必须存在", "缺失", key in fig1)
    expected_state = (bindings.get("state") or {}).get("path")
    need("fig1.state", expected_state, fig1.get("state"), fig1.get("state") == expected_state)
    events = fig3.get("events")
    need("fig3.events", "非空 list", events, isinstance(events, list) and bool(events))
    for i, event in enumerate(events if isinstance(events, list) else []):
        valid = isinstance(event, dict) and "label" in event and isinstance(event.get("date"), str)
        try:
            valid = valid and date.fromisoformat(event["date"]).isoformat() == event["date"]
        except ValueError:
            valid = False
        need(f"fig3.events[{i}]", "date=YYYY-MM-DD 与 label", event, valid)
    for key, aliases in (("price", ("price", "price_input")), ("volume", ("volume", "volume_input"))):
        alias = next((name for name in aliases if name in fig3), aliases[0])
        required_refs.append((f"fig3.{alias}", fig3.get(alias)))
    required_refs.append(("fig3.events_input", fig3.get("events_input")))
    lines = fig2.get("lines") if isinstance(fig2.get("lines"), list) else []
    for i, line in enumerate(lines):
        required_refs.append((f"fig2.lines[{i}].series_source", line.get("series_source")))
    for key in ("charts", "items"):
        for i, row in enumerate(flow.get(key) if isinstance(flow.get(key), list) else []):
            required_refs.append((f"flow.{key}[{i}].spec", row.get("spec")))
    price_source = bindings.get("price_source")
    required_refs.append(("bindings.price_source", price_source))
    price_path = price_source.get("path") if isinstance(price_source, dict) else None
    price2 = fig2.get("price_source", fig2.get("price"))
    price2_path = price2.get("path") if isinstance(price2, dict) else price2
    need("fig2.price_source|price", f"与 bindings.price_source.path={price_path} 同路径",
         price2_path, isinstance(price_path, str) and price2_path == price_path)
    price_errors, price_notes, price_ref = price_receipt_errors(case, bindings)
    errors.extend(price_errors)
    notes.extend(price_notes)
    if price_ref is not None:
        required_refs.append(("bindings.price_source_checks", price_ref))

    def self_reference(field, ref):
        return (field == "fig3.events_input" and isinstance(ref, dict)
                and ref.get("path") == workorder_rel and ref.get("key") == "fig3.events"
                and "sha256" in ref and ref["sha256"] in (None, ""))

    for field, ref in required_refs:
        if self_reference(field, ref):
            continue
        need(field, "{path,sha256} 完整且 sha256 非空", ref,
             isinstance(ref, dict) and isinstance(ref.get("path"), str)
             and isinstance(ref.get("sha256"), str) and bool(ref["sha256"]))
    verified_paths = set()
    for field, ref in walk_objects(obj):
        if "path" in ref:
            try:
                path = safe_case_file(case, ref["path"])
                if "sha256" in ref:
                    if self_reference(field, ref):
                        notes.append("NOTE: fig3.events_input 是工单 fig3.events 自引用，空哈希不核")
                    else:
                        actual = digest(path.read_bytes())
                        need(field + ".sha256", actual, ref["sha256"], actual == ref["sha256"])
                        if actual == ref["sha256"]:
                            verified_paths.add(ref["path"])
            except (OSError, ValueError) as exc:
                errors.append(workorder_error(field + ".path", "案内普通文件", str(exc)))
        if "out" in ref:
            value = ref["out"]
            try:
                safe_case_file(case, value, must_exist=False)
                if not value.startswith("charts/final/") or not value.endswith(".png"):
                    raise ValueError(value)
            except (OSError, ValueError, AttributeError) as exc:
                errors.append(workorder_error(field + ".out", "charts/final/*.png", str(exc)))
    if fig1.get("price_csv"):
        value = fig1["price_csv"]
        need("fig1.price_csv", "已通过 sha256 重验引用的 path", value,
             isinstance(value, str) and value in verified_paths)
    for i, line in enumerate(lines):
        source = line.get("series_source") or {}
        try:
            series = load(case, source.get("path"))
            need(f"fig2.lines[{i}].series_source.key", "entity_series 中的 key", source.get("key"), source.get("key") in series)
        except Exception as exc:
            errors.append(workorder_error(f"fig2.lines[{i}].series_source", "可读取的 entity_series", str(exc)))
    for validator, value in ((fig2_selection_errors, fig2), (flow_selection_errors, flow)):
        found, extra = validator(facts, value)
        errors.extend(found)
        notes.extend(extra)
    return errors, notes


def fig2_series_errors(case, workorder_rel=WORKORDER):
    import figures_from_facts

    errors, notes = [], ["NOTE: time_range 未核", SERIES_BOUNDARY]
    out = safe_case_file(case, "whale_series.json", must_exist=False)
    sidecar = safe_case_file(case, "whale_series.provenance.json", must_exist=False)
    if not out.exists() and not sidecar.exists():
        return ["未生成 whale_series：运行 `figures_from_facts.py fig2-series` 生成（历史案迁移办法同此）"], notes
    provenance = load(case, "whale_series.provenance.json")
    workorder = load(case, workorder_rel)
    if provenance.get("schema") != "fig2-series-provenance/v1":
        errors.append("旁车 schema 非 fig2-series-provenance/v1")
    if (provenance.get("out") or {}).get("path") != "whale_series.json":
        errors.append("旁车 out 非案根 whale_series.json")
    for name in ("entity_series", "facts", "out"):
        ref = provenance.get(name) or {}
        try:
            if ref.get("sha256") != file_sha(case, ref.get("path")):
                errors.append(f"旁车 {name}.sha256 与实物不等")
        except (OSError, ValueError) as exc:
            errors.append(f"旁车 {name}.path 非案内实物: {exc}")
    facts_ref = provenance.get("facts") or {}
    if facts_ref.get("path") != workorder["bindings"]["facts"]["path"]:
        errors.append("旁车 facts.path 与工单 bindings.facts.path 不等")
    lines = workorder["fig2"]["lines"]
    source = provenance.get("entity_series") or {}
    source_keys, entity_ids = [], []
    for i, line in enumerate(lines):
        ref = line.get("series_source") or {}
        for key in ("path", "sha256"):
            if ref.get(key) != source.get(key):
                errors.append(f"fig2.lines[{i}].series_source.{key} 与旁车 entity_series.{key} 不等")
        key, entity_id = ref.get("key"), line.get("entity_id")
        source_keys.append(key)
        entity_ids.append(entity_id)
        if entity_id != key:
            errors.append(f"fig2.lines[{i}].entity_id 与 series_source.key 逐行错配")
    keys = provenance.get("keys")
    if not isinstance(keys, list) or len(keys) != len(set(keys)):
        errors.append("旁车 keys 非 list 或重复")
        keys = []
    if len(source_keys) != len(set(source_keys)):
        errors.append("工单 series_source.key 重复")
    if len(entity_ids) != len(set(entity_ids)):
        errors.append("工单 lines.entity_id 重复")
    if set(source_keys) != set(keys):
        errors.append("工单 series_source keys 集合与旁车 keys 不等")
    facts = load(case, facts_ref.get("path"))
    try:
        replay = figures_from_facts.dumps_fig2_series(figures_from_facts.build_fig2_series(
            load(case, source.get("path")), facts, keys))
        if replay != out.read_bytes():
            errors.append("whale_series 重放字节不符")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"whale_series 重放失败: {exc}")
    check_errors, _count = figures_from_facts.fig2_check_errors(
        safe_case_file(case, facts_ref.get("path")), safe_case_file(case, "whale_series.json"),
        figures_from_facts.DEFAULT_TOL_PP)
    errors.extend(check_errors)
    series = load(case, "whale_series.json")
    if not isinstance(series, list):
        return errors + ["whale_series 非 list"], notes
    series_ids = [line.get("entity_id") for line in series]
    if len(series_ids) != len(set(series_ids)):
        errors.append("whale_series entity_id 重复")
    if set(series_ids) != set(entity_ids):
        errors.append("whale_series entity_id 集合与工单 lines 不等")
    for i, line in enumerate(series):
        entity = facts["entities"].get(line.get("entity_id")) or {}
        if not entity or line.get("label") != entity.get("label"):
            errors.append(f"whale_series[{i}].label 与 facts 不同源")
    for i, line in enumerate(lines):
        label = line.get("display_label")
        if not isinstance(label, str) or not label.strip():
            errors.append(f"fig2.lines[{i}].display_label 为空")
        elif label != (facts["entities"].get(line.get("entity_id")) or {}).get("label"):
            notes.append(f"NOTE: fig2.lines[{i}] 展示名为缩写")
    return errors, notes


def run_checks(case, report_rel, workorder_rel=WORKORDER):
    """Run every check even after exceptions. NOTE/ABSENT never block."""
    checks = []

    def record(name, fn):
        try:
            errors, notes, status = fn()
            checks.append({"name": name, "status": "BLOCK" if errors else status,
                           "detail": list(errors) + list(notes)})
        except (Exception, SystemExit) as exc:
            message = f"{type(exc).__name__}: {exc}"
            if name == "workorder":
                message = workorder_error("workorder", "可读取的合法工单和绑定", message)
            checks.append({"name": name, "status": "BLOCK",
                           "detail": [message]})

    def report_path():
        return safe_case_file(case, report_rel)

    def report_text():
        return report_path().read_bytes().decode("utf-8")

    def seal_check():
        seal = load(case, "a4_seal.json")
        errors, _paths = a4_gate.seal_integrity_errors(case, seal)
        if seal.get("workflow_type") != "new-analysis":
            errors.append("stage2_closeout 只服务 new-analysis：a4_seal.workflow_type 非 new-analysis")
        return errors, [], "PASS"

    def downstream():
        rows = a4_gate.downstream_stale(case)
        errors = [json.dumps(row, ensure_ascii=False) for row in rows if row["status"] == "stale"]
        return errors, [json.dumps(row, ensure_ascii=False) for row in rows if row["status"] != "stale"] + [
            "fix_order: " + a4_gate.DOWNSTREAM_FIX_ORDER], "ABSENT" if all(row["status"] == "absent" for row in rows) else "PASS"

    def bundle(which):
        seal = load(case, "a4_seal.json")
        if which == "flip":
            value = a5_report_seal.provenance_flip_bundle(case, report_text(), seal)
            allowed = {"DISCLOSED", "NO_LEDGER", "NO_FLIPS"}
        else:
            value = a5_report_seal.distribution_bundle(case, report_path(), seal)
            allowed = {"NORMAL", "LOW_SAMPLE", "EXPLAINED", "WAIVED"}
        status = value.get("status")
        return ([] if status in allowed else [f"bundle status 不可放行: {status}"],
                [f"status={status}"], "PASS")

    def caption():
        errors, notes = caption_same_source(report_text(), terminal_scan(case))
        status = "NOTE" if "NOTE: 图注未披露集中度数字" in notes else "PASS"
        return errors, notes, status

    def dual():
        facts = load(case, "facts.json")
        if "dual_basis" not in facts:
            return [], ["未声明双口径"], "NOTE"
        basis, text = facts["dual_basis"], report_text()
        errors = []
        for key in ("lower", "upper"):
            metric = basis.get(key)
            if metric not in facts.get("metrics", {}) or "{{m:" + str(metric) + "}}" not in text:
                errors.append(f"dual_basis.{key} 未在 facts.metrics 与报告宏中同时出现: {metric}")
        return errors, [], "PASS"

    def rules(fn):
        errors, notes = fn()
        return errors, notes, "PASS"

    def facts_check():
        _rendered, errors, notes = facts_gate.load_and_check(
            safe_case_file(case, "facts.json"), safe_case_file(case, "analysis-state.json"), report_text())
        return errors, notes, "PASS"

    record("release_gate_dryrun", lambda: (
        audit_release_gate.run(case, report_path(), profile="stage2-dryrun"), [DRYRUN_BOUNDARY], "PASS"))
    record("a4_seal_integrity", seal_check)
    record("downstream_stale", downstream)
    record("identity_gate", lambda: (entity_identity_gate.validate_gate(
        safe_case_file(case, "identity_gate.json"), safe_case_file(case, "analysis-state.json"),
        require_resolved=True), [], "PASS"))
    record("a5_provenance_flip", lambda: bundle("flip"))
    record("a5_distribution", lambda: bundle("distribution"))
    record("caption_same_source", caption)
    record("dual_basis", dual)
    record("fig2_series", lambda: rules(lambda: fig2_series_errors(case, workorder_rel)))
    record("workorder", lambda: rules(lambda: workorder_errors(case, report_rel, workorder_rel)))

    def facts_vs_ledgers():
        errors = []
        audit_release_gate.check_facts_vs_ledgers(case, load(case, "facts.json"), errors)
        return errors, [], "PASS"

    record("facts_gate", facts_check)
    record("facts_vs_ledgers", facts_vs_ledgers)
    return checks


def verdict(checks):
    return "BLOCK" if any(check["status"] == "BLOCK" for check in checks) else "PASS"


def receipt_document(case, report_rel, workorder_rel, checks):
    # Failed checks still yield a receipt, including when input files are absent.
    def optional(fn):
        try:
            return fn()
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return None

    hashes = optional(lambda: workorder_hashes(load(case, workorder_rel))) or {
        key: None for key in ("frozen_sha256", "report_image_refs_sha256", "amendments_sha256", "amendments_count")}
    terminal = optional(lambda: load(case, "distribution_rounds.json")["terminal"]) or {}
    series_sha = optional(lambda: file_sha(case, "whale_series.json"))
    return {"schema": SCHEMA, "verdict": verdict(checks),
            "report_md": {"path": report_rel, "sha256": optional(lambda: file_sha(case, report_rel))},
            "workorder": {"path": workorder_rel, **hashes},
            "facts": {"sha256": optional(lambda: file_sha(case, "facts.json"))},
            "state": {"sha256": optional(lambda: file_sha(case, "analysis-state.json"))},
            "entity_freeze_revision": optional(lambda: freeze_revision(case)),
            "a4_seal_sha256": optional(lambda: file_sha(case, "a4_seal.json")),
            "rounds": {"sha256": optional(lambda: file_sha(case, "distribution_rounds.json")),
                       "terminal_round_n": terminal.get("round_n"), "status": terminal.get("status")},
            "whale_series": {"path": "whale_series.json", "sha256": series_sha} if series_sha else None,
            "skill_commit": skill_commit(), "checks": checks, "pending_for_stage3": list(PENDING),
            "amendment_chain": []}


def receipt_only_errors(case, report_rel, workorder_rel=WORKORDER):
    errors = []

    def drift(item):
        errors.append(f"closeout 收据与现场漂移: {item}，退回 −2 重跑 stage2_closeout")

    try:
        receipt = load(case, RECEIPT)
        if receipt.get("schema") != SCHEMA:
            drift("schema")
            return errors
    except (OSError, ValueError, AttributeError) as exc:
        drift(f"schema/receipt: {exc}")
        return errors

    for key in ("report_md", "workorder", "facts", "state", "rounds"):
        if not isinstance(receipt.get(key), dict):
            drift(key)
    chain = receipt.get("amendment_chain")
    if not isinstance(chain, list) or any(not isinstance(row, dict) for row in chain):
        drift("amendment_chain")
    series = receipt.get("whale_series")
    if series is not None and not isinstance(series, dict):
        drift("whale_series")
    if errors:
        return errors

    def compare(item, fn, expected):
        try:
            if fn() != expected:
                drift(item)
        except (Exception, SystemExit) as exc:
            drift(f"{item}: {exc}")

    expected_report = chain[-1].get("after_sha256") if chain else receipt.get("report_md", {}).get("sha256")
    compare("report_md.path", lambda: report_rel, receipt.get("report_md", {}).get("path"))
    compare("report_md.sha256", lambda: file_sha(case, report_rel), expected_report)
    binding = receipt.get("workorder") or {}
    compare("workorder.path", lambda: workorder_rel, binding.get("path"))
    for key in ("frozen_sha256", "report_image_refs_sha256", "amendments_sha256", "amendments_count"):
        compare(key, lambda key=key: workorder_hashes(load(case, workorder_rel))[key], binding.get(key))
    for key, rel in (("facts", "facts.json"), ("state", "analysis-state.json"), ("rounds", "distribution_rounds.json")):
        compare(key, lambda rel=rel: file_sha(case, rel), (receipt.get(key) or {}).get("sha256"))
    compare("a4_seal_sha256", lambda: file_sha(case, "a4_seal.json"), receipt.get("a4_seal_sha256"))
    compare("entity_freeze_revision", lambda: freeze_revision(case), receipt.get("entity_freeze_revision"))
    if series is None:
        compare("whale_series", lambda: safe_case_file(case, "whale_series.json", must_exist=False).exists(), False)
    else:
        compare("whale_series.path", lambda: series.get("path"), "whale_series.json")
        compare("whale_series.sha256", lambda: file_sha(case, "whale_series.json"), series.get("sha256"))
    compare("skill_commit；skill 已换版，重跑 stage2_closeout", skill_commit, receipt.get("skill_commit"))
    compare("verdict", lambda: receipt.get("verdict"), "PASS")
    return errors


def fill_workorder(case, report_rel, workorder_rel=WORKORDER):
    path = safe_case_file(case, workorder_rel, must_exist=False)
    skeleton = {
        "note": None, "meta": {}, "bindings": {}, "report_image_refs": [],
        "fig1": {"state": None, "price_csv": None, "overlay": None, "out": None},
        "fig2": {"lines": None, "required_entity_ids": None, "price_source": None, "out": None},
        "fig3": {"price": None, "volume": None, "events_input": None, "events": None, "out": None},
        "flow": {"eligible_entity_ids": None, "charts": None}, "amendments": []}
    obj = load(case, workorder_rel) if path.exists() else {}
    for key, value in skeleton.items():
        if key not in obj:
            obj[key] = value
        elif key in {"fig1", "fig2", "fig3", "flow"} and isinstance(obj[key], dict):
            for field, default in value.items():
                # Preserve the two supported alias shapes when adding empty selections.
                if (key, field) == ("flow", "charts") and "items" in obj[key]:
                    continue
                if (key, field) in {("fig3", "price"), ("fig3", "volume")} and field + "_input" in obj[key]:
                    continue
                if (key, field) == ("fig2", "price_source") and "price" in obj[key]:
                    continue
                obj[key].setdefault(field, default)
    bindings = obj.setdefault("bindings", {})
    terminal = load(case, "distribution_rounds.json")["terminal"]
    def ref(rel):
        return {"path": rel, "sha256": file_sha(case, rel)}
    bindings.update({"a4_seal_sha256": file_sha(case, "a4_seal.json"),
                     "entity_freeze_revision": freeze_revision(case),
                     "facts": ref("facts.json"), "state": ref("analysis-state.json"),
                     "rounds": ref("distribution_rounds.json"),
                     "final_distribution_png": ref(terminal["final_chart_path"]),
                     "final_distribution_scan": ref(terminal["final_scan_path"]),
                     "distribution_terminal": {key: terminal[key] for key in ("status", "round_n")}})
    if "report_md" not in bindings:
        bindings["report_md"] = ref(report_rel)
    obj["report_image_refs"] = image_refs(safe_case_file(case, report_rel).read_bytes().decode("utf-8"))
    obj.setdefault("meta", {}).update({"skill_version": (REPO / "VERSION").read_text(encoding="utf-8").strip(),
                                      "skill_commit": skill_commit(),
                                      "produced_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    _atomic_json(case, workorder_rel, obj)
    pending = [field + "." + key if field else key for field, row in walk_objects(obj)
               for key, value in row.items() if value is None]
    print("待 −2 亲笔: " + ("、".join(pending) or "无空字段；选材仍由 −2 负责"))
    return obj


def amend(case, report_rel, previous_rel=None):
    """Validate the immutable prefix and byte-exact approved replacement before writing."""
    receipt = load(case, RECEIPT)
    if receipt.get("schema") != SCHEMA or receipt.get("verdict") != "PASS":
        return ["amend 前置：须在场的 PASS stage2-closeout/v1 收据"], None
    if receipt.get("report_md", {}).get("path") != report_rel:
        return ["amend report_md.path 与收据不等"], None
    workorder_rel = receipt["workorder"]["path"]
    obj = load(case, workorder_rel)
    hashes = workorder_hashes(obj)
    bound = receipt["workorder"]
    if hashes["frozen_sha256"] != bound.get("frozen_sha256"):
        return ["工单冻结字段已改（frozen_sha256 漂移）：退回 −2 重跑 stage2_closeout"], None
    amendments = obj["amendments"]
    if (len(amendments) != bound.get("amendments_count", -1) + 1
            or digest(canon(amendments[:-1])) != bound.get("amendments_sha256")):
        return ["amendments 旧前缀已变或追加数量不为 1（amendments_sha256/count）"], None
    row = amendments[-1]
    errors = amendment_errors(row, "amendments[-1]")
    if errors:
        return errors, None
    chain = receipt.get("amendment_chain") or []
    current_sha = chain[-1]["after_sha256"] if chain else receipt["report_md"]["sha256"]
    current_bytes = safe_case_file(case, report_rel).read_bytes()
    if row["before_sha256"] != current_sha or row["after_sha256"] != digest(current_bytes):
        return ["amend before_sha256/after_sha256 与收据或报告实物不等"], None
    before = row["exact_change"]["before"].encode("utf-8")
    after = row["exact_change"]["after"].encode("utf-8")
    if after and current_bytes.count(after) == 1:
        replay_ok = digest(current_bytes.replace(after, before, 1)) == row["before_sha256"]
    elif previous_rel:
        previous = safe_case_file(case, previous_rel).read_bytes()
        replay_ok = (digest(previous) == row["before_sha256"] and bool(before) and previous.count(before) == 1
                     and digest(previous.replace(before, after, 1)) == digest(current_bytes))
    else:
        return ["实际改动与 exact_change 不符：正文混入未获准改动；after 为空或不唯一时必须传 --previous"], None
    if not replay_ok:
        return ["实际改动与 exact_change 不符：正文混入未获准改动"], None
    checks = run_checks(case, report_rel, workorder_rel)
    if verdict(checks) != "PASS":
        return [f"{check['name']}: {detail}" for check in checks if check["status"] == "BLOCK"
                for detail in check["detail"]], None
    updated = receipt_document(case, report_rel, workorder_rel, checks)
    updated["amendment_chain"] = chain + [{"before_sha256": row["before_sha256"],
                                         "after_sha256": row["after_sha256"], "verdict": "PASS"}]
    _atomic_json(case, RECEIPT, updated)
    return [], updated


def reseal_stop(code, message):
    print(message)
    raise SystemExit(code)


def reseal_cli(case, script, *arguments, execute=True):
    command = [sys.executable, "-B", str(HERE / script), *map(str, arguments),
               "--case-dir", str(case)]
    print("命令｜" + shlex.join(command))
    if not execute:
        return None
    proc = subprocess.run(command, cwd=str(case),
                          env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                          capture_output=True, text=True)
    print(proc.stdout, end="")
    print(proc.stderr, end="", file=sys.stderr)
    return proc


def reseal_require(case, script, *arguments):
    proc = reseal_cli(case, script, *arguments)
    if proc.returncode:
        reseal_stop(2, f"前置不过：{script} exit {proc.returncode}")
    return proc


def reseal_ledger(case):
    import holder_distribution_scan as scanner
    if not (case / "distribution_rounds.json").exists():
        return {"rounds": [], "terminal": None}
    ledger = load(case, "distribution_rounds.json")
    if not isinstance(ledger, dict):
        raise ValueError("rounds 台账必须是对象")
    errors = scanner.validate_rounds_ledger(ledger)
    if errors:
        raise ValueError("; ".join(errors))
    return ledger


def reseal_identity(case, path):
    return path.resolve().relative_to(case).as_posix()


def reseal_move_sets(case, ledger):
    m3, m4 = set(), set()
    final = case / "charts/final"
    if final.exists():
        for entry in final.iterdir():
            if entry.name == "holder_distribution_current.png":
                continue
            files = entry.rglob("*") if entry.is_dir() else [entry]
            for path in files:
                if path.is_file():
                    m3.add(reseal_identity(case, path))
    if ledger.get("terminal") is not None:
        m4.add("distribution_rounds.json")
        for path in (case / "dist_rounds").rglob("*"):
            if path.is_file():
                m4.add(reseal_identity(case, path))
        m4.add(reseal_identity(case, case / ledger["terminal"]["final_chart_path"]))
    return m3, m4


def reseal_sealed_paths(case, seal):
    rows = list(seal.get("sealed_files", []))
    rows += [seal.get(key) for key in ("registry", "verdicts", "distribution_claim_source")]
    return {reseal_identity(case, safe_case_file(case, row["path"], must_exist=False))
            for row in rows if isinstance(row, dict) and row.get("path")}


def reseal_adjudication_dependencies(case, scan_rel, entity_file):
    """Use each consumer's resolver before comparing resolved case identities."""
    import holder_distribution_scan as scanner
    dependencies = set()

    def add(rel):
        path = scanner.safe_file(case, rel, "裁决校验依赖")
        dependencies.add(reseal_identity(case, path))

    scan = load(case, scan_rel)
    if not isinstance(scan, dict) or not isinstance(scan.get("input_binding"), dict):
        raise ValueError("裁决 scan/input_binding 必须是对象")

    def walk(value, keys=()):
        if keys[:2] == ("algorithm", "files") or keys == ("labels_manifest",):
            return
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "path":
                    add(item)
                else:
                    walk(item, keys + (key,))
        elif isinstance(value, list):
            for item in value:
                walk(item, keys)

    add(scan_rel)
    walk(scan["input_binding"])
    for rel in ("handoff_manifest.json", "identity_snapshot_receipt.json", "a4_seal.json",
                "entity_freeze.json", "membership_ledger.json", "position_ledger.json",
                "economic_control_ledger.json", "distribution_scan.json",
                "distribution_adjudications.json"):
        add(rel)
    if (case / "distribution_rounds.json").exists():
        add("distribution_rounds.json")
        ledger = reseal_ledger(case)
        for row in ledger["rounds"]:
            if row.get("round_n") == scan.get("round"):
                add(row["final_scan_path"])
    if (case / "distribution_reopen.json").exists():
        add("distribution_reopen.json")
        scanner.validate_reopen_receipt(case)
        last = load(case, "distribution_reopen.json")["cycles"][-1]
        for row in last["archived"]:
            add(row["to"])
        snapshot = f"data/stage2/dist_cycle{last['cycle']}/a4_snapshot/a4_seal.json"
        if (case / snapshot).exists():
            add(snapshot)
    if entity_file is not None:
        dependencies.add(reseal_identity(case, safe_case_file(case, entity_file)))
    return dependencies


def reseal_archive(case, m3, m4, terminal, entity_file=None, *,
                   sealed_paths=(), from_layer="rounds", dry_run=False):
    """Shared A0.3–A0.5; every predictable refusal precedes all mutations."""
    case = Path(case).resolve()
    adjudication = case / "distribution_adjudications.json"
    p, m5, prevalidated = None, set(), []
    validate_args = ["distribution-validate"]
    if entity_file is not None:
        validate_args += ["--entity-file", entity_file]
    try:
        if adjudication.exists() or adjudication.is_symlink():
            p = reseal_identity(case, safe_case_file(
                case, load(case, "distribution_adjudications.json")["source_scan"]["path"]))
            if p in m4:
                m5 = {"distribution_adjudications.json"}
            elif terminal or p in m3:
                reseal_stop(3, f"裁决文件绑定的 scan {p} 不随周期归档/将被本步搬走，"
                            "归档后其绑定必失效且 A0.5 不承接：人工处置（把裁决件移出案根或改绑；"
                            "终态后由 −2 重新承接裁决）")
            else:
                overlap = reseal_adjudication_dependencies(case, p, entity_file) & m3
                if overlap:
                    reseal_stop(3, "裁决校验依赖 " + ", ".join(sorted(overlap)) +
                                " 将被本步搬走，归档后裁决必失效且 A0.5 不承接：人工处置（改绑或把裁决件移出案根）")
                reseal_require(case, "adjudication_validator.py", *validate_args)
                prevalidated.append(p)
        overlap = set(sealed_paths) & (m3 | m4 | m5)
        if from_layer == "rounds" and overlap:
            reseal_stop(3, "\n".join(f"归档将搬走 seal 封入的文件 {rel}，seal 会失效：改走 `--from a4`"
                                    for rel in sorted(overlap)))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        reseal_stop(2, f"A0.3 前置不过：{exc}")
    entries = []
    final = case / "charts/final"
    if final.exists():
        entries = [path.relative_to(case).as_posix() + ("/" if path.is_dir() else "")
                   for path in sorted(final.iterdir()) if path.name != "holder_distribution_current.png"]
    print("A0.3–A0.5｜将归档｜" + json.dumps(sorted(m3 | m4 | m5), ensure_ascii=False))
    print("A0.3｜整体搬运条目｜" + json.dumps(entries, ensure_ascii=False))
    if terminal:
        stage2 = case / "data/stage2"
        cycles = [int(match.group(1)) for path in stage2.iterdir()
                  if path.is_dir() and (match := re.match(r"^dist_cycle(\d+)", path.name))] if stage2.is_dir() else []
        print(f"A0.4｜周期归档目标｜data/stage2/dist_cycle{max(cycles, default=0) + 1}/")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    history = f"data/stage2/_history/{stamp}"
    if dry_run:
        if terminal:
            reseal_cli(case, "holder_distribution_scan.py", "reopen-cycle", "--reason",
                       f"reseal --from {from_layer} <UTC>", execute=False)
        return {"stage_done": "A0.5", "prevalidated_scan_paths": prevalidated}
    final = case / "charts/final"
    if final.exists():
        for entry in sorted(final.iterdir()):
            if entry.name != "holder_distribution_current.png":
                target = safe_case_file(case, f"{history}/charts_final/{entry.name}", must_exist=False)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(entry), str(target))
    moved = set()
    if terminal:
        reseal_require(case, "holder_distribution_scan.py", "reopen-cycle", "--reason",
                       f"reseal --from {from_layer} {stamp}")
        moved = {row["from"] for row in load(case, "distribution_reopen.json")["cycles"][-1]["archived"]
                 if row["mode"] == "moved"}
    if p is not None:
        if p in moved:
            target = safe_case_file(case, f"{history}/distribution_adjudications.json", must_exist=False)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(adjudication), str(target))
            _atomic_json(case, f"{history}/reseal_log.json", {
                "skill_commit": skill_commit(),
                "失效原因": "绑定的分布扫描已随周期归档；终态后由 −2 重新承接裁决"})
        else:
            proc = reseal_cli(case, "adjudication_validator.py", *validate_args)
            if proc.returncode:
                reseal_stop(2, "A0.3 预验通过后依赖失效")
    return {"stage_done": "A0.5", "prevalidated_scan_paths": prevalidated}


def reseal_preflight(case):
    import handoff_manifest
    try:
        accounting = load(case, "accounting_mode.json")
        path = accounting["observation_bundle"]["path"]
        if not isinstance(path, str) or not path.strip():
            raise ValueError("observation bundle 路径字段缺失")
        if Path(path).is_absolute() and not Path(path).resolve().is_relative_to(case):
            reseal_stop(2, "案根已迁移：observation bundle 绝对路径指向原案，reseal 须在原路径执行；"
                        "未迁移重绑的复制案无法通过发布闸")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        reseal_stop(2, f"A0.0 前置不过：accounting_mode.json observation bundle 路径缺失或不可读：{exc}")
    try:
        algorithm = load(case, "provenance_ledger.json")["input_binding"]["algorithm"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"算法文件 entity_source_trace.py 漂移：缺 input_binding.algorithm：{exc}")
        algorithm = {}
    current_sha, current_size = handoff_manifest.full_sha256_file(HERE / "entity_source_trace.py")
    if not isinstance(algorithm, dict):
        print("算法文件 entity_source_trace.py 漂移：input_binding.algorithm 必须是对象")
        algorithm = {}
    failed = algorithm.get("script_sha256") != current_sha
    print(f"A0.1 顶层 script_sha256｜记录={algorithm.get('script_sha256')}｜当前={current_sha}（{current_size} bytes）")
    files = algorithm.get("files")
    for name, target in (("entity_source_trace.py", HERE / "entity_source_trace.py"),
                         ("wave_scan.py", HERE / "wave_scan.py"),
                         ("sqd_cache_identity.py", REPO / "scripts/solana/sqd_cache_identity.py")):
        record = files.get(name) if isinstance(files, dict) else None
        _, error = handoff_manifest.check_algorithm_file(record, target)
        sha, size = handoff_manifest.full_sha256_file(target)
        shown = record if isinstance(record, dict) else {}
        print(f"A0.1 文件 {name}｜记录 sha/bytes={shown.get('sha256')}/{shown.get('bytes')}"
              f"｜当前 sha/bytes={sha}/{size}")
        if error:
            failed = True
            print(f"算法文件 {name} 漂移：{error}")
            if isinstance(record, dict) and isinstance(record.get("path"), str) and \
                    Path(record["path"]).resolve() != target.resolve():
                print("单文件校验在路径比较处返回；上述当前 sha/bytes 为另外只读计算，未由单文件校验比较内容")
    if failed:
        reseal_stop(2, "算法文件 entity_source_trace.py/wave_scan.py/sqd_cache_identity.py 漂移："
                    "须在与 freeze 记录同一 checkout 下运行，或在当前代码下重跑 provenance/freeze 链")


def freeze_readback(case):
    frozen = load(case, "entity_freeze.json")
    arguments = ["freeze", "--members", frozen["members_source"], "--entity-file", frozen["entity_file"]]
    if frozen["pending_items"]:
        arguments += ["--pending", ";".join(frozen["pending_items"])]
    if frozen.get("casebook_note") is not None:
        arguments += ["--casebook-note", frozen["casebook_note"]]
    before = freeze_revision(case)
    reseal_require(case, "handoff_manifest.py", *arguments)
    after = freeze_revision(case)
    print(f"A1 freeze revision {before} → {after}；" + ("无需新 revision" if before == after else "revision 已增加"))


def reseal_cluster_ids(scan):
    return {f"dist-{row['cluster_id']}" for row in scan.get("abnormal_clusters", [])}


def reseal_source(case, claims, *, terminal_will_reopen=False):
    ledger = reseal_ledger(case)
    wanted = {row["id"] for row in claims if row["id"].startswith("dist-")}
    initial = reseal_cluster_ids(load(case, "distribution_scan.json"))
    if ledger["rounds"] and not terminal_will_reopen:
        rel = ledger["rounds"][-1]["final_scan_path"]
        found = reseal_cluster_ids(load(case, rel))
        proc = reseal_cli(case, "holder_distribution_scan.py", "validate", "--scan", rel,
                          "--expected-stage", "final")
        print(f"分支=final；D={sorted(wanted)}；F_old={sorted(found)}；最新 final 当前有效={'是' if proc.returncode == 0 else '否'}")
        return "final", rel, wanted, found, proc.returncode == 0
    branch = "initial" if wanted == initial else "final"
    print(f"分支={branch}；D={sorted(wanted)}；I={sorted(initial)}")
    return branch, "distribution_scan.json", wanted, initial, True


def reseal_scan(case):
    n = len(reseal_ledger(case)["rounds"]) + 1
    reseal_require(case, "holder_distribution_scan.py", "--stage", "final", "--round", n)
    rel = f"dist_rounds/round_{n}/distribution_scan.json"
    return n, rel, load(case, rel)


def reseal_prepare_source(case, claims):
    branch, rel, wanted, found, valid = reseal_source(case, claims)
    ledger = reseal_ledger(case)
    if ledger["rounds"] and valid:
        if wanted != found:
            reseal_stop(3, f"待登记 dist-* claims {sorted(wanted)} 与现存非终态 final 簇 {sorted(found)} 不闭合："
                        "人工重定 claims 或改 `--from rounds` 续跑")
        return rel
    if branch == "initial":
        return rel
    n, rel, scan = reseal_scan(case)
    reseal_require(case, "holder_distribution_scan.py", "record-round", "--scan", rel)
    if reseal_ledger(case).get("terminal") is not None:
        reseal_stop(3, "分布形态已变，dist-* claims 失去来源，须人工重定 claims；台账已终态，重封前需再 reopen-cycle")
    found = reseal_cluster_ids(scan)
    if found != wanted:
        reseal_stop(3, f"final scan 异常簇 {sorted(found)} 与待登记 dist-* claims {sorted(wanted)} 不闭合："
                    f"人工重定 claims（--claims-file）后重跑 reseal；本轮 {n} 已记入台账为非终态锚")
    return rel


def reseal_mapped_path(case, rel, purpose):
    if (case / rel).exists():
        return safe_case_file(case, rel).relative_to(case).as_posix()
    if (case / "distribution_reopen.json").exists():
        for row in load(case, "distribution_reopen.json")["cycles"][-1]["archived"]:
            if row["mode"] == "moved" and row["from"] == rel:
                if file_sha(case, row["to"]) == row["sha256"]:
                    print(f"{purpose} 映射 {rel} → {row['to']}")
                    return row["to"]
                break
    reseal_stop(3, f"{purpose} 缺文件或归档 sha 不符：{rel}；要求显式 --{purpose}")


def reseal_register_needed(case, claims, claims_file):
    old = load(case, "a4_claims.json")["claims"]
    archived = set()
    if (case / "distribution_reopen.json").exists():
        archived = {row["from"] for row in load(case, "distribution_reopen.json")["cycles"][-1]["archived"]
                    if row["mode"] == "moved"}
    for row in old:
        for rel in row["files"]:
            if not (case / rel).exists() and rel in archived and claims_file is None:
                reseal_stop(3, f"claim {row['id']} 引用已归档文件 {rel}＝claims 变更："
                            "用 --claims-file 重定引用后重跑 reseal；仅传 --seal-files 无效")
    try:
        same = canon(a4_gate.validate_claim_rows(case, claims)) == canon(a4_gate.validate_claim_rows(case, old))
    except ValueError:
        same = False
    try:
        bound = file_sha(case, "a4_claims.json") == load(case, "adversarial_review.json")["claim_registry"]["sha256"]
    except (OSError, ValueError, KeyError, TypeError):
        bound = False
    return not (same and bound)


def reseal_verdicts(case, path, seal, claims):
    if path is None:
        return None
    rel = path.relative_to(case).as_posix()
    rows = load(case, rel)
    if not isinstance(rows, list):
        raise ValueError("verdicts 必须为数组")
    registered = {row["id"] for row in claims}
    old = {row["id"]: row["verdict"] for row in seal["claims"]}
    for row in rows:
        if row["id"] not in registered:
            reseal_stop(2, "verdicts 含未登记 id：" + row["id"])
        if row["id"] in old and row["verdict"].strip().upper() != old[row["id"]]:
            reseal_stop(3, "A4 verdict 与上版有差异＝判断变更：请人工按 A4 流程 `a4_gate finalize` 封新 revision、"
                        "按 `downstream-check` 重跑受影响复核，然后 `reseal --from rounds`")
    return path


def reseal_copy_verdicts(case, source, target):
    """Persist the exact verdict bytes; replacement is one-file atomic."""
    destination = safe_case_file(case, target, must_exist=False)
    data = safe_case_file(case, source).read_bytes()
    fd, temporary = tempfile.mkstemp(prefix=".reseal-verdicts-", dir=destination.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return destination


def reseal_extra_files(case, seal, claims, source, explicit):
    if explicit is not None:
        return explicit
    automatic = set(a4_gate.MANDATORY_SEAL_FILES) | {source}
    automatic.update(rel for row in claims for rel in row["files"])
    return ",".join(reseal_mapped_path(case, row["path"], "seal-files")
                    for row in seal["sealed_files"] if row["path"] not in automatic)


def reseal_a4(case, args, claims, claims_file, verdicts_file, source):
    seal = load(case, "a4_seal.json")
    if reseal_register_needed(case, claims, claims_file):
        if claims_file is None:
            _atomic_json(case, "reseal_claims.json", claims)
            claims_file = case / "reseal_claims.json"
        reseal_require(case, "a4_gate.py", "register", "--claims-file", claims_file)
        reseal_stop(3, "registry 已变：按 runner 记录的实际路数重跑受影响复核 → adversarial_review_runner finalize → "
                    "shared_release_receipt；完成后再跑 reseal --from a4")
    reseal_verdicts(case, verdicts_file, seal, claims)
    if verdicts_file is None:
        old = reseal_mapped_path(case, seal["verdicts"]["path"], "verdicts-file")
        verdicts_file = reseal_copy_verdicts(case, old, f"verdicts_rev{seal['revision'] + 1}.json")
    extras = reseal_extra_files(case, seal, claims, source, args.seal_files)
    reseal_require(case, "a4_gate.py", "finalize", "--verdicts-file", verdicts_file,
                   "--seal-files", extras, "--workflow-type", "new-analysis")
    pending = (case / "distribution_rounds.json").exists() and reseal_ledger(case)["terminal"] is None
    stops = []
    for row in a4_gate.downstream_stale(case):
        if row["status"] != "stale":
            continue
        if pending and row["item"] in {"rounds.a4_seal_sha", "rounds.entity_freeze_revision"}:
            print(f"pending_a3：{row['item']}，延期到 A3 终态验证")
        else:
            stops.append(row)
    if stops:
        reseal_stop(3, "下游过期：" + json.dumps(stops, ensure_ascii=False))


def reseal_rounds(case, old_waived):
    n, rel, scan = reseal_scan(case)
    new_clusters = reseal_cluster_ids(scan) - {row["id"] for row in load(case, "a4_seal.json")["claims"]}
    explanation, failure = None, ""
    if scan["verdict"] == "ABNORMAL_SHAPE" and not new_clusters and not old_waived:
        output = f"dist_rounds/round_{n}/explanation.json"
        proc = reseal_cli(case, "distribution_explanation_check.py", "--scan", rel,
                          "--a4-seal", "a4_seal.json", "--out", output)
        if proc.returncode:
            failure = "解释检查失败：" + proc.stdout + proc.stderr
        else:
            explanation = output
    arguments = ["record-round", "--scan", rel]
    if explanation:
        arguments += ["--explanation", explanation]
    reseal_require(case, "holder_distribution_scan.py", *arguments)
    if old_waived:
        reseal_stop(3, "waiver 须 ≥ 第 2 轮且重新绑定当前 scan/seal/台账：补证据/复核 → 需要则 finalize → "
                    f"--stage final --round {n + 1} → 人工 waiver record")
    if new_clusters:
        reseal_stop(3, "新簇回流 A4：" + ", ".join(sorted(new_clusters)))
    if reseal_ledger(case)["terminal"] is None:
        reseal_stop(3, failure + "\n补证据/复核 → finalize → reseal --from rounds（轮号自动 n+1，再次尝试解释）")


def reseal(case, args):
    try:
        reseal_preflight(case)
        claims_file = Path(args.claims_file).resolve() if args.claims_file else None
        verdicts_file = Path(args.verdicts_file).resolve() if args.verdicts_file else None
        if verdicts_file is not None:
            safe_case_file(case, verdicts_file.relative_to(case).as_posix())
        claims = json.loads(claims_file.read_bytes()) if claims_file else load(case, "a4_claims.json")["claims"]
        if not isinstance(claims, list):
            raise ValueError("claims-file 必须为数组")
        seal = load(case, "a4_seal.json")
        ledger = reseal_ledger(case)
        terminal = ledger.get("terminal") is not None
        old_waived = terminal and ledger["terminal"].get("status") == "WAIVED"
        print("层｜动作｜将失效下游件")
        if args.from_layer in {"freeze", "a4"}:
            print(f"{args.from_layer}｜重封｜final scan（各轮）、rounds 全部行、a4（freeze revision 变时）、"
                  "adversarial_review/shared_release_receipt（按 registry sha，不按 seal revision）、a5 seal、工单 bindings")
        else:
            print("rounds｜重开/续轮｜rounds 行、终态图、a5 seal、工单 bindings.rounds/终态图")
        m3, m4 = reseal_move_sets(case, ledger)
        frozen = load(case, "entity_freeze.json")
        if (case / "distribution_adjudications.json").exists() and not terminal and args.from_layer != "rounds":
            print("恢复步骤：人工归档旧裁决并移出默认案根路径 → 检查它是否被 seal/freeze 封入 → 续跑对应层；"
                  "重新承接裁决须从绑定新 final 的 scan 重新 distribution-template；freeze 再变仍会使来源 scan 过期")
        reseal_archive(case, m3, m4, terminal, frozen.get("entity_file"),
                       sealed_paths=reseal_sealed_paths(case, seal), from_layer=args.from_layer, dry_run=args.dry_run)
        if args.from_layer != "rounds":
            branch, source, wanted, found, valid = reseal_source(case, claims, terminal_will_reopen=args.dry_run and terminal)
            print("旧 seal 来源（仅参考）：" + json.dumps(seal.get("distribution_claim_source"), ensure_ascii=False))
        if args.dry_run:
            next_round = 1 if terminal else len(ledger["rounds"]) + 1
            if args.from_layer != "rounds":
                needed = reseal_register_needed(case, claims, claims_file)
                print(f"register={'须执行并停点' if needed else '跳过'}")
                reseal_verdicts(case, verdicts_file, seal, claims)
                prebuild = branch == "final" and (terminal or not ledger["rounds"] or not valid)
                if prebuild:
                    prebuild_round = next_round
                    source = f"dist_rounds/round_{next_round}/distribution_scan.json"
                    next_round += 1
                elif branch == "final" and wanted != found:
                    print(f"A1.5 当前停点预判：待登记 dist-* claims {sorted(wanted)} 与现存非终态 final 簇 {sorted(found)} 不闭合")
                extras = reseal_extra_files(case, seal, claims, source, args.seal_files)
                if verdicts_file is None:
                    old_verdicts = reseal_mapped_path(case, seal["verdicts"]["path"], "verdicts-file")
                    verdicts_file = case / f"verdicts_rev{seal['revision'] + 1}.json"
                    print(f"A2.2｜持久复制｜{old_verdicts} → {verdicts_file.name}")
                print("A1 后须重验；dry-run 不运行 freeze 试探")
                if args.from_layer == "freeze":
                    arguments = ["freeze", "--members", frozen.get("members_source"), "--entity-file", frozen.get("entity_file")]
                    if frozen.get("pending_items"):
                        arguments += ["--pending", ";".join(frozen["pending_items"])]
                    if frozen.get("casebook_note") is not None:
                        arguments += ["--casebook-note", frozen["casebook_note"]]
                    reseal_cli(case, "handoff_manifest.py", *arguments, execute=False)
                if prebuild:
                    reseal_cli(case, "holder_distribution_scan.py", "--stage", "final", "--round", prebuild_round, execute=False)
                    reseal_cli(case, "holder_distribution_scan.py", "record-round", "--scan", source, execute=False)
                if needed:
                    reseal_cli(case, "a4_gate.py", "register", "--claims-file", claims_file or case / "reseal_claims.json", execute=False)
                reseal_cli(case, "a4_gate.py", "finalize", "--verdicts-file", verdicts_file,
                           "--seal-files", extras, "--workflow-type", "new-analysis", execute=False)
            reseal_cli(case, "holder_distribution_scan.py", "--stage", "final", "--round",
                       next_round, execute=False)
            reseal_cli(case, "holder_distribution_scan.py", "record-round", "--scan", "<本轮 final scan>", execute=False)
            for command in ("fill-workorder", "check"):
                reseal_cli(case, "stage2_closeout.py", command, "--report", args.report, execute=False)
            return 0
        if args.from_layer == "freeze":
            freeze_readback(case)
        if args.from_layer != "rounds":
            source = reseal_prepare_source(case, claims)
            reseal_a4(case, args, claims, claims_file, verdicts_file, source)
        reseal_rounds(case, old_waived)
        reseal_require(case, "stage2_closeout.py", "fill-workorder", "--report", args.report)
        return reseal_cli(case, "stage2_closeout.py", "check", "--report", args.report).returncode
    except (ValueError, OSError, KeyError, TypeError) as exc:
        reseal_stop(2, f"reseal 前置不过：{exc}")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or (argv[0].startswith("--") and argv[0] != "--help"):
        argv.insert(0, "check")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    for name in ("check", "fill-workorder", "amend", "reseal"):
        parser = sub.add_parser(name, description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
        parser.add_argument("--case-dir", required=True, type=Path)
        parser.add_argument("--report", required=True, help="案根相对路径")
        if name not in {"amend", "reseal"}:
            parser.add_argument("--workorder", default=WORKORDER, help="案根相对路径")
        if name == "check":
            parser.add_argument("--receipt-only", action="store_true")
            parser.add_argument("--json-out", help="案内结果文件相对路径")
        if name == "amend":
            parser.add_argument("--previous", help="修正前报告副本，案根相对路径；以原始字节重放")
        if name == "reseal":
            parser.add_argument("--from", dest="from_layer", required=True, choices=("freeze", "a4", "rounds"))
            parser.add_argument("--claims-file")
            parser.add_argument("--verdicts-file")
            parser.add_argument("--seal-files")
            parser.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    case = a.case_dir.resolve()
    try:
        if not case.is_dir():
            raise ValueError(f"案目录不存在: {case}")
        if a.command == "reseal":
            return reseal(case, a)
        if a.command == "fill-workorder":
            fill_workorder(case, a.report, a.workorder)
            return 0
        if a.command == "amend":
            try:
                errors, _updated = amend(case, a.report, a.previous)
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
                errors = [f"amend 前置失败: {exc}"]
            for error in errors:
                print("BLOCK: " + error)
            if not errors:
                print(PASS_MESSAGE)
            return 2 if errors else 0
        if a.receipt_only:
            errors = receipt_only_errors(case, a.report, a.workorder)
            result = {"verdict": "BLOCK" if errors else "PASS", "errors": errors}
            for error in errors:
                print(error)
        else:
            checks = run_checks(case, a.report, a.workorder)
            result = receipt_document(case, a.report, a.workorder, checks)
            _atomic_json(case, RECEIPT, result)
            for check in checks:
                print(f"{check['status']}: {check['name']}")
                for detail in check["detail"]:
                    print("  " + str(detail))
        if a.json_out:
            _atomic_json(case, a.json_out, result)
        if result["verdict"] == "PASS":
            print(PASS_MESSAGE)
            return 0
        print("BLOCK: −2 收口未通过")
        return 2
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
