#!/usr/bin/env python3
"""B3-SOL-E2E: real Solana CLIs through runner, handoff and release gates."""
from __future__ import annotations

import base64
import gzip
import hashlib
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
import solana_exact_validate as exact  # noqa: E402
from sqd_v4_test_fixture import FETCH_SHA256  # noqa: E402
from wave_contract import has_formal_wave_semantics  # noqa: E402

MINT = "CreiuhfwdWCN5mJbMJtA9bBpYQrQF2tCBuZwSPWfpump"
PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
COVERAGE_FIXTURE = ROOT / "scripts/tests/fixtures/sqd_coverage/happy"
ZERO = "0x" + "0" * 40
OWNER = "11111111111111111111111111111111"
OBSERVED_SLOT = 103


def mint_raw(supply):
    raw = bytearray(82)
    raw[36:44] = int(supply).to_bytes(8, "little")
    raw[44] = 0
    raw[45] = 1
    return bytes(raw)


class FixtureHandler(BaseHTTPRequestHandler):
    calls = []
    supply = 100
    slot = OBSERVED_SLOT

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
                                           "preMint": MINT, "postMint": MINT,
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
                type(self).slot = max(OBSERVED_SLOT, minimum)
                if config.get("encoding") == "jsonParsed":
                    data = {"parsed": {"type": "mint", "info": {
                        "mintAuthority": None, "freezeAuthority": None,
                        "supply": str(type(self).supply), "decimals": 0}}}
                else:
                    data = [base64.b64encode(mint_raw(type(self).supply)).decode(), "base64"]
                value = {"context": {"slot": type(self).slot},
                         "value": {"owner": PROGRAM, "data": data}}
            elif method == "getTokenSupply":
                type(self).slot = OBSERVED_SLOT
                value = {"context": {"slot": type(self).slot},
                         "value": {"amount": str(type(self).supply), "decimals": 0}}
            elif method == "getProgramAccounts":
                config = params[1]
                type(self).slot = max(OBSERVED_SLOT,
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


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


SUPPLY_REGENERATED_DATA_MAP_PATHS = frozenset({
    "data/_supply.json",
    "data/_gpa_raw_all.json",
    "data/_gpa_raw_all.meta.json",
    "data/holders_accounts.json",
    "data/holders_owners.json",
    "data/holders_snapshot_meta.json",
    "data/solana_observation_bundle.json",
    "supply_snapshot.json",
})


def refresh_runner_regenerated_data_map(case, data_map):
    """Refresh only existing data-map rows rewritten by the supply producer."""
    root = Path(case).resolve()
    files = data_map.get("files")
    assert isinstance(files, list), "data_map.files must be a list"
    refreshed = []
    for row in files:
        if not isinstance(row, dict) or row.get("path") not in \
                SUPPLY_REGENERATED_DATA_MAP_PATHS:
            continue
        rel = row["path"]
        path = (root / rel).resolve()
        assert root in path.parents and path.is_file(), \
            f"runner regenerated data_map path missing or escaped: {rel}"
        row["size"] = path.stat().st_size
        row["sha256"] = sha(path)
        refreshed.append(rel)
    return refreshed


def test_refresh_runner_regenerated_data_map():
    with tempfile.TemporaryDirectory(prefix="b5e-data-map-", dir="/private/tmp") as td:
        case = Path(td)
        data = case / "data"
        data.mkdir()
        owners = data / "holders_owners.json"
        owners.write_text('{"old":1}')
        old_sha = sha(owners)
        snapshot_meta = data / "holders_snapshot_meta.json"
        snapshot_meta.write_text('{"old":true}')
        bundle = data / "solana_observation_bundle.json"
        bundle.write_text('{"old":true}')
        data_map = {"files": [
            {"path": "data/holders_owners.json", "sha256": old_sha,
             "source": "test", "note": "preserve"},
            {"path": "data/holders_snapshot_meta.json", "sha256": "0" * 64,
             "source": "future-fixture"},
            {"path": "data/solana_observation_bundle.json", "sha256": "1" * 64,
             "source": "future-fixture"},
            {"path": "data/transfers.csv", "rows": 2, "source": "test"},
        ]}
        owners.write_text('{"new":2}')
        snapshot_meta.write_text('{"new":true}')
        bundle.write_text('{"new":true}')
        refreshed = refresh_runner_regenerated_data_map(case, data_map)
        assert refreshed == ["data/holders_owners.json",
                             "data/holders_snapshot_meta.json",
                             "data/solana_observation_bundle.json"]
        row = data_map["files"][0]
        assert row == {
            "path": "data/holders_owners.json", "size": owners.stat().st_size,
            "sha256": sha(owners), "source": "test", "note": "preserve",
        }
        assert data_map["files"][1] == {
            "path": "data/holders_snapshot_meta.json",
            "size": snapshot_meta.stat().st_size, "sha256": sha(snapshot_meta),
            "source": "future-fixture",
        }
        assert data_map["files"][2] == {
            "path": "data/solana_observation_bundle.json",
            "size": bundle.stat().st_size, "sha256": sha(bundle),
            "source": "future-fixture",
        }
        assert data_map["files"][3] == {
            "path": "data/transfers.csv", "rows": 2, "source": "test",
        }


def refresh_binding_mutation_refs(case, rewritten_reports):
    """Refresh only existing fixture hashes downstream of rewritten reports."""
    root = Path(case).resolve()
    rewritten = {}
    for report in rewritten_reports:
        path = Path(report).resolve()
        assert root in path.parents and path.is_file(), \
            f"binding-mutated report missing or escaped: {report}"
        rewritten[path.relative_to(root).as_posix()] = path

    refreshed = []
    dormant_path = root / "dormant_warehouse_audit.json"
    if dormant_path.is_file():
        dormant = json.loads(dormant_path.read_text())
        universe_ref = dormant.get("universe_ref")
        rel = universe_ref.get("path") if isinstance(universe_ref, dict) else None
        if rel in rewritten:
            universe_ref["sha256"] = sha(rewritten[rel])
            dormant_path.write_text(json.dumps(dormant))
            refreshed.append(f"dormant_warehouse_audit.json:universe_ref:{rel}")

    data_map_path = root / "data_map.json"
    if data_map_path.is_file():
        data_map = json.loads(data_map_path.read_text())
        files = data_map.get("files")
        assert isinstance(files, list), "data_map.files must be a list"
        changed = False
        for row in files:
            if not isinstance(row, dict) or "sha256" not in row:
                continue
            rel = row.get("path")
            if rel not in rewritten:
                continue
            path = rewritten[rel]
            row["size"] = path.stat().st_size
            row["sha256"] = sha(path)
            refreshed.append(f"data_map.json:{rel}")
            changed = True
        if changed:
            data_map_path.write_text(json.dumps(data_map))
    return refreshed


def test_refresh_binding_mutation_refs():
    with tempfile.TemporaryDirectory(prefix="b5i-binding-refs-",
                                     dir="/private/tmp") as td:
        case = Path(td)
        wave = case / "wave_scan_report.json"
        flow = case / "flow_anomaly_report.json"
        other = case / "other.json"
        wave.write_text('{"schema":"wave-scan/v5"}')
        flow.write_text('{"schema":"flow-anomaly/v3"}')
        other.write_text('{"stable":true}')
        old_wave_sha = sha(wave)
        (case / "dormant_warehouse_audit.json").write_text(json.dumps({
            "universe_ref": {"path": wave.name, "sha256": old_wave_sha},
            "preserve": True,
        }))
        original_map = {"files": [
            {"path": wave.name, "sha256": old_wave_sha,
             "source": "fixture", "note": "preserve"},
            {"path": flow.name, "sha256": sha(flow), "source": "fixture"},
            {"path": other.name, "sha256": sha(other), "source": "fixture"},
            {"path": "unhashed.json", "source": "fixture"},
        ]}
        (case / "data_map.json").write_text(json.dumps(original_map))

        wave.write_text('{"schema":"wave-scan/v5","edge_source_binding":{}}')
        flow.write_text('{"schema":"flow-anomaly/v3","edge_source_binding":{}}')
        refreshed = refresh_binding_mutation_refs(case, (wave, flow))
        assert refreshed == [
            "dormant_warehouse_audit.json:universe_ref:wave_scan_report.json",
            "data_map.json:wave_scan_report.json",
            "data_map.json:flow_anomaly_report.json",
        ]
        dormant = json.loads((case / "dormant_warehouse_audit.json").read_text())
        assert dormant == {
            "universe_ref": {"path": wave.name, "sha256": sha(wave)},
            "preserve": True,
        }
        data_map = json.loads((case / "data_map.json").read_text())
        assert data_map["files"][0] == {
            "path": wave.name, "size": wave.stat().st_size, "sha256": sha(wave),
            "source": "fixture", "note": "preserve",
        }
        assert data_map["files"][1] == {
            "path": flow.name, "size": flow.stat().st_size, "sha256": sha(flow),
            "source": "fixture",
        }
        assert data_map["files"][2:] == original_map["files"][2:]


def solanaize_release_wave_fixture(case):
    """Convert the borrowed EVM release wave fixture to the real Solana edge path."""
    wave_path = Path(case) / "wave_scan_report.json"
    wave = json.loads(wave_path.read_text())
    key = hashlib.sha256(MINT.encode()).hexdigest()
    wave["params"] = {"edges_sol": f"data/soltx-{key}.jsonl.gz"}
    wave_path.write_text(json.dumps(wave))
    return wave_path


def test_solanaize_release_wave_fixture():
    with tempfile.TemporaryDirectory(prefix="b5j-sol-wave-",
                                     dir="/private/tmp") as td:
        case = Path(td)
        wave_path = case / "wave_scan_report.json"
        original = {
            "schema": "wave-scan/v5", "edge_order_granularity": "transaction",
            "order_ambiguous": True, "non_formal": False,
            "params": {"edges_evm_v2": "data/v2"},
            "scan_universe_count": 1,
            "scan_universe": [{"addr": "fixture", "must_adjudicate": False}],
        }
        binding = {
            "cache_kind": "base", "gid": None,
            "soltx_edges_sha256": "1" * 64,
            "soltx_meta_sha256": "2" * 64,
            "edge_logical_sha256": "3" * 64,
        }
        wave_path.write_text(json.dumps(original))
        (case / "dormant_warehouse_audit.json").write_text(json.dumps({
            "universe_ref": {"path": wave_path.name, "sha256": sha(wave_path)},
        }))
        evm_bound = {**original, "edge_source_binding": binding}
        assert not has_formal_wave_semantics(evm_bound)

        solanaize_release_wave_fixture(case)
        solana_wave = json.loads(wave_path.read_text())
        key = hashlib.sha256(MINT.encode()).hexdigest()
        assert solana_wave["params"] == {
            "edges_sol": f"data/soltx-{key}.jsonl.gz"}
        assert solana_wave["scan_universe"] == original["scan_universe"]
        solana_wave["edge_source_binding"] = binding
        wave_path.write_text(json.dumps(solana_wave))
        refresh_binding_mutation_refs(case, (wave_path,))
        assert has_formal_wave_semantics(json.loads(wave_path.read_text()))
        dormant = json.loads((case / "dormant_warehouse_audit.json").read_text())
        assert dormant["universe_ref"] == {
            "path": wave_path.name, "sha256": sha(wave_path)}


def prepare_exact_inputs(case, slot=OBSERVED_SLOT, total=100):
    """Create a one-edge formal cache and a complete healthy coverage generation."""
    data = case / "data"
    data.mkdir(exist_ok=True)
    key = hashlib.sha256(MINT.encode()).hexdigest()
    edge = data / f"soltx-{key}.jsonl.gz"
    row = [1735689600, slot, 0, -1, ZERO, OWNER, total]
    with gzip.open(edge, "wt", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")
    logical = hashlib.sha256((json.dumps(row) + "\n").encode()).hexdigest()
    meta = data / f"soltx-{key}.meta.json"
    meta.write_text(json.dumps({
        "schema": "sqd-solana-cache/v4", "version": 4, "mint": MINT,
        "endpoint": "https://portal.sqd.dev", "endpoint_sha256": "1" * 64,
        "collector": "fetch_sqd_transfers_v2.py/v4",
        "collector_sha256": FETCH_SHA256,
        "edge_schema": ["ts", "slot", "tx_index", "instr_index", "from", "to", "amt"],
        "edge_semantics": "owner-net-greedy", "order_granularity": "transaction",
        "order_exact": False, "dedupe_identity": "slot-txindex-digest/v1",
        "supply_delta_source": "tokenBalances-owner-net", "from_slot": slot,
        "finalized_upper_slot": slot, "edge_logical_sha256": logical, "edge_rows": 1,
    }))

    parent = data / "sqd_coverage"
    parent.mkdir(exist_ok=True)
    counts_bytes = gzip.compress(bytes([3]), mtime=0)
    ledger_row = {"seq": 0, "ok": True, "counts_coverage": True,
                  "from": slot, "to": slot, "slots_covered": 1, "provider": "SQD",
                  "empty_response": False, "returned_from": slot,
                  "returned_to": slot, "n_blocks": 1}
    ledger_bytes = (json.dumps(ledger_row, sort_keys=True) + "\n").encode()
    producer = {"path": "scripts/solana/sqd_coverage_probe.py",
                "sha256": sha(ROOT / "scripts/solana/sqd_coverage_probe.py")}
    metadata = {"dataset_id": "solana-mainnet", "start_block": 0,
                "real_time": True}
    classified = exact.classify_four_states(bytes([3]), slot)
    coverage = {
        "schema": exact.COVERAGE_SCHEMA, "version": 1, "chain": "solana",
        "mint": MINT, "producer": producer,
        "sqd": {"endpoint_fingerprint": "1" * 64, "dataset": "solana-mainnet",
                "metadata_normalized": metadata,
                "metadata_sha256": exact.sha256_bytes(exact.canonical_json(metadata)),
                "finalized_head_at_scan": slot, "query_body_sha256": "2" * 64},
        "scan_ranges": [{"from_slot": slot, "to_slot": slot, "mode": "full"}],
        "sample_ranges": [], "era_params": dict(exact.ERA_PARAMS),
        "slot_counts": {"path": "slot_counts.bin.gz", "size": len(counts_bytes),
                        "sha256": hashlib.sha256(counts_bytes).hexdigest(),
                        "from_slot": slot, "to_slot": slot,
                        "encoding": exact.COUNT_ENCODING},
        "skipped_confirmation": None, "shared_map": None,
        "ledger": {"path": "ledger.jsonl", "size": len(ledger_bytes),
                   "sha256": hashlib.sha256(ledger_bytes).hexdigest(), "requests": 1,
                   "success_ranges_sha256": exact.sha256_bytes(
                       exact.canonical_json([[slot, slot]]))},
        "summary": classified["summary"],
        "candidate_slots": classified["candidate_slots"],
        "verdict": classified["verdict"], "probe_id": ""}
    coverage["probe_id"] = exact.compute_probe_id(coverage)
    generation = parent / coverage["probe_id"]
    generation.mkdir()
    counts = generation / "slot_counts.bin.gz"
    ledger = generation / "ledger.jsonl"
    coverage_path = generation / "coverage_map.json"
    counts.write_bytes(counts_bytes)
    ledger.write_bytes(ledger_bytes)
    coverage_path.write_text(json.dumps(coverage))

    def ref(path):
        return {"path": path.relative_to(case).as_posix(),
                "size": path.stat().st_size, "sha256": sha(path)}
    pointer = {"schema": exact.COVERAGE_POINTER_SCHEMA,
               "target": {"chain": "solana", "token": MINT, "as_of_block": slot},
               "mode": "formal", "verdict": "PASS", "exit_code": 0,
               "producer": producer,
               "inputs": {"coverage_map": ref(coverage_path),
                          "slot_counts": ref(counts), "ledger": ref(ledger)},
               "probe_id": coverage["probe_id"], "supersedes": None,
               "published_at": "2026-08-23T00:00:00Z"}
    pointer_path = parent / "CURRENT.json"
    pointer_path.write_text(json.dumps(pointer))
    checked = exact.validate_coverage(case, coverage_path, pointer_path, slot, slot)
    assert checked["ok"], checked["reasons"]


def runner_spec(case, endpoint):
    target = {"chain": "solana", "token": MINT, "as_of_block": None}
    observed = "{observed_as_of_block}"
    anchor = ["--start", "2025-01-01", "--end", "2025-01-01",
              "--ref-slot", observed, "--ref-ts", "1735689600",
              "--as-of-slot", observed,
              "--endpoint", endpoint]
    return {"case_dir": str(case), "target": target,
            "derive_as_of_from": "supply",
            "inputs": {"config": "config.json", "stats": "stats.json"},
            "checks": {
                "supply": {"producer": "scripts/solana/scan_token_accounts.py",
                           "argv": [MINT, "--program", "spl", "--rpc", endpoint,
                                    "--out", "supply_snapshot.json",
                                    "--bundle", "data/solana_observation_bundle.json",
                                    "--work-dir", "data"],
                           "receipt": "data/solana_observation_bundle.json"},
                "balance": {"producer": "scripts/solana/anchor_sampler.py",
                            "argv": [*anchor, "--out", "balance.jsonl",
                                     "--receipt", "balance_receipt.json"],
                            "receipt": "balance_receipt.json"},
                "supply_truth": {"producer": "scripts/lib/supply_truth_gate.py",
                                 "argv": ["--chain", "solana", "--mint", MINT,
                                          "--observation-bundle",
                                          "data/solana_observation_bundle.json",
                                          "--as-of-block", observed,
                                          "--replay-stats", "stats.json",
                                          "--out", "supply_truth.json"],
                                 "receipt": "supply_truth.json"},
                "time": {"producer": "scripts/solana/anchor_sampler.py",
                         "argv": [*anchor, "--out", "time.jsonl",
                                  "--receipt", "time_spotcheck.json"],
                         "receipt": "time_spotcheck.json"},
                "exact_reconcile": {
                    "producer": "scripts/solana/replay_edges.py",
                    "argv": ["reconcile", "--mint", MINT,
                             "--case-root", str(case), "--as-of-slot", str(OBSERVED_SLOT),
                             "--receipt", "data/reconcile_receipt.json"],
                    "receipt": "data/reconcile_receipt.json"}}}


def test_supply_bundle_layout_contract():
    """Supply bundle and its relative holder refs must share the producer work-dir."""
    with tempfile.TemporaryDirectory(prefix="b5g-supply-layout-",
                                     dir="/private/tmp") as td:
        spec = runner_spec(Path(td), "http://127.0.0.1:1")
        supply = spec["checks"]["supply"]
        argv = supply["argv"]
        work_dir = argv[argv.index("--work-dir") + 1]
        marker = argv[argv.index("--bundle") + 1]
        expected = (Path(work_dir) / "solana_observation_bundle.json").as_posix()
        assert marker == expected
        assert supply["receipt"] == expected
        truth_argv = spec["checks"]["supply_truth"]["argv"]
        assert truth_argv[truth_argv.index("--observation-bundle") + 1] == expected


def execute_real_slice(case, endpoint):
    holders = case / "data/holders_owners.json"
    total = sum(json.loads(holders.read_text()).values()) if holders.is_file() else 100
    FixtureHandler.supply = total
    prepare_exact_inputs(case, slot=OBSERVED_SLOT, total=total)
    (case / "config.json").write_text(json.dumps({"mint": MINT}))
    (case / "stats.json").write_text(json.dumps({"mint_total_raw": total,
                                                  "burn_total_raw": 0}))
    spec = case / "reconciliation_job.json"
    spec.write_text(json.dumps(runner_spec(case, endpoint)))
    run([sys.executable, str(ROOT / "scripts/report/reconciliation_report.py"), str(spec)], case)
    data_map_path = case / "data_map.json"
    if data_map_path.is_file():
        data_map = json.loads(data_map_path.read_text())
        refresh_runner_regenerated_data_map(case, data_map)
        data_map_path.write_text(json.dumps(data_map))
    bundle_path = case / "data/solana_observation_bundle.json"
    bundle = json.loads(bundle_path.read_text())
    slot = bundle["snapshot"]["slot"]
    run([sys.executable, str(ROOT / "scripts/solana/accounting_gate_sol.py"),
         "--mint", MINT, "--bundle", "data/solana_observation_bundle.json",
         "--as-of-slot", str(slot), "--out", "accounting_mode.json"], case)
    run([sys.executable, str(ROOT / "scripts/solana/window_fetch.py"), str(slot), str(slot),
         "window.jsonl", "--receipt", "window_receipt.json", "--endpoint", endpoint,
         "--conc", "1"], case)
    exact_receipt = json.loads((case / "data/reconcile_receipt.json").read_text())
    checked = exact.validate_reconcile_receipt_deep(
        case / "data/reconcile_receipt.json", case_root=case)
    assert checked["ok"], checked["reasons"]
    if data_map_path.is_file():
        data_map = json.loads(data_map_path.read_text())
        known = {row.get("path") for row in data_map.get("files", [])}
        required = {"data/reconcile_receipt.json"}
        required.update(ref["path"] for ref in exact_receipt["inputs"].values())
        for rel in sorted(required - known):
            data_map["files"].append({"path": rel, "source": "B3 Solana exact reconcile"})
        data_map_path.write_text(json.dumps(data_map))
    binding = exact_receipt["edge_source_binding"]
    rewritten_reports = []
    for name in ("wave_scan_report.json", "flow_anomaly_report.json"):
        path = case / name
        if path.is_file():
            value = json.loads(path.read_text())
            value["edge_source_binding"] = binding
            path.write_text(json.dumps(value))
            rewritten_reports.append(path)
    refresh_binding_mutation_refs(case, rewritten_reports)
    return total, slot


def execute_coverage_fixture():
    """Run the real coverage producer with transport-only offline fixtures."""
    with tempfile.TemporaryDirectory(prefix="b3-sol-coverage-") as td:
        case = Path(td).resolve()
        run([sys.executable, str(ROOT / "scripts/solana/sqd_coverage_probe.py"),
             "--mint", MINT, "--case-root", str(case),
             "--from-slot", "100", "--to-slot", "103", "--full",
             "--workers", "2", "--transport-fixture", str(COVERAGE_FIXTURE)], case)
        pointer_path = case / "data/sqd_coverage/CURRENT.json"
        pointer = json.loads(pointer_path.read_text())
        generation = case / "data/sqd_coverage" / pointer["probe_id"]
        assert pointer["schema"] == "sqd-solana-coverage-pointer/v1"
        assert (generation / "coverage_map.json").is_file()
        assert (generation / "slot_counts.bin.gz").is_file()
        assert (generation / "blocks.bin.gz").is_file()
        assert (generation / "ledger.jsonl").is_file()


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
                     "time_spotcheck.json", "data/solana_observation_bundle.json"):
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
        solanaize_release_wave_fixture(case)
        for path in [*(case / f"{key}_receipt.json"
                       for key in ("balance", "supply", "supply_truth", "time")),
                     case / "reconciliation_report.json", case / "accounting_mode.json",
                     case / "shared_release_receipt.json",
                     case / "data/solana_observation_bundle.json"]:
            path.unlink(missing_ok=True)
        adversarial = json.loads((case / "adversarial_review.json").read_text())
        total, slot = execute_real_slice(case, endpoint)
        adversarial["target"] = {"chain": "solana", "token": MINT,
                                 "as_of_block": slot}
        (case / "adversarial_review.json").write_text(json.dumps(adversarial))
        # B-7（批 D）：三账 balance_source 须与真实四查 owner 快照同时点等值——
        # build_case 的 EVM 编造三账（0xabc@123）在真实 Solana 切片里是夹具失真，对齐之。
        from test_audit_release_gate import align_ledgers_to_owner_snapshot
        align_ledgers_to_owner_snapshot(case, case / "data/holders_owners.json")
        run([sys.executable, str(ROOT / "scripts/report/shared_release_receipt.py"), str(case)], case)
        run([sys.executable, str(ROOT / "scripts/report/audit_release_gate.py"),
             str(case), "--report", str(report)], case)


@formal_evidence_target("sol")
def test_r9_solana_pythia_mainnet_vertical_slice():
    FixtureHandler.calls = []
    FixtureHandler.slot = OBSERVED_SLOT
    execute_coverage_fixture()
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
    test_supply_bundle_layout_contract()
    test_refresh_runner_regenerated_data_map()
    test_refresh_binding_mutation_refs()
    test_solanaize_release_wave_fixture()
    test_r9_solana_pythia_mainnet_vertical_slice()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
