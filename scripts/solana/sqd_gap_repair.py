#!/usr/bin/env python3
"""Produce, verify and publish deterministic Solana SQD repair generations."""
from __future__ import annotations

import argparse
import concurrent.futures
import fcntl
import gzip
import hashlib
import json
import os
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

LIB = Path(__file__).resolve().parents[1] / "lib"
sys.path.insert(0, str(LIB))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import net  # noqa: E402
from endpoint_identity import (endpoint_fingerprint, public_endpoint,
                               redact_endpoint_text)  # noqa: E402
from receipt_kernel import publish_exclusive, publish_overwrite  # noqa: E402
from solana_exact_validate import validate_coverage, validate_repair_bundle_deep  # noqa: E402
from spl_edge_core import soltx_cache_paths, sqd_repair_paths  # noqa: E402
from sqd_coverage_probe import sqd_query_body  # noqa: E402
from sqd_cache_identity import (resolve_formal_cache,
                                validate_repair_bundle)  # noqa: E402
from sqd_repair_core import (canonical_json, compute_gid, compute_plan_digest,
                             account_keys, derive_residual_owners,
                             edge_logical_evidence, edges_for_transaction,
                             is_nonce_transaction, is_vote_transaction, merge_edges,
                             owner_activity, parse_routea_cache, read_edge_file,
                             sha256_bytes, sha256_file)  # noqa: E402


CACHE_SCHEMA = "sqd-solana-cache/v4"
COLLECTOR_ID = "sqd_gap_repair.py/v1"
PRODUCED_SCHEMAS = (
    CACHE_SCHEMA, "sqd-solana-repair-bundle/v1",
    "sqd-solana-coverage-resolution/v1", "sqd-solana-repair-pointer/v1",
)
KEY_FILE = Path.home() / ".config/helius/api-key"
KEYS_FILE = Path.home() / ".config/helius/api-keys"
QUOTA_STATUSES = {402, 429}
DEFAULT_SQD = "https://portal.sqd.dev/datasets/solana-mainnet"


class QuotaStopped(RuntimeError):
    def __init__(self, cursor, payloads=None, ledger=None, completed_slots=None):
        super().__init__("reference-quota")
        self.cursor = cursor
        self.payloads = list(payloads or [])
        self.ledger = list(ledger or [])
        self.completed_slots = sorted(set(completed_slots or []))


def request_digest(kind, body):
    return sha256_bytes(canonical_json({"kind": kind, "body": body}))


class RepairFixtureTransport:
    def __init__(self, directory):
        payload = _json(Path(directory) / "responses.json")
        if payload.get("format") != "sqd-gap-repair-transport-fixture-v1":
            raise ValueError("repair fixture transport schema mismatch")
        self.responses = payload.get("responses") or {}

    def call(self, kind, body):
        item = self.responses.get(request_digest(kind, body))
        if not isinstance(item, dict):
            return net.Result(ok=False, error={
                "category": "fixture", "message": "missing fixture response",
                "http_status": None, "retryable": False})
        if item.get("ok") is True:
            return net.Result(ok=True, value=item.get("value"))
        return net.Result(ok=False, error={
            "category": item.get("category", "fixture"),
            "message": str(item.get("message", "fixture failure")),
            "http_status": item.get("http_status"),
            "retryable": bool(item.get("retryable", False)),
        })


class RepairLiveTransport:
    def __init__(self, reference_endpoint):
        self.reference_endpoint = reference_endpoint

    def call(self, kind, body):
        if kind == "reference-getBlock":
            return net.curl_json(self.reference_endpoint, post_json=body,
                                 no_retry_statuses=tuple(QUOTA_STATUSES))
        if kind in {"sqd-census", "sqd-probe", "sqd-beta"}:
            return net.curl_json(f"{DEFAULT_SQD}/stream", post_json=body)
        raise ValueError(f"unknown repair transport kind: {kind}")


def reference_endpoint_identity(endpoint):
    """Return the host/path identity used by plans and resumable ledgers."""
    fingerprint_input = public_endpoint(endpoint)
    return {
        "fingerprint_input": fingerprint_input,
        "sha256": endpoint_fingerprint(fingerprint_input)["sha256"],
    }


def _keys_from_file(path):
    path = Path(path)
    if not path.is_file():
        return []
    keys = []
    for line in path.read_text(encoding="utf-8").splitlines():
        key = line.strip()
        if key and key not in keys:
            keys.append(key)
    return keys


def load_reference_endpoints(reference_rpc=None, reference_keys_file=None, *,
                             keys_file=KEYS_FILE, key_file=KEY_FILE):
    """Resolve an explicit RPC or the CLI/default/fallback Helius key files."""
    if reference_rpc:
        return [str(reference_rpc)]
    selected = Path(reference_keys_file) if reference_keys_file else Path(keys_file)
    if reference_keys_file and not selected.is_file():
        raise ValueError(f"reference keys file unavailable: {selected}")
    keys = _keys_from_file(selected)
    if not keys:
        keys = _keys_from_file(key_file)
    if not keys:
        raise ValueError("reference key unavailable: ~/.config/helius/api-key")
    return [f"https://mainnet.helius-rpc.com/?api-key={key}" for key in keys]


class ReferenceEndpointPool:
    """Round-robin reference pool with process-local permanent quota eviction."""

    def __init__(self, endpoints, transport_factory):
        self._active = [(endpoint, transport_factory(endpoint))
                        for endpoint in endpoints]
        if not self._active:
            raise ValueError("reference endpoint pool is empty")
        self._cursor = 0
        self._lock = threading.Lock()

    def _next(self, slot):
        with self._lock:
            if not self._active:
                raise QuotaStopped(slot)
            index = self._cursor % len(self._active)
            item = self._active[index]
            self._cursor = (index + 1) % len(self._active)
            return item

    def _remove(self, endpoint):
        with self._lock:
            for index, (candidate, _transport) in enumerate(self._active):
                if candidate == endpoint:
                    self._active.pop(index)
                    if self._active:
                        self._cursor %= len(self._active)
                    else:
                        self._cursor = 0
                    break

    def get_block(self, slot, body):
        attempts = 0
        while True:
            endpoint, transport = self._next(slot)
            attempts += 1
            result = transport.call("reference-getBlock", body)
            block, error = _result_value(result)
            if _is_quota(result, error):
                self._remove(endpoint)
                continue
            return result, block, error, attempts


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _file_ref(path, relative):
    path = Path(path)
    return {"path": str(relative), "size": path.stat().st_size,
            "sha256": sha256_file(path)}


