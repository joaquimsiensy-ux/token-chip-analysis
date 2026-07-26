#!/usr/bin/env python3
"""图表数据同源化（3.19，A8）——报告编译化从正文延伸到图层。

解决的缺口：facts 语义 gate（facts_gate.py）管住了正文数字，但图 1/流转图的数据
此前仍是每案现场手工装配 Python 结构传绘图函数——手抄数字被消灭于正文，却还能
溜进图里的卡片与【总量X%】标注。本件让图的数据要么直接从 state/facts 生成、要么
经宏渲染同源、要么与 facts 强制对账。

三种模式：

  fig1   图 1 从 analysis-state.json 的 camp_share_series 直出（消灭手工装配）：
         python3 figures_from_facts.py fig1 --state analysis-state.json \
             --token QUQ --out charts/fig1.png [--price-csv price.csv]
         price csv 列自动探测（date/ts/time/day + close/price/usd），也可用
         --price-cols date,close 显式指定。

  flow   流转图 spec 渲染出图：spec JSON（nodes/edges/title/subtitle/footnote 直传
         lifecycle_flow.draw_lifecycle_flow）中**一切字符串字段允许写 facts 宏**
         （{{e_x.amount_share}} 等，语法同 facts_gate）——流转图卡片数字与正文
         同源；渲染后任何残留 {{...}} 即失败（同 G4，宏名打错不许静默）：
         python3 figures_from_facts.py flow --facts facts.json \
             --spec flow_e_big1.json --out charts/flow_e_big1.png \
             --strict-text-numbers
         新写作纪律：spec 用户可见文字里的持仓/份额/成员数/日期/层数等案情数字
         一律写宏，禁止手打；strict 模式会拒绝残留硬编码数字。

  check  图 2 装配数据与 facts 终值对账：whale_series JSON 各实体线的 pct 末点
         vs facts entities 的 current share，偏差 > 容差（默认 0.05pp）报错。
         若实体资金曾进入临时托管/锁仓设施，line 可带
         temporary_custody_checks=[{label,start_date,end_date,minimum_raw}]；
         check 会验证区间内经济归属线不低于该可归属本金，防止把“转入设施”
         误画成“实体清仓”：
         python3 figures_from_facts.py check --facts facts.json \
             --series charts/whale_series.json [--tol-pp 0.05]
         series 条目带 entity_id 的按 id 对 facts 实体；否则按 label 匹配。
         图 2 的时间序列本身无法从快照型 state 重建（需重放中间序列），故此处
         做终值对账而非生成——序列中间值的正确性仍由重放脚本+对账关卡负责。

退出码：0=成功/对账过；1=失败（宏残留/对账超差/输入缺失）。
"""
import argparse
import csv
import datetime as dt
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from facts_gate import Facts, MACRO_RE  # noqa: E402


def _load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _parse_date(s):
    s = str(s).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(s, fmt)
        except ValueError:
            pass
    # epoch 秒
    try:
        return dt.datetime.fromtimestamp(float(s), dt.timezone.utc).replace(tzinfo=None)
    except (ValueError, OSError):
        raise SystemExit(f"FAIL: 无法解析日期 {s!r}")


def _read_price_csv(path, cols=None):
    """价格 csv → {"ts": [...], "usd": [...]}；列名自动探测或 --price-cols 指定。"""
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit(f"FAIL: 价格文件空 {path}")
    if cols:
        dcol, pcol = [c.strip() for c in cols.split(",")]
    else:
        keys = {k.lower(): k for k in rows[0]}
        dcol = next((keys[k] for k in ("date", "ts", "time", "day", "datetime")
                     if k in keys), None)
        pcol = next((keys[k] for k in ("close", "price", "usd", "price_usd")
                     if k in keys), None)
        if not dcol or not pcol:
            raise SystemExit(f"FAIL: 价格列探测失败（列={list(rows[0])}），"
                             "用 --price-cols 日期列,价格列 指定")
    ts, usd = [], []
    for r in rows:
        if not (r.get(dcol) and r.get(pcol)):
            continue
        ts.append(_parse_date(r[dcol]))
        usd.append(float(r[pcol]))
    return {"ts": ts, "usd": usd}


