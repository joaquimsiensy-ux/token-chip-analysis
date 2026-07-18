#!/usr/bin/env python3
"""Robinhood 链 Blockscout verified-contracts 增量拉取（v4.1 2026-07-17，P1 通道落地）

用途：定期把链上已验证合约拉成候选池 sources/robinhood_verified_contracts.csv——
  同名家族=工厂克隆线索（发射台实例/公共 bot 变体），人工审后按角色补录标签库。
  ⚠️ 只产候选，不自动入库（合约名≠角色；纪律：行为复核后才定 exclude）。

用法（在 scripts/labels/ 下）：
  python3 pull_verified_contracts.py            # 增量：拉到全页已知即停
  python3 pull_verified_contracts.py --full     # 全量重拉（首轮/校准用）
  python3 pull_verified_contracts.py --families # 只统计现有候选池同名家族 Top50

坑：Blockscout 须带浏览器 UA（python 默认 UA 被 403）；分页 next_page_params 原样回传。
"""
import csv, json, os, ssl, sys, time, urllib.parse, urllib.request

try:
    import certifi
    _CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _CTX = ssl.create_default_context()

_HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(_HERE, 'sources', 'robinhood_verified_contracts.csv')
BASE = 'https://robinhoodchain.blockscout.com/api/v2/smart-contracts'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')
FIELDS = ['address', 'name', 'compiler_version', 'language', 'verified_at']


def fetch(params):
    url = BASE + ('?' + urllib.parse.urlencode(params) if params else '')
    req = urllib.request.Request(url, headers={'accept': 'application/json', 'User-Agent': UA})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60, context=_CTX) as r:
                return json.load(r)
        except Exception as e:
            print(f'  页失败（{e}），退避 {10 * (attempt + 1)}s', file=sys.stderr)
            time.sleep(10 * (attempt + 1))
    raise RuntimeError('连续 5 次失败，中止（已拉部分已落盘）')


def families(rows, top=50):
    from collections import Counter
    c = Counter(r['name'] for r in rows if r['name'])
    print(f'候选池 {len(rows)} 合约 | 同名家族 Top{top}（≥2 才列，克隆工厂线索）:')
    for name, n in c.most_common(top):
        if n < 2:
            break
        print(f'  {n:6d}  {name}')


def main():
    known_rows = []
    if os.path.exists(OUT):
        known_rows = list(csv.DictReader(open(OUT)))
    known = {r['address'].lower() for r in known_rows}
    if '--families' in sys.argv:
        families(known_rows)
        return
    full = '--full' in sys.argv
    new_rows, params, page = [], {}, 0
    while True:
        d = fetch(params)
        items = d.get('items', [])
        page += 1
        fresh = 0
        for it in items:
            a = (it.get('address') or {})
            h = (a.get('hash') or '').lower()
            if not h:
                continue
            if h in known:
                continue
            known.add(h)
            fresh += 1
            new_rows.append({
                'address': h,
                'name': a.get('name') or it.get('name') or '',
                'compiler_version': it.get('compiler_version') or '',
                'language': it.get('language') or '',
                'verified_at': (it.get('verified_at') or '')[:19],
            })
        if page % 20 == 0:
            print(f'  第 {page} 页 | 新增累计 {len(new_rows)}')
        nxt = d.get('next_page_params')
        if not nxt:
            break
        if not full and items and fresh == 0:
            print(f'  第 {page} 页全部已知，增量模式停止')
            break
        params = nxt
        time.sleep(0.3)
    if not new_rows:
        print(f'无新增（候选池 {len(known_rows)}）')
        return
    all_rows = new_rows + known_rows          # 新的在前（id 降序习惯）
    tmp = OUT + '.tmp'
    with open(tmp, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction='ignore')
        w.writeheader()
        w.writerows(all_rows)
    os.replace(tmp, OUT)
    print(f'完成：新增 {len(new_rows)} → 候选池 {len(all_rows)}，已存 {OUT}')
    families(all_rows, top=30)


if __name__ == '__main__':
    main()
