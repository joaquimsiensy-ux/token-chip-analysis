#!/usr/bin/env python3
"""labels-filecoin.csv 构建器（v4 2026-07-17 首建）

源：filfox API 逐个 GET /address/f0<N>（低位段 f00–f0126 = 创世实体/系统 actor 集中区，
方法出处 references/data-pipeline-filecoin.md §2；actor ID 协议分配不轮换，标签长期稳定）。
收录规则：
  - 系统 actor（actor ∈ system/init/reward/cron/storagepower/storagemarket/verifiedregistry/
    paymentchannel/eam/burn…）→ infra/exclude（f099 燃烧地址 → burn/exclude）
  - 带官方 tag 的实体（Foundation/Protocol Labs/Mining Reserve…）→ fund/identity
  - 其余带 tag 的 → entity/identity；无 tag 且非系统 actor 的跳过（宁缺毋滥）
用法：python3 build_filecoin_labels.py && cd sources && python3 ../add_labels.py filecoin_additions.csv
"""
import csv, json, os, time, urllib.request, ssl

try:
    import certifi
    CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    CTX = ssl.create_default_context()

_HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(_HERE, 'sources', 'filecoin_additions.csv')

SYSTEM_ACTORS = {'system', 'init', 'reward', 'cron', 'storagepower', 'storagemarket',
                 'verifiedregistry', 'paymentchannel', 'eam', 'datacap', 'ethaccount', 'evm'}


UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')     # filfox 拦 python 默认 UA（403）


def fetch(fid):
    url = f'https://filfox.info/api/v1/address/{fid}'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=20, context=CTX) as r:
            return json.loads(r.read())
    except Exception:
        return None


def main():
    rows = []
    for n in range(0, 127):
        fid = f'f0{n}' if n >= 10 else f'f0{n}'
        d = fetch(f'f0{n}')
        time.sleep(0.25)
        if not d or d.get('id') is None:
            continue
        fid = d['id']
        tag = ((d.get('tag') or {}).get('name') or '').strip()
        actor = (d.get('actor') or '').strip()
        if fid == 'f099' or actor == 'burn':
            cat, tier, name = 'burn', 'exclude', tag or 'Filecoin 燃烧地址'
        elif actor in SYSTEM_ACTORS:
            cat, tier = 'infra', 'exclude'
            name = tag or f'Filecoin 系统 actor（{actor}）'
        elif tag:
            low = tag.lower()
            if 'foundation' in low or 'protocol labs' in low or 'reserve' in low:
                cat, tier, name = 'fund', 'identity', tag
            elif 'exchange' in low or any(w in low for w in ('binance', 'okx', 'huobi', 'gate')):
                cat, tier, name = 'cex', 'exclude', tag
            else:
                cat, tier, name = 'entity', 'identity', tag
        else:
            continue        # 无 tag 非系统：跳过
        rows.append({
            'address': fid, 'chain': 'filecoin', 'name': name, 'category': cat, 'tier': tier,
            'source': 'manual-filfox', 'added_date': '2026-07-17',
            'evidence': f'filfox /address/{fid} 官方标签（actor={actor}，2026-07-17 拉取）',
            'risk_flags': '', 'merge_policy': '', 'balance_policy': '',
            'source_snapshot_at': '2026-07-17', 'verified_at': '2026-07-17',
            'status': '', 'raw_labels': actor,
        })
        if n % 30 == 0:
            print(f'  f0{n} … {len(rows)} 条')
    with open(OUT, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    from collections import Counter
    print(f'filecoin_additions.csv: {len(rows)} 条 |', Counter(r['category'] for r in rows).most_common())


if __name__ == '__main__':
    main()
