#!/usr/bin/env python3
"""合并 HyperSync gzip + RPC jsonl，填 ts，去重，输出 data/transfers.jsonl.gz（覆盖）"""
import json, gzip, os
seen=set(); rows=[]
f=gzip.open('data/transfers.jsonl.gz','rt')
try:
    for line in f:
        try: r=json.loads(line)
        except Exception: continue
        k=(r['block'], r['logi'])
        if k in seen: continue
        seen.add(k); rows.append(r)
except EOFError:
    print('gzip 截断，止于已读部分')
f.close()
hs_max=max(r['block'] for r in rows)
from datetime import datetime, timezone
anch=json.load(open('data/ts_anchors.json'))
ab=sorted(int(k) for k in anch)
import bisect
def interp(b):
    i=bisect.bisect_left(ab,b)
    if i==0: return anch[str(ab[0])]
    if i>=len(ab): return anch[str(ab[-1])]
    b0,b1=ab[i-1],ab[i]
    t0,t1=anch[str(b0)],anch[str(b1)]
    return t0+(t1-t0)*(b-b0)/(b1-b0) if b1>b0 else t0
n_rpc=0
for line in open('data/transfers_rpc.jsonl'):
    r=json.loads(line)
    k=(r['block'], r['logi'])
    if k in seen: continue
    r['ts']=datetime.fromtimestamp(interp(r['block']),timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    seen.add(k); rows.append(r); n_rpc+=1
rows.sort(key=lambda r:(r['block'],r['logi']))
miss_ts=sum(1 for r in rows if not r.get('ts'))
with gzip.open('data/transfers_merged.jsonl.gz','wt') as f:
    for r in rows: f.write(json.dumps(r)+'\n')
os.replace('data/transfers_merged.jsonl.gz','data/transfers.jsonl.gz')
print(f'HyperSync段最高块={hs_max} RPC新增={n_rpc} 合计={len(rows)} 缺ts={miss_ts}')
