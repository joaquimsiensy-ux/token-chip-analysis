#!/usr/bin/env python3
"""F-07 回归：三支 HyperSync 脚本禁用命令行明文 token。"""
import importlib.util
import os
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = {
    "fetch_hypersync": ROOT / "scripts" / "evm" / "fetch_hypersync.py",
    "fetch_hypersync_logs": ROOT / "scripts" / "evm" / "fetch_hypersync_logs.py",
    "fetch_pool_swaps": ROOT / "scripts" / "evm" / "fetch_pool_swaps.py",
}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name + "_token_contract", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def expect_parse_fail(mod, args):
    try:
        mod.parse_args(args)
    except SystemExit as exc:
        assert exc.code != 0
    else:
        raise AssertionError("旧位置参数 token 竟通过解析")


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td); token_file = root / "token"; token_file.write_text(" file-token \n")
        out = root / "out.csv"
        common = {
            "fetch_hypersync": ["0", "--url", "http://fixture", "--token-addr",
                                "0x" + "1" * 40, "--out", str(out)],
            "fetch_hypersync_logs": ["0", "--url", "http://fixture", "--addr",
                                     "0x" + "1" * 40, "--out", str(out)],
            "fetch_pool_swaps": ["--pool", "0x" + "1" * 40, "--from-block", "10",
                                 "--to-block", "11", "--out", str(out)],
        }
        for name, path in SCRIPTS.items():
            mod = load(name, path)
            expect_parse_fail(mod, ["plaintext-secret", *common[name]])
            with mock.patch.dict(os.environ, {"HYPERSYNC_TOKEN": "env-token"}, clear=False):
                args = mod.parse_args([*common[name], "--token-file", str(token_file)])
                assert args.token == "file-token", f"{name} 显式文件没有覆盖环境变量"
                args = mod.parse_args(common[name])
                assert args.token == "env-token", f"{name} 未读取 HYPERSYNC_TOKEN"
            empty = root / f"{name}.empty"; empty.write_text("")
            with mock.patch.dict(os.environ, {}, clear=True):
                expect_parse_fail(mod, [*common[name], "--token-file", str(empty)])
                expect_parse_fail(mod, [*common[name], "--token-file", str(root / "missing")])
    print("PASS: 三脚本拒绝位置 token，并遵守 token-file > 环境变量 > 默认文件")


if __name__ == "__main__":
    main()
