#!/usr/bin/env python3
"""B1-B negative/positive tests for the sole chain-attested EVM RPC session."""
from __future__ import annotations

import asyncio
import contextlib
import csv
import importlib.util
import io
import json
import os
import subprocess
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


def test_evm_attestation_errors_redact_endpoint_query():
    async def transport(client, bucket, method, url, *, json_body=None, attempts=6):
        raise TimeoutError(f"failed endpoint {url}")

    endpoints = (
        "https://evm.invalid/rpc?api-key=SECRET#private",
        "https://base-mainnet.g.alchemy.com/v2/FAKEKEY123",
    )
    for endpoint in endpoints:
        pool = net.RpcPool(endpoint, expected_chain_id=56)
        try:
            run_with_backend(pool, transport)
        except net.RpcAttestationError as exc:
            rendered = str(exc)
        else:
            raise AssertionError("EVM transport failure was accepted")
        for secret in ("api-key", "SECRET", "#private", "FAKEKEY123"):
            assert secret not in rendered, rendered


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
        source = root / "transfers.csv"
        source.write_text(
            "block,ts,tx,from,to,value\n"
            f"10,2025-01-01T00:00:00Z,0xt1,0x{'0' * 40},{address},100\n")
        produced = subprocess.run([
            sys.executable, str(ROOT / "scripts/lib/anchor_plan.py"),
            "--input", str(source), "--chain", "bsc", "--token", token,
            "--total-supply", "100", "--decimals", "0", "--min-pct", "0",
            "--final-block", "10", "--out-dir", str(root)],
            capture_output=True, text=True)
        assert produced.returncode == 0, produced.stdout + produced.stderr
        plan = root / "anchor_plan.json"
        spot = load("scripts/lib/time_spotcheck.py", "batch1_time_spotcheck")
        methods = []
        argv = ["time_spotcheck.py", "--plan", str(plan), "--input", str(source),
                "--chain", "bsc",
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
                "--rpc", "http://wrong", "--exploration",
                "--out", str(root / "supply.json")]
        with mock.patch.object(sys, "argv", argv), mock.patch.object(
                net, "_request_json", side_effect=_wrong_chain_backend(methods)):
            rc = supply.main()
        assert rc != 0 and methods == ["eth_chainId"], ("supply_truth_gate", rc, methods)

        # observe_supply: the bundle producer itself must attest before block/supply calls.
        observe = load("scripts/evm/observe_supply.py", "batch1_observe_supply")
        methods = []
        argv = ["observe_supply.py", "--chain", "bsc", "--token", token,
                "--as-of-block", "10", "--rpc", "http://wrong",
                "--out", str(root / "observation.json"),
                "--transcript-out", str(root / "observation-transcript.json")]
        with mock.patch.object(sys, "argv", argv), mock.patch.object(
                net, "_request_json", side_effect=_wrong_chain_backend(methods)):
            rc = observe.main()
        assert rc != 0 and methods == ["eth_chainId"], ("observe_supply", rc, methods)

        # accounting_gate: first requested business method is eth_blockNumber.
        accounting = load("scripts/evm/accounting_gate.py", "batch1_accounting_gate")
        methods = []
        secret_rpc = "https://mainnet.infura.io/v3/FAKEKEY123"
        accounting_out = root / "accounting.json"
        argv = ["accounting_gate.py", "--chain", "bsc", "--token", token,
                "--rpc", secret_rpc, "--exploration",
                "--out", str(accounting_out)]
        with mock.patch.object(sys, "argv", argv), mock.patch.object(
                net, "_request_json", side_effect=_wrong_chain_backend(methods)):
            try:
                accounting.main()
            except SystemExit as exc:
                rc = int(exc.code)
            else:
                raise AssertionError("accounting_gate did not exit")
        assert rc != 0 and methods == ["eth_chainId"], ("accounting_gate", rc, methods)
        assert "FAKEKEY123" not in accounting_out.read_text(), accounting_out.read_text()


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


