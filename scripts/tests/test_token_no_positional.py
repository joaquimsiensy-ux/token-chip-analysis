#!/usr/bin/env python3
"""F-04/F-07 回归：自动枚举现役 HyperSync 入口并禁止命令行明文 token。"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import re
import tempfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
EVM = ROOT / "scripts" / "evm"
MANIFEST = ROOT / "scripts" / "tests" / "invariant_manifest.json"
SENTINEL = "plaintext-secret"


def enumerate_hypersync_entrypoints():
    """用 SDK、endpoint、正式登记三路证据的并集生成测试分母。"""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    registered = {
        ROOT / rel for rel in manifest.get("formal_entrypoints", [])
        if isinstance(rel, str) and rel.startswith("scripts/evm/")
    }
    found = set()
    for path in EVM.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        sdk_import = re.search(r"(?m)^\s*(?:import\s+hypersync\b|from\s+hypersync\b)", source)
        endpoint_collector = path.name.startswith("fetch_") and (
            "hypersync.xyz" in source or "hypersync" in path.stem.lower())
        registered_hypersync = path in registered and "hypersync" in path.stem.lower()
        if sdk_import or endpoint_collector or registered_hypersync:
            found.add(path)
    return sorted(found)


def load(path):
    name = path.stem + "_token_contract"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def expect_parse_fail_without_secret(mod, args):
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            mod.parse_args(args)
        except SystemExit as exc:
            assert exc.code != 0
        else:
            raise AssertionError("旧位置参数 token 竟通过解析")
    emitted = stdout.getvalue() + stderr.getvalue()
    assert SENTINEL not in emitted, (
        f"{mod.__name__} 将 sentinel secret 写入 stdout/stderr: {emitted!r}")


def main():
    paths = enumerate_hypersync_entrypoints()
    assert len(paths) >= 4, [str(path.relative_to(ROOT)) for path in paths]
    modules = {path.stem: load(path) for path in paths}
    required = {
        "fetch_hypersync", "fetch_hypersync_logs", "fetch_hypersync_v2", "fetch_pool_swaps",
    }
    assert required <= set(modules), sorted(modules)

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        explicit = root / "explicit.token"
        explicit.write_text(" explicit-token \n", encoding="utf-8")
        default = root / "default.token"
        default.write_text(" default-token \n", encoding="utf-8")
        out = root / "out.csv"
        common = {
            "fetch_hypersync": ["0", "--url", "http://fixture", "--token-addr",
                                "0x" + "1" * 40, "--out", str(out)],
            "fetch_hypersync_logs": ["0", "--url", "http://fixture", "--addr",
                                     "0x" + "1" * 40, "--out", str(out)],
            "fetch_hypersync_v2": ["0", "--url", "http://fixture", "--token-addr",
                                   "0x" + "1" * 40, "--outdir", str(root / "v2")],
            "fetch_pool_swaps": ["--pool", "0x" + "1" * 40, "--from-block", "10",
                                 "--to-block", "11", "--out", str(out)],
        }
        for name, mod in modules.items():
            assert name in common, f"新 HyperSync 入口 {name} 尚未补测试参数夹具"
            expect_parse_fail_without_secret(mod, [SENTINEL, *common[name]])
            expect_parse_fail_without_secret(mod, [*common[name], SENTINEL])

            with mock.patch.dict(os.environ, {"HYPERSYNC_TOKEN": "env-token"}, clear=False):
                args = mod.parse_args([*common[name], "--token-file", str(explicit)])
                assert args.token == "explicit-token", f"{name} 显式文件没有覆盖环境变量"
                args = mod.parse_args(common[name])
                assert args.token == "env-token", f"{name} 未读取 HYPERSYNC_TOKEN"

            with mock.patch.object(mod, "DEFAULT_TOKEN_FILE", str(default)), \
                    mock.patch.dict(os.environ, {}, clear=True):
                args = mod.parse_args(common[name])
                assert args.token == "default-token", f"{name} 未回落默认 token 文件"

            empty = root / f"{name}.empty"
            empty.write_text("", encoding="utf-8")
            with mock.patch.dict(os.environ, {}, clear=True):
                for bad_path in (empty, root / f"{name}.missing"):
                    with contextlib.redirect_stdout(io.StringIO()), \
                            contextlib.redirect_stderr(io.StringIO()):
                        try:
                            mod.parse_args([*common[name], "--token-file", str(bad_path)])
                        except SystemExit as exc:
                            assert exc.code == 2
                        else:
                            raise AssertionError(f"{name} 放行缺失或空 token 文件: {bad_path}")

    names = ", ".join(sorted(modules))
    print(f"PASS: 自动枚举 {len(modules)} 个 HyperSync 入口；拒绝位置 token、输出无 secret、优先序三层闭合: {names}")


if __name__ == "__main__":
    main()
