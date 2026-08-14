#!/usr/bin/env python3
"""Attested, observation-led Solana token snapshot protocol.

The canonical snapshot slot is returned by ``getProgramAccounts``.  Caller
slots are assertions or lower bounds only; they never manufacture an observed
slot.  Every business request is issued through ``SolanaAttestedSession``.
"""
from __future__ import annotations

import base64
import hashlib
import json
import time
from pathlib import Path

from endpoint_identity import endpoint_fingerprint
from receipt_kernel import build_envelope, finalize_envelope
from receipt_validate import validate_receipt
from solana_attested_session import (SOLANA_MAINNET_GENESIS_HASH,
                                     SolanaAttestedSession)


BUNDLE_SCHEMA = "solana-observation-bundle/v1"
MAX_WINDOW_SLOTS = 512
MAX_ATTEMPTS = 3
COMPLETE_SIGNATURE_LIMIT = 200
SIGNATURE_PAGE_LIMIT = 1000
COMPLETE_RPC_LIMIT = 250
ACTIVITY_DEADLINE_SECONDS = 120
LIGHT_SAMPLE_LIMIT = 50


class SolanaObservationError(ValueError):
    pass


class RetryableObservationError(SolanaObservationError):
    pass


def canonical_json_bytes(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def canonical_json_sha256(value) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def assert_declared_slot(declared, observed, flag="--as-of-slot"):
    if declared is None:
        return
    if isinstance(declared, bool) or not isinstance(declared, int) or declared < 0:
        raise ValueError(f"{flag} must be a non-negative integer")
    if declared != observed:
        raise ValueError(
            f"{flag} assertion mismatch: declared={declared}, observed={observed}")


def _slot_context(result, method):
    if not isinstance(result, dict):
        raise SolanaObservationError(f"{method} result must be an object")
    context = result.get("context")
    slot = context.get("slot") if isinstance(context, dict) else None
    if isinstance(slot, bool) or not isinstance(slot, int) or slot < 0:
        raise SolanaObservationError(f"{method} result.context.slot missing or invalid")
    return slot


def _account_value(result, method):
    slot = _slot_context(result, method)
    value = result.get("value")
    if not isinstance(value, dict):
        raise SolanaObservationError(f"{method} mint account missing")
    return slot, value


def _decode_base64_account(value, method):
    data = value.get("data")
    if (not isinstance(data, list) or len(data) < 2 or data[1] != "base64"
            or not isinstance(data[0], str)):
        raise SolanaObservationError(f"{method} did not return raw base64 account data")
    try:
        return base64.b64decode(data[0], validate=True)
    except Exception as exc:
        raise SolanaObservationError(f"{method} base64 account data invalid: {exc}") from exc


def parse_mint_supply(raw: bytes) -> tuple[int, int]:
    """Parse the common SPL/Token-2022 mint base layout."""
    if not isinstance(raw, bytes) or len(raw) < 46:
        raise SolanaObservationError("mint raw account is shorter than the 46-byte base layout")
    if raw[45] not in (0, 1):
        raise SolanaObservationError("mint initialized flag is invalid")
    return int.from_bytes(raw[36:44], "little"), int(raw[44])


def _parsed_mint(value):
    data = value.get("data")
    if not isinstance(data, dict):
        raise SolanaObservationError("jsonParsed mint data is not an object")
    parsed = data.get("parsed")
    info = parsed.get("info") if isinstance(parsed, dict) else None
    if not isinstance(parsed, dict) or parsed.get("type") != "mint" or not isinstance(info, dict):
        raise SolanaObservationError("jsonParsed account is not a mint")
    return parsed, info


def _account_keys_and_writable(transaction):
    tx = transaction.get("transaction") if isinstance(transaction, dict) else None
    message = tx.get("message") if isinstance(tx, dict) else None
    if not isinstance(message, dict):
        raise SolanaObservationError("transaction message missing")
    raw_keys = message.get("accountKeys")
    if not isinstance(raw_keys, list):
        raise SolanaObservationError("transaction accountKeys missing")

    keys = []
    explicit = []
    for item in raw_keys:
        if isinstance(item, str):
            keys.append(item)
            explicit.append(None)
        elif isinstance(item, dict) and isinstance(item.get("pubkey"), str):
            keys.append(item["pubkey"])
            explicit.append(item.get("writable") if isinstance(item.get("writable"), bool)
                            else None)
        else:
            raise SolanaObservationError("transaction accountKeys entry invalid")

    header = message.get("header")
    if not isinstance(header, dict):
        header = {}
    required = header.get("numRequiredSignatures")
    ro_signed = header.get("numReadonlySignedAccounts")
    ro_unsigned = header.get("numReadonlyUnsignedAccounts")
    if not all(isinstance(item, int) and not isinstance(item, bool) and item >= 0
               for item in (required, ro_signed, ro_unsigned)):
        if not all(item is not None for item in explicit):
            raise SolanaObservationError("transaction header writable metadata missing")
        writable = [bool(item) for item in explicit]
    else:
        if required > len(keys) or ro_signed > required or ro_unsigned > len(keys) - required:
            raise SolanaObservationError("transaction header readonly counts invalid")
        signed_writable_end = required - ro_signed
        unsigned_writable_end = len(keys) - ro_unsigned
        writable = []
        for index in range(len(keys)):
            derived = (index < signed_writable_end if index < required
                       else index < unsigned_writable_end)
            # Header-derived writability is authoritative for the static key
            # layout.  Parsed per-key flags may only make the result stricter.
            writable.append(derived or explicit[index] is True)

    meta = transaction.get("meta") if isinstance(transaction, dict) else None
    loaded = meta.get("loadedAddresses") if isinstance(meta, dict) else None
    lookups = message.get("addressTableLookups")
    if lookups is not None and not isinstance(lookups, list):
        raise SolanaObservationError("transaction addressTableLookups invalid")
    if lookups and not isinstance(loaded, dict):
        raise SolanaObservationError(
            "transaction loadedAddresses missing for addressTableLookups")
    if isinstance(loaded, dict):
        for item in loaded.get("writable") or []:
            if not isinstance(item, str):
                raise SolanaObservationError("loaded writable address invalid")
            keys.append(item); writable.append(True)
        for item in loaded.get("readonly") or []:
            if not isinstance(item, str):
                raise SolanaObservationError("loaded readonly address invalid")
            keys.append(item); writable.append(False)
    return keys, writable


def mint_is_writable(transaction, mint: str) -> bool:
    keys, writable = _account_keys_and_writable(transaction)
    return any(key == mint and writable[index] for index, key in enumerate(keys))


def _activity_validation(session, mint, pre_slot, post_slot, *, deadline_seconds):
    started = time.monotonic()
    rpc_calls = 0
    references = []
    before = None
    complete = False
    pagination_error = None
    budget_limited = False
    time_limited = False
    signature_pages = 0
    while len(references) <= COMPLETE_SIGNATURE_LIMIT:
        if time.monotonic() - started > deadline_seconds:
            time_limited = True
            break
        if rpc_calls >= COMPLETE_RPC_LIMIT:
            budget_limited = True
            break
        config = {"commitment": "finalized", "limit": SIGNATURE_PAGE_LIMIT}
        if before:
            config["before"] = before
        try:
            page = session.call("getSignaturesForAddress", [mint, config])
            rpc_calls += 1
            signature_pages += 1
        except Exception as exc:
            pagination_error = str(exc)
            break
        if not isinstance(page, list):
            pagination_error = "getSignaturesForAddress result is not a list"
            break
        if not page:
            complete = True
            break
        boundary_seen = False
        for row in page:
            if not isinstance(row, dict) or not isinstance(row.get("signature"), str) \
                    or isinstance(row.get("slot"), bool) or not isinstance(row.get("slot"), int):
                pagination_error = "signature page contains malformed entry"
                break
            slot = row["slot"]
            if slot < pre_slot:
                boundary_seen = True
                break
            if slot <= post_slot:
                references.append(row)
        if pagination_error:
            break
        if boundary_seen or len(page) < SIGNATURE_PAGE_LIMIT:
            complete = True
            break
        before = page[-1]["signature"]

    elapsed = time.monotonic() - started
    successful_reference_count = sum(row.get("err") is None for row in references)
    complete_cost_exceeds_budget = (
        rpc_calls + successful_reference_count > COMPLETE_RPC_LIMIT)
    high_activity = (len(references) > COMPLETE_SIGNATURE_LIMIT
                     or budget_limited or time_limited
                     or complete_cost_exceeds_budget
                     or elapsed > deadline_seconds)
    if pagination_error and not high_activity:
        raise RetryableObservationError(
            f"complete activity pagination incomplete: {pagination_error}")
    # Every non-complete exit above records either pagination_error or one of
    # the high-activity budget flags; there is no third reachable state.

    mode = "lightweight" if high_activity else "complete"
    candidates = references[:LIGHT_SAMPLE_LIMIT] if mode == "lightweight" else references
    successful = [row for row in candidates if row.get("err") is None]
    checked = 0
    unavailable = 0
    writable_hits = []
    for row in successful:
        if mode == "complete" and (rpc_calls >= COMPLETE_RPC_LIMIT
                                    or time.monotonic() - started > deadline_seconds):
            mode = "lightweight"
            successful = successful[:LIGHT_SAMPLE_LIMIT]
            checked = min(checked, LIGHT_SAMPLE_LIMIT)
            break
        try:
            tx = session.call("getTransaction", [row["signature"], {
                "commitment": "finalized", "encoding": "jsonParsed",
                "maxSupportedTransactionVersion": 0,
            }])
            rpc_calls += 1
        except Exception as exc:
            if mode == "complete":
                raise RetryableObservationError(
                    f"complete activity transaction scan incomplete: {exc}") from exc
            unavailable += 1
            continue
        if tx is None:
            if mode == "complete":
                raise RetryableObservationError(
                    "complete activity transaction scan incomplete: transaction unavailable")
            unavailable += 1
            continue
        meta = tx.get("meta") if isinstance(tx, dict) else None
        if isinstance(meta, dict) and meta.get("err") is not None:
            continue
        checked += 1
        if mint_is_writable(tx, mint):
            writable_hits.append(row["signature"])
    if writable_hits:
        raise RetryableObservationError(
            f"mint writable mutation reference observed: {writable_hits[0]}")

    elapsed = time.monotonic() - started
    is_complete = mode == "complete" and complete and unavailable == 0 \
        and len(references) <= COMPLETE_SIGNATURE_LIMIT
    return {
        "mode": mode,
        "window": {"from_slot": pre_slot, "to_slot": post_slot},
        "referenced_signatures": len(references),
        "successful_references": successful_reference_count,
        "sample_size": checked,
        "unavailable_transactions": unavailable,
        "complete": is_complete,
        "pagination_complete": complete,
        "pagination_error": pagination_error,
        "signature_pages": signature_pages,
        "limits": {"complete_signature_limit": COMPLETE_SIGNATURE_LIMIT,
                   "signature_page_limit": SIGNATURE_PAGE_LIMIT,
                   "complete_rpc_limit": COMPLETE_RPC_LIMIT,
                   "deadline_seconds": deadline_seconds,
                   "light_sample_limit": LIGHT_SAMPLE_LIMIT},
        "writable_hits": writable_hits,
        "rpc_calls": rpc_calls,
        "elapsed_seconds": round(elapsed, 6),
        "coverage_statement": (
            "zero referenced signatures were returned for the observed window; "
            "no transaction writable checks were performed"
            if is_complete and not references else
            "all successful referenced transactions in the observed window were parsed; "
            "the mint was never writable" if is_complete else
            "adaptive sample only; this does not prove absence of intermediate mint state changes"
        ),
        "signature_set_sha256": canonical_json_sha256([
            {"signature": row["signature"], "slot": row["slot"], "err": row.get("err")}
            for row in references
        ]),
    }


def measure_mint_activity(session, mint, from_slot, to_slot, *,
                          deadline_seconds=ACTIVITY_DEADLINE_SECONDS):
    """Public preflight entry using the exact production adaptive validator."""
    if not isinstance(session, SolanaAttestedSession):
        raise TypeError("activity measurement requires SolanaAttestedSession")
    if (not isinstance(from_slot, int) or isinstance(from_slot, bool)
            or not isinstance(to_slot, int) or isinstance(to_slot, bool)
            or from_slot < 0 or from_slot > to_slot):
        raise ValueError("activity window must satisfy 0 <= from_slot <= to_slot")
    return _activity_validation(
        session, mint, from_slot, to_slot, deadline_seconds=deadline_seconds)


def _normalized_gpa_accounts(result):
    slot = _slot_context(result, "getProgramAccounts")
    values = result.get("value")
    if not isinstance(values, list):
        raise SolanaObservationError("getProgramAccounts value must be a list")
    normalized = []
    seen = set()
    for item in values:
        if not isinstance(item, dict) or not isinstance(item.get("pubkey"), str):
            raise SolanaObservationError("getProgramAccounts entry invalid")
        pubkey = item["pubkey"]
        if pubkey in seen:
            raise SolanaObservationError(f"duplicate token account in GPA: {pubkey}")
        seen.add(pubkey)
        account = item.get("account")
        if not isinstance(account, dict):
            raise SolanaObservationError("getProgramAccounts account payload invalid")
        raw = _decode_base64_account(account, "getProgramAccounts")
        if len(raw) < 40:
            raise SolanaObservationError("GPA dataSlice account shorter than 40 bytes")
        normalized.append({"pubkey": pubkey, "data_base64": base64.b64encode(raw).decode()})
    normalized.sort(key=lambda item: item["pubkey"])
    return slot, normalized


def _observe_once(session, mint, program, min_context_slot, deadline_seconds):
    pre_raw_result = session.call("getAccountInfo", [mint, {
        "commitment": "finalized", "encoding": "base64",
        "minContextSlot": min_context_slot,
    }])
    pre_slot, pre_value = _account_value(pre_raw_result, "getAccountInfo(raw pre)")
    if pre_slot < min_context_slot:
        raise SolanaObservationError(
            f"getAccountInfo(raw pre) slot {pre_slot} is below min_context_slot "
            f"{min_context_slot}")
    if pre_value.get("owner") != program:
        raise SolanaObservationError(
            f"mint owner mismatch: expected {program}, observed {pre_value.get('owner')}")
    pre_raw = _decode_base64_account(pre_value, "getAccountInfo(raw pre)")
    mint_supply, mint_decimals = parse_mint_supply(pre_raw)

    parsed_result = session.call("getAccountInfo", [mint, {
        "commitment": "finalized", "encoding": "jsonParsed",
        "minContextSlot": pre_slot,
    }])
    parsed_slot, parsed_value = _account_value(parsed_result, "getAccountInfo(jsonParsed)")
    if parsed_slot < pre_slot:
        raise SolanaObservationError(
            "getAccountInfo(jsonParsed) context slot is below the raw pre-observation")
    if parsed_value.get("owner") != program:
        raise SolanaObservationError("jsonParsed mint owner does not match raw observation")
    parsed, info = _parsed_mint(parsed_value)
    if int(str(info.get("supply"))) != mint_supply or int(info.get("decimals")) != mint_decimals:
        raise SolanaObservationError("raw/jsonParsed mint supply or decimals mismatch")

    filters = [{"memcmp": {"offset": 0, "bytes": mint}}]
    gpa_result = session.call("getProgramAccounts", [program, {
        "commitment": "finalized", "encoding": "base64",
        "dataSlice": {"offset": 32, "length": 40},
        "filters": filters, "withContext": True, "minContextSlot": parsed_slot,
    }])
    snapshot_slot, accounts = _normalized_gpa_accounts(gpa_result)
    if snapshot_slot < parsed_slot:
        raise SolanaObservationError(
            "GPA context slot is below the jsonParsed minContextSlot floor")

    post_result = session.call("getAccountInfo", [mint, {
        "commitment": "finalized", "encoding": "base64",
        "minContextSlot": snapshot_slot,
    }])
    post_slot, post_value = _account_value(post_result, "getAccountInfo(raw post)")
    if post_value.get("owner") != program:
        raise SolanaObservationError("post-observation mint owner mismatch")
    post_raw = _decode_base64_account(post_value, "getAccountInfo(raw post)")
    if post_slot < snapshot_slot:
        raise SolanaObservationError("post-observation slot is below the snapshot slot")
    if post_slot - pre_slot > MAX_WINDOW_SLOTS:
        raise RetryableObservationError(
            f"observation window too wide: {post_slot - pre_slot} > {MAX_WINDOW_SLOTS}")
    if pre_raw != post_raw:
        raise RetryableObservationError("mint raw account changed across observation window")

    activity = _activity_validation(
        session, mint, pre_slot, post_slot, deadline_seconds=deadline_seconds)

    supply_result = session.call("getTokenSupply", [mint, {"commitment": "finalized"}])
    supply_slot = _slot_context(supply_result, "getTokenSupply")
    value = supply_result.get("value")
    if not isinstance(value, dict):
        raise SolanaObservationError("getTokenSupply value missing")
    supply_amount = int(str(value.get("amount")))
    supply_decimals = int(value.get("decimals"))
    if supply_slot < snapshot_slot:
        # getTokenSupply does not support minContextSlot; a lagging failover
        # endpoint is therefore a retryable observation race, not a hard shape error.
        raise RetryableObservationError(
            f"getTokenSupply context slot {supply_slot} is before snapshot {snapshot_slot}")

    account_total = 0
    for account in accounts:
        raw = base64.b64decode(account["data_base64"])
        account_total += int.from_bytes(raw[32:40], "little")
    closed = (account_total == mint_supply == supply_amount
              and mint_decimals == supply_decimals)
    if not closed:
        raise SolanaObservationError(
            "three-way supply closure failed: "
            f"gpa={account_total}, mint_raw={mint_supply}, token_supply={supply_amount}, "
            f"mint_decimals={mint_decimals}, supply_decimals={supply_decimals}")

    raw_hash = sha256_bytes(pre_raw)
    return {
        "schema": "solana-observation-core/v1",
        "canonical_target": {"chain": "solana", "token": mint.lower(),
                             "as_of_block": snapshot_slot},
        "attestation": {
            "expected_genesis": SOLANA_MAINNET_GENESIS_HASH,
            "observed_genesis": session.observed_genesis,
            "endpoint": endpoint_fingerprint(session.endpoint),
        },
        "mint": mint,
        "program": program,
        "mint_pre": {"slot": pre_slot, "raw_sha256": raw_hash,
                     "json_parsed_slot": parsed_slot, "json_parsed": parsed},
        "snapshot": {"slot": snapshot_slot, "account_count": len(accounts),
                     "accounts_sha256": canonical_json_sha256(accounts)},
        "mint_post": {"slot": post_slot, "raw_sha256": sha256_bytes(post_raw)},
        "activity": activity,
        "supply": {"slot": supply_slot, "amount": str(supply_amount),
                   "decimals": supply_decimals,
                   "semantics": "cross-check observation only; not the freeze point"},
        "closure": {"gpa_amount": str(account_total),
                    "mint_raw_amount": str(mint_supply),
                    "token_supply_amount": str(supply_amount), "closed": True},
        "input_hashes": {
            "pre_raw": raw_hash,
            "json_parsed": canonical_json_sha256(parsed_result),
            "gpa": canonical_json_sha256(gpa_result),
            "post_raw": sha256_bytes(post_raw),
            "token_supply": canonical_json_sha256(supply_result),
        },
    }, accounts


def observe_snapshot(session, mint, program, *, min_context_slot=0,
                     max_attempts=MAX_ATTEMPTS,
                     activity_deadline_seconds=ACTIVITY_DEADLINE_SECONDS):
    if not isinstance(session, SolanaAttestedSession):
        raise TypeError("Solana observation requires SolanaAttestedSession")
    if not isinstance(mint, str) or not mint.strip():
        raise ValueError("mint must be a non-empty string")
    if not isinstance(program, str) or not program.strip():
        raise ValueError("program must be a non-empty string")
    if isinstance(min_context_slot, bool) or not isinstance(min_context_slot, int) \
            or min_context_slot < 0:
        raise ValueError("min_context_slot must be a non-negative integer")
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) \
            or not 1 <= max_attempts <= MAX_ATTEMPTS:
        raise ValueError(f"max_attempts must be in 1..{MAX_ATTEMPTS}")
    failures = []
    for attempt in range(1, max_attempts + 1):
        try:
            core, accounts = _observe_once(
                session, mint.strip(), program.strip(), min_context_slot,
                activity_deadline_seconds)
            core["attempt"] = attempt
            return core, accounts
        except RetryableObservationError as exc:
            failures.append(str(exc))
    raise SolanaObservationError(
        f"observation retries exhausted after {max_attempts} attempts: "
        + " | ".join(failures))


