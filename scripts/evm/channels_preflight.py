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
import tempfile
from pathlib import Path


SCHEMA = "evm-channels/v2"
RECEIPT_SCHEMA = "evm-channel-receipt/v2"
COLLECTOR_RECEIPT_SCHEMA = "evm-collector-run/v2"
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


# 采集器脚本升级后，正版历史版本采的存量数据不应被"当前哈希"白名单追溯否定
# （NES 案实证：v6.39.5 正版 fetch_hypersync.py 产的 169 份 receipt 在脚本升级后
# 全数被拒，而数据完整性另有四查/供给闭合/时间抽查独立证明）。本表是显式静态
# 登记：每个哈希必须先在 skill 仓库 git 历史中考证到具体 commit 才准入表——
# `git show <rev>:scripts/evm/<name> | shasum -a 256` 逐条可复验；不提供任何
# 运行时扩表通道，伪造采集器仍然无法过闸。
_HISTORICAL_COLLECTOR_HASHES = {
    "fetch_hypersync.py": {
        # v6.39.5（commit 2ebd885d1a1364779338e02f8f30e991eec2302d）——NES 案
        # −1 段（2026-08-12）BSC/ETH 全量 CSV 通道的采集版本
        "d8113c590fe78e497364b15089215e82d0b061c413f80bb4600913f334f36b6d",
    },
    "fetch_sqd_evm.py": set(),
}


def _historical_script_hashes(name):
    return _HISTORICAL_COLLECTOR_HASHES.get(name, set())


