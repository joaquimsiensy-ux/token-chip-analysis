#!/usr/bin/env python3
"""Pure helpers for Solana SPL transaction-net edge collection."""
from collections.abc import Mapping
import hashlib
import json
from pathlib import Path


ZERO_OWNER = "0x" + "0" * 40

# v4 transaction-net edge semantics.  Producers and formal consumers import
# these constants instead of duplicating schema strings.
EDGE_SCHEMA_FIELDS = ("ts", "slot", "tx_index", "instr_index", "from", "to", "amt")
EDGE_SEMANTICS = "owner-net-greedy"
ORDER_GRANULARITY_TX = "transaction"
INSTR_INDEX_TX_NET = -1


def validate_edge_row(row):
    """Return one canonical v4 edge tuple or reject legacy/malformed rows."""
    if not isinstance(row, (list, tuple)) or len(row) != len(EDGE_SCHEMA_FIELDS):
        raise ValueError(
            "v4 edge row must contain exactly 7 fields; legacy 5-tuples require full recapture")
    ts, slot, tx_index, instr_index, owner_from, owner_to, amount = row
    for name, value in (("ts", ts), ("slot", slot), ("tx_index", tx_index)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"edge {name} must be a non-negative integer")
    if isinstance(instr_index, bool) or instr_index != INSTR_INDEX_TX_NET:
        raise ValueError(f"transaction-net edge instr_index must be {INSTR_INDEX_TX_NET}")
    for name, value in (("from", owner_from), ("to", owner_to)):
        if not isinstance(value, str) or not value:
            raise ValueError(f"edge {name} must be a non-empty string")
    if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
        raise ValueError("edge amt must be a positive integer")
    return (ts, slot, tx_index, instr_index, owner_from, owner_to, amount)


def edge_sort_key(edge):
    """Canonical v4 output order; amount text keeps external merge lossless."""
    row = validate_edge_row(edge)
    return (row[1], row[2], row[4], row[5], str(row[6]))


