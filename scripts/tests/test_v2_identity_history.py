#!/usr/bin/env python3
"""R-3 v2: historical capture identity is accepted without weakening shape checks."""
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
EVM = HERE.parent / "evm"
FETCH_SCRIPT = EVM / "fetch_hypersync_v2.py"
sys.path.insert(0, str(EVM))

import fetch_hypersync_v2 as fetch_v2
from channels_preflight import ChannelsPreflightError, _v2_provenance
from collector_history import historical_script_hashes


TOKEN = "0x" + "a" * 40
URL = "https://bsc.hypersync.xyz"
HISTORICAL_HASH = sorted(historical_script_hashes("fetch_hypersync_v2.py"))[0]
UNKNOWN_HASH = "f" * 64


def _write_parquets(run_dir, blocks):
    import duckdb

    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
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
        con.execute(f"COPY logs TO '{run_dir / 'logs.parquet'}' (FORMAT parquet)")
        con.execute("CREATE TABLE blocks(number BIGINT, timestamp BIGINT)")
        for block in blocks:
            con.execute("INSERT INTO blocks VALUES (?,?)", [block, 1700000000 + block])
        con.execute(f"COPY blocks TO '{run_dir / 'blocks.parquet'}' (FORMAT parquet)")
    finally:
        con.close()


def _file_meta(path, block_col):
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


def _make_done(outdir, start=10, end=20, *, schema=fetch_v2.MANIFEST_SCHEMA,
               capture_from=10):
    run_dir = Path(outdir) / f"run_{start}"
    _write_parquets(run_dir, [start, end - 1])
    done = {
        "schema": schema,
        "query_schema": fetch_v2.QUERY_SCHEMA,
        "capture_from": capture_from,
        "from_block": start,
        "to_block": end,
        "next_block": end,
        "token": TOKEN,
        "url": URL,
        "client_version": "historical-fixture",
    }
    if schema == fetch_v2.MANIFEST_SCHEMA:
        done["files"] = {
            "logs.parquet": _file_meta(run_dir / "logs.parquet", "block_number"),
            "blocks.parquet": _file_meta(run_dir / "blocks.parquet", "number"),
        }
    (run_dir / "done.json").write_text(json.dumps(done), encoding="utf-8")
    return run_dir


def _write_identity(outdir, collector_hash, *, collector_extra=None, top_extra=None,
                    identity_url=URL):
    identity = fetch_v2.capture_identity(TOKEN, identity_url)
    identity["collector"] = {
        "path": "fetch_hypersync_v2.py",
        "sha256": collector_hash,
    }
    if collector_extra:
        identity["collector"].update(collector_extra)
    if top_extra:
        identity.update(top_extra)
    path = Path(outdir) / fetch_v2.IDENTITY_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(identity, indent=1), encoding="utf-8")
    return path


def _assert_raises(exc_type, fn, message):
    try:
        fn()
    except exc_type:
        return
    raise AssertionError(message)


class _FakeClient:
    def __init__(self):
        self.collected = False

    async def get_height(self):
        return 30

    async def collect_parquet(self, run_dir, query, _cfg):
        self.collected = True
        _write_parquets(run_dir, [query.from_block, query.to_block - 1])


def _run_main(outdir, *, expect_reject=False):
    client = _FakeClient()
    args = argparse.Namespace(
        token="fixture-token", url=URL, token_addr=TOKEN, outdir=str(outdir),
        from_block=10, to_block=30, concurrency=1, token_file=None,
    )
    passthrough = lambda **kwargs: argparse.Namespace(**kwargs)
    patches = (
        mock.patch.object(fetch_v2, "parse_args", return_value=args),
        mock.patch.object(fetch_v2, "ClientConfig", side_effect=passthrough),
        mock.patch.object(fetch_v2.hypersync, "HypersyncClient", return_value=client),
        mock.patch.object(fetch_v2, "Query", side_effect=passthrough),
        mock.patch.object(fetch_v2, "LogSelection", side_effect=passthrough),
        mock.patch.object(fetch_v2, "FieldSelection", side_effect=passthrough),
        mock.patch.object(fetch_v2, "StreamConfig", side_effect=passthrough),
    )
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
        if expect_reject:
            _assert_raises(SystemExit, lambda: asyncio.run(fetch_v2.main()),
                           "main must reject an unsupported capture identity")
            assert not client.collected, "rejected identity must fail before collection"
        else:
            asyncio.run(fetch_v2.main())
            assert client.collected, "main must continue collection after the historical run"


