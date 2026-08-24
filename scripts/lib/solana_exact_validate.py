#!/usr/bin/env python3
"""Independent Solana exact validators.

Coverage segment (batch 2): implemented below.  It validates
``sqd-solana-coverage/v1`` and ``sqd-solana-coverage-pointer/v1`` from disk.

Repair segment (batch 3) and reconcile segment (batch 5) are implemented below.

This module is deliberately independent from ``replay_edges`` and
``sqd_repair_core``.  Validators receive paths and explicit case bounds; they
never infer a case root from the current working directory.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
from pathlib import Path


COVERAGE_SCHEMA = "sqd-solana-coverage/v1"
COVERAGE_POINTER_SCHEMA = "sqd-solana-coverage-pointer/v1"
ERA_PARAMS = {
    "window": 1_000_000,
    "min_headers": 10_000,
    "min_ratio_num": 99,
    "min_ratio_den": 100,
}
COUNT_ENCODING = (
    "u8:0=UNSCANNED,1=NO_HEADER,2=HEADER_ZERO_NONCE,"
    "n>=3→nonce_count=n-2，255饱和"
)
BITMAP_ENCODING = "u1 per slot,1=getBlocks列出该slot"
VERDICTS = {
    "NO_KNOWN_NONCE_OMISSION_DETECTED", "DEFECTS_CONFIRMED", "INCONCLUSIVE",
}


def canonical_json(value):
    """Return the frozen canonical JSON bytes, rejecting every float."""
    def walk(item, where="$"):
        if isinstance(item, float):
            raise ValueError(f"float forbidden at {where}")
        if isinstance(item, dict):
            for key, child in item.items():
                walk(child, f"{where}.{key}")
        elif isinstance(item, list):
            for index, child in enumerate(item):
                walk(child, f"{where}[{index}]")
    walk(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compute_probe_id(coverage_map):
    material = dict(coverage_map)
    material.pop("probe_id", None)
    return sha256_bytes(canonical_json(material))[:16]


def _integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _range_pair(item, start_key="from_slot", end_key="to_slot"):
    if not isinstance(item, dict):
        raise ValueError("range must be object")
    start, end = item.get(start_key), item.get(end_key)
    if not _integer(start) or not _integer(end) or start > end:
        raise ValueError(f"invalid range {item!r}")
    return start, end


def merge_ranges(ranges):
    """Return normalized inclusive union; overlapping/adjacent ranges merge."""
    normalized = sorted((int(start), int(end)) for start, end in ranges)
    out = []
    for start, end in normalized:
        if start > end:
            raise ValueError(f"invalid range {start}..{end}")
        if out and start <= out[-1][1] + 1:
            out[-1] = (out[-1][0], max(out[-1][1], end))
        else:
            out.append((start, end))
    return out


def ranges_cover(ranges, lower, upper):
    if not _integer(lower) or not _integer(upper) or lower > upper:
        return False
    union = merge_ranges(ranges)
    cursor = lower
    for start, end in union:
        if end < cursor:
            continue
        if start > cursor:
            return False
        cursor = max(cursor, end + 1)
        if cursor > upper:
            return True
    return cursor > upper


def encode_bitmap(slots, from_slot, to_slot):
    """Pack a slot set into little-bit-order bytes (bit i == slot from+i)."""
    if not _integer(from_slot) or not _integer(to_slot) or from_slot > to_slot:
        raise ValueError("invalid bitmap interval")
    width = to_slot - from_slot + 1
    raw = bytearray((width + 7) // 8)
    previous = None
    for slot in slots:
        if not _integer(slot) or slot < from_slot or slot > to_slot:
            raise ValueError(f"bitmap slot outside interval: {slot!r}")
        if previous is not None and slot <= previous:
            raise ValueError("bitmap slots must be strictly increasing and unique")
        previous = slot
        index = slot - from_slot
        raw[index // 8] |= 1 << (index % 8)
    return bytes(raw)


def bitmap_bit(raw, index):
    return bool(raw[index // 8] & (1 << (index % 8)))


def bitmap_popcount(raw, start_index, width):
    return sum(bitmap_bit(raw, index) for index in range(start_index,
                                                         start_index + width))


def validate_blocks_bitmap(raw, from_slot, to_slot):
    reasons = []
    if not isinstance(raw, (bytes, bytearray)):
        return {"ok": False, "reasons": ["blocks bitmap is not bytes"],
                "popcount": 0}
    if not _integer(from_slot) or not _integer(to_slot) or from_slot > to_slot:
        return {"ok": False, "reasons": ["blocks bitmap interval invalid"],
                "popcount": 0}
    width = to_slot - from_slot + 1
    expected = (width + 7) // 8
    if len(raw) != expected:
        reasons.append(
            f"blocks bitmap byte length mismatch: expected {expected}, got {len(raw)}")
    elif width % 8:
        padding_mask = ~((1 << (width % 8)) - 1) & 0xFF
        if raw[-1] & padding_mask:
            reasons.append("blocks bitmap nonzero padding bits")
    popcount = sum(byte.bit_count() for byte in raw[:expected]) if len(raw) >= expected else 0
    return {"ok": not reasons, "reasons": reasons, "popcount": popcount,
            "width": width}


def derive_getblocks_complete(segment, bitmap_raw, bitmap_from_slot):
    """Recompute errata E2's eight-way conjunction for one RPC segment."""
    try:
        start, end = _range_pair(segment, "from", "to")
    except ValueError:
        return False
    width = end - start + 1
    if not _integer(bitmap_from_slot):
        return False
    start_index = start - bitmap_from_slot
    bitmap_width = len(bitmap_raw) * 8
    segment_fits = start_index >= 0 and start_index + width <= bitmap_width
    popcount = (bitmap_popcount(bitmap_raw, start_index, width)
                if segment_fits else -1)
    return (
        segment.get("response_ok") is True
        and segment.get("array_monotonic_unique") is True
        and segment.get("array_in_range") is True
        and width <= 500_000
        and _integer(segment.get("reference_head_at_check"))
        and segment["reference_head_at_check"] >= end
        and segment_fits
        and _integer(segment.get("count"))
        and popcount == segment["count"]
        and segment["count"] <= width
    )


def _window_stats(counts, from_slot):
    stats = {}
    for offset, code in enumerate(counts):
        if code < 2:
            continue
        window = (from_slot + offset) // ERA_PARAMS["window"]
        item = stats.setdefault(window, {"headers": 0, "nonce_blocks": 0})
        item["headers"] += 1
        if code >= 3:
            item["nonce_blocks"] += 1
    return stats


