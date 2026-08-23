"""Solana SQD cache v4/legacy meta 身份的共享 fail-closed 校验。"""

from __future__ import annotations

import re
import hashlib
import json
from pathlib import Path

from producer_history import historical_producer_hashes
from spl_edge_core import (EDGE_SCHEMA_FIELDS, EDGE_SEMANTICS, ORDER_GRANULARITY_TX,
                           soltx_cache_paths, sqd_repair_paths)


SQD_CACHE_PROTOCOL = "sqd-solana-cache/v4"
SQD_COLLECTOR_ID = "fetch_sqd_transfers_v2.py/v4"
SQD_COLLECTOR_SCRIPT = "scripts/solana/fetch_sqd_transfers_v2.py"
REPAIR_COLLECTOR_ID = "sqd_gap_repair.py/v1"
REPAIR_COLLECTOR_SCRIPT = "scripts/solana/sqd_gap_repair.py"
COLLECTORS = {
    SQD_COLLECTOR_ID: {"script": SQD_COLLECTOR_SCRIPT, "kind": "base"},
    REPAIR_COLLECTOR_ID: {"script": REPAIR_COLLECTOR_SCRIPT, "kind": "repaired"},
}


def _valid_nonnegative_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def validate_cache_meta(meta: dict, mint: str, *, legacy_sol5: bool) -> tuple[int, int]:
    """验证 cache 身份；v4 逻辑摘要与行数由 collector 建立，消费端不得回填。"""
    frm = meta.get("from_slot")
    if legacy_sol5:
        upper = meta.get("collection_upper_slot")
        valid = (
            meta.get("schema") == "sqd-solana-cache/v3"
            and meta.get("mint") == mint
            and _valid_nonnegative_int(frm)
            and _valid_nonnegative_int(upper)
            and upper >= frm
        )
        if not valid:
            raise ValueError(
                "legacy-sol5 只接受绑定原始 mint/from_slot/collection_upper_slot 的 v3 meta"
            )
        return frm, upper

    upper = meta.get("finalized_upper_slot")
    valid = (
        meta.get("schema") == SQD_CACHE_PROTOCOL
        and meta.get("version") == 4
        and meta.get("mint") == mint
        and meta.get("collector") == SQD_COLLECTOR_ID
        and meta.get("edge_schema") == list(EDGE_SCHEMA_FIELDS)
        and meta.get("edge_semantics") == EDGE_SEMANTICS
        and meta.get("order_granularity") == ORDER_GRANULARITY_TX
        and meta.get("order_exact") is False
        and _valid_nonnegative_int(frm)
        and _valid_nonnegative_int(upper)
        and upper >= frm
    )
    if not valid:
        raise ValueError(
            "正式重放只接受绑定原始 mint、v4 边契约及 finalized_upper_slot 的 v4 meta"
        )

    digest = meta.get("edge_logical_sha256")
    rows = meta.get("edge_rows")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None \
            or isinstance(rows, bool) or not isinstance(rows, int) or rows <= 0:
        raise ValueError(
            "SQD v4 meta.edge_logical_sha256/edge_rows 为 collector 必填证据"
        )

    collector_sha256 = meta.get("collector_sha256")
    allowed_hashes = historical_producer_hashes(
        SQD_COLLECTOR_SCRIPT, SQD_CACHE_PROTOCOL
    )
    if collector_sha256 not in allowed_hashes:
        raise ValueError(
            "SQD v4 meta.collector_sha256 未命中 fetch_sqd_transfers_v2.py producer 登记"
        )
    return frm, upper


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _case_root(value):
    raw = Path(value)
    cursor = raw if raw.is_absolute() else Path.cwd() / raw
    probe = Path(cursor.anchor)
    for part in cursor.parts[1:]:
        probe /= part
        if probe.is_symlink():
            raise ValueError("case_root must not contain symlinks")
    root = cursor.resolve()
    if not root.is_dir():
        raise ValueError("case_root must be an existing directory")
    return root


def _read_json(path, label):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is unreadable: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _binding(kind, gid, edge_path, meta_path, meta):
    return {
        "cache_kind": kind, "gid": gid,
        "soltx_edges_sha256": _sha256(edge_path),
        "soltx_meta_sha256": _sha256(meta_path),
        "edge_logical_sha256": meta.get("edge_logical_sha256"),
    }


