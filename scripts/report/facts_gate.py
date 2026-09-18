#!/usr/bin/env python3
"""报告编译化事实源（3.18.0，@CX 融合方案第一档 Top1 的第 1+2 步）。

解决的架构病：数字/地址手抄进报告已第四犯——纪律拦不住，只有"架构不允许手抄"拦得住。
报告 md 里写宏引用，本模块渲染+语义 gate：正文数字、附录 B、analysis-state.json 三处
永远同源；改一处数据其余处必然跟着变，对不上编译直接失败（fail-closed）。

facts.json schema（每案一份，阶段 3 结束时由 build 子命令从三账生成，禁手抄；数值一律**原始整数字符串**）：
{
  "token": {"symbol": "QUQ", "decimals": 18, "total_supply_raw": "1000...0"},
  "entities": {
    "e_big1": {"label": "大庄#1(bot体系)",
               "addresses": ["0x完整地址", ...],
               "current_raw": "278400...", "peak_raw": "687000...",
               "peak_date": "2026-05-01", "role_notes": {"0x地址": "角色备注(可选)"},
               "merge_evidence_earliest": "2026-05-03",   # 多地址实体必填(3.19)：
               "merge_evidence_note": "gas同源+同分钟批量"  # 实体合并证据的最早可见时间
  },
  "metrics": {
    "m_alpha": {"num_raw": "376...", "den": "total_supply", "desc": "币安Alpha托管"},
    "m_price_x": {"value": "9.4", "unit": "倍", "desc": "峰值涨幅"}   # 自由值型
  }
}

实体主键（3.19 起）：entities 的字典键（如 e_big1）就是该实体的稳定 entity_id——
analysis-state.json 的 whale_groups[].entity_id 必须写同一个值。G1 对账**优先按
entity_id 匹配**，label 只是展示文案（改措辞不再断链路）；旧 state 无 entity_id 时
回退 label 匹配（向后兼容）。

时间因果轻量口径（3.19，A1）：merge_evidence_earliest = 该实体各地址被归并为同一
实体的证据**最早出现时间**。报告叙述早期共同行为时必须用"以最终归并口径回看"限定
或标注该时间（宏 {{e_x.merged_since}}）；禁写"当时已可确认同一实体"——后期归集/
后期 gas 同源不能倒灌证明早期已可见（措辞细则见 playbook-evidence-wording.md）。

报告 md 宏语法（渲染后无残留 {{...}}，否则 gate 拒绝——宏名打错不许静默漏渲染）：
  {{e_big1.label}}            → 大庄#1(bot体系)
  {{e_big1.share}}            → 27.84%（current_raw/total_supply）
  {{e_big1.peak_share}}       → 68.70%
  {{e_big1.amount}}           → 2.78亿枚
  {{e_big1.amount_share}}     → 2.78亿枚【总量27.84%】（最常用组合，报告纪律格式）
  {{e_big1.naddr}}            → 215（成员地址数）
  {{e_big1.merged_since}}     → 2026-05-03（merge_evidence_earliest，A1 时间因果）
  {{m:m_alpha}}               → 37.60%（num/den 型）或 value+unit（自由值型）
  {{appendix_b}}              → 附录 B 标签↔地址对照表整块（md 表格，与 entities 同源）

语义 gate（--state 给了 analysis-state.json 时全部启用）：
  G1 实体成员集合：facts.entities[*].addresses 与 state.whale_groups 逐组相等
     （匹配键优先 entity_id==facts 实体键，旧 state 无 entity_id 回退 label）
  G2 供给上界：Σ entities.current_raw ≤ total_supply_raw
  G3 内部一致：current_raw ≤ peak_raw（每实体）
  G4 渲染完备：渲染后正文无残留 {{...}}
  G5 手写数字检测：正文所有 NN.NN% 中不来自宏渲染的列成清单（NOTE 级人工过目；
     百分比一律该走宏——这是新写作纪律，见 report-template.md）
  G6 合并时点提示（NOTE 级）：多地址实体缺 merge_evidence_earliest 时提醒补
  G7 血缘提示（NOTE 级）：state 缺 provenance（schema_version/skill_commit/
     data_sources 薄版血缘，3.19 起新案必带）时提醒补

用法（库 + CLI 双形态；build_html.py --facts 参数内部调用）：
  python3 facts_gate.py --facts facts.json --state analysis-state.json   # 纯校验
  python3 facts_gate.py build [--case-dir .] [--source state_source.json] [--out facts.json] [--exploration]
      # 从三账＋identity_gate＋provenance_ledger＋state_source.facts_inputs 生成 facts.json（7.2.0，R07）
state_source.facts_inputs schema：
  symbol: str（必填）；decimals: int≥0（必填）
  entity_labels: {eid: label}（必填、非空、覆盖全部实体）
  peak_overrides: {eid: {peak_raw, peak_date, evidence: {path, sha256}}}，证据 JSON 须为 {entity_id: {peak_raw, peak_date}} 与申报相等
      （可选，优先于 provenance 锚点，证据须为案根常规文件）
  merge_evidence: {eid: {earliest, note}}（可选）
  role_notes: {eid: {addr: note}}（可选）
  metrics: {mid: {...}}（可选；对象且每项为对象）；dual_basis: {}（可选；对象）
  禁止 provenance/facts_binding 键；绑定块只能由 build 生成。
"""
import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path

