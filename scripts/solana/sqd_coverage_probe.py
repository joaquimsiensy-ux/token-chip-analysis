#!/usr/bin/env python3
"""Probe Solana SQD AdvanceNonce coverage and publish immutable evidence.

Produces ``sqd-solana-coverage/v1`` plus the kernel pointer
``sqd-solana-coverage-pointer/v1``.  Network requests go through ``net.py``;
``--transport-fixture`` replaces transport only and preserves production
artifact semantics for deterministic offline vertical-slice tests.
"""
from __future__ import annotations

import argparse
import fcntl
import gzip
import json
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

LIB = Path(__file__).resolve().parents[1] / "lib"
sys.path.insert(0, str(LIB))

import net  # noqa: E402
from endpoint_identity import endpoint_fingerprint, redact_endpoint_text  # noqa: E402
from receipt_kernel import publish_exclusive, publish_overwrite  # noqa: E402
from solana_exact_validate import (  # noqa: E402
    BITMAP_ENCODING, COUNT_ENCODING, ERA_PARAMS, canonical_json,
    classify_four_states, compute_probe_id,
    derive_getblocks_complete, encode_bitmap, merge_ranges, ranges_cover,
    sha256_bytes, sha256_file, validate_blocks_bitmap, validate_coverage,
    validate_coverage_map, validate_shared_map, validate_slot_counts,
)


COVERAGE_SCHEMA = "sqd-solana-coverage/v1"
COVERAGE_POINTER_SCHEMA = "sqd-solana-coverage-pointer/v1"
PRODUCED_SCHEMAS = (COVERAGE_SCHEMA, COVERAGE_POINTER_SCHEMA)
SYSTEM_PROGRAM = "11111111111111111111111111111111"
SQD_DATASET = "solana-mainnet"
DEFAULT_SQD = "https://portal.sqd.dev/datasets/solana-mainnet"
SQD_PAGE_SLOTS = 450
GETBLOCKS_PAGE_SLOTS = 500_000
PROGRESS_EVERY = 500
QUOTA_STATUSES = (402, 429)
KEY_FILE = Path.home() / ".config/helius/api-key"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def _sha_ref(path, rel):
    path = Path(path)
    return {"path": rel, "size": path.stat().st_size, "sha256": sha256_file(path)}


def _safe_text(value, endpoints):
    return redact_endpoint_text(value, endpoints)


def request_digest(kind, body):
    return sha256_bytes(canonical_json({"kind": kind, "body": body}))


class FixtureTransport:
    """Digest-addressed offline request/response transport."""
    def __init__(self, directory):
        self.directory = Path(directory)
        path = self.directory / "responses.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("format") != "sqd-coverage-transport-fixture-v1":
            raise ValueError("fixture transport schema mismatch")
        self.responses = payload.get("responses") or {}
        self.calls = []

    def call(self, kind, body):
        digest = request_digest(kind, body)
        self.calls.append({"kind": kind, "digest": digest})
        item = self.responses.get(digest)
        if not isinstance(item, dict):
            return net.Result(ok=False, error={
                "category": "fixture", "message": f"missing fixture {digest}",
                "http_status": None, "retryable": False})
        if item.get("ok") is True:
            return net.Result(ok=True, value=item.get("value"))
        return net.Result(ok=False, error={
            "category": item.get("category", "fixture"),
            "message": str(item.get("message", "fixture failure")),
            "http_status": item.get("http_status"),
            "retryable": bool(item.get("retryable", False)),
        })


class LiveTransport:
    def __init__(self, sqd_endpoint, rpc_endpoint):
        self.sqd_endpoint = sqd_endpoint.rstrip("/")
        self.rpc_endpoint = rpc_endpoint

    def call(self, kind, body):
        if kind == "sqd-head":
            return net.curl_json(f"{self.sqd_endpoint}/head")
        if kind == "sqd-stream":
            return net.curl_json(f"{self.sqd_endpoint}/stream", post_json=body)
        if kind in {"rpc-getSlot", "rpc-getBlocks"}:
            return net.curl_json(self.rpc_endpoint, post_json=body,
                                 no_retry_statuses=QUOTA_STATUSES)
        raise ValueError(f"unknown transport kind {kind}")


def sqd_query_body(from_slot, to_slot):
    return {
        "type": "solana", "fromBlock": int(from_slot), "toBlock": int(to_slot),
        "includeAllBlocks": True,
        "fields": {"block": {"number": True},
                   "instruction": {"transactionIndex": True}},
        "instructions": [{"programId": [SYSTEM_PROGRAM],
                          "d4": ["0x04000000"]}],
    }


def sqd_query_template_sha256():
    return sha256_bytes(canonical_json(sqd_query_body(0, 0)))


def rpc_body(method, params, request_id):
    return {"jsonrpc": "2.0", "id": int(request_id),
            "method": method, "params": params}


def _decoded_size(value):
    return len(canonical_json(value))


def _result_http_status(result):
    if result.ok:
        return 200
    error = result.error if isinstance(result.error, dict) else {}
    return error.get("http_status")


def _result_error(result, endpoints):
    error = result.error if isinstance(result.error, dict) else {"message": result.error}
    return _safe_text(error.get("message", "request failed"), endpoints)


def _rpc_result(result):
    if not result.ok:
        return None, result.error
    value = result.value
    if isinstance(value, dict) and "error" in value:
        return None, value["error"]
    if isinstance(value, dict) and "result" in value:
        return value["result"], None
    return value, None


def _quota_error(result, rpc_error):
    status = _result_http_status(result)
    if status in QUOTA_STATUSES:
        return True
    if isinstance(rpc_error, dict):
        code = rpc_error.get("code")
        message = str(rpc_error.get("message", "")).lower()
        return code in QUOTA_STATUSES or any(
            needle in message for needle in (
                "quota", "credit", "payment required", "rate limit", "too many request"))
    return False


