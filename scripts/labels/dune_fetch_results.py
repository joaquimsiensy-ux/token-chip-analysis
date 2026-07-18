#!/usr/bin/env python3
"""直接翻页拉取 Dune query 的已有结果 CSV（不重新 execute）
用法: python3 dune_fetch_results.py <key文件或key> <query_id> [输出文件]"""
import os, subprocess, sys, urllib.request, ssl, certifi

KEY, QID = sys.argv[1], sys.argv[2]
OUT = sys.argv[3] if len(sys.argv) > 3 else 'dune_labels.csv'
if os.path.exists(KEY):
    KEY = open(KEY).read().strip()
ctx = ssl.create_default_context(cafile=certifi.where())

url = f'https://api.dune.com/api/v1/query/{QID}/results/csv?limit=100000'
out = open(OUT, 'wb')
page, first = 0, True
while url:
    req = urllib.request.Request(url, headers={'X-Dune-API-Key': KEY})
    with urllib.request.urlopen(req, context=ctx, timeout=300) as resp:
        data = resp.read()
        nexturi = resp.headers.get('X-Dune-Next-Uri') or ''
    if not first and b'\n' in data:
        data = data.split(b'\n', 1)[1]
    out.write(data)
    page += 1
    print(f'page {page}: {len(data)/1e6:.1f}MB, next={bool(nexturi)}', flush=True)
    first = False
    url = nexturi or None
out.close()
subprocess.run(['wc', '-l', OUT], check=False)
