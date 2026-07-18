#!/usr/bin/env python3
"""快速 gas 溯源：翻页上限 2 页，超深地址标 approx。累积落盘 data/gas_origins.json。"""
import json, subprocess, sys, time
from pathlib import Path
RPC = "https://api.mainnet-beta.solana.com"
PROXY = "http://127.0.0.1:7897"
def rpc(method, params, retries=4):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params})
    for i in range(retries):
        p = subprocess.run(["curl","-s","-m","30","-x",PROXY,RPC,"-H","Content-Type: application/json","-d",body],
                           capture_output=True, text=True)
        try:
            d = json.loads(p.stdout)
            if "result" in d: return d["result"]
            if (d.get("error") or {}).get("code")==429: time.sleep(3*(i+1)); continue
        except: pass
        time.sleep(1.5*(i+1))
    return None
def oldest_sigs(addr, max_pages=2):
    sigs, before = [], None; approx=False
    for pg in range(max_pages):
        params=[addr,{"limit":1000}]
        if before: params[1]["before"]=before
        res = rpc("getSignaturesForAddress", params)
        if res is None: return None, False
        if not res: break
        sigs.extend(res); before=res[-1]["signature"]; time.sleep(0.13)
        if len(res)<1000: break
    else:
        approx=True  # 达上限，最老可能未到
    sigs=[s for s in sigs if s.get("err") is None]
    return sigs[-3:], approx
def get_funder(sig, addr):
    tx = rpc("getTransaction", [sig, {"encoding":"jsonParsed","maxSupportedTransactionVersion":0}])
    if not tx: return None, None
    meta = tx.get("meta") or {}
    keys = [k["pubkey"] if isinstance(k,dict) else k for k in tx["transaction"]["message"]["accountKeys"]]
    pre, post = meta.get("preBalances",[]), meta.get("postBalances",[])
    my_delta=0; funder=None; best=0
    for i,k in enumerate(keys):
        d=(post[i]-pre[i])/1e9
        if k==addr: my_delta=d
        elif d < best: best=d; funder=k
    return funder, my_delta
targets = sys.argv[1:]
out_f = Path("data/gas_origins.json")
out = json.loads(out_f.read_text()) if out_f.exists() else {}
for a in targets:
    if a in out: continue
    olds, approx = oldest_sigs(a)
    if olds is None: print(f"{a[:10]} FAIL"); continue
    rec={"first_txs":[], "approx":approx}
    for s in reversed(olds):
        f, d = get_funder(s["signature"], a)
        rec["first_txs"].append({"sig":s["signature"],"ts":s.get("blockTime"),"my_sol_delta":d,"funder":f})
        time.sleep(0.13)
    out[a]=rec
    out_f.write_text(json.dumps(out))
    fn = rec["first_txs"][0]["funder"] if rec["first_txs"] else None
    print(f"{a[:10]}… funder={fn[:10] if fn else '?'}{' [approx]' if approx else ''}", flush=True)
print("DONE")