def transaction_digest(edges):
    """Hash one transaction's complete, order-independent canonical edge set."""
    rows = tuple(sorted({validate_edge_row(row) for row in edges}, key=edge_sort_key))
    if not rows:
        raise ValueError("transaction edge set must not be empty")
    identities = {(row[1], row[2]) for row in rows}
    if len(identities) != 1:
        raise ValueError("transaction digest input mixes slot/tx_index identities")
    payload = json.dumps(rows, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest(), rows


def dedupe_transaction_sources(sources):
    """Deduplicate complete transactions across named sources, rejecting conflicts."""
    versions = {}
    for source_name, source_rows in sources:
        grouped = {}
        for raw in source_rows:
            row = validate_edge_row(raw)
            grouped.setdefault((row[1], row[2]), []).append(row)
        for identity, rows in grouped.items():
            digest, canonical = transaction_digest(rows)
            prior = versions.get(identity)
            if prior is not None and prior[0] != digest:
                raise RuntimeError(
                    "conflicting transaction edge sets for "
                    f"slot={identity[0]} tx_index={identity[1]} "
                    f"({prior[2]} vs {source_name})")
            if prior is None:
                versions[identity] = (digest, canonical, source_name)
    return [row for _identity, (_digest, rows, _source) in sorted(versions.items())
            for row in rows]


def _validated_delta(delta):
    if not isinstance(delta, Mapping):
        raise TypeError("delta must be a mapping of owner to integer amount")
    checked = []
    for owner, amount in delta.items():
        if not isinstance(owner, str) or not owner:
            raise TypeError("delta owner must be a non-empty string")
        if isinstance(amount, bool) or not isinstance(amount, int):
            raise TypeError(f"delta amount for {owner!r} must be an integer")
        checked.append((owner, amount))
    return checked


def pair_tx(delta):
    """Greedily pair owner-level transaction deltas in deterministic order."""
    checked = _validated_delta(delta)
    pos = sorted(([owner, amount] for owner, amount in checked if amount > 0),
                 key=lambda item: (-item[1], item[0]))
    neg = sorted(([owner, -amount] for owner, amount in checked if amount < 0),
                 key=lambda item: (-item[1], item[0]))
    edges, i, j = [], 0, 0
    while i < len(pos) and j < len(neg):
        matched = min(pos[i][1], neg[j][1])
        edges.append((neg[j][0], pos[i][0], matched))
        pos[i][1] -= matched
        neg[j][1] -= matched
        if pos[i][1] == 0:
            i += 1
        if neg[j][1] == 0:
            j += 1
    edges.extend((ZERO_OWNER, owner, remaining)
                 for owner, remaining in pos[i:] if remaining)
    edges.extend((owner, ZERO_OWNER, remaining)
                 for owner, remaining in neg[j:] if remaining)
    return edges


def _raw_amount(value, field):
    if value is None or value == "":
        return 0
    if isinstance(value, bool):
        raise TypeError(f"{field} must be a non-negative raw integer")
    if isinstance(value, int):
        amount = value
    elif isinstance(value, str) and value.isdigit():
        amount = int(value)
    else:
        raise TypeError(f"{field} must be a non-negative raw integer")
    if amount < 0:
        raise ValueError(f"{field} must not be negative")
    return amount


def _optional_text(value, field):
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string or null")
    return value


def parse_owner_delta(record, target_mint):
    """Validate one tokenBalance row and return its two-sided owner deltas.

    The account authority can change inside one successful transaction.  The
    pre side therefore always debits ``preOwner`` and the post side credits
    ``postOwner`` independently; only sides bound to ``target_mint`` enter the
    ledger.
    """
    if not isinstance(record, Mapping):
        raise TypeError("tokenBalance record must be a mapping")
    if not isinstance(target_mint, str) or not target_mint:
        raise TypeError("target mint must be a non-empty string")
    required = ("transactionIndex", "account", "preMint", "postMint",
                "preOwner", "postOwner", "preAmount", "postAmount")
    missing = [field for field in required if field not in record]
    if missing:
        raise ValueError(f"tokenBalance record missing fields: {','.join(missing)}")

    tx_index = record["transactionIndex"]
    if isinstance(tx_index, bool) or not isinstance(tx_index, int) or tx_index < 0:
        raise ValueError("transactionIndex must be a non-negative integer")
    account = record["account"]
    if not isinstance(account, str) or not account:
        raise ValueError("tokenBalance account must be a non-empty string")

    pre_mint = _optional_text(record["preMint"], "preMint")
    post_mint = _optional_text(record["postMint"], "postMint")
    pre_owner = _optional_text(record["preOwner"], "preOwner")
    post_owner = _optional_text(record["postOwner"], "postOwner")
    pre_amount = _raw_amount(record["preAmount"], "preAmount")
    post_amount = _raw_amount(record["postAmount"], "postAmount")

    if pre_amount and pre_owner is None:
        raise ValueError("nonzero preAmount requires preOwner")
    if post_amount and post_owner is None:
        raise ValueError("nonzero postAmount requires postOwner")
    if pre_amount and pre_mint is None:
        raise ValueError("nonzero preAmount requires preMint")
    if post_amount and post_mint is None:
        raise ValueError("nonzero postAmount requires postMint")
    if pre_mint != target_mint and post_mint != target_mint:
        raise ValueError("tokenBalance record is not bound to the target mint")

    deltas = {}
    if pre_mint == target_mint and pre_amount:
        deltas[pre_owner] = deltas.get(pre_owner, 0) - pre_amount
    if post_mint == target_mint and post_amount:
        deltas[post_owner] = deltas.get(post_owner, 0) + post_amount
    return tx_index, account, tuple(
        (owner, amount) for owner, amount in deltas.items() if amount)


def owner_deltas_by_tx(records, target_mint):
    """Aggregate validated owner deltas and reject duplicate account records."""
    grouped = {}
    seen = set()
    for record in records:
        tx_index, account, deltas = parse_owner_delta(record, target_mint)
        identity = (tx_index, account)
        if identity in seen:
            raise ValueError(
                f"duplicate tokenBalance record for tx_index={tx_index} account={account}")
        seen.add(identity)
        ledger = grouped.setdefault(tx_index, {})
        for owner, amount in deltas:
            ledger[owner] = ledger.get(owner, 0) + amount
    for ledger in grouped.values():
        for owner in [owner for owner, amount in ledger.items() if not amount]:
            del ledger[owner]
    return grouped


def soltx_cache_paths(mint, data_dir):
    """Resolve the case-sensitive sha256(mint) cache, meta and parts paths."""
    if not isinstance(mint, str):
        raise TypeError("mint must be a string")
    root = Path(data_dir)
    key = hashlib.sha256(mint.encode("utf-8")).hexdigest()
    return (root / f"soltx-{key}.jsonl.gz", root / f"soltx-{key}.meta.json",
            root / f"soltx-{key}.parts")
