#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补抓指定地址(top200 的关键对手方):detail + 近6个月流水 + 最早流水。
来源：FIL(Filecoin) 分析会话实战产物, 2026-07。
用法: python3 fetch_extra.py --data-dir <案目录/data> extra_addrs.txt
"""
import argparse
from fetch_data import configure_data_dir, fetch_address, initialize_data_dirs

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("addresses_file")
    args = parser.parse_args()
    configure_data_dir(args.data_dir)
    initialize_data_dirs()
    with open(args.addresses_file) as f:
        addrs = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    for i, a in enumerate(addrs, 1):
        fetch_address(a, f"extra-{i}/{len(addrs)}")
