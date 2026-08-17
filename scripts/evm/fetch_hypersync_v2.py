#!/usr/bin/env python3
"""HyperSync 官方客户端采集器 v2（Rust 内核自动并发 + Parquet 直写）。
与 v1（fetch_hypersync.py 手写 JSON 轮询）的差别：传输为压缩二进制、客户端内部并发流水线
（掩盖 RTT——v3.11.2 POC 实测正是 RTT 主导瓶颈）、直接落 Parquet 免逐行 CSV。

用法: python3 fetch_hypersync_v2.py <from_block> \
        --url https://bsc.hypersync.xyz --token-addr 0x标的 --outdir data/v2 \
        [--to-block N] [--concurrency 10] [--token-file ~/.config/hypersync/token]
  - API token 读取优先级（C3 密钥治理）：显式 --token-file > HYPERSYNC_TOKEN
    > 默认 ~/.config/hypersync/token；禁止位置参数明文传入，避免 secret 进入 argv/ps
  - --url 注意是裸域名（官方客户端自己拼路径，不要带 /query）
  - --concurrency 官方默认 10；高密度合约建议 20 起调；免费层别超 4（限流）
  - 断点续传：--outdir 已有 run_*/ 时自动从最大 next_block 续拉，新数据落新 run_<from>/ 子目录
  - 存量 v2 done 迁移：python3 fetch_hypersync_v2.py --refresh-manifests --outdir data/v2
输出: <outdir>/run_<from>/logs.parquet + blocks.parquet
  下游用 transfers_lib.py 的 read_transfers() 合成标准 8 列表（自动 join 时间戳）。
（来源：v3.11.2 采集加速工程，2026-07-21）"""
import argparse, asyncio, glob, hashlib, importlib.util, json, os, re, sys, time
from datetime import datetime, timezone
from pathlib import Path

import hypersync
from hypersync import (BlockField, ClientConfig, FieldSelection, HexOutput,
                       LogField, LogSelection, Query, StreamConfig)

try:
    import collector_history as _collector_history
    historical_script_hashes = _collector_history.historical_script_hashes
except ModuleNotFoundError as exc:
    if exc.name != "collector_history":
        raise
    # 审计守卫会以 spec_from_file_location 单文件加载入口，此时脚本邻接目录不在
    # sys.path；仍从固定邻接文件消费同一零依赖登记表，不开放运行时扩展路径。
    _history_spec = importlib.util.spec_from_file_location(
        "fetch_hypersync_v2_collector_history",
        Path(__file__).resolve().with_name("collector_history.py"),
    )
    if _history_spec is None or _history_spec.loader is None:
        raise
    _history_module = importlib.util.module_from_spec(_history_spec)
    _history_spec.loader.exec_module(_history_module)
    _collector_history = _history_module
    historical_script_hashes = _history_module.historical_script_hashes

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from anchor_point_contract import strict_json_loads


TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
MANIFEST_SCHEMA = "hypersync-v2-done/v4"
LEGACY_MANIFEST_SCHEMAS = {"hypersync-v2-done/v2", "hypersync-v2-done/v3"}
QUERY_SCHEMA = "erc20-transfer-fields/v2"
IDENTITY_SCHEMA = "hypersync-capture-identity/v1"
RECOVERED_IDENTITY_SCHEMA = "hypersync-capture-identity/v2"
IDENTITY_NAME = "capture_identity.json"
SCRIPT_NAME = "fetch_hypersync_v2.py"
SCRIPT_PATH = "scripts/evm/fetch_hypersync_v2.py"
DEFAULT_TOKEN_FILE = "~/.config/hypersync/token"


class SafeParser(argparse.ArgumentParser):
    def parse_args(self, args=None, namespace=None):
        parsed, extras = self.parse_known_args(args, namespace)
        if extras:
            self.error("存在未识别参数（输入值已隐去）")
        return parsed


def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError("须为整数（输入值已隐去）") from None


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _read_strict_json(path, label):
    """Read one immutable byte snapshot and reject duplicate keys at every depth."""
    source = Path(path)
    raw = source.read_bytes()
    try:
        value = strict_json_loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"{label} 不可读: {exc}") from exc
    return value, raw, hashlib.sha256(raw).hexdigest()


def _revoked_script_hashes():
    """Return the registry-wide deny set; REVOKED beats a current worktree hash."""
    return {
        entry["sha256"]
        for entry in _collector_history.COLLECTOR_HISTORY
        if entry["status"] == "REVOKED"
    }


def _current_script_hash():
    current = sha256_file(__file__)
    if current in _revoked_script_hashes():
        raise ValueError("当前脚本版本已被吊销，禁止继续签发/校验")
    return current


def _allowed_script_hashes(protocol):
    return historical_script_hashes(SCRIPT_NAME, protocol=protocol) | {_current_script_hash()}


def _validate_script_actor(actor, protocol, label, *, path=SCRIPT_PATH):
    if not isinstance(actor, dict) or set(actor) != {"path", "sha256"}:
        raise ValueError(f"{label} 形态非法")
    actor_path, actor_hash = actor.get("path"), actor.get("sha256")
    if not isinstance(actor_path, str) or not isinstance(actor_hash, str) \
            or actor_path != path or actor_hash not in _allowed_script_hashes(protocol):
        raise ValueError(f"{label} 未绑定当前或历史 ACTIVE {protocol} 采集器")
    return actor


