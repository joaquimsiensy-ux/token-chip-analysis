#!/usr/bin/env python3
"""D-05: analysis-state has one compiler and cannot drift from facts membership."""

import copy
import importlib.util
import json
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
TARGET = HERE.parent / "report" / "state_from_facts.py"
spec = importlib.util.spec_from_file_location("state_compiler", TARGET)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

GATE_TARGET = HERE.parent / "report" / "audit_release_gate.py"
gate_spec = importlib.util.spec_from_file_location("audit_release_gate", GATE_TARGET)
gate_mod = importlib.util.module_from_spec(gate_spec)
gate_spec.loader.exec_module(gate_mod)


def check_compiled_state(state):
    """Write the real compiler result and run the formal cross-partition gate."""
    with tempfile.TemporaryDirectory() as tmp:
        case_dir = Path(tmp)
        (case_dir / "analysis-state.json").write_text(
            json.dumps(state, ensure_ascii=False), encoding="utf-8")
        data = {}
        errors = []
        result = gate_mod.check_formal_case_chain(case_dir, data, errors)
    return result, errors


def main():
    facts = {
        "token": {"symbol": "TT", "decimals": 2, "total_supply_raw": "10000"},
        "entities": {"e1": {"label": "大庄#1", "addresses": ["0xabc"],
                              "current_raw": "2500", "peak_raw": "4000"}},
    }
    source = {
        "schema": "analysis-state-source/v1",
        "token": {"chain": "bsc", "data_cutoff": "2026-08-04T00:00:00Z",
                  "skill_version": "6.13.0"},
        "entity_annotations": {"e1": {"type": "single", "status": "holding"}},
        "address_balances": {"0xabc": "25"},
        "vault_addresses": [],
        # F-04 起 compile_state 无条件校验数值面（白名单/值域/同点闭合/日期轴），
        # fixture 须为闭合形态：大庄+散户=100
        "camp_share_series": {"dates": ["2026-08-04"],
                              "series": {"大庄": [25.0], "散户": [75.0]}},
        "provenance": {"skill_commit": "fixture", "data_sources": ["snapshot"]},
    }
    state = mod.compile_state(facts, source)
    group = state["whale_groups"][0]
    assert group["entity_id"] == "e1" and group["addresses"] == ["0xabc"]
    assert group["current_share_pct"] == 25.0 and group["peak_share_pct"] == 40.0
    assert state["token"]["total_supply"] == "100"
    assert state["chain"] and state["chain"] == state["token"]["chain"] == "bsc"

    chain, errors = check_compiled_state(state)
    assert chain == "bsc" and errors == []
    print("PASS: real compile_state output passes formal chain gate")

    missing_chain = copy.deepcopy(state)
    del missing_chain["chain"]
    chain, errors = check_compiled_state(missing_chain)
    assert chain == "bsc"
    assert errors and any(
        "analysis-state.json.chain" in error and "跨分区 chain 声明缺失" in error
        for error in errors
    )
    print("PASS: missing top-level chain is rejected by formal chain gate")

    contradictory_chain = copy.deepcopy(state)
    contradictory_chain["chain"] = "eth"
    chain, errors = check_compiled_state(contradictory_chain)
    assert chain is None
    assert errors and any("chain 声明矛盾" in error for error in errors)
    print("PASS: contradictory top-level/token chain is rejected by formal chain gate")

    bad = dict(source)
    bad["address_balances"] = {"0xdef": "25"}
    try:
        mod.compile_state(facts, bad)
    except ValueError as exc:
        assert "address_balances" in str(exc)
    else:
        raise AssertionError("facts/state member drift was accepted")
    print("PASS: D-05 state_from_facts compiler owns membership and raw-derived shares")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
