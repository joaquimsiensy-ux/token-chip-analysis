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

burn 口径按 producer 的 series_format 分家（堆叠语义不由分母口径猜测）：
  - EVM `evm-dict`（scripts/evm/replay_pass2.py:84-86,101-106,139-145）：
    `锁仓/销毁` 是 camps spec 普通堆叠桶，两种分母都计入 known；仅 net 输出的
    `burn_cum_pct` 是堆叠外披露轨。legacy 不输出 `burn_cum_pct`/`_meta`。
  - Solana `sol-rows`（scripts/solana/replay_edges.py:648-657）：
    `锁仓/销毁` 是 minted−burned 净供应分母外的真烧毁披露桶，不参与堆叠。
  - Solana `sol-anchor-rows`（scripts/solana/build_evolution.py:177-183）：
    `锁仓/销毁` 写入 camp_raw、计入 known，散户补 TOT−known，全桶除以 TOT，
    因而无堆叠豁免；producer 不输出 `burn_cum_pct`，该键出现即拒。该辅助格式
    不接入正式编译链，但校验映射仍固定，调用者无权另传豁免集合。
  - 无 series_format 的手填路径保留历史 dual/net/total 双式行为，逐字兼容。
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
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "solana"))
from sqd_cache_identity import resolve_formal_cache  # noqa: E402

SIDECAR_SCHEMA = "camp-series-provenance/v1"
# 跨格式 burn 披露键全集；不可直接当堆叠豁免集。实际豁免只能由
# stack_exempt_for(series_format) 固定派生：EVM 依据 replay_pass2.py:84-86,101-106,
# 139-145 仅豁免 burn_cum_pct；sol-rows 依据 replay_edges.py:648-657 两键均豁免；
# sol-anchor-rows 依据 build_evolution.py:177-183 无豁免。
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
SOLANA_MINT_RE = re.compile(r"[1-9A-HJ-NP-Za-km-z]{32,44}")
class SeriesProvenanceError(ValueError):
    """sidecar 缺失/不匹配/序列数值面非法/末点对账失败（调用方按 exit 2 处理）。"""


def stack_exempt_for(series_format: str) -> tuple[str, ...]:
    """返回 producer 固定的堆叠外键；anchor 依据 build_evolution.py:177-183。"""
    if series_format == "evm-dict":
        return ("burn_cum_pct",)
    if series_format == "sol-rows":
        return BURN_EXEMPT_KEYS
    if series_format == "sol-anchor-rows":
        return ()
    raise SeriesProvenanceError(
        f"series_format {series_format!r} 无堆叠语义映射")


def _reject_constant(value: str):
    raise SeriesProvenanceError(f"JSON 非有限数值 {value} 不允许")


def _json_loads(value, label="JSON"):
    try:
        return json.loads(value, parse_constant=_reject_constant)
    except SeriesProvenanceError:
        raise
    except (json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise SeriesProvenanceError(f"{label} 非法: {exc}") from exc


def _validate_solana_mint(mint, label="mint"):
    if not isinstance(mint, str) or mint != mint.strip() \
            or SOLANA_MINT_RE.fullmatch(mint) is None:
        raise SeriesProvenanceError(
            f"{label} 必须是 strip 后非空、32~44 字符的 Solana base58 地址")
    return mint


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
                         final_balances_path=None, inputs=None, extra=None,
                         edge_source_binding=None) -> Path:
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
    if edge_source_binding is not None:
        doc["edge_source_binding"] = dict(edge_source_binding)
    if extra:
        doc["extra"] = dict(extra)
    out = sidecar_path_for(series_path)
    tmp = out.with_name(out.name + ".tmp")
    # F-C6：fsync 对齐仓内最强先例（receipt_kernel 的 flush+fsync+replace）——
    # sidecar 是来源链锚点件，掉电半写不可接受
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, out)
    return out


# ── consumer 侧 ──────────────────────────────────────────────────────


