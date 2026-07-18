#!/usr/bin/env python3
"""manual 层双份真源一致性校验（v4 2026-07-17，README「已知局限」欠账清偿）

背景：references/address-book.md（人读文档）与 gen_manual_from_addressbook.py（硬编码）
是两份手抄——历史上要求"改地址簿必须同步改脚本"，全凭自觉。本脚本给它装上牙齿：
双向 diff，白名单外的不一致 = exit 1（build_labels.py 末尾强制调用）。

方向 A  地址簿有、脚本没有 → 漏同步（新核验条目没入库）
方向 B  脚本有、地址簿没有 → 幽灵条目（脚本手抄漂移，或地址簿删了脚本没删）

白名单（ALLOW_*）：地址簿里"性质说明型"条目（7702 delegate 实现、截断示意地址等）
本来就不入标签库；脚本里的协议常识地址（burn/系统程序）不要求地址簿收录。
"""
import os, re, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
BOOK = os.path.normpath(os.path.join(_HERE, '..', '..', 'references', 'address-book.md'))
GEN = os.path.join(_HERE, 'gen_manual_from_addressbook.py')

EVM_RE = re.compile(r'0x[0-9a-fA-F]{40}(?![0-9a-fA-F])')
B58_RE = re.compile(r'(?<![1-9A-HJ-NP-Za-km-z])[1-9A-HJ-NP-Za-km-z]{32,44}(?![1-9A-HJ-NP-Za-km-z])')

# 地址簿有但按设计不入标签库的条目（每条必须带原因；新增前先想清楚是不是该入库）
ALLOW_BOOK_ONLY = {
    # EIP-7702 delegate 实现：海量用户共用的"实现指纹"，语义是判别知识不是地址标签
    '0xcc0c946eecf01a4bc76bc333ea74ceb04756f17b',
    '0x63c0c19a282a1b52b07dd5a65b58948a07dae32b',
    '0xe6cae83bde06e4c305530e199d7217f42808555b',
    # 金主/待溯源实例（单次分析标的信息，纪律②不入库）
    '0x469cb5da5f46d9c16d9825e41d831377e167478f',
}
# 脚本有但地址簿不逐条罗列的（协议常识/批量层）
ALLOW_GEN_ONLY = {
    '0x0000000000000000000000000000000000000000', '0x000000000000000000000000000000000000dead',
    '0x0000000000000000000000000000000000000001', '11111111111111111111111111111111',
    '1nc1nerator11111111111111111111111111111111',
    # KOL 公开地址（来源是推特考证不是地址簿；evidence 已带出处）
    'HUpPyLU8KWisCAr3mzWy2FKT6uuxQ2qGgJQxyTpDoes5', 'G1pRtSyKuWSjTqRDcazzKBDzqEF96i1xSURpiXj3yFcc',
    'Ay9wnuZCRTceZJuRpGZnuwYZuWdsviM4cMiCwFoSQiPH', '8deJ9xeUvXSJwicYptA9mHsU2rN2pDx37KWzkDkEXhU6',
    # locker 快速档（bscscan/etherscan 亲验补录，地址簿只记纪律不逐条罗列）
    '0x407993575c91ce7643a4d4ccacc9a98c36ee1bbe', '0xe2fe530c047f2d85298b07d9333c05737f1435fb',
}
# 已知非地址的 base58 误抓词（markdown 里的长驼峰词）
B58_STOPWORDS = {'NonfungiblePositionManager', 'TransparentUpgradeableProxy',
                 'AdminUpgradeabilityProxy', 'StatelessDeleGator'}


def extract(text):
    addrs = set()
    for m in EVM_RE.findall(text):
        addrs.add(m.lower())
    # 先把 EVM 地址整体抹掉再提 base58，防止 0x 后的 hex 子串被误抓成 base58
    text_wo_evm = EVM_RE.sub(' ', text)
    for m in B58_RE.findall(text_wo_evm):
        if m in B58_STOPWORDS:
            continue
        # base58 地址要求含数字的高熵形态，纯字母长词（驼峰名）跳过
        if any(c.isdigit() for c in m):
            addrs.add(m)
    return addrs


def main():
    book_addrs = extract(open(BOOK).read())
    gen_addrs = extract(open(GEN).read())

    only_book = sorted(a for a in book_addrs - gen_addrs
                       if a not in {x.lower() for x in ALLOW_BOOK_ONLY} and a not in ALLOW_BOOK_ONLY)
    only_gen = sorted(a for a in gen_addrs - book_addrs
                      if a not in {x.lower() for x in ALLOW_GEN_ONLY} and a not in ALLOW_GEN_ONLY)

    print(f'[check_manual_sync] 地址簿 {len(book_addrs)} 址 | 脚本 {len(gen_addrs)} 址 | '
          f'漏同步 {len(only_book)} | 幽灵 {len(only_gen)}')
    if only_book:
        print('  方向A 地址簿有、gen_manual 没有（漏同步——新核验条目未入库，或加 ALLOW_BOOK_ONLY 并写原因）:')
        for a in only_book:
            print(f'    - {a}')
    if only_gen:
        print('  方向B gen_manual 有、地址簿没有（幽灵条目——手抄漂移，或加 ALLOW_GEN_ONLY 并写原因）:')
        for a in only_gen:
            print(f'    - {a}')
    if only_book or only_gen:
        sys.exit(1)
    print('  一致 ✓')


if __name__ == '__main__':
    main()
