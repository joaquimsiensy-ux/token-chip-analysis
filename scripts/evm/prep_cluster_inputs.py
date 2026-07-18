#!/usr/bin/env python3
"""把 merged.csv 转成 cluster.py 期望的 6 列 part 文件；把 gmgn/*.json 转成顶层 {list:[...]} 结构。
（cluster.py 只认顶层 list；gmgn-cli --raw 是 data.list —— 不转换 R2 gas 同源会静默失效）
工作目录跑：python3 scripts/prep_cluster_inputs.py
"""
import csv, json, glob, os, shutil

# 1) merged.csv -> eth_part_0.csv (block,tx,log_index,from,to,value)
n = 0
with open('data/merged.csv') as f, open('eth_part_0.csv', 'w', newline='') as g:
    r = csv.reader(f)
    w = csv.writer(g)
    header = next(r)  # block,ts,tx,log_index,from,to,value
    for row in r:
        blk, ts, tx, li, frm, to, val = row
        w.writerow([blk, tx, li, frm, to, val])
        n += 1
print(f'eth_part_0.csv: {n} rows')

# 2) gmgn 原始移入 data/gmgn_raw/，gmgn/ 放顶层 list 转换版
os.makedirs('data/gmgn_raw', exist_ok=True)
for p in glob.glob('gmgn/eth_*.json'):
    base = os.path.basename(p)
    raw_path = os.path.join('data/gmgn_raw', base)
    if not os.path.exists(raw_path):
        shutil.copy2(p, raw_path)
    try:
        j = json.load(open(raw_path))
    except Exception:
        continue
    lst = (j.get('data') or {}).get('list') if isinstance(j.get('data'), dict) else None
    if lst is None:
        lst = j.get('list') or []
    json.dump({'list': lst}, open(p, 'w'))
print('gmgn/ 转换完成（原始在 data/gmgn_raw/）')