def _sha256_prefix(path: Path, size: int):
    if isinstance(size, bool) or not isinstance(size, int) or size < 0 or size > path.stat().st_size:
        raise ChannelsPreflightError("collector segment prefix size 非法")
    h, left = hashlib.sha256(), size
    with path.open("rb") as f:
        while left:
            block = f.read(min(left, 8 * 1024 * 1024))
            if not block:
                raise ChannelsPreflightError("collector segment prefix 提前 EOF")
            h.update(block); left -= len(block)
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
    """Validate a chained native CSV receipt down to every historical file prefix."""
    rp, data = Path(receipt_path).resolve(), Path(data_path).resolve()
    if rp.is_symlink() or not rp.is_file():
        raise ChannelsPreflightError(f"CSV 采集回执不存在或为符号链接: {rp}")
    try:
        d = json.loads(rp.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ChannelsPreflightError(f"CSV 采集回执不可读: {exc}") from exc
    if d.get("schema") != COLLECTOR_RECEIPT_SCHEMA or d.get("status") != "PASS":
        raise ChannelsPreflightError("CSV 采集回执非 evm-collector-run/v2 PASS")
    collector = d.get("collector")
    if not isinstance(collector, dict):
        raise ChannelsPreflightError("CSV 采集回执缺 collector")
    name = collector.get("path")
    allowed = {x.name: x for x in (Path(__file__).with_name("fetch_hypersync.py"),
                                      Path(__file__).with_name("fetch_sqd_evm.py"))}
    expected_script = allowed.get(name)
    if expected_script is None or (
            collector.get("sha256") != _sha256_file(expected_script)
            and collector.get("sha256") not in _historical_script_hashes(name)):
        raise ChannelsPreflightError("CSV 采集回执未绑定当前受支持采集器")
    q = d.get("query")
    if not isinstance(q, dict) or str(q.get("token", "")).lower() != str(token).lower() \
            or q.get("query_schema") != "erc20-transfer-fields/v2" \
            or q.get("requested_from") != lo or q.get("requested_to") != hi \
            or not str(q.get("provider_url", "")).strip():
        raise ChannelsPreflightError("CSV 采集回执的 token/query/bounds 与通道不绑定")
    completion = d.get("completion")
    if not isinstance(completion, dict) or completion.get("reason") != "requested_bound_reached" \
            or isinstance(completion.get("next_block"), bool) \
            or not isinstance(completion.get("next_block"), int) \
            or completion.get("next_block") < hi:
        raise ChannelsPreflightError("CSV 采集回执缺 provider 可验的完成原因/目标上界")
    segments = d.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ChannelsPreflightError("CSV 采集回执缺不可伪造的 segment chain")
    cursor, prior_size = lo, -1
    for i, seg in enumerate(segments):
        if not isinstance(seg, dict) or seg.get("requested_from") != cursor \
                or isinstance(seg.get("requested_to"), bool) \
                or not isinstance(seg.get("requested_to"), int) \
                or seg["requested_to"] <= cursor \
                or isinstance(seg.get("provider_next_block"), bool) \
                or not isinstance(seg.get("provider_next_block"), int) \
                or seg["provider_next_block"] < seg["requested_to"]:
            raise ChannelsPreflightError(f"CSV segment[{i}] coverage/cursor 非法")
        prefix = seg.get("output_prefix")
        if not isinstance(prefix, dict) or not isinstance(prefix.get("size"), int) \
                or prefix["size"] <= prior_size \
                or prefix.get("sha256") != _sha256_prefix(data, prefix["size"]):
            raise ChannelsPreflightError(f"CSV segment[{i}] 历史前缀哈希不闭合")
        cursor, prior_size = seg["requested_to"], prefix["size"]
    if cursor != hi:
        raise ChannelsPreflightError("CSV segment chain 未连续覆盖完整声明区间")
    rows, min_block, max_block = _csv_stats(data)
    output = d.get("output")
    actual = {"path": str(data), "size": data.stat().st_size,
              "sha256": _sha256_file(data), "rows": rows,
              "min_block": min_block, "max_block": max_block}
    if output != actual or prior_size != actual["size"]:
        raise ChannelsPreflightError("CSV 采集回执未绑定当前数据文件")
    return {"kind": "collector-native-csv-chain", "receipt_path": str(rp),
            "receipt_sha256": _sha256_file(rp), "query": q,
            "completion": completion, "segments": segments}


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


def validate_preflight_artifact(path):
    """Re-run the canonical preflight from its bound manifest and compare exact evidence."""
    raw_artifact = Path(path)
    if raw_artifact.is_symlink():
        raise ChannelsPreflightError("preflight artifact 不得为符号链接")
    artifact = raw_artifact.resolve()
    try:
        claimed = json.loads(artifact.read_text(encoding="utf-8"))
        producer = claimed.get("producer") or {}
        if producer != {"path": "channels_preflight.py",
                        "sha256": _sha256_file(Path(__file__))}:
            raise ChannelsPreflightError("preflight producer 不是当前生产脚本")
        manifest_ref = claimed.get("manifest") or {}
        manifest = Path(str(manifest_ref.get("path", ""))).resolve()
        if not manifest.is_file() or manifest_ref.get("sha256") != _sha256_file(manifest):
            raise ChannelsPreflightError("preflight manifest 绑定无效")
        with tempfile.TemporaryDirectory(prefix="identity_preflight_recheck_") as td:
            preflight_channels(manifest, td)
            actual = json.loads((Path(td) / "channels_preflight.json").read_text(encoding="utf-8"))
        if claimed != actual:
            raise ChannelsPreflightError("preflight 与当前 manifest/collector receipts/数据实物不一致")
        return claimed
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        raise ChannelsPreflightError(f"preflight artifact 不可验证: {exc}") from exc


def replay_provenance(out_dir, engine_path):
    """Bind replay stats to the exact preflight and data inputs consumed by this run."""
    preflight = Path(out_dir).resolve() / "channels_preflight.json"
    obj = validate_preflight_artifact(preflight)
    engine = Path(engine_path).resolve()
    balances = Path(out_dir).resolve() / "balances_final.json"
    if balances.is_symlink() or not balances.is_file():
        raise ChannelsPreflightError("replay 尚未产出 balances_final.json，不能签 stats")
    return {"producer": {"path": engine.name, "sha256": _sha256_file(engine)},
            "preflight": {"path": preflight.name, "sha256": _sha256_file(preflight)},
            # 覆盖截止块=声明区间 [expected_from, expected_to) 的最后一个块。采集覆盖
            # 语义而非最后事件块（尾部空块不缩小覆盖）；取自重验过的 preflight 声明，
            # 不由引擎自报。verify_recon 以它断言重放范围对齐对账目标块。
            "max_block": int(obj["expected_to"]) - 1,
            "inputs": obj["inputs"],
            "outputs": {"balances_final": {"path": balances.name,
                         "size": balances.stat().st_size, "sha256": _sha256_file(balances)}}}


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

        channel_rows, inputs = [], []
        for c in ordered:
            rp = Path(c["receipt"]).resolve()
            receipt_obj = json.loads(rp.read_text(encoding="utf-8"))
            row = {k: c[k] for k in ("tag", "path", "format", "lo", "hi", "rows",
                                            "min_block", "max_block", "receipt")}
            row["receipt_sha256"] = _sha256_file(rp)
            if c["format"] == "v1csv":
                native_path = Path(receipt_obj["provenance"]["receipt_path"]).resolve()
                row["collector_receipt"] = {"path": str(native_path),
                                              "sha256": _sha256_file(native_path)}
                files = [Path(c["path"]).resolve()]
            else:
                files = sorted([Path(x) for x in glob.glob(str(Path(c["path"]) / "run_*" / "logs.parquet"))]
                               + [Path(x) for x in glob.glob(str(Path(c["path"]) / "run_*" / "blocks.parquet"))])
            for fp in files:
                inputs.append({"path": str(fp), "size": fp.stat().st_size,
                               "sha256": _sha256_file(fp)})
            channel_rows.append(row)
        payload = {"schema": PREFLIGHT_SCHEMA, "status": "PASS",
                   "producer": {"path": "channels_preflight.py",
                                "sha256": _sha256_file(Path(__file__))},
                   "manifest": {"path": str(manifest), "sha256": _sha256_file(manifest)},
                   "token": token, "expected_from": expected_from, "expected_to": expected_to,
                   "channels": channel_rows, "inputs": sorted(inputs, key=lambda x: x["path"])}
        _write_preflight(out_dir, payload)
        return ordered
    except (OSError, json.JSONDecodeError, ChannelsPreflightError) as e:
        _write_preflight(out_dir, {"schema": PREFLIGHT_SCHEMA, "status": "BLOCK",
                                   "manifest": str(manifest), "error": str(e)})
        raise SystemExit(f"[channels preflight] BLOCK: {e}") from e
