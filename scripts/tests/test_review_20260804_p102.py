#!/usr/bin/env python3
"""P1-02: Filecoin official-address history must not silently stop at 5,000."""
from __future__ import annotations

import importlib.util
import json
import re
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FETCH = HERE.parent / "filecoin" / "fetch_data.py"


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, FETCH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def collect(total, drift=False):
    td = tempfile.TemporaryDirectory()
    root = Path(td.name)
    mod = load_module(f"filecoin_{total}_{drift}")
    mod.configure_data_dir(root / "data")
    mod.initialize_data_dirs()
    (Path(mod.DATA) / "official_scan.json").write_text(json.dumps({
        "f010": {"tag": {"name": "official"}}}), encoding="utf-8")

    def fake(url, retries=5):
        page = int(re.search(r"page=(\d+)", url).group(1))
        start = page * 100
        ids = list(range(start, min(start + 100, total)))
        if drift and page == 1:
            ids = [99] + ids[:-1]
        elif drift and page >= 2:
            ids = [x - 1 for x in ids]
            if page * 100 >= total:
                ids = [total - 1]
        return {"totalCount": total, "transfers": [{"cid": f"m{x}"} for x in ids]}

    mod.get_json = fake
    mod.fetch_official_transfers()
    obj = json.loads((Path(mod.OFFICIAL_DIR) / "f010_transfers.json").read_text())
    td.cleanup()
    return obj


def main():
    for total in (4999, 5000, 5001, 6000):
        obj = collect(total)
        assert obj["complete"] is True and obj["truncated"] is False, (total, obj)
        assert len(obj["transfers"]) == total, (total, len(obj["transfers"]))
    obj = collect(501, drift=True)
    assert obj["complete"] is True and len(obj["transfers"]) == 501
    assert len({x["cid"] for x in obj["transfers"]}) == 501
    assert obj["duplicate_count"] > 0
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        mod = load_module("filecoin_cap")
        mod.configure_data_dir(root / "data")
        mod.initialize_data_dirs()
        (Path(mod.DATA) / "official_scan.json").write_text(json.dumps({
            "f010": {"tag": {"name": "official"}}}))
        mod.MAX_OFFICIAL_PAGES = 1
        mod.get_json = lambda url, retries=5: {
            "totalCount": 101, "transfers": [{"cid": f"m{x}"} for x in range(100)]}
        try:
            mod.fetch_official_transfers()
        except RuntimeError:
            pass
        else:
            raise AssertionError("official hard cap must block")
        capped = json.loads((Path(mod.OFFICIAL_DIR) / "f010_transfers.json").read_text())
        assert capped["complete"] is False and capped["truncated"] is True
        assert capped["complete_reason"] == "official_page_cap"
    print("PASS: P1-02 Filecoin official history 4999/5000/5001/6000 + drift dedup")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
