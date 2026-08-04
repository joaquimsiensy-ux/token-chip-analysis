#!/usr/bin/env python3
"""Round4c F-03: Solana identity evidence must replay raw GPA responses offline."""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOL = HERE.parent / "solana"
REPORT = HERE.parent / "report"
sys.path[:0] = [str(SOL), str(REPORT), str(HERE)]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def artifact(path):
    path = Path(path)
    return {"path": path.name, "size": path.stat().st_size, "sha256": sha(path)}


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj))


def test_attack_b_is_rejected():
    import scan_token_accounts as scan
    from identity_snapshot_receipt import emit_solana, validate_receipt
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        owners = root / "holders_owners.json"
        accounts = root / "holders_accounts.json"
        supply = root / "supply.json"
        raw = root / "scan_raw.json"
        scan_meta = root / "scan_meta.json"
        meta = root / "holders_snapshot_meta.json"
        write_json(owners, {"evilowner": 100})
        write_json(accounts, [])
        write_json(supply, {"result": {"context": {"slot": 123},
                                        "value": {"amount": "100", "decimals": 0}}})
        write_json(raw, {"result": {"context": {"slot": 123}, "value": []}})
        scan_claim = {"schema": "solana-gpa-cache-v2", "mint": "mint",
                      "program": scan.SPL, "rpc": "https://fixture", "filters": [],
                      "supply_observed_slot": 123, "gpa_response_slot": 123,
                      "account_count": 0}
        write_json(scan_meta, scan_claim)
        scan_claim = {**scan_claim, "raw_artifact": artifact(raw),
                      "meta_artifact": artifact(scan_meta)}
        write_json(meta, {"schema": "solana-holder-snapshot-v2", "mint": "mint",
                          "program": scan.SPL, "rpc": "https://fixture",
                          "supply_raw": "100", "sum_accounts_raw": "100",
                          "decimals": 0, "closed": True,
                          "producer": {"path": "scan_token_accounts.py",
                                       "sha256": sha(SOL / "scan_token_accounts.py")},
                          "supply_receipt": artifact(supply),
                          "outputs": {"holders_accounts": artifact(accounts),
                                      "holders_owners": artifact(owners)},
                          "scans": [scan_claim]})
        try:
            emit_solana("mint", 123, owners, meta, 100, root / "identity.json")
        except ValueError as exc:
            assert "offline replay" in str(exc)
        else:
            raise AssertionError("six handwritten self-consistent files must not emit Solana identity receipt")
        forged_receipt = root / "forged_identity.json"
        write_json(forged_receipt, {
            "schema": "identity-holder-snapshot/v2", "status": "PASS",
            "complete_owner_universe": True,
            "producer": {"path": "identity_snapshot_receipt.py",
                         "sha256": sha(REPORT / "identity_snapshot_receipt.py")},
            "adapter": "sol", "token": "mint", "as_of_block": 123,
            "total_supply_raw": "100",
            "snapshot": {"path": owners.name, "sha256": sha(owners)},
            "source": {"kind": "solana-token-accounts",
                       "snapshot_meta": {"path": meta.name, "sha256": sha(meta)},
                       "collector": {"path": "scan_token_accounts.py",
                                     "sha256": sha(SOL / "scan_token_accounts.py")}}})
        errors = validate_receipt(forged_receipt, owners, 100, "sol")
        assert any("offline replay" in error for error in errors), errors


def test_bound_owner_amount_tamper_is_rejected():
    from test_round4_identity_emitter import run_solana
    from identity_snapshot_receipt import emit_solana, validate_solana_source
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        owners, meta = run_solana(root)
        values = json.loads(owners.read_text())
        owner = next(iter(values))
        values[owner] += 1
        owners.write_text(json.dumps(values))
        meta_obj = json.loads(meta.read_text())
        meta_obj["outputs"]["holders_owners"] = artifact(owners)
        meta.write_text(json.dumps(meta_obj))
        for call in (lambda: validate_solana_source("mint", owners, meta, 100),
                     lambda: emit_solana("mint", 123, owners, meta, 100,
                                         owners.parent / "identity_tampered.json")):
            try:
                call()
            except ValueError as exc:
                assert "offline replay" in str(exc)
            else:
                raise AssertionError("owner amount tamper plus refreshed output hash must be rejected")



def test_supply_receipt_content_tamper_is_rejected():
    from test_round4_identity_emitter import run_solana
    from identity_snapshot_receipt import validate_solana_source
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        owners, meta = run_solana(root)
        meta_obj = json.loads(meta.read_text())
        supply = owners.parent / meta_obj["supply_receipt"]["path"]
        supply_obj = json.loads(supply.read_text())
        supply_obj["result"]["value"]["amount"] = "999"
        supply.write_text(json.dumps(supply_obj))
        meta_obj["supply_receipt"] = artifact(supply)
        meta.write_text(json.dumps(meta_obj))
        try:
            validate_solana_source("mint", owners, meta, 100)
        except ValueError as exc:
            assert "supply receipt" in str(exc)
        else:
            raise AssertionError("refreshed hash must not hide forged getTokenSupply amount")


def test_cross_scan_pubkey_dedup_uses_canonical_parser():
    import base64
    from scan_token_accounts import parse_token_accounts
    raw = base64.b64encode(bytes(range(32)) + (100).to_bytes(8, "little")).decode()
    account = {"pubkey": "same", "account": {"data": [raw, "base64"]}}
    unique, rows, owners, malformed = parse_token_accounts([account, account])
    assert len(unique) == 1 and len(rows) == 1 and sum(owners.values()) == 100
    assert malformed == 0

def main():
    test_attack_b_is_rejected()
    test_bound_owner_amount_tamper_is_rejected()
    test_supply_receipt_content_tamper_is_rejected()
    test_cross_scan_pubkey_dedup_uses_canonical_parser()
    print("PASS: raw GPA replay rejects six-file/owner/supply forgeries; pubkey dedup preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
