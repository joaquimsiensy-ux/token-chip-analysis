#!/usr/bin/env python3
"""第六轮批①：结构化回执、语义校验与 fail-closed 离线反例。"""
import csv
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/report"))
sys.path.insert(0, str(ROOT / "scripts/evm"))
sys.path.insert(0, str(ROOT / "scripts/solana"))
sys.path.insert(0, str(ROOT / "scripts/tests"))

from test_audit_release_gate import write_deep_recon_fixtures


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_shared_receipt_semantics(root):
    shared = load(ROOT / "scripts/report/shared_release_receipt.py", "sixlens_shared")
    root.mkdir(parents=True, exist_ok=True)
    target = {"chain": "bsc", "token": "0xtoken", "as_of_block": 123}
    fake = root / "fake.json"
    source = root / "source.txt"
    source.write_text("fixture\n", encoding="utf-8")
    write_json(fake, {"anything": True})
    item = {"status": "PASS", "exit_code": 0,
            "receipt": {"path": fake.name, "sha256": sha(fake)}}
    try:
        shared.validate_reconciliation_check(root, "balance", item, target, "evm")
    except ValueError as exc:
        assert "v2" in str(exc) or "schema" in str(exc), exc
    else:
        raise AssertionError("任意 JSON 伪回执被接受")

    good, _ = write_deep_recon_fixtures(root, target, source)
    write_json(fake, good)
    item["receipt"]["sha256"] = sha(fake)
    shared.validate_reconciliation_check(root, "balance", item, target, "evm")
    bad_target = dict(good, target={**target, "token": "0xother"})
    write_json(fake, bad_target); item["receipt"]["sha256"] = sha(fake)
    try:
        shared.validate_reconciliation_check(root, "balance", item, target, "evm")
    except ValueError:
        pass
    else:
        raise AssertionError("target 漂移被接受")
    bad_verdict = dict(good, verdict="FAIL", exit_code=2)
    write_json(fake, bad_verdict); item["receipt"]["sha256"] = sha(fake)
    try:
        shared.validate_reconciliation_check(root, "balance", item, target, "evm")
    except ValueError:
        pass
    else:
        raise AssertionError("wrapper PASS 与 receipt FAIL 矛盾被接受")


def recon_fixture(root, closed=True):
    cfg = root / "config.json"
    balances = root / "balances.json"
    stats = root / "stats.json"
    gmgn = root / "gmgn.csv"
    write_json(cfg, {"total_supply_human": 100, "decimals": 0,
                     "alchemy": {"url": "http://fixture/", "key": "key"},
                     "proxy": "", "token": "0xtoken"})
    write_json(balances, {"0x" + "1" * 40: 100 if closed else 90})
    write_json(stats, {"mint_total_wei": 100, "burn_total_wei": 0, "max_block": 123})
    with gmgn.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["address", "pct"]); w.writeheader()
        w.writerow({"address": "0x" + "1" * 40, "pct": "1"})
    return cfg, balances, stats, gmgn


def recon_args(paths, out):
    cfg, balances, stats, gmgn = paths
    return ["--config", str(cfg), "--balances", str(balances),
            "--replay-stats", str(stats), "--gmgn", str(gmgn),
            "--chain", "bsc", "--token", "0xtoken", "--end-block", "123",
            "--out", str(out)]