# 字符类含连字符：实体键约定（3.19 起 entities 字典键=stable entity_id）允许
# ENT-PROJ 型命名——缺连字符时这类宏既不渲染也不被 G4 检出（死宏静默漏进正文，
# SPORTFUN 2026-08-25 实踩），扩集是收紧方向（原漏检死宏开始被渲染/检出）。
MACRO_RE = re.compile(r"\{\{([A-Za-z0-9_.:-]+)\}\}")
PCT_RE = re.compile(r"\d+(?:\.\d+)?%")


def _int(s):
    return int(str(s))


def fmt_pct(num, den):
    if den == 0:
        return "0.00%"
    return f"{num / den * 100:.2f}%"


def fmt_amount(raw, decimals):
    """原始整数 → 中文单位枚数（亿/万两档，保留 2 位）。"""
    v = _int(raw) / 10 ** decimals
    if v >= 1e8:
        return f"{v / 1e8:.2f}亿枚"
    if v >= 1e4:
        return f"{v / 1e4:.2f}万枚"
    return f"{v:,.2f}枚"


class Facts:
    def __init__(self, facts_dict):
        self.d = facts_dict
        self.token = facts_dict.get("token") or {}
        self.decimals = int(self.token.get("decimals", 18))
        self.total_raw = _int(self.token.get("total_supply_raw", "0"))
        if self.total_raw <= 0:
            # 键名必须 total_supply_raw（raw 整数）；human 版键名会让分母为 0、全部 share 宏静默算出 0.00%（SPX6900 2026-07-25 实踩）
            raise ValueError("token.total_supply_raw 缺失或为 0——检查键名（不认 total_supply 等 human 版键）与取值（raw 整数字符串）")
        self.entities = facts_dict.get("entities") or {}
        self.metrics = facts_dict.get("metrics") or {}
        self.rendered_values = set()   # 渲染产出的字符串（G5 手写数字差集用）

    # ---- 宏求值 ----
    def _entity_value(self, ent, field):
        cur = _int(ent.get("current_raw", "0"))
        peak = _int(ent.get("peak_raw", ent.get("current_raw", "0")))
        if field == "label":
            return ent.get("label", "?")
        if field == "share":
            return fmt_pct(cur, self.total_raw)
        if field == "peak_share":
            return fmt_pct(peak, self.total_raw)
        if field == "amount":
            return fmt_amount(cur, self.decimals)
        if field == "amount_share":
            return f"{fmt_amount(cur, self.decimals)}【总量{fmt_pct(cur, self.total_raw)}】"
        if field == "peak_amount_share":
            return f"{fmt_amount(peak, self.decimals)}【总量{fmt_pct(peak, self.total_raw)}】"
        if field == "naddr":
            return str(len(ent.get("addresses") or []))
        if field == "peak_date":
            return str(ent.get("peak_date", "?"))
        if field == "merged_since":
            v = ent.get("merge_evidence_earliest")
            if not v:
                raise KeyError("宏 merged_since 但实体缺 merge_evidence_earliest 字段")
            return str(v)
        raise KeyError(f"实体宏字段不认识: {field}")

    def _metric_value(self, mid):
        m = self.metrics.get(mid)
        if m is None:
            raise KeyError(f"metrics 缺 {mid}")
        if "num_raw" in m:
            den = (self.total_raw if m.get("den", "total_supply") == "total_supply"
                   else _int(m["den"]))
            return fmt_pct(_int(m["num_raw"]), den)
        return f"{m.get('value', '?')}{m.get('unit', '')}"

    def appendix_b_table(self):
        """附录 B 标签↔地址对照表（与 entities 同源生成——手抄地址的架构级消灭）。"""
        lines = ["| 实体/标签 | 地址 | 备注 |", "|---|---|---|"]
        for eid in self.entities:
            ent = self.entities[eid]
            notes = ent.get("role_notes") or {}
            for i, a in enumerate(ent.get("addresses") or []):
                label = ent.get("label", eid) if i == 0 else "〃"
                lines.append(f"| {label} | `{a}` | {notes.get(a, '')} |")
        return "\n".join(lines)

    def eval_macro(self, expr):
        if expr == "appendix_b":
            return self.appendix_b_table()
        if expr.startswith("m:"):
            v = self._metric_value(expr[2:])
        else:
            eid, _, field = expr.partition(".")
            if eid not in self.entities:
                raise KeyError(f"entities 缺 {eid}（宏 {{{{{expr}}}}}）")
            v = self._entity_value(self.entities[eid], field or "label")
        self.rendered_values.add(v)
        # 组合宏里的百分比子串也计入已渲染集合（G5 白名单）
        for p in PCT_RE.findall(v):
            self.rendered_values.add(p)
        return v

    def render(self, md_text):
        """渲染全部宏；宏求值错误直接抛（编译失败——宏名打错不许静默）。"""
        return MACRO_RE.sub(lambda m: self.eval_macro(m.group(1)), md_text)


