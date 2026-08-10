#!/usr/bin/env python3
"""校验 address-book.md 单源与运行时 CSV 的行及复合键完全同步。"""
import csv
import os
import subprocess
import sys


_HERE = os.path.dirname(os.path.abspath(__file__))
BOOK = os.path.normpath(os.path.join(_HERE, '..', '..', 'references', 'address-book.md'))
GEN = os.path.join(_HERE, 'gen_manual_from_addressbook.py')
RUNTIME = os.path.join(_HERE, 'sources', 'manual_labels.csv')
sys.path.insert(0, _HERE)
from gen_manual_from_addressbook import source_rows

def _key(row):
    address = row.get('address') or ''
    return (row.get('chain') or '', address.lower() if address.startswith('0x') else address)


def source_keys():
    return {_key(row) for row in source_rows()}


def runtime_keys():
    with open(RUNTIME, newline='', encoding='utf-8') as f:
        return {_key(row) for row in csv.DictReader(f)}


def main():
    generated = subprocess.run([sys.executable, GEN, '--check'], capture_output=True, text=True)
    book_keys = source_keys()
    csv_keys = runtime_keys()
    only_book = sorted(book_keys - csv_keys)
    only_gen = sorted(csv_keys - book_keys)

    print(f'[check_manual_sync] 地址簿 {len(book_keys)} 复合键 | 运行时 {len(csv_keys)} 复合键 | '
          f'漏同步 {len(only_book)} | 幽灵 {len(only_gen)}')
    if generated.returncode:
        print('  生成物逐行校验失败：')
        print((generated.stdout + generated.stderr).strip())
    if only_book:
        print('  方向A 地址簿有、运行时没有（漏同步）：')
        for chain, address in only_book:
            print(f'    - ({chain}, {address})')
    if only_gen:
        print('  方向B 运行时有、地址簿没有（幽灵条目——唯一真源违规）：')
        for chain, address in only_gen:
            print(f'    - ({chain}, {address})')
    if generated.returncode or only_book or only_gen:
        return 1
    print('  一致 ✓')
    return 0


if __name__ == '__main__':
    sys.exit(main())
