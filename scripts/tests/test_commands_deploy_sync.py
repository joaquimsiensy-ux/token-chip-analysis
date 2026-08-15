#!/usr/bin/env python3
"""校验 commands-staging 与 Claude Code 已部署 slash commands 逐文件一致。"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import pwd
import sys


ROOT = Path(__file__).resolve().parents[2]
ACCOUNT_HOME = Path(pwd.getpwuid(os.getuid()).pw_dir)
DEPLOYED = ACCOUNT_HOME / ".claude" / "commands"
EXPECTED = {
    "token-analyze-1.md",
    "token-analyze-2.md",
    "token-analyze.md",
}
RETIRED = {"collect-data.md", "token-easy-analysis.md", "token-update.md"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_canonical_checkout(root: Path, home: Path | None = None) -> bool:
    """精确识别正式部署机上的规范 skill checkout。"""
    resolved_home = ACCOUNT_HOME if home is None else home
    canonical = resolved_home / ".claude" / "skills" / "token-chip-analysis"
    return root.resolve() == canonical.resolve()


def check_deploy_sync(root: Path, deployed: Path) -> list[str]:
    """只读校验 staging 与 deployed，返回全部失败原因。"""
    failures: list[str] = []
    staging = root / "commands-staging"
    if not deployed.is_dir():
        failures.append(f"部署目录不存在：{deployed}")
    staging_files = sorted(staging.glob("*.md"))
    if not staging_files:
        failures.append(f"staging 中没有命令文件：{staging}")
    actual = {path.name for path in staging_files}
    if actual != EXPECTED:
        failures.append(
            "staging 命令清单不符："
            f"expected={sorted(EXPECTED)} actual={sorted(actual)}"
        )
    for source in staging_files:
        deployed_file = deployed / source.name
        if not deployed_file.is_file():
            failures.append(f"部署版缺失：{deployed_file}")
            continue
        source_hash = sha256(source)
        deployed_hash = sha256(deployed_file)
        if source_hash != deployed_hash:
            failures.append(
                f"SHA-256 不一致：{source.name} staging={source_hash} deployed={deployed_hash}"
            )
    return failures


def main(*, root: Path | None = None, deployed: Path | None = None,
         home: Path | None = None) -> int:
    resolved_root = (ROOT if root is None else root).resolve()
    resolved_deployed = (DEPLOYED if deployed is None else deployed).resolve()
    if not resolved_deployed.is_dir() and not is_canonical_checkout(resolved_root, home):
        print(f"SKIP_NON_CANONICAL_CHECKOUT: {resolved_root}")
        return 0

    failures = check_deploy_sync(resolved_root, resolved_deployed)

    if failures:
        for failure in failures:
            print(f"- {failure}")
        print("FAIL: commands-staging 与已部署命令不一致")
        return 1

    staging = resolved_root / "commands-staging"
    staging_files = sorted(staging.glob("*.md"))
    retired_present = sorted(
        name for name in RETIRED if (resolved_deployed / name).is_file()
    )
    if retired_present:
        print(
            f"PASS: {len(staging_files)} 份 staging 命令清单正确；"
            f"部署侧待验收后删除退役文件 {retired_present}"
        )
    else:
        print(f"PASS: {len(staging_files)} 份 staging/部署命令 SHA-256 逐文件一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
