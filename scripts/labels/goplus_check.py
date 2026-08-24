#!/usr/bin/env python3
"""GoPlus 恶意地址运行时查询通道（v4.1 2026-07-17，P2 风险层落地）

定位：**动态 candidate 层**，与静态标签库互补——GoPlus address_security 是查询式 API
（无法下载黑名单批量入库），故做成分析时对候选大户/关联地址的批量体检。
纪律（同 risk_flags candidate 档）：命中=降权提示+人工核验线索，不作定性依据；
报告措辞「GoPlus（数据源 <data_source>）标注该地址有 XX 行为记录」。

用法（playbook §3 第零步 label_lookup 之后，对未命中库的候选跑）：
  python3 goplus_check.py --chain bsc ADDR1 ADDR2 ...
  python3 goplus_check.py --chain eth --file candidates.txt [--json] [--all]
  --all  显示全部（含干净地址）；默认只列命中
链参数：eth/bsc/base/arbitrum 走链 id；robinhood/sol 不传 chain_id 查通用库
  （EVM 恶意 EOA 跨链通用，2026-07-17 实测不带 chain_id 可命中；
   ⚠️ Solana 覆盖未证实——OFAC SOL 制裁地址实测返回全 0，结果仅供参考勿当无风险）。
额度：免费 30 次/分钟 → 2.2s 间隔；大列表自带断点缓存（--cache 路径，默认同目录 .goplus_cache.json）。
"""
import argparse, json, os, ssl, sys, time, urllib.request

try:
    import certifi
    _CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _CTX = ssl.create_default_context()

CHAIN_ID = {'eth': '1', 'bsc': '56', 'base': '8453', 'arbitrum': '42161'}
# 行为旗标字段（值 '1' 即命中）；data_source/contract_address 为元信息
FLAG_FIELDS = ('cybercrime', 'money_laundering', 'financial_crime', 'darkweb_transactions',
               'phishing_activities', 'blacklist_doubt', 'stealing_attack', 'blackmail_activities',
               'sanctioned', 'mixer', 'honeypot_related_address', 'fake_kyc',
               'malicious_mining_activities', 'gas_abuse', 'reinit', 'fake_token',
               'fake_standard_interface', 'number_of_malicious_contracts_created')


def query(addr, chain, retries=4):
    url = f'https://api.gopluslabs.io/api/v1/address_security/{addr}'
    cid = CHAIN_ID.get(chain)
    if cid:
        url += f'?chain_id={cid}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    for i in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30, context=_CTX) as r:
                d = json.load(r)
            if d.get('code') == 1:
                return d.get('result') or {}
            if d.get('code') == 4029:          # rate limit
                time.sleep(30)
                continue
            return {'_error': f"code={d.get('code')} {d.get('message')}"}
        except Exception as e:
            time.sleep(8 * (i + 1))
    return {'_error': 'retries exhausted'}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('addrs', nargs='*')
    p.add_argument('--chain', required=True,
                   choices=['eth', 'bsc', 'base', 'arbitrum', 'sol', 'robinhood'])
    p.add_argument('--file')
    p.add_argument('--json', action='store_true')
    p.add_argument('--all', action='store_true')
    p.add_argument('--cache', default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                   '.goplus_cache.json'))
    a = p.parse_args()
    addrs = list(a.addrs)
    if a.file:
        addrs += [l.strip() for l in open(a.file) if l.strip()]
    if not addrs:
        p.error('无地址输入')
    cache = {}
    if os.path.exists(a.cache):
        cache = json.load(open(a.cache))
    n_hit = 0
    for i, addr in enumerate(addrs):
        key = f'{a.chain}:{addr.lower()}'
        if key in cache:
            res = cache[key]
        else:
            res = query(addr, a.chain)
            cache[key] = res
            if (i + 1) % 25 == 0:
                json.dump(cache, open(a.cache, 'w'))
            time.sleep(2.2)
        hits = sorted(k for k in FLAG_FIELDS if res.get(k) not in (None, '', '0'))
        err = res.get('_error')
        if hits:
            n_hit += 1
        if a.json:
            print(json.dumps({'address': addr, 'chain': a.chain, 'hits': hits,
                              'data_source': res.get('data_source', ''), 'error': err},
                             ensure_ascii=False))
        elif hits:
            print(f'[HIT ] {addr}  {"|".join(hits)}  (源:{res.get("data_source", "?")})')
        elif err:
            print(f'[ERR ] {addr}  {err}')
        elif a.all:
            print(f'[ok  ] {addr}')
    json.dump(cache, open(a.cache, 'w'))
    if not a.json:
        print(f'—— {len(addrs)} 址 | 命中 {n_hit} | candidate 级：命中≠定性，人工核验后才可写进报告', file=sys.stderr)


if __name__ == '__main__':
    main()
