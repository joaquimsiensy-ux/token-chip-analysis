#!/usr/bin/env python3
"""R9 batch-3 Solana observation protocol and nine fail-closed variants."""
from __future__ import annotations

import base64
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/lib"))

from solana_attested_session import (SOLANA_MAINNET_GENESIS_HASH,
                                     SolanaAttestedSession)  # noqa: E402

MINT = "CreiuhfwdWCN5mJbMJtA9bBpYQrQF2tCBuZwSPWfpump"
PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"


def mint_bytes(supply=100, decimals=0, marker=0):
    raw = bytearray(82)
    raw[36:44] = int(supply).to_bytes(8, "little")
    raw[44] = decimals
    raw[45] = 1
    raw[81] = marker
    return bytes(raw)


def token_account_bytes(amount=100):
    return bytes(32) + int(amount).to_bytes(8, "little")


def readonly_tx(signature="sig-1"):
    return {
        "slot": 103,
        "meta": {"err": None, "loadedAddresses": {"writable": [], "readonly": []}},
        "transaction": {"signatures": [signature], "message": {
            "accountKeys": ["payer", MINT],
            "header": {"numRequiredSignatures": 1, "numReadonlySignedAccounts": 0,
                       "numReadonlyUnsignedAccounts": 1},
        }},
    }


def writable_tx(signature="sig-1", *, loaded=False):
    tx = readonly_tx(signature)
    if loaded:
        tx["transaction"]["message"]["accountKeys"] = ["payer"]
        tx["transaction"]["message"]["header"]["numReadonlyUnsignedAccounts"] = 0
        tx["meta"]["loadedAddresses"]["writable"] = [MINT]
    else:
        tx["transaction"]["message"]["header"]["numReadonlyUnsignedAccounts"] = 0
    return tx