# ---- 语义 gate ----

def gate_check(facts, state=None, rendered_md=None):
    """返回 (errors, notes)。errors 非空=编译失败。"""
    errors, notes = [], []
    # G3 内部一致
    for eid, ent in facts.entities.items():
        cur = _int(ent.get("current_raw", "0"))
        peak = _int(ent.get("peak_raw", ent.get("current_raw", "0")))
        if cur > peak:
            errors.append(f"G3 {eid} current_raw > peak_raw（{cur} > {peak}）")
        if facts.total_raw and peak > facts.total_raw:
            errors.append(f"G2 {eid} peak_raw {peak} 超过总供应 {facts.total_raw}")
    # G2 供给上界
    total_cur = sum(_int(e.get("current_raw", "0")) for e in facts.entities.values())
    if facts.total_raw and total_cur > facts.total_raw:
        errors.append(f"G2 Σ实体当前持仓 {total_cur} 超过总供应 {facts.total_raw}")
    # G1 与 state 成员集合对账（EVM 小写归一；SOL base58 大小写敏感不动）
    def _norm(x):
        v = x.get("address") if isinstance(x, dict) else x
        v = (v or "").strip()
        return v.lower() if v.startswith("0x") else v

    if state is not None:
        by_id, by_label = {}, {}
        for g in state.get("whale_groups") or []:
            members = {_norm(a) for a in (g.get("addresses") or [])}
            gid = (g.get("entity_id") or "").strip()
            if gid:
                by_id[gid] = members
            by_label[(g.get("label") or "").strip()] = members
        for eid, ent in facts.entities.items():
            lbl = (ent.get("label") or "").strip()
            # 3.19：主键优先 entity_id（facts 实体键==state.entity_id），label 只是展示；
            # 旧 state 无 entity_id 时回退 label 匹配（向后兼容）
            if eid in by_id:
                sa, keydesc = by_id[eid], f"entity_id={eid}"
            elif lbl in by_label:
                sa, keydesc = by_label[lbl], f"label「{lbl}」"
            else:
                errors.append(f"G1 state.whale_groups 缺组（facts {eid}「{lbl}」——"
                              f"按 entity_id 与 label 均未匹配）")
                continue
            fa = {_norm(a) for a in ent.get("addresses") or []}
            if fa != sa:
                miss, extra = sorted(sa - fa)[:3], sorted(fa - sa)[:3]
                errors.append(f"G1 {keydesc} 成员集合不一致：state 独有 {len(sa-fa)} 个"
                              f"（样例 {miss}），facts 独有 {len(fa-sa)} 个（样例 {extra}）")
        # G7 薄版血缘提示（3.19）：新案 state 顶层应带 provenance
        prov = state.get("provenance") or {}
        missing = [k for k in ("schema_version", "skill_commit", "data_sources")
                   if not prov.get(k)]
        if missing:
            notes.append(f"G7 state.provenance 缺 {missing}（薄版血缘，3.19 起新案必带："
                         "schema_version/skill_commit/data_sources）")
    # G6 合并时点提示（3.19，A1 时间因果）：多地址实体应记录归并证据最早时间
    no_merge_ts = [eid for eid, ent in facts.entities.items()
                   if len(ent.get("addresses") or []) >= 2
                   and not ent.get("merge_evidence_earliest")]
    if no_merge_ts:
        notes.append(f"G6 多地址实体缺 merge_evidence_earliest: {no_merge_ts[:8]}"
                     "（A1 时间因果：记录归并证据最早时间，报告叙述早期共同行为须"
                     "标注归并口径）")
    # G4 渲染完备 + G5 手写数字
    if rendered_md is not None:
        left = MACRO_RE.findall(rendered_md)
        if left:
            errors.append(f"G4 渲染后残留宏 {left[:5]}（宏名打错或 facts 缺键）")
        handwritten = [p for p in set(PCT_RE.findall(rendered_md))
                       if p not in facts.rendered_values]
        if handwritten:
            notes.append("G5 疑似手写百分比（新纪律：结论性百分比一律走宏；确认为"
                         "非结论数字——如价格涨跌幅/费率——可交付）: "
                         + " ".join(sorted(handwritten)[:15]))
    return errors, notes