def _run_refresh(outdir):
    return subprocess.run(
        [sys.executable, str(FETCH_SCRIPT), "--refresh-manifests", "--outdir", str(outdir)],
        capture_output=True,
        text=True,
    )


def test_historical_identity_find_resume_positive(tmp):
    root = Path(tmp) / "resume"
    _make_done(root)
    _write_identity(root, HISTORICAL_HASH)
    assert fetch_v2.find_resume_block(root, 10, 30, TOKEN, URL) == 20


def test_historical_identity_refresh_positive(tmp):
    root = Path(tmp) / "refresh"
    _make_done(root, schema="hypersync-v2-done/v2")
    identity_path = _write_identity(root, HISTORICAL_HASH)
    before = identity_path.read_bytes()
    proc = _run_refresh(root)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert identity_path.read_bytes() == before, "refresh must not rewrite historical identity"
    assert json.loads((root / "run_10" / "done.json").read_text())["schema"] \
        == fetch_v2.MANIFEST_SCHEMA


def test_historical_identity_main_continuation_positive(tmp):
    root = Path(tmp) / "continuation"
    _make_done(root)
    _write_identity(root, HISTORICAL_HASH)
    _run_main(root)
    assert (root / "run_20" / "done.json").is_file()


def test_mixed_directory_preflight_positive(tmp):
    root = Path(tmp) / "mixed"
    _make_done(root, 10, 20, capture_from=10)
    _make_done(root, 20, 30, capture_from=10)
    _write_identity(root, HISTORICAL_HASH)

    # Mixed-version directories prove contiguous range and bound file receipts only.
    # capture_identity.json names the directory lineage issuer; it does not prove that
    # every done segment was collected by the same collector version.
    proof = _v2_provenance(root, TOKEN, 10, 30)
    assert proof["completion"] == {
        "reason": "contiguous_done_receipts", "lo": 10, "hi": 30,
    }


def test_unknown_hash_rejected_everywhere(tmp):
    root = Path(tmp) / "unknown"
    _make_done(root)
    _write_identity(root, UNKNOWN_HASH)
    _assert_raises(SystemExit,
                   lambda: fetch_v2.find_resume_block(root, 10, 30, TOKEN, URL),
                   "find_resume_block must reject an unknown collector hash")
    proc = _run_refresh(root)
    assert proc.returncode != 0 and "fail-closed" in proc.stderr, proc.stdout + proc.stderr
    _run_main(root, expect_reject=True)
    _assert_raises(ChannelsPreflightError, lambda: _v2_provenance(root, TOKEN, 10, 20),
                   "_v2_provenance must reject an unknown collector hash")


def test_collector_extra_key_rejected_both_sides(tmp):
    root = Path(tmp) / "collector-extra"
    _make_done(root)
    _write_identity(root, HISTORICAL_HASH, collector_extra={"note": "must reject"})
    _assert_raises(ValueError, lambda: fetch_v2.ensure_outdir_identity(root, TOKEN, URL),
                   "ensure_outdir_identity must reject collector extra keys")
    _assert_raises(ChannelsPreflightError, lambda: _v2_provenance(root, TOKEN, 10, 20),
                   "_v2_provenance must reject collector extra keys")


def test_top_level_extra_key_rejected_both_sides(tmp):
    root = Path(tmp) / "top-extra"
    _make_done(root)
    _write_identity(root, HISTORICAL_HASH, top_extra={"note": "must reject"})
    _assert_raises(ValueError, lambda: fetch_v2.ensure_outdir_identity(root, TOKEN, URL),
                   "ensure_outdir_identity must reject top-level extra keys")
    _assert_raises(ChannelsPreflightError, lambda: _v2_provenance(root, TOKEN, 10, 20),
                   "_v2_provenance must reject top-level extra keys")


