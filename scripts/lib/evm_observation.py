#!/usr/bin/env python3
"""Attested EVM frozen-block supply observation and bundle validation.

The bundle binds a normalized JSON-RPC request/result transcript, not proof
that a remote node really executed the requests.  State reads use an EIP-1898
canonical block-hash selector and fail closed when an endpoint cannot serve it.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from chain_registry import evm_chain_id_for
from endpoint_identity import endpoint_fingerprint
from receipt_kernel import build_envelope, finalize_envelope
from receipt_validate import validate_receipt
from solana_observation import assert_declared_slot
from supply_semantics import DEAD, ZERO


BUNDLE_SCHEMA = "evm-observation-bundle/v1"
SEL_TOTSUP = "0x18160ddd"
SEL_BALANCE = "0x70a08231"
BLOCK_BINDING = "eip1898-block-hash"
_ADDRESS = re.compile(r"0x[0-9a-f]{40}")
_HASH32 = re.compile(r"0x[0-9a-fA-F]{64}")
_HEX_DATA = re.compile(r"0x(?:[0-9a-fA-F]{2})*")
_HEX_VALUE = re.compile(r"0x[0-9a-fA-F]+")


class EvmObservationError(ValueError):
    """The endpoint response or persisted observation violates the protocol."""


def canonical_json_bytes(value) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def canonical_json_sha256(value) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _quantity(value, label) -> int:
    if isinstance(value, bool):
        raise EvmObservationError(f"{label} is not a hexadecimal quantity")
    if isinstance(value, int):
        if value < 0:
            raise EvmObservationError(f"{label} is negative")
        return value
    if not isinstance(value, str) or not _HEX_VALUE.fullmatch(value):
        raise EvmObservationError(f"{label} is not a hexadecimal quantity: {value!r}")
    return int(value, 16)


def _call_value(response, label):
    if not isinstance(response, dict) or response.get("ok") is not True:
        error = response.get("error") if isinstance(response, dict) else response
        raise EvmObservationError(f"{label} RPC failed: {error}")
    return response.get("result")


def _eth_call_value(response, label) -> tuple[int, str]:
    raw = _call_value(response, f"eth_call {label}")
    if not isinstance(raw, str) or not _HEX_VALUE.fullmatch(raw):
        raise EvmObservationError(f"eth_call {label} returned invalid value: {raw!r}")
    return int(raw, 16), raw


def _balance_of_data(address):
    return SEL_BALANCE + "0" * 24 + address.removeprefix("0x").lower()


def _block(value, label):
    if not isinstance(value, dict):
        raise EvmObservationError(f"{label} result must be a block object")
    number = _quantity(value.get("number"), f"{label}.number")
    block_hash = value.get("hash")
    parent_hash = value.get("parentHash")
    timestamp = _quantity(value.get("timestamp"), f"{label}.timestamp")
    if not isinstance(block_hash, str) or not _HASH32.fullmatch(block_hash):
        raise EvmObservationError(f"{label}.hash must be 0x plus 64 hex characters")
    if not isinstance(parent_hash, str) or not _HASH32.fullmatch(parent_hash):
        raise EvmObservationError(f"{label}.parentHash must be 0x plus 64 hex characters")
    if timestamp <= 0:
        raise EvmObservationError(f"{label}.timestamp must be positive")
    return {
        "number": number,
        "block_hash": block_hash,
        "parent_hash": parent_hash,
        "timestamp": timestamp,
    }


def _record(transcript, method, params, result):
    transcript.append({
        "seq": len(transcript), "method": method,
        "params": params, "result": result,
    })


def _endpoint(pool):
    value = getattr(pool, "url", None)
    if not isinstance(value, str) or not value.strip():
        raise EvmObservationError("RPC pool endpoint is missing")
    return value


def _assert_endpoint(pool, expected):
    current = _endpoint(pool)
    if current != expected:
        raise EvmObservationError(
            "RPC endpoint changed after explicit chainId attestation; "
            "restart the observation on one stable endpoint")


def observe_evm_supply(pool, chain, token, as_of_block, *, expected_chain_id):
    """Observe one formal EVM token at one declared archive block.

    The returned core contains a private ``_transcript`` list for the producer;
    ``build_evm_observation_bundle`` deliberately excludes it from the bundle.
    """
    canonical_chain = str(chain or "").strip().lower()
    canonical_token = str(token or "").strip().lower()
    if not _ADDRESS.fullmatch(canonical_token):
        raise ValueError("token must be a 20-byte lower-case EVM address")
    if isinstance(as_of_block, bool) or not isinstance(as_of_block, int) \
            or as_of_block < 0:
        raise ValueError("as_of_block must be a non-negative integer")
    registered_chain_id = evm_chain_id_for(canonical_chain)
    if isinstance(expected_chain_id, bool) or not isinstance(expected_chain_id, int) \
            or expected_chain_id <= 0:
        raise ValueError("expected_chain_id must be a positive integer")
    if registered_chain_id != expected_chain_id:
        raise EvmObservationError(
            f"expected chain id {expected_chain_id} differs from chain_registry "
            f"value {registered_chain_id} for {canonical_chain}")

    transcript = []
    observed_chain_id = pool.attest()
    _record(transcript, "eth_chainId", [], observed_chain_id)
    if isinstance(observed_chain_id, bool) or not isinstance(observed_chain_id, int) \
            or observed_chain_id != expected_chain_id:
        raise EvmObservationError(
            f"observed chainId {observed_chain_id!r} differs from expected "
            f"{expected_chain_id}")
    attested_endpoint = _endpoint(pool)

    block_params = [hex(as_of_block), False]
    first_response = pool.call("eth_getBlockByNumber", block_params)
    _assert_endpoint(pool, attested_endpoint)
    first_raw = _call_value(first_response, "eth_getBlockByNumber(pre)")
    _record(transcript, "eth_getBlockByNumber", block_params, first_raw)
    first = _block(first_raw, "anchor block")
    assert_declared_slot(as_of_block, first["number"], "--as-of-block")

    tip_response = pool.call("eth_blockNumber", [])
    _assert_endpoint(pool, attested_endpoint)
    tip_raw = _call_value(tip_response, "eth_blockNumber")
    _record(transcript, "eth_blockNumber", [], tip_raw)
    tip = _quantity(tip_raw, "eth_blockNumber result")
    if tip < first["number"]:
        raise EvmObservationError(
            f"tip block {tip} precedes anchor block {first['number']}")

    block_selector = {
        "blockHash": first["block_hash"], "requireCanonical": True,
    }
    eth_calls = [
        ("eth_call", [{"to": canonical_token, "data": SEL_TOTSUP}, block_selector]),
        ("eth_call", [{"to": canonical_token,
                       "data": _balance_of_data(ZERO)}, block_selector]),
        ("eth_call", [{"to": canonical_token,
                       "data": _balance_of_data(DEAD)}, block_selector]),
    ]
    responses = pool.call_many(eth_calls, progress=False)
    _assert_endpoint(pool, attested_endpoint)
    if not isinstance(responses, list) or len(responses) != len(eth_calls):
        raise EvmObservationError("eth_call supply response count is incomplete")
    values = []
    for (method, params), response, label in zip(
            eth_calls, responses,
            ("totalSupply", "balanceOf(ZERO)", "balanceOf(DEAD)")):
        value, raw = _eth_call_value(response, label)
        _record(transcript, method, params, raw)
        values.append(value)

    code_params = [canonical_token, hex(as_of_block)]
    code_response = pool.call("eth_getCode", code_params)
    _assert_endpoint(pool, attested_endpoint)
    code_raw = _call_value(code_response, "eth_getCode")
    _record(transcript, "eth_getCode", code_params, code_raw)
    if not isinstance(code_raw, str) or not _HEX_DATA.fullmatch(code_raw):
        raise EvmObservationError(f"eth_getCode returned invalid bytecode: {code_raw!r}")
    runtime_code_sha256 = hashlib.sha256(bytes.fromhex(code_raw[2:])).hexdigest()

    recheck_response = pool.call("eth_getBlockByNumber", block_params)
    _assert_endpoint(pool, attested_endpoint)
    recheck_raw = _call_value(recheck_response, "eth_getBlockByNumber(recheck)")
    _record(transcript, "eth_getBlockByNumber", block_params, recheck_raw)
    recheck = _block(recheck_raw, "recheck block")
    if recheck["number"] != first["number"]:
        raise EvmObservationError("block number recheck mismatch")
    if recheck["block_hash"] != first["block_hash"]:
        raise EvmObservationError("block hash recheck mismatch")

    return {
        "attestation": {
            "expected_chain_id": expected_chain_id,
            "observed_chain_id": observed_chain_id,
            "endpoint": endpoint_fingerprint(attested_endpoint),
        },
        "anchor": {
            **first,
            "recheck_block_hash": recheck["block_hash"],
            "tip_block": tip,
            "confirmations": tip - first["number"],
        },
        "supply": {
            "total_supply_raw": str(values[0]),
            "zero_balance_raw": str(values[1]),
            "dead_balance_raw": str(values[2]),
            "block_binding": BLOCK_BINDING,
        },
        "code": {"runtime_code_sha256": runtime_code_sha256},
        "_transcript": transcript,
    }


def build_evm_observation_bundle(core, transcript_path, target, producer_file, *, input_base):
    if not isinstance(core, dict):
        raise ValueError("EVM observation core must be an object")
    required = {"attestation", "anchor", "supply", "code"}
    if not required <= set(core):
        raise ValueError("EVM observation core fields are incomplete")
    envelope = build_envelope(
        BUNDLE_SCHEMA, target, producer_file, "formal",
        inputs={"transcript": transcript_path}, input_base=input_base)
    return finalize_envelope(
        envelope, "PASS", 0,
        **{key: core[key] for key in ("attestation", "anchor", "supply", "code")})


def _non_negative_decimal(value, label) -> int:
    if not isinstance(value, str) or not re.fullmatch(r"0|[1-9][0-9]*", value):
        raise ValueError(f"{label} must be a non-negative decimal string")
    return int(value)


def _transcript_path(bundle, bundle_path):
    ref = (bundle.get("inputs") or {}).get("transcript") or {}
    shown = ref.get("path")
    raw = Path(str(shown or ""))
    return raw if raw.is_absolute() else Path(bundle_path).resolve().parent / raw


def _validate_transcript(bundle, transcript):
    if not isinstance(transcript, list) or len(transcript) != 8:
        raise ValueError("observation transcript must contain exactly 8 calls")
    methods = [
        "eth_chainId", "eth_getBlockByNumber", "eth_blockNumber",
        "eth_call", "eth_call", "eth_call", "eth_getCode",
        "eth_getBlockByNumber",
    ]
    for index, (row, method) in enumerate(zip(transcript, methods)):
        if not isinstance(row, dict) or set(row) != {"seq", "method", "params", "result"}:
            raise ValueError(f"transcript row {index} shape invalid")
        if isinstance(row.get("seq"), bool) or row.get("seq") != index:
            raise ValueError(f"transcript seq {index} is not continuous")
        if row.get("method") != method:
            raise ValueError(f"transcript method sequence mismatch at seq {index}")

    target = bundle["target"]
    anchor = bundle["anchor"]
    supply = bundle["supply"]
    token = target["token"]
    as_of = target["as_of_block"]
    expected_block_params = [hex(as_of), False]
    if transcript[0]["params"] != []:
        raise ValueError("transcript eth_chainId params mismatch")
    if transcript[1]["params"] != expected_block_params \
            or transcript[7]["params"] != expected_block_params:
        raise ValueError("transcript block params mismatch")
    if transcript[2]["params"] != []:
        raise ValueError("transcript eth_blockNumber params mismatch")
    selector = {"blockHash": anchor["block_hash"], "requireCanonical": True}
    expected_call_params = [
        [{"to": token, "data": SEL_TOTSUP}, selector],
        [{"to": token, "data": _balance_of_data(ZERO)}, selector],
        [{"to": token, "data": _balance_of_data(DEAD)}, selector],
    ]
    for offset, expected in enumerate(expected_call_params, start=3):
        if transcript[offset]["params"] != expected:
            raise ValueError(f"transcript eth_call params mismatch at seq {offset}")
    if transcript[6]["params"] != [token, hex(as_of)]:
        raise ValueError("transcript eth_getCode params mismatch")

    attestation = bundle["attestation"]
    if _quantity(transcript[0]["result"], "transcript chainId") \
            != attestation["observed_chain_id"]:
        raise ValueError("transcript chainId result mismatch")
    first = _block(transcript[1]["result"], "transcript anchor block")
    if first != {key: anchor[key] for key in
                 ("number", "block_hash", "parent_hash", "timestamp")}:
        raise ValueError("transcript anchor block result mismatch")
    if _quantity(transcript[2]["result"], "transcript tip") != anchor["tip_block"]:
        raise ValueError("transcript tip result mismatch")
    for offset, field in enumerate(
            ("total_supply_raw", "zero_balance_raw", "dead_balance_raw"), start=3):
        raw = transcript[offset]["result"]
        if not isinstance(raw, str) or not _HEX_VALUE.fullmatch(raw) \
                or int(raw, 16) != int(supply[field]):
            raise ValueError(f"transcript {field} result mismatch")
    code_raw = transcript[6]["result"]
    if not isinstance(code_raw, str) or not _HEX_DATA.fullmatch(code_raw):
        raise ValueError("transcript eth_getCode result invalid")
    if hashlib.sha256(bytes.fromhex(code_raw[2:])).hexdigest() \
            != bundle["code"]["runtime_code_sha256"]:
        raise ValueError("transcript runtime code result mismatch")
    recheck = _block(transcript[7]["result"], "transcript recheck block")
    if recheck["number"] != anchor["number"] \
            or recheck["block_hash"] != anchor["recheck_block_hash"]:
        raise ValueError("transcript recheck block result mismatch")


def validate_evm_observation_bundle(
        bundle, *, bundle_path=None, expected_token=None, expected_chain_id=None,
        expected_producer="scripts/evm/observe_supply.py"):
    if not isinstance(bundle, dict) or bundle.get("schema") != BUNDLE_SCHEMA:
        raise ValueError("EVM observation bundle schema invalid")
    case_root = Path(bundle_path).resolve().parent if bundle_path is not None else None
    errors = validate_receipt(bundle, case_root=case_root)
    if errors:
        raise ValueError(f"EVM observation bundle envelope invalid: {errors[0]}")
    if bundle.get("verdict") != "PASS" or bundle.get("exit_code") != 0 \
            or bundle.get("mode") != "formal":
        raise ValueError("formal EVM observation bundle must be PASS/0")
    if (bundle.get("producer") or {}).get("path") != expected_producer:
        raise ValueError("EVM observation bundle producer binding invalid")

    target = bundle.get("target") or {}
    token = target.get("token")
    as_of = target.get("as_of_block")
    if not isinstance(token, str) or token != token.lower() or not _ADDRESS.fullmatch(token):
        raise ValueError("EVM observation bundle target token invalid")
    if expected_token is not None and token != str(expected_token).lower():
        raise ValueError("EVM observation bundle token target mismatch")
    if isinstance(as_of, bool) or not isinstance(as_of, int) or as_of < 0:
        raise ValueError("EVM observation bundle target block invalid")

    attestation = bundle.get("attestation") or {}
    expected = attestation.get("expected_chain_id")
    observed = attestation.get("observed_chain_id")
    registered = evm_chain_id_for(target.get("chain"))
    if isinstance(expected, bool) or not isinstance(expected, int) or expected <= 0 \
            or observed != expected or registered != expected:
        raise ValueError("EVM observation bundle chainId attestation invalid")
    if expected_chain_id is not None and expected != expected_chain_id:
        raise ValueError("EVM observation bundle expected chainId mismatch")
    endpoint = attestation.get("endpoint") or {}
    if set(endpoint) != {"public_origin", "sha256"} \
            or not isinstance(endpoint.get("public_origin"), str) \
            or not endpoint["public_origin"].strip() \
            or not isinstance(endpoint.get("sha256"), str) \
            or not re.fullmatch(r"[0-9a-f]{64}", endpoint["sha256"]):
        raise ValueError("EVM observation bundle endpoint fingerprint invalid")

    anchor = bundle.get("anchor") or {}
    if anchor.get("number") != as_of:
        raise ValueError("EVM observation bundle anchor number target mismatch")
    for field in ("block_hash", "parent_hash", "recheck_block_hash"):
        if not isinstance(anchor.get(field), str) or not _HASH32.fullmatch(anchor[field]):
            raise ValueError(f"EVM observation bundle anchor {field} invalid")
    if anchor["block_hash"] != anchor["recheck_block_hash"]:
        raise ValueError("EVM observation bundle anchor recheck hash mismatch")
    tip = anchor.get("tip_block")
    confirmations = anchor.get("confirmations")
    timestamp = anchor.get("timestamp")
    if any(isinstance(item, bool) or not isinstance(item, int)
           for item in (tip, confirmations, timestamp)) \
            or tip < as_of or confirmations != tip - as_of or timestamp <= 0:
        raise ValueError("EVM observation bundle anchor heights/timestamp invalid")

    supply = bundle.get("supply") or {}
    for field in ("total_supply_raw", "zero_balance_raw", "dead_balance_raw"):
        _non_negative_decimal(supply.get(field), f"supply.{field}")
    if supply.get("block_binding") != BLOCK_BINDING:
        raise ValueError("EVM observation bundle supply block binding invalid")
    code = bundle.get("code") or {}
    if not isinstance(code.get("runtime_code_sha256"), str) \
            or not re.fullmatch(r"[0-9a-f]{64}", code["runtime_code_sha256"]):
        raise ValueError("EVM observation bundle runtime code sha256 invalid")

    if bundle_path is not None:
        path = Path(bundle_path).resolve(strict=True)
        disk = json.loads(path.read_text(encoding="utf-8"))
        if canonical_json_sha256(disk) != canonical_json_sha256(bundle):
            raise ValueError("EVM observation bundle path bytes do not match supplied object")
        transcript_path = _transcript_path(bundle, path).resolve(strict=True)
        transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
        _validate_transcript(bundle, transcript)
    return bundle
