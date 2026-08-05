#!/usr/bin/env python3
"""校验 commands-staging 与 Claude Code 已部署 slash commands 逐文件一致。"""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
STAGING = ROOT / "commands-staging"
DEPLOYED = Path.home() / ".claude" / "commands"
EXPECTED = {
    "collect-data.md",
    "token-analyze-1.md",
    "token-analyze-2.md",
    "token-analyze.md",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    if not DEPLOYED.is_dir():
        print(f"SKIP: 部署目录不存在（异机允许）：{DEPLOYED}")
        return 0

    failures: list[str] = []
    staging_files = sorted(STAGING.glob("*.md"))
    if not staging_files:
        failures.append(f"staging 中没有命令文件：{STAGING}")
    actual = {path.name for path in staging_files}
    if actual != EXPECTED:
        failures.append(
            "staging 命令清单不符："
            f"expected={sorted(EXPECTED)} actual={sorted(actual)}"
        )

    for source in staging_files:
        deployed = DEPLOYED / source.name
        if not deployed.is_file():
            failures.append(f"部署版缺失：{deployed}")
            continue
        source_hash = sha256(source)
        deployed_hash = sha256(deployed)
        if source_hash != deployed_hash:
            failures.append(
                f"SHA-256 不一致：{source.name} staging={source_hash} deployed={deployed_hash}"
            )

    if failures:
        print("FAIL: commands-staging 与已部署命令不一致")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"PASS: {len(staging_files)} 份 staging/部署命令 SHA-256 逐文件一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