def test_non_string_collector_fields_rejected_both_sides(tmp):
    bad_collectors = (
        {"path": "fetch_hypersync_v2.py", "sha256": [HISTORICAL_HASH]},
        {"path": "fetch_hypersync_v2.py", "sha256": 7},
        {"path": ["fetch_hypersync_v2.py"], "sha256": HISTORICAL_HASH},
    )
    for index, collector in enumerate(bad_collectors):
        ensure_root = Path(tmp) / f"non-string-ensure-{index}"
        _make_done(ensure_root)
        identity_path = _write_identity(ensure_root, HISTORICAL_HASH)
        identity = json.loads(identity_path.read_text(encoding="utf-8"))
        identity["collector"] = collector
        identity_path.write_text(json.dumps(identity), encoding="utf-8")
        _assert_raises(
            ValueError,
            lambda root=ensure_root: fetch_v2.ensure_outdir_identity(
                root, TOKEN, URL),
            "ensure_outdir_identity must control-reject non-string collector fields",
        )

        preflight_root = Path(tmp) / f"non-string-preflight-{index}"
        _make_done(preflight_root)
        identity_path = _write_identity(preflight_root, HISTORICAL_HASH)
        identity = json.loads(identity_path.read_text(encoding="utf-8"))
        identity["collector"] = collector
        identity_path.write_text(json.dumps(identity), encoding="utf-8")
        _assert_raises(
            ChannelsPreflightError,
            lambda root=preflight_root: _v2_provenance(root, TOKEN, 10, 20),
            "_v2_provenance must control-reject non-string collector fields",
        )


def test_identity_url_must_match_every_done(tmp):
    root = Path(tmp) / "identity-url-mismatch"
    _make_done(root)
    _write_identity(
        root, HISTORICAL_HASH, identity_url="https://evil.example.invalid"
    )
    _assert_raises(
        ChannelsPreflightError,
        lambda: _v2_provenance(root, TOKEN, 10, 20),
        "_v2_provenance must reject identity.url/done.url mismatch",
    )


def test_ensure_preserves_historical_identity_bytes(tmp):
    root = Path(tmp) / "immutable"
    _make_done(root)
    identity_path = _write_identity(root, HISTORICAL_HASH)
    before = identity_path.read_bytes()
    fetch_v2.ensure_outdir_identity(root, TOKEN, URL)
    assert identity_path.read_bytes() == before


def test_current_hash_preflight_positive(tmp):
    root = Path(tmp) / "current"
    _make_done(root)
    current = fetch_v2.capture_identity(TOKEN, URL)["collector"]["sha256"]
    _write_identity(root, current)
    proof = _v2_provenance(root, TOKEN, 10, 20)
    assert proof["completion"]["reason"] == "contiguous_done_receipts"


CASES = (
    test_historical_identity_find_resume_positive,
    test_historical_identity_refresh_positive,
    test_historical_identity_main_continuation_positive,
    test_unknown_hash_rejected_everywhere,
    test_collector_extra_key_rejected_both_sides,
    test_top_level_extra_key_rejected_both_sides,
    test_non_string_collector_fields_rejected_both_sides,
    test_identity_url_must_match_every_done,
    test_ensure_preserves_historical_identity_bytes,
    test_mixed_directory_preflight_positive,
    test_current_hash_preflight_positive,
)


def main():
    try:
        import duckdb  # noqa: F401
    except ImportError:
        raise SystemExit("duckdb required for v2 identity history regression")
    failures = []
    for case in CASES:
        try:
            with tempfile.TemporaryDirectory() as tmp:
                case(tmp)
        except (Exception, SystemExit) as exc:
            failures.append((case.__name__, exc))
            print(f"FAIL: {case.__name__}: {type(exc).__name__}: {exc}")
        else:
            print(f"PASS: {case.__name__}")
    if failures:
        print(f"FAIL: R-3 v2 identity history ({len(failures)}/{len(CASES)} cases)")
        return 1
    print("PASS: R-3 v2 historical identity maintenance/consumer parity")
    return 0


if __name__ == "__main__":
    sys.exit(main())