def _resolve_ref(ref: dict, label: str, search_dirs) -> Path:
    """按 basename 在 series 目录与其父目录（案根）两层内找实物并三验。

    basename 未命中时，登记路径兜底只接受案根内相对路径；sha256 仍是
    权威身份。符号链接拒收（与 F-08/批 B 同口径）。
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

    registered = str(ref["path"])
    rel = Path(registered)
    parts = registered.split("/")
    if rel.is_absolute() or any(part in {"", ".", ".."} for part in parts):
        raise SeriesProvenanceError(
            f"sidecar {label} 登记路径必须是案根内且不含空段/./.. 的相对路径: "
            f"{registered!r}")
    for base in search_dirs:
        base = Path(base)
        root = base.resolve()
        cursor = root
        for part in parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise SeriesProvenanceError(
                    f"sidecar {label} 登记路径含符号链接 {cursor}，拒收")
        cand = base / registered
        resolved_cand = cand.resolve()
        if resolved_cand != root and root not in resolved_cand.parents:
            raise SeriesProvenanceError(
                f"sidecar {label} 登记路径逃出案根 {base}: {registered!r}")
        if cand.is_file():
            if cand.stat().st_size != ref.get("size"):
                raise SeriesProvenanceError(
                    f"sidecar {label} size 不匹配（{cand}: 实测 "
                    f"{cand.stat().st_size} ≠ 登记 {ref.get('size')}）")
            if sha256_file(cand) != str(ref["sha256"]).lower():
                raise SeriesProvenanceError(f"sidecar {label} sha256 不匹配（{cand}）")
            return cand
    raise SeriesProvenanceError(
        f"sidecar {label}（{name}）在序列目录与案根两层内按文件名找不到，"
        f"按登记路径 {ref['path']!r} 解析亦未命中")


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
    sidecar = _json_loads(sc_path.read_text(encoding="utf-8"), "series sidecar")
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
    raw = _json_loads(series_path.read_text(encoding="utf-8"), "series payload")
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


def closure_mode_for(denominator: str) -> str:
    """F-C4：校验 sidecar denominator 并保留历史闭合模式标签。

    绑定路径的堆叠集合只由 stack_exempt_for(series_format) 决定：EVM 依据
    replay_pass2.py:84-86,101-106,139-145；sol-rows 依据 replay_edges.py:648-657；
    sol-anchor-rows 依据 build_evolution.py:177-183。
    返回值继续校验 denominator 合法性，并供无 format 手填路径保持既有行为。
    """
    if denominator in ("current_net_supply", "net_supply"):
        return "net"
    if denominator in ("mint_total_legacy", "config_total_supply"):
        return "total"
    raise SeriesProvenanceError(f"denominator {denominator!r} 无闭合口径映射")


def validate_series_payload(css: dict, *, tol_pp: float = CLOSURE_TOL_PP,
                            closure_mode: str = "dual", series_format=None):
    """state 形态 camp_share_series 的数值面硬校验（拒=raise SeriesProvenanceError）：

    ①桶名白名单=CAMP_ORDER_MODERN ∪ burn 豁免键（legacy 桶名/实体级自造桶名一律拒，
      新报告禁用；旧案重绘不经 compile_state）；
    ②全值有限（json 的 NaN/Infinity 字面量默认能解析进来，必须显式查）；
    ③堆叠桶值域 [0,100]；堆叠外披露桶仅验非负有限；豁免集合由 producer 格式
      固定：evm-dict 依据 replay_pass2.py:84-86,101-106,139-145 仅豁免
      burn_cum_pct；sol-rows 依据 replay_edges.py:648-657 豁免 BURN_EXEMPT_KEYS；
      sol-anchor-rows 依据 build_evolution.py:177-183 无豁免，调用者不能自定义；
    ④有 series_format 时只认实际堆叠键之和≈100；closure_mode 仍验合法，且
      evm-dict+mint_total_legacy 禁带 producer 从不输出的 burn_cum_pct。无 format
      时 closure_mode 的 dual/net/total 历史双式行为逐字保留。全桶全零点豁免。
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
            f"自造桶名新报告禁用）。存量案迁移口径见 scan-schemas.md §13"
            f"「存量迁移」：不重编译不受影响；重编译须先按案内证据把桶归入现代名"
            f"（映射是分析判断非机械替换）")
    stack_exempt = BURN_EXEMPT_KEYS if series_format is None \
        else stack_exempt_for(series_format)
    if series_format == "sol-anchor-rows" and "burn_cum_pct" in series:
        raise SeriesProvenanceError(
            "sol-anchor-rows 序列不得含 burn_cum_pct：build_evolution 不输出该键"
            "（scripts/solana/build_evolution.py:177-183）")
    if series_format == "evm-dict" and closure_mode == "total" \
            and "burn_cum_pct" in series:
        raise SeriesProvenanceError(
            "evm-dict + mint_total_legacy 序列不得含 burn_cum_pct："
            "replay_pass2 legacy producer 从不输出该键")
    n = len(dates)
    for camp, values in series.items():
        if not isinstance(values, list) or len(values) != n:
            raise SeriesProvenanceError(f"桶「{camp}」长度 {len(values) if isinstance(values, list) else '非列表'} ≠ dates {n}")
        is_exempt = camp in stack_exempt
        for i, v in enumerate(values):
            if isinstance(v, bool) or not isinstance(v, (int, float)) \
                    or v != v or v in (float("inf"), float("-inf")):
                raise SeriesProvenanceError(f"桶「{camp}」[{i}] 非有限数值: {v!r}")
            if v < 0:
                raise SeriesProvenanceError(f"桶「{camp}」[{i}] 为负: {v}")
            if not is_exempt and v > 100:
                raise SeriesProvenanceError(f"桶「{camp}」[{i}] 超出 100: {v}")
    if closure_mode not in ("dual", "net", "total"):
        raise SeriesProvenanceError(f"closure_mode 只认 dual/net/total，"
                                    f"收到 {closure_mode!r}")
    non_burn = [c for c in series if c not in BURN_EXEMPT_KEYS]
    burn = [c for c in series if c in BURN_EXEMPT_KEYS]
    for i in range(n):
        s_non = sum(series[c][i] for c in non_burn)
        s_all = s_non + sum(series[c][i] for c in burn)
        if s_all == 0:
            continue  # 供应尚未产生的点（producer 全零输出），豁免
        if series_format is not None:
            stack_keys = [c for c in series if c not in stack_exempt]
            s_stack = sum(series[c][i] for c in stack_keys)
            closed = abs(s_stack - 100.0) <= tol_pp
        elif closure_mode == "net":
            closed = abs(s_non - 100.0) <= tol_pp
        elif closure_mode == "total":
            closed = abs(s_all - 100.0) <= tol_pp
        else:
            closed = abs(s_non - 100.0) <= tol_pp or abs(s_all - 100.0) <= tol_pp
        if not closed:
            if series_format is not None:
                raise SeriesProvenanceError(
                    f"第 {i} 点（{dates[i]}）合计不闭合"
                    f"（series_format={series_format}, closure_mode={closure_mode}）："
                    f"实际堆叠键Σ={s_stack:.4f}，偏离 100 超过 {tol_pp}pp")
            raise SeriesProvenanceError(
                f"第 {i} 点（{dates[i]}）合计不闭合（closure_mode={closure_mode}）："
                f"非burn桶Σ={s_non:.4f}、全桶Σ={s_all:.4f}，"
                f"偏离 100 超过 {tol_pp}pp")
    prev = None
    for i, d in enumerate(dates):
        cur = parse_axis_utc(d, i)
        if prev is not None and cur <= prev:
            raise SeriesProvenanceError(
                f"日期轴非严格递增：dates[{i}]={d!r}（UTC {cur.isoformat()}）"
                f"不晚于前一点（UTC {prev.isoformat()}）——倒序/重复/时区换算倒挂都不许")
        prev = cur


