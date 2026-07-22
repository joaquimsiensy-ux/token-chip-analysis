#!/usr/bin/env python3
"""惯犯庄家层（serial-actor）聚合器（v4 2026-07-17 首建）

从历史分析 appendix.json **与 analysis-state.json**（3.18.0 起双源——监控包 v3.2 后
默认只交付 state 文件，只扫 appendix 会漏掉全部"没买入"案子的实锤庄）的 whale_groups
抽【实锤定性】的庄家/收割集团地址，生成 sources/serial_actors.csv——同一工作室换币
再开盘是行业惯例，命中即高亮"此地址是 XX 案实锤惯犯"，新分析开局即知对手是谁。

固定动作（3.18.0）：每次分析交付后（完整版阶段5 / easy E5 落盘 state 后）跑一次
  python3 accumulate_offenders.py --apply     # 生成+直接入库（add_labels 内置校验，FAIL 自动还原）
不带 --apply 只生成 CSV 供人工过目后再手动入库。

收纳纪律（宁缺毋滥，误标惯犯比漏标伤害大）：
  自动收：组 label 匹配 庄#N/小庄/离场庄/狙击集团#N/工作室 且定性词干净
  自动排：疑似/高度疑似/边界/观察/未达标签/不计庄家数/PLAUSIBLE/未证实/候选
  纯"项目方"组不收（项目方身份是标的专属；金库/vesting 地址跨盘无意义）——
  例外走 MANUAL_INCLUDE 白名单（如 meow 案"项目方"实为连环发币工作室，记忆存档实锤）
语义（labels_resolver 已内置）：tier=identity、不剔除、不禁边（惯犯地址间本就
  同实体，正常聚类）、risk_flags=serial-offender、lookup/analyze 命中即高亮。

用法：python3 accumulate_offenders.py [分析根目录] [--apply]   # 产物 sources/serial_actors.csv
手动入库：cd sources && python3 ../add_labels.py serial_actors.csv
"""
import csv, datetime, glob, json, os, re, subprocess, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.expanduser('~/Desktop/老公用/fable筹码分析')
OUT = os.path.join(_HERE, 'sources', 'serial_actors.csv')

CHAIN_MAP = {'solana': 'sol', 'ethereum': 'eth', 'bnb': 'bsc', 'binance': 'bsc'}
INCLUDE_RE = re.compile(r'(庄\s*#?\d|^庄|小庄|离场庄|狙击集团|工作室|收割)')
EXCLUDE_RE = re.compile(r'(疑似|边界|观察|未达标签|不计庄家|PLAUSIBLE|未证实|候选|行为学披露)')

# 人工白名单：label 上看不出、但记忆/报告存档实锤的组（案目录名, 组label 前缀）
MANUAL_INCLUDE = {
    # meow 案"项目方"7 址实为连环发币工作室（自购砸价+马甲低吸卖FOMO 组合拳实锤，
    # 记忆存档 meow-robinhood-analysis-conclusions 2026-07）
    ('meow分析', '项目方'),
    # CASHCAT 案"项目方"= 旧庄#1 工作室核心（3 实锤庄高度疑似同一工作室，已收割 $1200 万，
    # 记忆存档 cashcat-robinhood-analysis-conclusions 2026-07）
    ('CASHCAT分析', '项目方'),
}


def norm_chain(c):
    c = (c or '').strip().lower()
    c = re.sub(r'\s*\(chainid.*\)', '', c).replace('robinhood chain', 'robinhood')
    return CHAIN_MAP.get(c, c)


def valid_addr(a, chain):
    if isinstance(a, dict):        # 部分案 addresses 元素是 {address, role} 对象（Pointless 形态）
        a = a.get('address')
    a = (a or '').strip()
    if chain == 'sol':
        return a if 32 <= len(a) <= 44 else None
    a = a.lower()
    return a if re.fullmatch(r'0x[0-9a-f]{40}', a) else None


def case_files(root):
    """每个案目录取一个状态文件：appendix.json 优先（监控包语境更全），缺则 analysis-state.json。"""
    by_case = {}
    for fname in ('analysis-state.json', 'appendix.json'):   # appendix 后写入=优先
        for path in glob.glob(os.path.join(root, '*', fname)):
            by_case[os.path.dirname(path)] = path
    return [by_case[k] for k in sorted(by_case)]


