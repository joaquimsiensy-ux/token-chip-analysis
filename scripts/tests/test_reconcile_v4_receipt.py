#!/usr/bin/env python3
"""Batch 1b expected-red tests for formal cache routing and reconcile v4."""

from __future__ import annotations

import gzip
import hashlib
import importlib
import io
import json
import os
import subprocess
import sys
import tempfile
from contextlib import redirect_stderr
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
for sub in ("tests", "solana", "report", "lib"):
    sys.path.insert(0, str(ROOT / "scripts" / sub))

import audit_closed_accounts  # noqa: E402
import camp_series_provenance  # noqa: E402
import curve_cost  # noqa: E402
import duckdb  # noqa: E402
import entity_source_trace  # noqa: E402
import flow_anomaly_scan  # noqa: E402
import receipt_validate  # noqa: E402
import replay_edges  # noqa: E402
import shared_release_receipt as shared  # noqa: E402
import solana_exact_validate as exact  # noqa: E402
import sqd_cache_identity  # noqa: E402
import wave_scan  # noqa: E402
from sqd_v4_test_fixture import FETCH_SHA256, MINT  # noqa: E402


TARGET = "scripts.lib.solana_exact_validate"
ZERO = "0x" + "0" * 40
OWNER = "So1BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ref(path, shown=None):
    path = Path(path)
    return {"path": shown or str(path), "size": path.stat().st_size, "sha256": sha(path)}


def write_edges(path, rows):
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def logical_digest(rows):
    digest = hashlib.sha256()
    for row in rows:
        digest.update((json.dumps(row, ensure_ascii=False) + "\n").encode())
    return digest.hexdigest()


def meta_for(rows):
    return {
        "schema": "sqd-solana-cache/v4", "version": 4, "mint": MINT,
        "endpoint": "https://portal.sqd.dev", "endpoint_sha256": "1" * 64,
        "collector": "fetch_sqd_transfers_v2.py/v4", "collector_sha256": FETCH_SHA256,
        "edge_schema": ["ts", "slot", "tx_index", "instr_index", "from", "to", "amt"],
        "edge_semantics": "owner-net-greedy", "order_granularity": "transaction",
        "order_exact": False, "dedupe_identity": "slot-txindex-digest/v1",
        "supply_delta_source": "tokenBalances-owner-net", "from_slot": 1,
        "finalized_upper_slot": 1, "edge_logical_sha256": logical_digest(rows),
        "edge_rows": len(rows),
    }


def cache_paths(data):
    key = hashlib.sha256(MINT.encode()).hexdigest()
    return data / f"soltx-{key}.jsonl.gz", data / f"soltx-{key}.meta.json"


def expected_red(item, symbol, detail):
    try:
        module = importlib.import_module(TARGET)
        if not hasattr(module, symbol):
            raise AttributeError(symbol)
    except (ImportError, AttributeError):
        print(f"EXPECTED_RED: {TARGET}/{symbol} 未实现")
        print(f"RED {item} missing-mechanism {detail}")
        return 1
    print(f"GREEN {item} implemented {symbol} 已实现")
    return 0


def prepare_base(data):
    rows = [[100, 1, 0, -1, ZERO, OWNER, 100]]
    edge, meta = cache_paths(data)
    write_edges(edge, rows)
    meta.write_text(json.dumps(meta_for(rows)), encoding="utf-8")
    return rows, edge, meta


