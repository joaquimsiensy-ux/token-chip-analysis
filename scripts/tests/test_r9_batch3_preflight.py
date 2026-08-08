#!/usr/bin/env python3
"""Offline wiring checks for both G3-0 preflight carriers."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts/lib"), str(ROOT / "scripts/tests")]
from test_r9_batch3_solana_observation import SolanaTransportFake  # noqa: E402


def load(name):
    path = ROOT / "maintenance/repair-20260806/g3_preflight" / name
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_usdc_shell_uses_production_activity_parser():
    module = load("g3_0a_usdc_activity.py")
    fake = SolanaTransportFake(activity="light")
    report = module.run_endpoint("fixture://usdc", request_json=fake)
    assert report["status"] == "PASS"
    assert report["activity"]["mode"] == "lightweight"
    assert report["activity"]["sample_size"] == 50


def test_pythia_shell_uses_full_production_observation():
    module = load("g3_0b_pythia_gpa.py")
    fake = SolanaTransportFake(activity="full")
    report = module.run_endpoint("fixture://pythia", request_json=fake)
    assert report["status"] == "PASS"
    assert report["observation"]["closure"]["closed"] is True
    assert report["observation"]["snapshot"]["slot"]


def test_real_preflight_transport_reuses_production_urllib():
    module = load("g3_0a_usdc_activity.py")
    payload = {"jsonrpc": "2.0", "id": 1, "method": "getGenesisHash"}
    response = {"jsonrpc": "2.0", "id": 1, "result": "fixture"}
    with mock.patch.object(module, "_urllib_json", return_value=response) as request_json:
        assert module.CostedTransport()("https://rpc.example.test", payload, 3) == response
    request_json.assert_called_once_with("https://rpc.example.test", payload, 3)


def test_preflight_error_reports_redact_endpoint_query():
    endpoint = "https://mainnet.helius-rpc.com/v1?api-key=SECRET#private"

    def fail_transport(_endpoint, _payload, _timeout):
        raise OSError(f"failed endpoint {_endpoint}")

    for filename in ("g3_0a_usdc_activity.py", "g3_0b_pythia_gpa.py"):
        report = load(filename).run_endpoint(endpoint, request_json=fail_transport)
        encoded = json.dumps(report, sort_keys=True)
        assert report["status"] == "ERROR"
        assert "api-key" not in encoded
        assert "SECRET" not in encoded
        assert "#private" not in encoded


def main():
    test_usdc_shell_uses_production_activity_parser()
    test_pythia_shell_uses_full_production_observation()
    test_real_preflight_transport_reuses_production_urllib()
    test_preflight_error_reports_redact_endpoint_query()
    print("PASS R9 B3-G5: both preflight shells execute production observation code")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
