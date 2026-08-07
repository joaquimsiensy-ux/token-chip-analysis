#!/usr/bin/env python3
"""V3 池 LP 头寸取证：把「谁在什么价位挂了多少、单边还是双边」逐笔还原。

## 为什么必须做这一步（不是可选项）

**转账金额判断不了动作性质。** 项目方钱包"少了 38.9 万枚"，看转账像出货，读交易回执
才知道是 `Mint`（挂流动性）；"多了 30 万枚"则是 `Burn`（撤流动性）。KOGE(BSC) 初版
分析仅凭转账金额把这些动作写成"注入/撤出流动性"，方向对但性质没定死；补回执后才拿到
参数级证据。**凡庄级实体的大额进出对手方是 DEX 池，一律查回执区分 Mint/Burn/Swap。**

## 两个判别参数（决定"做市"还是"挂单"）

    tick 宽度 = tickUpper - tickLower
      == 1（0.01% 费率池的最小档）→ 经济上等价于一张限价单，与做市无关
      宽区间                        → 才是常规做市

    双边构成：Mint 时 amount0/amount1 是否有一侧为 0
      单边 → 只挂卖单（或买单）墙，不提供双向深度；价格要穿过必须先吃光这堵墙
      双边 → 真实做市

KOGE(BSC) 实测：81 次操作 67 次是 1-tick；项目方 15 次挂入 14 次单边 0 USDT，
合计 197 万枚（占供给 58%）——价格被钉在墙位上下 0.1% 达九个月。

## Mint 与 Burn 的发起人不一致 → 追 NFT（关联证据的新通道）

V3 头寸是 ERC721，**只有持有人能 burn**。所以"挂的人 ≠ 撤的人"必然意味着 NFT 转移过。
本脚本自动标出这类头寸。拿到 tokenId 后追它的 ERC721 Transfer：

    HyperSync 查 NPM 合约、topic0=Transfer、topic3=tokenId（块区间就在两笔操作之间，一次返回）

**无对价（tx value=0、无配套支付）的 LP 头寸划转 = 关联硬证据**——KOGE 案一个刷量地址
铸得的头寸 6 分 44 秒后无偿转给项目方签名人，这是该案刷量层与项目方之间的首条资产层直接证据。

## 用法

    python3 lp_positions.py --chain bsc --logs <标的Transfer的parquet> --pool 0x.. \\
        --threshold 20000 --decimals 18 --out data/lp_positions.json [--rpc URL]

`--threshold` 只用来**选取要查回执的交易**（挂墙级操作都是大额），不参与任何净额计算。
⚠ 阈值样本禁止用于净额/盈亏判定——见 analysis-playbook「判定纪律」。

## 产物

    lp_positions.json   每次 Mint/Burn：ts/tx/kind/tick 区间/两侧数量/发起人
    stdout              时间线 + 按操作方汇总 + 单边率 + tick 宽度分布 + NFT 待追清单

（来源：KOGE(BSC) 第二轮追加取证，2026-07-25）
"""
import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from net import RpcAttestationError, attested_rpc_pool

MINT = '0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde'
BURN = '0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c'
DEFAULT_RPCS = ['https://bsc-dataseed.binance.org/', 'https://bsc-dataseed1.defibit.io/',
                'https://bsc-dataseed1.ninicoin.io/', 'https://bsc-dataseed2.binance.org/']
VAL = ("CASE WHEN data IS NULL OR data IN ('','0x') THEN 0::HUGEINT ELSE "
       "('0x'||substr(data,35,16))::UBIGINT::HUGEINT * '18446744073709551616'::HUGEINT "
       "+ ('0x'||substr(data,51,16))::UBIGINT::HUGEINT END")


def s24(h):
    v = int(h, 16)
    return v - (1 << 256) if v >= (1 << 255) else v


