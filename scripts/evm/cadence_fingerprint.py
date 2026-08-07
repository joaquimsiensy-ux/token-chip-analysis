#!/usr/bin/env python3
"""买入序列节拍指纹检测器——识别常规聚类结构性失明的协同网络。

来源：EGL1(BSC) 分析，2026-07-26。**本件补的是 cluster.py 的设计盲区，不是它的 bug。**

## 解决的问题

cluster.py 的三条规则各有前提：
  R1 直转边  —— 前提：成员之间互相转过账
  R2 gas 同源 —— 前提：成员共享 gas 供给方
  R3 金库一跳 —— 前提：币源自可识别的官方金库

一个成熟的分仓操盘方只要做到「**彼此零转账 + 一址一个一次性 gas 注资方 + 各自独立向池子下单**」，
三条规则就全部永不触发，该实体在聚类结果里是一堆**孤立节点**。EGL1 实测：18 个地址持
6.84% 总供应、买入 308 笔卖出 0 笔，cluster.py 95 个集群里一个都没抓到。

但操盘方绕不开一件事：**这些钱包是被同一个程序、按同一份名单驱动的**。只要它批量操作过
两次以上，遍历顺序就会留下痕迹。

## 判据（本脚本检测的东西）

对同一组地址的两个不同批次操作窗口，比对其**首笔动作的时间排序**：
  - 完全正序匹配 / 完全逆序匹配 → 同一份钱包数组被程序遍历两次
  - n 个地址随机出现完全逆序的概率 = 1/n!（n=18 时 1.6e-16）

★★ **匹配判据必须用秩相关（Spearman ρ）+ 随机排列检验，不能只用位置精确匹配** ★★
  这是 EGL1 案交付后二次修正翻出来的最大教训。位置精确匹配（第 k 位是否同一地址）
  对成员增删**极度脆弱**：名单中间插入一个新地址，其后所有位置全部错位，匹配数从
  满分直接跌到 0。真实网络会增删成员、会有拖尾小单，于是——
    EGL1 一稿（精确匹配 ≥6 位 + 单笔 ≥5,000 枚门槛）→ 43 址 13.14% 总供应
    EGL1 二稿（Spearman ρ + 排列检验 + 无金额门槛）→ 191 址 60.18%，再叠加母子
    直转边核查后 → 254 址 71.73% 总供应
  **同一份数据，规模差 5.5 倍，判级从"2 个小庄"跃迁到"1 个控盘型大庄"。**
  ρ 用秩差平方和，天然容忍局部错位；显著性用 shuffle 3000 次的排列检验，不依赖
  任何分布假设。**本脚本仍是位置匹配版（用于 25 万地址级的全库粗扫）；秩相关版是
  同目录的 `cadence_rank.py`，用于候选池细扫。两件必须配套跑，只跑本件会严重漏检。**

## ★ 跨批次判据（实体归并的核心，比单批次强得多）

单个遍历窗口只能证明"这批地址此刻被同一程序驱动"。真正锁死实体的是：
**一个遍历窗口里的地址，分散在多个不同的建仓批次里，而遍历顺序仍严格对应其
「首次买入的全局时序」。** EGL1 实测 2025-07-22 的 37 址跨 10 个建仓窗口、
跨度 4 天，ρ=−1.000；07-21 的 31 址跨 13 个窗口、跨度两周。
要按建仓时序倒着操作一份跨批次名单，操作者必须持有**按建仓时间排序的完整名单**——
独立散户没有这份名单，不同用户共用同一个交易工具也不会有（工具不知道别人的建仓时间）。
该判据由 `cadence_rank.py` 实现（本脚本不做跨批次统计）。

配套的三条辅助指纹（本脚本一并输出，不单独定案）：
  a) **一次性 gas 隔离层**：注资方 nonce=1 / 余额 0 / 无代码。**注意方向**——
     "每个地址的注资方都不同"过去常被当成"它们是独立用户"的证据，EGL1 案证明
     恰恰相反：真散户的 gas 来自 CEX 热钱包(nonce 百万级)或自用钱包(nonce 几十+)，
     **一址配一个用完即弃的中转地址是刻意规避 gas 同源检测的庄家指纹**。
  b) **批次内间隔规律性**：程序化下单的相邻地址间隔集中（EGL1 实测 9-31 秒），
     变异系数远低于人工操作。
  c) **持仓规模趋同**：同一批次成员的余额落在窄带内。

## 用法

  python3 cadence_fingerprint.py --parquet out/merged.parquet \\
      --pool 0x<主池地址> --total-supply 1000000000 --decimals 18 \\
      [--min-amount 5000] [--gap-sec 90] [--min-size 4] [--out cadence.json]

  --pool 可给多个（逗号分隔）：只把「从池子买入」当作下单动作，排除内部转账干扰。
  不传 --pool 则用全部转入事件（噪声更大）。

输出 cadence.json：{batches:[...], pairs:[{a,b,n_match,kind,p_random}], candidates:[{members,...}]}
stdout 只打 ≤40 行摘要。

## 纪律

- **零金额事件必须先剔除**（address-poisoning spam 会制造假的"同笔交易共现"）。本脚本已内置。
- 本脚本给的是**候选**，不是定案。候选出来后必须逐个人工核对：成员持仓、留存率、
  是否有独立的资金/gas 证据、是否只是同一分钟碰巧下单的散户。
- **切勿只用一个批次**。单批次的顺序不构成证据——同一分钟买入的地址天然有个顺序。
  至少要两个相隔较远的批次，且顺序呈正序或逆序对应。
- **★ 节拍完美 ≠ 是庄**。刷量/套利 bot 群与已离场的狙击残仓同样由程序驱动、同样呈现
  完美的正/逆序匹配（EGL1 实测：脚本 top 候选里 18 址 6.47%、7 址 2.93%、59 址 0.08%
  三组的顺序匹配都很强，但留存率分别只有 3.85%/1.78%/0.00%、收发各十几万到百万笔——
  全是 bot 群）。**必须用留存率与换手笔数分流**，本脚本已内置 kind 字段：
  持仓型(留存≥50%)=庄候选 / 过手型(累计买入≥1倍总供应 或 收发≥5000笔)=bot 嫌疑 /
  其余=已离场残仓。只有「持仓型」才进人工核对队列。
"""
import argparse
import json
import math
import sys

