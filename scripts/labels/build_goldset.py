#!/usr/bin/env python3
"""回归金标集构建器（P2 回归基准，codex 复核融合 2026-07-16）

从实战产物与受跟踪裁决真源抽取"地址→期望归类"金标：
  entity          历史分析确认的庄家/项目方/狙击集团地址（appendix.json 的 whale_groups /
                  addresses / monitoring_advice）——【库不得将其标为 exclude】，
                  错误 exclude = 聚类阶段直接漏庄，是最严重的库缺陷。
  infrastructure  实战核验的设施地址（appendix 中 role 含设施词的条目 + manual 层
                  tier=exclude 条目）——重建后必须仍命中 no_merge（防重建退化回归）。

用法：
  python3 build_goldset.py [分析根目录]     # 默认 ~/Desktop/老公用/fable筹码分析
产物：
  references/labels/benchmark/goldset.csv（chain,address,expected,note,source_analysis）

裁决真源：
  references/labels/benchmark/goldset_curated.csv
  自动抽样完成后按 (chain,address) 覆盖合并，保证人工裁决不被重抽样漂移冲掉。

纪律：role 语义不明的条目宁缺毋滥直接丢弃；entity/infrastructure 冲突的条目丢弃并警告。

v4 2026-07-17（codex 第二轮复核：金标失衡修复——Base entity 0 / ETH 1 不能承担门禁）：
  random-eoa      从历史分析的 transfers/swaps 数据抽"低频普通交易者"作负样本
                  （每链至多 60 条；确定性抽样=按 sha256(addr) 排序取前 N，重跑稳定）。
                  断言同 entity：不得被 exclude。低频过滤（出现 1-5 次）把误抽真设施的
                  概率压到极低——设施地址在单币数据里几乎必然高频。
  仍无数据的链（如 base 无历史分析）在 benchmark 侧显式输出【弱门禁】警告，不假装有防线。
"""
import csv, glob, hashlib, json, os, re, sys
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.expanduser('~/Desktop/老公用/fable筹码分析')
OUT_DIR = os.path.normpath(os.path.join(_HERE, '..', '..', 'references', 'labels', 'benchmark'))
CURATED_GOLDSET = os.path.join(OUT_DIR, 'goldset_curated.csv')
CHAIN_MAP = {'solana': 'sol', 'ethereum': 'eth', 'bnb': 'bsc', 'binance': 'bsc'}
SUPPORTED_CHAINS = frozenset(('eth', 'bsc', 'base', 'arbitrum', 'sol', 'robinhood'))

# 人工仲裁名单：appendix 金标与标签库冲突、经浏览器官方标签亲验裁决的条目（裁决优先于一切自动分类）
ARBITRATED = {
    # GME 报告曾判"L1金主（注资小庄#1钱包#6）"；etherscan 亲验=ChangeNOW 16 即时兑换热钱包
    # （Exchange 标签、287 万笔）——公共服务不构成关联证据，报告侧定性应降级（2026-07-16 基准首跑发现）
    ('eth', '0xeba88149813bec1cccccfdb0dacefaaa5de94cb1'):
        ('infrastructure', 'etherscan 官方标签亲验=ChangeNOW 16（2026-07-16）'),
}

# role/label 含这些词 → 实战核验的公共设施（appendix 侧的 infrastructure gold）
INFRA_KW = ('路由', '桥', '聚合器', '热钱包', '工厂', 'relayer', 'Relayer', '结算', '托管出金',
            '发射台', '锁仓合约', 'locker', '公共', '设施', '预编译', 'PoolManager', 'Router',
            'EntryPoint', 'bot 服务', 'bot服务', '出纳服务', '提款', 'CEX', '交易所')
# role 含这些词 → 庄家/项目方实体（entity gold）；两类词都含 → 冲突丢弃
ENTITY_KW = ('项目方', '庄', '马甲', '狙击', '金主', '工作室', '波段', '吸筹', '大户', '团队',
             '创始', 'dev', 'Dev', '回购', '基金会', '金库', '老鼠仓', '实体', '集团', '聚类',
             '集群', '家族', '收割')


def norm_chain(c):
    c = (c or '').strip().lower()
    return CHAIN_MAP.get(c, c)