class SolanaTransportFake:
    """Monotonic Solana JSON-RPC transport; no production business logic is replaced."""

    def __init__(self, *, genesis=SOLANA_MAINNET_GENESIS_HASH, activity="full",
                 mutate_mint=False, writable=False, incomplete=False,
                 supply_slot_early=False, gpa_total=100, mint_supply=100,
                 supply_amount=100, parsed_slot_early=False,
                 gpa_slot_early=False, pre_slot_ignores_min=False,
                 supply_early_attempts=0):
        self.genesis = genesis
        self.activity = activity
        self.mutate_mint = mutate_mint
        self.writable = writable
        self.incomplete = incomplete
        self.supply_slot_early = supply_slot_early
        self.gpa_total = gpa_total
        self.mint_supply = mint_supply
        self.supply_amount = supply_amount
        self.parsed_slot_early = parsed_slot_early
        self.gpa_slot_early = gpa_slot_early
        self.pre_slot_ignores_min = pre_slot_ignores_min
        self.supply_early_attempts = supply_early_attempts
        self.calls = []
        self.business_calls = 0
        self.slot = 100
        self.raw_reads = 0
        self.signature_pages = 0
        self.supply_calls = 0

    def _slot(self, config=None):
        minimum = int((config or {}).get("minContextSlot", 0))
        self.slot = max(self.slot + 1, minimum)
        return self.slot

    def __call__(self, _endpoint, payload, _timeout):
        method = payload["method"]
        params = payload.get("params") or []
        self.calls.append((method, params))
        if method == "getGenesisHash":
            return {"result": self.genesis}
        self.business_calls += 1
        if method == "getAccountInfo":
            config = params[1]
            slot = self._slot(config)
            if config.get("encoding") == "jsonParsed":
                if self.parsed_slot_early:
                    slot = 100
                value = {"owner": PROGRAM, "data": {"parsed": {"type": "mint", "info": {
                    "mintAuthority": None, "freezeAuthority": None,
                    "supply": str(self.mint_supply), "decimals": 0,
                }}}}
            else:
                self.raw_reads += 1
                if self.pre_slot_ignores_min and self.raw_reads % 2 == 1:
                    slot = 5
                    self.slot = slot
                marker = 1 if self.mutate_mint and self.raw_reads >= 2 else 0
                raw = mint_bytes(self.mint_supply, marker=marker)
                value = {"owner": PROGRAM,
                         "data": [base64.b64encode(raw).decode(), "base64"]}
            return {"result": {"context": {"slot": slot}, "value": value}}
        if method == "getProgramAccounts":
            config = params[1]
            slot = self._slot(config)
            if self.gpa_slot_early:
                slot = 101
            raw = token_account_bytes(self.gpa_total)
            return {"result": {"context": {"slot": slot}, "value": [{
                "pubkey": "Account1", "account": {
                    "data": [base64.b64encode(raw).decode(), "base64"]},
            }]}}
        if method == "getSignaturesForAddress":
            self.signature_pages += 1
            if self.activity == "zero":
                return {"result": []}
            if self.activity == "rpc-pressure":
                if self.signature_pages > 251:
                    raise RuntimeError("fixture RPC budget sentinel")
                return {"result": [{
                    "signature": f"future-{self.signature_pages}-{i}",
                    "slot": self.slot + 100, "err": None,
                } for i in range(1000)]}
            if self.incomplete and self.signature_pages > 1:
                raise RuntimeError("fixture pagination interrupted")
            if self.activity == "light":
                rows = [{"signature": f"sig-{i}", "slot": self.slot, "err": None}
                        for i in range(201)]
            elif self.activity == "downgrade":
                rows = [{"signature": f"sig-{i}", "slot": self.slot, "err": None}
                        for i in range(60)]
            elif self.incomplete:
                rows = ([{"signature": f"sig-{i}", "slot": self.slot, "err": None}
                         for i in range(200)]
                        + [{"signature": f"future-{i}", "slot": self.slot + 100,
                            "err": None} for i in range(800)])
            else:
                rows = [{"signature": "sig-1", "slot": self.slot, "err": None},
                        {"signature": "old", "slot": max(0, self.slot - 10), "err": None}]
            return {"result": rows}
        if method == "getTransaction":
            signature = params[0]
            tx = writable_tx(signature) if self.writable else readonly_tx(signature)
            return {"result": tx}
        if method == "getTokenSupply":
            self.supply_calls += 1
            early = self.supply_slot_early or self.supply_calls <= self.supply_early_attempts
            slot = 101 if early else self._slot()
            return {"result": {"context": {"slot": slot}, "value": {
                "amount": str(self.supply_amount), "decimals": 0,
            }}}
        if method == "getSlot":
            self.slot = max(self.slot + 1, 1000)
            return {"result": self.slot}
        raise AssertionError(f"unexpected RPC method: {method}")


def session(fake):
    return SolanaAttestedSession("fixture://solana", request_json=fake, timeout=1)


def observe(fake, **kwargs):
    from solana_observation import observe_snapshot
    return observe_snapshot(session(fake), MINT, PROGRAM, max_attempts=1, **kwargs)


def expect_error(fake, needle=None):
    try:
        observe(fake)
    except Exception as exc:
        if needle:
            assert needle.lower() in str(exc).lower(), str(exc)
        return
    raise AssertionError("invalid observation was accepted")


def test_wrong_genesis_zero_business():
    fake = SolanaTransportFake(genesis="wrong")
    expect_error(fake, "genesis")
    assert fake.business_calls == 0


def test_monotonic_full_and_light_modes():
    full, accounts = observe(SolanaTransportFake(activity="full"))
    assert full["activity"]["mode"] == "complete"
    assert full["activity"]["complete"] is True
    assert full["snapshot"]["slot"] >= full["mint_pre"]["slot"]
    assert full["mint_post"]["slot"] >= full["snapshot"]["slot"]
    assert len(accounts) == 1
    light_fake = SolanaTransportFake(activity="light")
    light, _ = observe(light_fake)
    assert light["activity"]["mode"] == "lightweight"
    assert light["activity"]["sample_size"] == 50
    assert light["activity"]["complete"] is False
    signature_call = next(call for call in light_fake.calls
                          if call[0] == "getSignaturesForAddress")
    assert signature_call[1][1]["limit"] > 200
    assert "no intermediate" not in json.dumps(light).lower()


