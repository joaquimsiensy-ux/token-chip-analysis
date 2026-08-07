#!/usr/bin/env python3
"""SPL / Token-2022 全量持仓扫描（getProgramAccounts + dataSlice{32,40}）。

用法：python3 scan_token_accounts.py <mint> [--program auto|token2022|spl] [--rpc URL] [--timeout 秒]
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
import argparse, base64, hashlib, json, os, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from receipt_kernel import (assert_distinct_paths, build_envelope, finalize_envelope,
                            publish_txn)

SPL = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
T22 = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
ALPHA = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def quarantine_current(path, run_id):
    """Remove a prior canonical artifact from the current-run namespace."""
    current = Path(os.path.abspath(os.path.expanduser(str(path))))
    if not os.path.lexists(current):
        return None
    if not current.is_file() and not current.is_symlink():
        raise RuntimeError(f"old canonical is not a regular file: {current}")
    stale = current.with_name(f"{current.name}.stale.{run_id}")
    if os.path.lexists(stale):
        raise RuntimeError(f"stale destination already exists: {stale}")
    os.replace(current, stale)
    return stale


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


def rpc_call(url: str, payload: dict, out_file: Path, timeout: int = 120):
    body = json.dumps(payload)
    for attempt in range(4):
        p = subprocess.run(
            ["curl", "-s", "--compressed", "-m", str(timeout), url, "-X", "POST",
             "-H", "Content-Type: application/json", "-d", body, "-o", str(out_file)],
            capture_output=True, text=True, timeout=timeout + 30)
        # 校验返回体为含 result 的合法 JSON 才算成功——curl 对 504/HTML 错误页同样 returncode=0，
        # 错误体一旦落盘会被当缓存复用（PUB 增量实战踩坑，2026-07-15）
        if p.returncode == 0 and out_file.exists() and out_file.stat().st_size > 0:
            try:
                if "result" in json.loads(out_file.read_text()):
                    return True
            except Exception:
                pass
            head = out_file.read_text()[:80]
            print(f"[warn] RPC 返回非 JSON/无 result（attempt {attempt+1}）: {head}", file=sys.stderr)
            out_file.unlink(missing_ok=True)
        time.sleep(2 * (attempt + 1))
    return False


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mint")
    ap.add_argument("--program", choices=["auto", "token2022", "spl"], default="auto",
                    help="auto=getAccountInfo(mint) 查 owner 自动判定（默认，防标准 SPL 币被 token2022 空扫）")
    ap.add_argument("--rpc", default="https://solana-rpc.publicnode.com")
    ap.add_argument("--datasizes", default="auto",
                    help="auto=Token-2022 无 dataSize 全扫/SPL 165；也可给逗号列表或 all"
                         "（publicnode 会 504；api.mainnet-beta 实测放行，2026-07-13）")
    ap.add_argument("--timeout", type=int, default=150,
                    help="GPA 请求超时秒（大盘子 mint 配 Helius 用 300，2026-07-22 GOAT 实测）")
    ap.add_argument("--as-of-slot", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--receipt", required=True)
    ap.add_argument("--work-dir", default="data")
    args = ap.parse_args()
    if args.as_of_slot < 0:
        ap.error("--as-of-slot must be non-negative")
    try:
        assert_distinct_paths(args.out, args.receipt)
    except Exception as exc:
        print(f"FATAL: output/receipt path conflict: {exc}", file=sys.stderr)
        return 2

    run_id = f"{time.time_ns()}.{os.getpid()}"
    try:
        # The receipt is the commit marker: invalidate it before data so a
        # partial quarantine can never leave a current PASS marker.
        stale_receipt = quarantine_current(args.receipt, run_id)
        stale_out = quarantine_current(args.out, run_id)
    except Exception as exc:
        print(f"FATAL: prior snapshot/marker quarantine failed: {exc}", file=sys.stderr)
        return 1
    if stale_receipt is not None:
        print(f"[stale] previous marker moved to {stale_receipt}", file=sys.stderr)
    if stale_out is not None:
        print(f"[stale] previous snapshot moved to {stale_out}", file=sys.stderr)

    data_dir = Path(args.work_dir); data_dir.mkdir(parents=True, exist_ok=True)

    if args.program == "auto":
        info_f = data_dir / "_mint_info.json"
        ok = rpc_call(args.rpc, {"jsonrpc": "2.0", "id": 1, "method": "getAccountInfo",
                                 "params": [args.mint, {"encoding": "base64"}]}, info_f, 30)
        if not ok:
            print("FATAL: getAccountInfo(mint) 失败，无法自动判定 program——用 --program 显式指定", file=sys.stderr)
            sys.exit(1)
        mint_owner = (json.loads(info_f.read_text())["result"]["value"] or {}).get("owner")
        if mint_owner == T22:
            prog = T22
        elif mint_owner == SPL:
            prog = SPL
        else:
            print(f"FATAL: mint owner={mint_owner} 不是 SPL/Token-2022 程序", file=sys.stderr)
            sys.exit(1)
        print(f"program=auto → mint owner 判定为 {'Token-2022' if prog == T22 else '标准 SPL'}")
    else:
        prog = T22 if args.program == "token2022" else SPL

    # 冒烟：supply
    sup_f = data_dir / "_supply.json"
    ok = rpc_call(args.rpc, {"jsonrpc": "2.0", "id": 1, "method": "getTokenSupply",
                             "params": [args.mint]}, sup_f, 30)
    if not ok:
        print("FATAL: getTokenSupply 失败", file=sys.stderr); sys.exit(1)
    supply_slot, decimals, supply_raw = parse_supply_response(json.loads(sup_f.read_text()))
    if supply_slot != args.as_of_slot:
        print(f"FATAL: getTokenSupply slot={supply_slot} != frozen slot={args.as_of_slot}",
              file=sys.stderr)
        return 1
    print(f"supply={supply_raw} decimals={decimals} ui={supply_raw/10**decimals:,.2f}")

    # Token-2022 extension 账户长度不封顶，正式默认必须无 dataSize 全扫。
    accounts = []
    try:
        ds_list = choose_datasizes(prog, args.datasizes)
    except ValueError:
        print("FATAL: Token-2022 正式快照必须无 dataSize 全扫；扩展账户长度不封顶。"
              "请使用 --datasizes all（或默认 auto）并选择支持该查询的 RPC。", file=sys.stderr)
        sys.exit(2)
    scan_receipts = []
    for ds in ds_list:
        raw_f = data_dir / f"_gpa_raw_{ds}.json"
        meta_f = data_dir / f"_gpa_raw_{ds}.meta.json"
        t0 = time.time()
        reused = False
        filters = [{"memcmp": {"offset": 0, "bytes": args.mint}}]
        if ds != "all":
            filters.insert(0, {"dataSize": ds})
        expected_identity = {"schema": "solana-gpa-cache-v2", "mint": args.mint,
                             "program": prog, "rpc": args.rpc, "filters": filters,
                             "supply_observed_slot": supply_slot}
        if raw_f.exists() and raw_f.stat().st_size > 100:
            try:
                resp = json.loads(raw_f.read_text())
                meta = json.loads(meta_f.read_text()) if meta_f.exists() else {}
                reused = "result" in resp and cache_identity_matches(meta, expected_identity)
            except Exception:
                reused = False
        if reused:
            age_h = (time.time() - raw_f.stat().st_mtime) / 3600
            print(f"[warn] 复用缓存 {raw_f.name}（{age_h:.1f} 小时前）——数据非实时；"
                  f"增量更新/要最新快照请先删除或改名该缓存", file=sys.stderr)
        if not reused:
            payload = {"jsonrpc": "2.0", "id": 1, "method": "getProgramAccounts", "params": [
                prog, {"encoding": "base64", "dataSlice": {"offset": 32, "length": 40},
                       "filters": filters, "withContext": True,
                       **({"minContextSlot": supply_slot} if supply_slot is not None else {})}]}
            ok = rpc_call(args.rpc, payload, raw_f, args.timeout)
            if not ok:
                print(f"FATAL: getProgramAccounts dataSize={ds} 失败", file=sys.stderr); sys.exit(1)
            resp = json.loads(raw_f.read_text())
        try:
            batch, gpa_slot = parse_gpa_response(resp)
        except ValueError as exc:
            print(f"FATAL: RPC error (ds={ds}): {exc}", file=sys.stderr); sys.exit(1)
        if gpa_slot != args.as_of_slot:
            print(f"FATAL: GPA slot={gpa_slot} != frozen slot={args.as_of_slot}",
                  file=sys.stderr)
            return 1
        meta = {**expected_identity, "gpa_response_slot": gpa_slot, "account_count": len(batch)}
        if not reused:
            meta_f.write_text(json.dumps(meta, indent=2, sort_keys=True))
        elif json.loads(meta_f.read_text()) != meta:
            print(f"FATAL: 缓存 meta 与响应不闭合（ds={ds}）", file=sys.stderr)
            sys.exit(2)
        scan_receipts.append({**meta,
            "raw_artifact": {"path": raw_f.name, "size": raw_f.stat().st_size,
                             "sha256": sha256_file(raw_f)},
            "meta_artifact": {"path": meta_f.name, "size": meta_f.stat().st_size,
                              "sha256": sha256_file(meta_f)}})
        print(f"scan ds={ds}: {len(batch)} accounts, {raw_f.stat().st_size/1e6:.1f}MB, {time.time()-t0:.0f}s")
        accounts.extend(batch)
    accounts, rows, owners, malformed = parse_token_accounts(accounts)
    print(f"scan total: {len(accounts)} accounts (去重后)")

    total = sum(owners.values())
    print(f"nonzero token accounts={len(rows)}  unique owners={len(owners)}")
    print(f"对账: 扫描加总={total} vs getTokenSupply={supply_raw}  diff={supply_raw-total}")
    try:
        require_snapshot_closed(total, supply_raw, malformed)
    except ValueError:
        print(f"FATAL: holder snapshot 不闭合：malformed={malformed} "
              f"sum_accounts={total} supply={supply_raw} diff={supply_raw-total}。"
              "不得生成正式 holders 产物；换完整 RPC/检查过滤器后重跑。", file=sys.stderr)
        sys.exit(2)
    owners_sorted = owners
    accounts_out = data_dir / "holders_accounts.json"
    owners_out = data_dir / "holders_owners.json"
    accounts_out.write_text(json.dumps(rows))
    owners_out.write_text(json.dumps(owners_sorted))
    (data_dir / "holders_snapshot_meta.json").write_text(json.dumps({
        "schema": "solana-holder-snapshot-v2", "mint": args.mint, "program": prog,
        "target": {"chain": "solana", "token": args.mint.lower(),
                   "as_of_block": supply_slot},
        "verdict": "PASS", "exit_code": 0,
        "rpc": args.rpc, "supply_raw": str(supply_raw), "sum_accounts_raw": str(total),
        "decimals": decimals, "closed": True,
        "producer": {"path": "scan_token_accounts.py", "sha256": sha256_file(__file__)},
        "supply_receipt": {"path": sup_f.name, "size": sup_f.stat().st_size,
                           "sha256": sha256_file(sup_f)},
        "outputs": {
            "holders_accounts": {"path": accounts_out.name, "size": accounts_out.stat().st_size,
                                 "sha256": sha256_file(accounts_out)},
            "holders_owners": {"path": owners_out.name, "size": owners_out.stat().st_size,
                               "sha256": sha256_file(owners_out)}},
        "scans": scan_receipts,
    }, indent=2, sort_keys=True))

    snapshot = {
        "schema": "solana-holder-snapshot/v3",
        "target": {"chain": "solana", "token": args.mint.lower(),
                   "as_of_block": args.as_of_slot},
        "mint": args.mint,
        "program": prog,
        "rpc": args.rpc,
        "decimals": decimals,
        "supply_raw": str(supply_raw),
        "sum_accounts_raw": str(total),
        "closed": True,
        "accounts": rows,
        "owners": owners_sorted,
    }
    envelope = build_envelope(
        "solana-holder-snapshot-receipt/v3",
        snapshot["target"], __file__, "formal",
        inputs={"supply_rpc": sup_f,
                **{f"gpa_{i}": data_dir / scan["raw_artifact"]["path"]
                   for i, scan in enumerate(scan_receipts)}})
    data_bytes = (json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n").encode()
    receipt = finalize_envelope(
        envelope, "PASS", 0, closed=True,
        supply_raw=str(supply_raw), sum_accounts_raw=str(total),
        observed_slots={"supply": supply_slot,
                        "gpa": [scan["gpa_response_slot"] for scan in scan_receipts]},
        output={"path": str(Path(args.out).resolve()), "size": len(data_bytes),
                "sha256": hashlib.sha256(data_bytes).hexdigest()})
    try:
        publish_txn(args.out, snapshot, args.receipt, receipt)
    except Exception as exc:
        print(f"FATAL: snapshot transaction publish failed: {exc}", file=sys.stderr)
        return 1

    ui = lambda x: x / 10**decimals
    tiers = [(1e6, ">=100万"), (1e5, "10-100万"), (1e4, "1-10万"), (1e3, "1千-1万"), (0, "<1千")]
    cnt = {label: [0, 0] for _, label in tiers}
    for amt in owners.values():
        u = ui(amt)
        for thr, label in tiers:
            if u >= thr:
                cnt[label][0] += 1; cnt[label][1] += amt
                break
    print("五档分层（owner 口径）:")
    for _, label in tiers:
        c, s = cnt[label]
        print(f"  {label:>8}: {c:>6} owners  {ui(s):>18,.0f} 枚  {s/total*100:6.2f}%")

    print("top20 owners:")
    for i, (o, amt) in enumerate(list(owners_sorted.items())[:20], 1):
        print(f"  #{i:<3}{o}  {ui(amt):>16,.0f}  {amt/total*100:6.3f}%")


if __name__ == "__main__":
    raise SystemExit(main())
