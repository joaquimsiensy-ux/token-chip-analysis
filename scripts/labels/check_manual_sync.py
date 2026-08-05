#!/usr/bin/env python3
"""校验 address-book.md 唯一真源与运行时 manual_labels.csv 完全同步。"""
import csv
import os
import re
import subprocess
import sys


_HERE = os.path.dirname(os.path.abspath(__file__))
BOOK = os.path.normpath(os.path.join(_HERE, '..', '..', 'references', 'address-book.md'))
GEN = os.path.join(_HERE, 'gen_manual_from_addressbook.py')
RUNTIME = os.path.join(_HERE, 'sources', 'manual_labels.csv')

EVM_RE = re.compile(r'0x[0-9a-fA-F]{40}(?![0-9a-fA-F])')
B58_RE = re.compile(r'(?<![1-9A-HJ-NP-Za-km-z])[1-9A-HJ-NP-Za-km-z]{32,44}(?![1-9A-HJ-NP-Za-km-z])')

# 地址簿有但按设计不入运行时标签的条目（每条独立说明，禁止集合式豁免）。
ALLOW_BOOK_ONLY = {
    # BN111 的 ProgramData 账户：只用于绑定可升级程序实现，不是可查询的实体/设施标签。
    'Df3ssK1ni8GzEoFuQyn4cQfC5mGZykebTERTT6EGQcFc',
    # BN111 的 upgrade_authority：仅作当次程序治理溯源指纹，地址簿未把它定性为公共实体。
    'FYtWDy1MfASNVWsqwC2CSu4xRbVcrd8RSC8Ts8qYJawB',
}
ALLOW_GEN_ONLY = set()  # 唯一真源建立后，运行时禁止出现地址簿之外的地址。
B58_STOPWORDS = {'NonfungiblePositionManager', 'TransparentUpgradeableProxy',
                 'AdminUpgradeabilityProxy', 'StatelessDeleGator'}


def extract(text):
    addrs = {match.lower() for match in EVM_RE.findall(text)}
    text_wo_evm = EVM_RE.sub(' ', text)
    for match in B58_RE.findall(text_wo_evm):
        if match not in B58_STOPWORDS and any(char.isdigit() for char in match):
            addrs.add(match)
    return addrs


def runtime_addresses():
    with open(RUNTIME, newline='', encoding='utf-8') as f:
        return {((row.get('address') or '').lower()
                 if (row.get('address') or '').startswith('0x') else (row.get('address') or ''))
                for row in csv.DictReader(f)}


def main():
    generated = subprocess.run([sys.executable, GEN, '--check'], capture_output=True, text=True)
    book_addrs = extract(open(BOOK, encoding='utf-8').read())
    csv_addrs = runtime_addresses()
    allow_book = {item.lower() if item.startswith('0x') else item for item in ALLOW_BOOK_ONLY}
    allow_gen = {item.lower() if item.startswith('0x') else item for item in ALLOW_GEN_ONLY}
    only_book = sorted(book_addrs - csv_addrs - allow_book)
    only_gen = sorted(csv_addrs - book_addrs - allow_gen)

    print(f'[check_manual_sync] 地址簿 {len(book_addrs)} 址 | 运行时 {len(csv_addrs)} 址 | '
          f'漏同步 {len(only_book)} | 幽灵 {len(only_gen)}')
    if generated.returncode:
        print('  生成物逐行校验失败：')
        print((generated.stdout + generated.stderr).strip())
    if only_book:
        print('  方向A 地址簿有、运行时没有（漏同步——入规范区，或逐址加 ALLOW_BOOK_ONLY 原因）：')
        for address in only_book:
            print(f'    - {address}')
    if only_gen:
        print('  方向B 运行时有、地址簿没有（幽灵条目——唯一真源违规）：')
        for address in only_gen:
            print(f'    - {address}')
    if generated.returncode or only_book or only_gen:
        return 1
    print('  一致 ✓')
    return 0


if __name__ == '__main__':
    sys.exit(main())
