#!/usr/bin/env python3
"""Identity-bound descriptor for the Solana mainnet SQD dataset.

The R9 batch-3 collector calls this adapter before consuming its requested
range.  It fixes the dataset request identity and proves that the range is
anchored by the real ``SolanaAttestedSession`` trust root.
"""
from __future__ import annotations

from solana_attested_session import (SOLANA_MAINNET_GENESIS_HASH,
                                     SolanaAttestedSession)


SOLANA_SQD_DATASET_ID = "solana-mainnet"


class SolanaSqdDatasetAdapter:
    """Bind dataset id, mint and inclusive slot range to mainnet state."""

    def __init__(self, *, dataset_id, mint, from_slot, to_slot, state_session):
        if dataset_id != SOLANA_SQD_DATASET_ID:
            raise ValueError(
                f"SQD dataset_id must be {SOLANA_SQD_DATASET_ID!r}")
        if not isinstance(mint, str) or not mint.strip():
            raise ValueError("SQD target mint must be a non-empty string")
        for name, value in (("from_slot", from_slot), ("to_slot", to_slot)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise TypeError(f"SQD {name} must be a non-negative integer")
        if from_slot > to_slot:
            raise ValueError("SQD slot range must satisfy from_slot <= to_slot")
        if not isinstance(state_session, SolanaAttestedSession):
            raise TypeError("SQD state anchor requires SolanaAttestedSession")
        self.dataset_id = dataset_id
        self.mint = mint.strip()
        self.from_slot = from_slot
        self.to_slot = to_slot
        self.state_session = state_session
        self._state_anchor_slot = None

    @property
    def state_anchor_slot(self):
        return self._state_anchor_slot

    def attest_state_anchor(self):
        """Attest mainnet and prove the RPC head covers the dataset range."""
        slot = self.state_session.call("getSlot", [{"commitment": "finalized"}])
        if isinstance(slot, bool) or not isinstance(slot, int) or slot < 0:
            raise ValueError(f"Solana getSlot returned invalid anchor: {slot!r}")
        if self.state_session.observed_genesis != SOLANA_MAINNET_GENESIS_HASH:
            raise ValueError("Solana state session lacks verified mainnet genesis")
        if slot < self.to_slot:
            raise ValueError(
                f"Solana state anchor {slot} does not cover SQD to_slot {self.to_slot}")
        self._state_anchor_slot = slot
        return {
            "dataset_id": self.dataset_id,
            "mint": self.mint,
            "from_slot": self.from_slot,
            "to_slot": self.to_slot,
            "state_anchor_slot": slot,
            "state_genesis": self.state_session.observed_genesis,
        }
