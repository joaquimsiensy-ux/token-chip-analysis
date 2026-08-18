#!/usr/bin/env python3
"""校验 commands-staging 与 Claude Code 已部署 slash commands 逐文件一致。"""

from __future__ import annotations

import hashlib
import json
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
    "token-analyze-3.md",
    "token-analyze.md",
}
RETIRED = {"collect-data.md", "token-easy-analysis.md", "token-update.md"}
CONTRACT_MANIFEST_REL = Path("scripts/tests/contract_manifest.json")
COMMAND_AUTHORITY_PREFIX = "commands-staging/"


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


def load_command_contracts(root: Path) -> tuple[list[dict], list[str]]:
    """从 canonical manifest 读取 command required/banned 契约；禁止空跑。"""
    path = root / CONTRACT_MANIFEST_REL
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [], [f"command 契约注册表无法读取：{path}: {exc}"]
    if not isinstance(manifest, dict):
        return [], [f"command 契约注册表顶层不是对象：{path}"]
    raw_contracts = manifest.get("contracts")
    if not isinstance(raw_contracts, list) or not raw_contracts:
        return [], [f"command 契约注册表为空：{path}"]

    contracts: list[dict] = []
    failures: list[str] = []
    for index, contract in enumerate(raw_contracts, 1):
        if not isinstance(contract, dict):
            failures.append(f"command 契约项不是对象：contracts[{index}]")
            continue
        authority = contract.get("authority_file")
        if not isinstance(authority, str) or not authority.startswith(
                COMMAND_AUTHORITY_PREFIX):
            continue
        contract_id = contract.get("id")
        kind = contract.get("kind")
        needle = contract.get("needle")
        if (not isinstance(contract_id, str) or kind not in {"required", "banned"}
                or not isinstance(needle, str) or not needle):
            failures.append(f"command 契约字段非法：contracts[{index}]")
            continue
        contracts.append(contract)
    if not contracts:
        failures.append(f"command 契约注册表没有 {COMMAND_AUTHORITY_PREFIX} 契约：{path}")
    return contracts, failures


def check_command_semantics(root: Path, deployed: Path) -> list[str]:
    """对 staging 与 deployed 实物双侧执行 manifest 语义契约。"""
    contracts, failures = load_command_contracts(root)
    for contract in contracts:
        authority = contract["authority_file"]
        targets = (
            ("staging", root / authority),
            ("deployed", deployed / Path(authority).name),
        )
        for side, path in targets:
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                failures.append(
                    f"command 语义实物无法读取 {contract['id']} {side}: {path}: {exc}"
                )
                continue
            needle = contract["needle"]
            if contract["kind"] == "required" and needle not in text:
                failures.append(
                    f"command required needle 缺失 {contract['id']} {side}: "
                    f"{path} -> {needle}"
                )
            if contract["kind"] == "banned" and needle in text:
                failures.append(
                    f"command banned needle 回捡 {contract['id']} {side}: "
                    f"{path} -> {needle}"
                )
    return failures


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
    # 语义层只叠加，不改变也不豁免上面的逐文件 SHA 严判。
    failures.extend(check_command_semantics(root, deployed))
    return failures


def main(*, root: Path | None = None, deployed: Path | None = None,
         home: Path | None = None) -> int:
    resolved_root = (ROOT if root is None else root).resolve()
    resolved_deployed = (DEPLOYED if deployed is None else deployed).resolve()
    # 即使非 canonical checkout 会因缺部署目录走显式 SKIP，manifest 缺失/空/坏
    # 也必须先 FAIL，不能借 SKIP 把语义层静默关掉。
    _, manifest_failures = load_command_contracts(resolved_root)
    if manifest_failures:
        for failure in manifest_failures:
            print(f"- {failure}")
        print("FAIL: command 契约注册表不可用")
        return 1
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
