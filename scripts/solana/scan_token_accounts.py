#!/usr/bin/env python3
"""SPL / Token-2022 全量持仓扫描（getProgramAccounts + dataSlice{32,40}）。

用法：python3 scan_token_accounts.py <mint> --out <snapshot.json> --bundle <bundle.json>
      [--program auto|token2022|spl] [--rpc URL] [--min-context-slot N] [--timeout 秒]
--program 默认 auto：先 getAccountInfo(mint) 看 owner 自动判定 SPL / Token-2022——
  旧默认 token2022 对标准 SPL 老币会扫出 0 账户且不报错（TROLL 实战踩坑：叠加代理返回
  "合法空 result"被当缓存，两层坑连环；2026-07-29 改 auto 根治）
大盘子 mint（20万+ 账户）：publicnode 恒 504、Helius 默认 120s 也断——
  --rpc <helius端点> --timeout 300 一次拉全（curl 已内置 --compressed，gzip 对 60MB+ 响应是成败关键；
  GOAT 24.7万账户 67MB 实测，2026-07-22）
输出（写入 ./data/）：
  holders_accounts.json  每行 {account, owner, amount_raw}
  holders_owners.json    owner 聚合去重 {owner: amount_raw}，降序
  stdout 摘要：账户数/独立 owner 数双口径、五档分层、top20、对账（加总 vs getTokenSupply）

要点（data-pipeline-solana.md §1）：
- Token-2022 账户可带 extension 变长，不能用 dataSize:165 过滤——只用 memcmp(offset=0, mint)
- 基础布局不变：mint@0 owner@32 amount@64(u64 LE)，dataSlice{32,40} 一次带出 owner+amount
- getProgramAccounts 无分页，一次全量返回；落盘后本地解析
"""
import argparse, base64, hashlib, json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from artifact_quarantine import quarantine_current, quarantine_run_id
from receipt_kernel import (assert_distinct_paths, build_envelope, finalize_envelope,
                            publish_error_receipt, publish_overwrite, publish_txn)
from solana_attested_session import SolanaAttestedSession
from solana_observation import (assert_declared_slot, build_observation_bundle,
                                observe_snapshot, validate_observation_bundle)

SPL = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
T22 = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
ALPHA = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def b58encode(b: bytes) -> str:
    n = int.from_bytes(b, "big")
    s = ""
    while n:
        n, r = divmod(n, 58)
        s = ALPHA[r] + s
    for byte in b:
        if byte == 0:
            s = "1" + s
        else:
            break
    return s


def choose_datasizes(program, requested):
    if requested == "auto":
        return ["all"] if program == T22 else [165]
    values = ["all"] if requested == "all" else [int(x) for x in requested.split(",")]
    if program == T22 and values != ["all"]:
        raise ValueError("Token-2022 requires an unfiltered all-size account scan")
    return values


def cache_identity_matches(meta, expected):
    return bool(meta) and all(meta.get(k) == v for k, v in expected.items())


def require_snapshot_closed(total, supply, malformed=0):
    if malformed or total != supply:
        raise ValueError(f"holder snapshot not closed: malformed={malformed} "
                         f"total={total} supply={supply}")


def parse_supply_response(response):
    """Parse the persisted getTokenSupply response used by both producer and receipt validator."""
    result = response["result"]
    value = result["value"]
    supply_raw = int(value["amount"])
    decimals = int(value["decimals"])
    if supply_raw < 0 or decimals < 0:
        raise ValueError("invalid negative token supply/decimals")
    return (result.get("context") or {}).get("slot"), decimals, supply_raw


def parse_gpa_response(response):
    """Return one GPA response's account list and context slot, rejecting malformed RPC payloads."""
    if not isinstance(response, dict) or "error" in response or "result" not in response:
        raise ValueError("invalid getProgramAccounts response")
    result = response["result"]
    if isinstance(result, dict) and "value" in result:
        batch = result["value"]
        slot = (result.get("context") or {}).get("slot")
    else:
        batch = result
        slot = None
    if not isinstance(batch, list):
        raise ValueError("getProgramAccounts result must be a list")
    return batch, slot


def parse_token_accounts(accounts):
    """Canonical dataSlice{32,40} decoder and cross-scan pubkey deduplicator."""
    seen_pk = set()
    unique = [a for a in accounts
              if not (a["pubkey"] in seen_pk or seen_pk.add(a["pubkey"]))]
    rows, owners, malformed = [], {}, 0
    for account in unique:
        raw = base64.b64decode(account["account"]["data"][0])
        if len(raw) < 40:
            malformed += 1
            continue
        owner = b58encode(raw[0:32])
        amount = int.from_bytes(raw[32:40], "little")
        if amount == 0:
            continue
        rows.append({"account": account["pubkey"], "owner": owner, "amount_raw": amount})
        owners[owner] = owners.get(owner, 0) + amount
    return unique, rows, dict(sorted(owners.items(), key=lambda kv: -kv[1])), malformed


