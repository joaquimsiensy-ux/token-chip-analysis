#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补抓指定地址(top200 的关键对手方):detail + 近6个月流水 + 最早流水。
来源：FIL(Filecoin) 分析会话实战产物, 2026-07。
用法: python3 fetch_extra.py extra_addrs.txt   (每行一个地址,# 开头为注释;复用 fetch_data.py 的抓取函数)
"""
import sys
from fetch_data import fetch_address

if __name__ == "__main__":
    with open(sys.argv[1]) as f:
        addrs = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    for i, a in enumerate(addrs, 1):
        fetch_address(a, f"extra-{i}/{len(addrs)}")
