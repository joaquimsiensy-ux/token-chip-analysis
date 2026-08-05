#!/usr/bin/env python3
"""Validate collector-native provenance and atomically emit evm-channel-receipt/v2."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from channels_preflight import (
    RECEIPT_SCHEMA,
    ChannelsPreflightError,
    _csv_stats,
    _file_fingerprints,
    _csv_collector_provenance,
    _v2_stats,
    _v2_provenance,
)


def make_receipt(data, fmt, token, lo, hi, tag, *, collector_receipt=None,
                 empty_proof=None):
    path = Path(data).resolve()
    if fmt == "v1csv":
        if not path.is_file():
            raise ChannelsPreflightError(f"v1csv 数据文件不存在: {path}")
        rows, min_block, max_block = _csv_stats(path)
        if not collector_receipt:
            raise ChannelsPreflightError(
                "legacy CSV 不能从数据文件自证 token/区间完整性；缺 --collector-receipt")
        provenance = _csv_collector_provenance(collector_receipt, path, token, lo, hi)
    elif fmt == "v2":
        if not path.is_dir():
            raise ChannelsPreflightError(f"v2 数据目录不存在: {path}")
        rows, min_block, max_block = _v2_stats(path)
        provenance = _v2_provenance(path, token, lo, hi)
    else:
        raise ChannelsPreflightError("format 必须是 v1csv|v2")
    if not token.strip() or not tag.strip():
        raise ChannelsPreflightError("token/tag 不得为空")
    if lo >= hi:
        raise ChannelsPreflightError("lo 必须小于 hi")
    if empty_proof is not None:
        raise ChannelsPreflightError("--empty-proof 自报文字已废止；空段必须由采集器完成回执证明")
    if rows and (min_block is None or max_block is None
                 or min_block < lo or max_block >= hi):
        raise ChannelsPreflightError(
            f"数据块范围 [{min_block},{max_block}] 越过声明区间 [{lo},{hi})")
    payload = {
        "schema": RECEIPT_SCHEMA,
        "status": "PASS",
        "producer": "make_channel_receipt.py/v1",
        "tag": tag.strip(),
        "token": token.strip(),
        "lo": lo,
        "hi": hi,
        "data_path": str(path),
        "format": fmt,
        "rows": rows,
        "min_block": min_block,
        "max_block": max_block,
        "files": _file_fingerprints(path, fmt),
        "provenance": provenance,
    }
    return payload


def atomic_write(path, payload):
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.parent / f".{target.name}.tmp.{os.getpid()}"
    try:
        with tmp.open("x", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, target)
        try:
            fd = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        except OSError:
            pass
    finally:
        if tmp.exists():
            tmp.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True)
    parser.add_argument("--format", required=True, choices=("v1csv", "v2"))
    parser.add_argument("--token", required=True)
    parser.add_argument("--lo", required=True, type=int)
    parser.add_argument("--hi", required=True, type=int)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--empty-proof")
    parser.add_argument("--collector-receipt",
                        help="v1csv 必填：采集器成功收尾时直接产生的完成回执")
    args = parser.parse_args(argv)
    try:
        payload = make_receipt(args.data, args.format, args.token, args.lo, args.hi,
                               args.tag, collector_receipt=args.collector_receipt,
                               empty_proof=args.empty_proof)
        atomic_write(args.out, payload)
    except (OSError, ChannelsPreflightError) as exc:
        parser.exit(2, f"BLOCK: {exc}\n")
    print(json.dumps({"status": "PASS", "receipt": str(Path(args.out).resolve()),
                      "rows": payload["rows"], "min_block": payload["min_block"],
                      "max_block": payload["max_block"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
