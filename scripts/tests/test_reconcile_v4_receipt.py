#!/usr/bin/env python3
"""Batch 1b expected-red tests for formal cache routing and reconcile v4."""

from __future__ import annotations

import gzip
import hashlib
import importlib
import json
import os
import subprocess
import sys
import tempfile
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


def make_reconcile(case, rows, edge, meta, snapshot_slot=2):
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
    assert replay_edges.cmd_reconcile(rows, 1, mint=MINT, cache_meta_path=meta) is True
    after = sha(meta)
    receipt_path = data / "reconcile_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    return receipt_path, receipt, before, after


def current_camp_accepts(receipt_path, cutoff):
    series = receipt_path.parent / "camp_share_series.json"
    series.write_text("[]", encoding="utf-8")
    result = camp_series_provenance.registry_anchor_check(
        {"series_format": "sol-rows"}, {"inputs.reconcile_receipt": receipt_path},
        series, expected_chain="solana", expected_mint=MINT,
        expected_cutoff_slot=cutoff)
    return result == receipt_path


def main():
    red = 0
    old = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="batch1b-reconcile-", dir="/private/tmp") as raw:
        case = Path(raw)
        data = case / "data"
        data.mkdir()
        rows, edge, meta = prepare_base(data)
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
            receipt_path, receipt, before_meta, after_meta = make_reconcile(
                case, rows, edge, meta, snapshot_slot=2)

            assert receipt["gate_pass"] is True and current_camp_accepts(receipt_path, 2)
            print("RED 12 semantic-acceptance cache upper=1、snapshot slot=2 仍产 gate_pass=true 且现役 consumer 接受")
            red += 1

            assert before_meta != after_meta
            print("RED 13 semantic-mutation replay_edges reconcile 改写 base meta 的物理 sha256")
            red += 1

            # (31) Change coverage CURRENT after the receipt; current receipt and consumer ignore it.
            coverage = data / "sqd_coverage"
            coverage.mkdir()
            pointer = coverage / "CURRENT.json"
            pointer.write_text(json.dumps({"schema": "sqd-solana-coverage-pointer/v1",
                                           "probe_id": "p1"}), encoding="utf-8")
            pointer.write_text(json.dumps({"schema": "sqd-solana-coverage-pointer/v1",
                                           "probe_id": "p2"}), encoding="utf-8")
            assert "coverage_pointer" not in receipt.get("inputs", {})
            assert current_camp_accepts(receipt_path, 2)
            print("RED 31 semantic-acceptance coverage CURRENT 更新后旧 receipt 仍被现役 consumer 接受")
            red += 1

            assert all(isinstance(receipt[name], str)
                       for name in ("minted_raw", "burned_raw", "snapshot_supply_raw"))
            print("RED 33 semantic-evidence 现役 v3 receipt 三个 raw 字段为字符串且 v4 类型拒绝器不存在")
            red += 1
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
        red += expected_red("11", "validate_reconcile_v4", "v4 base/repaired 条件 inputs 深验尚未实现")

        # (32) Record generic behavior, then require the missing three-way consistency check.
        pass2 = {**null_receipt, "inputs": {}, "exit_code": 2, "gate_pass": True}
        generic_errors = receipt_validate.validate_receipt(pass2, repo_root=ROOT, case_root=case)
        assert "verdict/exit_code inconsistent" in generic_errors
        print("OBSERVED 32 receipt_validate PASS/2 => verdict/exit_code inconsistent")
        triads = [("PASS", 2, True), ("FAIL", 0, False), ("FAIL", 2, True)]
        assert all(not ((v == "PASS" and code == 0 and gate) or
                        (v == "FAIL" and code == 2 and not gate)) for v, code, gate in triads)
        red += expected_red("32", "validate_verdict_gate_triad", "verdict/exit_code/gate_pass 三元互洽尚未实现")

    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main())
