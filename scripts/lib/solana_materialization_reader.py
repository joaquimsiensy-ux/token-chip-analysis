"""Read an authenticated loader database as raw rows for independent validators.

This does not approve an attribution or a repair result. It exposes the exact
seven original fields plus the verified file dependencies to the calling proof
collector. The caller still applies its own edge contract and accounting logic.
"""
import json
from pathlib import Path

from content_cache import CacheStore, CacheIntegrityError, emit_metric, sha256_file, canonical_bytes
from solana_edge_store import COLUMNS, _inputs, _source_unchanged


def verified_rows(path, case_root):
    """Return None or {rows, source_sha256, dependency_files, algorithm_files}."""
    import duckdb
    source = Path(path).resolve()
    store = CacheStore(case_root, "solana-edges")
    for manifest in sorted(store.directory.glob("*.json")):
        if manifest.is_symlink() or not manifest.is_file():
            raise CacheIntegrityError("materialization index must not follow a symlink")
        # This read is only an index hint. Every candidate is subsequently checked
        # against the authenticated receipt and freshly reconstructed inputs.
        try:
            inputs = json.loads(manifest.read_text(encoding="utf-8"))["body"]["inputs"]
        except (OSError, KeyError, ValueError, TypeError):
            continue
        if inputs.get("source_path") != str(source):
            continue
        payload = store.load(inputs)
        if payload is None or store.path(inputs) != manifest:
            raise CacheIntegrityError("materialization receipt filename/key mismatch")
        meta_path = Path(inputs["meta_path"])
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        prepared = {"files": [str(source)], "cache_meta": meta,
                    "meta_path": str(meta_path), "edge_source_binding": inputs["edge_source_binding"]}
        if canonical_bytes(_inputs(prepared, case_root, inputs["mint"])) != canonical_bytes(inputs):
            # A former loader implementation is not evidence for the current one.
            continue
        _source_unchanged(prepared)
        db_path = store.directory / (store.key(inputs) + ".duckdb")
        if db_path.is_symlink() or not db_path.is_file() or sha256_file(db_path) != payload["database_sha256"]:
            raise CacheIntegrityError("independent raw reader: database content mismatch")
        if payload.get("rows") != inputs.get("edge_rows"):
            raise CacheIntegrityError("independent raw reader: row-count binding mismatch")
        db = duckdb.connect(str(db_path), read_only=True)
        if [(r[0], r[1]) for r in db.execute("DESCRIBE edges").fetchall()] != COLUMNS:
            db.close()
            raise CacheIntegrityError("independent raw reader: database column contract mismatch")
        dependencies = [
            {"path": str(source), "bytes": source.stat().st_size,
             "sha256": inputs["edge_source_binding"]["soltx_edges_sha256"]},
            {"path": str(meta_path), "bytes": meta_path.stat().st_size,
             "sha256": inputs["edge_source_binding"]["soltx_meta_sha256"]},
            {"path": str(db_path), "bytes": db_path.stat().st_size,
             "sha256": payload["database_sha256"]},
            {"path": str(manifest), "bytes": manifest.stat().st_size,
             "sha256": sha256_file(manifest)},
        ]

        def rows(connection=db):
            try:
                connection.execute("SET threads=2")
                cursor = connection.execute("SELECT ts,chain_pos1,chain_pos2,chain_pos3,f,t,amt "
                                            "FROM edges ORDER BY ingest_seq")
                while True:
                    chunk = cursor.fetchmany(100_000)
                    if not chunk:
                        break
                    yield from chunk
            finally:
                connection.close()
        emit_metric("raw_materialization_shared", source=str(source), rows=payload["rows"],
                    reason="independent_validator_reuses_verified_raw_rows")
        return {"rows": rows(), "source_sha256": dependencies[0]["sha256"],
                "dependency_files": dependencies,
                "algorithm_files": [__file__, *inputs["algorithm"]],
                "edge_source_binding": inputs["edge_source_binding"]}
    return None
