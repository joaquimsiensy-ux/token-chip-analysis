#!/usr/bin/env python3
"""滚动拉 GMGN kol/smartmoney 交易流，聚合独立钱包 → gmgn_wallets.jsonl"""
import json, subprocess, time, sys, os

GMGN = '/Users/uravvv/.npm-global/bin/gmgn-cli'
CHAINS = ['sol', 'bsc', 'base', 'eth']
KINDS = ['kol', 'smartmoney']
ROUNDS = int(sys.argv[1]) if len(sys.argv) > 1 else 12
OUT = 'gmgn_wallets.jsonl'

seen = {}  # (chain, maker) -> info
if os.path.exists(OUT):
    for line in open(OUT):
        try:
            r = json.loads(line)
            seen[(r['chain'], r['address'])] = r
        except Exception:
            pass

def flush():
    with open(OUT, 'w') as f:
        for r in seen.values():
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

for rnd in range(ROUNDS):
    for chain in CHAINS:
        for kind in KINDS:
            try:
                p = subprocess.run([GMGN, 'track', kind, '--chain', chain, '--limit', '200', '--raw'],
                                   capture_output=True, text=True, timeout=60)
                d = json.loads(p.stdout)
            except Exception as e:
                print(f'r{rnd} {chain}/{kind} ERR {e}', flush=True)
                time.sleep(2); continue
            new = 0
            for t in d.get('list', []):
                m = t.get('maker'); mi = t.get('maker_info') or {}
                if not m: continue
                key = (chain, m)
                rec = seen.get(key)
                tags = sorted(set((rec['tags'] if rec else []) + (mi.get('tags') or [])))
                kinds = sorted(set((rec['kinds'] if rec else []) + [kind]))
                if not rec: new += 1
                seen[key] = {
                    'address': m, 'chain': chain, 'kinds': kinds, 'tags': tags,
                    'twitter_username': mi.get('twitter_username') or (rec or {}).get('twitter_username') or '',
                    'twitter_name': mi.get('twitter_name') or (rec or {}).get('twitter_name') or '',
                    'name': mi.get('name') or (rec or {}).get('name') or '',
                    'last_seen_ts': max(t.get('timestamp') or 0, (rec or {}).get('last_seen_ts') or 0),
                }
            print(f'r{rnd} {chain}/{kind}: +{new} (total {len(seen)})', flush=True)
            time.sleep(1.5)
    flush()
    time.sleep(20)
flush()
print('DONE total wallets:', len(seen))
