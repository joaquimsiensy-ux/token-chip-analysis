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

跨案身份冲突检测（A7 2026-07-22；3.19.1 起设施级硬闸）：候选地址逐一对照主标签库——
  同址在主库当前是基础设施类身份（cex/suspected-cex/infra/bridge/dex/bundler/paymaster/mev）
  或命中 benchmark 设施金标，而本工具要标它"庄家实体成员"→ 写 conflicts 报告
  （sources/serial_conflicts_<日期>.json+.md，含两侧证据），且 **primary/goldset-infra 级
  冲突地址被硬闸拦截、不写入 serial_actors.csv**（--apply 与手动 add_labels 两条入库路径
  一并挡住）；secondary/cross_chain 仅提示。危险场景实案：QUQ 案大庄#1 误吸 PancakeSwap
  Infinity Vault，2026-07-22 --apply 高置信覆盖抹掉主库设施身份 → 聚类禁边失效（用户裁决
  后以 curation override 恢复，本硬闸即该事故的防线）。被拦地址裁决后的入库路径：
  ①案源误吸→修 whale_groups 重跑 ②主库错→curation override ③确属庄家自建设施→
  手工编辑 CSV 单独 add_labels（绕闸需人工显式动作，无 --force 参数）。
  不带 --apply 跑一次 = 存量扫描（候选全集=惯犯库全量,逐址对照主库）。

