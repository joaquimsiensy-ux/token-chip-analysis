#!/usr/bin/env python3
"""W3 offline reseal contracts. Fixtures and algorithm paths belong to this checkout."""
import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path[:0] = [str(HERE), str(REPO / "scripts/report"), str(REPO / "scripts/lib")]
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
import test_stage2_closeout as w2
import stage2_closeout as subject
from formal_ready_test_harness import test_vertical_slices

read, write, sha = w2.read, w2.write, w2.sha


def add_reseal_prereqs(case):
    w2.add_provenance_ledger(case)


def snapshot(root):
    files, directories = {}, set()
    for current, dirs, names in os.walk(root):
        rel = Path(current).relative_to(root).as_posix()
        directories.add(rel)
        for name in names:
            path = Path(current) / name
            files[path.relative_to(root).as_posix()] = sha(path)
    return files, directories


def cli(case, *arguments, layer="a4"):
    return w2.cli(case, "reseal", "--from", layer, *arguments)


def expect(proc, code, needle=""):
    assert proc.returncode == code, proc.stdout + proc.stderr
    assert needle in proc.stdout + proc.stderr, proc.stdout + proc.stderr


class Cases(w2.Cases):
    def fresh(self):
        case = super().fresh()
        add_reseal_prereqs(case)
        return case


def skip_register_when_claims_same(cases):
    case = cases.fresh()
    registry = (case / "a4_claims.json").read_bytes()
    revision = read(case / "a4_seal.json")["revision"]
    proc = cli(case)
    expect(proc, 0)
    assert (case / "a4_claims.json").read_bytes() == registry
    assert read(case / "a4_seal.json")["revision"] == revision + 1


def registry_sha_drift_forces_register(cases):
    case = cases.fresh()
    obj = read(case / "a4_claims.json")
    obj["registered_at_utc"] = "2000-01-01T00:00:00Z"
    write(case / "a4_claims.json", obj)
    before = sha(case / "a4_claims.json")
    expect(cli(case), 3, "registry 已变")
    assert sha(case / "a4_claims.json") != before


def verdict_change_stops(cases):
    case = cases.fresh()
    seal = sha(case / "a4_seal.json")
    path = case / "changed.json"
    write(path, [{"id": "C1", "verdict": "WEAKENED", "revision_note": "证据不足"}])
    expect(cli(case, "--verdicts-file", str(path)), 3, "判断变更")
    assert sha(case / "a4_seal.json") == seal
    before = snapshot(case)
    outside = cases.root / "outside-verdicts.json"
    write(outside, [])
    expect(cli(case, "--verdicts-file", str(outside)), 2)
    assert snapshot(case) == before


def terminal_ledger_triggers_reopen(cases):
    case = cases.fresh()
    expect(cli(case), 0)
    assert (case / "data/stage2/dist_cycle1").is_dir()
    ledger = read(case / "distribution_rounds.json")
    assert len(ledger["rounds"]) == 1 and ledger["terminal"] is not None
    assert {p.name for p in (case / "charts/final").iterdir()} == {"holder_distribution_current.png"}


def other_charts_archived_not_deleted(cases):
    case = cases.fresh()
    final = case / "charts/final"
    (final / "fig1.png").write_bytes(b"W3 PNG placeholder")
    (final / "sub").mkdir()
    (final / "sub/x.png").write_bytes(b"nested PNG")
    (final / "empty").mkdir()
    before = snapshot(case)
    expect(cli(case, "--dry-run"), 0)
    assert snapshot(case) == before
    expect(cli(case), 0)
    histories = list((case / "data/stage2/_history").glob("*/charts_final"))
    assert len(histories) == 1
    archived = histories[0]
    assert (archived / "fig1.png").read_bytes() == b"W3 PNG placeholder"
    assert (archived / "sub/x.png").read_bytes() == b"nested PNG"
    assert (archived / "empty").is_dir() and not list((archived / "empty").iterdir())
    assert {p.name for p in final.iterdir()} == {"holder_distribution_current.png"}
    assert (case / "data/stage2/dist_cycle1").is_dir()


