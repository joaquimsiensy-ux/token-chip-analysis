#!/usr/bin/env python3
"""对账三查：①重建余额 vs 链上 balanceOf（Alchemy，截止块口径）②供给闭合 ③GMGN top10 对表。
用法：python3 scripts/verify_recon.py  （工作目录跑，读 data/balances_final.json + data/replay_stats.json）
"""
import json, csv, subprocess, sys

CFG = json.load(open('config.json'))
TOT = CFG['total_supply_human'] * 10**CFG['decimals']
KEY = CFG['alchemy']['key']
EP = CFG['alchemy']['url'] + KEY
PROXY = CFG['proxy']
Z = '0x0000000000000000000000000000000000000000'
DEAD = '0x000000000000000000000000000000000000dead'

bal = json.load(open('data/balances_final.json'))
stats = json.load(open('data/replay_stats.json'))
print('replay_stats:', json.dumps(stats)[:400])

# ---- 查2：供给闭合 ----
mint = int(stats.get('mint_total_wei', 0))
burn = int(stats.get('burn_total_wei', 0))
ssum = sum(int(v) for v in bal.values())
print(f'\n[查2 供给闭合] mint={mint} burn={burn} mint-burn={mint-burn}')
print(f'  sum(balances)={ssum}  vs 名义总量 {TOT}')
print(f'  mint==名义总量: {mint == TOT}   sum==mint-burn: {ssum == mint - burn}')
neg = [(a, v) for a, v in bal.items() if int(v) < 0]
print(f'  负余额地址数: {len(neg)}', neg[:3] if neg else '')

# ---- 查1：重建余额 vs 链上 balanceOf（截止块）----
end_block = stats.get('max_block') or stats.get('last_block')
if not end_block:
    # 从 merged.csv 末行拿
    import subprocess as sp
    last = sp.run(['tail', '-1', 'data/merged.csv'], capture_output=True, text=True).stdout
    end_block = int(last.split(',')[0])
tag = hex(int(end_block))
top = sorted(bal.items(), key=lambda kv: -int(kv[1]))[:15]
print(f'\n[查1 余额对账] 截止块 {end_block}，top15 重建 vs eth_call balanceOf:')
ok = bad = 0
for a, v in top:
    if a in (Z, DEAD):
        continue
    data = '0x70a08231' + '0' * 24 + a[2:]
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_call",
                       "params": [{"to": CFG['token'], "data": data}, tag]})
    r = subprocess.run(['curl', '-s', '-x', PROXY, '--max-time', '20', '-X', 'POST',
                        '-H', 'Content-Type: application/json', '-d', body, EP],
                       capture_output=True, text=True)
    try:
        chain = int(json.loads(r.stdout)['result'], 16)
    except Exception:
        print(f'  {a[:16]} RPC失败: {r.stdout[:80]}')
        bad += 1
        continue
    match = chain == int(v)
    ok += match
    bad += (not match)
    print(f'  {a[:16]} 重建 {int(v)/10**9/1e9:.4f}B vs 链上 {chain/10**9/1e9:.4f}B  {"OK" if match else "MISMATCH Δ=%d" % (chain-int(v))}')
print(f'  结果: {ok} OK / {bad} MISMATCH-or-fail')

# ---- 查3：GMGN top10 对表（软对账，口径差异容忍 0.1pp）----
print('\n[查3 GMGN对表] (软对账，GMGN 快照有延迟)')
gm = list(csv.DictReader(open('data/gmgn_top100.csv')))[:10]
for g in gm:
    a = g['address']
    p_g = float(g['pct'] or 0) * 100
    p_r = int(bal.get(a, 0)) * 100 / TOT
    flag = 'OK' if abs(p_g - p_r) < 0.15 else 'DIFF'
    print(f'  {a[:16]} gmgn {p_g:.3f}% vs 重建 {p_r:.3f}%  {flag}')
print('\n完成。查1 全 OK + 查2 闭合 = 硬关卡通过；查3 DIFF 需解释（GMGN 延迟/口径）。')