def test_verify_recon(root):
    mod = load(ROOT / "scripts/evm/verify_recon.py", "sixlens_verify_recon")
    pool = mock.Mock()
    pool.attest.return_value = 56
    paths = recon_fixture(root / "closed", closed=True)
    out = root / "closed" / "receipt.json"
    with mock.patch.object(mod, "attested_rpc_pool", return_value=pool), \
            mock.patch.object(mod, "rpc_balance_of", return_value=100):
        assert mod.main(recon_args(paths, out)) == 0
    receipt = json.loads(out.read_text())
    assert receipt["schema"] == "evm-reconciliation-receipt/v3"
    assert receipt["target"] == {"chain": "bsc", "token": "0xtoken", "as_of_block": 123}

    paths = recon_fixture(root / "supply-fail", closed=False)
    out = root / "supply-fail" / "receipt.json"
    with mock.patch.object(mod, "attested_rpc_pool", return_value=pool), \
            mock.patch.object(mod, "rpc_balance_of", return_value=90):
        assert mod.main(recon_args(paths, out)) == 2
    assert json.loads(out.read_text())["verdict"] == "FAIL"

    paths = recon_fixture(root / "balance-fail", closed=True)
    out = root / "balance-fail" / "receipt.json"
    with mock.patch.object(mod, "attested_rpc_pool", return_value=pool), \
            mock.patch.object(mod, "rpc_balance_of", return_value=99):
        assert mod.main(recon_args(paths, out)) == 2

    paths = recon_fixture(root / "rpc-fail", closed=True)
    out = root / "rpc-fail" / "receipt.json"
    with mock.patch.object(mod, "attested_rpc_pool", return_value=pool), \
            mock.patch.object(mod, "rpc_balance_of", side_effect=RuntimeError("rpc down")):
        assert mod.main(recon_args(paths, out)) == 1
    assert not out.exists()
    errors = list(out.parent.glob("receipt.error.*.json"))
    assert len(errors) == 1 and json.loads(errors[0].read_text())["verdict"] == "ERROR"


def test_anchor_sampler(root):
    work = root / "anchor"; work.mkdir()
    write_json(work / "config.json", {"mint": "mint1", "ref_slot": 10000, "ref_ts": 1767225600})
    old = Path.cwd(); os.chdir(work)
    try:
        mod = load(ROOT / "scripts/solana/anchor_sampler.py", "sixlens_anchor")
        args = ["--start", "2026-01-01", "--end", "2026-01-01",
                "--as-of-slot", "10000", "--out", str(work / "anchors.jsonl"),
                "--receipt", str(work / "anchor_receipt.json"), "--endpoint",
                "https://portal.sqd.dev/datasets/solana-mainnet/stream?api-key=SECRET#private"]
        with mock.patch.object(mod, "fetch_window", return_value=None), \
                mock.patch.object(mod.time, "sleep"):
            assert mod.main(args) != 0
        assert not (work / "anchor_receipt.json").exists()
        errors = list(work.glob("anchor_receipt.error.*.json"))
        assert len(errors) == 1 and json.loads(errors[0].read_text())["verdict"] == "ERROR"

        def no_converge(frm, to, endpoint):
            return [{"header": {"timestamp": 1, "number": frm}, "transactions": [],
                     "tokenBalances": []}]
        (work / "anchors.jsonl").unlink(missing_ok=True)
        with mock.patch.object(mod, "fetch_window", side_effect=no_converge):
            assert mod.main(args) != 0
        assert not (work / "anchor_receipt.json").exists()
        assert len(list(work.glob("anchor_receipt.error.*.json"))) == 2

        (work / "anchors.jsonl").unlink(missing_ok=True)
        with mock.patch.object(mod, "fetch_window", return_value=[]), \
                mock.patch.object(mod, "publish_txn", side_effect=OSError("disk full")):
            assert mod.main(args) == 1
        assert not (work / "anchor_receipt.json").exists(), "写回失败留下 PASS receipt"

        (work / "anchors.jsonl").unlink(missing_ok=True)
        with mock.patch.object(mod, "fetch_window", return_value=[]):
            assert mod.main(args) == 0
        receipt = json.loads((work / "anchor_receipt.json").read_text())
        row = json.loads((work / "anchors.jsonl").read_text())
        assert receipt["verdict"] == "PASS" and receipt["mode"] == "formal"
        assert {"path", "size", "sha256"} <= set(receipt["output"])
        assert {"chain", "mint", "endpoint", "as_of_slot"} <= set(row)
        assert row["chain"] == "solana" and row["mint"] == "mint1"
        assert row["endpoint"] == "https://portal.sqd.dev/datasets/solana-mainnet/stream"
        assert "api-key" not in (work / "anchors.jsonl").read_text()
        assert "SECRET" not in (work / "anchors.jsonl").read_text()
        validator = load(ROOT / "scripts/lib/receipt_validate.py", "sixlens_anchor_validator")
        assert validator.validate_receipt(receipt) == []
        shared = load(ROOT / "scripts/report/shared_release_receipt.py", "sixlens_anchor_shared")
        item = {"status": "PASS", "exit_code": 0,
                "receipt": {"path": "anchor_receipt.json",
                            "sha256": sha(work / "anchor_receipt.json")}}
        target = {"chain": "solana", "token": "mint1", "as_of_block": 10000}
        shared.validate_reconciliation_check(work, "balance", item, target, "solana")
        shared.validate_reconciliation_check(work, "time", item, target, "solana")

        (work / "anchor_receipt.json").unlink()
        variants = [
            {**row, "chain": "ethereum"},
            {**row, "mint": "other-mint"},
            {**row, "endpoint": "https://other.invalid"},
            {**row, "as_of_slot": 9999},
            {**row, "to_slot": 10001},
        ]
        for bad_row in variants:
            (work / "anchors.jsonl").write_text(json.dumps(bad_row) + "\n", encoding="utf-8")
            with mock.patch.object(mod, "fetch_window") as fetch:
                assert mod.main(args) == 2
            fetch.assert_not_called()
    finally:
        os.chdir(old)