def classify_four_states(counts, from_slot, *, confirmation=None,
                         blocks_bitmap=None):
    """Classify each slot without run-length heuristics."""
    stats = _window_stats(counts, from_slot)
    complete_segments = []
    bitmap_from = from_slot
    if confirmation is not None and blocks_bitmap is not None:
        bitmap_from = confirmation.get("blocks_bitmap", {}).get("from_slot", from_slot)
        for segment in confirmation.get("ranges", []):
            enriched = dict(segment)
            enriched["reference_head_at_check"] = confirmation.get(
                "reference_head_at_check")
            if derive_getblocks_complete(enriched, blocks_bitmap, bitmap_from):
                complete_segments.append((segment["from"], segment["to"]))

    states = []
    candidates = []
    unconfirmed = []
    summary = {
        "slots": len(counts), "unscanned": 0, "healthy": 0, "no_header": 0,
        "header_zero_nonce": 0, "defect_candidate": 0, "era_uncertain": 0,
        "skipped_confirmed": 0, "missing_block_candidate": 0,
        "no_header_unconfirmed": 0, "saturated_nonce_count": 0,
    }
    for offset, code in enumerate(counts):
        slot = from_slot + offset
        if code == 0:
            state = "UNSCANNED"
            summary["unscanned"] += 1
            unconfirmed.append(slot)
        elif code == 1:
            state = "NO_HEADER"
            summary["no_header"] += 1
            covered = any(start <= slot <= end for start, end in complete_segments)
            if covered:
                if bitmap_bit(blocks_bitmap, slot - bitmap_from):
                    state = "MISSING_BLOCK"
                    summary["missing_block_candidate"] += 1
                    candidates.append(slot)
                else:
                    state = "SKIPPED_CONFIRMED"
                    summary["skipped_confirmed"] += 1
            else:
                summary["no_header_unconfirmed"] += 1
                unconfirmed.append(slot)
        elif code == 2:
            summary["header_zero_nonce"] += 1
            item = stats[(slot // ERA_PARAMS["window"])]
            calibrated = (
                item["headers"] >= ERA_PARAMS["min_headers"]
                and item["nonce_blocks"] * ERA_PARAMS["min_ratio_den"]
                >= item["headers"] * ERA_PARAMS["min_ratio_num"]
            )
            if calibrated:
                state = "DEFECT_CANDIDATE"
                summary["defect_candidate"] += 1
                candidates.append(slot)
            else:
                state = "ERA_UNCERTAIN"
                summary["era_uncertain"] += 1
                unconfirmed.append(slot)
        else:
            state = "HEALTHY"
            summary["healthy"] += 1
            if code == 255:
                summary["saturated_nonce_count"] += 1
        states.append(state)
    candidates = sorted(set(candidates))
    if candidates or unconfirmed:
        verdict = "INCONCLUSIVE"
    else:
        verdict = "NO_KNOWN_NONCE_OMISSION_DETECTED"
    return {"states": states, "candidate_slots": candidates,
            "unconfirmed_slots": sorted(set(unconfirmed)), "summary": summary,
            "verdict": verdict, "era_windows": stats}


def validate_slot_counts(counts, from_slot, to_slot, scan_ranges, ledger_ranges):
    reasons = []
    expected = to_slot - from_slot + 1
    if len(counts) != expected:
        reasons.append(f"slot_counts length mismatch: expected {expected}, got {len(counts)}")
    if any(value == 0 for value in counts):
        reasons.append("slot_counts contains UNSCANNED")
    try:
        scan_union = merge_ranges(scan_ranges)
        ledger_union = merge_ranges(ledger_ranges)
    except ValueError as exc:
        reasons.append(str(exc))
        scan_union, ledger_union = [], []
    if not ranges_cover(scan_union, from_slot, to_slot):
        reasons.append("scan_ranges union does not cover case interval")
    if ledger_union != scan_union:
        reasons.append("ledger successful union differs from scan_ranges union")
    return {"ok": not reasons, "reasons": reasons,
            "scan_union": scan_union, "ledger_union": ledger_union}


def validate_coverage_map(coverage_map, *, case_from_slot, case_to_slot):
    reasons = []
    if not isinstance(coverage_map, dict):
        return {"ok": False, "reasons": ["coverage map is not object"]}
    try:
        canonical_json(coverage_map)
    except ValueError as exc:
        reasons.append(str(exc))
    if coverage_map.get("schema") != COVERAGE_SCHEMA:
        reasons.append("coverage schema mismatch")
    if coverage_map.get("version") != 1:
        reasons.append("coverage version mismatch")
    if coverage_map.get("chain") != "solana":
        reasons.append("coverage chain mismatch")
    if not isinstance(coverage_map.get("mint"), str) or not coverage_map["mint"]:
        reasons.append("coverage mint missing")
    params = coverage_map.get("era_params")
    if params != ERA_PARAMS:
        reasons.append("era_params mismatch")
    scan = coverage_map.get("scan_ranges")
    if not isinstance(scan, list):
        reasons.append("scan_ranges missing")
    else:
        try:
            pairs = [_range_pair(item) for item in scan]
            if any(item.get("mode") not in {"full", "map-reuse", "recheck"}
                   for item in scan):
                reasons.append("scan_ranges mode invalid")
            if not ranges_cover(pairs, case_from_slot, case_to_slot):
                reasons.append("scan_ranges union does not cover case interval")
        except ValueError as exc:
            reasons.append(str(exc))
    if coverage_map.get("verdict") not in VERDICTS:
        reasons.append("coverage verdict invalid")
    if coverage_map.get("probe_id") != compute_probe_id(coverage_map):
        reasons.append("probe_id mismatch")
    return {"ok": not reasons, "reasons": reasons}


def _safe_case_path(case_root, rel):
    root = Path(case_root).resolve()
    if not isinstance(rel, str) or not rel or Path(rel).is_absolute():
        raise ValueError(f"artifact path must be case-relative: {rel!r}")
    candidate = root / rel
    cursor = root
    for part in Path(rel).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError(f"artifact path contains symlink: {rel}")
    path = candidate.resolve()
    if path != root and root not in path.parents:
        raise ValueError(f"artifact path escapes case root: {rel}")
    return path


def _check_file_ref(case_root, ref, label, reasons):
    if not isinstance(ref, dict) or set(ref) != {"path", "size", "sha256"}:
        reasons.append(f"{label} reference shape invalid")
        return None
    try:
        path = _safe_case_path(case_root, ref["path"])
    except ValueError as exc:
        reasons.append(str(exc))
        return None
    if not path.is_file():
        reasons.append(f"{label} file missing: {ref['path']}")
        return None
    if path.stat().st_size != ref.get("size"):
        reasons.append(f"{label} size mismatch")
    if sha256_file(path) != ref.get("sha256"):
        reasons.append(f"{label} sha256 mismatch")
    return path


def _read_ledger(path, reasons):
    rows = []
    try:
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            row = json.loads(line)
            canonical_json(row)
            rows.append(row)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        reasons.append(f"ledger invalid: {exc}")
        return []
    seqs = [row.get("seq") for row in rows]
    if seqs != list(range(len(rows))):
        reasons.append("ledger seq has hole or is not zero-based")
    return rows


def _success_ranges(rows, reasons):
    ranges = []
    empty_response_count = 0
    for row in rows:
        if row.get("ok") is not True or row.get("counts_coverage") is not True:
            continue
        try:
            start, requested_end = _range_pair(row, "from", "to")
        except ValueError as exc:
            reasons.append(f"ledger success range invalid: {exc}")
            continue
        covered = row.get("slots_covered")
        if not _integer(covered) or covered <= 0:
            reasons.append("ledger slots_covered must be positive integer")
            continue
        actual_end = start + covered - 1
        if actual_end > requested_end:
            reasons.append("ledger actual coverage exceeds requested range")
            continue
        if row.get("provider") == "SQD":
            empty = row.get("empty_response")
            if not isinstance(empty, bool):
                reasons.append("SQD ledger empty_response must be boolean")
            elif empty:
                empty_response_count += 1
                if covered != requested_end - start + 1:
                    reasons.append("empty SQD response does not cover requested tail")
                if row.get("returned_from") is not None \
                        or row.get("returned_to") is not None \
                        or row.get("n_blocks") != 0:
                    reasons.append("empty SQD response has returned block facts")
            else:
                returned_from = row.get("returned_from")
                returned_to = row.get("returned_to")
                n_blocks = row.get("n_blocks")
                if not _integer(returned_from) or not _integer(returned_to) \
                        or not _integer(n_blocks) or n_blocks <= 0:
                    reasons.append("nonempty SQD response block facts invalid")
                elif not (start <= returned_from <= returned_to == actual_end
                          <= requested_end):
                    reasons.append("nonempty SQD response cursor facts inconsistent")
        ranges.append((start, actual_end))
    return ranges, empty_response_count


def validate_coverage(case_root, coverage_path, pointer_path,
                      case_from_slot, case_to_slot):
    """Validate coverage files and current pointer, returning structured facts."""
    reasons = []
    recomputed = {}
    try:
        case_root = Path(case_root).resolve()
        coverage_path = Path(coverage_path).resolve()
        pointer_path = Path(pointer_path).resolve()
        coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
        pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"ok": False, "reasons": [f"coverage input unreadable: {exc}"],
                "recomputed": recomputed}

    basic = validate_coverage_map(
        coverage, case_from_slot=case_from_slot, case_to_slot=case_to_slot)
    reasons.extend(basic["reasons"])
    try:
        canonical_json(pointer)
    except ValueError as exc:
        reasons.append(f"pointer {exc}")
    if pointer.get("schema") != COVERAGE_POINTER_SCHEMA:
        reasons.append("coverage pointer schema mismatch")
    if pointer.get("probe_id") != coverage.get("probe_id"):
        reasons.append("pointer probe_id mismatch")
    if not isinstance(pointer.get("published_at"), str) or not pointer["published_at"]:
        reasons.append("pointer published_at missing")
    if pointer.get("target") != {"chain": "solana", "token": coverage.get("mint"),
                                  "as_of_block": coverage.get("slot_counts", {}).get("to_slot")}:
        reasons.append("pointer target mismatch")
    if (pointer.get("mode"), pointer.get("verdict"), pointer.get("exit_code")) != (
            "formal", "PASS", 0):
        reasons.append("pointer envelope is not formal PASS/0")
    producer = coverage.get("producer")
    if pointer.get("producer") != producer:
        reasons.append("pointer producer differs from coverage producer")
    expected_producer_path = "scripts/solana/sqd_coverage_probe.py"
    if not isinstance(producer, dict) or producer.get("path") != expected_producer_path:
        reasons.append("coverage producer path invalid")
    else:
        producer_file = Path(__file__).resolve().parents[2] / expected_producer_path
        if not producer_file.is_file() or producer.get("sha256") != sha256_file(producer_file):
            reasons.append("coverage producer sha256 mismatch")
    sqd = coverage.get("sqd") if isinstance(coverage.get("sqd"), dict) else {}
    metadata = sqd.get("metadata_normalized")
    try:
        metadata_sha = sha256_bytes(canonical_json(metadata))
    except ValueError as exc:
        reasons.append(f"SQD metadata invalid: {exc}")
    else:
        if sqd.get("metadata_sha256") != metadata_sha:
            reasons.append("SQD metadata sha256 mismatch")
    if sqd.get("dataset") != "solana-mainnet":
        reasons.append("SQD dataset mismatch")
    if not isinstance(sqd.get("endpoint_fingerprint"), str) \
            or not sqd["endpoint_fingerprint"]:
        reasons.append("SQD endpoint fingerprint invalid")
    if not _integer(sqd.get("finalized_head_at_scan")):
        reasons.append("SQD finalized head invalid")
    if not isinstance(sqd.get("query_body_sha256"), str) \
            or not re.fullmatch(r"[0-9a-f]{64}", sqd["query_body_sha256"]):
        reasons.append("SQD query body sha256 invalid")

    inputs = pointer.get("inputs")
    if not isinstance(inputs, dict):
        reasons.append("pointer inputs missing")
        inputs = {}
    expected_input_keys = {"coverage_map", "slot_counts", "ledger"}
    if coverage.get("skipped_confirmation") is not None:
        expected_input_keys.add("blocks_bitmap")
    if set(inputs) != expected_input_keys:
        reasons.append("pointer inputs conditional key set mismatch")
    paths = {}
    for key in sorted(expected_input_keys):
        paths[key] = _check_file_ref(case_root, inputs.get(key), key, reasons)
    if paths.get("coverage_map") != coverage_path:
        reasons.append("pointer coverage_map path is not supplied coverage path")

    slot_meta = coverage.get("slot_counts") if isinstance(
        coverage.get("slot_counts"), dict) else {}
    counts = b""
    if paths.get("slot_counts"):
        try:
            counts = gzip.decompress(paths["slot_counts"].read_bytes())
        except (OSError, EOFError) as exc:
            reasons.append(f"slot_counts gzip invalid: {exc}")
    for key in ("path", "size", "sha256"):
        expected = inputs.get("slot_counts", {}).get(key)
        actual = slot_meta.get(key)
        if key == "path" and isinstance(expected, str):
            expected = Path(expected).name
        if actual != expected:
            reasons.append(f"coverage slot_counts {key} differs from pointer")
    if slot_meta.get("encoding") != COUNT_ENCODING:
        reasons.append("slot_counts encoding mismatch")
    from_slot, to_slot = slot_meta.get("from_slot"), slot_meta.get("to_slot")
    if not _integer(from_slot) or not _integer(to_slot) or from_slot > to_slot:
        reasons.append("slot_counts interval invalid")
        from_slot, to_slot = case_from_slot, case_to_slot
    elif from_slot > case_from_slot or to_slot < case_to_slot:
        reasons.append("slot_counts interval does not cover case interval")

    ledger_rows = _read_ledger(paths["ledger"], reasons) if paths.get("ledger") else []
    ledger_ranges, empty_response_count = _success_ranges(ledger_rows, reasons)
    scan_ranges = []
    try:
        scan_ranges = [_range_pair(item) for item in coverage.get("scan_ranges", [])]
    except ValueError as exc:
        reasons.append(str(exc))
    structural = validate_slot_counts(
        counts, from_slot, to_slot, scan_ranges, ledger_ranges)
    reasons.extend(structural["reasons"])

    ledger_meta = coverage.get("ledger") if isinstance(coverage.get("ledger"), dict) else {}
    for key in ("path", "size", "sha256"):
        expected = inputs.get("ledger", {}).get(key)
        actual = ledger_meta.get(key)
        if key == "path" and isinstance(expected, str):
            expected = Path(expected).name
        if actual != expected:
            reasons.append(f"coverage ledger {key} differs from pointer")
    success_sha = sha256_bytes(canonical_json(
        [[start, end] for start, end in structural["ledger_union"]]))
    if ledger_meta.get("requests") != len(ledger_rows):
        reasons.append("ledger request count mismatch")
    if ledger_meta.get("success_ranges_sha256") != success_sha:
        reasons.append("ledger success_ranges_sha256 mismatch")

    confirmation = coverage.get("skipped_confirmation")
    blocks_raw = None
    getblocks_complete = []
    if confirmation is not None:
        if not isinstance(confirmation, dict):
            reasons.append("skipped_confirmation must be object or null")
        elif paths.get("blocks_bitmap"):
            try:
                blocks_raw = gzip.decompress(paths["blocks_bitmap"].read_bytes())
            except (OSError, EOFError) as exc:
                reasons.append(f"blocks bitmap gzip invalid: {exc}")
                blocks_raw = b""
            bitmap_meta = confirmation.get("blocks_bitmap", {})
            for key in ("path", "size", "sha256"):
                expected = inputs.get("blocks_bitmap", {}).get(key)
                actual = bitmap_meta.get(key)
                if key == "path" and isinstance(expected, str):
                    expected = Path(expected).name
                if actual != expected:
                    reasons.append(f"blocks bitmap {key} differs from pointer")
            if bitmap_meta.get("encoding") != BITMAP_ENCODING:
                reasons.append("blocks bitmap encoding mismatch")
            bitmap_check = validate_blocks_bitmap(
                blocks_raw, bitmap_meta.get("from_slot"), bitmap_meta.get("to_slot"))
            reasons.extend(bitmap_check["reasons"])
            if (bitmap_meta.get("from_slot"), bitmap_meta.get("to_slot")) != (
                    from_slot, to_slot):
                reasons.append("blocks bitmap interval differs from slot_counts")
            if confirmation.get("method") != "getBlocks" \
                    or confirmation.get("commitment") != "finalized":
                reasons.append("getBlocks confirmation method/commitment invalid")
            if not isinstance(confirmation.get("endpoint_fingerprint"), str) \
                    or not confirmation["endpoint_fingerprint"]:
                reasons.append("getBlocks endpoint fingerprint invalid")
            if not _integer(confirmation.get("reference_head_at_check")):
                reasons.append("getBlocks reference head invalid")
            expected_bitmap_keys = {"path", "size", "sha256", "from_slot", "to_slot",
                                    "encoding"}
            if set(bitmap_meta) != expected_bitmap_keys:
                reasons.append("blocks bitmap metadata shape invalid")
            expected_range_keys = {"from", "to", "response_sha256", "count",
                                   "response_ok", "array_monotonic_unique",
                                   "array_in_range"}
            confirmation_ranges = confirmation.get("ranges", [])
            segment_pairs = []
            for segment in confirmation_ranges:
                if not isinstance(segment, dict) or set(segment) != expected_range_keys:
                    reasons.append("getBlocks range shape invalid")
                    getblocks_complete.append(False)
                    continue
                try:
                    segment_pair = _range_pair(segment, "from", "to")
                    segment_pairs.append(segment_pair)
                except ValueError as exc:
                    reasons.append(f"getBlocks range invalid: {exc}")
                    getblocks_complete.append(False)
                    continue
                if segment_pair[0] < bitmap_meta.get("from_slot") \
                        or segment_pair[1] > bitmap_meta.get("to_slot"):
                    reasons.append("getBlocks range escapes blocks bitmap interval")
                    getblocks_complete.append(False)
                    continue
                if not isinstance(segment.get("response_sha256"), str) \
                        or not re.fullmatch(r"[0-9a-f]{64}", segment["response_sha256"]):
                    reasons.append("getBlocks response sha256 invalid")
                if not _integer(segment.get("count")) or segment["count"] < 0:
                    reasons.append("getBlocks count invalid")
                if any(not isinstance(segment.get(key), bool) for key in (
                        "response_ok", "array_monotonic_unique", "array_in_range")):
                    reasons.append("getBlocks assertion flags invalid")
                enriched = dict(segment)
                enriched["reference_head_at_check"] = confirmation.get(
                    "reference_head_at_check")
                complete = derive_getblocks_complete(
                    enriched, blocks_raw, bitmap_meta.get("from_slot"))
                getblocks_complete.append(complete)
            if not ranges_cover(segment_pairs, from_slot, to_slot):
                reasons.append("getBlocks ranges do not cover slot_counts interval")

    classified = classify_four_states(
        counts, from_slot, confirmation=confirmation, blocks_bitmap=blocks_raw)
    recomputed.update(classified)
    recomputed["probe_id"] = compute_probe_id(coverage)
    recomputed["getblocks_complete"] = getblocks_complete
    recomputed["scan_union"] = structural["scan_union"]
    recomputed["ledger_union"] = structural["ledger_union"]
    recomputed["empty_response_count"] = empty_response_count
    if coverage.get("summary") != classified["summary"]:
        reasons.append("coverage summary mismatch")
    if coverage.get("candidate_slots") != classified["candidate_slots"]:
        reasons.append("candidate_slots mismatch")
    if coverage.get("verdict") != classified["verdict"]:
        reasons.append("coverage verdict mismatch")

    supersedes = pointer.get("supersedes")
    if supersedes is not None:
        if not isinstance(supersedes, str) \
                or not re.fullmatch(r"[0-9a-f]{16}", supersedes):
            reasons.append("pointer supersedes invalid")
        elif not (case_root / "data/sqd_coverage" / supersedes).is_dir():
            reasons.append("pointer supersedes generation is not traceable")
    return {"ok": not reasons, "reasons": reasons, "recomputed": recomputed}


SHARED_MAP_SCHEMA = "sqd-solana-shared-coverage-map/v1"
REPAIR_BUNDLE_SCHEMA = "sqd-solana-repair-bundle/v1"
REPAIR_LAYER_SCHEMA = "sqd-solana-repair-layer/v1"
REPAIR_MAP_SCHEMA = "sqd-solana-slot-index-map/v1"
REPAIR_RESOLUTION_SCHEMA = "sqd-solana-coverage-resolution/v1"
REPAIR_LEDGER_SCHEMA = "sqd-solana-rpc-ledger/v1"
REPAIR_POINTER_SCHEMA = "sqd-solana-repair-pointer/v1"
RECONCILE_SCHEMA = "solana-reconcile/v4"


def validate_shared_map(asset_json_path):
    """Independently validate one reusable shared coverage-map triplet."""
    reasons = []
    asset_path = Path(asset_json_path).resolve()
    try:
        asset = json.loads(asset_path.read_text(encoding="utf-8"))
        canonical_json(asset)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"ok": False, "reasons": [f"shared map unreadable: {exc}"]}
    if asset.get("schema") != SHARED_MAP_SCHEMA:
        reasons.append("shared map schema mismatch")
    version = asset.get("version")
    if not isinstance(version, str) or re.fullmatch(r"[0-9]{8}", version) is None:
        reasons.append("shared map version must be YYYYMMDD")
    if asset.get("ttl_days") != 30:
        reasons.append("shared map ttl_days must be 30")
    if "supersedes" not in asset or (asset.get("supersedes") is not None
                                      and not isinstance(asset.get("supersedes"), str)):
        reasons.append("shared map supersedes invalid")
    if not isinstance(asset.get("generated_at"), str) or not asset["generated_at"]:
        reasons.append("shared map generated_at missing")
    if not isinstance(asset.get("sqd"), dict):
        reasons.append("shared map SQD identity missing")

    loaded = {}
    for key, encoding in (("slot_counts", COUNT_ENCODING),
                          ("blocks_bitmap", BITMAP_ENCODING)):
        meta = asset.get(key)
        expected_keys = {"path", "size", "sha256", "from_slot", "to_slot",
                         "encoding"}
        if not isinstance(meta, dict) or set(meta) != expected_keys:
            reasons.append(f"shared map {key} metadata shape invalid")
            continue
        if meta.get("encoding") != encoding:
            reasons.append(f"shared map {key} encoding mismatch")
        try:
            path = (asset_path.parent / meta["path"]).resolve()
            if path.parent != asset_path.parent or not path.is_file():
                raise ValueError("path escapes asset directory or is missing")
            if path.stat().st_size != meta["size"]:
                reasons.append(f"shared map {key} size mismatch")
            if sha256_file(path) != meta["sha256"]:
                reasons.append(f"shared map {key} sha256 mismatch")
            loaded[key] = gzip.decompress(path.read_bytes())
        except (OSError, EOFError, KeyError, TypeError, ValueError) as exc:
            reasons.append(f"shared map {key} unreadable: {exc}")

    counts = loaded.get("slot_counts", b"")
    blocks = loaded.get("blocks_bitmap", b"")
    count_meta = asset.get("slot_counts") or {}
    block_meta = asset.get("blocks_bitmap") or {}
    lower, upper = count_meta.get("from_slot"), count_meta.get("to_slot")
    if not _integer(lower) or not _integer(upper) or lower > upper:
        reasons.append("shared map interval invalid")
    else:
        if len(counts) != upper - lower + 1:
            reasons.append("shared map counts length mismatch")
        if (block_meta.get("from_slot"), block_meta.get("to_slot")) != (lower, upper):
            reasons.append("shared map binary intervals differ")
        bitmap = validate_blocks_bitmap(blocks, lower, upper)
        reasons.extend(f"shared map {reason}" for reason in bitmap["reasons"])

    canary = asset.get("canary")
    slots = canary.get("slots") if isinstance(canary, dict) else None
    canary_counts = canary.get("counts") if isinstance(canary, dict) else None
    if not isinstance(slots, list) or len(slots) != 64 \
            or not isinstance(canary_counts, list) or len(canary_counts) != 64:
        reasons.append("shared map canary must contain 64 slots and counts")
    elif _integer(lower) and _integer(upper) \
            and len(counts) == upper - lower + 1:
        if slots != sorted(set(slots)) or any(
                not _integer(slot) or slot < lower or slot > upper for slot in slots):
            reasons.append("shared map canary slots invalid")
        elif any(not _integer(value) or not (0 <= value <= 255)
                 for value in canary_counts):
            reasons.append("shared map canary counts invalid")
        elif any(counts[slot - lower] != value
                 for slot, value in zip(slots, canary_counts)):
            reasons.append("shared map canary differs from counts")
        elif any(counts[slot - lower] < 2 for slot in slots):
            reasons.append("shared map canary includes slot without block header")
    elif isinstance(slots, list) and isinstance(canary_counts, list):
        reasons.append("shared map canary cannot be checked against invalid counts")

    candidates = asset.get("candidate_slots")
    refuted = asset.get("refuted_slots")
    if not isinstance(candidates, list) or candidates != sorted(set(candidates)):
        reasons.append("shared map candidate_slots invalid")
    if not isinstance(refuted, list) or refuted != sorted(set(refuted)):
        reasons.append("shared map refuted_slots invalid")
    if _integer(lower) and len(counts) == max(0, upper - lower + 1):
        confirmation = None
        if blocks:
            segment = {"from": lower, "to": upper,
                       "response_sha256": sha256_bytes(blocks),
                       "count": sum(byte.bit_count() for byte in blocks),
                       "response_ok": True, "array_monotonic_unique": True,
                       "array_in_range": True}
            confirmation = {
                "reference_head_at_check": upper,
                "blocks_bitmap": {"from_slot": lower, "to_slot": upper},
                "ranges": [segment],
            }
        classified = classify_four_states(
            counts, lower, confirmation=confirmation, blocks_bitmap=blocks)
        if candidates != classified["candidate_slots"]:
            reasons.append("shared map candidate_slots do not recompute from binaries")
    return {"ok": not reasons, "reasons": reasons, "asset": asset,
            "counts": counts, "blocks_bitmap": blocks}


