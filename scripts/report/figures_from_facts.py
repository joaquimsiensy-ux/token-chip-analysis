#!/usr/bin/env python3
"""图表数据同源化（3.19，A8）——报告编译化从正文延伸到图层。

解决的缺口：facts 语义 gate（facts_gate.py）管住了正文数字，但图 1/流转图的数据
此前仍是每案现场手工装配 Python 结构传绘图函数——手抄数字被消灭于正文，却还能
溜进图里的卡片与【总量X%】标注。本件让图的数据要么直接从 state/facts 生成、要么
经宏渲染同源、要么与 facts 强制对账。

三种模式：

  fig1   图 1 从 analysis-state.json 的 camp_share_series 直出（消灭手工装配）：
         python3 figures_from_facts.py fig1 --state analysis-state.json \
             --token QUQ --out charts/final/fig1.png [--price-csv price.csv]
         price csv 列自动探测（date/ts/time/day + close/price/usd），也可用
         --price-cols date,close 显式指定。

  flow   流转图 spec 渲染出图：spec JSON（nodes/edges/title/subtitle/footnote 直传
         lifecycle_flow.draw_lifecycle_flow）中**一切字符串字段允许写 facts 宏**
         （{{e_x.amount_share}} 等，语法同 facts_gate）——流转图卡片数字与正文
         同源；渲染后任何残留 {{...}} 即失败（同 G4，宏名打错不许静默）：
         python3 figures_from_facts.py flow --facts facts.json \
             --spec flow_e_big1.json --out charts/flow_e_big1.png
         新写作纪律：spec 里的持仓/份额/成员数数字一律写宏，禁止手打。

  check  图 2 装配数据与 facts 终值对账：whale_series JSON 各实体线的 pct 末点
         vs facts entities 的 current share，偏差 > 容差（默认 0.05pp）报错：
         python3 figures_from_facts.py check --facts facts.json \
             --series charts/whale_series.json [--tol-pp 0.05]
         series 条目带 entity_id 的按 id 对 facts 实体；否则按 label 匹配。
         图 2 的时间序列本身无法从快照型 state 重建（需重放中间序列），故此处
         做终值对账而非生成——序列中间值的正确性仍由重放脚本+对账关卡负责。

退出码：0=成功/对账过；1=失败（宏残留/对账超差/输入缺失）；
        2=check 容差政策拒（正式模式改 --tol-pp 未加 --exploration，F-04 钳制）。
check 留痕（F-C5）：每次对账（PASS/FAIL、formal/exploration）都落
  figure2_check_receipt.json（mode/tol_pp/verdict/facts+series sha）到工作目录；
  发布闸 new-analysis 复验其在场且 mode=formal、tol_pp=默认、verdict=PASS——
  exploration 放宽的运行有痕、且过不了发布闸。
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import os
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
    dates, series_by_camp = css.get("dates"), css.get("series")
    if not dates or not series_by_camp:
        raise SystemExit("FAIL: state 缺 camp_share_series.dates/series，无法直出图 1")
    series = {"ts": [_parse_date(d) for d in dates]}
    n = len(series["ts"])
    for camp, vals in series_by_camp.items():
        if len(vals) != n:
            raise SystemExit(f"FAIL: 阵营「{camp}」长度 {len(vals)} ≠ dates {n}")
        series[camp] = vals
    price = _read_price_csv(a.price_csv, a.price_cols) if a.price_csv else None
    overlay = None
    if a.overlay:
        overlay = []
        for spec in a.overlay:
            label, sep, expr = spec.partition("=")
            if not sep:
                raise SystemExit(f'FAIL: --overlay 格式应为 "标签=阵营A+阵营B"，收到 {spec!r}')
            names = [c.strip() for c in expr.split("+") if c.strip()]
            missing = [c for c in names if c not in series_by_camp]
            if missing:
                raise SystemExit(f"FAIL: --overlay 引用了不存在的阵营 {missing}；"
                                 f"可用阵营：{list(series_by_camp)}")
            overlay.append({"label": label.strip(),
                            "pct": [sum(series_by_camp[c][i] for c in names) for i in range(n)]})
    from standard_charts import plot_camp_evolution
    plot_camp_evolution(series, a.out, a.token or
                        (state.get("token") or {}).get("symbol", "?"),
                        price_series=price, overlay=overlay)
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


def mode_flow(a):
    facts = Facts(_load(a.facts))
    spec = _load(a.spec)
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


DEFAULT_TOL_PP = 0.05  # 图 2 末点对账容差；formal 写死本值，仅 --exploration 可覆盖
CHECK_RECEIPT_NAME = "figure2_check_receipt.json"


def _file_ref(path):
    data = open(path, "rb").read()
    return {"path": os.path.basename(str(path)),
            "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}


def _write_check_receipt(a, verdict, okc, errs):
    """F-C5：check 的留痕收据（写 --series 文件同目录；whale_series 惯例在案根，
    收据即落案根供发布闸复验）。PASS/FAIL 都写（exploration 运行同样留痕，mode
    字段如实记录）；发布闸（audit_release_gate new-analysis）复验在场且
    mode==formal、tol_pp==默认、verdict==PASS。政策拒（exit 2）在此之前发生，
    不产收据。写法=tmp+fsync+os.replace（对齐 receipt_kernel 先例）。"""
    doc = {"schema": "figure2-check-receipt/v1",
           "mode": "exploration" if a.exploration else "formal",
           "tol_pp": a.tol_pp, "verdict": verdict,
           "facts": _file_ref(a.facts), "series": _file_ref(a.series),
           "lines_checked": okc, "mismatches": errs,
           "generated_at_utc": dt.datetime.now(dt.timezone.utc)
                                 .strftime("%Y-%m-%dT%H:%M:%SZ")}
    out = os.path.join(os.path.dirname(os.path.abspath(a.series)),
                       CHECK_RECEIPT_NAME)
    tmp = out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, out)


def mode_check(a):
    # F-04 同族钳制（同 supply_truth_gate --tolerance-bps 的 F-02 模式）：--tol-pp 直接
    # 决定图 2 末点对账 PASS/FAIL，是判定翻转参数——正式模式写死默认值，探索放宽必须
    # 显式声明 --exploration（fail-loud，不静默夹回默认值）。exit 2=容差政策拒
    # （调用方式非法，与对账 FAIL 的 exit 1 区分，同 supply_truth_gate 口径）
    if not a.exploration and a.tol_pp != DEFAULT_TOL_PP:
        print(f"FAIL: 正式模式 --tol-pp 写死 {DEFAULT_TOL_PP}pp（收到 {a.tol_pp}）"
              f"——探索性放宽必须显式加 --exploration", file=sys.stderr)
        raise SystemExit(2)
    facts = Facts(_load(a.facts))
    series = _load(a.series)
    if not isinstance(series, list):
        raise SystemExit("FAIL: --series 应为图 2 whale_series JSON（list of lines）")
    by_label = {(e.get("label") or "").strip(): (eid, e)
                for eid, e in facts.entities.items()}
    errs, okc = [], 0
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
        if not pct:
            errs.append(f"{key} 线无 pct 数据")
            continue
        last = float(pct[-1])
        cur = int(str(ent.get("current_raw", "0")))
        want = cur / facts.total_raw * 100 if facts.total_raw else 0.0
        if abs(last - want) > a.tol_pp:
            errs.append(f"{key} 线末点 {last:.4f}% ≠ facts 当前 {want:.4f}%"
                        f"（差 {abs(last-want):.4f}pp > 容差 {a.tol_pp}pp）")
        else:
            okc += 1
    if errs:
        for e in errs:
            print(f"[CHECK-FAIL] {e}")
        _write_check_receipt(a, "FAIL", okc, errs)
        print(f"FAIL: 图 2 装配数据与 facts 终值 {len(errs)} 处不同源"
              f"（收据 {CHECK_RECEIPT_NAME}）")
        return 1
    _write_check_receipt(a, "PASS", okc, [])
    tag = "[exploration] " if a.exploration else ""
    print(f"{tag}PASS: 图 2 全部 {okc} 条实体线末点与 facts 当前持仓同源"
          f"（容差 {a.tol_pp}pp，收据 {CHECK_RECEIPT_NAME}）")
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
    p1.add_argument("--overlay", action="append", metavar="标签=阵营A+阵营B",
                    help="合并口径虚线（可重复）。凡实体筹码会在两个并列阵营间搬家"
                         "（项目方自挂 LP／金库↔质押／金库↔CEX），分列堆叠图会把搬家画成增减持，"
                         "必须加此线；阵营名须存在于 camp_share_series，否则报错。"
                         '例：--overlay "项目方＋池中自挂LP（合计·上界）=项目方+流动性池"')
    p1.set_defaults(fn=mode_fig1)
    p2 = sub.add_parser("flow", help="流转图 spec 宏渲染出图")
    p2.add_argument("--facts", required=True)
    p2.add_argument("--spec", required=True)
    p2.add_argument("--out", required=True)
    p2.set_defaults(fn=mode_flow)
    p3 = sub.add_parser("check", help="图2 装配数据与 facts 终值对账")
    p3.add_argument("--facts", required=True)
    p3.add_argument("--series", required=True)
    p3.add_argument("--tol-pp", type=float, default=DEFAULT_TOL_PP,
                    help=f"末点对账容差 pp；正式模式写死 {DEFAULT_TOL_PP}，"
                         "改动必须同时加 --exploration")
    p3.add_argument("--exploration", action="store_true",
                    help="显式声明探索运行，才允许覆盖 --tol-pp（正式发布禁用）")
    p3.set_defaults(fn=mode_check)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