def main():
    args = [a for a in sys.argv[1:] if a != '--apply']
    apply_mode = '--apply' in sys.argv[1:]
    root = args[0] if args else DEFAULT_ROOT
    today = datetime.date.today().isoformat()
    rows = {}          # (chain, addr) -> row（跨案命中合并 evidence——跨案=超强信号）
    n_groups = 0
    for path in case_files(root):
        case = os.path.basename(os.path.dirname(path))
        try:
            d = json.load(open(path))
        except Exception:
            continue
        dc = (d.get('token') or {}).get('data_cutoff')   # 新案 dict{block,utc}，旧案字符串，都见过
        if isinstance(dc, dict):
            dc = dc.get('utc')
        cutoff = str(dc or '')[:10] or today
        chain = norm_chain((d.get('token') or {}).get('chain'))
        token = (d.get('token') or {}).get('symbol') or case
        if chain not in ('eth', 'bsc', 'base', 'sol', 'robinhood', 'hyperliquid', 'filecoin'):
            continue
        for g in d.get('whale_groups') or []:
            label = (g.get('label') or '').strip()
            manual = any(case == c and label.startswith(p) for c, p in MANUAL_INCLUDE)
            if not manual:
                if not INCLUDE_RE.search(label) or EXCLUDE_RE.search(label):
                    continue
                if label.startswith('项目方') and '工作室' not in label:
                    continue
            n_groups += 1
            ev = f'{case} appendix whale_group「{label}」' + ('（人工白名单：记忆存档实锤工作室）' if manual else '')
            for a in g.get('addresses') or []:
                na = valid_addr(a, chain)
                if not na:
                    continue
                key = (chain, na)
                if key in rows:
                    if case not in rows[key]['evidence']:
                        rows[key]['evidence'] += f'；{ev}'
                        rows[key]['name'] += f'+{token}案'
                    continue
                rows[key] = {
                    'address': na, 'chain': chain,
                    'name': f'惯犯庄家（{token}案·{label[:24]}）',
                    'category': 'serial-actor', 'tier': 'identity',
                    'source': 'serial-offenders', 'added_date': today,
                    'evidence': ev, 'risk_flags': 'serial-offender',
                    'merge_policy': '', 'balance_policy': '',
                    'source_snapshot_at': cutoff, 'verified_at': today,
                    'status': '', 'raw_labels': '',
                }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    out_rows = sorted(rows.values(), key=lambda r: (r['chain'], r['address']))
    with open(OUT, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()) if out_rows else
                           ['address', 'chain'])
        w.writeheader(); w.writerows(out_rows)
    from collections import Counter
    cc = Counter(r['chain'] for r in out_rows)
    multi = [r for r in out_rows if '；' in r['evidence']]
    print(f'serial_actors.csv: {len(out_rows)} 址（{n_groups} 个实锤组）| 分链 {dict(cc)}')
    if multi:
        print(f'🚨 跨案命中 {len(multi)} 址（同一惯犯出现在多个案子——最高优先级）:')
        for r in multi[:10]:
            print(f'   {r["address"][:16]} {r["evidence"][:90]}')
    if apply_mode and out_rows:
        r = subprocess.run([sys.executable, os.path.join(_HERE, 'add_labels.py'), OUT],
                           capture_output=True, text=True)
        tail = (r.stdout.strip().splitlines() or ['(无输出)'])[-1]
        print(f'--apply 入库: {"OK" if r.returncode == 0 else "FAIL"} | {tail}')
        if r.returncode != 0:
            print(r.stdout + r.stderr)
            sys.exit(1)
        # 合法增量后立即重落发布指纹（否则 labels_manifest 校验会一直红）
        mf = os.path.join(_HERE, '..', 'tests', 'labels_manifest.py')
        r2 = subprocess.run([sys.executable, mf, '--write'], capture_output=True, text=True)
        print((r2.stdout.strip().splitlines() or ['(无输出)'])[-1])
    elif not apply_mode:
        print('（未入库；确认无误后 --apply 或手动 add_labels.py）')


if __name__ == '__main__':
    main()
