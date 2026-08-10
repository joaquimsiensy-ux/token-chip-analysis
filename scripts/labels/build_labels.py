#!/usr/bin/env python3
"""
多源标签合并构建器 → 分链 labels-{chain}.csv（+labels-{chain}-privacy.csv 隐私体积层）
源优先级: manual > spellbook > dawsbot(etherscan系官方标签) > brianleect(2023快照) > tokens > gmgn
tier: exclude(聚类前剔除) / identity(识别身份不剔除) / risk(制裁·黑客·重大信号)

v4 2026-07-17（codex 交叉复核第二轮融合）：
- 输出 v4 扩展列：merge_policy/balance_policy（默认空=走 resolver 推导）、
  source_snapshot_at（上游快照时点）、verified_at/status（人工核验时态）、raw_labels（原始标签多值保留）
- OFAC ETH 表/ScamSniffer 不再无条件注入三 EVM 链：读 sources/ 下 codetype 辅助文件
  （B2 任务用 RPC getCode 生成），EOA 才跨链注入（同私钥跨链同控成立）；合约只入原链。
  codetype 文件缺失时保守只入原链并告警——宁可少注入，不违反"跨链同址只提示"纪律。
- 纯 tornado-user 行拆到 labels-{chain}-privacy.csv（主表瘦身，resolver 加载时自动合并）
- serial_actors.csv（accumulate_offenders.py 产出的惯犯层）作为 manual 级源合并
- 末尾强制 validate_labels.py + check_manual_sync.py 双校验
"""
import csv, json, os, re, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from labels_resolver import norm_addr   # 全链统一地址规范化
from risk_flags import canonical_risk_flags, merge_risk_flags, parse_risk_flags

CHAIN_BY_ID = {'1': 'eth', '8453': 'base', '56': 'bsc'}
# 这是标签资产构建面，不是 release-tier 或 formal-ready 链清单。
BUILD_CHAINS = {'eth', 'bsc', 'base', 'sol', 'robinhood'}

# 各上游源的快照时点（重建/换源时人工更新；写进 source_snapshot_at 列供时效审计）
SOURCE_SNAPSHOT = {
    'dawsbot': '2026-07-17', 'brianleect': '2023-10', 'tokens': '2026-07-17',
    'dune': '2026-07-16', 'spellbook': '2026-07-16', 'scamsniffer': '2026-07-16',
    'manual': '', 'solprog': '2026-07-16', 'jup': '2026-07-16',
    'gmgn': '2026-07-16', 'kolscan': '2026-07-16', 'serial': '',
}
def snap_of(source):
    return SOURCE_SNAPSHOT.get(source.split('-')[0], '')

# ---------- label -> (category, tier) 映射 ----------
CEX_LABELS = {
    'bitget','deribit','bilaxy','coinbase','kraken','bybit','binance','okex','okx','mexc',
    'gate-io','gate','kucoin','htx','huobi','bitfinex','crypto-com','gemini','bitstamp','upbit',
    'bithumb','poloniex','bittrex','hotbit','exchange','bitmex','phemex','bingx','lbank','xt-com',
    'whitebit','latoken','probit','coinex','ascendex','bitmart','pionex','weex','coinw','hashkey',
    'backpack','nexo','celsius-network','voyager','blockfi','genesis-trading',
    'wazirx','bitrue','tokenize','coindcx','bitso','luno','paribu','btcturk','bitpanda','swissborg',
    'coincheck','bitflyer','liquid','zaif','korbit','coinone','gopax','indodax','bitkub','maicoin',
    'max-exchange','bitopro','hoo','aex','zb','bkex','digifinex','cointiger','bigone','fatbtc',
}
RISK_LABELS = {
    'blocked','ofac-sanctions-lists','ofac-sanctioned','tornado-cash','heist','gambling',
    'phish-hack','exploit','exploiter','scam','mixer','ponzi','plustoken','lazarus-group','sanctioned',
}
BRIDGE_LABELS = {
    'bridge','multichain','wormhole','layer-2','arbitrum','optimism','zksync','starknet','scroll',
    'linea','celer','synapse','hop-protocol','across','stargate','layerzero','axelar','orbiter',
    'polygon','avalanche-bridge','ronin','harmony','anyswap','portal','debridge','base-bridge',
    'rainbow-bridge','gravity-bridge','omni','allbridge','symbiosis','router-protocol','squid',
}
MEV_LABELS = {'mev-bot','mev-builder','sandwich-bot','arbitrage-bot','flashbots'}
INFRA_LABELS = {
    'erc-4337-bundler','pimlico','paymaster','multicall','authereum','safe-formerly-gnosis-safe',
    'account-abstraction','gsn','relayer','gas-station','biconomy','disperse','multisender',
}
BURN_LABELS = {'burn'}
TOKEN_LABELS = {'token-contract','bridged-token','stablecoin','wrapped-token'}
IDENTITY_LABELS = {
    'genesis-address','ico-wallets','token-sale','mining','airdrop-hunter','sybil-delegate',
    'buidlguidl-builders','protocol-guild-member','endaoment','nonprofit','charity','donate',
    'gitcoin-grants','fund','maker-vault-owner','balancer-vested-shareholders','multisig-owner',
    'avs-operator','contract-deployer','proposer-fee-recipient','eth2-depositor','whale',
    'market-maker','otc','vc','dao-treasury','team-wallet','advisor','influencer',
}
DROP_LABELS = {'take-action','friend-tech-users','null',''}
# 高频协议名显式表（其余走后缀规则）
PROTOCOL_LABELS = {
    'sushiswap','balancer','bancor','pancakeswap','burgerswap','bscswap','kyberswap','1inch',
    '0x-protocol','dydx','morpho','euler','liquity','olympusdao','tokemak','set-protocol','mstable',
    'aave','compound','lido','maker','sky','synthetix','yearn','pendle','chainlink','the-graph',
    'curve-finance','curve-fi','uniswap','dex','defi','vaults','staking','proxy-contract',
    'old-contract','deprecated','v1','v2','v3','website-down','eigenlayer','symbiotic','mellow',
    'zapper-fi','juicebox','ondo-finance','paraswap','cow-protocol','metamask','rainbow','xstocks',
    'real-world-assets','yield-farming','lending','derivatives','options','insurance','oracle',
    'ens','nft-marketplace','opensea','blur','looksrare','x2y2','seaport','wyvern',
}
PROTOCOL_SUFFIX = ('-finance','-protocol','-swap','-dao','-fi','-network','-exchange-contract',
                   '-vault','-pool','-router','-capital','-labs','-money','-markets','-lending')

