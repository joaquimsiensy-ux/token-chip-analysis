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
import argparse, base64, json, subprocess, sys, time
from pathlib import Path

SPL = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
T22 = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
ALPHA = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


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
    args = ap.parse_args()

    data_dir = Path("data"); data_dir.mkdir(exist_ok=True)

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
    sup_result = json.loads(sup_f.read_text())["result"]
    sup = sup_result["value"]
    supply_slot = (sup_result.get("context") or {}).get("slot")
    decimals, supply_raw = sup["decimals"], int(sup["amount"])
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
        if "error" in resp:
            print(f"FATAL: RPC error (ds={ds}): {resp['error']}", file=sys.stderr); sys.exit(1)
        result = resp["result"]
        if isinstance(result, dict) and "value" in result:
            batch = result["value"]
            gpa_slot = (result.get("context") or {}).get("slot")
        else:  # old RPC compatibility: still bind an unknown upper slot and refuse cache promotion
            batch = result
            gpa_slot = None
        meta = {**expected_identity, "gpa_response_slot": gpa_slot, "account_count": len(batch)}
        if not reused:
            meta_f.write_text(json.dumps(meta, indent=2, sort_keys=True))
        elif json.loads(meta_f.read_text()) != meta:
            print(f"FATAL: 缓存 meta 与响应不闭合（ds={ds}）", file=sys.stderr)
            sys.exit(2)
        scan_receipts.append(meta)
        print(f"scan ds={ds}: {len(batch)} accounts, {raw_f.stat().st_size/1e6:.1f}MB, {time.time()-t0:.0f}s")
        accounts.extend(batch)
    seen_pk = set()
    accounts = [a for a in accounts if not (a["pubkey"] in seen_pk or seen_pk.add(a["pubkey"]))]
    print(f"scan total: {len(accounts)} accounts (去重后)")

    rows, owners, malformed = [], {}, 0
    for a in accounts:
        raw = base64.b64decode(a["account"]["data"][0])
        if len(raw) < 40:
            malformed += 1
            continue
        owner = b58encode(raw[0:32])
        amount = int.from_bytes(raw[32:40], "little")
        if amount == 0:
            continue
        rows.append({"account": a["pubkey"], "owner": owner, "amount_raw": amount})
        owners[owner] = owners.get(owner, 0) + amount

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
    owners_sorted = dict(sorted(owners.items(), key=lambda kv: -kv[1]))
    (data_dir / "holders_accounts.json").write_text(json.dumps(rows))
    (data_dir / "holders_owners.json").write_text(json.dumps(owners_sorted))
    (data_dir / "holders_snapshot_meta.json").write_text(json.dumps({
        "schema": "solana-holder-snapshot-v2", "mint": args.mint, "program": prog,
        "rpc": args.rpc, "supply_raw": str(supply_raw), "sum_accounts_raw": str(total),
        "decimals": decimals, "closed": True, "scans": scan_receipts,
    }, indent=2, sort_keys=True))

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
    main()
