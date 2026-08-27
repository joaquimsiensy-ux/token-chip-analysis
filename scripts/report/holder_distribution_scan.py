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

scan 重新派生五桶并生成 distribution-scan/v2；validate 从 input_binding 读取上游文件，
重新派生、重新分箱并逐项比对，不信产物自报。owner 快照必须对**铸造总量 mint_total**
（replay 侧产物，EVM 取 replay_stats、Solana 取 onchain）逐 wei 精确闭合——replay 记账
不抹除，sum(快照含 dead/zero)==mint 恒成立，对 onchain 闭合会误杀整类 form1 销毁币。
闭合分母绝不取 total_supply_raw/frozen 影子键。initial 不绑定 handoff manifest，其
upstream_receipts 是记录性收据（可缺席不记，记了就逐项三验＋path 白名单）；final 绑定
READY manifest、身份收据、A4 seal、entity_freeze revision、三账，且其 owner 快照必须与
initial scan 是同一份（跨轮不得更换）。
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

SCHEMA = "distribution-scan/v2"
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
# 快照对冻结 total supply 的闭合容差，单位 bps（万分之一）。
# 消化循环第 1 轮（P2-B4）收回到 0＝逐 wei 精确：闭合锚点改用 replay 侧 mint_total 后，
# sum(快照含 dead/zero) == mint_total 在真实 form1/form2 案上均逐 wei 成立（APU/IQ/KOGE 实测），
# 且快照与 totalSupply 同 as_of_block 冻结不存在块高漂移，故不再留任何容差窗口——
# 留窗口会被"删掉几个刚过 dust 线的 owner 翻 low_sample"这类判定翻转攻击钻空（P2-B4 反例）。
# 这是快照闭合闸自己的旋钮，独立写死；不把 supply_truth 的漂移 tolerance 当快照容差。
SNAPSHOT_CLOSURE_TOLERANCE_BPS = 0
# replay_stats 里 mint/burn 的字段名（与 supply_truth_gate.FIELD_PAIRS 同口径，此处内联避免依赖）。
MINT_BURN_FIELD_PAIRS = (("mint_total_wei", "burn_total_wei"),
                         ("mint_total_raw", "burn_total_raw"),
                         ("mint_total", "burn_total"))
# 记录性上游收据的合法 path 白名单（build_scan 只会记这两个名，见 P2-B5）。
UPSTREAM_RECEIPT_WHITELIST = ("channels_preflight.json", "holders_snapshot_meta.json")
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


def load_supply(case_dir: Path) -> tuple[Path, int, int, str, dict, int]:
    """读 supply_truth，返回 (path, onchain, net, chain, obj, supply_drift_raw)。

    onchain（链上流通总量）与 net（分布百分比分母）都**优先取真实生产键**
    onchain_total_supply/replay_net；只有真实键缺席时才回退影子键
    total_supply_raw/net_supply_raw（P1-B2：真实案永远走真实键，注入影子键翻不动结果）。
    闭合分母不在这里取，见 mint_closure_anchor。
    """
    path = safe_file(case_dir, "supply_truth.json", "供给真值")
    obj = load_json(path)
    if str(obj.get("verdict", "")).upper() != "PASS" or obj.get("exit_code") != 0:
        raise ValueError("supply_truth 非 PASS/exit 0")
    onchain = strict_raw(obj.get("onchain_total_supply", obj.get(
        "total_supply_raw", obj.get("frozen_total_supply_raw"))), "onchain_total_supply")
    net = strict_raw(obj.get("replay_net", obj.get("net_supply_raw", onchain)),
                     "net_supply_raw")
    if not onchain or not net:
        raise ValueError("供给真值 onchain/net 非法")
    supply_drift_raw = net - onchain
    if supply_drift_raw > 0:
        drift_boundary = ("供给真值 onchain/net 非法；冻结态例外只接受 PASS/exit 0、"
                          "diff 逐位一致且漂移不超过收据 tolerance_bps")
        try:
            receipt_diff = strict_raw(obj.get("diff"), "supply_truth.diff")
            tolerance_bps = strict_raw(obj.get("tolerance_bps"),
                                       "supply_truth.tolerance_bps")
        except ValueError as exc:
            raise ValueError(f"{drift_boundary}: {exc}") from exc
        if receipt_diff != supply_drift_raw \
                or supply_drift_raw * 10000 > tolerance_bps * onchain:
            raise ValueError(drift_boundary)
    chain = str(obj.get("chain", "")).strip().lower()
    return path, onchain, net, chain, obj, max(0, supply_drift_raw)


