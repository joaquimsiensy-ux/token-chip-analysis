#!/usr/bin/env python3
"""B1-B negative/positive tests for the sole chain-attested EVM RPC session."""
from __future__ import annotations

import asyncio
import csv
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/lib"))

import net


def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_with_backend(pool, backend, method="eth_call"):
    with mock.patch.object(net, "_request_json", side_effect=backend):
        return pool.call(method, [{"to": "0x" + "1" * 40}, "latest"])


def test_wrong_chain_zero_business():
    calls = []

    async def backend(client, bucket, method, url, *, json_body=None, attempts=6):
        calls.append((url, json_body["method"]))
        if json_body["method"] == "eth_chainId":
            return {"jsonrpc": "2.0", "id": 1, "result": "0x1"}
        return {"jsonrpc": "2.0", "id": 1, "result": "0x64"}

    pool = net.RpcPool("http://wrong", expected_chain_id=56)
    try:
        run_with_backend(pool, backend)
    except net.RpcChainMismatch:
        pass
    else:
        raise AssertionError("wrong-chain endpoint was accepted")
    assert calls == [("http://wrong", "eth_chainId")], calls


def test_attestation_failures():
    bad_values = [None, "0x", "56", "not-hex", {"nested": 56}]
    for bad in bad_values:
        methods = []

        async def backend(client, bucket, method, url, *, json_body=None, attempts=6):
            methods.append(json_body["method"])
            return {"jsonrpc": "2.0", "id": 1, "result": bad}

        pool = net.RpcPool("http://bad", expected_chain_id=56)
        try:
            run_with_backend(pool, backend)
        except net.RpcAttestationError:
            pass
        else:
            raise AssertionError(f"unparseable chain id accepted: {bad!r}")
        assert methods == ["eth_chainId"], (bad, methods)

    methods = []

    async def rpc_error(client, bucket, method, url, *, json_body=None, attempts=6):
        methods.append(json_body["method"])
        return {"jsonrpc": "2.0", "id": 1,
                "error": {"code": -32000, "message": "injected"}}

    pool = net.RpcPool("http://rpc-error", expected_chain_id=56)
    try:
        run_with_backend(pool, rpc_error)
    except net.RpcAttestationError:
        pass
    else:
        raise AssertionError("eth_chainId RPC error was accepted")
    assert methods == ["eth_chainId"], methods

    methods = []

    async def transport_failure(client, bucket, method, url, *, json_body=None, attempts=6):
        methods.append(json_body["method"])
        raise TimeoutError("injected chainId timeout")

    pool = net.RpcPool("http://timeout", expected_chain_id=56)
    try:
        run_with_backend(pool, transport_failure)
    except net.RpcAttestationError:
        pass
    else:
        raise AssertionError("chainId timeout was accepted")
    assert methods == ["eth_chainId"], methods


def test_correct_chain_and_failover_reattest():
    calls = []

    async def correct(client, bucket, method, url, *, json_body=None, attempts=6):
        rpc_method = json_body["method"]
        calls.append((url, rpc_method))
        if rpc_method == "eth_chainId":
            return {"jsonrpc": "2.0", "id": 1, "result": "0x38"}
        return {"jsonrpc": "2.0", "id": 1, "result": "0x64"}

    pool = net.RpcPool("http://correct", expected_chain_id=56)
    got = run_with_backend(pool, correct)
    assert got == {"ok": True, "result": "0x64"}, got
    assert calls == [("http://correct", "eth_chainId"),
                     ("http://correct", "eth_call")], calls

    calls = []

    async def failover(client, bucket, method, url, *, json_body=None, attempts=6):
        rpc_method = json_body["method"]
        calls.append((url, rpc_method))
        if rpc_method == "eth_chainId":
            return {"jsonrpc": "2.0", "id": 1, "result": "0x38"}
        if url == "http://first":
            raise TimeoutError("first endpoint down")
        return {"jsonrpc": "2.0", "id": 1, "result": "0x2a"}

    pool = net.RpcPool(["http://first", "http://second"],
                       expected_chain_id=56, attempts=1)
    got = run_with_backend(pool, failover)
    assert got == {"ok": True, "result": "0x2a"}, got
    assert calls == [("http://first", "eth_chainId"),
                     ("http://first", "eth_call"),
                     ("http://second", "eth_chainId"),
                     ("http://second", "eth_call")], calls


