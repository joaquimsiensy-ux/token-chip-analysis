#!/usr/bin/env python3
"""U2 增量重放：旧期末余额快照 + 增量转账 → 最新全量余额表 + 每地址窗口行为统计，
含供给闭合检查与可选的双路径互验。

来源：RAXOL/Pointless/TRASH/VEX 四次 /token-update 实战合并参数化收编（v2.10.0）——
重放骨架四战同构；全局 (tx,logi) 去重与窗口统计取 Pointless 版（比单边界去重更鲁棒、
下游 analyze_inc 直接复用统计）；双路径互验（--full）取 Pointless 版。

用法（工作目录含 config.json）：
  python3 replay_inc.py --old-balances data/balances_now.json
                        [--inc data/transfers_inc.jsonl.gz]
                        [--cutoff-block N]          # 默认取增量文件首行块（重叠窗设计）
                        [--full data/transfers.jsonl.gz]   # 可选：全量从零重放互验
                        [--out data/balances_new.json] [--stats data/window_stats.json]
输入旧快照格式：{addr: str_wei} 或 {"balances": {...}} 均可（各期实战文件名不一，常见
  balances_now.json / balances_latest.json / balances.json / replay_final_balances.json）。
输出：
  --out   {"last_block","last_ts","cutoff_block","balances":{addr:str_wei 非零}}
  --stats {addr:{buy,sell,t_in,t_out,burn(str wei),n_buy,n_sell,n_tx,first_ts,last_ts}}
          buy/sell=与 config pools 直接对手；t_in/t_out=非池转账；burn=入 0x0/dead。
供给闭合：全地址余额和应=0；正余额合计与 total_supply−累计烧毁 比对；负余额地址应仅 0x0。
对不上=增量数据有洞（最常见：重叠窗处理错、窗口内漏段）＝回 U1 补，不许"差不多"。
退出码（v3.3 硬关卡）：非零地址负余额=1；旧快照含 ZERO 负项且全网恒等式不闭合=1；
  正余额型旧快照（无 ZERO 键，实战两种格式并存）恒等式不适用、打 NOTE 降级为对表关卡兜底。
"""
import argparse, gzip, json, sys
from collections import defaultdict

ZERO = "0x" + "0" * 40
DEAD = "0x" + "0" * 36 + "dead"


def load_balances(path):
    with open(path) as f:
        d = json.load(f)
    if "balances" in d and isinstance(d["balances"], dict):
        d = d["balances"]
    return {k.lower(): int(v) for k, v in d.items()}