def _normalize_metadata(value):
    if isinstance(value, dict) and "result" in value:
        value = value["result"]
    if not isinstance(value, dict):
        value = {"number": value}
    number = value.get("number", value.get("height", value.get("finalized_head", 0)))
    if not isinstance(number, int) or isinstance(number, bool):
        raise ValueError("SQD head lacks integer number")
    normalized = {
        "dataset_id": str(value.get("dataset_id", SQD_DATASET)),
        "start_block": int(value.get("start_block", 0)),
        "real_time": bool(value.get("real_time", True)),
        "finalized_head": number,
    }
    for key in sorted(value):
        item = value[key]
        if key not in normalized and isinstance(item, (str, int, bool)) \
                and not isinstance(item, float):
            normalized[key] = item
    return normalized


def _partition(start, end, width):
    cursor = start
    while cursor <= end:
        stop = min(end, cursor + width - 1)
        yield cursor, stop
        cursor = stop + 1


def _missing_ranges(mask, base_slot):
    ranges = []
    start = None
    for offset, value in enumerate(mask):
        slot = base_slot + offset
        if value == 0 and start is None:
            start = slot
        elif value != 0 and start is not None:
            ranges.append((start, slot - 1))
            start = None
    if start is not None:
        ranges.append((start, base_slot + len(mask) - 1))
    return ranges


def _scan_request(transport, start, end, seq, endpoints, *, mode="full"):
    body = sqd_query_body(start, end)
    result = transport.call("sqd-stream", body)
    row = {
        "seq": seq, "ts": utc_now(), "provider": "SQD", "mode": mode,
        "counts_coverage": True, "query_body_sha256": sha256_bytes(canonical_json(body)),
        "from": start, "to": end, "http_status": _result_http_status(result),
        "returned_from": None, "returned_to": None, "n_blocks": 0,
        "slots_covered": 0, "empty_response": False, "bytes": 0,
        "response_sha256": None, "ok": False,
    }
    if not result.ok:
        row["error"] = _result_error(result, endpoints)
        return row, None
    value = result.value
    blocks = value if isinstance(value, list) else [value]
    raw = canonical_json(blocks)
    row.update(bytes=len(raw), response_sha256=sha256_bytes(raw))
    if not blocks:
        row.update(slots_covered=end - start + 1, empty_response=True, ok=True)
        return row, bytes([1]) * (end - start + 1)
    try:
        slots = []
        for block in blocks:
            if not isinstance(block, dict):
                raise ValueError("SQD block is not object")
            header = block.get("header") or {}
            slot = header.get("number")
            if not isinstance(slot, int) or isinstance(slot, bool) \
                    or slot < start or slot > end:
                raise ValueError(f"SQD block number invalid: {slot!r}")
            if slots and slot <= slots[-1]:
                raise ValueError(
                    f"SQD block numbers not strictly increasing: {slots[-1]}, {slot}")
            slots.append(slot)
        covered_to = slots[-1]
        counts = bytearray([1]) * (covered_to - start + 1)
        for block, slot in zip(blocks, slots):
            instructions = block.get("instructions") or []
            if not isinstance(instructions, list):
                raise ValueError("SQD instructions is not array")
            counts[slot - start] = min(255, 2 + len(instructions))
    except (TypeError, ValueError) as exc:
        row.update(ok=False, slots_covered=0,
                   error=_safe_text(exc, endpoints))
        return row, None
    row.update(returned_from=slots[0], returned_to=covered_to,
               n_blocks=len(slots), slots_covered=covered_to - start + 1,
               ok=True)
    return row, bytes(counts)


def _append_ledger(ledger, rows):
    for row in rows:
        row = dict(row)
        row["seq"] = len(ledger)
        ledger.append(row)


def _scan_partition(transport, start, end, endpoints, *, mode):
    """Follow SQD's response cursor within one independently scheduled shard."""
    pages = []
    cursor = start
    while cursor <= end:
        row, part = _scan_request(
            transport, cursor, end, 0, endpoints, mode=mode)
        pages.append((cursor, row, part))
        if part is None:
            break
        covered = row.get("slots_covered")
        if not isinstance(covered, int) or isinstance(covered, bool) or covered <= 0:
            row.update(ok=False, slots_covered=0,
                       error="SQD page made no cursor progress")
            pages[-1] = (cursor, row, None)
            break
        cursor += covered
    return pages


def _successful_coverage_range(row):
    covered = row.get("slots_covered")
    start = row.get("from")
    if row.get("ok") is not True or row.get("counts_coverage") is not True \
            or not isinstance(start, int) or isinstance(start, bool) \
            or not isinstance(covered, int) or isinstance(covered, bool) \
            or covered <= 0:
        return None
    return start, start + covered - 1