def _repair_path(case_root, generation, value, label, reasons):
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        reasons.append(f"{label} path invalid")
        return None
    base = case_root if value.startswith("data/") else generation
    try:
        path = _safe_case_path(base, value)
    except ValueError as exc:
        reasons.append(f"{label}: {exc}")
        return None
    return path


def _repair_ref(case_root, generation, ref, label, reasons):
    if not isinstance(ref, dict) or not {"path", "size", "sha256"}.issubset(ref):
        reasons.append(f"{label} reference shape invalid")
        return None
    path = _repair_path(case_root, generation, ref.get("path"), label, reasons)
    if path is None or not path.is_file():
        reasons.append(f"{label} file missing")
        return None
    if path.stat().st_size != ref.get("size"):
        reasons.append(f"{label} size mismatch")
    if sha256_file(path) != ref.get("sha256"):
        reasons.append(f"{label} sha256 mismatch")
    return path


def _jsonl(path, reasons, label):
    rows = []
    try:
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            row = json.loads(line)
            canonical_json(row)
            rows.append(row)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        reasons.append(f"{label} invalid: {exc}")
    return rows


def _edge_rows(path, reasons, label):
    rows = []
    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                if not isinstance(row, list) or len(row) != 7:
                    raise ValueError("edge must contain seven fields")
                ts, slot, tx_index, instr, source, target, amount = row
                if any(not _integer(item) for item in (ts, slot, tx_index, amount)) \
                        or instr != -1 or amount <= 0 \
                        or not isinstance(source, str) or not isinstance(target, str):
                    raise ValueError("edge field contract invalid")
                rows.append(tuple(row))
    except (OSError, EOFError, ValueError, json.JSONDecodeError) as exc:
        reasons.append(f"{label} invalid: {exc}")
    return rows


