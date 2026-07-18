#!/usr/bin/env python3
"""U0 辅助：从旧全量转账文件从零重放出 wei 级精确期末余额快照（EVM）。

用途：旧研报的期末快照可能是 float"枚"格式（float64 精度不足 wei 级，直接喂
replay_inc 会错 10^18 倍）——旧全量转账在场时，从零重放即得精确 wei 快照，
同时与旧 float 快照逐址互验（独立复算旧账本：供给闭合 + 偏差 >1 枚清单）。
来源：CASHCAT(Robinhood) 增量更新 2026-07-15 参数化收编（v2.12.0）。

用法（工作目录含 config.json，需 total_supply_tokens/decimals）：
  python3 rebuild_wei_balances.py [--old data/transfers.jsonl.gz]
      [--float-snapshot data/balances_final.json]   # 可选：旧 float 快照互验
      [--out data/balances_wei.json]
输出 {addr: str_wei}（零余额剔除），可直接作 replay_inc 的 --old-balances。
去重口径与 replay_inc 一致：(tx, logi) 全局去重。
"""
import argparse, gzip, json, os, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", default="data/transfers.jsonl.gz")
    ap.add_argument("--float-snapshot", default=None,
                    help="旧 float 枚快照路径（存在则互验，容差 1 枚）")
    ap.add_argument("--out", default="data/balances_wei.json")
    args = ap.parse_args()

    with open("config.json") as f:
        cfg = json.load(f)
    dec = int(cfg.get("decimals", 18))
    total = int(cfg["total_supply_tokens"]) * 10 ** dec
    unit = 10 ** dec

    bal, seen, n, dup = {}, set(), 0, 0
    with gzip.open(args.old, "rt") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            key = (r["tx"], r["logi"])
            if key in seen:
                dup += 1
                continue
            seen.add(key)
            amt = int(r["amount"])
            fr, to = r["from"].lower(), r["to"].lower()
            bal[fr] = bal.get(fr, 0) - amt
            bal[to] = bal.get(to, 0) + amt
            n += 1

    zero = "0x" + "0" * 40
    mint_net = -bal.get(zero, 0)
    pos = {a: v for a, v in bal.items() if v > 0 and a != zero}
    neg = {a: v for a, v in bal.items() if v < 0 and a != zero}
    sum_pos = sum(pos.values())
    print(f"重放 {n} 条（去重 {dup}），地址数 {len(bal)}；净铸出 {mint_net / unit:,.0f} 枚")
    ok = sum_pos == mint_net and not neg
    print(f"供给闭合: 正余额合计 {sum_pos} vs 净铸出 {mint_net} → {'PASS' if ok else 'FAIL'}")
    if neg:
        print(f"⚠ 负余额地址 {len(neg)} 个（数据有洞）:", list(neg.items())[:5])

    snap = args.float_snapshot
    if snap and os.path.exists(snap):
        old = json.load(open(snap))
        if isinstance(old.get("balances"), dict):
            old = old["balances"]
        bad = 0
        for a, v in old.items():
            w = bal.get(a.lower(), 0)
            try:
                fv = float(v)
            except (TypeError, ValueError):
                continue
            if abs(w / unit - fv) > 1.0:
                bad += 1
                if bad <= 5:
                    print(f"  互验偏差>1枚: {a} float={v} wei重放={w / unit}")
        lower_old = {k.lower() for k in old}
        extra = [a for a, v in pos.items() if a not in lower_old and v > unit]
        print(f"与 float 快照互验：{len(old)} 址偏差>1枚 {bad} 个；重放多出的>1枚地址 {len(extra)} 个")
        if bad or extra:
            print("⚠ 互验未全过——先查旧快照口径（截止块/剔除名单）再继续")

    json.dump({a: str(v) for a, v in bal.items() if v != 0}, open(args.out, "w"))
    print(f"落盘 {args.out}")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
