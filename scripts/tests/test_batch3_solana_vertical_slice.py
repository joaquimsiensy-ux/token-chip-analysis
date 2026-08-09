#!/usr/bin/env python3
"""B3-SOL-E2E: real Solana CLIs through runner, handoff and release gates."""
from __future__ import annotations

import base64
import json
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import os

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts/report"), str(ROOT / "scripts/tests"),
                str(ROOT / "scripts/lib")]
from formal_ready_test_harness import run_formal_script  # noqa: E402
from formal_capability_probes import formal_evidence_target  # noqa: E402
from solana_attested_session import SOLANA_MAINNET_GENESIS_HASH  # noqa: E402

MINT = "CreiuhfwdWCN5mJbMJtA9bBpYQrQF2tCBuZwSPWfpump"
PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"


def mint_raw(supply):
    raw = bytearray(82)
    raw[36:44] = int(supply).to_bytes(8, "little")
    raw[44] = 0
    raw[45] = 1
    return bytes(raw)


class FixtureHandler(BaseHTTPRequestHandler):
    calls = []
    supply = 100
    slot = 100

    def log_message(self, *_args):
        return

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        type(self).calls.append(body)
        if body.get("type") == "solana":
            slot = int(body["fromBlock"])
            value = [{"header": {"number": slot, "timestamp": 1735689600},
                      "transactions": [{"transactionIndex": 0, "err": None}],
                      "tokenBalances": [{"transactionIndex": 0, "account": "Account1",
                                           "preOwner": "OwnerA", "postOwner": "OwnerB",
                                           "preAmount": "0", "postAmount": "100"}]}]
        else:
            method = body.get("method")
            params = body.get("params") or []
            if method == "getGenesisHash":
                value = SOLANA_MAINNET_GENESIS_HASH
            elif method == "getAccountInfo":
                config = params[1]
                minimum = int(config.get("minContextSlot", 0))
                type(self).slot = max(type(self).slot + 1, minimum)
                if config.get("encoding") == "jsonParsed":
                    data = {"parsed": {"type": "mint", "info": {
                        "mintAuthority": None, "freezeAuthority": None,
                        "supply": str(type(self).supply), "decimals": 0}}}
                else:
                    data = [base64.b64encode(mint_raw(type(self).supply)).decode(), "base64"]
                value = {"context": {"slot": type(self).slot},
                         "value": {"owner": PROGRAM, "data": data}}
            elif method == "getTokenSupply":
                type(self).slot += 1
                value = {"context": {"slot": type(self).slot},
                         "value": {"amount": str(type(self).supply), "decimals": 0}}
            elif method == "getProgramAccounts":
                config = params[1]
                type(self).slot = max(type(self).slot + 1,
                                      int(config.get("minContextSlot", 0)))
                raw = bytes(32) + int(type(self).supply).to_bytes(8, "little")
                value = {"context": {"slot": type(self).slot}, "value": [{
                    "pubkey": "Account1", "account": {
                        "data": [base64.b64encode(raw).decode(), "base64"]}}]}
            elif method == "getSignaturesForAddress":
                value = [{"signature": "sig-readonly", "slot": type(self).slot,
                          "err": None},
                         {"signature": "sig-before", "slot": max(0, type(self).slot - 10),
                          "err": None}]
            elif method == "getTransaction":
                value = {"slot": type(self).slot, "meta": {
                    "err": None, "loadedAddresses": {"writable": [], "readonly": []}},
                    "transaction": {"signatures": [params[0]], "message": {
                        "accountKeys": ["payer", MINT],
                        "header": {"numRequiredSignatures": 1,
                                   "numReadonlySignedAccounts": 0,
                                   "numReadonlyUnsignedAccounts": 1}}}}
            else:
                self.send_error(400, method)
                return
        payload = value if body.get("type") == "solana" else {
            "jsonrpc": "2.0", "id": body.get("id", 1), "result": value}
        encoded = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def run(command, cwd):
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    formal_fixture = Path(command[1]).name in {
        "handoff_manifest.py", "audit_release_gate.py",
    }
    if formal_fixture:
        proc = run_formal_script(command[1], command[2:], env=env, cwd=cwd)
    else:
        proc = subprocess.run(
            command, cwd=cwd, capture_output=True, text=True, env=env)
    if proc.returncode:
        wrapper = Path(cwd) / "reconciliation_report.json"
        detail = wrapper.read_text() if wrapper.is_file() else ""
        raise AssertionError(f"{command}\n{proc.stdout}\n{proc.stderr}\n{detail}")
    return proc


