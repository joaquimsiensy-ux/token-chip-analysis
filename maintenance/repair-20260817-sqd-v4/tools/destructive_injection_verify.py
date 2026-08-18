#!/usr/bin/env python3
"""Run batch-5 destructive injections against copies of the ARC live artifact."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


REPO = Path(__file__).resolve().parents[3]
MINT = "61V8vBaqAGMpgDQi4JcAwo1dmBGHsyhzodcPqnEVpump"
EDGE_KEY = hashlib.sha256(MINT.encode("utf-8")).hexdigest()
SOURCE_DATA = (
    REPO
    / "maintenance/repair-20260817-sqd-v4/live_windows"
    / "collision_382697976_382714174/data"
)
EDGE_NAME = f"soltx-{EDGE_KEY}.jsonl.gz"
META_NAME = f"soltx-{EDGE_KEY}.meta.json"
REPLAY = REPO / "scripts/solana/replay_edges.py"
COLLECTOR = REPO / "scripts/solana/fetch_sqd_transfers_v2.py"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], cwd: Path) -> dict:
    completed = subprocess.run(
        command, cwd=cwd, text=True, capture_output=True, timeout=120, check=False)
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def copy_case(root: Path, name: str) -> Path:
    case = root / name
    shutil.copytree(SOURCE_DATA, case / "data")
    return case


def mutate_one_logical_byte(edge_path: Path) -> dict:
    with gzip.open(edge_path, "rb") as handle:
        original = handle.read()
    first_end = original.index(b"\n")
    amount_end = original.rfind(b"]", 0, first_end)
    if amount_end <= 0 or original[amount_end - 1:amount_end] not in b"0123456789":
        raise ValueError("first edge does not end in an integer amount")
    offset = amount_end - 1
    replacement = b"8" if original[offset:offset + 1] != b"8" else b"7"
    mutated = original[:offset] + replacement + original[offset + 1:]
    differences = [index for index, pair in enumerate(zip(original, mutated)) if pair[0] != pair[1]]
    if len(original) != len(mutated) or differences != [offset]:
        raise AssertionError("logical injection must change exactly one byte")
    with edge_path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            zipped.write(mutated)
    return {
        "logical_byte_offset": offset,
        "before": original[offset:offset + 1].decode("ascii"),
        "after": replacement.decode("ascii"),
        "logical_length_unchanged": len(original) == len(mutated),
        "logical_hamming_distance": 1,
    }


def main() -> int:
    original_edge = SOURCE_DATA / EDGE_NAME
    original_meta = SOURCE_DATA / META_NAME
    original_hashes = {"edge": sha256(original_edge), "meta": sha256(original_meta)}
    temp_root = Path(tempfile.mkdtemp(prefix="token-chip-batch5-injection-"))

    case1 = copy_case(temp_root, "edge-byte")
    case1_edge = case1 / "data" / EDGE_NAME
    one_byte = mutate_one_logical_byte(case1_edge)
    edge_result = run([
        "python3", str(REPLAY), "reconcile", "--mint", MINT, "--no-labels"
    ], case1)
    edge_hit = (
        edge_result["returncode"] == 2
        and "meta.edge_logical_sha256 与实际边重放摘要不一致" in edge_result["stderr"]
    )

    case2 = copy_case(temp_root, "collector-hash")
    case2_meta = case2 / "data" / META_NAME
    meta = json.loads(case2_meta.read_text(encoding="utf-8"))
    registered_hash = meta["collector_sha256"]
    meta["collector_sha256"] = "f" * 64
    case2_meta.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    collector_result = run([
        "python3", str(REPLAY), "top", "1", "--mint", MINT, "--no-labels"
    ], case2)
    collector_hit = (
        collector_result["returncode"] != 0
        and "meta.collector_sha256 未命中" in collector_result["stderr"]
    )

    case3 = copy_case(temp_root, "v3-meta")
    case3_meta = case3 / "data" / META_NAME
    v4_meta = json.loads(case3_meta.read_text(encoding="utf-8"))
    v3_meta = {
        "schema": "sqd-solana-cache/v3",
        "version": 3,
        "mint": MINT,
        "from_slot": v4_meta["from_slot"],
        "collection_upper_slot": v4_meta["finalized_upper_slot"],
        "collector": "fetch_sqd_transfers_v2.py/v3",
    }
    case3_meta.write_text(
        json.dumps(v3_meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    v3_replay_result = run([
        "python3", str(REPLAY), "top", "1", "--mint", MINT, "--no-labels"
    ], case3)
    v3_collector_result = run([
        "python3", str(COLLECTOR), MINT,
        "--from-slot", str(v3_meta["from_slot"]),
        "--to-slot", str(v3_meta["collection_upper_slot"]),
        "--wall-min", "1",
        "--key-file", "/dev/null",
        "--url", "http://127.0.0.1:9",
        "--state-rpc", "http://127.0.0.1:9",
    ], case3)
    v3_hit = (
        v3_replay_result["returncode"] != 0
        and "正式重放只接受绑定原始 mint、v4 边契约" in v3_replay_result["stderr"]
        and v3_collector_result["returncode"] == 2
        and "检测到旧 SQD cache meta 'sqd-solana-cache/v3'" in v3_collector_result["stderr"]
        and "格式升级需全量重采，旧缓存请改名归档" in v3_collector_result["stderr"]
    )

    case4 = copy_case(temp_root, "missing-logical-evidence")
    case4_meta = case4 / "data" / META_NAME
    missing_meta = json.loads(case4_meta.read_text(encoding="utf-8"))
    removed_fields = {
        key: missing_meta.pop(key)
        for key in ("edge_logical_sha256", "edge_rows")
    }
    case4_meta.write_text(
        json.dumps(missing_meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    missing_result = run([
        "python3", str(REPLAY), "top", "1", "--mint", MINT, "--no-labels"
    ], case4)
    missing_hit = (
        missing_result["returncode"] != 0
        and "edge_logical_sha256" in missing_result["stderr"]
        and "edge_rows" in missing_result["stderr"]
    )

    originals_unchanged = original_hashes == {
        "edge": sha256(original_edge), "meta": sha256(original_meta)
    }
    report = {
        "schema": "arc-live-destructive-injection/v1",
        "temp_root": str(temp_root),
        "source_artifact": str(SOURCE_DATA.relative_to(REPO)),
        "source_hashes_before": original_hashes,
        "source_unchanged_after": originals_unchanged,
        "injections": {
            "edge_one_logical_byte": {
                **one_byte,
                "mutated_edge_sha256": sha256(case1_edge),
                "target_branch": "cmd_reconcile logical digest comparison",
                "result": edge_result,
                "target_branch_reached": edge_hit,
            },
            "unregistered_collector_sha256": {
                "before": registered_hash,
                "after": "f" * 64,
                "target_branch": "_validate_cache_meta producer history lookup",
                "result": collector_result,
                "target_branch_reached": collector_hit,
            },
            "legacy_v3_meta": {
                "injected_meta": v3_meta,
                "target_branch": "formal v4 meta gate and producer preflight upgrade gate",
                "replay_result": v3_replay_result,
                "collector_preflight_result": v3_collector_result,
                "target_branch_reached": v3_hit,
                "network_sentinel": "127.0.0.1:9; expected rejection precedes access",
            },
            "missing_logical_evidence": {
                "removed_fields": removed_fields,
                "target_branch": "_validate_cache_meta required logical evidence",
                "result": missing_result,
                "target_branch_reached": missing_hit,
            },
        },
    }
    passed = originals_unchanged and edge_hit and collector_hit and v3_hit and missing_hit
    report["status"] = "PASS" if passed else "FAIL"
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
