#!/usr/bin/env python3
"""锚点时间戳：每 20000 块一个锚 + 全部锚点单发；输出 data/ts_anchors.json {block:unix_ts}"""
import json, subprocess, time
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
RPC="https://rpc.mainnet.chain.robinhood.com"
anchors=list(range(1670000,12366461,20000))+[12366460]
done={}
import os
if os.path.exists('data/ts_anchors.json'): done=json.load(open('data/ts_anchors.json'))
for i,b in enumerate(anchors):
    if str(b) in done: continue
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_getBlockByNumber","params":[hex(b),False]})
    for att in range(4):
        r=subprocess.run(['curl','-s','--max-time','30','-H','User-Agent: '+UA,'-H','Content-Type: application/json','-X','POST',RPC,'-d',body],capture_output=True,text=True)
        try:
            res=json.loads(r.stdout).get('result') or {}
            if res.get('timestamp'):
                done[str(b)]=int(res['timestamp'],16); break
        except Exception: pass
        time.sleep(1+att)
    if i%50==0:
        print(f'{i}/{len(anchors)}',flush=True); json.dump(done,open('data/ts_anchors.json','w'))
json.dump(done,open('data/ts_anchors.json','w'))
print('DONE',len(done),flush=True)