def _scan_ranges(transport, counts, base_slot, ranges, workers, ledger,
                 endpoints, *, mode="full", checkpoint=None,
                 checkpoint_every=0):
    lower_bound = sum((upper - lower + SQD_PAGE_SLOTS) // SQD_PAGE_SLOTS
                      for lower, upper in ranges)
    request_iter = ((start, end) for lower, upper in ranges
                    for start, end in _partition(lower, upper, SQD_PAGE_SLOTS))
    completed_count = 0
    completed_since_checkpoint = 0
    batch_size = max(workers, workers * 4)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        while True:
            batch = []
            for _ in range(batch_size):
                try:
                    batch.append(next(request_iter))
                except StopIteration:
                    break
            if not batch:
                break
            futures = {pool.submit(_scan_partition, transport, start, end,
                                   endpoints, mode=mode): (start, end)
                       for start, end in batch}
            completed = []
            for future in as_completed(futures):
                start, end = futures[future]
                try:
                    pages = future.result()
                except Exception as exc:
                    row = {
                        "seq": 0, "ts": utc_now(), "provider": "SQD", "mode": mode,
                        "counts_coverage": True,
                        "query_body_sha256": sha256_bytes(canonical_json(
                        sqd_query_body(start, end))),
                        "from": start, "to": end, "http_status": None, "bytes": 0,
                        "returned_from": None, "returned_to": None, "n_blocks": 0,
                        "empty_response": False, "response_sha256": None,
                        "slots_covered": 0, "ok": False,
                        "error": _safe_text(exc, endpoints),
                    }
                    pages = [(start, row, None)]
                completed.append((start, pages))
            for _shard_start, pages in sorted(completed):
                for page_start, row, part in pages:
                    _append_ledger(ledger, [row])
                    if part is not None:
                        offset = page_start - base_slot
                        counts[offset:offset + len(part)] = part
                    completed_count += 1
                    completed_since_checkpoint += 1
                    if completed_count % PROGRESS_EVERY == 0:
                        print(
                            f"[sqd-coverage] completed {completed_count} requests "
                            f"(lower bound {lower_bound})", file=sys.stderr)
            if checkpoint is not None and checkpoint_every > 0 \
                    and completed_since_checkpoint >= checkpoint_every:
                checkpoint()
                print(_safe_text(
                    f"[sqd-coverage] checkpoint written "
                    f"(completed {completed_count} requests)", endpoints),
                    file=sys.stderr)
                completed_since_checkpoint = 0


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _parse_time(value):
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _load_known_map(path, mint_from, mint_to, sqd_identity, metadata,
                    transport, ledger, endpoints):
    """Validate and recheck a shared map; return reusable counts or fallback."""
    asset_path = Path(path).resolve()
    info = {"asset_path": str(asset_path), "version": None, "sha256": None,
            "supersedes": None, "generated_at": None, "reused_ranges": [],
            "canary": {"slots": [], "counts_sha256": sha256_bytes(b""),
                       "verified_at": utc_now()}}
    try:
        shared_checked = validate_shared_map(asset_path)
        if not shared_checked["ok"]:
            raise ValueError("shared-map-invalid:" + ";".join(
                shared_checked["reasons"]))
        asset = _read_json(asset_path)
        if asset.get("schema") != "sqd-solana-shared-coverage-map/v1":
            raise ValueError("shared-map-schema-invalid")
        if asset.get("ttl_days") != 30:
            raise ValueError("ttl-days-must-be-30")
        if "supersedes" not in asset:
            raise ValueError("supersedes-missing")
        info.update(version=asset.get("version"), sha256=sha256_file(asset_path),
                    supersedes=asset.get("supersedes"),
                    generated_at=asset.get("generated_at"))
        expires = _parse_time(asset["generated_at"]) + timedelta(
            days=int(asset.get("ttl_days", 30)))
        if datetime.now(timezone.utc) > expires:
            raise ValueError("ttl-expired")
        if asset.get("sqd", {}).get("endpoint_fingerprint") != sqd_identity:
            raise ValueError("endpoint-fingerprint-changed")
        if asset.get("sqd", {}).get("metadata_normalized") != metadata:
            raise ValueError("metadata-changed")
        slot_meta = asset["slot_counts"]
        if slot_meta.get("encoding") != COUNT_ENCODING:
            raise ValueError("counts-encoding-mismatch")
        counts_path = (asset_path.parent / slot_meta["path"]).resolve()
        if counts_path.stat().st_size != slot_meta.get("size"):
            raise ValueError("counts-size-mismatch")
        if sha256_file(counts_path) != slot_meta["sha256"]:
            raise ValueError("counts-sha256-mismatch")
        asset_counts = gzip.decompress(counts_path.read_bytes())
        afrom, ato = int(slot_meta["from_slot"]), int(slot_meta["to_slot"])
        if len(asset_counts) != ato - afrom + 1:
            raise ValueError("counts-length-mismatch")
        blocks_meta = asset["blocks_bitmap"]
        if blocks_meta.get("encoding") != BITMAP_ENCODING:
            raise ValueError("blocks-encoding-mismatch")
        blocks_path = (asset_path.parent / blocks_meta["path"]).resolve()
        if blocks_path.stat().st_size != blocks_meta.get("size"):
            raise ValueError("blocks-size-mismatch")
        if (blocks_meta.get("from_slot"), blocks_meta.get("to_slot")) != (afrom, ato):
            raise ValueError("blocks-interval-mismatch")
        if sha256_file(blocks_path) != blocks_meta["sha256"]:
            raise ValueError("blocks-sha256-mismatch")
        blocks_raw = gzip.decompress(blocks_path.read_bytes())
        bitmap_check = validate_blocks_bitmap(blocks_raw, afrom, ato)
        if not bitmap_check["ok"]:
            raise ValueError("blocks-bitmap-invalid")
        canary = asset.get("canary") or {}
        slots = canary.get("slots")
        expected_counts = canary.get("counts")
        if not isinstance(slots, list) or len(slots) != 64 \
                or not isinstance(expected_counts, list) or len(expected_counts) != 64:
            raise ValueError("canary-shape-invalid")
        recheck = sorted(set(slots + asset.get("candidate_slots", [])
                             + asset.get("refuted_slots", [])))
        actual = {}
        for slot in recheck:
            row, part = _scan_request(transport, slot, slot, 0, endpoints,
                                      mode="recheck")
            _append_ledger(ledger, [row])
            if part is None or part[0] != asset_counts[slot - afrom]:
                raise ValueError(f"recheck-mismatch:{slot}")
            actual[slot] = part[0]
        actual_canary = [actual[slot] for slot in slots]
        if actual_canary != expected_counts:
            raise ValueError("canary-counts-changed")
        info["canary"] = {
            "slots": slots,
            "counts_sha256": sha256_bytes(canonical_json(actual_canary)),
            "verified_at": utc_now(),
        }
        overlap_from, overlap_to = max(mint_from, afrom), min(mint_to, ato)
        if overlap_from > overlap_to:
            raise ValueError("map-does-not-overlap-case")
        info["reused_ranges"] = [{"from_slot": overlap_from,
                                  "to_slot": overlap_to}]
        return info, asset_counts[overlap_from - afrom:overlap_to - afrom + 1], \
            overlap_from, overlap_to
    except Exception as exc:
        info["fallback_reason"] = _safe_text(exc, endpoints)
        return info, None, None, None


