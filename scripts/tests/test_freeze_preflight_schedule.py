#!/usr/bin/env python3
"""Bounded real-entry scheduling regressions; all outputs stay in a test root."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "scripts/tests"
REPORT = ROOT / "scripts/report"
sys.path[:0] = [str(TESTS), str(REPORT), str(ROOT / "scripts/lib")]
os.environ["CHIP_BLIND_SERIAL"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
import test_handoff_manifest as ready_fixture
import test_trace_compute_cache as trace_fixture


# Observe real function and subprocess entry without replacing verifier code or
# returning synthetic PASS results. Child interpreters inherit this observer.
OBSERVER = '''import json, os, sys
_out = os.environ.get("CHIP_SCHEDULE_COUNTS")
_raw = set(json.loads(os.environ.get("CHIP_SCHEDULE_RAW_PATHS", "[]")))
_watched = {"verify_case", "validate_reconciliation_report", "compute_from_edges", "run",
            "full_sha256_file", "sha256_file", "_sha256", "_file_sha256", "_sha256_file"}
def _observe(frame, event, arg):
    if event != "call": return
    name = frame.f_code.co_name
    if name not in _watched: return
    filename = os.path.basename(frame.f_code.co_filename)
    kind = None
    if filename == "handoff_manifest.py" and name == "verify_case": kind = "verify_entry"
    elif filename == "shared_release_receipt.py" and name == "validate_reconciliation_report": kind = "deep"
    elif filename == "entity_source_trace.py" and name == "compute_from_edges": kind = "trace_compute"
    elif name in {"full_sha256_file", "sha256_file", "_sha256", "_file_sha256", "_sha256_file"}:
        path = frame.f_locals.get("path", frame.f_locals.get("p"))
        if path is not None and os.path.realpath(str(path)) in _raw: kind = "raw_hash"
    elif filename == "subprocess.py" and name == "run":
        args = frame.f_locals.get("popenargs") or ()
        cmd = args[0] if args else frame.f_locals.get("kwargs", {}).get("args", [])
        if isinstance(cmd, (list, tuple)):
            if any(os.path.basename(str(x)) == "holder_distribution_scan.py" for x in cmd): kind = "distribution"
            elif any(os.path.basename(str(x)) == "entity_source_trace.py" for x in cmd) and "--compute-cache-mode" in cmd:
                if cmd[cmd.index("--compute-cache-mode") + 1] == "off": kind = "p4"
    if kind and _out:
        with open(_out, "a") as handle:
            handle.write(json.dumps({"kind": kind, "pid": os.getpid(), "function": name}) + "\\n")
if _out: sys.setprofile(_observe)
'''

P4_WORKER = '''import json, sys
from pathlib import Path
repo, root = map(Path, sys.argv[1:3])
sys.path[:0] = [str(repo / "scripts/report"), str(repo / "scripts/lib")]
import entity_source_trace
import handoff_manifest as h
pl = json.loads((root / "provenance_ledger.json").read_text())
manifest = json.loads((root / "handoff_manifest.json").read_text())
fails = h.validate_and_replay_provenance(str(root), pl, str(root / "provenance_ledger.json"), str(root / "entities.json"), manifest)
print(json.dumps(fails, ensure_ascii=False))
raise SystemExit(2 if fails else 0)
'''


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def ref(path, root):
    return {"path": str(path.relative_to(root)), "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


class FreezePreflightTests(unittest.TestCase):
    run_trace = trace_fixture.TraceCacheTests.run_trace
    confirmation = trace_fixture.TraceCacheTests.confirmation

    @classmethod
    def setUpClass(cls):
        configured = os.environ.get("CHIP_PERF_TEST_ROOT")
        cls.tests_root = Path(configured).resolve() if configured else Path(
            tempfile.mkdtemp(prefix="token-chip-performance-"))
        cls.tests_root.mkdir(parents=True, exist_ok=True)

    def setUp(self):
        trace_fixture.TraceCacheTests.setUp(self)
        # Existing bounded fixture supplies actual, locally revalidated release
        # inputs. Only its setup runs here; its full test suite is never invoked.
        ready_fixture.make_case(str(self.root))
        dm = json.loads((self.root / "data_map.json").read_text())
        dm["files"].append({"path": "edges.duckdb"})
        write(self.root / "data_map.json", dm)
        initial = subprocess.run([sys.executable, str(REPORT / "holder_distribution_scan.py"),
            "--case-dir", str(self.root), "--stage", "initial"],
            capture_output=True, text=True, env=self.env)
        self.assertEqual(initial.returncode, 0, initial.stdout + initial.stderr)
        generated = ready_fixture.run(["generate", "--case-dir", str(self.root),
            "--status", "READY", *ready_fixture.GEN, "--denominators",
            json.dumps({"total_supply_raw": "1000000"})])
        self.assertEqual(generated.returncode, 0, generated.stdout + generated.stderr)
        self.manifest = json.loads((self.root / "handoff_manifest.json").read_text())
        # Stage -2 adjudications come after the stage -1 manifest, as in the
        # formal workflow, so an unfilled receipt is not hidden by hash drift.
        templated = subprocess.run([sys.executable, str(REPORT / "adjudication_validator.py"),
            "template", "--case-dir", str(self.root)], capture_output=True, text=True, env=self.env)
        self.assertEqual(templated.returncode, 0, templated.stdout + templated.stderr)
        adj = self.root / "candidate_adjudications.json"
        obj = json.loads(adj.read_text()); obj["adjudicated_at"] = "2026-08-01T00:00:00Z"
        write(adj, obj)
        write(self.root / "members.json", {"entities": ["e"]})
        first = self.run_trace()
        receipt = self.confirmation(first)
        self.approved = self.run_trace("--acknowledge-flip", str(receipt), expected=0)
        self.observer = self.root / "observer"
        self.observer.mkdir()
        (self.observer / "sitecustomize.py").write_text(OBSERVER)
        self.raw_paths = [str(self.db.resolve()), str(Path(ready_fixture.sol_edge_path(str(self.root))).resolve())]
        self.sequence = 0

    def counted(self, argv, tag):
        self.sequence += 1
        log = self.root / f"{self.sequence:02d}-{tag}.counts.jsonl"
        env = dict(self.env, PYTHONPATH=str(self.observer),
                   CHIP_SCHEDULE_COUNTS=str(log), CHIP_SCHEDULE_RAW_PATHS=json.dumps(self.raw_paths))
        proc = subprocess.run(argv, capture_output=True, text=True, env=env)
        events = [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []
        counts = {kind: sum(row["kind"] == kind for row in events)
                  for kind in ("verify_entry", "deep", "distribution", "raw_hash", "p4", "trace_compute")}
        result = {"tag": tag, "argv": argv, "exit_code": proc.returncode,
                  "counts": counts, "stdout": proc.stdout, "stderr": proc.stderr}
        write(self.root / f"{self.sequence:02d}-{tag}.result.json", result)
        print(json.dumps({k: result[k] for k in ("tag", "exit_code", "counts")}), flush=True)
        return proc, counts

    def freeze(self, tag):
        return self.counted([sys.executable, str(REPORT / "handoff_manifest.py"), "freeze",
            "--case-dir", str(self.root), "--members", "members.json", "--entity-file", "entities.json"], tag)

    def p4(self, tag):
        return self.counted([sys.executable, "-c", P4_WORKER, str(ROOT), str(self.root)], tag)

    def assert_early_rejection(self, proc, counts):
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(counts, {key: 0 for key in counts}, proc.stdout + proc.stderr)

    def malformed(self):
        cases = []
        def add(name, mutate):
            obj = copy.deepcopy(self.approved); mutate(obj); cases.append((name, obj))
        add("missing_input_binding", lambda p: p.pop("input_binding"))
        for name in ("labels_file", "entity_file", "source", "algorithm_params", "handoff_manifest", "data_map", "total_supply_raw"):
            add("missing_" + name, lambda p, n=name: p["input_binding"].pop(n))
        add("missing_flip_receipt", lambda p: p["input_binding"]["algorithm_params"]["flip_adjudications"].update(path="absent-confirmation.json"))
        add("withdrawn_flip_receipt", lambda p: p["input_binding"]["algorithm_params"].pop("flip_adjudications"))
        add("missing_labels_path", lambda p: p["input_binding"]["labels_file"].update(path="absent-labels.json"))
        add("missing_source_argument", lambda p: p["input_binding"]["source"].pop("argument"))
        add("missing_raw_path", lambda p: p["input_binding"]["source"]["files"][0].update(path="absent.duckdb"))
        for name in ("depth_limit", "facility_min_degree", "node_budget", "edge_budget"):
            add("missing_" + name, lambda p, n=name: p["input_binding"]["algorithm_params"].pop(n))
        add("invalid_depth_type", lambda p: p["input_binding"]["algorithm_params"].update(depth_limit="invalid"))
        edge_path = Path(ready_fixture.sol_edge_path(str(self.root)))
        meta = edge_path.with_name(edge_path.name.replace(".jsonl.gz", ".meta.json"))
        for field in ("cache_meta", "mint"):
            def missing_sol(p, field=field):
                source = p["input_binding"]["source"]
                source.update(kind="sol", cache_meta=str(meta.relative_to(self.root)), mint=ready_fixture.MINT)
                source.pop(field)
            add("missing_sol_" + field, missing_sol)
        def missing_meta_file(p):
            p["input_binding"]["source"].update(kind="sol", cache_meta="absent.meta.json", mint=ready_fixture.MINT)
        add("missing_sol_meta_file", missing_meta_file)
        return cases

    def test_freeze_rejects_listed_inputs_before_all_expensive_work(self):
        for name, ledger in self.malformed():
            with self.subTest(name=name):
                write(self.ledger, ledger)
                self.assert_early_rejection(*self.freeze(name))

    def test_p4_reuses_same_cheap_checks_before_full_hashes(self):
        for name, ledger in self.malformed():
            with self.subTest(name=name):
                write(self.ledger, ledger)
                self.assert_early_rejection(*self.p4(name))

    def test_unclosed_candidate_and_distribution_never_start_replay(self):
        adj_path = self.root / "candidate_adjudications.json"
        original = json.loads(adj_path.read_text())
        unclosed = copy.deepcopy(original); unclosed["adjudicated_at"] = None
        write(adj_path, unclosed)
        with self.subTest(name="candidate_unclosed"):
            self.assert_early_rejection(*self.freeze("candidate_unclosed"))
        write(adj_path, original)
        scan_path = self.root / "unclosed-final-scan.json"
        scan = {"denominators": {"net_supply_raw": "1000000"}, "abnormal_clusters": [
            {"cluster_id": "fixture", "trigger": "head_concentration", "raw_balance": "30000",
             "net_supply_pct": 3, "members": [{"owner": "E"}]}]}
        write(scan_path, scan)
        obj = {"schema": "distribution-adjudications/v1", "adjudicated_at": None,
               "source_scan": {"path": scan_path.name, "sha256": ref(scan_path, self.root)["sha256"]},
               "adjudications": []}
        write(self.root / "distribution_adjudications.json", obj)
        with self.subTest(name="distribution_unclosed"):
            self.assert_early_rejection(*self.freeze("distribution_unclosed"))
        # A complete receipt does not authorize trusting an unvalidated scan.
        scan["abnormal_clusters"] = []
        write(scan_path, scan)
        obj["adjudicated_at"] = "2026-08-01T00:00:00Z"
        obj["source_scan"]["sha256"] = ref(scan_path, self.root)["sha256"]
        write(self.root / "distribution_adjudications.json", obj)
        proc, counts = self.counted([sys.executable, str(REPORT / "adjudication_validator.py"),
            "distribution-validate", "--case-dir", str(self.root),
            "--entity-file", "entities.json"], "complete_receipt_bad_scan")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(counts["distribution"], 1)

    def test_valid_p4_still_computes_off_then_reuses_own_proof(self):
        first, counts = self.freeze("valid_first")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(counts["p4"], 1)
        self.assertEqual(counts["trace_compute"], 1)
        self.assertGreater(counts["raw_hash"], 0)
        again, counts = self.freeze("valid_again")
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
        self.assertEqual(counts["p4"], 0)
        self.assertEqual(counts["trace_compute"], 0)
        self.assertIn('"cache_hit":true', (self.root / "metrics.jsonl").read_text().replace(" ", ""))



#!/usr/bin/env python3
"""Bounded algorithm-shape and moved-validation mutation regressions."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

