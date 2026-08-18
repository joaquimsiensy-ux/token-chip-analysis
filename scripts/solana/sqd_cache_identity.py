"""Solana SQD cache v4/legacy meta 身份的共享 fail-closed 校验。"""

from __future__ import annotations

import re

from producer_history import historical_producer_hashes
from spl_edge_core import EDGE_SCHEMA_FIELDS, EDGE_SEMANTICS, ORDER_GRANULARITY_TX


SQD_CACHE_PROTOCOL = "sqd-solana-cache/v4"
SQD_COLLECTOR_ID = "fetch_sqd_transfers_v2.py/v4"
SQD_COLLECTOR_SCRIPT = "scripts/solana/fetch_sqd_transfers_v2.py"


def _valid_nonnegative_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def validate_cache_meta(meta: dict, mint: str, *, legacy_sol5: bool) -> tuple[int, int]:
    """验证 cache 身份；v4 逻辑摘要与行数由 collector 建立，消费端不得回填。"""
    frm = meta.get("from_slot")
    if legacy_sol5:
        upper = meta.get("collection_upper_slot")
        valid = (
            meta.get("schema") == "sqd-solana-cache/v3"
            and meta.get("mint") == mint
            and _valid_nonnegative_int(frm)
            and _valid_nonnegative_int(upper)
            and upper >= frm
        )
        if not valid:
            raise ValueError(
                "legacy-sol5 只接受绑定原始 mint/from_slot/collection_upper_slot 的 v3 meta"
            )
        return frm, upper

    upper = meta.get("finalized_upper_slot")
    valid = (
        meta.get("schema") == SQD_CACHE_PROTOCOL
        and meta.get("version") == 4
        and meta.get("mint") == mint
        and meta.get("collector") == SQD_COLLECTOR_ID
        and meta.get("edge_schema") == list(EDGE_SCHEMA_FIELDS)
        and meta.get("edge_semantics") == EDGE_SEMANTICS
        and meta.get("order_granularity") == ORDER_GRANULARITY_TX
        and meta.get("order_exact") is False
        and _valid_nonnegative_int(frm)
        and _valid_nonnegative_int(upper)
        and upper >= frm
    )
    if not valid:
        raise ValueError(
            "正式重放只接受绑定原始 mint、v4 边契约及 finalized_upper_slot 的 v4 meta"
        )

    digest = meta.get("edge_logical_sha256")
    rows = meta.get("edge_rows")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None \
            or isinstance(rows, bool) or not isinstance(rows, int) or rows <= 0:
        raise ValueError(
            "SQD v4 meta.edge_logical_sha256/edge_rows 为 collector 必填证据"
        )

    collector_sha256 = meta.get("collector_sha256")
    allowed_hashes = historical_producer_hashes(
        SQD_COLLECTOR_SCRIPT, SQD_CACHE_PROTOCOL
    )
    if collector_sha256 not in allowed_hashes:
        raise ValueError(
            "SQD v4 meta.collector_sha256 未命中 fetch_sqd_transfers_v2.py producer 登记"
        )
    return frm, upper