def ends_with_closeout_check(cases):
    case = cases.fresh()
    original = read(case / subject.WORKORDER)["bindings"]["report_md"]
    expect(cli(case), 0)
    assert read(case / subject.RECEIPT)["verdict"] == "PASS"
    bindings = read(case / subject.WORKORDER)["bindings"]
    assert bindings["report_md"] == original
    assert bindings["a4_seal_sha256"] == sha(case / "a4_seal.json")
    assert (case / read(case / "a4_seal.json")["verdicts"]["path"]).is_file()


def migrated_case_root_stops(cases):
    case = cases.fresh()
    obj = read(case / "accounting_mode.json")
    obj["observation_bundle"]["path"] = str(cases.root / "original/bundle.json")
    write(case / "accounting_mode.json", obj)
    before = snapshot(case)
    for extra in ([], ["--dry-run"]):
        expect(cli(case, *extra), 2, "案根已迁移")
        assert snapshot(case) == before


def adjudication_bound_to_m3_only_stops(cases):
    for terminal in (True, False):
        case = cases.fresh()
        if not terminal:
            ledger = read(case / "distribution_rounds.json")
            ledger["terminal"] = None
            ledger["rounds"][-1]["status"] = "UNEXPLAINED"
            write(case / "distribution_rounds.json", ledger)
        rel = "charts/final/extra_scan.json"
        write(case / rel, {})
        import adjudication_validator
        write(case / "distribution_adjudications.json", {
            "schema": adjudication_validator.DISTRIBUTION_SCHEMA,
            "source_scan": {"path": rel, "sha256": sha(case / rel)}})
        before = snapshot(case)
        scripts_before = snapshot(REPO / "scripts")
        for layer in ("rounds", "a4"):
            real = cli(case, layer=layer)
            expect(real, 3, "不承接")
            dry = cli(case, "--dry-run", layer=layer)
            expect(dry, 3, "不承接")
            assert real.stdout == dry.stdout
            assert snapshot(case) == before
            assert snapshot(REPO / "scripts") == scripts_before
        print(f"ok    15{'a' if terminal else 'b'}/15e terminal={terminal}: real/dry both exit 3, unchanged", flush=True)


def freeze_readback_no_new_revision(cases):
    import test_handoff_manifest as handoff
    for pending, note in ((["待证据"], "保留说明"), ([], None), (["待证据"], None), ([], "保留说明")):
        case = Path(tempfile.mkdtemp(prefix="w3-freeze-", dir=cases.root))
        handoff.make_case(str(case))
        expect(handoff.run(["generate", "--case-dir", str(case), "--status", "READY", *handoff.GEN]), 0)
        handoff.setup_freezeable(str(case))
        arguments = ["freeze", "--case-dir", str(case), *handoff.FRZ]
        if pending:
            arguments += ["--pending", ";".join(pending)]
        if note is not None:
            arguments += ["--casebook-note", note]
        expect(handoff.run(arguments), 0)
        before = read(case / "entity_freeze.json")
        with contextlib.redirect_stdout(io.StringIO()) as output:
            subject.freeze_readback(case)
        after = read(case / "entity_freeze.json")
        assert len(after["revisions"]) == len(before["revisions"])
        assert after["pending_items"] == pending and after["casebook_note"] == note
        assert "无需新 revision" in output.getvalue()
        print(f"ok    6 pending={bool(pending)} note={note is not None}: freeze revision unchanged", flush=True)


def raw(case, script, *arguments):
    return w2.run_formal_script(REPO / "scripts/report" / script,
                                [*map(str, arguments), "--case-dir", str(case)])


def adjudicate(case, scan_rel):
    expect(raw(case, "adjudication_validator.py", "distribution-template", "--scan", scan_rel), 0)
    path = case / "distribution_adjudications.json"
    obj = read(path)
    scan = read(case / scan_rel)
    members = {"dist-" + row["cluster_id"]: {m["owner"] for m in row["members"]}
               for row in scan["abnormal_clusters"]}
    obj["adjudicated_at"] = "2026-09-16T00:00:00Z"
    for row in obj["adjudications"]:
        row["candidate_verdict"] = "excluded"
        row["accepted_members"] = []
        row["excluded_members"] = [{"addr": owner, "reason": "离线夹具已逐员核对"}
                                   for owner in sorted(members[row["candidate_id"]])]
        assert {m["addr"] for m in row["excluded_members"]} == members[row["candidate_id"]]
    write(path, obj)
    expect(raw(case, "adjudication_validator.py", "distribution-validate"), 0)
    return path


