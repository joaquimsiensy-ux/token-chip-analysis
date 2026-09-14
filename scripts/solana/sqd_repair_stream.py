"""Disk-backed equivalent of repair_core.merge_edges and its gzip publication.

Memory is bounded by SQLite's page/sort buffers, one edge, and one slot's
index lookup; the supplied slot-map objects are not copied in full. Temporary
files live outside the generation directory, on the same filesystem, so
publication can use an exclusive link without publishing stale crash scratch.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile

try:
    from .spl_edge_core import edge_sort_key, validate_edge_row
    from .sqd_repair_core import iter_edge_file
except ImportError:
    from spl_edge_core import edge_sort_key, validate_edge_row
    from sqd_repair_core import iter_edge_file


def _same_bytes(left, right):
    with open(left, "rb") as a, open(right, "rb") as b:
        while True:
            x, y = a.read(1024 * 1024), b.read(1024 * 1024)
            if x != y:
                return False
            if not x:
                return True


def publish_merged_edges(base_edge_path, repair_edges, slot_maps, output_path, *, work_dir=None):
    """Remap, stably sort, hash and exclusively publish a repaired edge file.

    ``slot_maps`` has the native producer's integer slot keys and map rows
    ``[old_index, nonvote_index, signature]``. ``repair_edges`` may be one-pass.
    Returns edge_logical_sha256, edge_rows, edge_file_sha256, edge_file_size and
    edges_added, all computed during this invocation. Existing identical bytes
    are reused; different bytes raise FileExistsError without replacement.
    ``work_dir`` defaults to the destination directory's parent, outside the
    immutable generation. It must share the destination filesystem.
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    workspace = Path(work_dir) if work_dir is not None else output.parent.parent
    workspace.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".repair-merge-", dir=workspace))
    database, compressed = temporary / "sort.sqlite", temporary / "edges.gz"
    connection = None
    try:
        connection = sqlite3.connect(database)
        connection.execute("PRAGMA journal_mode=OFF")
        connection.execute("PRAGMA synchronous=OFF")
        connection.execute("PRAGMA temp_store=FILE")
        connection.execute("PRAGMA cache_size=-8192")
        connection.execute("PRAGMA mmap_size=0")
        connection.execute("PRAGMA threads=1")
        # Positive integer text plus its length sorts exactly as Python ints,
        # without SQLite INTEGER's signed-64-bit limitation. Amount is lexical.
        connection.execute("""CREATE TABLE edges (
            slot_len INTEGER, slot_text TEXT, tx_len INTEGER, tx_text TEXT,
            owner_from TEXT, owner_to TEXT, amount_text TEXT,
            ordinal INTEGER PRIMARY KEY, payload TEXT)""")
        insert = "INSERT INTO edges VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        count = 0

        def add(raw):
            nonlocal count
            row = validate_edge_row(raw)
            slot, tx, owner_from, owner_to, amount = edge_sort_key(row)
            slot_text, tx_text = str(slot), str(tx)
            payload = json.dumps(list(row), separators=(",", ":"), ensure_ascii=False)
            connection.execute(insert, (len(slot_text), slot_text, len(tx_text), tx_text,
                                        owner_from, owner_to, amount, count, payload))
            count += 1

        cached_slot, lookup = None, None
        for row in iter_edge_file(base_edge_path):
            if row[1] in slot_maps:
                if cached_slot != row[1]:
                    cached_slot = row[1]
                    lookup = {item[0]: item[1] for item in slot_maps[cached_slot]}
                if row[2] not in lookup:
                    raise ValueError(f"base edge has no slot-index solution: {row[1]}/{row[2]}")
                row = (row[0], row[1], lookup[row[2]], *row[3:])
            add(row)
        base_count = count
        for row in repair_edges:
            add(row)
        added = count - base_count
        connection.commit()
        logical = hashlib.sha256()
        written = 0
        query = """SELECT payload FROM edges ORDER BY
            slot_len, slot_text COLLATE BINARY, tx_len, tx_text COLLATE BINARY,
            owner_from COLLATE BINARY, owner_to COLLATE BINARY,
            amount_text COLLATE BINARY, ordinal"""
        with compressed.open("xb") as raw_output:
            # Empty filename avoids a path-dependent gzip header. Level 9 is
            # gzip.compress's native default in supported Python 3.9-3.14.
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw_output,
                               compresslevel=9, mtime=0) as stream:
                for (payload,) in connection.execute(query):
                    row = validate_edge_row(json.loads(payload))
                    logical.update((json.dumps(list(row), ensure_ascii=False) + "\n").encode())
                    stream.write((payload + "\n").encode())
                    written += 1
            raw_output.flush()
            os.fsync(raw_output.fileno())
        if written != count:
            raise RuntimeError("repair merge row count changed during disk sort")
        digest = hashlib.sha256()
        with compressed.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        result = {"edge_logical_sha256": logical.hexdigest(), "edge_rows": written,
                  "edge_file_sha256": digest.hexdigest(),
                  "edge_file_size": compressed.stat().st_size, "edges_added": added}
        try:
            os.link(compressed, output)
        except FileExistsError:
            if not output.is_file() or not _same_bytes(compressed, output):
                raise FileExistsError(f"resume artifact differs: {output}") from None
        directory_fd = os.open(output.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return result
    finally:
        if connection is not None:
            connection.close()
        # Only the two exact private files created above can be removed.
        # Never recursively remove a directory or sweep caller artifacts.
        for path in (compressed, database):
            if path.exists():
                path.unlink()
        temporary.rmdir()