def test_window_fetch(root):
    work = root / "window"; work.mkdir()
    write_json(work / "config.json", {"mint": "mint1"})
    old = Path.cwd(); os.chdir(work)
    try:
        mod = load(ROOT / "scripts/solana/window_fetch.py", "sixlens_window")
        out = work / "window.jsonl"; receipt = work / "window_receipt.json"
        args = ["0", "10", str(out), "--conc", "1", "--receipt", str(receipt)]

        reverse = work / "reverse.jsonl"; reverse_receipt = work / "reverse_receipt.json"
        assert mod.main(["10", "0", str(reverse), "--conc", "1",
                         "--receipt", str(reverse_receipt)]) == 2
        assert not reverse.exists() and not reverse_receipt.exists()
        negative = work / "negative.jsonl"; negative_receipt = work / "negative_receipt.json"
        assert mod.main(["-1", "0", str(negative), "--conc", "1",
                         "--receipt", str(negative_receipt)]) == 2
        assert not negative.exists() and not negative_receipt.exists()

        out.write_text("old-formal\n", encoding="utf-8")
        with mock.patch.object(mod, "scan_seg", return_value=([(1, 1, "a", "b", 1)], False, [1])):
            assert mod.main(args) == 2
        assert not out.exists() and Path(str(out) + ".partial").exists()
        failed_receipt = json.loads(receipt.read_text())
        assert failed_receipt["verdict"] == "FAIL"
        validator = load(ROOT / "scripts/lib/receipt_validate.py", "sixlens_window_validator")
        assert validator.validate_receipt(failed_receipt) == []
        stale = list(work.glob("window.jsonl.stale.*"))
        assert len(stale) == 1 and stale[0].read_text() == "old-formal\n"

        for p in (Path(str(out) + ".partial"), Path(str(out) + ".gaps.json"), receipt):
            if p.exists(): p.unlink()
        with mock.patch.object(mod, "scan_seg", return_value=([(1, 1, "a", "b", 1)], True, [1])):
            assert mod.main(args) == 0
        passed_receipt = json.loads(receipt.read_text())
        assert out.exists() and passed_receipt["verdict"] == "PASS"
        assert validator.validate_receipt(passed_receipt) == []

        out.unlink(); receipt.unlink()
        with mock.patch.object(mod, "scan_seg", return_value=([(1, 1, "a", "b", 1)], True, [1])), \
                mock.patch.object(mod, "publish_overwrite", side_effect=OSError("disk full")):
            assert mod.main(args) == 1
        assert not out.exists(), "receipt 写失败前已发布正式 window 文件"

        out.write_text("old-formal\n", encoding="utf-8")
        before = out.read_bytes()
        with mock.patch.object(mod, "scan_seg", return_value=([(1, 1, "a", "b", 1)], True, [1])), \
                mock.patch.object(mod, "publish_overwrite", side_effect=OSError("disk full")):
            assert mod.main(args) == 1
        assert out.read_bytes() == before, "刷新失败未恢复旧 window 正式文件"
    finally:
        os.chdir(old)


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        test_shared_receipt_semantics(root / "shared")
        test_verify_recon(root / "recon")
        test_anchor_sampler(root)
        test_window_fetch(root)
    print("PASS: 六视角批①结构化回执与 fail-closed")


if __name__ == "__main__":
    main()
