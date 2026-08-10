#!/usr/bin/env python3
"""G3-0a: USDC activity-volume preflight; never runs GPA or holder closure."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/lib"))
from solana_attested_session import (SolanaAttestedSession,
                                     _urllib_json)  # noqa: E402
from solana_observation import (endpoint_fingerprint,
                                measure_mint_activity)  # noqa: E402

USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


class CostedTransport:
    def __init__(self, delegate=None):
        self.delegate = delegate
        self.calls = 0
        self.response_bytes = 0
        self.rate_limit_events = 0
        self.elapsed = 0.0

    def _http(self, endpoint, payload, timeout):
        try:
            response = _urllib_json(endpoint, payload, timeout)
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                self.rate_limit_events += 1
            raise
        # The shared transport owns TLS/CA handling.  The decoded JSON size is
        # the stable cost proxy available at this wrapper boundary.
        self.response_bytes += len(
            json.dumps(response, separators=(",", ":")).encode("utf-8"))
        return response

    def __call__(self, endpoint, payload, timeout):
        started = time.monotonic()
        self.calls += 1
        try:
            if self.delegate is None:
                return self._http(endpoint, payload, timeout)
            response = self.delegate(endpoint, payload, timeout)
            self.response_bytes += len(json.dumps(response, separators=(",", ":")).encode())
            return response
        finally:
            self.elapsed += time.monotonic() - started

    def report(self):
        return {"rpc_calls": self.calls, "response_bytes": self.response_bytes,
                "elapsed_seconds": round(self.elapsed, 6),
                "rate_limit_events": self.rate_limit_events}


def run_endpoint(endpoint, *, request_json=None):
    cost = CostedTransport(request_json)
    started = time.monotonic()
    try:
        session = SolanaAttestedSession(endpoint, request_json=cost, timeout=30)
        tip = session.call("getSlot", [{"commitment": "finalized"}])
        if isinstance(tip, bool) or not isinstance(tip, int) or tip < 0:
            raise ValueError(f"invalid finalized tip: {tip!r}")
        activity = measure_mint_activity(
            session, USDC_MINT, max(0, tip - 512), tip)
        return {"status": "PASS", "carrier": "native-usdc-activity-only",
                "mint": USDC_MINT, "endpoint": endpoint_fingerprint(endpoint),
                "finalized_tip": tip, "window": {"from_slot": max(0, tip - 512),
                                                  "to_slot": tip},
                "activity": activity, "cost": cost.report(),
                "wall_seconds": round(time.monotonic() - started, 6),
                "scope_note": "USDC is activity-only; no GPA or holder closure is attempted."}
    except Exception as exc:
        return {"status": "ERROR", "carrier": "native-usdc-activity-only",
                "mint": USDC_MINT, "endpoint": endpoint_fingerprint(endpoint),
                "error": str(exc), "cost": cost.report(),
                "wall_seconds": round(time.monotonic() - started, 6),
                "non_blocking": True}


def _write(path, value):
    path = Path(path).resolve()
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", action="append", required=True)
    parser.add_argument("--out", default=str(Path(__file__).with_name("g3_0a_usdc_activity.json")))
    args = parser.parse_args(argv)
    report = {"schema": "g3-0a-usdc-activity/v1",
              "results": [run_endpoint(endpoint) for endpoint in args.endpoint]}
    _write(args.out, report)
    print(args.out)
    return 0  # USDC failures never stop batch 3.


if __name__ == "__main__":
    raise SystemExit(main())
