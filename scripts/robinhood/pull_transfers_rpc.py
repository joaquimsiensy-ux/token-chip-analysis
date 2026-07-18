#!/usr/bin/env python3
"""RPC getLogs 版全量 Transfer 拉取（HyperSync 429 时的备选通道，v2.25 收编）。
来源：Index(Robinhood) 分析 2026-07-18——HyperSync logs 高峰期整体 429 连败时切此通道。
token/rpc 从工作目录 config.json 读；用法：python3 pull_transfers_rpc.py <起始block> <结束block>
坑：RPC getLogs 无块时间戳，须配 pull_block_ts_anchors.py 拉锚点插值；"log query timed out" 会自适应缩窗。
输出与 pull_transfers.py 兼容：data/transfers_rpc.jsonl（block/ts/tx/logi/from/to/amount；无 txfrom/txto）。
自适应缩窗：结果超限或报错就折半窗口。块时间戳批量另取（按块号去重后 eth_getBlockByNumber）。"""
import json, subprocess, sys, time

UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
RPC=None  # 从 config 读，见 _cfg()
import os
def _cfg():
    with open("config.json") as f: c=json.load(f)
    return (c.get("token") or "").lower(), (c.get("rpc") or "https://rpc.mainnet.chain.robinhood.com")
TOKEN,RPC_CFG=_cfg()
TRANSFER="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

def rpc(method, params, retries=6):
    global RPC
    RPC=RPC or RPC_CFG
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params})
    for i in range(retries):
        r=subprocess.run(['curl','-s','--max-time','120','-H','User-Agent: '+UA,'-H','Content-Type: application/json','-X','POST',RPC,'-d',body],capture_output=True,text=True)
        try:
            d=json.loads(r.stdout)
            if 'error' in d: return ('err', d['error'])
            return ('ok', d.get('result'))
        except Exception:
            time.sleep(2*(i+1))
    return ('err', {'message':'curl fail'})

start_block=int(sys.argv[1]); end_block=int(sys.argv[2])
out=open('data/transfers_rpc.jsonl','a')
blocks_need=set()
cur=start_block; win=200000
rows_total=0
while cur<=end_block:
    hi=min(cur+win-1, end_block)
    st,res=rpc('eth_getLogs',[{"fromBlock":hex(cur),"toBlock":hex(hi),"address":TOKEN,"topics":[[TRANSFER]]}])
    if st=='err':
        msg=str(res.get('message',''))
        if win>2000:
            win//=2; print(f'窗口缩至{win} ({msg[:60]})',flush=True); continue
        else:
            print('小窗仍失败,等5s',msg[:80],flush=True); time.sleep(5); continue
    n=len(res)
    for lg in res:
        blk=int(lg['blockNumber'],16)
        row={"block":blk,"ts":None,"tx":lg['transactionHash'],
             "logi":int(lg['logIndex'],16),
             "from":'0x'+lg['topics'][1][26:],"to":'0x'+lg['topics'][2][26:],
             "amount":str(int(lg['data'][:66],16))}
        out.write(json.dumps(row)+'\n'); blocks_need.add(blk)
    rows_total+=n
    print(f'blocks {cur}-{hi}: {n} logs (累计{rows_total})',flush=True)
    cur=hi+1
    if n>8000 and win>4000: win=int(win*0.6)
    elif n<2000: win=min(win*2, 400000)
out.close()
json.dump(sorted(blocks_need), open('data/rpc_blocks_need.json','w'))
print(f'DONE rows={rows_total} blocks={len(blocks_need)}',flush=True)
