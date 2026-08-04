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


def make_formal_corpus(mod):
    root = Path(mod.DATA)
    mod.save(str(root / "overview.json"), {"ok": True})
    mod.save(str(root / "price_180d.json"), {"prices": [[1, 1]]})
    rich = [{"address": f"f1{i:03d}"} for i in range(200)]
    mod.save(str(root / "richlist.json"), rich)
    for row in rich:
        d = root / "addr" / row["address"]
        d.mkdir(parents=True)
        mod.save(str(d / "detail.json"), {"address": row["address"]})
        mod.save(str(d / "transfers_recent.json"),
                 {"complete": True, "complete_reason": "empty_page",
                  "truncated": False, "transfers": []})
        mod.save(str(d / "transfers_earliest.json"), {"complete": True, "transfers": []})
    return rich


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
    # Round4 P1-01：三张 PASS receipt 不能替代 top-200 主体文件。
    with tempfile.TemporaryDirectory() as td:
        mod = load("round4_unbound")
        mod.configure_data_dir(Path(td) / "data")
        mod.initialize_data_dirs()
        pagination = {"schema": "filecoin-richlist-pagination/v1", "status": "PASS",
                      "complete": True, "compared_count": 200}
        official = {"schema": "filecoin-official-scan/v1", "status": "PASS", "complete": True}
        transfers = {"schema": "filecoin-official-transfers/v1", "status": "PASS", "complete": True}
        for name, obj in (("richlist_pagination_receipt.json", pagination),
                          ("official_scan_receipt.json", official),
                          ("official_transfers_receipt.json", transfers)):
            mod.save(str(Path(mod.DATA) / name), obj)
        try:
            mod.write_collection_manifest(200, official, transfers)
        except RuntimeError as exc:
            assert "richlist.json" in str(exc) or "overview.json" in str(exc)
        else:
            raise AssertionError("missing formal top-200 corpus must BLOCK")
        assert not (Path(mod.DATA) / "collection_manifest.json").exists()

        # 同族变体：主体齐全后缺任一 top-200 文件也必须阻断。
        make_formal_corpus(mod)
        victim = Path(mod.DATA) / "addr" / "f1199" / "detail.json"
        victim.unlink()
        try:
            mod.write_collection_manifest(200, official, transfers)
        except RuntimeError as exc:
            assert "addr/f1199/detail.json" in str(exc)
        else:
            raise AssertionError("one missing top-200 file must BLOCK")
        mod.save(str(victim), {"address": "f1199"})

        # 失败分支：完成/截断元数据必须是 collector 实际字段，不接受字符串布尔。
        bad = Path(mod.DATA) / "addr" / "f1000" / "transfers_recent.json"
        mod.save(str(bad), {"complete": True, "complete_reason": "page_cap",
                            "truncated": "false", "transfers": []})
        try:
            mod.write_collection_manifest(200, official, transfers)
        except RuntimeError as exc:
            assert "completion fields invalid" in str(exc)
        else:
            raise AssertionError("invalid completion/truncation state must BLOCK")

    print("PASS: Filecoin smoke isolation + top-200 corpus/hash/completion manifest closure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
