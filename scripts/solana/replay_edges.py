#!/usr/bin/env python3
"""SQD 转账边重放引擎（所有 SQD 链分析的下游标准件）。

读 fetch_sqd_transfers.py 落盘的 data/soltx-<小写mint>.jsonl.gz，边格式
[ts, slot, from_owner, to_owner, amount_raw]，ZERO(0x00…00)=铸造/销毁哨兵。

子命令：
  reconcile             全量重放 → 供给闭合 + 末态 vs 快照 top50 对账（阶段2关卡）
                        需 data/holders_owners.json（scan_token_accounts.py 产物）
  trace <addr> [n]      单地址全部进出边（时间序，默认显示 200 条）
  top [n]               重放末态 top n（默认 30）
  sniper [分钟]         发射后 N 分钟内首次收币的地址集（狙击窗，默认 30）
  mints                 全部铸造/销毁边清单（★pump.fun 币第一优先检查项：
                        创建 tx 的铸造边可有多条，dev-buy 直分收币地址可不是 creator）
  evolution             小时级阵营占比序列（含质押修正）→ data/camp_share_series.json
                        + 有效持仓末态 data/effective_balances.json

mint 来源：--mint / MINT 环境变量 / 工作目录 config.json 的 mint 字段。
evolution 的阵营定义读 --camps camps.json：{"阵营名": [完整地址...]}；
"流动性池" 键列池子地址；质押池用 --stake-pool（或 config.json 的 stake_pools 数组）——
与质押池的边改写为 owner 的质押子仓（有效持仓=现货+质押），防质押潮造成阵营虚降
（判别质押池本身用 pipeline §2 五步法）。
发射时刻默认取首条铸造边 ts，--launch-ts 可覆盖。
来源：PUB(Solana) 分析 2026-07-14 收编（replay+camp_evolution 合并参数化）。
"""
import argparse, gzip, json, os, sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# 批量标签库共享内核（v4 2026-07-17 接入 SOL 主流程；--no-labels 关闭）：
# top/sniper/trace 输出带标签标注（CEX/桥/程序/惯犯高亮），top 未命中大户落 miss 队列
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "labels"))
try:
    from labels_resolver import LabelResolver, append_misses
except Exception:
    LabelResolver = None
    append_misses = None
RESV = None


def lbl(addr):
    """输出行标注：命中标签库时返回 '  ⟨名字<类目>⟩'（serial 惯犯加🚨），未命中返回 ''。"""
    if RESV is None:
        return ""
    r = RESV.get(addr)
    if not r:
        return ""
    mark = "🚨惯犯:" if r.get("serial") else ""
    return f"  ⟨{mark}{r['name'][:36]}<{r['category']}>⟩"

ZERO = "0x" + "0" * 40


def resolve_mint(cli):
    if cli:
        return cli
    if os.environ.get("MINT"):
        return os.environ["MINT"]
    p = Path("config.json")
    if p.exists():
        m = json.loads(p.read_text()).get("mint")
        if m:
            return m
    sys.exit("mint 未指定：--mint / MINT 环境变量 / config.json:mint")


def load_edges(mint):
    f = Path(f"data/soltx-{mint.lower()}.jsonl.gz")
    if not f.exists():
        sys.exit(f"边文件不存在：{f}（先跑 fetch_sqd_transfers.py）")
    edges = []
    with gzip.open(f, "rt") as fh:
        for line in fh:
            if line.strip():
                edges.append(json.loads(line))
    edges.sort(key=lambda e: (e[1], e[0]))  # slot 序
    return edges


def replay(edges):
    bal = defaultdict(int)
    minted = burned = 0
    for ts, slot, src, dst, amt in edges:
        if src == ZERO:
            minted += amt
        else:
            bal[src] -= amt
        if dst == ZERO:
            burned += amt
        else:
            bal[dst] += amt
    return bal, minted, burned