def coverage_missing_precedes_large_edge_load(case):
    data = case / "data"
    data.mkdir(parents=True)
    _rows, edge, _meta = prepare_base(data)
    # 大文件只作顺序哨兵；缺 coverage 时不得读取或解析其内容。
    edge.write_bytes(b"x" * (8 * 1024 * 1024))
    (data / "holders_snapshot_meta.json").write_text(
        json.dumps({"schema": "solana-holder-snapshot-v2"}), encoding="utf-8")

    original_load_edges = replay_edges.load_edges
    original_argv = sys.argv

    def forbidden_load_edges(*_args, **_kwargs):
        raise AssertionError("edges loaded before cheap preflight")

    replay_edges.load_edges = forbidden_load_edges
    sys.argv = [
        str(ROOT / "scripts/solana/replay_edges.py"), "reconcile",
        "--mint", MINT, "--case-root", str(case), "--as-of-slot", "1",
        "--receipt", "data/reconcile_receipt.batch5c-test.json", "--no-labels",
    ]
    stderr = io.StringIO()
    try:
        with redirect_stderr(stderr):
            exit_code = replay_edges.main()
    finally:
        replay_edges.load_edges = original_load_edges
        sys.argv = original_argv

    assert exit_code == 2
    assert "coverage 强制输入缺失: data/sqd_coverage/CURRENT.json" in stderr.getvalue()
    assert not (data / "reconcile_receipt.batch5c-test.json").exists()
    print("GREEN batch5c coverage 缺件在大边文件 load_edges 前 exit 2")


def write_coverage(case):
    parent = case / "data/sqd_coverage"
    parent.mkdir(parents=True, exist_ok=True)
    counts_raw = bytes([3])
    counts_bytes = gzip.compress(counts_raw, mtime=0)
    ledger_row = {
        "seq": 0, "ok": True, "counts_coverage": True,
        "from": 1, "to": 1, "slots_covered": 1, "provider": "SQD",
        "empty_response": False, "returned_from": 1, "returned_to": 1,
        "n_blocks": 1,
    }
    ledger_bytes = (json.dumps(ledger_row, sort_keys=True) + "\n").encode()
    producer = {"path": "scripts/solana/sqd_coverage_probe.py",
                "sha256": sha(ROOT / "scripts/solana/sqd_coverage_probe.py")}
    metadata = {"dataset_id": "solana-mainnet", "start_block": 0,
                "real_time": True}
    classified = exact.classify_four_states(counts_raw, 1)
    coverage = {
        "schema": exact.COVERAGE_SCHEMA, "version": 1, "chain": "solana",
        "mint": MINT, "producer": producer,
        "sqd": {"endpoint_fingerprint": "1" * 64,
                "dataset": "solana-mainnet", "metadata_normalized": metadata,
                "metadata_sha256": exact.sha256_bytes(exact.canonical_json(metadata)),
                "finalized_head_at_scan": 1, "query_body_sha256": "2" * 64},
        "scan_ranges": [{"from_slot": 1, "to_slot": 1, "mode": "full"}],
        "sample_ranges": [], "era_params": dict(exact.ERA_PARAMS),
        "slot_counts": {"path": "slot_counts.bin.gz", "size": len(counts_bytes),
                        "sha256": hashlib.sha256(counts_bytes).hexdigest(),
                        "from_slot": 1, "to_slot": 1,
                        "encoding": exact.COUNT_ENCODING},
        "skipped_confirmation": None, "shared_map": None,
        "ledger": {"path": "ledger.jsonl", "size": len(ledger_bytes),
                   "sha256": hashlib.sha256(ledger_bytes).hexdigest(), "requests": 1,
                   "success_ranges_sha256": exact.sha256_bytes(
                       exact.canonical_json([[1, 1]]))},
        "summary": classified["summary"],
        "candidate_slots": classified["candidate_slots"],
        "verdict": classified["verdict"], "probe_id": "",
    }
    coverage["probe_id"] = exact.compute_probe_id(coverage)
    generation = parent / coverage["probe_id"]
    generation.mkdir()
    counts = generation / "slot_counts.bin.gz"
    ledger = generation / "ledger.jsonl"
    coverage_path = generation / "coverage_map.json"
    counts.write_bytes(counts_bytes)
    ledger.write_bytes(ledger_bytes)
    coverage_path.write_text(json.dumps(coverage), encoding="utf-8")

    def case_ref(path):
        return {"path": path.relative_to(case).as_posix(),
                "size": path.stat().st_size, "sha256": sha(path)}

    pointer = {
        "schema": exact.COVERAGE_POINTER_SCHEMA,
        "target": {"chain": "solana", "token": MINT, "as_of_block": 1},
        "mode": "formal", "verdict": "PASS", "exit_code": 0,
        "producer": producer,
        "inputs": {"coverage_map": case_ref(coverage_path),
                   "slot_counts": case_ref(counts), "ledger": case_ref(ledger)},
        "probe_id": coverage["probe_id"], "supersedes": None,
        "published_at": "2026-08-23T00:00:00Z",
    }
    pointer_path = parent / "CURRENT.json"
    pointer_path.write_text(json.dumps(pointer), encoding="utf-8")
    checked = exact.validate_coverage(case, coverage_path, pointer_path, 1, 1)
    assert checked["ok"], checked["reasons"]
    return pointer_path


