#!/usr/bin/env python3
"""基础设施/身份标签批量查询器（token-chip-analysis 聚类前置步骤；内核为 labels_resolver）

用法：
  python3 label_lookup.py --chain sol ADDR1 ADDR2 ...
  python3 label_lookup.py --chain bsc --file candidates.txt        # 每行一地址（容忍 CSV 取首列）
  cat addrs.txt | python3 label_lookup.py --chain eth
  python3 label_lookup.py --chain all ADDR ...                     # 跨全部链查
  python3 label_lookup.py --chain bsc --json --file a.txt          # JSONL 机器可读输出（脚本管道用）

文本输出七段（v4 2026-07-16，codex 交叉复核第二轮融合）：
  [SERIAL]         历史分析实锤惯犯庄家——命中=高优先级信号，立即比对案源背景
  [RISK]           定性风险（制裁/黑客/赌博）——大户命中=重大信号，必须写进报告
  [RISK-CANDIDATE] 社区候选（ScamSniffer 等单源上报）——降权提示，不作定性依据
  [RISK-UNKNOWN]   白名单外未识别旗标——人工核验后扩白名单或修数据，不自动定性
  [EXCLUDE]        CEX/桥/路由/协议/发射台/bot 设施——禁止计入实体持仓/聚类合并边；资金路径叙事保留
  [IDENTITY]       KOL/基金/做市商/locker 等身份——不剔除，报告标注
                   （locker/airdrop-distributor/token-sale/charity 禁作聚类合并边）
  [PRIVACY]        Tornado 使用记录——陈述事实不定性；"庄家资金源头自 Tornado 提取"是必写信号
非 sol/eth/filecoin 链自动对 eth 表做 EVM 同址联查（cross_chain 提示级：EOA=同私钥可信，
CREATE2 canonical=同部署流程，普通合约同址≠同实体需现场核验；自动决策不采信）。
"""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from labels_resolver import LabelResolver, KNOWN_CHAINS, norm_addr, SERIAL_CATEGORY

SECTIONS = ('serial', 'risk', 'candidate', 'unknown', 'exclude', 'identity', 'privacy')
SECTION_HEAD = {
    'serial': '[SERIAL] 历史实锤惯犯庄家——高优先级信号，立即调案源核对（换币再开盘是其惯例）',
    'risk': '[RISK] 定性风险（制裁/黑客/赌博）——大户命中必须写进报告',
    'candidate': '[RISK-CANDIDATE] 社区候选（单源上报，延迟约 7 天）——降权提示，不作定性',
    'unknown': '[RISK-UNKNOWN] 白名单外旗标——人工核验后扩白名单或修数据，不自动定性',
    'exclude': '[EXCLUDE] 基础设施——禁止计入实体持仓/聚类合并边（资金路径叙事保留）',
    'identity': '[IDENTITY] 身份标注——不剔除，报告注明（KOL 钱包会轮换，用前抽查；'
                'locker/分发/募集/慈善类禁作合并边）',
    'privacy': '[PRIVACY] Tornado 使用记录——陈述事实不定性（资金源头自 Tornado 提取则必写）',
}


def read_addrs(args):
    raw = list(args.addrs)
    if args.file:
        for line in open(args.file):
            line = line.strip()
            if line and not line.startswith('#'):
                raw.append(line.split(',')[0])
    if not raw and not sys.stdin.isatty():
        for line in sys.stdin:
            line = line.strip()
            if line and not line.startswith('#'):
                raw.append(line.split(',')[0])
    return raw