FACTS_PROVENANCE_SCHEMA = "facts-provenance/v1"
STATE_SOURCE_SCHEMA = "analysis-state-source/v1"
FACTS_INPUTS_KEY = "facts_inputs"
FACTS_LEDGER_INPUTS = ("membership_ledger.json", "position_ledger.json",
                       "economic_control_ledger.json", "identity_gate.json")


def _sha256_path(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _norm_addr(value):
    v = str(value or "").strip()
    return v.lower() if v.lower().startswith("0x") else v


def _case_file(case_dir, rel, label):
    """案内常规文件：basename 相对案根、非符号链接、必须在场；否则 ValueError。"""
    name = Path(str(rel or "")).name
    if not name or name != str(rel):
        raise ValueError(f"{label} 路径必须是案根内 basename: {rel!r}")
    p = Path(case_dir) / name
    if p.is_symlink() or not p.is_file():
        raise ValueError(f"{label} 不在案根或是符号链接: {name}")
    return p


def _reject_constant(value):
    raise ValueError(f"JSON 含非有限常量 {value}（NaN/Infinity 不允许）")


def _finite_float(text):
    v = float(text)
    if v != v or v in (float("inf"), float("-inf")):
        raise ValueError(f"JSON 浮点非有限: {text}")
    return v


def _load_case_json(case_dir, rel, label):
    with open(_case_file(case_dir, rel, label), encoding="utf-8") as fh:
        try:
            return json.load(fh, parse_constant=_reject_constant, parse_float=_finite_float)
        except ValueError as exc:
            raise ValueError(f"{label} 解析失败: {exc}") from exc


def _raw_str(value, label):
    n = _int(value)
    if n < 0:
        raise ValueError(f"{label} 不得为负: {value!r}")
    return str(n)


def derive_facts(case_dir, *, exploration=False):
    """R07（7.2.0）：从三账＋identity_gate＋（可选）provenance_ledger＋state_source.facts_inputs
    重算 facts.json。纯函数：只读案内文件，不写盘，不带时间戳；build 与发布闸/收口共用，
    闸用它重算后与落盘 facts 逐字段比对。任何缺件/不闭合/证据不符一律 ValueError（fail-closed）。"""
    case_dir = Path(case_dir)
    data = {n: _load_case_json(case_dir, n, n) for n in FACTS_LEDGER_INPUTS[:3]}
    for name, obj in data.items():
        rows = obj.get("entries", obj.get("entities")) if isinstance(obj, dict) else None
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"{name} 缺 entries/entities 或为空——空账不得生成 facts")
    import audit_release_gate  # 同目录；三账闭合复用发布闸同一实现
    errs = []
    audit_release_gate.check_three_ledgers(case_dir, data, errs, chain=None)
    if errs:
        raise ValueError("三账不闭合，拒绝生成 facts: " + "; ".join(errs[:3]))
    identity = _load_case_json(case_dir, "identity_gate.json", "identity_gate.json")
    total_raw = _raw_str(identity.get("total_supply_raw"), "identity_gate.total_supply_raw")
    if int(total_raw) <= 0:
        raise ValueError("identity_gate.total_supply_raw 必须为正")
    ledger_path = case_dir / "provenance_ledger.json"
    ledger = None
    if ledger_path.is_file() and not ledger_path.is_symlink():
        ledger = _load_case_json(case_dir, "provenance_ledger.json", "provenance_ledger.json")
        if not exploration and ledger.get("exploration") is True:
            raise ValueError("provenance_ledger 为探索产物，formal build 拒绝")
        lt = ledger.get("total_supply_raw")
        if lt is not None and _raw_str(lt, "provenance_ledger.total_supply_raw") != total_raw:
            raise ValueError(f"total_supply_raw 冲突: identity_gate {total_raw} != provenance_ledger {lt}")
    source = _load_case_json(case_dir, "state_source.json", "state_source.json")
    if source.get("schema") != STATE_SOURCE_SCHEMA:
        raise ValueError(f"state_source.schema 必须是 {STATE_SOURCE_SCHEMA}")
    fi = source.get(FACTS_INPUTS_KEY)
    if not isinstance(fi, dict):
        raise ValueError(f"state_source 缺 {FACTS_INPUTS_KEY} 对象")
    if "provenance" in fi or "facts_binding" in fi:
        raise ValueError("state_source.facts_inputs 不得预置 provenance/facts_binding——绑定块只能由 build 生成")
    symbol = fi.get("symbol")
    decimals = fi.get("decimals")
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("facts_inputs.symbol 必须是非空字符串")
    symbol = symbol.strip()
    if isinstance(decimals, bool) or not isinstance(decimals, int) or decimals < 0:
        raise ValueError("facts_inputs.decimals 必须是 ≥0 的整数")
    labels = fi.get("entity_labels")
    if not isinstance(labels, dict) or not labels:
        raise ValueError("facts_inputs.entity_labels 缺失或为空")
    overrides = fi.get("peak_overrides") or {}
    merges = fi.get("merge_evidence") or {}
    roles = fi.get("role_notes") or {}
    if not all(isinstance(x, dict) for x in (overrides, merges, roles)):
        raise ValueError("facts_inputs.peak_overrides/merge_evidence/role_notes 须为对象")
    metrics = fi.get("metrics", {})
    if not isinstance(metrics, dict) or any(not isinstance(v, dict) for v in metrics.values()):
        raise ValueError("facts_inputs.metrics 须为对象且每项为对象")
    dual_basis = fi.get("dual_basis")
    if "dual_basis" in fi and not isinstance(dual_basis, dict):
        raise ValueError("facts_inputs.dual_basis 须为对象")

    members = data["membership_ledger.json"]
    members = members.get("entries", members.get("entities", []))
    strict_by_entity = {}
    for row in members:
        if str(row.get("membership", "")).strip() == "strict":
            strict_by_entity.setdefault(str(row.get("entity_id", "")).strip(), set()).add(
                _norm_addr(row.get("address")))
    ledger_entities = {}
    if ledger is not None:
        for item in ledger.get("entities") or []:
            if isinstance(item, dict) and item.get("entity_id"):
                ledger_entities[str(item["entity_id"])] = item

    econ = data["economic_control_ledger.json"]
    econ = econ.get("entries", econ.get("entities", []))
    entities, used_overrides = {}, {}
    for row in econ:
        eid = str(row.get("entity_id", "")).strip()
        label = str(labels.get(eid) or "").strip()
        if not label:
            raise ValueError(f"facts_inputs.entity_labels 缺实体 {eid} 的 label")
        current = _raw_str(row.get("confirmed_economic_control_raw"),
                           f"economic {eid}.confirmed_economic_control_raw")
        ent = {"label": label, "addresses": sorted(strict_by_entity.get(eid, set())),
               "current_raw": current}
        ov = overrides.get(eid)
        if ov is not None:
            if not isinstance(ov, dict):
                raise ValueError(f"peak_overrides.{eid} 须为对象")
            ev = ov.get("evidence")
            if not isinstance(ev, dict) or not ev.get("path") or not ev.get("sha256"):
                raise ValueError(f"peak_overrides.{eid} 缺 evidence.path/sha256")
            ev_path = _case_file(case_dir, ev["path"], f"peak_overrides.{eid}.evidence")
            if _sha256_path(ev_path) != str(ev["sha256"]).lower():
                raise ValueError(f"peak_overrides.{eid}.evidence sha256 与案内实物不一致")
            peak = _raw_str(ov.get("peak_raw"), f"peak_overrides.{eid}.peak_raw")
            peak_date = str(ov.get("peak_date") or "").strip()
            if not peak_date:
                raise ValueError(f"peak_overrides.{eid} 缺 peak_date")
            # F05（7.2.1）：证据内容须可解释——JSON 对象，以 entity_id 为键，给出与申报相等的
            # peak_raw/peak_date；hash 只证明文件没变，不证明值来自文件。
            ev_obj = _load_case_json(case_dir, ev["path"], f"peak_overrides.{eid}.evidence")
            ev_ent = ev_obj.get(eid) if isinstance(ev_obj, dict) else None
            if (not isinstance(ev_ent, dict)
                    or _raw_str(ev_ent.get("peak_raw"), f"evidence[{eid}].peak_raw") != peak
                    or str(ev_ent.get("peak_date") or "").strip() != peak_date):
                raise ValueError(f"peak_overrides.{eid} 证据内容与申报 peak_raw/peak_date 不一致"
                                 f"（证据须为 {{\"{eid}\": {{\"peak_raw\", \"peak_date\"}}}}）")
            used_overrides[eid] = {"peak_raw": peak, "peak_date": peak_date,
                                   "evidence": {"path": ev_path.name,
                                                "sha256": str(ev["sha256"]).lower()}}
        elif eid in ledger_entities:
            anchor = ((ledger_entities[eid].get("anchors") or {}).get("peak") or {})
            peak = _raw_str(anchor.get("stock_raw"), f"provenance_ledger {eid}.anchors.peak.stock_raw")
            peak_date = str(anchor.get("date") or "").strip()
            if not peak_date:
                raise ValueError(f"provenance_ledger {eid}.anchors.peak 缺 date")
        elif exploration:
            peak, peak_date = current, None
        else:
            raise ValueError(f"实体 {eid} 无峰值来源（provenance_ledger 锚点或 peak_overrides）——formal build 拒绝")
        if peak_date is not None:
            try:
                peak_day = _dt.date.fromisoformat(peak_date)
            except ValueError as exc:
                raise ValueError(f"实体 {eid} peak_date {peak_date!r} 非 YYYY-MM-DD: {exc}") from exc
            if peak_day.isoformat() != peak_date:
                raise ValueError(f"实体 {eid} peak_date {peak_date!r} 非 YYYY-MM-DD（fromisoformat 接受 20260102/周格式，此处严格）")
            cur_date = str((((ledger_entities.get(eid) or {}).get("anchors") or {})
                            .get("current") or {}).get("date") or "").strip()
            if cur_date and peak_day > _dt.date.fromisoformat(cur_date):
                raise ValueError(f"实体 {eid} peak_date {peak_date} 晚于 provenance 当前锚点日 {cur_date}")
        if int(peak) < int(current):
            raise ValueError(f"实体 {eid} peak_raw {peak} < current_raw {current}")
        ent["peak_raw"] = peak
        ent["peak_date"] = peak_date
        m = merges.get(eid)
        if isinstance(m, dict) and m.get("earliest"):
            ent["merge_evidence_earliest"] = str(m["earliest"])
            if m.get("note"):
                ent["merge_evidence_note"] = str(m["note"])
        r = roles.get(eid)
        if isinstance(r, dict) and r:
            ent["role_notes"] = {str(k): str(v) for k, v in r.items()}
        entities[eid] = ent
    unknown = sorted(set(labels) - set(entities))
    if unknown:
        raise ValueError(f"facts_inputs.entity_labels 含三账之外的实体: {unknown[:5]}")
    unknown = sorted(set(overrides) - set(entities))
    if unknown:
        raise ValueError(f"facts_inputs.peak_overrides 含三账之外的实体: {unknown[:5]}")

    inputs = {n: {"sha256": _sha256_path(case_dir / n)} for n in FACTS_LEDGER_INPUTS}
    if ledger is not None:
        inputs["provenance_ledger.json"] = {"sha256": _sha256_path(ledger_path)}
    facts = {"token": {"symbol": symbol, "decimals": decimals, "total_supply_raw": total_raw},
             "entities": entities, "metrics": metrics}
    if dual_basis is not None:
        facts["dual_basis"] = dual_basis
    facts["provenance"] = {
        "schema": FACTS_PROVENANCE_SCHEMA, "facts_binding": "ledger-derived",
        "mode": "exploration" if exploration else "formal",
        "inputs": inputs,
        "state_source": {"path": "state_source.json",
                         "sha256": _sha256_path(case_dir / "state_source.json")},
        "peak_overrides": used_overrides,
        "producer": {"path": "scripts/report/facts_gate.py",
                     "sha256": _sha256_path(Path(__file__).resolve())},
    }
    # 生成物必须过既有 facts gate（G2 供给上界/G3 内部一致等；无 state/渲染文本时 G1/G5 自然跳过）
    gate_errors, _notes = gate_check(Facts(facts))
    if gate_errors:
        raise ValueError("生成的 facts 未过既有 facts gate: " + "; ".join(gate_errors[:3]))
    return facts


