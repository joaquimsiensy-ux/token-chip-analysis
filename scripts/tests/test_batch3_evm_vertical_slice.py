#!/usr/bin/env python3
"""B3-EVM-E2E: eth/bsc/base real CLIs with loopback transport only."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts/report"), str(ROOT / "scripts/tests"),
                str(ROOT / "scripts/lib")]
from formal_ready_test_harness import run_formal_script  # noqa: E402
from formal_capability_probes import formal_evidence_target  # noqa: E402
TOKEN = "0x" + "9" * 40
A = "0x" + "1" * 40
B = "0x" + "2" * 40
ZERO = "0x" + "0" * 40
DEAD = "0x000000000000000000000000000000000000dead"
CHAIN_IDS = {"eth": 1, "bsc": 56, "base": 8453}
BLOCK_HASH = "0x" + "a" * 64
PARENT_HASH = "0x" + "b" * 64


class FixtureHandler(BaseHTTPRequestHandler):
    chain_id = 1
    supply = 100
    dead_balance = 0
    methods = []

    def log_message(self, *_args):
        return

    def do_GET(self):
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        if self.path.endswith("/query"):
            log = {"block_number": 122, "log_index": 0, "transaction_hash": "0xabc",
                   "topic1": "0x" + "0" * 24 + A[2:],
                   "topic2": "0x" + "0" * 24 + B[2:],
                   "data": hex(self.supply - self.dead_balance)}
            value = {"data": [{"logs": [log]}], "next_block": body["to_block"]}
        else:
            method = body.get("method")
            type(self).methods.append(method)
            params = body.get("params") or []
            if method == "eth_chainId":
                result = hex(type(self).chain_id)
            elif method == "eth_blockNumber":
                result = hex(123)
            elif method == "eth_getBlockByNumber":
                result = {
                    "number": hex(123), "hash": BLOCK_HASH,
                    "parentHash": PARENT_HASH, "timestamp": hex(1_700_000_000),
                }
            elif method == "eth_getCode":
                block = params[1]
                if isinstance(block, dict):
                    assert block == {"blockHash": BLOCK_HASH,
                                     "requireCanonical": True}, block
                else:
                    assert block == "latest", block
                result = "0x6000"
            elif method == "eth_getStorageAt":
                result = "0x" + "0" * 64
            elif method == "eth_call":
                call = params[0]
                data = call.get("data", "")
                if data.startswith("0x18160ddd"):
                    amount = type(self).supply
                else:
                    address = "0x" + data[-40:]
                    block = params[1]
                    if isinstance(block, dict):
                        assert block == {"blockHash": BLOCK_HASH,
                                         "requireCanonical": True}, block
                    if address.lower() == B and block == hex(121):
                        amount = 0
                    elif address.lower() == A and block != hex(121):
                        amount = 0
                    elif address.lower() == ZERO:
                        amount = 0
                    elif address.lower() == DEAD:
                        amount = type(self).dead_balance
                    elif address.lower() == B:
                        amount = type(self).supply - type(self).dead_balance
                    else:
                        amount = type(self).supply
                result = f"0x{amount:064x}"
            elif method == "eth_getTransactionReceipt":
                result = {"blockNumber": hex(123), "logs": [{
                    "address": TOKEN,
                    "topics": [
                        "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
                        "0x" + "0" * 64,
                        "0x" + "0" * 24 + B[2:],
                    ],
                    "data": hex(type(self).supply - type(self).dead_balance),
                }]}
            elif method == "eth_simulateV1":
                sent = int(params[0]["blockStateCalls"][0]["calls"][0]["data"][-64:], 16)
                result = [{"calls": [{"status": "0x1"}, {"returnData": hex(sent)}]}]
            else:
                self.send_error(400, method)
                return
            value = {"jsonrpc": "2.0", "id": body.get("id", 1), "result": result}
        encoded = json.dumps(value).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def run(command, cwd, *, expect=0):
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    formal_fixture = Path(command[1]).name in {
        "handoff_manifest.py", "audit_release_gate.py",
    }
    if formal_fixture:
        proc = run_formal_script(command[1], command[2:], env=env, cwd=cwd)
    else:
        proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True, env=env)
    if (proc.returncode == 0) != (expect == 0):
        wrapper = Path(cwd) / "reconciliation_report.json"
        detail = wrapper.read_text() if wrapper.is_file() else ""
        raise AssertionError(f"{command}\n{proc.stdout}\n{proc.stderr}\n{detail}")
    return proc


def prepare_inputs(case, chain, total, dead_balance=0):
    (case / "config_evm.json").write_text(json.dumps(
        {"token": TOKEN, "decimals": 0, "total_supply_human": str(total)}))
    balances = {B: str(total - dead_balance)}
    if dead_balance:
        balances[DEAD] = str(dead_balance)
    (case / "balances_evm.json").write_text(json.dumps(balances))
    (case / "stats_evm.json").write_text(json.dumps(
        {"max_block": 123, "mint_total_raw": str(total),
         "burn_total_raw": str(dead_balance),
         "zero_event_inflow_wei": "0",
         "dead_event_inflow_wei": str(dead_balance),
         "dead_event_outflow_wei": "0",
         "dead_sink_net_wei": str(dead_balance)}))
    (case / "gmgn_evm.csv").write_text("address,pct\n")
    (case / "transfers_evm.csv").write_text(
        "block,ts,tx,from,to,value\n"
        f"123,2025-01-01T00:00:00Z,0xt1,0x{'0' * 40},{B},{total - dead_balance}\n")
    run([sys.executable, str(ROOT / "scripts/lib/anchor_plan.py"),
         "--input", "transfers_evm.csv", "--chain", chain, "--token", TOKEN,
         "--total-supply", str(total), "--decimals", "0", "--min-pct", "0",
         "--final-block", "123", "--out-dir", "."], case)


def spec(case, chain, endpoint):
    common = ["--config", "config_evm.json", "--balances", "balances_evm.json",
              "--replay-stats", "stats_evm.json", "--gmgn", "gmgn_evm.csv",
              "--chain", chain, "--token", TOKEN, "--end-block", "123",
              "--rpc", endpoint, "--top-n", "1"]
    return {"case_dir": str(case),
            "target": {"chain": chain, "token": TOKEN, "as_of_block": 123},
            "inputs": {name: name for name in
                       ("config_evm.json", "balances_evm.json", "stats_evm.json",
                        "gmgn_evm.csv", "transfers_evm.csv", "anchor_plan.json",
                        "anchor_plan.receipt.json", "evm_observation_bundle.json",
                        "evm_observation_transcript.json")},
            "checks": {
                "balance": {"producer": "scripts/evm/verify_recon.py",
                            "argv": [*common, "--out", "balance_receipt.json"],
                            "receipt": "balance_receipt.json"},
                "supply": {"producer": "scripts/evm/verify_recon.py",
                           "argv": [*common, "--out", "supply_receipt.json"],
                           "receipt": "supply_receipt.json"},
                "supply_truth": {"producer": "scripts/lib/supply_truth_gate.py",
                                 "argv": ["--chain", chain, "--token", TOKEN,
                                          "--as-of-block", "123", "--replay-stats",
                                          "stats_evm.json", "--rpc", endpoint,
                                          "--observation-bundle",
                                          "evm_observation_bundle.json",
                                          "--out", "supply_truth.json"],
                                 "receipt": "supply_truth.json"},
                "time": {"producer": "scripts/lib/time_spotcheck.py",
                         "argv": ["--plan", "anchor_plan.json", "--input", "transfers_evm.csv",
                                  "--chain", chain,
                                  "--token", TOKEN, "--final-block", "123", "--rpc", endpoint,
                                  "--out", "time_spotcheck.json"],
                         "receipt": "time_spotcheck.json"}}}


def execute_real_slice(case, chain, endpoint, total, dead_balance=0):
    FixtureHandler.chain_id = CHAIN_IDS[chain]
    FixtureHandler.supply = total
    FixtureHandler.dead_balance = dead_balance
    prepare_inputs(case, chain, total, dead_balance)
    run([sys.executable, str(ROOT / "scripts/evm/observe_supply.py"),
         "--chain", chain, "--token", TOKEN, "--as-of-block", "123",
         "--rpc", endpoint, "--out", "evm_observation_bundle.json",
         "--transcript-out", "evm_observation_transcript.json"], case)
    run([sys.executable, str(ROOT / "scripts/evm/accounting_gate.py"),
         "--chain", chain, "--token", TOKEN, "--rpc", endpoint,
         "--hypersync", endpoint, "--sourcify", endpoint, "--samples", "1",
         "--as-of-block", "123", "--bundle", "evm_observation_bundle.json",
         "--out", "accounting_mode.json"], case)
    job = case / "reconciliation_job.json"
    job.write_text(json.dumps(spec(case, chain, endpoint)))
    run([sys.executable, str(ROOT / "scripts/report/reconciliation_report.py"), str(job)], case)


def wrong_chain_zero_business(case, chain, endpoint):
    prepare_inputs(case, chain, 100)
    FixtureHandler.chain_id = 999
    FixtureHandler.methods.clear()
    proc = run([sys.executable, str(ROOT / "scripts/lib/time_spotcheck.py"),
                "--plan", "anchor_plan.json", "--input", "transfers_evm.csv",
                "--chain", chain, "--token", TOKEN,
                "--final-block", "123", "--rpc", endpoint,
                "--out", "wrong_chain.json"], case, expect=1)
    assert proc.returncode != 0
    assert FixtureHandler.methods and set(FixtureHandler.methods) == {"eth_chainId"}, \
        (chain, FixtureHandler.methods)


def full_chain(chain, endpoint):
    from test_handoff_manifest import make_case
    from test_audit_release_gate import build_case

    with tempfile.TemporaryDirectory(prefix=f"b3-{chain}-wrong-", dir="/private/tmp") as td:
        wrong_chain_zero_business(Path(td), chain, endpoint)

    with tempfile.TemporaryDirectory(prefix=f"b3-{chain}-handoff-", dir="/private/tmp") as td:
        case = Path(td)
        make_case(str(case), chain=chain, token=TOKEN, as_of_block=123)
        total = sum(json.loads((case / "data/holders_owners.json").read_text()).values())
        for name in ("reconciliation_report.json", "reconciliation_balance_receipt.json",
                     "reconciliation_supply_receipt.json",
                     "reconciliation_supply_truth_receipt.json",
                     "reconciliation_time_receipt.json", "supply_truth.json",
                     "time_spotcheck.json"):
            (case / name).unlink(missing_ok=True)
        execute_real_slice(case, chain, endpoint, total)
        run([sys.executable, str(ROOT / "scripts/report/holder_distribution_scan.py"),
             "--case-dir", str(case), "--stage", "initial"], case)
        run([sys.executable, str(ROOT / "scripts/report/handoff_manifest.py"), "generate",
             "--case-dir", str(case), "--status", "READY", "--mode", "full",
             "--producer-model", "batch3", "--chain", chain, "--contract", TOKEN,
             "--cutoff", "2025-01-01T00:00:00Z", "--frozen-block", "123",
             "--denominators", json.dumps({"total_supply_raw": str(total)})], case)
        run([sys.executable, str(ROOT / "scripts/report/handoff_manifest.py"), "verify",
             "--case-dir", str(case)], case)

    with tempfile.TemporaryDirectory(prefix=f"b3-{chain}-release-", dir="/private/tmp") as td:
        case = Path(td)
        report = build_case(case, historical=False)
        for path in [*(case / f"{key}_receipt.json"
                       for key in ("balance", "supply", "supply_truth", "time")),
                     case / "reconciliation_report.json", case / "accounting_mode.json",
                     case / "shared_release_receipt.json"]:
            path.unlink(missing_ok=True)
        adversarial = json.loads((case / "adversarial_review.json").read_text())
        adversarial["target"] = {"chain": chain, "token": TOKEN, "as_of_block": 123}
        (case / "adversarial_review.json").write_text(json.dumps(adversarial))
        execute_real_slice(case, chain, endpoint, 100)
        # B-7（批 D）：三账 balance_source 须与真实四查 owner 快照同时点等值——
        # build_case 编造的三账（0xabc@123）对齐到本切片 verify_recon 真吃的余额文件。
        from test_audit_release_gate import align_ledgers_to_owner_snapshot
        align_ledgers_to_owner_snapshot(case, case / "balances_evm.json")
        run([sys.executable, str(ROOT / "scripts/report/shared_release_receipt.py"), str(case)], case)
        run([sys.executable, str(ROOT / "scripts/report/audit_release_gate.py"),
             str(case), "--report", str(report)], case)


def _run_registered_chain(chain):
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        endpoint = f"http://127.0.0.1:{server.server_port}"
        full_chain(chain, endpoint)
    finally:
        server.shutdown()
        thread.join()


def test_nonzero_dead_vertical_slice():
    """burn>0: verify sum==mint, supply-truth v3 fallback, shared validator all PASS."""
    from test_audit_release_gate import build_case

    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        endpoint = f"http://127.0.0.1:{server.server_port}"
        with tempfile.TemporaryDirectory(prefix="b3-eth-dead-", dir="/private/tmp") as td:
            case = Path(td)
            build_case(case, historical=False)
            for path in [*(case / f"{key}_receipt.json"
                           for key in ("balance", "supply", "supply_truth", "time")),
                         case / "reconciliation_report.json", case / "accounting_mode.json",
                         case / "shared_release_receipt.json"]:
                path.unlink(missing_ok=True)
            adversarial = json.loads((case / "adversarial_review.json").read_text())
            adversarial["target"] = {"chain": "eth", "token": TOKEN,
                                     "as_of_block": 123}
            (case / "adversarial_review.json").write_text(json.dumps(adversarial))
            execute_real_slice(case, "eth", endpoint, 100, dead_balance=20)

            supply = json.loads((case / "supply_receipt.json").read_text())
            truth = json.loads((case / "supply_truth.json").read_text())
            assert supply["observations"]["supply_closure"]["closed"] is True
            assert truth["schema"] == "supply-truth-receipt/v4"
            assert truth["decision_rule"] == "sink_fallback_form2"
            assert truth["burn_form"] == "dead_sink"
            run([sys.executable, str(ROOT / "scripts/report/shared_release_receipt.py"),
                 str(case)], case)
    finally:
        server.shutdown()
        thread.join()


@formal_evidence_target("eth")
def test_r9_eth_mainnet_vertical_slice():
    _run_registered_chain("eth")


@formal_evidence_target("bsc")
def test_r9_bsc_mainnet_vertical_slice():
    _run_registered_chain("bsc")


@formal_evidence_target("base")
def test_r9_base_mainnet_vertical_slice():
    _run_registered_chain("base")


def main():
    test_r9_eth_mainnet_vertical_slice()
    test_r9_bsc_mainnet_vertical_slice()
    test_r9_base_mainnet_vertical_slice()
    test_nonzero_dead_vertical_slice()
    print("PASS B3-EVM-E2E: eth/bsc/base slices + nonzero dead vertical closure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