def fmt_ts(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%m-%d %H:%M:%S")


def launch_ts_of(edges, override):
    if override:
        return override
    for ts, slot, src, dst, amt in edges:
        if src == ZERO:
            return ts
    return edges[0][0]


def cmd_reconcile(edges, dec):
    bal, minted, burned = replay(edges)
    print(f"边数={len(edges):,}  时间范围 {fmt_ts(edges[0][0])} → {fmt_ts(edges[-1][0])}")
    print(f"铸造={minted:,}  销毁={burned:,}  净={minted-burned:,}")
    neg = {a: v for a, v in bal.items() if v < -1}  # 负余额=数据洞
    print(f"负余额地址数={len(neg)}" + (f"  最大负值={min(neg.values()):,}" if neg else ""))
    rb = {a: v for a, v in bal.items() if v > 0}
    snap_f = Path("data/holders_owners.json")
    if snap_f.exists():
        snap = json.loads(snap_f.read_text())
        supply = sum(snap.values())
        print(f"快照 supply={supply:,}  重放净-快照差={minted-burned-supply:,}（快照晚于边末端会轻微漂移）")
        mismatch, checked = [], 0
        for a, v_snap in list(snap.items())[:50]:
            checked += 1
            if abs(rb.get(a, 0) - v_snap) > 2:
                mismatch.append((a, v_snap, rb.get(a, 0)))
        print(f"top50 对账：{checked-len(mismatch)}/{checked} 一致")
        for a, s_, r_ in mismatch[:12]:
            print(f"  MISMATCH {a}  快照={s_:,}  重放={r_:,}  差={r_-s_:,}")
    else:
        print("[提示] 无 data/holders_owners.json，跳过快照对账（关卡不完整）")
    json.dump(dict(sorted(rb.items(), key=lambda kv: -kv[1])),
              open("data/replay_final_balances.json", "w"))
    print("重放末态已写 data/replay_final_balances.json")


def cmd_trace(edges, addr, dec, limit):
    rows = [e for e in edges if e[2] == addr or e[3] == addr]
    print(f"{addr} 相关边 {len(rows)} 条（显示前 {limit}）")
    net = 0
    for ts, slot, src, dst, amt in rows[:limit]:
        d = "IN " if dst == addr else "OUT"
        other = src if dst == addr else dst
        net += amt if dst == addr else -amt
        print(f"{fmt_ts(ts)} {d} {amt/dec:>16,.2f}  对手 {other}{lbl(other)}")
    if len(rows) > limit:
        print(f"...({len(rows)-limit} 条省略)")
    print(f"净变动 {net/dec:,.2f}")


def cmd_top(edges, dec, n):
    bal, minted, burned = replay(edges)
    total = minted - burned
    top = sorted(bal.items(), key=lambda kv: -kv[1])[:n]
    for i, (a, v) in enumerate(top, 1):
        print(f"#{i:<3} {a}  {v/dec:>16,.0f}  {v/total*100:.3f}%{lbl(a)}")
    # 实战 miss 队列（v4）：top 未命中标签库的大户落盘，跨 token 反复出现者是设施/MM 候选
    if RESV is not None and append_misses is not None and RESV.table:
        miss = [(a, round(v / total * 100, 3), "SOL top 持仓未命中")
                for a, v in top if RESV.get(a) is None]
        tag = os.path.basename(os.getcwd())
        k = append_misses("sol", miss, f"{tag} replay-top")
        if k:
            print(f"（miss 队列新记 {k} 个未命中大户 → references/labels/miss-queue/sol.csv）")


def cmd_sniper(edges, dec, minutes, launch_ts):
    cutoff = launch_ts + minutes * 60
    first_in = {}
    for ts, slot, src, dst, amt in edges:
        if dst != ZERO and dst not in first_in:
            first_in[dst] = (ts, amt, src)
    snipers = {a: v for a, v in first_in.items() if v[0] <= cutoff}
    print(f"发射({fmt_ts(launch_ts)})后 {minutes} 分钟内首次收币地址：{len(snipers)} 个")
    for a, (ts, amt, src) in sorted(snipers.items(), key=lambda kv: kv[1][0]):
        print(f"{fmt_ts(ts)}  {a}{lbl(a)}  首笔 {amt/dec:>15,.0f}  来自 {src}{lbl(src)}")


def cmd_mints(edges, dec):
    total = sum(a for _, _, s, _, a in edges if s == ZERO) or 1
    print("铸造边（src=ZERO）全清单：")
    for ts, slot, src, dst, amt in edges:
        if src == ZERO:
            print(f"  {fmt_ts(ts)} slot={slot}  → {dst}  {amt/dec:,.0f}（{amt/total*100:.2f}% 铸造量）")
    print("销毁边（dst=ZERO）全清单：")
    n = 0
    for ts, slot, src, dst, amt in edges:
        if dst == ZERO:
            n += 1
            if n <= 30:
                print(f"  {fmt_ts(ts)} slot={slot}  {src} →  {amt/dec:,.0f}")
    if n > 30:
        print(f"  ...(销毁边共 {n} 条，仅显示前 30)")


def cmd_evolution(edges, dec, camps_file, stake_pools):
    camps_def = json.loads(Path(camps_file).read_text()) if Path(camps_file).exists() else {}
    addr2camp = {}
    pools = set()
    for camp, addrs in camps_def.items():
        for a in addrs:
            addr2camp[a] = camp
        if camp == "流动性池":
            pools |= set(addrs)
    _, minted, burned0 = replay(edges)
    total = minted - burned0
    launch_ts = launch_ts_of(edges, None)

    # 第一遍：首30分钟狙击者（未列入阵营定义的首买地址）
    cutoff = launch_ts + 30 * 60
    first_in = {}
    for ts, slot, src, dst, amt in edges:
        if dst != ZERO and dst not in first_in:
            first_in[dst] = ts
    snipers = {a for a, ts in first_in.items()
               if ts <= cutoff and a not in pools and a not in stake_pools and a not in addr2camp}
    json.dump(sorted(snipers), open("data/sniper_set.json", "w"))
    print(f"首30分钟狙击者 {len(snipers)} 个（已写 data/sniper_set.json）")

    def camp_of(a):
        if a in addr2camp:
            return addr2camp[a]
        if a in snipers:
            return "首30分钟狙击者"
        return "其他散户"

    # 第二遍：重放（与质押池的边改写为 owner 质押子仓，有效持仓=现货+质押）
    spot, staked = defaultdict(int), defaultdict(int)
    burned = 0
    series = []
    cur_hour = None

    def snapshot(h):
        agg = defaultdict(int)
        for bookmap in (spot, staked):
            for a, v in bookmap.items():
                if v > 0:
                    agg[camp_of(a)] += v
        row = {"ts": h}
        for c, v in agg.items():
            row[c] = round(v / total * 100, 4)
        row["锁仓/销毁"] = round(burned / total * 100, 4)
        series.append(row)

    for ts, slot, src, dst, amt in edges:
        h = ts - ts % 3600
        if cur_hour is not None and h != cur_hour:
            snapshot(cur_hour)
        cur_hour = h
        if dst in stake_pools and src != ZERO:
            spot[src] -= amt
            staked[src] += amt
            continue
        if src in stake_pools and dst != ZERO:
            staked[dst] -= amt
            spot[dst] += amt
            continue
        if src != ZERO:
            spot[src] -= amt
        if dst == ZERO:
            burned += amt
        else:
            spot[dst] += amt
    if cur_hour is not None:
        snapshot(cur_hour)

    json.dump(series, open("data/camp_share_series.json", "w"))
    print(f"阵营序列 {len(series)} 个小时点，已写 data/camp_share_series.json")
    if series:
        print("末态占比：", {k: v for k, v in series[-1].items() if k != "ts"})
    eff = defaultdict(int)
    for bookmap in (spot, staked):
        for a, v in bookmap.items():
            eff[a] += v
    print("\n质押修正后有效持仓 top15：")
    for a, v in sorted(((a, v) for a, v in eff.items() if v > 0), key=lambda kv: -kv[1])[:15]:
        print(f"  {a}  {v/dec:>15,.0f}  {v/total*100:.3f}%  (现货{spot[a]/dec:,.0f}+质押{staked[a]/dec:,.0f})")
    json.dump({a: v for a, v in sorted(eff.items(), key=lambda kv: -kv[1]) if v != 0},
              open("data/effective_balances.json", "w"))
    print("有效持仓末态已写 data/effective_balances.json")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["reconcile", "trace", "top", "sniper", "mints", "evolution"])
    ap.add_argument("arg", nargs="?", help="trace 的地址 / top 的 n / sniper 的分钟数")
    ap.add_argument("arg2", nargs="?", help="trace 的显示条数")
    ap.add_argument("--mint")
    ap.add_argument("--decimals", type=int, default=6)
    ap.add_argument("--launch-ts", type=int, help="发射时刻 epoch（默认取首条铸造边）")
    ap.add_argument("--camps", default="camps.json", help="evolution 的阵营定义 JSON")
    ap.add_argument("--stake-pool", action="append", default=[],
                    help="质押/托管池 owner 地址（可多次；也可 config.json:stake_pools）")
    ap.add_argument("--no-labels", action="store_true", help="关闭批量标签库兜底")
    args = ap.parse_args()
    global RESV
    if LabelResolver is not None and "--no-labels" not in sys.argv:
        RESV = LabelResolver("sol")
        RESV.warn_if_degraded()     # 降级=显式 stderr 警告（"没命中"≠"没加载"，v4）
    elif LabelResolver is None:
        print("[labels][degraded_mode] labels_resolver 导入失败——本次运行无标签兜底", file=sys.stderr)
    mint = resolve_mint(args.mint)
    dec = 10 ** args.decimals
    edges = load_edges(mint)
    stake_pools = set(args.stake_pool)
    cfg = Path("config.json")
    if cfg.exists():
        stake_pools |= set(json.loads(cfg.read_text()).get("stake_pools", []))

    if args.cmd == "reconcile":
        cmd_reconcile(edges, dec)
    elif args.cmd == "trace":
        if not args.arg:
            sys.exit("trace 需要地址参数")
        cmd_trace(edges, args.arg, dec, int(args.arg2) if args.arg2 else 200)
    elif args.cmd == "top":
        cmd_top(edges, dec, int(args.arg) if args.arg else 30)
    elif args.cmd == "sniper":
        cmd_sniper(edges, dec, int(args.arg) if args.arg else 30, launch_ts_of(edges, args.launch_ts))
    elif args.cmd == "mints":
        cmd_mints(edges, dec)
    elif args.cmd == "evolution":
        cmd_evolution(edges, dec, args.camps, stake_pools)


if __name__ == "__main__":
    main()
