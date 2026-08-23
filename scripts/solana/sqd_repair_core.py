#!/usr/bin/env python3
"""Pure protocol helpers for deterministic Solana SQD repair generations."""
from __future__ import annotations

import gzip
import hashlib
import json
import struct
from pathlib import Path

from spl_edge_core import (INSTR_INDEX_TX_NET, edge_sort_key,
                           owner_deltas_by_tx, pair_tx, validate_edge_row)


VOTE_PROGRAM = "Vote111111111111111111111111111111111111111"
SYSTEM_PROGRAM = "11111111111111111111111111111111"
BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
NUMERIC_KEYS = {
    "amt", "slot", "tx_index", "ts", "reference_position",
    "nonvote_ordinal", "sqd_index", "edge_rows", "edges", "transactions",
    "from_slot", "to_slot", "finalized_upper_slot", "size", "requests",
    "credits_estimate", "seq", "attempt", "http_status", "bytes",
}


def canonical_json(value):
    """Frozen canonical JSON; floats and string-encoded numeric fields fail."""
    def walk(item, key=None, where="$"):
        if isinstance(item, float):
            raise ValueError(f"float forbidden at {where}")
        if key in NUMERIC_KEYS and not isinstance(item, (dict, list)) \
                and (isinstance(item, bool) or not isinstance(item, int)):
            raise ValueError(f"{key} must be JSON int at {where}")
        if isinstance(item, dict):
            for child_key, child in item.items():
                if not isinstance(child_key, str):
                    raise ValueError(f"object key must be string at {where}")
                walk(child, child_key, f"{where}.{child_key}")
        elif isinstance(item, list):
            for index, child in enumerate(item):
                walk(child, None, f"{where}[{index}]")
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


def compute_plan_digest(plan):
    required = {
        "base", "coverage", "candidate_slots", "mode", "reference", "producer"
    }
    if not isinstance(plan, dict) or not required.issubset(plan):
        raise ValueError("plan digest input missing required fields")
    material = {
        "base": {
            "edge_sha256": plan["base"]["edge_sha256"],
            "meta_sha256": plan["base"]["meta_sha256"],
        },
        "coverage": {
            "probe_id": plan["coverage"]["probe_id"],
            "map_sha256": plan["coverage"]["map_sha256"],
        },
        "candidate_slots": sorted(set(plan["candidate_slots"])),
        "mode": plan["mode"],
        "reference": {
            "kind": plan["reference"]["kind"],
            "endpoint_fingerprint": plan["reference"]["endpoint_fingerprint"],
        },
        "producer": {"sha256": plan["producer"]["sha256"]},
    }
    return sha256_bytes(canonical_json(material))[:16]


def compute_gid(value):
    """Hash the deterministic repair identity; exclude all labels and RPC ledger."""
    if not isinstance(value, dict):
        raise ValueError("gid input must be object")
    material = dict(value)
    for key in ("gid", "generated_at", "rpc_ledger", "bundle_sha256"):
        material.pop(key, None)
    if material.get("kind") != "repair":
        material["kind"] = "repair"
    return sha256_bytes(canonical_json(material))[:16]


def derive_residual_owners(receipt, replay_balances, snapshot_balances,
                           subset=None):
    """Derive E25 residual owners from the three existing replay artifacts."""
    if not isinstance(receipt, dict) or not isinstance(receipt.get("gate_pass"), bool):
        raise ValueError("reconcile receipt gate_pass must be boolean")
    for label, value in (("replay_final_balances", replay_balances),
                         ("holders_owners", snapshot_balances)):
        if not isinstance(value, dict):
            raise ValueError(f"{label} must be an owner-to-int object")
        for owner, amount in value.items():
            if not isinstance(owner, str) or not owner \
                    or not isinstance(amount, int) or isinstance(amount, bool):
                raise ValueError(f"{label} contains invalid owner balance")
    if receipt["gate_pass"]:
        return []
    allowed = None
    if subset is not None:
        if not isinstance(subset, (list, tuple, set)) \
                or any(not isinstance(owner, str) or not owner for owner in subset):
            raise ValueError("residual owner subset must contain owner strings")
        allowed = set(subset)
    owners = sorted(set(replay_balances) | set(snapshot_balances))
    rows = []
    for owner in owners:
        replay = replay_balances.get(owner, 0)
        snapshot = snapshot_balances.get(owner, 0)
        if replay != snapshot and (allowed is None or owner in allowed):
            rows.append({"owner": owner, "replay": replay,
                         "snapshot": snapshot})
    return rows