用法：python3 accumulate_offenders.py [分析根目录] [--apply] [--labels-dir DIR]
手动入库：cd sources && python3 ../add_labels.py serial_actors.csv
"""
import csv, datetime, glob, json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from labels_resolver import LabelResolver

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.expanduser('~/Desktop/老公用/fable筹码分析')
OUT = os.path.join(_HERE, 'sources', 'serial_actors.csv')

# A7：基础设施类身份清单（主档冲突）；其余 tier=exclude / no_merge 类目作次档提示
INFRA_CATS = {'cex', 'suspected-cex', 'infra', 'bridge', 'dex', 'bundler', 'paymaster', 'mev', 'locker'}


def load_goldset_infra(labels_dir=None):
    """benchmark 金标里的设施地址集 {(chain, addr)}——检测"已被 serial 覆盖的设施"
    （高置信覆盖发生后主库只剩 serial-actor 行，resolver 查不出原设施身份；金标是
    独立真相源。实案：QUQ 惯犯层曾把 PancakeSwap Infinity Vault 覆盖成 serial-actor）。"""
    from labels_resolver import DEFAULT_LABELS_DIR
    p = os.path.join(labels_dir or DEFAULT_LABELS_DIR, 'benchmark', 'goldset.csv')
    out = set()
    if os.path.exists(p):
        with open(p, newline='') as f:
            for r in csv.DictReader(f):
                if (r.get('expected') or '').strip() == 'infrastructure':
                    out.add(((r.get('chain') or '').strip(), (r.get('address') or '').strip().lower()))
    return out


def detect_conflicts(rows, labels_dir=None):
    """候选 {(chain,addr): row} 逐址查主标签库，返回冲突列表（不修改任何库）。
    severity: primary   = 主库当前 category ∈ INFRA_CATS（设施身份 vs 庄家成员，最危险）
              goldset-infra = benchmark 设施金标命中（含已被 serial 覆盖的历史冲突，primary 级）
              secondary = 主库 tier=exclude 或 merge_policy=no_merge 的其他类目（protocol/locker…）
              cross_chain = EVM 跨链 fallback 在 eth 表是设施（提示级，不计主数）"""
    conflicts = []
    resolvers = {}
    gold_infra = load_goldset_infra(labels_dir)
    for (chain, na), cand in sorted(rows.items()):
        if chain not in resolvers:
            resolvers[chain] = LabelResolver(chain, labels_dir)
        resv = resolvers[chain]
        r = resv.get(na)
        if (chain, na) in gold_infra:
            # 金标说它是设施——无论主库当前是什么（含已被高置信覆盖成 serial-actor 的行）
            conflicts.append({
                'severity': 'goldset-infra', 'chain': chain, 'address': na,
                'serial_side': {'name': cand['name'], 'evidence': cand['evidence'],
                                'source': cand['source']},
                'label_side': {'name': (r or {}).get('name', '(主库无行)'),
                               'category': (r or {}).get('category', ''),
                               'tier': (r or {}).get('tier', ''),
                               'merge_policy': (r or {}).get('merge_policy', ''),
                               'balance_policy': (r or {}).get('balance_policy', ''),
                               'source': (r or {}).get('source', ''),
                               'evidence': 'benchmark goldset expected=infrastructure（manual 层设施金标）',
                               'verified_at': (r or {}).get('verified_at', ''),
                               'cross_chain': bool(r and r['cross_chain'])},
            })
            continue
        if r is None:
            continue
        main_cat = (r.get('category') or '').strip()
        if main_cat == 'serial-actor':
            continue   # 主库已是惯犯身份（本工具此前入库）——一致，无冲突
        sev = None
        if not r['cross_chain']:
            if main_cat in INFRA_CATS:
                sev = 'primary'
            elif (r.get('tier') or '').strip() == 'exclude' or r.get('merge_policy') == 'no_merge':
                sev = 'secondary'
        elif main_cat in INFRA_CATS:
            sev = 'cross_chain'
        if sev is None:
            continue
        conflicts.append({
            'severity': sev, 'chain': chain, 'address': na,
            'serial_side': {'name': cand['name'], 'evidence': cand['evidence'],
                            'source': cand['source']},
            'label_side': {'name': r.get('name', ''), 'category': main_cat,
                           'tier': r.get('tier', ''), 'merge_policy': r.get('merge_policy', ''),
                           'balance_policy': r.get('balance_policy', ''),
                           'source': r.get('source', ''), 'evidence': r.get('evidence', ''),
                           'verified_at': r.get('verified_at', ''),
                           'cross_chain': r['cross_chain']},
        })
    return conflicts


def write_conflict_report(conflicts, out_dir):
    """conflicts 报告落惯犯库同目录（json+md，命名带日期）；空冲突不落文件。"""
    if not conflicts:
        return None
    today = datetime.date.today().isoformat()
    jp = os.path.join(out_dir, f'serial_conflicts_{today}.json')
    mp = os.path.join(out_dir, f'serial_conflicts_{today}.md')
    order = {'primary': 0, 'goldset-infra': 0, 'secondary': 1, 'cross_chain': 2}
    conflicts = sorted(conflicts, key=lambda c: (order.get(c['severity'], 9), c['chain'], c['address']))
    n_pri = sum(1 for c in conflicts if c['severity'] in ('primary', 'goldset-infra'))
    json.dump({'generated': today, 'total': len(conflicts), 'primary': n_pri,
               'note': '同址双身份=设施(主标签库) vs 庄家实体成员(惯犯候选)。primary/goldset-infra'
                       ' 级已被硬闸拦截在 serial_actors.csv 外(3.19.1),不会入库;逐条人工裁决:'
                       '①案源实体划分误吸设施→修 whale_groups 并重跑本工具 ②主库标签错→修主库'
                       '(curation override) ③确属庄家自建设施→手工编辑 CSV 单独 add_labels'
                       '(绕闸需人工显式动作)。实案:QUQ 大庄#1 误吸 PancakeSwap Infinity Vault,'
                       '2026-07-22 覆盖事故后用户裁决①+②并加本硬闸。',
               'conflicts': conflicts}, open(jp, 'w'), ensure_ascii=False, indent=1)
    with open(mp, 'w') as f:
        f.write(f'# 惯犯库 × 主标签库 身份冲突报告（{today}）\n\n')
        f.write(f'共 {len(conflicts)} 条（primary {n_pri}）。primary=主库设施身份 vs 庄家成员,'
                f'误入库会被高置信覆盖抹掉设施标签→聚类拦截失效。**设施级已硬闸拦截不入库,'
                f'逐条人工裁决**（三路径见脚本 docstring）。\n\n')
        for c in conflicts:
            f.write(f"## [{c['severity']}] {c['chain']} `{c['address']}`\n"
                    f"- 惯犯侧: {c['serial_side']['name']}\n"
                    f"  - 证据: {c['serial_side']['evidence'][:200]}\n"
                    f"- 主库侧: {c['label_side']['name']} <{c['label_side']['category']}"
                    f"|tier={c['label_side']['tier']}|merge={c['label_side']['merge_policy']}>"
                    f" 来源:{c['label_side']['source']}"
                    f"{' (eth 表跨链联查,提示级)' if c['label_side']['cross_chain'] else ''}\n")
            if c['label_side']['evidence']:
                f.write(f"  - 证据: {c['label_side']['evidence'][:200]}\n")
            f.write('\n')
    return jp

# 侧链/L2 一律折进 eth 表：标签库只有 7 条链的分表，而 EVM 的 EOA 是同私钥跨链同一人，
# resolver 对非 eth 的 EVM 链本就做 eth 表同址联查（KNOWN_CHAINS 之外的链原先会被
# 下面的白名单直接 continue 掉 → Arbitrum/Avalanche 等案的实锤庄永远进不了惯犯库，
# GMX(Arbitrum) 2026-07-26 实测暴露）。合约地址同址≠同实体，resolver 命中时已附提示。
CHAIN_MAP = {'solana': 'sol', 'ethereum': 'eth', 'bnb': 'bsc', 'binance': 'bsc',
             'arbitrum': 'eth', 'arbitrum one': 'eth', 'arbitrum-one': 'eth', 'arb': 'eth',
             'avalanche': 'eth', 'avax': 'eth', 'avalanche c-chain': 'eth',
             'polygon': 'eth', 'matic': 'eth', 'optimism': 'eth', 'op': 'eth',
             'linea': 'eth', 'scroll': 'eth', 'blast': 'eth', 'mantle': 'eth'}
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
    argv = sys.argv[1:]
    labels_dir, out_path, args, skip = None, OUT, [], False
    for i, a in enumerate(argv):
        if skip:
            skip = False
            continue
        if a.startswith('--labels-dir='):
            labels_dir = a.split('=', 1)[1]
        elif a == '--labels-dir':
            labels_dir = argv[i + 1] if i + 1 < len(argv) else None
            skip = True
        elif a.startswith('--out='):
            out_path = a.split('=', 1)[1]   # 测试/沙盘用；正式流程用默认 sources/serial_actors.csv
        elif not a.startswith('--'):
            args.append(a)
    apply_mode = '--apply' in argv
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
        tok = d.get('token') or {}
        raw_chain = tok.get('chain')
        if not raw_chain:                       # 多链 state（token.chains 数组）：取 native 链
            chs = tok.get('chains') or []
            if chs:
                nat = next((c for c in chs if (c.get('role') or '') == 'native'), chs[0])
                raw_chain = nat.get('chain')
        chain = norm_chain(raw_chain)
        token = tok.get('symbol') or case
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
    # A7 跨案身份冲突检测——写 CSV 前做（3.19.1 硬闸）：primary/goldset-infra 级冲突地址
    # 直接拦在 CSV 外，--apply 与"手动 add_labels serial_actors.csv"两条路径一并挡住；
    # 全部冲突（含被拦项）仍完整落 conflicts 报告供裁决。
    conflicts = detect_conflicts(rows, labels_dir)
    blocked = [(c['chain'], c['address']) for c in conflicts
               if c['severity'] in ('primary', 'goldset-infra')]
    for key in blocked:
        rows.pop(key, None)

    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    out_rows = sorted(rows.values(), key=lambda r: (r['chain'], r['address']))
    with open(out_path, 'w', newline='') as f:
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

    # A7 冲突报告与拦截提示（检测已在写 CSV 前完成）
    if conflicts:
        rp = write_conflict_report(conflicts, os.path.dirname(out_path) or '.')
        print(f'⚠️ 身份冲突 {len(conflicts)} 条，其中设施级 {len(blocked)} 址已硬闸拦截'
              f'（未写入 CSV，不会入库）——报告已落 {rp}（+同名 .md），逐条裁决后按 docstring 三路径处理')
        for c in conflicts[:6]:
            tag = '🚫已拦截' if c['severity'] in ('primary', 'goldset-infra') else '提示'
            print(f"   [{c['severity']}|{tag}] {c['chain']} {c['address'][:16]}… "
                  f"主库={c['label_side']['name'][:28]}<{c['label_side']['category']}> "
                  f"vs 惯犯候选={c['serial_side']['name'][:28]}")
    else:
        print('身份冲突检测: 0 条（候选与主标签库无设施类身份重叠）')
    if apply_mode and out_rows:
        r = subprocess.run([sys.executable, os.path.join(_HERE, 'add_labels.py'), out_path],
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
