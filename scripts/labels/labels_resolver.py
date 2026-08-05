#!/usr/bin/env python3
"""共享标签解析器（label_lookup CLI、cluster.py、analyze_holdings.py、SOL 管线共用内核）
v4 2026-07-16（codex 交叉复核第二轮融合：policy 三维拆分 / risk 白名单制 / 新链 / privacy 子表 / serial 层 / degraded_mode）。

纪律（与 references/labels/README.md 对齐）：
1. 自动决策只认【目标链直接命中】；EVM 跨链同址（对 eth 表 fallback）只作提示
   （cross_chain=True），绝不据此自动剔除——BSC/Base 与 eth 表 5,100 个同址中已实测存在
   分类冲突，普通合约同址≠同实体。
2. exclude ≠ 从数据中删除：仅禁止作聚类合并边、不计入实体持仓/大户榜；
   "经 XX 桥入金"的资金路径叙事保留，它们是边界节点不是空气。
3. 风险旗标分区【白名单制】（v4 起，修复"未知旗标一律 definitive"的休眠炸弹）：
   definitive（白名单精确命中或 *-exploit 后缀）——大户命中=必写进报告；
   candidate（scam-candidate…社区单源候选）——降权提示，不作定性；
   privacy（tornado-user）——只陈述"有 Tornado 使用记录"，不定性"脏钱"；
   unknown（白名单外的一切旗标）——提示"未识别旗标，人工核验后归档"，不自动当定性。
4. 决策三维（v4 起，替代"tier 单字段身兼多职"）：
   merge_policy   allow | no_merge          —— 能否作聚类合并边
   balance_policy count | bucket | exclude  —— 实体持仓怎么算（bucket=单列桶，如锁仓量）
   风险分区独立于上述两维（risk_partition）。
   推导规则见 derive_policy()；CSV 可选列 merge_policy/balance_policy 存在且非空时覆盖推导。
5. locker / airdrop-distributor / token-sale / charity 等公共多对一·一对多通道：
   不剔除（其持仓可能有经济含义→bucket 或 count），但禁止作聚类合并边——
   多项目锁同一 locker、多人打款同一 ICO/慈善地址、一工具分发万人，合并全是假连。
6. serial-actor（惯犯庄家层，v4 新增）：历史案标记的收割集团地址（案内定性、
   多数案源未经用户复核，消费按线索级——见 labels/README serial-actor 段）。
   不剔除、不禁边（惯犯地址间本就是同实体，正常聚类），命中即高亮"XX 案标记惯犯"。
7. 标签时效（3.18.0，提示不定罪）：get() 附 stale_days（距最近核验/快照/入库天数）；
   时效敏感类目（CEX 热钱包/bundler 等会轮换的设施）超 STALE_DAYS 只提示"须复核"，
   **自动决策不因库龄变老而失效**（若过期即失效，建库 N 月后设施剔除会整体瓦解=更大事故）；
   status ∈ INACTIVE_STATUS（人工显式标记 deprecated/rotated/historical/stale）的行按
   **语义切分**处理：余额侧回退（is_exclude=False、balance_policy=count——退役设施的
   "当前持仓"不再自动剔）；聚类禁边**保留**（no_merge 不放开——重放全历史时退役桥/轮换
   热钱包在其活跃期的边依然是公共边，放开=聚类污染回归）。
"""
import csv, datetime, os, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LABELS_DIR = os.path.normpath(os.path.join(_HERE, '..', '..', 'references', 'labels'))

LABELS_SCHEMA_VERSION = 4
# known 包含可探索链；正式发布集合由 report/audit_release_gate.py 的 FORMAL_CHAINS 裁决。
KNOWN_CHAINS = ('eth', 'base', 'bsc', 'arbitrum', 'sol', 'robinhood')

# 基础 9 列（v3）+ v4 可选列（旧行空值合法，resolver 对空值走推导）
BASE_FIELDS = ['address', 'chain', 'name', 'category', 'tier', 'source',
               'added_date', 'evidence', 'risk_flags']
V4_OPTIONAL_FIELDS = ['merge_policy', 'balance_policy',
                      'source_snapshot_at', 'verified_at', 'status', 'raw_labels']

# ---- 风险旗标白名单（v4：只有名单内才 definitive；模式规则见 _classify_flag） ----
DEFINITIVE_RISK = {'ofac-sdn', 'ofac-sanctions-lists', 'ofac-sanctioned', 'sanctioned',
                   'heist', 'exploit', 'exploiter', 'phish-hack', 'scam', 'blocked',
                   'gambling', 'mixer', 'ponzi', 'lazarus-group', 'plustoken',
                   'tornado-cash', 'serial-offender'}