first = sys.modules[__name__]
import test_distribution_gate as distribution_fixture


OBSERVER = first.OBSERVER.replace(
    '    kind = None\n',
    '    kind = None\n'
    '    if filename == "handoff_manifest.py" and name == "full_sha256_file" and _out:\n'
    '        with open(_out, "a") as handle:\n'
    '            handle.write(json.dumps({"kind": "bound_file_hash", "pid": os.getpid()}) + "\\n")\n')

MUTATE_CANDIDATE = '''
    if filename == "handoff_manifest.py" and name == "verify_case" and os.environ.get("CHIP_TEST_CANDIDATE_DRIFT"):
        candidate = os.path.join(frame.f_locals["case_dir"], "candidate_adjudications.json")
        with open(candidate) as handle: current = json.load(handle)
        current["adjudicated_at"] = None
        with open(candidate, "w") as handle: json.dump(current, handle)
'''

DISTRIBUTION_WORKER = '''import json, os, subprocess, sys
from pathlib import Path
from types import SimpleNamespace
repo, case = map(Path, sys.argv[1:3]); mutate = sys.argv[3] == "mutate"
sys.path[:0] = [str(repo / "scripts/report"), str(repo / "scripts/lib")]
import adjudication_validator as validator
original = subprocess.run
calls = []
def observe_run(*args, **kwargs):
    cmd = args[0] if args else kwargs.get("args", [])
    result = original(*args, **kwargs)
    if any(Path(str(x)).name == "holder_distribution_scan.py" for x in cmd):
        calls.append({"argv": cmd, "exit_code": result.returncode,
                      "stdout": result.stdout, "stderr": result.stderr})
        if mutate and result.returncode == 0:
            path = case / "entities.json"; stat = path.stat()
            obj = json.loads(path.read_text())
            obj = {key: ["x" * len(member) for member in members] for key, members in obj.items()}
            path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\\n")
            os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    return result
subprocess.run = observe_run
result = validator.cmd_distribution_validate(SimpleNamespace(case_dir=str(case),
    adjudications="distribution_adjudications.json", entity_file="entities.json"))
print(json.dumps({"actual_scan_calls": calls, "outer_exit_code": result, "mutated": mutate}))
raise SystemExit(result)
'''


