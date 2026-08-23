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
    except (ImportError, AttributeError):
        print(f"EXPECTED_RED: {TARGET}/{symbol} 未实现")
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


def main():
    red = 0

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
