#!/usr/bin/env python3
"""Pure helpers for Solana SPL transaction-net edge collection."""
from collections.abc import Mapping
import hashlib
from pathlib import Path


ZERO_OWNER = "0x" + "0" * 40

# v4 transaction-net edge semantics.  Producers and formal consumers import
# these constants instead of duplicating schema strings.
EDGE_SCHEMA_FIELDS = ("ts", "slot", "tx_index", "instr_index", "from", "to", "amt")
EDGE_SEMANTICS = "owner-net-greedy"
ORDER_GRANULARITY_TX = "transaction"
INSTR_INDEX_TX_NET = -1


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


def parse_owner_delta(record):
    """Return the legacy SQD owner delta tuple, or None for a skipped row.

    Batch 1 intentionally preserves ``postOwner or preOwner`` and the existing
    silent-skip behavior.  Owner-authority and collector failure semantics are
    tightened together in batch 2.
    """
    tx_index = record.get("transactionIndex")
    owner = record.get("postOwner") or record.get("preOwner")
    if not owner:
        return None
    try:
        amount = int(record.get("postAmount") or 0) - int(record.get("preAmount") or 0)
    except (ValueError, TypeError):
        return None
    if not amount:
        return None
    return tx_index, owner, amount


def soltx_cache_paths(mint, data_dir):
    """Resolve the case-sensitive sha256(mint) cache, meta and parts paths."""
    if not isinstance(mint, str):
        raise TypeError("mint must be a string")
    root = Path(data_dir)
    key = hashlib.sha256(mint.encode("utf-8")).hexdigest()
    return (root / f"soltx-{key}.jsonl.gz", root / f"soltx-{key}.meta.json",
            root / f"soltx-{key}.parts")