def _edge_sort(row):
    return row[1], row[2], row[4], row[5], str(row[6])


def _edge_evidence(rows):
    digest = hashlib.sha256()
    for row in rows:
        digest.update((json.dumps(list(row), ensure_ascii=False) + "\n").encode())
    return digest.hexdigest(), len(rows)


def _repair_gid(material):
    value = dict(material)
    for key in ("gid", "generated_at", "rpc_ledger", "bundle_sha256"):
        value.pop(key, None)
    value["kind"] = "repair"
    return sha256_bytes(canonical_json(value))[:16]


def validate_repair_pointer(pointer, *, expected_mint, expected_gid,
                            expected_bundle_sha256):
    """Validate the current repair pointer envelope and bundle binding."""
    reasons = []
    if not isinstance(pointer, dict) or pointer.get("schema") != REPAIR_POINTER_SCHEMA:
        reasons.append("repair pointer schema mismatch")
        return {"ok": False, "reasons": reasons}
    if pointer.get("target", {}).get("chain") != "solana" \
            or pointer.get("target", {}).get("token") != expected_mint:
        reasons.append("repair pointer target mismatch")
    if (pointer.get("mode"), pointer.get("verdict"), pointer.get("exit_code")) \
            != ("formal", "PASS", 0):
        reasons.append("repair pointer is not formal PASS/0")
    if pointer.get("gid") != expected_gid:
        reasons.append("repair pointer gid mismatch")
    if pointer.get("inputs", {}).get("bundle", {}).get("sha256") \
            != expected_bundle_sha256:
        reasons.append("repair pointer bundle sha256 mismatch")
    return {"ok": not reasons, "reasons": reasons}


def validate_beta_trace(trace, *, case_root, generation=None):
    """Independently validate E25 trace structure and its three live inputs."""
    reasons = []
    case_root = Path(case_root).resolve()
    generation = Path(generation or case_root).resolve()
    if not isinstance(trace, dict):
        return {"ok": False, "reasons": ["beta trace must be an object"]}
    try:
        canonical_json(trace)
    except ValueError as exc:
        reasons.append(f"beta trace canonicalization failed: {exc}")
    if trace.get("schema") != "sqd-solana-beta-trace/v1":
        reasons.append("beta trace schema mismatch")
    inputs = trace.get("inputs")
    if not isinstance(inputs, dict) or set(inputs) != {
            "receipt", "replay_final_balances", "holders_owners"}:
        reasons.append("beta trace input key set mismatch")
        inputs = {}
    loaded = {}
    for name in ("receipt", "replay_final_balances", "holders_owners"):
        path = _repair_ref(case_root, generation, inputs.get(name),
                           f"beta input {name}", reasons)
        if path is not None:
            try:
                loaded[name] = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                reasons.append(f"beta input {name} unreadable: {exc}")
    receipt = loaded.get("receipt", {})
    replay = loaded.get("replay_final_balances", {})
    snapshot = loaded.get("holders_owners", {})
    if not isinstance(receipt, dict) or not isinstance(receipt.get("gate_pass"), bool):
        reasons.append("beta receipt gate_pass invalid")
    for label, value in (("replay", replay), ("snapshot", snapshot)):
        if not isinstance(value, dict) or any(
                not isinstance(owner, str) or not owner or not _integer(amount)
                for owner, amount in (value.items() if isinstance(value, dict) else [])):
            reasons.append(f"beta {label} owner balances invalid")
    expected = {owner: (replay.get(owner, 0), snapshot.get(owner, 0))
                for owner in sorted(set(replay) | set(snapshot))
                if replay.get(owner, 0) != snapshot.get(owner, 0)} \
        if isinstance(replay, dict) and isinstance(snapshot, dict) else {}
    residual = trace.get("residual_owners")
    if not isinstance(residual, list):
        reasons.append("beta residual_owners must be an array")
        residual = []
    owners = [row.get("owner") for row in residual if isinstance(row, dict)]
    if owners != sorted(set(owners)):
        reasons.append("beta residual owners are not sorted unique")
    for row in residual:
        if not isinstance(row, dict) or set(row) != {"owner", "replay", "snapshot"}:
            reasons.append("beta residual owner row shape invalid")
            continue
        pair = expected.get(row["owner"])
        if pair != (row["replay"], row["snapshot"]):
            reasons.append("beta residual owner differs from bound inputs")
    if receipt.get("gate_pass") is True and residual:
        reasons.append("gate-passing receipt cannot produce beta residual owners")

    rounds = trace.get("rounds")
    if not isinstance(rounds, list):
        reasons.append("beta rounds must be an array")
        rounds = []
    union = set()
    round_owners = []
    for row in rounds:
        if not isinstance(row, dict):
            reasons.append("beta round must be an object")
            continue
        owner = row.get("owner")
        round_owners.append(owner)
        if owner not in owners or row.get("round") not in {1, 2, 3}:
            reasons.append("beta round owner/index invalid")
        probes = row.get("probes")
        if not isinstance(probes, list) or len(probes) > 40:
            reasons.append("beta probes missing or exceed owner limit")
            probes = []
        probe_slots = [item.get("slot") for item in probes
                       if isinstance(item, dict)]
        if probe_slots != sorted(set(probe_slots)):
            reasons.append("beta probes are not slot-sorted unique")
        for item in probes:
            if not isinstance(item, dict):
                reasons.append("beta probe row invalid")
                continue
            actual, replay_value = item.get("sqd_post_amount"), item.get(
                "replay_balance")
            if actual is not None and not _integer(actual):
                reasons.append("beta probe SQD amount invalid")
            if not _integer(replay_value) or item.get("match") != (
                    actual is not None and actual == replay_value):
                reasons.append("beta probe match is not mechanically derived")
            for key in ("query_body_sha256", "response_sha256"):
                if not isinstance(item.get(key), str) or re.fullmatch(
                        r"[0-9a-f]{64}", item[key]) is None:
                    reasons.append(f"beta probe {key} invalid")
        breakpoint = row.get("breakpoint_slot")
        window = row.get("window")
        fingerprint = row.get("fingerprint")
        candidates = row.get("candidate_slots")
        if breakpoint is None:
            if window is not None or fingerprint not in ([], None) or candidates not in ([], None):
                reasons.append("beta no-breakpoint round has derived artifacts")
            candidates = []
        else:
            if not _integer(breakpoint) or not isinstance(window, dict) \
                    or set(window) != {"from", "to"} \
                    or not _integer(window.get("from")) \
                    or not _integer(window.get("to")) \
                    or not window["from"] <= breakpoint <= window["to"]:
                reasons.append("beta breakpoint/window invalid")
            if not isinstance(fingerprint, list):
                reasons.append("beta fingerprint missing")
                fingerprint = []
            fp_slots = [item.get("slot") for item in fingerprint
                        if isinstance(item, dict)]
            expected_window = {
                "from": max(0, breakpoint - 64), "to": breakpoint + 64}
            if window != expected_window:
                reasons.append("beta fingerprint window is not exact +/-64")
            if fp_slots != list(range(window.get("from", 0),
                                      window.get("to", -1) + 1)):
                reasons.append("beta fingerprint does not cover its full window")
            if any(not isinstance(item, dict)
                   or set(item) != {"slot", "count"}
                   or not _integer(item.get("count"))
                   or item["count"] < -1 for item in fingerprint):
                reasons.append("beta fingerprint row invalid")
            derived = sorted(item.get("slot") for item in fingerprint
                             if isinstance(item, dict) and item.get("count") == 0)
            if candidates != derived:
                reasons.append("beta round candidates differ from fingerprint")
                candidates = derived
        union.update(candidates or [])
    if round_owners != owners:
        reasons.append("beta rounds do not cover residual owners in order")
    candidates = trace.get("candidate_slots")
    if candidates != sorted(union):
        reasons.append("beta trace candidate union mismatch")
    return {"ok": not reasons, "reasons": reasons,
            "candidate_slots": sorted(union), "residual_owners": owners}