DEFINITIVE_SUFFIXES = ('-exploit',)       # filament-exploit / bybit-exploit… Dune/Etherscan 惯例族
CANDIDATE_RISK = {'scam-candidate', 'risk-candidate'}
PRIVACY_FLAGS = {'tornado-user'}

# identity 层但禁止作聚类合并边的公共通道类目（纪律 5）
# v4.2 +launchpad（平台署名 creator/平台金库等 identity 级发射台地址，与用户的边全是公共
# 通道边——Bags creator/Believe Token Authority 若可合并会把全平台买家缝成一个实体）
# +suspected-cex（未确证设施：禁边不剔仓，确证后才升 cex/exclude）
NO_MERGE_CATEGORIES = {'locker', 'airdrop-distributor', 'token-sale', 'charity',
                       'launchpad', 'suspected-cex'}
# identity 层持仓单列桶（不混入实体持仓，也不无视）的类目
BUCKET_CATEGORIES = {'locker', 'airdrop-distributor', 'launchpad'}
SERIAL_CATEGORY = 'serial-actor'

# ---- 标签时效（3.18.0）----
STALE_DAYS = 90
# 会轮换/迁移的设施类目：过期命中要提示复核（CEX 热钱包轮换、bundler EOA 轮换实测都有）
TIME_SENSITIVE_CATEGORIES = {'cex', 'suspected-cex', 'infra', 'bridge', 'bundler',
                             'paymaster', 'mev'}
# 人工显式标记的失效状态：自动决策回退保守值（历史标签只提示不驱动决策）
INACTIVE_STATUS = {'deprecated', 'rotated', 'historical', 'stale'}


def staleness(row, today=None):
    """距最近一次 verified_at/source_snapshot_at/added_date 的天数；三列都解析不出返回 None。"""
    best = None
    for k in ('verified_at', 'source_snapshot_at', 'added_date'):
        v = (row.get(k) or '').strip()[:10]
        try:
            d = datetime.date.fromisoformat(v)
        except ValueError:
            continue
        if best is None or d > best:
            best = d
    if best is None:
        return None
    return ((today or datetime.date.today()) - best).days

_B58 = set('123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz')
_B58_ALPHA = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'


def _b58_bytelen(s):
    """base58 字符串解码后的字节长度（前导 '1' = 前导零字节）"""
    n = 0
    for c in s:
        n = n * 58 + _B58_ALPHA.index(c)
    return (n.bit_length() + 7) // 8 + (len(s) - len(s.lstrip('1')))
_MERGE_VALUES = {'allow', 'no_merge'}
_BALANCE_VALUES = {'count', 'bucket', 'exclude'}


def norm_addr(addr, chain):
    """规范化地址；不合法返回 None。EVM 一律小写 0x40；SOL base58。"""
    a = (addr or '').strip().strip('"').strip("'")
    if not a:
        return None
    if chain == 'sol':
        # v4.1：字符集+长度不够——BTC bech32/Cardano 切片/hex 串恰好都能过（spellbook 曾混入 55 条
        # 跨链垃圾）。合法 SOL 地址 = base58 解码恰好 32 字节（ed25519 公钥）。
        if not (32 <= len(a) <= 44 and set(a) <= _B58):
            return None
        return a if _b58_bytelen(a) == 32 else None
    a = a.lower()
    return a if (a.startswith('0x') and len(a) == 42
                 and all(c in '0123456789abcdef' for c in a[2:])) else None


def _read_rows(path):
    if not os.path.exists(path):
        return []
    with open(path, newline='') as f:
        return list(csv.DictReader(f))


def _load_csv(labels_dir, chain):
    """主表 + privacy 子表（labels-<chain>-privacy.csv，v4 拆分 tornado-user 体积层）合并。
    加载顺序 privacy 先、主表后：同址时主表行覆盖（主表信息更全）。"""
    table = {}
    for suffix in ('-privacy', ''):
        for r in _read_rows(os.path.join(labels_dir, f'labels-{chain}{suffix}.csv')):
            table[r['address']] = r
    return table