def _bound_replay_stats(case_dir: Path, supply_obj: dict) -> Path | None:
    """取 supply_truth 收据 inputs.replay_stats **绑定的那份**实物（不是案根硬编码文件名）。

    这条路径与 shared_release_receipt._bound_replay_totals 同口径：案根遏制＋本函数自带
    sha256/size 三验（B-4：本扫描器可在发布闸之外独立运行，receipt_validate 的三验只在
    发布链路上有人跑——这里不引用别人的检查作自己的证据，绑定登记的 sha/size 与实物
    不符即拒）。绑定缺席返回 None。
    """
    ref = (supply_obj.get("inputs") or {}).get("replay_stats")
    if not isinstance(ref, dict) or not str(ref.get("path") or ""):
        return None
    path = Path(str(ref["path"]))
    path = path if path.is_absolute() else (case_dir / path)
    path = path.resolve()
    try:
        path.relative_to(Path(case_dir).resolve())
    except ValueError as exc:
        raise ValueError("收据绑定的 replay_stats 实物不在当前案根内，不得作闭合锚点") from exc
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"收据绑定的 replay_stats 实物缺失或非普通文件: {ref['path']}")
    # B-4：收据登记的 sha256/size 必须与实物一致——换包/陈旧实物不得作闭合锚点。
    if ref.get("sha256") != sha256_file(path) or ref.get("size") != path.stat().st_size:
        raise ValueError(f"收据绑定的 replay_stats 实物 sha256/size 与登记不符（换包或陈旧）: "
                         f"{ref['path']}")
    return path


def _mint_from_stats(stats: dict, label: str) -> tuple[int, int]:
    for mk, bk in MINT_BURN_FIELD_PAIRS:
        if mk in stats:
            return (strict_raw(stats[mk], f"{label}.{mk}"),
                    strict_raw(stats.get(bk, 0), f"{label}.{bk}"))
    raise ValueError(f"{label} 缺 mint 字段（认 {[m for m, _ in MINT_BURN_FIELD_PAIRS]}）")


def mint_closure_anchor(case_dir: Path, supply_obj: dict, chain: str,
                        onchain: int) -> tuple[int, str, dict | None]:
    """快照闭合分母＝铸造总量 mint_total（replay 侧），分链且绝不依赖影子键。

    replay 对 sink 是记账不抹除：sum(balances_final 含 dead/zero) == mint_total 恒成立，
    form1（真 _burn，onchain==mint−burn）与 form2（转 dead 不减供给，onchain==mint）都如此
    （APU/IQ/KOGE 真案逐 wei 实测）。对 onchain/total 闭合会把整类 form1 币误杀（P1-B3）。

    取值顺序（N-B1：**已绑定已验证的链路优先**，案根裸件永不作锚点来源）：
      Solana：== onchain（scanner require_snapshot_closed 已保证 sum==supply，另一套精确等式，
              不套 EVM 的 replay mint 语义）。
      EVM：① supply_truth 收据 inputs.replay_stats **绑定**的那份实物（已过三验＋案根遏制，
              且这里再交叉验 mint−burn == replay_net，与四查同一口径）
           ② supply_truth 收据的 mint_total 字段（同样受四查链约束）
           ③ supply_truth 的 onchain_total_supply（无 burn 的简单真实案）
    绝不取 total_supply_raw/frozen_total_supply_raw 影子键。

    **案根裸 replay_stats.json 不是锚点来源**（N-B1）：真案 9/10 把 replay_stats 放
    data/、out/、replay/ 等子目录，只有 APU 在案根——把案根硬编码文件名排在第一，既让
    "抹平快照＋伪造一份未绑定案根件"直接过闸（攻击面），又让"案根留一份陈旧件"把合法案
    打成 data_broken（误伤面，对 8/9 真案成立）。未绑定的文件不是证据，既不该被采用，
    也不该有一票否决权，故合法但未绑定的案根件**忽略**（理由见工单）。但它若**在场却非法**
    （符号链接／非普通文件）仍 fail-closed 拒（N-B2）——与本文件 F-08 "在场非法不得静默
    漂白"同一把尺子，案目录被动过手脚是完整性信号，不因该文件不参与计算而豁免。
    """
    if chain == "solana":
        return onchain, "solana_onchain", None
    # N-B2：案根同名件在场即验，非法即拒；它不参与取值，只做完整性闸。
    root_stats = Path(case_dir) / "replay_stats.json"
    if root_stats.is_symlink() or (root_stats.exists() and not root_stats.is_file()):
        raise ValueError("案根 replay_stats.json 在场但非法（符号链接或非普通文件），"
                         "拒绝静默换档：请移除或换成真实 replay 产物")
    bound = _bound_replay_stats(case_dir, supply_obj)
    if bound is not None:
        mint, burn = _mint_from_stats(load_json(bound), "绑定 replay_stats")
        replay_net = supply_obj.get("replay_net")
        if replay_net not in (None, "") and mint - burn != strict_raw(replay_net, "replay_net"):
            raise ValueError("绑定 replay_stats 的 mint−burn 与收据 replay_net 不一致，"
                             "闭合锚点不可信")
        return mint, "bound_replay_mint", rel_entry(case_dir, bound)
    if supply_obj.get("mint_total") not in (None, ""):
        return strict_raw(supply_obj.get("mint_total"), "supply_truth.mint_total"), \
            "supply_truth_mint", None
    if supply_obj.get("onchain_total_supply") not in (None, ""):
        return strict_raw(supply_obj.get("onchain_total_supply"), "onchain_total_supply"), \
            "supply_truth_onchain", None
    raise ValueError("无法确定快照闭合锚点：缺收据绑定的 replay_stats / supply_truth.mint_total "
                     "/ onchain_total_supply（total_supply_raw 影子键不作闭合分母）")


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


