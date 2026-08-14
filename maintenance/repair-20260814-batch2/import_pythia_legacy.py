#!/usr/bin/env python3
"""Workorder C only: import the read-only PYTHIA legacy case into isolated staging.

This is deliberately not a formal scripts/ entrypoint.  It validates the frozen
collect manifest and deterministically replays the persisted GPA response before
publishing current replay_edges inputs.  The large edge gzip is hard-linked; no
symlink is accepted or created.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path


EXPECTED_MINT = "CreiuhfwdWCN5mJbMJtA9bBpYQrQF2tCBuZwSPWfpump"
EXPECTED_ROWS = 4_857_654
EXPECTED_CUTOFF = 436_376_480
EXPECTED_EDGE_DIGEST = "11d45c2f0aa0663b564debe5fd065982d913f169d11f3c11b427bf016b1807c7"
MANIFEST_SCHEMA = "solana-collect-manifest/v1"


class ImportFailure(ValueError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def file_ref(path: Path, *, base: Path | None = None, known_sha: str | None = None):
    label = path.relative_to(base).as_posix() if base is not None else path.name
    return {"path": label, "size": path.stat().st_size,
            "sha256": known_sha or sha256_file(path)}


def read_object(path: Path, label: str):
    if path.is_symlink() or not path.is_file():
        raise ImportFailure(f"{label} 缺失、非普通文件或为 symlink: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ImportFailure(f"{label} JSON 非法: {exc}") from exc
    if not isinstance(value, dict):
        raise ImportFailure(f"{label} 顶层必须是对象")
    return value


def source_path(root: Path, rel: str, label: str) -> Path:
    if not isinstance(rel, str) or not rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
        raise ImportFailure(f"{label} 必须是案根内相对路径")
    path = (root / rel).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ImportFailure(f"{label} 逃逸历史案根") from exc
    if path.is_symlink() or not path.is_file():
        raise ImportFailure(f"{label} 缺失、非普通文件或为 symlink: {path}")
    return path


def validate_manifest(root: Path):
    manifest_path = root / "collect_manifest.json"
    manifest = read_object(manifest_path, "collect_manifest")
    expected = {
        "schema": MANIFEST_SCHEMA, "chain": "solana", "mint": EXPECTED_MINT,
        "edge_rows": EXPECTED_ROWS, "edge_logical_sha256": EXPECTED_EDGE_DIGEST,
        "frozen_cutoff_slot": EXPECTED_CUTOFF, "coverage_front_slot": EXPECTED_CUTOFF,
        "gaps": [],
    }
    differences = {key: {"expected": want, "actual": manifest.get(key)}
                   for key, want in expected.items() if manifest.get(key) != want}
    if differences:
        raise ImportFailure("collect_manifest 事实差异: "
                            + json.dumps(differences, ensure_ascii=False, sort_keys=True))
    edge_path = source_path(root, manifest.get("edge_source"), "edge_source")
    meta_path = source_path(root, manifest.get("collector_meta_path"), "collector_meta_path")
    legacy_meta = read_object(meta_path, "legacy collector meta")
    if legacy_meta.get("version") != 2 or legacy_meta.get("launch_covered") is not True:
        raise ImportFailure("legacy collector meta 必须 version=2 且 launch_covered=true")
    frm = legacy_meta.get("from_slot")
    if isinstance(frm, bool) or not isinstance(frm, int) or frm < 0 or frm > EXPECTED_CUTOFF:
        raise ImportFailure("legacy collector meta.from_slot 非法")
    return manifest_path, manifest, edge_path, meta_path, legacy_meta


def replay_edge_facts(edge_path: Path):
    logical = hashlib.sha256()
    rows = 0
    first = last = None
    previous = None
    try:
        with gzip.open(edge_path, "rb") as fh:
            for raw in fh:
                if not raw.strip():
                    continue
                logical.update(raw)
                row = json.loads(raw)
                if not isinstance(row, list) or len(row) != 5:
                    raise ImportFailure(f"edge line {rows + 1} 不是五元组")
                ts, slot, src, dst, amount = row
                if any(isinstance(v, bool) or not isinstance(v, int)
                       for v in (ts, slot, amount)) or amount < 0 \
                        or not isinstance(src, str) or not isinstance(dst, str):
                    raise ImportFailure(f"edge line {rows + 1} 字段类型非法")
                order = (slot, ts, src, dst, str(amount))
                if previous is not None and order < previous:
                    raise ImportFailure(f"edge line {rows + 1} 未按 collector 契约排序")
                previous = order
                point = {"slot": slot, "ts": ts}
                first = first or point
                last = point
                rows += 1
    except ImportFailure:
        raise
    except Exception as exc:
        raise ImportFailure(f"edge gzip/JSON 重放失败: {exc}") from exc
    digest = logical.hexdigest()
    if rows != EXPECTED_ROWS or digest != EXPECTED_EDGE_DIGEST:
        raise ImportFailure(
            "edge 逻辑事实差异: " + json.dumps({
                "rows": {"expected": EXPECTED_ROWS, "actual": rows},
                "sha256": {"expected": EXPECTED_EDGE_DIGEST, "actual": digest}},
                ensure_ascii=False, sort_keys=True))
    if first is None or last is None or last["slot"] > EXPECTED_CUTOFF:
        raise ImportFailure("edge extrema 为空或超过冻结 cutoff")
    return {"rows": rows, "sha256": digest, "first": first, "last": last}


def replay_gpa(root: Path, manifest: dict):
    snap_dir = root / "data/snapshot_final"
    gpa_path = snap_dir / "gpa_with_context.json"
    owners_path = snap_dir / "holders_owners.json"
    snapshot_manifest_path = snap_dir / "snapshot_manifest.json"
    supply_path = snap_dir / "supply.json"
    gpa = read_object(gpa_path, "raw GPA gpa_with_context.json")
    stored_owners = read_object(owners_path, "snapshot_final/holders_owners.json")
    snapshot_manifest = read_object(snapshot_manifest_path, "snapshot_manifest")
    supply = read_object(supply_path, "snapshot supply")

    repo_root = Path(__file__).resolve().parents[2]
    solana_dir = repo_root / "scripts/solana"
    sys.path.insert(0, str(solana_dir))
    from scan_token_accounts import (parse_gpa_response, parse_supply_response,
                                     parse_token_accounts)
    accounts, context_slot = parse_gpa_response(gpa)
    unique, rows, rebuilt, malformed = parse_token_accounts(accounts)
    supply_slot, decimals, supply_raw = parse_supply_response(supply)
    normalized_stored = {str(k): int(v) for k, v in stored_owners.items()}
    differences = {}
    if malformed:
        differences["malformed_accounts"] = malformed
    if rebuilt != normalized_stored:
        differences["owners"] = {
            "rebuilt_count": len(rebuilt), "stored_count": len(normalized_stored),
            "rebuilt_sum": str(sum(rebuilt.values())),
            "stored_sum": str(sum(normalized_stored.values()))}
    expected_supply = int(manifest["supply_raw"])
    facts = {
        "context_slot": context_slot, "supply_slot": supply_slot,
        "decimals": decimals, "supply_raw": supply_raw,
        "raw_accounts": len(accounts), "unique_accounts": len(unique),
        "nonzero_accounts": len(rows), "unique_owners": len(rebuilt),
        "owner_sum_raw": sum(rebuilt.values()),
    }
    expected_facts = {
        "context_slot": EXPECTED_CUTOFF,
        "supply_raw": expected_supply,
        "owner_sum_raw": expected_supply,
        "nonzero_accounts": snapshot_manifest.get("nonzero_token_accounts"),
        "unique_owners": snapshot_manifest.get("unique_owners"),
    }
    for key, want in expected_facts.items():
        if facts.get(key) != want:
            differences[key] = {"expected": want, "actual": facts.get(key)}
    if snapshot_manifest.get("mint") != EXPECTED_MINT \
            or snapshot_manifest.get("context_slot") != EXPECTED_CUTOFF:
        differences["snapshot_manifest_identity"] = {
            "mint": snapshot_manifest.get("mint"),
            "context_slot": snapshot_manifest.get("context_slot")}
    if differences:
        raise ImportFailure("GPA 确定性重放未闭合: "
                            + json.dumps(differences, ensure_ascii=False, sort_keys=True))
    return {
        "gpa_path": gpa_path, "owners_path": owners_path,
        "snapshot_manifest_path": snapshot_manifest_path, "supply_path": supply_path,
        "owners": normalized_stored, "facts": facts,
    }


def camps_from_analysis(root: Path):
    state_path = root / "analysis-state.json"
    state = read_object(state_path, "analysis-state")
    groups = state.get("whale_groups")
    if not isinstance(groups, list) or len(groups) != 8:
        raise ImportFailure("analysis-state.whale_groups 必须恰为冻结案的八组")
    allowed = {"项目方", "大庄", "小庄", "离场庄", "刷量地址", "CEX资金通道",
               "CEX托管", "疑似CEX托管", "流动性池", "其他大户", "历史大户",
               "桥锁仓", "锁仓/销毁"}
    camps: dict[str, list[str]] = {}
    seen = set()
    for group in groups:
        camp = group.get("type")
        addresses = group.get("addresses")
        if camp not in allowed or not isinstance(addresses, list) or not addresses:
            raise ImportFailure("whale_groups type/addresses 不可按唯一机械规则转换")
        for address in addresses:
            if not isinstance(address, str) or not address or address in seen:
                raise ImportFailure(f"whale_groups 地址缺失或重复: {address!r}")
            seen.add(address)
            camps.setdefault(camp, []).append(address)
    return state_path, camps, len(seen)


def atomic_copy(source: Path, target: Path):
    tmp = target.with_name(target.name + ".tmp")
    shutil.copyfile(source, tmp)
    os.replace(tmp, target)


def atomic_json(target: Path, value):
    tmp = target.with_name(target.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(value, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, target)


def import_case(source_root: Path, staging_case: Path):
    source_root = source_root.resolve()
    staging_case = staging_case.resolve()
    if source_root == staging_case or source_root in staging_case.parents:
        raise ImportFailure("staging_case 不得位于历史案根内")
    manifest_path, manifest, edge_path, legacy_meta_path, legacy_meta = \
        validate_manifest(source_root)
    # 先验所有事实；这里之前 staging 不发布任何业务产物。
    edge_facts = replay_edge_facts(edge_path)
    edge_physical_sha = sha256_file(edge_path)
    gpa = replay_gpa(source_root, manifest)
    state_path, camps, camp_addresses = camps_from_analysis(source_root)

    staging_case.mkdir(parents=True, exist_ok=True)
    data_dir = staging_case / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(EXPECTED_MINT.encode("utf-8")).hexdigest()
    staged_edge = data_dir / f"soltx-{key}.jsonl.gz"
    staged_meta = data_dir / f"soltx-{key}.meta.json"
    staged_owners = data_dir / "holders_owners.json"
    staged_snapshot_meta = data_dir / "holders_snapshot_meta.json"
    if staged_edge.exists() or staged_edge.is_symlink():
        raise ImportFailure(f"staging 边目标已存在，拒绝覆盖: {staged_edge}")
    os.link(edge_path, staged_edge)
    if staged_edge.is_symlink() or staged_edge.stat().st_ino != edge_path.stat().st_ino:
        staged_edge.unlink(missing_ok=True)
        raise ImportFailure("边文件未形成同盘 hard link")

    try:
        atomic_copy(gpa["owners_path"], staged_owners)
        owners_ref = file_ref(staged_owners)
        snapshot_meta = {
            "schema": "solana-holder-snapshot-v2", "mint": EXPECTED_MINT,
            "target": {"chain": "solana", "token": EXPECTED_MINT,
                       "as_of_block": EXPECTED_CUTOFF},
            "supply_raw": str(gpa["facts"]["supply_raw"]),
            "sum_accounts_raw": str(gpa["facts"]["owner_sum_raw"]),
            "decimals": gpa["facts"]["decimals"], "closed": True,
            "producer": {"path": "maintenance/repair-20260814-batch2/"
                                  "import_pythia_legacy.py",
                         "sha256": sha256_file(Path(__file__).resolve())},
            "outputs": {"holders_owners": owners_ref},
            "migration": "PYTHIA legacy deterministic GPA replay",
        }
        atomic_json(staged_snapshot_meta, snapshot_meta)
        current_meta = {
            "schema": "sqd-solana-cache/v3", "version": 3,
            "mint": EXPECTED_MINT, "from_slot": legacy_meta["from_slot"],
            "collection_upper_slot": EXPECTED_CUTOFF,
            "launch_covered": True, "gaps": [],
            "edge_logical_sha256": edge_facts["sha256"],
            "edge_rows": edge_facts["rows"],
            "collector": "legacy-import/workorder-C",
            "migration_source_schema": MANIFEST_SCHEMA,
        }
        atomic_json(staged_meta, current_meta)
        atomic_json(staging_case / "camps.json", camps)
        atomic_json(staging_case / "config.json", {
            "chain": "solana", "mint": EXPECTED_MINT,
            "decimals": gpa["facts"]["decimals"], "stake_pools": []})
        # 可审计的小输入均实拷；91MB 边文件只有上面的硬链接。
        for src, name in ((manifest_path, "source_collect_manifest.json"),
                          (legacy_meta_path, "source_legacy_meta.json"),
                          (gpa["gpa_path"], "source_gpa_with_context.json"),
                          (gpa["snapshot_manifest_path"], "source_snapshot_manifest.json"),
                          (gpa["supply_path"], "source_supply.json"),
                          (state_path, "source_analysis-state.json")):
            atomic_copy(src, data_dir / name)
        receipt = {
            "schema": "pythia-legacy-migration/v1", "verdict": "PASS", "exit_code": 0,
            "target": {"chain": "solana", "token": EXPECTED_MINT,
                       "as_of_block": EXPECTED_CUTOFF},
            "mode": "isolated-hardlink-import",
            "source": {
                "collect_manifest": file_ref(manifest_path, base=source_root),
                "legacy_meta": file_ref(legacy_meta_path, base=source_root),
                "edge_file": file_ref(edge_path, base=source_root,
                                      known_sha=edge_physical_sha),
                "raw_gpa": file_ref(gpa["gpa_path"], base=source_root),
                "analysis_state": file_ref(state_path, base=source_root),
            },
            "validated": {"edge": edge_facts, "gpa": gpa["facts"],
                          "whale_groups": 8, "camp_addresses": camp_addresses,
                          "gaps": []},
            "outputs": {
                "edge_hardlink": {**file_ref(staged_edge, known_sha=edge_physical_sha),
                                  "logical_sha256": edge_facts["sha256"],
                                  "same_inode_as_source": True},
                "soltx_meta": file_ref(staged_meta),
                "holders_owners": file_ref(staged_owners),
                "holders_snapshot_meta": file_ref(staged_snapshot_meta),
                "camps": file_ref(staging_case / "camps.json"),
            },
            "producer": {"path": "maintenance/repair-20260814-batch2/"
                                  "import_pythia_legacy.py",
                         "sha256": sha256_file(Path(__file__).resolve())},
        }
        atomic_json(staging_case / "migration_receipt.json", receipt)
    except BaseException:
        # 逐个明确文件回滚；不递归删除目录，也不碰历史案根。
        for path in (staging_case / "migration_receipt.json",
                     staging_case / "config.json", staging_case / "camps.json",
                     data_dir / "source_collect_manifest.json",
                     data_dir / "source_legacy_meta.json",
                     data_dir / "source_gpa_with_context.json",
                     data_dir / "source_snapshot_manifest.json",
                     data_dir / "source_supply.json",
                     data_dir / "source_analysis-state.json",
                     staged_snapshot_meta, staged_owners, staged_meta, staged_edge):
            path.unlink(missing_ok=True)
        raise
    return staging_case / "migration_receipt.json"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-root", type=Path, required=True)
    ap.add_argument("--staging-case", type=Path, required=True)
    args = ap.parse_args(argv)
    try:
        receipt = import_case(args.source_root, args.staging_case)
    except Exception as exc:
        print(f"IMPORT_BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(f"IMPORT_PASS: {receipt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
