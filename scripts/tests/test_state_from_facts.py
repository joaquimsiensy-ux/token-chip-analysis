#!/usr/bin/env python3
"""D-05: analysis-state has one compiler and cannot drift from facts membership."""

import importlib.util
from pathlib import Path


HERE = Path(__file__).resolve().parent
TARGET = HERE.parent / "report" / "state_from_facts.py"
spec = importlib.util.spec_from_file_location("state_compiler", TARGET)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def main():
    facts = {
        "token": {"symbol": "TT", "decimals": 2, "total_supply_raw": "10000"},
        "entities": {"e1": {"label": "大庄#1", "addresses": ["0xabc"],
                              "current_raw": "2500", "peak_raw": "4000"}},
    }
    source = {
        "schema": "analysis-state-source/v1",
        "token": {"chain": "arbitrum", "data_cutoff": "2026-08-04T00:00:00Z",
                  "skill_version": "6.13.0"},
        "entity_annotations": {"e1": {"type": "single", "status": "holding"}},
        "address_balances": {"0xabc": "25"},
        "vault_addresses": [],
        "camp_share_series": {"dates": ["2026-08-04"], "series": {"大庄": [25.0]}},
        "provenance": {"skill_commit": "fixture", "data_sources": ["snapshot"]},
    }
    state = mod.compile_state(facts, source)
    group = state["whale_groups"][0]
    assert group["entity_id"] == "e1" and group["addresses"] == ["0xabc"]
    assert group["current_share_pct"] == 25.0 and group["peak_share_pct"] == 40.0
    assert state["token"]["total_supply"] == "100"

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