def prepare_complete_case(case):
    data = case / "data"
    data.mkdir(parents=True)
    rows, edge, meta = prepare_base(data)
    write_coverage(case)
    owners = data / "holders_owners.json"
    owners.write_text(json.dumps({OWNER: 100}), encoding="utf-8")
    snapshot = data / "holders_snapshot_meta.json"
    snapshot.write_text(json.dumps({
        "schema": "solana-holder-snapshot-v2", "mint": MINT,
        "target": {"chain": "solana", "token": MINT, "as_of_block": 1},
        "closed": True, "supply_raw": "100",
        "outputs": {"holders_owners": ref(owners, owners.name)},
    }), encoding="utf-8")
    return rows, edge, meta


def invoke_reconcile_main(case, receipt):
    original_argv = sys.argv
    sys.argv = [
        str(ROOT / "scripts/solana/replay_edges.py"), "reconcile",
        "--mint", MINT, "--case-root", str(case), "--as-of-slot", "1",
        "--receipt", receipt, "--no-labels",
    ]
    stderr = io.StringIO()
    try:
        with redirect_stderr(stderr):
            try:
                exit_code = replay_edges.main()
            except SystemExit as exc:
                exit_code = exc.code
    finally:
        sys.argv = original_argv
    return exit_code, stderr.getvalue()


def case_root_symlink_semantics():
    # macOS: /tmp 是 /private/tmp 的系统级 symlink；祖先别名不得误杀真实案根。
    assert Path("/tmp").is_symlink(), "该回归要求 macOS /tmp -> /private/tmp"
    with tempfile.TemporaryDirectory(prefix="batch5d-macos-ancestor-",
                                     dir="/tmp") as raw:
        case = Path(raw)
        _rows, edge, meta = prepare_complete_case(case)
        resolved_edge, resolved_meta, _kind, _gid, _binding = \
            replay_edges.resolve_formal_cache(MINT, case)
        assert resolved_edge == edge.resolve() and resolved_meta == meta.resolve()

        con = duckdb.connect(":memory:")
        try:
            loaded, _binding = wave_scan.load_sol(
                con, str(edge), cache_meta_path=str(meta), expected_mint=MINT,
                case_root=case)
            assert loaded == 1
        finally:
            con.close()

        exit_code, stderr = invoke_reconcile_main(
            case, "data/reconcile_receipt.batch5d-test.json")
        assert exit_code == 0, stderr
        assert (case / "data/reconcile_receipt.batch5d-test.json").is_file()

    with tempfile.TemporaryDirectory(prefix="batch5d-self-link-",
                                     dir="/private/tmp") as raw:
        parent = Path(raw)
        real_case = parent / "real-case"
        real_case.mkdir()
        prepare_complete_case(real_case)
        link = parent / "case-alias"
        link.symlink_to(real_case, target_is_directory=True)
        exit_code, stderr = invoke_reconcile_main(
            link, "data/reconcile_receipt.batch5d-link-test.json")
        assert exit_code == 2, (exit_code, stderr)
        assert "BLOCK: case_root itself must not be a symlink" in stderr
        assert not (real_case / "data/reconcile_receipt.batch5d-link-test.json").exists()
    print("GREEN batch5d macOS symlink 祖先合法，案根自身 symlink clean exit 2")


