#!/usr/bin/env python3
"""F-04 regressions for strict EVM returndata and deployed runtime code."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts/lib"), str(ROOT / "scripts/tests")]

from evm_observation import (  # noqa: E402
    build_evm_observation_bundle,
    observe_evm_supply,
    validate_evm_observation_bundle,
)
from test_evm_observation import (  # noqa: E402
    AS_OF,
    CHAIN_ID,
    RUNTIME_CODE,
    TOKEN,
    FakePool,
)


ZERO_WORD = "0x" + "0" * 64
EMPTY_CODE_SHA256 = hashlib.sha256(b"").hexdigest()


class ContractPool(FakePool):
    """Existing transport fake with F-04-specific returndata controls."""

    def __init__(self, *, runtime_code=RUNTIME_CODE, short_total_supply=False):
        super().__init__()
        self.runtime_code = runtime_code
        self.short_total_supply = short_total_supply

    def _response(self, method, params):
        if method == "eth_call":
            self.calls.append((method, params))
            self.business_calls += 1
            selector = params[0]["data"][:10]
            if selector == "0x18160ddd" and self.short_total_supply:
                return {"ok": True, "result": "0x0"}
            return {"ok": True, "result": ZERO_WORD}
        if method == "eth_getCode":
            self.calls.append((method, params))
            self.business_calls += 1
            return {"ok": True, "result": self.runtime_code}
        return super()._response(method, params)


def observe(pool=None):
    return observe_evm_supply(
        pool or ContractPool(), "eth", TOKEN, AS_OF,
        expected_chain_id=CHAIN_ID)


def expect_error(action, needle):
    try:
        action()
    except Exception as exc:  # noqa: BLE001 - assertion helper
        message = str(exc)
        assert needle.lower() in message.lower(), message
        return message
    raise AssertionError(f"invalid EVM observation accepted; expected {needle!r}")


def persist_bundle(case: Path, core: dict, transcript: list):
    transcript_path = case / "transcript.json"
    transcript_path.write_text(
        json.dumps(transcript, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    target = {"chain": "eth", "token": TOKEN, "as_of_block": AS_OF}
    bundle = build_evm_observation_bundle(
        core, transcript_path, target, "scripts/evm/observe_supply.py",
        input_base=case)
    bundle_path = case / "bundle.json"
    bundle_path.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    return bundle, bundle_path


def test_empty_runtime_code_rejected_by_producer():
    expect_error(lambda: observe(ContractPool(runtime_code="0x")), "bytecode")


def test_short_total_supply_word_rejected_by_producer():
    expect_error(
        lambda: observe(ContractPool(short_total_supply=True)), "invalid value")


def test_empty_runtime_code_hash_rejected_by_validator():
    core = observe()
    core["code"]["runtime_code_sha256"] = EMPTY_CODE_SHA256
    transcript = copy.deepcopy(core["_transcript"])
    transcript[6]["result"] = "0x"
    with tempfile.TemporaryDirectory(prefix="evm-empty-code-hash-") as raw:
        case = Path(raw)
        bundle, bundle_path = persist_bundle(case, core, transcript)
        expect_error(
            lambda: validate_evm_observation_bundle(
                bundle, bundle_path=bundle_path, expected_token=TOKEN,
                expected_chain_id=CHAIN_ID),
            "runtime code")


def test_legacy_getcode_block_number_rejected_by_transcript_validator():
    core = observe()
    transcript = copy.deepcopy(core["_transcript"])
    transcript[6]["params"] = [TOKEN, hex(AS_OF)]
    with tempfile.TemporaryDirectory(prefix="evm-getcode-selector-") as raw:
        case = Path(raw)
        bundle, bundle_path = persist_bundle(case, core, transcript)
        expect_error(
            lambda: validate_evm_observation_bundle(
                bundle, bundle_path=bundle_path, expected_token=TOKEN,
                expected_chain_id=CHAIN_ID),
            "getcode params")


def test_zero_supply_deployed_contract_passes_full_chain():
    core = observe()
    assert core["supply"] == {
        "total_supply_raw": "0",
        "zero_balance_raw": "0",
        "dead_balance_raw": "0",
        "block_binding": "eip1898-block-hash",
    }
    assert core["code"]["runtime_code_sha256"] != EMPTY_CODE_SHA256
    with tempfile.TemporaryDirectory(prefix="evm-zero-supply-contract-") as raw:
        case = Path(raw)
        bundle, bundle_path = persist_bundle(case, core, core["_transcript"])
        validated = validate_evm_observation_bundle(
            bundle, bundle_path=bundle_path, expected_token=TOKEN,
            expected_chain_id=CHAIN_ID)
        assert validated is bundle


def main():
    tests = [
        test_empty_runtime_code_rejected_by_producer,
        test_short_total_supply_word_rejected_by_producer,
        test_empty_runtime_code_hash_rejected_by_validator,
        test_legacy_getcode_block_number_rejected_by_transcript_validator,
        test_zero_supply_deployed_contract_passes_full_chain,
    ]
    failures = []
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001 - standalone runner
            failures.append(f"{test.__name__}: {type(exc).__name__}: {exc}")
    if failures:
        raise AssertionError("\n".join(failures))
    print(f"PASS F-04 EVM nonempty code and ABI word checks: {len(tests)}/{len(tests)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
