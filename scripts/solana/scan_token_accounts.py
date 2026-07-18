#!/usr/bin/env python3
"""SPL / Token-2022 全量持仓扫描（getProgramAccounts + dataSlice{32,40}）。

用法：python3 scan_token_accounts.py <mint> [--program token2022|spl] [--rpc URL]
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
            ["curl", "-s", "-m", str(timeout), url, "-X", "POST",
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mint")
    ap.add_argument("--program", choices=["token2022", "spl"], default="token2022")
    ap.add_argument("--rpc", default="https://solana-rpc.publicnode.com")
    ap.add_argument("--datasizes", default="165,170",
                    help="逗号分隔的 dataSize 列表，或 'all'=无 dataSize 过滤单发全扫"
                         "（publicnode 会 504；api.mainnet-beta 实测放行，2026-07-13）")
    args = ap.parse_args()

    prog = T22 if args.program == "token2022" else SPL
    data_dir = Path("data"); data_dir.mkdir(exist_ok=True)

    # 冒烟：supply
    sup_f = data_dir / "_supply.json"
    ok = rpc_call(args.rpc, {"jsonrpc": "2.0", "id": 1, "method": "getTokenSupply",
                             "params": [args.mint]}, sup_f, 30)
    if not ok:
        print("FATAL: getTokenSupply 失败", file=sys.stderr); sys.exit(1)
    sup = json.loads(sup_f.read_text())["result"]["value"]
    decimals, supply_raw = sup["decimals"], int(sup["amount"])
    print(f"supply={supply_raw} decimals={decimals} ui={supply_raw/10**decimals:,.2f}")

    # 全量扫描（逐 dataSize 扫描合并——publicnode 对无 dataSize 过滤的 Token-2022 扫描 504）
    accounts = []
    ds_list = ["all"] if args.datasizes == "all" else [int(x) for x in args.datasizes.split(",")]
    for ds in ds_list:
        raw_f = data_dir / f"_gpa_raw_{ds}.json"
        t0 = time.time()
        reused = False
        if raw_f.exists() and raw_f.stat().st_size > 100:
            try:
                resp = json.loads(raw_f.read_text())
                reused = "result" in resp
            except Exception:
                reused = False
        if reused:
            age_h = (time.time() - raw_f.stat().st_mtime) / 3600
            print(f"[warn] 复用缓存 {raw_f.name}（{age_h:.1f} 小时前）——数据非实时；"
                  f"增量更新/要最新快照请先删除或改名该缓存", file=sys.stderr)
        if not reused:
            filters = [{"memcmp": {"offset": 0, "bytes": args.mint}}]
            if ds != "all":
                filters.insert(0, {"dataSize": ds})
            payload = {"jsonrpc": "2.0", "id": 1, "method": "getProgramAccounts", "params": [
                prog, {"encoding": "base64", "dataSlice": {"offset": 32, "length": 40},
                       "filters": filters}]}
            ok = rpc_call(args.rpc, payload, raw_f, 150)
            if not ok:
                print(f"FATAL: getProgramAccounts dataSize={ds} 失败", file=sys.stderr); sys.exit(1)
            resp = json.loads(raw_f.read_text())
        if "error" in resp:
            print(f"FATAL: RPC error (ds={ds}): {resp['error']}", file=sys.stderr); sys.exit(1)
        batch = resp["result"]
        print(f"scan ds={ds}: {len(batch)} accounts, {raw_f.stat().st_size/1e6:.1f}MB, {time.time()-t0:.0f}s")
        accounts.extend(batch)
    seen_pk = set()
    accounts = [a for a in accounts if not (a["pubkey"] in seen_pk or seen_pk.add(a["pubkey"]))]
    print(f"scan total: {len(accounts)} accounts (去重后)")

    rows, owners = [], {}
    for a in accounts:
        raw = base64.b64decode(a["account"]["data"][0])
        if len(raw) < 40:
            continue
        owner = b58encode(raw[0:32])
        amount = int.from_bytes(raw[32:40], "little")
        if amount == 0:
            continue
        rows.append({"account": a["pubkey"], "owner": owner, "amount_raw": amount})
        owners[owner] = owners.get(owner, 0) + amount

    (data_dir / "holders_accounts.json").write_text(json.dumps(rows))
    owners_sorted = dict(sorted(owners.items(), key=lambda kv: -kv[1]))
    (data_dir / "holders_owners.json").write_text(json.dumps(owners_sorted))

    total = sum(owners.values())
    print(f"nonzero token accounts={len(rows)}  unique owners={len(owners)}")
    print(f"对账: 扫描加总={total} vs getTokenSupply={supply_raw}  diff={supply_raw-total}")

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
