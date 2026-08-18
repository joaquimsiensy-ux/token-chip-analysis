#!/usr/bin/env python3
"""Independent read-only oracle for ARC's frozen legacy five-field SQD parts.

This tool deliberately does not import the production Solana collector or its
mergers.  It parses the frozen five-field rows twice: once with Python memory
structures and once with DuckDB.  Only ``out_dir`` is writable.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import duckdb


ZERO = "0x" + "0" * 40
CANONICAL_ORDER = "slot,ts,from,to,amount_raw"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_load(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def nonnegative_int(value, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def positive_int(value, field: str) -> int:
    value = nonnegative_int(value, field)
    if value == 0:
        raise ValueError(f"{field} must be positive")
    return value


def parse_row(raw, label: str) -> tuple[int, int, str, str, int]:
    if not isinstance(raw, list) or len(raw) != 5:
        raise ValueError(f"{label}: expected legacy five-field edge row")
    ts = nonnegative_int(raw[0], f"{label}.ts")
    slot = nonnegative_int(raw[1], f"{label}.slot")
    src, dst = raw[2], raw[3]
    if not isinstance(src, str) or not src or not isinstance(dst, str) or not dst:
        raise ValueError(f"{label}: from/to must be non-empty strings")
    amount = positive_int(raw[4], f"{label}.amount_raw")
    return ts, slot, sys.intern(src), sys.intern(dst), amount


def canonical_line(row) -> bytes:
    return (json.dumps(list(row), ensure_ascii=False, separators=(",", ":"))
            + "\n").encode("utf-8")


def sort_key(row):
    ts, slot, src, dst, amount = row
    return slot, ts, src, dst, amount


def update_balance(balance, row, multiplier=1) -> None:
    _ts, _slot, src, dst, amount = row
    value = amount * multiplier
    if src != ZERO:
        balance[src] -= value
    if dst != ZERO:
        balance[dst] += value


def freeze_parts(case_root: Path, source_manifest: Path, parts_root: Path):
    manifest = json_load(source_manifest)
    listed = manifest.get("parts")
    if manifest.get("part_count") != 1348 or not isinstance(listed, list) \
            or len(listed) != manifest.get("part_count"):
        raise ValueError("ARC source manifest does not contain exactly 1348 parts")

    expected_names = []
    source_by_name = {}
    for index, record in enumerate(listed):
        rel = record.get("path")
        if not isinstance(rel, str) or not rel:
            raise ValueError(f"source manifest parts[{index}].path invalid")
        name = Path(rel).name
        if name in source_by_name:
            raise ValueError(f"duplicate part filename in source manifest: {name}")
        expected_names.append(name)
        source_by_name[name] = record

    actual_files = sorted(parts_root.glob("*.jsonl"), key=lambda path: path.name)
    if any(path.is_symlink() for path in actual_files):
        raise ValueError("ARC parts root contains symlinks")
    actual_names = [path.name for path in actual_files]
    if actual_names != sorted(expected_names):
        missing = sorted(set(expected_names) - set(actual_names))[:20]
        extra = sorted(set(actual_names) - set(expected_names))[:20]
        raise ValueError(f"ARC parts filename set mismatch: missing={missing} extra={extra}")

    frozen = []
    rows_all = []
    balance_all = defaultdict(int)
    for file_index, path in enumerate(actual_files, 1):
        source = source_by_name[path.name]
        stat_before = path.stat()
        digest = hashlib.sha256()
        rows = 0
        min_slot = None
        max_slot = None
        with path.open("rb") as raw_handle:
            for line_no, raw_line in enumerate(raw_handle, 1):
                digest.update(raw_line)
                if not raw_line.strip():
                    continue
                try:
                    decoded = json.loads(raw_line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path.name}:{line_no}: invalid JSON: {exc}") from exc
                row = parse_row(decoded, f"{path.name}:{line_no}")
                rows_all.append(row)
                update_balance(balance_all, row)
                rows += 1
                min_slot = row[1] if min_slot is None else min(min_slot, row[1])
                max_slot = row[1] if max_slot is None else max(max_slot, row[1])
        actual = {
            "filename": path.name,
            "size": stat_before.st_size,
            "rows": rows,
            "sha256": digest.hexdigest(),
            "min_edge_slot": min_slot,
            "max_edge_slot": max_slot,
            "mtime_ns": stat_before.st_mtime_ns,
        }
        comparisons = {
            "size": source.get("size") == actual["size"],
            "rows": source.get("rows") == actual["rows"],
            "sha256": source.get("sha256") == actual["sha256"],
            "min_edge_slot": source.get("min_edge_slot") == actual["min_edge_slot"],
            "max_edge_slot": source.get("max_edge_slot") == actual["max_edge_slot"],
        }
        if not all(comparisons.values()):
            raise ValueError(
                f"ARC part differs from source manifest: {path.name} {comparisons}")
        actual["source_manifest_match"] = comparisons
        frozen.append(actual)
        if file_index % 100 == 0:
            print(f"[oracle] froze {file_index}/1348 parts", flush=True)

    if len(rows_all) != manifest.get("part_row_count"):
        raise ValueError(
            f"part row total mismatch: actual={len(rows_all)} "
            f"manifest={manifest.get('part_row_count')}")
    return manifest, frozen, rows_all, balance_all


def interval_proof(frozen):
    ordered = sorted(frozen, key=lambda item: (
        item["min_edge_slot"], item["max_edge_slot"], item["filename"]))
    overlaps = []
    left = ordered[0] if ordered else None
    for right in ordered[1:]:
        if left["max_edge_slot"] >= right["min_edge_slot"]:
            overlaps.append({
                "left": left["filename"],
                "left_range": [left["min_edge_slot"], left["max_edge_slot"]],
                "right": right["filename"],
                "right_range": [right["min_edge_slot"], right["max_edge_slot"]],
                "overlap_slots": left["max_edge_slot"] - right["min_edge_slot"] + 1,
            })
        if right["max_edge_slot"] > left["max_edge_slot"]:
            left = right
    return {
        "ordered_by": "min_edge_slot,max_edge_slot,filename",
        "adjacent_pairs_checked": max(0, len(ordered) - 1),
        "non_overlapping": not overlaps,
        "overlap_pair_count": len(overlaps),
        "overlaps": overlaps,
    }


def hash_rows(rows):
    digest = hashlib.sha256()
    byte_count = 0
    row_count = 0
    for row in rows:
        line = canonical_line(row)
        digest.update(line)
        byte_count += len(line)
        row_count += 1
    return {"rows": row_count, "bytes": byte_count, "sha256": digest.hexdigest()}


def memory_semantics(rows_all, balance_all):
    print(f"[oracle] sorting {len(rows_all):,} rows in memory", flush=True)
    rows_all.sort(key=sort_key)
    multiset_hash = hash_rows(rows_all)
    distinct_balance = defaultdict(int)
    distinct_digest = hashlib.sha256()
    distinct_bytes = 0
    distinct_rows = 0
    collision_groups = 0
    multiplicities = Counter()
    by_slot = defaultdict(lambda: [0, 0])
    by_million = defaultdict(lambda: [0, 0])
    top_groups = []

    for row, group in itertools.groupby(rows_all):
        count = sum(1 for _ in group)
        line = canonical_line(row)
        distinct_digest.update(line)
        distinct_bytes += len(line)
        distinct_rows += 1
        update_balance(distinct_balance, row)
        if count > 1:
            collision_groups += 1
            extra = count - 1
            multiplicities[count] += 1
            slot = row[1]
            by_slot[slot][0] += 1
            by_slot[slot][1] += extra
            band = (slot // 1_000_000) * 1_000_000
            by_million[band][0] += 1
            by_million[band][1] += extra
            if len(top_groups) < 200:
                top_groups.append({
                    "edge": list(row), "multiplicity": count, "extra_rows": extra})

    distinct_hash = {
        "rows": distinct_rows,
        "bytes": distinct_bytes,
        "sha256": distinct_digest.hexdigest(),
    }
    top_slots = sorted(
        ({"slot": slot, "collision_groups": values[0], "extra_rows": values[1]}
         for slot, values in by_slot.items()),
        key=lambda item: (-item["extra_rows"], -item["collision_groups"], item["slot"]),
    )[:100]
    slot_bands = [
        {"from_slot": band, "to_slot": band + 999_999,
         "collision_groups": values[0], "extra_rows": values[1]}
        for band, values in sorted(by_million.items())
    ]
    return {
        "multiset": multiset_hash,
        "distinct": distinct_hash,
        "row_difference": multiset_hash["rows"] - distinct_hash["rows"],
        "collisions": {
            "group_count": collision_groups,
            "extra_row_count": multiset_hash["rows"] - distinct_hash["rows"],
            "multiplicity_histogram": {str(key): value for key, value in sorted(multiplicities.items())},
            "top_slots": top_slots,
            "slot_bands_1m": slot_bands,
            "sample_groups": top_groups,
        },
        "balances": {
            "multiset": dict(balance_all),
            "distinct": dict(distinct_balance),
        },
    }


def duckdb_semantics(parts_root: Path, db_path: Path):
    files = [str(path) for path in sorted(parts_root.glob("*.jsonl"))]
    con = duckdb.connect(str(db_path))
    try:
        con.execute("SET memory_limit='4GB'")
        con.execute("SET threads=4")
        con.execute("SET preserve_insertion_order=false")
        con.execute("""
            CREATE TABLE raw AS
            SELECT filename, x, try_cast(x AS JSON) AS j
            FROM read_csv(?, columns={'x':'VARCHAR'}, header=false, quote='',
                          delim='\x07', filename=true)
        """, [files])
        invalid = con.execute("""
            SELECT filename, x FROM raw
            WHERE j IS NULL OR json_array_length(j) <> 5
               OR json_type(j, '$[0]') NOT IN ('UBIGINT','BIGINT')
               OR json_type(j, '$[1]') NOT IN ('UBIGINT','BIGINT')
               OR json_type(j, '$[2]') <> 'VARCHAR'
               OR json_type(j, '$[3]') <> 'VARCHAR'
               OR json_type(j, '$[4]') NOT IN ('UBIGINT','BIGINT')
               OR try_cast(json_extract_string(j, '$[0]') AS BIGINT) < 0
               OR try_cast(json_extract_string(j, '$[1]') AS BIGINT) < 0
               OR json_extract_string(j, '$[2]') = ''
               OR json_extract_string(j, '$[3]') = ''
               OR try_cast(json_extract_string(j, '$[4]') AS HUGEINT) <= 0
            LIMIT 1
        """).fetchone()
        if invalid:
            raise ValueError(f"DuckDB path rejected legacy edge row: {invalid}")
        con.execute("""
            CREATE TABLE edges AS
            SELECT CAST(json_extract_string(j, '$[0]') AS BIGINT) AS ts,
                   CAST(json_extract_string(j, '$[1]') AS BIGINT) AS slot,
                   json_extract_string(j, '$[2]') AS src,
                   json_extract_string(j, '$[3]') AS dst,
                   CAST(json_extract_string(j, '$[4]') AS HUGEINT) AS amount
            FROM raw
        """)

        def query_hash(distinct: bool):
            keyword = "DISTINCT" if distinct else ""
            cursor = con.execute(f"""
                SELECT {keyword} ts, slot, src, dst, amount
                FROM edges ORDER BY slot, ts, src, dst, amount
            """)
            digest = hashlib.sha256()
            byte_count = 0
            row_count = 0
            while True:
                batch = cursor.fetchmany(50_000)
                if not batch:
                    break
                for ts, slot, src, dst, amount in batch:
                    line = canonical_line((int(ts), int(slot), src, dst, int(amount)))
                    digest.update(line)
                    byte_count += len(line)
                    row_count += 1
            return {"rows": row_count, "bytes": byte_count,
                    "sha256": digest.hexdigest()}

        multiset = query_hash(False)
        distinct = query_hash(True)
        return {
            "multiset": multiset,
            "distinct": distinct,
            "row_difference": multiset["rows"] - distinct["rows"],
        }
    finally:
        con.close()


def balance_report(memory_result, snapshot_path: Path | None):
    multiset = memory_result["balances"]["multiset"]
    distinct = memory_result["balances"]["distinct"]
    owners = (set(multiset) | set(distinct)) - {ZERO}
    differing = [owner for owner in owners if multiset.get(owner, 0) != distinct.get(owner, 0)]
    top_diff = sorted(
        ({"owner": owner, "multiset": multiset.get(owner, 0),
          "distinct": distinct.get(owner, 0),
          "delta_multiset_minus_distinct": multiset.get(owner, 0) - distinct.get(owner, 0)}
         for owner in differing),
        key=lambda item: (-abs(item["delta_multiset_minus_distinct"]), item["owner"]),
    )[:200]
    result = {
        "owner_union_count": len(owners),
        "differing_owner_count": len(differing),
        "negative_owner_count": {
            "multiset": sum(value < 0 for owner, value in multiset.items() if owner != ZERO),
            "distinct": sum(value < 0 for owner, value in distinct.items() if owner != ZERO),
        },
        "top_owner_differences": top_diff,
        "snapshot": {"available": False},
    }
    if snapshot_path is not None and snapshot_path.is_file():
        snapshot_raw = json_load(snapshot_path)
        if not isinstance(snapshot_raw, dict):
            raise ValueError("holders_owners.json must be an object")
        snapshot = {}
        for owner, value in snapshot_raw.items():
            snapshot[owner] = nonnegative_int(value, f"holders_owners[{owner!r}]")

        def comparison(balance):
            union = (set(balance) | set(snapshot)) - {ZERO}
            mismatch = [owner for owner in union if balance.get(owner, 0) != snapshot.get(owner, 0)]
            return {
                "owner_union_count": len(union),
                "mismatch_owner_count": len(mismatch),
                "exact_match_owner_count": len(union) - len(mismatch),
                "top_mismatches": sorted(
                    ({"owner": owner, "replay": balance.get(owner, 0),
                      "snapshot": snapshot.get(owner, 0),
                      "delta": balance.get(owner, 0) - snapshot.get(owner, 0)}
                     for owner in mismatch),
                    key=lambda item: (-abs(item["delta"]), item["owner"]),
                )[:100],
            }

        result["snapshot"] = {
            "available": True,
            "path": snapshot_path.name,
            "size": snapshot_path.stat().st_size,
            "sha256": sha256_file(snapshot_path),
            "owners": len(snapshot),
            "scope_note": (
                "The 1348 parts cover only their frozen slot intervals; this snapshot "
                "comparison is diagnostic and is not a full-history reconciliation."),
            "multiset": comparison(multiset),
            "distinct": comparison(distinct),
        }
    return result


def verify_inputs_unchanged(frozen, parts_root, source_manifest, manifest_ref,
                            snapshot_path, snapshot_ref):
    changed = []
    for record in frozen:
        path = parts_root / record["filename"]
        stat = path.stat()
        if (stat.st_size != record["size"] or stat.st_mtime_ns != record["mtime_ns"]
                or sha256_file(path) != record["sha256"]):
            changed.append(record["filename"])
    manifest_after = {"size": source_manifest.stat().st_size,
                      "sha256": sha256_file(source_manifest)}
    snapshot_after = None
    if snapshot_path is not None and snapshot_path.is_file():
        snapshot_after = {"size": snapshot_path.stat().st_size,
                          "sha256": sha256_file(snapshot_path)}
    return {
        "verified": not changed and manifest_after == manifest_ref
                    and snapshot_after == snapshot_ref,
        "parts_rehashed": len(frozen),
        "changed_parts": changed,
        "source_manifest_before": manifest_ref,
        "source_manifest_after": manifest_after,
        "snapshot_before": snapshot_ref,
        "snapshot_after": snapshot_after,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-root", required=True)
    parser.add_argument("--source-manifest", required=True)
    parser.add_argument("--parts-root", required=True)
    parser.add_argument("--snapshot")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)

    started = time.time()
    case_root = Path(args.case_root).resolve()
    source_manifest = Path(args.source_manifest).resolve()
    parts_root = Path(args.parts_root).resolve()
    snapshot_path = Path(args.snapshot).resolve() if args.snapshot else None
    out_dir = Path(args.out_dir).resolve()
    if under(out_dir, case_root):
        raise SystemExit("out-dir must not be inside the read-only ARC case")
    for label, path in (("source manifest", source_manifest),
                        ("parts root", parts_root)):
        if not under(path, case_root):
            raise SystemExit(f"{label} must resolve inside ARC case root")
    if snapshot_path is not None and not under(snapshot_path, case_root):
        raise SystemExit("snapshot must resolve inside ARC case root")
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest_ref = {"size": source_manifest.stat().st_size,
                    "sha256": sha256_file(source_manifest)}
    snapshot_ref = None
    if snapshot_path is not None and snapshot_path.is_file():
        snapshot_ref = {"size": snapshot_path.stat().st_size,
                        "sha256": sha256_file(snapshot_path)}

    source, frozen, rows_all, balance_all = freeze_parts(
        case_root, source_manifest, parts_root)
    parts_manifest = {
        "schema": "arc-parts-oracle-manifest/v1",
        "case": "ARC",
        "source_manifest": {"path": str(source_manifest), **manifest_ref},
        "parts_root": str(parts_root),
        "part_count": len(frozen),
        "row_count": len(rows_all),
        "parts": frozen,
    }
    write_json(out_dir / "arc_parts_manifest.json", parts_manifest)

    intervals = interval_proof(frozen)
    memory = memory_semantics(rows_all, balance_all)
    db_path = out_dir / "arc_oracle.duckdb.tmp"
    duck = duckdb_semantics(parts_root, db_path)
    db_path.unlink(missing_ok=True)
    equivalence = {
        "canonical_order": CANONICAL_ORDER,
        "multiset_bytewise_equal": memory["multiset"] == duck["multiset"],
        "distinct_bytewise_equal": memory["distinct"] == duck["distinct"],
        "memory": {key: memory[key] for key in ("multiset", "distinct", "row_difference")},
        "duckdb": duck,
    }
    equivalence["pass"] = (equivalence["multiset_bytewise_equal"]
                           and equivalence["distinct_bytewise_equal"])
    if not equivalence["pass"]:
        raise ValueError("memory and DuckDB oracle paths are not bytewise equivalent")

    owners = balance_report(memory, snapshot_path)
    read_only = verify_inputs_unchanged(
        frozen, parts_root, source_manifest, manifest_ref, snapshot_path, snapshot_ref)
    if not read_only["verified"]:
        raise ValueError(f"ARC read-only input verification failed: {read_only}")

    report = {
        "schema": "arc-parts-oracle-report/v1",
        "status": "PASS",
        "case": "ARC",
        "mint": source.get("mint"),
        "elapsed_seconds": round(time.time() - started, 3),
        "parts_integrity": {
            "source_manifest_status": source.get("status"),
            "part_count": len(frozen),
            "row_count": len(rows_all),
            "all_source_manifest_fields_match": True,
        },
        "interval_non_overlap": intervals,
        "semantics": {
            "input_shape": "1348 frozen parts only",
            "multiset_rows": memory["multiset"]["rows"],
            "five_field_distinct_rows": memory["distinct"]["rows"],
            "row_difference": memory["row_difference"],
            "source_manifest_declared_duplicate_extra_row_count":
                source.get("duplicate_extra_row_count"),
            "source_manifest_count_matches":
                source.get("duplicate_extra_row_count") == memory["row_difference"],
            "workorder_expected_row_difference": 124816,
            "workorder_expectation_matches": memory["row_difference"] == 124816,
            "expectation_verdict": (
                "CONFIRMED" if memory["row_difference"] == 124816 else
                "REFUTED_BY_FROZEN_PARTS_AND_SOURCE_MANIFEST"),
        },
        "collisions": memory["collisions"],
        "owner_terminal_comparison": owners,
        "implementation_path_equivalence": equivalence,
        "read_only_verification": read_only,
        "artifacts": {
            "parts_manifest": "arc_parts_manifest.json",
            "report": "arc_oracle_report.json",
        },
    }
    write_json(out_dir / "arc_oracle_report.json", report)
    print(json.dumps({
        "status": report["status"],
        "part_count": len(frozen),
        "multiset_rows": memory["multiset"]["rows"],
        "distinct_rows": memory["distinct"]["rows"],
        "row_difference": memory["row_difference"],
        "collision_groups": memory["collisions"]["group_count"],
        "owner_differences": owners["differing_owner_count"],
        "negative_owners": owners["negative_owner_count"],
        "bytewise_equivalence": equivalence["pass"],
        "read_only_verified": read_only["verified"],
        "elapsed_seconds": report["elapsed_seconds"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