class FollowupTests(first.FreezePreflightTests):
    def setUp(self):
        super().setUp()
        (self.observer / "sitecustomize.py").write_text(OBSERVER)

    def counted(self, argv, tag):
        proc, counts = super().counted(argv, tag)
        log = self.root / f"{self.sequence:02d}-{tag}.counts.jsonl"
        rows = [json.loads(row) for row in log.read_text().splitlines()] if log.exists() else []
        counts["bound_file_hash"] = sum(row["kind"] == "bound_file_hash" for row in rows)
        result_path = self.root / f"{self.sequence:02d}-{tag}.result.json"
        obj = json.loads(result_path.read_text()); obj["counts"] = counts; first.write(result_path, obj)
        return proc, counts

    def test_algorithm_shapes_before_hash_or_replay(self):
        mutations = [("algorithm", lambda p: p["input_binding"].pop("algorithm"))]
        for field in ("runtime", "files", "script_sha256"):
            mutations.append((field, lambda p, key=field: p["input_binding"]["algorithm"].pop(key)))
        mutations += [
            ("dependency_record", lambda p: p["input_binding"]["algorithm"]["files"].pop("wave_scan.py")),
            ("dependency_path", lambda p: p["input_binding"]["algorithm"]["files"]["wave_scan.py"].update(path="missing.py")),
            ("dependency_sha", lambda p: p["input_binding"]["algorithm"]["files"]["wave_scan.py"].pop("sha256")),
            ("runtime_field", lambda p: p["input_binding"]["algorithm"]["runtime"].pop("python")),
        ]
        for name, mutate in mutations:
            ledger = copy.deepcopy(self.approved); mutate(ledger); first.write(self.ledger, ledger)
            for entry in ("freeze", "p4"):
                with self.subTest(name=name, entry=entry):
                    self.assert_early_rejection(*getattr(self, entry)("missing_" + name + "_" + entry))

    def test_algorithm_digests_before_expensive_replay(self):
        mutations = [
            ("script_sha256", lambda p: p["input_binding"]["algorithm"].update(script_sha256="0" * 64)),
        ]
        mutations += [(name + "_sha256", lambda p, key=name:
                       p["input_binding"]["algorithm"]["files"][key].update(sha256="0" * 64))
                      for name in self.approved["input_binding"]["algorithm"]["files"]]
        for name, mutate in mutations:
            ledger = copy.deepcopy(self.approved); mutate(ledger); first.write(self.ledger, ledger)
            for entry in ("freeze", "p4"):
                with self.subTest(name=name, entry=entry):
                    proc, counts = getattr(self, entry)("wrong_" + name + "_" + entry)
                    self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                    expensive = {key: value for key, value in counts.items() if key != "bound_file_hash"}
                    self.assertEqual(expensive, {key: 0 for key in expensive}, proc.stdout + proc.stderr)
                    self.assertGreater(counts["bound_file_hash"], 0)
                    self.assertIn("算法", proc.stdout + proc.stderr)

    def test_candidate_mutation_after_precheck_is_rejected(self):
        (self.observer / "sitecustomize.py").write_text(OBSERVER.replace(
            '    kind = None\n', MUTATE_CANDIDATE + '    kind = None\n'))
        self.env["CHIP_TEST_CANDIDATE_DRIFT"] = "1"
        proc, counts = self.freeze("candidate_mutation")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(counts["verify_entry"], 1)
        self.assertGreater(counts["deep"], 0)
        self.assertFalse((self.root / "entity_freeze.json").exists())

    def test_distribution_member_mutation_cannot_return_old_pass(self):
        case = self.root / "distribution_case"; case.mkdir()
        _, final = distribution_fixture.prepare_explanation_case(case)
        self.assertEqual(final.returncode, 0, final.stdout + final.stderr)
        templated = subprocess.run([sys.executable, str(first.REPORT / "adjudication_validator.py"),
            "distribution-template", "--case-dir", str(case),
            "--scan", "dist_rounds/round_1/distribution_scan.json"], capture_output=True, text=True, env=self.env)
        self.assertEqual(templated.returncode, 0, templated.stdout + templated.stderr)
        path = case / "distribution_adjudications.json"; obj = json.loads(path.read_text())
        obj["adjudicated_at"] = "2026-08-01T00:00:00Z"
        members = set()
        for row in obj["adjudications"]:
            accepted = row.pop("_members_total"); members.update(accepted)
            row.update(candidate_verdict="pattern_confirmed", accepted_members=accepted,
                       excluded_members=[], linked_entity_id="fixture", evidence=["evidence.json"])
        first.write(path, obj); first.write(case / "entities.json", {"fixture": sorted(members)})
        args = [sys.executable, "-c", DISTRIBUTION_WORKER, str(first.ROOT), str(case)]
        valid, _ = self.counted(args + ["stable"], "distribution_stable")
        self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)
        original = (case / "entities.json").read_bytes(); stat = (case / "entities.json").stat()
        drift, _ = self.counted(args + ["mutate"], "distribution_member_mutation")
        self.assertEqual(len((case / "entities.json").read_bytes()), len(original))
        self.assertEqual((case / "entities.json").stat().st_mtime_ns, stat.st_mtime_ns)
        detail = json.loads(drift.stdout.splitlines()[-1])
        self.assertTrue(detail["actual_scan_calls"])
        self.assertTrue(all(row["exit_code"] == 0 for row in detail["actual_scan_calls"]))
        self.assertEqual(drift.returncode, 2, drift.stdout + drift.stderr)
        self.assertIn("实体名册", drift.stdout + drift.stderr)



if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(FreezePreflightTests)
    suite.addTests(FollowupTests(name) for name in (
        "test_algorithm_shapes_before_hash_or_replay",
        "test_algorithm_digests_before_expensive_replay",
        "test_candidate_mutation_after_precheck_is_rejected",
        "test_distribution_member_mutation_cannot_return_old_pass"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
