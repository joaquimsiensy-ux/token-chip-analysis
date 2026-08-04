#!/usr/bin/env python3
"""Strict shared preflight for every EVM replay engine.

The supply equation only proves algebra over rows that were read.  This gate proves the
declared channel set itself is present, typed, receipted, contiguous, and covers the
explicit global bounds before any replay engine consumes events.
"""
from __future__ import annotations

import csv
import glob
import hashlib
import json
import os
from pathlib import Path


SCHEMA = "evm-channels/v2"
RECEIPT_SCHEMA = "evm-channel-receipt/v2"
COLLECTOR_RECEIPT_SCHEMA = "evm-collector-run/v1"
PREFLIGHT_SCHEMA = "evm-channels-preflight/v1"


class ChannelsPreflightError(ValueError):
    pass


def _int(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ChannelsPreflightError(f"{label} 必须是整数")
    return value


def _resolve(base: Path, value, label):
    if not isinstance(value, str) or not value.strip():
        raise ChannelsPreflightError(f"{label} 必须是非空路径")
    p = Path(value)
    return (p if p.is_absolute() else base / p).resolve()


def _csv_stats(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = set(reader.fieldnames or [])
        legacy = {"block", "ts", "tx", "from", "to", "uniqueId"} <= header \
            and ("value" in header or "value_raw" in header)
        standard8 = {"block", "ts", "tx", "log_index", "from", "to",
                     "value_raw", "block_hash"} <= header
        if not (legacy or standard8):
            raise ChannelsPreflightError(f"CSV header 非 legacy7/standard8: {sorted(header)}")
        rows = 0
        blocks = []
        for row in reader:
            if not row or not any(row.values()):
                continue
            rows += 1
            try:
                blocks.append(int(row.get("block")))
            except (TypeError, ValueError):
                pass
    return rows, (min(blocks) if blocks else None), (max(blocks) if blocks else None)


def _v2_stats(path: Path):
    logs = sorted(glob.glob(str(path / "run_*" / "logs.parquet")))
    blocks = sorted(glob.glob(str(path / "run_*" / "blocks.parquet")))
    if not logs or not blocks:
        raise ChannelsPreflightError("v2 目录缺 run_*/logs.parquet 或 blocks.parquet")
    try:
        import duckdb
        con = duckdb.connect()
        # read_parquet does not accept a parameterized list in all supported DuckDB versions.
        esc = "[" + ",".join("'" + x.replace("'", "''") + "'" for x in logs) + "]"
        cols = {r[0] for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet({esc}, union_by_name=true)").fetchall()}
        required = {"block_number", "log_index", "transaction_hash", "topic1", "topic2", "data"}
        if not required <= cols:
            raise ChannelsPreflightError(f"logs parquet schema 缺字段: {sorted(required - cols)}")
        rows, lo, hi = con.execute(
            f"SELECT COUNT(*), MIN(block_number), MAX(block_number) "
            f"FROM read_parquet({esc}, union_by_name=true)").fetchone()
        return int(rows), lo, hi
    except ChannelsPreflightError:
        raise
    except Exception as e:
        raise ChannelsPreflightError(f"v2 parquet 不可读: {e}") from e


def _sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _file_fingerprints(path: Path, fmt: str):
    """返回 receipt 绑定的精确文件集；v2 同时绑定 logs/blocks。"""
    if fmt == "v1csv":
        files = [path]
        base = path.parent
    elif fmt == "v2":
        files = sorted(
            [Path(x) for x in glob.glob(str(path / "run_*" / "logs.parquet"))]
            + [Path(x) for x in glob.glob(str(path / "run_*" / "blocks.parquet"))]
        )
        base = path
    else:
        raise ChannelsPreflightError(f"format 必须是 v1csv|v2: {fmt}")
    if not files:
        raise ChannelsPreflightError(f"{fmt} 无可绑定数据文件: {path}")
    return [{"path": str(p.relative_to(base)), "size": p.stat().st_size,
             "sha256": _sha256_file(p)} for p in files]


def _csv_collector_provenance(receipt_path, data_path, token, lo, hi):
    """Validate a collector-native CSV completion receipt; CLI assertions are not evidence."""
    rp = Path(receipt_path).resolve()
    if rp.is_symlink() or not rp.is_file():
        raise ChannelsPreflightError(f"CSV 采集回执不存在或为符号链接: {rp}")
    try:
        d = json.loads(rp.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ChannelsPreflightError(f"CSV 采集回执不可读: {exc}") from exc
    if d.get("schema") != COLLECTOR_RECEIPT_SCHEMA or d.get("status") != "PASS":
        raise ChannelsPreflightError("CSV 采集回执非 evm-collector-run/v1 PASS")
    collector = d.get("collector")
    expected_script = Path(__file__).with_name("fetch_hypersync.py")
    if not isinstance(collector, dict) or collector.get("path") != "fetch_hypersync.py" \
            or collector.get("sha256") != _sha256_file(expected_script):
        raise ChannelsPreflightError("CSV 采集回执未绑定当前受支持采集器")
    q = d.get("query")
    if not isinstance(q, dict) or str(q.get("token", "")).lower() != str(token).lower() \
            or q.get("query_schema") != "erc20-transfer-fields/v2" \
            or q.get("requested_from") != lo or q.get("requested_to") != hi \
            or not str(q.get("provider_url", "")).strip():
        raise ChannelsPreflightError("CSV 采集回执的 token/query/bounds 与通道不绑定")
    completion = d.get("completion")
    if not isinstance(completion, dict) or completion.get("reason") not in {
            "requested_bound_reached", "archive_height_reached"} \
            or completion.get("next_block") != hi:
        raise ChannelsPreflightError("CSV 采集回执缺可验的分页/区间完成原因")
    rows, min_block, max_block = _csv_stats(Path(data_path))
    output = d.get("output")
    actual = {"path": str(Path(data_path).resolve()), "size": Path(data_path).stat().st_size,
              "sha256": _sha256_file(Path(data_path)), "rows": rows,
              "min_block": min_block, "max_block": max_block}
    if output != actual:
        raise ChannelsPreflightError("CSV 采集回执未绑定当前数据文件")
    return {"kind": "collector-native-csv", "receipt_path": str(rp),
            "receipt_sha256": _sha256_file(rp), "query": q, "completion": completion}


def _v2_provenance(path, token, lo, hi):
    """Revalidate every native done receipt and exact contiguous requested coverage."""
    root = Path(path).resolve()
    identity_path = root / "capture_identity.json"
    if identity_path.is_symlink() or not identity_path.is_file():
        raise ChannelsPreflightError("v2 采集根目录缺不可变 capture_identity.json")
    try:
        from fetch_hypersync_v2 import capture_identity, validate_done_manifest
        identity_manifest = json.loads(identity_path.read_text(encoding="utf-8"))
        first_url = identity_manifest.get("url") if isinstance(identity_manifest, dict) else None
        if identity_manifest != capture_identity(token, first_url):
            raise ValueError("capture_identity.json 与 token/url/query/collector 不一致")
    except Exception as exc:
        raise ChannelsPreflightError(f"v2 capture identity 校验失败: {exc}") from exc
    done_paths = sorted(root.glob("run_*/done.json"))
    run_dirs = {p.parent for p in root.glob("run_*/logs.parquet")} \
        | {p.parent for p in root.glob("run_*/blocks.parquet")}
    if not done_paths or run_dirs != {p.parent for p in done_paths}:
        raise ChannelsPreflightError("v2 采集根目录的 run 与 done.json 不完整对应")
    intervals, receipts, identity = [], [], None
    for done_path in done_paths:
        try:
            raw = json.loads(done_path.read_text(encoding="utf-8"))
            current_identity = (str(raw.get("token", "")).lower(), raw.get("url"),
                                raw.get("query_schema"))
            if identity is None:
                identity = current_identity
            if current_identity != identity or current_identity[0] != str(token).lower():
                raise ValueError("done token/url/query_schema 混入不同 capture identity")
            frm, end = int(raw["from_block"]), int(raw["to_block"])
            validate_done_manifest(done_path, int(raw["capture_from"]), end,
                                   token, raw["url"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ChannelsPreflightError(f"v2 done 回执校验失败 {done_path}: {exc}") from exc
        intervals.append((frm, end))
        receipts.append({"path": str(done_path.relative_to(root)),
                         "sha256": _sha256_file(done_path),
                         "from_block": frm, "to_block": end})
    intervals.sort()
    if intervals[0][0] != lo or intervals[-1][1] != hi:
        raise ChannelsPreflightError(
            f"v2 done 区间未覆盖声明边界: {intervals[0][0]}..{intervals[-1][1]} != {lo}..{hi}")
    for prev, nxt in zip(intervals, intervals[1:]):
        if prev[1] != nxt[0]:
            raise ChannelsPreflightError(f"v2 done 区间有洞或重叠: {prev} -> {nxt}")
    return {"kind": "hypersync-v2-native",
            "identity_manifest": {"path": "capture_identity.json",
                                  "sha256": _sha256_file(identity_path)}, "identity": {
                "token": identity[0], "provider_url": identity[1], "query_schema": identity[2]},
            "completion": {"reason": "contiguous_done_receipts", "lo": lo, "hi": hi},
            "done_receipts": receipts}


def _write_preflight(out_dir, payload):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    target = out / "channels_preflight.json"
    tmp = out / ".channels_preflight.json.tmp"
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, target)


def preflight_channels(manifest_path, out_dir, *, allowed_formats=None):
    manifest = Path(manifest_path).resolve()
    base = manifest.parent
    try:
        obj = json.loads(manifest.read_text(encoding="utf-8"))
        if not isinstance(obj, dict) or obj.get("schema") != SCHEMA:
            raise ChannelsPreflightError(f"schema 必须为 {SCHEMA}")
        token = str(obj.get("token", "")).strip()
        if not token:
            raise ChannelsPreflightError("token 不得为空")
        expected_from = _int(obj.get("expected_from"), "expected_from")
        expected_to = _int(obj.get("expected_to"), "expected_to")
        if expected_from >= expected_to:
            raise ChannelsPreflightError("expected_from 必须小于 expected_to")
        channels = obj.get("channels")
        if not isinstance(channels, list) or not channels:
            raise ChannelsPreflightError("channels 必须是非空数组")

        normalized = []
        seen_tags = set()
        for i, channel in enumerate(channels):
            if not isinstance(channel, dict):
                raise ChannelsPreflightError(f"channels[{i}] 必须是对象")
            tag = str(channel.get("tag", "")).strip()
            if not tag or tag in seen_tags:
                raise ChannelsPreflightError(f"channels[{i}].tag 为空或重复: {tag!r}")
            seen_tags.add(tag)
            lo = _int(channel.get("lo"), f"{tag}.lo")
            hi = _int(channel.get("hi"), f"{tag}.hi")
            if lo >= hi:
                raise ChannelsPreflightError(f"{tag} 区间非法: [{lo},{hi})")
            fmt = channel.get("format")
            if fmt not in {"v1csv", "v2"}:
                raise ChannelsPreflightError(f"{tag}.format 必须是 v1csv|v2")
            if allowed_formats and fmt not in allowed_formats:
                raise ChannelsPreflightError(f"{tag}.format={fmt} 不被当前引擎支持")
            path = _resolve(base, channel.get("path"), f"{tag}.path")
            if fmt == "v1csv":
                if not path.is_file():
                    raise ChannelsPreflightError(f"{tag} 声明文件不存在或类型错误: {path}")
                rows, min_block, max_block = _csv_stats(path)
            else:
                if not path.is_dir():
                    raise ChannelsPreflightError(f"{tag} 声明 v2 目录不存在或类型错误: {path}")
                rows, min_block, max_block = _v2_stats(path)
            files = _file_fingerprints(path, fmt)

            receipt_path = _resolve(base, channel.get("receipt"), f"{tag}.receipt")
            if not receipt_path.is_file():
                raise ChannelsPreflightError(f"{tag} receipt 不存在: {receipt_path}")
            try:
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            except Exception as e:
                raise ChannelsPreflightError(f"{tag} receipt 不可读: {e}") from e
            bound_path = _resolve(base, receipt.get("data_path"), f"{tag}.receipt.data_path")
            if fmt == "v1csv":
                provenance_obj = receipt.get("provenance")
                source_path = provenance_obj.get("receipt_path") if isinstance(provenance_obj, dict) else None
                provenance = _csv_collector_provenance(source_path, path, token, lo, hi)
            else:
                provenance = _v2_provenance(path, token, lo, hi)
            expected = {"schema": RECEIPT_SCHEMA, "status": "PASS", "tag": tag,
                        "token": token, "lo": lo, "hi": hi, "data_path": path,
                        "format": fmt, "rows": rows, "min_block": min_block,
                        "max_block": max_block, "files": files, "provenance": provenance}
            actual = {"schema": receipt.get("schema"), "status": receipt.get("status"),
                      "tag": receipt.get("tag"), "token": str(receipt.get("token", "")).strip(),
                      "lo": receipt.get("lo"), "hi": receipt.get("hi"),
                      "data_path": bound_path, "format": receipt.get("format"),
                      "rows": receipt.get("rows"), "min_block": receipt.get("min_block"),
                      "max_block": receipt.get("max_block"), "files": receipt.get("files"),
                      "provenance": receipt.get("provenance")}
            if isinstance(expected["token"], str) and expected["token"].startswith("0x"):
                expected["token"] = expected["token"].lower()
                actual["token"] = actual["token"].lower()
            if actual != expected:
                raise ChannelsPreflightError(f"{tag} receipt 与当前 token/bounds/path/rows 不绑定")
            normalized.append({**channel, "tag": tag, "lo": lo, "hi": hi,
                               "format": fmt, "path": str(path), "receipt": str(receipt_path),
                               "rows": rows, "min_block": min_block, "max_block": max_block})

        ordered = sorted(normalized, key=lambda c: (c["lo"], c["hi"], c["tag"]))
        if ordered[0]["lo"] != expected_from or ordered[-1]["hi"] != expected_to:
            raise ChannelsPreflightError(
                f"首尾未覆盖声明边界: actual=[{ordered[0]['lo']},{ordered[-1]['hi']}) "
                f"expected=[{expected_from},{expected_to})")
        for prev, nxt in zip(ordered, ordered[1:]):
            if nxt["lo"] != prev["hi"]:
                kind = "重叠" if nxt["lo"] < prev["hi"] else "区间洞"
                raise ChannelsPreflightError(
                    f"{kind}: {prev['tag']}=[{prev['lo']},{prev['hi']}) -> "
                    f"{nxt['tag']}=[{nxt['lo']},{nxt['hi']})")

        _write_preflight(out_dir, {"schema": PREFLIGHT_SCHEMA, "status": "PASS",
                                   "manifest": str(manifest), "token": token,
                                   "expected_from": expected_from, "expected_to": expected_to,
                                   "channels": [{k: c[k] for k in
                                                 ("tag", "path", "format", "lo", "hi", "rows",
                                                  "min_block", "max_block", "receipt")}
                                                for c in ordered]})
        return ordered
    except (OSError, json.JSONDecodeError, ChannelsPreflightError) as e:
        _write_preflight(out_dir, {"schema": PREFLIGHT_SCHEMA, "status": "BLOCK",
                                   "manifest": str(manifest), "error": str(e)})
        raise SystemExit(f"[channels preflight] BLOCK: {e}") from e