def test_declared_slot_is_assertion_not_observation():
    from solana_observation import assert_declared_slot
    assert_declared_slot(None, 999, "--as-of-slot")
    assert_declared_slot(999, 999, "--as-of-slot")
    try:
        assert_declared_slot(77, 999, "--as-of-slot")
    except ValueError as exc:
        assert "77" in str(exc) and "999" in str(exc)
    else:
        raise AssertionError("declared slot mismatch accepted")


def test_mint_pre_post_change_rejected():
    expect_error(SolanaTransportFake(mutate_mint=True), "changed")


def test_json_parsed_slot_cannot_precede_raw_pre():
    expect_error(SolanaTransportFake(parsed_slot_early=True), "jsonparsed")


def test_gpa_slot_cannot_precede_json_parsed_floor():
    expect_error(SolanaTransportFake(gpa_slot_early=True), "gpa")


def test_pre_slot_must_honor_cli_min_context_slot():
    try:
        observe(SolanaTransportFake(pre_slot_ignores_min=True), min_context_slot=1_000_000)
    except Exception as exc:
        assert "min_context_slot" in str(exc)
    else:
        raise AssertionError("node response below min_context_slot was accepted")


def test_complete_pagination_incomplete_rejected():
    expect_error(SolanaTransportFake(incomplete=True), "incomplete")


def test_writable_mutation_rejected_in_both_modes():
    expect_error(SolanaTransportFake(writable=True), "writable")
    expect_error(SolanaTransportFake(activity="light", writable=True), "writable")


def test_supply_context_before_snapshot_rejected():
    expect_error(SolanaTransportFake(supply_slot_early=True), "supply")


def test_supply_context_lag_is_retryable():
    fake = SolanaTransportFake(supply_early_attempts=1)
    from solana_observation import observe_snapshot
    core, _ = observe_snapshot(session(fake), MINT, PROGRAM, max_attempts=2)
    assert core["attempt"] == 2
    assert fake.supply_calls == 2


def test_three_way_supply_closure_rejected():
    expect_error(SolanaTransportFake(gpa_total=99), "closure")
    expect_error(SolanaTransportFake(supply_amount=99), "closure")


def test_writable_parser_static_and_loaded_addresses():
    from solana_observation import mint_is_writable
    assert mint_is_writable(readonly_tx(), MINT) is False
    assert mint_is_writable(writable_tx(), MINT) is True
    assert mint_is_writable(writable_tx(loaded=True), MINT) is True


def test_writable_parser_fails_closed_on_unresolved_lookup_table():
    from solana_observation import mint_is_writable
    tx = readonly_tx("lookup-missing")
    tx["transaction"]["message"]["accountKeys"] = ["payer"]
    tx["transaction"]["message"]["header"]["numReadonlyUnsignedAccounts"] = 0
    tx["transaction"]["message"]["addressTableLookups"] = [{
        "accountKey": "LookupTable", "writableIndexes": [0], "readonlyIndexes": [],
    }]
    tx["meta"].pop("loadedAddresses")
    try:
        mint_is_writable(tx, MINT)
    except Exception as exc:
        assert "loadedaddresses" in str(exc).lower()
    else:
        raise AssertionError("unresolved address lookup was treated as readonly")


def test_explicit_readonly_cannot_override_header_writable():
    from solana_observation import mint_is_writable
    tx = writable_tx("lying-explicit")
    tx["transaction"]["message"]["accountKeys"] = [
        {"pubkey": "payer", "writable": True, "signer": True},
        {"pubkey": MINT, "writable": False, "signer": False},
    ]
    assert mint_is_writable(tx, MINT) is True


def test_complete_zero_reference_coverage_is_explicit():
    core, _ = observe(SolanaTransportFake(activity="zero"))
    activity = core["activity"]
    assert activity["mode"] == "complete" and activity["sample_size"] == 0
    statement = activity["coverage_statement"].lower()
    assert "zero" in statement or "0" in statement
    assert "all successful referenced transactions" not in statement


def test_activity_rpc_budget_switches_before_call_251():
    full, _ = observe(SolanaTransportFake(activity="rpc-pressure"))
    assert full["activity"]["mode"] == "lightweight"
    assert full["activity"]["rpc_calls"] <= 250


class DeadlineClock:
    def __init__(self, flip):
        self.flip = flip
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return 0.0 if self.calls <= self.flip else 999.0