def validate_repair_bundle(bundle_path, *, deep=False, case_root=None,
                           current_base=None):
    """Validate one repair bundle; deep mode delegates to the independent validator."""
    bundle_path = Path(bundle_path).resolve()
    bundle = _read_json(bundle_path, "repair bundle")
    required = {
        "schema", "mint", "plan_digest", "gid", "kind", "mode", "producer",
        "base", "coverage", "coverage_resolution", "repair_layer",
        "slot_index_map", "evidence_manifest", "merged", "reference",
        "rpc_ledger", "supersedes", "generated_at",
    }
    if set(bundle) != required:
        raise ValueError("repair bundle key set mismatch")
    if bundle.get("schema") != "sqd-solana-repair-bundle/v1" \
            or bundle.get("kind") != "repair":
        raise ValueError("repair bundle schema/kind mismatch")
    source, mode = bundle.get("reference", {}).get("source"), bundle.get("mode")
    if (mode == "formal") != (source == "live"):
        raise ValueError("formal bundle requires live reference and vice versa")
    if mode == "formal":
        allowed = historical_producer_hashes(
            REPAIR_COLLECTOR_SCRIPT, "sqd-solana-cache/v4")
        if bundle.get("producer", {}).get("sha256") not in allowed:
            raise ValueError("formal repair producer is not registered")
    generation = bundle_path.parent
    for name in ("coverage_resolution", "repair_layer", "slot_index_map",
                 "evidence_manifest", "rpc_ledger"):
        ref = bundle.get(name)
        if not isinstance(ref, dict) or not {"path", "size", "sha256"}.issubset(ref):
            raise ValueError(f"bundle {name} reference invalid")
        path = generation / ref["path"]
        if path.resolve().parent != generation and generation not in path.resolve().parents:
            raise ValueError(f"bundle {name} escapes generation")
        if not path.is_file() or path.stat().st_size != ref["size"] \
                or _sha256(path) != ref["sha256"]:
            raise ValueError(f"bundle {name} reference mismatch")
    merged = bundle.get("merged", {})
    if merged.get("edge_rows") != bundle.get("base", {}).get("edge_rows", -1) \
            + bundle.get("repair_layer", {}).get("edges", -1):
        raise ValueError("bundle edge row identity mismatch")
    if deep:
        if case_root is None or current_base is None:
            raise ValueError("deep bundle validation requires case_root and current_base")
        from solana_exact_validate import validate_repair_bundle_deep
        result = validate_repair_bundle_deep(
            bundle_path, case_root=case_root, current_base=current_base)
        if not result["ok"]:
            raise ValueError("deep repair validation failed: " + "; ".join(result["reasons"]))
    return bundle


def validate_cache_meta_v2(meta, mint, *, case_root, meta_path):
    """Validate a v4 meta only at the unique resolver-selected formal path."""
    root = _case_root(case_root)
    meta_path = Path(meta_path).resolve()
    base_edge, base_meta, _parts = soltx_cache_paths(mint, root / "data")
    parent, current_path, _lock = sqd_repair_paths(root, mint)
    current = _read_json(current_path, "repair pointer") if current_path.is_file() else None
    collector = COLLECTORS.get(meta.get("collector"))
    if collector is None:
        raise ValueError("cache collector is outside the closed set")
    frm, upper = validate_cache_meta(meta, mint, legacy_sol5=False) \
        if collector["kind"] == "base" else _validate_repaired_meta(meta, mint)
    if current is None:
        if collector["kind"] != "base" or meta_path != base_meta.resolve():
            raise ValueError("without CURRENT only the canonical base meta is formal")
        if not base_edge.is_file():
            raise ValueError("canonical base edge file missing")
        return frm, upper, "base", None, _binding(
            "base", None, base_edge, base_meta, meta)
    if collector["kind"] == "base":
        raise ValueError("CURRENT exists; formal resolver must not fall back to base")
    gid = current.get("gid")
    if not isinstance(gid, str) or re.fullmatch(r"[0-9a-f]{16}", gid) is None:
        raise ValueError("repair pointer gid invalid")
    generation = parent / f"gen-{gid}"
    expected_meta = generation / f"soltx-{hashlib.sha256(mint.encode()).hexdigest()}.repaired.meta.json"
    if meta_path != expected_meta.resolve():
        raise ValueError("repaired meta is outside CURRENT-selected formal path")
    bundle_ref = current.get("inputs", {}).get("bundle", {})
    bundle_path = root / bundle_ref.get("path", "")
    if bundle_path.resolve() != (generation / "bundle.json").resolve() \
            or not bundle_path.is_file() or _sha256(bundle_path) != bundle_ref.get("sha256"):
        raise ValueError("repair pointer bundle binding invalid")
    bundle = validate_repair_bundle(bundle_path, deep=False)
    if bundle.get("gid") != gid or bundle.get("merged", {}).get("meta_sha256") != _sha256(meta_path):
        raise ValueError("CURRENT to merged meta binding invalid")
    if meta.get("plan_digest") != bundle.get("plan_digest"):
        raise ValueError("repaired meta plan_digest mismatch")
    if meta.get("base_edge_sha256") != _sha256(base_edge):
        raise ValueError("repaired generation was invalidated by base recapture")
    edge_path = generation / bundle["merged"]["edge_file"]
    if not edge_path.is_file() or _sha256(edge_path) != bundle["merged"]["edge_sha256"]:
        raise ValueError("repaired edge binding invalid")
    return frm, upper, "repaired", gid, _binding(
        "repaired", gid, edge_path, meta_path, meta)


