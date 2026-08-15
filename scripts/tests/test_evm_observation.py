#!/usr/bin/env python3
"""Workorder A: EVM observation bundle producer/validator regressions."""
from __future__ import annotations

import contextlib
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

TOKEN = "0x" + "ab" * 20
AS_OF = 100
CHAIN_ID = 1
BLOCK_HASH = "0x" + "11" * 32
PARENT_HASH = "0x" + "22" * 32
REORG_HASH = "0x" + "33" * 32
RUNTIME_CODE = "0x6001600055"


@contextlib.contextmanager
def chdir(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def _load_cli(name):
    path = ROOT / "scripts/evm/observe_supply.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakePool:
    """Transport-only EVM fake; production parsing and validation remain live."""

    def __init__(self, *, chain_id=CHAIN_ID, block_number=AS_OF,
                 invalid_call=False, reorg=False, eip1898_unsupported=False,
                 endpoint_drift=False, endpoint="https://rpc.example.test"):
        self.url = endpoint
        self.chain_id = chain_id
        self.block_number = block_number
        self.invalid_call = invalid_call
        self.reorg = reorg
        self.eip1898_unsupported = eip1898_unsupported
        self.endpoint_drift = endpoint_drift
        self.calls = []
        self.business_calls = 0
        self.block_reads = 0

    def attest(self):
        self.calls.append(("eth_chainId", []))
        return self.chain_id

    def _response(self, method, params):
        self.calls.append((method, params))
        self.business_calls += 1
        if self.endpoint_drift and self.business_calls == 1:
            self.url = "https://failover.example.test"
        if method == "eth_getBlockByNumber":
            self.block_reads += 1
            block_hash = REORG_HASH if self.reorg and self.block_reads == 2 else BLOCK_HASH
            return {"ok": True, "result": {
                "number": hex(self.block_number),
                "hash": block_hash,
                "parentHash": PARENT_HASH,
                "timestamp": hex(1_700_000_000),
            }}
        if method == "eth_blockNumber":
            return {"ok": True, "result": hex(AS_OF + 12)}
        if method == "eth_call":
            if self.eip1898_unsupported:
                return {"ok": False, "error": "rpc -32602: unsupported blockHash selector"}
            selector = params[0]["data"][:10]
            values = {"0x18160ddd": 1_000_000, "0x70a08231": 7}
            raw = "not-hex" if self.invalid_call else hex(values[selector])
            return {"ok": True, "result": raw}
        if method == "eth_getCode":
            return {"ok": True, "result": RUNTIME_CODE}
        raise AssertionError(f"unexpected method: {method}")

    def call(self, method, params):
        return self._response(method, params)

    def call_many(self, calls, progress=True):
        del progress
        return [self._response(method, params) for method, params in calls]


def observe(pool=None, **kwargs):
    from evm_observation import observe_evm_supply
    return observe_evm_supply(
        pool or FakePool(), "eth", TOKEN, AS_OF,
        expected_chain_id=CHAIN_ID, **kwargs)


def expect_error(action, needle):
    try:
        action()
    except Exception as exc:
        assert needle.lower() in str(exc).lower(), str(exc)
        return str(exc)
    raise AssertionError(f"invalid EVM observation was accepted; expected {needle!r}")


def cli_args(rpc="https://rpc.example.test"):
    return [
        "--chain", "eth", "--token", TOKEN, "--as-of-block", str(AS_OF),
        "--rpc", rpc, "--proxy", "none", "--out", "bundle.json",
        "--transcript-out", "transcript.json",
    ]


def test_wrong_chain_id_zero_business_calls():
    fake = FakePool(chain_id=56)
    expect_error(lambda: observe(fake), "chainid")
    assert fake.business_calls == 0


def test_invalid_eth_call_result_rejected():
    expect_error(lambda: observe(FakePool(invalid_call=True)), "invalid")


def test_pre_post_block_hash_mismatch_rejected():
    expect_error(lambda: observe(FakePool(reorg=True)), "recheck")


def test_eip1898_unsupported_fails_closed_without_outputs():
    cli = _load_cli("evm_observe_eip1898_red")
    fake = FakePool(eip1898_unsupported=True)
    with tempfile.TemporaryDirectory(prefix="evm-observe-eip1898-") as raw:
        case = Path(raw)
        with chdir(case), mock.patch.object(cli, "attested_rpc_pool", return_value=fake):
            rc = cli.main(cli_args())
        assert rc != 0
        assert not (case / "bundle.json").exists()
        assert not (case / "transcript.json").exists()
        assert not any(call[1] and call[1][-1] == hex(AS_OF) for call in fake.calls
                       if call[0] == "eth_call")


def test_declared_as_of_block_mismatch_rejected():
    expect_error(lambda: observe(FakePool(block_number=AS_OF + 1)), "assertion mismatch")


def test_endpoint_failover_cannot_rebind_attestation():
    expect_error(lambda: observe(FakePool(endpoint_drift=True)), "endpoint")


def _write_bundle(case, transcript):
    from evm_observation import (build_evm_observation_bundle,
                                 validate_evm_observation_bundle)
    core = observe()
    transcript_path = case / "transcript.json"
    transcript_path.write_text(
        json.dumps(transcript, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    target = {"chain": "eth", "token": TOKEN, "as_of_block": AS_OF}
    bundle = build_evm_observation_bundle(
        core, transcript_path, target, "scripts/evm/observe_supply.py", input_base=case)
    bundle_path = case / "bundle.json"
    bundle_path.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return bundle, bundle_path, validate_evm_observation_bundle


def test_transcript_method_and_params_tamper_rejected():
    core = observe()
    original = core["_transcript"]
    for label, mutate in (
            ("method", lambda rows: rows[3].__setitem__("method", "eth_getCode")),
            ("params", lambda rows: rows[3]["params"][0].__setitem__("to", "0x" + "cd" * 20))):
        rows = json.loads(json.dumps(original))
        mutate(rows)
        with tempfile.TemporaryDirectory(prefix=f"evm-transcript-{label}-") as raw:
            case = Path(raw)
            bundle, path, validate = _write_bundle(case, rows)
            expect_error(
                lambda: validate(bundle, bundle_path=path, expected_token=TOKEN,
                                 expected_chain_id=CHAIN_ID),
                label)


def test_prepublication_self_validation_failure_leaves_no_canonicals():
    cli = _load_cli("evm_observe_self_validate_red")
    with tempfile.TemporaryDirectory(prefix="evm-observe-self-validate-") as raw:
        case = Path(raw)
        with chdir(case), \
                mock.patch.object(cli, "attested_rpc_pool", return_value=FakePool()), \
                mock.patch.object(
                    cli, "validate_evm_observation_bundle",
                    side_effect=ValueError("injected producer self-validation failure")) as check:
            rc = cli.main(cli_args())
        assert check.call_count == 1
        assert rc != 0
        assert not (case / "bundle.json").exists()
        assert not (case / "transcript.json").exists()
        assert list(case.glob("bundle.error.*.json"))


def test_error_path_redacts_endpoint_query():
    cli = _load_cli("evm_observe_secret_red")
    endpoint = "https://rpc.example.test/v1?api-key=SECRET_VALUE#private"
    fake = FakePool(invalid_call=True, endpoint=endpoint)
    with tempfile.TemporaryDirectory(prefix="evm-observe-secret-") as raw:
        case = Path(raw)
        stderr = io.StringIO()
        with chdir(case), contextlib.redirect_stderr(stderr), \
                mock.patch.object(cli, "attested_rpc_pool", return_value=fake):
            rc = cli.main(cli_args(endpoint))
        errors = list(case.glob("bundle.error.*.json"))
        assert rc != 0 and errors
        for rendered in (stderr.getvalue(), errors[0].read_text(encoding="utf-8")):
            assert "api-key" not in rendered
            assert "SECRET_VALUE" not in rendered
            assert "#private" not in rendered


def test_legal_cli_flow_publishes_and_validates_both_files():
    cli = _load_cli("evm_observe_happy_red")
    from evm_observation import validate_evm_observation_bundle
    with tempfile.TemporaryDirectory(prefix="evm-observe-happy-") as raw:
        case = Path(raw)
        with chdir(case), mock.patch.object(
                cli, "attested_rpc_pool", return_value=FakePool()):
            rc = cli.main(cli_args())
        assert rc == 0
        bundle_path = case / "bundle.json"
        transcript_path = case / "transcript.json"
        assert bundle_path.is_file() and transcript_path.is_file()
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        validate_evm_observation_bundle(
            bundle, bundle_path=bundle_path, expected_token=TOKEN,
            expected_chain_id=CHAIN_ID)


def main():
    tests = [
        test_wrong_chain_id_zero_business_calls,
        test_invalid_eth_call_result_rejected,
        test_pre_post_block_hash_mismatch_rejected,
        test_eip1898_unsupported_fails_closed_without_outputs,
        test_declared_as_of_block_mismatch_rejected,
        test_endpoint_failover_cannot_rebind_attestation,
        test_transcript_method_and_params_tamper_rejected,
        test_prepublication_self_validation_failure_leaves_no_canonicals,
        test_error_path_redacts_endpoint_query,
        test_legal_cli_flow_publishes_and_validates_both_files,
    ]
    failures = []
    for test in tests:
        try:
            test()
        except Exception as exc:
            failures.append(f"{test.__name__}: {type(exc).__name__}: {exc}")
    if failures:
        raise AssertionError("\n".join(failures))
    print(f"PASS EVM observation bundle protocol: {len(tests)}/{len(tests)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
