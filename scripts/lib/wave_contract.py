"""wave-scan/v4 跨链正式顺序语义的单一机器契约。"""

WAVE_SCHEMA = "wave-scan/v4"
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
    return (
        report.get("schema") == WAVE_SCHEMA
        and report.get("non_formal") is False
        and isinstance(report.get("order_ambiguous"), bool)
        and report.get("edge_order_granularity") in FORMAL_EDGE_ORDER_GRANULARITIES
    )