def map_label(label: str):
    l = (label or '').strip().lower()
    if l in DROP_LABELS: return None
    if l in CEX_LABELS: return ('cex', 'exclude')
    if l in RISK_LABELS or l.endswith('-exploit') or l.endswith('-hack'): return (l, 'risk')  # 保留原始风险标签名进 risk_flags
    if l in BRIDGE_LABELS: return ('bridge', 'exclude')
    if l in MEV_LABELS: return ('mev', 'exclude')
    if l in INFRA_LABELS: return ('infra', 'exclude')
    if l in BURN_LABELS: return ('burn', 'exclude')
    if l in TOKEN_LABELS: return ('token-contract', 'exclude')
    if l in PROTOCOL_LABELS: return ('protocol', 'exclude')
    if l in IDENTITY_LABELS: return (l, 'identity')
    if 'exchange' in l: return ('cex', 'exclude')
    if 'bridge' in l: return ('bridge', 'exclude')
    if any(l.endswith(s) for s in PROTOCOL_SUFFIX): return ('protocol', 'exclude')
    return (l or 'other', 'identity')  # 长尾默认识别级，保留原 label 作类目

SRC_PRIORITY = {'curation': -1, 'manual': 0, 'addressbook': 0, 'serial': 0, 'registry': 1, 'spellbook': 1, 'solprog': 1,
                'dune': 1, 'jup': 2, 'dawsbot': 2, 'brianleect': 3, 'tokens': 4,
                'gmgn': 5, 'kolscan': 5}
# curation = 人工精修固化层（additions/curation_overrides_*.csv），必须严格高于 manual/addressbook：
# add_labels.py 对同级采用"新条目覆盖"、本构建器采用"先到保留"，两语义不一致曾致 v4.2 期间
# 直改发布库的 ~20 行精修（Relay solver 官方 API 亲验等）在全量重建时被 gen_manual 泛化行回退
#（2026-07-18 稳定化审计列级 diff 实测）。精修行救回 override 文件并用 curation 源后此回退不再可能。

book = {}  # (chain, address) -> row dict

def upsert(chain, address, name, category, tier, source, date='', evidence='', risk_flag='',
           raw_label=None, verified_at='', status='', merge_policy='', balance_policy=''):
    """risk 不再覆盖功能分类（codex 复核 2026-07-16）：risk 命中记入独立 risk_flags 列，
    与 cex/bridge 等 role 并存——被制裁的 CEX 地址既保留 exclude 剔除行为，又保留高危提示。
    v4：raw_label 多值积累进 raw_labels 列（taxonomy 归并的信息不再丢失）。
    v4.2：merge_policy/balance_policy 透传（此前硬编码空——全量重建会丢手工策略覆盖，
    codex 第四轮复核发现的 round-trip 断环）。"""
    addr = norm_addr(address, chain)    # 全链统一规范化（EVM/HL 小写 0x40、SOL base58、FIL f 地址）
    if addr is None: return
    name = re.sub(r'[\x00-\x08\x0b-\x1f\x7f]', '', name or '')  # 剥 NUL/控制字符（Dune balancer_lbp 名字段实测带 \x00）
    name = re.sub(r'\s+', ' ', name.replace('null', '').strip(' :'))
    if tier == 'risk' and not risk_flag:
        risk_flag = category if category != 'risk' else 'risk'
    key = (chain, addr)
    old = book.get(key)
    prio = SRC_PRIORITY.get(source.split('-')[0], 9)
    raws = set()
    if raw_label:
        raws = {raw_label} if isinstance(raw_label, str) else set(raw_label)
    if old is None:
        book[key] = {'address': addr, 'chain': chain, 'name': name, 'category': category,
                     'tier': tier, 'source': source, 'added_date': date, 'evidence': evidence,
                     'risk_flags': risk_flag, 'merge_policy': merge_policy, 'balance_policy': balance_policy,
                     'source_snapshot_at': snap_of(source), 'verified_at': verified_at,
                     'status': status, '_raw': raws, '_p': prio}
        return
    old['_raw'] |= raws
    # risk 信息只追加 flags，不动已有功能分类
    if risk_flag:
        old['risk_flags'] = merge_risk_flags(old['risk_flags'], risk_flag)
    incoming_is_pure_risk = (tier == 'risk')
    if prio < old['_p']:
        if name: old['name'] = name
        if not incoming_is_pure_risk:
            old.update({'category': category, 'tier': tier})
        elif old['tier'] == 'risk':
            old.update({'category': category, 'tier': tier})
        # 高优先级源带 policy 覆盖值 → 一并生效（v4.2 round-trip 闭环）
        if merge_policy: old['merge_policy'] = merge_policy
        if balance_policy: old['balance_policy'] = balance_policy
        # 高优先级源的 evidence/verified_at/status 同样覆盖（有值才覆盖；2026-07-18 稳定化修复：
        # 此前三列只走末尾"补空"逻辑，curation 精修的证据出处会被先到的低层源占住无法救回）
        if evidence: old['evidence'] = evidence
        if verified_at: old['verified_at'] = verified_at
        if status: old['status'] = status
        old['_p'] = prio
    elif name and not old['name']:
        old['name'] = name
    # 低优先级来源的 policy 只补空，不覆盖
    if merge_policy and not old.get('merge_policy'):
        old['merge_policy'] = merge_policy
    if balance_policy and not old.get('balance_policy'):
        old['balance_policy'] = balance_policy
    # 已存行是纯 risk 占位、新行带功能分类 → 补上功能分类（无论优先级）
    if old['tier'] == 'risk' and not incoming_is_pure_risk:
        old.update({'category': category, 'tier': tier})
    if source not in old['source']:
        old['source'] += '+' + source
    if evidence and not old['evidence']:
        old['evidence'] = evidence
    if verified_at and not old['verified_at']:
        old['verified_at'] = verified_at
    if status and not old['status']:
        old['status'] = status

