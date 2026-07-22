#!/usr/bin/env python3
"""HyperSync Solana ↔ SQD 完备性对账器（GA 后重验收专用，data-pipeline-solana-capture §13d）。

用途：HyperSync Solana(early access) 2026-07-22 验收不通过（历史区持久缺行越老越糟+近端
乱序回填暂态洞），双引擎已禁用；官方 GA 后用本脚本重验收，通过才可解禁 --hypersync。
用法：改 MINT/FRM/TO 三个常量，按三区分级各跑一轮（前沿 head-18万 slot 内 / 近端
head-13~33万 / 历史区 head-450万 与 head-1450万），四轮全零差才算通过；差集行须再用
Helius getTransaction 链上终审定责（哪边缺）。原型即 3.18.0 验收所用 recon2.py，逻辑未动。

对账键去掉 tx_index（两家编号体系不同——HS 含投票交易原始索引 vs SQD 过滤后索引）。
键 = (slot, account, pre, post) 多重集；另做"per-slot 分组指纹"对账保证 tx 级分组等价性。
"""
import json, os, time
from collections import Counter, defaultdict
import requests

MINT = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
FRM, TO = 434_297_000, 434_300_000

HS_TOK = open(os.path.expanduser("~/.config/hypersync/token")).read().strip()
HS_URL = "https://solana.hypersync.xyz/query"
HS_H = {"Authorization": f"Bearer {HS_TOK}", "Content-Type": "application/json"}
SQD_URL = "https://portal.sqd.dev/datasets/solana-mainnet/stream"


def hs_flat(v):
    out = []
    for x in v or []:
        out.extend(x if isinstance(x, list) else [x])
    return out


def pull_hs():
    rows, txs = [], {}
    cur = FRM
    while cur < TO:
        q = {"from_slot": cur, "to_slot": TO,
             "token_balances": [{"mint": [MINT]}],
             "field_selection": {
                 "token_balance": ["slot", "owner", "account", "pre_amount",
                                   "post_amount", "transaction_index"],
                 "transaction": ["slot", "transaction_index", "success"]}}
        r = requests.post(HS_URL, headers=HS_H, json=q, timeout=120)
        r.raise_for_status()
        j = r.json()
        rows.extend(hs_flat(j.get("token_balances")))
        for t in hs_flat(j.get("transactions")):
            txs[(t["slot"], t["transaction_index"])] = t.get("success")
        cur = j["next_slot"]
    return rows, txs


def pull_sqd():
    rows, txerr = [], {}
    body_fields = {"block": {"number": True, "timestamp": True},
                   "transaction": {"transactionIndex": True, "err": True},
                   "tokenBalance": {"transactionIndex": True, "account": True,
                                    "preOwner": True, "postOwner": True,
                                    "preAmount": True, "postAmount": True}}
    filt = [{"postMint": [MINT], "transaction": True},
            {"preMint": [MINT], "transaction": True}]
    cur, sess = FRM, requests.Session()
    while cur < TO:
        body = {"type": "solana", "fromBlock": cur, "toBlock": TO - 1,
                "fields": body_fields, "tokenBalances": filt}
        last = None
        with sess.post(SQD_URL, json=body, stream=True, timeout=(15, 90)) as r:
            r.raise_for_status()
            for ln in r.iter_lines(decode_unicode=True):
                if not ln:
                    continue
                try:
                    b = json.loads(ln)
                except ValueError:
                    break
                hdr = b.get("header", {})
                slot = hdr.get("number")
                last = slot if slot is not None else last
                for tx in b.get("transactions") or []:
                    txerr[(slot, tx.get("transactionIndex"))] = tx.get("err")
                for rec in b.get("tokenBalances") or []:
                    rec["slot"] = slot
                    rows.append(rec)
        cur = last + 1
    return rows, txerr


hs_rows, hs_txs = pull_hs()
sqd_rows, sqd_txerr = pull_sqd()
print(f"HS {len(hs_rows)} 行 / SQD {len(sqd_rows)} 行")

hs_ok = [r for r in hs_rows if hs_txs.get((r["slot"], r["transaction_index"])) is not False]
sqd_ok = [r for r in sqd_rows if sqd_txerr.get((r["slot"], r["transactionIndex"])) is None]
print(f"成功 tx 过滤后：HS {len(hs_ok)} / SQD {len(sqd_ok)}")