def build_main(argv):
    ap = argparse.ArgumentParser(prog="facts_gate.py build")
    ap.add_argument("--case-dir", default=".")
    ap.add_argument("--source", default="state_source.json",
                    help="人工输入文件（basename，须在案根；读取其 facts_inputs 块）")
    ap.add_argument("--out", default="facts.json")
    ap.add_argument("--exploration", action="store_true",
                    help="允许缺峰值来源（peak=current）；产物 provenance.mode=exploration，发布闸/收口必拒")
    a = ap.parse_args(argv)
    case_dir = Path(a.case_dir)
    if a.source != "state_source.json":
        print("FAIL: --source 只接受案根 state_source.json（人工字段复用该文件，不另立文件）")
        return 2
    try:
        facts = derive_facts(case_dir, exploration=a.exploration)
    except (KeyError, ValueError, OSError, TypeError) as exc:
        print(f"FAIL: facts 生成失败——{exc}")
        return 2
    out = case_dir / Path(a.out).name
    payload = json.dumps(facts, ensure_ascii=False, indent=2) + "\n"
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, out)
    mode = facts["provenance"]["mode"]
    print(f"PASS: facts 生成 {out.name}（mode={mode}，实体 {len(facts['entities'])} 个，"
          f"override {len(facts['provenance']['peak_overrides'])} 个）")
    if mode == "exploration":
        print("[exploration] 产物带非正式标记，new-analysis 发布闸与 stage2 收口必拒")
    return 0