def _load_codetype(fn):
    """{addr: 'eoa'|'contract'} 辅助文件（probe_codetype.py 生成）；缺失返回 None"""
    if os.path.exists(fn):
        return {k.lower(): v for k, v in json.load(open(fn)).items()}
    return None

# ---------- 1) spellbook（人工核验，高优先级） ----------
# v4.1（codex 第三轮复核）：cex_evms 是同一批地址三链展开——EOA 同私钥跨链同控成立照入；
# 合约地址跨链不成立（他链同址多为无码空投影）——某链无码但他链有码的行 skip。
# codetype 由 probe_codetype.py 对 spellbook_cex_addrs.txt 三链各跑一次生成；缺失则照旧全入+告警。
_SB_CT = {ch: _load_codetype(f'spellbook_cex_codetype_{ch}.json') for ch in ('eth', 'bsc', 'base')}
if any(v is None for v in _SB_CT.values()):
    print('!! spellbook_cex_codetype_*.json 不全：spellbook CEX 未做合约跨链分流（先跑 probe_codetype.py 三链）',
          file=sys.stderr)
    _SB_CT = None
# 【v4.2】SOL 链上存在性黑名单：v4.1 清洗的 55 条跨链垃圾里有 21 条格式恰好合法
# （base58 解码恰 32B）、纯靠 getSignaturesForAddress 从无签名定罪——norm_addr 拦不住，
# 此前删除只做在现库 → 全量重建即复活（v4.2 干跑实测抓出）。审计档从此进构建流。
_SOL_NEVER = set()
if os.path.exists('sol_cex_cleanup_20260717.json'):
    _SOL_NEVER = set(json.load(open('sol_cex_cleanup_20260717.json')).get('never', []))
else:
    print('!! sol_cex_cleanup_20260717.json 缺失：SOL spellbook 垃圾黑名单未生效（21 条从未上链的假地址会复活）',
          file=sys.stderr)
if os.path.exists('spellbook_parsed.csv'):
    n = n_skip = n_never = 0
    for r in csv.DictReader(open('spellbook_parsed.csv')):
        cat = r['category']
        ch = r['chain']
        if ch == 'sol' and r['address'] in _SOL_NEVER:
            n_never += 1
            continue    # 链上从无签名的跨链垃圾（v4.1 清洗审计档）
        if (_SB_CT and cat == 'cex' and r['source'] == 'spellbook-cex-evms' and ch in _SB_CT
                and _SB_CT[ch].get(r['address'].lower()) == 'eoa'
                and any(_SB_CT[o].get(r['address'].lower()) == 'contract'
                        for o in _SB_CT if o != ch)):
            n_skip += 1
            continue    # 合约的跨链空投影，不入该链
        tier = 'exclude' if cat in ('cex', 'bridge') else 'identity'  # fund=识别级
        upsert(ch, r['address'], r['name'], cat, tier, r['source'], r['added_date'])
        n += 1
    print(f'spellbook merged: {n}（合约跨链投影 skip {n_skip}；SOL 链上不存在黑名单 skip {n_never}）')

# ---------- 2) dawsbot accounts.csv ----------
n = 0
for r in csv.DictReader(open('accounts.csv')):
    chain = CHAIN_BY_ID.get(r['chainId'])
    if not chain: continue
    m = map_label(r['label'])
    if m is None: continue
    cat, tier = m
    name = r['nameTag'] if r['nameTag'] not in ('null', '') else r['label']
    upsert(chain, r['address'], name, cat, tier, 'dawsbot', '', raw_label=r['label'])
    n += 1
print('dawsbot merged:', n)

# ---------- 3) dawsbot tokens.csv（代币合约） ----------
n = 0
for r in csv.DictReader(open('tokens.csv')):
    chain = CHAIN_BY_ID.get(r['chainId'])
    if not chain: continue
    nm = r['name'] or r['label']
    if r.get('symbol'): nm = f"{nm} ({r['symbol']})"
    upsert(chain, r['address'], nm, 'token-contract', 'exclude', 'tokens', '')
    n += 1
print('tokens merged:', n)

# ---------- 4) brianleect（2023 快照补充） ----------
for fn, chain in [('brianleect_eth.json', 'eth'), ('brianleect_bsc.json', 'bsc')]:
    if not os.path.exists(fn): continue
    d = json.load(open(fn))
    n = 0
    for addr, info in d.items():
        labels = info.get('labels') or []
        mapped = [m for m in (map_label(l) for l in labels) if m]
        if not mapped: continue
        # risk 标签独立成 flags，功能标签取 exclude > identity（codex 复核修正）
        risks = [c for c, t in mapped if t == 'risk']
        funcs = sorted([m for m in mapped if m[1] != 'risk'], key=lambda x: {'exclude': 0, 'identity': 1}[x[1]])
        if funcs:
            cat, tier = funcs[0]
        else:
            cat, tier = 'risk', 'risk'
        upsert(chain, addr, info.get('name') or labels[0], cat, tier, 'brianleect', '2023-10',
               risk_flag='|'.join(risks), raw_label=labels)
        n += 1
    print(fn, 'merged:', n)