def test_registry_factory_rejects_missing_identity():
    for chain in ("robinhood", "opbnb"):
        try:
            net.attested_rpc_pool("http://fixture", chain, formal=True)
        except net.RpcAttestationError:
            pass
        else:
            raise AssertionError(f"formal chain without evm_chain_id accepted: {chain}")


def _wrong_chain_backend(method_log):
    async def backend(client, bucket, method, url, *, json_body=None, attempts=6):
        method_log.append(json_body["method"])
        if json_body["method"] == "eth_chainId":
            return {"jsonrpc": "2.0", "id": 1, "result": "0x1"}
        return {"jsonrpc": "2.0", "id": 1, "result": "0x64"}
    return backend


def _write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def test_each_formal_callsite_wrong_chain_zero_business():
    token = "0x" + "a" * 40
    address = "0x" + "b" * 40
    with tempfile.TemporaryDirectory(prefix="batch1-rpc-sites-") as td:
        root = Path(td).resolve()

        # verify_recon: its former private attestation must now be gone.
        config = root / "config.json"
        balances = root / "balances.json"
        stats = root / "stats.json"
        gmgn = root / "gmgn.csv"
        _write_json(config, {"token": token, "decimals": 0,
                             "total_supply_human": "100"})
        _write_json(balances, {address: "100"})
        _write_json(stats, {"max_block": 10, "mint_total_raw": "100",
                            "burn_total_raw": "0"})
        gmgn.write_text("address,pct\n", encoding="utf-8")
        verify = load("scripts/evm/verify_recon.py", "batch1_verify_recon")
        methods = []
        with mock.patch.object(net, "_request_json",
                               side_effect=_wrong_chain_backend(methods)):
            rc = verify.main([
                "--config", str(config), "--balances", str(balances),
                "--replay-stats", str(stats), "--gmgn", str(gmgn),
                "--chain", "bsc", "--token", token, "--end-block", "10",
                "--out", str(root / "verify.json"), "--rpc", "http://wrong"])
        assert rc != 0 and methods == ["eth_chainId"], ("verify_recon", rc, methods)

        # time_spotcheck.
        plan = root / "plan.json"
        _write_json(plan, {"chain": "bsc", "token": token,
                           "final_block": 10,
                           "matrix_points": [{"kind": "fixture", "addr": address,
                                              "day_end_block": 10,
                                              "expected_balance_raw": "100"}],
                           "forced_points": []})
        spot = load("scripts/lib/time_spotcheck.py", "batch1_time_spotcheck")
        methods = []
        argv = ["time_spotcheck.py", "--plan", str(plan), "--chain", "bsc",
                "--rpc", "http://wrong", "--token", token, "--final-block", "10",
                "--out", str(root / "spot.json")]
        with mock.patch.object(sys, "argv", argv), mock.patch.object(
                net, "_request_json", side_effect=_wrong_chain_backend(methods)):
            rc = spot.main()
        assert rc != 0 and methods == ["eth_chainId"], ("time_spotcheck", rc, methods)

        # supply_truth_gate.
        supply = load("scripts/lib/supply_truth_gate.py", "batch1_supply_truth")
        methods = []
        argv = ["supply_truth_gate.py", "--chain", "bsc", "--token", token,
                "--as-of-block", "10", "--replay-stats", str(stats),
                "--rpc", "http://wrong", "--out", str(root / "supply.json")]
        with mock.patch.object(sys, "argv", argv), mock.patch.object(
                net, "_request_json", side_effect=_wrong_chain_backend(methods)):
            rc = supply.main()
        assert rc != 0 and methods == ["eth_chainId"], ("supply_truth_gate", rc, methods)

        # accounting_gate: first requested business method is eth_blockNumber.
        accounting = load("scripts/evm/accounting_gate.py", "batch1_accounting_gate")
        methods = []
        argv = ["accounting_gate.py", "--chain", "bsc", "--token", token,
                "--rpc", "http://wrong", "--out", str(root / "accounting.json")]
        with mock.patch.object(sys, "argv", argv), mock.patch.object(
                net, "_request_json", side_effect=_wrong_chain_backend(methods)):
            try:
                accounting.main()
            except SystemExit as exc:
                rc = int(exc.code)
            else:
                raise AssertionError("accounting_gate did not exit")
        assert rc != 0 and methods == ["eth_chainId"], ("accounting_gate", rc, methods)


