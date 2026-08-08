#!/usr/bin/env python3
"""A2 分层抽查计划器——对账四查“时间抽查”的锚点选取（纯随机 → 分层矩阵+强制覆盖）。

痛点定位：旧流程时间抽查是纯随机锚点，容易全抽在平静期（转账稀疏、余额不动），
抽了等于没抽。本脚本按「时间三段（早/中/晚）× 余额档（大/中/小户）」分层随机抽
"地址-日"锚点，再叠加四类强制覆盖点（全史最大单笔 / 最大单日净变动 / 数据源交界块
附近 / 门槛 ±10% 边缘地址），每点附预期日终余额与浏览器核对 URL，人工照单核对。

输入自适应（列名嗅探，见共享模块 anchor_selection）：
  - v2 parquet 目录（run_*/logs.parquet + blocks.parquet，HyperSync v2 原始 hex）
  - v1 7列 CSV（block,ts,tx,from,to,value|value_raw,uniqueId；ts ISO）
  - GME 变体 CSV（block,tx,log_index,from,to,value,timestamp；unix 秒）
  - 单 parquet 文件（列名同上述 CSV 任一变体）
  ⚠ Solana soltx-*.jsonl.gz 不支持（Solana 案是混合重建、无全量 merged，锚点抽查
    走 solana/anchor_sampler.py 通道）；value 超 127bit 的超大值币硬退（同 replay_duck）。

纯离线：只读输入文件做 DuckDB 聚合，不打任何外网；大文件靠 DuckDB 列式+mem-limit。

用法:
  python3 anchor_plan.py --input <transfers.csv|merged.parquet|v2目录> \
      --chain bsc --token 0x4fa7... --total-supply 1000000000 --decimals 18 \
      [--threshold-pct 1.0] [--boundary-blocks 111305341,111314259] \
      [--per-cell 1] [--edge-max 5] [--seed 42] [--mem-limit 6GB] --out-dir plan_out

输出：out-dir/anchor_plan.json（结构化）+ anchor_plan.md（人工核对清单）。
（来源：A2 时间抽查工程件，2026-07-22；QUQ v2 1.03 亿行实测通过）"""
import argparse
import datetime
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from anchor_selection import generate_anchor_selection, input_identity as compute_input_identity
from artifact_quarantine import quarantine_current, quarantine_run_id
from receipt_kernel import (RawBytes, build_envelope, finalize_envelope,
                            publish_overwrite, publish_txn)

PLAN_SCHEMA = "anchor-plan/v2"
RECEIPT_SCHEMA = "anchor-plan-receipt/v2"

def _validate_probe_blocks(plan, final_block):
    for family in ("matrix_points", "forced_points"):
        for index, point in enumerate(plan.get(family) or []):
            for key in ("day_end_block", "block"):
                value = point.get(key)
                if value is None:
                    continue
                if (isinstance(value, bool) or not isinstance(value, int)
                        or value < 0 or value > final_block):
                    raise ValueError(
                        f"{family}[{index}].{key}={value!r} outside final_block={final_block}")

