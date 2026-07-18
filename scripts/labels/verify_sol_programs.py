#!/usr/bin/env python3
"""SOL 主流程序 ID 候选 → 公共 RPC getMultipleAccounts 核验 executable
高置信=vanity 自说明或官方文档背书；核验不过的一律不入库"""
import json, urllib.request, ssl, certifi, time

CANDIDATES = [
    # (program_id, name, category, confidence_note)
    ('TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb', 'Token-2022 程序', 'program', 'vanity 自说明'),
    ('ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL', 'Associated Token Account 程序', 'program', 'vanity'),
    ('MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr', 'Memo 程序', 'program', 'vanity'),
    ('Stake11111111111111111111111111111111111111', 'Stake 程序', 'program', 'native'),
    ('Vote111111111111111111111111111111111111111', 'Vote 程序', 'program', 'native'),
    ('ComputeBudget111111111111111111111111111111', 'Compute Budget 程序', 'program', 'native'),
    ('BPFLoaderUpgradeab1e11111111111111111111111', 'BPF Loader Upgradeable', 'program', 'native'),
    ('675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8', 'Raydium AMM V4', 'program', '社区公认'),
    ('CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK', 'Raydium CLMM', 'program', 'vanity CAMM'),
    ('CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C', 'Raydium CPMM', 'program', 'vanity CPMM'),
    ('LanMV9sAd7wArD4vJFi2qDdfnVhFxYSUg6eADduJ3uj', 'Raydium LaunchLab（bonk.fun 发射）', 'launchpad', 'vanity Lan'),
    ('whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc', 'Orca Whirlpool', 'program', 'vanity whirL'),
    ('LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo', 'Meteora DLMM', 'program', 'vanity LB'),
    ('Eo7WjKq67rjJQSZxS6z3YkapzY3eMj6Xy8X5EQVn5UaB', 'Meteora Dynamic AMM (Pools)', 'program', '待交叉核验'),
    ('dbcij3LWUppWqq96dh6gJWwBifmcGfLSB5D4DuSMaqN', 'Meteora DBC（dynamic bonding curve）', 'launchpad', '待交叉核验'),
    ('cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG', 'Meteora DAMM v2', 'program', '待交叉核验'),
    ('JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4', 'Jupiter Aggregator v6', 'router', 'vanity JUP6'),
    ('j1o2qRpjcyUwEvwtcfhEQefh773ZgjxcVRry7LDqg5X', 'Jupiter Limit Order', 'router', '待交叉核验'),
    ('MoonCVVNZFSYkqNXP6bxHLPL6QQJiMagDL3qcqUQTrG', 'Moonshot 发射程序', 'launchpad', 'vanity Moon'),
    ('wormDTUJ6AWPNvk59vGQbDvGJmqbDTdgWgAqcLBCgUb', 'Wormhole Portal Token Bridge', 'bridge', 'vanity worm'),
    ('worm2ZoG2kUd4vFXhvjh93UUH596ayRfgQ2MgjNMTth', 'Wormhole Core Bridge', 'bridge', 'vanity worm2'),
    ('DEbrdGj3HsRsAzx6uH4MKyREKxVAfBydijLUF3ygsFfh', 'deBridge DLN 程序', 'bridge', '待交叉核验'),
    ('srmqPvymJeFKQ4zGQed1GFppgkRHL9kaELCbyksJtPX', 'OpenBook/Serum DEX v3', 'program', 'vanity srm'),
    ('opnb2LAfJYbRMAHHvqjCwQxanZn7ReEHp1k81EohpZb', 'OpenBook v2', 'program', 'vanity opnb'),
    ('PhoeNiXZ8ByJGLkxNfZRnkUfjvmuYqLR89jjFHGqdXY', 'Phoenix DEX', 'program', 'vanity Phoe'),
    ('9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP', 'Orca Token Swap v2（旧）', 'program', '待交叉核验'),
    ('SSwpkEEcbUqx4vtoEByFjSkhKdCT862DNVb52nZg1UZ', 'Saber Stable Swap', 'program', 'vanity SSwp'),
    ('MERLuDFBMmsHnsBPZw2sDQZHvXFMwp8EdjudcU2HKky', 'Mercurial（Meteora 前身）', 'program', 'vanity MER'),
    ('PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu', 'Drift Perp？待核验名称', 'program', '低置信'),
    ('4wTV1YmiEkRvAtNtsSGPtUrqRYQMe5SKy2uB4Jjaxnjf', 'Squads v4？待核验', 'program', '低置信'),
]

ctx = ssl.create_default_context(cafile=certifi.where())
def rpc(method, params):
    req = urllib.request.Request('https://api.mainnet-beta.solana.com',
        data=json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode(),
        headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
        return json.load(r)

ids = [c[0] for c in CANDIDATES]
ok, fail = [], []
for i in range(0, len(ids), 30):
    batch = ids[i:i+30]
    res = rpc('getMultipleAccounts', [batch, {'encoding': 'base64', 'dataSlice': {'offset': 0, 'length': 0}}])
    vals = res['result']['value']
    for pid, acc in zip(batch, vals):
        cand = next(c for c in CANDIDATES if c[0] == pid)
        if acc is None:
            fail.append((pid, cand[1], '账户不存在'))
        elif not acc.get('executable'):
            fail.append((pid, cand[1], 'executable=false'))
        else:
            ok.append(cand)
    time.sleep(1)

print(f'=== 核验通过 {len(ok)} ===')
for c in ok: print(f'  {c[0]}  {c[1]}  [{c[3]}]')
print(f'=== 核验失败 {len(fail)}（不入库） ===')
for pid, name, why in fail: print(f'  {pid}  {name}  -> {why}')

json.dump([{'address': c[0], 'name': c[1], 'category': c[2], 'note': c[3]} for c in ok],
          open('sol_programs_verified.json', 'w'), ensure_ascii=False, indent=1)