def _repair_state_matches(state, header_present, nonce_count):
    if not _integer(nonce_count) or nonce_count < 0:
        return False
    if state in {"NO_HEADER", "MISSING_BLOCK", "SKIPPED_CONFIRMED"}:
        return not header_present
    if state in {"DEFECT_CANDIDATE", "ERA_UNCERTAIN"}:
        return header_present and nonce_count == 0
    if state == "HEALTHY":
        return header_present and nonce_count > 0
    return False


def _repair_getblock_params_digest(slot):
    body = {
        "jsonrpc": "2.0", "id": slot, "method": "getBlock",
        "params": [slot, {"commitment": "finalized",
                          "transactionDetails": "full", "encoding": "json",
                          "rewards": False,
                          "maxSupportedTransactionVersion": 0}],
    }
    return sha256_bytes(canonical_json(body))


def validate_repair_bundle_deep(bundle_path, *, case_root, current_base,
                                live_canary=0, live_canary_fetch=None):
    """Rebuild a repair generation without importing producer/replay code."""
    reasons = []
    case_root = Path(case_root).resolve()
    bundle_path = Path(bundle_path).resolve()
    generation = bundle_path.parent
    try:
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        canonical_json(bundle)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"ok": False, "reasons": [f"bundle unreadable: {exc}"]}
    if bundle.get("schema") != REPAIR_BUNDLE_SCHEMA or bundle.get("kind") != "repair":
        reasons.append("repair bundle schema/kind mismatch")
    source = (bundle.get("reference") or {}).get("source")
    mode = bundle.get("mode")
    if (mode == "formal") != (source == "live"):
        reasons.append("formal/reference source equivalence violated")
    if mode not in {"formal", "exploration"}:
        reasons.append("bundle mode invalid")
    base = bundle.get("base") if isinstance(bundle.get("base"), dict) else {}
    current_edge_sha = (current_base.get("edge_sha256")
                        if isinstance(current_base, dict) else None)
    if current_edge_sha is None and isinstance(current_base, (tuple, list)) \
            and current_base:
        current_edge_sha = sha256_file(current_base[0])
    if base.get("edge_sha256") != current_edge_sha:
        reasons.append("bundle base edge sha256 differs from current base")

    refs = {}
    for key in ("coverage_resolution", "repair_layer", "slot_index_map",
                "evidence_manifest", "rpc_ledger"):
        refs[key] = _repair_ref(case_root, generation, bundle.get(key), key, reasons)
    merged = bundle.get("merged") if isinstance(bundle.get("merged"), dict) else {}
    base_edge = _repair_path(case_root, generation, base.get("edge_file"),
                             "base edge", reasons)
    merged_edge = _repair_path(case_root, generation, merged.get("edge_file"),
                               "merged edge", reasons)
    merged_meta_path = _repair_path(case_root, generation, merged.get("meta_file"),
                                    "merged meta", reasons)
    for path, expected, label in (
            (base_edge, base.get("edge_sha256"), "base edge"),
            (merged_edge, merged.get("edge_sha256"), "merged edge"),
            (merged_meta_path, merged.get("meta_sha256"), "merged meta")):
        if path is None or not path.is_file():
            reasons.append(f"{label} missing")
        elif sha256_file(path) != expected:
            reasons.append(f"{label} sha256 mismatch")

    def read_json(path, label):
        if path is None:
            return {}
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            canonical_json(value)
            return value
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            reasons.append(f"{label} invalid: {exc}")
            return {}

    resolution = read_json(refs.get("coverage_resolution"), "resolution")
    manifest = read_json(refs.get("evidence_manifest"), "evidence manifest")
    meta = read_json(merged_meta_path, "merged meta")
    layer_rows = _jsonl(refs["repair_layer"], reasons, "repair layer") \
        if refs.get("repair_layer") else []
    map_rows = _jsonl(refs["slot_index_map"], reasons, "slot index map") \
        if refs.get("slot_index_map") else []
    ledger_rows = _jsonl(refs["rpc_ledger"], reasons, "RPC ledger") \
        if refs.get("rpc_ledger") else []
    if resolution.get("schema") != REPAIR_RESOLUTION_SCHEMA:
        reasons.append("resolution schema mismatch")
    if not layer_rows or layer_rows[0].get("schema") != REPAIR_LAYER_SCHEMA:
        reasons.append("repair layer header mismatch")
    if not map_rows or map_rows[0].get("schema") != REPAIR_MAP_SCHEMA:
        reasons.append("slot index map header mismatch")
    if not ledger_rows or ledger_rows[0].get("schema") != REPAIR_LEDGER_SCHEMA:
        reasons.append("RPC ledger header mismatch")
    digest = bundle.get("plan_digest")
    plan_values = [resolution.get("plan_digest"), meta.get("plan_digest")]
    if layer_rows:
        plan_values.append(layer_rows[0].get("plan_digest"))
    if map_rows:
        plan_values.append(map_rows[0].get("plan_digest"))
    if ledger_rows:
        plan_values.append(ledger_rows[0].get("plan_digest"))
    if any(value != digest for value in plan_values):
        reasons.append("plan_digest differs across generation")
    if ledger_rows:
        if ledger_rows[0].get("plan_digest") != digest:
            reasons.append("RPC ledger header plan_digest mismatch")
        seqs = []
        for row in ledger_rows[1:]:
            seqs.append(row.get("seq"))
            required = {"seq", "ts", "method", "params_digest", "slot",
                        "endpoint_fingerprint", "http_status", "bytes",
                        "credits_estimate", "result_sha256", "attempt"}
            if not isinstance(row, dict) or set(row) != required \
                    or row.get("method") != "getBlock" \
                    or any(not _integer(row.get(key)) for key in (
                        "seq", "ts", "slot", "http_status", "bytes",
                        "credits_estimate", "attempt")) \
                    or any(not isinstance(row.get(key), str) or re.fullmatch(
                        r"[0-9a-f]{64}", row[key]) is None for key in (
                            "params_digest", "endpoint_fingerprint",
                            "result_sha256")):
                reasons.append("RPC ledger row contract invalid")
        if seqs != list(range(len(seqs))):
            reasons.append("RPC ledger sequence is not contiguous")
        ledger_slots = [row.get("slot") for row in ledger_rows[1:]
                        if isinstance(row, dict)]
        if len(ledger_slots) != len(set(ledger_slots)):
            reasons.append("RPC ledger slots are not unique")
        if (bundle.get("rpc_ledger") or {}).get("requests") != len(
                ledger_rows) - 1:
            reasons.append("bundle RPC ledger request count mismatch")
    if "gid" in meta or "bundle_sha256" in meta:
        reasons.append("merged meta contains forbidden circular binding")
    if meta.get("base_edge_sha256") != base.get("edge_sha256"):
        reasons.append("merged meta base binding mismatch")

    evidence = {}
    expected_manifest = []
    if not isinstance(manifest, list):
        reasons.append("evidence manifest must be an array")
        manifest = []
    for item in manifest:
        path = _repair_ref(case_root, generation, item, "evidence", reasons)
        if path:
            evidence[item["path"]] = read_json(path, item["path"])
            expected_manifest.append(item)
    if manifest != sorted(manifest, key=lambda item: item.get("path", "")):
        reasons.append("evidence manifest is not path-sorted")
    if live_canary:
        if not _integer(live_canary) or live_canary < 0:
            reasons.append("live_canary must be a nonnegative integer")
        elif not callable(live_canary_fetch):
            reasons.append("live canary requested without a reference transport")
        else:
            slots = sorted({row.get("slot") for row in resolution.get("census", [])
                            if _integer(row.get("slot"))})[:live_canary]
            for slot in slots:
                try:
                    block = live_canary_fetch(slot)
                    expected = evidence[f"evidence/{slot}.ref.json"]
                    signatures = [((tx.get("transaction") or {}).get(
                        "signatures") or [None])[0]
                                  for tx in block.get("transactions", [])]
                    expected_signatures = [row.get("signature")
                                           for row in expected.get("transactions", [])]
                    if block.get("blockhash") != expected.get("blockhash") \
                            or signatures != expected_signatures:
                        reasons.append(f"live canary differs at slot {slot}")
                except Exception as exc:
                    reasons.append(f"live canary failed at slot {slot}: {exc}")

    layer = layer_rows[1:] if layer_rows else []
    maps = map_rows[1:] if map_rows else []
    signatures = [row.get("signature") for row in layer]
    if signatures != sorted(set(signatures)):
        reasons.append("repair layer signatures are not sorted unique")
    confirmed = {row.get("slot") for row in resolution.get("census", [])
                 if isinstance(row, dict) and str(row.get("result", "")).startswith("confirmed_")}
    census_slots = {row.get("slot") for row in resolution.get("census", [])
                    if isinstance(row, dict)}
    coverage_candidates = set()
    coverage_map_ref = (bundle.get("coverage") or {}).get("map")
    coverage_map_path = _repair_ref(case_root, generation, coverage_map_ref,
                                    "coverage map", reasons)
    coverage_map = read_json(coverage_map_path, "coverage map")
    coverage_candidates.update(coverage_map.get("candidate_slots") or [])
    plan_candidates = resolution.get("plan_candidates")
    if not isinstance(plan_candidates, dict) or set(plan_candidates) != {
            "coverage", "beta"}:
        reasons.append("resolution plan_candidates shape invalid")
        plan_candidates = {"coverage": [], "beta": []}
    for key in ("coverage", "beta"):
        values = plan_candidates.get(key)
        if not isinstance(values, list) or values != sorted(set(values)) \
                or any(not _integer(slot) for slot in values):
            reasons.append(f"resolution plan_candidates.{key} invalid")
            plan_candidates[key] = []
    if plan_candidates["coverage"] != sorted(coverage_candidates):
        reasons.append("resolution coverage candidates differ from coverage map")
    beta_trace = evidence.get("evidence/beta_trace.json")
    if isinstance(beta_trace, dict):
        beta_checked = validate_beta_trace(
            beta_trace, case_root=case_root, generation=generation)
        reasons.extend(beta_checked["reasons"])
        if beta_checked["candidate_slots"] != plan_candidates["beta"]:
            reasons.append("plan beta candidates differ from beta trace")
    elif plan_candidates["beta"]:
        reasons.append("beta candidates require beta_trace evidence")
    all_candidates = set(plan_candidates["coverage"]) | set(
        plan_candidates["beta"])
    if not all_candidates.issubset(census_slots):
        reasons.append("plan candidates lack census disposition")
    effective = ("INCONCLUSIVE" if not all_candidates.issubset(census_slots)
                 else "DEFECTS_CONFIRMED" if confirmed
                 else "NO_KNOWN_NONCE_OMISSION_DETECTED")
    if resolution.get("effective_verdict") != effective:
        reasons.append("resolution effective verdict mismatch")
    # 加固(缺口1)：formal 修复的 census 确认集必须全部落在候选集内。否则逐 slot 严格
    # 校验（其遍历主键含候选集）会漏掉它们，而修复边准入只查 `slot in confirmed`，
    # 攻击者即可凭一条自报 confirmed census 行让凭空修复边通过深验。
    # exploration 用本地证据缓存，可确认自扫（SQD 指纹）漏标的缺陷，故豁免此包含。
    if mode == "formal" and not confirmed.issubset(all_candidates):
        reasons.append("confirmed census slots escape candidate set")
    # 加固(缺口1)：干净 coverage 判定不得携带任何 confirmed 处置或修复边。
    if effective == "NO_KNOWN_NONCE_OMISSION_DETECTED" and (
            confirmed or (bundle.get("repair_layer") or {}).get("edges")):
        reasons.append("clean coverage verdict carries confirmed census or repair edges")
    # 加固(缺口1)：formal 修复不得携带 exploration 指纹（null nonce 复查），
    # 且该判定不依赖候选循环是否触达对应 slot。
    if mode == "formal" and any(
            row.get("sqd_nonce_count_at_repair") is None
            for row in resolution.get("census", []) if isinstance(row, dict)):
        reasons.append("formal repair census carries exploration null-nonce fingerprint")

    coverage_check = None
    slot_meta = coverage_map.get("slot_counts", {}) if isinstance(
        coverage_map, dict) else {}
    if coverage_map_path is not None:
        pointer_path = case_root / "data/sqd_coverage/CURRENT.json"
        coverage_check = validate_coverage(
            case_root, coverage_map_path, pointer_path,
            slot_meta.get("from_slot"), slot_meta.get("to_slot"))
        if not coverage_check["ok"]:
            reasons.append("bundle coverage no longer validates: "
                           + "; ".join(coverage_check["reasons"]))
    state_by_slot = {}
    if coverage_check and coverage_check["ok"]:
        lower = slot_meta["from_slot"]
        state_by_slot = {lower + index: state for index, state in enumerate(
            coverage_check["recomputed"]["states"])}
    census_by_slot = {row.get("slot"): row for row in resolution.get("census", [])
                      if isinstance(row, dict)}
    ledger_by_slot = {row.get("slot"): row for row in ledger_rows[1:]
                      if isinstance(row, dict) and _integer(row.get("slot"))}
    # 加固(缺口1)：formal 逐 slot 严格校验的遍历主键 = 候选集 ∪ census 确认集 ∪ 修复层
    # 各 slot。任何"实际被确认为缺陷 / 实际产生修复边"的 slot 都必须逐个跑严格校验，
    # 否则候选集为空/不含该 slot 时严格校验被整段跳过。exploration 探索代不进入正式
    # 发布路径，保持原候选集遍历以免误伤其"本地证据确认自扫漏标缺陷"的合法语义。
    repair_touched = {slot for slot in all_candidates if _integer(slot)}
    if mode == "formal":
        repair_touched |= {slot for slot in confirmed if _integer(slot)}
        repair_touched |= {item.get("slot") for item in layer
                           if _integer(item.get("slot"))}
    for slot in sorted(repair_touched):
        row = census_by_slot.get(slot, {})
        evidence_row = evidence.get(f"evidence/{slot}.sqd.json", {})
        expected_state = state_by_slot.get(slot)
        if row.get("coverage_state") != expected_state \
                or evidence_row.get("coverage_state") != expected_state:
            reasons.append(f"coverage state does not recompute for {slot}")
        nonce_count = row.get("sqd_nonce_count_at_repair")
        if evidence_row.get("sqd_nonce_count_at_repair") != nonce_count:
            reasons.append(f"repair nonce count differs from evidence for {slot}")
        if mode == "formal":
            header_present = evidence_row.get("blockhash") is not None
            if not _repair_state_matches(expected_state, header_present, nonce_count):
                reasons.append(f"repair coverage state semantics mismatch for {slot}")
            for key in ("query_body_sha256", "response_sha256",
                        "coverage_probe_query_sha256",
                        "coverage_probe_response_sha256"):
                if not isinstance(evidence_row.get(key), str) or re.fullmatch(
                        r"[0-9a-f]{64}", evidence_row[key]) is None:
                    reasons.append(f"repair state evidence {key} invalid for {slot}")
            ledger_row = ledger_by_slot.get(slot)
            ref_row = evidence.get(f"evidence/{slot}.ref.json", {})
            if not isinstance(ledger_row, dict) \
                    or ledger_row.get("params_digest") != _repair_getblock_params_digest(slot) \
                    or ledger_row.get("result_sha256") != ref_row.get(
                        "raw_response_sha256"):
                reasons.append(f"repair ledger/evidence resume identity mismatch for {slot}")
        elif nonce_count is not None:
            reasons.append("exploration cache repair must use null nonce recheck")
    # 加固(缺口1)：formal 下 rpc_ledger 必须为每个修复 slot 留下实物 getBlock 请求，
    # 请求数不得少于修复层触及的 slot 数。
    if mode == "formal":
        repair_layer_slots = {item.get("slot") for item in layer
                              if _integer(item.get("slot"))}
        if len(ledger_rows) - 1 < len(repair_layer_slots):
            reasons.append("formal repair ledger has fewer getBlock requests than repair slots")

    map_lookup = {}
    for item in maps:
        slot = item.get("slot")
        triples = item.get("map")
        if not _integer(slot) or not isinstance(triples, list):
            reasons.append("slot index map row invalid")
            continue
        columns = list(zip(*triples)) if triples else [(), (), ()]
        if any(len(set(column)) != len(column) for column in columns) \
                or triples != sorted(triples, key=lambda row: row[0]):
            reasons.append(f"slot index map not bijective for {slot}")
        map_lookup[slot] = {row[0]: row[1] for row in triples}
        sqd_evidence = evidence.get(f"evidence/{slot}.sqd.json", {})
        ref_evidence = evidence.get(f"evidence/{slot}.ref.json", {})
        reference_rows = ref_evidence.get("transactions", [])
        nonvote = [row.get("signature") for row in reference_rows
                   if isinstance(row, dict) and row.get("is_vote") is False]
        if len(nonvote) != len(set(nonvote)) or any(not value for value in nonvote):
            reasons.append(f"reference transaction identity invalid for {slot}")
        else:
            ordinal = {signature: index for index, signature in enumerate(nonvote)}
            expected_map = []
            for row in sqd_evidence.get("transactions", []):
                index, signature = row.get("index"), row.get("signature")
                if not _integer(index) or signature not in ordinal:
                    reasons.append(f"SQD/reference transaction identity mismatch for {slot}")
                    expected_map = None
                    break
                expected_map.append([index, ordinal[signature], signature])
            if expected_map is not None and triples != sorted(
                    expected_map, key=lambda row: row[0]):
                reasons.append(f"slot index map differs from evidence for {slot}")
        if item.get("blockhash") != ref_evidence.get("blockhash") \
                or (sqd_evidence.get("blockhash") is not None
                    and sqd_evidence.get("blockhash") != ref_evidence.get("blockhash")):
            reasons.append(f"blockhash mismatch for repair slot {slot}")

    repair_edges = []
    for item in layer:
        slot = item.get("slot")
        sqd = evidence.get(item.get("evidence", {}).get("sqd"), {})
        sqd_signatures = {row.get("signature") for row in sqd.get("transactions", [])}
        if item.get("signature") in sqd_signatures:
            reasons.append("repair signature is present in SQD evidence")
        if slot not in confirmed:
            reasons.append("repair transaction lacks confirmed census support")
        for edge in item.get("edges") or []:
            if len(edge) != 7 or edge[1] != slot or edge[2] != item.get("nonvote_ordinal") \
                    or edge[3] != -1:
                reasons.append("repair edge identity mismatch")
            else:
                repair_edges.append(tuple(edge))

    base_rows = _edge_rows(base_edge, reasons, "base edges") if base_edge else []
    rebuilt = []
    for row in base_rows:
        if row[1] in map_lookup:
            if row[2] not in map_lookup[row[1]]:
                reasons.append("base edge lacks slot-index map solution")
                continue
            row = (row[0], row[1], map_lookup[row[1]][row[2]], *row[3:])
        rebuilt.append(row)
    rebuilt.extend(repair_edges)
    rebuilt.sort(key=_edge_sort)
    actual_merged = _edge_rows(merged_edge, reasons, "merged edges") if merged_edge else []
    if actual_merged != rebuilt:
        reasons.append("merged edges do not equal f(base,layer,map)")
    # 加固(缺口3)：所有 merged 边的 slot 必须落在声明的 coverage 窗口 [from,to] 内，
    # 且声明窗口 upper 必须与 base.finalized_upper_slot 一致；否则 slot>声明 upper 的
    # 边（谎报采集时点/夹带超窗口数据）会被无声混入余额与供应。
    window_lower = slot_meta.get("from_slot")
    window_upper = slot_meta.get("to_slot")
    if _integer(window_lower) and _integer(window_upper):
        if any(not (window_lower <= row[1] <= window_upper)
               for row in actual_merged):
            reasons.append("merged edge slot escapes declared coverage window")
        if _integer(base.get("finalized_upper_slot")) \
                and base.get("finalized_upper_slot") != window_upper:
            reasons.append("base finalized_upper_slot differs from coverage window upper")
    logical_sha, logical_rows = _edge_evidence(actual_merged)
    if merged.get("edge_logical_sha256") != logical_sha \
            or meta.get("edge_logical_sha256") != logical_sha:
        reasons.append("merged logical edge sha256 mismatch")
    if merged.get("edge_rows") != logical_rows or meta.get("edge_rows") != logical_rows:
        reasons.append("merged edge row count mismatch")
    if logical_rows != base.get("edge_rows", -1) + len(repair_edges):
        reasons.append("merged row count identity violated")
    if (bundle.get("repair_layer") or {}).get("edges") != len(repair_edges):
        reasons.append("bundle repair edge count mismatch")

    gid_material = {
        "plan_digest": digest, "kind": "repair", "supersedes": bundle.get("supersedes"),
        "census": resolution.get("census", []), "transactions": layer,
        "slot_index_map": maps, "evidence_manifest": manifest,
        "mode": mode, "reference": {"source": source},
    }
    recomputed_gid = _repair_gid(gid_material)
    if bundle.get("gid") != recomputed_gid or generation.name != f"gen-{bundle.get('gid')}":
        reasons.append("bundle gid or generation directory mismatch")
    return {"ok": not reasons, "reasons": reasons, "bundle": bundle,
            "gid": recomputed_gid, "effective_verdict": effective,
            "edge_rows": logical_rows}