def main():
    ap = argparse.ArgumentParser(description="A2 分层抽查计划器（时间三段×余额档+强制覆盖点）")
    ap.add_argument("--input", required=True, help="merged 转账数据：csv / parquet / v2 目录")
    ap.add_argument("--chain", required=True, help="bsc/eth/base/arbitrum/polygon/...")
    ap.add_argument("--token", required=True, help="代币合约地址（正式 plan target 身份）")
    ap.add_argument("--final-block", type=int, required=True,
                    help="冻结截止块；全部探测块必须不高于此块")
    ap.add_argument("--total-supply", type=float, required=True, help="总供应（human 单位）")
    ap.add_argument("--decimals", type=int, required=True)
    ap.add_argument("--threshold-pct", type=float, default=1.0,
                    help="大户门槛（占总供应%%，默认 1.0；中户=其 1/10，小户再往下）")
    ap.add_argument("--min-pct", type=float, default=0.0001,
                    help="小户下限（占总供应%%，默认 0.0001，滤尘埃）")
    ap.add_argument("--boundary-blocks", default=None,
                    help="数据源交界块号，逗号分隔（拿不到就不传，跳过该类强制点）")
    ap.add_argument("--per-cell", type=int, default=1, help="每格抽点数（默认 1，共 3×3 格）")
    ap.add_argument("--edge-max", type=int, default=5, help="门槛±10%% 边缘地址最多列几个")
    ap.add_argument("--seed", type=int, default=42, help="随机种子（同种子可复现）")
    ap.add_argument("--mem-limit", default="6GB")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()

    if a.final_block < 0:
        ap.error("--final-block must be non-negative")
    a.chain = a.chain.lower()
    a.token = a.token.lower()
    out_dir = Path(a.out_dir).expanduser().resolve()
    plan_path = out_dir / "anchor_plan.json"
    receipt_path = out_dir / "anchor_plan.receipt.json"
    run_id = quarantine_run_id()
    try:
        # Receipt is the commit marker: remove it first so partial quarantine
        # cannot leave a prior plan consumable as the current run's output.
        stale_receipt = quarantine_current(receipt_path, run_id)
        stale_plan = quarantine_current(plan_path, run_id)
    except Exception as exc:
        print(f"[fatal] prior anchor plan/receipt quarantine failed: {exc}", file=sys.stderr)
        return 1
    if stale_receipt is not None:
        print(f"[stale] previous anchor receipt moved to {stale_receipt}", file=sys.stderr)
    if stale_plan is not None:
        print(f"[stale] previous anchor plan moved to {stale_plan}", file=sys.stderr)
    try:
        input_identity, input_files = compute_input_identity(a.input)
    except Exception as exc:
        ap.error(f"input identity failed: {exc}")

    os.makedirs(out_dir, exist_ok=True)
    a.out_dir = str(out_dir)
    bounds = [int(x) for x in a.boundary_blocks.split(",")] if a.boundary_blocks else []
    try:
        selection = generate_anchor_selection(
            input_path=a.input, chain=a.chain, token=a.token,
            total_supply=a.total_supply, decimals=a.decimals,
            threshold_pct=a.threshold_pct, min_pct=a.min_pct,
            boundary_blocks=bounds, per_cell=a.per_cell, edge_max=a.edge_max,
            seed=a.seed, mem_limit=a.mem_limit, threads=a.threads,
            progress=lambda message: print(message, flush=True))
    except Exception as exc:
        print(f"[fatal] anchor selection failed: {exc}", file=sys.stderr)
        return 2

    print("[5/5] 写出计划…", flush=True)
    generated_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    plan = {"schema": PLAN_SCHEMA, "generated_at": generated_at,
            "target": {"chain": a.chain, "token": a.token,
                       "as_of_block": a.final_block},
            "input": input_identity, "chain": a.chain, "token": a.token,
            "final_block": a.final_block,
            "total_supply": a.total_supply, "decimals": a.decimals,
            "threshold_pct": a.threshold_pct, "min_pct": a.min_pct,
            "per_cell": a.per_cell, "edge_max": a.edge_max, "seed": a.seed,
            **selection}
    matrix = plan["matrix_points"]
    forced = plan["forced_points"]
    d0, d1 = plan["date_range"]
    cut1, cut2 = plan["time_cuts"]
    try:
        _validate_probe_blocks(plan, a.final_block)
    except ValueError as exc:
        print(f"[fatal] anchor plan probe boundary invalid: {exc}", file=sys.stderr)
        return 2

    jp = plan_path
    rp = receipt_path
    ip = Path(a.out_dir) / "anchor_plan.input.json"
    input_manifest = {"schema": "anchor-plan-input/v1", "input": input_identity,
                      "files": input_files}
    try:
        publish_overwrite(ip, input_manifest)
        envelope = build_envelope(
            RECEIPT_SCHEMA, plan["target"], Path(__file__).resolve(), "formal",
            inputs={"input_manifest": ip})
        plan["producer"] = envelope["producer"]
        plan["input_manifest"] = envelope["inputs"]["input_manifest"]
        plan_bytes = (json.dumps(plan, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        receipt = finalize_envelope(
            envelope, "PASS", 0, plan_schema=PLAN_SCHEMA,
            generated_at=generated_at, input_identity=input_identity,
            probe_count=len(matrix) + len(forced),
            output={"path": str(jp.resolve()), "size": len(plan_bytes),
                    "sha256": hashlib.sha256(plan_bytes).hexdigest()})
    except Exception as exc:
        print(f"[fatal] anchor plan receipt build failed: {exc}", file=sys.stderr)
        return 1

    md = [f"# 分层抽查计划（{a.chain} · {a.token or '?'}）",
          f"数据 {d0} → {d1}；时段切点 {cut1} / {cut2}；门槛 {a.threshold_pct}%；seed={a.seed}",
          "", "## 一、分层矩阵抽点（时间三段 × 余额档）",
          "| 格 | 地址 | 日期 | 日终块 | 预期余额 | 占供应% | 最终% | 核对 URL |",
          "|---|---|---|---|---|---|---|---|"]
    for p in matrix:
        md.append(f"| {p['kind']} | `{p['addr']}` | {p['day']} | {p['day_end_block']} "
                  f"| {p['expected_balance_human']:,} | {p['expected_pct']} | {p['final_pct']} "
                  f"| {p['check_urls'].get('addr', '')} |")
    md += ["", "## 二、强制覆盖点", ""]
    for p in forced:
        md.append(f"### {p['kind']}")
        for k in ("addr", "tx", "from", "to", "day", "block", "day_end_block"):
            if p.get(k) is not None:
                md.append(f"- {k}: `{p[k]}`")
        for k in ("expected_balance_human", "expected_pct", "expected_value_human",
                  "day_delta_human"):
            if p.get(k) is not None:
                md.append(f"- {k}: {p[k]:,}" if isinstance(p[k], (int, float))
                          else f"- {k}: {p[k]}")
        md.append(f"- 说明: {p['note']}")
        for uk, uv in p["check_urls"].items():
            md.append(f"- URL({uk}): {uv}")
        md.append("")
    md += ["## 核对方法",
           "- 地址-日锚点：EVM 用浏览器 tokencheck-tool（token+地址+上表『日终块』查历史余额），"
           "或在地址页翻该日交易核流水；tx 锚点：打开 tx 页核金额与双方。",
           "- 任何一点对不上 → 按对账三查流程回溯该地址全史重放，不许只改单点。"]
    mp = Path(a.out_dir) / "anchor_plan.md"
    try:
        publish_overwrite(mp, RawBytes(("\n".join(md) + "\n").encode("utf-8")))
        publish_txn(jp, plan, rp, receipt)
    except Exception as exc:
        print(f"[fatal] anchor plan publication failed: {exc}", file=sys.stderr)
        return 1
    print(f"[done] 矩阵点 {len(matrix)} + 强制点 {len(forced)} → {jp} / {mp} / {rp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
