#!/usr/bin/env python3
"""Batch 18 manifest reverse-binding exclusion and stage-2 convergence tests."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts/report"), str(ROOT / "scripts/lib"),
                str(ROOT / "scripts/tests")]

from test_handoff_manifest import (  # noqa: E402
    FRZ,
    GEN,
    make_case,
    make_provenance,
    run,
    setup_freezeable,
)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1) + "\n",
                    encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(root: Path, run_id: str, *extra: str):
    return run(["generate", "--case-dir", str(root), "--status", "READY",
                "--run-id", run_id] + GEN + list(extra))


def artifact_paths(root: Path) -> set[str]:
    return {item["path"] for item in load(root / "handoff_manifest.json")["artifacts"]}


def prepare_loop_case(root: Path):
    make_case(str(root))
    first = generate(root, "A")
    assert first.returncode == 0, first.stdout + first.stderr
    setup_freezeable(str(root))
    second = generate(root, "B")
    assert second.returncode == 0, second.stdout + second.stderr
    dump(root / "provenance_ledger.json",
         make_provenance(str(root), {"E1": ["0xabc"]}))
    return second


def test_r1_two_generates_then_trace_converge_before_freeze() -> None:
    with tempfile.TemporaryDirectory(prefix="batch18-manifest-r1-", dir="/private/tmp") as raw:
        root = Path(raw)
        second = prepare_loop_case(root)
        verify = run(["verify", "--case-dir", str(root)])
        freeze = run(["freeze", "--case-dir", str(root)] + FRZ)
        if verify.returncode or freeze.returncode:
            raise AssertionError(
                "R1 修前 manifest/账本反绑不收敛："
                + json.dumps({
                    "generate_stderr": second.stderr,
                    "verify_rc": verify.returncode,
                    "verify": verify.stdout + verify.stderr,
                    "freeze_rc": freeze.returncode,
                    "freeze": freeze.stdout + freeze.stderr,
                }, ensure_ascii=False))
        frozen = load(root / "entity_freeze.json")
        assert frozen["provenance_ledger_sha256"] == sha(
            root / "provenance_ledger.json")


def test_n1_ledger_is_skipped_with_visible_notice_and_ready_preserved() -> None:
    with tempfile.TemporaryDirectory(prefix="batch18-manifest-n1-", dir="/private/tmp") as raw:
        root = Path(raw)
        second = prepare_loop_case(root)
        assert "provenance_ledger.json" not in artifact_paths(root)
        assert load(root / "handoff_manifest.json")["status"] == "READY"
        assert "跳过反绑产物 provenance_ledger.json" in second.stderr, second.stderr


def test_n2_explicit_include_and_gate_reject_reverse_binding() -> None:
    for extra in (
            ("--include", "provenance_ledger.json"),
            ("--gate", "x:PASS:0:provenance_ledger.json")):
        with tempfile.TemporaryDirectory(prefix="batch18-manifest-n2-", dir="/private/tmp") as raw:
            root = Path(raw)
            make_case(str(root))
            dump(root / "provenance_ledger.json", {"input_binding": {}})
            proc = generate(root, "explicit", *extra)
            combined = proc.stdout + proc.stderr
            assert proc.returncode == 2, combined
            assert "反绑产物禁止进入 manifest: provenance_ledger.json" in combined, combined
            assert "产物不存在" not in combined, combined


def test_n3_tampered_ledger_still_blocks_freeze() -> None:
    with tempfile.TemporaryDirectory(prefix="batch18-manifest-n3-", dir="/private/tmp") as raw:
        root = Path(raw)
        prepare_loop_case(root)
        ledger = load(root / "provenance_ledger.json")
        ledger["input_binding"]["handoff_manifest"]["sha256"] = "0" * 64
        dump(root / "provenance_ledger.json", ledger)
        proc = run(["freeze", "--case-dir", str(root)] + FRZ)
        assert proc.returncode == 2, proc.stdout + proc.stderr


def test_n4_legacy_manifest_ledger_binding_still_verifies_hash() -> None:
    with tempfile.TemporaryDirectory(prefix="batch18-manifest-n4-", dir="/private/tmp") as raw:
        root = Path(raw)
        prepare_loop_case(root)
        ledger = root / "provenance_ledger.json"
        manifest_path = root / "handoff_manifest.json"
        manifest = load(manifest_path)
        manifest["artifacts"].append({
            "path": "provenance_ledger.json", "bytes": ledger.stat().st_size,
            "hash_algo": "sha256", "sha256": sha(ledger),
        })
        dump(manifest_path, manifest)
        good = run(["verify", "--case-dir", str(root)])
        assert good.returncode == 0, good.stdout + good.stderr
        ledger.write_text(ledger.read_text(encoding="utf-8") + "\n",
                          encoding="utf-8")
        bad = run(["verify", "--case-dir", str(root)])
        assert bad.returncode == 2 and "漂移" in (bad.stdout + bad.stderr), \
            bad.stdout + bad.stderr


def test_n5_final_distribution_is_skipped_but_initial_remains_required() -> None:
    with tempfile.TemporaryDirectory(prefix="batch18-manifest-n5-", dir="/private/tmp") as raw:
        root = Path(raw)
        make_case(str(root))
        rel = "dist_rounds/round_1/distribution_scan.json"
        dump(root / rel, {"stage": "final", "input_binding": {
            "handoff_manifest": {"run_id": "A", "sha256": "0" * 64}}})
        data_map = load(root / "data_map.json")
        data_map["files"].append({"path": rel, "source": "test"})
        dump(root / "data_map.json", data_map)
        proc = generate(root, "final-skip")
        assert proc.returncode == 0, proc.stdout + proc.stderr
        paths = artifact_paths(root)
        assert rel not in paths and "distribution_scan.json" in paths, paths
        assert f"跳过反绑产物 {rel}" in proc.stderr, proc.stderr
        explicit = generate(root, "final-explicit", "--include", rel)
        combined = explicit.stdout + explicit.stderr
        assert explicit.returncode == 2, combined
        assert f"反绑产物禁止进入 manifest: {rel}" in combined, combined


def test_n6_same_basename_without_final_binding_is_included() -> None:
    with tempfile.TemporaryDirectory(prefix="batch18-manifest-n6-", dir="/private/tmp") as raw:
        root = Path(raw)
        make_case(str(root))
        rel = "data/x/distribution_scan.json"
        dump(root / rel, {"stage": "final", "input_binding": {}})
        data_map = load(root / "data_map.json")
        data_map["files"].append({"path": rel, "source": "test"})
        dump(root / "data_map.json", data_map)
        proc = generate(root, "ordinary")
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert rel in artifact_paths(root), artifact_paths(root)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv not in ([], ["--r1"]):
        raise SystemExit("usage: test_batch18_manifest_stage2_loop.py [--r1]")
    tests = [test_r1_two_generates_then_trace_converge_before_freeze]
    if not argv:
        tests += [
            test_n1_ledger_is_skipped_with_visible_notice_and_ready_preserved,
            test_n2_explicit_include_and_gate_reject_reverse_binding,
            test_n3_tampered_ledger_still_blocks_freeze,
            test_n4_legacy_manifest_ledger_binding_still_verifies_hash,
            test_n5_final_distribution_is_skipped_but_initial_remains_required,
            test_n6_same_basename_without_final_binding_is_included,
        ]
    failed = []
    for test in tests:
        try:
            test()
        except Exception as exc:
            failed.append((test.__name__, exc))
            print(f"FAIL {test.__name__}: {type(exc).__name__}: {exc}")
        else:
            print(f"PASS {test.__name__}")
    if failed:
        print(f"FAIL batch18 manifest stage2 loop: {len(failed)}/{len(tests)}")
        return 1
    print(f"PASS batch18 manifest stage2 loop: {len(tests)}/{len(tests)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
