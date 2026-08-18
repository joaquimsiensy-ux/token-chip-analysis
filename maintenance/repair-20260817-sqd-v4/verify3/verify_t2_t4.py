#!/usr/local/bin/python3
"""Independent batch-7 defensive verification for workorder T2-T4.

All fixtures and mutations are created below /private/tmp.  The repository is
only imported as the production implementation under test.
"""

from __future__ import annotations

import ast
import gzip
import hashlib
import inspect
import json
import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
for sub in ("solana", "lib", "labels"):
    sys.path.insert(0, str(ROOT / "scripts" / sub))

import curve_cost  # noqa: E402
import replay_edges  # noqa: E402
import sqd_cache_identity  # noqa: E402
from camp_series_provenance import (  # noqa: E402
    SeriesProvenanceError,
    registry_anchor_check,
)
from spl_edge_core import (  # noqa: E402
    EDGE_SCHEMA_FIELDS,
    EDGE_SEMANTICS,
    ORDER_GRANULARITY_TX,
)


PYTHON = "/usr/local/bin/python3"
ZERO = "0x" + "0" * 40
MINT = "So1AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
CURVE = "Curve11111111111111111111111111111111111"
BUYER = "Buyer11111111111111111111111111111111111"
ACTIVE_COLLECTOR_SHA256 = (
    "2589f6a396c262d0747343ef21dee2bc7ba814eaa59eebdfa782fe9253c32212"
)


