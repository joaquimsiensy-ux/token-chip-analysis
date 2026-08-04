#!/usr/bin/env python3
"""D-09/D-11: one Filecoin window and executable pagination consistency proof."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
TARGET = HERE.parent / "filecoin" / "fetch_data.py"
spec = importlib.util.spec_from_file_location("filecoin_drift_target", TARGET)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def rows(start: int, count: int):
    return [{"address": f"f1{i:04d}", "balance": str(1000 - i)}
            for i in range(start, start + count)]


def main() -> int:
    as_of = datetime(2026, 8, 4, tzinfo=timezone.utc)
    mod.configure_window(as_of, 180)
    assert mod.WINDOW_DAYS == 180
    assert mod.CUTOFF == int(datetime(2026, 2, 5, tzinfo=timezone.utc).timestamp())
    assert mod.PRICE_DAYS == 180

    with tempfile.TemporaryDirectory() as td:
        mod.configure_data_dir(td)
        mod.initialize_data_dirs()

        def good_get(url):
            if "pageSize=100" in url:
                page = int(url.rsplit("page=", 1)[1])
                return {"richList": rows(page * 100, 100)}
            page = int(url.rsplit("page=", 1)[1])
            return {"richList": rows(page * 50, 50)}

        mod.get_json = good_get
        result = mod.fetch_richlist(200)
        assert len(result) == 200
        receipt = json.loads(Path(td, "richlist_pagination_receipt.json").read_text())
        assert receipt["status"] == "PASS" and receipt["compared_count"] == 200

    with tempfile.TemporaryDirectory() as td:
        mod.configure_data_dir(td)
        mod.initialize_data_dirs()

        def drifted_get(url):
            if "pageSize=100" in url:
                page = int(url.rsplit("page=", 1)[1])
                return {"richList": rows(page * 100, 100)}
            page = int(url.rsplit("page=", 1)[1])
            out = rows(page * 50, 50)
            if page == 1:
                out[0] = {"address": "f1DRIFT", "balance": "0"}
            return {"richList": out}

        mod.get_json = drifted_get
        try:
            mod.fetch_richlist(200)
        except RuntimeError as exc:
            assert "pagination" in str(exc).lower() or "分页" in str(exc)
        else:
            raise AssertionError("pageSize=50/100 mismatch was not rejected")

    print("PASS: D-09 shared 180-day window + D-11 executable rich-list cross-page proof")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