K = lambda s, a, p, q: (s, a, int(p or 0), int(q or 0))
hs_c = Counter(K(r["slot"], r["account"], r.get("pre_amount"), r.get("post_amount")) for r in hs_ok)
sqd_c = Counter(K(r["slot"], r.get("account"), r.get("preAmount"), r.get("postAmount")) for r in sqd_ok)
oh, os_ = hs_c - sqd_c, sqd_c - hs_c
print(f"\n== 键(slot,account,pre,post)对账（成功 tx）==")
print(f"HS 独有 {sum(oh.values())} / SQD 独有 {sum(os_.values())} / 交集 {sum((hs_c & sqd_c).values())}")
for name, d in (("HS 独有", oh), ("SQD 独有", os_)):
    for k, n in list(d.items())[:8]:
        print(f"  {name} ×{n}: slot={k[0]} account={k[1]} pre={k[2]} post={k[3]}")

# 含失败 tx 的全量行对账（验证"收录范围"本身一致）
hs_c2 = Counter(K(r["slot"], r["account"], r.get("pre_amount"), r.get("post_amount")) for r in hs_rows)
sqd_c2 = Counter(K(r["slot"], r.get("account"), r.get("preAmount"), r.get("postAmount")) for r in sqd_rows)
print(f"\n== 全量行对账（含失败 tx）==")
print(f"HS 独有 {sum((hs_c2 - sqd_c2).values())} / SQD 独有 {sum((sqd_c2 - hs_c2).values())}")

# 关户/清仓专项
hz = Counter(k for k in hs_c.elements() if k[3] == 0)
sz = Counter(k for k in sqd_c.elements() if k[3] == 0)
print(f"\n== 关户/清仓行（成功 tx 中 post=0）==")
print(f"HS {sum(hz.values())} / SQD {sum(sz.values())} / HS独有 {sum((hz-sz).values())} / SQD独有 {sum((sz-hz).values())}")

# SQD 关户指纹行（postOwner 缺失）在 HS 的覆盖 + owner 语义
hs_map = defaultdict(list)
for r in hs_ok:
    hs_map[K(r["slot"], r["account"], r.get("pre_amount"), r.get("post_amount"))].append(r)
gone = [r for r in sqd_ok if not r.get("postOwner") and r.get("preOwner")]
cov = sum(1 for r in gone
          if hs_map.get(K(r["slot"], r.get("account"), r.get("preAmount"), r.get("postAmount"))))
print(f"\nSQD 关户指纹行（postOwner 缺失）{len(gone)} 条 → HS 同键覆盖 {cov} 条")
own_post = own_pre_only = other = 0
gone_owner_pre = 0
for r in sqd_ok:
    m = hs_map.get(K(r["slot"], r.get("account"), r.get("preAmount"), r.get("postAmount")))
    if not m:
        continue
    ho = m[0].get("owner")
    po, pr = r.get("postOwner"), r.get("preOwner")
    if ho and ho == po:
        own_post += 1
    elif ho and ho == pr:
        own_pre_only += 1
        if not po:
            gone_owner_pre += 1
    else:
        other += 1
print(f"owner 语义（同键行）：==postOwner {own_post} / ==preOwner(仅) {own_pre_only}"
      f"（其中关户行 {gone_owner_pre}）/ 其他 {other}")

# tx 级分组指纹：per (slot, tx) 的行键集合排序哈希——验证两边"哪些行属于同一笔 tx"等价
def grp_fp(rows, slot_f, ti_f, acc_f, pre_f, post_f, okset):
    g = defaultdict(list)
    for r in rows:
        if not okset(r):
            continue
        g[(r[slot_f], r[ti_f])].append((r.get(acc_f), int(r.get(pre_f) or 0), int(r.get(post_f) or 0)))
    return Counter(tuple(sorted(v)) for v in g.values())


fp_hs = grp_fp(hs_rows, "slot", "transaction_index", "account", "pre_amount", "post_amount",
               lambda r: hs_txs.get((r["slot"], r["transaction_index"])) is not False)
fp_sqd = grp_fp(sqd_rows, "slot", "transactionIndex", "account", "preAmount", "postAmount",
                lambda r: sqd_txerr.get((r["slot"], r["transactionIndex"])) is None)
d1, d2 = fp_hs - fp_sqd, fp_sqd - fp_hs
print(f"\n== tx 级分组指纹对账（成功 tx；验证 pair_tx 分组等价）==")
print(f"HS 组 {sum(fp_hs.values())} / SQD 组 {sum(fp_sqd.values())} / "
      f"HS 独有组 {sum(d1.values())} / SQD 独有组 {sum(d2.values())}")
for name, d in (("HS 独有组", d1), ("SQD 独有组", d2)):
    for k, n in list(d.items())[:3]:
        print(f"  {name} ×{n}: {str(k)[:200]}")