def classify_role(text):
    t = text or ''
    infra = any(k in t for k in INFRA_KW)
    entity = any(k in t for k in ENTITY_KW)
    if infra and entity:
        return 'conflict'
    if infra:
        return 'infrastructure'
    if entity:
        return 'entity'
    return None            # 语义不明，不入 gold


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ROOT
    gold = {}      # (chain, address) -> dict
    conflicts, dropped = [], 0

    def put(chain, addr, expected, note, src):
        nonlocal dropped
        chain = norm_chain(chain)
        if isinstance(addr, list):     # monitoring_advice.watch 可能是地址数组
            for a in addr:
                put(chain, a, expected, note, src)
            return
        if isinstance(addr, dict):     # 部分新版 appendix 的 addresses 是对象列表
            addr = addr.get('address') or addr.get('addr') or ''
        if not isinstance(addr, str):
            dropped += 1
            return
        addr = (addr or '').strip()
        if chain not in ('eth', 'bsc', 'base', 'arbitrum', 'sol', 'robinhood') or not addr:
            dropped += 1
            return
        if chain != 'sol':
            addr = addr.lower()
            if not re.fullmatch(r'0x[0-9a-f]{40}', addr):
                dropped += 1
                return
        key = (chain, addr)
        if key in ARBITRATED:
            expected, note = ARBITRATED[key]
            src = src + '+arbitrated'
        old = gold.get(key)
        if old and old['expected'] != expected:
            conflicts.append((key, old['expected'], expected, note))
            gold.pop(key)            # 冲突条目整体丢弃（错误 exclude 断言不容含糊样本）
            return
        if not old:
            gold[key] = {'chain': chain, 'address': addr, 'expected': expected,
                         'note': (note or '')[:120], 'source_analysis': src}

    # ---- 1) 历史分析 appendix.json ----
    apps = sorted(glob.glob(os.path.join(root, '*', 'appendix.json')))
    for path in apps:
        src = os.path.basename(os.path.dirname(path))
        try:
            d = json.load(open(path))
        except Exception as e:
            print(f'skip {src}: {e}')
            continue
        default_chain = norm_chain((d.get('token') or {}).get('chain'))
        for g in d.get('whale_groups') or []:
            note = f"{g.get('label', '')}({g.get('tier', '')})"
            cls = classify_role(g.get('label') or '') or 'entity'   # whale_groups 默认实体
            if cls == 'conflict':
                cls = 'entity'
            for a in g.get('addresses') or []:
                put(default_chain, a, cls, note, src)
        for row in d.get('addresses') or []:
            cls = classify_role(row.get('role') or '')
            if cls in ('entity', 'infrastructure'):
                put(row.get('chain') or default_chain, row.get('address'), cls, row.get('role'), src)
        for m in d.get('monitoring_advice') or []:
            cls = classify_role(m.get('label') or '')
            if cls in ('entity', 'infrastructure'):
                put(default_chain, m.get('watch'), cls, m.get('label'), src)

    # ---- 2) manual 层 tier=exclude（防重建退化的回归样本） ----
    manual = os.path.join(_HERE, 'sources', 'manual_labels.csv')
    if os.path.exists(manual):
        for r in csv.DictReader(open(manual)):
            if r['tier'] == 'exclude':
                put(r['chain'], r['address'], 'infrastructure', r['name'], 'manual-layer')

    # ---- 2b) manual/registry 级补录源也进金标。----
    # 覆盖 policy 断言：merge_policy=no_merge 的覆盖行入金标后，
    # 全量重建若丢 policy → no_merge 退化为 allow → benchmark 立刻 FAIL（round-trip 活体断言）。
    PER_SRC_CAP = 40
    extra_srcs = sorted(glob.glob(os.path.join(_HERE, 'sources', 'additions', '*.csv')))
    extra_srcs += [os.path.join(_HERE, 'sources', f) for f in
                   ('official_registry.csv', 'tornado_bsc_contracts.csv')]
    n_extra = 0
    for fn in extra_srcs:
        if not os.path.exists(fn):
            continue
        rows_f = [r for r in csv.DictReader(open(fn))
                  if r.get('source', '').split('-')[0].split('+')[0] in
                     ('manual', 'registry', 'official', 'addressbook')]
        picked = [r for r in rows_f if r.get('tier') == 'exclude'
                  or (r.get('merge_policy') or '').strip() == 'no_merge']
        picked.sort(key=lambda r: hashlib.sha256(r['address'].encode()).hexdigest())
        for r in picked[:PER_SRC_CAP]:
            before = len(gold)
            put(r['chain'], r['address'], 'infrastructure',
                (r.get('name') or '') + ('（policy覆盖断言）' if (r.get('merge_policy') or '').strip() == 'no_merge'
                                          and r.get('tier') != 'exclude' else ''),
                'manual-layer')
            if len(gold) > before:
                n_extra += 1
    print(f'补录源设施金标（additions/registry，每源上限 {PER_SRC_CAP}）: {n_extra} 条')

    # ---- 3) random-eoa 负样本（v4：从历史 transfers/swaps 抽低频普通交易者） ----
    # 目的：给 entity 金标稀少的链补"不得 exclude"断言的地面真值。确定性抽样保证重跑稳定。
    PER_CHAIN_CAP = 60
    freq = {}          # chain -> Counter(addr)
    data_files = []
    for pat in ('*/data/*transfer*.csv', '*/data/*swap*.csv', '*/*transfers*.csv', '*/*swaps*.csv',
                '*/*_part_*.csv'):        # part 文件 = HyperSync 拉的 headerless 6 列转账
        data_files += glob.glob(os.path.join(root, pat))
    for path in sorted(set(data_files))[:120]:          # 上限防失控
        # 从同目录 appendix.json 或路径猜链；猜不到跳过（宁缺毋滥）
        chain = None
        appx = os.path.join(os.path.dirname(path.replace('/data/', '/')), 'appendix.json')
        cand = glob.glob(os.path.join(os.path.dirname(path), 'appendix.json')) or \
               glob.glob(os.path.join(os.path.dirname(os.path.dirname(path)), 'appendix.json'))
        if cand:
            try:
                chain = norm_chain((json.load(open(cand[0])).get('token') or {}).get('chain'))
            except Exception:
                chain = None
        if chain not in ('eth', 'bsc', 'base', 'arbitrum', 'sol', 'robinhood'):
            continue
        cnt = freq.setdefault(chain, Counter())
        try:
            if '_part_' in os.path.basename(path):
                # headerless 6 列（block,txhash,logidx,from,to,value）——scan_transfers 产物
                with open(path, newline='') as f:
                    for i, line in enumerate(f):
                        if i > 400000:
                            break
                        parts = line.strip().split(',')
                        if len(parts) == 6 and parts[0] != 'block':
                            cnt[parts[3].strip()] += 1
                            cnt[parts[4].strip()] += 1
                continue
            with open(path, newline='') as f:
                rd = csv.DictReader(f)
                cols = [c for c in (rd.fieldnames or [])
                        if c and c.lower() in ('from', 'to', 'from_address', 'to_address',
                                               'sender', 'recipient', 'owner', 'trader', 'wallet')]
                if not cols:
                    continue
                for i, row in enumerate(rd):
                    if i > 400000:
                        break
                    for c in cols:
                        a = (row.get(c) or '').strip()
                        if a:
                            cnt[a] += 1
        except Exception:
            continue
    n_rand = 0
    for chain, cnt in freq.items():
        low = [a for a, n in cnt.items() if 1 <= n <= 5]
        low.sort(key=lambda a: hashlib.sha256(a.encode()).hexdigest())   # 确定性伪随机
        picked = 0
        for a in low:
            if picked >= PER_CHAIN_CAP:
                break
            key = (chain, a if chain == 'sol' else a.lower())
            if key in gold or key in ARBITRATED:
                continue
            before = len(gold)
            put(chain, a, 'random-eoa', '低频普通交易者负样本（1-5 次出现）', 'random-sample')
            if len(gold) > before:
                picked += 1
                n_rand += 1
    print(f'random-eoa 负样本: {n_rand} 条（低频过滤 1-5 次，sha256 确定性抽样）')

    # ---- 4) 裁决金标真源（优先于全部自动分类与重抽样） ----
    # 该文件保存已经独立复核的人工裁决；不得从一次性交接目录或历史分析根隐式恢复。
    required = {'chain', 'address', 'expected', 'note', 'source_analysis'}
    if not os.path.isfile(CURATED_GOLDSET):
        raise FileNotFoundError(f'裁决金标真源缺失: {CURATED_GOLDSET}')
    curated_seen = set()
    with open(CURATED_GOLDSET, newline='', encoding='utf-8') as f:
        rd = csv.DictReader(f)
        missing_fields = required - set(rd.fieldnames or [])
        if missing_fields:
            raise ValueError(f'裁决金标缺字段: {sorted(missing_fields)}')
        for lineno, r in enumerate(rd, 2):
            chain = norm_chain(r.get('chain'))
            addr = (r.get('address') or '').strip()
            if chain != 'sol':
                addr = addr.lower()
            expected = (r.get('expected') or '').strip()
            if chain not in SUPPORTED_CHAINS:
                raise ValueError(f'裁决金标第 {lineno} 行链无效: {chain!r}')
            if chain != 'sol' and not re.fullmatch(r'0x[0-9a-f]{40}', addr):
                raise ValueError(f'裁决金标第 {lineno} 行地址无效: {addr!r}')
            if expected not in ('entity', 'infrastructure', 'random-eoa'):
                raise ValueError(f'裁决金标第 {lineno} 行 expected 无效: {expected!r}')
            key = (chain, addr)
            if key in curated_seen:
                raise ValueError(f'裁决金标重复键: {key}')
            curated_seen.add(key)
            gold[key] = {
                'chain': chain,
                'address': addr,
                'expected': expected,
                'note': (r.get('note') or '').strip(),
                'source_analysis': (r.get('source_analysis') or '').strip(),
            }
    print(f'裁决金标覆盖合并: {len(curated_seen)} 条（真源={CURATED_GOLDSET}）')

    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, 'goldset.csv')
    rows = sorted(gold.values(), key=lambda r: (r['chain'], r['expected'], r['address']))
    with open(out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['chain', 'address', 'expected', 'note', 'source_analysis'],
                           lineterminator='\n')
        w.writeheader(); w.writerows(rows)

    cc = Counter((r['chain'], r['expected']) for r in rows)
    print(f'goldset.csv: {len(rows)} 条（扫 {len(apps)} 份 appendix；丢弃格式不符 {dropped}）')
    for (ch, ex), n in sorted(cc.items()):
        print(f'  {ch:10s} {ex:14s} {n}')
    if conflicts:
        print(f'!! {len(conflicts)} 条 entity/infrastructure 冲突已丢弃（人工复核）:')
        for (key, a, b, note) in conflicts[:10]:
            print(f'   {key} {a} vs {b} | {note[:60]}')


if __name__ == '__main__':
    main()
