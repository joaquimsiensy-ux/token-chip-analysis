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
    "token-analyze-1.md",
    "token-analyze-2.md",
    "token-analyze.md",
}
RETIRED = {"collect-data.md", "token-easy-analysis.md", "token-update.md"}
MIGRATION_CHANGED = {"token-analyze-1.md", "token-analyze-2.md"}
MIGRATION_NEEDLES = {
    "token-analyze-1.md": ("distribution_scan.json", "handoff/v3"),
    "token-analyze-2.md": ("a4-seal/v4", "G11", "只支持 full"),
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
    retired_present = sorted(name for name in RETIRED if (DEPLOYED / name).is_file())

    for source in staging_files:
        deployed = DEPLOYED / source.name
        if not deployed.is_file():
            failures.append(f"部署版缺失：{deployed}")
            continue
        source_hash = sha256(source)
        deployed_hash = sha256(deployed)
        if source_hash != deployed_hash:
            if source.name not in MIGRATION_CHANGED:
                failures.append(
                    f"SHA-256 不一致：{source.name} staging={source_hash} deployed={deployed_hash}"
                )
            else:
                text = source.read_text(encoding="utf-8")
                missing = [x for x in MIGRATION_NEEDLES[source.name] if x not in text]
                if missing:
                    failures.append(f"待部署迁移命令缺新契约 {source.name}: {missing}")

    if failures:
        print("FAIL: commands-staging 与已部署命令不一致")
        for failure in failures:
            print(f"- {failure}")
        return 1

    pending = sorted(name for name in MIGRATION_CHANGED
                     if (DEPLOYED / name).is_file()
                     and sha256(STAGING / name) != sha256(DEPLOYED / name))
    if pending:
        print(f"PASS: staging 新契约已守护；待 Fable 部署同步 {pending}")
    elif retired_present:
        print(
            f"PASS: {len(staging_files)} 份 staging 命令清单正确；"
            f"部署侧待验收后删除退役文件 {retired_present}"
        )
    else:
        print(f"PASS: {len(staging_files)} 份 staging/部署命令 SHA-256 逐文件一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