def mode_fig1(a):
    state = _load(a.state)
    css = state.get("camp_share_series") or {}
    if not isinstance(css, dict):
        raise SystemExit(
            "FAIL: state.camp_share_series 必须是 "
            '{"dates":[...],"series":{"阵营":[...]}} 对象，不能是逐日对象列表'
        )
    dates, series_by_camp = css.get("dates"), css.get("series")
    if not dates or not isinstance(series_by_camp, dict) or not series_by_camp:
        raise SystemExit("FAIL: state 缺 camp_share_series.dates/series，无法直出图 1")
    series = {"ts": [_parse_date(d) for d in dates]}
    n = len(series["ts"])
    for camp, vals in series_by_camp.items():
        if len(vals) != n:
            raise SystemExit(f"FAIL: 阵营「{camp}」长度 {len(vals)} ≠ dates {n}")
        series[camp] = vals
    price = _read_price_csv(a.price_csv, a.price_cols) if a.price_csv else None
    from standard_charts import plot_camp_evolution
    plot_camp_evolution(series, a.out, a.token or
                        (state.get("token") or {}).get("symbol", "?"),
                        price_series=price)
    print(f"OK fig1: {len(series['ts'])} 点 × {len(series_by_camp)} 阵营 → {a.out}"
          + (f"（价格 {len(price['ts'])} 点）" if price else "（无价格轴）"))
    return 0


def _render_deep(obj, facts):
    """递归渲染任意嵌套结构里的字符串宏（数字同源的通道）。"""
    if isinstance(obj, str):
        return facts.render(obj)
    if isinstance(obj, list):
        return [_render_deep(x, facts) for x in obj]
    if isinstance(obj, dict):
        return {k: _render_deep(v, facts) for k, v in obj.items()}
    return obj


_STATIC_NUMERIC_TOKEN_RE = re.compile(r"\b(?:V[234]|P[01]|R[1-4])\b|#\d+")
_DIGIT_RE = re.compile(r"\d")


