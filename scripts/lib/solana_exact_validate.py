#!/usr/bin/env python3
"""Independent Solana exact validators.

Coverage segment (batch 2): implemented below.  It validates
``sqd-solana-coverage/v1`` and ``sqd-solana-coverage-pointer/v1`` from disk.

Repair segment (batch 3): intentionally not implemented in this batch.

Reconcile segment (batch 5): intentionally not implemented in this batch.

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
