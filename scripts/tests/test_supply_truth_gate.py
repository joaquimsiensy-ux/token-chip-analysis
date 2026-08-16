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
from endpoint_identity import endpoint_fingerprint  # noqa: E402
from evm_observation import build_evm_observation_bundle  # noqa: E402

FAILS = []
ZERO = "0x0000000000000000000000000000000000000000"
DEAD = "0x000000000000000000000000000000000000dead"
TOKEN = "0x" + "9" * 40
APU_MINT = 420690000000000000000000000000
APU_DEAD = 82800853653911207346039942180
BLOCK_HASH = "0x" + "1" * 64
PARENT_HASH = "0x" + "2" * 64
RUNTIME_CODE = "0x6001600055"


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


def write_evm_bundle(root, *, token=TOKEN, chain="eth", as_of=123,
                     total=APU_MINT, zero=0, dead=APU_DEAD):
    """落一份通过工单 A 公共 validator 的 EVM 观测实物。"""
    endpoint = "https://rpc.example.test"
    block = {
        "number": hex(as_of), "hash": BLOCK_HASH,
        "parentHash": PARENT_HASH, "timestamp": hex(1_700_000_000),
    }
    selector = {"blockHash": BLOCK_HASH, "requireCanonical": True}
    balance = lambda address: (  # noqa: E731
        "0x70a08231" + "0" * 24 + address.removeprefix("0x").lower())
    word = lambda value: f"0x{value:064x}"  # noqa: E731
    chain_id = {"eth": 1, "bsc": 56, "base": 8453}[chain]
    transcript = [
        {"seq": 0, "method": "eth_chainId", "params": [], "result": chain_id},
        {"seq": 1, "method": "eth_getBlockByNumber",
         "params": [hex(as_of), False], "result": block},
        {"seq": 2, "method": "eth_blockNumber", "params": [],
         "result": hex(as_of + 12)},
        {"seq": 3, "method": "eth_call",
         "params": [{"to": token, "data": "0x18160ddd"}, selector],
         "result": word(total)},
        {"seq": 4, "method": "eth_call",
         "params": [{"to": token, "data": balance(ZERO)}, selector],
         "result": word(zero)},
        {"seq": 5, "method": "eth_call",
         "params": [{"to": token, "data": balance(DEAD)}, selector],
         "result": word(dead)},
        {"seq": 6, "method": "eth_getCode", "params": [token, selector],
         "result": RUNTIME_CODE},
        {"seq": 7, "method": "eth_getBlockByNumber",
         "params": [hex(as_of), False], "result": block},
    ]
    transcript_path = root / "evm_observation_transcript.json"
    transcript_path.write_text(json.dumps(transcript), encoding="utf-8")
    core = {
        "attestation": {
            "expected_chain_id": chain_id, "observed_chain_id": chain_id,
            "endpoint": endpoint_fingerprint(endpoint),
        },
        "anchor": {
            "number": as_of, "block_hash": BLOCK_HASH,
            "parent_hash": PARENT_HASH, "timestamp": 1_700_000_000,
            "recheck_block_hash": BLOCK_HASH, "tip_block": as_of + 12,
            "confirmations": 12,
        },
        "supply": {
            "total_supply_raw": str(total), "zero_balance_raw": str(zero),
            "dead_balance_raw": str(dead),
            "block_binding": "eip1898-block-hash",
        },
        "code": {"runtime_code_sha256": hashlib.sha256(
            bytes.fromhex(RUNTIME_CODE[2:])).hexdigest()},
    }
    target = {"chain": chain, "token": token, "as_of_block": as_of}
    bundle = build_evm_observation_bundle(
        core, transcript_path, target, "scripts/evm/observe_supply.py",
        input_base=root)
    bundle_path = root / "evm_observation_bundle.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    return bundle_path


