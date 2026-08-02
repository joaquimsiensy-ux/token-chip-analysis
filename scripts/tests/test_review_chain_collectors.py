#!/usr/bin/env python3
"""2026-08-02 review regressions: H-07 through H-10."""
import gzip
import importlib.util
import json
import os
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
    mod.DATA = str(Path(tmp) / "data")
    mod.ADDR_DIR = str(Path(tmp) / "data" / "addr")
    Path(mod.ADDR_DIR).mkdir(parents=True)

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
        test_h10(tmp)
    print("PASS: H-07 HL identity/worklist, H-08 non-HYPE config, H-09 FIL failure, H-10 overlap/failure states")
    return 0


if __name__ == "__main__":
    sys.exit(main())