def classify(row, rp):
    """一行命中归入哪些段落：返回 section 列表（可多段并存，如被制裁的 CEX = risk+exclude）。"""
    secs = []
    if row['category'] == SERIAL_CATEGORY:
        secs.append('serial')
    if rp['definitive']:
        secs.append('risk')
    if rp['candidate']:
        secs.append('candidate')
    if rp['unknown']:
        secs.append('unknown')
    if rp['privacy']:
        secs.append('privacy')
    if row['tier'] == 'exclude':
        secs.append('exclude')
    elif row['tier'] == 'identity' and row['category'] not in (
            'tornado-user', 'scam-candidate', SERIAL_CATEGORY):
        # 纯 tornado/scam 候选行不再重复进 IDENTITY 段；serial 已有专段
        secs.append('identity')
    elif row['tier'] == 'risk' and not secs:
        secs.append('risk')
    return secs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--chain', required=True, choices=KNOWN_CHAINS + ('all',))
    ap.add_argument('--file', help='地址清单文件（每行一个；CSV 取第一列）')
    ap.add_argument('--labels-dir', default=None)
    ap.add_argument('--no-evm-common', action='store_true', help='关闭对 eth 表的 EVM 同址联查')
    ap.add_argument('--misses', action='store_true', help='额外列出未命中的地址')
    ap.add_argument('--json', action='store_true', help='JSONL 输出（每地址一行，机器可读）')
    ap.add_argument('addrs', nargs='*')
    args = ap.parse_args()

    raw = read_addrs(args)
    if not raw:
        ap.error('没有输入地址（位置参数 / --file / stdin 三选一）')

    chains = list(KNOWN_CHAINS) if args.chain == 'all' else [args.chain]
    hits, misses = [], []
    for chain in chains:
        resv = LabelResolver(chain, args.labels_dir, evm_fallback=not args.no_evm_common)
        if not resv.table and args.chain == 'all':
            continue
        if args.chain != 'all':
            resv.warn_if_degraded()
        for a in raw:
            na = norm_addr(a, chain)
            if na is None:
                continue
            row = resv.get(na)
            if row is not None:
                hits.append((chain, na, row))
            elif args.chain != 'all':
                misses.append((chain, na))

    if args.json:
        seen = set()
        for chain, na, row in hits:
            if (chain, na) in seen:
                continue
            seen.add((chain, na))
            rp = LabelResolver.risk_partition(row)
            print(json.dumps({
                'chain': chain, 'address': na, 'hit': True,
                'name': row['name'], 'category': row['category'], 'tier': row['tier'],
                'merge_policy': row['merge_policy'], 'balance_policy': row['balance_policy'],
                'serial': row['serial'],
                'risk_flags': row['risk_flags'], 'risk_partition': rp,
                'sections': classify(row, rp), 'cross_chain': row['cross_chain'],
                'source': row['source'], 'evidence': row.get('evidence', ''),
                'verified_at': row.get('verified_at', ''), 'status': row.get('status', ''),
            }, ensure_ascii=False))
        for chain, na in misses:
            print(json.dumps({'chain': chain, 'address': na, 'hit': False}, ensure_ascii=False))
        return

    if not hits:
        print(f'0/{len(set(raw))} 命中（库无记录≠白户，仅代表不在已知标签内）')
    else:
        by_sec = {}
        for chain, na, row in hits:
            rp = LabelResolver.risk_partition(row)
            for sec in classify(row, rp):
                by_sec.setdefault(sec, []).append((chain, na, row))
        uniq = {(c, a) for c, a, _ in hits}
        print(f'{len(uniq)}/{len(set(raw))} 地址命中标签库\n')
        for sec in SECTIONS:
            rows = by_sec.get(sec)
            if not rows:
                continue
            print(f'== {SECTION_HEAD[sec]} ==')
            for chain, na, row in rows:
                src = row['source'].split('+')[0]
                ev = f" | {row['evidence']}" if row.get('evidence') else ''
                rf = f"  ⚠risk:{row['risk_flags']}" if (row.get('risk_flags') or '').strip() else ''
                pol = f"  [merge:{row['merge_policy']}|balance:{row['balance_policy']}]"
                via = ''
                if row['cross_chain']:
                    via = '（EVM 同址联查自 eth 表；EOA=同私钥可信，CREATE2 canonical=同部署流程，普通合约同址≠同实体需现场核验；自动决策不采信）'
                print(f'  [{chain}] {na}')
                print(f'      {row["name"]}  <{row["category"]}>{rf}{pol}  来源:{src}{ev} {via}')
            print()
    if args.misses and misses:
        print('== 未命中 ==')
        for chain, na in misses:
            print(f'  [{chain}] {na}')


if __name__ == '__main__':
    main()