def containment_alias_semantics():
    """Batch 5f: containment compares canonical paths without weakening escape guards."""
    with tempfile.TemporaryDirectory(prefix="batch5f-containment-",
                                     dir="/private/tmp") as raw:
        parent = Path(raw)
        real_case = parent / "real"
        real_case.mkdir()
        prepare_complete_case(real_case)
        exit_code, stderr = invoke_reconcile_main(
            real_case, "data/reconcile_receipt.batch5f-test.json")
        assert exit_code == 0, stderr

        alias = parent / "alias"
        alias.symlink_to(real_case, target_is_directory=True)
        owners = real_case / "data/holders_owners.json"
        receipt = real_case / "data/reconcile_receipt.batch5f-test.json"

        # 外部显示路径含 alias，但实物与 resolved 案根相同，应视为案内。
        assert exact._safe_case_path(alias, "data/holders_owners.json") == owners.resolve()
        owner_ref = ref(owners, str(alias / "data/holders_owners.json"))
        assert shared._bound_case_ref(alias, owner_ref, "alias owners") == owners.resolve()
        checked = exact.validate_reconcile_receipt_deep(
            alias / "data/reconcile_receipt.batch5f-test.json", case_root=alias)
        assert checked["ok"], checked["reasons"]

        outside = parent / "outside.json"
        outside.write_text(json.dumps({OWNER: 100}), encoding="utf-8")
        escaped = real_case / "data/escaped-owner.json"
        escaped.symlink_to(outside)
        try:
            exact._safe_case_path(alias, "../outside.json")
        except ValueError as exc:
            assert "escapes case root" in str(exc)
        else:
            raise AssertionError("_safe_case_path accepted ../ escape")
        try:
            exact._safe_case_path(alias, "data/escaped-owner.json")
        except ValueError as exc:
            assert "symlink" in str(exc)
        else:
            raise AssertionError("_safe_case_path accepted file symlink to outside")
        try:
            shared._bound_case_ref(
                alias, ref(outside, str(alias / "data/escaped-owner.json")),
                "escaped owners")
        except ValueError as exc:
            assert "symlink" in str(exc) or "escapes case root" in str(exc)
        else:
            raise AssertionError("shared containment accepted file symlink to outside")

        mutant = json.loads(receipt.read_text(encoding="utf-8"))
        mutant["inputs"]["holders_owners"] = ref(
            outside, "data/escaped-owner.json")
        mutant_path = real_case / "data/reconcile_receipt.batch5f-escape.json"
        mutant_path.write_text(json.dumps(mutant), encoding="utf-8")
        escaped_checked = exact.validate_reconcile_receipt_deep(
            mutant_path, case_root=alias)
        assert not escaped_checked["ok"] and any(
            "symlink" in reason or "escapes case root" in reason
            for reason in escaped_checked["reasons"]), escaped_checked["reasons"]
        outside_checked = exact.validate_reconcile_receipt_deep(
            outside, case_root=alias)
        assert not outside_checked["ok"] and any(
            "escapes case root" in reason for reason in outside_checked["reasons"])
    print("GREEN batch5f alias containment canonicalized；../ 与案外 symlink 仍拒")


def explicit_path_rejection(case, rows, edge, meta):
    copied = case / "copied-base"
    copied.mkdir()
    copied_edge, copied_meta = cache_paths(copied)
    copied_edge.write_bytes(edge.read_bytes())
    copied_meta.write_bytes(meta.read_bytes())

    rejected = []
    for name, loader in (("wave", wave_scan.load_sol), ("flow", flow_anomaly_scan.load_sol),
                         ("entity", entity_source_trace.load_sol)):
        con = duckdb.connect(":memory:")
        try:
            try:
                loader(con, str(copied_edge), cache_meta_path=str(copied_meta),
                       expected_mint=MINT, case_root=case)
            except SystemExit as exc:
                if exc.code == 2:
                    rejected.append(name)
        finally:
            con.close()

    curve_rows, curve_binding = curve_cost.load_edges(MINT, case)
    replay_rows, replay_meta, replay_binding = replay_edges.load_edges(
        MINT, case_root=case)
    assert curve_rows == replay_rows == rows and replay_meta == meta
    assert curve_binding == replay_binding
    rejected += ["curve", "replay-evolution"]

    explicit = audit_closed_accounts.resolve_edge_source(
        MINT, explicit_edges=copied_edge, case_root=case)
    assert explicit == (copied_edge, None, False, "explicit-edges")
    rejected.append("audit_closed-nonformal")
    assert rejected == ["wave", "flow", "entity", "curve", "replay-evolution",
                        "audit_closed-nonformal"]
    return copied, copied_edge, copied_meta


