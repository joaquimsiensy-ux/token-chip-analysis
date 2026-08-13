#!/usr/bin/env python3
"""当前快照持仓分布形态硬闸。

固定统计定义：分箱从私人可入箱供应的 0.000001% 到 100%，相邻边界相差
sqrt(2)，平移复算使用半档。私人主箱低于 100 个 owner 时切换小样本集中度模式。
鼓包零假设是各档人数服从均值为单调递减拟合值的独立 Poisson 分布；使用单侧尾概率，
同一轮全部可检档按 Holm-Bonferroni 控制族错误率 1%。单档至少 5 个 owner 才进入
检验。异常簇还须占净供应至少 2%，且基础分箱与平移分箱成员 Jaccard 至少 0.8。
头部集中度固定检查 top-1/3/5/10、相邻质量跃迁与 HHI。未识别合约披露线为净供应
1%。dust 线等于最低分箱边界。所有常数均无运行时覆盖参数。

定标基线（2026-08-05）：QUQ 当前 owner 快照由头部集中度触发；PYTHIA 当前 46 址
等额组落在基础 33-35 档和平移 32-34 档，成员 Jaccard=0.852。旧案只用于探索性
定标，不构成现役防伪链 fixture。TROLL soltx 元数据 launch_covered=false，未纳入保留集。

scan 重新派生五桶并生成 distribution-scan/v1；validate 从 input_binding 读取上游文件，
重新派生、重新分箱并逐项比对，不信产物自报。owner 快照必须对冻结 total_supply_raw
双向闭合，容差 10bps 写死在本脚本、与供给真值那把容差各是各的旋钮。initial 不绑定
handoff manifest，其 upstream_receipts 是记录性收据（可以缺席不记，记了就逐项三验）；
final 才绑定 READY manifest、身份收据、A4 seal、entity_freeze revision 和三账。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import struct
import sys
import tempfile
import zlib
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "distribution-scan/v1"
ROUNDS_SCHEMA = "distribution-rounds/v1"
WAIVER_SCHEMA = "distribution-exception-receipt/v1"
BIN_MIN_PCT = 0.000001
BIN_MAX_PCT = 100.0
BIN_RATIO = math.sqrt(2.0)
ECONOMIC_GATE_PCT = 2.0
MIN_BIN_OWNERS = 5
SHIFT_JACCARD_MIN = 0.8
SAMPLE_LINE = 100
DISCLOSURE_PCT = 1.0
# 快照对冻结 total supply 的双向闭合容差，单位 bps（万分之一）。
# 这是本闸自己的旋钮，独立写死，**不读 supply_truth 收据里的 tolerance_bps**：
# 供给真值那边即便按批准的 waiver 放宽容差，也不得连带把这里的闭合闸一起松动。
SNAPSHOT_CLOSURE_TOLERANCE_BPS = 10
FAMILY_ALPHA = 0.01
TOP_K_BASELINES = {1: 20.0, 3: 30.0, 5: 40.0, 10: 50.0}
HHI_BASELINE = 0.05
MASS_JUMP_RATIO = 8.0
RECOGNITION_RULE_VERSION = "private-wallet-recognition/v1"
BUCKETS = ("private_main", "private_dust", "public_facility",
           "unresolved_contract", "burn_sentinel")
SOURCE_BUCKETS = {"private": "private", "private_wallet": "private",
                  "private_main": "private", "public_facility": "public_facility",
                  "facility": "public_facility", "cex": "public_facility",
                  "lp": "public_facility", "bridge": "public_facility",
                  "vault": "public_facility", "staking": "public_facility",
                  "infrastructure": "public_facility",
                  "unresolved": "unresolved_contract",
                  "unresolved_contract": "unresolved_contract",
                  "burn": "burn_sentinel", "sentinel": "burn_sentinel",
                  "burn_sentinel": "burn_sentinel"}


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical_sha(value) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def formatted_json_sha(value) -> str:
    """计算 atomic_json 落盘格式的 SHA256，供追加前台账重建复核。"""
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(value, fh, ensure_ascii=False, indent=2)
            fh.write("\n"); fh.flush(); os.fsync(fh.fileno())
        os.replace(name, path)
    except BaseException:
        if os.path.exists(name):
            os.unlink(name)
        raise


def safe_file(root: Path, rel: str, label="文件") -> Path:
    if not isinstance(rel, str) or not rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
        raise ValueError(f"{label}路径非法: {rel!r}")
    raw = root / rel
    if raw.is_symlink():
        raise ValueError(f"{label}拒绝符号链接: {rel}")
    path = raw.resolve(); path.relative_to(root.resolve())
    if not path.is_file():
        raise ValueError(f"{label}不存在: {rel}")
    return path


def rel_entry(root: Path, path: Path) -> dict:
    return {"path": path.resolve().relative_to(root.resolve()).as_posix(),
            "sha256": sha256_file(path), "size": path.stat().st_size}


def strict_raw(value, label: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} 不是非负 raw 整数")
    if isinstance(value, int):
        out = value
    elif isinstance(value, str) and value and value.strip() == value \
            and value.lstrip("+").isdigit():
        out = int(value, 10)
    else:
        raise ValueError(f"{label} 不是非负 raw 整数")
    if out < 0:
        raise ValueError(f"{label} 为负数")
    return out


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def parse_snapshot(path: Path) -> dict[str, int]:
    obj = load_json(path)
    if isinstance(obj, dict) and isinstance(obj.get("balances"), (dict, list)):
        obj = obj["balances"]
    rows = []
    if isinstance(obj, dict):
        rows = list(obj.items())
    elif isinstance(obj, list):
        for i, row in enumerate(obj):
            if not isinstance(row, dict):
                raise ValueError(f"快照第 {i} 行不是对象")
            owner = row.get("owner", row.get("address", row.get("addr")))
            raw = row.get("balance_raw", row.get("raw", row.get("balance")))
            rows.append((owner, raw))
    else:
        raise ValueError("快照顶层必须是 owner->raw 对象或逐 owner 数组")
    out = {}
    for owner, value in rows:
        owner = str(owner or "").strip()
        if not owner:
            raise ValueError("快照存在空 owner")
        key = owner.lower() if owner.lower().startswith("0x") else owner
        if key in out:
            raise ValueError(f"快照 owner 重复: {owner}")
        raw = strict_raw(value, f"{owner}.balance_raw")
        if raw:
            out[key] = raw
    if not out:
        raise ValueError("快照没有非零 owner")
    return out


def find_snapshot(case_dir: Path, requested: str | None) -> tuple[Path, str]:
    if requested:
        path = safe_file(case_dir, requested, "快照")
        return path, requested
    for rel in ("data/balances_final.json", "data/holders_owners.json",
                "balances_final.json", "holders_owners.json"):
        try:
            return safe_file(case_dir, rel, "快照"), rel
        except ValueError:
            pass
    raise ValueError("找不到 A2 owner 快照 balances_final.json/holders_owners.json")


def _walk_entries(value):
    if isinstance(value, dict):
        if isinstance(value.get("path"), str):
            yield value
        for child in value.values():
            yield from _walk_entries(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_entries(child)


def verify_data_map(case_dir: Path, snapshot_rel: str, snapshot: Path) -> Path:
    path = safe_file(case_dir, "data_map.json", "data_map")
    obj = load_json(path)
    matches = [x for x in _walk_entries(obj) if x.get("path") == snapshot_rel]
    if len(matches) != 1:
        raise ValueError("data_map 必须唯一登记当前 owner 快照")
    recorded = str(matches[0].get("sha256", "")).lower()
    if recorded != sha256_file(snapshot):
        raise ValueError("owner 快照 sha256 与 data_map 不一致")
    return path


def load_supply(case_dir: Path) -> tuple[Path, int, int]:
    path = safe_file(case_dir, "supply_truth.json", "供给真值")
    obj = load_json(path)
    if str(obj.get("verdict", "")).upper() != "PASS" or obj.get("exit_code") != 0:
        raise ValueError("supply_truth 非 PASS/exit 0")
    total = strict_raw(obj.get("total_supply_raw", obj.get(
        "frozen_total_supply_raw", obj.get("onchain_total_supply"))),
                       "total_supply_raw")
    net = strict_raw(obj.get("net_supply_raw", obj.get("replay_net", total)),
                     "net_supply_raw")
    if not total or not net or net > total:
        raise ValueError("供给真值 total/net 非法")
    return path, total, net


def threshold_snapshot() -> dict:
    return {
        "bin_ratio": "sqrt(2)", "bin_min_private_pct": BIN_MIN_PCT,
        "bin_max_private_pct": BIN_MAX_PCT,
        "dust_private_pct": BIN_MIN_PCT,
        "economic_gate_net_pct": ECONOMIC_GATE_PCT,
        "minimum_bin_owner_count": MIN_BIN_OWNERS,
        "shift_jaccard_min": SHIFT_JACCARD_MIN, "sample_line": SAMPLE_LINE,
        "unresolved_contract_disclosure_net_pct": DISCLOSURE_PCT,
        "poisson_family_alpha": FAMILY_ALPHA,
        "multiple_testing": "Holm-Bonferroni",
        "low_count_rule": "observed_owner_count>=5",
        "head_top_k_net_pct": {str(k): v for k, v in TOP_K_BASELINES.items()},
        "head_hhi": HHI_BASELINE, "head_adjacent_mass_ratio": MASS_JUMP_RATIO,
        "explanation_member_coverage_min": 0.8,
        "explanation_residual_cluster_pct_max": 1.0,
    }


def recognition_hash() -> str:
    return canonical_sha({"version": RECOGNITION_RULE_VERSION,
                          "source_buckets": SOURCE_BUCKETS,
                          "private_contract_rules": ["evm-safe", "solana-squads"]})


def _extract_partition_rows(obj) -> list[dict]:
    candidates = []
    if isinstance(obj, dict):
        for key in ("auto_excluded_candidate", "distribution_partition",
                    "distribution_classification", "rows", "addresses"):
            if isinstance(obj.get(key), list):
                candidates.extend(obj[key])
    return [x for x in candidates if isinstance(x, dict)]


def derive_partition(case_dir: Path, balances: dict[str, int], stage: str):
    if stage == "initial":
        source_names = ["candidate_screening.json"]
    else:
        source_names = ["entity_freeze.json", "analysis-state.json", "membership_ledger.json",
                        "position_ledger.json", "economic_control_ledger.json",
                        "address_classification.json"]
    sources = []
    explicit: dict[str, str] = {}
    derivation_rows = []
    for rel in source_names:
        try:
            path = safe_file(case_dir, rel, "排除派生来源")
        except ValueError:
            if stage == "initial" and rel == "candidate_screening.json":
                raise
            if stage == "final":
                raise
            continue
        obj = load_json(path); sources.append(rel_entry(case_dir, path))
        for row in _extract_partition_rows(obj):
            addr = str(row.get("address", row.get("owner", row.get("addr", "")))).strip()
            if not addr:
                continue
            addr = addr.lower() if addr.lower().startswith("0x") else addr
            bucket_raw = str(row.get("bucket", row.get("classification", row.get("category", "")))).lower()
            bucket = SOURCE_BUCKETS.get(bucket_raw)
            if bucket is None:
                continue
            if addr in explicit:
                raise ValueError(f"排除派生链同址重复/冲突: {addr}")
            explicit[addr] = bucket
            derivation_rows.append({"address": addr, "bucket": bucket, "source": rel})

    private_total = sum(raw for addr, raw in balances.items()
                        if explicit.get(addr, "private") == "private")
    if private_total <= 0:
        raise ValueError("私人可入箱供应为零")
    dust_raw = max(1, math.ceil(private_total * BIN_MIN_PCT / 100.0))
    partition = {name: [] for name in BUCKETS}
    seen = set()
    for addr, raw in balances.items():
        kind = explicit.get(addr, "private")
        if kind == "private":
            kind = "private_dust" if raw < dust_raw else "private_main"
        if kind not in partition or addr in seen:
            raise ValueError(f"五桶分区失败: {addr}")
        partition[kind].append({"owner": addr, "raw": str(raw)})
        seen.add(addr)
    if seen != set(balances):
        raise ValueError("五桶分区未覆盖全部非零 owner")
    bucket_raw = {k: sum(int(x["raw"]) for x in v) for k, v in partition.items()}
    if sum(bucket_raw.values()) != sum(balances.values()):
        raise ValueError("五桶 raw 和不等于快照 raw 和")
    private_supply = bucket_raw["private_main"] + bucket_raw["private_dust"]
    derivation = {"stage": stage, "algorithm": "distribution-exclusion-derivation/v1",
                  "algorithm_sha256": canonical_sha({"source_buckets": SOURCE_BUCKETS,
                                                       "recognition": recognition_hash()}),
                  "sources": sources, "rows": sorted(derivation_rows,
                                                       key=lambda x: (x["address"], x["source"]))}
    return partition, bucket_raw, private_supply, dust_raw, derivation


def _pava_nonincreasing(values: list[int]) -> list[float]:
    blocks = []
    for i, value in enumerate(values):
        blocks.append([i, i, float(value), 1])
        while len(blocks) >= 2:
            left, right = blocks[-2], blocks[-1]
            if left[2] / left[3] >= right[2] / right[3]:
                break
            blocks[-2:] = [[left[0], right[1], left[2] + right[2], left[3] + right[3]]]
    out = [0.0] * len(values)
    for start, end, total, count in blocks:
        for i in range(start, end + 1):
            out[i] = total / count
    return out


def poisson_upper(observed: int, expected: float) -> float:
    if observed <= expected or expected <= 0:
        return 1.0 if observed <= expected else 0.0
    z = (observed - expected - 0.5) / math.sqrt(expected)
    return max(0.0, min(1.0, 0.5 * math.erfc(z / math.sqrt(2.0))))


def holm_rejections(items: list[tuple[int, float]]) -> set[int]:
    ordered = sorted(items, key=lambda x: (x[1], x[0])); accepted = set(); m = len(ordered)
    for rank, (idx, pvalue) in enumerate(ordered):
        if pvalue <= FAMILY_ALPHA / (m - rank):
            accepted.add(idx)
        else:
            break
    return accepted


def bin_scan(main_rows: list[dict], private_supply: int, net_supply: int, shift: float):
    edges = []
    value = BIN_MIN_PCT * (BIN_RATIO ** shift)
    while value < BIN_MAX_PCT:
        edges.append(value); value *= BIN_RATIO
    edges.append(BIN_MAX_PCT * (BIN_RATIO ** shift))
    bins = [[] for _ in range(len(edges))]
    for row in main_rows:
        pct = int(row["raw"]) * 100.0 / private_supply
        idx = 0 if pct <= edges[0] else min(len(edges) - 1,
                    int(math.floor(math.log(pct / edges[0], BIN_RATIO))) + 1)
        bins[idx].append(row)
    counts = [len(x) for x in bins]
    expected = _pava_nonincreasing(counts)
    tests = [(i, poisson_upper(counts[i], expected[i])) for i in range(len(bins))
             if counts[i] >= MIN_BIN_OWNERS and counts[i] > expected[i]]
    significant = holm_rejections(tests)
    groups = []
    for idx in sorted(significant):
        if groups and idx == groups[-1][-1] + 1:
            groups[-1].append(idx)
        else:
            groups.append([idx])
    clusters = []
    for indices in groups:
        members = [r for i in indices for r in bins[i]]
        raw = sum(int(x["raw"]) for x in members)
        econ = raw * 100.0 / net_supply
        if len(members) < MIN_BIN_OWNERS or econ + 1e-12 < ECONOMIC_GATE_PCT:
            continue
        clusters.append({"bin_start": indices[0], "bin_end": indices[-1],
                         "owner_count": len(members), "raw_balance": str(raw),
                         "net_supply_pct": econ,
                         "members": [{"owner": x["owner"], "raw": x["raw"]}
                                     for x in sorted(members, key=lambda z: z["owner"])],
                         "p_values": [poisson_upper(counts[i], expected[i]) for i in indices]})
    detail = [{"index": i, "upper_private_pct": edge, "owner_count": counts[i],
               "expected_owner_count": expected[i],
               "raw_balance": str(sum(int(x["raw"]) for x in bins[i]))}
              for i, edge in enumerate(edges)]
    return clusters, detail


def _members(cluster) -> set[str]:
    return {x["owner"] for x in cluster.get("members", [])}


def robust_bumps(main_rows, private_supply, net_supply):
    base, base_bins = bin_scan(main_rows, private_supply, net_supply, 0.0)
    shifted, shifted_bins = bin_scan(main_rows, private_supply, net_supply, 0.5)
    out = []
    for cluster in base:
        best = None
        for other in shifted:
            union = _members(cluster) | _members(other)
            score = len(_members(cluster) & _members(other)) / len(union) if union else 0.0
            if best is None or score > best[0]:
                best = (score, other)
        if best and best[0] >= SHIFT_JACCARD_MIN:
            row = dict(cluster); row["trigger"] = "bin_count_bump"
            row["shift_jaccard"] = best[0]
            row["shift_bin_start"] = best[1]["bin_start"]
            row["shift_bin_end"] = best[1]["bin_end"]
            row["cluster_id"] = canonical_sha({"trigger": row["trigger"],
                                                "members": sorted(_members(row))})[:20]
            out.append(row)
    return out, base_bins, shifted_bins


def concentration_cluster(main_rows, net_supply):
    ranked = sorted(main_rows, key=lambda x: (-int(x["raw"]), x["owner"]))
    total = sum(int(x["raw"]) for x in ranked)
    top = {}
    for k in (1, 3, 5, 10):
        top[str(k)] = sum(int(x["raw"]) for x in ranked[:k]) * 100.0 / net_supply
    hhi = sum((int(x["raw"]) / net_supply) ** 2 for x in ranked)
    jump = int(ranked[0]["raw"]) / max(1, int(ranked[1]["raw"])) if len(ranked) > 1 else float("inf")
    hits = [k for k, limit in TOP_K_BASELINES.items() if top[str(k)] >= limit]
    if hhi >= HHI_BASELINE and 1 not in hits:
        hits.append(1)
    if jump >= MASS_JUMP_RATIO and top["1"] >= ECONOMIC_GATE_PCT and 1 not in hits:
        hits.append(1)
    metrics = {"top_k_net_pct": top, "hhi": hhi, "top1_to_top2_ratio": jump,
               "triggered_k": sorted(hits)}
    if not hits:
        return None, metrics
    k = min(hits); members = ranked[:k]; raw = sum(int(x["raw"]) for x in members)
    if raw * 100.0 / net_supply < ECONOMIC_GATE_PCT:
        return None, metrics
    row = {"trigger": "head_concentration", "owner_count": len(members),
           "raw_balance": str(raw), "net_supply_pct": raw * 100.0 / net_supply,
           "members": [{"owner": x["owner"], "raw": x["raw"]} for x in members],
           "metrics": metrics}
    row["cluster_id"] = canonical_sha({"trigger": row["trigger"],
                                        "members": sorted(_members(row))})[:20]
    return row, metrics


def analyze(partition, bucket_raw, private_supply, total_supply, net_supply):
    main_rows = partition["private_main"]
    coverage = {k: {"raw": str(v), "net_supply_pct": v * 100.0 / net_supply}
                for k, v in bucket_raw.items()}
    denominators = {"total_supply_raw": str(total_supply), "net_supply_raw": str(net_supply),
                    "private_boxable_supply_raw": str(private_supply)}
    if len(main_rows) < SAMPLE_LINE:
        ranked = sorted(main_rows, key=lambda x: (-int(x["raw"]), x["owner"]))
        top = {str(k): sum(int(x["raw"]) for x in ranked[:k]) * 100.0 / net_supply
               for k in (1, 3, 5, 10)}
        equal = {}
        for row in ranked:
            equal.setdefault(row["raw"], []).append(row["owner"])
        groups = [{"raw_each": raw, "owners": owners,
                   "combined_raw": str(int(raw) * len(owners))}
                  for raw, owners in sorted(equal.items(), key=lambda x: -int(x[0]))
                  if len(owners) >= MIN_BIN_OWNERS]
        mode = {"complete": True,
                "owner_classifications": [{"owner": x["owner"], "raw": x["raw"],
                                            "bucket": "private_main"} for x in ranked],
                "top_k": top,
                "hhi": sum((int(x["raw"]) / net_supply) ** 2 for x in ranked),
                "equal_amount_groups": groups, "partition_closed": True}
        return {"verdict": "NOT_EVALUABLE", "not_evaluable_reason": "low_sample",
                "small_sample_mode": mode, "abnormal_clusters": [],
                "denominators": denominators, "bucket_coverage": coverage,
                "owner_count_private_main": len(main_rows),
                "disclosure_required": coverage["unresolved_contract"]["net_supply_pct"] >= DISCLOSURE_PCT}
    bumps, base_bins, shifted_bins = robust_bumps(main_rows, private_supply, net_supply)
    head, concentration = concentration_cluster(main_rows, net_supply)
    clusters = bumps + ([head] if head else [])
    clusters.sort(key=lambda x: (x["trigger"], x["cluster_id"]))
    return {"verdict": "ABNORMAL_SHAPE" if clusters else "NORMAL_SHAPE",
            "not_evaluable_reason": None, "small_sample_mode": None,
            "abnormal_clusters": clusters, "denominators": denominators,
            "bucket_coverage": coverage, "owner_count_private_main": len(main_rows),
            "base_bins": base_bins, "shifted_bins": shifted_bins,
            "concentration": concentration,
            "disclosure_required": coverage["unresolved_contract"]["net_supply_pct"] >= DISCLOSURE_PCT}


def _label_manifest(case_dir: Path):
    path = Path(__file__).resolve().parents[2] / "references/labels/manifest.json"
    return {"path": str(path), "sha256": sha256_file(path), "size": path.stat().st_size} \
        if path.is_file() else None


def build_scan(case_dir: Path, stage: str, snapshot_arg: str | None):
    snapshot, snapshot_rel = find_snapshot(case_dir, snapshot_arg)
    balances = parse_snapshot(snapshot)
    data_map = verify_data_map(case_dir, snapshot_rel, snapshot)
    supply, total, net = load_supply(case_dir)
    snapshot_sum = sum(balances.values())
    # 快照必须对 total_supply_raw **双向**闭合：只拦"多出来"挡不住"少了 99%"的残缺
    # 快照，头部集中度和鼓包会被整段藏掉。闭合分母是 total 不是 net——五桶分区物理上
    # 含 burn_sentinel（dead 地址就在快照里），net 只用来算分布百分比；对 net 闭合会
    # 误杀 mint=100/burn=20 这类合法 dead-sink 案。整数交叉乘法，18 位面额的大整数
    # 全程不经过 float。
    if abs(snapshot_sum - total) * 10000 > total * SNAPSHOT_CLOSURE_TOLERANCE_BPS:
        raise ValueError(f"快照 raw 和未对冻结 total supply 闭合: 快照={snapshot_sum} "
                         f"total={total} 容差={SNAPSHOT_CLOSURE_TOLERANCE_BPS}bps")
    partition, bucket_raw, private_supply, dust_raw, derivation = derive_partition(
        case_dir, balances, stage)
    result = analyze(partition, bucket_raw, private_supply, total, net)
    script = Path(__file__).resolve()
    common = {"snapshot": rel_entry(case_dir, snapshot), "data_map": rel_entry(case_dir, data_map),
              "supply_truth": rel_entry(case_dir, supply),
              "exclusion_sources": derivation["sources"],
              "exclusion_derivation_sha256": canonical_sha(derivation),
              "algorithm": {"name": "holder-distribution-gate/v1",
                            "files": [rel_entry(script.parent.parent.parent, script)],
                            "sha256": sha256_file(script)},
              "thresholds_sha256": canonical_sha(threshold_snapshot()),
              "recognition_rules": {"version": RECOGNITION_RULE_VERSION,
                                    "sha256": recognition_hash()},
              "labels_manifest": _label_manifest(case_dir)}
    if stage == "initial":
        receipts = []
        for rel in ("channels_preflight.json", "holders_snapshot_meta.json"):
            candidate = case_dir / rel
            # 记录性收据：案根压根没有这份文件＝合法缺席，跳过不记（split-run 下 −1 出
            # initial scan 时，−2 还没把 preflight 副本拷进案根）。但文件**在场却非法**
            # （符号链接、指到案外、不是普通文件）必须炸——旧版一律 except: pass 会把
            # 掉包过的收据静默漂白成"没记"。
            if not candidate.exists() and not candidate.is_symlink():
                continue
            receipts.append(rel_entry(case_dir, safe_file(case_dir, rel, "上游收据")))
        common["upstream_receipts"] = receipts
        common["handoff_manifest"] = None
    else:
        final_files = {}
        for rel in ("handoff_manifest.json", "identity_snapshot_receipt.json", "a4_seal.json",
                    "entity_freeze.json", "membership_ledger.json", "position_ledger.json",
                    "economic_control_ledger.json", "distribution_scan.json"):
            final_files[rel] = rel_entry(case_dir, safe_file(case_dir, rel, "final 绑定"))
        manifest = load_json(case_dir / "handoff_manifest.json")
        if manifest.get("consumer_min_schema") != "handoff/v3" or manifest.get("status") != "READY":
            raise ValueError("final scan 只接受 READY handoff/v3")
        freeze = load_json(case_dir / "entity_freeze.json")
        seal = load_json(case_dir / "a4_seal.json")
        if seal.get("schema") != "a4-seal/v4" or seal.get("verdict") != "PASS":
            raise ValueError("final scan 只接受 PASS a4-seal/v4")
        common["final_bindings"] = final_files
        common["handoff_manifest"] = {"run_id": manifest.get("run_id"),
                                      **final_files["handoff_manifest.json"]}
        common["entity_freeze_revision"] = len(freeze.get("revisions", [])) + 1
        common["a4_seal_revision"] = seal.get("revision")
    return {"schema": SCHEMA, "stage": stage, "generated_at_utc": utcnow(),
            "exit_code": 0, "thresholds": threshold_snapshot(), "input_binding": common,
            "partition": partition, "partition_check": {"closed": True,
                "snapshot_total_raw": str(sum(balances.values())),
                "bucket_total_raw": str(sum(bucket_raw.values())),
                "owner_count": len(balances), "bucket_owner_counts": {k: len(v) for k, v in partition.items()},
                "dust_cutoff_raw": str(dust_raw)}, **result}


def semantic_payload(scan: dict):
    keys = ("schema", "stage", "exit_code", "thresholds", "input_binding", "partition",
            "partition_check", "verdict", "not_evaluable_reason", "small_sample_mode",
            "abnormal_clusters", "denominators", "bucket_coverage", "owner_count_private_main",
            "base_bins", "shifted_bins", "concentration", "disclosure_required")
    payload = {k: scan.get(k) for k in keys}
    binding = payload.get("input_binding")
    if isinstance(binding, dict):
        binding = dict(binding)
        if isinstance(binding.get("labels_manifest"), dict):
            # labels_manifest 的语义身份是内容哈希；path 是宿主 checkout 的绝对路径，
            # 换 checkout 位置验证同一案目录时会漂移，不得进语义比较（内容漂移仍由 sha256 抓）
            binding["labels_manifest"] = {k: v for k, v in binding["labels_manifest"].items()
                                          if k != "path"}
        # upstream_receipts 是记录性收据（initial 专有）：split-run 下 initial scan 由 −1 生成，
        # 彼时案根尚无 −2 为 G8 拷入的 channels_preflight.json 副本；A5 重验时副本被重算收录，
        # 造成"分区语义逐位一致、仅收据清单漂移"的假阳性，且与 G8 的案根同目录要求物理互斥
        # （TAG 2026-08-12 实撞，用户批准修复）。收据不参与分区/阈值/判定计算，剔出语义比较；
        # final 阶段对 handoff_manifest 的强绑定由 validate_scan 的显式检查承担，不经此路径。
        binding.pop("upstream_receipts", None)
        payload["input_binding"] = binding
    return payload


def write_png(path: Path, scan: dict) -> None:
    width, height = 800, 420
    rgb = bytearray([248, 249, 251] * width * height)
    bins = scan.get("base_bins") or []
    max_count = max([x.get("owner_count", 0) for x in bins] or [1])
    if bins:
        bar_w = max(1, (width - 60) // len(bins))
        for i, row in enumerate(bins):
            bh = int((height - 60) * row.get("owner_count", 0) / max_count)
            for y in range(height - 30 - bh, height - 30):
                for x in range(30 + i * bar_w, min(width - 30, 30 + (i + 1) * bar_w - 1)):
                    pos = (y * width + x) * 3; rgb[pos:pos + 3] = bytes((53, 112, 181))
    raw = b"".join(b"\x00" + bytes(rgb[y * width * 3:(y + 1) * width * 3]) for y in range(height))
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) \
          + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(png)


def scan_output_paths(case_dir: Path, stage: str, output: str | None, chart: str | None, round_n: int | None):
    if stage == "initial":
        return case_dir / (output or "distribution_scan.json"), case_dir / (chart or "charts/distribution_stage1.png")
    if not round_n or round_n < 1:
        raise ValueError("final scan 必须给 --round 正整数")
    base = Path(f"dist_rounds/round_{round_n}")
    return case_dir / (output or str(base / "distribution_scan.json")), \
           case_dir / (chart or str(base / "holder_distribution_round.png"))


def data_broken(stage: str, error: str) -> dict:
    return {"schema": SCHEMA, "stage": stage, "generated_at_utc": utcnow(), "exit_code": 2,
            "thresholds": threshold_snapshot(), "verdict": "NOT_EVALUABLE",
            "not_evaluable_reason": "data_broken", "errors": [error],
            "abnormal_clusters": []}


def validate_rounds_ledger(ledger: dict) -> list[str]:
    errors = []
    if ledger.get("schema") != ROUNDS_SCHEMA or not isinstance(ledger.get("rounds"), list):
        return ["rounds 台账 schema 或 rounds 非法"]
    rounds = ledger["rounds"]
    for index, row in enumerate(rounds, 1):
        if row.get("round_n") != index:
            errors.append(f"rounds 第 {index} 项 round_n 不连续")
        expected = canonical_sha(rounds[index - 2]) if index > 1 else None
        if row.get("previous_entry_sha256") != expected:
            errors.append(f"rounds 第 {index} 项前向哈希断裂")
    terminal = ledger.get("terminal")
    if terminal is not None:
        matched = [row for row in rounds if row.get("round_n") == terminal.get("round_n")]
        if len(matched) != 1 or matched[0].get("status") != terminal.get("status"):
            errors.append("rounds terminal 没有唯一匹配记录")
        elif matched[0].get("status") not in {"NORMAL", "LOW_SAMPLE", "EXPLAINED", "WAIVED"}:
            errors.append("rounds terminal 指向非终态记录")
    return errors


def attach_round_binding(case: Path, scan: dict, round_n: int) -> None:
    """把 final scan 绑定到追加前台账和上一轮 final scan。"""
    ledger_path = case / "distribution_rounds.json"
    if ledger_path.is_file():
        ledger = load_json(ledger_path)
        errors = validate_rounds_ledger(ledger)
        if errors:
            raise ValueError("; ".join(errors))
        if ledger.get("terminal") is not None:
            raise ValueError("rounds 已有 terminal，禁止再生成 final scan")
        rounds = ledger["rounds"]
        if round_n != len(rounds) + 1:
            raise ValueError("final round 必须紧接当前台账")
        previous = rounds[-1] if rounds else None
        previous_scan = rel_entry(case, safe_file(case, previous["final_scan_path"], "上一轮 final scan")) \
            if previous else None
        ledger_entry = {"schema": ROUNDS_SCHEMA, "round_count": len(rounds),
                        "canonical_sha256": canonical_sha(ledger)}
    else:
        if round_n != 1:
            raise ValueError("rounds 台账缺失，不能从非首轮生成 final scan")
        rounds = []
        previous = None
        previous_scan = None
        ledger_entry = None
    scan["round"] = round_n
    scan["previous_round"] = previous.get("round_n") if previous else None
    scan["previous_round_entry_sha256"] = canonical_sha(previous) if previous else None
    scan["input_binding"]["round_binding"] = {
        "round_n": round_n,
        "previous_round": scan["previous_round"],
        "previous_final_scan": previous_scan,
        "rounds_before_append": ledger_entry,
        "terminal_before_append": None,
    }


def validate_round_binding(case: Path, scan: dict) -> list[str]:
    errors = []
    try:
        round_n = scan.get("round")
        if not isinstance(round_n, int) or round_n < 1:
            return ["final scan round 非正整数"]
        rb = (scan.get("input_binding") or {}).get("round_binding")
        if not isinstance(rb, dict) or rb.get("round_n") != round_n \
                or rb.get("terminal_before_append") is not None:
            return ["final scan round_binding 不完整"]
        ledger_path = case / "distribution_rounds.json"
        current = load_json(ledger_path) if ledger_path.is_file() else None
        if current is None:
            if round_n != 1:
                errors.append("rounds 台账缺失，非首轮 final scan 不可重验")
            previous = None; preledger = None
        else:
            errors.extend(validate_rounds_ledger(current))
            rounds = current.get("rounds", [])
            recorded = next((x for x in rounds if x.get("round_n") == round_n), None)
            if recorded:
                scan_path = safe_file(case, recorded.get("final_scan_path"), "已记录 final scan")
                if sha256_file(scan_path) != recorded.get("final_scan_sha"):
                    errors.append("rounds 记录的 final scan 哈希漂移")
                prior = rounds[:round_n - 1]
                preledger = {k: v for k, v in current.items() if k not in {"rounds", "terminal"}}
                preledger.update({"rounds": prior, "terminal": None})
                previous = prior[-1] if prior else None
            else:
                if current.get("terminal") is not None or round_n != len(rounds) + 1:
                    errors.append("final scan 轮次与当前 rounds 台账不相邻")
                preledger = current
                previous = rounds[-1] if rounds else None
        expected_previous = previous.get("round_n") if previous else None
        if scan.get("previous_round") != expected_previous \
                or rb.get("previous_round") != expected_previous:
            errors.append("final scan previous_round 绑定不符")
        expected_entry_sha = canonical_sha(previous) if previous else None
        if scan.get("previous_round_entry_sha256") != expected_entry_sha:
            errors.append("final scan 上一轮 entry 哈希不符")
        expected_scan = rel_entry(case, safe_file(case, previous["final_scan_path"], "上一轮 final scan")) \
            if previous else None
        if rb.get("previous_final_scan") != expected_scan:
            errors.append("final scan 未正确绑定上一轮 final scan")
        expected_ledger = None if round_n == 1 and rb.get("rounds_before_append") is None else \
            ({"schema": ROUNDS_SCHEMA, "round_count": len(preledger["rounds"]),
              "canonical_sha256": canonical_sha(preledger)} if preledger else None)
        if rb.get("rounds_before_append") != expected_ledger:
            errors.append("final scan 未正确绑定追加前 rounds 台账")
    except Exception as exc:
        errors.append(f"final round_binding 不可重验: {exc}")
    return errors


def cmd_scan(args) -> int:
    case = Path(args.case_dir).resolve()
    try:
        out, chart = scan_output_paths(case, args.stage, args.output, args.chart, args.round)
    except ValueError as exc:
        print(f"BLOCK: {exc}", file=sys.stderr); return 2
    try:
        scan = build_scan(case, args.stage, args.snapshot)
        if args.stage == "final":
            attach_round_binding(case, scan, args.round)
        atomic_json(out, scan); write_png(chart, scan)
        print(f"PASS: {args.stage} {scan['verdict']} -> {out}")
        return 0
    except Exception as exc:
        broken = data_broken(args.stage, str(exc)); atomic_json(out, broken)
        print(f"BLOCK: distribution data_broken: {exc}", file=sys.stderr); return 2


def _verify_bound(case: Path, entry: dict, label: str):
    path = safe_file(case, entry.get("path"), label)
    if sha256_file(path) != entry.get("sha256") or path.stat().st_size != entry.get("size"):
        raise ValueError(f"{label}哈希或大小漂移: {entry.get('path')}")
    return path


def validate_scan(case: Path, scan_rel: str, expected_stage: str | None = None) -> list[str]:
    errors = []
    try:
        path = safe_file(case, scan_rel, "scan")
        scan = load_json(path)
        if scan.get("schema") != SCHEMA or scan.get("exit_code") != 0:
            return ["scan schema 非 distribution-scan/v1 或 exit_code 非 0"]
        if expected_stage and scan.get("stage") != expected_stage:
            return [f"scan stage={scan.get('stage')} 不能冒充 {expected_stage}"]
        binding = scan.get("input_binding")
        if not isinstance(binding, dict):
            return ["scan 缺 input_binding"]
        _verify_bound(case, binding["snapshot"], "快照")
        _verify_bound(case, binding["data_map"], "data_map")
        _verify_bound(case, binding["supply_truth"], "供给真值")
        for entry in binding.get("exclusion_sources", []):
            _verify_bound(case, entry, "排除来源")
        # 上游收据是"记录性收据"：可以不记，但**记了就得逐项三验**（存在＋sha256＋size）。
        # 校验对象是 scan 里已记录的条目，**不是磁盘上现有的文件**——方向写反（要求磁盘上
        # 有的都必须被记）会把 6.39.5 修掉的 split-run 三闸死环原样修回来。
        receipts = binding.get("upstream_receipts")
        if receipts is not None:
            if not isinstance(receipts, list):
                raise ValueError("upstream_receipts 不是数组")
            for entry in receipts:
                if not isinstance(entry, dict):
                    raise ValueError("upstream_receipts 条目不是对象")
                _verify_bound(case, entry, "上游收据")
        if binding.get("thresholds_sha256") != canonical_sha(threshold_snapshot()):
            errors.append("阈值快照哈希不符")
        if binding.get("recognition_rules") != {"version": RECOGNITION_RULE_VERSION,
                                                  "sha256": recognition_hash()}:
            errors.append("私人合约钱包识别规则漂移")
        if scan.get("stage") == "initial" and binding.get("handoff_manifest") is not None:
            errors.append("initial scan 禁止绑定 handoff manifest，避免哈希循环")
        if scan.get("stage") == "final" and not binding.get("handoff_manifest"):
            errors.append("final scan 缺 READY handoff manifest 绑定")
        if scan.get("stage") == "final":
            errors.extend(validate_round_binding(case, scan))
        rebuilt = build_scan(case, scan.get("stage"), binding["snapshot"]["path"])
        rebuilt["generated_at_utc"] = scan.get("generated_at_utc")
        if scan.get("stage") == "final":
            for key in ("round", "previous_round", "previous_round_entry_sha256"):
                rebuilt[key] = scan.get(key)
            rebuilt["input_binding"]["round_binding"] = binding.get("round_binding")
        if semantic_payload(rebuilt) != semantic_payload(scan):
            errors.append("scan 语义与独立重算不一致")
    except Exception as exc:
        errors.append(f"scan 不可重验: {exc}")
    return errors


def cmd_validate(args) -> int:
    errors = validate_scan(Path(args.case_dir).resolve(), args.scan, args.expected_stage)
    if errors:
        print("BLOCK: distribution scan validate")
        for error in errors: print(f"- {error}")
        return 2
    print("PASS: distribution scan 独立重算一致")
    return 0


def validate_waiver(case: Path, waiver: dict, scan_path: Path, ledger_sha: str, round_n: int) -> list[str]:
    errors = []
    required = ("user_decided_at_utc", "round_n", "unexplained_clusters",
                "unexplained_raw", "a4_seal_sha256", "final_scan_sha256", "rounds_sha256")
    if waiver.get("schema") != WAIVER_SCHEMA or any(waiver.get(k) in (None, "", []) for k in required):
        errors.append("waiver 收据 schema 或必填字段不完整")
    if waiver.get("round_n") != round_n or waiver.get("final_scan_sha256") != sha256_file(scan_path):
        errors.append("waiver 未绑定当前轮 final scan")
    if waiver.get("rounds_sha256") != ledger_sha:
        errors.append("waiver 未绑定追加前 rounds 台账")
    try:
        if waiver.get("a4_seal_sha256") != sha256_file(case / "a4_seal.json"):
            errors.append("waiver 未绑定当前 A4 seal")
    except OSError:
        errors.append("waiver 的 A4 seal 不存在")
    return errors


def cmd_record_round(args) -> int:
    case = Path(args.case_dir).resolve(); scan_path = safe_file(case, args.scan, "final scan")
    errors = validate_scan(case, args.scan, "final")
    if errors:
        print("BLOCK: final scan 无效: " + "; ".join(errors)); return 2
    scan = load_json(scan_path); round_n = scan.get("round")
    ledger_path = case / "distribution_rounds.json"
    if ledger_path.is_file():
        ledger = load_json(ledger_path)
        lerrors = validate_rounds_ledger(ledger)
        if lerrors or ledger.get("terminal") is not None:
            print("BLOCK: rounds 台账非法或已有 terminal: " + "; ".join(lerrors)); return 2
        rounds = ledger.get("rounds", [])
        if rounds and canonical_sha(rounds[-1]) != scan.get("previous_round_entry_sha256"):
            print("BLOCK: rounds 哈希链断裂"); return 2
    else:
        ledger = {"schema": ROUNDS_SCHEMA, "created_at_utc": utcnow(), "rounds": [], "terminal": None}
        rounds = ledger["rounds"]
        if scan.get("previous_round") is not None or round_n != 1:
            print("BLOCK: rounds 台账缺失，不能删台账后从非首轮继续"); return 2
    if round_n != len(rounds) + 1:
        print("BLOCK: round_n 必须严格递增"); return 2
    a4 = load_json(case / "a4_seal.json")
    claim_ids = {str(x.get("id")) for x in a4.get("claims", [])}
    cluster_ids = {f"dist-{x['cluster_id']}" for x in scan.get("abnormal_clusters", [])}
    new_clusters = sorted(cluster_ids - claim_ids)
    explanation_sha = None; explanation_path = None; terminal = False
    if scan["verdict"] == "NORMAL_SHAPE":
        status = "NORMAL"; terminal = True
    elif scan["verdict"] == "NOT_EVALUABLE" and scan.get("not_evaluable_reason") == "low_sample" \
            and (scan.get("small_sample_mode") or {}).get("complete") is True:
        status = "LOW_SAMPLE"; terminal = True
    elif new_clusters:
        status = "REQUIRES_A4_REFLOW"
    elif args.explanation:
        ep = safe_file(case, args.explanation, "解释检查"); explanation = load_json(ep)
        explanation_sha = sha256_file(ep); explanation_path = args.explanation
        status = "EXPLAINED" if explanation.get("verdict") == "EXPLAINED" else "UNEXPLAINED"
        terminal = status == "EXPLAINED"
    elif args.waiver:
        if round_n < 2:
            print("BLOCK: 未满两轮不能走 waiver"); return 2
        ledger_sha = sha256_file(ledger_path)
        wp = safe_file(case, args.waiver, "waiver"); waiver = load_json(wp)
        werrors = validate_waiver(case, waiver, scan_path, ledger_sha, round_n)
        if werrors:
            print("BLOCK: " + "; ".join(werrors)); return 2
        explanation_sha = sha256_file(wp); explanation_path = args.waiver
        status = "WAIVED"; terminal = True
    else:
        status = "UNEXPLAINED"
    binding = scan["input_binding"]
    entry = {"round_n": round_n, "snapshot_sha": binding["snapshot"]["sha256"],
             "exclusion_derivation_sha": binding["exclusion_derivation_sha256"],
             "entity_freeze_revision": binding.get("entity_freeze_revision"),
             "a4_seal_sha": sha256_file(case / "a4_seal.json"),
             "final_scan_path": args.scan, "final_scan_sha": sha256_file(scan_path),
             "explanation_path": explanation_path, "explanation_sha": explanation_sha,
             "verdict": scan["verdict"],
             "status": status, "new_clusters": new_clusters, "ts_utc": utcnow(),
             "previous_entry_sha256": canonical_sha(rounds[-1]) if rounds else None}
    rounds.append(entry)
    if terminal:
        chart_rel = str(Path(args.scan).parent / "holder_distribution_round.png")
        chart = safe_file(case, chart_rel, "本轮图")
        final_chart = case / "charts/final/holder_distribution_current.png"
        final_chart.parent.mkdir(parents=True, exist_ok=True)
        if any(x for x in final_chart.parent.iterdir() if x.name != final_chart.name):
            print("BLOCK: charts/final 只能物化一张分布终版图"); return 2
        shutil.copyfile(chart, final_chart)
        ledger["terminal"] = {"round_n": round_n, "status": status,
                              "final_scan_path": args.scan,
                              "final_chart_path": "charts/final/holder_distribution_current.png"}
    atomic_json(ledger_path, ledger)
    print(f"PASS: round {round_n} -> {status}")
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in {"validate", "record-round"}:
        cmd = argv.pop(0)
        ap = argparse.ArgumentParser()
        ap.add_argument("--case-dir", required=True)
        ap.add_argument("--scan", required=True)
        if cmd == "validate":
            ap.add_argument("--expected-stage", choices=["initial", "final"])
            return cmd_validate(ap.parse_args(argv))
        ap.add_argument("--explanation"); ap.add_argument("--waiver")
        return cmd_record_round(ap.parse_args(argv))
    ap = argparse.ArgumentParser(description="当前快照持仓分布形态硬闸")
    ap.add_argument("--case-dir", required=True)
    ap.add_argument("--stage", required=True, choices=["initial", "final"])
    ap.add_argument("--snapshot", help="案目录内 A2 owner 快照相对路径")
    ap.add_argument("--output", help="案目录内扫描 JSON 相对路径")
    ap.add_argument("--chart", help="案目录内工作图相对路径")
    ap.add_argument("--round", type=int, help="final 轮次；initial 不使用")
    return cmd_scan(ap.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