# ---- address-book.md 手工核验层（v4.2 2026-07-30）----
# 血案背景：PYTHIA 案币安 Alpha 库存仓 9ZPsR… 早已录入 address-book.md 并点名 PYTHIA
# 第一大持仓，但 label_lookup 只读 CSV 库 → 零命中 → 该仓被误判"小庄#1 私人庄家"。
# 同族错误第三次复发（IQ 案 Upbit 托管判大庄、LPT 案 Bitvavo 质押判巨鲸）。
# 运行时只读由 address-book.md 规范区确定性生成的 sources/manual_labels.csv；
# gen_manual_from_addressbook.py 负责生成，check_manual_sync.py 逐行及双向对账并进入全量 suite。
# CSV 主库同址覆盖本手工层（主库信息更全）。
_BOOK_CATEGORY_RULES = (
    ('做市商', 'market-maker', 'identity'),
    ('锁仓', 'locker', 'identity'),
    ('CEX', 'cex', 'exclude'),
    ('提币热钱包', 'cex', 'exclude'),
    ('桥', 'bridge', 'exclude'),
    ('聚合器', 'bridge', 'exclude'),
    ('程序', 'program', 'exclude'),
)


def _load_address_book(labels_dir, chain):
    """Load the generated address-book layer with an explicit per-row chain.

    Address shape is not chain evidence: the same 0x address can mean unrelated
    contracts on ETH/BSC/Base.  The human markdown is therefore never parsed
    directly at runtime; its chain-qualified generated table is the executable
    schema and check_manual_sync keeps the two sources aligned.
    """
    path = os.path.join(_HERE, 'sources', 'manual_labels.csv')
    if not os.path.exists(path):
        return {}
    table = {}
    for raw in _read_rows(path):
        if (raw.get('chain') or '').strip() != chain:
            continue
        addr = norm_addr(raw.get('address'), chain)
        if addr is None:
            continue
        row = {k: (raw.get(k) or '') for k in BASE_FIELDS + V4_OPTIONAL_FIELDS}
        row['address'] = addr
        row['chain'] = chain
        row['source'] = row['source'] or 'address-book'
        table[addr] = row
    return table


def _classify_flag(f):
    if f in PRIVACY_FLAGS:
        return 'privacy'
    if f in CANDIDATE_RISK:
        return 'candidate'
    if f in DEFINITIVE_RISK or any(f.endswith(s) for s in DEFINITIVE_SUFFIXES):
        return 'definitive'
    return 'unknown'


def derive_policy(row):
    """从 (tier, category) 推导决策三维；CSV 可选列非空时覆盖推导。
    返回 {'merge_policy', 'balance_policy', 'serial'}。"""
    tier = (row.get('tier') or '').strip()
    cat = (row.get('category') or '').strip()
    merge = 'no_merge' if (tier == 'exclude' or cat in NO_MERGE_CATEGORIES) else 'allow'
    if tier == 'exclude':
        balance = 'exclude'
    elif cat in BUCKET_CATEGORIES:
        balance = 'bucket'
    else:
        balance = 'count'
    m_override = (row.get('merge_policy') or '').strip()
    b_override = (row.get('balance_policy') or '').strip()
    if m_override in _MERGE_VALUES:
        merge = m_override
    if b_override in _BALANCE_VALUES:
        balance = b_override
    return {'merge_policy': merge, 'balance_policy': balance, 'serial': cat == SERIAL_CATEGORY}