def word(h, i):
    return int(h[2 + 64 * i:2 + 64 * (i + 1)], 16)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", required=True, help="标的 Transfer 事件 parquet（glob 亦可）")
    ap.add_argument("--blockts", help="blockts.parquet（replay_stream 产出）；不给则只输出块号")
    ap.add_argument("--pool", required=True, help="目标 V3 池地址")
    ap.add_argument("--threshold", type=float, default=20000, help="选取交易的金额门槛（枚）")
    ap.add_argument("--decimals", type=int, default=18)
    ap.add_argument("--out", default="data/lp_positions.json")
    ap.add_argument("--rpc", action="append", help="可重复；默认 BSC 公共节点组")
    ap.add_argument("--chain", default="bsc",
                    choices=["eth", "bsc", "base", "arbitrum"],
                    help="目标链（默认 bsc；chain id 只读 chain_registry）")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--labels", help="JSON: {地址: 标签}，用于 stdout 可读化")
    a = ap.parse_args()

    pool = a.pool.lower()
    rpcs = a.rpc or DEFAULT_RPCS
    rpc_pool = attested_rpc_pool(
        rpcs, a.chain, formal=True, rps=max(1, a.workers), concurrency=a.workers)
    try:
        rpc_pool.attest()
    except RpcAttestationError as exc:
        print(f"[fatal] RPC chain attestation failed: {exc}", file=sys.stderr)
        return 1
    E = 10 ** a.decimals
    lbl = json.load(open(a.labels)) if a.labels else {}

    con = duckdb.connect()
    con.execute("SET memory_limit='4GB'"); con.execute("SET threads=4")
    con.execute("SET preserve_insertion_order=false")
    ts_sel, ts_join = "NULL ts", ""
    if a.blockts:
        con.execute(f"""CREATE TABLE bts AS SELECT block_number,
            strftime(make_timestamp((ts_i*1000000)::BIGINT),'%Y-%m-%d %H:%M:%S') ts
            FROM read_parquet('{a.blockts}')""")
        ts_sel, ts_join = "bts.ts", "JOIN bts ON bts.block_number = e.b"
    rows = con.execute(f"""
        SELECT DISTINCT e.tx, {ts_sel} FROM (
            SELECT block_number b, transaction_hash tx,
                   '0x'||right(lower(COALESCE(topic1,repeat('0',64))),40) frm,
                   '0x'||right(lower(COALESCE(topic2,repeat('0',64))),40) t2, {VAL} v
            FROM read_parquet('{a.logs}', union_by_name=true)
            WHERE block_number IS NOT NULL AND log_index IS NOT NULL
              AND (data IS NULL OR data IN ('','0x') OR LENGTH(data)=66)
        ) e {ts_join}
        WHERE (e.frm='{pool}' OR e.t2='{pool}') AND e.v >= {int(a.threshold * E)}""").fetchall()
    print(f"待查回执 {len(rows)} 笔（门槛 {a.threshold:g} 枚）", flush=True)

    def parse_receipt(row, response):
        tx, ts = row
        rc = response.get('result') if response.get('ok') else None
        if not rc:
            return []
        out = []
        for lg in rc['logs']:
            if lg['address'].lower() == pool and lg['topics'][0] in (MINT, BURN):
                is_m = lg['topics'][0] == MINT
                d = lg['data']
                a0, a1 = (word(d, 2), word(d, 3)) if is_m else (word(d, 1), word(d, 2))
                out.append({'ts': ts, 'block': int(rc['blockNumber'], 16), 'tx': tx,
                            'kind': 'Mint' if is_m else 'Burn',
                            'tickLower': s24(lg['topics'][2]), 'tickUpper': s24(lg['topics'][3]),
                            'amount0': str(a0), 'amount1': str(a1),
                            'from': rc['from'].lower()})
        return out

    res, t0 = [], time.time()
    responses = rpc_pool.call_many(
        [('eth_getTransactionReceipt', [tx]) for tx, _ in rows])
    for i, (row, response) in enumerate(zip(rows, responses)):
        res.extend(parse_receipt(row, response))
        if i and i % 200 == 0:
            print(f"  {i}/{len(rows)}  解析 {len(res)} 个 LP 事件  {time.time()-t0:.0f}s", flush=True)
    res.sort(key=lambda x: (x['block'], x['tx']))
    json.dump(res, open(a.out, 'w'), indent=1)
    if not res:
        sys.exit("[警告] 0 个 LP 事件——先确认池版本的 Mint/Burn topic0 是否与本脚本一致")

    print(f"\n{'时间/块':<21}{'操作':<6}{'tick 区间':<20}{'宽':>4}{'amount0':>16}{'amount1':>16}  操作方")
    print('-' * 118)
    for r in res:
        w = r['tickUpper'] - r['tickLower']
        who = lbl.get(r['from'], r['from'][:12] + '…')
        rng = "[%d,%d]" % (r['tickLower'], r['tickUpper'])
        when = str(r['ts'] or r['block'])
        kind = '加LP' if r['kind'] == 'Mint' else '撤LP'
        print(f"{when:<21}{kind:<6}{rng:<20}{w:>4}"
              f"{int(r['amount0'])/E:>16,.2f}{int(r['amount1'])/E:>16,.2f}  {who}")

    agg = defaultdict(lambda: [0, 0, 0, 0, 0, 0])
    for r in res:
        g = agg[r['from']]
        i = 0 if r['kind'] == 'Mint' else 2
        g[i] += int(r['amount0']); g[i + 1] += int(r['amount1'])
        g[4 if r['kind'] == 'Mint' else 5] += 1
    print(f"\n{'操作方':<26}{'加LP amt0':>15}{'加LP amt1':>15}{'撤LP amt0':>15}{'撤LP amt1':>15}{'次数':>8}")
    for k, v in sorted(agg.items(), key=lambda x: -(x[1][1] + x[1][3])):
        print(f"{lbl.get(k, k[:24]):<26}{v[0]/E:>15,.0f}{v[1]/E:>15,.0f}"
              f"{v[2]/E:>15,.0f}{v[3]/E:>15,.0f}{v[4]+v[5]:>8}")

    mints = [r for r in res if r['kind'] == 'Mint']
    one = [r for r in mints if int(r['amount0']) == 0 or int(r['amount1']) == 0]
    wid = Counter(r['tickUpper'] - r['tickLower'] for r in res)
    print(f"\n单边率: {len(one)}/{len(mints)} = {100*len(one)/max(len(mints),1):.1f}% 的挂入是单边（一侧为 0）")
    print(f"tick 宽度分布: {dict(sorted(wid.items()))}   ← 宽度 1 = 最小档 = 等价限价单")

    # Mint 与 Burn 发起人不一致的头寸 → 需追 NFT 归属
    pos = defaultdict(lambda: {'mint': set(), 'burn': set()})
    for r in res:
        pos[(r['tickLower'], r['tickUpper'])]['mint' if r['kind'] == 'Mint' else 'burn'].add(r['from'])
    need = [(k, v) for k, v in pos.items() if v['burn'] - v['mint']]
    strong = [(k, v) for k, v in need if v['mint']]
    weak = [(k, v) for k, v in need if not v['mint']]
    if strong:
        print(f"\n⚠ 强信号 {len(strong)} 个：该区间有挂入方，但撤出方不在其中 → NFT 转移过，按 docstring 追 tokenId")
        for (tl, tu), v in strong[:20]:
            print(f"    tick[{tl},{tu}]  挂入方 {[lbl.get(x, x[:10]) for x in v['mint']]}"
                  f"  → 另有撤出方 {[lbl.get(x, x[:10]) for x in v['burn'] - v['mint']]}")
    if weak:
        print(f"\n（弱信号 {len(weak)} 个：区间内只见撤出不见挂入，多半是挂入额低于 --threshold 被漏选，"
              f"不是 NFT 转移；要排除就把门槛调低重跑）")
    print(f"\n[out] {len(res)} 条 → {a.out}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
