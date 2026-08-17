"""Shared machine contract for legacy anchor-plan point shapes.

The legacy edge point has no machine-readable block-source field.  When the
plan schema is next revised, add ``balance_block_source=final_block`` and stop
depending on the human-facing ``kind`` text entirely.

Signing, construction, and deep validation all read fields inside the plan;
``date_range`` is an anchor embedded in the object being constrained.  This
contract therefore catches drift and internal errors, but cannot defend against
an adversary able to re-sign a replacement plan.  The external anchor lives at
execution: ``validate_semantic_replay`` and ``verify_recon`` couple the cutoff
across independently bound partitions.
"""

LEGACY_FINAL_BLOCK_EDGE_KIND = "门槛±10% 边缘地址"


def is_legacy_final_block_edge_point(point, family, plan):
    """Return whether *point* is the exact legacy forced final-block edge shape."""
    if not isinstance(point, dict) or not isinstance(plan, dict):
        return False
    date_range = plan.get("date_range")
    return (
        family == "forced_points"
        and point.get("kind") == LEGACY_FINAL_BLOCK_EDGE_KIND
        and bool(point.get("addr"))
        and point.get("expected_balance_raw") is not None
        and all(key not in point for key in ("day_end_block", "block", "tx"))
        and isinstance(date_range, list)
        and bool(date_range)
        and point.get("day") == date_range[-1]
    )