# ---------- 5) GMGN KOL/聪明钱 ----------
if os.path.exists('gmgn_wallets.jsonl'):
    n = 0
    for line in open('gmgn_wallets.jsonl'):
        r = json.loads(line)
        tags = r.get('tags') or []
        if 'kol' in tags: cat = 'kol'
        elif any(t in tags for t in ('smart_degen', 'renowned', 'smart_money')): cat = 'smart-money'
        elif 'kol' in (r.get('kinds') or []): cat = 'kol'
        else: cat = 'smart-money'
        tw = r.get('twitter_username') or ''
        nm = r.get('twitter_name') or r.get('name') or ''
        disp = f"{nm} (@{tw})" if tw else nm
        extra = ','.join(t for t in tags if t not in ('gmgn',))
        if extra: disp = f"{disp} [{extra}]" if disp else f"[{extra}]"
        upsert(r['chain'], r['address'], disp, cat, 'identity', 'gmgn',
               date='2026-07-16', evidence=f"gmgn tags:{','.join(tags)}")
        n += 1
    print('gmgn merged:', n)

# ---------- 5b) SOL 程序（RPC executable 核验 + 名称交叉核验） ----------
SOL_NAME_FIX = {
    'PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu': ('Jupiter Perpetuals', 'program'),
    'Eo7WjKq67rjJQSZxS6z3YkapzY3eMj6Xy8X5EQVn5UaB': ('Meteora Dynamic AMM v1 (DAMM)', 'program'),
}
if os.path.exists('sol_programs_verified.json'):
    n = 0
    for p in json.load(open('sol_programs_verified.json')):
        nm, cat = SOL_NAME_FIX.get(p['address'], (p['name'], p['category']))
        upsert('sol', p['address'], nm, cat, 'exclude', 'solprog',
               date='2026-07-16', evidence='RPC executable 核验+vanity/官方文档')
        n += 1
    print('sol programs merged:', n)

# ---------- 5c) Jupiter 官方 program-id-to-label（97 个 DEX/协议程序） ----------
if os.path.exists('jup_labels.json'):
    n = 0
    for pid, label in json.load(open('jup_labels.json')).items():
        upsert('sol', pid, label, 'program', 'exclude', 'jup-official',
               date='2026-07-16', evidence='Jupiter swap API program-id-to-label')
        n += 1
    print('jupiter labels merged:', n)

# ---------- 5d) kolscan KOL 钱包 ----------
if os.path.exists('kolscan_wallets.json'):
    n = 0
    for k in json.load(open('kolscan_wallets.json')):
        # 修复 unicode_escape 二次解码的 UTF-8 乱码
        try:
            nm = k['name'].encode('latin-1', errors='ignore').decode('utf-8', errors='ignore').strip()
        except Exception:
            nm = k['name']
        tw = (k.get('twitter') or '').replace('https://x.com/', '@').replace('https://twitter.com/', '@')
        disp = f'{nm} ({tw})' if tw else nm
        upsert('sol', k['address'], disp, 'kol', 'identity', 'kolscan',
               date='2026-07-16', evidence='kolscan.io 公开 KOL 榜')
        n += 1
    print('kolscan merged:', n)

# ---------- 6) 手工核验表（manual_labels.csv，v4.2 起 15 列全量透传） ----------
if os.path.exists('manual_labels.csv'):
    n = 0
    for r in csv.DictReader(open('manual_labels.csv')):
        upsert(r['chain'], r['address'], r['name'], r['category'], r['tier'],
               'manual-' + (r.get('source') or 'verified'), r.get('added_date', ''), r.get('evidence', ''),
               risk_flag=r.get('risk_flags', ''), verified_at=r.get('verified_at', ''),
               status=r.get('status', ''),
               merge_policy=r.get('merge_policy', ''), balance_policy=r.get('balance_policy', ''))
        n += 1
    print('manual merged:', n)

# ---------- 7) OFAC SDN 制裁地址（分资产精确导入；v4 EOA 分流，codex 第二轮复核修正） ----------
# 上游按资产分表（lists 分支）。v4 起 ETH 表不再无条件注入三 EVM 链：
# 读 ofac_eth_codetype.json（{addr: 'eoa'|'contract'}，scripts/labels/probe_codetype.py 生成）——
# EOA 才跨链注入（同私钥跨链同控成立）；合约只入 eth（Tornado 等合约在他链地址不同）。
# codetype 文件缺失 → 保守只入 eth+专表并告警，不违反"跨链同址只提示"纪律。
# 刷新: curl -sL -x $PROXY -o ofac_<asset>.txt \
#   https://raw.githubusercontent.com/0xB10C/ofac-sanctioned-digital-currency-addresses/lists/sanctioned_addresses_<ASSET>.txt
OFAC_CODETYPE = _load_codetype('ofac_eth_codetype.json')   # _load_codetype 定义已提前至 spellbook 段前
if OFAC_CODETYPE is None:
    print('!! ofac_eth_codetype.json 缺失：OFAC ETH 表只入 eth 不跨链注入（先跑 probe_codetype.py）', file=sys.stderr)
