#!/usr/bin/env python3
"""Verify batch-5 ARC live windows and optionally replay three collisions online."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import sys

import requests


REPO = Path(__file__).resolve().parents[3]
MAINTENANCE = REPO / "maintenance/repair-20260817-sqd-v4"
LIVE_ROOT = MAINTENANCE / "live_windows"
CASE_ROOT = Path("/Users/uravvv/Documents/5.6筹码分析/ARC分析")
MINT = "61V8vBaqAGMpgDQi4JcAwo1dmBGHsyhzodcPqnEVpump"
EDGE_NAME = "soltx-6b99816bc26d8c53bac165b4efeb03a2b0beee563bf242e05b8906ae8dff3cb8"
CASE_EDGES = CASE_ROOT / "data" / f"{EDGE_NAME}-txaware-repaired.jsonl.gz"
SQD_BASE = "https://portal.sqd.dev/datasets/solana-mainnet"
STATE_RPCS = (
    "https://api.mainnet-beta.solana.com",
    "https://solana-rpc.publicnode.com",
)
WINDOWS = (
    ("collision_382697976_382714174", 382697976, 382714174, True),
    ("green_374331356_374344169", 374331356, 374344169, False),
)
EDGE_SCHEMA = ["ts", "slot", "tx_index", "instr_index", "from", "to", "amt"]


sys.path.insert(0, str(REPO / "scripts/lib"))
from producer_history import historical_producer_hashes  # noqa: E402
from solana_attested_session import SolanaAttestedSession  # noqa: E402


def load_live(path: Path) -> tuple[list[tuple], str]:
    rows: list[tuple] = []
    digest = hashlib.sha256()
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            row = json.loads(line)
            if not isinstance(row, list) or len(row) != 7:
                raise ValueError(f"{path}:{line_no}: expected strict 7-tuple")
            ts, slot, tx_index, instr_index, owner_from, owner_to, amount = row
            if any(isinstance(value, bool) or not isinstance(value, int)
                   for value in (ts, slot, tx_index, instr_index, amount)):
                raise ValueError(f"{path}:{line_no}: invalid integer field")
            if tx_index < 0 or instr_index != -1 or amount <= 0:
                raise ValueError(f"{path}:{line_no}: invalid v4 identity/amount")
            if not isinstance(owner_from, str) or not owner_from:
                raise ValueError(f"{path}:{line_no}: invalid from owner")
            if not isinstance(owner_to, str) or not owner_to:
                raise ValueError(f"{path}:{line_no}: invalid to owner")
            normalized = json.dumps(row, ensure_ascii=False) + "\n"
            digest.update(normalized.encode("utf-8"))
            rows.append(tuple(row))
    return rows, digest.hexdigest()


def case_projection(lo: int, hi: int) -> Counter:
    projected: Counter = Counter()
    with gzip.open(CASE_EDGES, "rt", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            row = json.loads(line)
            if not isinstance(row, list) or len(row) != 5:
                raise ValueError(f"{CASE_EDGES}:{line_no}: expected 5-tuple")
            if lo <= row[1] <= hi:
                projected[tuple(row)] += 1
    return projected


def collision_groups(rows: list[tuple]) -> list[dict]:
    grouped: dict[tuple, list[int]] = defaultdict(list)
    for ts, slot, tx_index, _instr_index, owner_from, owner_to, amount in rows:
        grouped[(ts, slot, owner_from, owner_to, amount)].append(tx_index)
    collisions = [
        {"projection": list(projection), "multiplicity": len(indexes),
         "tx_indexes": sorted(indexes)}
        for projection, indexes in grouped.items()
        if len(indexes) > 1
    ]
    return sorted(collisions, key=lambda item: (-item["multiplicity"], item["projection"]))


def verify_window(name: str, lo: int, hi: int, expect_collision: bool) -> tuple[dict, list[dict]]:
    data_dir = LIVE_ROOT / name / "data"
    edge_path = data_dir / f"{EDGE_NAME}.jsonl.gz"
    meta_path = data_dir / f"{EDGE_NAME}.meta.json"
    rows, logical_sha = load_live(edge_path)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    active = historical_producer_hashes(
        "scripts/solana/fetch_sqd_transfers_v2.py", "sqd-solana-cache/v4")
    required = {
        "schema": "sqd-solana-cache/v4",
        "version": 4,
        "mint": MINT,
        "collector": "fetch_sqd_transfers_v2.py/v4",
        "edge_schema": EDGE_SCHEMA,
        "edge_semantics": "owner-net-greedy",
        "order_granularity": "transaction",
        "order_exact": False,
        "dedupe_identity": "slot-txindex-digest/v1",
        "from_slot": lo,
        "finalized_upper_slot": hi,
        "edge_rows": len(rows),
        "edge_logical_sha256": logical_sha,
    }
    mismatches = {
        key: {"expected": expected, "actual": meta.get(key)}
        for key, expected in required.items() if meta.get(key) != expected
    }
    collector_registered = meta.get("collector_sha256") in active
    live_projection = Counter((row[0], row[1], row[4], row[5], row[6]) for row in rows)
    case_rows = case_projection(lo, hi)
    collisions = collision_groups(rows)
    passed = (
        not mismatches
        and collector_registered
        and live_projection == case_rows
        and bool(collisions) == expect_collision
    )
    result = {
        "status": "PASS" if passed else "FAIL",
        "window": [lo, hi],
        "slot_count": hi - lo + 1,
        "live_rows": len(rows),
        "case_rows": sum(case_rows.values()),
        "projection_multiset_equal": live_projection == case_rows,
        "live_only_rows": sum((live_projection - case_rows).values()),
        "case_only_rows": sum((case_rows - live_projection).values()),
        "collision_groups": len(collisions),
        "collision_extra_rows": sum(item["multiplicity"] - 1 for item in collisions),
        "max_collision_multiplicity": max(
            (item["multiplicity"] for item in collisions), default=1),
        "meta_mismatches": mismatches,
        "collector_sha256": meta.get("collector_sha256"),
        "collector_registered_active": collector_registered,
        "edge_logical_sha256": logical_sha,
    }
    return result, collisions


def sqd_replay(slot: int, tx_indexes: list[int]) -> dict:
    fields = {
        "block": {"number": True, "timestamp": True},
        "transaction": {"transactionIndex": True, "err": True},
        "tokenBalance": {
            "transactionIndex": True,
            "account": True,
            "preMint": True,
            "postMint": True,
            "preOwner": True,
            "postOwner": True,
            "preAmount": True,
            "postAmount": True,
        },
    }
    body = {
        "type": "solana",
        "fromBlock": slot,
        "toBlock": slot,
        "fields": fields,
        "tokenBalances": [
            {"postMint": [MINT], "transaction": True},
            {"preMint": [MINT], "transaction": True},
        ],
    }
    response = requests.post(
        SQD_BASE + "/stream", json=body, timeout=(15, 60))
    response.raise_for_status()
    blocks = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    raw_records = []
    statuses = {}
    for block in blocks:
        for transaction in block.get("transactions") or []:
            index = transaction.get("transactionIndex")
            if index in tx_indexes:
                statuses[str(index)] = transaction.get("err")
        for record in block.get("tokenBalances") or []:
            if record.get("transactionIndex") in tx_indexes:
                raw_records.append(record)
    observed = sorted({record["transactionIndex"] for record in raw_records})
    return {
        "request": body,
        "http_status": response.status_code,
        "observed_transaction_indexes": observed,
        "transaction_statuses": statuses,
        "raw_token_balance_excerpt": raw_records[:12],
    }


def requests_json(endpoint: str, payload: dict, timeout: int) -> dict:
    """Use the same proven transport stack as the SQD replay, without weakening attestation."""
    response = requests.post(
        endpoint,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=timeout,
    )
    response.raise_for_status()
    decoded = response.json()
    if not isinstance(decoded, dict):
        raise ValueError("Solana RPC response is not an object")
    return decoded


def rpc_replay(session: SolanaAttestedSession, slot: int, tx_indexes: list[int]) -> dict:
    params = [slot, {
        "commitment": "finalized",
        "encoding": "json",
        "transactionDetails": "full",
        "rewards": False,
        "maxSupportedTransactionVersion": 0,
    }]
    block = session.call("getBlock", params)
    transactions = block.get("transactions") if isinstance(block, dict) else None
    if not isinstance(transactions, list):
        raise ValueError(f"getBlock({slot}) returned no transaction list")
    excerpts = []
    for index in tx_indexes:
        if index >= len(transactions):
            raise ValueError(
                f"getBlock({slot}) has {len(transactions)} txs; index {index} absent")
        signatures = transactions[index].get("transaction", {}).get("signatures") or []
        if not signatures:
            raise ValueError(f"getBlock({slot}) tx_index={index} has no signature")
        excerpts.append({"transaction_index": index, "signature": signatures[0]})
    if len({item["signature"] for item in excerpts}) != len(excerpts):
        raise ValueError(f"getBlock({slot}) sampled signatures are not distinct")
    return {
        "request": {"method": "getBlock", "params": params},
        "attested_endpoint": session.endpoint,
        "observed_genesis_hash": session.observed_genesis,
        "blockhash": block.get("blockhash"),
        "transaction_count": len(transactions),
        "response_excerpt": excerpts,
        "distinct_signatures": True,
    }


def online_samples(collisions: list[dict]) -> list[dict]:
    selected = []
    used_slots = set()
    for collision in collisions:
        slot = collision["projection"][1]
        if slot not in used_slots:
            selected.append(collision)
            used_slots.add(slot)
        if len(selected) == 3:
            break
    if len(selected) < 3:
        raise ValueError("need at least three collision groups on distinct slots")
    session = SolanaAttestedSession(
        STATE_RPCS, request_json=requests_json, timeout=60)
    samples = []
    for collision in selected:
        slot = collision["projection"][1]
        indexes = collision["tx_indexes"][:2]
        sqd = sqd_replay(slot, indexes)
        if sqd["observed_transaction_indexes"] != indexes:
            raise ValueError(
                f"SQD slot {slot}: expected tx indexes {indexes}, "
                f"observed {sqd['observed_transaction_indexes']}")
        if any(sqd["transaction_statuses"].get(str(index)) is not None for index in indexes):
            raise ValueError(f"SQD slot {slot}: sampled transaction was not successful")
        samples.append({
            "projection": collision["projection"],
            "sampled_transaction_indexes": indexes,
            "sqd": sqd,
            "solana_rpc": rpc_replay(session, slot, indexes),
            "status": "PASS",
        })
    return samples


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--online", action="store_true")
    args = parser.parse_args()
    report = {"schema": "arc-live-window-verification/v1", "windows": {}}
    collision_rows = []
    for name, lo, hi, expect_collision in WINDOWS:
        result, collisions = verify_window(name, lo, hi, expect_collision)
        report["windows"][name] = result
        if expect_collision:
            collision_rows = collisions
    if args.online:
        report["online_collision_samples"] = online_samples(collision_rows)
    report["status"] = "PASS" if all(
        item["status"] == "PASS" for item in report["windows"].values()) else "FAIL"
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
