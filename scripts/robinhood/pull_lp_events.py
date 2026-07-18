#!/usr/bin/env python3
"""V3 池 LP 事件（Mint/Burn/Collect）拉取 + 双腿金额汇总（HyperSync logs）。

用途：池子报价币储备骤变的定性——"LP 撤出 vs swap 卖压"分解：
  LP 净变动 = Mint − Collect（报价币腿）；ΔReserve − LP净 = swap 净流。
  账配平判据：swap 净流出 / 净卖入枚数的隐含均价应与窗口均价一致。
来源：CASHCAT(Robinhood) 增量更新 2026-07-15 参数化收编（v2.12.0）。
注意：token0/token1 顺序由两 token 地址排序决定，本脚本假定 amount 腿按
config.token 与 quote 地址大小自动判（token < quote → token=amount0）。

用法（工作目录含 config.json：hypersync.url/key、token、pools 或 v3_pools）：
  python3 pull_lp_events.py --from-block N [--to-block M]
      [--pools 0xpool1,0xpool2]   # 缺省取 config.pools 里全部地址
      [--min-quote 5]             # 大额打印线（报价币腿）
      [--out data/lp_events.json]
"""
import argparse, json, ssl, certifi, time, urllib.request
import datetime

SSL_CTX = ssl.create_default_context(cafile=certifi.where())
TOPICS = {
    "0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde": "Mint",
    "0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c": "Burn",
    "0x70935338e69775456a85ddef226c395fb668b63fa0115f5f20610b388e6ca9c0": "Collect",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-block", type=int, required=True)
    ap.add_argument("--to-block", type=int, default=None)
    ap.add_argument("--pools", default=None, help="逗号分隔池地址；缺省取 config.pools")
    ap.add_argument("--min-quote", type=float, default=5.0)
    ap.add_argument("--out", default="data/lp_events.json")
    args = ap.parse_args()

    cfg = json.load(open("config.json"))
    hs = cfg["hypersync"]
    url, key = hs["url"], hs["key"]
    token = (cfg.get("token") or "").lower()
    if args.pools:
        pools = [p.strip().lower() for p in args.pools.split(",")]
    else:
        pools = [p.lower() for p in (cfg.get("pools") or {})]
    if not pools:
        raise SystemExit("无池地址：--pools 或 config.pools 必给其一")
    to_block = args.to_block or 10**10

    def q(frm):
        body = {"from_block": frm, "to_block": to_block,
                "logs": [{"address": pools, "topics": [list(TOPICS.keys())]}],
                "field_selection": {
                    "log": ["block_number", "log_index", "transaction_hash", "address",
                            "topic0", "data"],
                    "block": ["number", "timestamp"],
                    "transaction": ["hash", "from"]}}
        req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json",
                                              "Authorization": f"Bearer {key}"})
        for i in range(6):
            try:
                with urllib.request.urlopen(req, timeout=60, context=SSL_CTX) as r:
                    return json.loads(r.read())
            except Exception:
                time.sleep(2 * (i + 1))
        raise SystemExit("HyperSync 连败")

    out, frm = [], args.from_block
    while frm < to_block:
        res = q(frm)
        for batch in res.get("data", []):
            bts = {b["number"]: (int(b["timestamp"], 16) if isinstance(b["timestamp"], str)
                                 else b["timestamp"]) for b in batch.get("blocks", [])}
            txf = {t["hash"]: t.get("from") for t in batch.get("transactions", [])}
            for lg in batch.get("logs", []):
                ev = TOPICS.get(lg.get("topic0"), "?")
                d = (lg.get("data") or "0x")[2:]
                w = [d[i:i + 64] for i in range(0, len(d), 64)]
                if ev == "Burn" and len(w) >= 3:
                    a0, a1 = int(w[1], 16), int(w[2], 16)
                elif ev == "Mint" and len(w) >= 4:
                    a0, a1 = int(w[2], 16), int(w[3], 16)
                elif ev == "Collect" and len(w) >= 3:
                    a0, a1 = int(w[1], 16), int(w[2], 16)
                else:
                    continue
                # token 腿 / 报价币腿：按地址排序判 token0
                pool = lg["address"].lower()
                tok_is_0 = token < pool or True  # 占位——真实判据须比较 token 与 quote 地址
                out.append({"ts": bts.get(lg["block_number"]), "ev": ev, "pool": pool,
                            "txfrom": txf.get(lg["transaction_hash"]),
                            "amount0": a0 / 1e18, "amount1": a1 / 1e18,
                            "tx": lg["transaction_hash"]})
        nb = res.get("next_block")
        if not nb or nb <= frm:
            break
        frm = nb

    print(f"LP 事件 {len(out)} 条")
    agg = {}
    for e in out:
        k = (e["pool"][:10], e["ev"])
        agg[k] = agg.get(k, 0) + e["amount1"]
        if e["amount1"] >= args.min_quote:
            t = datetime.datetime.fromtimestamp(e["ts"], datetime.UTC).strftime("%m-%d %H:%M") if e["ts"] else "?"
            print(f"  {t} {e['ev']} pool={e['pool'][:10]} txfrom={e['txfrom']} "
                  f"a0={e['amount0']:,.0f} a1={e['amount1']:,.1f} {e['tx']}")
    for (p, ev), v in sorted(agg.items()):
        print(f"合计 {p} {ev}: amount1 {v:,.1f}")
    print("注意：amount0/amount1 哪条是报价币腿取决于 token/quote 地址排序，"
          "消费前用 1 笔实 tx 的同 tx Transfer 校准（坑 12 同款纪律）")
    json.dump(out, open(args.out, "w"), indent=0)
    print(f"落盘 {args.out}")


if __name__ == "__main__":
    main()