OFAC_FILES = [('ofac_eth.txt', 'eth'), ('ofac_bsc.txt', 'bsc'), ('ofac_sol.txt', 'sol')]
for fn, home_chain in OFAC_FILES:
    if not os.path.exists(fn): continue
    n = 0
    for line in open(fn):
        addr = line.strip()
        if not addr: continue
        chains = (home_chain,)
        note = f'{home_chain.upper()} 资产专表'
        if fn == 'ofac_eth.txt' and OFAC_CODETYPE and OFAC_CODETYPE.get(addr.lower()) == 'eoa':
            chains = ('eth', 'bsc', 'base')
            note = 'ETH 资产表 EOA（getCode 亲验空码，同私钥跨链同控 → 三链注入）'
        for ch in chains:
            upsert(ch, addr, 'OFAC SDN 制裁地址', 'risk', 'risk', 'manual-ofac',
                   date='2026-07-16', evidence=f'0xB10C/ofac-sanctioned…（OFAC SDN 每日同步 lists 分支；{note}）',
                   risk_flag='ofac-sdn')
        n += 1
    print(f'ofac {fn} merged:', n)

# ---------- 7b) ScamSniffer 社区黑名单（候选降权层，不作定性；v4 EOA 分流同 OFAC） ----------
# 刷新: curl -sL -x $PROXY -o scamsniffer_address.json \
#   https://raw.githubusercontent.com/scamsniffer/scam-database/main/blacklist/address.json
if os.path.exists('scamsniffer_address.json'):
    SS_CODETYPE = _load_codetype('scamsniffer_codetype.json')
    if SS_CODETYPE is None:
        print('!! scamsniffer_codetype.json 缺失：ScamSniffer 只入 eth 不跨链注入（先跑 probe_codetype.py）', file=sys.stderr)
    n = 0
    for addr in json.load(open('scamsniffer_address.json')):
        chains = ('eth', 'bsc', 'base') if (SS_CODETYPE and SS_CODETYPE.get(addr.lower()) == 'eoa') else ('eth',)
        for ch in chains:
            upsert(ch, addr, 'ScamSniffer 社区举报地址（drainer/钓鱼候选）', 'scam-candidate', 'identity',
                   'scamsniffer', date='2026-07-16',
                   evidence='scamsniffer/scam-database 开源黑名单（社区上报候选，延迟约 7 天，不作单源定性）'
                            + ('；EOA getCode 亲验 → 跨链注入' if len(chains) == 3 else ''),
                   risk_flag='scam-candidate')
        n += 1
    print('scamsniffer merged:', n)

# ---------- 6b) 官方 deployment registry 层（v4 新增：协议官方仓库/npm 包/官方 docs 亲验的
#              工厂/router/locker 部署表；Base 补录 2026-07-17 首建，Aerodrome/Clanker/Zora/
#              Uniswap V4/Virtuals；增量走 add_labels.py，本文件保证重建不丢） ----------
# 6c) 链上亲验补录（tornado_bsc_contracts.csv 等 manual-chainverify 层）
# 6d) 【v4.2】sources/additions/ 目录整目录进重建流：add_labels.py 增量入库过的每份补录 CSV
#     都归档于此（入库脚本自动归档）。此前 v4.1 的 7 份增量文件不在重建源里——全量重建会
#     静默丢掉全部增量（codex 第四轮复核抓出的最大 round-trip 断环）。约定：进过现库的
#     additions 文件永不删除；重建即全量回放。
import glob as _glob
_EXTRA_SOURCES = ['official_registry.csv', 'tornado_bsc_contracts.csv', 'gmgn_additions.csv']
_ADDITION_FILES = sorted(_glob.glob('additions/*.csv'))
if not _ADDITION_FILES:
    print('!! sources/additions/ 目录为空——历史增量补录（桥/router/locker/SOL CEX 等）'
          '本轮重建不含，产物将比现库缺百余条 registry 级设施标签', file=sys.stderr)
for _fn in _EXTRA_SOURCES + _ADDITION_FILES:
    if not os.path.exists(_fn):
        print(f'!! {_fn} 缺失——对应层本轮重建不含其数据，勿 cp 覆盖现库',
              file=sys.stderr)
        continue
    n = 0
    for r in csv.DictReader(open(_fn)):
        if r.get('chain') not in BUILD_CHAINS:
            continue
        _rawl = [x for x in (r.get('raw_labels') or '').split('|') if x]
        upsert(r['chain'], r['address'], r['name'], r['category'], r['tier'],
               r['source'], r.get('added_date', ''), r.get('evidence', ''),
               risk_flag=r.get('risk_flags', ''), verified_at=r.get('verified_at', ''),
               status=r.get('status', ''), raw_label=_rawl or None,
               merge_policy=r.get('merge_policy', ''), balance_policy=r.get('balance_policy', ''))
        n += 1
    print(f'{_fn} merged:', n)

# ---------- 7c) 惯犯庄家层（serial-actor；accumulate_offenders.py 产出，v4 新增） ----------
# 历史案标记收割集团地址（案内定性、多数案源未经复核，线索级）：不剔除、不禁边，命中即高亮"XX 案标记惯犯"
if os.path.exists('serial_actors.csv'):
    n = 0
    for r in csv.DictReader(open('serial_actors.csv')):
        upsert(r['chain'], r['address'], r['name'], 'serial-actor', 'identity',
               'serial-offenders', date=r.get('added_date', ''), evidence=r['evidence'],
               risk_flag='serial-offender', verified_at=r.get('verified_at', ''))
        n += 1
    print('serial actors merged:', n)

# ---------- 8) Jito tip accounts（SOL "共同下游"假信号源） ----------
JITO_TIPS = ['ADuUkR4vqLUMWXxW9gh6D6L8pMSawimctcNZ5pGwDcEt', 'HFqU5x63VTqvQss8hp11i4wVV8bD44PvwucfZ2bU7gRe',
             'DfXygSm4jCyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh', 'ADaUMid9yfUytqMBgopwjb2DTLSokTSzL1zt6iGPaS49',
             '96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5', '3AVi9Tg9Uo68tJfuvoKvqKNWKkC5wPdSSdeBnizKZ6jT',
             'Cw8CFyM9FkoMi7K7Crf6HNQqf4uEMzpKw6QNghXLvLkY', 'DttWaMuVvTiduZRnguLF7jNxTgiMBZ1hyAumKUiL2KRL']