def load_and_check(facts_path, state_path=None, md_text=None):
    """build_html.py 的接入点：渲染 md 并跑全 gate。返回 (rendered_md, errors, notes)。"""
    facts = Facts(json.load(open(facts_path, encoding="utf-8")))
    rendered = facts.render(md_text) if md_text is not None else None
    state = json.load(open(state_path, encoding="utf-8")) if state_path else None
    errors, notes = gate_check(facts, state, rendered)
    return rendered, errors, notes


def main():
    if sys.argv[1:2] == ["build"]:
        return build_main(sys.argv[2:])
    ap = argparse.ArgumentParser()
    ap.add_argument("--facts", required=True)
    ap.add_argument("--state", help="analysis-state.json（给了才做 G1 成员集合对账）")
    ap.add_argument("--md", help="报告 md（给了才做 G4/G5 渲染检查）")
    a = ap.parse_args()
    md = open(a.md, encoding="utf-8").read() if a.md else None
    try:
        _, errors, notes = load_and_check(a.facts, a.state, md)
    except (KeyError, ValueError) as e:
        print(f"FAIL: 宏/facts 结构错误——{e}")
        return 1
    for n in notes:
        print(f"[NOTE] {n}")
    if errors:
        for e in errors:
            print(f"[GATE-FAIL] {e}")
        print(f"FAIL: {len(errors)} 项语义 gate 未过——数字/成员不同源，修 facts 或 state")
        return 1
    print("PASS: facts 语义 gate 全过（成员集合/供给上界/内部一致"
          + ("/渲染完备" if md else "") + "）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