def adjudication_bound_to_m4_archived(cases):
    case = cases.fresh()
    path = adjudicate(case, "dist_rounds/round_1/distribution_scan.json")
    original = path.read_bytes()
    expect(cli(case, layer="rounds"), 0)
    assert not path.exists()
    files = list((case / "data/stage2/_history").glob("*/distribution_adjudications.json"))
    assert len(files) == 1 and files[0].read_bytes() == original
    assert "随周期归档" in (files[0].parent / "reseal_log.json").read_text()


def nonterminal_ignores_history_receipt(cases):
    import test_distribution_gate as distribution
    import test_reopen_cycle as reopen
    case = Path(tempfile.mkdtemp(prefix="w3-adjudication-history-", dir=cases.root))
    _, proc = distribution.prepare_explanation_case(case)
    expect(proc, 0)
    expect(reopen.record(case, reopen.ROUND1, "--explanation", reopen.explain(case, 1)), 0)
    add_reseal_prereqs(case)
    expect(reopen.reopen(case), 0)
    expect(distribution.run_scan(case, "final", "--round", "1"), 0)
    expect(reopen.record(case), 0, "UNEXPLAINED")
    assert read(case / "distribution_rounds.json")["terminal"] is None
    assert read(case / reopen.ROUND1)["input_binding"]["reopened_from_cycle"]["cycle"] == 1
    path = adjudicate(case, reopen.ROUND1)
    before = snapshot(case)
    m3 = {p.resolve().relative_to(case).as_posix() for p in (case / "charts/final").rglob("*")
          if p.is_file() and p.name != "holder_distribution_current.png"}
    with contextlib.redirect_stdout(io.StringIO()):
        result = subject.reseal_archive(case, m3, set(), False)
    assert result["stage_done"] == "A0.5"
    assert reopen.ROUND1 in result["prevalidated_scan_paths"]
    assert snapshot(case) == before and path.exists()
    assert not (case / "data/stage2/_history").exists()


def adjudication_bound_to_copy_terminal_stops(cases):
    case = cases.fresh()
    target = case / "evidence/final_scan_copy.json"
    target.parent.mkdir(exist_ok=True)
    shutil.copyfile(case / "dist_rounds/round_1/distribution_scan.json", target)
    adjudicate(case, "evidence/final_scan_copy.json")
    before = snapshot(case)
    for layer in ("rounds", "a4"):
        expect(cli(case, layer=layer), 3, "不承接")
        assert snapshot(case) == before


def adjudication_dependency_in_charts_final_stops(cases):
    import test_distribution_gate as distribution
    case = Path(tempfile.mkdtemp(prefix="w3-adjudication-dependency-", dir=cases.root))
    distribution.make_case(case, distribution.head_balances())
    final = case / "charts/final"
    final.mkdir(parents=True)
    shutil.move(str(case / "data/holders_owners.json"), str(final / "owners.json"))
    write(case / "data_map.json", {"schema": "data-map/v1", "files": [
        {"path": "charts/final/owners.json", "sha256": sha(final / "owners.json")}]})
    expect(distribution.run_scan(case, "initial", "--snapshot", "charts/final/owners.json"), 0)
    distribution.add_final_inputs(case, [{"id": "C1", "text": "夹具普通命题",
                                         "files": ["evidence.json"], "report_locations": ["报告.md:1"]}])
    expect(distribution.run_scan(case, "final", "--round", "1"), 0)
    add_reseal_prereqs(case)
    adjudicate(case, "dist_rounds/round_1/distribution_scan.json")
    before = snapshot(case)
    m3 = {p.resolve().relative_to(case).as_posix() for p in final.rglob("*") if p.is_file()}
    with contextlib.redirect_stdout(io.StringIO()) as output:
        try:
            subject.reseal_archive(case, m3, set(), False)
        except SystemExit as exc:
            assert exc.code == 3
        else:
            raise AssertionError("裁决依赖将被搬走却未阻断")
    assert "裁决校验依赖 charts/final/owners.json 将被本步搬走" in output.getvalue()
    assert snapshot(case) == before
    assert not (case / "data/stage2/_history").exists()


