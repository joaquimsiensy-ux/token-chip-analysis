#!/usr/bin/env python3
"""2026-08-02 review regressions: H-07 through H-10."""
import gzip
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
HL = ROOT / "hyperliquid"
FIL = ROOT / "filecoin"
RH = ROOT / "robinhood"
sys.path.insert(0, str(RH))
from resume_guard import bind_output, overlap_state, require_fetch_success, require_progress


def run(cmd, cwd):
    return subprocess.run([sys.executable] + [str(x) for x in cmd], cwd=cwd,
                          capture_output=True, text=True)


def hl_config(data, symbol="FOO"):
    return {"token_symbol": symbol, "token_id": "token-id", "candle_coin": "@1",
            "tge_ms": 1, "snapshot_start_s": 1,
            "entities": {"team": "0x" + "1" * 40}, "team_entity": "team",
            "fills_recent_entity": "", "evm_bridge": "0x" + "2" * 40,
            "watch": {}, "summary_fund": "", "summary_cols": {},
            "data_dir": str(data), "out_dir": str(Path(data).parent / "out"),
            "system_addresses": ["0x" + "0" * 40], "asset_type": "spot",
            "cex_keywords": ["CEX"], "min_transfer_amount": 1,
            "genesis_min_amount": 1, "genesis_window_days": 1}


def test_h07_h08(tmp):
    data = Path(tmp) / "hl_data"
    (data / "static").mkdir(parents=True)
    (data / "addresses").mkdir()
    (data / "static" / "global_aliases.json").write_text("{}")
    (data / "static" / "holders.json").write_text(json.dumps({"holders": {}}))
    (data / "static" / "token_details.json").write_text(json.dumps(
        {"circulatingSupply": 100, "genesis": {"userBalances": []}}))
    (data / "worklist.json").write_text(json.dumps({"count": 0, "team_recv": [], "addresses": []}))
    cfg = Path(tmp) / "foo.json"
    cfg.write_text(json.dumps(hl_config(data)))
    p = run([HL / "collect.py", "--config", cfg, "addresses"], tmp)
    assert p.returncode == 0, p.stdout + p.stderr
    receipt = json.loads((data / "addresses_receipt.json").read_text())
    assert receipt["status"] == "PASS" and receipt["token_symbol"] == "FOO"
    changed = Path(tmp) / "bar.json"
    changed.write_text(json.dumps(hl_config(data, "BAR")))
    p = run([HL / "collect.py", "--config", changed, "addresses"], tmp)
    assert p.returncode != 0 and "不一致" in (p.stdout + p.stderr)

    p = run([HL / "main_metrics.py", "--config", cfg, "--no-labels"], tmp)
    assert p.returncode == 0, p.stdout + p.stderr
    assert (Path(tmp) / "out" / "clusters.json").exists()


def test_h09(tmp):
    spec = importlib.util.spec_from_file_location("filecoin_fetch", FIL / "fetch_data.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.configure_data_dir(Path(tmp) / "data")
    mod.initialize_data_dirs()

    def fake(url, retries=5):
        if "/transfers" in url:
            return {"_error": url}
        return {"address": "f1test"}

    mod.get_json = fake
    try:
        mod.fetch_address("f1test", 1)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Filecoin page failure must propagate")
    assert not (Path(mod.ADDR_DIR) / "f1test" / "transfers_recent.json").exists()

    # P1-04：161 个官方 ID 任一网络失败都不得落 complete/PASS，重跑须补查失败项。
    calls = []

    def official_fail(url, retries=5):
        aid = url.rsplit("/", 1)[-1]
        calls.append(aid)
        if aid == "f042":
            return {"_error": url}
        return {"address": aid}

    mod.get_json = official_fail
    try:
        mod.fetch_official_scan()
    except RuntimeError:
        pass
    else:
        raise AssertionError("official scan network failure must block")
    receipt_path = Path(mod.DATA) / "official_scan_receipt.json"
    receipt = json.loads(receipt_path.read_text())
    assert receipt["status"] == "BLOCK" and receipt["counts"]["failed"] == 1
    assert not (Path(mod.DATA) / "official_scan.json").exists()

    calls.clear()
    mod.get_json = lambda url, retries=5: (calls.append(url.rsplit("/", 1)[-1])
                                           or {"address": url.rsplit("/", 1)[-1]})
    receipt = mod.fetch_official_scan()
    assert receipt["status"] == "PASS" and calls == ["f042"], calls
    transfers_receipt = {"schema": "filecoin-official-transfers/v1",
                         "status": "PASS", "complete": True,
                         "addresses": 0, "outputs": []}
    (Path(mod.DATA) / "official_transfers_receipt.json").write_text(
        json.dumps(transfers_receipt))
    manifest = mod.write_collection_manifest(200, receipt, transfers_receipt)
    ref = manifest["substage_receipts"]["official_scan"]
    assert ref["path"] == "official_scan_receipt.json" and len(ref["sha256"]) == 64


def test_p202_import_and_data_dir(tmp):
    probe = Path(tmp) / "import_probe"
    probe.mkdir()
    copied = probe / "fetch_data.py"
    shutil.copy2(FIL / "fetch_data.py", copied)
    p = subprocess.run(
        [sys.executable, "-c",
         "import importlib.util; "
         "s=importlib.util.spec_from_file_location('probe_fetch', 'fetch_data.py'); "
         "m=importlib.util.module_from_spec(s); s.loader.exec_module(m)"],
        cwd=probe, capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    assert not (probe / "data").exists(), "import 不得创建 data 目录"

    spec = importlib.util.spec_from_file_location("filecoin_fetch_injected",
                                                  FIL / "fetch_data.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    target = Path(tmp) / "injected_data"
    mod.configure_data_dir(target)
    assert Path(mod.DATA) == target.resolve()
    assert not target.exists(), "配置注入本身不得写盘"
    mod.initialize_data_dirs()
    assert (target / "addr").is_dir() and (target / "official").is_dir()


def test_h10(tmp):
    out = str(Path(tmp) / "events.jsonl.gz")
    identity = {"collector": "fixture", "token": "0x1", "query_schema": "q"}
    bind_output(out, identity)
    with gzip.open(out, "wt") as f:
        f.write(json.dumps({"block": 7, "tx": "a", "logi": 0}) + "\n")
        f.write(json.dumps({"block": 7, "tx": "b", "logi": 1}) + "\n")
    start, keys, count = overlap_state(out, ("block", "tx", "logi"))
    assert start == 7 and count == 2 and keys == {(7, "a", 0), (7, "b", 1)}
    try:
        require_progress(7, 7, 10)
    except RuntimeError:
        pass
    else:
        raise AssertionError("stalled next_block must reject")
    try:
        require_fetch_success(False, None)
    except RuntimeError:
        pass
    else:
        raise AssertionError("network failure must not become EMPTY/done")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        test_h07_h08(tmp)
    with tempfile.TemporaryDirectory() as tmp:
        test_h09(tmp)
    with tempfile.TemporaryDirectory() as tmp:
        test_p202_import_and_data_dir(tmp)
    with tempfile.TemporaryDirectory() as tmp:
        test_h10(tmp)
    print("PASS: H-07/H-08/H-09/H-10 + P1-04 official-scan + P2-02 import side effects")
    return 0


if __name__ == "__main__":
    sys.exit(main())