def _validate_repaired_meta(meta, mint):
    frm, upper = meta.get("from_slot"), meta.get("finalized_upper_slot")
    valid = (
        meta.get("schema") == SQD_CACHE_PROTOCOL and meta.get("version") == 4
        and meta.get("mint") == mint and meta.get("collector") == REPAIR_COLLECTOR_ID
        and meta.get("edge_schema") == list(EDGE_SCHEMA_FIELDS)
        and meta.get("edge_semantics") == EDGE_SEMANTICS
        and meta.get("order_granularity") == ORDER_GRANULARITY_TX
        and meta.get("order_exact") is False and _valid_nonnegative_int(frm)
        and _valid_nonnegative_int(upper) and upper >= frm
        and isinstance(meta.get("edge_logical_sha256"), str)
        and re.fullmatch(r"[0-9a-f]{64}", meta["edge_logical_sha256"])
        and _valid_nonnegative_int(meta.get("edge_rows"))
        and _valid_nonnegative_int(meta.get("edge_file_size"))
        and isinstance(meta.get("edge_file_sha256"), str)
        and re.fullmatch(r"[0-9a-f]{64}", meta["edge_file_sha256"])
        and isinstance(meta.get("plan_digest"), str)
        and re.fullmatch(r"[0-9a-f]{16}", meta["plan_digest"])
        and "gid" not in meta and "bundle_sha256" not in meta
    )
    if not valid:
        raise ValueError("repaired v4 meta contract invalid")
    return frm, upper


def resolve_formal_cache(mint, case_root):
    """Resolve exactly the current formal cache pair; invalid CURRENT is fatal."""
    root = _case_root(case_root)
    base_edge, base_meta, _parts = soltx_cache_paths(mint, root / "data")
    if not base_edge.is_file() or not base_meta.is_file():
        raise ValueError("canonical base cache pair is missing")
    parent, current_path, _lock = sqd_repair_paths(root, mint)
    if not current_path.is_file():
        meta = _read_json(base_meta, "base meta")
        frm, upper, kind, gid, binding = validate_cache_meta_v2(
            meta, mint, case_root=root, meta_path=base_meta)
        del frm, upper
        return base_edge, base_meta, kind, gid, binding
    pointer = _read_json(current_path, "repair pointer")
    if pointer.get("schema") != "sqd-solana-repair-pointer/v1" \
            or pointer.get("mode") != "formal" or pointer.get("verdict") != "PASS" \
            or pointer.get("exit_code") != 0 \
            or pointer.get("target", {}).get("token") != mint:
        raise ValueError("repair pointer envelope invalid")
    gid = pointer.get("gid")
    if not isinstance(gid, str):
        raise ValueError("repair pointer gid missing")
    bundle_path = parent / f"gen-{gid}" / "bundle.json"
    bundle = _read_json(bundle_path, "repair bundle")
    meta_path = parent / f"gen-{gid}" / bundle.get("merged", {}).get("meta_file", "")
    meta = _read_json(meta_path, "repaired meta")
    _frm, _upper, kind, checked_gid, binding = validate_cache_meta_v2(
        meta, mint, case_root=root, meta_path=meta_path)
    edge_path = parent / f"gen-{gid}" / bundle["merged"]["edge_file"]
    return edge_path, meta_path, kind, checked_gid, binding