def validate_verdict_gate_triad(value, exit_code=None, gate_pass=None):
    """Return whether E11's verdict/exit_code/gate_pass triad is exact.

    ``value`` may be the receipt object or the verdict string.  Keeping this
    pure makes the rule reusable by producers, deep consumers and mutation
    tests without importing the generic receipt validator.
    """
    if isinstance(value, dict):
        verdict = value.get("verdict")
        exit_code = value.get("exit_code")
        gate_pass = value.get("gate_pass")
    else:
        verdict = value
    return ((gate_pass is True and verdict == "PASS" and exit_code == 0)
            or (gate_pass is False and verdict == "FAIL" and exit_code == 2))


def _load_json_object(path, label, reasons):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        canonical_json(value)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        reasons.append(f"{label} unreadable: {exc}")
        return {}
    if not isinstance(value, dict):
        reasons.append(f"{label} must be an object")
        return {}
    return value


def _snapshot_output_path(case_root, snapshot_path, ref, reasons):
    if not isinstance(ref, dict) or not {"path", "size", "sha256"}.issubset(ref):
        reasons.append("holders snapshot owners reference invalid")
        return None
    shown = ref.get("path")
    if not isinstance(shown, str) or not shown or Path(shown).is_absolute():
        reasons.append("holders snapshot owners path invalid")
        return None
    candidates = [Path(snapshot_path).parent / shown, Path(case_root) / shown]
    path = next((candidate.resolve() for candidate in candidates
                 if candidate.is_file()), None)
    root = Path(case_root).resolve()
    if path is None or (path != root and root not in path.parents):
        reasons.append("holders snapshot owners path missing or escapes case")
        return None
    if path.stat().st_size != ref.get("size") or sha256_file(path) != ref.get("sha256"):
        reasons.append("holders snapshot owners reference mismatch")
    return path


