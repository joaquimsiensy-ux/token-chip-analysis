#!/usr/bin/env python3
"""P1-03: Filecoin smoke runs cannot emit a formal PASS collection manifest."""
from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FETCH = HERE.parent / "filecoin" / "fetch_data.py"


def load(name):
    spec = importlib.util.spec_from_file_location(name, FETCH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def smoke(n):
    td = tempfile.TemporaryDirectory()
    root = Path(td.name)
    mod = load(f"smoke_{n}")
    mod.fetch_overview = lambda: None
    mod.fetch_price = lambda: None
    def fake_richlist(count):
        mod.save(str(Path(mod.DATA) / "richlist_pagination_receipt.json"),
                 {"schema": "filecoin-richlist-pagination/v1", "status": "PASS",
                  "complete": True, "compared_count": count})
        return [{"address": f"f1{x}"} for x in range(count)]
    mod.fetch_richlist = fake_richlist
    mod.fetch_address = lambda addr, rank: None
    mod.main(["--data-dir", str(root / "data"), "--smoke", str(n)])
    formal = root / "data" / "collection_manifest.json"
    receipt = root / "data" / "smoke_receipt.json"
    assert not formal.exists(), f"--smoke {n} must not emit formal collection_manifest.json"
    obj = json.loads(receipt.read_text())
    assert obj["status"] == "SMOKE" and obj["complete"] is False and obj["top_n"] == n
    td.cleanup()


def main():
    for n in (1, 10, 199):
        smoke(n)
    with tempfile.TemporaryDirectory() as td:
        mod = load("formal_missing")
        mod.configure_data_dir(Path(td) / "data")
        mod.initialize_data_dirs()
        try:
            mod.write_collection_manifest(200, None, None)
        except RuntimeError:
            pass
        else:
            raise AssertionError("top_n=200 without official receipts must BLOCK")
        assert not (Path(mod.DATA) / "collection_manifest.json").exists()
    print("PASS: P1-03 smoke 1/10/199 isolated; formal 200 requires all substage receipts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