def test_mid_scan_lightweight_downgrade_never_publishes_over_limit():
    scan = _load(ROOT / "scripts/solana/scan_token_accounts.py", "r9_b3_scan_downgrade")
    with tempfile.TemporaryDirectory(prefix="r9-b3-scan-downgrade-") as raw:
        case = Path(raw).resolve()
        old = Path.cwd()
        os.chdir(case)
        try:
            with mock.patch("solana_observation.time.monotonic", DeadlineClock(58)):
                rc = scan.main([
                    MINT, "--program", "spl", "--rpc", "fixture://solana",
                    "--out", "snapshot.json", "--bundle", "bundle.json",
                    "--work-dir", "data",
                ], request_json=SolanaTransportFake(activity="downgrade"))
            if rc == 0:
                bundle = json.loads((case / "bundle.json").read_text())
                assert bundle["activity"]["mode"] == "lightweight"
                assert bundle["activity"]["sample_size"] <= 50
            else:
                assert not (case / "bundle.json").exists()
                assert not (case / "snapshot.json").exists()
        finally:
            os.chdir(old)


def test_scan_rejects_gpa_below_parsed_before_formal_publish():
    scan = _load(ROOT / "scripts/solana/scan_token_accounts.py", "r9_b3_scan_gpa_floor")
    with tempfile.TemporaryDirectory(prefix="r9-b3-scan-gpa-floor-") as raw:
        case = Path(raw).resolve()
        old = Path.cwd()
        os.chdir(case)
        try:
            rc = scan.main([
                MINT, "--program", "spl", "--rpc", "fixture://solana",
                "--out", "snapshot.json", "--bundle", "bundle.json",
                "--work-dir", "data",
            ], request_json=SolanaTransportFake(gpa_slot_early=True))
            assert rc != 0
            assert not (case / "bundle.json").exists()
            assert not (case / "snapshot.json").exists()
        finally:
            os.chdir(old)


def test_scan_runs_in_memory_bundle_validator_before_publish():
    scan = _load(ROOT / "scripts/solana/scan_token_accounts.py", "r9_b3_scan_self_validate")
    with tempfile.TemporaryDirectory(prefix="r9-b3-scan-self-validate-") as raw:
        case = Path(raw).resolve()
        old = Path.cwd()
        os.chdir(case)
        try:
            with mock.patch.object(
                    scan, "validate_observation_bundle",
                    side_effect=ValueError("injected producer-validator disagreement")) as validate:
                rc = scan.main([
                    MINT, "--program", "spl", "--rpc", "fixture://solana",
                    "--out", "snapshot.json", "--bundle", "bundle.json",
                    "--work-dir", "data",
                ], request_json=SolanaTransportFake())
            assert validate.call_count == 1
            assert rc != 0
            assert not (case / "bundle.json").exists()
            assert not (case / "snapshot.json").exists()
            assert list(case.glob("bundle.error.*.json"))
        finally:
            os.chdir(old)


def test_bundle_hashes_are_deterministic():
    from solana_observation import canonical_json_sha256
    fake = SolanaTransportFake()
    bundle, _ = observe(fake)
    assert bundle["snapshot"]["accounts_sha256"]
    assert bundle["mint_pre"]["raw_sha256"] == bundle["mint_post"]["raw_sha256"]
    assert canonical_json_sha256({"b": 1, "a": 2}) == hashlib.sha256(
        b'{"a":2,"b":1}').hexdigest()


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_scan_cli_assertion_quarantines_old_marker():
    scan = _load(ROOT / "scripts/solana/scan_token_accounts.py", "r9_b3_scan_cli")
    with tempfile.TemporaryDirectory(prefix="r9-b3-scan-") as raw:
        case = Path(raw).resolve()
        old = Path.cwd()
        os.chdir(case)
        try:
            common = [MINT, "--program", "spl", "--rpc", "fixture://solana",
                      "--out", "snapshot.json", "--bundle", "bundle.json",
                      "--work-dir", "data"]
            assert scan.main(common, request_json=SolanaTransportFake()) == 0
            produced = json.loads((case / "bundle.json").read_text())
            observed = produced["snapshot"]["slot"]
            assert produced["as_of_slot"] == observed
            assert produced["as_of_block"] == observed
            assert produced["observed_context_slot"] == observed
            assert observed != 77
            rc = scan.main([*common, "--as-of-slot", "77"],
                           request_json=SolanaTransportFake())
            assert rc != 0
            assert not (case / "bundle.json").exists()
            assert not (case / "snapshot.json").exists()
            errors = list(case.glob("bundle.error.*.json"))
            assert errors
            error_receipt = json.loads(errors[0].read_text())
            assert error_receipt["target"]["as_of_block"] == observed
            assert list(case.glob("bundle.json.stale.*"))
            assert list(case.glob("snapshot.json.stale.*"))
        finally:
            os.chdir(old)