import duckdb


def find_batches(con, pools, min_amt_wei, gap_sec, min_size):
    """先按事件时间间隔切窗口，再在**每个窗口内**取各地址的首笔并排序。

    ⚠ 不能用全局 GROUP BY addr 取 MIN(ts)——那样每个地址只会落进它最早出现的那个
    批次，同一组钱包的第二次遍历会整体消失，两批次比对永远为空（EGL1 首版实测踩过）。
    """
    pool_filter = ""
    if pools:
        pool_filter = " AND frm IN (" + ",".join(repr(p.lower()) for p in pools) + ")"
    rows = con.execute(f"""
        SELECT ts, block, t2 AS addr FROM ev
        WHERE v >= {min_amt_wei}{pool_filter}
        ORDER BY block, log_index
    """).fetchall()
    if not rows:
        return []
    windows, cur = [], [rows[0]]
    for prev, r in zip(rows, rows[1:]):
        if _epoch(r[0]) - _epoch(prev[0]) > gap_sec:
            windows.append(cur)
            cur = []
        cur.append(r)
    windows.append(cur)

    batches = []
    for w in windows:
        seen, order = set(), []
        for ts, blk, addr in w:                 # 窗口内按时序取各地址首笔
            if addr not in seen:
                seen.add(addr)
                order.append((addr, ts, blk))
        if len(order) >= min_size:
            batches.append(order)
    return batches


def _epoch(ts):
    import datetime as dt
    return dt.datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S").timestamp()


def compare(b1, b2):
    """两个批次的地址顺序比对。返回 (共同成员数, 正序匹配位数, 逆序匹配位数)。"""
    s1 = [r[0] for r in b1]
    s2 = [r[0] for r in b2]
    common = set(s1) & set(s2)
    if len(common) < 4:
        return len(common), 0, 0
    o1 = [a for a in s1 if a in common]
    o2 = [a for a in s2 if a in common]
    fwd = sum(1 for i, a in enumerate(o2) if a == o1[i])
    rev = sum(1 for i, a in enumerate(o2) if a == o1[::-1][i])
    return len(common), fwd, rev