def _strict_text_number_violations(obj, path="$"):
    """找用户可见字符串里未走 facts 宏的案情数字；结构字段与固定类型号除外。"""
    errs = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in {"id", "src", "dst", "kind", "color"}:
                continue
            errs.extend(_strict_text_number_violations(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            errs.extend(_strict_text_number_violations(v, f"{path}[{i}]"))
    elif isinstance(obj, str):
        masked = MACRO_RE.sub("", obj)
        masked = _STATIC_NUMERIC_TOKEN_RE.sub("", masked)
        if _DIGIT_RE.search(masked):
            errs.append((path, obj))
    return errs


def mode_flow(a):
    facts = Facts(_load(a.facts))
    spec = _load(a.spec)
    if a.strict_text_numbers:
        violations = _strict_text_number_violations(spec)
        if violations:
            for path, value in violations[:10]:
                print(f"[FLOW-NUM-FAIL] {path}: {value!r}")
            raise SystemExit(
                "FAIL: flow spec 用户可见文字含未走 facts 宏的数字；"
                "成员数/日期/金额/份额/层数等均改用 {{e.naddr}} 或 {{m:id}}。"
            )
    try:
        spec = _render_deep(spec, facts)
    except KeyError as e:
        raise SystemExit(f"FAIL: flow spec 宏渲染失败——{e}")
    leftovers = MACRO_RE.findall(json.dumps(spec, ensure_ascii=False))
    if leftovers:
        raise SystemExit(f"FAIL: flow spec 渲染后残留宏 {leftovers[:5]}（同 G4 语义）")
    from lifecycle_flow import draw_lifecycle_flow
    draw_lifecycle_flow(a.out, spec.get("title", ""), spec.get("nodes") or [],
                        spec.get("edges") or [], footnote=spec.get("footnote", ""),
                        subtitle=spec.get("subtitle", ""))
    print(f"OK flow: {len(spec.get('nodes') or [])} 节点 / "
          f"{len(spec.get('edges') or [])} 边（宏已同源渲染）→ {a.out}")
    return 0


def mode_check(a):
    facts = Facts(_load(a.facts))
    series = _load(a.series)
    if not isinstance(series, list):
        raise SystemExit("FAIL: --series 应为图 2 whale_series JSON（list of lines）")
    by_label = {(e.get("label") or "").strip(): (eid, e)
                for eid, e in facts.entities.items()}
    errs, okc, custody_okc = [], 0, 0
    for line in series:
        eid = (line.get("entity_id") or "").strip()
        lbl = (line.get("label") or "").strip()
        if eid and eid in facts.entities:
            ent, key = facts.entities[eid], f"entity_id={eid}"
        elif lbl in by_label:
            eid, ent = by_label[lbl]
            key = f"label「{lbl}」"
        else:
            errs.append(f"线「{lbl or eid}」在 facts.entities 中无匹配"
                        "（加 entity_id 字段或对齐 label）")
            continue
        pct = line.get("pct") or []
        ts = line.get("ts") or []
        if not pct:
            errs.append(f"{key} 线无 pct 数据")
            continue
        if len(ts) != len(pct):
            errs.append(f"{key} ts 长度 {len(ts)} ≠ pct 长度 {len(pct)}")
            continue
        last = float(pct[-1])
        cur = int(str(ent.get("current_raw", "0")))
        want = cur / facts.total_raw * 100 if facts.total_raw else 0.0
        if abs(last - want) > a.tol_pp:
            errs.append(f"{key} 线末点 {last:.4f}% ≠ facts 当前 {want:.4f}%"
                        f"（差 {abs(last-want):.4f}pp > 容差 {a.tol_pp}pp）")
        else:
            okc += 1
        for check in line.get("temporary_custody_checks") or []:
            cname = str(check.get("label") or "临时托管区间")
            start_s = check.get("start_date")
            end_s = check.get("end_date")
            minimum_raw = check.get("minimum_raw")
            if not start_s or not end_s or minimum_raw in (None, ""):
                errs.append(
                    f"{key} 的 {cname} 缺 start_date/end_date/minimum_raw"
                )
                continue
            try:
                start, end = _parse_date(start_s), _parse_date(end_s)
                minimum_pct = int(str(minimum_raw)) / facts.total_raw * 100
                points = [
                    float(value)
                    for day, value in zip(ts, pct)
                    if start <= _parse_date(day) <= end
                ]
            except (TypeError, ValueError):
                errs.append(f"{key} 的 {cname} 日期或 minimum_raw 无法解析")
                continue
            if not points:
                errs.append(f"{key} 的 {cname} 在 {start_s}~{end_s} 无序列点")
                continue
            observed_min = min(points)
            if observed_min + a.tol_pp < minimum_pct:
                errs.append(
                    f"{key} 的 {cname} 区间最低 {observed_min:.4f}% "
                    f"< 可归属本金 {minimum_pct:.4f}%"
                    f"（容差 {a.tol_pp}pp；疑似把临时托管误画成清仓）"
                )
            else:
                custody_okc += 1
    if errs:
        for e in errs:
            print(f"[CHECK-FAIL] {e}")
        print(f"FAIL: 图 2 装配数据与 facts 终值 {len(errs)} 处不同源")
        return 1
    print(f"PASS: 图 2 全部 {okc} 条实体线末点与 facts 当前持仓同源"
          f"（容差 {a.tol_pp}pp）；临时托管连续性检查 {custody_okc} 条通过")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="mode", required=True)
    p1 = sub.add_parser("fig1", help="图1 从 state 直出")
    p1.add_argument("--state", required=True)
    p1.add_argument("--token")
    p1.add_argument("--out", required=True)
    p1.add_argument("--price-csv")
    p1.add_argument("--price-cols", help="日期列,价格列（默认自动探测）")
    p1.set_defaults(fn=mode_fig1)
    p2 = sub.add_parser("flow", help="流转图 spec 宏渲染出图")
    p2.add_argument("--facts", required=True)
    p2.add_argument("--spec", required=True)
    p2.add_argument("--out", required=True)
    p2.add_argument(
        "--strict-text-numbers",
        action="store_true",
        help="拒绝 title/subtitle/nodes/edges/footnote 中未走 facts 宏的案情数字",
    )
    p2.set_defaults(fn=mode_flow)
    p3 = sub.add_parser("check", help="图2 装配数据与 facts 终值对账")
    p3.add_argument("--facts", required=True)
    p3.add_argument("--series", required=True)
    p3.add_argument("--tol-pp", type=float, default=0.05)
    p3.set_defaults(fn=mode_check)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
