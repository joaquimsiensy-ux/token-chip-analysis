#!/usr/bin/env python3
"""Round-7 findings: fifteen independent red-before-green regressions.

EXPECTED_RED is an anti-zombie quarantine, not an xfail decorator: a quarantined
test must fail.  Once production is fixed, remove its id from EXPECTED_RED in the
same change; an unexpected pass therefore fails the suite.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
import types
from contextlib import contextmanager
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "scripts/tests"
for rel in ("scripts/report", "scripts/evm", "scripts/solana", "scripts/lib",
            "scripts/labels", "scripts/tests"):
    sys.path.insert(0, str(ROOT / rel))

EXPECTED_RED = set()
FIELDS = ["address", "chain", "name", "category", "tier", "source", "added_date",
          "evidence", "risk_flags", "merge_policy", "balance_policy",
          "source_snapshot_at", "verified_at", "status", "raw_labels"]


@contextmanager
def pushd(path):
    old = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def write_table(path, chain, **changes):
    row = dict.fromkeys(FIELDS, "")
    row.update({"address": "0x" + "1" * 40, "chain": chain, "name": "fixture",
                "category": "kol", "tier": "identity", "source": "manual",
                "added_date": "2026-08-01", "verified_at": "2026-08-06"})
    row.update(changes)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader(); writer.writerow(row)


def test_r7_01():
    """A wrapper without the current controlled-runner binding must be rejected."""
    from test_audit_release_gate import build_case
    shared = load(ROOT / "scripts/report/shared_release_receipt.py", "r7_shared")
    for mutation in ("missing", "bad-hash"):
        with tempfile.TemporaryDirectory() as td:
            case = Path(td).resolve()
            build_case(case)
            wrapper = json.loads((case / "reconciliation_report.json").read_text())
            if mutation == "missing":
                wrapper.pop("producer")
            else:
                wrapper["producer"]["sha256"] = "0" * 64
            write_json(case / "reconciliation_report.json", wrapper)
            try:
                shared.validate_sources(case)
            except ValueError as exc:
                assert "wrapper" in str(exc), exc
            else:
                raise AssertionError(f"fabricated wrapper accepted: {mutation}")


def test_r7_02():
    """curl rc=7 plus empty stdout is transport failure, never an empty success."""
    with tempfile.TemporaryDirectory() as td, pushd(td):
        write_json(Path("config.json"), {"mint": "mint-a"})
        mod = load(ROOT / "scripts/solana/anchor_sampler.py", "r7_anchor_transport")
        failed = subprocess.CompletedProcess(["curl"], 7, stdout="", stderr="connect failed")
        with mock.patch.object(mod.net.subprocess, "run", return_value=failed), \
                mock.patch.object(mod.net.time, "sleep"):
            result = mod.fetch_window(1, 2)
        assert result is None, f"transport failure returned successful payload {result!r}"


def test_r7_03():
    """Resume rows without mint/cutoff/endpoint identity must not be reused."""
    with tempfile.TemporaryDirectory() as td, pushd(td):
        root = Path(td).resolve()
        write_json(root / "config.json", {"mint": "mint-b", "ref_slot": 1000, "ref_ts": 1})
        out = root / "anchors.jsonl"
        out.write_text(json.dumps({"date": "2026-01-01", "from_slot": 10,
                                   "to_slot": 20, "ts_seen": None,
                                   "n_rows": 0, "accounts": {}}) + "\n")
        mod = load(ROOT / "scripts/solana/anchor_sampler.py", "r7_anchor_resume")
        rc = mod.main(["--start", "2026-01-01", "--end", "2026-01-01",
                       "--as-of-slot", "1000", "--out", str(out),
                       "--receipt", str(root / "receipt.json")])
        assert rc != 0, "mint-b silently reused identity-free mint-a anchor rows"


def test_r7_04():
    """Formal supply truth rejects raw override and binds inputs/context slot."""
    mod = load(ROOT / "scripts/lib/supply_truth_gate.py", "r7_supply")
    problems = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve(); out = root / "receipt.json"
        argv = ["supply_truth_gate.py", "--chain", "solana", "--mint", "MintA",
                "--as-of-block", "123", "--replay-net-raw", "100", "--out", str(out)]
        with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(mod, "fetch_onchain_supply", return_value=(100, 321)):
            rc = mod.main()
        if rc != 1 or out.exists() or not list(root.glob("receipt.error.*.json")):
            problems.append("formal --replay-net-raw was accepted without --exploration")

        explore_out = root / "explore.json"
        explore_argv = argv[:-1] + [str(explore_out), "--exploration"]
        with mock.patch.object(sys, "argv", explore_argv), \
                mock.patch.object(mod, "fetch_onchain_supply", return_value=(100, 321)):
            rc = mod.main()
        exploration = json.loads(explore_out.read_text()) if explore_out.exists() else {}
        if rc != 0 or exploration.get("mode") != "exploration" \
                or exploration.get("observed_context_slot") != 321:
            problems.append("explicit exploration raw override lacks mode/context binding")
        else:
            shared = load(ROOT / "scripts/report/shared_release_receipt.py", "r7_supply_shared")
            item = {"status": "PASS", "exit_code": 0,
                    "receipt": {"path": explore_out.name, "sha256": hashlib.sha256(
                        explore_out.read_bytes()).hexdigest()}}
            try:
                shared.validate_reconciliation_check(root, "supply_truth", item,
                                                     exploration["target"], "solana")
            except ValueError:
                pass
            else:
                problems.append("formal aggregator accepted exploration receipt")

        stats = root / "stats.json"
        write_json(stats, {"mint_total_raw": 100, "burn_total_raw": 0})
        formal_out = root / "formal.json"
        formal_argv = ["supply_truth_gate.py", "--chain", "solana", "--mint", "MintA",
                       "--as-of-block", "123", "--replay-stats", str(stats),
                       "--out", str(formal_out)]
        with mock.patch.object(sys, "argv", formal_argv), \
                mock.patch.object(mod, "fetch_onchain_supply", return_value=(100, 123)):
            rc = mod.main()
        receipt = json.loads(formal_out.read_text()) if formal_out.exists() else {}
        inputs = receipt.get("inputs") or {}
        if not any(isinstance(v, dict) and {"path", "size", "sha256"} <= set(v)
                   for v in inputs.values()):
            problems.append("receipt has no inputs file_ref")
        if rc != 0 or receipt.get("mode") != "formal" or receipt.get("observed_context_slot") != 123:
            problems.append("Solana receipt omits observed_context_slot")
    assert not problems, "; ".join(problems)


def test_r7_05():
    """A mandatory reconciliation_report/v2 needs a production writer."""
    scan = load(TESTS / "invariant_scan.py", "r7_invariant_scan")
    producers = scan.scan_actual()["receipt_producers"]
    writers = [x["script"] for x in producers if "reconciliation-report/v2" in x["schemas"]]
    assert writers, "no production script writes reconciliation-report/v2"


def test_r7_06():
    """Reverse windows fail without artifacts; gaps quarantine old formal output."""
    problems = []
    with tempfile.TemporaryDirectory() as td, pushd(td):
        root = Path(td).resolve(); write_json(root / "config.json", {"mint": "mint-a"})
        mod = load(ROOT / "scripts/solana/window_fetch.py", "r7_window")
        out = root / "reverse.jsonl"; receipt = root / "reverse_receipt.json"
        rc = mod.main(["10", "0", str(out), "--receipt", str(receipt), "--conc", "1"])
        if rc != 2 or out.exists() or receipt.exists():
            problems.append(f"reverse range rc={rc}, out={out.exists()}, receipt={receipt.exists()}")

        old = root / "old.jsonl"; old.write_text("old-formal\n", encoding="utf-8")
        gap_receipt = root / "gap_receipt.json"
        with mock.patch.object(mod, "scan_seg", return_value=([], False, [])):
            rc = mod.main(["0", "0", str(old), "--receipt", str(gap_receipt), "--conc", "1"])
        stale = list(root.glob("old.jsonl.stale.*"))
        if rc != 2 or old.exists() or not stale:
            problems.append(f"gap run did not quarantine old formal output (rc={rc}, stale={stale})")
    assert not problems, "; ".join(problems)


def _handoff_generate(case, chain, *extra):
    import test_handoff_manifest as fixture
    fixture.make_case(str(case))
    args = ["generate", "--case-dir", str(case), "--status", "READY", "--mode", "full",
            "--producer-model", "test-model", "--chain", chain, "--contract", "0x0",
            "--cutoff", "2026-08-01T00:00:00Z", "--frozen-block", "999",
            "--denominators", json.dumps({"total_supply_raw": str(10 ** 12)}), *extra]
    return fixture.run(args), fixture


def test_r7_07():
    """READY only accepts formal chains and shares the release-chain source."""
    handoff = load(ROOT / "scripts/report/handoff_manifest.py", "r7_handoff_sets")
    audit = load(ROOT / "scripts/report/audit_release_gate.py", "r7_audit_sets")
    from chain_registry import formal_ready_chains
    problems = []
    with tempfile.TemporaryDirectory() as td:
        proc, _ = _handoff_generate(Path(td).resolve(), "arbitrum")
        if proc.returncode == 0:
            problems.append("handoff generate accepted READY for exploration-only arbitrum")
    if set(handoff.READY_CHAINS) != formal_ready_chains():
        problems.append("handoff and audit formal chains differ instead of sharing the registry")
    assert not problems, "; ".join(problems)


def test_r7_08():
    """A declared PASS with nonzero exit code cannot contribute to READY."""
    with tempfile.TemporaryDirectory() as td:
        case = Path(td).resolve()
        generated, fixture = _handoff_generate(
            case, "bsc", "--gate", "x:PASS:2:accounting_mode.json")
        verified = fixture.run(["verify", "--case-dir", str(case)]) \
            if generated.returncode == 0 else generated
        assert generated.returncode != 0 or verified.returncode != 0, \
            "declared gate PASS/exit=2 survived generate and verify"


def test_r7_09():
    """Formal entity trace requires at least one valid label."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        (root / "edges.jsonl").write_text(
            json.dumps([86400, 1, 0, 0,
                        "0x0000000000000000000000000000000000000000", "0xabc", 100]) + "\n")
        write_json(root / "entities.json", {"E1": ["0xabc"]})
        write_json(root / "labels.json", {})
        proc = subprocess.run([
            sys.executable, str(ROOT / "scripts/report/entity_source_trace.py"),
            "--edges-sol", str(root / "edges.jsonl"), "--total-supply", "1000",
            "--entity-file", str(root / "entities.json"),
            "--labels-file", str(root / "labels.json"), "--out", str(root / "out.json")],
            capture_output=True, text=True)
        assert proc.returncode == 2, \
            f"formal empty-label trace accepted rc={proc.returncode}: {proc.stdout}{proc.stderr}"