def validate_reconcile_v4(receipt, *, case_root=None, receipt_path=None):
    """Validate the v4 envelope shape; deep validation is path based below."""
    reasons = []
    if not isinstance(receipt, dict):
        return {"ok": False, "reasons": ["reconcile receipt must be an object"]}
    try:
        canonical_json(receipt)
    except ValueError as exc:
        reasons.append(f"reconcile canonicalization failed: {exc}")
    if receipt.get("schema") != RECONCILE_SCHEMA:
        reasons.append("reconcile schema mismatch")
    if receipt.get("mode") != "formal":
        reasons.append("reconcile mode must be formal")
    target = receipt.get("target")
    if not isinstance(target, dict) or set(target) != {
            "chain", "token", "as_of_block"} \
            or target.get("chain") != "solana" \
            or not isinstance(target.get("token"), str) \
            or not target.get("token") \
            or not _integer(target.get("as_of_block")):
        reasons.append("reconcile target invalid")
    if not validate_verdict_gate_triad(receipt):
        reasons.append("verdict/exit_code/gate_pass triad inconsistent")
    for name in ("minted_raw", "burned_raw", "snapshot_supply_raw",
                 "net_supply_raw", "negative_balance_count",
                 "snapshot_mismatch_count", "edge_count"):
        if not _integer(receipt.get(name)) or receipt[name] < 0:
            reasons.append(f"reconcile {name} must be a nonnegative JSON int")
    for name in ("snapshot_present", "snapshot_meta_present", "snapshot_closed"):
        if not isinstance(receipt.get(name), bool):
            reasons.append(f"reconcile {name} must be boolean")
    binding = receipt.get("edge_source_binding")
    expected_binding = {"cache_kind", "gid", "soltx_edges_sha256",
                        "soltx_meta_sha256", "edge_logical_sha256"}
    if not isinstance(binding, dict) or set(binding) != expected_binding \
            or binding.get("cache_kind") not in {"base", "repaired"}:
        reasons.append("edge_source_binding shape invalid")
    inputs = receipt.get("inputs")
    required = {"soltx_edges", "soltx_meta", "holders_owners",
                "holders_snapshot_meta", "coverage_map",
                "coverage_slot_counts", "coverage_pointer"}
    optional = {"coverage_resolution", "repair_bundle", "repair_pointer"}
    if not isinstance(inputs, dict):
        reasons.append("reconcile inputs missing")
    else:
        kind = binding.get("cache_kind") if isinstance(binding, dict) else None
        expected = required if kind == "base" else required | optional
        if set(inputs) != expected:
            reasons.append(f"reconcile conditional input key set mismatch: expected {sorted(expected)}")
        if any(inputs.get(name) is None for name in inputs):
            reasons.append("reconcile inputs may not contain null references")
    if case_root is not None and receipt_path is not None:
        root = Path(case_root).resolve()
        path = Path(receipt_path).resolve()
        if path != root and root not in path.parents:
            reasons.append("reconcile receipt path escapes case root")
    return {"ok": not reasons, "reasons": reasons}


