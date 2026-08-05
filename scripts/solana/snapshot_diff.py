#!/usr/bin/env python3
"""新旧持仓快照 diff（data-pipeline-solana §10 快照对比法核心件）。

用法:
  python3 snapshot_diff.py --old data/holders_owners_旧日期.json --new data/holders_owners.json \
      [--entities entity_map.json] [--min-delta 1000000] [--decimals 6]

输入:
  --old/--new  owner→raw 余额 dict(scan_token_accounts.py 的 holders_owners.json)
  --entities   可选 {地址: 标签} JSON——旧研报实体表(appendix whale_groups+观察哨地址),
               命中者在输出中带标签;不给则全部按匿名地址处理
输出:
  data/snapshot_diff.json + stdout(实体逐址变动 / 大额变动榜含新面孔与清零标注 / 新 top30 粗筛)

来源:CLUDE(Solana) 增量更新 2026-07-15(61 个百万枚级变动地址全覆盖定性的第一步)。
"""
import argparse, json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--entities", default=None, help="{addr: label} JSON,可选")
    ap.add_argument("--min-delta", type=float, default=1_000_000, help="大额变动榜阈值(UI 枚)")
    ap.add_argument("--decimals", type=int, default=6)
    ap.add_argument("--out", default="data/snapshot_diff.json")
    args = ap.parse_args()

    old = {k: int(v) for k, v in json.loads(Path(args.old).read_text()).items()}
    new = {k: int(v) for k, v in json.loads(Path(args.new).read_text()).items()}
    ent = json.loads(Path(args.entities).read_text()) if args.entities else {}
    dec = 10 ** args.decimals
    supply_old, supply_new = sum(old.values()), sum(new.values())

    def ui(raw): return raw / dec
    def pct(raw): return raw / supply_new * 100 if supply_new else 0.0

    print(f"旧快照 owner={len(old)}  新快照 owner={len(new)}  (+{len(new)-len(old)})")
    print(f"加总: 旧 {supply_old} -> 新 {supply_new}  (Δ {ui(supply_new-supply_old):+,.2f} 枚,负=窗口内销毁)")
    print()
    if ent:
        print("== 旧实体逐址变动 ==")
        for addr, tag in ent.items():
            o, n = old.get(addr, 0), new.get(addr, 0)
            d = n - o
            flag = "  " if d == 0 else ("↑↑" if d > 0 else "↓↓")
            print(f"{flag} {tag:<30} 旧 {ui(o):>14,.0f}  新 {ui(n):>14,.0f}  Δ {ui(d):>+13,.0f}  ({pct(n):.3f}%)")
        print()

    thr = int(args.min_delta * dec)
    rows = []
    for k in set(old) | set(new):
        o, n = old.get(k, 0), new.get(k, 0)
        d = n - o
        if abs(d) >= thr:
            rows.append({"owner": k, "old_raw": o, "new_raw": n, "delta_raw": d,
                         "old_ui": ui(o), "new_ui": ui(n), "delta_ui": ui(d),
                         "new_pct": pct(n), "tag": ent.get(k, ""),
                         "is_new_face": o == 0, "zeroed": n == 0 and o > 0})
    rows.sort(key=lambda r: r["delta_raw"])
    print(f"== 大额变动榜(|Δ|>= {args.min_delta:,.0f} 枚,共 {len(rows)} 址)==")
    for r in rows:
        mark = r["tag"] or ("★新面孔" if r["is_new_face"] else ("→清零" if r["zeroed"] else ""))
        print(f"  Δ{r['delta_ui']:>+13,.0f}  旧{r['old_ui']:>13,.0f} 新{r['new_ui']:>13,.0f} ({r['new_pct']:5.2f}%)  {r['owner']}  {mark}")

    Path(args.out).write_text(json.dumps(
        {"old_file": args.old, "new_file": args.new,
         "supply_old_raw": supply_old, "supply_new_raw": supply_new,
         "owners_old": len(old), "owners_new": len(new), "big_moves": rows},
        ensure_ascii=False, indent=1))
    print(f"\n明细已写 {args.out}")

    print("\n== 新 top30(非实体地址,升级/新庄候选粗筛)==")
    for i, (k, v) in enumerate(sorted(new.items(), key=lambda kv: -kv[1])[:30], 1):
        if k in ent:
            continue
        d = v - old.get(k, 0)
        print(f"  #{i:<3} {k}  {ui(v):>14,.0f} ({pct(v):5.2f}%)  Δ{ui(d):>+12,.0f}")


if __name__ == "__main__":
    main()