def test_r7_10():
    """Archive-copy failure rolls labels and manifest back byte-for-byte."""
    mod = load(ROOT / "scripts/labels/add_labels.py", "r7_add_labels")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve(); labels = root / "labels"; labels.mkdir()
        additions = root / "additions"
        old = labels / "labels-eth.csv"
        write_table(old, "eth", name="old")
        old_bytes = old.read_bytes()
        manifest = labels / "manifest.json"; manifest.write_text('{"old":true}\n')
        manifest_bytes = manifest.read_bytes()
        src = root / "incoming.csv"; write_table(src, "eth", name="new", source="curation")
        mod.DEFAULT_LABELS_DIR = str(labels); mod.ADDITIONS_DIR = str(additions)
        calls = []

        def fake_run(args, **kwargs):
            calls.append(args)
            if "labels_manifest.py" in " ".join(map(str, args)):
                manifest.write_text('{"new":true}\n')
            return subprocess.CompletedProcess(args, 0)

        real_copy = shutil.copy

        def fail_archive(src_path, dst_path, *args, **kwargs):
            if Path(dst_path).parent == additions:
                raise OSError("archive copy injected failure")
            return real_copy(src_path, dst_path, *args, **kwargs)

        with mock.patch.object(sys, "argv", [str(ROOT / "scripts/labels/add_labels.py"), str(src)]), \
                mock.patch.object(mod.subprocess, "run", side_effect=fake_run), \
                mock.patch.object(mod.shutil, "copy", side_effect=fail_archive):
            try:
                mod.main()
            except OSError:
                pass
        assert old.read_bytes() == old_bytes and manifest.read_bytes() == manifest_bytes, \
            "archive failure left published labels/manifest changed and rollback backups gone"