def owner_activity(rows, owner):
    """Return sorted activity slots and inclusive replay balances for one owner."""
    per_slot = {}
    for raw in rows:
        row = validate_edge_row(raw)
        delta = (row[6] if row[5] == owner else 0) \
            - (row[6] if row[4] == owner else 0)
        if delta:
            per_slot[row[1]] = per_slot.get(row[1], 0) + delta
    slots = sorted(per_slot)
    balance = 0
    out = []
    for slot in slots:
        balance += per_slot[slot]
        out.append({"slot": slot, "replay_balance": balance})
    return out


def b58decode(value):
    if not isinstance(value, str):
        raise ValueError("base58 value must be string")
    number = 0
    for char in value:
        try:
            number = number * 58 + BASE58.index(char)
        except ValueError as exc:
            raise ValueError("invalid base58 data") from exc
    body = number.to_bytes((number.bit_length() + 7) // 8, "big") if number else b""
    return b"\0" * (len(value) - len(value.lstrip("1"))) + body


def _message(tx):
    return tx.get("transaction", {}).get("message", {}) if isinstance(tx, dict) else {}


def account_keys(tx):
    message = _message(tx)
    keys = []
    for item in message.get("accountKeys") or []:
        keys.append(item.get("pubkey") if isinstance(item, dict) else item)
    loaded = tx.get("meta", {}).get("loadedAddresses") or {}
    keys.extend(loaded.get("writable") or [])
    keys.extend(loaded.get("readonly") or [])
    return keys


def _instruction_program(instruction, keys):
    direct = instruction.get("programId")
    if isinstance(direct, str):
        return direct
    index = instruction.get("programIdIndex")
    return keys[index] if isinstance(index, int) and 0 <= index < len(keys) else None


def is_vote_transaction(tx):
    keys = account_keys(tx)
    return any(_instruction_program(ix, keys) == VOTE_PROGRAM
               for ix in (_message(tx).get("instructions") or [])
               if isinstance(ix, dict))


def is_nonce_transaction(tx):
    keys = account_keys(tx)
    for instruction in _message(tx).get("instructions") or []:
        if not isinstance(instruction, dict) \
                or _instruction_program(instruction, keys) != SYSTEM_PROGRAM:
            continue
        data = instruction.get("data")
        if not data:
            continue
        decoded = b58decode(data)
        if len(decoded) >= 4 and struct.unpack("<I", decoded[:4])[0] == 4:
            return True
    return False


def transaction_signature(tx):
    signatures = tx.get("transaction", {}).get("signatures") or []
    return signatures[0] if signatures else None


def signature_difference(reference_transactions, sqd_transactions):
    sqd = {row.get("signature") or (row.get("signatures") or [None])[0]
           for row in sqd_transactions}
    out = []
    for position, tx in enumerate(reference_transactions):
        signature = transaction_signature(tx)
        if not signature or is_vote_transaction(tx) or signature in sqd:
            continue
        out.append({"position": position, "signature": signature,
                    "nonce": is_nonce_transaction(tx), "tx": tx})
    return out


def classify_missing(*, sqd_present, missing):
    if not sqd_present:
        return "confirmed_missing_block"
    if any(item.get("nonce") for item in missing):
        return "confirmed_nonce_defect"
    if missing:
        return "confirmed_other_defect"
    return "refuted"


def token_balance_records(tx, tx_index, mint):
    keys = account_keys(tx)
    meta = tx.get("meta") or {}
    by_account = {}
    for prefix, field in (("pre", "preTokenBalances"),
                          ("post", "postTokenBalances")):
        for balance in meta.get(field) or []:
            if balance.get("mint") != mint:
                continue
            index = balance.get("accountIndex")
            if not isinstance(index, int) or not (0 <= index < len(keys)):
                raise ValueError("token balance accountIndex outside account keys")
            account = keys[index]
            row = by_account.setdefault(account, {
                "transactionIndex": tx_index, "account": account,
                "preMint": None, "postMint": None, "preOwner": None,
                "postOwner": None, "preAmount": None, "postAmount": None,
            })
            row[prefix + "Mint"] = balance.get("mint")
            row[prefix + "Owner"] = balance.get("owner")
            amount = (balance.get("uiTokenAmount") or {}).get("amount")
            if isinstance(amount, str):
                if not amount.isdigit():
                    raise ValueError("token amount is not a decimal integer")
                amount = int(amount)
            row[prefix + "Amount"] = amount
    return list(by_account.values())


def edges_for_transaction(tx, *, mint, slot, tx_index, block_time):
    if (tx.get("meta") or {}).get("err") is not None:
        return []
    records = token_balance_records(tx, tx_index, mint)
    deltas = owner_deltas_by_tx(records, mint).get(tx_index, {}) if records else {}
    return [validate_edge_row((block_time, slot, tx_index, INSTR_INDEX_TX_NET,
                               source, target, amount))
            for source, target, amount in pair_tx(deltas)]


def build_slot_index_map(sqd_transactions, reference_transactions):
    ref = []
    ordinal = 0
    for position, tx in enumerate(reference_transactions):
        if is_vote_transaction(tx):
            continue
        signature = transaction_signature(tx)
        if not signature:
            raise ValueError("reference transaction lacks signature")
        ref.append((position, ordinal, signature))
        ordinal += 1
    by_signature = {signature: nonvote for _position, nonvote, signature in ref}
    if len(by_signature) != len(ref):
        raise ValueError("reference signatures are not unique")
    rows = []
    seen_indices = set()
    for row in sqd_transactions:
        index = row.get("index", row.get("transactionIndex"))
        signature = row.get("signature") or (row.get("signatures") or [None])[0]
        if not isinstance(index, int) or isinstance(index, bool) or index < 0:
            raise ValueError("SQD transaction index invalid")
        if index in seen_indices or signature not in by_signature:
            raise ValueError("SQD/ref signature map is not a bijection")
        seen_indices.add(index)
        rows.append([index, by_signature[signature], signature])
    rows.sort(key=lambda item: item[0])
    if len({item[1] for item in rows}) != len(rows) \
            or len({item[2] for item in rows}) != len(rows):
        raise ValueError("slot index map columns are not unique")
    return rows, len(ref)


def remap_base_edges(base_edges, map_rows, defect_slots):
    lookups = {int(slot): {item[0]: item[1] for item in rows}
               for slot, rows in map_rows.items()}
    out = []
    for raw in base_edges:
        row = list(validate_edge_row(raw))
        if row[1] in defect_slots:
            lookup = lookups.get(row[1], {})
            if row[2] not in lookup:
                raise ValueError(f"base edge has no slot-index solution: {row[1]}/{row[2]}")
            row[2] = lookup[row[2]]
        out.append(tuple(row))
    return out


def merge_edges(base_edges, repair_edges, slot_maps):
    defect_slots = set(slot_maps)
    merged = remap_base_edges(base_edges, slot_maps, defect_slots)
    merged.extend(validate_edge_row(row) for row in repair_edges)
    return sorted(merged, key=edge_sort_key)


def edge_logical_evidence(rows):
    digest = hashlib.sha256()
    count = 0
    for row in rows:
        checked = validate_edge_row(row)
        digest.update((json.dumps(list(checked), ensure_ascii=False) + "\n").encode())
        count += 1
    return digest.hexdigest(), count


def read_edge_file(path):
    rows = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(validate_edge_row(json.loads(line)))
    return rows


def parse_routea_cache(path):
    path = Path(path)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    required = {"slot", "blockhash", "blockTime", "helius_sigs", "sqd_sigs",
                "missing_full"}
    if not required.issubset(payload):
        raise ValueError("routeA cache shape invalid")
    if not set(payload["sqd_sigs"]).issubset(payload["helius_sigs"]):
        raise ValueError("routeA SQD signatures are not a reference subset")
    missing = {item.get("sig") for item in payload["missing_full"]}
    expected = set(payload["helius_sigs"]) - set(payload["sqd_sigs"])
    if not missing.issubset(expected):
        raise ValueError("routeA missing_full contains non-missing signature")
    return payload