def terminal_downstream_mismatches_block(cases):
    for field in ("rounds.a4_seal_sha", "rounds.entity_freeze_revision"):
        case = cases.fresh()
        if field == "rounds.a4_seal_sha":
            ledger = read(case / "distribution_rounds.json")
            n = ledger["terminal"]["round_n"]
            row = next(row for row in ledger["rounds"] if row["round_n"] == n)
            row["a4_seal_sha"] = "0" * 64
            write(case / "distribution_rounds.json", ledger)
        else:
            rel = read(case / "distribution_rounds.json")["terminal"]["final_scan_path"]
            scan = read(case / rel)
            scan["input_binding"]["entity_freeze_revision"] += 1
            write(case / rel, scan)
        checks = w2.check_result(case, 2)
        matches = [row for row in checks.values() if field in w2.detail(row)]
        assert matches and any(row["status"] == "BLOCK" for row in matches), checks
        print("ok    14 downstream fallback: " + field, flush=True)


def new_cluster_case(cases):
    import test_distribution_gate as distribution
    case = cases.fresh()
    balances = distribution.smooth_balances(240)
    balances["head-new"] = sum(balances.values()) // 3
    distribution.make_case(case, balances)
    write(case / "evidence.json", {"source": "W3 offline distribution fixture"})
    write(case / "candidate_screening.json", {"schema": "candidate-screening/v1",
          "auto_excluded_candidate": [{"address": "head-new", "bucket": "public_facility"}]})
    expect(distribution.run_scan(case), 0)
    assert read(case / "distribution_scan.json")["abnormal_clusters"] == []
    return case


def new_clusters_stop(cases):
    case = new_cluster_case(cases)
    expect(cli(case, layer="rounds"), 3, "回流 A4")
    ledger = read(case / "distribution_rounds.json")
    assert ledger["terminal"] is None
    assert ledger["rounds"][-1]["status"] == "REQUIRES_A4_REFLOW"


def final_source_branch_prebuilds_round(cases):
    for matching in (False, True):
        case = new_cluster_case(cases)
        # Probe the real scanner without recording; reseal archives this probe with the old cycle.
        probe = raw(case, "holder_distribution_scan.py", "validate", "--scan", "distribution_scan.json", "--expected-stage", "initial")
        expect(probe, 0)
        # Deterministic cluster ID comes from the same frozen balances/rules, not a made-up verdict.
        # Independently construct the same full-chain inputs: copying after the
        # intentional snapshot change cannot rebind its old accounting receipt.
        discovery = new_cluster_case(cases)
        expect(raw(discovery, "holder_distribution_scan.py", "reopen-cycle", "--reason", "discover X"), 0)
        expect(raw(discovery, "holder_distribution_scan.py", "--stage", "final", "--round", "1"), 0)
        ids = subject.reseal_cluster_ids(read(discovery / "dist_rounds/round_1/distribution_scan.json"))
        assert ids
        claims = read(case / "a4_claims.json")["claims"]
        for claim_id in sorted(ids if matching else {"dist-intentionally-different"}):
            claims.append({"id": claim_id, "text": "分布异常待复核", "files": ["evidence.json"],
                           "report_locations": ["report.md:1"]})
        path = case / "new_claims.json"
        write(path, claims)
        dry = cli(case, "--claims-file", str(path), "--dry-run")
        expect(dry, 0, "分支=final")
        proc = cli(case, "--claims-file", str(path))
        expect(proc, 3, "registry 已变" if matching else "不闭合")
        ledger = read(case / "distribution_rounds.json")
        assert len(ledger["rounds"]) == 1 and ledger["terminal"] is None
        if not matching:
            print("ok    13a final source mismatch: nonterminal anchor retained", flush=True)
            continue
        assert ledger["rounds"][0]["status"] == "REQUIRES_A4_REFLOW"
        # Fork before finalize so 13c never starts with a scan bound to a superseded seal.
        continuation = new_cluster_case(cases)
        write(continuation / "new_claims.json", claims)
        expect(cli(continuation, "--claims-file", str(continuation / "new_claims.json")), 3, "registry 已变")
        verdicts = [{"id": row["id"], "verdict": "CONFIRMED"} for row in claims]
        write(case / "new_verdicts.json", verdicts)
        old_seal = read(case / "a4_seal.json")
        extra = subject.reseal_extra_files(case, old_seal, claims,
                                            "dist_rounds/round_1/distribution_scan.json", None)
        expect(raw(case, "a4_gate.py", "finalize", "--verdicts-file", case / "new_verdicts.json",
                   "--seal-files", extra, "--workflow-type", "new-analysis"), 0)
        source = read(case / "a4_seal.json")["distribution_claim_source"]
        assert source["stage"] == "final" and set(source["cluster_claim_ids"]) == ids
        print("ok    13b matching final source: register stop then real finalize", flush=True)
        review = read(continuation / "adversarial_review.json")
        review["claim_registry"]["sha256"] = sha(continuation / "a4_claims.json")
        write(continuation / "adversarial_review.json", review)
        receipt = read(continuation / "shared_release_receipt.json")
        receipt["inputs"]["adversarial_review.json"]["sha256"] = sha(continuation / "adversarial_review.json")
        write(continuation / "shared_release_receipt.json", receipt)
        write(continuation / "new_verdicts.json", verdicts)
        revision = read(continuation / "a4_seal.json")["revision"]
        proc = cli(continuation, "--verdicts-file", str(continuation / "new_verdicts.json"))
        expect(proc, 3, "解释检查失败")
        assert "pending_a3" in proc.stdout
        ledger = read(continuation / "distribution_rounds.json")
        assert len(ledger["rounds"]) == 2 and ledger["rounds"][-1]["status"] == "UNEXPLAINED"
        assert read(continuation / "a4_seal.json")["revision"] == revision + 1
        second = read(continuation / "dist_rounds/round_2/distribution_scan.json")
        assert second["input_binding"]["final_bindings"]["a4_seal.json"]["sha256"] == sha(continuation / "a4_seal.json")
        print("ok    13c pending_a3 -> round 2 UNEXPLAINED; exactly one seal revision", flush=True)


