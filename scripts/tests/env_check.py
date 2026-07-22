#!/usr/bin/env python3
"""环境一致性校验（A4 依赖锁的活体守卫，2026-07-22）。

对照 requirements.lock 校验关键依赖的已装版本：缺失或版本不一致 → FAIL。
目的：防"pip 悄悄升级了某库，旧脚本行为漂移"——数字工作流里版本漂移=对账事故
候选。库升级的正规流程见 pyproject.toml 头注（先跑全家桶+基线对表，再更新 lock）。

只校验 KEY_PKGS（引擎/采集/测试核心）——lock 里的传递依赖不逐一较真，
避免系统级 Python 里无关包的噪音把 gate 弄狼来了。
"""
import os, sys
from importlib import metadata

HERE = os.path.dirname(os.path.abspath(__file__))
LOCK = os.path.join(HERE, "..", "..", "requirements.lock")

KEY_PKGS = ["duckdb", "pyarrow", "pandas", "numpy", "hypersync", "requests",
            "networkx", "rustworkx", "hypothesis", "psutil", "matplotlib",
            "httpx", "tenacity", "msgspec"]


def main():
    if not os.path.exists(LOCK):
        print("FAIL: requirements.lock 不存在（依赖锁未建立）")
        return 1
    locked = {}
    for line in open(LOCK):
        line = line.strip()
        if "==" in line and not line.startswith("#"):
            name, ver = line.split("==", 1)
            locked[name.lower().replace("_", "-")] = ver
    bad = []
    for pkg in KEY_PKGS:
        want = locked.get(pkg.lower())
        if want is None:
            bad.append(f"{pkg}: lock 里没有（先补 lock）")
            continue
        try:
            got = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            bad.append(f"{pkg}: 未安装（lock 要求 {want}）")
            continue
        if got != want:
            bad.append(f"{pkg}: 已装 {got} ≠ lock {want}")
    if bad:
        print("FAIL: 环境与依赖锁不一致——" + "; ".join(bad))
        print("（有意升级请走 pyproject.toml 头注流程：全家桶+基线对表过了再更新 lock）")
        return 1
    print(f"PASS: {len(KEY_PKGS)} 个关键依赖与 requirements.lock 一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