def make_reconcile(case, rows, edge, meta, snapshot_slot=1, as_of_slot=None):
    data = case / "data"
    owners = data / "holders_owners.json"
    owners.write_text(json.dumps({OWNER: 100}), encoding="utf-8")
    owner_ref = ref(owners, owners.name)
    snapshot = data / "holders_snapshot_meta.json"
    snapshot.write_text(json.dumps({
        "schema": "solana-holder-snapshot-v2", "mint": MINT,
        "target": {"chain": "solana", "token": MINT, "as_of_block": snapshot_slot},
        "closed": True, "supply_raw": "100", "outputs": {"holders_owners": owner_ref},
    }), encoding="utf-8")
    before = sha(meta)
    _edge, _meta, _kind, _gid, binding = replay_edges.resolve_formal_cache(MINT, case)
    result = replay_edges.cmd_reconcile(
        rows, 1, mint=MINT, cache_meta_path=meta, case_root=case,
        as_of_slot=snapshot_slot if as_of_slot is None else as_of_slot,
        edge_source_binding=binding)
    after = sha(meta)
    receipt_path = data / "reconcile_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    return receipt_path, receipt, before, after, result


def current_camp_accepts(receipt_path, cutoff):
    series = receipt_path.parent / "camp_share_series.json"
    series.write_text("[]", encoding="utf-8")
    result = camp_series_provenance.registry_anchor_check(
        {"series_format": "sol-rows", "edge_source_binding":
         json.loads(receipt_path.read_text())["edge_source_binding"]},
        {"inputs.reconcile_receipt": receipt_path},
        series, expected_chain="solana", expected_mint=MINT,
        expected_cutoff_slot=cutoff)
    return result == receipt_path


