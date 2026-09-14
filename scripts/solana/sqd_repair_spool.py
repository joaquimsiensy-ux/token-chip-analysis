"""Ephemeral disk spool preserving native repair row and canonical GID order."""
from collections.abc import Mapping
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import tempfile

from spl_edge_core import validate_edge_row
from sqd_repair_core import canonical_json


def _integer(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _same_bytes(first, second):
    descriptor = os.open(second, os.O_RDONLY | os.O_NOFOLLOW)
    with open(first, 'rb') as left, os.fdopen(descriptor, 'rb') as right:
        identity = os.fstat(right.fileno())
        if not stat.S_ISREG(identity.st_mode):
            return False
        while True:
            chunk = left.read(1024 * 1024)
            if chunk != right.read(1024 * 1024):
                return False
            if not chunk:
                current = os.stat(second, follow_symlinks=False)
                return (current.st_dev, current.st_ino, current.st_size,
                        current.st_mtime_ns) == (identity.st_dev, identity.st_ino,
                                                identity.st_size, identity.st_mtime_ns)


def publish_jsonl_exclusive(path, rows, *, temporary_directory=None):
    """Complete and fsync a stream before atomically publishing without replace."""
    path = Path(path)
    if path.is_symlink():
        raise ValueError('JSONL publication symlink forbidden')
    descriptor, temporary = tempfile.mkstemp(
        prefix='.repair-jsonl-', dir=temporary_directory or path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as handle:
            for row in rows:
                handle.write(canonical_json(row) + b'\n')
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path, follow_symlinks=False)
        except FileExistsError:
            if path.is_symlink() or not path.is_file() or not _same_bytes(temporary, path):
                raise ValueError(f'existing JSONL publication differs: {path.name}')
        descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        Path(temporary).unlink()


class _SlotMaps(Mapping):
    def __init__(self, spool):
        self.spool = spool

    def __len__(self):
        return self.spool.map_count

    def __iter__(self):
        for (slot,) in self.spool.connection.execute(
                'SELECT slot FROM maps ORDER BY length(slot), slot COLLATE BINARY'):
            yield int(slot)

    def __contains__(self, slot):
        return _integer(slot) and self.spool.connection.execute(
            'SELECT 1 FROM maps WHERE slot=?', (str(slot),)).fetchone() is not None

    def __getitem__(self, slot):
        if not _integer(slot):
            raise KeyError(slot)
        row = self.spool.connection.execute(
            'SELECT row_json FROM maps WHERE slot=?', (str(slot),)).fetchone()
        if row is None:
            raise KeyError(slot)
        return json.loads(row[0])['map']


class RepairSpool:
    """One-slot atomic ingestion; all whole-history sorting lives in SQLite."""
    def __init__(self, directory):
        descriptor, name = tempfile.mkstemp(prefix='.repair-spool-', suffix='.sqlite',
                                          dir=directory)
        os.close(descriptor)
        self.path = Path(name)
        self.connection = sqlite3.connect(name)
        self.connection.execute('PRAGMA temp_store=FILE')
        self.connection.execute('PRAGMA cache_size=-4096')
        # This is disposable scratch, never a checkpoint or formal evidence.
        self.connection.execute('PRAGMA journal_mode=MEMORY')
        self.connection.execute('CREATE TABLE maps (slot TEXT PRIMARY KEY, row_json BLOB)')
        self.connection.execute('CREATE TABLE layer (ordinal INTEGER PRIMARY KEY, '
                                'signature TEXT, row_json BLOB)')
        self.map_count = self.transaction_count = self.edge_count = 0
        self.slot_maps = _SlotMaps(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None
            self.path.unlink()

    def commit(self):
        self.connection.commit()

    def add(self, map_row, layer_rows):
        """Validate and persist one slot, rolling back the entire slot on failure."""
        if not isinstance(map_row, dict) or not _integer(map_row.get('slot')):
            raise ValueError('map slot must be a nonnegative JSON integer')
        slot = map_row['slot']
        triples = map_row.get('map')
        if not isinstance(triples, list):
            raise ValueError('slot map must be a list')
        old, new, signatures = set(), set(), set()
        for triple in triples:
            if not isinstance(triple, list) or len(triple) != 3 \
                    or not _integer(triple[0]) or not _integer(triple[1]) \
                    or not isinstance(triple[2], str) or not triple[2] \
                    or triple[0] in old or triple[1] in new or triple[2] in signatures:
                raise ValueError('invalid or non-bijective slot map')
            old.add(triple[0]); new.add(triple[1]); signatures.add(triple[2])
        map_raw = canonical_json(map_row)
        transaction_count = edge_count = 0
        try:
            with self.connection:
                self.connection.execute('INSERT INTO maps VALUES (?, ?)', (str(slot), map_raw))
                for row in layer_rows:
                    if not isinstance(row, dict) or not _integer(row.get('slot')) \
                            or row['slot'] != slot or not isinstance(row.get('signature'), str) \
                            or not row['signature'] or not isinstance(row.get('edges'), list):
                        raise ValueError('repair layer identity/edges invalid')
                    for edge in row['edges']:
                        checked = validate_edge_row(edge)
                        if checked[1] != slot:
                            raise ValueError('repair edge belongs to another slot')
                    self.connection.execute('INSERT INTO layer VALUES (?, ?, ?)', (
                        self.transaction_count + transaction_count, row['signature'], canonical_json(row)))
                    transaction_count += 1
                    edge_count += len(row['edges'])
        except sqlite3.IntegrityError as exc:
            raise ValueError('duplicate spool slot') from exc
        self.map_count += 1
        self.transaction_count += transaction_count
        self.edge_count += edge_count

    def _raw_layer(self):
        for (raw,) in self.connection.execute(
                'SELECT row_json FROM layer ORDER BY signature COLLATE BINARY, ordinal'):
            yield raw

    def _raw_maps(self):
        for (raw,) in self.connection.execute(
                'SELECT row_json FROM maps ORDER BY length(slot), slot COLLATE BINARY'):
            yield raw

    def iter_layer(self):
        for raw in self._raw_layer():
            yield json.loads(raw)

    def iter_maps(self):
        for raw in self._raw_maps():
            yield json.loads(raw)

    def iter_repair_edges(self):
        for row in self.iter_layer():
            for edge in row['edges']:
                yield validate_edge_row(edge)

    def compute_gid(self, material):
        """Byte-equivalent to core.compute_gid with the two disk-backed arrays."""
        if not isinstance(material, dict) or any(not isinstance(key, str) for key in material):
            raise ValueError('gid material must be a string-keyed object')
        if 'transactions' in material or 'slot_index_map' in material:
            raise ValueError('spool owns transactions and slot_index_map GID fields')
        fields = dict(material)
        for key in ('gid', 'generated_at', 'rpc_ledger', 'bundle_sha256'):
            fields.pop(key, None)
        fields['kind'] = 'repair'
        streams = {'transactions': self._raw_layer, 'slot_index_map': self._raw_maps}
        digest = hashlib.sha256()
        digest.update(b'{')
        for ordinal, key in enumerate(sorted(set(fields) | set(streams))):
            if ordinal:
                digest.update(b',')
            if key in streams:
                digest.update(canonical_json(key) + b':[')
                for index, raw in enumerate(streams[key]()):
                    if index:
                        digest.update(b',')
                    digest.update(raw)
                digest.update(b']')
            else:
                # Keep numeric-field validation in its original object context.
                digest.update(canonical_json({key: fields[key]})[1:-1])
        digest.update(b'}')
        return digest.hexdigest()[:16]

    def publish_layer(self, path, header):
        publish_jsonl_exclusive(path, self._with_header(header, self.iter_layer()),
                                temporary_directory=self.path.parent)

    def publish_maps(self, path, header):
        publish_jsonl_exclusive(path, self._with_header(header, self.iter_maps()),
                                temporary_directory=self.path.parent)

    @staticmethod
    def _with_header(header, rows):
        yield header
        yield from rows
