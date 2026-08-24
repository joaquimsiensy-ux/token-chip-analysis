#!/usr/bin/env python3
"""F-007: series_format-specific stack semantics for closure and endpoint checks."""
from __future__ import annotations

import inspect
import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/lib"))

from camp_series_provenance import (  # noqa: E402
    SeriesProvenanceError,
    closure_mode_for,
    endpoint_reconcile,
    validate_series_payload,
)


PROJECT = "0x00000000000000000000000000000000000000aa"
DEAD = "0x000000000000000000000000000000000000dead"
RETAIL = "0x00000000000000000000000000000000000000bb"
ZERO = "0x0000000000000000000000000000000000000000"
SOL_PROJECT = "So11111111111111111111111111111111111111112"
SOL_RETAIL = "11111111111111111111111111111111"


def _write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _css(series: dict[str, list[float]]) -> dict:
    return {"dates": ["2026-08-24T00:00:00Z"], "series": series}


def _validate_bound(css: dict, series_format: str, denominator: str) -> None:
    """Use the pre-fix API only while capturing RED; require format once present."""
    kwargs = {"closure_mode": closure_mode_for(denominator)}
    if "series_format" in inspect.signature(validate_series_payload).parameters:
        kwargs["series_format"] = series_format
    validate_series_payload(css, **kwargs)


def _evm_fixture(tmp: Path, denominator: str, *, retail=5, lock=15):
    camps = tmp / "camps.json"
    balances = tmp / "balances_final.json"
    _write_json(camps, {"camps": {"项目方": [PROJECT], "锁仓/销毁": [DEAD]}})
    values = {PROJECT: 80, DEAD: lock, RETAIL: retail}
    if denominator == "current_net_supply":
        values[ZERO] = 10
    _write_json(balances, values)
    sidecar = {"series_format": "evm-dict", "denominator": denominator}
    resolved = {"camps_spec": camps, "final_balances": balances}
    return sidecar, resolved


def _expect_rejected(label: str, needle: str, action) -> None:
    try:
        action()
    except SeriesProvenanceError as exc:
        if needle not in str(exc):
            raise AssertionError(f"{label}: wrong rejection: {exc}") from exc
        return
    raise AssertionError(f"{label}: unexpectedly accepted")


def test_lit_legacy_endpoint() -> None:
    with tempfile.TemporaryDirectory() as raw:
        sidecar, resolved = _evm_fixture(Path(raw), "mint_total_legacy")
        css = _css({"项目方": [80.0], "锁仓/销毁": [15.0], "散户": [5.0]})
        endpoint_reconcile(sidecar, css, resolved)


def test_lit_net_closure() -> None:
    css = _css({
        "项目方": [80.0], "锁仓/销毁": [15.0], "散户": [5.0],
        "burn_cum_pct": [10.0],
    })
    _validate_bound(css, "evm-dict", "current_net_supply")
    with tempfile.TemporaryDirectory() as raw:
        sidecar, resolved = _evm_fixture(Path(raw), "current_net_supply")
        endpoint_reconcile(sidecar, css, resolved)


def test_evm_net_burn_and_dead_sink() -> None:
    css = _css({
        "项目方": [70.0], "锁仓/销毁": [20.0], "散户": [10.0],
        "burn_cum_pct": [30.0],
    })
    validate_series_payload(
        css, closure_mode=closure_mode_for("current_net_supply"),
        series_format="evm-dict")


def test_legacy_rejects_burn_cum_pct() -> None:
    css = _css({
        "项目方": [80.0], "锁仓/销毁": [15.0], "散户": [5.0],
        "burn_cum_pct": [10.0],
    })
    _expect_rejected(
        "legacy burn_cum_pct consistency gate", "mint_total_legacy",
        lambda: validate_series_payload(
            css, closure_mode=closure_mode_for("mint_total_legacy"),
            series_format="evm-dict"))


def test_retail_endpoint_tamper_still_rejected() -> None:
    with tempfile.TemporaryDirectory() as raw:
        sidecar, resolved = _evm_fixture(Path(raw), "mint_total_legacy")
        css = _css({"项目方": [80.0], "锁仓/销毁": [15.0], "散户": [8.0]})
        _expect_rejected(
            "retail endpoint tamper", "散户残差",
            lambda: endpoint_reconcile(sidecar, css, resolved))


def test_dead_sink_endpoint_tamper_still_rejected() -> None:
    with tempfile.TemporaryDirectory() as raw:
        sidecar, resolved = _evm_fixture(Path(raw), "mint_total_legacy")
        css = _css({"项目方": [80.0], "锁仓/销毁": [16.0], "散户": [5.0]})
        _expect_rejected(
            "dead-sink endpoint tamper", "burn 桶「锁仓/销毁」",
            lambda: endpoint_reconcile(sidecar, css, resolved))


def test_net_burn_cannot_rescue_stack_gap() -> None:
    css = _css({
        "项目方": [70.0], "锁仓/销毁": [20.0], "散户": [5.0],
        "burn_cum_pct": [5.0],
    })
    _expect_rejected(
        "burn_cum_pct stack-gap rescue", "不闭合",
        lambda: validate_series_payload(
            css, closure_mode=closure_mode_for("current_net_supply"),
            series_format="evm-dict"))