class LabelResolver:
    def __init__(self, chain, labels_dir=None, evm_fallback=True):
        self.chain = chain
        self.labels_dir = labels_dir or DEFAULT_LABELS_DIR
        csv_table = _load_csv(self.labels_dir, chain)
        # v4.2：address-book.md 手工核验层永久并源（PYTHIA 9ZPsR 血案根治）；
        # CSV 主库同址覆盖手工层
        self.table = _load_address_book(self.labels_dir, chain)
        self.book_rows = len(self.table)
        self.table.update(csv_table)
        self.fallback = {}
        # Robinhood/BSC/Base/Arbitrum 等 EVM 地址体系链：对 eth 表同址联查（仅提示不决策）
        if evm_fallback and chain not in ('sol', 'eth') and chain in KNOWN_CHAINS:
            self.fallback = _load_csv(self.labels_dir, 'eth')
        self._hits = {'direct': 0, 'cross': 0}
        # 降级模式：CSV 主库一行都没加载到 → 表缺失/路径错/文件损坏。
        # 判定只看 CSV（地址簿加载成功不得掩盖主库缺失警告）。
        # "没命中"与"库根本没加载"必须可区分（codex 复核 2026-07-16）。
        self.degraded = chain in KNOWN_CHAINS and not csv_table

    def warn_if_degraded(self, stream=None):
        """降级时向 stderr 打一行显式警告；返回是否降级。调用方（cluster 等）启动时必调。"""
        if self.degraded:
            print(f'[labels][degraded_mode] chain={self.chain} 标签表加载 0 行 '
                  f'（{self.labels_dir}/labels-{self.chain}.csv 缺失或为空）——'
                  f'本次运行【无标签兜底】，设施剔除/合并拦截全部失效，结论按无标签口径解读',
                  file=stream or sys.stderr)
        return self.degraded

    def get(self, addr):
        """返回标签行 dict（附 cross_chain 布尔 + policy 三维），未命中返回 None。"""
        na = norm_addr(addr, self.chain)
        if na is None:
            return None
        row = self.table.get(na)
        cross = False
        if row is None:
            row = self.fallback.get(na)
            cross = row is not None
        if row is None:
            return None
        self._hits['cross' if cross else 'direct'] += 1
        out = dict(row)
        out['cross_chain'] = cross
        out.update(derive_policy(row))
        out['stale_days'] = staleness(row)
        out['status_inactive'] = (row.get('status') or '').strip().lower() in INACTIVE_STATUS
        out['stale_hint'] = bool(
            out['stale_days'] is not None and out['stale_days'] > STALE_DAYS
            and (row.get('category') or '').strip() in TIME_SENSITIVE_CATEGORIES)
        return out

    # ---- 自动决策接口：只认目标链直接命中（cross_chain 命中一律不触发） ----
    def is_exclude(self, addr):
        """该地址是否为基础设施（禁止计入实体持仓/大户榜）。等价 balance_policy=exclude。
        status_inactive（人工标记失效）时不自动决策（3.18.0 纪律 7）。"""
        r = self.get(addr)
        return (bool(r) and not r['cross_chain'] and not r['status_inactive']
                and r['balance_policy'] == 'exclude')

    def no_merge(self, addr):
        """该地址是否禁止作聚类合并边（exclude 设施 + locker/分发/募集类公共通道）。
        注意：status_inactive **不**放开禁边——重放的是全历史，退役桥/轮换热钱包在其
        活跃期的转账边依然是公共边，放开=聚类污染回归（3.18.0 语义切分：
        聚类边规则跟历史走，余额规则跟当下走）。"""
        r = self.get(addr)
        return bool(r) and not r['cross_chain'] and r['merge_policy'] == 'no_merge'

    def balance_policy(self, addr):
        """count | bucket | exclude；未命中/跨链命中/人工标记失效返回 'count'（不自动决策）。"""
        r = self.get(addr)
        if not r or r['cross_chain'] or r['status_inactive']:
            return 'count'
        return r['balance_policy']

    def is_serial(self, addr):
        """是否历史案标记惯犯（serial-actor，案内定性线索级）。跨链命中也提示（EOA 同私钥，惯犯跨链常见），
        但输出方须标注 cross_chain 让人工复核。"""
        r = self.get(addr)
        return bool(r) and r.get('serial', False)

    def policy(self, addr):
        """完整决策视图；未命中返回 None。自动决策字段在 cross_chain=True 或
        status_inactive=True（人工标记失效）时一律回退保守值。"""
        r = self.get(addr)
        if not r:
            return None
        if r['cross_chain'] or r['status_inactive']:
            # cross_chain：全部回退保守。status_inactive：仅余额侧回退（merge 禁边跟历史走）
            return {'hit': True, 'cross_chain': r['cross_chain'],
                    'status_inactive': r['status_inactive'],
                    'merge_policy': 'allow' if r['cross_chain'] else r['merge_policy'],
                    'balance_policy': 'count', 'serial': r['serial'],
                    'stale_days': r['stale_days'], 'stale_hint': r['stale_hint'],
                    'risk': self.risk_partition(r), 'row': r}
        return {'hit': True, 'cross_chain': False, 'status_inactive': False,
                'merge_policy': r['merge_policy'], 'balance_policy': r['balance_policy'],
                'serial': r['serial'], 'stale_days': r['stale_days'],
                'stale_hint': r['stale_hint'], 'risk': self.risk_partition(r), 'row': r}

    # ---- 风险分区（v4 白名单制，四档） ----
    @staticmethod
    def risk_partition(row):
        """把一行的 risk_flags 拆成 definitive/candidate/privacy/unknown 四档。
        unknown=白名单外旗标：提示人工核验，不作自动定性（修复 v3"宁严勿松"把
        拼错/脏旗标放大成'必写报告重大信号'的副作用）。"""
        out = {'definitive': [], 'candidate': [], 'privacy': [], 'unknown': []}
        for f in (row.get('risk_flags') or '').split('|'):
            f = f.strip()
            if f:
                out[_classify_flag(f)].append(f)
        return out

    def stats(self):
        return {'chain': self.chain, 'schema': LABELS_SCHEMA_VERSION,
                'table_rows': len(self.table), 'fallback_rows': len(self.fallback),
                'degraded': self.degraded, **self._hits}

    def meta(self):
        """写进分析产物 JSON 的标签库元信息（labels_meta），供事后审计口径。"""
        s = self.stats()
        s['labels_dir'] = self.labels_dir
        return s


