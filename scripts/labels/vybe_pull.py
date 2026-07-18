#!/usr/bin/env python3
"""拉取 Vybe known/labeled accounts 全量 → vybe_known_accounts.json
用法: python3 vybe_pull.py <API_KEY 或存放 key 的文件路径>"""
import json, os, sys, time, urllib.request, urllib.error, ssl, certifi

KEY = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/.config/vybe/api-key')
if os.path.exists(KEY):
    KEY = open(KEY).read().strip()
ctx = ssl.create_default_context(cafile=certifi.where())
BASES = ['https://api.vybenetwork.xyz/account/known-accounts',
         'https://api.vybenetwork.xyz/v4/wallets/labeled-accounts']

def get(url):
    req = urllib.request.Request(url, headers={'x-api-key': KEY, 'accept': 'application/json'})
    with urllib.request.urlopen(req, context=ctx, timeout=60) as r:
        return json.load(r)

base = None
probe = None
for b in BASES:
    try:
        probe = get(b)
        base = b
        print('可用端点:', b)
        break
    except urllib.error.HTTPError as e:
        print(b, '->', e.code)
if base is None:
    sys.exit('两个端点都不可用')

# 观察返回结构
if isinstance(probe, dict):
    print('顶层键:', list(probe.keys()))
    for k, v in probe.items():
        if isinstance(v, list):
            print(f'  {k}: {len(v)} 条; 样例:', json.dumps(v[0], ensure_ascii=False)[:300] if v else '空')

rows = probe.get('accounts') if isinstance(probe, dict) else probe
rows = rows or []
# 若一次未返回全量，按 labels 逐类补拉（labels 取样例里出现过的）
labels_seen = set()
for r in rows:
    for l in (r.get('labels') or []):
        labels_seen.add(l)
print('首拉:', len(rows), '条; 标签种类:', sorted(labels_seen))

allrows = {r.get('ownerAddress') or r.get('accountAddress') or r.get('address'): r for r in rows}
for l in sorted(labels_seen):
    try:
        d = get(base + '?labels=' + urllib.parse.quote(l))
        rs = d.get('accounts') if isinstance(d, dict) else d
        n0 = len(allrows)
        for r in (rs or []):
            allrows[r.get('ownerAddress') or r.get('accountAddress') or r.get('address')] = r
        print(f'label={l}: +{len(allrows)-n0} (total {len(allrows)})')
        time.sleep(1.1)  # 60 RPM 限速
    except Exception as e:
        print(f'label={l} ERR {e}')

json.dump(list(allrows.values()), open('vybe_known_accounts.json', 'w'), ensure_ascii=False, indent=1)
print('DONE ->', len(allrows), '条存 vybe_known_accounts.json')
