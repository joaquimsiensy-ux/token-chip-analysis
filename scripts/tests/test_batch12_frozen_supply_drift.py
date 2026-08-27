#!/usr/bin/env python3
"""Batch 12：distribution scanner 冻结态 supply 漂移容差与静态态零变化。"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from test_distribution_gate import make_case, run_scan, smooth_balances, write_json


ARC_ONCHAIN = 999_982_737_505_447
ARC_NET = 999_982_737_531_582
ARC_DIFF = ARC_NET - ARC_ONCHAIN


def exact_balances(total: int, count: int = 120) -> dict[str, int]:
    quotient, remainder = divmod(total, count)
    return {f"owner-{index:03d}": quotient + (index < remainder)
            for index in range(count)}


def set_supply(root: Path, *, chain: str, onchain: int, net: int,
               diff: int | None, tolerance_bps: int | None,
               verdict: str = "PASS", exit_code: int = 0) -> None:
    path = root / "supply_truth.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    receipt.update({
        "chain": chain,
        "onchain_total_supply": str(onchain),
        "replay_net": str(net),
        "mint_total": str(onchain),
        "verdict": verdict,
        "exit_code": exit_code,
    })
    if diff is None:
        receipt.pop("diff", None)
    else:
        receipt["diff"] = str(diff)
    if tolerance_bps is None:
        receipt.pop("tolerance_bps", None)
    else:
        receipt["tolerance_bps"] = tolerance_bps
    write_json(path, receipt)


def scan_fixture(*, chain: str, onchain: int, net: int, diff: int | None,
                 tolerance_bps: int | None, verdict: str = "PASS",
                 exit_code: int = 0):
    td = tempfile.TemporaryDirectory()
    root = Path(td.name) / "case"
    root.mkdir()
    make_case(root, exact_balances(onchain))
    set_supply(root, chain=chain, onchain=onchain, net=net, diff=diff,
               tolerance_bps=tolerance_bps, verdict=verdict, exit_code=exit_code)
    result = run_scan(root)
    output_path = root / "distribution_scan.json"
    output = json.loads(output_path.read_text(encoding="utf-8")) \
        if output_path.is_file() else {}
    return td, root, result, output


def check(name: str, condition: bool, details: str = "") -> bool:
    print(("ok   " if condition else "FAIL ") + f"[{name}]"
          + (f" {details}" if details and not condition else ""))
    return condition


def main() -> int:
    ok = True

    td, _, result, output = scan_fixture(
        chain="solana", onchain=ARC_ONCHAIN, net=ARC_NET,
        diff=ARC_DIFF, tolerance_bps=10)
    with td:
        denominators = output.get("denominators") or {}
        ok &= check(
            "R1/G1 ARC 同形 PASS 收据容差内冻结态漂移放行并留痕",
            result.returncode == 0
            and output.get("schema") == "distribution-scan/v2"
            and output.get("exit_code") == 0
            and denominators.get("net_supply_raw") == str(ARC_NET)
            and denominators.get("supply_drift_raw") == str(ARC_DIFF),
            result.stdout + result.stderr + json.dumps(denominators, ensure_ascii=False))

    td, _, result, _ = scan_fixture(
        chain="solana", onchain=ARC_ONCHAIN, net=ARC_NET,
        diff=ARC_DIFF + 1, tolerance_bps=10)
    with td:
        ok &= check("N1 diff 与 net-onchain 不等仍拒", result.returncode == 2
                    and "供给真值 onchain/net 非法" in result.stderr,
                    result.stdout + result.stderr)

    huge_onchain = 10 ** 30 + 1
    boundary = huge_onchain * 10 // 10_000
    td, _, result, _ = scan_fixture(
        chain="solana", onchain=huge_onchain, net=huge_onchain + boundary + 1,
        diff=boundary + 1, tolerance_bps=10)
    with td:
        ok &= check("N2 超 tolerance_bps 一 raw 仍拒且计算不经浮点", result.returncode == 2
                    and "供给真值 onchain/net 非法" in result.stderr,
                    result.stdout + result.stderr)

    for verdict, exit_code, label in (("FAIL", 0, "非 PASS"), ("PASS", 2, "exit 非 0")):
        td, _, result, _ = scan_fixture(
            chain="solana", onchain=ARC_ONCHAIN, net=ARC_NET,
            diff=ARC_DIFF, tolerance_bps=10, verdict=verdict, exit_code=exit_code)
        with td:
            ok &= check(f"N3 {label} 收据仍拒", result.returncode == 2
                        and "supply_truth 非 PASS/exit 0" in result.stderr,
                        result.stdout + result.stderr)

    static = smooth_balances()
    static_total = sum(static.values())
    for chain, anchor_source in (("bsc", "supply_truth_mint"),
                                 ("solana", "solana_onchain")):
        with tempfile.TemporaryDirectory() as raw_td:
            root = Path(raw_td) / chain
            root.mkdir()
            make_case(root, static)
            set_supply(root, chain=chain, onchain=static_total, net=static_total,
                       diff=0, tolerance_bps=10)
            result = run_scan(root)
            output = json.loads((root / "distribution_scan.json").read_text(encoding="utf-8"))
            denominators = output.get("denominators") or {}
            ok &= check(
                f"N4 {chain} 静态态输出语义零变化",
                result.returncode == 0
                and denominators.get("mint_total_raw") == str(static_total)
                and denominators.get("net_supply_raw") == str(static_total)
                and "supply_drift_raw" not in denominators
                and ((output.get("input_binding") or {}).get("mint_closure_anchor") or {}).get(
                    "source") == anchor_source,
                result.stdout + result.stderr + json.dumps(denominators, ensure_ascii=False))

    print("PASS: batch12 frozen supply drift contract" if ok
          else "FAIL: batch12 frozen supply drift contract")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
