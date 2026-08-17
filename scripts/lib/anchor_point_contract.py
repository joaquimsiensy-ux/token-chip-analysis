"""Shared machine contracts for anchor-plan JSON and point shapes.

The v2 legacy edge point has no machine-readable block-source field.  V3 uses
``balance_block_source`` and never derives semantics from human-facing ``kind``.

Signing, construction, and deep validation all read fields inside the plan;
``date_range`` is an anchor embedded in the object being constrained.  This
contract therefore catches drift and internal errors, but cannot defend against
an adversary able to re-sign a replacement plan.  The external anchor lives at
execution: ``validate_semantic_replay`` and ``verify_recon`` couple the cutoff
across independently bound partitions.
"""
import json

LEGACY_FINAL_BLOCK_EDGE_KIND = "门槛±10% 边缘地址"
V2_SCHEMA = "anchor-plan/v2"
V3_SCHEMA = "anchor-plan/v3"
BALANCE_BLOCK_SOURCES = {"day_end_block", "final_block"}


def reject_duplicate_keys_object_pairs_hook(pairs):
    """Build one JSON object while rejecting duplicate keys at every depth."""
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key rejected: {key!r}")
        value[key] = item
    return value


def strict_json_loads(text, **kwargs):
    """Parse JSON with duplicate-key rejection while preserving caller options."""
    if "object_pairs_hook" in kwargs:
        raise TypeError("strict_json_loads owns object_pairs_hook")
    return json.loads(
        text,
        object_pairs_hook=reject_duplicate_keys_object_pairs_hook,
        **kwargs,
    )


def is_legacy_final_block_edge_point(point, family, plan):
    """Return whether *point* is the exact legacy forced final-block edge shape."""
    if not isinstance(point, dict) or not isinstance(plan, dict):
        return False
    if plan.get("schema") == V2_SCHEMA and "balance_block_source" in point:
        raise ValueError("v2 plan point carries v3 machine field")
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


def balance_block_source_of(point, family, plan):
    """Validate one v3 point and return its balance block source, or ``None`` for tx.

    Balance and transaction shapes are a strict XOR.  Key presence is checked
    deliberately: a forbidden key with a null value is still forbidden.
    """
    if not isinstance(point, dict) or not isinstance(plan, dict):
        raise ValueError("anchor-plan/v3 point and plan must be objects")
    if plan.get("schema") != V3_SCHEMA:
        raise ValueError("machine point contract requires anchor-plan/v3")
    if family not in {"matrix_points", "forced_points"}:
        raise ValueError(f"anchor-plan/v3 point family invalid: {family!r}")

    is_balance = (point.get("expected_balance_raw") is not None
                  and bool(point.get("addr")))
    is_tx = (bool(point.get("tx"))
             and point.get("expected_value_raw") is not None)
    if is_balance == is_tx:
        raise ValueError("anchor-plan/v3 point must match exactly one balance/tx shape")

    if is_balance:
        forbidden = [key for key in ("tx", "block", "expected_value_raw")
                     if key in point]
        if forbidden:
            raise ValueError(
                "anchor-plan/v3 balance point carries forbidden keys: "
                + ", ".join(forbidden))
        source = point.get("balance_block_source")
        if not isinstance(source, str) or source not in BALANCE_BLOCK_SOURCES:
            raise ValueError(
                f"anchor-plan/v3 balance_block_source invalid: {source!r}")
        if source == "day_end_block":
            block = point.get("day_end_block")
            if ("day_end_block" not in point or isinstance(block, bool)
                    or not isinstance(block, int) or block < 0):
                raise ValueError(
                    "anchor-plan/v3 day_end_block source requires a non-negative int "
                    "day_end_block")
        else:
            if family != "forced_points":
                raise ValueError(
                    "anchor-plan/v3 final_block source is allowed only in forced_points")
            forbidden = [key for key in ("day_end_block", "block", "tx")
                         if key in point]
            if forbidden:
                raise ValueError(
                    "anchor-plan/v3 final_block source carries forbidden keys: "
                    + ", ".join(forbidden))
            date_range = plan.get("date_range")
            if (not isinstance(date_range, list) or not date_range
                    or point.get("day") != date_range[-1]):
                raise ValueError(
                    "anchor-plan/v3 final_block source day must equal date_range[-1]")
        return source

    forbidden = [key for key in (
        "addr", "day_end_block", "expected_balance_raw", "balance_block_source"
    ) if key in point]
    if forbidden:
        raise ValueError(
            "anchor-plan/v3 tx point carries forbidden keys: " + ", ".join(forbidden))
    return None