def validate_reconcile_receipt_deep(receipt_path, *, case_root):
    """Independently replay and validate one ``solana-reconcile/v4`` receipt."""
    reasons = []
    root = Path(case_root).resolve()
    receipt_path = Path(receipt_path).resolve()
    if receipt_path != root and root not in receipt_path.parents:
        return {"ok": False, "reasons": ["reconcile receipt escapes case root"]}
    receipt = _load_json_object(receipt_path, "reconcile receipt", reasons)
    shallow = validate_reconcile_v4(
        receipt, case_root=root, receipt_path=receipt_path)
    reasons.extend(shallow["reasons"])
    inputs = receipt.get("inputs") if isinstance(receipt.get("inputs"), dict) else {}
    paths = {name: _check_file_ref(root, ref, f"reconcile input {name}", reasons)
             for name, ref in inputs.items()}

    expected_pointer = root / "data/sqd_coverage/CURRENT.json"
    if paths.get("coverage_pointer") != expected_pointer.resolve():
        reasons.append("coverage pointer is not data/sqd_coverage/CURRENT.json")
    edge_path = paths.get("soltx_edges")
    meta_path = paths.get("soltx_meta")
    owners_path = paths.get("holders_owners")
    snapshot_path = paths.get("holders_snapshot_meta")
    coverage_path = paths.get("coverage_map")
    pointer_path = paths.get("coverage_pointer")

    meta = _load_json_object(meta_path, "soltx meta", reasons) if meta_path else {}
    owners = _load_json_object(owners_path, "holders owners", reasons) if owners_path else {}
    snapshot = _load_json_object(
        snapshot_path, "holders snapshot meta", reasons) if snapshot_path else {}
    pointer = _load_json_object(pointer_path, "coverage pointer", reasons) \
        if pointer_path else {}
    coverage = _load_json_object(coverage_path, "coverage map", reasons) \
        if coverage_path else {}

    mint = receipt.get("target", {}).get("token")
    frm, upper = meta.get("from_slot"), meta.get("finalized_upper_slot")
    if meta.get("schema") != "sqd-solana-cache/v4" or meta.get("mint") != mint \
            or not _integer(frm) or not _integer(upper) or frm > upper:
        reasons.append("soltx meta identity/window invalid")
    if receipt.get("chain") != "solana" or receipt.get("mint") != mint:
        reasons.append("inherited reconcile chain/mint differs from target")
    if receipt.get("collection_window") != {"from_slot": frm, "to_slot": upper}:
        reasons.append("reconcile collection_window differs from soltx meta")

    edge_rows = _edge_rows(edge_path, reasons, "reconcile edges") if edge_path else []
    balances = {}
    minted = burned = 0
    for _ts, _slot_value, _tx, _instr, source, target, amount in edge_rows:
        if source == "0x" + "0" * 40:
            minted += amount
        else:
            balances[source] = balances.get(source, 0) - amount
        if target == "0x" + "0" * 40:
            burned += amount
        else:
            balances[target] = balances.get(target, 0) + amount
    replay_positive = {owner: amount for owner, amount in balances.items() if amount > 0}
    negatives = {owner: amount for owner, amount in balances.items() if amount < 0}
    digest, count = _edge_evidence(edge_rows)
    if edge_rows:
        extrema = {"first": {"slot": edge_rows[0][1], "ts": edge_rows[0][0]},
                   "last": {"slot": edge_rows[-1][1], "ts": edge_rows[-1][0]}}
        if receipt.get("edge_extrema") != extrema:
            reasons.append("reconcile edge extrema mismatch")
    if receipt.get("edge_digest") != digest or receipt.get("edge_count") != count:
        reasons.append("reconcile edge digest/count mismatch")
    if meta.get("edge_logical_sha256") != digest or meta.get("edge_rows") != count:
        reasons.append("soltx meta logical digest/count mismatch")
    for name, actual in (("minted_raw", minted), ("burned_raw", burned),
                         ("net_supply_raw", minted - burned),
                         ("negative_balance_count", len(negatives))):
        if receipt.get(name) != actual:
            reasons.append(f"reconcile {name} does not recompute")

    owner_values_ok = isinstance(owners, dict) and all(
        isinstance(owner, str) and owner and _integer(amount) and amount >= 0
        for owner, amount in owners.items())
    if not owner_values_ok:
        reasons.append("holders owners balances must be nonnegative JSON ints")
    mismatches = [owner for owner in sorted(set(owners) | set(replay_positive))
                  if owners.get(owner, 0) != replay_positive.get(owner, 0)] \
        if owner_values_ok else []
    snapshot_supply = sum(owners.values()) if owner_values_ok else 0
    snapshot_target = snapshot.get("target") if isinstance(snapshot.get("target"), dict) else {}
    try:
        declared_supply = int(snapshot.get("supply_raw"))
    except (TypeError, ValueError):
        declared_supply = None
        reasons.append("holders snapshot supply_raw is not an integer")
    output_path = _snapshot_output_path(
        root, snapshot_path, (snapshot.get("outputs") or {}).get("holders_owners"),
        reasons) if snapshot_path else None
    snapshot_closed = (
        snapshot.get("schema") == "solana-holder-snapshot-v2"
        and snapshot.get("mint") == mint
        and snapshot_target == receipt.get("target")
        and snapshot.get("closed") is True
        and declared_supply == snapshot_supply
        and output_path == owners_path)
    if receipt.get("snapshot_supply_raw") != snapshot_supply:
        reasons.append("reconcile snapshot_supply_raw does not recompute")
    if receipt.get("snapshot_mismatch_count") != len(mismatches):
        reasons.append("reconcile snapshot_mismatch_count does not recompute")
    if receipt.get("snapshot_present") is not True \
            or receipt.get("snapshot_meta_present") is not True \
            or receipt.get("snapshot_closed") is not snapshot_closed:
        reasons.append("reconcile snapshot presence/closure facts mismatch")
    if not _integer(upper) or receipt.get("target", {}).get("as_of_block") != upper:
        reasons.append("as_of_slot must equal snapshot slot and finalized_upper_slot")

    coverage_check = None
    if coverage_path and pointer_path and _integer(frm) and _integer(upper):
        coverage_check = validate_coverage(root, coverage_path, pointer_path, frm, upper)
        reasons.extend(f"reconcile coverage: {reason}"
                       for reason in coverage_check["reasons"])
    cache_endpoint = meta.get("endpoint_sha256")
    coverage_endpoint = (coverage.get("sqd") or {}).get("endpoint_fingerprint") \
        if isinstance(coverage.get("sqd"), dict) else None
    if cache_endpoint is not None and cache_endpoint != coverage_endpoint:
        reasons.append("coverage SQD endpoint fingerprint differs from soltx meta")
    pointer_map = (pointer.get("inputs") or {}).get("coverage_map") or {}
    if pointer_map.get("path") != (inputs.get("coverage_map") or {}).get("path"):
        reasons.append("coverage pointer map path differs from receipt")
    if pointer.get("probe_id") != coverage.get("probe_id"):
        reasons.append("coverage pointer/map probe_id mismatch")
    if paths.get("coverage_slot_counts") is not None:
        expected_counts = ((pointer.get("inputs") or {}).get("slot_counts") or {})
        if expected_counts != inputs.get("coverage_slot_counts"):
            reasons.append("coverage slot_counts receipt/pointer reference mismatch")

    binding = receipt.get("edge_source_binding") or {}
    actual_binding = {
        "cache_kind": binding.get("cache_kind"), "gid": binding.get("gid"),
        "soltx_edges_sha256": sha256_file(edge_path) if edge_path else None,
        "soltx_meta_sha256": sha256_file(meta_path) if meta_path else None,
        "edge_logical_sha256": digest,
    }
    if binding != actual_binding:
        reasons.append("edge_source_binding does not equal bound edge/meta facts")

    coverage_verdict = (coverage_check or {}).get("recomputed", {}).get("verdict")
    combination_ok = False
    if binding.get("cache_kind") == "base":
        if binding.get("gid") is not None:
            reasons.append("base binding gid must be null")
        combination_ok = coverage_verdict == "NO_KNOWN_NONCE_OMISSION_DETECTED"
        effective = coverage_verdict
    else:
        effective = None
        bundle_path = paths.get("repair_bundle")
        resolution = _load_json_object(
            paths.get("coverage_resolution"), "coverage resolution", reasons) \
            if paths.get("coverage_resolution") else {}
        bundle = _load_json_object(
            bundle_path, "repair bundle", reasons) if bundle_path else {}
        base_edge = root / "data" / (
            f"soltx-{sha256_bytes(str(mint).encode('utf-8'))}.jsonl.gz")
        current_base = {"edge_sha256": sha256_file(base_edge)} \
            if base_edge.is_file() else {"edge_sha256": None}
        bundle_result = validate_repair_bundle_deep(
            bundle_path, case_root=root, current_base=current_base) \
            if bundle_path else {"ok": False, "reasons": ["repair bundle missing"]}
        reasons.extend(f"reconcile repair: {reason}" for reason in bundle_result["reasons"])
        effective = bundle_result.get("effective_verdict")
        current_candidates = set((coverage_check or {}).get(
            "recomputed", {}).get("candidate_slots", []))
        census_slots = {row.get("slot") for row in resolution.get("census", [])
                        if isinstance(row, dict)}
        combination_ok = (bundle_result.get("ok") is True
                          and effective == "DEFECTS_CONFIRMED"
                          and current_candidates.issubset(census_slots)
                          and binding.get("gid") == bundle.get("gid"))
        repair_pointer = _load_json_object(
            paths.get("repair_pointer"), "repair pointer", reasons) \
            if paths.get("repair_pointer") else {}
        if repair_pointer.get("gid") != binding.get("gid"):
            reasons.append("repair pointer gid differs from edge binding")
    if receipt.get("coverage_effective_verdict") != effective:
        reasons.append("coverage_effective_verdict does not recompute")

    gate_expected = bool(
        not negatives and snapshot_closed and snapshot_supply == minted - burned
        and not mismatches and combination_ok)
    if receipt.get("gate_pass") is not gate_expected:
        reasons.append("gate_pass does not recompute from exact reconciliation")
    if not validate_verdict_gate_triad(
            receipt.get("verdict"), receipt.get("exit_code"), gate_expected):
        reasons.append("verdict/exit_code do not match recomputed gate_pass")
    producer = receipt.get("producer") or {}
    producer_path = Path(__file__).resolve().parents[2] / "scripts/solana/replay_edges.py"
    if producer != {"path": "scripts/solana/replay_edges.py",
                    "sha256": sha256_file(producer_path)}:
        reasons.append("reconcile producer is not current replay_edges.py")
    return {"ok": not reasons, "reasons": reasons, "receipt": receipt,
            "gate_pass": gate_expected, "edge_source_binding": actual_binding,
            "coverage_effective_verdict": effective,
            "holders_owners_path": owners_path}
