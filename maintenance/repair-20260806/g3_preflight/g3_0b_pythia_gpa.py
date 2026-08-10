#!/usr/bin/env python3
"""G3-0b: full production observation protocol against the PYTHIA mint."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PREFLIGHT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "scripts/lib"), str(PREFLIGHT)]
from g3_0a_usdc_activity import CostedTransport  # noqa: E402
from solana_attested_session import SolanaAttestedSession  # noqa: E402
from solana_observation import (endpoint_fingerprint,
                                observe_snapshot)  # noqa: E402

PYTHIA_MINT = "CreiuhfwdWCN5mJbMJtA9bBpYQrQF2tCBuZwSPWfpump"
SPL_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"


def run_endpoint(endpoint, *, request_json=None):
    cost = CostedTransport(request_json)
    started = time.monotonic()
    try:
        session = SolanaAttestedSession(endpoint, request_json=cost, timeout=300)
        core, accounts = observe_snapshot(session, PYTHIA_MINT, SPL_PROGRAM)
        return {"status": "PASS", "carrier": "pythia-full-observation",
                "mint": PYTHIA_MINT, "endpoint": endpoint_fingerprint(endpoint),
                "observation": core, "gpa_account_count": len(accounts),
                "cost": cost.report(),
                "wall_seconds": round(time.monotonic() - started, 6),
                "baseline_scale_note": "~38,039 nonzero accounts/~38,012 owners is context only, never PASS evidence."}
    except Exception as exc:
        return {"status": "ERROR", "carrier": "pythia-full-observation",
                "mint": PYTHIA_MINT, "endpoint": endpoint_fingerprint(endpoint),
                "error": str(exc), "cost": cost.report(),
                "wall_seconds": round(time.monotonic() - started, 6)}


def _write(path, value):
    path = Path(path).resolve()
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", action="append", required=True)
    parser.add_argument("--out", default=str(Path(__file__).with_name("g3_0b_pythia_gpa.json")))
    args = parser.parse_args(argv)
    results = [run_endpoint(endpoint) for endpoint in args.endpoint]
    report = {"schema": "g3-0b-pythia-gpa/v1", "results": results,
              "verdict": "PASS" if any(item["status"] == "PASS" for item in results) else "ERROR"}
    _write(args.out, report)
    print(args.out)
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