def _default_rpc():
    key_file = Path.home() / ".config/helius/api-key"
    if key_file.is_file():
        key = key_file.read_text(encoding="utf-8").strip()
        if key:
            return f"https://mainnet.helius-rpc.com/?api-key={key}"
    return "https://api.mainnet-beta.solana.com"


def _case_relative(path):
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError as exc:
        raise ValueError("formal outputs must stay inside the case directory") from exc


def main(argv=None, *, request_json=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mint")
    ap.add_argument("--program", choices=["auto", "token2022", "spl"], default="auto")
    ap.add_argument("--rpc", action="append", dest="rpcs",
                    help="Solana JSON-RPC endpoint; repeat for attested failover")
    ap.add_argument("--datasizes", default="auto",
                    help="compatibility option; the observation protocol always scans all extension sizes")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--as-of-slot", type=int, default=None,
                    help="optional compatibility assertion against observed GPA context.slot")
    ap.add_argument("--min-context-slot", type=int, default=0,
                    help="lower bound forwarded to finalized account/GPA observations")
    ap.add_argument("--out", required=True, help="solana-holder-snapshot/v3 output")
    ap.add_argument("--receipt", help="compatibility name for the observation bundle/commit marker")
    ap.add_argument("--bundle", help="solana-observation-bundle/v1 output/commit marker")
    ap.add_argument("--work-dir", default="data")
    args = ap.parse_args(argv)
    marker = args.bundle or args.receipt
    if not marker:
        ap.error("one of --bundle/--receipt is required")
    if args.bundle and args.receipt and Path(args.bundle).resolve() != Path(args.receipt).resolve():
        ap.error("--bundle and --receipt name the same commit marker; separate paths are rejected")
    if args.as_of_slot is not None and args.as_of_slot < 0:
        ap.error("--as-of-slot must be non-negative")
    if args.min_context_slot < 0:
        ap.error("--min-context-slot must be non-negative")
    if args.timeout <= 0:
        ap.error("--timeout must be positive")
    try:
        assert_distinct_paths(args.out, marker)
    except Exception as exc:
        print(f"FATAL: output/bundle path conflict: {exc}", file=sys.stderr)
        return 2

    run_id = quarantine_run_id()
    try:
        stale_marker = quarantine_current(marker, run_id)
        stale_out = quarantine_current(args.out, run_id)
    except Exception as exc:
        print(f"FATAL: prior snapshot/marker quarantine failed: {exc}", file=sys.stderr)
        return 1
    for label, stale in (("marker", stale_marker), ("snapshot", stale_out)):
        if stale is not None:
            print(f"[stale] previous {label} moved to {stale}", file=sys.stderr)

    data_dir = Path(args.work_dir).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    endpoints = args.rpcs or [_default_rpc()]
    error_target = {"chain": "solana", "token": args.mint,
                    "as_of_block": (args.as_of_slot if args.as_of_slot is not None
                                    else args.min_context_slot)}
    error_envelope = None
    try:
        error_envelope = build_envelope(
            "solana-observation-bundle/v1", error_target, __file__, "formal")
        session = SolanaAttestedSession(
            endpoints, request_json=request_json, timeout=args.timeout)
        if args.program == "auto":
            detected = session.call("getAccountInfo", [args.mint, {
                "commitment": "finalized", "encoding": "base64",
                "minContextSlot": args.min_context_slot,
            }])
            value = detected.get("value") if isinstance(detected, dict) else None
            prog = value.get("owner") if isinstance(value, dict) else None
            if prog not in {SPL, T22}:
                raise ValueError(f"mint owner={prog!r} is not SPL/Token-2022")
        else:
            prog = T22 if args.program == "token2022" else SPL
        if args.datasizes not in {"auto", "all"} and prog == T22:
            raise ValueError("Token-2022 formal observation rejects dataSize filters")

        core, normalized = observe_snapshot(
            session, args.mint, prog, min_context_slot=args.min_context_slot)
        snapshot_slot = core["snapshot"]["slot"]
        error_envelope = build_envelope(
            "solana-observation-bundle/v1",
            {"chain": "solana", "token": args.mint,
             "as_of_block": snapshot_slot},
            __file__, "formal")
        assert_declared_slot(args.as_of_slot, snapshot_slot, "--as-of-slot")
        supply_raw = int(core["supply"]["amount"])
        decimals = int(core["supply"]["decimals"])

        rpc_accounts = [{"pubkey": item["pubkey"], "account": {
            "data": [item["data_base64"], "base64"]}} for item in normalized]
        _, rows, owners, malformed = parse_token_accounts(rpc_accounts)
        total = sum(owners.values())
        require_snapshot_closed(total, supply_raw, malformed)

        supply_file = data_dir / "_supply.json"
        gpa_file = data_dir / "_gpa_raw_all.json"
        gpa_meta_file = data_dir / "_gpa_raw_all.meta.json"
        accounts_out = data_dir / "holders_accounts.json"
        owners_out = data_dir / "holders_owners.json"
        supply_payload = {"result": {"context": {"slot": core["supply"]["slot"]},
                                      "value": {"amount": str(supply_raw),
                                                "decimals": decimals}}}
        gpa_payload = {"result": {"context": {"slot": snapshot_slot},
                                   "value": rpc_accounts}}
        filters = [{"memcmp": {"offset": 0, "bytes": args.mint}}]
        gpa_meta = {"schema": "solana-gpa-cache-v2", "mint": args.mint,
                    "program": prog, "rpc": core["attestation"]["endpoint"]["public_origin"],
                    "filters": filters, "supply_observed_slot": core["supply"]["slot"],
                    "gpa_response_slot": snapshot_slot, "account_count": len(rpc_accounts)}
        for path, payload in ((supply_file, supply_payload), (gpa_file, gpa_payload),
                              (gpa_meta_file, gpa_meta), (accounts_out, rows),
                              (owners_out, owners)):
            publish_overwrite(path, payload)

        def ref(path):
            return {"path": Path(path).name, "size": Path(path).stat().st_size,
                    "sha256": sha256_file(path)}

        scan_receipt = {**gpa_meta, "raw_artifact": ref(gpa_file),
                        "meta_artifact": ref(gpa_meta_file)}
        meta = {
            "schema": "solana-holder-snapshot-v2", "mint": args.mint, "program": prog,
            "target": core["canonical_target"], "verdict": "PASS", "exit_code": 0,
            "rpc": core["attestation"]["endpoint"]["public_origin"],
            "supply_raw": str(supply_raw), "sum_accounts_raw": str(total),
            "decimals": decimals, "closed": True,
            "producer": {"path": "scan_token_accounts.py", "sha256": sha256_file(__file__)},
            "supply_receipt": ref(supply_file),
            "outputs": {"holders_accounts": ref(accounts_out),
                        "holders_owners": ref(owners_out)},
            "scans": [scan_receipt],
            "observation_bundle": {"path": _case_relative(marker)},
        }
        publish_overwrite(data_dir / "holders_snapshot_meta.json", meta)

        snapshot = {
            "schema": "solana-holder-snapshot/v3", "target": core["canonical_target"],
            "mint": args.mint, "program": prog,
            "endpoint": core["attestation"]["endpoint"], "decimals": decimals,
            "supply_raw": str(supply_raw), "sum_accounts_raw": str(total),
            "closed": True, "accounts": rows, "owners": owners,
        }
        data_bytes = (json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n").encode()
        bundle = build_observation_bundle(
            core, __file__, inputs={"supply_rpc": supply_file, "gpa_rpc": gpa_file,
                                    "gpa_meta": gpa_meta_file},
            closed=True, supply_raw=str(supply_raw), sum_accounts_raw=str(total),
            as_of_slot=snapshot_slot, as_of_block=snapshot_slot,
            observed_context_slot=snapshot_slot,
            observed_slots={"pre": core["mint_pre"]["slot"], "gpa": snapshot_slot,
                            "post": core["mint_post"]["slot"],
                            "supply": core["supply"]["slot"]},
            output={"path": _case_relative(args.out), "size": len(data_bytes),
                    "sha256": hashlib.sha256(data_bytes).hexdigest()},
            holder_outputs={"accounts": ref(accounts_out), "owners": ref(owners_out)})
        # Producer and consumers share the exact same object-level contract.
        # bundle_path is intentionally omitted because the atomic formal write
        # has not happened yet; byte equality is checked by consumers later.
        validate_observation_bundle(bundle, expected_mint=args.mint)
        publish_txn(args.out, snapshot, marker, bundle)
    except Exception as exc:
        print(f"FATAL: Solana observation failed: {exc}", file=sys.stderr)
        if error_envelope is not None:
            try:
                error_path = publish_error_receipt(marker, error_envelope, exc, run_id=run_id)
                print(f"[scan_token_accounts] ERROR -> {error_path}", file=sys.stderr)
            except Exception as write_exc:
                print(f"[scan_token_accounts] ERROR receipt failed: {write_exc}", file=sys.stderr)
        return 1

    print(f"snapshot_slot={snapshot_slot} accounts={len(rows)} owners={len(owners)} "
          f"supply={supply_raw} activity={core['activity']['mode']} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
