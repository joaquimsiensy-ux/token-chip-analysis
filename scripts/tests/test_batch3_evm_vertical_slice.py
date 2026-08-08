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
sys.path[:0] = [str(ROOT / "scripts/report"), str(ROOT / "scripts/tests")]
from formal_ready_test_harness import run_formal_script  # noqa: E402
TOKEN = "0x" + "9" * 40
A = "0x" + "1" * 40
B = "0x" + "2" * 40
CHAIN_IDS = {"eth": 1, "bsc": 56, "base": 8453}


class FixtureHandler(BaseHTTPRequestHandler):
    chain_id = 1
    supply = 100
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
                   "topic2": "0x" + "0" * 24 + B[2:], "data": hex(self.supply)}
            value = {"data": [{"logs": [log]}], "next_block": body["to_block"]}
        else:
            method = body.get("method")
            type(self).methods.append(method)
            params = body.get("params") or []
            if method == "eth_chainId":
                result = hex(type(self).chain_id)
            elif method == "eth_blockNumber":
                result = hex(123)
            elif method == "eth_getCode":
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
                    if address.lower() == B and block == hex(121):
                        amount = 0
                    elif address.lower() == A and block != hex(121):
                        amount = 0
                    else:
                        amount = type(self).supply
                result = hex(amount)
            elif method == "eth_getTransactionReceipt":
                result = {"blockNumber": hex(123), "logs": [{
                    "address": TOKEN,
                    "topics": [
                        "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
                        "0x" + "0" * 64,
                        "0x" + "0" * 24 + B[2:],
                    ],
                    "data": hex(type(self).supply),
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


def prepare_inputs(case, chain, total):
    (case / "config_evm.json").write_text(json.dumps(
        {"token": TOKEN, "decimals": 0, "total_supply_human": str(total)}))
    (case / "balances_evm.json").write_text(json.dumps({B: str(total)}))
    (case / "stats_evm.json").write_text(json.dumps(
        {"max_block": 123, "mint_total_raw": str(total), "burn_total_raw": "0"}))
    (case / "gmgn_evm.csv").write_text("address,pct\n")
    (case / "transfers_evm.csv").write_text(
        "block,ts,tx,from,to,value\n"
        f"123,2025-01-01T00:00:00Z,0xt1,0x{'0' * 40},{B},{total}\n")
    run([sys.executable, str(ROOT / "scripts/lib/anchor_plan.py"),
         "--input", "transfers_evm.csv", "--chain", chain, "--token", TOKEN,
         "--total-supply", str(total), "--decimals", "0", "--min-pct", "0",
         "--final-block", "123", "--out-dir", "."], case)


def spec(case, chain, endpoint):
    common = ["--config", "config_evm.json", "--balances", "balances_evm.json",
              "--replay-stats", "stats_evm.json", "--gmgn", "gmgn_evm.csv",
              "--chain", chain, "--token", TOKEN, "--end-block", "123",
              "--rpc", endpoint, "--top-n", "1"]
    return {"family": "evm", "case_dir": str(case),
            "target": {"chain": chain, "token": TOKEN, "as_of_block": 123},
            "inputs": {name: name for name in
                       ("config_evm.json", "balances_evm.json", "stats_evm.json",
                        "gmgn_evm.csv", "transfers_evm.csv", "anchor_plan.json",
                        "anchor_plan.receipt.json")},
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
                                          "--out", "supply_truth.json"],
                                 "receipt": "supply_truth.json"},
                "time": {"producer": "scripts/lib/time_spotcheck.py",
                         "argv": ["--plan", "anchor_plan.json", "--input", "transfers_evm.csv",
                                  "--chain", chain,
                                  "--token", TOKEN, "--final-block", "123", "--rpc", endpoint,
                                  "--out", "time_spotcheck.json"],
                         "receipt": "time_spotcheck.json"}}}


def execute_real_slice(case, chain, endpoint, total):
    FixtureHandler.chain_id = CHAIN_IDS[chain]
    FixtureHandler.supply = total
    prepare_inputs(case, chain, total)
    run([sys.executable, str(ROOT / "scripts/evm/accounting_gate.py"),
         "--chain", chain, "--token", TOKEN, "--rpc", endpoint,
         "--hypersync", endpoint, "--sourcify", endpoint, "--samples", "1",
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

    with tempfile.TemporaryDirectory(prefix=f"b3-{chain}-wrong-") as td:
        wrong_chain_zero_business(Path(td), chain, endpoint)

    with tempfile.TemporaryDirectory(prefix=f"b3-{chain}-handoff-") as td:
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

    with tempfile.TemporaryDirectory(prefix=f"b3-{chain}-release-") as td:
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
        run([sys.executable, str(ROOT / "scripts/report/shared_release_receipt.py"), str(case)], case)
        run([sys.executable, str(ROOT / "scripts/report/audit_release_gate.py"),
             str(case), "--report", str(report)], case)


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        endpoint = f"http://127.0.0.1:{server.server_port}"
        for chain in ("eth", "bsc", "base"):
            full_chain(chain, endpoint)
    finally:
        server.shutdown()
        thread.join()
    print("PASS B3-EVM-E2E: eth/bsc/base real slices; wrong chain has zero business RPC")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
