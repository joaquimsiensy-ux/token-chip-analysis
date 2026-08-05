#!/usr/bin/env python3
"""从 address-book.md 的规范 CSV 区确定性生成运行时 manual_labels.csv。"""
import argparse
import csv
import io
import os
import sys


_HERE = os.path.dirname(os.path.abspath(__file__))
BOOK = os.path.normpath(os.path.join(_HERE, '..', '..', 'references', 'address-book.md'))
OUTPUT = os.path.join(_HERE, 'sources', 'manual_labels.csv')
BLOCK_START = '```manual-labels-csv'
BLOCK_END = '```'
FIELDS = [
    'address', 'chain', 'name', 'category', 'tier', 'source', 'added_date', 'evidence',
    'risk_flags', 'merge_policy', 'balance_policy', 'source_snapshot_at', 'verified_at',
    'status', 'raw_labels',
]
CHAINS = {'eth', 'bsc', 'base', 'arbitrum', 'robinhood', 'sol'}


def _read_block():
    with open(BOOK, encoding='utf-8') as f:
        lines = f.read().splitlines()
    starts = [i for i, line in enumerate(lines) if line.strip() == BLOCK_START]
    if len(starts) != 1:
        raise ValueError(f'address-book.md 必须且只能有一个 {BLOCK_START} 规范区')
    start = starts[0] + 1
    ends = [i for i in range(start, len(lines)) if lines[i].strip() == BLOCK_END]
    if not ends:
        raise ValueError('manual-labels-csv 规范区未闭合')
    return '\n'.join(lines[start:ends[0]]) + '\n'


def expected_rows():
    reader = csv.DictReader(io.StringIO(_read_block()))
    if reader.fieldnames != FIELDS:
        raise ValueError(f'规范区表头错误：{reader.fieldnames!r}')
    rows = []
    seen = set()
    for line_no, raw in enumerate(reader, start=2):
        row = {field: (raw.get(field) or '').strip() for field in FIELDS}
        missing = [field for field in ('address', 'chain', 'name', 'category', 'tier')
                   if not row[field]]
        if missing:
            raise ValueError(f'规范区 CSV 第 {line_no} 行缺字段：{missing}')
        if row['chain'] not in CHAINS:
            raise ValueError(f'规范区 CSV 第 {line_no} 行链名非法：{row["chain"]}')
        key = (row['address'].lower() if row['address'].startswith('0x') else row['address'],
               row['chain'])
        if key in seen:
            raise ValueError(f'规范区 CSV 第 {line_no} 行重复 address+chain：{key}')
        seen.add(key)
        row['source'] = row['source'] or 'addressbook'
        rows.append(row)
    if not rows:
        raise ValueError('manual-labels-csv 规范区为空')
    return rows


def _read_output_rows():
    if not os.path.exists(OUTPUT):
        return None, None
    with open(OUTPUT, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, [{field: (row.get(field) or '').strip() for field in FIELDS}
                                   for row in reader]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='只校验生成物与地址簿规范区一致')
    args = parser.parse_args()
    try:
        rows = expected_rows()
    except (OSError, ValueError, csv.Error) as exc:
        print(f'[gen_manual] FAIL: {exc}', file=sys.stderr)
        return 1

    if args.check:
        fields, current = _read_output_rows()
        if fields != FIELDS or current != rows:
            print('[gen_manual] FAIL: sources/manual_labels.csv 已漂移；请重跑生成器',
                  file=sys.stderr)
            return 1
        print(f'[gen_manual] PASS: {len(rows)} 行与 address-book.md 规范区一致')
        return 0

    with open(OUTPUT, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    print(f'manual_labels.csv rows: {len(rows)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