def sealed_extra_case(cases, rel, *, claim_file=False):
    """Add evidence before the first real finalize, retaining the W2 full chain."""
    original_run = w2.fixture.run
    invoked = []

    def run_with_extra(script, arguments):
        if script == w2.fixture.GATE and arguments[:1] == ["finalize"]:
            case = Path(arguments[arguments.index("--case-dir") + 1])
            target = case / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('{"W3":"persistent sealed evidence"}\n')
            arguments = list(arguments)
            index = arguments.index("--seal-files") + 1
            arguments[index] += "," + rel
            if claim_file:
                claims = read(case / "a4_claims.json")["claims"]
                claims[0]["files"].append(rel)
                write(case / "fixture_claims.json", claims)
                expect(original_run(w2.fixture.GATE, ["register", "--case-dir", str(case),
                                                      "--claims-file", str(case / "fixture_claims.json")]), 0)
                # Preserve old review outputs; refresh_adversarial only creates absent outputs.
                prior = case / "evidence/prior_review"
                prior.mkdir(parents=True)
                for name in ("review_entity_attribution_skeptic.json", "review_entity_attribution_skeptic_execution.json",
                             "review_completeness_critic.json", "review_completeness_critic_execution.json",
                             "adversarial_review.json"):
                    shutil.move(str(case / name), str(prior / name))
                w2.fixture.refresh_adversarial(case)
                from shared_release_receipt import create_bundle
                create_bundle(case)
            invoked.append(str(case))
        return original_run(script, arguments)

    root = Path(tempfile.mkdtemp(prefix="w3-extra-seal-", dir=cases.root))
    with patch.object(w2.fixture, "run", run_with_extra):
        case = w2.build_closeout_case(root)
    assert invoked == [str(case)]
    add_reseal_prereqs(case)
    w2.check_result(case)
    return case


def sealed_file_missing_stops(cases):
    case = sealed_extra_case(cases, "notes.md")
    shutil.move(str(case / "notes.md"), str(case / "notes.moved.md"))
    before = sha(case / "a4_seal.json")
    expect(cli(case), 3, "notes.md")
    assert sha(case / "a4_seal.json") == before