def run_evm(stats, pool, *, tolerance=10, with_bundle=True, bundle_token=TOKEN,
            bundle_as_of=123, exploration=False):
    with tempfile.TemporaryDirectory(prefix="supply-truth-test-", dir="/private/tmp") as td:
        root = Path(td)
        (root / "stats.json").write_text(json.dumps(stats), encoding="utf-8")
        bundle = write_evm_bundle(
            root, token=bundle_token, as_of=bundle_as_of,
            total=pool.values[0], zero=pool.values[1], dead=pool.values[2]) \
            if with_bundle else None
        out = root / "supply_truth.json"
        argv = [
            "--chain", "eth", "--token", TOKEN, "--as-of-block", "123",
            "--replay-stats", "stats.json", "--rpc", "offline://mock",
            "--tolerance-bps", str(tolerance), "--out", str(out),
        ]
        if bundle is not None:
            argv.extend(["--observation-bundle", str(bundle)])
        if exploration:
            argv.append("--exploration")
        with chdir(root), patch.object(gate, "attested_rpc_pool", return_value=pool):
            rc = gate.main(argv)
        candidates = [out] if out.exists() else sorted(root.glob("supply_truth.error.*.json"))
        receipt = (json.loads(candidates[-1].read_text(encoding="utf-8"))
                   if candidates else None)
        return rc, receipt


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
    check("APU EVM formal receipt v4", receipt.get("schema") == "supply-truth-receipt/v4")
    check("APU receipt fallback semantics", receipt.get("burn_form") == "dead_sink"
          and receipt.get("decision_rule") == "sink_fallback_form2"
          and receipt.get("primary_verdict") == "FAIL")
    recon = receipt.get("sink_reconciliation") or {}
    check("APU sink reconciliation exact strings", recon == {
        "zero": {"replay_raw": "0", "onchain_raw": "0"},
        "dead": {"replay_raw": str(APU_DEAD), "onchain_raw": str(APU_DEAD)},
    })
    check("formal fallback uses bundle and zero RPC",
          pool.calls == [] and pool.many_calls == [])


def test_evm_formal_bundle_contract_and_exploration_regression():
    missing_pool = FakePool(1000)
    rc, missing = run_evm(
        split_stats(mint=1000, burn=0, zero=0, dead=0), missing_pool,
        with_bundle=False)
    check("EVM formal missing observation bundle rejected",
          rc == 1 and missing is None)

    mismatch_pool = FakePool(1000)
    rc, mismatch = run_evm(
        split_stats(mint=1000, burn=0, zero=0, dead=0), mismatch_pool,
        bundle_token="0x" + "8" * 40)
    check("EVM formal bundle token mismatch rejected",
          rc == 1 and mismatch is None)

    block_pool = FakePool(1000)
    rc, block_mismatch = run_evm(
        split_stats(mint=1000, burn=0, zero=0, dead=0), block_pool,
        bundle_as_of=124)
    check("EVM formal declared as_of mismatch rejected",
          rc == 1 and block_mismatch.get("verdict") == "ERROR")

    formal_pool = FakePool(1000)
    rc, formal = run_evm(
        split_stats(mint=1000, burn=0, zero=0, dead=0), formal_pool)
    check("EVM formal main path zero RPC", rc == 0
          and formal_pool.calls == [] and formal_pool.many_calls == [])
    check("EVM formal bundle binding and semantics", formal.get("schema")
          == "supply-truth-receipt/v4"
          and (formal.get("inputs") or {}).get("observation_bundle")
          and formal.get("observation_bundle")
          and formal.get("supply_observation_semantics")
          == "frozen-block eth_call via evm-observation-bundle (EIP-1898 block-hash binding)")

    exploration_pool = FakePool(1000)
    rc, exploration = run_evm(
        split_stats(mint=1000, burn=0, zero=0, dead=0), exploration_pool,
        with_bundle=False, exploration=True)
    check("EVM exploration retains v3 live RPC behavior", rc == 0
          and exploration.get("schema") == "supply-truth-receipt/v3"
          and len(exploration_pool.calls) == 1)


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
    rc, broken = run_evm(
        split_stats(), broken_pool, with_bundle=False, exploration=True)
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
    test_evm_formal_bundle_contract_and_exploration_regression()
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
