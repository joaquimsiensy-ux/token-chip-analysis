#!/usr/bin/env python3
"""报告编译化事实源（3.18.0，@CX 融合方案第一档 Top1 的第 1+2 步）。

解决的架构病：数字/地址手抄进报告已第四犯——纪律拦不住，只有"架构不允许手抄"拦得住。
报告 md 里写宏引用，本模块渲染+语义 gate：正文数字、附录 B、analysis-state.json 三处
永远同源；改一处数据其余处必然跟着变，对不上编译直接失败（fail-closed）。

facts.json schema（每案一份，阶段 3 结束时从落盘数据构建；数值一律**原始整数字符串**）：
{
  "token": {"symbol": "QUQ", "decimals": 18, "total_supply_raw": "1000...0"},
  "entities": {
    "e_big1": {"label": "大庄#1(bot体系)", "tier": "P0",
               "addresses": ["0x完整地址", ...],
               "current_raw": "278400...", "peak_raw": "687000...",
               "peak_date": "2026-05-01", "role_notes": {"0x地址": "角色备注(可选)"}}
  },
  "metrics": {
    "m_alpha": {"num_raw": "376...", "den": "total_supply", "desc": "币安Alpha托管"},
    "m_price_x": {"value": "9.4", "unit": "倍", "desc": "峰值涨幅"}   # 自由值型
  }
}

报告 md 宏语法（渲染后无残留 {{...}}，否则 gate 拒绝——宏名打错不许静默漏渲染）：
  {{e_big1.label}}            → 大庄#1(bot体系)
  {{e_big1.share}}            → 27.84%（current_raw/total_supply）
  {{e_big1.peak_share}}       → 68.70%
  {{e_big1.amount}}           → 2.78亿枚
  {{e_big1.amount_share}}     → 2.78亿枚【总量27.84%】（最常用组合，报告纪律格式）
  {{e_big1.naddr}}            → 215（成员地址数）
  {{m:m_alpha}}               → 37.60%（num/den 型）或 value+unit（自由值型）
  {{appendix_b}}              → 附录 B 标签↔地址对照表整块（md 表格，与 entities 同源）

语义 gate（--state 给了 analysis-state.json 时全部启用）：
  G1 实体成员集合：facts.entities[*].addresses 与 state.whale_groups 同 label 组逐组相等
  G2 供给上界：Σ entities.current_raw ≤ total_supply_raw
  G3 内部一致：current_raw ≤ peak_raw（每实体）
  G4 渲染完备：渲染后正文无残留 {{...}}
  G5 手写数字检测：正文所有 NN.NN% 中不来自宏渲染的列成清单（NOTE 级人工过目；
     百分比一律该走宏——这是新写作纪律，见 report-template.md）

用法（库 + CLI 双形态；build_html.py --facts 参数内部调用）：
  python3 facts_gate.py --facts facts.json --state analysis-state.json   # 纯校验
"""
import argparse
import json
import re
import sys

MACRO_RE = re.compile(r"\{\{([A-Za-z0-9_.:]+)\}\}")
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
        by_label = {}
        for g in state.get("whale_groups") or []:
            by_label[(g.get("label") or "").strip()] = {
                _norm(a) for a in (g.get("addresses") or [])}
        for eid, ent in facts.entities.items():
            lbl = (ent.get("label") or "").strip()
            if lbl not in by_label:
                errors.append(f"G1 state.whale_groups 缺组「{lbl}」（facts {eid}）")
                continue
            fa = {_norm(a) for a in ent.get("addresses") or []}
            sa = by_label[lbl]
            if fa != sa:
                miss, extra = sorted(sa - fa)[:3], sorted(fa - sa)[:3]
                errors.append(f"G1 「{lbl}」成员集合不一致：state 独有 {len(sa-fa)} 个"
                              f"（样例 {miss}），facts 独有 {len(fa-sa)} 个（样例 {extra}）")
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


def load_and_check(facts_path, state_path=None, md_text=None):
    """build_html.py 的接入点：渲染 md 并跑全 gate。返回 (rendered_md, errors, notes)。"""
    facts = Facts(json.load(open(facts_path, encoding="utf-8")))
    rendered = facts.render(md_text) if md_text is not None else None
    state = json.load(open(state_path, encoding="utf-8")) if state_path else None
    errors, notes = gate_check(facts, state, rendered)
    return rendered, errors, notes


def main():
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