# ---- 惯犯层延迟揭盲（A5 2026-07-22）：聚类阶段盲化 serial 命中，防先入之见 ----
# 流程：聚类/持仓分析期开 CHIP_BLIND_SERIAL=1（或 label_lookup --blind-serial）——
# serial 命中不进任何主输出，完整详情追加封存 sealed_serial_hits.jsonl；
# 实体冻结后复核期 label_lookup.py --unseal 揭盲，作定向复核线索。
# 注意：盲化只隐藏"输出"，不改变聚类决策本身（cluster.py 的 gatekeeper 豁免照旧）。
SEALED_BASENAME = 'sealed_serial_hits.jsonl'


def blind_serial_env():
    """CHIP_BLIND_SERIAL=1 时聚类路径各出口统一盲化 serial 层输出。"""
    return os.environ.get('CHIP_BLIND_SERIAL', '') == '1'


def seal_serial_hits(records, sealed_dir='.', context=''):
    """把 serial 命中完整详情追加封存（每行一 JSON）；records=[{chain,address,...row字段}]。
    返回封存文件路径（records 为空也返回路径但不写入——调用方可据此提示位置）。"""
    import json as _json
    path = os.path.join(sealed_dir or '.', SEALED_BASENAME)
    if not records:
        return path
    ts = datetime.datetime.now().isoformat(timespec='seconds')
    with open(path, 'a') as f:
        for r in records:
            rec = {'sealed_at': ts, 'context': context}
            for k, v in r.items():
                if isinstance(v, (str, int, float, bool, list, dict)) or v is None:
                    rec[k] = v
            f.write(_json.dumps(rec, ensure_ascii=False) + '\n')
    return path


def blind_notice(sealed_path, stream=None):
    """盲化固定提示行：无论有无命中都打印同一句（有无命中本身也是需要盲化的信息）。"""
    print(f'[blind-serial] serial 惯犯层已盲化：本输出不含惯犯命中信息（无论有无命中）；'
          f'实体冻结后复核期揭盲：python3 label_lookup.py --unseal --sealed-dir '
          f'{os.path.dirname(sealed_path) or "."}', file=stream or sys.stderr)


def read_sealed(sealed_dir='.'):
    """读取封存的 serial 命中；文件不存在返回 []。"""
    import json as _json
    path = os.path.join(sealed_dir or '.', SEALED_BASENAME)
    if not os.path.exists(path):
        return []
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(_json.loads(line))
                except ValueError:
                    continue
    return out


def resolve_file(chain, path, labels_dir=None):
    """便利函数：对一个地址清单文件逐行 resolve，返回 [(addr, row|None)]。"""
    resv = LabelResolver(chain, labels_dir)
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            a = line.split(',')[0]
            out.append((a, resv.get(a)))
    return out


def append_misses(chain, entries, context, labels_dir=None):
    """实战 miss 队列（v4，codex 第二轮复核提案）：分析时把【未命中标签库的高权重地址】
    落盘积累——高余额/高度数/共同 funder/高频中转是静态库最该收录却最容易缺的对象。
    按出现次数人工审核回填 manual 层，是个人工具最省人力的扩容路径。

    entries: [(addr, weight, reason)]；context: 本次分析标识（如 'GME cluster R2'）。
    产物: references/labels/miss-queue/<chain>.csv（追加式；同址同 context 不重写）。
    """
    import datetime
    d = os.path.join(labels_dir or DEFAULT_LABELS_DIR, 'miss-queue')
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f'{chain}.csv')
    seen = set()
    if os.path.exists(path):
        with open(path, newline='') as f:
            for r in csv.DictReader(f):
                seen.add((r['address'], r['context']))
    new = [(a, w, why) for a, w, why in entries if (norm_addr(a, chain), context) not in seen
           and norm_addr(a, chain)]
    if not new:
        return 0
    write_header = not os.path.exists(path)
    with open(path, 'a', newline='') as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(['address', 'chain', 'reason', 'weight', 'context', 'seen_date'])
        today = datetime.date.today().isoformat()
        for a, wt, why in new:
            w.writerow([norm_addr(a, chain), chain, why, wt, context, today])
    return len(new)