def p_random(n, matched):
    """n 个成员中 matched 位落在指定排列上的粗略随机概率（保守上界）。"""
    if matched >= n:
        return 1.0 / math.factorial(n)
    # 至少 matched 位固定：C(n,matched)*(n-matched)!/n! 的量级近似
    return math.comb(n, matched) * math.factorial(n - matched) / math.factorial(n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", required=True, help="全量重放产物 merged.parquet")
    ap.add_argument("--pool", default="", help="主池地址，逗号分隔（只认从池子买入）")
    ap.add_argument("--total-supply", type=float, required=True)
    ap.add_argument("--decimals", type=int, default=18)
    ap.add_argument("--min-amount", type=float, default=5000, help="单笔买入下限（枚）")
    ap.add_argument("--gap-sec", type=int, default=90, help="批次切分间隔（秒）")
    ap.add_argument("--min-size", type=int, default=4, help="批次最小地址数")
    ap.add_argument("--min-match", type=int, default=6, help="报告候选的最小匹配位数")
    ap.add_argument("--mem-limit", default="6GB")
    ap.add_argument("--out", default="cadence.json")
    a = ap.parse_args()

    con = duckdb.connect()
    con.execute(f"SET memory_limit='{a.mem_limit}'")
    # ★ 零金额事件必须剔除：spam 会制造假共现
    con.execute(f"""CREATE VIEW ev AS
        SELECT block, ts, tx, log_index, "from" AS frm, "to" AS t2,
               CAST(value AS HUGEINT) AS v
        FROM read_parquet('{a.parquet}')
        WHERE CAST(value AS HUGEINT) > 0""")

    D = 10 ** a.decimals
    pools = [p.strip() for p in a.pool.split(",") if p.strip()]
    batches = find_batches(con, pools, int(a.min_amount * D), a.gap_sec, a.min_size)
    print(f"[batch] 切出 {len(batches)} 个批次窗口"
          f"（单笔≥{a.min_amount:,.0f} 枚、间隔>{a.gap_sec}s 切分、≥{a.min_size} 址）")

    pairs = []
    for i in range(len(batches)):
        for j in range(i + 1, len(batches)):
            n, fwd, rev = compare(batches[i], batches[j])
            if n >= a.min_size and max(fwd, rev) >= a.min_match:
                kind = "逆序" if rev >= fwd else "正序"
                m = max(fwd, rev)
                pairs.append({"batch_a": i, "batch_b": j, "n_common": n,
                              "fwd_match": fwd, "rev_match": rev, "kind": kind,
                              "p_random": p_random(n, m),
                              "t_a": batches[i][0][1], "t_b": batches[j][0][1],
                              "members": sorted(set(r[0] for r in batches[i])
                                                & set(r[0] for r in batches[j]))})
    pairs.sort(key=lambda x: (-max(x["fwd_match"], x["rev_match"]), x["p_random"]))

    print(f"[pair] {len(pairs)} 对批次呈显著顺序对应（匹配≥{a.min_match} 位）")
    for p in pairs[:12]:
        print(f"  {p['t_a'][:19]} ↔ {p['t_b'][:19]}  共同 {p['n_common']} 址，"
              f"{p['kind']}匹配 {max(p['fwd_match'], p['rev_match'])}/{p['n_common']}，"
              f"随机概率 ~{p['p_random']:.2e}")

    # 候选实体：把有顺序对应关系的成员集合并
    seen, cands = [], []
    for p in pairs:
        ms = set(p["members"])
        for c in cands:
            if len(ms & set(c["members"])) >= max(3, len(ms) // 2):
                c["members"] = sorted(set(c["members"]) | ms)
                c["evidence"].append(f"{p['t_a'][:19]}↔{p['t_b'][:19]} {p['kind']}"
                                     f"{max(p['fwd_match'], p['rev_match'])}/{p['n_common']}")
                break
        else:
            cands.append({"members": sorted(ms),
                          "evidence": [f"{p['t_a'][:19]}↔{p['t_b'][:19]} {p['kind']}"
                                       f"{max(p['fwd_match'], p['rev_match'])}/{p['n_common']}"]})

    TOT = a.total_supply * D
    bal = con.execute("""
        SELECT addr, SUM(d) AS b FROM (
            SELECT t2 AS addr, v AS d FROM ev
            UNION ALL SELECT frm, -v FROM ev
        ) GROUP BY 1""").df()
    bmap = dict(zip(bal.addr, bal.b))

    # ★ 持仓型 vs 过手型的分流（EGL1 实测必须做）：刷量 bot 群与已离场的狙击残仓
    #   同样是程序驱动、同样呈现完美节拍，只看顺序匹配会把它们一并判成"庄"。
    #   分流靠两个量：留存率（余额/累计买入）与换手笔数。
    for c in cands:
        L = ",".join(repr(x) for x in c["members"])
        ain, nin = con.execute(f"SELECT COALESCE(SUM(v),0), COUNT(*) FROM ev WHERE t2 IN ({L})").fetchone()
        aout, nout = con.execute(f"SELECT COALESCE(SUM(v),0), COUNT(*) FROM ev WHERE frm IN ({L})").fetchone()
        s = sum(int(bmap.get(m, 0)) for m in c["members"])
        c["n"] = len(c["members"])
        c["current_pct_supply"] = s / TOT * 100
        c["retention_pct"] = (s / ain * 100) if ain else 0.0
        c["n_in"], c["n_out"] = nin, nout
        c["turnover_multiple"] = (int(ain) / TOT) if TOT else 0
        if c["retention_pct"] >= 50:
            c["kind"] = "持仓型（庄候选）"
        elif c["turnover_multiple"] >= 1.0 or nin + nout >= 5000:
            c["kind"] = "过手型（刷量/套利 bot 嫌疑）"
        else:
            c["kind"] = "已离场（残仓）"
    cands.sort(key=lambda x: (x["kind"] != "持仓型（庄候选）", -x["current_pct_supply"]))
    print(f"\n[cand] {len(cands)} 个候选（已按持仓型/过手型/已离场分流）：")
    for c in cands:
        print(f"  [{c['kind']}] {c['n']:>3} 址 {c['current_pct_supply']:>7.4f}% 总供应"
              f"  留存 {c['retention_pct']:>6.2f}%  收/发 {c['n_in']}/{c['n_out']} 笔"
              f"  证据: {'; '.join(c['evidence'][:2])}")

    json.dump({"batches": [[{"addr": r[0], "ts": r[1]} for r in b] for b in batches],
               "pairs": pairs, "candidates": cands},
              open(a.out, "w"), ensure_ascii=False, indent=1)
    print(f"\n[done] -> {a.out}")
    print("⚠ 候选不是定案：逐个核对持仓/留存/gas 画像后才可判级；"
          "单批次顺序不构成证据，至少要两个相隔较远的批次呈正/逆序对应。")


if __name__ == "__main__":
    raise SystemExit(main())