def sealed_path_remapped_from_reopen(cases):
    case = sealed_extra_case(cases, "dist_rounds/round_1/notes.json")
    before = snapshot(case)
    scripts_before = snapshot(REPO / "scripts")
    actual = cli(case, layer="rounds")
    expect(actual, 3, "归档将搬走 seal 封入的文件 dist_rounds/round_1/notes.json")
    assert snapshot(case) == before
    dry = cli(case, "--dry-run", layer="rounds")
    expect(dry, 3)
    assert actual.stdout == dry.stdout and snapshot(case) == before
    assert snapshot(REPO / "scripts") == scripts_before
    expect(cli(case), 0, "seal-files 映射")
    rel = "data/stage2/dist_cycle1/dist_rounds/round_1/notes.json"
    assert (case / rel).is_file()
    assert rel in {row["path"] for row in read(case / "a4_seal.json")["sealed_files"]}


def archived_claim_reference_stops(cases):
    case = sealed_extra_case(cases, "dist_rounds/round_1/claim-note.json", claim_file=True)
    before = sha(case / "a4_seal.json")
    expect(cli(case), 3, "claims 变更")
    assert sha(case / "a4_seal.json") == before


def round_number_continues_nonterminal_ledger(cases):
    # Full-chain case; the new cluster is first registered and sealed, then recorded without explanation.
    case = new_cluster_case(cases)
    expect(cli(case, layer="rounds"), 3, "回流 A4")
    claims = read(case / "a4_claims.json")["claims"]
    scan = read(case / "dist_rounds/round_1/distribution_scan.json")
    claims += [{"id": cid, "text": "分布异常", "files": ["evidence.json"],
                "report_locations": ["report.md:1"]} for cid in sorted(subject.reseal_cluster_ids(scan))]
    write(case / "claims_next.json", claims)
    expect(raw(case, "a4_gate.py", "register", "--claims-file", case / "claims_next.json"), 0)
    write(case / "verdicts_next.json", [{"id": row["id"], "verdict": "CONFIRMED"} for row in claims])
    expect(raw(case, "a4_gate.py", "finalize", "--verdicts-file", case / "verdicts_next.json",
               "--seal-files", "", "--workflow-type", "new-analysis"), 0)
    # Start a new cycle-shaped nonterminal ledger under the new seal with real scan/record CLIs.
    saved = case / "evidence/previous_rounds"
    saved.mkdir(parents=True)
    shutil.move(str(case / "distribution_rounds.json"), str(saved / "distribution_rounds.json"))
    shutil.move(str(case / "dist_rounds"), str(saved / "dist_rounds"))
    expect(raw(case, "holder_distribution_scan.py", "--stage", "final", "--round", "1"), 0)
    expect(raw(case, "holder_distribution_scan.py", "record-round", "--scan", "dist_rounds/round_1/distribution_scan.json"), 0, "UNEXPLAINED")
    first = (case / "dist_rounds/round_1/distribution_scan.json").read_bytes()
    revision = read(case / "a4_seal.json")["revision"]
    expect(cli(case, layer="rounds"), 3, "解释检查失败")
    assert (case / "dist_rounds/round_1/distribution_scan.json").read_bytes() == first
    ledger = read(case / "distribution_rounds.json")
    assert len(ledger["rounds"]) == 2 and ledger["rounds"][-1]["round_n"] == 2
    assert read(case / "a4_seal.json")["revision"] == revision


BLOCKER_SOURCE = '''import os, sys
class MatplotlibBlocker:
    def find_spec(self, name, path=None, target=None):
        if name == 'matplotlib' or name.startswith('matplotlib.'):
            with open(os.environ['MPL_BLOCK_MARK'], 'a') as stream:
                stream.write(name + '\\n')
            raise ImportError('matplotlib blocked by dry-run verification')
        return None
sys.meta_path.insert(0, MatplotlibBlocker())
'''


