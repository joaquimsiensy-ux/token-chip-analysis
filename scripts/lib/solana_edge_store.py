"""Reusable, integer-exact materialization of formal Solana seven-field edges.

The existing formal resolver remains authoritative. Raw bytes and metadata are
checked on every use; a signed receipt binds those inputs to the entire database
file. A cached database is attached read-only, preserving all nine loader columns.
"""
from __future__ import annotations

import fcntl
import gzip
import hashlib
import json
import os
import sys
import zlib
import time
import uuid
from pathlib import Path

from content_cache import (CacheIntegrityError, CacheStore, code_fingerprint,
                           emit_metric, sha256_file, ResidentCodeGuard)

EDGE_DDL = """CREATE TABLE edges (
    ts BIGINT, f VARCHAR, t VARCHAR, amt HUGEINT,
    chain_pos1 BIGINT, chain_pos2 BIGINT, chain_pos3 BIGINT,
    order_exact BOOLEAN, ingest_seq BIGINT)"""
COLUMNS = [("ts", "BIGINT"), ("f", "VARCHAR"), ("t", "VARCHAR"),
           ("amt", "HUGEINT"), ("chain_pos1", "BIGINT"),
           ("chain_pos2", "BIGINT"), ("chain_pos3", "BIGINT"),
           ("order_exact", "BOOLEAN"), ("ingest_seq", "BIGINT")]


def _inputs(preflight, case_root, mint):
    import duckdb
    import pyarrow
    _BUILD_CODE_GUARD.check(_build)
    code = Path(__file__).resolve().parent
    current_algorithm = code_fingerprint([__file__, code / "content_cache.py",
                                           code.parent / "solana" / "spl_edge_core.py"])
    if current_algorithm != _ALGORITHM_AT_IMPORT:
        raise CacheIntegrityError("materialization algorithm changed since module import; restart required")
    return {"schema": "solana-edge-materialization/v1", "mint": mint,
            "case_root": str(Path(case_root).resolve()),
            "edge_source_binding": preflight["edge_source_binding"],
            "edge_rows": preflight["cache_meta"]["edge_rows"],
            "source_path": str(Path(preflight["files"][0]).resolve()),
            "meta_path": str(Path(preflight["meta_path"]).resolve()),
            "columns": COLUMNS,
            "algorithm": current_algorithm,
            "loaded_builder_code_sha256": _BUILD_CODE_AT_IMPORT,
            "duckdb": duckdb.__version__, "pyarrow": pyarrow.__version__,
            "python": list(sys.version_info[:3]), "zlib": zlib.ZLIB_RUNTIME_VERSION}


def _source_unchanged(preflight):
    binding = preflight["edge_source_binding"]
    if (sha256_file(preflight["files"][0]) != binding["soltx_edges_sha256"]
            or sha256_file(preflight["meta_path"]) != binding["soltx_meta_sha256"]):
        raise CacheIntegrityError("Solana input changed after preflight")