def test_remaining_formal_entrypoints_wrong_chain_zero_business():
    token = "0x" + "a" * 40
    address = "0x" + "b" * 40
    txhash = "0x" + "c" * 64
    cases = [
        ("multicall_balances", "scripts/evm/multicall_balances.py",
         ["multicall_balances.py", "--chain", "bsc", "--token", token,
          "--input", "{empty}", "--out", "{out}"]),
        ("pierce_stake", "scripts/evm/pierce_stake.py",
         ["pierce_stake.py", "--chain", "arbitrum", "--tracker", token,
          "--token", address, "--addrs", "{empty}", "--out", "{out}"]),
        ("lp_positions", "scripts/evm/lp_positions.py",
         ["lp_positions.py", "--chain", "bsc", "--logs", "{missing}",
          "--pool", token, "--out", "{out}"]),
        ("scan_bloxroute_seg", "scripts/evm/scan_bloxroute_seg.py",
         ["scan_bloxroute_seg.py", "--chain", "bsc", "--token", token,
          "--lo", "0", "--hi", "0", "--out", "{out}"]),
        ("rpc_batch", "scripts/lib/rpc_batch.py",
         ["rpc_batch.py", "http://wrong", "getcode", address,
          "--chain", "bsc", "--out", "{out}"]),
        ("fetch_alchemy", "scripts/evm/fetch_alchemy.py",
         ["fetch_alchemy.py", "--config", "{config}", "--chain", "bsc",
          "--out-dir", "{outdir}", "--from-block", "0", "--to-block", "1"]),
    ]
    with tempfile.TemporaryDirectory(prefix="batch1-rpc-more-") as td:
        root = Path(td).resolve()
        empty = root / "empty.txt"
        empty.write_text("", encoding="utf-8")
        config = root / "config.json"
        _write_json(config, {"alchemy_key": "fixture", "alchemy_network": "bnb-mainnet",
                             "token": token})
        for name, relative, template in cases:
            module = load(relative, f"batch1_{name}")
            methods = []
            argv = [item.format(empty=empty, missing=root / "missing.parquet",
                                out=root / f"{name}.json", config=config,
                                outdir=root / f"{name}-out") for item in template]
            with mock.patch.object(sys, "argv", argv), mock.patch.object(
                    net, "_request_json", side_effect=_wrong_chain_backend(methods)):
                try:
                    rc = module.main()
                except SystemExit as exc:
                    rc = int(exc.code) if isinstance(exc.code, int) else 1
                except Exception:
                    rc = 1
            assert rc != 0 and methods == ["eth_chainId"], (name, rc, methods)


def main():
    test_wrong_chain_zero_business()
    test_attestation_failures()
    test_correct_chain_and_failover_reattest()
    test_registry_factory_rejects_missing_identity()
    test_each_formal_callsite_wrong_chain_zero_business()
    test_remaining_formal_entrypoints_wrong_chain_zero_business()
    print("PASS B1-B RPC session: wrong-chain zero business/fail-closed/correct/failover")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
