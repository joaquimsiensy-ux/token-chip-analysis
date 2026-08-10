#!/usr/bin/env python3
"""HyperSync 官方客户端采集器 v2（Rust 内核自动并发 + Parquet 直写）。
与 v1（fetch_hypersync.py 手写 JSON 轮询）的差别：传输为压缩二进制、客户端内部并发流水线
（掩盖 RTT——v3.11.2 POC 实测正是 RTT 主导瓶颈）、直接落 Parquet 免逐行 CSV。

用法: python3 fetch_hypersync_v2.py <from_block> \
        --url https://bsc.hypersync.xyz --token-addr 0x标的 --outdir data/v2 \
        [--to-block N] [--concurrency 10] [--token-file ~/.config/hypersync/token]
  - API token 读取优先级（C3 密钥治理，2026-07-22——**不要把 token 放进命令行**，
    ps 进程列表可见）：位置参数（仅旧用法兼容，勿新用）> 环境变量 HYPERSYNC_TOKEN
    > --token-file 文件（默认 ~/.config/hypersync/token，chmod 600）
  - --url 注意是裸域名（官方客户端自己拼路径，不要带 /query）
  - --concurrency 官方默认 10；高密度合约建议 20 起调；免费层别超 4（限流）
  - 断点续传：--outdir 已有 run_*/ 时自动从最大 next_block 续拉，新数据落新 run_<from>/ 子目录
  - 存量 v2 done 迁移：python3 fetch_hypersync_v2.py --refresh-manifests --outdir data/v2
输出: <outdir>/run_<from>/logs.parquet + blocks.parquet
  下游用 transfers_lib.py 的 read_transfers() 合成标准 8 列表（自动 join 时间戳）。
（来源：v3.11.2 采集加速工程，2026-07-21）"""
import argparse, asyncio, glob, hashlib, json, os, re, sys, time
from pathlib import Path

import hypersync
from hypersync import (BlockField, ClientConfig, FieldSelection, HexOutput,
                       LogField, LogSelection, Query, StreamConfig)

TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
MANIFEST_SCHEMA = "hypersync-v2-done/v3"
LEGACY_MANIFEST_SCHEMAS = {"hypersync-v2-done/v2"}
QUERY_SCHEMA = "erc20-transfer-fields/v2"
IDENTITY_SCHEMA = "hypersync-capture-identity/v1"
IDENTITY_NAME = "capture_identity.json"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


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
        d = json.load(open(done_path, encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"unreadable done manifest {done_path}: {exc}") from exc
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
            "collector": {"path": "fetch_hypersync_v2.py",
                          "sha256": sha256_file(__file__)}}


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
            actual = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError(f"{IDENTITY_NAME} 不可读: {exc}") from exc
        if actual != expected:
            raise ValueError(f"{IDENTITY_NAME} 与本次 token/url/query/collector 不一致")
        return actual
    # Migrating an existing root is allowed only when every native done has the same identity.
    for done_path in sorted(root.glob("run_*/done.json")):
        try:
            d = json.loads(done_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError(f"done manifest 不可读 {done_path}: {exc}") from exc
        observed = (str(d.get("token", "")).lower(), d.get("url"), d.get("query_schema"))
        wanted = (expected["token"], expected["url"], expected["query_schema"])
        if observed != wanted:
            raise ValueError(f"旧 run capture identity 与本次请求不一致: {done_path}")
    atomic_write_json(path, expected)
    return expected


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
            raw = json.load(open(f, encoding="utf-8"))
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


def _manifest_refresh_candidate(done_path):
    """重验单个旧 run，返回待原子写入的 v3 payload。"""
    path = Path(done_path)
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"done manifest 不可读: {exc}") from exc
    schema = d.get("schema")
    if schema == MANIFEST_SCHEMA:
        try:
            frm, end = int(d["from_block"]), int(d["to_block"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("v3 done manifest 边界缺失/非整数") from exc
        actual = inspect_run_files(path.parent, frm, end)
        if d.get("files") != actual:
            raise ValueError("v3 done manifest files 与当前 Parquet 不一致")
        return None
    if "schema" not in d:
        return _prehistoric_refresh_candidate(path, d)
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
    return {**d, "schema": MANIFEST_SCHEMA, "token": token, "url": url,
            "files": files, "refreshed_from_schema": schema}


PREHISTORIC_KEYS = {"from_block", "next_block", "token", "url"}


def _prehistoric_refresh_candidate(path, d):
    """无 schema 字段的太古 done（v1 采集时代五键格式）→ 现行 v3 payload。

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
    files = inspect_run_files(path.parent, frm, nb)
    payload = {"schema": MANIFEST_SCHEMA, "query_schema": QUERY_SCHEMA,
               "capture_from": frm, "from_block": frm, "to_block": nb,
               "next_block": nb, "token": token, "url": url, "files": files,
               "refreshed_from_schema": "pre-schema-v1"}
    if "elapsed_s" in d:
        payload["elapsed_s"] = d["elapsed_s"]
    return payload


def refresh_manifests(outdir):
    """Two-phase refresh: validate every run first; write none if any run is bad."""
    root = Path(outdir).resolve()
    done_paths = sorted(root.glob("run_*/done.json"))
    if not done_paths:
        raise ValueError(f"outdir 下没有 run_*/done.json: {root}")
    pending, failures, identities = [], [], set()
    for path in done_paths:
        try:
            payload = _manifest_refresh_candidate(path)
            if payload is not None:
                pending.append((path, payload))
                current = payload
            else:
                current = json.loads(path.read_text(encoding="utf-8"))
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
    for path, payload in pending:
        atomic_write_json(path, payload)
    # identity 必须建在 done 升级之后：其迁移预检要求磁盘上每个 done 已带现行
    # query_schema，太古 done 升级前不满足。唯一性上面已验；ensure 幂等，此处
    # 失败时重跑 refresh 自愈（done 已 v3 走 already_v3 路径）。
    ensure_outdir_identity(root, token, url)
    return {"checked": len(done_paths), "upgraded": len(pending),
            "already_v3": len(done_paths) - len(pending)}


def resolve_token(a):
    """C3：token 优先级 位置参数(旧兼容) > $HYPERSYNC_TOKEN > --token-file 文件。"""
    if a.api_token:
        print("[warn] token 经命令行传入（ps 可见）——建议改用 --token-file/环境变量",
              flush=True)
        return a.api_token
    env = os.environ.get("HYPERSYNC_TOKEN", "").strip()
    if env:
        return env
    try:
        tok = open(os.path.expanduser(a.token_file)).read().strip()
    except OSError:
        sys.exit(f"[fatal] 读不到 HyperSync token 文件: {a.token_file}"
                 "（也可设环境变量 HYPERSYNC_TOKEN）")
    if not tok:
        sys.exit(f"[fatal] token 文件为空: {a.token_file}")
    return tok


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("api_token", nargs="?", default=None,
                    help="（旧用法兼容，勿新用——token 会进 ps）留空则读 env/文件")
    ap.add_argument("from_block", type=int)
    ap.add_argument("--url", default="https://bsc.hypersync.xyz")
    ap.add_argument("--token-addr", required=True)
    ap.add_argument("--outdir", default="data/v2")
    ap.add_argument("--to-block", type=int, default=None)
    ap.add_argument("--concurrency", type=int, default=10)
    ap.add_argument("--token-file", default="~/.config/hypersync/token",
                    help="API token 文件路径（默认 ~/.config/hypersync/token）")
    a = ap.parse_args()
    token = resolve_token(a)
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
               "files": files}
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
    a = ap.parse_args(argv)
    try:
        result = refresh_manifests(a.outdir)
    except ValueError as exc:
        print(f"[fail-closed] {exc}", file=sys.stderr)
        return 2
    print(f"[refreshed] checked={result['checked']} upgraded={result['upgraded']} "
          f"already_v3={result['already_v3']}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "verify-done":
        sys.exit(verify_done_cli(sys.argv[2:]))
    if "--refresh-manifests" in sys.argv[1:]:
        sys.exit(refresh_manifests_cli(sys.argv[1:]))
    asyncio.run(main())
