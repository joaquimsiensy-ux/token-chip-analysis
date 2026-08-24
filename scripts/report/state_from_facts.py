#!/usr/bin/env python3
"""Compile analysis-state.json from facts.json plus non-duplicative state inputs.

The source file carries only fields facts.json cannot own: analysis cutoff/version,
per-address snapshot balances, entity type/status annotations, vaults and camp series.
Entity ids, labels, membership and current/peak amounts always come from facts.json.

用法（唯一生成入口，report-template.md「analysis-state 编译」节同步）：
  python3 state_from_facts.py --facts facts.json --source state_source.json \
    --out analysis-state.json \
    [--series-source data/camp_series.json]

camp_share_series 的两道闸（F-04，2026-08-13；F-C1 消化轮把第二道焊成必经）：
  ①无条件数值面（camp_series_provenance.validate_series_payload）：桶名白名单
    =standard_charts.CAMP_ORDER_MODERN、有限数、堆叠桶值域 [0,100]、同点合计闭合、
    日期轴 UTC 严格递增——绑定路径的堆叠集合由 series_format 按 producer 固定
    （EVM replay_pass2.py:84-86,101-106,139-145；Solana replay_edges.py:648-657），
    手填 series 无 format 时保留历史 dual 行为；
  ②来源绑定＝formal 必经（F-C1）：默认（formal）编译 **--series-source 必填**，
    缺席直接 BLOCK exit 2——闸不许挂在可选参数上（v6.11.0 B-03 元规则第八层）。
    --series-source 指向四族重放 producer 落盘的原生序列文件，必须带
    `<序列名>.provenance.json` sidecar——验输出 sha＋输入实物三验＋登记面命中
    （supply_truth/reconcile）＋按 sidecar 格式的实际堆叠单式闭合＋camps spec 末点
    对账；state 的 series 由本编译器从原生文件转换生成（source 里可省略
    camp_share_series；写了就必须与转换结果完全一致，防双源分叉）。产物
    provenance 落 series_binding="producer-sidecar"＋camp_series_sidecar 绑定块，
    发布闸（audit_release_gate new-analysis）复验。
  探索豁免：显式 --exploration 才可不带 --series-source，产物 provenance 落
    series_binding="exploration-unbound" 非正式标记——带该标记的 state 进
    new-analysis 发布闸必拒（非正式产物不得进正式发布）。source.provenance 不得
    预置 series_binding/camp_series_sidecar（只能由编译器生成，预置即拒）。
    旧案无 sidecar → 不经 compile_state 的重绘不受影响。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from camp_series_provenance import (_json_loads, closure_mode_for, endpoint_reconcile,
                                    load_series_with_sidecar,
                                    registry_anchor_check, series_to_state_form,
                                    validate_series_payload)


def load_object(path: Path, label: str) -> dict:
    value = _json_loads(path.read_text(encoding="utf-8"), label)
    if not isinstance(value, dict):
        raise ValueError(f"{label} 顶层必须是对象")
    return value


def percent(raw, total):
    return float((Decimal(raw) * Decimal(100) / Decimal(total)).quantize(Decimal("0.00000001")))


def compile_state(facts: dict, source: dict) -> dict:
    if source.get("schema") != "analysis-state-source/v1":
        raise ValueError("source schema 必须为 analysis-state-source/v1")
    token_facts = facts.get("token") or {}
    entities = facts.get("entities")
    total_raw = token_facts.get("total_supply_raw")
    decimals = token_facts.get("decimals")
    if not isinstance(entities, dict) or not entities:
        raise ValueError("facts.entities 必须为非空对象")
    if not isinstance(total_raw, str) or not total_raw.isdigit() or int(total_raw) <= 0:
        raise ValueError("facts.token.total_supply_raw 必须为正整数字符串")
    if isinstance(decimals, bool) or not isinstance(decimals, int) or decimals < 0:
        raise ValueError("facts.token.decimals 必须为非负整数")

    token_source = source.get("token") or {}
    for key in ("chain", "data_cutoff", "skill_version"):
        if not token_source.get(key):
            raise ValueError(f"source.token 缺 {key}")
    annotations = source.get("entity_annotations") or {}
    balances = source.get("address_balances") or {}
    expected_addresses = []
    whale_groups = []
    address_rows = []
    for entity_id, entity in entities.items():
        addresses = entity.get("addresses") or []
        if not isinstance(addresses, list) or not addresses:
            raise ValueError(f"facts entity {entity_id} addresses 为空")
        ann = annotations.get(entity_id)
        if not isinstance(ann, dict) or not ann.get("type") or not ann.get("status"):
            raise ValueError(f"source.entity_annotations 缺 {entity_id} type/status")
        current_raw = entity.get("current_raw")
        peak_raw = entity.get("peak_raw", current_raw)
        if not all(isinstance(x, str) and x.isdigit() for x in (current_raw, peak_raw)):
            raise ValueError(f"facts entity {entity_id} current_raw/peak_raw 非整数字符串")
        whale_groups.append({
            "entity_id": entity_id, "label": entity.get("label") or entity_id,
            "type": ann["type"], "status": ann["status"], "addresses": addresses,
            "current_share_pct": percent(current_raw, total_raw),
            "peak_share_pct": percent(peak_raw, total_raw),
        })
        for address in addresses:
            expected_addresses.append(address)
            if address not in balances:
                raise ValueError(f"source.address_balances 缺 facts 成员 {address}")
            address_rows.append({
                "address": address, "chain": token_source["chain"],
                "role": entity.get("label") or entity_id,
                "balance_est": balances[address], "group": entity_id,
            })
    if set(balances) != set(expected_addresses):
        raise ValueError("source.address_balances 与 facts 成员集合不一致")

    series = source.get("camp_share_series")
    if not isinstance(series, dict) or not isinstance(series.get("dates"), list) \
            or not isinstance(series.get("series"), dict):
        raise ValueError("source.camp_share_series 结构非法")
    n_dates = len(series["dates"])
    if any(not isinstance(values, list) or len(values) != n_dates
           for values in series["series"].values()):
        raise ValueError("camp_share_series 序列长度与 dates 不一致")
    # F-04 无条件数值面：白名单/有限数/值域/同点闭合/日期轴（与 --series-source 无关，
    # 手填 series 注入 -899/999 之类的自报数字在这里就被拒）
    validate_series_payload(series)
    provenance = source.get("provenance") or {}
    if not provenance.get("skill_commit") or not provenance.get("data_sources"):
        raise ValueError("source.provenance 缺 skill_commit/data_sources")

    total_human = Decimal(total_raw) / (Decimal(10) ** decimals)
    token = dict(token_source)
    token.update({"symbol": token_facts.get("symbol"),
                  "total_supply": format(total_human, "f")})
    return {
        # 顶层 chain 与 token.chain 同值：audit_release_gate 跨分区 target 检查
        # 读 state 顶层 chain（缺失即 WARN 拒发布），编译产物必须自带（NES 首案，2026-08-16）
        "chain": token.get("chain"),
        "token": token,
        "whale_groups": whale_groups,
        "vault_addresses": source.get("vault_addresses") or [],
        "addresses": address_rows,
        "camp_share_series": series,
        "provenance": {"schema_version": "2", **provenance},
    }


def bind_series_source(source: dict, series_source: Path) -> dict:
    """--series-source：producer 原生序列（带 sidecar）→ 验证链 → 注入 source。

    验证链＝输出 sha 绑定＋输入实物三验＋登记面命中＋末点对账（全在
    camp_series_provenance，失败=SeriesProvenanceError→exit 2）。state 的 series
    由转换器生成；source 手填了 camp_share_series 时必须与生成结果完全一致。
    """
    sidecar, raw, resolved = load_series_with_sidecar(series_source)
    compiled = series_to_state_form(raw, sidecar["series_format"])
    # F-C4/F-007：denominator 仍须映射以验证合法性；堆叠集合按 producer 的
    # series_format 固定（EVM replay_pass2.py:84-86,101-106,139-145；Solana
    # replay_edges.py:648-657）。无 sidecar 的手填路径仍保留历史 dual 行为。
    validate_series_payload(compiled,
                            closure_mode=closure_mode_for(sidecar["denominator"]),
                            series_format=sidecar["series_format"])
    target = source.get("token") or {}
    if target.get("chain") == "solana" and "data_cutoff_slot" not in target:
        raise ValueError(
            "source.token 缺 data_cutoff_slot；存量案补填方法见 "
            "scan-schemas.md 存量迁移段")
    registry_anchor_check(
        sidecar, resolved, series_source,
        expected_chain=target.get("chain"),
        expected_mint=target.get("mint"),
        expected_cutoff_slot=target.get("data_cutoff_slot"))
    endpoint_reconcile(sidecar, compiled, resolved)
    manual = source.get("camp_share_series")
    if manual is not None and manual != compiled:
        raise ValueError(
            "source.camp_share_series 与 --series-source 转换结果不一致——"
            "series 只有一个事实源（producer 序列文件），source 里要么省略该字段"
            "要么逐点相等")
    bound = dict(source)
    bound["camp_share_series"] = compiled
    provenance = dict(bound.get("provenance") or {})
    provenance["series_binding"] = "producer-sidecar"
    provenance["camp_series_sidecar"] = {
        "producer": sidecar.get("producer"),
        "series_file": sidecar.get("series_file"),
        "series_sha256": sidecar.get("series_sha256"),
        # 消化轮 2（F-C1 终关）：发布闸要用同一转换器把案内序列实物重转换一遍
        # 与 state 的 camp_share_series 逐点比对——format 必须随绑定块落盘
        "series_format": sidecar.get("series_format"),
    }
    bound["provenance"] = provenance
    return bound


def main(argv=None):
    ap = argparse.ArgumentParser(description="facts.json -> analysis-state.json compiler")
    ap.add_argument("--facts", type=Path, required=True)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--series-source", type=Path,
                    help="四族重放 producer 落盘的原生序列文件（须带 .provenance.json "
                         "sidecar）。formal（默认）路径必填，缺席 BLOCK exit 2")
    ap.add_argument("--exploration", action="store_true",
                    help="显式声明探索编译，才允许不带 --series-source；产物 provenance "
                         "落 series_binding=exploration-unbound 非正式标记，"
                         "new-analysis 发布闸必拒")
    args = ap.parse_args(argv)
    try:
        source = load_object(args.source, "source")
        # F-C1：绑定标记只能由本编译器生成——source 预置即拒（防手编 source 伪装
        # formal 绑定绕过来源链）
        preset = source.get("provenance") or {}
        if "series_binding" in preset or "camp_series_sidecar" in preset:
            raise ValueError(
                "source.provenance 不得预置 series_binding/camp_series_sidecar"
                "——绑定标记只能由编译器按验证结果生成")
        if args.series_source:
            source = bind_series_source(source, args.series_source)
        elif args.exploration:
            source = dict(source)
            provenance = dict(source.get("provenance") or {})
            provenance["series_binding"] = "exploration-unbound"
            source["provenance"] = provenance
            print("[exploration] series 无来源绑定——产物带非正式标记，"
                  "不得进正式发布链")
        else:
            raise ValueError(
                "formal 编译必须 --series-source（camp_share_series 来源绑定是"
                "必经之路，闸不挂可选参数）；探索运行显式加 --exploration")
        result = compile_state(load_object(args.facts, "facts"), source)
    except (OSError, ValueError, json.JSONDecodeError, RecursionError) as exc:
        print(f"BLOCK: {exc}")
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.out.with_name(args.out.name + ".tmp")
    tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, args.out)
    print(f"PASS: compiled {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