for t in JITO_TIPS:
    upsert('sol', t, 'Jito tip account（付小费公共账户，"共同下游"不构成关联）', 'infra', 'exclude',
           'manual-jito', date='2026-07-16', evidence='Jito getTipAccounts 实拉 2026-07-16')
print('jito tips merged:', len(JITO_TIPS))

# ---------- 9) Robinhood Chain 官方合约（docs.robinhood.com 抓取 2026-07-16） ----------
RH_L2 = [
    ('0x1e324b9316138ca9a73f960213621ad1aaf01b89', 'Robinhood 官方桥 L2 Gateway Router', 'bridge'),
    ('0xfd9b17206278c16ddaacf6ac8f05dbf97edcb31e', 'Robinhood 官方桥 L2 ERC20 Gateway', 'bridge'),
    ('0x912285144fc0f6e89d3ed16f5ab72f87a1878959', 'Robinhood 官方桥 L2 Arb-Custom Gateway', 'bridge'),
    ('0x1d187c3e2da52d72bc9c41e3aba0fdfa6a7bf055', 'Robinhood 官方桥 L2 Weth Gateway', 'bridge'),
    ('0xa3acd31afb851b4eb9dad00f5204c01d924267df', 'Robinhood L2 Proxy Admin', 'infra'),
    ('0x2cac2d899ecc914d704feaae33ac1bf36277dad1', 'Robinhood L2 Multicall', 'infra'),
]
for addr, nm, cat in RH_L2:
    upsert('robinhood', addr, nm, cat, 'exclude', 'manual-rhdocs',
           date='2026-07-16', evidence='docs.robinhood.com/chain 官方合约页')
RH_PRECOMPILES = {
    '0x0000000000000000000000000000000000000064': 'ArbSys', '0x0000000000000000000000000000000000000065': 'ArbInfo',
    '0x0000000000000000000000000000000000000066': 'ArbAddressTable', '0x0000000000000000000000000000000000000068': 'ArbFunctionTable',
    '0x000000000000000000000000000000000000006b': 'ArbOwnerPublic', '0x000000000000000000000000000000000000006c': 'ArbGasInfo',
    '0x000000000000000000000000000000000000006d': 'ArbAggregator', '0x000000000000000000000000000000000000006e': 'ArbRetryableTx',
    '0x000000000000000000000000000000000000006f': 'ArbStatistics', '0x0000000000000000000000000000000000000070': 'ArbOwner',
    '0x0000000000000000000000000000000000000071': 'ArbWasm', '0x0000000000000000000000000000000000000072': 'ArbWasmCache',
    '0x00000000000000000000000000000000000000c8': 'NodeInterface',
}
for addr, nm in RH_PRECOMPILES.items():
    upsert('robinhood', addr, f'Arbitrum Orbit 预编译: {nm}', 'infra', 'exclude', 'manual-rhdocs',
           date='2026-07-16', evidence='docs.robinhood.com/chain 官方合约页')
RH_L1 = [
    ('0x23a19d23e89166adedbdcb432518ab01e4272d94', 'Robinhood Chain L1: Rollup', 'bridge'),
    ('0xbd0d173eeb87d57a09521c24388a12789f33ba96', 'Robinhood Chain L1: Sequencer Inbox', 'bridge'),
    ('0x1232813bdd40aa9d53066a880de78a4be70b90fd', 'Robinhood Chain L1: CoreProxyAdmin', 'bridge'),
    ('0x1a07cc4bd17e0118bdb54d70990d2158abad7a2d', 'Robinhood Chain L1: Delayed Inbox', 'bridge'),
    ('0xdf8755334ce7a73ccf6b581c02ea649ae3e864b3', 'Robinhood Chain L1: Bridge', 'bridge'),
    ('0xf0ce991ea4a0d2400a4ab49b20ae333f6dce3de9', 'Robinhood Chain L1: Outbox', 'bridge'),
    ('0x6a2e3a1e16fc29f27ce61429746d558d656975bb', 'Robinhood Chain L1: Gateway Router', 'bridge'),
    ('0x85001cc4867c5e1c22da4b79bb8852b9e2a06da0', 'Robinhood Chain L1: ERC20 Gateway', 'bridge'),
    ('0x9368eaebfe6e063c69dcf8126711a6997e0ecee1', 'Robinhood Chain L1: Arb-Custom Gateway', 'bridge'),
    ('0xf7e12b9614b509c747ab4423bc4acf923759cf1b', 'Robinhood Chain L1: Weth Gateway', 'bridge'),
    ('0x7cdcb0cc61f47b8dd8f47c5a29edadd84a1bdf5e', 'Robinhood Chain L1: Multicall', 'infra'),
]
for addr, nm, cat in RH_L1:
    upsert('eth', addr, nm, cat, 'exclude', 'manual-rhdocs',
           date='2026-07-16', evidence='docs.robinhood.com/chain 官方合约页（ETH 主网侧）')
# Permit2 canonical 全链同址
for ch in ('eth', 'bsc', 'base', 'robinhood'):
    upsert(ch, '0x000000000022d473030f116ddee9f6b43ac78ba3', 'Permit2（Uniswap canonical，全链同址）',
           'infra', 'exclude', 'manual-rhdocs', date='2026-07-16', evidence='canonical CREATE2 部署')
print('robinhood official contracts merged:', len(RH_L2) + len(RH_PRECOMPILES) + len(RH_L1) + 4)