def test_scan_error_receipt_and_stderr_redact_endpoint_query():
    scan = _load(ROOT / "scripts/solana/scan_token_accounts.py", "r9_b3_scan_secret")
    endpoint = "https://mainnet.helius-rpc.com/v1?api-key=SECRET#private"

    def fail_transport(_endpoint, _payload, _timeout):
        raise OSError(f"transport rejected {_endpoint}")

    with tempfile.TemporaryDirectory(prefix="r9-b3-scan-secret-") as raw:
        case = Path(raw).resolve()
        old = Path.cwd()
        os.chdir(case)
        try:
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                rc = scan.main([
                    MINT, "--program", "spl", "--rpc", endpoint,
                    "--out", "snapshot.json", "--bundle", "bundle.json",
                    "--work-dir", "data",
                ], request_json=fail_transport)
            errors = list(case.glob("bundle.error.*.json"))
            assert rc != 0 and errors
            persisted = errors[0].read_text(encoding="utf-8")
            for rendered in (stderr.getvalue(), persisted):
                assert "api-key" not in rendered
                assert "SECRET" not in rendered
                assert "#private" not in rendered
        finally:
            os.chdir(old)


def test_sqd_dataset_mint_and_slot_scope_rejected():
    from solana_sqd_dataset import SolanaSqdDatasetAdapter

    state = session(SolanaTransportFake())
    invalid = (
        {"dataset_id": "solana-devnet", "mint": MINT, "from_slot": 1, "to_slot": 2},
        {"dataset_id": "solana-mainnet", "mint": "", "from_slot": 1, "to_slot": 2},
        {"dataset_id": "solana-mainnet", "mint": MINT, "from_slot": 3, "to_slot": 2},
    )
    for kwargs in invalid:
        try:
            SolanaSqdDatasetAdapter(state_session=state, **kwargs)
        except (TypeError, ValueError):
            pass
        else:
            raise AssertionError(f"invalid SQD scope accepted: {kwargs}")


