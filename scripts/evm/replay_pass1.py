#!/usr/bin/env python3
"""第一遍重放：多通道 CSV 按块段互斥拼接去重 → merged.csv + 终态余额 + 历史峰值 + mint 账本 + 供给闭合。
来源：PING(Base) 分析会话实战产物，2026-07-17（v2.26 收编参数化）。

为什么必须按块段划通道归属（必读）：HyperSync uniqueId 尾号=链上 log_index，
Alchemy uniqueId 尾号=类别内序号——语义不同，跨通道按 (tx,尾号) 去重必然失败
（重叠段双计，实测造出 5,485 个负余额地址）。本脚本要求各通道块段互斥，
段内用自家 (tag,tx,尾号) 键去重；负余额地址数=0 才算过对账 gate。

用法：python3 replay_pass1.py --channels channels.json [--out-dir data]
channels.json 示例（lo<=block<hi 才收，各段必须互斥，重叠即报错退出）：
  {"channels": [
     {"path": "data/transfers_full.csv",          "lo": 0,        "hi": 37284486, "tag": "hs"},
     {"path": "data_alchemy3/transfers_full.csv", "lo": 37284486, "hi": 38000000, "tag": "a3"},
     {"path": "data_alchemy2/transfers_full.csv", "lo": 38000000, "hi": 43000000, "tag": "a2"},
     {"path": "data_alchemy/transfers_full.csv",  "lo": 43000000, "hi": 99999999999, "tag": "a1"}]}
输入 CSV 列：block,ts,tx,from,to,value,uniqueId（fetch_hypersync/fetch_alchemy 输出格式）
输出（--out-dir 下）：merged.csv、balances_final.json、peaks.json（峰值≥总铸量 0.1%，含 peak_blk/first_blk/last_blk）、
  mint_ledger.json（from=0x0 按接收地址记，x402/批量代执行 mint 必须按接收方不按 tx.from）、replay_stats.json
"""
import csv, json, argparse
from collections import defaultdict