# ---------- 10) Dune labels.addresses 精选模型（query 7999252，API 拉取 2026-07-16） ----------
DUNE_CHAIN = {'ethereum': 'eth', 'bnb': 'bsc', 'base': 'base', 'solana': 'sol'}
DUNE_MODEL_MAP = {
    # model_name: (category, tier, risk_flag)
    'cex_ethereum': ('cex', 'exclude', ''), 'cex_bnb': ('cex', 'exclude', ''),
    'bridges_ethereum': ('bridge', 'exclude', ''), 'bridges_bnb': ('bridge', 'exclude', ''),
    'bridges_base': ('bridge', 'exclude', ''), 'aztec_v2_contracts_ethereum': ('bridge', 'exclude', ''),
    'ofac_sanctionned': ('risk', 'risk', 'ofac-sdn'),
    'dao_multisig': ('dao-multisig', 'identity', ''), 'dao_framework': ('dao', 'identity', ''),
    'validators_solana': ('validator', 'identity', ''),
    'burn_addresses': ('burn', 'exclude', ''), 'system_addresses': ('infra', 'exclude', ''),
    'stablecoins': ('token-contract', 'exclude', ''), 'cex_tokens': ('token-contract', 'exclude', ''),
    'flashbots': ('flashbots-user', 'identity', ''),
    'sandwich_attackers': ('sandwich-bot', 'identity', ''),
    'smart_dex_traders': ('active-trader', 'identity', ''),
    'mev': ('mev', 'exclude', ''),
}
for m in ('balancer_v1_pools_ethereum', 'balancer_v2_pools_ethereum', 'balancer_v3_pools_ethereum',
          'balancer_v2_pools_base', 'balancer_v3_pools_base', 'balancer_gauges_ethereum',
          'balancer_gauges_base', 'balancer_cowswap_amm_pools_ethereum', 'balancer_cowswap_amm_pools_base'):
    DUNE_MODEL_MAP[m] = ('protocol', 'exclude', '')

B58A = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
def hex_to_b58(h):
    """Dune 把 solana pubkey 存成 varbinary hex；转回 base58（含前导零字节 → '1'）"""
    hs = h[2:] if h.startswith('0x') else h
    try:
        b = bytes.fromhex(hs)
    except ValueError:
        return None
    if len(b) != 32:
        return None
    n = int.from_bytes(b, 'big')
    out = ''
    while n:
        n, r = divmod(n, 58)
        out = B58A[r] + out
    pad = len(b) - len(b.lstrip(b'\x00'))
    return '1' * pad + (out or '')

DUNE_MODEL_MAP['tornado_cash'] = ('tornado-user', 'identity', 'tornado-user')

DUNE_FILES = [f for f in ('dune_labels_v2.csv', 'dune_tornado.csv') if os.path.exists(f)]
for dune_file in DUNE_FILES:
    n = 0; skipped = 0
    for r in csv.DictReader(open(dune_file)):
        mm = DUNE_MODEL_MAP.get(r['model_name'])
        chain = DUNE_CHAIN.get(r['blockchain'])
        if not mm or not chain:
            skipped += 1; continue
        cat, tier, rf = mm
        addr = r['address']
        if chain == 'sol':
            addr = hex_to_b58(addr)
            if addr is None:
                skipped += 1; continue
        nm = r['name'] or r['model_name']
        upsert(chain, addr, nm, cat, tier, 'dune-labels', date='2026-07-16',
               evidence=f"Dune labels.addresses model={r['model_name']}", risk_flag=rf,
               raw_label=r['model_name'])
        n += 1
    print(f'dune {dune_file} merged:', n, 'skipped:', skipped)

# ---------- 11) 输出前后处理（codex 复核融合 2026-07-16 v3） ----------
# a) 风险旗标分级剥离：
#    burn 地址是全网垃圾桶，任何 risk 旗标都是噪音（实测 0x0000/0xdead 曾被打上 tornado-user/blocked）；
#    exclude 基础设施剥离"行为型"旗标（tornado-user——谁都能经公共设施收发 Tornado 资金），
#    但保留"定性型"旗标（ofac-sdn/heist/exploit——被制裁的 CEX/桥要保留双重属性）。
KNOWN_BURN = {'0x0000000000000000000000000000000000000000',
              '0x000000000000000000000000000000000000dead',
              '0x0000000000000000000000000000000000000001'}
BEHAVIORAL_FLAGS = {'tornado-user'}
# b) locker 归一：锁仓合约（锁仓量是有经济含义的供应，识别不剔除——tier=identity，
#    聚类合并边禁用由 resolver 的 no_merge 负责）；排除 token-contract（UNCX 代币合约≠锁仓合约）
LOCKER_NAME_RE = re.compile(
    r'(pink ?lock|pinksale.{0,12}lock|unicrypt|uncx|team ?finance ?:|mudra.{0,10}lock|deep ?lock'
    r'|dx ?lock|dxsale.{0,12}lock|flokifi.{0,12}lock|trustswap.{0,12}lock|gempad.{0,12}lock'
    r'|token ?lock|liquidity ?lock|lp ?lock|vesting)', re.I)
TOKEN_NAME_RE = re.compile(r'\([A-Za-z0-9$]{1,14}\)\s*$')   # "Name (SYMBOL)" 代币命名格式，防代币误归 locker
n_strip, n_locker = 0, 0
for (chain, addr), row in book.items():
    if row['category'] == 'burn' or addr in KNOWN_BURN:
        if row['risk_flags']:
            row['risk_flags'] = ''; n_strip += 1
    elif row['tier'] == 'exclude' and row['risk_flags']:
        parsed = parse_risk_flags(row['risk_flags'])
        kept = [f for f in parsed if f not in BEHAVIORAL_FLAGS]
        if len(kept) != len(parsed):
            n_strip += 1
        row['risk_flags'] = canonical_risk_flags('|'.join(kept))
    else:
        row['risk_flags'] = canonical_risk_flags(row['risk_flags'])
    if (row['category'] not in ('token-contract', 'kol', 'smart-money', 'tornado-user', 'scam-candidate')
            and LOCKER_NAME_RE.search(row['name'] or '')
            and not TOKEN_NAME_RE.search(row['name'] or '')):
        row['category'] = 'locker'; row['tier'] = 'identity'; n_locker += 1
