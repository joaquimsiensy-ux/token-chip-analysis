#!/usr/bin/env python3
"""Synthetic raw-source tests with an explicit or unique temporary output root."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "scripts" / "report"
sys.path[:0] = [str(REPORT), str(ROOT / "scripts" / "lib")]
os.environ["CHIP_BLIND_SERIAL"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
import duckdb
import entity_source_trace as trace
import handoff_manifest as handoff
import trace_compute_cache as cache
from content_cache import CacheStore


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TraceCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configured = os.environ.get("CHIP_PERF_TEST_ROOT")
        cls.tests_root = (Path(configured).expanduser().resolve() if configured
                          else Path(tempfile.mkdtemp(prefix="token-chip-performance-")))
        cls.tests_root.mkdir(parents=True, exist_ok=True)

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix=self._testMethodName + "-", dir=self.tests_root))
        self.metrics = self.root / "metrics.jsonl"
        self.env = dict(os.environ, CHIP_PERF_METRICS=str(self.metrics),
                        CHIP_PERF_CACHE_ROOT=str(self.root / "cache"))
        self.patch_env = patch.dict(os.environ, self.env)
        self.patch_env.start()
        self.addCleanup(self.patch_env.stop)
        self.entity = self.root / "entities.json"
        self.labels = self.root / "labels.json"
        self.db = self.root / "edges.duckdb"
        self.ledger = self.root / "provenance_ledger.json"
        write(self.entity, {"e": ["E"]})
        write(self.labels, {"CEX": {"kind": "cex"}, "DEX": {"kind": "dex_pool"}})
        con = duckdb.connect(str(self.db))
        con.execute("CREATE TABLE transfers(ts BIGINT, f VARCHAR, t VARCHAR, amt HUGEINT, block_number BIGINT, log_index BIGINT)")
        con.executemany("INSERT INTO transfers VALUES (?,?,?,?,?,?)", [
            (86400, "CEX", "E", 100, 1, 0),
            (172800, "DEX", "E", 100, 2, 0),
            (259200, "E", "OUT", 100, 3, 0),
        ])
        con.close()
        self.manifest = {"run_id": "synthetic-test", "scope": {
            "chains": ["ethereum"], "contract": "synthetic", "cutoff_utc": "1970-01-10T00:00:00Z",
            "frozen_block": 100, "denominators": {"total_supply_raw": "1000000"}},
            "artifacts": [{"path": "edges.duckdb"}]}
        write(self.root / "handoff_manifest.json", self.manifest)
        write(self.root / "data_map.json", {"files": [{"path": "edges.duckdb"}]})

    def run_trace(self, *extra, expected=2):
        args = [sys.executable, str(REPORT / "entity_source_trace.py"),
                "--duckdb", str(self.db), "--edges-table", "transfers",
                "--total-supply", "1000000", "--entity-file", str(self.entity),
                "--labels-file", str(self.labels), "--out", str(self.ledger), *extra]
        proc = subprocess.run(args, capture_output=True, text=True, env=self.env)
        self.assertEqual(proc.returncode, expected, proc.stdout + proc.stderr)
        return json.loads(self.ledger.read_text())

    def confirmation(self, report, reason="Synthetic test decision with policy differences explicitly preserved"):
        evidence = self.root / "confirmation-evidence.txt"
        evidence.write_text("Synthetic test evidence only: three-policy differences were inspected.\n")
        def ref(path):
            return {"path": path.name, "size": path.stat().st_size, "sha256": digest(path)}
        rows = []
        for (entity, anchor), flip in handoff.ledger_real_flips(report).items():
            rows.append({"entity_id": entity, "anchor": anchor, "reason": reason,
                         "flip_fingerprint": flip["fingerprint"], "disclosure": {
                             "top_by_policy": {p: {"terminal": flip["tops"][p],
                                                   "share_pct": flip["shares"][p]} for p in handoff.FLIP_POLICIES},
                             "report_locations": ["synthetic-test:policy-table"]}})
        self.assertTrue(rows)
        path = self.root / "confirmation.json"
        write(path, {"schema": "flip-adjudications/v1", "approved_by": "synthetic test",
                     "user_decided_at_utc": "2026-08-01T00:00:00Z", "entity_file": ref(self.entity),
                     "evidence_refs": [ref(evidence)], "adjudications": rows})
        return path

    def test_confirmation_only_reuses_computation_but_never_old_pass(self):
        first = self.run_trace()
        self.assertFalse(first["computation_reuse"]["cache_hit"])
        self.assertEqual(first["computation_reuse"]["policy_simulations"], 3)
        receipt = self.confirmation(first)
        approved = self.run_trace("--acknowledge-flip", str(receipt), expected=0)
        self.assertTrue(approved["computation_reuse"]["cache_hit"])
        self.assertEqual(approved["computation_reuse"]["edges_loaded_for_trace"], 0)
        self.assertTrue(approved["bounds_sensitivity"]["publishable"])
        old_ref = approved["input_binding"]["algorithm_params"]["flip_adjudications"]
        self.confirmation(approved, "A different synthetic decision still discloses every policy difference")
        updated = self.run_trace("--acknowledge-flip", str(receipt), expected=0)
        self.assertTrue(updated["computation_reuse"]["cache_hit"])
        self.assertNotEqual(old_ref, updated["input_binding"]["algorithm_params"]["flip_adjudications"])
        withdrawn = self.run_trace()
        self.assertTrue(withdrawn["computation_reuse"]["cache_hit"])
        self.assertFalse(withdrawn["bounds_sensitivity"]["publishable"])
        self.assertEqual(withdrawn["bounds_sensitivity"]["acknowledged_flips"], [])
        self.assertEqual(cache.computation_output(first), cache.computation_output(updated))

    def test_name_label_scope_and_raw_content_changes_miss(self):
        self.run_trace()
        self.assertTrue(self.run_trace()["computation_reuse"]["cache_hit"])
        write(self.labels, {"CEX": {"kind": "cex", "name": "changed label"}, "DEX": {"kind": "dex_pool"}})
        self.assertFalse(self.run_trace()["computation_reuse"]["cache_hit"])
        write(self.entity, {"e": ["E", "NEW_MEMBER"]})
        self.assertFalse(self.run_trace()["computation_reuse"]["cache_hit"])
        self.manifest["scope"]["frozen_block"] = 101
        write(self.root / "handoff_manifest.json", self.manifest)
        self.assertFalse(self.run_trace()["computation_reuse"]["cache_hit"])
        con = duckdb.connect(str(self.db)); con.execute("UPDATE transfers SET amt=101 WHERE f='DEX'"); con.close()
        self.assertFalse(self.run_trace()["computation_reuse"]["cache_hit"])

    def test_corrupt_cache_is_rejected_and_recomputed(self):
        first = self.run_trace()
        store = CacheStore(self.root, cache.PRODUCER_NAMESPACE)
        path = store.path(cache.computation_inputs(first["input_binding"]))
        envelope = json.loads(path.read_text())
        envelope["body"]["payload"]["counts"]["source_edges"] = 9000
        write(path, envelope)
        fresh = self.run_trace()
        self.assertFalse(fresh["computation_reuse"]["cache_hit"])
        self.assertEqual(fresh["computation_reuse"]["full_rerun_reason"], "cache_integrity_rejected")
        self.assertEqual(fresh["computation_reuse"]["source_edges"], 3)

    def test_confirmation_free_key_binds_algorithm_and_every_parameter(self):
        first = self.run_trace()
        binding = first["input_binding"]
        key = cache.computation_inputs(binding)
        changed = copy.deepcopy(binding)
        changed["algorithm_params"]["flip_adjudications"] = {"sha256": "f" * 64}
        changed["handoff_manifest"]["file"]["sha256"] = "e" * 64
        self.assertEqual(key, cache.computation_inputs(changed))
        for field in ("depth_limit", "facility_min_degree", "node_budget", "edge_budget", "mem_limit"):
            changed = copy.deepcopy(binding)
            changed["algorithm_params"][field] = "different"
            self.assertNotEqual(key, cache.computation_inputs(changed), field)
        changed = copy.deepcopy(binding)
        changed["algorithm"]["files"]["trace_compute_cache.py"]["sha256"] = "0" * 64
        self.assertNotEqual(key, cache.computation_inputs(changed))
        for dependency in ("python", "duckdb", "pyarrow", "zlib"):
            changed = copy.deepcopy(binding)
            changed["algorithm"]["runtime"][dependency] = "different"
            self.assertNotEqual(key, cache.computation_inputs(changed), dependency)
        changed = copy.deepcopy(binding)
        changed["edge_source_binding"] = {"CURRENT": "another generation"}
        self.assertNotEqual(key, cache.computation_inputs(changed))

    def test_independent_replay_has_own_cache_and_rejects_changed_candidate(self):
        first = self.run_trace()
        receipt = self.confirmation(first)
        approved = self.run_trace("--acknowledge-flip", str(receipt), expected=0)
        # A producer's authenticated computation is already present. First P4
        # must still run its own subprocess with producer cache consumption off.
        real_run = subprocess.run
        with patch.object(handoff.subprocess, "run", wraps=real_run) as invoked:
            fails = handoff.validate_and_replay_provenance(str(self.root), approved,
                str(self.ledger), str(self.entity), self.manifest)
        self.assertEqual(fails, [])
        self.assertEqual(invoked.call_count, 1)
        cmd = invoked.call_args.args[0]
        self.assertEqual(cmd[cmd.index("--compute-cache-mode") + 1], "off")
        with patch.object(handoff.subprocess, "run", side_effect=AssertionError("unexpected replay")):
            self.assertEqual(handoff.validate_and_replay_provenance(str(self.root), approved,
                str(self.ledger), str(self.entity), self.manifest), [])
        own_store = CacheStore(self.root, cache.INDEPENDENT_NAMESPACE)
        own_path = own_store.path(cache.independent_inputs(approved["input_binding"], approved))
        envelope = json.loads(own_path.read_text())
        envelope["body"]["payload"]["independent_computation"]["unresolved_total_pct"] = 999
        write(own_path, envelope)
        with patch.object(handoff.subprocess, "run", wraps=real_run) as invoked:
            self.assertEqual(handoff.validate_and_replay_provenance(str(self.root), approved,
                str(self.ledger), str(self.entity), self.manifest), [])
        self.assertEqual(invoked.call_count, 1)
        self.confirmation(approved, "Another synthetic user confirmation without any computational change")
        confirmed_again = self.run_trace("--acknowledge-flip", str(receipt), expected=0)
        with patch.object(handoff.subprocess, "run", side_effect=AssertionError("confirmation caused replay")):
            self.assertEqual(handoff.validate_and_replay_provenance(str(self.root), confirmed_again,
                str(self.ledger), str(self.entity), self.manifest), [])
        stale_confirmation = copy.deepcopy(confirmed_again)
        stale_confirmation["bounds_sensitivity"]["acknowledged_flips"] = []
        with patch.object(handoff.subprocess, "run", side_effect=AssertionError("bad confirmation ran replay")):
            failures = handoff.validate_and_replay_provenance(str(self.root), stale_confirmation,
                str(self.ledger), str(self.entity), self.manifest)
        self.assertTrue(any("当前确认层" in x for x in failures), failures)
        forged = copy.deepcopy(confirmed_again)
        forged["entities"][0]["turnover"]["gross_in_raw"] = "999"
        write(self.ledger, forged)
        with patch.object(handoff.subprocess, "run", wraps=real_run) as invoked:
            failures = handoff.validate_and_replay_provenance(str(self.root), forged,
                str(self.ledger), str(self.entity), self.manifest)
        self.assertEqual(invoked.call_count, 1)
        self.assertTrue(any("重放语义摘要" in x for x in failures), failures)

    def test_missing_confirmation_stops_freeze_before_expensive_verify(self):
        self.run_trace()
        write(self.root / "members.json", {"entities": []})
        from types import SimpleNamespace
        args = SimpleNamespace(case_dir=str(self.root), check_unseal=False,
                               members="members.json", entity_file="entities.json")
        with patch.object(handoff, "verify_case", side_effect=AssertionError("expensive verify ran")):
            self.assertEqual(handoff.cmd_freeze(args), 2)

    def test_dependency_drift_during_computation_prevents_output(self):
        args = ["trace", "--duckdb", str(self.db), "--edges-table", "transfers",
                "--total-supply", "1000000", "--entity-file", str(self.entity),
                "--labels-file", str(self.labels), "--out", str(self.ledger)]
        original = trace.compute_from_edges
        def drift(*a, **kw):
            value = original(*a, **kw)
            write(self.labels, {"CEX": {"kind": "cex", "name": "changed while running"}})
            return value
        with patch.object(sys, "argv", args), patch.object(trace, "compute_from_edges", side_effect=drift):
            self.assertEqual(trace.main(), 2)
        self.assertFalse(self.ledger.exists())

    def test_solana_optional_meta_keeps_preflight_request_intact(self):
        from sqd_v4_test_fixture import formal_cli_args
        edge_path = self.root / "sol-edges.jsonl"
        edge_path.write_text(json.dumps([86400, 1, 0, 0, trace.Z, "E", 100]) + "\n")
        formal = formal_cli_args(str(edge_path))
        index = formal.index("--sol-cache-meta")
        effective_meta = formal[index + 1]
        formal = formal[:index] + formal[index + 2:]
        args = [sys.executable, str(REPORT / "entity_source_trace.py"),
                "--edges-sol", str(edge_path), "--total-supply", "1000000",
                "--entity-file", str(self.entity), "--labels-file", str(self.labels),
                "--out", str(self.ledger), *formal]
        for expected_hit in (False, True):
            proc = subprocess.run(args, capture_output=True, text=True, env=self.env)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            report = json.loads(self.ledger.read_text())
            self.assertEqual(report["computation_reuse"]["cache_hit"], expected_hit)
            self.assertIsNone(report["params"]["sol_cache_meta"])
            self.assertEqual(Path(self.root, report["input_binding"]["source"]["cache_meta"]).resolve(), Path(effective_meta).resolve())

    def test_output_directory_does_not_change_case_or_confirmation_scope(self):
        first = self.run_trace()
        receipt = self.confirmation(first)
        isolated = self.root / "performance-output"
        isolated.mkdir()
        target = isolated / "confirmed.json"
        args = [sys.executable, str(REPORT / "entity_source_trace.py"),
                "--duckdb", str(self.db), "--edges-table", "transfers", "--total-supply", "1000000",
                "--entity-file", str(self.entity), "--labels-file", str(self.labels),
                "--case-root", str(self.root), "--out", str(target), "--acknowledge-flip", str(receipt)]
        proc = subprocess.run(args, capture_output=True, text=True, env=self.env)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        report = json.loads(target.read_text())
        self.assertTrue(report["computation_reuse"]["cache_hit"])
        self.assertEqual(report["input_binding"]["handoff_manifest"]["scope"], self.manifest["scope"])
        self.assertEqual(report["input_binding"]["entity_file"]["path"], "entities.json")
        self.assertFalse(json.loads(self.ledger.read_text())["bounds_sensitivity"]["publishable"])
        root_files = {p.name: digest(p) for p in self.root.iterdir() if p.is_file()}
        with patch.dict(os.environ, {"CHIP_PERF_METRICS": str(isolated / "metrics.jsonl")}), \
                patch.object(handoff.subprocess, "run", wraps=subprocess.run) as invoked:
            fails = handoff.validate_and_replay_provenance(str(self.root), report,
                str(target), str(self.entity), self.manifest)
        self.assertEqual(fails, [])
        self.assertEqual(invoked.call_count, 1)
        replay_args = invoked.call_args.args[0]
        self.assertEqual(Path(replay_args[replay_args.index("--out") + 1]).parent, isolated)
        self.assertEqual(replay_args[replay_args.index("--case-root") + 1], str(self.root))
        self.assertEqual(root_files, {p.name: digest(p) for p in self.root.iterdir() if p.is_file()})


if __name__ == "__main__":
    unittest.main(verbosity=2)
