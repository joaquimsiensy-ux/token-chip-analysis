"""wave-scan/v5 跨链正式顺序语义与 Solana 边源绑定的单一机器契约。"""

import re

WAVE_SCHEMA = "wave-scan/v5"
ORDER_GRANULARITY_TRANSACTION = "transaction"
ORDER_GRANULARITY_INSTRUCTION = "instruction"
ORDER_GRANULARITY_LOG = "log"
ORDER_GRANULARITY_SOURCE_DEFINED = "source-defined"

FORMAL_EDGE_ORDER_GRANULARITIES = frozenset(
    {
        ORDER_GRANULARITY_TRANSACTION,
        ORDER_GRANULARITY_INSTRUCTION,
        ORDER_GRANULARITY_LOG,
        ORDER_GRANULARITY_SOURCE_DEFINED,
    }
)


def has_formal_wave_semantics(report: dict) -> bool:
    """正式 wave 必须显式非 legacy，并声明全链允许的顺序粒度。"""
    base_valid = (
        report.get("schema") == WAVE_SCHEMA
        and report.get("non_formal") is False
        and isinstance(report.get("order_ambiguous"), bool)
        and report.get("edge_order_granularity") in FORMAL_EDGE_ORDER_GRANULARITIES
    )
    if not base_valid:
        return False
    params = report.get("params") or {}
    if not isinstance(params, dict):
        return False
    binding = report.get("edge_source_binding")
    if params.get("edges_sol"):
        if not isinstance(binding, dict) or set(binding) != {
                "cache_kind", "gid", "soltx_edges_sha256",
                "soltx_meta_sha256", "edge_logical_sha256"}:
            return False
        if binding.get("cache_kind") not in {"base", "repaired"}:
            return False
        if binding["cache_kind"] == "base" and binding.get("gid") is not None:
            return False
        if binding["cache_kind"] == "repaired" \
                and (not isinstance(binding.get("gid"), str)
                     or re.fullmatch(r"[0-9a-f]{16}", binding["gid"]) is None):
            return False
        return all(isinstance(binding.get(name), str)
                   and re.fullmatch(r"[0-9a-f]{64}", binding[name]) is not None
                   for name in ("soltx_edges_sha256", "soltx_meta_sha256",
                                "edge_logical_sha256"))
    if params.get("edges_evm_v2"):
        return "edge_source_binding" not in report
    return "edge_source_binding" not in report
