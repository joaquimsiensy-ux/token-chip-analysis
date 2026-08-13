#!/usr/bin/env python3
"""阵营序列 producer→consumer 链（F-04，2026-08-13 六视角修复批 C）。

问题背景：analysis-state 的 camp_share_series（图 1 数据）此前是调用者自报字段——
compile_state 只验容器与长度，不验有限数/值域/闭合/标准阵营名，也不绑定任何
重放产物；伪造序列可以一路走到 A5 封章。本模块补上两件事：

一、producer sidecar（来源绑定）：四族重放 producer 写序列文件时同步写
   `<序列名去 .json>.provenance.json`，内容=producer 名＋阵营 spec/输入文件的
   sha256＋输出文件 sha256。consumer（state_from_facts --series-source）只认
   带 sidecar 的序列：验输出 sha 匹配＋输入实物三验（存在+sha+size）＋
   inputs 命中案内 supply_truth/reconcile 登记面。伪造序列由此必须连案内
   整条数据链一起伪造（与 F-12 已接受边界同款残余）。

二、末点对账（camps spec 机械派生）：从 sidecar 绑定的 camps spec＋同一次
   重放落盘的终态余额快照，机械重算各 spec 阵营的终点份额，与序列末点比对。
   08-13 真实案实测（工单批 C）：TROLL(Solana) spec 内三阵营 0.0000pp 全中、
   TAG(BSC) 项目方 0.0137pp 命中；同时实测确认两条硬边界——
   ①快照必须与序列同一次重放同源（TROLL 用异时点链上快照比对差 0.08~0.44pp、
     用另一版重放差 1.7~2.3pp，异源比对必假红），sidecar 的"同运行输出登记"
     就是为此；
   ②动态桶（其他大户动态判定/首30分钟狙击者/散户残差）不在 camps spec 里，
     无法机械派生——末点对账=spec 内阵营逐桶精确比对＋spec 外桶合并成残差
     用恒等式比对（不是单向下界：spec 桶全部双向精确，残差=100−Σspec 也是
     双向等式）。

burn 口径定案（施工前 rg 全库落锤，防 100% 闭合闸误杀 burn 案）：
  - EVM camp_series.json（dict 形态）：轴键 `dates`、元数据 `_meta`、
    burn 单列 `burn_cum_pct`（分母=当期净供应，可 >100%，不参与堆叠闭合）；
    legacy 口径（CHIP_LEGACY_CAMP_DENOM=1）"销毁"桶参与 100% 闭合。
  - Solana replay_edges camp_share_series.json（行数组形态）：行内轴键 `ts`、
    元数据 `_supply_raw`、burn 行内桶 `锁仓/销毁`（分母=净供应 minted−burned，
    不参与闭合，可 >100%）。
  - Solana build_evolution camp_series.json（行数组形态）：`锁仓/销毁` 在
    total_supply 分母下**参与** 100% 闭合（散户残差吸收）——与 replay_edges
    同名键不同语义。
  故同点闭合公式=双式：非 burn 桶之和≈100（净分母族）或 全桶之和≈100
  （total 分母族/legacy），二中其一即过；burn 桶单独验非负有限、不设 100 上界。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from supply_semantics import ZERO  # noqa: E402

SIDECAR_SCHEMA = "camp-series-provenance/v1"
# 净分母族的 burn 桶不参与堆叠闭合；total 分母族"锁仓/销毁"参与——双式闭合见 docstring。
# EVM legacy 堆叠桶"销毁"（CHIP_LEGACY_CAMP_DENOM=1 才出现）不在此列：legacy 重放
# 不入正式编译，白名单先拒，列进来就是永远走不到的死分支
BURN_EXEMPT_KEYS = ("burn_cum_pct", "锁仓/销毁")
AXIS_META_KEYS = ("dates", "ts", "_meta", "_supply_raw")
CLOSURE_TOL_PP = 0.05     # 同点合计闭合容差（0.05pp 级；round(4)×14 桶的舍入远小于此）
ENDPOINT_TOL_PP = 0.05    # 末点对账容差（formal 写死，与 figures check 默认同族同值）
# sol-rows 动态桶 → 现役散户桶的固定并桶映射（replay_edges 现役输出含两个 legacy 动态
# 桶名；新报告禁用 legacy 阵营名，转换层并入散户，狙击窗信息在 sniper_set.json 另存不丢）。
# 这是转换语义不是阵营名单——阵营白名单唯一权威仍是 standard_charts.CAMP_ORDER_MODERN。
SOL_DYNAMIC_BUCKET_MERGE = {"其他散户": "散户", "首30分钟狙击者": "散户"}
SERIES_FORMATS = ("evm-dict", "sol-rows", "sol-anchor-rows", "evm-entity-dict")
DENOMINATORS = ("current_net_supply", "mint_total_legacy", "net_supply",
                "config_total_supply")


class SeriesProvenanceError(ValueError):
    """sidecar 缺失/不匹配/序列数值面非法/末点对账失败（调用方按 exit 2 处理）。"""


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sidecar_path_for(series_path) -> Path:
    series_path = Path(series_path)
    stem = series_path.name[:-5] if series_path.name.endswith(".json") \
        else series_path.name
    return series_path.with_name(stem + ".provenance.json")


def _file_ref(path) -> dict:
    path = Path(path)
    return {"path": path.name, "sha256": sha256_file(path),
            "size": path.stat().st_size}


def write_series_sidecar(series_path, *, producer: str, series_format: str,
                         denominator: str, camps_spec_path=None,
                         final_balances_path=None, inputs=None, extra=None) -> Path:
    """producer 在序列文件落盘后立即调用；sidecar 与序列同目录、tmp+os.replace 原子写。

    inputs: {语义名: 路径} —— 只登记与本次重放同源的小文件（replay_stats/
    reconcile_receipt/sniper_set 等）；亿级边数据本体不进 sidecar（其完整性由
    replay_stats 的 reject 记账与 supply truth 链保证，sidecar 锚 replay_stats
    即锚到该链）。
    """
    series_path = Path(series_path)
    if series_format not in SERIES_FORMATS:
        raise SeriesProvenanceError(f"series_format 只认 {SERIES_FORMATS}，"
                                    f"收到 {series_format!r}")
    if denominator not in DENOMINATORS:
        raise SeriesProvenanceError(f"denominator 只认 {DENOMINATORS}，"
                                    f"收到 {denominator!r}")
    doc = {
        "schema": SIDECAR_SCHEMA,
        "producer": producer,
        "series_file": series_path.name,
        "series_sha256": sha256_file(series_path),
        "series_size": series_path.stat().st_size,
        "series_format": series_format,
        "denominator": denominator,
        "camps_spec": _file_ref(camps_spec_path) if camps_spec_path else None,
        "final_balances": _file_ref(final_balances_path) if final_balances_path else None,
        "inputs": {name: _file_ref(p) for name, p in (inputs or {}).items()},
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if extra:
        doc["extra"] = dict(extra)
    out = sidecar_path_for(series_path)
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8")
    os.replace(tmp, out)
    return out


# ── consumer 侧 ──────────────────────────────────────────────────────


def _resolve_ref(ref: dict, label: str, search_dirs) -> Path:
    """按 basename 在 series 目录与其父目录（案根）两层内找实物并三验。

    路径只按 basename 解析（sidecar 不携带可逃逸路径），sha256 是权威身份；
    符号链接拒收（与 F-08/批 B 同口径）。
    """
    if not isinstance(ref, dict) or not ref.get("path") or not ref.get("sha256"):
        raise SeriesProvenanceError(f"sidecar {label} 必须绑定 path/sha256/size")
    name = Path(str(ref["path"])).name
    for base in search_dirs:
        cand = Path(base) / name
        if cand.is_symlink():
            raise SeriesProvenanceError(f"sidecar {label} 指向符号链接 {cand}，拒收")
        if cand.is_file():
            if cand.stat().st_size != ref.get("size"):
                raise SeriesProvenanceError(
                    f"sidecar {label} size 不匹配（{cand}: 实测 "
                    f"{cand.stat().st_size} ≠ 登记 {ref.get('size')}）")
            if sha256_file(cand) != str(ref["sha256"]).lower():
                raise SeriesProvenanceError(f"sidecar {label} sha256 不匹配（{cand}）")
            return cand
    raise SeriesProvenanceError(
        f"sidecar {label}（{name}）在序列目录与案根两层内都找不到")


def load_series_with_sidecar(series_path):
    """读序列文件＋sidecar，验证输出绑定与全部输入实物。返回 (sidecar, 原生序列, 实物路径表)。"""
    series_path = Path(series_path)
    if not series_path.is_file():
        raise SeriesProvenanceError(f"序列文件不存在: {series_path}")
    sc_path = sidecar_path_for(series_path)
    if not sc_path.is_file():
        raise SeriesProvenanceError(
            f"序列缺 provenance sidecar: {sc_path.name}——正式编译只认四族重放 "
            f"producer 落盘的序列（旧案重绘不经 compile_state，不受影响）")
    sidecar = json.loads(sc_path.read_text(encoding="utf-8"))
    if sidecar.get("schema") != SIDECAR_SCHEMA:
        raise SeriesProvenanceError(
            f"sidecar schema 必须是 {SIDECAR_SCHEMA}，收到 {sidecar.get('schema')!r}")
    if sidecar.get("series_file") != series_path.name:
        raise SeriesProvenanceError("sidecar series_file 与序列文件名不一致")
    if sha256_file(series_path) != str(sidecar.get("series_sha256", "")).lower():
        raise SeriesProvenanceError(
            "序列文件 sha256 与 sidecar 登记不一致——序列在 producer 落盘后被改动")
    if sidecar.get("series_format") not in SERIES_FORMATS:
        raise SeriesProvenanceError(f"sidecar series_format 非法: "
                                    f"{sidecar.get('series_format')!r}")
    search_dirs = [series_path.parent, series_path.parent.parent]
    resolved = {}
    if sidecar.get("camps_spec"):
        resolved["camps_spec"] = _resolve_ref(sidecar["camps_spec"], "camps_spec",
                                              search_dirs)
    if sidecar.get("final_balances"):
        resolved["final_balances"] = _resolve_ref(sidecar["final_balances"],
                                                  "final_balances", search_dirs)
    for name, ref in (sidecar.get("inputs") or {}).items():
        resolved[f"inputs.{name}"] = _resolve_ref(ref, f"inputs.{name}", search_dirs)
    raw = json.loads(series_path.read_text(encoding="utf-8"))
    return sidecar, raw, resolved


def series_to_state_form(raw, series_format: str) -> dict:
    """producer 原生形态 → state 标准形态 {"dates": [...], "series": {桶: [...]}}。

    转换规则固化在 consumer 单点（消灭案内手工转换的自由度）：
      evm-dict:  dates 原样；丢 _meta；burn_cum_pct 保留为豁免桶。
      sol-rows:  ts(epoch 秒) → "YYYY-MM-DDTHH:MM:SSZ"；丢 _supply_raw；
                 缺席行的桶补 0.0；动态桶按 SOL_DYNAMIC_BUCKET_MERGE 并入散户。
    """
    if series_format == "evm-dict":
        if not isinstance(raw, dict) or not isinstance(raw.get("dates"), list):
            raise SeriesProvenanceError("evm-dict 序列必须是含 dates 列表的对象")
        series = {k: v for k, v in raw.items() if k not in ("dates", "_meta")}
        return {"dates": list(raw["dates"]), "series": series}
    if series_format == "sol-rows":
        if not isinstance(raw, list) or not raw:
            raise SeriesProvenanceError("sol-rows 序列必须是非空行数组")
        buckets = []
        for row in raw:
            if not isinstance(row, dict) or "ts" not in row:
                raise SeriesProvenanceError("sol-rows 每行必须是含 ts 的对象")
            for key in row:
                if key in ("ts", "_supply_raw"):
                    continue
                mapped = SOL_DYNAMIC_BUCKET_MERGE.get(key, key)
                if mapped not in buckets:
                    buckets.append(mapped)
        dates, series = [], {c: [] for c in buckets}
        for row in raw:
            ts = row["ts"]
            if not isinstance(ts, (int, float)) or isinstance(ts, bool):
                raise SeriesProvenanceError(f"sol-rows ts 必须是 epoch 数值: {ts!r}")
            dates.append(datetime.fromtimestamp(int(ts), tz=timezone.utc)
                         .strftime("%Y-%m-%dT%H:%M:%SZ"))
            acc = {c: 0.0 for c in buckets}
            for key, value in row.items():
                if key in ("ts", "_supply_raw"):
                    continue
                acc[SOL_DYNAMIC_BUCKET_MERGE.get(key, key)] += float(value)
            for c in buckets:
                series[c].append(round(acc[c], 4))
        return {"dates": dates, "series": series}
    raise SeriesProvenanceError(
        f"series_format {series_format!r} 不接入正式编译链"
        f"（sol-anchor-rows=锚点法小样本辅助件、无对账链锚，正式序列走 "
        f"replay_edges/replay_duck；entity 序列走图 2 check 通道）")


# ── 数值面校验（compile_state 无条件调用，与 --series-source 无关）──────


_EPOCH_RE = re.compile(r"^\d{9,12}(\.\d+)?$")


def parse_axis_utc(value, index: int) -> datetime:
    """日期轴元素 → aware UTC datetime。接受 YYYY-MM-DD / ISO 日期时间（naive 视为
    UTC，带 tz 换算成 UTC）/ epoch 秒。解析失败=拒（非法日期不许静默）。"""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if _EPOCH_RE.match(text):
            return datetime.fromtimestamp(float(text), tz=timezone.utc)
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise SeriesProvenanceError(
                f"camp_share_series dates[{index}] 无法按 UTC 解析: {value!r}") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    raise SeriesProvenanceError(
        f"camp_share_series dates[{index}] 类型非法: {type(value).__name__}")


def modern_camp_whitelist() -> set:
    """阵营名唯一权威=standard_charts.CAMP_ORDER_MODERN（禁手抄第二份清单）。
    函数内 import：standard_charts 拖 matplotlib，producer 侧写 sidecar 不需要它。"""
    report_dir = Path(__file__).resolve().parents[1] / "report"
    if str(report_dir) not in sys.path:
        sys.path.insert(0, str(report_dir))
    from standard_charts import CAMP_ORDER_MODERN
    return set(CAMP_ORDER_MODERN)


def validate_series_payload(css: dict, *, tol_pp: float = CLOSURE_TOL_PP):
    """state 形态 camp_share_series 的数值面硬校验（拒=raise SeriesProvenanceError）：

    ①桶名白名单=CAMP_ORDER_MODERN ∪ burn 豁免键（legacy 桶名/实体级自造桶名一律拒，
      新报告禁用；旧案重绘不经 compile_state）；
    ②全值有限（json 的 NaN/Infinity 字面量默认能解析进来，必须显式查）；
    ③非 burn 桶值域 [0,100]；burn 桶仅验非负有限（burn_cum_pct 按净分母可 >100 合法）；
    ④同点合计双式闭合：非 burn 之和≈100 或 全桶之和≈100（容差 tol_pp；
      全桶全零点=供应未产生，豁免）；
    ⑤日期轴统一 UTC 解析后严格递增无重复（倒序/重复/非法日期/时区换算后倒挂都拒）。
    """
    dates = css.get("dates")
    series = css.get("series")
    if not isinstance(dates, list) or not dates or not isinstance(series, dict) \
            or not series:
        raise SeriesProvenanceError("camp_share_series 必须含非空 dates 列表与 series 对象")
    # "销毁"是 EVM legacy 堆叠桶（CHIP_LEGACY_CAMP_DENOM=1 才出现），legacy 重放不入
    # 正式编译，故不进白名单；"锁仓/销毁"在 CAMP_ORDER_MODERN 内本就合法
    allowed = modern_camp_whitelist() | {"burn_cum_pct"}
    bad_names = [c for c in series if c not in allowed]
    if bad_names:
        raise SeriesProvenanceError(
            f"camp_share_series 含白名单外桶名 {bad_names}——阵营名唯一权威是 "
            f"standard_charts.CAMP_ORDER_MODERN（v5.0 标签体系；legacy 名与实体级"
            f"自造桶名新报告禁用）")
    n = len(dates)
    for camp, values in series.items():
        if not isinstance(values, list) or len(values) != n:
            raise SeriesProvenanceError(f"桶「{camp}」长度 {len(values) if isinstance(values, list) else '非列表'} ≠ dates {n}")
        is_burn = camp in BURN_EXEMPT_KEYS
        for i, v in enumerate(values):
            if isinstance(v, bool) or not isinstance(v, (int, float)) \
                    or v != v or v in (float("inf"), float("-inf")):
                raise SeriesProvenanceError(f"桶「{camp}」[{i}] 非有限数值: {v!r}")
            if v < 0:
                raise SeriesProvenanceError(f"桶「{camp}」[{i}] 为负: {v}")
            if not is_burn and v > 100:
                raise SeriesProvenanceError(f"桶「{camp}」[{i}] 超出 100: {v}")
    non_burn = [c for c in series if c not in BURN_EXEMPT_KEYS]
    burn = [c for c in series if c in BURN_EXEMPT_KEYS]
    for i in range(n):
        s_non = sum(series[c][i] for c in non_burn)
        s_all = s_non + sum(series[c][i] for c in burn)
        if s_all == 0:
            continue  # 供应尚未产生的点（producer 全零输出），豁免
        if abs(s_non - 100.0) > tol_pp and abs(s_all - 100.0) > tol_pp:
            raise SeriesProvenanceError(
                f"第 {i} 点（{dates[i]}）合计不闭合：非burn桶Σ={s_non:.4f}、"
                f"全桶Σ={s_all:.4f}，两式均偏离 100 超过 {tol_pp}pp")
    prev = None
    for i, d in enumerate(dates):
        cur = parse_axis_utc(d, i)
        if prev is not None and cur <= prev:
            raise SeriesProvenanceError(
                f"日期轴非严格递增：dates[{i}]={d!r}（UTC {cur.isoformat()}）"
                f"不晚于前一点（UTC {prev.isoformat()}）——倒序/重复/时区换算倒挂都不许")
        prev = cur


# ── 登记面命中与末点对账（--series-source 模式）─────────────────────


def _sha_values(obj) -> set:
    out = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "sha256" and isinstance(value, str):
                out.add(value.lower())
            else:
                out.update(_sha_values(value))
    elif isinstance(obj, list):
        for item in obj:
            out.update(_sha_values(item))
    return out


def registry_anchor_check(sidecar: dict, resolved: dict, series_path):
    """sidecar 的 inputs 必须命中案内已对账的登记面（把序列锚进案内数据链）：

    evm-dict：案内（序列目录或其父目录）supply_truth.json 必须在场，且 sidecar
      登记的 replay_stats sha256 出现在 supply_truth 的 sha256 绑定集合中
      （supply_truth 收据 inputs.replay_stats 由批 A 起哈希绑定）。
    sol-rows：sidecar 必须绑定 reconcile_receipt（inputs.reconcile_receipt），
      该收据 gate_pass 必须为 true——工作流上 reconcile 是阶段 2 硬关卡，先于
      evolution；缺收据/收据 FAIL 的序列不入正式编译。
    """
    fmt = sidecar.get("series_format")
    series_path = Path(series_path)
    dirs = [series_path.parent, series_path.parent.parent]
    if fmt == "evm-dict":
        st = next((d / "supply_truth.json" for d in dirs
                   if (d / "supply_truth.json").is_file()), None)
        if st is None:
            raise SeriesProvenanceError(
                "案内找不到 supply_truth.json——正式序列必须先过供给真值闸"
                "（supply_truth_gate.py）再进编译")
        stats_ref = (sidecar.get("inputs") or {}).get("replay_stats")
        if not stats_ref:
            raise SeriesProvenanceError("evm-dict sidecar 必须登记 inputs.replay_stats")
        registered = _sha_values(json.loads(st.read_text(encoding="utf-8")))
        if str(stats_ref.get("sha256", "")).lower() not in registered:
            raise SeriesProvenanceError(
                "sidecar 登记的 replay_stats sha256 未命中 supply_truth.json 的"
                "绑定集合——序列与供给真值闸不是同一条数据链")
        return st
    if fmt == "sol-rows":
        rr = resolved.get("inputs.reconcile_receipt")
        if rr is None:
            raise SeriesProvenanceError(
                "sol-rows sidecar 必须登记 inputs.reconcile_receipt"
                "（replay_edges reconcile 是阶段 2 硬关卡，先跑 reconcile 再跑 evolution）")
        receipt = json.loads(Path(rr).read_text(encoding="utf-8"))
        if not receipt.get("gate_pass"):
            raise SeriesProvenanceError("reconcile_receipt gate_pass 非 true，序列不入正式编译")
        return rr
    raise SeriesProvenanceError(f"series_format {fmt!r} 无登记面锚，不入正式编译链")


def _load_camps_spec(resolved: dict, series_format: str, chain_family: str):
    from camp_spec import validate_camp_spec
    spec_path = resolved.get("camps_spec")
    if spec_path is None:
        raise SeriesProvenanceError("sidecar 未绑定 camps_spec，无法做末点对账")
    obj = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    if series_format == "evm-dict":
        obj = obj.get("camps", {})
    return validate_camp_spec(obj, chain_family=chain_family,
                              source_label=str(spec_path))


def endpoint_reconcile(sidecar: dict, css: dict, resolved: dict,
                       *, tol_pp: float = ENDPOINT_TOL_PP):
    """末点对账=camps spec＋同源终态余额快照机械重算 vs 序列末点。

    spec 内阵营逐桶 |重算−末点| ≤ tol_pp；序列里 spec 外的非散户非豁免桶=拒
    （该序列不是这份 spec 产的）；散户（含 sol 动态桶并入后）用残差恒等式比对。
    分母不信 sidecar 自报数字，一律从终态快照机械派生：
      evm-dict 当期净供应 = Σ(全部终态余额) − ZERO 哨兵余额（烧入 0x0 的量）；
               legacy 口径 = Σ(全部终态余额)（=mint_total，供给闭合恒等）；
      sol-rows 净供应 = Σ(effective_balances 全部值)（含负，重放恒等=minted−burned），
               并与 reconcile_receipt.net_supply_raw 交叉相等。
    """
    fmt = sidecar.get("series_format")
    series = css["series"]
    fb_path = resolved.get("final_balances")
    if fb_path is None:
        raise SeriesProvenanceError("sidecar 未绑定 final_balances（同源终态快照），"
                                    "无法做末点对账")
    balances = {k: int(v) for k, v in
                json.loads(Path(fb_path).read_text(encoding="utf-8")).items()}
    if fmt == "evm-dict":
        spec = _load_camps_spec(resolved, fmt, "evm")
        total = sum(balances.values())
        zero_bal = balances.get(ZERO, 0)
        den = total if sidecar.get("denominator") == "mint_total_legacy" \
            else total - zero_bal
        burn_recon = {"burn_cum_pct": (zero_bal / den * 100) if den else 0.0}
    elif fmt == "sol-rows":
        spec = _load_camps_spec(resolved, fmt, "solana")
        den = sum(balances.values())
        rr = resolved.get("inputs.reconcile_receipt")
        receipt = json.loads(Path(rr).read_text(encoding="utf-8")) if rr else {}
        net_registered = receipt.get("net_supply_raw")
        if net_registered is not None and int(net_registered) != den:
            raise SeriesProvenanceError(
                f"终态快照合计 {den} ≠ reconcile_receipt.net_supply_raw "
                f"{net_registered}——快照与对账收据不是同一条数据链")
        burned = int(receipt.get("burned_raw", 0))
        burn_recon = {"锁仓/销毁": (burned / den * 100) if den else 0.0}
    else:
        raise SeriesProvenanceError(f"series_format {fmt!r} 不支持末点对账")
    if den <= 0:
        raise SeriesProvenanceError("终态快照派生分母 ≤ 0，数据链非法")

    residual_keys = {"散户"}
    stray = [c for c in series
             if c not in spec and c not in residual_keys
             and c not in BURN_EXEMPT_KEYS]
    if stray:
        raise SeriesProvenanceError(
            f"序列含 camps spec 之外的桶 {stray}——该序列不是 sidecar 绑定的"
            f"阵营 spec 产出的")
    failures, spec_sum = [], 0.0
    for camp, addrs in spec.items():
        if fmt == "sol-rows":
            recon = sum(balances.get(a, 0) for a in addrs
                        if balances.get(a, 0) > 0) / den * 100
        else:
            recon = sum(balances.get(a, 0) for a in addrs) / den * 100
        if camp in BURN_EXEMPT_KEYS:
            # spec 里显式配置的销毁类阵营（如 0xdead 地址）：其终点参与 burn 桶比对
            burn_recon[camp] = burn_recon.get(camp, 0.0) + recon
            continue
        spec_sum += recon
        if camp not in series:
            if recon > tol_pp:
                failures.append(f"spec 阵营「{camp}」重算 {recon:.4f}% 但序列无此桶")
            continue
        last = float(series[camp][-1])
        if abs(recon - last) > tol_pp:
            failures.append(f"「{camp}」末点 {last:.4f}% ≠ 重算 {recon:.4f}%"
                            f"（差 {abs(recon - last):.4f}pp）")
    if "散户" in series:
        resid_want = 100.0 - spec_sum
        resid_have = float(series["散户"][-1])
        if abs(resid_have - resid_want) > tol_pp:
            failures.append(f"散户残差末点 {resid_have:.4f}% ≠ 恒等式 "
                            f"100−Σspec={resid_want:.4f}%（差 "
                            f"{abs(resid_have - resid_want):.4f}pp）")
    for camp, recon in burn_recon.items():
        if camp in series:
            last = float(series[camp][-1])
            if abs(recon - last) > tol_pp:
                failures.append(f"burn 桶「{camp}」末点 {last:.4f}% ≠ 重算 "
                                f"{recon:.4f}%（差 {abs(recon - last):.4f}pp）")
    if failures:
        raise SeriesProvenanceError("末点对账失败：" + "；".join(failures))
    return {"denominator_raw": str(den), "spec_camps": len(spec),
            "tol_pp": tol_pp}
