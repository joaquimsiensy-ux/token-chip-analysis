#!/usr/bin/env python3
"""Compile analysis-state.json from facts.json plus non-duplicative state inputs.

The source file carries only fields facts.json cannot own: analysis cutoff/version,
per-address snapshot balances, entity type/status annotations, vaults and camp series.
Entity ids, labels, membership and current/peak amounts always come from facts.json.

Usage:
  python3 state_from_facts.py --facts facts.json --source state_source.json \
    --out analysis-state.json
"""

from __future__ import annotations

import argparse
import json
import os
from decimal import Decimal
from pathlib import Path


def load_object(path: Path, label: str) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
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
    provenance = source.get("provenance") or {}
    if not provenance.get("skill_commit") or not provenance.get("data_sources"):
        raise ValueError("source.provenance 缺 skill_commit/data_sources")

    total_human = Decimal(total_raw) / (Decimal(10) ** decimals)
    token = dict(token_source)
    token.update({"symbol": token_facts.get("symbol"),
                  "total_supply": format(total_human, "f")})
    return {
        "token": token,
        "whale_groups": whale_groups,
        "vault_addresses": source.get("vault_addresses") or [],
        "addresses": address_rows,
        "camp_share_series": series,
        "provenance": {"schema_version": "2", **provenance},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="facts.json -> analysis-state.json compiler")
    ap.add_argument("--facts", type=Path, required=True)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    try:
        result = compile_state(load_object(args.facts, "facts"),
                               load_object(args.source, "source"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
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