def test_r7_11():
    """A staging verified_at older than publication is directional data loss."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve(); pub = root / "pub"; out = root / "out"
        for chain in ("eth", "bsc", "base", "sol", "robinhood"):
            write_table(pub / f"labels-{chain}.csv", chain, verified_at="2026-08-06")
            write_table(out / f"labels-{chain}.csv", chain,
                        verified_at="2026-08-05" if chain == "eth" else "2026-08-06")
        proc = subprocess.run([
            sys.executable, str(ROOT / "scripts/labels/roundtrip_check.py"),
            "--pub-dir", str(pub), "--out-dir", str(out), "--dump-dir", str(root)],
            capture_output=True, text=True)
        assert proc.returncode != 0, "verified_at regression was WARN-only exit 0"


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_r7_12():
    """RPC eth_chainId mismatch fails before any balance comparison."""
    from test_sixlens_receipts import recon_args, recon_fixture
    mod = load(ROOT / "scripts/evm/verify_recon.py", "r7_verify_chain")
    methods = []

    async def post(client, bucket, method, url, *, json_body=None, attempts=6):
        rpc_method = json_body.get("method"); methods.append(rpc_method)
        if rpc_method == "eth_chainId":
            return {"jsonrpc": "2.0", "id": 1, "result": "0x1"}
        return {"jsonrpc": "2.0", "id": 1, "result": hex(100)}

    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve(); paths = recon_fixture(root, closed=True); receipt = root / "receipt.json"
        import net
        with mock.patch.object(net, "_request_json", side_effect=post):
            rc = mod.main(recon_args(paths, receipt))
    assert rc != 0 and "eth_call" not in methods, \
        f"wrong-chain RPC reached balance comparison (rc={rc}, methods={methods})"


class _Pool:
    def __init__(self, *args, **kwargs):
        pass

    def call_many(self, calls):
        results = []
        for method, _params in calls:
            if method == "eth_call":
                result = hex(100)
            elif method == "eth_getTransactionReceipt":
                result = {"blockNumber": hex(10), "logs": [{
                    "address": "0xbbb",
                    "topics": [
                        "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
                        "0x" + "0" * 64,
                        "0x" + "0" * 24 + "1" * 40,
                    ],
                    "data": hex(100),
                }]}
            else:
                raise AssertionError(method)
            results.append({"ok": True, "result": result})
        return results


def test_r7_13():
    """Spotcheck binds plan target and a path/size/hash file_ref."""
    mod = load(ROOT / "scripts/lib/time_spotcheck.py", "r7_spotcheck")
    problems = []
    fake_net = types.SimpleNamespace(attested_rpc_pool=lambda *args, **kwargs: _Pool())
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        source = root / "transfers.csv"
        source.write_text(
            "block,ts,tx,from,to,value\n"
            f"10,2025-01-01T00:00:00Z,0xt1,0x{'0' * 40},0x{'1' * 40},100\n")
        produced = subprocess.run([
            sys.executable, str(ROOT / "scripts/lib/anchor_plan.py"),
            "--input", str(source), "--chain", "bsc", "--token", "0xbbb",
            "--total-supply", "100", "--decimals", "0", "--min-pct", "0",
            "--final-block", "10", "--out-dir", str(root)],
            capture_output=True, text=True)
        assert produced.returncode == 0, produced.stdout + produced.stderr
        good = root / "anchor_plan.json"
        out_bad = root / "bad_receipt.json"
        args = ["time_spotcheck.py", "--plan", str(good), "--chain", "eth",
                "--rpc", "http://fixture", "--token", "0xaaa", "--final-block", "10",
                "--out", str(out_bad)]
        with mock.patch.object(sys, "argv", args), mock.patch.dict(sys.modules, {"net": fake_net}):
            rc = mod.main()
        if rc == 0:
            problems.append("plan chain/token mismatch accepted")

        out_good = root / "good_receipt.json"
        args[args.index("--chain") + 1] = "bsc"
        args[args.index("--token") + 1] = "0xbbb"
        args[-1] = str(out_good)
        with mock.patch.object(sys, "argv", args), mock.patch.dict(sys.modules, {"net": fake_net}):
            rc = mod.main()
        receipt = json.loads(out_good.read_text()) if out_good.exists() else {}
        plan_ref = (receipt.get("inputs") or {}).get("plan")
        if rc != 0 or not isinstance(plan_ref, dict) or \
                not {"path", "size", "sha256"} <= set(plan_ref):
            problems.append("successful receipt lacks plan file_ref")
    assert not problems, "; ".join(problems)


def test_r7_14():
    """risk_flags is a trim/deduplicate/set-sort field."""
    mod = load(ROOT / "scripts/labels/roundtrip_check.py", "r7_roundtrip_flags")
    base = {field: "" for field in mod.DECISION_FIELDS}; base["risk_flags"] = "a|b"
    dup = dict(base, risk_flags="a|a|b")
    spaced = dict(base, risk_flags="a| b")
    assert mod._decision(base) == mod._decision(dup) == mod._decision(spaced), \
        f"semantic flag sets differ: {mod._decision(base)}, {mod._decision(dup)}, {mod._decision(spaced)}"


def test_r7_15():
    """Maintenance docs agree with decision-field count and three-gate transaction."""
    roundtrip = load(ROOT / "scripts/labels/roundtrip_check.py", "r7_roundtrip_docs")
    text = (ROOT / "references/labels/MAINTENANCE.md").read_text(encoding="utf-8")
    number = {6: "六", 7: "七", 8: "八"}.get(len(roundtrip.DECISION_FIELDS), str(len(roundtrip.DECISION_FIELDS)))
    section = text.split("**增量入库（免重建）与惯犯层刷新**", 1)[-1].split("**Dune 月度刷新**", 1)[0]
    assert f"{number}个决策字段" in text, \
        f"docs field count does not match DECISION_FIELDS={len(roundtrip.DECISION_FIELDS)}"
    assert "三闸" in section and all(name in section for name in ("validate", "benchmark", "manifest")), \
        "incremental transaction docs do not name validate + benchmark + manifest three gates"


CASES = {
    "R7-01": test_r7_01, "R7-02": test_r7_02, "R7-03": test_r7_03,
    "R7-04": test_r7_04, "R7-05": test_r7_05, "R7-06": test_r7_06,
    "R7-07": test_r7_07, "R7-08": test_r7_08, "R7-09": test_r7_09,
    "R7-10": test_r7_10, "R7-11": test_r7_11, "R7-12": test_r7_12,
    "R7-13": test_r7_13, "R7-14": test_r7_14, "R7-15": test_r7_15,
}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", choices=sorted(CASES), help="show one raw failure traceback")
    args = ap.parse_args(argv)
    selected = [args.show] if args.show else sorted(CASES)
    failures = []
    expected_count = 0
    for finding in selected:
        try:
            CASES[finding]()
        except Exception as exc:
            raw = traceback.format_exc()
            if finding in EXPECTED_RED:
                expected_count += 1
                print(f"EXPECTED-RED {finding}: {type(exc).__name__}: {exc}")
                if args.show:
                    print(raw, end="")
            else:
                failures.append((finding, raw))
                print(f"FAIL {finding}: {type(exc).__name__}: {exc}")
        else:
            if finding in EXPECTED_RED:
                failures.append((finding, "unexpected green; remove id from EXPECTED_RED with its fix"))
                print(f"FAIL {finding}: UNEXPECTED-GREEN while still quarantined")
            else:
                print(f"PASS {finding}")
    if failures:
        print(f"R7 regression suite FAIL: {len(failures)} item(s)")
        for finding, raw in failures:
            print(f"--- {finding} ---\n{raw}")
        return 1
    green_count = len(selected) - expected_count
    if EXPECTED_RED:
        print(f"PASS R7 expected-red quarantine: {expected_count}/{len(selected)} observed red")
    else:
        print(f"PASS R7 regression suite: {green_count}/{len(selected)} observed green; "
              "EXPECTED_RED=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