def build_observation_bundle(core, producer_file, *, inputs=None, mode="formal", **extra):
    if not isinstance(core, dict) or core.get("schema") != "solana-observation-core/v1":
        raise ValueError("observation core schema invalid")
    target = core.get("canonical_target")
    envelope = build_envelope(BUNDLE_SCHEMA, target, producer_file, mode, inputs=inputs)
    fields = {key: value for key, value in core.items()
              if key not in {"schema", "canonical_target"}}
    conflicts = sorted(set(fields).intersection(extra))
    if conflicts:
        raise ValueError(f"observation bundle extra fields conflict: {conflicts}")
    fields.update(extra)
    return finalize_envelope(envelope, "PASS", 0, **fields)


def validate_observation_bundle(bundle, *, bundle_path=None, expected_mint=None,
                                expected_producer="scripts/solana/scan_token_accounts.py"):
    if not isinstance(bundle, dict) or bundle.get("schema") != BUNDLE_SCHEMA:
        raise ValueError("observation bundle schema invalid")
    errors = validate_receipt(bundle)
    if errors:
        raise ValueError(f"observation bundle envelope invalid: {errors[0]}")
    if bundle.get("verdict") != "PASS" or bundle.get("exit_code") != 0 \
            or bundle.get("mode") != "formal":
        raise ValueError("formal observation bundle must be PASS/0")
    producer = bundle.get("producer") or {}
    if producer.get("path") != expected_producer:
        raise ValueError("observation bundle producer binding invalid")
    target = bundle.get("target") or {}
    if expected_mint is not None and target.get("token") != expected_mint.lower():
        raise ValueError("observation bundle mint target mismatch")
    snapshot = bundle.get("snapshot") or {}
    pre = bundle.get("mint_pre") or {}
    post = bundle.get("mint_post") or {}
    supply = bundle.get("supply") or {}
    closure = bundle.get("closure") or {}
    attestation = bundle.get("attestation") or {}
    if snapshot.get("slot") != target.get("as_of_block"):
        raise ValueError("observation bundle target is not the GPA snapshot slot")
    if (bundle.get("as_of_slot") != snapshot.get("slot")
            or bundle.get("as_of_block") != snapshot.get("slot")
            or bundle.get("observed_context_slot") != snapshot.get("slot")):
        raise ValueError("observation bundle compatibility slots are not observed GPA slot")
    if not all(isinstance(value, int) for value in
               (pre.get("slot"), snapshot.get("slot"), post.get("slot"), supply.get("slot"))):
        raise ValueError("observation bundle slots incomplete")
    if not pre["slot"] <= snapshot["slot"] <= post["slot"] \
            or post["slot"] - pre["slot"] > MAX_WINDOW_SLOTS:
        raise ValueError("observation bundle slot window invalid")
    parsed_slot = pre.get("json_parsed_slot")
    if (isinstance(parsed_slot, bool) or not isinstance(parsed_slot, int)
            or not pre["slot"] <= parsed_slot <= snapshot["slot"]):
        raise ValueError("observation bundle jsonParsed slot window invalid")
    if pre.get("raw_sha256") != post.get("raw_sha256"):
        raise ValueError("observation bundle mint hashes differ")
    if supply["slot"] < snapshot["slot"] or closure.get("closed") is not True:
        raise ValueError("observation bundle supply closure invalid")
    if not (str(closure.get("gpa_amount")) == str(closure.get("mint_raw_amount"))
            == str(closure.get("token_supply_amount")) == str(supply.get("amount"))):
        raise ValueError("observation bundle three-way amounts differ")
    if attestation.get("expected_genesis") != SOLANA_MAINNET_GENESIS_HASH \
            or attestation.get("observed_genesis") != SOLANA_MAINNET_GENESIS_HASH:
        raise ValueError("observation bundle genesis attestation invalid")
    activity = bundle.get("activity") or {}
    if activity.get("mode") not in {"complete", "lightweight"} \
            or activity.get("writable_hits") != []:
        raise ValueError("observation bundle activity evidence invalid")
    sample_size = activity.get("sample_size")
    rpc_calls = activity.get("rpc_calls")
    if (isinstance(sample_size, bool) or not isinstance(sample_size, int)
            or sample_size < 0 or isinstance(rpc_calls, bool)
            or not isinstance(rpc_calls, int) or rpc_calls < 0):
        raise ValueError("observation bundle activity counts invalid")
    if activity["mode"] == "complete":
        if activity.get("complete") is not True or rpc_calls > COMPLETE_RPC_LIMIT:
            raise ValueError("complete activity evidence exceeds its proof budget")
    elif sample_size > LIGHT_SAMPLE_LIMIT or activity.get("complete") is not False:
        raise ValueError("lightweight activity evidence overstates sampled coverage")
    if bundle_path is not None:
        path = Path(bundle_path).resolve(strict=True)
        if canonical_json_sha256(json.loads(path.read_text(encoding="utf-8"))) \
                != canonical_json_sha256(bundle):
            raise ValueError("observation bundle path bytes do not match supplied object")
        # B-1（F-B6①）：holder_outputs 文件级三验（存在＋sha256＋size）。此前该锚点只有
        # 对象里的自报 ref、无 validator 实物锚（弱 EVM 一档）；消费侧（bundle_path 在场）
        # 起必须能在磁盘上找到并验中这两份 holder 产物。查找目录＝收据 inputs 实物所在
        # 目录（work_dir，inputs 已过 envelope 三验）→ bundle 同目录 → 同目录 data/。
        holder_outputs = bundle.get("holder_outputs")
        if not isinstance(holder_outputs, dict) \
                or set(holder_outputs) != {"accounts", "owners"}:
            raise ValueError("observation bundle holder_outputs missing accounts/owners")
        search_dirs = []
        gpa_ref = (bundle.get("inputs") or {}).get("gpa_rpc") or {}
        gpa_shown = str(gpa_ref.get("path") or "")
        if gpa_shown:
            gpa_path = Path(gpa_shown)
            search_dirs.append((gpa_path if gpa_path.is_absolute()
                                else path.parent / gpa_path).parent)
        search_dirs += [path.parent, path.parent / "data"]
        for key in ("accounts", "owners"):
            ref = holder_outputs.get(key)
            if not isinstance(ref, dict) or not {"path", "size", "sha256"} <= set(ref):
                raise ValueError(f"observation bundle holder_outputs.{key} must bind "
                                 "path/size/sha256")
            name = Path(str(ref.get("path") or "")).name
            if not name:
                raise ValueError(f"observation bundle holder_outputs.{key} path empty")
            actual = None
            for directory in search_dirs:
                candidate = directory / name
                if candidate.is_symlink():
                    raise ValueError(
                        f"observation bundle holder_outputs.{key} is a symlink: {candidate}")
                if candidate.is_file():
                    actual = candidate
                    break
            if actual is None:
                raise ValueError(
                    f"observation bundle holder_outputs.{key} file not found near bundle: {name}")
            if (ref.get("size") != actual.stat().st_size
                    or ref.get("sha256") != sha256_bytes(actual.read_bytes())):
                raise ValueError(
                    f"observation bundle holder_outputs.{key} sha256/size mismatch: {name}")
    return bundle