def main():
    red = 0
    old = Path.cwd()
    case_root_symlink_semantics()
    containment_alias_semantics()
    with tempfile.TemporaryDirectory(prefix="batch5c-cheap-preflight-",
                                     dir="/private/tmp") as raw:
        coverage_missing_precedes_large_edge_load(Path(raw))
    with tempfile.TemporaryDirectory(prefix="batch1b-reconcile-", dir="/private/tmp") as raw:
        case = Path(raw)
        data = case / "data"
        data.mkdir()
        rows, edge, meta = prepare_base(data)
        pointer = write_coverage(case)
        copied, copied_edge, copied_meta = explicit_path_rejection(case, rows, edge, meta)
        print("GREEN 9 replay/curve/wave/flow/entity 正式入口拒绕 resolver；"
              "audit_closed 显式 --edges 强制 non-formal")

        # (17) The v2 identity gate accepts only the canonical resolver path.
        sqd_cache_identity.validate_cache_meta_v2(
            json.loads(meta.read_text(encoding="utf-8")), MINT,
            case_root=case, meta_path=meta)
        try:
            sqd_cache_identity.validate_cache_meta_v2(
                json.loads(copied_meta.read_text(encoding="utf-8")), MINT,
                case_root=case, meta_path=copied_meta)
        except ValueError:
            print("GREEN 17 validate_cache_meta_v2 拒绝正式路径集合外复制 meta")
        else:
            print("RED 17 semantic-acceptance validate_cache_meta_v2 接受正式路径集合外复制 meta")
            red += 1

        # (23) No --case-root and a symlinked case root are both rejected.
        help_run = subprocess.run([sys.executable, str(ROOT / "scripts/report/wave_scan.py"), "--help"],
                                  text=True, capture_output=True)
        assert help_run.returncode == 0 and "--case-root" in help_run.stdout
        con = duckdb.connect(":memory:")
        try:
            try:
                wave_scan.load_sol(
                    con, str(edge), cache_meta_path=str(meta), expected_mint=MINT)
            except SystemExit as exc:
                assert exc.code == 2
            else:
                raise AssertionError("wave formal loader accepted missing case_root")
        finally:
            con.close()
        link = case / "linked-case"
        link.symlink_to(case, target_is_directory=True)
        con = duckdb.connect(":memory:")
        try:
            try:
                wave_scan.load_sol(
                    con, str(link / "data" / edge.name),
                    cache_meta_path=str(link / "data" / meta.name),
                    expected_mint=MINT, case_root=link)
            except SystemExit as exc:
                assert exc.code == 2
            else:
                raise AssertionError("wave formal loader accepted symlink case_root")
        finally:
            con.close()
        print("GREEN 23 wave_scan 缺 --case-root 与 symlink 案根均拒收")

        os.chdir(case)
        try:
            before_meta = sha(meta)
            try:
                make_reconcile(case, rows, edge, meta, snapshot_slot=2, as_of_slot=2)
            except ValueError as exc:
                assert "--as-of-slot" in str(exc)
            else:
                raise AssertionError("upper≠as-of was accepted")
            assert not (data / "reconcile_receipt.json").exists()
            assert before_meta == sha(meta)
            print("GREEN 12 upper≠snapshot/as-of 在生成 receipt 前硬拒")

            print("GREEN 13 replay_edges reconcile 不再回写 base meta")

            original_meta = json.loads(meta.read_text(encoding="utf-8"))
            mismatched_meta = dict(original_meta)
            mismatched_meta["endpoint_sha256"] = "9" * 64
            meta.write_text(json.dumps(mismatched_meta), encoding="utf-8")
            try:
                make_reconcile(case, rows, edge, meta, snapshot_slot=1, as_of_slot=1)
            except ValueError as exc:
                assert "endpoint 指纹" in str(exc)
            else:
                raise AssertionError("coverage/cache SQD endpoint 指纹不一致仍签出 receipt")
            meta.write_text(json.dumps(original_meta), encoding="utf-8")
            print("GREEN coverage SQD endpoint 指纹不一致 fail-closed")

            receipt_path, receipt, before_meta, after_meta, result = make_reconcile(
                case, rows, edge, meta, snapshot_slot=1, as_of_slot=1)
            assert result is True and receipt["gate_pass"] is True
            checked = exact.validate_reconcile_receipt_deep(receipt_path, case_root=case)
            assert checked["ok"], checked["reasons"]
            assert current_camp_accepts(receipt_path, 1)

            # Batch 10: wrapper observes slot 2 while exact receipt remains bound to
            # cache finalized_upper_slot 1.  Only this Solana fifth check may differ.
            item = {"status": "PASS", "exit_code": 0,
                    "receipt": ref(receipt_path, "data/reconcile_receipt.json")}
            observed_target = {"chain": "solana", "token": MINT,
                               "as_of_block": 2}
            accepted = shared.validate_reconciliation_check(
                case, "exact_reconcile", item, observed_target, "solana")
            assert accepted["target"]["as_of_block"] == 1

            for mismatched_target in (
                    {"chain": "bsc", "token": MINT, "as_of_block": 2},
                    {"chain": "solana", "token": OWNER, "as_of_block": 2}):
                try:
                    shared.validate_reconciliation_check(
                        case, "exact_reconcile", item, mismatched_target, "solana")
                except ValueError as exc:
                    assert "must match wrapper chain/token" in str(exc)
                else:
                    raise AssertionError("shared validator accepted exact target mismatch")

            try:
                shared.validate_reconciliation_check(
                    case, "exact_reconcile", item,
                    {"chain": "solana", "token": MINT, "as_of_block": 0},
                    "solana")
            except ValueError as exc:
                assert "must not be later than the observed slot" in str(exc)
            else:
                raise AssertionError("shared validator accepted future exact receipt")

            stale_slot_receipt = dict(receipt)
            stale_slot_receipt["target"] = dict(receipt["target"])
            stale_slot_receipt["target"]["as_of_block"] = 0
            stale_slot_path = data / "wrong-cache-slot-receipt.json"
            stale_slot_path.write_text(json.dumps(stale_slot_receipt), encoding="utf-8")
            stale_slot_check = exact.validate_reconcile_receipt_deep(
                stale_slot_path, case_root=case)
            assert not stale_slot_check["ok"] and any(
                "finalized_upper_slot" in reason
                for reason in stale_slot_check["reasons"]), stale_slot_check["reasons"]
            print("GREEN batch10 exact target 放宽仅限冻结点≤观测点；"
                  "chain/token/future/cache-upper 错配均拒")

            # (31) Change coverage CURRENT after the receipt; current receipt and consumer ignore it.
            current = json.loads(pointer.read_text())
            current["published_at"] = "2026-08-23T00:00:01Z"
            pointer.write_text(json.dumps(current), encoding="utf-8")
            stale = exact.validate_reconcile_receipt_deep(receipt_path, case_root=case)
            assert not stale["ok"] and any("coverage_pointer" in reason
                                            or "sha256 mismatch" in reason
                                            for reason in stale["reasons"])
            try:
                current_camp_accepts(receipt_path, 1)
            except camp_series_provenance.SeriesProvenanceError:
                pass
            else:
                raise AssertionError("camp accepted stale coverage pointer")
            print("GREEN 31 coverage CURRENT 更新后旧 receipt 被独立深验与 camp 拒绝")

            current["published_at"] = "2026-08-23T00:00:00Z"
            pointer.write_text(json.dumps(current), encoding="utf-8")
            raw_mutant = dict(receipt)
            raw_mutant["minted_raw"] = str(raw_mutant["minted_raw"])
            mutant_path = data / "raw-string-receipt.json"
            mutant_path.write_text(json.dumps(raw_mutant), encoding="utf-8")
            raw_checked = exact.validate_reconcile_receipt_deep(
                mutant_path, case_root=case)
            assert not raw_checked["ok"] and any("minted_raw" in reason
                                                  for reason in raw_checked["reasons"])
            print("GREEN 33 v4 raw 字符串被独立深验拒绝")
        finally:
            os.chdir(old)

        # (11) Generic envelope validator rejects null, but the v4 schema-specific validator is absent.
        null_receipt = {
            "schema": "solana-reconcile/v4",
            "target": {"chain": "solana", "token": MINT, "as_of_block": 1},
            "mode": "formal", "verdict": "PASS", "exit_code": 0,
            "producer": {"path": "scripts/solana/replay_edges.py", "sha256": sha(ROOT / "scripts/solana/replay_edges.py")},
            "inputs": {"repair_bundle": None},
        }
        null_errors = receipt_validate.validate_receipt(null_receipt, repo_root=ROOT, case_root=case)
        assert any("repair_bundle" in error for error in null_errors)
        print("OBSERVED 11 receipt_validate generic envelope 拒绝 repair_bundle:null")
        checked_null = exact.validate_reconcile_v4(null_receipt)
        assert not checked_null["ok"] and any("null" in reason or "key set" in reason
                                               for reason in checked_null["reasons"])
        print("GREEN 11 v4 base/repaired 条件 inputs 拒绝 repair_bundle:null")

        # (32) Record generic behavior, then require the missing three-way consistency check.
        pass2 = {**null_receipt, "inputs": {}, "exit_code": 2, "gate_pass": True}
        generic_errors = receipt_validate.validate_receipt(pass2, repo_root=ROOT, case_root=case)
        assert "verdict/exit_code inconsistent" in generic_errors
        print("OBSERVED 32 receipt_validate PASS/2 => verdict/exit_code inconsistent")
        triads = [("PASS", 2, True), ("FAIL", 0, False), ("FAIL", 2, True)]
        assert all(not ((v == "PASS" and code == 0 and gate) or
                        (v == "FAIL" and code == 2 and not gate)) for v, code, gate in triads)
        assert all(not exact.validate_verdict_gate_triad(v, code, gate)
                   for v, code, gate in triads)
        assert exact.validate_verdict_gate_triad("PASS", 0, True)
        assert exact.validate_verdict_gate_triad("FAIL", 2, False)
        print("GREEN 32 verdict/exit_code/gate_pass 三元互洽")

    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main())
