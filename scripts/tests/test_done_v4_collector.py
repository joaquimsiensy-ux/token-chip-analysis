#!/usr/bin/env python3
"""U2 regressions: done/v4 collector ownership and explicit C12 recovery."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
EVM = HERE.parent / "evm"
sys.path[:0] = [str(EVM), str(HERE.parent / "lib")]

import collector_history
import fetch_hypersync_v2 as fetch_v2
from channels_preflight import ChannelsPreflightError, _v2_provenance


TOKEN = "0x" + "a" * 40
URL = "https://bsc.hypersync.xyz"
SCRIPT_PATH = "scripts/evm/fetch_hypersync_v2.py"


def _write_parquets(run_dir, blocks):
    import duckdb

    run = Path(run_dir)
    run.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    try:
        con.execute(
            "CREATE TABLE logs(block_number BIGINT, block_hash VARCHAR, log_index BIGINT, "
            "transaction_hash VARCHAR, topic1 VARCHAR, topic2 VARCHAR, data VARCHAR)"
        )
        for block in blocks:
            con.execute(
                "INSERT INTO logs VALUES (?,?,?,?,?,?,?)",
                [block, "0xhash", 0, f"0xtx{block}", "0x" + "0" * 64,
                 "0x" + "0" * 24 + "b" * 40, "0x" + f"{100:064x}"],
            )
        con.execute(f"COPY logs TO '{run / 'logs.parquet'}' (FORMAT parquet)")
        con.execute("CREATE TABLE blocks(number BIGINT, timestamp BIGINT)")
        for block in blocks:
            con.execute("INSERT INTO blocks VALUES (?,?)", [block, 1700000000 + block])
        con.execute(f"COPY blocks TO '{run / 'blocks.parquet'}' (FORMAT parquet)")
    finally:
        con.close()


def _meta(path, block_col):
    import duckdb

    path = Path(path)
    con = duckdb.connect()
    try:
        rows, lo, hi = con.execute(
            f"SELECT COUNT(*), MIN({block_col}), MAX({block_col}) FROM read_parquet(?)",
            [str(path)],
        ).fetchone()
    finally:
        con.close()
    return {
        "size": path.stat().st_size,
        "rows": int(rows),
        "min_block": int(lo) if lo is not None else None,
        "max_block": int(hi) if hi is not None else None,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _make_done(root, *, schema, start=10, end=20, capture_from=10, prehistoric=False):
    run = Path(root) / f"run_{start}"
    _write_parquets(run, [start, end - 1])
    if prehistoric:
        done = {
            "elapsed_s": 1.0,
            "from_block": start,
            "next_block": end,
            "token": TOKEN,
            "url": URL,
        }
    else:
        done = {
            "schema": schema,
            "query_schema": fetch_v2.QUERY_SCHEMA,
            "capture_from": capture_from,
            "from_block": start,
            "to_block": end,
            "next_block": end,
            "token": TOKEN,
            "url": URL,
            "files": {
                "logs.parquet": _meta(run / "logs.parquet", "block_number"),
                "blocks.parquet": _meta(run / "blocks.parquet", "number"),
            },
        }
        if schema == fetch_v2.MANIFEST_SCHEMA:
            done["collector"] = {
                "path": SCRIPT_PATH,
                "sha256": fetch_v2.sha256_file(fetch_v2.__file__),
            }
    path = run / "done.json"
    path.write_text(json.dumps(done, indent=1), encoding="utf-8")
    return path, done


def _write_v1_identity(root):
    path = Path(root) / fetch_v2.IDENTITY_NAME
    path.write_text(json.dumps(fetch_v2.capture_identity(TOKEN, URL), indent=1), encoding="utf-8")
    return path


def _assert_reject(exc_type, fn, needle=None):
    try:
        fn()
    except exc_type as exc:
        if needle is not None:
            assert needle in str(exc), str(exc)
        return exc
    raise AssertionError(f"expected {exc_type.__name__}")


class _FakeClient:
    def __init__(self):
        self.collected = False

    async def get_height(self):
        return 20

    async def collect_parquet(self, run_dir, query, _cfg):
        self.collected = True
        _write_parquets(run_dir, [query.from_block, query.to_block - 1])


def _run_main(root, sha_side_effect=None):
    client = _FakeClient()
    args = argparse.Namespace(
        token="fixture-token", url=URL, token_addr=TOKEN, outdir=str(root),
        from_block=10, to_block=20, concurrency=1, token_file=None,
    )
    passthrough = lambda **kwargs: argparse.Namespace(**kwargs)
    patches = [
        mock.patch.object(fetch_v2, "parse_args", return_value=args),
        mock.patch.object(fetch_v2, "ClientConfig", side_effect=passthrough),
        mock.patch.object(fetch_v2.hypersync, "HypersyncClient", return_value=client),
        mock.patch.object(fetch_v2, "Query", side_effect=passthrough),
        mock.patch.object(fetch_v2, "LogSelection", side_effect=passthrough),
        mock.patch.object(fetch_v2, "FieldSelection", side_effect=passthrough),
        mock.patch.object(fetch_v2, "StreamConfig", side_effect=passthrough),
    ]
    if sha_side_effect is not None:
        patches.append(mock.patch.object(fetch_v2, "sha256_file", side_effect=sha_side_effect))
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
        if len(patches) == 8:
            with patches[7]:
                asyncio.run(fetch_v2.main())
        else:
            asyncio.run(fetch_v2.main())
    return client


def test_01_new_capture_writes_segment_collector(tmp):
    _run_main(Path(tmp) / "native")
    done = json.loads((Path(tmp) / "native" / "run_10" / "done.json").read_text())
    assert done["schema"] == "hypersync-v2-done/v4"
    assert done["collector"] == {
        "path": SCRIPT_PATH,
        "sha256": fetch_v2.sha256_file(fetch_v2.__file__),
    }


def test_02_toctou_script_drift_rejects_done_write(tmp):
    real_sha = fetch_v2.sha256_file
    script = Path(fetch_v2.__file__).resolve()
    calls = {"script": 0}

    def drifting(path):
        if Path(path).resolve() == script:
            calls["script"] += 1
            return real_sha(path) if calls["script"] == 1 else "0" * 64
        return real_sha(path)

    try:
        _run_main(Path(tmp) / "drift", drifting)
    except SystemExit as exc:
        assert "collector" in str(exc).lower() or "漂移" in str(exc)
    else:
        raise AssertionError("collector script drift must reject done publication")
    assert (Path(tmp) / "drift" / "run_10" / "logs.parquet").is_file()
    assert not (Path(tmp) / "drift" / "run_10" / "done.json").exists()


def test_03_v3_to_v4_migration_is_unattributed(tmp):
    root = Path(tmp) / "v3"
    done_path, _ = _make_done(root, schema="hypersync-v2-done/v3")
    before_sha = hashlib.sha256(done_path.read_bytes()).hexdigest()
    fetch_v2.recover_identity(root)
    result = fetch_v2.refresh_manifests(root)
    assert result["upgraded"] == 1
    done = json.loads(done_path.read_text())
    assert done["schema"] == fetch_v2.MANIFEST_SCHEMA
    assert done["collector"] is None
    assert done["collector_provenance"] == "legacy-unattributed"
    assert done["refreshed_from_schema"] == "hypersync-v2-done/v3"
    assert done["pre_migration_sha256"] == before_sha
    assert set(done["migrator"]) == {"path", "sha256"}
    proof = _v2_provenance(root, TOKEN, 10, 20)
    assert proof["done_receipts"][0]["collector"] == "UNKNOWN_LEGACY"


def test_04_prehistoric_quq_shape_migrates(tmp):
    root = Path(tmp) / "prehistoric"
    done_path, _ = _make_done(root, schema=None, start=0, end=10, prehistoric=True)
    fetch_v2.recover_identity(root)
    fetch_v2.refresh_manifests(root)
    done = json.loads(done_path.read_text())
    assert done["capture_from"] == 0
    assert done["refreshed_from_schema"] == "pre-schema-v1"
    assert done["collector"] is None and done["elapsed_s"] == 1.0


def test_05_done_v4_discriminated_union_rejects_hybrids(tmp):
    for index, mutate in enumerate((
            lambda d: d.update(collector_provenance="legacy-unattributed"),
            lambda d: d.update(collector_provenance="legacy-unattributed",
                               refreshed_from_schema="hypersync-v2-done/v3",
                               pre_migration_sha256="1" * 64,
                               migrator=d["collector"]),
            lambda d: d.update(collector=None, collector_provenance="legacy-unattributed"))):
        root = Path(tmp) / f"hybrid-{index}"
        path, done = _make_done(root, schema=fetch_v2.MANIFEST_SCHEMA)
        mutate(done)
        path.write_text(json.dumps(done), encoding="utf-8")
        _assert_reject(ValueError, lambda p=path: fetch_v2.validate_done_manifest(
            p, 10, 20, TOKEN, URL))


def test_06_identity_protocol_hash_cannot_spoof_done_v4(tmp):
    identity_only = next(iter(collector_history.historical_script_hashes(
        "fetch_hypersync_v2.py", protocol="hypersync-capture-identity/v1")))
    root = Path(tmp) / "protocol-spoof"
    path, done = _make_done(root, schema=fetch_v2.MANIFEST_SCHEMA)
    done["collector"]["sha256"] = identity_only
    path.write_text(json.dumps(done), encoding="utf-8")
    _assert_reject(ValueError, lambda: fetch_v2.validate_done_manifest(
        path, 10, 20, TOKEN, URL))


def test_07_c12_only_vacuum_auto_signs(tmp):
    empty = Path(tmp) / "empty"
    fetch_v2.ensure_outdir_identity(empty, TOKEN, URL)
    assert (empty / fetch_v2.IDENTITY_NAME).is_file()
    legacy = Path(tmp) / "legacy"
    _make_done(legacy, schema="hypersync-v2-done/v3")
    _assert_reject(ValueError, lambda: fetch_v2.ensure_outdir_identity(legacy, TOKEN, URL),
                   "--recover-identity")


def test_08_recover_identity_positive_and_inventory_negative(tmp):
    root = Path(tmp) / "recover"
    _make_done(root, schema="hypersync-v2-done/v3")
    identity = fetch_v2.recover_identity(root)
    assert identity["schema"] == "hypersync-capture-identity/v2"
    assert identity["recovered"] is True and identity["lineage"] == "unknown"
    assert "collector" not in identity and set(identity["recoverer"]) == {"path", "sha256"}

    bad = Path(tmp) / "orphan"
    bad.mkdir()
    (bad / "orphan.parquet").write_bytes(b"x")
    _assert_reject(ValueError, lambda: fetch_v2.recover_identity(bad))


def test_09_legacy_readability_is_refresh_only(tmp):
    root = Path(tmp) / "legacy-layer"
    path, _ = _make_done(root, schema="hypersync-v2-done/v3")
    _assert_reject(ValueError, lambda: fetch_v2.validate_done_manifest(
        path, 10, 20, TOKEN, URL), "--refresh-manifests")
    fetch_v2.recover_identity(root)
    assert fetch_v2.refresh_manifests(root)["upgraded"] == 1


def test_10_protocol_filter_and_hash_wide_revocation(tmp):
    digest = "e" * 64
    original = collector_history.COLLECTOR_HISTORY
    active = {
        "script": "fetch_hypersync_v2.py", "sha256": digest, "commit": "test",
        "protocol": "hypersync-v2-done/v4", "status": "ACTIVE", "reason": "test",
    }
    revoked = dict(active, protocol="hypersync-capture-identity/v1", status="REVOKED")
    collector_history.COLLECTOR_HISTORY = original + (active,)
    try:
        assert digest in collector_history.historical_script_hashes(
            "fetch_hypersync_v2.py", protocol="hypersync-v2-done/v4")
        assert digest not in collector_history.historical_script_hashes(
            "fetch_hypersync_v2.py", protocol="hypersync-capture-identity/v1")
        collector_history.COLLECTOR_HISTORY += (revoked,)
        assert digest not in collector_history.historical_script_hashes(
            "fetch_hypersync_v2.py", protocol="hypersync-v2-done/v4")
    finally:
        collector_history.COLLECTOR_HISTORY = original


def test_11_recover_then_refresh_order_is_mandatory(tmp):
    root = Path(tmp) / "order"
    _make_done(root, schema="hypersync-v2-done/v3")
    _assert_reject(ValueError, lambda: fetch_v2.refresh_manifests(root),
                   "--recover-identity")
    fetch_v2.recover_identity(root)
    assert fetch_v2.refresh_manifests(root)["upgraded"] == 1


def test_12_unregistered_migrator_rejected(tmp):
    root = Path(tmp) / "migrator"
    path, _ = _make_done(root, schema="hypersync-v2-done/v3")
    fetch_v2.recover_identity(root)
    fetch_v2.refresh_manifests(root)
    done = json.loads(path.read_text())
    done["migrator"]["sha256"] = "f" * 64
    path.write_text(json.dumps(done), encoding="utf-8")
    _assert_reject(ValueError, lambda: fetch_v2.validate_done_manifest(
        path, 10, 20, TOKEN, URL))


def test_13_multirun_prehistoric_requires_capture_from(tmp):
    root = Path(tmp) / "multi-pre"
    _make_done(root, schema=None, start=0, end=10, prehistoric=True)
    _make_done(root, schema=None, start=10, end=20, prehistoric=True)
    fetch_v2.recover_identity(root)
    _assert_reject(ValueError, lambda: fetch_v2.refresh_manifests(root), "--capture-from")


def test_14_staged_capture_missing_identity_is_fatal(tmp):
    root = Path(tmp) / "staged"
    _make_done(root, schema=fetch_v2.MANIFEST_SCHEMA)
    proc = subprocess.run(
        [str(EVM / "staged_capture.sh"), TOKEN, URL, str(root), "10", "20"],
        capture_output=True, text=True,
    )
    assert proc.returncode != 0
    assert "FATAL" in proc.stdout + proc.stderr and "--recover-identity" in proc.stdout + proc.stderr


def test_15_duplicate_done_collector_key_rejected(tmp):
    root = Path(tmp) / "duplicate"
    path, done = _make_done(root, schema=fetch_v2.MANIFEST_SCHEMA)
    text = json.dumps(done)
    text = text.replace('"collector": {', '"collector": null, "collector": {', 1)
    path.write_text(text, encoding="utf-8")
    _assert_reject(ValueError, lambda: fetch_v2.validate_done_manifest(
        path, 10, 20, TOKEN, URL), "duplicate JSON key")


def test_16_unknown_done_schema_rejected(tmp):
    root = Path(tmp) / "unknown-schema"
    path, done = _make_done(root, schema=fetch_v2.MANIFEST_SCHEMA)
    done["schema"] = "hypersync-v2-done/v999"
    path.write_text(json.dumps(done), encoding="utf-8")
    _assert_reject(ValueError, lambda: fetch_v2.validate_done_manifest(
        path, 10, 20, TOKEN, URL))


def test_17_collector_provenance_type_rejected(tmp):
    root = Path(tmp) / "provenance-type"
    path, done = _make_done(root, schema=fetch_v2.MANIFEST_SCHEMA)
    done["collector"] = None
    done["collector_provenance"] = ["legacy-unattributed"]
    path.write_text(json.dumps(done), encoding="utf-8")
    _assert_reject(ValueError, lambda: fetch_v2.validate_done_manifest(
        path, 10, 20, TOKEN, URL))


CASES = tuple(value for name, value in sorted(globals().items())
              if name.startswith("test_") and callable(value))


def main():
    failures = []
    for case in CASES:
        try:
            with tempfile.TemporaryDirectory(prefix="u2-done-v4-", dir="/private/tmp") as tmp:
                case(tmp)
        except (Exception, SystemExit) as exc:
            failures.append((case.__name__, exc))
            print(f"FAIL: {case.__name__}: {type(exc).__name__}: {exc}")
        else:
            print(f"PASS: {case.__name__}")
    if failures:
        print(f"FAIL: U2 done/v4 collector + C12 recovery ({len(failures)}/{len(CASES)})")
        return 1
    print(f"PASS: U2 done/v4 collector + C12 recovery ({len(CASES)}/{len(CASES)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