def test_sqd_collector_rejects_bad_scope_before_run():
    collector = _load(
        ROOT / "scripts/solana/fetch_sqd_transfers_v2.py", "r9_b3_sqd_collector")
    secret_endpoint = "https://portal.sqd.dev/v2/FAKEKEY123"
    safe_identity = collector.cache_identity(MINT, secret_endpoint)
    assert "FAKEKEY123" not in json.dumps(safe_identity), safe_identity
    assert collector.cache_identity_matches(
        {**safe_identity, "finalized_upper_slot": 10}, MINT, secret_endpoint)
    legacy_meta = {
        "schema": "sqd-solana-cache/v3", "version": 3, "mint": MINT,
        "endpoint": secret_endpoint,
        "collector": "fetch_sqd_transfers_v2.py/v3",
        "collection_upper_slot": 10,
    }
    normalized = collector.normalize_cache_identity(legacy_meta, MINT, secret_endpoint)
    assert normalized is None, normalized
    cases = (
        [MINT, "--dataset-id", "solana-devnet"],
        ["", "--dataset-id", "solana-mainnet"],
        [MINT, "--from-slot", "3", "--to-slot", "2"],
    )
    with mock.patch.object(
            collector, "run", side_effect=AssertionError("SQD run was reached")) as run:
        for argv in cases:
            try:
                collector.main(argv, request_json=SolanaTransportFake())
            except (ValueError, SystemExit):
                pass
            else:
                raise AssertionError(f"invalid collector scope accepted: {argv}")
    assert run.call_count == 0

    with tempfile.TemporaryDirectory(prefix="r9-b3-sqd-scope-") as raw:
        old = Path.cwd()
        os.chdir(raw)
        try:
            _, meta, _ = collector.cache_paths(MINT)
            meta.parent.mkdir(parents=True, exist_ok=True)
            identity = collector.cache_identity(MINT, "fixture://sqd")
            meta.write_text(json.dumps({**identity, "version": 4,
                                        "mint": "wrong-mint",
                                        "finalized_upper_slot": 10}))
            with mock.patch.object(collector.Fetcher, "head", return_value=10):
                try:
                    collector.run(
                        MINT, None, 1, 1, 1, "fixture://sqd", None,
                        dataset_id="solana-mainnet",
                        state_session=session(SolanaTransportFake()))
                except SystemExit as exc:
                    assert "mint" in str(exc).lower() or "标的" in str(exc)
                else:
                    raise AssertionError("wrong-mint SQD cache identity was consumed")
        finally:
            os.chdir(old)

    with tempfile.TemporaryDirectory(prefix="r9-b3-sqd-toctou-") as raw:
        old = Path.cwd()
        os.chdir(raw)
        try:
            edge = (1700000000, 10, 0, -1, collector.ZERO, "OwnerA", 5)
            with (mock.patch.object(collector.Fetcher, "head", return_value=10),
                  mock.patch.object(collector.Fetcher, "scan_area",
                                    return_value=([edge], 10, True)),
                  mock.patch.object(collector, "collector_sha256",
                                    side_effect=["a" * 64, "b" * 64]),
                  mock.patch.object(collector.MemMerger, "finalize",
                                    side_effect=AssertionError("finalize reached")) as finalize):
                _edges, gap = collector.run(
                    MINT, None, 1, 1, 1, "fixture://sqd", None,
                    from_slot_cli=10, dataset_id="solana-mainnet",
                    state_session=session(SolanaTransportFake()))
            assert gap and "merge-fail" in gap, gap
            assert finalize.call_count == 0
        finally:
            os.chdir(old)


def test_r9_observation_negative_suite():
    test_monotonic_full_and_light_modes()
    test_wrong_genesis_zero_business()
    test_mint_pre_post_change_rejected()
    test_complete_pagination_incomplete_rejected()
    test_writable_mutation_rejected_in_both_modes()
    test_supply_context_before_snapshot_rejected()
    test_three_way_supply_closure_rejected()


def main():
    tests = [
        test_wrong_genesis_zero_business,
        test_monotonic_full_and_light_modes,
        test_declared_slot_is_assertion_not_observation,
        test_mint_pre_post_change_rejected,
        test_json_parsed_slot_cannot_precede_raw_pre,
        test_gpa_slot_cannot_precede_json_parsed_floor,
        test_pre_slot_must_honor_cli_min_context_slot,
        test_complete_pagination_incomplete_rejected,
        test_writable_mutation_rejected_in_both_modes,
        test_supply_context_before_snapshot_rejected,
        test_supply_context_lag_is_retryable,
        test_three_way_supply_closure_rejected,
        test_writable_parser_static_and_loaded_addresses,
        test_writable_parser_fails_closed_on_unresolved_lookup_table,
        test_explicit_readonly_cannot_override_header_writable,
        test_complete_zero_reference_coverage_is_explicit,
        test_activity_rpc_budget_switches_before_call_251,
        test_mid_scan_lightweight_downgrade_never_publishes_over_limit,
        test_scan_rejects_gpa_below_parsed_before_formal_publish,
        test_scan_runs_in_memory_bundle_validator_before_publish,
        test_bundle_hashes_are_deterministic,
        test_scan_cli_assertion_quarantines_old_marker,
        test_scan_error_receipt_and_stderr_redact_endpoint_query,
        test_sqd_dataset_mint_and_slot_scope_rejected,
        test_sqd_collector_rejects_bad_scope_before_run,
        test_r9_observation_negative_suite,
    ]
    failures = []
    for test in tests:
        try:
            test()
        except Exception as exc:
            failures.append(f"{test.__name__}: {type(exc).__name__}: {exc}")
    if failures:
        raise AssertionError("\n".join(failures))
    print("PASS R9 B3-G1/G4: Solana observation protocol and negative variants")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