def load_cfg():
    with open("config.json") as f:
        cfg = json.load(f)
    dec = int(cfg.get("decimals", 18))
    total = int(cfg["total_supply_tokens"]) * 10 ** dec
    pools = set(a.lower() for a in (cfg.get("pools") or {}))
    for key in ("pool", "pool_manager"):
        if cfg.get(key):
            pools.add(cfg[key].lower())
    for p in cfg.get("v2_pairs") or []:
        pools.add(p.lower())
    return total, dec, pools


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-balances", required=True, help="旧期末余额快照 JSON")
    ap.add_argument("--inc", default="data/transfers_inc.jsonl.gz")
    ap.add_argument("--cutoff-block", type=int, default=None,
                    help="旧快照截止块；<=该块的增量行跳过（默认取增量文件首行块）")
    ap.add_argument("--full", default=None, help="可选：旧全量转账文件，从零重放双路径互验")
    ap.add_argument("--out", default="data/balances_new.json")
    ap.add_argument("--stats", default="data/window_stats.json")
    args = ap.parse_args()

    total, dec, pools = load_cfg()
    unit = 10 ** dec
    bal = defaultdict(int)
    old_bal = load_balances(args.old_balances)
    old_has_zero = ZERO in old_bal  # 旧快照是否保留 mint 负项（两种格式实战都存在，决定恒等式关卡是否适用）
    for k, v in old_bal.items():
        bal[k] = v

    rows = []
    with gzip.open(args.inc, "rt") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    if not rows:
        sys.exit(f"{args.inc} 为空")
    rows.sort(key=lambda r: (r["block"], r["logi"]))
    cutoff = args.cutoff_block if args.cutoff_block is not None else rows[0]["block"]

    stats = defaultdict(lambda: {"buy": 0, "sell": 0, "t_in": 0, "t_out": 0, "burn": 0,
                                 "n_buy": 0, "n_sell": 0, "n_tx": 0,
                                 "first_ts": None, "last_ts": None})

    def touch(a, ts):
        s = stats[a]
        if s["first_ts"] is None:
            s["first_ts"] = ts
        s["last_ts"] = ts
        s["n_tx"] += 1

    seen = set()
    n = skipped = dup = 0
    burned_total = 0
    last_block = last_ts = 0
    for r in rows:
        if r["block"] <= cutoff:
            skipped += 1
            continue
        key = (r["tx"], r["logi"])
        if key in seen:
            dup += 1
            continue
        seen.add(key)
        amt = int(r["amount"])
        frm, to, ts = r["from"].lower(), r["to"].lower(), r.get("ts")
        bal[frm] -= amt
        bal[to] += amt
        n += 1
        last_block, last_ts = r["block"], ts
        # 窗口行为归因
        if frm in pools and to not in pools:
            stats[to]["buy"] += amt
            stats[to]["n_buy"] += 1
            touch(to, ts)
        elif to in pools and frm not in pools:
            stats[frm]["sell"] += amt
            stats[frm]["n_sell"] += 1
            touch(frm, ts)
        elif frm not in pools and to not in pools:
            if to in (ZERO, DEAD):
                stats[frm]["burn"] += amt
                touch(frm, ts)
            else:
                stats[frm]["t_out"] += amt
                stats[to]["t_in"] += amt
                touch(frm, ts)
                touch(to, ts)
        if to in (ZERO, DEAD):
            burned_total += amt

    print(f"重放 {n} 条（跳过重叠窗内 {skipped} 条、去重 {dup} 条），窗口末块 {last_block}")

    # ── 供给闭合（v3.3 硬关卡：恒等式与负余额由退出码兜底，不再只打印） ──
    sum_all = sum(bal.values())
    pos = {k: v for k, v in bal.items() if v > 0 and k != ZERO}
    neg = {k: v for k, v in bal.items() if v < 0 and k != ZERO}
    sum_pos = sum(pos.values())
    print(f"全地址余额和(应=0): {sum_all}")
    print(f"正余额合计 {sum_pos} vs total_supply {total} → "
          f"{'PASS' if sum_pos == total else 'Δ=' + str(sum_pos - total) + '（有烧毁到0x0则为负常态，人工核对）'}")
    if neg:
        print(f"FAIL: 非零地址出现负余额=数据有洞（漏段/重叠窗错），回 U1 补数据: {list(neg.items())[:5]}")
        sys.exit(1)
    if sum_all != 0:
        if old_has_zero:
            print(f"FAIL: 全地址余额和 {sum_all} ≠ 0——旧快照含 ZERO 负项，恒等式必须闭合；数据有洞，回 U1 补数据")
            sys.exit(1)
        print("NOTE: 旧快照未保留 ZERO/mint 负项（正余额型快照），全网恒等式不适用——"
              "供给闭合由上方 sum_pos vs total 人工核对 + verify_balances 对表关卡兜底")
    print(f"持币地址数: {len(pos)}")

    # ── 可选双路径互验 ──
    if args.full:
        bal2 = defaultdict(int)
        seen2 = set()
        n2 = 0
        for path in (args.full, args.inc):
            with gzip.open(path, "rt") as f:
                for line in f:
                    if not line.strip():
                        continue
                    r = json.loads(line)
                    key = (r["tx"], r["logi"])
                    if key in seen2:
                        continue
                    seen2.add(key)
                    amt = int(r["amount"])
                    bal2[r["from"].lower()] -= amt
                    bal2[r["to"].lower()] += amt
                    n2 += 1
        mism = [(a, bal.get(a, 0), bal2.get(a, 0))
                for a in set(bal) | set(bal2) if bal.get(a, 0) != bal2.get(a, 0)]
        print(f"双路径互验：全量从零重放 {n2} 条，逐地址比对 → "
              f"{'PASS 0 不匹配' if not mism else 'FAIL ' + str(len(mism)) + ' 址不匹配'}")
        for a, x, y in mism[:8]:
            print(f"  {a}: 快照+增量 {x} vs 全量 {y} (Δ {x - y:+})")
        if mism:
            sys.exit(1)

    with open(args.out, "w") as f:
        json.dump({"last_block": last_block, "last_ts": last_ts, "cutoff_block": cutoff,
                   "balances": {k: str(v) for k, v in bal.items() if v != 0}}, f)
    with open(args.stats, "w") as f:
        json.dump({a: {k: (str(v) if k in ("buy", "sell", "t_in", "t_out", "burn") else v)
                       for k, v in s.items()} for a, s in stats.items()}, f)
    print(f"落盘 {args.out}（{len([v for v in bal.values() if v])} 址）+ {args.stats}（{len(stats)} 址）")

    print("--- 最新 top20 ---")
    for a, v in sorted(pos.items(), key=lambda x: -x[1])[:20]:
        print(f"{a}  {v / unit:>16,.0f}  {v / total * 100:6.3f}%")


if __name__ == "__main__":
    main()
