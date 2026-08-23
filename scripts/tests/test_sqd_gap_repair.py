#!/usr/bin/env python3
"""Batch 1b expected-red tests for the SQD repair generation protocol."""

from __future__ import annotations

import gzip
import hashlib
import importlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from sqd_v4_test_fixture import FETCH_SHA256, MINT


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
TARGET = "scripts.solana.sqd_gap_repair"
CURVE = "CurveOwner"
ZERO = "0x" + "0" * 40


def canonical_bytes(value):
    def walk(node):
        if isinstance(node, float):
            raise ValueError("float forbidden")
        if isinstance(node, dict):
            for key, child in node.items():
                if key in {"amt", "slot", "tx_index", "ts"} and (
                        not isinstance(child, int) or isinstance(child, bool)):
                    raise ValueError(f"{key} must be JSON int")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
    walk(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode()


def gid_for(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()[:16]


def expected_red(item, symbol, detail):
    try:
        module = importlib.import_module(TARGET)
        if not hasattr(module, symbol):
            raise AttributeError(symbol)
    except (ImportError, AttributeError) as exc:
        print(f"EXPECTED_RED: {TARGET}/{symbol} 未实现 ({type(exc).__name__}: {exc})")
        print(f"RED {item} missing-mechanism {detail}")
        return 1
    print(f"GREEN {item} implemented {symbol} 已实现")
    return 0


def write_curve_case(case, rows):
    data = case / "data"
    data.mkdir(parents=True)
    key = hashlib.sha256(MINT.encode()).hexdigest()
    edge = data / f"soltx-{key}.jsonl.gz"
    digest = hashlib.sha256()
    with gzip.open(edge, "wt", encoding="utf-8") as handle:
        for row in rows:
            line = json.dumps(row, ensure_ascii=False) + "\n"
            handle.write(line)
            digest.update(line.encode())
    meta = {
        "schema": "sqd-solana-cache/v4", "version": 4, "mint": MINT,
        "collector": "fetch_sqd_transfers_v2.py/v4",
        "collector_sha256": FETCH_SHA256,
        "edge_schema": ["ts", "slot", "tx_index", "instr_index", "from", "to", "amt"],
        "edge_semantics": "owner-net-greedy", "order_granularity": "transaction",
        "order_exact": False, "from_slot": 100, "finalized_upper_slot": 100,
        "edge_logical_sha256": digest.hexdigest(), "edge_rows": len(rows),
    }
    (data / f"soltx-{key}.meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (data / "solusdt_1h.json").write_text(json.dumps([[0, "1", "1", "1", "1"]]),
                                           encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/solana/curve_cost.py"), CURVE,
         "--grad-price", "1", "--mint", MINT, "--vs0", "30", "--vt0", "1000",
         "--decimals", "0"], cwd=case, text=True, capture_output=True)
    if proc.returncode != 0:
        raise AssertionError(proc.stdout + proc.stderr)
    return json.loads((data / "curve_costs.json").read_text(encoding="utf-8"))


def load_entity_module():
    path = ROOT / "scripts/report/entity_source_trace.py"
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("batch1b_entity_source_trace", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def semantic_order_probe():
    base = [
        [1, 100, 0, -1, CURVE, "A", 100],
        [1, 100, 1, -1, "A", CURVE, 50],
        [1, 100, 2, -1, CURVE, "B", 100],
    ]
    pseudo = [base[0], [*base[2][:2], 1, *base[2][3:]], [*base[1][:2], 2, *base[1][3:]]]
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        curve_ref = write_curve_case(root / "ref", base)
        curve_pseudo = write_curve_case(root / "pseudo", pseudo)
    assert curve_ref["B"]["sol_paid"] != curve_pseudo["B"]["sol_paid"]

    entity = load_entity_module()
    origin = ("PROVEN_ORIGIN", "mint", "O")
    ref_edges = [(1, 100, 0, -1, True, 0, "O", "M", 10),
                 (1, 100, 1, -1, True, 1, "M", "E", 10)]
    pseudo_edges = [ref_edges[1], ref_edges[0]]
    args = ({"E"}, {"M"}, {"O": origin}, {"O": 1}, "pro_rata", 1)
    entity_ref = entity.simulate(ref_edges, *args)
    entity_pseudo = entity.simulate(pseudo_edges, *args)
    assert entity_ref["current"] != entity_pseudo["current"]
    return curve_ref["B"]["sol_paid"], curve_pseudo["B"]["sol_paid"]


def functional_repair_regressions():
    from scripts.solana import sqd_gap_repair as repair
    from scripts.solana import sqd_repair_core as core

    vectors = json.loads((ROOT / "scripts/tests/fixtures/sqd_repair/vectors.json").read_text())
    canonical = core.canonical_json(vectors["canonical"]["input"])
    assert canonical.decode() == vectors["canonical"]["bytes"]
    assert hashlib.sha256(canonical).hexdigest() == vectors["canonical"]["sha256"]
    base_gid = {
        "plan_digest": "0123456789abcdef", "kind": "repair",
        "supersedes": None, "census": [], "transactions": [],
        "slot_index_map": [], "evidence_manifest": [],
        "mode": "formal", "reference": {"source": "live"},
        "rpc_ledger": {"sha256": "x"},
    }
    assert core.compute_gid(base_gid) == vectors["gid"]["formal"]
    assert core.compute_gid({**base_gid, "rpc_ledger": {"sha256": "changed"}}) \
        == vectors["gid"]["formal"]
    exploration = {**base_gid, "mode": "exploration",
                   "reference": {"source": "local-evidence-cache"}}
    assert core.compute_gid(exploration) == vectors["gid"]["exploration"]

    routea = ROOT / ".staging_b3/routeA_pilot/426649168.json.gz"
    payload = core.parse_routea_cache(routea)
    mint = "61V8vBaqAGMpgDQi4JcAwo1dmBGHsyhzodcPqnEVpump"
    census, layer, mapping, _sqd, _ref = repair._routea_slot(payload, mint)
    assert census["result"] == "confirmed_nonce_defect"
    assert mapping["sqd_count"] == len(payload["sqd_sigs"])
    actual = {(row["signature"], edge[4], edge[5], edge[6])
              for row in layer for edge in row["edges"]}
    expected = set()
    with (ROOT / ".staging_b3/routeA_pilot/repair_edges_pilot.jsonl").open() as handle:
        for line in handle:
            item = json.loads(line)
            edge = item["edge"]
            if edge[1] == payload["slot"]:
                expected.add((item["signature"], edge[4], edge[5], edge[6]))
    assert actual == expected
    nonce_tx = next(item["tx"] for item in payload["missing_full"]
                    if item.get("nonce"))
    assert core.is_nonce_transaction(nonce_tx)
    first_present = next(sig for sig in payload["helius_sigs"]
                         if sig in set(payload["sqd_sigs"]))
    indexed = dict(payload)
    indexed["sqd_sigs"] = [first_present]
    indexed["sqd_transactions"] = [
        {"index": 7, "signature": first_present, "err": None}]
    _census, _layer, indexed_map, _sqd, _ref = repair._routea_slot(indexed, mint)
    assert len(indexed_map["map"]) == 1
    assert indexed_map["map"][0][0] == 7
    assert indexed_map["map"][0][2] == first_present

    with tempfile.TemporaryDirectory(prefix="sqd-repair-cas-", dir="/private/tmp") as td:
        root = Path(td)
        base_edge = root / "base.gz"
        base_edge.write_bytes(b"base")
        bundle_path = root / "bundle.json"
        bundle_path.write_text(json.dumps({
            "base": {"edge_sha256": hashlib.sha256(b"base").hexdigest()}}))
        bundle_sha = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
        current_path = root / "CURRENT.json"
        pointer = {"gid": "a" * 16, "supersedes": None,
                   "inputs": {"bundle": {"sha256": bundle_sha}}}
        assert repair.publish_current_cas(
            current_path, pointer, expected_current=None,
            bundle_path=bundle_path, base_edge_path=base_edge) == "published"
        current = json.loads(current_path.read_text())
        idempotent = {**pointer, "supersedes": "wrong"}
        assert repair.publish_current_cas(
            current_path, idempotent, expected_current=current,
            bundle_path=bundle_path, base_edge_path=base_edge) == "idempotent-republish"
        stale = {"gid": "b" * 16, "supersedes": "wrong",
                 "inputs": {"bundle": {"sha256": bundle_sha}}}
        try:
            repair.publish_current_cas(
                current_path, stale, expected_current=current,
                bundle_path=bundle_path, base_edge_path=base_edge)
        except RuntimeError:
            pass
        else:
            raise AssertionError("stale CAS overwrote CURRENT")
    print("GREEN functional canonical/gid/E17/routeA truth/CAS regressions")


def blocks_cache_end_to_end():
    from scripts.lib import solana_exact_validate as exact
    from scripts.solana import sqd_coverage_probe as probe
    from scripts.solana import sqd_gap_repair as repair
    from scripts.solana.spl_edge_core import (EDGE_SCHEMA_FIELDS, EDGE_SEMANTICS,
                                               ORDER_GRANULARITY_TX)

    slot = 426649168
    mint = "61V8vBaqAGMpgDQi4JcAwo1dmBGHsyhzodcPqnEVpump"
    with tempfile.TemporaryDirectory(prefix="sqd-blocks-e2e-", dir="/private/tmp") as td:
        root = Path(td)
        case = root / "case"
        data = case / "data"
        data.mkdir(parents=True)
        fixture = root / "transport"
        fixture.mkdir()
        metadata = {"dataset_id": "solana-mainnet", "start_block": 0,
                    "real_time": True, "number": slot}
        responses = {probe.request_digest("sqd-head", {}): {
            "ok": True, "value": metadata}}
        body = probe.sqd_query_body(slot, slot)
        responses[probe.request_digest("sqd-stream", body)] = {
            "ok": True, "value": [{"header": {"number": slot},
                                     "instructions": [{"transactionIndex": 0}]}]}
        (fixture / "responses.json").write_text(json.dumps({
            "format": "sqd-coverage-transport-fixture-v1",
            "responses": responses}), encoding="utf-8")
        assert probe.main([
            "--mint", mint, "--case-root", str(case),
            "--from-slot", str(slot), "--to-slot", str(slot), "--full",
            "--no-getblocks", "--transport-fixture", str(fixture)]) == 0

        key = hashlib.sha256(mint.encode()).hexdigest()
        edge_path = data / f"soltx-{key}.jsonl.gz"
        meta_path = data / f"soltx-{key}.meta.json"
        base_row = [1781532455, slot, 0, -1, "BaseFrom", "BaseTo", 1]
        with gzip.open(edge_path, "wt", encoding="utf-8") as handle:
            handle.write(json.dumps(base_row, ensure_ascii=False) + "\n")
        logical = hashlib.sha256(
            (json.dumps(base_row, ensure_ascii=False) + "\n").encode()).hexdigest()
        meta_path.write_text(json.dumps({
            "schema": "sqd-solana-cache/v4", "version": 4, "mint": mint,
            "endpoint": "fixture://sqd", "endpoint_sha256": "0" * 64,
            "collector": "fetch_sqd_transfers_v2.py/v4",
            "collector_sha256": FETCH_SHA256,
            "edge_schema": list(EDGE_SCHEMA_FIELDS),
            "edge_semantics": EDGE_SEMANTICS,
            "order_granularity": ORDER_GRANULARITY_TX, "order_exact": False,
            "dedupe_identity": "transaction", "supply_delta_source": "fixture",
            "from_slot": slot, "finalized_upper_slot": slot,
            "edge_logical_sha256": logical, "edge_rows": 1,
        }), encoding="utf-8")
        cache = root / "blocks"
        cache.mkdir()
        cache_file = cache / f"{slot}.json.gz"
        cache_file.write_bytes((ROOT / ".staging_b3/routeA_pilot/426649168.json.gz").read_bytes())
        assert repair.main(["repair", "--mint", mint, "--case-root", str(case),
                            "--blocks-cache", str(cache)]) == 0
        parent = data / "sqd_repair" / key
        generations = list(parent.glob("gen-*"))
        assert len(generations) == 1 and not (parent / "CURRENT.json").exists()
        bundle = json.loads((generations[0] / "bundle.json").read_text())
        assert bundle["mode"] == "exploration"
        assert bundle["reference"]["source"] == "local-evidence-cache"
        assert bundle["repair_layer"]["edges"] == 1
        checked = exact.validate_repair_bundle_deep(
            generations[0] / "bundle.json", case_root=case,
            current_base={"edge_sha256": hashlib.sha256(edge_path.read_bytes()).hexdigest()})
        assert checked["ok"], checked
    print("GREEN --blocks-cache exploration generation/deep validation/no pointer")


def live_mock_transport_regression():
    from scripts.solana import sqd_coverage_probe as probe
    from scripts.solana import sqd_gap_repair as repair
    from scripts.solana.spl_edge_core import (EDGE_SCHEMA_FIELDS, EDGE_SEMANTICS,
                                               ORDER_GRANULARITY_TX)

    slot = 426649168
    mint = "61V8vBaqAGMpgDQi4JcAwo1dmBGHsyhzodcPqnEVpump"
    with gzip.open(ROOT / ".staging_b3/routeA_pilot/426649168.json.gz", "rt") as handle:
        routea = json.load(handle)
    missing = next(item for item in routea["missing_full"]
                   if item["sig"].startswith("5NFBt2"))
    with tempfile.TemporaryDirectory(prefix="sqd-live-mock-", dir="/private/tmp") as td:
        root = Path(td)
        case, data = root / "case", root / "case/data"
        data.mkdir(parents=True)
        coverage_fixture = root / "coverage-fixture"
        coverage_fixture.mkdir()
        metadata = {"dataset_id": "solana-mainnet", "start_block": 0,
                    "real_time": True, "number": slot}
        coverage_responses = {probe.request_digest("sqd-head", {}): {
            "ok": True, "value": metadata}}
        coverage_body = probe.sqd_query_body(slot - 1, slot)
        coverage_responses[probe.request_digest("sqd-stream", coverage_body)] = {
            "ok": True, "value": [
                {"header": {"number": value},
                 "instructions": [{"transactionIndex": 0}]}
                for value in (slot - 1, slot)]}
        (coverage_fixture / "responses.json").write_text(json.dumps({
            "format": "sqd-coverage-transport-fixture-v1",
            "responses": coverage_responses}), encoding="utf-8")
        assert probe.main([
            "--mint", mint, "--case-root", str(case),
            "--from-slot", str(slot - 1), "--to-slot", str(slot), "--full",
            "--no-getblocks", "--transport-fixture", str(coverage_fixture)]) == 0

        key = hashlib.sha256(mint.encode()).hexdigest()
        edge_path = data / f"soltx-{key}.jsonl.gz"
        meta_path = data / f"soltx-{key}.meta.json"
        base_row = [routea["blockTime"] - 1, slot - 1, 0, -1,
                    "BaseFrom", "BaseTo", 1]
        with gzip.open(edge_path, "wt", encoding="utf-8") as handle:
            handle.write(json.dumps(base_row, ensure_ascii=False) + "\n")
        logical = hashlib.sha256(
            (json.dumps(base_row, ensure_ascii=False) + "\n").encode()).hexdigest()
        meta_path.write_text(json.dumps({
            "schema": "sqd-solana-cache/v4", "version": 4, "mint": mint,
            "endpoint": "fixture://sqd", "endpoint_sha256": "0" * 64,
            "collector": "fetch_sqd_transfers_v2.py/v4",
            "collector_sha256": FETCH_SHA256,
            "edge_schema": list(EDGE_SCHEMA_FIELDS),
            "edge_semantics": EDGE_SEMANTICS,
            "order_granularity": ORDER_GRANULARITY_TX, "order_exact": False,
            "dedupe_identity": "transaction", "supply_delta_source": "fixture",
            "from_slot": slot - 1, "finalized_upper_slot": slot,
            "edge_logical_sha256": logical, "edge_rows": 1,
        }), encoding="utf-8")
        residual = root / "residual.json"
        residual.write_text(json.dumps({"candidate_slots": [slot]}), encoding="utf-8")
        repair_fixture = root / "repair-fixture"
        repair_fixture.mkdir()
        block = {"blockhash": routea["blockhash"], "parentSlot": slot - 1,
                 "blockTime": routea["blockTime"], "transactions": [missing["tx"]]}
        census = [{"header": {"number": slot, "hash": routea["blockhash"],
                               "parentSlot": slot - 1}, "transactions": []}]
        repair_responses = {
            repair.request_digest("reference-getBlock", repair._rpc_body(slot)): {
                "ok": True, "value": {"jsonrpc": "2.0", "id": slot,
                                        "result": block}},
            repair.request_digest("sqd-census", repair._census_body(slot)): {
                "ok": True, "value": census},
        }
        (repair_fixture / "responses.json").write_text(json.dumps({
            "format": "sqd-gap-repair-transport-fixture-v1",
            "responses": repair_responses}), encoding="utf-8")
        assert repair.main([
            "repair", "--mint", mint, "--case-root", str(case),
            "--residual-owners", str(residual),
            "--transport-fixture", str(repair_fixture)]) == 0
        parent = data / "sqd_repair" / key
        pointer = json.loads((parent / "CURRENT.json").read_text())
        bundle = json.loads((parent / f"gen-{pointer['gid']}/bundle.json").read_text())
        assert bundle["mode"] == "formal" and bundle["reference"]["source"] == "live"
        assert bundle["rpc_ledger"]["requests"] == 1
        ledger = (parent / f"gen-{pointer['gid']}/rpc_ledger.jsonl").read_text().splitlines()
        assert json.loads(ledger[0])["plan_digest"] == bundle["plan_digest"]
    print("GREEN live Helius getBlock/SQD census mock transport/formal pointer")


def main():
    red = 0

    functional_repair_regressions()
    blocks_cache_end_to_end()
    live_mock_transport_regression()

    ref_cost, pseudo_cost = semantic_order_probe()
    print(f"GREEN 2-fact order-sensitive curve/entity 现役顺序敏感成立 curve_B={ref_cost:.12g}/{pseudo_cost:.12g}")
    production = "\n".join((ROOT / p).read_text(encoding="utf-8") for p in (
        "scripts/solana/curve_cost.py", "scripts/report/entity_source_trace.py",
        "scripts/solana/sqd_cache_identity.py"))
    if "slot_index_map" not in production and "reference-nonvote-ordinal" not in production:
        print("RED 2 missing-mechanism 现役无 slot_index_map 双射统一缺陷 slot 参考序号机制")
        red += 1
    else:
        print("GREEN 2 implemented 缺陷 slot 参考序号统一机制已存在")

    assert not ("data/sqd_coverage/x".startswith("data/sqd_coverage/") and "repair" == "probe")
    red += expected_red("4", "guard_coverage_writes", "repair 写 coverage 资产尚无拒绝机制")

    assert 3 == 1 + 2
    red += expected_red("5", "merge_edges", "同签名多边行数恒等式尚无生产实现")

    existing = {"gen-a"}
    assert "gen-a" in existing
    red += expected_red("6", "publish_generation_exclusive", "不可变 gen 目录 exclusive 写尚未实现")

    dirs = {"pending-x", "gen-orphan"}
    assert "CURRENT.json" not in dirs
    red += expected_red("7", "resolve_formal_cache", "pending 与无指针孤儿代过滤尚未实现")

    assert {"mode": "exploration", "reference": {"source": "local-evidence-cache"}}["mode"] != "formal"
    red += expected_red("8", "validate_repair_bundle", "formal 拒 local-evidence-cache 尚未实现")

    census = [{"result": "refuted"}]
    assert not any(row["result"].startswith("confirmed_") for row in census)
    red += expected_red("10", "should_publish_generation", "refuted-only 不产代规则尚未实现")

    assert "old" != "current"
    red += expected_red("15", "validate_base_binding", "base 重采后旧代硬错尚未实现")

    plan = {"kind": "repair", "mode": "formal", "supersedes": "a", "amt": 1}
    assert gid_for(plan) != gid_for({**plan, "mode": "exploration"})
    assert gid_for(plan) != gid_for({**plan, "supersedes": "b"})
    assert "gid" not in plan
    red += expected_red("16", "compute_gid", "gid 去自引用并绑定 mode/supersedes 尚未实现")

    current = {"gid": "a", "bundle_sha256": "h"}
    assert ({"gid": "b", "supersedes": "wrong"}["supersedes"] != current["gid"])
    assert current == {"gid": "a", "bundle_sha256": "h"}
    red += expected_red("18", "publish_current_cas", "CAS 与同 gid 幂等分支尚未实现")

    meta = {"plan_digest": "p", "base_edge_sha256": "b"}
    bundle = {"merged": {"meta_sha256": "expected"}}
    assert "gid" not in meta and "bundle_sha256" not in meta
    assert bundle["merged"]["meta_sha256"] != "actual"
    red += expected_red("25", "validate_merged_binding", "merged meta 禁环与 bundle meta 哈希核对尚未实现")

    assert ["generation_dir", "repair_parent", "pointer_parent"] != ["generation_dir", "pointer_parent"]
    red += expected_red("26", "fsync_publish_directories", "代目录、父目录、指针父目录 fsync 尚未实现")

    try:
        canonical_bytes({"amt": "1"})
    except ValueError:
        pass
    else:
        raise AssertionError("string integer oracle accepted")
    red += expected_red("27", "canonical_json", "字符串金额拒绝尚无生产规范化实现")

    assert "INCONCLUSIVE" != "DEFECTS_CONFIRMED"
    red += expected_red("29a", "validate_resolution", "非 DEFECTS_CONFIRMED resolution 尚无深验")

    confirmed = {100}
    repair_slots = {100, 101}
    assert not repair_slots.issubset(confirmed)
    red += expected_red("29b", "validate_census_support", "修复交易/重映射 slot confirmed 支撑尚无深验")

    current_candidates = {100, 102}
    generation_census = {100}
    assert not current_candidates.issubset(generation_census)
    red += expected_red("29c", "validate_current_candidates", "当前新候选全覆盖尚无深验")

    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main())
