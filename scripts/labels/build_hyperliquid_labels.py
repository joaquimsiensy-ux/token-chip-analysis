#!/usr/bin/env python3
"""labels-hyperliquid.csv 构建器（v4 2026-07-17 首建）

源：
  1. Hypurrscan /globalAliases（463 实体标签；sources/hypurrscan_aliases.json，
     刷新: curl -x $PROXY https://api.hypurrscan.io/globalAliases -o hypurrscan_aliases.json）
  2. manual 附加（RPC 亲验的 HyperEVM 系统合约；团队/基金会两条走 gen_manual 的 manual 层）
映射纪律：
  Deployer → contract-deployer/identity（发币人身份，不剔除——正是筹码分析要盯的人）
  CEX 名   → cex/exclude；Burn/HIP-2/HyperEVM 桥 → 设施 exclude
  Assistance Fund → fund/identity（回购基金持仓是 HYPE 分析核心主体，绝不能 exclude）
  其余     → entity/identity（保守：标注身份不剔除）
用法：python3 build_hyperliquid_labels.py && cd sources && python3 ../add_labels.py hyperliquid_additions.csv
"""
import csv, json, os, re

_HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(_HERE, 'sources', 'hypurrscan_aliases.json')
OUT = os.path.join(_HERE, 'sources', 'hyperliquid_additions.csv')

CEX_WORDS = ('binance', 'okx', 'bybit', 'gate', 'kucoin', 'mexc', 'bitget', 'htx', 'kraken',
             'coinbase', 'crypto.com', 'bitfinex', 'upbit', 'bithumb', 'deribit', 'bitmart',
             'robinhood', 'bitvavo', 'coinspot')   # v4.1 codex 复核：漏词致 8 条交易所钱包错归 entity


def classify(name):
    n = name.strip()
    l = n.lower()
    if 'deployer' in l:
        return 'contract-deployer', 'identity'
    if any(w in l for w in CEX_WORDS):
        return 'cex', 'exclude'
    if 'burn' in l:
        return 'burn', 'exclude'
    if n in ('HIP-2', 'HyperEVM'):        # 协议做市/官方桥
        return 'infra' if n == 'HIP-2' else 'bridge', 'exclude'
    if 'assistance fund' in l:
        return 'fund', 'identity'
    if 'foundation' in l or 'team' in l:
        return 'fund', 'identity'
    if 'vault' in l:
        return 'locker', 'identity'
    return 'entity', 'identity'


rows = []
d = json.load(open(SRC))
for addr, name in d.items():
    a = addr.lower()
    if not re.fullmatch(r'0x[0-9a-f]{40}', a):
        continue
    cat, tier = classify(name)
    rows.append({
        'address': a, 'chain': 'hyperliquid', 'name': name, 'category': cat, 'tier': tier,
        'source': 'hypurrscan-aliases', 'added_date': '2026-07-17',
        'evidence': 'Hypurrscan /globalAliases（2026-07-17 拉取）',
        'risk_flags': '', 'merge_policy': '', 'balance_policy': '',
        'source_snapshot_at': '2026-07-17', 'verified_at': '', 'status': '', 'raw_labels': '',
    })

# HyperCore↔HyperEVM 系统转移地址族（v4.1 codex 复核补录）
# 官方规则（hyperliquid.gitbook.io …/hypercore-less-than-greater-than-hyperevm-transfers）：
#   每个 spot token 的系统地址 = 首字节 0x20 + 全零 + token index（big-endian）
#   例外 HYPE = 0x2222…2222（系统合约，receive() 发 Received 事件）
# 这些地址在 EVM 侧托管 Core 侧总量（PURR 系统地址余额亲验 2026-07-17），漏标会被当成超级大户。
# 源：sources/hl_spotmeta.json（api.hyperliquid.xyz/info type=spotMeta 快照）；缺失则告警跳过。
SPOTMETA = os.path.join(_HERE, 'sources', 'hl_spotmeta.json')
if os.path.exists(SPOTMETA):
    _sm = json.load(open(SPOTMETA))
    for t in _sm.get('tokens', []):
        if t['name'] == 'HYPE':
            continue    # HYPE 走 0x2222…2222（Hypurrscan 'HyperEVM' 别名已入库，下面 MANUAL 增强）
        sys_addr = '0x20' + hex(t['index'])[2:].rjust(38, '0')
        rows.append({
            'address': sys_addr, 'chain': 'hyperliquid',
            'name': f"HyperCore 系统转移地址: {t['name']} (index {t['index']})",
            'category': 'bridge', 'tier': 'exclude',
            'source': 'manual-hldocs', 'added_date': '2026-07-17',
            'evidence': '官方 docs 系统地址规则（0x20+index big-endian）确定性生成；公式经官方示例 index200→…c8 单测',
            'risk_flags': '', 'merge_policy': '', 'balance_policy': '',
            'source_snapshot_at': '2026-07-17', 'verified_at': '2026-07-17', 'status': '', 'raw_labels': '',
        })
else:
    print('⚠️ sources/hl_spotmeta.json 缺失——系统转移地址族未生成（刷新: curl api.hyperliquid.xyz/info type=spotMeta）')

# manual 附加：HyperEVM 系统合约（RPC 亲验后收录）
MANUAL = [
    {'address': '0x2222222222222222222222222222222222222222', 'chain': 'hyperliquid',
     'name': 'HYPE 系统转移地址（HyperCore↔HyperEVM 官方桥）', 'category': 'bridge', 'tier': 'exclude',
     'source': 'manual-hldocs', 'added_date': '2026-07-17',
     'evidence': '官方 docs：HYPE system address 例外规则；rpc getCode 非空亲验 2026-07-17',
     'risk_flags': '', 'merge_policy': '', 'balance_policy': '',
     'source_snapshot_at': '2026-07-17', 'verified_at': '2026-07-17', 'status': '', 'raw_labels': ''},
    {'address': '0x3333333333333333333333333333333333333333', 'chain': 'hyperliquid',
     'name': 'CoreWriter（HyperEVM→HyperCore 动作系统合约）', 'category': 'infra', 'tier': 'exclude',
     'source': 'manual-hldocs', 'added_date': '2026-07-17',
     'evidence': '官方 docs Interacting with HyperCore 原文地址（2026-07-17 亲验）',
     'risk_flags': '', 'merge_policy': '', 'balance_policy': '',
     'source_snapshot_at': '2026-07-17', 'verified_at': '2026-07-17', 'status': '', 'raw_labels': ''},
    {'address': '0x5555555555555555555555555555555555555555', 'chain': 'hyperliquid',
     'name': 'WHYPE（HyperEVM 包装 HYPE）', 'category': 'token-contract', 'tier': 'exclude',
     'source': 'manual-rpc', 'added_date': '2026-07-17',
     'evidence': 'rpc.hyperliquid.xyz/evm getCode 非空 + symbol()=WHYPE 亲验 2026-07-17',
     'risk_flags': '', 'merge_policy': '', 'balance_policy': '',
     'source_snapshot_at': '2026-07-17', 'verified_at': '2026-07-17', 'status': '', 'raw_labels': ''},
]

with open(OUT, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows + MANUAL)
from collections import Counter
print(f'hyperliquid_additions.csv: {len(rows) + len(MANUAL)} 条 | ',
      Counter((r['category']) for r in rows).most_common(8))