# ── 登记面命中与末点对账（--series-source 模式）─────────────────────


SUPPLY_TRUTH_SCHEMAS = {
    "supply-truth-receipt/v3", "supply-truth-receipt/v4",
}
RECONCILE_SCHEMA = "solana-reconcile/v4"
LEGACY_RECONCILE_SCHEMAS = {"solana-reconcile/v2", "solana-reconcile/v3"}


def _slot(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SeriesProvenanceError(f"{label} 必须为非负整数 slot")
    return value


def _snapshot_cutoff(meta):
    target = meta.get("target") or {}
    if not isinstance(target, dict):
        raise SeriesProvenanceError("holders_snapshot_meta.target 必须为对象")
    return _slot(target.get("as_of_block"), "holders_snapshot_meta.target.as_of_block")


def registry_anchor_check(sidecar: dict, resolved: dict, series_path, *,
                          expected_chain=None, expected_mint=None,
                          expected_cutoff_slot=None,
                          verify_edge_physical_sha=False):
    """sidecar 的 inputs 必须命中案内已对账的登记面（把序列锚进案内数据链）。

    F-C3（消化轮）：登记面命中是**结构化校验**，不是"文件里含某个 sha 字符串"——
    修前的全文包含式实测被 46 字节任意 JSON（{"sha256": "..."}）伪造通过。修后：

    evm-dict：案内 supply_truth.json 必须在场且本身过合法性三验（真实生产者
      supply_truth_gate.py 的分链现役收据形态：Solana/legacy EVM v3、EVM formal v4，
      verdict==PASS、exit_code==0，参照 holder_distribution_scan.load_supply
      先例），且 sidecar 登记的 replay_stats sha256 必须命中收据的**特定字段位置**
      inputs.replay_stats.sha256（批 A 起哈希绑定的那一格，非任意位置）。
    sol-rows：sidecar 必须绑定 solana-reconcile/v4；chain/mint/cutoff 预期值必须
      由调用方案内 target 独立传入，绝不取收据自报值。收据输入三验、producer
      指纹、窗口包含关系与边摘要/行数对 cache meta 的关系均在这里重验。
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
        truth = _json_loads(st.read_text(encoding="utf-8"), "supply_truth.json")
        if not isinstance(truth, dict) \
                or truth.get("schema") not in SUPPLY_TRUTH_SCHEMAS:
            raise SeriesProvenanceError(
                "supply_truth.json 不是合法供给真值收据（schema 必须属于 "
                f"{sorted(SUPPLY_TRUTH_SCHEMAS)}）——任意 JSON 冒充登记面不算数")
        if str(truth.get("verdict", "")).upper() != "PASS" \
                or truth.get("exit_code") != 0:
            raise SeriesProvenanceError(
                "supply_truth.json 非 PASS/exit 0——供给真值闸未通过的案不得编译序列")
        # N-C3（消化轮 2）：target 三键=收据的案身份锚（真实生产者恒写
        # {chain, token, as_of_block}）。不验它，一份从别的案复制来的合法收据或
        # 凭空造的收据都能当登记面用。token 必须与案内采集链身份件
        # channels_preflight.json 的 token 一致（EVM replay 数据链必产、自身有
        # receipt 三验链）——找不到 preflight 即拒，不留条件式跳过（N-C1 教训）。
        target = truth.get("target")
        if not isinstance(target, dict) \
                or not str(target.get("chain") or "").strip() \
                or not str(target.get("token") or "").strip() \
                or isinstance(target.get("as_of_block"), bool) \
                or not isinstance(target.get("as_of_block"), int) \
                or target["as_of_block"] <= 0:
            raise SeriesProvenanceError(
                "supply_truth.json 缺合法 target 三键（chain/token/as_of_block）"
                "——没有案身份锚的收据不算登记面")
        if str(target.get("chain")).strip().lower() \
                != str(truth.get("chain") or "").strip().lower():
            raise SeriesProvenanceError(
                "supply_truth.json target.chain 与收据顶层 chain 不一致"
                "——真实生产者两处同源，撕裂即伪造/拼接")
        preflight = next((d / "channels_preflight.json" for d in dirs
                          if (d / "channels_preflight.json").is_file()), None)
        if preflight is None:
            raise SeriesProvenanceError(
                "案内找不到 channels_preflight.json——EVM 序列的采集链身份件缺席，"
                "target.token 无从对锚")
        preflight_token = str(_json_loads(
            preflight.read_text(encoding="utf-8"),
            "channels_preflight.json").get("token") or "").lower()
        if str(target.get("token")).lower() != preflight_token:
            raise SeriesProvenanceError(
                f"supply_truth.json target.token 与案内 channels_preflight.json "
                f"的 token 不一致——收据不是本案的（复制他案收据/凭空伪造）")
        bound = ((truth.get("inputs") or {}).get("replay_stats") or {})
        registered_sha = str(bound.get("sha256", "")).lower()
        if not registered_sha:
            raise SeriesProvenanceError(
                "supply_truth.json 缺 inputs.replay_stats.sha256 绑定"
                "——收据没有把 replay_stats 哈希绑定进来，登记面锚不成立")
        if str(stats_ref.get("sha256", "")).lower() != registered_sha:
            raise SeriesProvenanceError(
                "sidecar 登记的 replay_stats sha256 ≠ supply_truth.json 的 "
                "inputs.replay_stats.sha256——序列与供给真值闸不是同一条数据链")
        return st
    if fmt == "sol-rows":
        rr = resolved.get("inputs.reconcile_receipt")
        if rr is None:
            raise SeriesProvenanceError(
                "sol-rows sidecar 必须登记 inputs.reconcile_receipt"
                "（replay_edges reconcile 是阶段 2 硬关卡，先跑 reconcile 再跑 evolution）")
        receipt = _json_loads(Path(rr).read_text(encoding="utf-8"),
                              "reconcile_receipt")
        if isinstance(receipt, dict) and receipt.get("schema") in LEGACY_RECONCILE_SCHEMAS:
            raise SeriesProvenanceError(
                f"{receipt.get('schema')} 已归 LEGACY 并 fail-closed；"
                "重跑 replay_edges reconcile 重新生成 v4 收据")
        if not isinstance(receipt, dict) or receipt.get("schema") != RECONCILE_SCHEMA:
            raise SeriesProvenanceError(
                f"reconcile_receipt 不是合法对账收据（schema 必须是 "
                f"{RECONCILE_SCHEMA}）——重跑 replay_edges reconcile 重新生成 v4 收据")
        try:
            from solana_exact_validate import validate_reconcile_receipt_deep
            deep = validate_reconcile_receipt_deep(
                rr, case_root=Path(rr).parent.parent)
        except Exception as exc:
            raise SeriesProvenanceError(
                f"reconcile_receipt 独立深验器执行失败: {exc}") from exc
        if not deep["ok"]:
            raise SeriesProvenanceError(
                "reconcile_receipt 独立深验失败: " + "; ".join(deep["reasons"]))
        if receipt.get("gate_pass") is not True:
            raise SeriesProvenanceError("reconcile_receipt gate_pass 非 true，序列不入正式编译")
        for field in ("negative_balance_count", "snapshot_mismatch_count"):
            value = receipt.get(field)
            if isinstance(value, bool) or not isinstance(value, int) or value != 0:
                raise SeriesProvenanceError(
                    f"reconcile_receipt.{field} 必须是在场的精确 int 0")
        net_value = receipt.get("net_supply_raw")
        if isinstance(net_value, bool) or not isinstance(net_value, int) \
                or net_value < 0:
            raise SeriesProvenanceError(
                "reconcile_receipt.net_supply_raw 必须在场且为非负 int")
        if expected_chain is None or expected_mint is None or expected_cutoff_slot is None:
            raise SeriesProvenanceError(
                "sol-rows 身份校验缺案 target 的 expected_chain/expected_mint/"
                "expected_cutoff_slot；禁止用收据自报身份补空")
        _validate_solana_mint(expected_mint, "案 target mint")
        if receipt.get("chain") != expected_chain or expected_chain != "solana":
            raise SeriesProvenanceError(
                f"reconcile_receipt.chain={receipt.get('chain')!r} 与案 target.chain="
                f"{expected_chain!r} 不一致")
        # Solana base58 大小写敏感，严禁 lower 后比较。
        if receipt.get("mint") != expected_mint:
            raise SeriesProvenanceError(
                "reconcile_receipt.mint 与案 target mint 不一致（Solana base58 大小写敏感）")
        cutoff = _slot(expected_cutoff_slot, "案 target cutoff")
        window = receipt.get("collection_window") or {}
        frm = _slot(window.get("from_slot"), "collection_window.from_slot")
        to = _slot(window.get("to_slot"), "collection_window.to_slot")
        if frm > to:
            raise SeriesProvenanceError("collection_window.from_slot 大于 to_slot")
        extrema = receipt.get("edge_extrema") or {}
        first = extrema.get("first") or {}
        last = extrema.get("last") or {}
        fs = _slot(first.get("slot"), "edge_extrema.first.slot")
        ls = _slot(last.get("slot"), "edge_extrema.last.slot")
        # ts 仅为人读时间参考的记录字段；身份与排序校验只认 slot。
        _slot(first.get("ts"), "edge_extrema.first.ts")
        _slot(last.get("ts"), "edge_extrema.last.ts")
        if fs > ls or fs < frm or ls > to:
            raise SeriesProvenanceError(
                "edge_extrema 未按 slot 有序包含于 collection_window")
        if to > cutoff:
            raise SeriesProvenanceError(
                f"collection_window.to_slot={to} 超过案 target cutoff={cutoff}")
        edge_count = receipt.get("edge_count")
        digest = receipt.get("edge_digest")
        if isinstance(edge_count, bool) or not isinstance(edge_count, int) or edge_count <= 0:
            raise SeriesProvenanceError("reconcile_receipt.edge_count 必须为正整数")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise SeriesProvenanceError("reconcile_receipt.edge_digest 必须为小写 sha256")

        producer = receipt.get("producer") or {}
        producer_rel = "scripts/solana/replay_edges.py"
        producer_path = Path(__file__).resolve().parents[2] / producer_rel
        if producer.get("path") != producer_rel \
                or producer.get("sha256") != sha256_file(producer_path):
            raise SeriesProvenanceError(
                "reconcile_receipt producer path/sha256 与当前 replay_edges.py 不一致")

        receipt_dirs = [Path(rr).parent, Path(rr).parent.parent]
        inputs = receipt.get("inputs") or {}
        meta_path = _resolve_ref(inputs.get("soltx_meta"),
                                 "reconcile.inputs.soltx_meta", receipt_dirs)
        owners_path = _resolve_ref(inputs.get("holders_owners"),
                                   "reconcile.inputs.holders_owners", receipt_dirs)
        snapshot_path = _resolve_ref(inputs.get("holders_snapshot_meta"),
                                     "reconcile.inputs.holders_snapshot_meta", receipt_dirs)
        cache_meta = _json_loads(meta_path.read_text(encoding="utf-8"),
                                 "soltx meta")
        try:
            edge_path, resolver_meta_path, _cache_kind, _gid, resolver_binding = \
                resolve_formal_cache(expected_mint, Path(rr).parent.parent)
        except ValueError as exc:
            raise SeriesProvenanceError(
                "reconcile 绑定的 soltx meta schema/mint/producer/contract 或边文件"
                f"身份未通过正式 resolver: {exc}"
            ) from exc
        if resolver_meta_path.resolve() != meta_path.resolve():
            raise SeriesProvenanceError(
                "reconcile.inputs.soltx_meta 不是 resolver 当前选择的正式 meta")
        receipt_binding = receipt.get("edge_source_binding")
        if receipt_binding != resolver_binding:
            raise SeriesProvenanceError(
                "reconcile_receipt.edge_source_binding 与 resolver 当前边源不全等")
        side_binding = sidecar.get("edge_source_binding")
        if side_binding != receipt_binding:
            raise SeriesProvenanceError(
                "sidecar.edge_source_binding 与 exact reconcile 收据不全等")
        if cache_meta.get("from_slot") != frm \
                or cache_meta.get("finalized_upper_slot") != to:
            raise SeriesProvenanceError(
                "reconcile collection_window 与 soltx meta 采集窗口撕裂")
        if cache_meta.get("edge_logical_sha256") != digest \
                or cache_meta.get("edge_rows") != edge_count:
            raise SeriesProvenanceError(
                "reconcile edge_digest/edge_count 与 collector 绑定的 soltx meta 不一致")
        edge_ref = inputs.get("soltx_edges") or {}
        edge_size = edge_ref.get("size")
        edge_sha = edge_ref.get("sha256")
        if edge_path.is_symlink():
            raise SeriesProvenanceError(
                f"Solana 边文件是符号链接，拒收: {edge_path.name}")
        if not edge_path.is_file() or edge_path.stat().st_size <= 0:
            raise SeriesProvenanceError(
                f"Solana 边文件缺失或为空: {edge_path.name}")
        if isinstance(edge_size, bool) or not isinstance(edge_size, int) \
                or edge_size <= 0 or edge_path.stat().st_size != edge_size:
            raise SeriesProvenanceError(
                "Solana 边文件实物 size 与 reconcile.inputs.soltx_edges 不一致")
        if not isinstance(edge_sha, str) \
                or re.fullmatch(r"[0-9a-f]{64}", edge_sha) is None:
            raise SeriesProvenanceError(
                "reconcile.inputs.soltx_edges.sha256 必须为小写 sha256")
        if verify_edge_physical_sha and sha256_file(edge_path) != edge_sha:
            raise SeriesProvenanceError(
                "Solana 边文件物理 sha256 与 reconcile.inputs.soltx_edges 登记不一致")
        owners_obj = _json_loads(owners_path.read_text(encoding="utf-8"),
                                 "holders_owners.json")
        if not isinstance(owners_obj, dict):
            raise SeriesProvenanceError("holders_owners.json 顶层必须为对象")
        snapshot = _json_loads(snapshot_path.read_text(encoding="utf-8"),
                               "holders_snapshot_meta.json")
        snap_target = snapshot.get("target") or {}
        if snapshot.get("schema") != "solana-holder-snapshot-v2" \
                or snapshot.get("mint") != expected_mint \
                or snap_target.get("chain") != expected_chain \
                or snap_target.get("token") != expected_mint:
            raise SeriesProvenanceError(
                "holders_snapshot_meta schema/mint/target 与案 target 不一致")
        snap_cutoff = _snapshot_cutoff(snapshot)
        if snap_cutoff != cutoff or to > snap_cutoff:
            raise SeriesProvenanceError(
                "reconcile window 与 holders snapshot/案 target cutoff 不一致")
        owner_ref = ((snapshot.get("outputs") or {}).get("holders_owners") or {})
        receipt_owner_ref = inputs.get("holders_owners") or {}
        if (owner_ref.get("size"), owner_ref.get("sha256")) != (
                receipt_owner_ref.get("size"), receipt_owner_ref.get("sha256")):
            raise SeriesProvenanceError(
                "holders_snapshot_meta.outputs.holders_owners 与 reconcile 输入撕裂")
        # owners_path 已由 _resolve_ref 完成存在/size/sha 三验；变量保留用于明确
        # 表达 meta→owners 的同一份实物关系，避免未来退化成只比 JSON 引用。
        if owners_path.stat().st_size != owner_ref.get("size"):
            raise SeriesProvenanceError("holders owners 实物与 snapshot meta 不一致")
        return rr
    raise SeriesProvenanceError(f"series_format {fmt!r} 无登记面锚，不入正式编译链")


def _load_camps_spec(resolved: dict, series_format: str, chain_family: str):
    from camp_spec import validate_camp_spec
    spec_path = resolved.get("camps_spec")
    if spec_path is None:
        raise SeriesProvenanceError("sidecar 未绑定 camps_spec，无法做末点对账")
    obj = _json_loads(Path(spec_path).read_text(encoding="utf-8"), "camps spec")
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
                _json_loads(Path(fb_path).read_text(encoding="utf-8"),
                            "final_balances").items()}
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
        receipt = _json_loads(Path(rr).read_text(encoding="utf-8"),
                              "reconcile_receipt") if rr else {}
        net_registered = receipt.get("net_supply_raw")
        if isinstance(net_registered, bool) or not isinstance(net_registered, int) \
                or net_registered < 0:
            raise SeriesProvenanceError(
                "reconcile_receipt.net_supply_raw 必须在场且为非负 int")
        if net_registered != den:
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
            # EVM replay_pass2.py:84-86,101-106 的 camps stack 两种分母都包含
            # 「锁仓/销毁」；Solana replay_edges.py:648-657 则是堆叠外烧毁披露。
            if fmt == "evm-dict":
                spec_sum += recon
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