# d)【v4.2】AA 设施归一（codex 第四轮复核：Alchemy/Candide/Stackup 等 17 条 bundler/paymaster
#    因 dawsbot 用项目名当类目走长尾规则被判 identity，会合法参与聚类+gas 溯源——
#    bundler/paymaster 是"假共同金主"头号制造机，一律 infra/exclude）
AA_NAME_RE = re.compile(r'\b(bundler|paymaster|entry ?point)\b|erc-?4337', re.I)
# e)【v4.2】Seaport（NFT 结算，海量用户过手）名字归一——label 层缺口的兜底
SEAPORT_NAME_RE = re.compile(r'\bseaport\b', re.I)
# f)【v4.2】设施类目硬不变量：这些 category 语义上就是公共通道，tier=identity 即矛盾行
#    （Base "Banana Gun: Router" category=router tier=identity 实测会作合并边）
FACILITY_MUST_EXCLUDE = {'cex', 'bridge', 'router', 'mixer', 'bot-service'}
PROTECTED_CATS = ('token-contract', 'kol', 'smart-money', 'tornado-user', 'scam-candidate',
                  'serial-actor', 'validator')
n_aa = n_sea = n_fac = 0
for row in book.values():
    nm = row['name'] or ''
    if row['category'] not in PROTECTED_CATS:
        if AA_NAME_RE.search(nm):
            if row['tier'] != 'exclude' or row['category'] not in ('infra',):
                row['category'] = 'infra'; row['tier'] = 'exclude'; n_aa += 1
        elif SEAPORT_NAME_RE.search(nm) and row['tier'] != 'exclude':
            row['category'] = 'protocol'; row['tier'] = 'exclude'; n_sea += 1
    if row['category'] in FACILITY_MUST_EXCLUDE and row['tier'] == 'identity':
        row['tier'] = 'exclude'; n_fac += 1
print(f'后处理v4.2: AA归一 {n_aa} 行 | Seaport归一 {n_sea} 行 | 设施类目identity矛盾修正 {n_fac} 行')
# c) tier=risk 行的 evidence 兜底：dawsbot/brianleect 的 blocked/exploit/gambling 行证据即官方标签本身
n_ev = 0
for row in book.values():
    if row['tier'] == 'risk' and not (row['evidence'] or '').strip():
        row['evidence'] = 'Etherscan系官方标签快照（' + row['source'] + '）'
        n_ev += 1
print(f'后处理: 剥离噪音旗标 {n_strip} 行 | locker 归一 {n_locker} 行 | risk行补evidence {n_ev} 行')

# ---------- 输出分链 CSV（v4：扩展列 + 纯 tornado 行拆 privacy 子表） ----------
os.makedirs('out', exist_ok=True)
by_chain = {}
for (chain, addr), row in book.items():
    row['raw_labels'] = '|'.join(sorted(row.pop('_raw', set()) - {row['category']}))
    by_chain.setdefault(chain, []).append(row)
FIELDS = ['address', 'chain', 'name', 'category', 'tier', 'source', 'added_date', 'evidence',
          'risk_flags', 'merge_policy', 'balance_policy', 'source_snapshot_at',
          'verified_at', 'status', 'raw_labels']
for chain, rows in sorted(by_chain.items()):
    rows.sort(key=lambda r: (r['tier'], r['category'], r['address']))
    # 纯 tornado-user 行（category=tornado-user，无其他功能身份）拆到 privacy 子表：
    # 主表瘦身（29 万行体积层），resolver._load_csv 加载时自动合并，对使用方透明
    main_rows = [r for r in rows if r['category'] != 'tornado-user']
    priv_rows = [r for r in rows if r['category'] == 'tornado-user']
    with open(f'out/labels-{chain}.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction='ignore')
        w.writeheader(); w.writerows(main_rows)
    if priv_rows:
        with open(f'out/labels-{chain}-privacy.csv', 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction='ignore')
            w.writeheader(); w.writerows(priv_rows)
    tiers = Counter(r['tier'] for r in rows)
    nrisk = sum(1 for r in rows if r['risk_flags'])
    cats = Counter(r['category'] for r in rows)
    extra = f'（另 privacy 子表 {len(priv_rows)} 条）' if priv_rows else ''
    print(f"labels-{chain}.csv: {len(main_rows)} 条{extra} | tier: {dict(tiers)} | 带risk_flags: {nrisk} | top类目: {cats.most_common(8)}")

# ---------- 12) 构建后强制校验（不过即失败退出，禁止把坏库发布出去） ----------
import subprocess
_here = os.path.dirname(os.path.abspath(__file__))
rc = subprocess.run([sys.executable, os.path.join(_here, 'validate_labels.py'), 'out']).returncode
if rc != 0:
    print('!! 校验未通过，out/ 下产物不得拷贝到 references/labels/', file=sys.stderr)
    sys.exit(1)
# manual 层双份真源一致性（address-book.md vs gen_manual 硬编码；v4 新增，防手抄漂移）
rc2 = subprocess.run([sys.executable, os.path.join(_here, 'check_manual_sync.py')]).returncode
if rc2 != 0:
    print('!! manual 层与 address-book.md 不一致：先同步 gen_manual_from_addressbook.py 再重建', file=sys.stderr)
    sys.exit(1)