def dry_run_touches_nothing(cases):
    """Run in the prebuilt, fully overlaid acceptance checkout; direct CLI only."""
    if REPO.resolve() != Path("/tmp/w3_acceptance").resolve():
        acceptance = overlay_acceptance()
        proc = subprocess.run([sys.executable, "-B", str(acceptance / "scripts/tests/test_stage2_reseal.py"),
                               "--only", "dry_run_touches_nothing"], cwd=str(acceptance),
                              env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True)
        print(proc.stdout, end="")
        expect(proc, 0)
        return
    assert not list((REPO / "scripts").rglob("__pycache__"))
    blocker = Path(tempfile.mkdtemp(prefix="w3-mpl-blocker-", dir=cases.root))
    (blocker / "sitecustomize.py").write_text(BLOCKER_SOURCE)
    mpl = Path(tempfile.mkdtemp(prefix="w3-empty-mpl-", dir=cases.root))
    base_env = {**os.environ, "MPLCONFIGDIR": str(mpl), "PYTHONDONTWRITEBYTECODE": "1"}
    blocked_env = {**base_env, "PYTHONPATH": str(blocker) +
                   (os.pathsep + base_env["PYTHONPATH"] if base_env.get("PYTHONPATH") else ""),
                   "MPL_BLOCK_MARK": str(blocker / "selfcheck.mark")}
    for code in ("import matplotlib", "import subprocess,sys; subprocess.run([sys.executable,'-B','-c','import matplotlib.pyplot'])"):
        proc = subprocess.run([sys.executable, "-B", "-c", code], cwd=str(cases.root),
                              env=blocked_env, capture_output=True, text=True)
        assert "blocked" in proc.stderr, proc.stderr
    assert (blocker / "selfcheck.mark").read_text().splitlines() == ["matplotlib", "matplotlib"]
    print("7(d0) parent/child finder: exactly two matplotlib attempts; evidence=" + str(blocker), flush=True)

    def compare(case, layer, code, needle):
        command = [sys.executable, "-B", str(REPO / "scripts/report/stage2_closeout.py"), "reseal",
                   "--case-dir", str(case), "--report", "report.md", "--from", layer, "--dry-run"]
        before, scripts = snapshot(case), snapshot(REPO / "scripts")
        assert not list(mpl.iterdir())
        normal = subprocess.run(command, cwd=str(case), env=base_env, capture_output=True, text=True)
        expect(normal, code, needle)
        assert snapshot(case) == before and snapshot(REPO / "scripts") == scripts
        mark = blocker / (case.name + "-" + layer + ".mark")
        assert not mark.exists() or not mark.read_bytes()
        blocked = subprocess.run(command, cwd=str(case), env={**blocked_env, "MPL_BLOCK_MARK": str(mark)},
                                 capture_output=True, text=True)
        expect(blocked, code, needle)
        assert blocked.stdout == normal.stdout, blocked.stdout + "\nVERSUS\n" + normal.stdout
        assert "blocked" not in blocked.stderr
        assert not mark.exists() or not mark.read_bytes()
        assert snapshot(case) == before and snapshot(REPO / "scripts") == scripts
        assert not list(mpl.iterdir())
        return normal

    case = cases.fresh()
    for name in ("fig1.png", "fig2.png", "fig3.png"):
        (case / "charts/final" / name).write_bytes(b"fixture PNG")
    (case / "charts/final/sub").mkdir()
    (case / "charts/final/sub/x.png").write_bytes(b"nested")
    (case / "charts/final/empty").mkdir()
    proc = compare(case, "a4", 0, "分支=initial")
    for needle in ("fig1.png", "fig2.png", "fig3.png", "cycle1", "charts/final/sub/", "charts/final/empty/"):
        assert needle in proc.stdout
    migrated = cases.fresh()
    obj = read(migrated / "accounting_mode.json")
    obj["observation_bundle"]["path"] = str(cases.root / "old/bundle.json")
    write(migrated / "accounting_mode.json", obj)
    compare(migrated, "a4", 2, "案根已迁移")
    chained = cases.fresh()
    expect(raw(chained, "holder_distribution_scan.py", "reopen-cycle", "--reason", "7g prepare"), 0)
    expect(raw(chained, "holder_distribution_scan.py", "--stage", "final", "--round", "1"), 0)
    assert not (chained / "distribution_rounds.json").exists()
    adjudicate(chained, "dist_rounds/round_1/distribution_scan.json")
    proc = compare(chained, "rounds", 0, "distribution-validate")
    assert "PASS distribution" in proc.stdout
    print("7(b,d,e,g) direct CLI normal/blocked: identical stdout/code, zero case/scripts/MPL changes", flush=True)


