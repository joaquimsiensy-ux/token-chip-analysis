#!/usr/bin/env python3
"""旧 −1 案目录合规化迁移：把现行校验器上线前产的 −1 产物机械规范化（fail-closed）。

APU 案（ANOM-012）实证的三处存量漂移，本命令是唯一官方迁移路径（禁手拼）：
  1. data_map.json —— 旧版哈希值带 "sha256:" 前缀，现行 holder_distribution_scan
     等消费者按裸 hex 比对。剥前缀仅限精确形态 sha256:<64hex>，其余值原样保留；
     剥完对在场登记文件重验哈希，失配即整文件拒绝迁移（不把腐坏账本洗白成合规
     格式），登记文件已被清理（缺失）只计数报告不阻断。
  2. candidate_universe.json —— 旧条目稳定 ID 用 cid，现行 handoff_manifest 校验
     要求 id。补 id=cid 并保留 cid（与 APU −2 现场修法同型）；已有 id 的条目不动；
     既无 id 也无 cid 的条目无法机械定名，整文件拒绝。
  3. anchor_plan.json 在场而 anchor_plan.receipt.json 缺 —— receipt 是执行证据，
     不可补票伪造；报告 NEEDS_RERUN，指引用现行 scripts/lib/anchor_plan.py 重跑。

每个可改写文件独立处置：改前产 <name>.bak_migrate_<UTC时间戳> 备份，tmp+rename
原子落盘。退出码：0=目录已全合规；2=存在拒绝/需重跑项（可机械化部分已照常
落盘）；1=输入或写入错误。
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PREFIXED = re.compile(r"^sha256:([0-9a-f]{64})$")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def strip_prefixes(obj):
    """递归剥 sha256: 前缀，返回 (新对象, 剥除计数)；仅精确形态命中。"""
    if isinstance(obj, dict):
        out, n = {}, 0
        for k, v in obj.items():
            out[k], m = strip_prefixes(v)
            n += m
        return out, n
    if isinstance(obj, list):
        out, n = [], 0
        for v in obj:
            item, m = strip_prefixes(v)
            out.append(item)
            n += m
        return out, n
    if isinstance(obj, str):
        m = PREFIXED.match(obj)
        return (m.group(1), 1) if m else (obj, 0)
    return obj, 0


def walk_path_entries(value):
    """与 holder_distribution_scan._walk_entries 同型：找带 path 的 dict 条目。"""
    if isinstance(value, dict):
        if isinstance(value.get("path"), str):
            yield value
        for child in value.values():
            yield from walk_path_entries(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_path_entries(child)


def atomic_write_with_backup(path: Path, obj, stamp: str):
    backup = path.with_name(f"{path.name}.bak_migrate_{stamp}")
    if backup.exists():
        raise OSError(f"备份已存在，拒绝覆盖: {backup}")
    backup.write_bytes(path.read_bytes())
    tmp = path.with_name(f".{path.name}.migrate_tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    return backup


def migrate_data_map(case_dir: Path, stamp: str, report: list) -> bool:
    path = case_dir / "data_map.json"
    if not path.is_file():
        report.append("data_map.json 不在场，跳过")
        return True
    obj = json.loads(path.read_text(encoding="utf-8"))
    stripped, n = strip_prefixes(obj)
    if n == 0:
        report.append("data_map.json 无前缀哈希，已合规")
        return True
    verified = mismatched = missing = 0
    for entry in walk_path_entries(stripped):
        recorded = entry.get("sha256")
        if not isinstance(recorded, str) or not re.fullmatch(r"[0-9a-f]{64}", recorded):
            continue
        target = case_dir / str(entry["path"])
        if not target.is_file():
            missing += 1
            continue
        if sha256_file(target) == recorded:
            verified += 1
        else:
            mismatched += 1
            report.append(f"data_map 登记哈希失配: {entry['path']}")
    if mismatched:
        report.append(f"data_map.json 拒绝迁移：{mismatched} 个登记文件哈希失配"
                      "（不把腐坏账本洗白成合规格式，先人工仲裁）")
        return False
    backup = atomic_write_with_backup(path, stripped, stamp)
    report.append(f"data_map.json 剥前缀 {n} 处（重验在场 {verified}、缺失 {missing}）"
                  f"，备份 {backup.name}")
    return True


def migrate_candidate_universe(case_dir: Path, stamp: str, report: list) -> bool:
    path = case_dir / "candidate_universe.json"
    if not path.is_file():
        report.append("candidate_universe.json 不在场，跳过")
        return True
    obj = json.loads(path.read_text(encoding="utf-8"))
    cands = obj.get("candidates") if isinstance(obj, dict) else obj
    if not isinstance(cands, list) or not cands:
        report.append("candidate_universe.json 无 candidates 数组，拒绝迁移（先人工核）")
        return False
    orphans = [i for i, c in enumerate(cands)
               if not isinstance(c, dict) or ("id" not in c and "cid" not in c)]
    if orphans:
        report.append(f"candidate_universe.json 拒绝迁移：{len(orphans)} 个条目"
                      f"既无 id 也无 cid（首个下标 {orphans[0]}），无法机械定名")
        return False
    patched = copy.deepcopy(obj)
    p_cands = patched.get("candidates") if isinstance(patched, dict) else patched
    n = 0
    for c in p_cands:
        if "id" not in c:
            c["id"] = c["cid"]
            n += 1
    if n == 0:
        report.append("candidate_universe.json 条目已全带 id，已合规")
        return True
    backup = atomic_write_with_backup(path, patched, stamp)
    report.append(f"candidate_universe.json 补 id={n} 条（cid 保留），备份 {backup.name}")
    return True


def check_anchor_receipt(case_dir: Path, report: list) -> bool:
    plan = case_dir / "anchor_plan.json"
    receipt = case_dir / "anchor_plan.receipt.json"
    if not plan.is_file():
        report.append("anchor_plan.json 不在场，跳过")
        return True
    if receipt.is_file():
        report.append("anchor_plan.receipt.json 在场（有效性由 time_spotcheck 消费时验）")
        return True
    report.append("anchor_plan.json 无 kernel receipt —— NEEDS_RERUN：receipt 是执行"
                  "证据不可补票，用现行 scripts/lib/anchor_plan.py 重跑产 plan+receipt")
    return False


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case-dir", required=True, help="旧 −1 案目录")
    a = ap.parse_args(argv)
    case_dir = Path(a.case_dir).resolve()
    if not case_dir.is_dir():
        print(f"[migrate_legacy_case] 案目录不存在: {case_dir}", file=sys.stderr)
        return 1
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report: list[str] = []
    try:
        ok = migrate_data_map(case_dir, stamp, report)
        ok = migrate_candidate_universe(case_dir, stamp, report) and ok
        ok = check_anchor_receipt(case_dir, report) and ok
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"[migrate_legacy_case] ERROR: {exc}", file=sys.stderr)
        return 1
    for line in report:
        print(f"[migrate_legacy_case] {line}")
    print(f"[migrate_legacy_case] {'COMPLIANT' if ok else 'INCOMPLETE'}")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