Z = '0x0000000000000000000000000000000000000000'
DEAD = '0x000000000000000000000000000000000000dead'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channels", required=True, help="channels.json（通道路径+互斥块段+tag）")
    ap.add_argument("--out-dir", default="data")
    ap.add_argument("--allow-bad-rows", type=int, default=0,
                    help="允许的坏行上限（默认 0=任何坏行即退出；显式放行须先核明原因）")
    a = ap.parse_args()
    chans = json.load(open(a.channels))["channels"]

    # 块段互斥校验：排序后相邻段不得重叠
    segs = sorted((c["lo"], c["hi"], c["tag"]) for c in chans)
    for (l1, h1, t1), (l2, h2, t2) in zip(segs, segs[1:]):
        if l2 < h1:
            raise SystemExit(f"块段重叠：{t1}=[{l1},{h1}) 与 {t2}=[{l2},{h2}) ——通道归属必须互斥")

    rows = {}  # (tag,tx,uid尾号) -> (block, ts, from, to, value)；段互斥保证全局无重
    # 坏行记账（fail-closed 修复 2026-07-22）：结构坏（列数≠7）与字段坏（数字解析失败）
    # 一律计数+留样本，默认存在坏行即退出（--allow-bad-rows N 显式放行上限）。
    # 修复前 except: continue 静默丢行——坏行数从不可见，与对账三查精神冲突。
    bad_rows, bad_samples = 0, []
    for c in chans:
        n = 0
        try:
            f = open(c["path"])
        except FileNotFoundError:
            print(f"[warn] 缺文件 {c['path']}（tag={c['tag']}），跳过")
            continue
        r = csv.DictReader(f)
        header = set(r.fieldnames or [])
        legacy = {"block", "ts", "tx", "from", "to", "uniqueId"} <= header \
            and ("value" in header or "value_raw" in header)
        standard8 = {"block", "ts", "tx", "log_index", "from", "to", "value_raw", "block_hash"} <= header
        if not (legacy or standard8):
            raise SystemExit(f"[fail-closed] {c['path']} CSV header 非 legacy7/standard8: {sorted(header)}")
        for row in r:
            if not row or not any(row.values()):
                continue          # 空行不算数据损坏
            blk, ts, tx, frm, to = (row.get(k) for k in ("block", "ts", "tx", "from", "to"))
            val = row.get("value_raw", row.get("value"))
            uid = row.get("uniqueId")
            try:
                b = int(blk)
            except (TypeError, ValueError):
                bad_rows += 1
                if len(bad_samples) < 5:
                    bad_samples.append((c["tag"], "block 非数字", [blk, tx]))
                continue
            if not (c["lo"] <= b < c["hi"]):
                continue          # 段外行属通道路由，不算坏行
            try:
                li = int(row["log_index"]) if standard8 else int(uid.rsplit(':', 1)[-1])
                v = int(val)
            except (TypeError, ValueError):
                bad_rows += 1
                if len(bad_samples) < 5:
                    bad_samples.append((c["tag"], "li/value 非数字", [blk, tx]))
                continue
            rows[(c["tag"], tx.lower(), li)] = (b, ts, frm.lower(), (to or Z).lower(), v)
            n += 1
        f.close()
        print(f"{c['tag']}=[{c['lo']},{c['hi']}) 收 {n} 条")
    print(f"合计事件 {len(rows)}（坏行 {bad_rows}）")
    if bad_rows > a.allow_bad_rows:
        print(f"[fail-closed] 坏行 {bad_rows} 条 > 允许上限 {a.allow_bad_rows}，样本：{bad_samples}")
        print("[fail-closed] 先核数据来源；确属可解释的格式例外再用 --allow-bad-rows 显式放行")
        raise SystemExit(5)

    events = sorted(rows.items(), key=lambda kv: (kv[1][0], kv[0][2]))
    bal = defaultdict(int)
    peak = defaultdict(int)  # 每地址历史峰值（块末口径）
    peak_blk = {}
    mint_total = burn_total = 0
    mint_by_to = defaultdict(int)
    first_seen, last_active = {}, {}
    prev_blk, touched = None, set()
    with open(f"{a.out_dir}/merged.csv", "w", newline="") as g:
        w = csv.writer(g)
        w.writerow(["block", "ts", "tx", "log_index", "from", "to", "value"])
        for (tag, tx, li), (blk, ts, frm, to, val) in events:
            if prev_blk is not None and blk != prev_blk:
                for ad in touched:
                    if bal[ad] > peak[ad]:
                        peak[ad] = bal[ad]
                        peak_blk[ad] = prev_blk
                touched = set()
            prev_blk = blk
            w.writerow([blk, ts, tx, li, frm, to, val])
            if frm == Z:
                mint_total += val
                mint_by_to[to] += val
            else:
                bal[frm] -= val
                touched.add(frm)
            if to in (Z, DEAD):
                burn_total += val
            bal[to] += val
            touched.add(to)
            for ad in (frm, to):
                if ad != Z and ad not in first_seen:
                    first_seen[ad] = blk
            if frm != Z:
                last_active[frm] = blk
            last_active[to] = blk
    for ad in touched:
        if bal[ad] > peak[ad]:
            peak[ad] = bal[ad]
            peak_blk[ad] = prev_blk

    su = sum(bal.values())
    neg = [(ad, v) for ad, v in bal.items() if v < 0]
    peak_min = mint_total // 1000  # 峰值 ≥ 总铸量 0.1% 才存
    stats = {"events": len(rows), "mint_total_wei": str(mint_total), "burn_total_wei": str(burn_total),
             "sum_balances_wei": str(su), "supply_check_ok": su == mint_total,
             "neg_balance_addrs": len(neg), "unique_addrs": len(bal),
             "gate_pass": su == mint_total and len(neg) == 0,
             "n_bad_rows": bad_rows}
    json.dump(stats, open(f"{a.out_dir}/replay_stats.json", "w"), indent=1)
    json.dump({ad: str(v) for ad, v in bal.items() if v != 0}, open(f"{a.out_dir}/balances_final.json", "w"))
    json.dump({ad: {"peak": str(v), "peak_blk": peak_blk.get(ad), "first_blk": first_seen.get(ad), "last_blk": last_active.get(ad)}
               for ad, v in peak.items() if v >= peak_min}, open(f"{a.out_dir}/peaks.json", "w"))
    json.dump({ad: str(v) for ad, v in mint_by_to.items()}, open(f"{a.out_dir}/mint_ledger.json", "w"))
    print("stats:", json.dumps(stats, indent=1))
    print("负余额地址数:", len(neg), neg[:3] if neg else "（=0 才过 gate）")
    top = sorted(bal.items(), key=lambda kv: -kv[1])[:15]
    print("终态top15（%按总铸量）:")
    for ad, v in top:
        print(f"  {ad} {v/1e18/1e6:.2f}M ({v/mint_total*100 if mint_total else 0:.3f}%)")


if __name__ == "__main__":
    main()