def logical_digest(rows: list[list[object]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update((json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8"))
    return digest.hexdigest()


def gzip_bytes(rows: list[list[object]]) -> bytes:
    payload = "".join(
        json.dumps(row, ensure_ascii=False) + "\n" for row in rows
    ).encode("utf-8")
    return gzip.compress(payload, mtime=0)


def v4_meta(rows: list[list[object]]) -> dict[str, object]:
    return {
        "schema": "sqd-solana-cache/v4",
        "version": 4,
        "mint": MINT,
        "endpoint": "https://portal.sqd.dev",
        "endpoint_sha256": "1" * 64,
        "collector": "fetch_sqd_transfers_v2.py/v4",
        "collector_sha256": ACTIVE_COLLECTOR_SHA256,
        "edge_schema": list(EDGE_SCHEMA_FIELDS),
        "edge_semantics": EDGE_SEMANTICS,
        "order_granularity": ORDER_GRANULARITY_TX,
        "order_exact": False,
        "dedupe_identity": "slot-txindex-digest/v1",
        "supply_delta_source": "tokenBalances-owner-net",
        "from_slot": min(row[1] for row in rows),
        "finalized_upper_slot": max(row[1] for row in rows),
        "edge_logical_sha256": logical_digest(rows),
        "edge_rows": len(rows),
    }


def cache_paths(case: Path) -> tuple[Path, Path]:
    key = hashlib.sha256(MINT.encode("utf-8")).hexdigest()
    return (
        case / "data" / f"soltx-{key}.jsonl.gz",
        case / "data" / f"soltx-{key}.meta.json",
    )


def file_ref(path: Path) -> dict[str, object]:
    return {
        "path": path.name,
        "size": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


@contextmanager
def cwd(path: Path):
    old = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


def prepare_case(base: Path, name: str, rows: list[list[object]], meta: dict) -> Path:
    case = base / name
    (case / "data").mkdir(parents=True)
    edge_path, meta_path = cache_paths(case)
    edge_path.write_bytes(gzip_bytes(rows))
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    (case / "data" / "solusdt_1h.json").write_text(
        json.dumps([[0, "100", "100", "100", "100"]]), encoding="utf-8"
    )
    return case


def run_curve(case: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [
            PYTHON,
            str(ROOT / "scripts" / "solana" / "curve_cost.py"),
            CURVE,
            "--grad-price",
            "1",
            "--mint",
            MINT,
        ],
        cwd=case,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def t2(base: Path) -> None:
    rows = [[100, 1, 0, -1, CURVE, BUYER, 1_000_000]]
    cases: list[tuple[str, Path, int]] = []

    meta = v4_meta(rows)
    meta["collector_sha256"] = "f" * 64
    cases.append(("unregistered_collector", prepare_case(base, "t2_1", rows, meta), 2))

    meta = v4_meta(rows)
    meta["edge_logical_sha256"] = "0" * 64
    cases.append(("wrong_logical_digest", prepare_case(base, "t2_2", rows, meta), 2))

    meta = v4_meta(rows)
    meta["edge_rows"] = 2
    cases.append(("wrong_edge_rows", prepare_case(base, "t2_3", rows, meta), 2))

    meta = v4_meta(rows)
    tampered = [[100, 1, 0, -1, CURVE, BUYER, 1_000_001]]
    cases.append(("one_logical_byte_tamper", prepare_case(base, "t2_4", tampered, meta), 2))

    cases.append(("valid_v4", prepare_case(base, "t2_5", rows, v4_meta(rows)), 0))

    for name, case, expected_rc in cases:
        result = run_curve(case)
        output_path = case / "data" / "curve_costs.json"
        assert result.returncode == expected_rc, (name, result.returncode, result.stderr)
        if expected_rc:
            assert not output_path.exists(), f"{name} unexpectedly produced {output_path}"
        else:
            assert output_path.is_file(), "valid v4 did not produce curve_costs.json"
            produced = json.loads(output_path.read_text(encoding="utf-8"))
            assert BUYER in produced and produced[BUYER]["tokens"] == 1.0
        tail = (result.stderr.strip().splitlines() or result.stdout.strip().splitlines())[-1]
        print(
            f"T2 {name}: rc={result.returncode} output_exists={output_path.exists()} "
            f"tail={tail}"
        )

    source = inspect.getsource(curve_cost.load_edges)
    assert "validate_cache_meta(meta, mint, legacy_sol5=False)" in source
    assert curve_cost.validate_cache_meta is sqd_cache_identity.validate_cache_meta
    print(
        "T2 shared_validator: identity=true "
        "call=validate_cache_meta(meta, mint, legacy_sol5=False)"
    )


def prepare_reconcile_case(base: Path, name: str, rows: list[list[object]]) -> Path:
    case = prepare_case(base, name, rows, v4_meta(rows))
    owners = case / "data" / "holders_owners.json"
    owners.write_text(json.dumps({MINT: 100}), encoding="utf-8")
    snapshot = {
        "schema": "solana-holder-snapshot-v2",
        "mint": MINT,
        "target": {"chain": "solana", "token": MINT, "as_of_block": 1},
        "closed": True,
        "supply_raw": "100",
        "outputs": {"holders_owners": file_ref(owners)},
    }
    (case / "data" / "holders_snapshot_meta.json").write_text(
        json.dumps(snapshot), encoding="utf-8"
    )
    return case


def t3(base: Path) -> None:
    rows = [[100, 1, 0, -1, ZERO, MINT, 100]]
    # Change one same-width owner byte while keeping deterministic gzip size equal,
    # so the downstream failure is the physical SHA anchor, not the size check.
    replacement = [[100, 1, 0, -1, ZERO, MINT[:-1] + "0", 100]]
    case = prepare_reconcile_case(base, "t3", rows)
    edge_path, meta_path = cache_paths(case)
    original_bytes = edge_path.read_bytes()
    replacement_bytes = gzip_bytes(replacement)
    assert len(replacement_bytes) == len(original_bytes), (
        "fixture must isolate sha mismatch instead of size mismatch"
    )
    original_replay = replay_edges._replay_with_evidence

    def swap_after_replay(in_memory_edges):
        evidence = original_replay(in_memory_edges)
        edge_path.write_bytes(replacement_bytes)
        return evidence

    with cwd(case):
        replay_edges._replay_with_evidence = swap_after_replay
        try:
            gate_pass = replay_edges.cmd_reconcile(
                rows, 1, mint=MINT, cache_meta_path=meta_path
            )
        finally:
            replay_edges._replay_with_evidence = original_replay

        assert gate_pass is True
        published_meta = json.loads(meta_path.read_text(encoding="utf-8"))
        receipt_path = case / "data" / "reconcile_receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        frozen_sha = hashlib.sha256(original_bytes).hexdigest()
        disk_sha = hashlib.sha256(edge_path.read_bytes()).hexdigest()
        assert published_meta["edge_file_sha256"] == frozen_sha
        assert disk_sha != frozen_sha
        assert receipt["edge_digest"] == logical_digest(rows)
        series_path = case / "data" / "camp_share_series.json"
        series_path.write_text("[]", encoding="utf-8")
        try:
            registry_anchor_check(
                {"series_format": "sol-rows"},
                {"inputs.reconcile_receipt": receipt_path},
                series_path,
                expected_chain="solana",
                expected_mint=MINT,
                expected_cutoff_slot=1,
                verify_edge_physical_sha=True,
            )
        except SeriesProvenanceError as exc:
            rejection = str(exc)
        else:
            raise AssertionError("downstream physical anchor accepted replacement edge file")
        assert "物理 sha256" in rejection, rejection

    cmd_source = inspect.getsource(replay_edges.cmd_reconcile)
    parsed = ast.parse(cmd_source)
    sha_args = []
    for node in ast.walk(parsed):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id == "sha256_file":
            sha_args.append(ast.unparse(node.args[0]))
    assert sha_args == ["producer_path"], sha_args
    helper_source = inspect.getsource(replay_edges._read_frozen_formal_edges)
    assert "path.read_bytes()" in helper_source
    assert "_read_frozen_formal_edges(edge_path)" in cmd_source
    print(
        f"T3 frozen_sha={frozen_sha} disk_after_swap_sha={disk_sha} "
        f"receipt_edge_digest={receipt['edge_digest']} gate_pass={gate_pass}"
    )
    print(f"T3 downstream_reject={rejection}")
    print(f"T3 inspect sha256_file_args={sha_args} helper_read_bytes=true")


def expect_reject(name: str, path: Path, needle: str | None = None) -> None:
    try:
        replay_edges._read_frozen_formal_edges(path)
    except (ValueError, OSError) as exc:
        message = str(exc)
    else:
        raise AssertionError(f"{name} unexpectedly accepted")
    if needle is not None:
        assert needle in message, (name, message)
    print(f"T4 {name}: reject={message}")


def t4(base: Path) -> None:
    case = base / "t4"
    case.mkdir()
    valid = case / "valid.gz"
    valid.write_bytes(gzip_bytes([[100, 1, 0, -1, ZERO, MINT, 100]]))

    symlink = case / "symlink.gz"
    symlink.symlink_to(valid)
    expect_reject("symlink", symlink, "符号链接")

    empty = case / "empty.gz"
    empty.write_bytes(b"")
    expect_reject("empty_file", empty, "为空")

    bad_gzip = case / "bad_gzip.gz"
    bad_gzip.write_bytes(b"not-a-gzip")
    expect_reject("bad_gzip", bad_gzip, "gzip/UTF-8")

    bad_utf8 = case / "bad_utf8.gz"
    bad_utf8.write_bytes(gzip.compress(b"\xff\n", mtime=0))
    expect_reject("bad_utf8", bad_utf8, "gzip/UTF-8")

    bad_json = case / "bad_json.gz"
    bad_json.write_bytes(gzip.compress(b"{\n", mtime=0))
    expect_reject("bad_json", bad_json, "非法")

    non7 = case / "non7.gz"
    non7.write_bytes(gzip_bytes([[100, 1, ZERO, MINT, 100]]))
    expect_reject("non_7_tuple", non7, "七元组")

    rows = [[100, 1, 0, -1, ZERO, MINT, 100]]
    mismatch = [[101, 1, 0, -1, ZERO, MINT, 100]]
    mismatch_case = prepare_case(base, "t4_mismatch", rows, v4_meta(rows))
    _, meta_path = cache_paths(mismatch_case)
    with cwd(mismatch_case):
        try:
            replay_edges.cmd_reconcile(
                mismatch, 1, mint=MINT, cache_meta_path=meta_path
            )
        except ValueError as exc:
            message = str(exc)
        else:
            raise AssertionError("in-memory/disk mismatch unexpectedly accepted")
    assert "内存边与冻结边文件不一致" in message, message
    assert not (mismatch_case / "data" / "reconcile_receipt.json").exists()
    print(f"T4 memory_disk_mismatch: reject={message} receipt_exists=false")


def main() -> int:
    base = Path(tempfile.mkdtemp(prefix="batch7-verify3-", dir="/private/tmp"))
    print(f"temp_root={base}")
    t2(base)
    t3(base)
    t4(base)
    print("RESULT T2-T4 CONFIRMED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
