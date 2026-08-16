#!/usr/bin/env python3
"""Produce one formal EVM frozen-block observation bundle and transcript.

``--as-of-block`` is a declaration checked against the returned block header;
it is never allowed to manufacture the observed anchor.  The two canonical
outputs are published together only after the shared bundle validator passes.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from artifact_quarantine import quarantine_current, quarantine_run_id
from chain_registry import evm_chain_id_for, formal_evm_chains
from endpoint_identity import redact_endpoint_text
from evm_observation import (build_evm_observation_bundle, observe_evm_supply,
                             validate_evm_observation_bundle)
from net import attested_rpc_pool
from proxy_config import resolve_proxy
from receipt_kernel import (assert_distinct_paths, build_envelope,
                            publish_error_receipt, publish_txn)


BUNDLE_SCHEMA = "evm-observation-bundle/v1"
DEFAULT_RPC = {
    "eth": "https://ethereum-rpc.publicnode.com",
    "bsc": "https://bsc-dataseed.bnbchain.org",
    "base": "https://mainnet.base.org",
}


def _relative_to_root(path, root, label):
    resolved = Path(path).expanduser().resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError(f"{label} must stay inside the bundle case directory") from exc


def _write_stage(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--chain", required=True,
        choices=sorted(formal_evm_chains("supply_producer")))
    parser.add_argument("--token", required=True)
    parser.add_argument("--as-of-block", required=True, type=int)
    parser.add_argument("--rpc")
    parser.add_argument("--proxy")
    parser.add_argument("--out", default="evm_observation_bundle.json")
    parser.add_argument(
        "--transcript-out", default="evm_observation_transcript.json")
    args = parser.parse_args(argv)
    args.token = args.token.lower()
    if args.as_of_block < 0:
        parser.error("--as-of-block must be non-negative")
    try:
        assert_distinct_paths(args.out, args.transcript_out)
    except Exception as exc:
        print(f"FATAL: output/transcript path conflict: {exc}", file=sys.stderr)
        return 2

    run_id = quarantine_run_id()
    try:
        stale_out = quarantine_current(args.out, run_id)
        stale_transcript = quarantine_current(args.transcript_out, run_id)
    except Exception as exc:
        print(f"FATAL: prior EVM observation quarantine failed: {exc}", file=sys.stderr)
        return 1
    for label, stale in (("bundle", stale_out), ("transcript", stale_transcript)):
        if stale is not None:
            print(f"[stale] previous {label} moved to {stale}", file=sys.stderr)

    rpc_url = args.rpc or DEFAULT_RPC[args.chain]
    error_target = {
        "chain": args.chain, "token": args.token,
        "as_of_block": args.as_of_block,
    }
    error_envelope = None
    safe_endpoints = [rpc_url, args.proxy]
    try:
        error_envelope = build_envelope(
            BUNDLE_SCHEMA, error_target, __file__, "formal")
        should_resolve_proxy = args.proxy is not None or "CHIP_PROXY" in os.environ
        proxy = resolve_proxy(args.proxy) if should_resolve_proxy else None
        safe_endpoints.append(proxy)
        expected_chain_id = evm_chain_id_for(args.chain)
        pool = attested_rpc_pool(
            rpc_url, args.chain, formal=True, proxy=proxy,
            rps=2, concurrency=1)
        core = observe_evm_supply(
            pool, args.chain, args.token, args.as_of_block,
            expected_chain_id=expected_chain_id)
        observed_block = core["anchor"]["number"]
        error_target = {
            "chain": args.chain, "token": args.token,
            "as_of_block": observed_block,
        }
        error_envelope = build_envelope(
            BUNDLE_SCHEMA, error_target, __file__, "formal")

        bundle_path = Path(args.out).expanduser().resolve()
        case_root = bundle_path.parent
        case_root.mkdir(parents=True, exist_ok=True)
        transcript_rel = _relative_to_root(
            args.transcript_out, case_root, "--transcript-out")
        transcript = core["_transcript"]
        with tempfile.TemporaryDirectory(
                prefix=".evm-observation-stage-", dir=case_root) as raw_stage:
            stage_root = Path(raw_stage).resolve()
            staged_transcript = stage_root / transcript_rel
            _write_stage(staged_transcript, transcript)
            bundle = build_evm_observation_bundle(
                core, staged_transcript, error_target, __file__,
                input_base=stage_root)
            # Producer and consumers share this validator.  The temporary case
            # root mirrors final relative paths, so even pre-publication input
            # path/size/hash validation runs against the final path spelling.
            previous = Path.cwd()
            os.chdir(stage_root)
            try:
                validate_evm_observation_bundle(
                    bundle, expected_token=args.token,
                    expected_chain_id=expected_chain_id)
            finally:
                os.chdir(previous)
            publish_txn(args.transcript_out, transcript, args.out, bundle)
    except Exception as exc:
        safe_error = redact_endpoint_text(exc, safe_endpoints)
        print(f"FATAL: EVM observation failed: {safe_error}", file=sys.stderr)
        if error_envelope is not None:
            try:
                error_path = publish_error_receipt(
                    args.out, error_envelope, safe_error, run_id=run_id)
                print(f"[observe_supply] ERROR -> {error_path}", file=sys.stderr)
            except Exception as write_exc:
                safe_write_error = redact_endpoint_text(write_exc, safe_endpoints)
                print(
                    f"[observe_supply] ERROR receipt failed: {safe_write_error}",
                    file=sys.stderr)
        return 1

    print(
        f"chain={args.chain} block={observed_block} "
        f"confirmations={core['anchor']['confirmations']} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