def _validate_done_v4_shape(d):
    """Validate the mutually exclusive native and legacy-unattributed v4 states."""
    if not isinstance(d, dict):
        raise ValueError("done manifest 顶层必须是对象")
    provenance = d.get("collector_provenance")
    if "collector_provenance" in d and not isinstance(provenance, str):
        raise ValueError("collector_provenance 必须是字符串枚举")
    migration_keys = {"refreshed_from_schema", "pre_migration_sha256", "migrator"}
    collector = d.get("collector")
    if isinstance(collector, dict):
        if "collector_provenance" in d or migration_keys & set(d):
            raise ValueError("原生 v4 done 禁止携带 legacy provenance/迁移记录")
        _validate_script_actor(collector, MANIFEST_SCHEMA, "collector")
        return "SELF_REPORTED"
    if collector is not None:
        raise ValueError("done collector 必须为对象或 null")
    if "collector" not in d or provenance != "legacy-unattributed" \
            or not migration_keys <= set(d):
        raise ValueError("迁移 v4 done 的 legacy-unattributed 判别联合不完整")
    source = d.get("refreshed_from_schema")
    if not isinstance(source, str) or source not in LEGACY_MANIFEST_SCHEMAS | {"pre-schema-v1"}:
        raise ValueError("refreshed_from_schema 不是受支持的旧 schema")
    # Migration-time self-report only: after source bytes are replaced this trace cannot be
    # independently reverified.  The union checks presence/shape, not historical truth.
    pre_hash = d.get("pre_migration_sha256")
    if not isinstance(pre_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", pre_hash):
        raise ValueError("pre_migration_sha256 非 64 位十六进制")
    _validate_script_actor(d.get("migrator"), MANIFEST_SCHEMA, "migrator")
    return "UNKNOWN_LEGACY"


def inspect_run_files(run_dir, from_block, to_block):
    """Validate both Parquets and return their content-bound receipt metadata."""
    try:
        import duckdb
    except ImportError as e:
        raise ValueError("duckdb 未安装，无法重验 Parquet 完整性") from e
    run = Path(run_dir)
    specs = {
        "logs.parquet": ("block_number", {"block_number", "block_hash", "log_index",
                                            "transaction_hash", "topic1", "topic2", "data"}),
        "blocks.parquet": ("number", {"number", "timestamp"}),
    }
    result = {}
    con = duckdb.connect()
    try:
        for name, (block_col, required) in specs.items():
            path = run / name
            if not path.is_file():
                raise ValueError(f"{name} 不存在")
            try:
                cols = {r[0] for r in con.execute(
                    "DESCRIBE SELECT * FROM read_parquet(?)", [str(path)]).fetchall()}
                if not required <= cols:
                    raise ValueError(f"{name} schema 缺字段: {sorted(required - cols)}")
                rows, lo, hi = con.execute(
                    f"SELECT COUNT(*), MIN({block_col}), MAX({block_col}) FROM read_parquet(?)",
                    [str(path)]).fetchone()
            except ValueError:
                raise
            except Exception as e:
                raise ValueError(f"{name} 不可读或已截断: {e}") from e
            if rows and (lo is None or hi is None or int(lo) < int(from_block)
                         or int(hi) >= int(to_block)):
                raise ValueError(f"{name} 块范围 [{lo},{hi}] 越出 [{from_block},{to_block})")
            result[name] = {"size": path.stat().st_size, "rows": int(rows),
                            "min_block": int(lo) if lo is not None else None,
                            "max_block": int(hi) if hi is not None else None,
                            "sha256": sha256_file(path)}
        missing = con.execute(
            "SELECT COUNT(*) FROM read_parquet(?) l LEFT JOIN read_parquet(?) b "
            "ON l.block_number=b.number WHERE l.block_number IS NOT NULL AND b.number IS NULL",
            [str(run / "logs.parquet"), str(run / "blocks.parquet")]).fetchone()[0]
        if missing:
            raise ValueError(f"blocks.parquet 缺 {missing} 个 logs 所在块")
    finally:
        con.close()
    return result


def validate_done_manifest(done_path, default_from, to_block, token_addr, url):
    """Revalidate manifest identity, bounds, Parquet schemas, ranges, sizes and hashes."""
    try:
        d, _, _ = _read_strict_json(done_path, "done manifest")
    except Exception as exc:
        raise ValueError(f"unreadable done manifest {done_path}: {exc}") from exc
    if not isinstance(d, dict):
        raise ValueError(f"done manifest 顶层必须是对象: {done_path}")
    schema = d.get("schema")
    if not isinstance(schema, str):
        if "schema" not in d:
            raise ValueError("pre-schema done 未迁移；先运行 --refresh-manifests")
        raise ValueError("done schema 必须是字符串")
    if schema in LEGACY_MANIFEST_SCHEMAS:
        raise ValueError(f"legacy done {schema} 未迁移；先运行 --refresh-manifests")
    if schema != MANIFEST_SCHEMA:
        raise ValueError(f"不认识的 done schema: {schema!r}")
    _validate_done_v4_shape(d)
    expected = {"schema": MANIFEST_SCHEMA, "query_schema": QUERY_SCHEMA,
                "token": token_addr.lower(), "url": url}
    if any(d.get(k) != v for k, v in expected.items()):
        raise ValueError(f"done manifest identity mismatch: {done_path}")
    try:
        capture = int(d.get("capture_from", -1))
        frm, end, nb = (int(d.get(k, -1)) for k in ("from_block", "to_block", "next_block"))
    except (TypeError, ValueError) as e:
        raise ValueError(f"done manifest bounds non-integer: {done_path}") from e
    if capture != int(default_from) or not (default_from <= frm < end == nb <= to_block):
        raise ValueError(f"done manifest bounds invalid/outside request: {done_path}")
    actual = inspect_run_files(Path(done_path).parent, frm, end)
    recorded = d.get("files")
    if not isinstance(recorded, dict) or set(recorded) != set(actual):
        raise ValueError(f"done manifest files receipt missing/extra: {done_path}")
    for name, meta in actual.items():
        if recorded.get(name) != meta:
            raise ValueError(f"done manifest {name} size/rows/range/hash drift: {done_path}")
    return d


def atomic_write_json(path, obj):
    path = Path(path)
    tmp = path.with_name("." + path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    dir_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def capture_identity(token_addr, url):
    host = re.sub(r"^https?://", "", url).split("/", 1)[0]
    return {"schema": IDENTITY_SCHEMA, "token": token_addr.lower(), "url": url,
            "query_schema": QUERY_SCHEMA, "network": host.split(".", 1)[0],
            "collector": {"path": SCRIPT_NAME,
                          "sha256": _current_script_hash()}}


def _inventory_residue_error(name, *, location, is_directory=False):
    """Classify owned crash/rollback artifacts without turning rejection into cleanup."""
    display = f"{location}/{name}" if location else name
    if not location and name == "quarantine" and is_directory:
        return ("存在 staged_capture 隔离区 quarantine/；"
                "人工检视其内容后整体移出采集根再继续")
    if name.endswith(".recover"):
        return (f"{display} 是 refresh 回滚保留件；"
                "确认同名 done 原件完好后手动移除")
    if re.fullmatch(r"\..+\.refresh-(?:tmp|bak)\.[^.]+", name):
        return f"{display} 是刷新中断残留临时件；确认后手动移除"
    return f"v2 采集根目录有未识别残件: {display}；逐一检视后移出采集根再继续"


def validate_capture_inventory(outdir, *, identity_required=True):
    """Require the exact root/run inventory shared by recovery and preflight."""
    raw_root = Path(outdir)
    if raw_root.is_symlink():
        raise ValueError("v2 采集根目录不存在、非目录或为符号链接")
    root = raw_root.resolve()
    if not root.is_dir():
        raise ValueError("v2 采集根目录不存在、非目录或为符号链接")
    allowed_root_file = {IDENTITY_NAME} if identity_required else set()
    runs = []
    for entry in root.iterdir():
        if entry.name == ".DS_Store":
            continue
        if entry.name in allowed_root_file:
            if entry.is_symlink() or not entry.is_file():
                raise ValueError(f"{IDENTITY_NAME} 不是普通文件")
            continue
        if not re.fullmatch(r"run_[0-9]+", entry.name) or entry.is_symlink() \
                or not entry.is_dir():
            raise ValueError(_inventory_residue_error(
                entry.name, location="",
                is_directory=entry.is_dir() and not entry.is_symlink()))
        runs.append(entry)
    if identity_required and not (root / IDENTITY_NAME).is_file():
        raise ValueError(f"v2 采集根目录缺 {IDENTITY_NAME}")
    if not runs:
        raise ValueError("v2 采集根目录没有 run_* 数据段")
    expected = {"done.json", "logs.parquet", "blocks.parquet"}
    done_paths = []
    for run in sorted(runs):
        entries = [entry for entry in run.iterdir() if entry.name != ".DS_Store"]
        names = {entry.name for entry in entries}
        if names != expected:
            extras = sorted(names - expected)
            if extras:
                raise ValueError(_inventory_residue_error(extras[0], location=run.name))
            raise ValueError(f"{run.name} inventory 非精确三件套: {sorted(names)}")
        for entry in entries:
            if entry.is_symlink() or not entry.is_file():
                raise ValueError(f"{run.name}/{entry.name} 不是普通文件")
        done_paths.append(run / "done.json")
    return done_paths


def ensure_outdir_identity(outdir, token_addr, url):
    """Create once, then strictly validate the immutable outdir query identity."""
    root = Path(outdir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    expected = capture_identity(token_addr, url)
    path = root / IDENTITY_NAME
    if path.exists() or path.is_symlink():
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"{IDENTITY_NAME} 不是普通文件")
        try:
            actual, _, _ = _read_strict_json(path, IDENTITY_NAME)
        except Exception as exc:
            raise ValueError(f"{IDENTITY_NAME} 不可读: {exc}") from exc
        if not isinstance(actual, dict):
            raise ValueError(f"{IDENTITY_NAME} 顶层必须是对象")
        identity_schema = actual.get("schema")
        if not isinstance(identity_schema, str):
            raise ValueError(f"{IDENTITY_NAME} schema 必须是字符串")
        # v1 is a native lineage identity: collector is its issuer, not proof for each segment.
        # v2 is an explicit recovery identity: recoverer replaces collector and lineage is unknown.
        if identity_schema == IDENTITY_SCHEMA:
            actual_collector = actual.get("collector")
            expected_collector = expected["collector"]
            allowed_collector_hashes = historical_script_hashes(
                SCRIPT_NAME, protocol=IDENTITY_SCHEMA) | {expected_collector["sha256"]}
            actual_path = (actual_collector.get("path")
                           if isinstance(actual_collector, dict) else None)
            actual_hash = (actual_collector.get("sha256")
                           if isinstance(actual_collector, dict) else None)
            if isinstance(actual_path, str) and isinstance(actual_hash, str) and \
                    actual_path == SCRIPT_NAME and actual_hash in allowed_collector_hashes:
                expected = dict(expected, collector={
                    "path": actual_path,
                    "sha256": actual_hash,
                })
        elif identity_schema == RECOVERED_IDENTITY_SCHEMA:
            recoverer = actual.get("recoverer")
            recovery_time = actual.get("recovery_time")
            if actual.get("recovered") is True and actual.get("lineage") == "unknown" \
                    and isinstance(recovery_time, str) and recovery_time:
                _validate_script_actor(recoverer, RECOVERED_IDENTITY_SCHEMA, "recoverer")
                expected = {
                    "schema": RECOVERED_IDENTITY_SCHEMA,
                    "token": token_addr.lower(),
                    "url": url,
                    "query_schema": QUERY_SCHEMA,
                    "network": expected["network"],
                    "recovered": True,
                    "lineage": "unknown",
                    "recovery_time": recovery_time,
                    "recoverer": recoverer,
                }
        else:
            raise ValueError(f"不认识的 capture identity schema: {identity_schema!r}")
        if actual != expected:
            raise ValueError(f"{IDENTITY_NAME} 与本次 token/url/query/签发形态不一致")
        return actual
    # Auto-signing is safe only for a vacuum root. Any hidden file, partial run, or legacy
    # segment requires the explicit read-only recovery audit; deleting identity cannot re-sign.
    if any(entry.name != ".DS_Store" for entry in root.iterdir()):
        raise ValueError(f"遗留 outdir 缺 {IDENTITY_NAME}；先运行 --recover-identity")
    atomic_write_json(path, expected)
    return expected


def recover_identity(outdir):
    """Read-only audit every legacy run, then issue an explicit unknown-lineage identity."""
    raw_root = Path(outdir)
    if raw_root.is_symlink():
        raise ValueError("v2 采集根目录不存在、非目录或为符号链接")
    root = raw_root.resolve()
    identity_path = root / IDENTITY_NAME
    if identity_path.exists() or identity_path.is_symlink():
        raise ValueError(f"{IDENTITY_NAME} 已存在；拒绝覆盖恢复")
    recoverer_hash = _current_script_hash()
    done_paths = validate_capture_inventory(raw_root, identity_required=False)
    identities = set()
    for done_path in done_paths:
        d, _, _ = _read_strict_json(done_path, "done manifest")
        if not isinstance(d, dict):
            raise ValueError(f"done manifest 顶层必须是对象: {done_path}")
        schema = d.get("schema")
        if "schema" in d and not isinstance(schema, str):
            raise ValueError(f"done schema 必须是字符串: {done_path}")
        if schema is not None and schema != MANIFEST_SCHEMA and schema not in LEGACY_MANIFEST_SCHEMAS:
            raise ValueError(f"不认识的 done schema: {schema!r}")
        token = str(d.get("token", "")).strip().lower()
        url = re.sub(r"/query/?$", "", str(d.get("url", "")).strip().rstrip("/"))
        if not token or not url:
            raise ValueError(f"done token/url 身份字段缺失: {done_path}")
        if schema is not None and "query_schema" not in d:
            raise ValueError(f"带 schema done 缺 query_schema: {done_path}")
        if "query_schema" in d:
            query_schema = d.get("query_schema")
            if not isinstance(query_schema, str) or query_schema != QUERY_SCHEMA:
                raise ValueError(f"done query_schema 不是现行 {QUERY_SCHEMA}: {done_path}")
        identities.add((token, url))
        try:
            if schema is None:
                frm, end = int(d["from_block"]), int(d["next_block"])
                capture, nb = frm, end
            else:
                capture = int(d["capture_from"])
                frm, end, nb = (int(d[key])
                                for key in ("from_block", "to_block", "next_block"))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"done 边界缺失/非整数: {done_path}") from exc
        if not 0 <= capture <= frm < end == nb:
            raise ValueError(f"done 边界非法: {done_path}")
        actual_files = inspect_run_files(done_path.parent, frm, end)
        if schema in {"hypersync-v2-done/v3", MANIFEST_SCHEMA} \
                and d.get("files") != actual_files:
            raise ValueError(f"done files 与当前 Parquet 不一致: {done_path}")
        if schema == MANIFEST_SCHEMA:
            capture = int(d.get("capture_from", frm))
            validate_done_manifest(done_path, capture, end, token, url)
    if len(identities) != 1:
        raise ValueError(f"存量 run token/url identity 不唯一: {sorted(identities)!r}")
    token, url = next(iter(identities))
    if sha256_file(__file__) != recoverer_hash:
        raise ValueError("recoverer 脚本在恢复期间发生漂移；拒绝签发 identity")
    host = re.sub(r"^https?://", "", url).split("/", 1)[0]
    identity = {
        "schema": RECOVERED_IDENTITY_SCHEMA,
        "token": token,
        "url": url,
        "query_schema": QUERY_SCHEMA,
        "network": host.split(".", 1)[0],
        "recovered": True,
        "lineage": "unknown",
        "recovery_time": datetime.now(timezone.utc).isoformat(),
        "recoverer": {"path": SCRIPT_PATH, "sha256": recoverer_hash},
    }
    atomic_write_json(identity_path, identity)
    return identity


def find_resume_block(outdir, default_from, to_block, token_addr, url):
    """Resume only manifests bound to the same capture identity and bounds."""
    try:
        ensure_outdir_identity(outdir, token_addr, url)
    except ValueError as exc:
        raise SystemExit(f"[fail-closed] {exc}") from exc
    best = default_from
    intervals = []
    for f in glob.glob(os.path.join(outdir, "run_*", "done.json")):
        try:
            raw, _, _ = _read_strict_json(f, "done manifest")
        except Exception as exc:
            raise SystemExit(f"[fail-closed] unreadable done manifest {f}: {exc}")
        try:
            capture = int(raw.get("capture_from", -1))
            end = int(raw.get("to_block", -1))
            bound = to_block if capture == int(default_from) else end
            d = validate_done_manifest(f, capture, bound, token_addr, url)
        except ValueError as exc:
            raise SystemExit(f"[fail-closed] {exc}") from exc
        frm, end = int(d["from_block"]), int(d["to_block"])
        intervals.append((frm, end, f))
        if capture == int(default_from):
            best = max(best, int(d["next_block"]))
    intervals.sort()
    for prev, nxt in zip(intervals, intervals[1:]):
        if nxt[0] < prev[1]:
            raise SystemExit(f"[fail-closed] outdir run 区间重叠: {prev[2]} -> {nxt[2]}")
    return best


def _manifest_refresh_candidate(done_path, *, prehistoric_capture_from=None,
                                migrator_hash=None):
    """重验单个 run；从同一原始字节快照解析并生成待写 v4 payload。"""
    path = Path(done_path)
    d, _, source_sha = _read_strict_json(path, "done manifest")
    if not isinstance(d, dict):
        raise ValueError("done manifest 顶层必须是对象")
    schema = d.get("schema")
    if "schema" in d and not isinstance(schema, str):
        raise ValueError("done schema 必须是字符串")
    if schema == MANIFEST_SCHEMA:
        _validate_done_v4_shape(d)
        try:
            frm, end = int(d["from_block"]), int(d["to_block"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("v4 done manifest 边界缺失/非整数") from exc
        actual = inspect_run_files(path.parent, frm, end)
        if d.get("files") != actual:
            raise ValueError("v4 done manifest files 与当前 Parquet 不一致")
        return None, source_sha, d
    if "schema" not in d:
        payload = _prehistoric_refresh_candidate(
            path, d, source_sha=source_sha,
            capture_from=prehistoric_capture_from,
            migrator_hash=migrator_hash,
        )
        return payload, source_sha, d
    if schema not in LEGACY_MANIFEST_SCHEMAS:
        raise ValueError(f"不支持迁移的旧 schema: {schema!r}")
    if d.get("query_schema") != QUERY_SCHEMA:
        raise ValueError(f"query_schema 不是 {QUERY_SCHEMA}")
    token = str(d.get("token", "")).strip().lower()
    url = re.sub(r"/query/?$", "", str(d.get("url", "")).strip().rstrip("/"))
    if not token or not url:
        raise ValueError("token/url 身份字段缺失")
    try:
        capture = int(d["capture_from"])
        frm, end, nb = (int(d[k]) for k in ("from_block", "to_block", "next_block"))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("旧 manifest 边界缺失/非整数") from exc
    if not (capture <= frm < end == nb):
        raise ValueError(
            f"旧 manifest 边界非法: capture={capture} run=[{frm},{end}) next={nb}")
    files = inspect_run_files(path.parent, frm, end)
    actor_hash = migrator_hash or sha256_file(__file__)
    payload = {**d, "schema": MANIFEST_SCHEMA, "token": token, "url": url,
               "files": files, "collector": None,
               "collector_provenance": "legacy-unattributed",
               "refreshed_from_schema": schema,
               "pre_migration_sha256": source_sha,
               "migrator": {"path": SCRIPT_PATH, "sha256": actor_hash}}
    return payload, source_sha, d


PREHISTORIC_KEYS = {"from_block", "next_block", "token", "url"}


def _prehistoric_refresh_candidate(path, d, *, source_sha, capture_from=None,
                                   migrator_hash=None):
    """无 schema 字段的太古 done（v1 采集时代五键格式）→ 现行 v4 payload。

    太古 done 无任何回执可信，全部边界/文件指纹从数据实物重验重建；显式写
    "schema": null 的畸形件不走本分支（调用方按不支持 schema 拒绝）。
    query_schema 补写依据：inspect_run_files 硬验两个 Parquet 的列集与现行采集器
    field_selection 的产物形态一致（logs 7 列 / blocks 2 列）——列集是查询形态的
    物理证据，不是对旧声明的信任；列集不符即 fail-closed。
    """
    missing = PREHISTORIC_KEYS - set(d)
    if missing:
        raise ValueError(f"pre-schema done 缺必备键: {sorted(missing)}")
    token = str(d.get("token", "")).strip().lower()
    url = re.sub(r"/query/?$", "", str(d.get("url", "")).strip().rstrip("/"))
    if not token or not url:
        raise ValueError("token/url 身份字段缺失")
    try:
        frm, nb = int(d["from_block"]), int(d["next_block"])
    except (TypeError, ValueError) as exc:
        raise ValueError("pre-schema done 边界非整数") from exc
    if not 0 <= frm < nb:
        raise ValueError(f"pre-schema done 边界非法: from={frm} next={nb}")
    capture = frm if capture_from is None else capture_from
    if isinstance(capture, bool) or not isinstance(capture, int) or not 0 <= capture <= frm:
        raise ValueError(f"--capture-from 非法: {capture!r}（须 <= 段起点 {frm}）")
    files = inspect_run_files(path.parent, frm, nb)
    payload = {"schema": MANIFEST_SCHEMA, "query_schema": QUERY_SCHEMA,
               "capture_from": capture, "from_block": frm, "to_block": nb,
               "next_block": nb, "token": token, "url": url, "files": files,
               "collector": None, "collector_provenance": "legacy-unattributed",
               "refreshed_from_schema": "pre-schema-v1",
               "pre_migration_sha256": source_sha,
               "migrator": {"path": SCRIPT_PATH,
                            "sha256": migrator_hash or sha256_file(__file__)}}
    if "elapsed_s" in d:
        payload["elapsed_s"] = d["elapsed_s"]
    return payload


class RefreshRollbackError(Exception):
    """F-07：commit 期失败且回滚也失败——磁盘处于混合状态，恢复件已保留。

    CLI 对本异常 exit 1（脚本/环境故障，人工按 .recover 件恢复后重跑）；
    普通 ValueError/OSError（含回滚成功后的原始错误重抛）仍走 exit 2。
    """


def _fsync_file_and_dir(path):
    with open(path, "rb") as f:
        os.fsync(f.fileno())
    dir_fd = os.open(Path(path).parent, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def refresh_manifests(outdir, capture_from=None):
    """真事务迁移（F-07）：validate 全部 → prepare（全部新 manifest 各写临时件＋fsync）
    → commit（先备份原件，逐个 os.replace）。commit 期任一失败→逐文件从备份回滚
    ＋按字节哈希验证回滚结果；回滚失败保留 `<done>.recover` 恢复件并抛
    RefreshRollbackError（CLI exit 1）。不变量＝全有或全无：任何失败路径上，
    要么所有 done.json 都是新版，要么所有 done.json 字节回滚原样。"""
    raw_root = Path(outdir)
    if raw_root.is_symlink():
        raise ValueError("v2 采集根目录不存在、非目录或为符号链接")
    root = raw_root.resolve()
    identity_path = root / IDENTITY_NAME
    if identity_path.is_symlink() or not identity_path.is_file():
        raise ValueError(f"遗留 outdir 缺 {IDENTITY_NAME}；先运行 --recover-identity")
    _current_script_hash()
    done_paths = validate_capture_inventory(raw_root, identity_required=True)
    prehistoric_count = 0
    for path in done_paths:
        preview, _, _ = _read_strict_json(path, "done manifest")
        if isinstance(preview, dict) and "schema" not in preview:
            prehistoric_count += 1
    if prehistoric_count > 1 and capture_from is None:
        raise ValueError("同目录多段 pre-schema run 无法唯一推导同源 capture；"
                         "须显式传 --capture-from")
    migrator_start_hash = sha256_file(__file__)
    pending, failures, identities = [], [], set()
    for path in done_paths:
        try:
            payload, original_sha, current = _manifest_refresh_candidate(
                path,
                prehistoric_capture_from=capture_from,
                migrator_hash=migrator_start_hash,
            )
            if payload is not None:
                pending.append((path, payload, original_sha))
                current = payload
            identities.add((str(current.get("token", "")).lower(), current.get("url"),
                            current.get("query_schema")))
        except (OSError, ValueError) as exc:
            failures.append(f"{path.parent.name}: {exc}")
    if failures:
        raise ValueError("存量 manifest 迁移拒绝（未改写任何 done.json）:\n  - "
                         + "\n  - ".join(failures))
    if len(identities) != 1:
        raise ValueError(f"存量 run capture identity 不唯一: {sorted(identities)!r}")
    token, url, query_schema = next(iter(identities))
    if not token or not url or query_schema != QUERY_SCHEMA:
        raise ValueError("存量 run 缺 token/url 或 query_schema 非现行版")
    ensure_outdir_identity(root, token, url)

    # ── prepare：全部新 manifest 先写各自临时件＋fsync；此阶段任何失败都没有动过
    # 任何正式件，清理临时件后原样抛错（天然全无）。同时记录每个原件的字节哈希，
    # 供 commit 失败回滚后逐文件验证"字节回滚原样"。
    staged = []   # (done_path, tmp_path, bak_path, original_sha256)
    try:
        for path, payload, original_sha in pending:
            tmp = path.with_name("." + path.name + f".refresh-tmp.{os.getpid()}")
            bak = path.with_name("." + path.name + f".refresh-bak.{os.getpid()}")
            # F-D6：先登记再写——写到一半抛错的那个临时件必须在清理循环的遍历范围内，
            # 否则 prepare 期失败会把正在写的 tmp 泄漏在 run_*/ 下（卫生问题，正式件无恙）。
            staged.append((path, tmp, bak, original_sha))
            with tmp.open("w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=1)
                f.flush()
                os.fsync(f.fileno())
    except BaseException:
        for _, tmp, _, _ in staged:
            if tmp.exists():
                tmp.unlink()
        raise

    # ── commit：逐个先备份原件（os.replace 到 .refresh-bak），再把临时件替换上位。
    committed = []  # 已完成新件上位的 (path, tmp, bak, sha)
    moved_only = None  # 原件已移走成备份、新件尚未上位的那一条
    committed_all = False
    try:
        for entry in staged:
            path, tmp, bak, _ = entry
            if sha256_file(__file__) != migrator_start_hash:
                raise ValueError("migrator 脚本在迁移期间发生漂移；拒绝提交")
            if sha256_file(path) != entry[3]:
                raise ValueError(f"done.json 自解析后发生漂移；拒绝提交: {path}")
            os.replace(path, bak)
            moved_only = entry
            os.replace(tmp, path)
            moved_only = None
            committed.append(entry)
        committed_all = True
        # 全部新件已上位＝事务已提交；此后的持久化收尾/备份清理失败不再回滚
        # （对齐 receipt_kernel.publish_txn 先例：committed 后保留备份报错）。
        for path, _, bak, _ in committed:
            _fsync_file_and_dir(path)
            if bak.exists():
                bak.unlink()
    except BaseException as primary:
        if committed_all:
            kept = [str(b) for _, _, b, _ in committed if b.exists()]
            raise ValueError(
                f"迁移已提交但收尾（fsync/备份清理）失败——done.json 均为新版，"
                f"备份保留于 {kept}: {primary}") from primary
        # 回滚：半途那条（原件在 bak、新件没上位）与已提交各条全部从备份复位。
        rollback_failures = []
        to_restore = list(committed) + ([moved_only] if moved_only else [])
        for path, tmp, bak, original_sha in to_restore:
            try:
                os.replace(bak, path)
                if sha256_file(path) != original_sha:
                    raise OSError(f"回滚后字节与原件不一致: {path}")
            except BaseException as exc:
                rollback_failures.append((path, bak, exc))
        for _, tmp, _, _ in staged:
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass
        if rollback_failures:
            preserved = []
            for path, bak, _ in rollback_failures:
                recover = path.with_name(path.name + ".recover")
                try:
                    if bak.exists():
                        os.replace(bak, recover)
                        preserved.append(str(recover))
                except OSError:
                    if bak.exists():
                        preserved.append(str(bak))
            detail = "; ".join(f"{p}: {e}" for p, _, e in rollback_failures)
            raise RefreshRollbackError(
                f"迁移提交失败（{primary}）且回滚也失败——磁盘处于混合状态，"
                f"恢复件已保留: {preserved}；失败明细: {detail}") from primary
        raise
    return {"checked": len(done_paths), "upgraded": len(pending),
            "already_v4": len(done_paths) - len(pending)}


def _load_token(ap, token_file):
    """C3：显式 token 文件 > HYPERSYNC_TOKEN > 默认 token 文件。"""
    if token_file is not None:
        path = os.path.expanduser(token_file)
    else:
        env_token = os.environ.get("HYPERSYNC_TOKEN", "").strip()
        if env_token:
            return env_token
        path = os.path.expanduser(DEFAULT_TOKEN_FILE)
    try:
        token = Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        token = ""
    if not token:
        ap.error("HyperSync token 文件缺失或为空（路径已隐去）；"
                 "默认路径 ~/.config/hypersync/token，或设 HYPERSYNC_TOKEN")
    return token


def parse_args(argv=None):
    ap = SafeParser()
    ap.add_argument("from_block", type=_safe_int)
    ap.add_argument("--url", default="https://bsc.hypersync.xyz")
    ap.add_argument("--token-addr", required=True)
    ap.add_argument("--outdir", default="data/v2")
    ap.add_argument("--to-block", type=int, default=None)
    ap.add_argument("--concurrency", type=int, default=10)
    ap.add_argument("--token-file", default=None,
                    help="token 文件；显式给出时优先于 HYPERSYNC_TOKEN")
    a = ap.parse_args(argv)
    a.token = _load_token(ap, a.token_file)
    return a


async def main():
    a = parse_args()
    collector_start_hash = _current_script_hash()
    token = a.token
    url = re.sub(r"/query/?$", "", a.url.rstrip("/"))  # 容错：v1 习惯带 /query
    client = hypersync.HypersyncClient(ClientConfig(url=url, bearer_token=token))
    height = await client.get_height()
    to_block = a.to_block or height
    os.makedirs(a.outdir, exist_ok=True)
    try:
        ensure_outdir_identity(a.outdir, a.token_addr, url)
    except ValueError as exc:
        sys.exit(f"[fail-closed] {exc}")
    start = find_resume_block(a.outdir, a.from_block, to_block, a.token_addr, url)
    if start > a.from_block:
        print(f"[resume] 从已验证 manifest 的 next_block {start} 续拉", flush=True)
    if start >= to_block:
        sys.exit(f"[fail-closed] resume start {start} >= to_block {to_block}; "
                 "请求为空或已完成，拒绝写空完成记录")
    run_dir = os.path.join(a.outdir, f"run_{start}")
    os.makedirs(run_dir, exist_ok=True)
    query = Query(
        from_block=start,
        to_block=to_block,
        logs=[LogSelection(address=[a.token_addr.lower()], topics=[[TRANSFER]])],
        field_selection=FieldSelection(
            log=[LogField.BLOCK_NUMBER, LogField.BLOCK_HASH, LogField.LOG_INDEX,
                 LogField.TRANSACTION_HASH, LogField.TOPIC1, LogField.TOPIC2,
                 LogField.DATA],
            block=[BlockField.NUMBER, BlockField.TIMESTAMP],
        ),
    )
    cfg = StreamConfig(hex_output=HexOutput.PREFIXED, concurrency=a.concurrency)
    t0 = time.time()
    await client.collect_parquet(run_dir, query, cfg)
    el = time.time() - t0
    try:
        files = inspect_run_files(run_dir, start, to_block)
    except ValueError as exc:
        sys.exit(f"[fail-closed] collected Parquet validation failed: {exc}")
    for name in files:
        with open(os.path.join(run_dir, name), "rb") as f:
            os.fsync(f.fileno())
    done = {"schema": MANIFEST_SCHEMA, "query_schema": QUERY_SCHEMA,
               "capture_from": a.from_block, "next_block": to_block,
               "from_block": start, "to_block": to_block, "elapsed_s": round(el, 1),
               "token": a.token_addr.lower(), "url": url,
               "client_version": getattr(hypersync, "__version__", "unknown"),
               "collector": {"path": SCRIPT_PATH, "sha256": collector_start_hash},
               "files": files}
    # Self-reported binding detects accidental/runtime drift, not a malicious forger that can
    # rewrite both the collector and its receipt. Freeze at startup and recheck before publish.
    if sha256_file(__file__) != collector_start_hash:
        sys.exit("[fail-closed] collector 脚本在采集期间发生漂移；拒绝写 done.json")
    atomic_write_json(os.path.join(run_dir, "done.json"), done)
    print(f"[COMPLETE] [{start},{to_block}) -> {run_dir} 用时 {el:.0f}s", flush=True)


def verify_done_cli(argv):
    ap = argparse.ArgumentParser(description="Revalidate a HyperSync v2 done receipt and Parquets")
    ap.add_argument("--done", required=True)
    ap.add_argument("--capture-from", required=True, type=int)
    ap.add_argument("--to-block", required=True, type=int)
    ap.add_argument("--token-addr", required=True)
    ap.add_argument("--url", required=True)
    a = ap.parse_args(argv)
    url = re.sub(r"/query/?$", "", a.url.rstrip("/"))
    try:
        validate_done_manifest(a.done, a.capture_from, a.to_block, a.token_addr, url)
    except ValueError as exc:
        print(f"[fail-closed] {exc}", file=sys.stderr)
        return 2
    print(f"[verified] {a.done}")
    return 0


def refresh_manifests_cli(argv):
    ap = argparse.ArgumentParser(
        description="Revalidate legacy HyperSync Parquets and atomically upgrade done manifests")
    ap.add_argument("--refresh-manifests", action="store_true", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--capture-from", type=_safe_int)
    a = ap.parse_args(argv)
    try:
        result = refresh_manifests(a.outdir, capture_from=a.capture_from)
    except RefreshRollbackError as exc:
        # 回滚失败＝磁盘混合状态＋.recover 恢复件在场：exit 1（环境故障，人工恢复后重跑）。
        print(f"[rollback-failed] {exc}", file=sys.stderr)
        return 1
    except (ValueError, OSError) as exc:
        # OSError 一并捕获（F-07）：罩住 ensure_outdir_identity 与提交期 IO 故障，
        # 不再裸 traceback；此路径上事务已回滚或从未动过正式件。
        print(f"[fail-closed] {exc}", file=sys.stderr)
        return 2
    print(f"[refreshed] checked={result['checked']} upgraded={result['upgraded']} "
          f"already_v4={result['already_v4']}")
    return 0


def recover_identity_cli(argv):
    ap = argparse.ArgumentParser(
        description="Audit every legacy HyperSync run and issue an unknown-lineage identity")
    ap.add_argument("--recover-identity", action="store_true", required=True)
    ap.add_argument("--outdir", required=True)
    a = ap.parse_args(argv)
    try:
        identity = recover_identity(a.outdir)
    except (ValueError, OSError) as exc:
        print(f"[fail-closed] {exc}", file=sys.stderr)
        return 2
    print(f"[recovered] schema={identity['schema']} lineage={identity['lineage']} "
          f"outdir={Path(a.outdir).resolve()}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "verify-done":
        sys.exit(verify_done_cli(sys.argv[2:]))
    if "--refresh-manifests" in sys.argv[1:]:
        sys.exit(refresh_manifests_cli(sys.argv[1:]))
    if "--recover-identity" in sys.argv[1:]:
        sys.exit(recover_identity_cli(sys.argv[1:]))
    asyncio.run(main())
