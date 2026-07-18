#!/usr/bin/env python3
"""V3 池 tick 级头寸重建（EVM）：拉单池全史 Mint/Burn/Collect 事件，重建当前活跃 LP
头寸（owner × tick 区间 × 净流动性），产出挂单墙价位表——V3 挂单监控的正解。
"池子余额净变化"法禁用：集中流动性被穿越后回落自动复原、净额小推不出未成交
（data-pipeline-robinhood.md 方法论坑，V3 栈通用）。

⚠ 成熟度标注：单次实战抽象（VEX 2026-07-15 挂单墙实证 $0.01736-$0.02372，
scratch_skeptic2_pull_v3ev + scratch_skeptic2_ticks 合并收编 v2.10.0）。第二个标的
使用时务必用 GT/Dexscreener 现价交叉验证价格方向（build_price.py 曾因方向写死翻车，
v2.7.0 教训：token0/token1 由地址排序决定，本脚本已自动判定，但仍需实价对表确认）。

用法（工作目录含 config.json：token/decimals/hypersync）：
  python3 v3_positions.py --pool 0x池地址 --quote 0x报价币地址 --quote-decimals 6
                          [--quote-usd 1.0] [--from-block 0] [--to-block 链头]
                          [--out data/v3_positions.json]
输出：活跃头寸清单（owner/tick区间/价格带USD/流动性）+ 按 owner 聚合的标的侧
名义投放（mint−burn 的 token 腿）与已领费（collect），落盘 JSON + stdout 摘要。

读数两坑（VEX 回归实测）：
① owner 常是 V3 PositionManager（NFT 层持仓，经它开的仓池事件 owner=合约本身）；
  真实持有人需回 mint tx 溯源（tx 发起人 / NFT ownerOf）——直接对池操作的才显示本人。
② token_leg_outstanding 是"名义投放量"（mint−burn），挂单被 swap 吃掉不扣减——
  当前剩余挂单量要看活跃头寸 liquidity 或池内余额，勿把名义量当存量引用。
"""
import argparse, json, math, sys, time
import urllib.request
import ssl, certifi
from collections import defaultdict

SSL_CTX = ssl.create_default_context(cafile=certifi.where())
MINT = "0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde"
BURN = "0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c"
COLLECT = "0x70935338e69775456a85ddef226c395fb668b63fa0115f5f20610b388e6ca9c0"


def load_cfg():
    import os
    with open("config.json") as f:
        cfg = json.load(f)
    token = (cfg.get("token") or "").lower()
    dec = int(cfg.get("decimals", 18))
    hs = cfg.get("hypersync") or {}
    key = hs.get("key") or os.environ.get("HYPERSYNC_KEY") or ""
    if not token.startswith("0x") or not hs.get("url") or not key:
        sys.exit("config.json 需含 token 与 hypersync.url/key（key 可用环境变量 HYPERSYNC_KEY）")
    return token, dec, hs["url"], key