def overlay_acceptance():
    """Only inspect Git metadata and overlay authorized files; never repair a worktree."""
    acceptance = Path("/tmp/w3_acceptance").resolve()
    assert acceptance.is_dir(), "验收 worktree 缺失；须调度方预建"
    git_pointer = (acceptance / ".git").read_text().strip()
    assert git_pointer == "gitdir: " + str(REPO / ".git/worktrees/w3_acceptance"), git_pointer

    def git(*args):
        proc = subprocess.run(["git", *args], cwd=str(REPO), capture_output=True, text=True)
        expect(proc, 0)
        return proc.stdout.strip()

    head = git("rev-parse", "HEAD")
    acceptance_head = (REPO / ".git/worktrees/w3_acceptance/HEAD").read_text().strip()
    assert head == acceptance_head, "验收 HEAD 与派工 HEAD 不一致"
    assert not list((acceptance / "scripts").rglob("__pycache__")), "验收 worktree 已有缓存；不可自行清理"
    tracked = set(git("ls-tree", "-r", "HEAD", "--name-only").splitlines())
    changed = set(git("diff", "HEAD", "--name-only").splitlines())
    untracked = set(git("ls-files", "--others", "--exclude-standard").splitlines())
    allowed = {"scripts/report/stage2_closeout.py", "scripts/tests/test_stage2_reseal.py",
               "scripts/tests/run_all.py", "scripts/tests/invariant_manifest.json",
               "references/split-run.md", "references/analyze-workflow.md", "references/report-template.md",
               "CHANGELOG.md", "VERSION", "pyproject.toml", "SKILL.md",
               "maintenance/repair-20260915-stage2-closeout/w3_done.md",
               "maintenance/repair-20260915-stage2-closeout/w3_red_evidence.txt"}
    overlay = changed | untracked
    assert overlay <= allowed, "白名单外变更，停止验收：" + str(sorted(overlay - allowed))
    for rel in sorted(overlay):
        target = acceptance / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / rel, target)
        assert sha(target) == sha(REPO / rel), rel
    expected_files = tracked | overlay | {".git"}
    files, dirs = snapshot(acceptance)
    assert set(files) == expected_files, sorted(set(files) ^ expected_files)
    expected_dirs = {"."}
    for rel in expected_files:
        expected_dirs.update(path.as_posix() for path in Path(rel).parents)
    assert dirs == expected_dirs, sorted(dirs ^ expected_dirs)
    print(f"7(e) acceptance HEAD={head}; overlay={len(overlay)} sha256 equal; exact files/directories", flush=True)
    return acceptance


TESTS = [skip_register_when_claims_same, registry_sha_drift_forces_register,
         verdict_change_stops, terminal_ledger_triggers_reopen,
         other_charts_archived_not_deleted, ends_with_closeout_check,
         migrated_case_root_stops, adjudication_bound_to_m3_only_stops,
         freeze_readback_no_new_revision, adjudication_bound_to_m4_archived,
         nonterminal_ignores_history_receipt, adjudication_bound_to_copy_terminal_stops,
         adjudication_dependency_in_charts_final_stops, terminal_downstream_mismatches_block,
         new_clusters_stop, final_source_branch_prebuilds_round,
         sealed_file_missing_stops, sealed_path_remapped_from_reopen, archived_claim_reference_stops,
         round_number_continues_nonterminal_ledger, dry_run_touches_nothing]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only")
    args = parser.parse_args()
    root = Path(tempfile.mkdtemp(prefix="test-stage2-reseal-")).resolve()
    print("fixtures: " + str(root), flush=True)
    seed = w2.build_closeout_case(root / "baseline")
    cases = Cases(root, seed)
    selected = [test for test in TESTS if not args.only or any(part in test.__name__ for part in args.only.split(","))]
    assert selected
    failures = []
    for test in selected:
        try:
            with test_vertical_slices():
                test(cases)
            print("ok    " + test.__name__, flush=True)
        except Exception as exc:
            failures.append(test.__name__)
            print(f"FAIL  {test.__name__}: {type(exc).__name__}: {exc}", flush=True)
    print(f"stage2_reseal: {len(selected) - len(failures)}/{len(selected)} PASS", flush=True)
    return bool(failures)


if __name__ == "__main__":
    sys.exit(main())