def test_business_envelope_missing_result():
    """F04：握手正常、业务响应缺 result 键 → ok=False；合法 result=null 仍 ok=True。"""
    async def missing(client, bucket, method, url, *, json_body=None, attempts=6):
        if json_body["method"] == "eth_chainId":
            return {"jsonrpc": "2.0", "id": 1, "result": "0x38"}
        return {"jsonrpc": "2.0", "id": json_body["id"]}

    pool = net.RpcPool("http://envelope", expected_chain_id=56)
    got = run_with_backend(pool, missing)
    assert got["ok"] is False and "result" in got["error"], got

    async def null_result(client, bucket, method, url, *, json_body=None, attempts=6):
        if json_body["method"] == "eth_chainId":
            return {"jsonrpc": "2.0", "id": 1, "result": "0x38"}
        return {"jsonrpc": "2.0", "id": json_body["id"], "result": None}

    pool = net.RpcPool("http://envelope", expected_chain_id=56)
    got = run_with_backend(pool, null_result, method="eth_getTransactionReceipt")
    assert got == {"ok": True, "result": None}, got


def _getcode_scenario(module, td, name, payload):
    """跑一次真实 rpc_batch.main()（握手 0x38 正常，业务返回按 payload 构造），返回 (rc, 该地址结果, stdout)。"""
    address = "0x" + "b" * 40

    async def backend(client, bucket, method, url, *, json_body=None, attempts=6):
        if json_body["method"] == "eth_chainId":
            return {"jsonrpc": "2.0", "id": 1, "result": "0x38"}
        body = {"jsonrpc": "2.0", "id": json_body["id"]}
        if payload is not None:
            body.update(payload)
        return body

    out = Path(td) / f"{name}.json"
    argv = ["rpc_batch.py", "http://envelope", "getcode", address,
            "--chain", "bsc", "--out", str(out)]
    buf = io.StringIO()
    with mock.patch.object(sys, "argv", argv), mock.patch.object(
            net, "_request_json", side_effect=backend), contextlib.redirect_stdout(buf):
        rc = module.main()
    return rc, json.loads(out.read_text(encoding="utf-8"))[address], buf.getvalue()


def test_rpc_batch_getcode_rejects_malformed_code():
    """F04：rpc_batch getcode 对缺 result / null / 奇数长度 / 非十六进制 / 非字符串记 error 且退出 1，
    摘要"失败 1 / EOA 0"；"0x" 为 EOA、偶数长度十六进制为合约。"""
    module = load("scripts/lib/rpc_batch.py", "batch1_rpc_batch_f04")
    scenarios = [
        ("missing", None, False),          # 缺 result 键
        ("null", {"result": None}, False),
        ("odd", {"result": "0x0"}, False),
        ("badhex", {"result": "0xgg"}, False),
        ("int", {"result": 123}, False),
        ("eoa", {"result": "0x"}, True),
        ("contract", {"result": "0x6080"}, True),
    ]
    with tempfile.TemporaryDirectory(prefix="batch1-rpc-f04-") as td:
        for name, payload, expect_ok in scenarios:
            rc, got, stdout = _getcode_scenario(module, td, name, payload)
            if expect_ok:
                assert rc == 0 and "error" not in got, (name, rc, got)
                assert got["is_contract"] is (name == "contract"), (name, got)
            else:
                assert rc == 1 and "error" in got and "is_contract" not in got, (name, rc, got)
                assert "失败 1" in stdout and "EOA 0" in stdout, (name, stdout)


def main():
    test_wrong_chain_zero_business()
    test_attestation_failures()
    test_correct_chain_and_failover_reattest()
    test_evm_attestation_errors_redact_endpoint_query()
    test_registry_factory_rejects_missing_identity()
    test_each_formal_callsite_wrong_chain_zero_business()
    test_remaining_formal_entrypoints_wrong_chain_zero_business()
    test_business_envelope_missing_result()
    test_rpc_batch_getcode_rejects_malformed_code()
    print("PASS B1-B RPC session: wrong-chain zero business/fail-closed/correct/failover")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