def _shared_canary(probe_id, counts, from_slot):
    headers = [from_slot + offset for offset, value in enumerate(counts)
               if value >= 2]
    if len(headers) < 64:
        raise ValueError("shared map requires at least 64 slots with block headers")
    seed = int(sha256_bytes(probe_id.encode("utf-8")), 16)
    selected = {headers[(seed + (index * len(headers)) // 64) % len(headers)]
                for index in range(64)}
    if len(selected) != 64:
        # Full-history maps are much wider than 64; this only handles tiny fixtures.
        cursor = seed % len(headers)
        while len(selected) < 64:
            selected.add(headers[cursor % len(headers)])
            cursor += 1
    slots = sorted(selected)
    return slots, [counts[slot - from_slot] for slot in slots]


def export_shared_map(args):
    """Export a published case probe as one deterministic shared-map triplet."""
    case_root = Path(args.case_root).resolve()
    parent = case_root / "data/sqd_coverage"
    pointer_path = parent / "CURRENT.json"
    pointer = _read_json(pointer_path)
    if pointer.get("probe_id") != args.probe_id:
        raise ValueError("probe-id is not the currently published probe")
    generation = parent / args.probe_id
    coverage_path = generation / "coverage_map.json"
    coverage = _read_json(coverage_path)
    if coverage.get("probe_id") != args.probe_id:
        raise ValueError("coverage map probe_id mismatch")
    slot_meta = coverage.get("slot_counts", {})
    checked = validate_coverage(
        case_root, coverage_path, pointer_path,
        slot_meta.get("from_slot"), slot_meta.get("to_slot"))
    if not checked["ok"]:
        raise ValueError("published probe validation failed: "
                         + "; ".join(checked["reasons"]))
    if coverage.get("skipped_confirmation") is None:
        raise ValueError("shared map export requires getBlocks evidence")
    counts_source = generation / "slot_counts.bin.gz"
    blocks_source = generation / "blocks.bin.gz"
    counts = gzip.decompress(counts_source.read_bytes())
    version = args.version or datetime.now(timezone.utc).strftime("%Y%m%d")
    if not isinstance(version, str) or len(version) != 8 or not version.isdigit():
        raise ValueError("shared map version must be YYYYMMDD")
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    prior = sorted(path.stem for path in out.glob("[0-9]" * 8 + ".json")
                   if path.stem != version)
    supersedes = prior[-1] if prior else None
    counts_name = f"{version}.counts.bin.gz"
    blocks_name = f"{version}.blocks.bin.gz"
    _publish_bytes_overwrite(out / counts_name, counts_source.read_bytes())
    _publish_bytes_overwrite(out / blocks_name, blocks_source.read_bytes())
    slots, canary_counts = _shared_canary(
        args.probe_id, counts, slot_meta["from_slot"])
    counts_ref = _sha_ref(out / counts_name, counts_name)
    blocks_ref = _sha_ref(out / blocks_name, blocks_name)
    bitmap_meta = coverage["skipped_confirmation"]["blocks_bitmap"]
    asset = {
        "schema": "sqd-solana-shared-coverage-map/v1", "version": version,
        "generated_at": pointer["published_at"], "ttl_days": 30,
        "supersedes": supersedes, "sqd": coverage["sqd"],
        "slot_counts": {**counts_ref, "from_slot": slot_meta["from_slot"],
                        "to_slot": slot_meta["to_slot"],
                        "encoding": COUNT_ENCODING},
        "blocks_bitmap": {**blocks_ref,
                          "from_slot": bitmap_meta["from_slot"],
                          "to_slot": bitmap_meta["to_slot"],
                          "encoding": BITMAP_ENCODING},
        "candidate_slots": checked["recomputed"]["candidate_slots"],
        "refuted_slots": [],
        "canary": {"slots": slots, "counts": canary_counts},
    }
    asset_path = out / f"{version}.json"
    _publish_bytes_overwrite(asset_path, canonical_json(asset) + b"\n")
    asset_checked = validate_shared_map(asset_path)
    if not asset_checked["ok"]:
        raise ValueError("exported shared map failed validation: "
                         + "; ".join(asset_checked["reasons"]))
    print(json.dumps({"status": "exported", "version": version,
                      "asset": str(asset_path)}, sort_keys=True))
    return 0


def _get_reference_rpc(args):
    if args.transport_fixture:
        return "fixture://helius"
    if args.reference_rpc:
        return args.reference_rpc
    try:
        key = KEY_FILE.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ValueError(f"Helius key file unavailable: {KEY_FILE}") from exc
    if not key:
        raise ValueError(f"Helius key file empty: {KEY_FILE}")
    return f"https://mainnet.helius-rpc.com/?api-key={key}"


def _confirm_getblocks(transport, from_slot, to_slot, rpc_endpoint, ledger,
                       endpoints):
    head_body = rpc_body("getSlot", [{"commitment": "finalized"}], 1)
    head_result = transport.call("rpc-getSlot", head_body)
    head, head_error = _rpc_result(head_result)
    head_raw = canonical_json(head if head_error is None else {
        "error": _safe_text(head_error or _result_error(head_result, endpoints), endpoints)})
    head_row = {
        "seq": len(ledger), "ts": utc_now(), "provider": "reference-rpc",
        "mode": "getSlot", "counts_coverage": False,
        "query_body_sha256": sha256_bytes(canonical_json(head_body)),
        "from": from_slot, "to": from_slot,
        "http_status": _result_http_status(head_result), "bytes": len(head_raw),
        "response_sha256": sha256_bytes(head_raw), "slots_covered": 0,
        "ok": bool(head_result.ok and head_error is None and isinstance(head, int)
                   and not isinstance(head, bool)),
    }
    if not head_row["ok"]:
        head_row["error"] = _safe_text(
            head_error or _result_error(head_result, endpoints), endpoints)
    _append_ledger(ledger, [head_row])
    if _quota_error(head_result, head_error):
        return None, None, {"reason": "reference-quota", "cursor": from_slot}
    if not isinstance(head, int) or isinstance(head, bool):
        head = -1
    listed = []
    ranges = []
    for index, (start, end) in enumerate(
            _partition(from_slot, to_slot, GETBLOCKS_PAGE_SLOTS), 2):
        body = rpc_body("getBlocks", [start, end, {"commitment": "finalized"}], index)
        result = transport.call("rpc-getBlocks", body)
        value, rpc_error = _rpc_result(result)
        if _quota_error(result, rpc_error):
            return None, None, {"reason": "reference-quota", "cursor": start}
        response_ok = result.ok and rpc_error is None and isinstance(value, list)
        array_monotonic = response_ok and all(
            isinstance(slot, int) and not isinstance(slot, bool)
            for slot in value) and all(a < b for a, b in zip(value, value[1:]))
        array_in_range = response_ok and all(start <= slot <= end for slot in value)
        if response_ok:
            listed.extend(value)
        raw = canonical_json(value if response_ok else {
            "error": _safe_text(rpc_error or _result_error(result, endpoints), endpoints)})
        row = {
            "seq": len(ledger), "ts": utc_now(), "provider": "reference-rpc",
            "mode": "getBlocks", "counts_coverage": False,
            "query_body_sha256": sha256_bytes(canonical_json(body)),
            "from": start, "to": end, "http_status": _result_http_status(result),
            "bytes": len(raw), "response_sha256": sha256_bytes(raw),
            "slots_covered": 0, "ok": bool(response_ok),
        }
        if not response_ok:
            row["error"] = _safe_text(rpc_error or _result_error(result, endpoints),
                                       endpoints)
        _append_ledger(ledger, [row])
        ranges.append({
            "from": start, "to": end, "response_sha256": sha256_bytes(raw),
            "count": len(value) if response_ok else 0,
            "response_ok": bool(response_ok and array_monotonic and array_in_range),
            "array_monotonic_unique": bool(array_monotonic),
            "array_in_range": bool(array_in_range),
        })
    try:
        bitmap = encode_bitmap(listed, from_slot, to_slot)
    except ValueError:
        bitmap = bytes((to_slot - from_slot + 8) // 8)
    confirmation = {
        "method": "getBlocks", "commitment": "finalized",
        "reference_head_at_check": head,
        "endpoint_fingerprint": endpoint_fingerprint(rpc_endpoint)["sha256"],
        "blocks_bitmap": {"path": "blocks.bin.gz", "size": None,
                          "sha256": None, "from_slot": from_slot,
                          "to_slot": to_slot, "encoding": BITMAP_ENCODING},
        "ranges": ranges,
    }
    return confirmation, bitmap, None


def _gzip_bytes(raw):
    return gzip.compress(bytes(raw), mtime=0)


def _publish_bytes_overwrite(path, payload):
    """Atomically replace a binary/text file using same-directory staging."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.tmp.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
    return path


def _fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _ledger_bytes(rows):
    return b"".join(canonical_json(row) + b"\n" for row in rows)


def _remove_one(path):
    try:
        Path(path).unlink()
    except FileNotFoundError:
        pass


def _same_generation(left, right):
    names = ("coverage_map.json", "slot_counts.bin.gz", "blocks.bin.gz",
             "ledger.jsonl")
    for name in names:
        lpath, rpath = left / name, right / name
        if lpath.exists() != rpath.exists():
            return False
        if lpath.exists() and sha256_file(lpath) != sha256_file(rpath):
            return False
    return True


def _clear_pending(pending):
    for name in ("coverage_map.json", "slot_counts.bin.gz", "blocks.bin.gz",
                 "ledger.jsonl", "resume_state.json", "STOPPED.json"):
        _remove_one(pending / name)
    try:
        pending.rmdir()
    except OSError:
        pass


def publish_probe_generation(case_root, pending, probe_id, pointer,
                             *, observed_current, prepublish_validate=None):
    """Durably publish one immutable generation and lock/CAS its pointer."""
    case_root, pending = Path(case_root).resolve(), Path(pending).resolve()
    parent = case_root / "data/sqd_coverage"
    final = parent / probe_id
    current_path = parent / "CURRENT.json"
    _remove_one(pending / "resume_state.json")
    _remove_one(pending / "STOPPED.json")
    _fsync_dir(pending)
    if final.exists():
        if not final.is_dir() or not _same_generation(pending, final):
            raise RuntimeError(f"probe generation collision: {probe_id}")
        _clear_pending(pending)
    else:
        os.rename(pending, final)
    _fsync_dir(parent)
    if prepublish_validate is not None:
        prepublish_validate(final)
    lock_path = parent / ".lock"
    lock_path.touch(exist_ok=True)
    with lock_path.open("r+b") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        try:
            current = _read_json(current_path) if current_path.is_file() else None
            final_hash = sha256_file(final / "coverage_map.json")
            if (isinstance(current, dict) and current.get("probe_id") == probe_id
                    and current.get("inputs", {}).get("coverage_map", {}).get(
                        "sha256") == final_hash):
                _fsync_dir(parent)
                return "idempotent-republish"
            current_id = current.get("probe_id") if isinstance(current, dict) else None
            observed_id = (observed_current.get("probe_id")
                           if isinstance(observed_current, dict) else None)
            if pointer.get("supersedes") != current_id or current_id != observed_id:
                raise RuntimeError(
                    f"coverage pointer CAS failed: expected {pointer.get('supersedes')!r}, "
                    f"current {current_id!r}")
            publish_overwrite(current_path, pointer)
            _fsync_dir(parent)
            return "published"
        finally:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)


def _pending_state(parent, args, sqd_identity):
    if not args.resume:
        return None, None
    matches = []
    for pending in sorted(parent.glob("pending-*")):
        state_path = pending / "resume_state.json"
        if not state_path.is_file():
            continue
        try:
            state = _read_json(state_path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        identity = state.get("identity")
        expected = {"mint": args.mint, "from_slot": args.from_slot,
                    "to_slot": args.to_slot, "sqd_fingerprint": sqd_identity,
                    "plan": _plan_identity(args)}
        if identity == expected:
            matches.append((pending, state))
    if len(matches) > 1:
        raise ValueError("multiple resumable coverage pending directories match plan")
    return matches[0] if matches else (None, None)


def _write_resume(pending, identity, started_at, counts, ledger, stopped=None):
    _publish_bytes_overwrite(pending / "slot_counts.bin.gz", _gzip_bytes(counts))
    _publish_bytes_overwrite(pending / "ledger.jsonl", _ledger_bytes(ledger))
    publish_overwrite(pending / "resume_state.json", {
        "format": "sqd-coverage-resume-v1", "identity": identity,
        "started_at": started_at,
    })
    if stopped is not None:
        publish_overwrite(pending / "STOPPED.json", stopped)
    _fsync_dir(pending)


def _plan_identity(args):
    known_sha = None
    if args.known_map:
        try:
            known_sha = sha256_file(args.known_map)
        except OSError:
            known_sha = "unreadable"
    return {"mode": "full" if args.full else "known-map",
            "known_map_sha256": known_sha,
            "getblocks": not args.no_getblocks}


def _dry_run(args):
    slots = args.to_slot - args.from_slot + 1
    request_lower_bound = (slots + SQD_PAGE_SLOTS - 1) // SQD_PAGE_SLOTS
    map_plan = {"mode": "full",
                "request_lower_bound": request_lower_bound,
                "estimate_uncertain": True}
    reusable_lower_bound = request_lower_bound
    if args.known_map:
        map_plan = {"mode": "known-map", "asset": str(args.known_map),
                    "readable": False, "optimistic_reused_slots": 0,
                    "request_lower_bound": request_lower_bound,
                    "estimate_uncertain": True}
        try:
            asset = _read_json(args.known_map)
            lower = max(args.from_slot, int(asset["slot_counts"]["from_slot"]))
            upper = min(args.to_slot, int(asset["slot_counts"]["to_slot"]))
            reused = max(0, upper - lower + 1)
            reusable_lower_bound = (
                slots - reused + SQD_PAGE_SLOTS - 1) // SQD_PAGE_SLOTS
            map_plan.update(readable=True, optimistic_reused_slots=reused,
                            request_lower_bound_if_reusable=reusable_lower_bound,
                            ttl_days=asset.get("ttl_days"),
                            generated_at=asset.get("generated_at"))
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            map_plan["reason"] = str(exc)
    payload = {
        "dry_run": True, "slots": slots,
        "estimated_sqd_requests_lower_bound": request_lower_bound,
        "estimated_sqd_requests_if_map_reusable_lower_bound": reusable_lower_bound,
        "sqd_request_estimate": {
            "empirical_slots_per_page_upper_bound": SQD_PAGE_SLOTS,
            "uncertain": True,
            "reason": "SQD stream pages can truncate before the requested end",
        },
        "estimated_getBlocks_requests": 0 if args.no_getblocks else (
            slots + GETBLOCKS_PAGE_SLOTS - 1) // GETBLOCKS_PAGE_SLOTS,
        "map_plan": map_plan,
    }
    print(json.dumps(payload, sort_keys=True))
    return 0


def run_probe(args):
    if args.from_slot < 0 or args.to_slot < args.from_slot:
        raise ValueError("invalid case slot interval")
    if args.workers < 1:
        raise ValueError("workers must be positive")
    if args.sample < 0:
        raise ValueError("sample must be nonnegative")
    if args.dry_run:
        return _dry_run(args)

    case_root = Path(args.case_root).resolve()
    case_root.mkdir(parents=True, exist_ok=True)
    parent = case_root / "data/sqd_coverage"
    parent.mkdir(parents=True, exist_ok=True)
    current_path = parent / "CURRENT.json"
    observed_current = _read_json(current_path) if current_path.is_file() else None

    sqd_endpoint = "fixture://sqd" if args.transport_fixture else DEFAULT_SQD
    rpc_endpoint = None if args.no_getblocks else _get_reference_rpc(args)
    endpoints = [item for item in (sqd_endpoint, rpc_endpoint) if item]
    transport = (FixtureTransport(args.transport_fixture) if args.transport_fixture
                 else LiveTransport(sqd_endpoint, rpc_endpoint))
    head_result = transport.call("sqd-head", {})
    if not head_result.ok:
        print(_safe_text(_result_error(head_result, endpoints), endpoints), file=sys.stderr)
        return 2
    metadata = _normalize_metadata(head_result.value)
    sqd_identity = endpoint_fingerprint(sqd_endpoint)["sha256"]
    identity = {"mint": args.mint, "from_slot": args.from_slot,
                "to_slot": args.to_slot, "sqd_fingerprint": sqd_identity,
                "plan": _plan_identity(args)}
    pending, resume = _pending_state(parent, args, sqd_identity)
    if pending is None:
        started_at = utc_now()
        planned = [{"from_slot": args.from_slot, "to_slot": args.to_slot,
                    "mode": "full" if args.full else "map-reuse"}]
        scan_id = sha256_bytes(canonical_json({
            "mint": args.mint, "scan_ranges": planned,
            "sqd_fingerprint": sqd_identity, "started_at": started_at,
        }))[:16]
        pending = parent / f"pending-{scan_id}"
        pending.mkdir(exist_ok=False)
        counts = bytearray(args.to_slot - args.from_slot + 1)
        ledger = []
    else:
        started_at = resume["started_at"]
        counts = bytearray(gzip.decompress((pending / "slot_counts.bin.gz").read_bytes()))
        ledger = [json.loads(line) for line in (pending / "ledger.jsonl").read_text(
            encoding="utf-8").splitlines() if line.strip()]
    head_raw = canonical_json(head_result.value)
    _append_ledger(ledger, [{
        "seq": 0, "ts": utc_now(), "provider": "SQD", "mode": "metadata",
        "counts_coverage": False, "query_body_sha256": request_digest("sqd-head", {}),
        "from": args.from_slot, "to": args.from_slot, "http_status": 200,
        "bytes": len(head_raw), "response_sha256": sha256_bytes(head_raw),
        "slots_covered": 0, "ok": True,
    }])

    scan_ranges = []
    shared_map = None
    if not args.resume and args.known_map:
        shared_map, reused, reuse_from, reuse_to = _load_known_map(
            args.known_map, args.from_slot, args.to_slot, sqd_identity, metadata,
            transport, ledger, endpoints)
        if reused is not None:
            counts[reuse_from - args.from_slot:reuse_to - args.from_slot + 1] = reused
            scan_ranges.append({"from_slot": reuse_from, "to_slot": reuse_to,
                                "mode": "map-reuse"})
            _append_ledger(ledger, [{
                "seq": 0, "ts": utc_now(), "provider": "shared-map",
                "mode": "map-reuse", "counts_coverage": True,
                "query_body_sha256": sha256_bytes(canonical_json({
                    "asset": shared_map["sha256"]})),
                "from": reuse_from, "to": reuse_to, "http_status": None,
                "bytes": len(reused), "response_sha256": sha256_bytes(reused),
                "slots_covered": reuse_to - reuse_from + 1, "ok": True,
            }])
        else:
            counts[:] = bytes(len(counts))

    missing = _missing_ranges(counts, args.from_slot)
    if missing:
        _scan_ranges(transport, counts, args.from_slot, missing, args.workers,
                     ledger, endpoints, mode="full",
                     checkpoint=lambda: _write_resume(
                         pending, identity, started_at, counts, ledger),
                     checkpoint_every=args.checkpoint_every)
        scan_ranges.extend({"from_slot": start, "to_slot": end, "mode": "full"}
                           for start, end in missing)
    if args.resume and not scan_ranges:
        scan_ranges = [{"from_slot": args.from_slot, "to_slot": args.to_slot,
                        "mode": "full"}]
    if args.sample:
        span = args.to_slot - args.from_slot + 1
        samples = sorted({args.from_slot + (index * max(1, span - 1)) //
                          max(1, args.sample - 1) for index in range(args.sample)})
        sample_ranges = [{"from_slot": slot, "to_slot": slot} for slot in samples]
        for slot in samples:
            row, _part = _scan_request(transport, slot, slot, 0, endpoints,
                                       mode="sample")
            row["counts_coverage"] = False
            _append_ledger(ledger, [row])
    else:
        sample_ranges = []

    if any(value == 0 for value in counts):
        _write_resume(pending, identity, started_at, counts, ledger)
        gaps = _missing_ranges(counts, args.from_slot)
        print(json.dumps({"status": "UNSCANNED", "gaps": gaps}), file=sys.stderr)
        return 2

    confirmation = None
    bitmap = None
    if not args.no_getblocks:
        confirmation, bitmap, stopped = _confirm_getblocks(
            transport, args.from_slot, args.to_slot, rpc_endpoint, ledger, endpoints)
        if stopped is not None:
            stopped_payload = {"reason": stopped["reason"], "cursor": stopped["cursor"]}
            _write_resume(pending, identity, started_at, counts, ledger,
                          stopped=stopped_payload)
            print(json.dumps(stopped_payload), file=sys.stderr)
            return 3

    _publish_bytes_overwrite(pending / "slot_counts.bin.gz", _gzip_bytes(counts))
    if bitmap is not None:
        _publish_bytes_overwrite(pending / "blocks.bin.gz", _gzip_bytes(bitmap))
    _publish_bytes_overwrite(pending / "ledger.jsonl", _ledger_bytes(ledger))

    scan_ranges = []
    for mode in ("full", "map-reuse", "recheck"):
        union = merge_ranges(item for item in (
            _successful_coverage_range(row) for row in ledger
            if row.get("mode") == mode) if item is not None)
        scan_ranges.extend({"from_slot": start, "to_slot": end, "mode": mode}
                           for start, end in union)
    scan_ranges.sort(key=lambda item: (
        item["from_slot"], item["to_slot"], item["mode"]))
    counts_ref = _sha_ref(pending / "slot_counts.bin.gz", "slot_counts.bin.gz")
    ledger_ref = _sha_ref(pending / "ledger.jsonl", "ledger.jsonl")
    if confirmation is not None:
        blocks_ref = _sha_ref(pending / "blocks.bin.gz", "blocks.bin.gz")
        confirmation["blocks_bitmap"].update(
            size=blocks_ref["size"], sha256=blocks_ref["sha256"])
    classified = classify_four_states(
        counts, args.from_slot, confirmation=confirmation, blocks_bitmap=bitmap)
    success_ranges = merge_ranges(item for item in (
        _successful_coverage_range(row) for row in ledger) if item is not None)
    producer_path = Path(__file__).resolve()
    coverage = {
        "schema": COVERAGE_SCHEMA, "version": 1, "chain": "solana",
        "mint": args.mint, "probe_id": "",
        "producer": {"path": "scripts/solana/sqd_coverage_probe.py",
                     "sha256": sha256_file(producer_path)},
        "sqd": {
            "endpoint_fingerprint": sqd_identity, "dataset": SQD_DATASET,
            "metadata_normalized": metadata,
            "metadata_sha256": sha256_bytes(canonical_json(metadata)),
            "finalized_head_at_scan": metadata["finalized_head"],
            "query_body_sha256": sqd_query_template_sha256(),
        },
        "scan_ranges": scan_ranges, "era_params": dict(ERA_PARAMS),
        "slot_counts": {**counts_ref, "from_slot": args.from_slot,
                        "to_slot": args.to_slot, "encoding": COUNT_ENCODING},
        "skipped_confirmation": confirmation, "shared_map": shared_map,
        "ledger": {**ledger_ref, "requests": len(ledger),
                   "success_ranges_sha256": sha256_bytes(canonical_json(
                       [[a, b] for a, b in success_ranges]))},
        "summary": classified["summary"],
        "candidate_slots": classified["candidate_slots"],
        "verdict": classified["verdict"],
    }
    if sample_ranges:
        coverage["sample_ranges"] = sample_ranges
    coverage["probe_id"] = compute_probe_id(coverage)
    publish_exclusive(pending / "coverage_map.json", coverage)
    probe_id = coverage["probe_id"]
    base = f"data/sqd_coverage/{probe_id}"
    pointer_inputs = {
        "coverage_map": _sha_ref(pending / "coverage_map.json",
                                 f"{base}/coverage_map.json"),
        "slot_counts": _sha_ref(pending / "slot_counts.bin.gz",
                                f"{base}/slot_counts.bin.gz"),
        "ledger": _sha_ref(pending / "ledger.jsonl", f"{base}/ledger.jsonl"),
    }
    if confirmation is not None:
        pointer_inputs["blocks_bitmap"] = _sha_ref(
            pending / "blocks.bin.gz", f"{base}/blocks.bin.gz")
    supersedes = (observed_current.get("probe_id")
                  if isinstance(observed_current, dict) else None)
    pointer = {
        "schema": COVERAGE_POINTER_SCHEMA,
        "target": {"chain": "solana", "token": args.mint,
                   "as_of_block": args.to_slot},
        "mode": "formal", "verdict": "PASS", "exit_code": 0,
        "producer": coverage["producer"], "inputs": pointer_inputs,
        "probe_id": probe_id, "supersedes": supersedes,
        "published_at": utc_now(),
    }
    def prepublish_validate(final_dir):
        fd, candidate_name = tempfile.mkstemp(prefix="sqd-coverage-pointer-",
                                              suffix=".json")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(canonical_json(pointer) + b"\n")
                handle.flush()
                os.fsync(handle.fileno())
            checked = validate_coverage(
                case_root, final_dir / "coverage_map.json", candidate_name,
                args.from_slot, args.to_slot)
            if not checked["ok"]:
                raise RuntimeError("self-validation failed: "
                                   + "; ".join(checked["reasons"]))
        finally:
            _remove_one(candidate_name)

    action = publish_probe_generation(
        case_root, pending, probe_id, pointer, observed_current=observed_current,
        prepublish_validate=prepublish_validate)
    final = parent / probe_id
    result = validate_coverage(case_root, final / "coverage_map.json", current_path,
                               args.from_slot, args.to_slot)
    if not result["ok"]:
        raise RuntimeError("published pointer validation failed: "
                           + "; ".join(result["reasons"]))
    print(json.dumps({"status": action, "probe_id": probe_id,
                      "verdict": coverage["verdict"]}, sort_keys=True))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mint", required=True)
    parser.add_argument("--case-root", required=True)
    parser.add_argument("--from-slot", type=int, required=True)
    parser.add_argument("--to-slot", type=int, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--full", action="store_true")
    mode.add_argument("--known-map")
    parser.add_argument("--sample", type=int, default=0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--checkpoint-every", type=int, default=2000)
    parser.add_argument("--reference-rpc")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--no-getblocks", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--transport-fixture", help=argparse.SUPPRESS)
    return parser


def build_export_parser():
    parser = argparse.ArgumentParser(description="Export a published shared SQD map")
    parser.add_argument("--case-root", required=True)
    parser.add_argument("--probe-id", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--version")
    return parser


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "export-shared-map":
        args = build_export_parser().parse_args(argv[1:])
        try:
            return export_shared_map(args)
        except Exception as exc:
            print(_safe_text(f"sqd shared-map export failed: {exc}", []),
                  file=sys.stderr)
            return 2
    args = build_parser().parse_args(argv)
    try:
        return run_probe(args)
    except Exception as exc:
        fixture = "fixture://helius" if args.transport_fixture else args.reference_rpc
        endpoints = [item for item in (DEFAULT_SQD, fixture) if item]
        print(_safe_text(f"sqd coverage probe failed: {exc}", endpoints), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