def _build(path, preflight):
    import duckdb
    import pyarrow as pa
    from spl_edge_core import INSTR_INDEX_TX_NET
    total = 0
    logical = hashlib.sha256()
    columns = [[] for _ in COLUMNS]
    types = [pa.int64(), pa.string(), pa.string(), pa.string(), pa.int64(),
             pa.int64(), pa.int64(), pa.bool_(), pa.int64()]
    db = duckdb.connect(str(path))
    db.execute("SET threads=2")
    db.execute("SET memory_limit='2GB'")
    db.execute(EDGE_DDL)

    def flush():
        batch = pa.Table.from_arrays([pa.array(c, type=t) for c, t in zip(columns, types)],
                                    names=[c[0] for c in COLUMNS])
        db.register("_edge_batch", batch)
        # VARCHAR -> HUGEINT avoids a FLOAT or decimal precision intermediate.
        db.execute("INSERT INTO edges SELECT ts,f,t,CAST(amt AS HUGEINT),"
                   "chain_pos1,chain_pos2,chain_pos3,order_exact,ingest_seq FROM _edge_batch")
        db.unregister("_edge_batch")
        for column in columns:
            column.clear()

    fp = preflight["files"][0]
    opener = gzip.open if fp.endswith(".gz") else open
    try:
        with opener(fp, "rt", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except (ValueError, RecursionError) as exc:
                    raise ValueError(f"{fp} 第 {line_no} 行 JSON 非法: {exc}") from exc
                if not isinstance(row, list) or len(row) != 7:
                    raise ValueError(f"正式 Solana 边 {fp} 第 {line_no} 行必须为 7 元组")
                ts, slot, txi, ins, sender, receiver, amount = row
                if (any(not isinstance(v, int) or isinstance(v, bool) or v < 0
                        for v in (ts, slot, txi))
                        or not isinstance(ins, int) or isinstance(ins, bool) or ins < INSTR_INDEX_TX_NET
                        or not isinstance(sender, str) or not sender
                        or not isinstance(receiver, str) or not receiver
                        or not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0):
                    raise ValueError(f"正式 Solana 边 {fp} 第 {line_no} 行字段类型非法")
                logical.update((json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8"))
                values = (ts, sender, receiver, str(amount), slot, txi, ins, ins >= 0, total)
                for column, value in zip(columns, values):
                    column.append(value)
                total += 1
                if len(columns[0]) >= 100_000:
                    flush()
            if columns[0]:
                flush()
        meta = preflight["cache_meta"]
        if not total or total != meta["edge_rows"] or logical.hexdigest() != meta["edge_logical_sha256"]:
            raise ValueError("Solana edge_rows/edge_logical_sha256 differs from raw input")
        _source_unchanged(preflight)
        db.execute("CHECKPOINT")
    finally:
        db.close()
    return {"rows": total, "edge_logical_sha256": logical.hexdigest()}


def load_materialized(con, preflight, *, case_root, mint):
    started = time.monotonic()
    store = CacheStore(case_root, "solana-edges")
    inputs = _inputs(preflight, case_root, mint)
    key = store.key(inputs)
    db_path = store.directory / (key + ".duckdb")
    lock_path = store.directory / (key + ".lock")
    with open(lock_path, "a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        receipt = store.load(inputs)
        if receipt is None:
            if db_path.exists() or db_path.is_symlink():
                raise CacheIntegrityError("materialization exists without authenticated receipt")
            emit_metric("raw_load_start", reason="no_verified_materialization", source_rows=inputs["edge_rows"])
            tmp = store.directory / (".pending-" + uuid.uuid4().hex + ".duckdb")
            stats = _build(tmp, preflight)
            payload = {**stats, "database_sha256": sha256_file(tmp), "columns": COLUMNS}
            if _inputs(preflight, case_root, mint) != inputs:
                raise CacheIntegrityError("materialization algorithm changed during computation")
            os.replace(tmp, db_path)
            store.save(inputs, payload)
            receipt = payload
            emit_metric("raw_load_complete", elapsed_seconds=time.monotonic() - started, rows=stats["rows"])
        else:
            if db_path.is_symlink() or not db_path.is_file():
                raise CacheIntegrityError("materialized database missing or a symlink")
            if sha256_file(db_path) != receipt.get("database_sha256"):
                emit_metric("raw_load_reject", reason="database_hash_mismatch")
                raise CacheIntegrityError("materialized database SHA256 mismatch")
            _source_unchanged(preflight)
            emit_metric("raw_load_reuse", elapsed_seconds=time.monotonic() - started, rows=receipt["rows"])
        # Relation aliases are private per caller connection; SQL strings are quoted.
        alias = "_sol_edges_" + key[:20]
        quoted = str(db_path).replace("'", "''")
        con.execute(f"ATTACH '{quoted}' AS {alias} (READ_ONLY)")
        actual = [(r[0], r[1]) for r in con.execute(f"DESCRIBE {alias}.edges").fetchall()]
        if actual != COLUMNS or receipt["rows"] != inputs["edge_rows"]:
            raise CacheIntegrityError("materialization schema/count binding mismatch")
        con.execute(f"CREATE VIEW edges AS SELECT * FROM {alias}.edges")
    return receipt["rows"], preflight["edge_source_binding"]


# Bind the implementation actually loaded, not just file bytes seen later.
_ALGORITHM_AT_IMPORT = code_fingerprint([
    __file__, Path(__file__).parent / "content_cache.py",
    Path(__file__).parent.parent / "solana" / "spl_edge_core.py"])
_BUILD_CODE_GUARD = ResidentCodeGuard(_build)
_BUILD_CODE_AT_IMPORT = _BUILD_CODE_GUARD.sha256