def query(url, key, q):
    req = urllib.request.Request(url, data=json.dumps(q).encode(), headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    for i in range(8):
        try:
            with urllib.request.urlopen(req, timeout=120, context=SSL_CTX) as r:
                return json.loads(r.read())
        except Exception as e:
            print(f"  重试 {i+1}: {e}", flush=True)
            time.sleep(2 * (i + 1))
    raise RuntimeError("HyperSync 连续失败")


def s_int(hex32):
    v = int(hex32, 16)
    return v - 2**256 if v >= 2**255 else v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", required=True)
    ap.add_argument("--quote", required=True, help="报价币地址（判定 token0/token1 方向用）")
    ap.add_argument("--quote-decimals", type=int, required=True)
    ap.add_argument("--quote-usd", type=float, default=1.0, help="报价币 USD 价（稳定币=1）")
    ap.add_argument("--from-block", type=int, default=0)
    ap.add_argument("--to-block", type=int, default=None)
    ap.add_argument("--out", default="data/v3_positions.json")
    args = ap.parse_args()

    token, dec, url, key = load_cfg()
    pool = args.pool.lower()
    quote = args.quote.lower()
    # Uniswap 约定：token0 = 地址字典序小的一方
    token_is_0 = token < quote
    print(f"方向判定：标的是 token{'0' if token_is_0 else '1'}"
          f"（token0={'标的' if token_is_0 else '报价币'}）——务必用现价交叉验证")

    def tick_to_usd(t):
        # raw price = 1.0001^t = token1/token0（最小单位）；换算为"每枚标的的报价币枚数"
        raw = math.pow(1.0001, t)
        per_token_raw = raw if token_is_0 else 1.0 / raw
        return per_token_raw * 10 ** dec / 10 ** args.quote_decimals * args.quote_usd

    # ── 拉单池 LP 三事件 ──
    evs = []
    fb = args.from_block
    while True:
        q = {"from_block": fb,
             "logs": [{"address": [pool], "topics": [[MINT, BURN, COLLECT]]}],
             "field_selection": {"log": ["block_number", "transaction_hash", "log_index",
                                          "topic0", "topic1", "topic2", "topic3", "data"],
                                 "block": ["number", "timestamp"]}}
        if args.to_block:
            q["to_block"] = args.to_block
        res = query(url, key, q)
        for batch in res.get("data", []):
            evs.extend(batch.get("logs", []))
        nb = res.get("next_block")
        ah = res.get("archive_height") or 0
        if nb is None or nb <= fb:
            break
        fb = nb
        if (args.to_block and fb >= args.to_block) or (not args.to_block and fb >= ah):
            break
    print(f"LP 事件 {len(evs)} 条")

    # ── 头寸重建 ──
    pos = defaultdict(int)                     # (owner, tl, tu) -> net liquidity
    token_leg = defaultdict(int)               # owner -> 标的侧 mint−burn（挂单存量）
    collect_leg = defaultdict(lambda: [0, 0])  # owner -> [token0 领取, token1 领取]
    n = {"mint": 0, "burn": 0, "collect": 0}
    tok_idx = 1 if not token_is_0 else 0       # amount0/amount1 里标的那腿
    for e in evs:
        t0 = e["topic0"] if "topic0" in e else e.get("topics", [None])[0]
        topics = e.get("topics") or [e.get("topic0"), e.get("topic1"), e.get("topic2"), e.get("topic3")]
        d = e["data"][2:]
        if t0 == MINT:
            owner = "0x" + topics[1][-40:]
            tl, tu = s_int(topics[2]), s_int(topics[3])
            liq = int(d[64:128], 16)
            a = (int(d[128:192], 16), int(d[192:256], 16))
            pos[(owner, tl, tu)] += liq
            token_leg[owner] += a[tok_idx]
            n["mint"] += 1
        elif t0 == BURN:
            owner = "0x" + topics[1][-40:]
            tl, tu = s_int(topics[2]), s_int(topics[3])
            liq = int(d[0:64], 16)
            a = (int(d[64:128], 16), int(d[128:192], 16))
            pos[(owner, tl, tu)] -= liq
            token_leg[owner] -= a[tok_idx]
            n["burn"] += 1
        elif t0 == COLLECT:
            owner = "0x" + topics[1][-40:]
            a0 = int(d[64:128], 16)
            a1 = int(d[128:192], 16)
            collect_leg[owner][0] += a0
            collect_leg[owner][1] += a1
            n["collect"] += 1
    print(f"mint {n['mint']} / burn {n['burn']} / collect {n['collect']}")

    active = [{"owner": k[0], "tick_lower": k[1], "tick_upper": k[2], "liquidity": str(v),
               "price_usd_lo": round(min(tick_to_usd(k[1]), tick_to_usd(k[2])), 6),
               "price_usd_hi": round(max(tick_to_usd(k[1]), tick_to_usd(k[2])), 6)}
              for k, v in pos.items() if v > 0]
    active.sort(key=lambda x: x["price_usd_lo"])

    out = {"pool": pool, "token_is_token0": token_is_0,
           "active_positions": active,
           "token_leg_outstanding": {o: str(v) for o, v in token_leg.items() if v > 0},
           "collected": {o: {"token0": str(v[0]), "token1": str(v[1])}
                         for o, v in collect_leg.items()}}
    with open(args.out, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    owners = defaultdict(int)
    for p in active:
        owners[p["owner"]] += 1
    print(f"活跃头寸 {len(active)} 个 / owner {len(owners)} 个 → {args.out}")
    for p in active[:40]:
        print(f"  {p['owner'][:12]} tick[{p['tick_lower']},{p['tick_upper']}] "
              f"${p['price_usd_lo']:.6f}-${p['price_usd_hi']:.6f}")
    unit = 10 ** dec
    for o, v in sorted(token_leg.items(), key=lambda x: -x[1])[:8]:
        if v > 0:
            print(f"  挂单存量 {o[:12]}: {v/unit:,.0f} 枚（标的侧 mint−burn）")


if __name__ == "__main__":
    main()