def _fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _publish_bytes_exclusive(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        if path.read_bytes() == payload:
            return path
        raise FileExistsError(f"resume artifact differs: {path}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    return path


def _publish_json_exclusive(path, payload):
    path = Path(path)
    if path.is_file():
        if _json(path) == payload:
            return path
        raise FileExistsError(f"resume artifact differs: {path}")
    return publish_exclusive(path, payload)


def _jsonl_bytes(rows):
    return b"".join(canonical_json(row) + b"\n" for row in rows)


def _gzip_jsonl(rows):
    raw = b"".join((json.dumps(list(row), separators=(",", ":"),
                                   ensure_ascii=False) + "\n").encode()
                   for row in rows)
    return gzip.compress(raw, mtime=0)


def guard_coverage_writes(paths):
    """Repair is never authorized to mutate probe coverage assets."""
    for value in paths:
        normalized = "/" + str(value).replace("\\", "/").lstrip("/")
        if "/data/sqd_coverage/" in normalized:
            raise ValueError("repair producer must not write coverage assets")
    return True


def should_publish_generation(resolution, repair_layer=None, slot_index_map=None):
    census = resolution.get("census", []) if isinstance(resolution, dict) else []
    confirmed = any(str(row.get("result", "")).startswith("confirmed_")
                    for row in census if isinstance(row, dict))
    edges = sum(len(row.get("edges") or []) for row in (repair_layer or []))
    remaps = len(slot_index_map or [])
    return bool(confirmed and (edges or remaps))


def validate_resolution(resolution, candidate_slots, *, formal=False):
    if resolution.get("schema") != "sqd-solana-coverage-resolution/v1":
        raise ValueError("resolution schema mismatch")
    census = resolution.get("census")
    if not isinstance(census, list):
        raise ValueError("resolution census missing")
    slots = [row.get("slot") for row in census if isinstance(row, dict)]
    if slots != sorted(set(slots)):
        raise ValueError("resolution census slots must be sorted unique")
    candidates = set(candidate_slots)
    if not candidates.issubset(slots):
        effective = "INCONCLUSIVE"
    elif any(str(row.get("result", "")).startswith("confirmed_") for row in census):
        effective = "DEFECTS_CONFIRMED"
    else:
        effective = "NO_KNOWN_NONCE_OMISSION_DETECTED"
    if resolution.get("effective_verdict") != effective:
        raise ValueError("resolution effective_verdict is not mechanically derived")
    if formal and effective != "DEFECTS_CONFIRMED":
        raise ValueError("formal repair requires DEFECTS_CONFIRMED resolution")
    return effective


def validate_census_support(repair_transactions, map_rows, resolution):
    confirmed = {row.get("slot") for row in resolution.get("census", [])
                 if str(row.get("result", "")).startswith("confirmed_")}
    used = {row.get("slot") for row in repair_transactions} \
        | {row.get("slot") for row in map_rows}
    if not used.issubset(confirmed):
        raise ValueError("repair transaction/remap lacks confirmed census support")
    return True


def validate_current_candidates(current_candidates, resolution):
    census = {row.get("slot") for row in resolution.get("census", [])}
    if not set(current_candidates).issubset(census):
        raise ValueError("current coverage has candidates absent from generation census")
    return True


def validate_base_binding(bundle, base_edge_path):
    if bundle.get("base", {}).get("edge_sha256") != sha256_file(base_edge_path):
        raise ValueError("repair generation invalidated by base recapture")
    return True


def validate_merged_binding(meta, bundle, meta_path):
    if "gid" in meta or "bundle_sha256" in meta:
        raise ValueError("merged meta contains circular gid/bundle binding")
    if meta.get("plan_digest") != bundle.get("plan_digest") \
            or bundle.get("merged", {}).get("meta_sha256") != sha256_file(meta_path):
        raise ValueError("merged meta to bundle binding mismatch")
    return True


def fsync_publish_directories(generation_dir, repair_parent, pointer_parent):
    """Persist the generation, rename parent and pointer parent in that order."""
    for path in (generation_dir, repair_parent, pointer_parent):
        _fsync_dir(path)
    return True


def publish_generation_exclusive(pending, final):
    pending, final = Path(pending), Path(final)
    _fsync_dir(pending)
    if final.exists():
        raise FileExistsError(f"immutable generation already exists: {final}")
    os.rename(pending, final)
    _fsync_dir(final.parent)
    return final


def publish_current_cas(current_path, pointer, *, expected_current,
                        bundle_path, base_edge_path):
    """Lock, CAS and durably publish CURRENT, including E10 idempotence."""
    current_path, bundle_path = Path(current_path), Path(bundle_path)
    parent = current_path.parent
    parent.mkdir(parents=True, exist_ok=True)
    bundle = _json(bundle_path)
    validate_base_binding(bundle, base_edge_path)
    bundle_sha = sha256_file(bundle_path)
    if pointer.get("inputs", {}).get("bundle", {}).get("sha256") != bundle_sha:
        raise ValueError("repair pointer bundle sha256 differs from bundle")
    lock_path = parent / ".lock"
    lock_path.touch(exist_ok=True)
    with lock_path.open("r+b") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            current = _json(current_path) if current_path.is_file() else None
            if (isinstance(current, dict) and current.get("gid") == pointer.get("gid")
                    and current.get("inputs", {}).get("bundle", {}).get(
                        "sha256") == bundle_sha):
                _fsync_dir(parent)
                return "idempotent-republish"
            current_gid = current.get("gid") if isinstance(current, dict) else None
            expected_gid = (expected_current.get("gid")
                            if isinstance(expected_current, dict) else None)
            if pointer.get("supersedes") != current_gid or current_gid != expected_gid:
                raise RuntimeError("repair pointer CAS failed")
            publish_overwrite(current_path, pointer)
            _fsync_dir(parent)
            return "published"
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _coverage(case_root, mint):
    parent = case_root / "data/sqd_coverage"
    pointer_path = parent / "CURRENT.json"
    pointer = _json(pointer_path)
    if pointer.get("target", {}).get("token") != mint:
        raise ValueError("coverage pointer mint mismatch")
    probe_id = pointer.get("probe_id")
    coverage_path = parent / str(probe_id) / "coverage_map.json"
    coverage = _json(coverage_path)
    slot_meta = coverage.get("slot_counts", {})
    checked = validate_coverage(
        case_root, coverage_path, pointer_path,
        slot_meta.get("from_slot"), slot_meta.get("to_slot"))
    if not checked["ok"]:
        raise ValueError("coverage validation failed: " + "; ".join(checked["reasons"]))
    return (pointer, coverage, coverage_path,
            parent / str(probe_id) / "slot_counts.bin.gz", checked)


def _base(case_root, mint):
    edge, meta, _parts = soltx_cache_paths(mint, case_root / "data")
    if not edge.is_file() or not meta.is_file():
        raise ValueError("canonical base cache pair missing")
    return edge, meta, _json(meta)


def _residual_subset(path):
    if not path:
        return None
    payload = _json(path)
    if isinstance(payload, dict) and set(payload) == {"owners"}:
        payload = payload["owners"]
    if not isinstance(payload, list) or any(
            not isinstance(owner, str) or not owner for owner in payload):
        raise ValueError("--residual-owners must be a JSON owner string array")
    return sorted(set(payload))


def _beta_input(case_root, subset=None):
    data = Path(case_root) / "data"
    paths = {
        "receipt": data / "reconcile_receipt.json",
        "replay_final_balances": data / "replay_final_balances.json",
        "holders_owners": data / "holders_owners.json",
    }
    values = {name: _json(path) for name, path in paths.items()}
    residual = derive_residual_owners(
        values["receipt"], values["replay_final_balances"],
        values["holders_owners"], subset=subset)
    refs = {name: _file_ref(path, str(path.relative_to(case_root)))
            for name, path in paths.items()}
    return residual, refs


def _beta_body(owner, slot):
    fields = {
        "block": {"number": True},
        "transaction": {"transactionIndex": True},
        "tokenBalance": {
            "transactionIndex": True, "account": True,
            "preMint": True, "postMint": True,
            "preOwner": True, "postOwner": True,
            "preAmount": True, "postAmount": True,
        },
    }
    return {
        "type": "solana", "fromBlock": slot, "toBlock": slot,
        "includeAllBlocks": True, "fields": fields,
        "tokenBalances": [
            {"preOwner": [owner], "transaction": True},
            {"postOwner": [owner], "transaction": True},
        ],
    }


def _blocks(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _beta_post_amount(value, slot, owner, mint):
    matching = [block for block in _blocks(value) if isinstance(block, dict)
                and (block.get("header") or {}).get("number") == slot]
    rows = [row for block in matching for row in (block.get("tokenBalances") or [])
            if row.get("preMint") == mint or row.get("postMint") == mint]
    latest = {}
    for row in rows:
        if row.get("preOwner") != owner and row.get("postOwner") != owner:
            continue
        account = row.get("account")
        index = row.get("transactionIndex")
        if not isinstance(account, str) or not isinstance(index, int) \
                or isinstance(index, bool):
            raise ValueError("SQD beta token balance identity invalid")
        if account not in latest or index > latest[account][0]:
            amount = row.get("postAmount") if row.get("postOwner") == owner else 0
            if amount is None:
                amount = 0
            if isinstance(amount, str) and amount.isdigit():
                amount = int(amount)
            if not isinstance(amount, int) or isinstance(amount, bool):
                raise ValueError("SQD beta postAmount must be an integer")
            latest[account] = (index, amount)
    return sum(item[1] for item in latest.values()) if latest else None


def _probe_fingerprint(transport, lower, upper):
    body = sqd_query_body(lower, upper)
    result = transport.call("sqd-probe", body)
    value, error = _result_value(result)
    if error is not None:
        raise ValueError("SQD beta fingerprint failed")
    blocks = [block for block in _blocks(value) if isinstance(block, dict)]
    slots = [((block.get("header") or {}).get("number")) for block in blocks]
    if any(not isinstance(slot, int) or isinstance(slot, bool)
           or slot < lower or slot > upper for slot in slots) \
            or slots != sorted(set(slots)):
        raise ValueError("SQD beta fingerprint slot identity invalid")
    by_slot = dict(zip(slots, blocks))
    rows = []
    for slot in range(lower, upper + 1):
        block = by_slot.get(slot)
        rows.append({"slot": slot,
                     "count": (-1 if block is None else len(
                         block.get("instructions") or []))})
    return rows


def run_beta_search(args, case_root, base_edges, transport):
    """Run E25 owner-balance bisection and return a deterministic trace."""
    residual, refs = _beta_input(case_root, _residual_subset(args.residual_owners))
    trace = {
        "schema": "sqd-solana-beta-trace/v1", "inputs": refs,
        "residual_owners": residual, "rounds": [], "candidate_slots": [],
    }
    all_candidates = set()
    for item in residual:
        owner = item["owner"]
        activity = owner_activity(base_edges, owner)
        cache = {}

        def probe(index):
            slot = activity[index]["slot"]
            if slot not in cache:
                body = _beta_body(owner, slot)
                result = transport.call("sqd-beta", body)
                value, error = _result_value(result)
                if error is not None:
                    raise ValueError(f"SQD beta balance probe failed for owner {owner}")
                raw = canonical_json(_blocks(value))
                actual = _beta_post_amount(value, slot, owner, args.mint)
                cache[slot] = {
                    "slot": slot, "sqd_post_amount": actual,
                    "replay_balance": activity[index]["replay_balance"],
                    "match": (actual is not None
                              and actual == activity[index]["replay_balance"]),
                    "query_body_sha256": sha256_bytes(canonical_json(body)),
                    "response_sha256": sha256_bytes(raw),
                }
            return cache[slot]

        breakpoint = None
        if activity:
            last = probe(len(activity) - 1)
            first = probe(0)
            if not last["match"]:
                lo, hi = 0, len(activity) - 1
                if first["match"]:
                    while hi - lo > 1:
                        if len(cache) >= 40:
                            raise ValueError("SQD beta owner probe limit exceeded")
                        mid = (lo + hi) // 2
                        if probe(mid)["match"]:
                            lo = mid
                        else:
                            hi = mid
                else:
                    hi = 0
                breakpoint = activity[hi]["slot"]
        fingerprint = []
        candidates = []
        window = None
        if breakpoint is not None:
            window = {"from": max(0, breakpoint - 64), "to": breakpoint + 64}
            fingerprint = _probe_fingerprint(
                transport, window["from"], window["to"])
            candidates = sorted(row["slot"] for row in fingerprint
                                if row["count"] == 0)
            all_candidates.update(candidates)
        trace["rounds"].append({
            "round": 1, "owner": owner,
            "probes": sorted(cache.values(), key=lambda row: row["slot"]),
            "breakpoint_slot": breakpoint, "window": window,
            "fingerprint": fingerprint, "candidate_slots": candidates,
        })
    trace["candidate_slots"] = sorted(all_candidates)
    return trace


def validate_coverage_state_consistency(state, *, header_present,
                                        nonce_count, beta_candidate=False):
    if not isinstance(nonce_count, int) or isinstance(nonce_count, bool) \
            or nonce_count < 0:
        raise ValueError("repair nonce count must be a nonnegative integer")
    if not beta_candidate and state not in {"DEFECT_CANDIDATE", "MISSING_BLOCK"}:
        raise ValueError("non-candidate coverage state entered alpha")
    if state in {"NO_HEADER", "MISSING_BLOCK", "SKIPPED_CONFIRMED"}:
        matches = not header_present
    elif state in {"DEFECT_CANDIDATE", "ERA_UNCERTAIN"}:
        matches = header_present and nonce_count == 0
    elif state == "HEALTHY":
        matches = header_present and nonce_count > 0
    else:
        matches = False
    if not matches:
        raise ValueError("SQD coverage state changed before repair")
    return True


def _plan(case_root, mint, blocks_cache=None, reference_fingerprint=None,
          beta_slots=()):
    # Resolve first so an invalid CURRENT is a hard error; generation building
    # still binds the immutable canonical base pair below.
    resolve_formal_cache(mint, case_root)
    base_edge, base_meta, base = _base(case_root, mint)
    pointer, coverage, coverage_path, counts_path, checked = _coverage(case_root, mint)
    slot_meta = coverage.get("slot_counts", {})
    if slot_meta.get("from_slot") > base.get("from_slot") \
            or slot_meta.get("to_slot") < base.get("finalized_upper_slot"):
        raise ValueError("coverage interval does not cover the current base interval")
    candidates = sorted(set(coverage.get("candidate_slots") or [])
                        | set(beta_slots))
    source = "local-evidence-cache" if blocks_cache else "live"
    cache_dirs = ([blocks_cache] if isinstance(blocks_cache, (str, Path))
                  else list(blocks_cache or []))
    reference = {
        "kind": "helius-getBlock",
        "endpoint_fingerprint": (sha256_bytes(canonical_json(sorted(
            str(Path(item).resolve()) for item in cache_dirs)))
                                 if blocks_cache else reference_fingerprint),
        "source": source,
    }
    producer = {"path": "scripts/solana/sqd_gap_repair.py",
                "sha256": sha256_file(__file__)}
    plan = {
        "base": {"edge_sha256": sha256_file(base_edge),
                 "meta_sha256": sha256_file(base_meta)},
        "coverage": {"probe_id": coverage["probe_id"],
                     "map_sha256": sha256_file(coverage_path)},
        "candidate_slots": sorted(set(candidates)),
        "plan_candidates": {
            "coverage": sorted(set(coverage.get("candidate_slots") or [])),
            "beta": sorted(set(beta_slots)),
        },
        "mode": "exploration" if blocks_cache else "formal",
        "reference": reference, "producer": producer,
    }
    plan["plan_digest"] = compute_plan_digest(plan)
    return plan, (base_edge, base_meta, base), (
        pointer, coverage, coverage_path, counts_path, checked)


def _rpc_body(slot):
    return {
        "jsonrpc": "2.0", "id": slot, "method": "getBlock",
        "params": [slot, {"commitment": "finalized", "transactionDetails": "full",
                          "encoding": "json", "rewards": False,
                          "maxSupportedTransactionVersion": 0}],
    }


def _census_body(slot):
    return {
        "type": "solana", "fromBlock": slot, "toBlock": slot,
        "includeAllBlocks": True,
        "fields": {
            "block": {"number": True, "hash": True},
            "transaction": {"transactionIndex": True, "signatures": True,
                            "err": True},
        },
        "transactions": [{}],
    }


def _result_value(result):
    if not result.ok:
        return None, result.error
    value = result.value
    if isinstance(value, dict) and value.get("error") is not None:
        return None, value["error"]
    if isinstance(value, dict) and "result" in value:
        return value["result"], None
    return value, None


def _is_quota(result, error):
    transport_error = result.error if isinstance(result.error, dict) else {}
    if transport_error.get("http_status") in QUOTA_STATUSES:
        return True
    if isinstance(error, dict):
        message = str(error.get("message", "")).lower()
        return error.get("code") in QUOTA_STATUSES or any(
            text in message for text in ("quota", "credit", "payment required",
                                         "rate limit", "too many request"))
    return False


def _ledger_header(plan):
    return {
        "schema": "sqd-solana-rpc-ledger/v1",
        "plan_digest": plan["plan_digest"],
        "reference": {"kind": plan["reference"]["kind"],
                      "endpoint_fingerprint": plan["reference"][
                          "endpoint_fingerprint"]},
    }


def _read_ledger_prefix(path):
    path = Path(path)
    if not path.is_file():
        return []
    raw = path.read_bytes()
    complete = raw
    if raw and not raw.endswith(b"\n"):
        cut = raw.rfind(b"\n")
        complete = raw[:cut + 1] if cut >= 0 else b""
    rows = []
    for line in complete.splitlines():
        try:
            value = json.loads(line)
        except (ValueError, json.JSONDecodeError) as exc:
            raise ValueError("RPC ledger contains malformed complete line") from exc
        if not isinstance(value, dict):
            raise ValueError("RPC ledger complete line must be an object")
        rows.append(value)
    clean = _jsonl_bytes(rows)
    if clean != raw:
        with path.open("wb") as handle:
            handle.write(clean)
            handle.flush()
            os.fsync(handle.fileno())
    return rows


def _append_ledger_row(path, row):
    with Path(path).open("ab") as handle:
        handle.write(canonical_json(row) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())


def load_resume_slots(pending, header):
    """Return slots whose evidence pair and successful ledger row align."""
    pending = Path(pending)
    ledger_path = pending / "rpc_ledger.jsonl"
    rows = _read_ledger_prefix(ledger_path)
    if not rows:
        _publish_bytes_exclusive(ledger_path, _jsonl_bytes([header]))
        return set(), []
    if rows[0].get("schema") != "sqd-solana-rpc-ledger/v1" \
            or rows[0] != header:
        raise ValueError("resume RPC ledger header differs from plan")
    completed = set()
    seen_slots = set()
    required = {"seq", "ts", "method", "params_digest", "slot",
                "endpoint_fingerprint", "http_status", "bytes",
                "credits_estimate", "result_sha256", "attempt"}
    for expected_seq, row in enumerate(rows[1:]):
        slot = row.get("slot")
        if set(row) != required or row.get("seq") != expected_seq \
                or row.get("method") != "getBlock" \
                or row.get("http_status") != 200 \
                or not isinstance(slot, int) or isinstance(slot, bool) \
                or slot in seen_slots:
            raise ValueError("resume RPC ledger successful prefix is invalid")
        seen_slots.add(slot)
        sqd_path = pending / "evidence" / f"{slot}.sqd.json"
        ref_path = pending / "evidence" / f"{slot}.ref.json"
        if not sqd_path.is_file() or not ref_path.is_file():
            continue
        try:
            sqd = _json(sqd_path)
            ref = _json(ref_path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        expected_params = sha256_bytes(canonical_json(_rpc_body(slot)))
        if row.get("params_digest") == expected_params \
                and row.get("endpoint_fingerprint") == header["reference"][
                    "endpoint_fingerprint"] \
                and sqd.get("slot") == slot and ref.get("slot") == slot \
                and ref.get("raw_response_sha256") == row.get("result_sha256"):
            completed.add(slot)
    return completed, rows[1:]


def _sqd_call_with_backoff(transport, kind, body, slot, failure):
    """Retry transient SQD failures three times with bounded 2/4/8s backoff."""
    for attempt in range(4):
        result = transport.call(kind, body)
        value, error = _result_value(result)
        if error is None:
            return value
        transport_error = result.error if isinstance(result.error, dict) else {}
        status = transport_error.get("http_status")
        retryable = bool(transport_error.get("retryable")) or status == 529 \
            or isinstance(status, int) and status >= 500
        if not retryable or attempt == 3:
            raise ValueError(f"{failure} at slot {slot}: {error}")
        time.sleep((2, 4, 8)[attempt])
    raise AssertionError("unreachable SQD retry state")


def _state_probe(transport, slot, *, retry=False):
    body = sqd_query_body(slot, slot)
    if retry:
        value = _sqd_call_with_backoff(
            transport, "sqd-probe", body, slot,
            "SQD coverage-state recheck failed")
    else:
        result = transport.call("sqd-probe", body)
        value, error = _result_value(result)
        if error is not None:
            raise ValueError(f"SQD coverage-state recheck failed at slot {slot}")
    matching = [block for block in _blocks(value) if isinstance(block, dict)
                and (block.get("header") or {}).get("number") == slot]
    if len(matching) > 1:
        raise ValueError(f"SQD coverage-state recheck duplicated slot {slot}")
    present = bool(matching)
    count = len((matching[0].get("instructions") or [])) if present else 0
    raw = canonical_json(_blocks(value))
    return present, count, sha256_bytes(canonical_json(body)), sha256_bytes(raw)


def _payload_from_evidence(sqd_ev, ref_ev):
    transaction_by_signature = {
        row["signature"]: row for row in ref_ev.get("transactions", [])}
    missing = []
    for item in ref_ev.get("missing_detail", []):
        tx_row = transaction_by_signature.get(item.get("signature"), {})
        keys = item.get("account_keys_full") or []
        def balances(name):
            out = []
            for row in item.get(name, []):
                out.append({
                    "accountIndex": row.get("accountIndex"),
                    "mint": row.get("mint"), "owner": row.get("owner"),
                    "uiTokenAmount": {"amount": str(row.get("amount", 0)),
                                      "decimals": row.get("decimals", 0)},
                })
            return out
        tx = {
            "transaction": {"signatures": [item["signature"]],
                            "message": {"accountKeys": keys, "instructions": []}},
            "meta": {"err": tx_row.get("err"), "loadedAddresses": {},
                     "preTokenBalances": balances("pre_token_balances(mint)"),
                     "postTokenBalances": balances("post_token_balances(mint)")},
        }
        missing.append({"pos": tx_row.get("position"), "sig": item["signature"],
                        "nonce": tx_row.get("is_nonce") is True,
                        "failed": tx_row.get("err") is not None, "tx": tx})
    return {
        "slot": ref_ev["slot"], "blockhash": ref_ev["blockhash"],
        "sqd_blockhash": sqd_ev.get("blockhash"),
        "parentSlot": ref_ev.get("parent_slot"),
        "blockTime": ref_ev.get("block_time"),
        "helius_sigs": [row.get("signature")
                        for row in ref_ev.get("transactions", [])],
        "sqd_sigs": [row.get("signature")
                     for row in sqd_ev.get("transactions", [])],
        "sqd_transactions": sqd_ev.get("transactions", []),
        "missing_full": missing,
        "reference_response_sha256": ref_ev.get("raw_response_sha256"),
        "coverage_state": sqd_ev.get("coverage_state"),
        "sqd_nonce_count_at_repair": sqd_ev.get(
            "sqd_nonce_count_at_repair"),
        "coverage_probe_query_sha256": sqd_ev.get(
            "coverage_probe_query_sha256"),
        "coverage_probe_response_sha256": sqd_ev.get(
            "coverage_probe_response_sha256"),
        "census_query_body_sha256": sqd_ev.get("query_body_sha256"),
        "census_response_sha256": sqd_ev.get("response_sha256"),
    }


def _persist_live_slot(pending, payload, mint, ledger_row):
    evidence = Path(pending) / "evidence"
    evidence.mkdir(exist_ok=True)
    _census, _layer, _mapping, sqd_ev, ref_ev = _routea_slot(payload, mint)
    _publish_json_exclusive(evidence / f"{payload['slot']}.sqd.json", sqd_ev)
    _publish_json_exclusive(evidence / f"{payload['slot']}.ref.json", ref_ev)
    _append_ledger_row(Path(pending) / "rpc_ledger.jsonl", ledger_row)
    _fsync_dir(evidence)


def resume_published_generation(parent, plan_digest):
    """Find the unique immutable generation already produced for this plan."""
    matches = []
    for path in sorted(Path(parent).glob("gen-*/bundle.json")):
        try:
            bundle = _json(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if bundle.get("plan_digest") == plan_digest:
            matches.append((path.parent, bundle))
    if len(matches) > 1:
        raise ValueError("multiple immutable generations match resume plan")
    return matches[0] if matches else None


def assert_resume_cas(bundle, current):
    """Fail closed if CURRENT moved after the resumed generation was planned."""
    current_gid = current.get("gid") if isinstance(current, dict) else None
    if current_gid not in {bundle.get("supersedes"), bundle.get("gid")}:
        raise RuntimeError("repair pointer CAS failed after resume drift")
    return True


def _fetch_live_slot(slot, state, beta_slots, reference_pool, sqd_transport,
                     reference_fingerprint):
    present, nonce_count, probe_query_sha, probe_response_sha = _state_probe(
        sqd_transport, slot, retry=True)
    validate_coverage_state_consistency(
        state, header_present=present, nonce_count=nonce_count,
        beta_candidate=slot in beta_slots)
    body = _rpc_body(slot)
    result, block, error, attempts = reference_pool.get_block(slot, body)
    if error is not None or not isinstance(block, dict):
        raise ValueError(f"reference getBlock failed at slot {slot}: {error}")
    raw = json.dumps(block, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False).encode("utf-8")
    ledger_row = {
        "seq": None, "ts": int(time.time()), "method": "getBlock",
        "params_digest": sha256_bytes(canonical_json(body)), "slot": slot,
        "endpoint_fingerprint": reference_fingerprint,
        "http_status": (200 if result.ok else int(
            (result.error or {}).get("http_status") or 0)),
        "bytes": len(raw), "credits_estimate": 10,
        "result_sha256": sha256_bytes(raw), "attempt": attempts,
    }
    census_body = _census_body(slot)
    census_value = _sqd_call_with_backoff(
        sqd_transport, "sqd-census", census_body, slot, "SQD census failed")
    blocks = census_value if isinstance(census_value, list) else [census_value]
    census_raw = canonical_json(blocks)
    matching = [item for item in blocks if isinstance(item, dict)
                and (item.get("header") or {}).get("number") == slot]
    sqd_block = matching[0] if matching else None
    if bool(sqd_block) != present:
        raise ValueError(
            f"SQD state probe/census header disagreement at slot {slot}")
    sqd_transactions = (sqd_block.get("transactions") or []) if sqd_block else []
    normalized_sqd = []
    for row in sqd_transactions:
        signature = (row.get("signatures") or [None])[0]
        index = row.get("transactionIndex")
        if not signature or not isinstance(index, int) or isinstance(index, bool):
            raise ValueError(f"SQD census transaction identity invalid at slot {slot}")
        normalized_sqd.append({"index": index, "signature": signature,
                               "err": row.get("err")})
    if len({row["index"] for row in normalized_sqd}) != len(normalized_sqd) \
            or len({row["signature"] for row in normalized_sqd}) != len(normalized_sqd):
        raise ValueError(f"SQD census transaction identity is not unique at slot {slot}")
    normalized_sqd.sort(key=lambda row: row["index"])
    sqd_sigs = sorted(row["signature"] for row in normalized_sqd)
    reference_transactions = block.get("transactions") or []
    helius_sigs = [((tx.get("transaction") or {}).get("signatures") or [None])[0]
                   for tx in reference_transactions]
    missing_full = []
    for position, tx in enumerate(reference_transactions):
        signature = helius_sigs[position]
        if not signature or is_vote_transaction(tx) or signature in sqd_sigs:
            continue
        missing_full.append({
            "pos": position, "sig": signature,
            "nonce": is_nonce_transaction(tx),
            "failed": (tx.get("meta") or {}).get("err") is not None,
            "tx": tx,
        })
    payload = {
        "slot": slot, "blockhash": block.get("blockhash"),
        "sqd_blockhash": ((sqd_block or {}).get("header") or {}).get("hash"),
        "parentSlot": block.get("parentSlot"), "blockTime": block.get("blockTime"),
        "helius_sigs": helius_sigs, "sqd_sigs": sqd_sigs,
        "sqd_transactions": normalized_sqd,
        "missing_full": missing_full,
        "reference_response_sha256": sha256_bytes(raw),
        "coverage_state": state,
        "sqd_nonce_count_at_repair": nonce_count,
        "coverage_probe_query_sha256": probe_query_sha,
        "coverage_probe_response_sha256": probe_response_sha,
        "census_query_body_sha256": sha256_bytes(canonical_json(census_body)),
        "census_response_sha256": sha256_bytes(census_raw),
    }
    return payload, ledger_row


def _live_payloads(args, candidate_slots, reference_endpoints,
                   reference_fingerprint, *, pending, plan, coverage_states,
                   beta_slots):
    if args.transport_fixture:
        transport_factory = lambda _endpoint: RepairFixtureTransport(
            args.transport_fixture)
    else:
        transport_factory = RepairLiveTransport
    reference_pool = ReferenceEndpointPool(reference_endpoints, transport_factory)
    sqd_transport = transport_factory(reference_endpoints[0])
    header = _ledger_header(plan)
    completed, ledger = load_resume_slots(pending, header)
    workers = getattr(args, "workers", 1)

    def restored(slot):
        sqd_ev = _json(Path(pending) / "evidence" / f"{slot}.sqd.json")
        ref_ev = _json(Path(pending) / "evidence" / f"{slot}.ref.json")
        return _payload_from_evidence(sqd_ev, ref_ev)

    def persist(slot, result):
        payload, ledger_row = result
        ledger_row["seq"] = len(ledger)
        _persist_live_slot(pending, payload, args.mint, ledger_row)
        ledger.append(ledger_row)
        completed.add(slot)
        return payload

    if workers == 1:
        for slot in candidate_slots:
            if slot in completed:
                yield restored(slot)
                continue
            state = coverage_states.get(slot)
            if state is None:
                raise ValueError(f"candidate slot outside coverage interval: {slot}")
            try:
                result = _fetch_live_slot(
                    slot, state, beta_slots, reference_pool, sqd_transport,
                    reference_fingerprint)
            except QuotaStopped:
                raise QuotaStopped(slot, ledger=ledger, completed_slots=completed)
            yield persist(slot, result)
        return

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=workers)
    futures = {}
    submit_index = 0

    def fill_buffer():
        nonlocal submit_index
        limit = 4 * workers
        while submit_index < len(candidate_slots) and len(futures) < limit:
            slot = candidate_slots[submit_index]
            submit_index += 1
            if slot in completed:
                continue
            state = coverage_states.get(slot)
            if state is None:
                raise ValueError(f"candidate slot outside coverage interval: {slot}")
            futures[slot] = executor.submit(
                _fetch_live_slot, slot, state, beta_slots, reference_pool,
                sqd_transport, reference_fingerprint)

    try:
        fill_buffer()
        for slot in candidate_slots:
            if slot in completed:
                yield restored(slot)
            else:
                try:
                    result = futures.pop(slot).result()
                except QuotaStopped:
                    raise QuotaStopped(slot, ledger=ledger,
                                       completed_slots=completed)
                yield persist(slot, result)
            fill_buffer()
    finally:
        for future in futures.values():
            future.cancel()
        executor.shutdown(wait=True, cancel_futures=True)


def _cache_files(directory):
    directories = ([directory] if isinstance(directory, (str, Path))
                   else list(directory or []))
    paths = []
    for item in directories:
        for path in sorted(Path(item).iterdir()):
            if path.is_file() and (path.suffix == ".gz" or path.suffix == ".json"):
                try:
                    int(path.name.split(".", 1)[0])
                except ValueError:
                    continue
                paths.append(path)
    return sorted(paths, key=lambda path: (int(path.name.split(".", 1)[0]), str(path)))


def _cache_payloads(directories):
    """Load routeA caches and accept raw getBlock files as healthy canaries."""
    routea = {}
    for path in _cache_files(directories):
        try:
            payload = parse_routea_cache(path)
        except ValueError as route_error:
            opener = gzip.open if path.suffix == ".gz" else open
            try:
                with opener(path, "rt", encoding="utf-8") as handle:
                    raw = json.load(handle)
                block = raw.get("result") if isinstance(raw, dict) else None
                if not isinstance(block, dict) or not isinstance(
                        block.get("transactions"), list):
                    raise ValueError("not a raw getBlock response")
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError(f"unsupported blocks-cache file {path.name}: {route_error}") from exc
            continue
        slot = payload["slot"]
        prior = routea.get(slot)
        if prior is not None and json.dumps(
                prior, sort_keys=True, separators=(",", ":"), ensure_ascii=False) != json.dumps(
                    payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False):
            raise ValueError(f"conflicting routeA caches for slot {slot}")
        routea[slot] = payload
    return [routea[slot] for slot in sorted(routea)]


def _routea_slot(payload, mint):
    slot = payload["slot"]
    missing_by_sig = {item["sig"]: item for item in payload["missing_full"]}
    nonvote = set(payload["sqd_sigs"]) | set(missing_by_sig)
    ordered_nonvote = [signature for signature in payload["helius_sigs"]
                       if signature in nonvote]
    ordinal = {signature: index for index, signature in enumerate(ordered_nonvote)}
    if "sqd_transactions" in payload:
        sqd_transactions = sorted(payload["sqd_transactions"],
                                  key=lambda row: row["index"])
        if {row["signature"] for row in sqd_transactions} != set(payload["sqd_sigs"]):
            raise ValueError(f"SQD transaction rows/signature set mismatch at slot {slot}")
    else:
        # Frozen routeA/v0 caches predate explicit transactionIndex retention.
        # Their SQD list is a set; reconstruct its contiguous index in reference
        # non-vote order, matching the original routeA producer semantics.
        sqd_ordered = [signature for signature in ordered_nonvote
                       if signature in set(payload["sqd_sigs"])]
        sqd_transactions = [
            {"index": index, "signature": signature, "err": None}
            for index, signature in enumerate(sqd_ordered)
        ]
    if len({row["index"] for row in sqd_transactions}) != len(sqd_transactions) \
            or len({row["signature"] for row in sqd_transactions}) != len(sqd_transactions):
        raise ValueError(f"SQD transaction mapping is not unique at slot {slot}")
    triples = [[row["index"], ordinal[row["signature"]], row["signature"]]
               for row in sqd_transactions]
    layer = []
    for signature in ordered_nonvote:
        if signature not in missing_by_sig:
            continue
        item = missing_by_sig[signature]
        tx = item["tx"]
        edges = edges_for_transaction(
            tx, mint=mint, slot=slot, tx_index=ordinal[signature],
            block_time=payload["blockTime"])
        layer.append({
            "signature": signature, "slot": slot,
            "reference_position": item["pos"],
            "nonvote_ordinal": ordinal[signature],
            "nonce": bool(item.get("nonce")),
            "class": ("missing_block" if payload.get("sqd_blockhash") is None
                      else "nonce" if item.get("nonce") else "other"),
            "edges": [list(row) for row in sorted(edges, key=lambda row: (
                row[1], row[2], row[4], row[5], str(row[6])))],
            "evidence": {"sqd": f"evidence/{slot}.sqd.json",
                         "ref": f"evidence/{slot}.ref.json"},
        })
    transactions = []
    for position, signature in enumerate(payload["helius_sigs"]):
        missing = missing_by_sig.get(signature, {})
        transactions.append({
            "position": position, "signature": signature,
            "is_vote": signature not in nonvote,
            "is_nonce": bool(missing.get("nonce")),
            "err": (missing.get("tx", {}).get("meta", {}).get("err")
                    if missing else None),
        })
    sqd_evidence = {
        "slot": slot, "blockhash": payload.get("sqd_blockhash"),
        "parent_slot": payload.get("parentSlot", slot - 1),
        "transactions": sqd_transactions,
        "query_body_sha256": payload.get("census_query_body_sha256") or
        sha256_bytes(canonical_json({"slot": slot})),
        "response_sha256": payload.get("census_response_sha256") or
        sha256_bytes(canonical_json(sqd_transactions)),
        "coverage_state": payload.get("coverage_state", "DEFECT_CANDIDATE"),
        "sqd_nonce_count_at_repair": payload.get(
            "sqd_nonce_count_at_repair"),
        "coverage_probe_query_sha256": payload.get(
            "coverage_probe_query_sha256"),
        "coverage_probe_response_sha256": payload.get(
            "coverage_probe_response_sha256"),
    }
    def normalized_balances(tx, field):
        rows = []
        for balance in (tx.get("meta", {}).get(field) or []):
            if balance.get("mint") != mint:
                continue
            amount = (balance.get("uiTokenAmount") or {}).get("amount", 0)
            rows.append({
                "accountIndex": balance.get("accountIndex"), "mint": mint,
                "owner": balance.get("owner"),
                "amount": int(amount),
                "decimals": int((balance.get("uiTokenAmount") or {}).get(
                    "decimals", 0)),
            })
        return rows

    raw_digest = payload.get("reference_response_sha256") or hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False).encode("utf-8")).hexdigest()
    ref_evidence = {
        "slot": slot, "blockhash": payload["blockhash"],
        "parent_slot": payload.get("parentSlot", slot - 1),
        "block_time": payload["blockTime"], "transactions": transactions,
        "missing_detail": [
            {"signature": item["sig"], "account_keys_full": account_keys(item["tx"]),
             "pre_token_balances(mint)": normalized_balances(
                 item["tx"], "preTokenBalances"),
             "post_token_balances(mint)": normalized_balances(
                 item["tx"], "postTokenBalances")}
            for item in payload["missing_full"]
        ],
        "raw_response_sha256": raw_digest,
    }
    missing_nonce = sum(1 for item in payload["missing_full"] if item.get("nonce"))
    result = ("confirmed_missing_block" if payload.get("sqd_blockhash") is None
              else "confirmed_nonce_defect" if missing_nonce
              else "confirmed_other_defect" if payload["missing_full"] else "refuted")
    census = {
        "slot": slot, "state_in_map": "DEFECT_CANDIDATE", "result": result,
        "coverage_state": sqd_evidence["coverage_state"],
        "sqd_nonce_count_at_repair": sqd_evidence[
            "sqd_nonce_count_at_repair"],
        "sqd_tx_count": len(sqd_transactions),
        "sqd_blockhash": payload.get("sqd_blockhash"),
        "ref_tx_count": len(payload["helius_sigs"]),
        "ref_nonvote_count": len(ordered_nonvote),
        "ref_blockhash": payload["blockhash"],
        "missing_total": len(payload["missing_full"]),
        "missing_nonce": missing_nonce,
        "missing_err_excluded": sum(1 for item in payload["missing_full"]
                                    if item.get("failed")),
    }
    return census, layer, {
        "slot": slot, "blockhash": payload["blockhash"], "map": triples,
        "sqd_count": len(sqd_transactions), "ref_nonvote_count": len(ordered_nonvote),
    }, sqd_evidence, ref_evidence


def _produce_blocks(args):
    case_root = Path(args.case_root).resolve()
    if Path(args.case_root).is_symlink():
        raise ValueError("case-root symlink is forbidden")
    plan, base_info, coverage_info = _plan(
        case_root, args.mint, args.blocks_cache, args.reference_fingerprint,
        args.beta_slots)
    base_edge, base_meta, base = base_info
    _pointer, coverage, coverage_path, counts_path, coverage_checked = coverage_info
    from_slot = coverage["slot_counts"]["from_slot"]
    coverage_states = {
        from_slot + index: state for index, state in enumerate(
            coverage_checked["recomputed"]["states"])}
    parent, current_path, _lock = sqd_repair_paths(case_root, args.mint)
    parent.mkdir(parents=True, exist_ok=True)
    current = _json(current_path) if current_path.is_file() else None
    supersedes = current.get("gid") if isinstance(current, dict) else None
    if args.resume:
        recovered = resume_published_generation(parent, plan["plan_digest"])
        if recovered is not None:
            final, bundle = recovered
            checked = validate_repair_bundle_deep(
                final / "bundle.json", case_root=case_root,
                current_base={"edge_sha256": sha256_file(base_edge)})
            if not checked["ok"]:
                raise ValueError("resume generation deep validation failed: "
                                 + "; ".join(checked["reasons"]))
            action = "exploration-not-published"
            if bundle["mode"] == "formal":
                now_current = _json(current_path) if current_path.is_file() else None
                assert_resume_cas(bundle, now_current)
                bundle_ref = _file_ref(
                    final / "bundle.json",
                    str((final / "bundle.json").relative_to(case_root)))
                pointer = {
                    "schema": "sqd-solana-repair-pointer/v1",
                    "target": {"chain": "solana", "token": args.mint,
                               "as_of_block": base["finalized_upper_slot"]},
                    "mode": "formal", "verdict": "PASS", "exit_code": 0,
                    "producer": plan["producer"], "inputs": {"bundle": bundle_ref},
                    "gid": bundle["gid"], "supersedes": bundle["supersedes"],
                    "published_at": utc_now(),
                }
                expected = ({"gid": bundle["supersedes"]}
                            if bundle["supersedes"] is not None else None)
                action = publish_current_cas(
                    current_path, pointer, expected_current=expected,
                    bundle_path=final / "bundle.json", base_edge_path=base_edge)
            print(json.dumps({"status": action, "gid": bundle["gid"],
                              "plan_digest": plan["plan_digest"],
                              "repair_edges": bundle["repair_layer"]["edges"]},
                             sort_keys=True))
            return 0
    pending = parent / f"pending-{plan['plan_digest']}"
    if pending.exists() and not args.resume:
        raise ValueError("matching pending generation exists; use --resume")
    pending.mkdir(exist_ok=args.resume)
    guard_coverage_writes([pending])
    evidence_dir = pending / "evidence"
    evidence_dir.mkdir(exist_ok=True)
    beta_trace = getattr(args, "beta_trace", None)
    beta_trace_ref = None
    if beta_trace is not None and beta_trace.get("residual_owners"):
        beta_path = evidence_dir / "beta_trace.json"
        _publish_json_exclusive(beta_path, beta_trace)
        beta_trace_ref = _file_ref(beta_path, "evidence/beta_trace.json")

    census, layer, maps, evidence_manifest = [], [], [], []
    rpc_rows = []
    try:
        if args.blocks_cache:
            payloads = _cache_payloads(args.blocks_cache)
            for payload in payloads:
                state = coverage_states.get(payload["slot"])
                if state is None:
                    raise ValueError(
                        f"cache slot outside coverage interval: {payload['slot']}")
                payload["coverage_state"] = state
                payload["sqd_nonce_count_at_repair"] = None
                payload["coverage_probe_query_sha256"] = None
                payload["coverage_probe_response_sha256"] = None
        else:
            payloads = _live_payloads(
                args, plan["candidate_slots"], args.reference_endpoints,
                args.reference_fingerprint, pending=pending, plan=plan,
                coverage_states=coverage_states,
                beta_slots=set(plan["plan_candidates"]["beta"]))
        for payload in payloads:
            if payload.get("sqd_blockhash") not in (None, payload.get("blockhash")):
                raise ValueError(
                    f"reference/SQD blockhash mismatch at slot {payload['slot']}")
            census_row, layer_rows, map_row, sqd_ev, ref_ev = _routea_slot(
                payload, args.mint)
            sqd_path = evidence_dir / f"{payload['slot']}.sqd.json"
            ref_path = evidence_dir / f"{payload['slot']}.ref.json"
            _publish_json_exclusive(sqd_path, sqd_ev)
            _publish_json_exclusive(ref_path, ref_ev)
            sqd_ref = _file_ref(sqd_path, f"evidence/{sqd_path.name}")
            ref_ref = _file_ref(ref_path, f"evidence/{ref_path.name}")
            census_row["evidence"] = {"sqd": sqd_ref, "ref": ref_ref}
            census.append(census_row)
            layer.extend(layer_rows)
            maps.append(map_row)
            evidence_manifest.extend((sqd_ref, ref_ref))
    except QuotaStopped as exc:
        stopped = {"reason": "reference-quota", "cursor": exc.cursor,
                   "plan_digest": plan["plan_digest"],
                   "completed_slots": exc.completed_slots}
        publish_overwrite(pending / "STOPPED.json", stopped)
        _fsync_dir(pending)
        print(json.dumps(stopped, sort_keys=True), file=sys.stderr)
        return 3
    if beta_trace_ref is not None:
        evidence_manifest.append(beta_trace_ref)
    census.sort(key=lambda row: row["slot"])
    layer.sort(key=lambda row: row["signature"])
    maps.sort(key=lambda row: row["slot"])
    evidence_manifest.sort(key=lambda row: row["path"])
    candidate_slots = plan["candidate_slots"]
    census_slots = {row["slot"] for row in census}
    effective = ("INCONCLUSIVE" if not set(candidate_slots).issubset(census_slots)
                 else "DEFECTS_CONFIRMED" if any(
                     row["result"].startswith("confirmed_") for row in census)
                 else "NO_KNOWN_NONCE_OMISSION_DETECTED")
    resolution = {
        "schema": "sqd-solana-coverage-resolution/v1", "mint": args.mint,
        "plan_digest": plan["plan_digest"],
        "coverage": {"probe_id": coverage["probe_id"],
                     "map_sha256": sha256_file(coverage_path)},
        "plan_candidates": plan["plan_candidates"],
        "census": census, "effective_verdict": effective,
    }
    validate_resolution(resolution, candidate_slots, formal=False)
    if not should_publish_generation(resolution, layer, maps):
        print(json.dumps({"status": "refuted-only", "plan_digest": plan["plan_digest"]}))
        return 0
    repair_edges = [tuple(edge) for row in layer for edge in row["edges"]]
    slot_maps = {row["slot"]: row["map"] for row in maps}
    merged_rows = merge_edges(read_edge_file(base_edge), repair_edges, slot_maps)
    logical_sha, logical_rows = edge_logical_evidence(merged_rows)
    key = hashlib.sha256(args.mint.encode()).hexdigest()
    merged_edge_name = f"soltx-{key}.repaired.jsonl.gz"
    merged_meta_name = f"soltx-{key}.repaired.meta.json"
    merged_edge_path = pending / merged_edge_name
    _publish_bytes_exclusive(merged_edge_path, _gzip_jsonl(merged_rows))
    merged_meta = dict(base)
    merged_meta.update({
        "schema": CACHE_SCHEMA, "collector": COLLECTOR_ID,
        "collector_sha256": sha256_file(__file__),
        "edge_logical_sha256": logical_sha, "edge_rows": logical_rows,
        "edge_file_size": merged_edge_path.stat().st_size,
        "edge_file_sha256": sha256_file(merged_edge_path),
        "plan_digest": plan["plan_digest"],
        "base_meta_sha256": sha256_file(base_meta),
        "base_edge_sha256": sha256_file(base_edge),
        "repair": {"slots_confirmed": sum(
            row["result"].startswith("confirmed_") for row in census),
            "slots_remapped": len(maps), "edges_added": len(repair_edges)},
    })
    merged_meta.pop("gid", None)
    merged_meta.pop("bundle_sha256", None)
    _publish_json_exclusive(pending / merged_meta_name, merged_meta)
    _publish_json_exclusive(pending / "coverage_resolution.json", resolution)
    layer_header = {
        "schema": "sqd-solana-repair-layer/v1", "mint": args.mint,
        "plan_digest": plan["plan_digest"],
        "base": plan["base"], "coverage": plan["coverage"],
        "reference": {"kind": plan["reference"]["kind"],
                      "endpoint_fingerprint": plan["reference"]["endpoint_fingerprint"]},
        "producer": plan["producer"],
    }
    _publish_bytes_exclusive(pending / "repair_layer.jsonl",
                             _jsonl_bytes([layer_header, *layer]))
    map_header = {"schema": "sqd-solana-slot-index-map/v1", "mint": args.mint,
                  "plan_digest": plan["plan_digest"]}
    _publish_bytes_exclusive(pending / "slot_index_map.jsonl",
                             _jsonl_bytes([map_header, *maps]))
    _publish_json_exclusive(pending / "evidence_manifest.json", evidence_manifest)
    ledger_header = _ledger_header(plan)
    ledger_path = pending / "rpc_ledger.jsonl"
    if not ledger_path.is_file():
        _publish_bytes_exclusive(ledger_path,
                                 _jsonl_bytes([ledger_header, *rpc_rows]))
    complete_rows = _read_ledger_prefix(ledger_path)
    if not complete_rows or complete_rows[0] != ledger_header:
        raise ValueError("RPC ledger header differs from plan")
    rpc_rows = complete_rows[1:]
    stopped_path = pending / "STOPPED.json"
    if stopped_path.is_file():
        stopped_path.unlink()
        _fsync_dir(pending)
    gid_material = {
        "plan_digest": plan["plan_digest"], "kind": "repair",
        "supersedes": supersedes, "census": census, "transactions": layer,
        "slot_index_map": maps, "evidence_manifest": evidence_manifest,
        "mode": plan["mode"], "reference": {"source": plan["reference"]["source"]},
    }
    gid = compute_gid(gid_material)
    refs = {
        "coverage_resolution": _file_ref(pending / "coverage_resolution.json",
                                         "coverage_resolution.json"),
        "repair_layer": {**_file_ref(pending / "repair_layer.jsonl",
                                     "repair_layer.jsonl"),
                         "transactions": len(layer), "edges": len(repair_edges)},
        "slot_index_map": {**_file_ref(pending / "slot_index_map.jsonl",
                                       "slot_index_map.jsonl"), "slots": len(maps)},
        "evidence_manifest": _file_ref(pending / "evidence_manifest.json",
                                       "evidence_manifest.json"),
        "rpc_ledger": {**_file_ref(ledger_path, "rpc_ledger.jsonl"),
                       "requests": len(rpc_rows),
                       "credits_estimate": sum(row["credits_estimate"]
                                               for row in rpc_rows)},
    }
    bundle = {
        "schema": "sqd-solana-repair-bundle/v1", "mint": args.mint,
        "plan_digest": plan["plan_digest"], "gid": gid, "kind": "repair",
        "mode": plan["mode"], "producer": plan["producer"],
        "base": {"edge_file": str(base_edge.relative_to(case_root)),
                 "meta_file": str(base_meta.relative_to(case_root)),
                 "edge_sha256": sha256_file(base_edge),
                 "meta_sha256": sha256_file(base_meta),
                 "edge_logical_sha256": base["edge_logical_sha256"],
                 "edge_rows": base["edge_rows"],
                 "finalized_upper_slot": base["finalized_upper_slot"]},
        "coverage": {"probe_id": coverage["probe_id"],
                     "map": _file_ref(coverage_path,
                                      str(coverage_path.relative_to(case_root))),
                     "slot_counts": _file_ref(counts_path,
                                              str(counts_path.relative_to(case_root)))},
        **refs,
        "merged": {"edge_file": merged_edge_name, "meta_file": merged_meta_name,
                   "edge_sha256": sha256_file(merged_edge_path),
                   "meta_sha256": sha256_file(pending / merged_meta_name),
                   "edge_logical_sha256": logical_sha, "edge_rows": logical_rows},
        "reference": plan["reference"], "supersedes": supersedes,
        "generated_at": _pointer.get("published_at"),
    }
    _publish_json_exclusive(pending / "bundle.json", bundle)
    _fsync_dir(pending)
    final = parent / f"gen-{gid}"
    if final.is_dir():
        existing = _json(final / "bundle.json")
        if existing.get("gid") != gid or existing.get("plan_digest") != plan["plan_digest"]:
            raise ValueError("existing generation collides with computed gid")
        # Crash recovery: the immutable generation wins; pending remains ignored.
    else:
        publish_generation_exclusive(pending, final)
    current_base = {"edge_sha256": sha256_file(base_edge)}
    checked = validate_repair_bundle_deep(
        final / "bundle.json", case_root=case_root, current_base=current_base)
    if not checked["ok"]:
        raise ValueError("post-publish deep validation failed: " + "; ".join(checked["reasons"]))
    action = "exploration-not-published"
    if plan["mode"] == "formal":
        bundle_ref = _file_ref(final / "bundle.json",
                               str((final / "bundle.json").relative_to(case_root)))
        pointer = {
            "schema": "sqd-solana-repair-pointer/v1",
            "target": {"chain": "solana", "token": args.mint,
                       "as_of_block": base["finalized_upper_slot"]},
            "mode": "formal", "verdict": "PASS", "exit_code": 0,
            "producer": plan["producer"], "inputs": {"bundle": bundle_ref},
            "gid": gid, "supersedes": supersedes, "published_at": utc_now(),
        }
        action = publish_current_cas(
            current_path, pointer, expected_current=current,
            bundle_path=final / "bundle.json", base_edge_path=base_edge)
    print(json.dumps({"status": action, "gid": gid,
                      "plan_digest": plan["plan_digest"],
                      "repair_edges": len(repair_edges)}, sort_keys=True))
    return 0


def _verify(args):
    case_root = Path(args.case_root).resolve()
    parent, _current, _lock = sqd_repair_paths(case_root, args.mint)
    base_edge, _base_meta, _base = _base(case_root, args.mint)
    endpoints = []
    canary_fetch = None
    if args.live_canary:
        if args.transport_fixture:
            endpoint = "fixture://helius"
            transport = RepairFixtureTransport(args.transport_fixture)
        else:
            resolved = load_reference_endpoints(
                args.reference_rpc, args.reference_keys_file)
            endpoints.extend(resolved)
            endpoint = resolved[0]
            transport = RepairLiveTransport(endpoint)

        def canary_fetch(slot):
            result = transport.call("reference-getBlock", _rpc_body(slot))
            block, error = _result_value(result)
            if error is not None or not isinstance(block, dict):
                status = ((result.error or {}).get("http_status")
                          if isinstance(result.error, dict) else None)
                raise ValueError(
                    f"reference getBlock failed at slot {slot}; status={status}")
            return block

    result = validate_repair_bundle_deep(
        parent / f"gen-{args.gid}" / "bundle.json", case_root=case_root,
        current_base={"edge_sha256": sha256_file(base_edge)},
        live_canary=args.live_canary, live_canary_fetch=canary_fetch)
    if not result["ok"]:
        print(redact_endpoint_text(json.dumps(result, sort_keys=True), endpoints),
              file=sys.stderr)
        return 2
    print(json.dumps({"status": "PASS", "gid": args.gid}, sort_keys=True))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "repair"):
        item = sub.add_parser(name)
        item.add_argument("--mint", required=True)
        item.add_argument("--case-root", required=True)
        item.add_argument("--blocks-cache", action="append")
        item.add_argument("--reference-rpc")
        item.add_argument("--reference-keys-file")
        item.add_argument("--workers", type=int, default=1)
        item.add_argument("--transport-fixture", help=argparse.SUPPRESS)
        item.add_argument("--residual-owners")
        item.add_argument("--beta", action="store_true")
        item.add_argument("--beta-rounds", type=int, default=1)
        item.add_argument("--resume", action="store_true")
    verify = sub.add_parser("verify")
    verify.add_argument("gid")
    verify.add_argument("--mint", required=True)
    verify.add_argument("--case-root", required=True)
    verify.add_argument("--live-canary", type=int, default=0)
    verify.add_argument("--reference-rpc")
    verify.add_argument("--reference-keys-file")
    verify.add_argument("--transport-fixture", help=argparse.SUPPRESS)
    return parser


def _repair_publish_txn(args):
    """Named multi-file transaction boundary used by the formal invariant scan."""
    return _produce_blocks(args)


def publish_error_receipt(args, message):
    """Publish a unique secret-safe ERROR side receipt without touching CURRENT."""
    if not getattr(args, "case_root", None) or not getattr(args, "mint", None):
        return None
    parent, _current, _lock = sqd_repair_paths(
        Path(args.case_root).resolve(), args.mint)
    parent.mkdir(parents=True, exist_ok=True)
    stamp = int(time.time_ns())
    name = sha256_bytes(canonical_json({"mint": args.mint, "stamp": stamp,
                                       "message": str(message)}))[:16]
    path = parent / f"ERROR-{name}.json"
    publish_exclusive(path, {
        "format": "sqd-gap-repair-error/v1", "mint": args.mint,
        "verdict": "ERROR", "exit_code": 2, "message": str(message),
        "published_at": utc_now(),
    })
    _fsync_dir(parent)
    return path


def main(argv=None):
    args = build_parser().parse_args(argv)
    endpoints = []
    try:
        if args.command == "verify":
            return _verify(args)
        case_root = Path(args.case_root).resolve()
        args.reference_endpoint = None
        args.reference_endpoints = []
        args.reference_fingerprint = None
        args.beta_trace = None
        args.beta_slots = []
        if args.beta_rounds < 1 or args.beta_rounds > 3:
            raise ValueError("beta rounds must be within 1..3")
        if args.residual_owners and not args.beta:
            raise ValueError("--residual-owners requires --beta")
        if args.workers < 1:
            raise ValueError("workers must be a positive integer")
        if not args.blocks_cache:
            if args.transport_fixture:
                args.reference_endpoints = ["fixture://helius"]
            else:
                args.reference_endpoints = load_reference_endpoints(
                    args.reference_rpc, args.reference_keys_file)
            args.reference_endpoint = args.reference_endpoints[0]
            endpoints.extend(args.reference_endpoints)
            args.reference_fingerprint = reference_endpoint_identity(
                args.reference_endpoint)["sha256"]
        if args.beta:
            beta_transport = (RepairFixtureTransport(args.transport_fixture)
                              if args.transport_fixture else RepairLiveTransport(
                                  args.reference_endpoint))
            base_edge, _base_meta, _base_value = _base(case_root, args.mint)
            args.beta_trace = run_beta_search(
                args, case_root, read_edge_file(base_edge), beta_transport)
            args.beta_slots = args.beta_trace["candidate_slots"]
        plan, _base_info, _coverage_info = _plan(
            case_root, args.mint, args.blocks_cache, args.reference_fingerprint,
            args.beta_slots)
        if args.command == "plan":
            output = {**plan, "estimated_slots": len(plan["candidate_slots"]),
                              "estimated_requests": len(plan["candidate_slots"]) * 2,
                              "estimated_credits": len(plan["candidate_slots"]) * 10}
            if args.beta_trace is not None:
                output["beta_trace"] = args.beta_trace
            print(json.dumps(output, sort_keys=True))
            return 0
        return _repair_publish_txn(args)
    except Exception as exc:
        safe = redact_endpoint_text(f"sqd gap repair failed: {exc}", endpoints)
        try:
            publish_error_receipt(args, safe)
        except Exception:
            pass
        print(safe, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
