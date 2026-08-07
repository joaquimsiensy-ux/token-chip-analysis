#!/usr/bin/env python3
"""EVM 对账生产器：余额、供给闭合与 GMGN 对表，产绑定目标的 v2 回执。

退出码：0=全部硬检查 PASS；2=供给/余额硬不一致；1=输入、RPC 或写入失败。
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from net import RpcChainMismatch, attested_rpc_pool
from receipt_kernel import (build_envelope, finalize_envelope, publish_error_receipt,
                            publish_overwrite)

ZERO = "0x0000000000000000000000000000000000000000"
DEAD = "0x000000000000000000000000000000000000dead"
SCHEMA = "evm-reconciliation-receipt/v2"


class ReconFailure(ValueError):
    """A completed hard check failed (exit 2), as distinct from producer ERROR."""


def rpc_balance_of(pool, token, address, block):
    data = "0x70a08231" + "0" * 24 + address.lower().replace("0x", "")
    result = pool.call("eth_call", [{"to": token, "data": data}, hex(int(block))])
    if not result.get("ok") or result.get("result") in (None, "0x"):
        raise ValueError(f"eth_call 无有效 result: {result.get('error') or result.get('result')!r}")
    return int(result["result"], 16)


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True)
    ap.add_argument("--balances", required=True)
    ap.add_argument("--replay-stats", required=True)
    ap.add_argument("--gmgn", required=True)
    ap.add_argument("--chain", required=True, choices=["eth", "bsc", "base", "arbitrum"])
    ap.add_argument("--token", required=True)
    ap.add_argument("--end-block", required=True, type=int)
    ap.add_argument("--out", required=True)
    ap.add_argument("--rpc")
    ap.add_argument("--proxy")
    ap.add_argument("--top-n", type=int, default=15)
    return ap.parse_args(argv)


def main(argv=None):
    a = parse_args(argv)
    target = {"chain": a.chain, "token": a.token.lower(), "as_of_block": a.end_block}
    base_envelope = build_envelope(SCHEMA, target, __file__, "formal")
    envelope = base_envelope
    try:
        if a.end_block < 0 or a.top_n <= 0:
            raise ValueError("end-block 必须非负且 top-n 必须为正")
        config_path, balances_path = Path(a.config), Path(a.balances)
        stats_path, gmgn_path = Path(a.replay_stats), Path(a.gmgn)
        envelope = build_envelope(SCHEMA, target, __file__, "formal", inputs={
            "config": config_path, "balances": balances_path,
            "replay_stats": stats_path, "gmgn": gmgn_path})
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
        balances_raw = json.loads(balances_path.read_text(encoding="utf-8"))
        stats = json.loads(stats_path.read_text(encoding="utf-8"))
        if not isinstance(balances_raw, dict) or not balances_raw:
            raise ValueError("balances 必须是非空 address->raw 映射")
        balances = {str(k).lower(): int(str(v)) for k, v in balances_raw.items()}
        cfg_token = str(cfg.get("token") or "").lower()
        if cfg_token and cfg_token != target["token"]:
            raise ValueError("config token 与 --token 不一致")
        stats_end = stats.get("max_block") or stats.get("last_block")
        if stats_end is None or int(stats_end) != a.end_block:
            raise ValueError("replay_stats 截止块与 --end-block 不一致")
        decimals = int(cfg["decimals"])
        nominal = int(Decimal(str(cfg["total_supply_human"])) * (Decimal(10) ** decimals))
        mint = int(str(stats.get("mint_total_wei", stats.get("mint_total_raw", 0))))
        burn = int(str(stats.get("burn_total_wei", stats.get("burn_total_raw", 0))))
        balance_sum = sum(balances.values())
        negatives = sorted(k for k, v in balances.items() if v < 0)
        supply_closed = mint == nominal and balance_sum == mint - burn and not negatives

        rpc = a.rpc or str((cfg.get("alchemy") or {}).get("url", "")) + str(
            (cfg.get("alchemy") or {}).get("key", ""))
        if not rpc:
            raise ValueError("缺 RPC：给 --rpc 或 config.alchemy.url/key")
        proxy = a.proxy if a.proxy is not None else cfg.get("proxy")
        pool = attested_rpc_pool(rpc, a.chain, formal=True, proxy=proxy,
                                 rps=8, concurrency=1)
        try:
            pool.attest()
        except RpcChainMismatch as exc:
            raise ReconFailure(str(exc)) from exc
        rows, matched, mismatched, rpc_errors = [], 0, 0, 0
        top = sorted(balances.items(), key=lambda kv: -kv[1])[:a.top_n]
        for address, replay_raw in top:
            if address in {ZERO, DEAD}:
                continue
            try:
                chain_raw = int(rpc_balance_of(pool, target["token"], address,
                                               a.end_block))
                ok = chain_raw == replay_raw
                matched += int(ok); mismatched += int(not ok)
                rows.append({"address": address, "replay_raw": str(replay_raw),
                             "chain_raw": str(chain_raw), "diff_raw": str(chain_raw - replay_raw),
                             "status": "OK" if ok else "MISMATCH"})
            except Exception as exc:
                rpc_errors += 1
                rows.append({"address": address, "replay_raw": str(replay_raw),
                             "status": "RPC_ERROR", "error": str(exc)[:300]})

        gmgn_rows, gmgn_diff = [], 0
        with gmgn_path.open(newline="", encoding="utf-8") as f:
            for row in list(csv.DictReader(f))[:10]:
                address = str(row.get("address") or "").lower()
                if not address:
                    continue
                gmgn_pct = float(row.get("pct") or 0) * 100
                replay_pct = balances.get(address, 0) * 100 / nominal if nominal else 0.0
                diff_pp = abs(gmgn_pct - replay_pct)
                gmgn_diff += int(diff_pp >= 0.15)
                gmgn_rows.append({"address": address, "gmgn_pct": gmgn_pct,
                                  "replay_pct": replay_pct, "diff_pp": diff_pp,
                                  "status": "OK" if diff_pp < 0.15 else "DIFF"})

        observations = {
            "supply_closure": {"mint_total_raw": str(mint), "burn_total_raw": str(burn),
                               "nominal_supply_raw": str(nominal),
                               "balance_sum_raw": str(balance_sum),
                               "negative_count": len(negatives), "negative_addresses": negatives,
                               "closed": supply_closed},
            "balance_reconciliation": {"checked": len(rows), "matched": matched,
                                       "mismatched": mismatched, "rpc_errors": rpc_errors,
                                       "rows": rows},
            "gmgn_comparison": {"checked": len(gmgn_rows), "diff_count": gmgn_diff,
                                "tolerance_pp": 0.15, "rows": gmgn_rows},
        }
        if rpc_errors:
            raise ValueError(f"{rpc_errors} 个 RPC 观测失败")
        elif not supply_closed or mismatched:
            receipt = finalize_envelope(envelope, "FAIL", 2,
                                        observations=observations, error=None)
        else:
            receipt = finalize_envelope(envelope, "PASS", 0,
                                        observations=observations, error=None)
    except ReconFailure as exc:
        receipt = finalize_envelope(envelope, "FAIL", 2, observations={}, error=str(exc))
    except Exception as exc:
        try:
            error_path = publish_error_receipt(a.out, envelope, exc)
            print(f"[verify_recon] ERROR exit=1 → {error_path}")
        except Exception as write_exc:
            print(f"[verify_recon] ERROR receipt 写入失败: {write_exc}", file=sys.stderr)
        return 1
    try:
        publish_overwrite(a.out, receipt)
    except Exception as exc:
        print(f"[verify_recon] receipt 写入失败: {exc}", file=sys.stderr)
        return 1
    print(f"[verify_recon] {receipt['verdict']} exit={receipt['exit_code']} → {a.out}")
    return receipt["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