def test_illegal_denominator_still_rejected() -> None:
    _expect_rejected(
        "illegal denominator", "无闭合口径映射",
        lambda: closure_mode_for("floating_supply"))


def test_no_format_dual_behavior_unchanged() -> None:
    validate_series_payload(_css({
        "项目方": [40.0], "散户": [40.0], "锁仓/销毁": [20.0],
    }))
    validate_series_payload(_css({
        "项目方": [40.0], "散户": [60.0], "burn_cum_pct": [120.0],
    }))
    validate_series_payload(_css({
        "项目方": [55.0], "散户": [40.0], "burn_cum_pct": [5.0],
    }))
    _expect_rejected(
        "legacy closure_mode validation", "只认 dual/net/total",
        lambda: validate_series_payload(
            _css({"项目方": [40.0], "散户": [60.0]}),
            closure_mode="format-driven"))


def test_format_mapping_is_fixed() -> None:
    from camp_series_provenance import stack_exempt_for

    assert stack_exempt_for("evm-dict") == ("burn_cum_pct",)
    assert stack_exempt_for("sol-rows") == ("burn_cum_pct", "锁仓/销毁")
    assert stack_exempt_for("sol-anchor-rows") == ()
    _expect_rejected(
        "unsupported stack format", "无堆叠语义映射",
        lambda: stack_exempt_for("evm-entity-dict"))


def test_evm_dead_sink_is_stack_bounded() -> None:
    _expect_rejected(
        "EVM dead-sink stack range", "超出 100",
        lambda: validate_series_payload(
            _css({"锁仓/销毁": [101.0], "散户": [0.0]}),
            closure_mode="total", series_format="evm-dict"))


def test_solana_burn_disclosure_remains_exempt() -> None:
    css = _css({"项目方": [40.0], "散户": [60.0], "锁仓/销毁": [25.0]})
    validate_series_payload(css, closure_mode="net", series_format="sol-rows")

    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        camps = tmp / "camps.json"
        balances = tmp / "effective_balances.json"
        receipt = tmp / "reconcile.json"
        _write_json(camps, {"项目方": [SOL_PROJECT]})
        _write_json(balances, {SOL_PROJECT: 40, SOL_RETAIL: 60})
        _write_json(receipt, {"net_supply_raw": 100, "burned_raw": 25})
        endpoint_reconcile(
            {"series_format": "sol-rows", "denominator": "net_supply"}, css,
            {"camps_spec": camps, "final_balances": balances,
             "inputs.reconcile_receipt": receipt})


def test_sol_anchor_real_stack_closes() -> None:
    css = _css({"项目方": [40.0], "散户": [35.0], "锁仓/销毁": [25.0]})
    validate_series_payload(
        css, closure_mode="total", series_format="sol-anchor-rows")


def test_sol_anchor_false_oracle_rejected() -> None:
    css = _css({"项目方": [40.0], "散户": [60.0], "锁仓/销毁": [25.0]})
    _expect_rejected(
        "sol-anchor-rows false oracle", "实际堆叠键Σ=125.0000",
        lambda: validate_series_payload(
            css, closure_mode="total", series_format="sol-anchor-rows"))


def test_sol_anchor_rejects_burn_cum_pct() -> None:
    css = _css({
        "项目方": [40.0], "散户": [35.0], "锁仓/销毁": [25.0],
        "burn_cum_pct": [5.0],
    })
    _expect_rejected(
        "sol-anchor-rows burn_cum_pct consistency gate",
        "build_evolution 不输出该键",
        lambda: validate_series_payload(
            css, closure_mode="total", series_format="sol-anchor-rows"))


RED_CASES = [
    ("LIT legacy dead-sink endpoint", test_lit_legacy_endpoint),
    ("LIT net dead-sink closure", test_lit_net_closure),
]

ALL_CASES = RED_CASES + [
    ("EVM net burn plus dead-sink", test_evm_net_burn_and_dead_sink),
    ("legacy burn_cum_pct consistency gate", test_legacy_rejects_burn_cum_pct),
    ("retail endpoint tamper", test_retail_endpoint_tamper_still_rejected),
    ("dead-sink endpoint tamper", test_dead_sink_endpoint_tamper_still_rejected),
    ("burn cannot rescue stack gap", test_net_burn_cannot_rescue_stack_gap),
    ("illegal denominator", test_illegal_denominator_still_rejected),
    ("no-format dual compatibility", test_no_format_dual_behavior_unchanged),
    ("fixed format mapping", test_format_mapping_is_fixed),
    ("EVM dead-sink range", test_evm_dead_sink_is_stack_bounded),
    ("Solana burn disclosure", test_solana_burn_disclosure_remains_exempt),
    ("Solana anchor real stack", test_sol_anchor_real_stack_closes),
    ("Solana anchor false oracle", test_sol_anchor_false_oracle_rejected),
    ("Solana anchor burn_cum_pct consistency gate",
     test_sol_anchor_rejects_burn_cum_pct),
]


def main() -> int:
    cases = RED_CASES if "--red-only" in sys.argv[1:] else ALL_CASES
    failures = 0
    for label, case in cases:
        try:
            case()
        except Exception as exc:
            failures += 1
            print(f"FAIL: {label}: {type(exc).__name__}: {exc}")
        else:
            print(f"PASS: {label}")
    print(f"SUMMARY: {len(cases) - failures}/{len(cases)} PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
