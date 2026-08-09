#!/usr/bin/env python3
"""supply_truth_gate 离线契约测试：形态①保持、形态②回退与 fail-closed。"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/lib"))
sys.path.insert(0, str(ROOT / "scripts/report"))
import supply_truth_gate as gate  # noqa: E402
import shared_release_receipt as shared  # noqa: E402

FAILS = []
ZERO = "0x0000000000000000000000000000000000000000"
DEAD = "0x000000000000000000000000000000000000dead"
TOKEN = "0x" + "9" * 40
APU_MINT = 420690000000000000000000000000
APU_DEAD = 82800853653911207346039942180


def check(name, cond):
    if not cond:
        FAILS.append(name)
        print(f"FAIL  {name}")
    else:
        print(f"ok    {name}")


class FakePool:
    """严格离线 RPC pool；记录 primary call 与 fallback call_many。"""

    def __init__(self, supply, zero=0, dead=0, fail_many_index=None):
        self.values = [supply, zero, dead]
        self.fail_many_index = fail_many_index
        self.calls = []
        self.many_calls = []

    def call(self, method, params):
        self.calls.append((method, params))
        return {"ok": True, "result": hex(self.values[0])}

    def call_many(self, calls, progress=True):
        self.many_calls.append(calls)
        out = []
        for index, value in enumerate(self.values):
            if index == self.fail_many_index:
                out.append({"ok": False, "error": "offline injected RPC failure"})
            else:
                out.append({"ok": True, "result": hex(value)})
        return out


@contextmanager
def chdir(path):
    previous = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def split_stats(mint=APU_MINT, burn=APU_DEAD, zero=0, dead=APU_DEAD):
    return {
        "mint_total_wei": str(mint),
        "burn_total_wei": str(burn),
        "sum_balances_wei": str(mint),
        "zero_event_inflow_wei": str(zero),
        "dead_event_inflow_wei": str(dead),
        "dead_event_outflow_wei": "0",
        "dead_sink_net_wei": str(dead),
    }


def run_evm(stats, pool, *, tolerance=10):
    with tempfile.TemporaryDirectory(prefix="supply-truth-test-", dir="/private/tmp") as td:
        root = Path(td)
        (root / "stats.json").write_text(json.dumps(stats), encoding="utf-8")
        out = root / "supply_truth.json"
        with chdir(root), patch.object(gate, "attested_rpc_pool", return_value=pool):
            rc = gate.main([
                "--chain", "eth", "--token", TOKEN, "--as-of-block", "123",
                "--replay-stats", "stats.json", "--rpc", "offline://mock",
                "--tolerance-bps", str(tolerance), "--out", str(out),
            ])
        receipt_path = out if out.exists() else sorted(root.glob("supply_truth.error.*.json"))[-1]
        return rc, json.loads(receipt_path.read_text(encoding="utf-8"))


def fallback(*args):
    fn = getattr(gate, "decide_sink_fallback", None)
    return fn(*args) if fn is not None else ("MISSING", None)


def test_primary_decide_and_parser():
    e18 = 10 ** 18
    verdict, diff, bps = gate.decide(1_000_000 * e18, 1_000_000 * e18)
    check("primary exact-equal PASS", verdict == "PASS" and diff == 0 and bps == 0)
    verdict, diff, bps = gate.decide(1_000_000_000 * e18, 203_500_000 * e18)
    check("primary GNT silent-migration FAIL", verdict == "FAIL" and diff > 0 and bps > 10000)
    base = 1_000_000 * e18
    check("primary tolerance 9bps PASS", gate.decide(base + base * 9 // 10000, base)[0] == "PASS")
    check("primary tolerance 11bps FAIL", gate.decide(base + base * 11 // 10000, base)[0] == "FAIL")
    check("primary negative-diff FAIL", gate.decide(base - base * 11 // 10000, base)[0] == "FAIL")
    check("primary both-zero PASS", gate.decide(0, 0) == ("PASS", 0, None))
    check("primary replay>0/onchain=0 FAIL", gate.decide(5 * e18, 0)[0] == "FAIL")

    check("parse wei fields", gate.parse_replay_stats(
        {"mint_total_wei": "1000", "burn_total_wei": 200}) == (1000, 200))
    check("parse raw fields", gate.parse_replay_stats(
        {"mint_total_raw": 500, "burn_total_raw": "50"}) == (500, 50))
    check("parse plain fields", gate.parse_replay_stats({"mint_total": 42}) == (42, 0))
    try:
        gate.parse_replay_stats({"foo": 1})
        check("parse missing fields raises", False)
    except KeyError:
        check("parse missing fields raises", True)


def test_sink_fallback_pure_cases():
    # APU 真实反例。
    check("APU fallback pure PASS", fallback(
        APU_MINT, APU_DEAD, APU_MINT, 0, APU_DEAD, 0, APU_DEAD
    ) == ("PASS", "dead_sink"))

    e18 = 10 ** 18
    # GNT：C1 必须继续拦截，sink mock 无法洗白。
    check("GNT fallback C1 FAIL", fallback(
        1_000_000_000 * e18, 0, 203_500_000 * e18, 0, 0, 0, 0
    ) == ("FAIL", None))
    # 混合形态：mint != onchain，维持 FAIL。
    check("mixed burn forms FAIL", fallback(1000, 300, 800, 0, 300, 0, 300)
          == ("FAIL", None))
    check("dead sink differs by 1 wei FAIL", fallback(1000, 200, 1000, 0, 200, 0, 199)
          == ("FAIL", None))
    # 合计可补偿，但逐地址错位必须失败。
    check("cross-address compensation FAIL", fallback(1000, 300, 1000, 100, 200, 200, 100)
          == ("FAIL", None))
    check("None component fail-closed", fallback(None, 0, 0, 0, 0, 0, 0)
          == ("FAIL", None))


def test_apu_main_and_receipt():
    pool = FakePool(APU_MINT, 0, APU_DEAD)
    rc, receipt = run_evm(split_stats(), pool)
    check("APU main PASS", rc == 0 and receipt.get("verdict") == "PASS")
    check("APU receipt v3", receipt.get("schema") == "supply-truth-receipt/v3")
    check("APU receipt fallback semantics", receipt.get("burn_form") == "dead_sink"
          and receipt.get("decision_rule") == "sink_fallback_form2"
          and receipt.get("primary_verdict") == "FAIL")
    recon = receipt.get("sink_reconciliation") or {}
    check("APU sink reconciliation exact strings", recon == {
        "zero": {"replay_raw": "0", "onchain_raw": "0"},
        "dead": {"replay_raw": str(APU_DEAD), "onchain_raw": str(APU_DEAD)},
    })
    check("fallback uses one call_many of three at frozen block",
          len(pool.many_calls) == 1 and len(pool.many_calls[0]) == 3
          and all(call[1][-1] == hex(123) for call in pool.many_calls[0]))


def test_fail_closed_main_branches():
    # 旧 stats 缺拆分字段：不触发回退，保留 primary FAIL。
    legacy_pool = FakePool(APU_MINT, 0, APU_DEAD)
    rc, legacy = run_evm({"mint_total_wei": str(APU_MINT),
                           "burn_total_wei": str(APU_DEAD)}, legacy_pool)
    check("legacy stats remain FAIL", rc == 2 and legacy.get("verdict") == "FAIL"
          and legacy.get("primary_verdict") == "FAIL"
          and legacy.get("decision_rule") == "primary_form1"
          and not legacy_pool.many_calls)

    # 主判定 PASS：形态①字段和值保持，禁止多余 fallback RPC。
    primary_pool = FakePool(1000)
    rc, primary = run_evm(split_stats(mint=1000, burn=0, zero=0, dead=0), primary_pool)
    check("primary form1 receipt unchanged values", rc == 0
          and primary.get("replay_net") == "1000"
          and primary.get("mint_total") == "1000"
          and primary.get("burn_total") == "0"
          and primary.get("decision_rule") == "primary_form1"
          and primary.get("primary_verdict") == "PASS"
          and primary.get("burn_form") is None
          and not primary_pool.many_calls)

    # fallback 的三个观测任一失败都是检测自身失败 exit 1。
    broken_pool = FakePool(APU_MINT, 0, APU_DEAD, fail_many_index=1)
    rc, broken = run_evm(split_stats(), broken_pool)
    check("partial fallback RPC failure is ERROR", rc == 1
          and broken.get("verdict") == "ERROR" and broken.get("exit_code") == 1)


def test_solana_never_falls_back():
    with tempfile.TemporaryDirectory(prefix="supply-truth-sol-", dir="/private/tmp") as td:
        root = Path(td)
        (root / "stats.json").write_text(json.dumps(split_stats()), encoding="utf-8")
        bundle = {"snapshot": {"slot": 123}, "supply": {"amount": "100", "slot": 123}}
        (root / "bundle.json").write_text(json.dumps(bundle), encoding="utf-8")
        out = root / "supply_truth.json"
        with chdir(root), \
                patch.object(gate, "validate_observation_bundle", return_value=None), \
                patch.object(gate, "assert_declared_slot", return_value=None), \
                patch.object(gate, "attested_rpc_pool", side_effect=AssertionError("Solana used EVM RPC")):
            rc = gate.main([
                "--chain", "solana", "--mint", "So11111111111111111111111111111111111111112",
                "--as-of-block", "123", "--min-context-slot", "123",
                "--observation-bundle", "bundle.json", "--replay-stats", "stats.json",
                "--out", str(out),
            ])
        receipt = json.loads(out.read_text(encoding="utf-8"))
    check("Solana fallback disabled", rc == 2 and receipt.get("verdict") == "FAIL"
          and receipt.get("decision_rule") == "primary_form1")


def test_legacy_v2_fixture_rejected():
    """显式 legacy 负例：v3 校验器必须拒收 v2，不做隐式迁移。"""
    with tempfile.TemporaryDirectory(prefix="supply-truth-v2-", dir="/private/tmp") as td:
        root = Path(td)
        fixture = root / "fixture.json"
        fixture.write_text("{}", encoding="utf-8")

        def digest(path):
            return hashlib.sha256(Path(path).read_bytes()).hexdigest()

        target = {"chain": "eth", "token": TOKEN, "as_of_block": 123}
        receipt = {
            # legacy 负例：此处是 scripts/ 下唯一获准保留的 v2 字符串。
            "schema": "supply-truth-receipt/v2",
            "target": target,
            "producer": {"path": "scripts/lib/supply_truth_gate.py",
                         "sha256": digest(ROOT / "scripts/lib/supply_truth_gate.py")},
            "mode": "formal",
            "inputs": {"fixture": {"path": str(fixture), "size": fixture.stat().st_size,
                                    "sha256": digest(fixture)}},
            "gate": "supply_truth", "replay_net": "100",
            "onchain_total_supply": "100", "diff": "0",
            "verdict": "PASS", "exit_code": 0,
        }
        receipt_path = root / "legacy_supply_truth.json"
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        item = {"status": "PASS", "exit_code": 0,
                "receipt": {"path": receipt_path.name, "sha256": digest(receipt_path)}}
        try:
            shared.validate_reconciliation_check(root, "supply_truth", item, target, "evm")
            rejected = False
        except ValueError as exc:
            rejected = "unknown schema" in str(exc)
    check("legacy v2 fixture explicitly rejected", rejected)


def main():
    test_primary_decide_and_parser()
    test_sink_fallback_pure_cases()
    test_apu_main_and_receipt()
    test_fail_closed_main_branches()
    test_solana_never_falls_back()
    test_legacy_v2_fixture_rejected()
    print("=" * 56)
    if FAILS:
        print(f"{len(FAILS)} 项失败: {FAILS}")
        return 1
    print("supply_truth_gate 形态①/②离线契约测试全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