def runner_spec(case, endpoint):
    target = {"chain": "solana", "token": MINT.lower(), "as_of_block": None}
    observed = "{observed_as_of_block}"
    anchor = ["--start", "2025-01-01", "--end", "2025-01-01",
              "--ref-slot", observed, "--ref-ts", "1735689600",
              "--as-of-slot", observed,
              "--endpoint", endpoint]
    return {"family": "solana", "case_dir": str(case), "target": target,
            "derive_as_of_from": "supply",
            "inputs": {"config": "config.json", "stats": "stats.json"},
            "checks": {
                "balance": {"producer": "scripts/solana/anchor_sampler.py",
                            "argv": [*anchor, "--out", "balance.jsonl",
                                     "--receipt", "balance_receipt.json"],
                            "receipt": "balance_receipt.json"},
                "supply": {"producer": "scripts/solana/scan_token_accounts.py",
                           "argv": [MINT, "--program", "spl", "--rpc", endpoint,
                                    "--out", "supply_snapshot.json",
                                    "--bundle", "supply_receipt.json",
                                    "--work-dir", "solana_scan_work"],
                           "receipt": "supply_receipt.json"},
                "supply_truth": {"producer": "scripts/lib/supply_truth_gate.py",
                                 "argv": ["--chain", "solana", "--mint", MINT,
                                          "--observation-bundle", "supply_receipt.json",
                                          "--as-of-block", observed,
                                          "--replay-stats", "stats.json",
                                          "--out", "supply_truth.json"],
                                 "receipt": "supply_truth.json"},
                "time": {"producer": "scripts/solana/anchor_sampler.py",
                         "argv": [*anchor, "--out", "time.jsonl",
                                  "--receipt", "time_spotcheck.json"],
                         "receipt": "time_spotcheck.json"}}}


def execute_real_slice(case, endpoint):
    holders = case / "data/holders_owners.json"
    total = sum(json.loads(holders.read_text()).values()) if holders.is_file() else 100
    FixtureHandler.supply = total
    (case / "config.json").write_text(json.dumps({"mint": MINT}))
    (case / "stats.json").write_text(json.dumps({"mint_total_raw": total,
                                                  "burn_total_raw": 0}))
    spec = case / "reconciliation_job.json"
    spec.write_text(json.dumps(runner_spec(case, endpoint)))
    run([sys.executable, str(ROOT / "scripts/report/reconciliation_report.py"), str(spec)], case)
    bundle = json.loads((case / "supply_receipt.json").read_text())
    slot = bundle["snapshot"]["slot"]
    run([sys.executable, str(ROOT / "scripts/solana/accounting_gate_sol.py"),
         "--mint", MINT, "--bundle", "supply_receipt.json",
         "--as-of-slot", str(slot), "--out", "accounting_mode.json"], case)
    run([sys.executable, str(ROOT / "scripts/solana/window_fetch.py"), str(slot), str(slot),
         "window.jsonl", "--receipt", "window_receipt.json", "--endpoint", endpoint,
         "--conc", "1"], case)
    return total, slot


def test_handoff_and_release(endpoint):
    from test_handoff_manifest import make_case
    from test_audit_release_gate import build_case

    with tempfile.TemporaryDirectory(prefix="b3-sol-handoff-") as td:
        case = Path(td)
        make_case(str(case), chain="solana", token=MINT, as_of_block=77)
        for name in ("reconciliation_report.json", "reconciliation_balance_receipt.json",
                     "reconciliation_supply_receipt.json",
                     "reconciliation_supply_truth_receipt.json",
                     "reconciliation_time_receipt.json", "supply_truth.json",
                     "time_spotcheck.json"):
            (case / name).unlink(missing_ok=True)
        total, slot = execute_real_slice(case, endpoint)
        run([sys.executable, str(ROOT / "scripts/report/holder_distribution_scan.py"),
             "--case-dir", str(case), "--stage", "initial"], case)
        args = [sys.executable, str(ROOT / "scripts/report/handoff_manifest.py"), "generate",
                "--case-dir", str(case), "--status", "READY", "--mode", "full",
                "--producer-model", "batch3", "--chain", "solana", "--contract", MINT,
                "--cutoff", "2025-01-01T00:00:00Z", "--frozen-block", str(slot),
                "--denominators", json.dumps({"total_supply_raw": str(total)})]
        run(args, case)
        run([sys.executable, str(ROOT / "scripts/report/handoff_manifest.py"), "verify",
             "--case-dir", str(case)], case)

    with tempfile.TemporaryDirectory(prefix="b3-sol-release-") as td:
        case = Path(td)
        report = build_case(case, historical=False)
        for path in [*(case / f"{key}_receipt.json"
                       for key in ("balance", "supply", "supply_truth", "time")),
                     case / "reconciliation_report.json", case / "accounting_mode.json",
                     case / "shared_release_receipt.json"]:
            path.unlink(missing_ok=True)
        adversarial = json.loads((case / "adversarial_review.json").read_text())
        total, slot = execute_real_slice(case, endpoint)
        adversarial["target"] = {"chain": "solana", "token": MINT.lower(),
                                 "as_of_block": slot}
        (case / "adversarial_review.json").write_text(json.dumps(adversarial))
        run([sys.executable, str(ROOT / "scripts/report/shared_release_receipt.py"), str(case)], case)
        run([sys.executable, str(ROOT / "scripts/report/audit_release_gate.py"),
             str(case), "--report", str(report)], case)


@formal_evidence_target("sol")
def test_r9_solana_pythia_mainnet_vertical_slice():
    FixtureHandler.calls = []
    FixtureHandler.slot = 100
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        test_handoff_and_release(f"http://127.0.0.1:{server.server_port}")
    finally:
        server.shutdown()
        thread.join()
    print("PASS B3-SOL-E2E: real producer->runner->aggregator->READY->release")


def main():
    test_r9_solana_pythia_mainnet_vertical_slice()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