def analyze(partition, bucket_raw, private_supply, total_supply, net_supply,
            supply_drift_raw=0):
    main_rows = partition["private_main"]
    coverage = {k: {"raw": str(v), "net_supply_pct": v * 100.0 / net_supply}
                for k, v in bucket_raw.items()}
    # B-3（批 D，schema 升 v2）：铸造总量键名改 mint_total_raw——旧名 total_supply_raw 在
    # 真 _burn 案上语义误导（IQ 案与流通量差 34.9%）；net_supply_raw 语义不变。
    denominators = {"mint_total_raw": str(total_supply), "net_supply_raw": str(net_supply),
                    "private_boxable_supply_raw": str(private_supply)}
    if supply_drift_raw:
        denominators["supply_drift_raw"] = str(supply_drift_raw)
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
    supply, onchain, net, chain, supply_obj, supply_drift_raw = load_supply(case_dir)
    anchor, anchor_source, replay_ref = mint_closure_anchor(case_dir, supply_obj, chain, onchain)
    snapshot_sum = sum(balances.values())
    # 快照必须对**铸造总量 mint_total（闭合锚点）逐 wei 精确闭合**：缺口和超发同拦。
    # 锚点是 mint 不是 onchain——replay 记账不抹除，sum(快照含 dead/zero) == mint 恒成立；
    # 对 onchain(=mint−burn) 闭合会把整类 form1 销毁币误杀（P1-B3，APU/IQ/KOGE 真案实测）。
    # 零容差：块高同点冻结无漂移，留窗口会被"抹平快照翻 low_sample"攻击钻空（P2-B4）。
    if abs(snapshot_sum - anchor) * 10000 > anchor * SNAPSHOT_CLOSURE_TOLERANCE_BPS:
        raise ValueError(f"快照 raw 和未对铸造总量 mint 精确闭合: 快照={snapshot_sum} "
                         f"mint={anchor}（{anchor_source}）容差={SNAPSHOT_CLOSURE_TOLERANCE_BPS}bps")
    partition, bucket_raw, private_supply, dust_raw, derivation = derive_partition(
        case_dir, balances, stage)
    # denominators：mint 展示铸造总量；net 保持冻结 replay_net 分布分母。
    result = analyze(partition, bucket_raw, private_supply, anchor, net,
                     supply_drift_raw=supply_drift_raw)
    script = Path(__file__).resolve()
    common = {"snapshot": rel_entry(case_dir, snapshot), "data_map": rel_entry(case_dir, data_map),
              "supply_truth": rel_entry(case_dir, supply),
              "mint_closure_anchor": {"source": anchor_source, "raw": str(anchor),
                                      **({"replay_stats": replay_ref} if replay_ref else {})},
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
        # P0-B1：final 轮吃的 owner 快照必须与它绑定的 initial scan 是同一份。
        # 否则可以 initial 喂真快照过第二层交叉检查、final 换一份"抹平/换仓"快照产终态判定，
        # 终版图/A5 seal/发布闸全程放行（盲审端到端复现）。两个 sha 本已在场，直接比对。
        initial_scan = load_json(case_dir / "distribution_scan.json")
        initial_snapshot = ((initial_scan.get("input_binding") or {}).get("snapshot") or {})
        if initial_snapshot.get("sha256") != common["snapshot"]["sha256"]:
            raise ValueError(
                "final scan 快照与绑定的 initial scan 快照不一致（final 轮不得更换 owner 快照）: "
                f"initial={initial_snapshot.get('sha256')} final={common['snapshot']['sha256']}")
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
    first_snapshot_sha = rounds[0].get("snapshot_sha") if rounds else None
    for index, row in enumerate(rounds, 1):
        if row.get("round_n") != index:
            errors.append(f"rounds 第 {index} 项 round_n 不连续")
        expected = canonical_sha(rounds[index - 2]) if index > 1 else None
        if row.get("previous_entry_sha256") != expected:
            errors.append(f"rounds 第 {index} 项前向哈希断裂")
        # P0-B1：同一 cutoff 的当前快照跨轮必须是同一份——各轮 snapshot_sha 必须一致，
        # 否则某一轮偷换 owner 快照（抹平/换仓）而台账照样连续。现在只记不比＝漏洞。
        if row.get("snapshot_sha") != first_snapshot_sha:
            errors.append(f"rounds 第 {index} 项 snapshot_sha 与首轮不一致（当前快照跨轮被更换）")
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
            return ["scan schema 非 distribution-scan/v2 或 exit_code 非 0"]
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
                # P2-B5：path 钉白名单——build_scan 只会记这两个名，记别的（哪怕文件真存在、
                # sha/size 都对）也是伪造记录项，直接拒。
                if entry.get("path") not in UPSTREAM_RECEIPT_WHITELIST:
                    raise ValueError(f"上游收据 path 不在白名单 {UPSTREAM_RECEIPT_WHITELIST}: "
                                     f"{entry.get('path')}")
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
