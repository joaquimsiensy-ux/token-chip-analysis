#!/usr/bin/env python3
"""split-run 交接契约工具（references/split-run.md §2 的机器实现）。

子命令：
  generate  −1 收工产 handoff_manifest.json（语义收据：gate 状态自动适配＋产物 allowlist 哈希）
  verify    −2 开工 fail-closed 校验（文件齐/哈希对/gate 重查/schema 兼容/状态 READY）
  receipt   −1 每步追加 stage1_receipts.json 执行收据（断点恢复＋盲化审计）
  freeze    −2 实体冻结物化 entity_freeze.json（revision 追加制）；--check-unseal 把关揭盲/读 sealed

退出码语义（对齐 skill 现有 gate）：0=放行；2=验证不通过/前置未满足（硬停）；1=脚本自身错误（修完重跑）。
用法示例：
  python3 handoff_manifest.py generate --case-dir <案目录> --mode full --status READY \
      --producer-model gpt-5.6 --case-id QUQ-bsc --chain bsc --contract 0x... --cutoff 2026-07-30T00:00:00Z \
      --gate "recon_four_checks:PASS:0:transfer_reconciliation.json"
  python3 handoff_manifest.py verify --case-dir <案目录>
  python3 handoff_manifest.py receipt --case-dir <案目录> --step A1-collect --cmd "..." --exit 0 --artifacts a.json,b.csv
  python3 handoff_manifest.py freeze --case-dir <案目录> --members analysis-state.json --entity-file s2_entity_members.json
  python3 handoff_manifest.py freeze --case-dir <案目录> --check-unseal

freeze 四重机器前置（全部 fail-closed 无跳过通道）：
  0. 同进程严格 v2 verify（manifest 缺失/BLOCKED/漂移/legacy 一律拒）
  1. 裁决闭环 validator validate --entity-file（全候选成员级裁决＋linked_entity 名册绑定）
  2. 溯源台账内容级绑定（schema=v2＋实体集双向一致＋逐实体成员哈希＋closure 按
     composition 明细重算）
  3. 原始边/标签/分母/cutoff/block/manifest/data_map/算法哈希全绑定，以当前代码真实重放；
     从三策略完整明细重算消费与顺序敏感性，不信 stable 自报。全部绑定哈希入 revision，
     check-unseal 逐项复核当前文件。
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unicodedata
from datetime import datetime, timedelta, timezone

_LIB = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
sys.path.insert(0, _LIB)
from chain_registry import (evm_family, formal_ready_chains, get_chain_config,
                            release_tier_for, resolve_alias)
from case_paths import safe_case_dir, safe_case_file
from shared_release_receipt import (validate_accounting_receipt,
                                    accounting_expected_target,
                                    canonical_target,
                                    SOLANA_FROZEN_OBSERVATION_BUNDLE,
                                    validate_evm_observation_source_chain,
                                    validate_reconciliation_report,
                                    validate_solana_derived_bindings)
from wave_contract import WAVE_SCHEMA, has_formal_wave_semantics

SCHEMA_VERSION = "handoff/v3"
# verify 端支持集；consumer_min_schema 不在集内即拒收。
# v1（6.7.x 及以前）默认拒——fail-open 修复（2026-08-01 codex 复核）：漏跑新生产器的旧格式
# 不得静默过闸；已冻结旧案只能走 verify --legacy-read-only 显式降级（不得生成新正式报告）。
SUPPORTED_SCHEMAS = {"handoff/v3"}
LEGACY_SCHEMAS = {"handoff/v1", "handoff/v2"}
MANIFEST_NAME = "handoff_manifest.json"
RECEIPTS_NAME = "stage1_receipts.json"
FREEZE_NAME = "entity_freeze.json"
ADJUDICATIONS_NAME = "candidate_adjudications.json"
DISTRIBUTION_ADJUDICATIONS_NAME = "distribution_adjudications.json"
LEGACY_RECEIPT_NAME = "legacy_readonly_receipt.json"
PROVENANCE_SCHEMA = "provenance-ledger/v2"  # v1 是 pro-rata 数学错误版（2026-08-01 codex 复核），一律拒
# F-008: these names share one source of truth with the run_*/logs.parquet and
# run_*/blocks.parquet constructions in wave_scan.load_evm_v2 and
# entity_source_trace.source_binding.  Those two bound algorithm files are
# forbidden to change here; an AST guard test locks all three sites together.
EVM_V2_EDGE_NAMES = ("logs.parquet", "blocks.parquet")
EVM_V2_RUN_PREFIX = "run_"
STATUSES = {"READY", "BLOCKED", "PARTIAL", "SUPERSEDED", "BLOCKED_CEX_GATE"}
SPARSE_THRESHOLD = 64 * 1024 * 1024  # >64MB 用分片哈希（split-run §2.2：不收尾全盘重哈希）
CHUNK = 4 * 1024 * 1024

# 契约核心件（存在即登记；candidate_universe/anomalies/data_map 为 READY 必备，见 REQUIRED_FOR_READY）
CONTRACT_FILES = [
    "candidate_universe.json", "candidate_screening.json", "identity_preflight.json",
    "anomalies.json", "data_map.json", "unlock_evidence.json", RECEIPTS_NAME,
    "accounting_mode.json", "supply_truth.json", "wave_scan_report.json",
    "flow_anomaly_report.json", ADJUDICATIONS_NAME, "provenance_ledger.json",
    "time_spotcheck.json", "distribution_scan.json", DISTRIBUTION_ADJUDICATIONS_NAME,
    "reconciliation_report.json", "evm_observation_bundle.json",
    "evm_observation_transcript.json",
]
REQUIRED_FOR_READY = ["candidate_universe.json", "candidate_screening.json",
                      "identity_preflight.json", "anomalies.json", "data_map.json",
                      # A0/A2 必产的两个 gate 产物——READY 缺任一＝流程没跑完（dry-run 步 3.5 收紧）
                      "accounting_mode.json", "supply_truth.json",
                      # 波次扫描＋资金流异常扫描（W1 二次漏检复盘 v6.8.0）——两扫描器任一未跑
                      # 不得 READY；旧案目录复用须补跑后重新 generate，回退路径=旧单会话命令。
                      # candidate_adjudications.json 是 −2 判断层产物，不在 −1 READY 清单——
                      # 它的强制在 freeze 端（validator 全候选校验，缺漏即 exit 2）
                      "wave_scan_report.json", "flow_anomaly_report.json",
                      # A3 机械层第 9 项：initial 分布扫描。scan 不反绑 manifest；
                      # READY manifest 单向绑定 scan，避免 B-01 哈希循环。
                      "distribution_scan.json",
                      # INV-12：四查 wrapper 及其四份生产 receipt 是所有 READY 链的无条件必备件。
                      "reconciliation_report.json"]
# EVM 家族链另加时间抽查产物为 READY 必备（6.7.0，APU SQD 全史重拉冗余复盘）——
# time_spotcheck.py 固化后，锚点级第二源直查是 A2 第 4 查的机器凭证，缺件＝时间抽查没跑
# 或又走了自由发挥老路。Solana（anchor_sampler 通道）等非 EVM 链时间抽查形态不同，
# 不进本硬闸（白名单法：链名命中才强制，未知新链不误伤）。
READY_CHAINS = formal_ready_chains()
REQUIRED_FOR_READY_EVM = ["time_spotcheck.json", "evm_observation_bundle.json",
                          "evm_observation_transcript.json"]
# 自动 gate 适配：从产物 JSON 读 verdict/exit_code（防手报）；verify 时重读比对
AUTO_GATES = {"accounting_gate": "accounting_mode.json", "supply_truth_gate": "supply_truth.json",
              "time_spotcheck": "time_spotcheck.json",
              "reconciliation_checks": "reconciliation_report.json"}
LEGACY_AUTO_GATE_ALIASES = {"reconciliation_four_checks": "reconciliation_checks"}
# accounting_gate.py 的公开退出码契约允许 WARN + exit 0 放行；其余自动 gate 必须 PASS。
AUTO_GATE_ACCEPTED_VERDICTS = {"accounting_gate": {"PASS", "WARN"}}
PROVENANCE_LABEL_KINDS = {"cex", "dex_pool", "facility", "bridge", "launch_alloc",
                          "airdrop", "vesting"}
# data_map 明确登记的 .duckdb 可能是 provenance 的正式重放源，必须进 manifest 绑定；
# WAL/临时文件仍排除。大库由 sha256-sparse 做交接哈希，freeze 的 input_binding 另做完整哈希。
EXCLUDE_SUFFIXES = (".log", ".duckdb.wal", ".lock", ".tmp", ".bak")
EXCLUDE_NAMES = {"config.json", MANIFEST_NAME}  # manifest 不含自身；config 可能含运行时 key 路径


def utcnow():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _solana_required_exact_paths(wrapper, exact):
    """Exact receipt/inputs plus the frozen anti-forgery bundle in dynamic cases."""
    exact_item = (wrapper.get("checks") or {}).get("exact_reconcile") or {}
    required = {((exact_item.get("receipt") or {}).get("path"))}
    required.update(ref.get("path") for ref in (exact.get("inputs") or {}).values()
                    if isinstance(ref, dict))
    exact_target = canonical_target(exact.get("target"))
    wrapper_target = canonical_target(wrapper.get("target"))
    if exact_target["as_of_block"] < wrapper_target["as_of_block"]:
        required.add(SOLANA_FROZEN_OBSERVATION_BUNDLE)
    required.discard(None)
    return required


def sha256_file(path):
    """≤64MB 全量 sha256；更大用 头4MB+尾4MB+size 的分片哈希（algo 字段区分，不可混同）。"""
    size = os.path.getsize(path)
    h = hashlib.sha256()
    with open(path, "rb") as f:
        if size <= SPARSE_THRESHOLD:
            for blk in iter(lambda: f.read(CHUNK), b""):
                h.update(blk)
            return "sha256", h.hexdigest(), size
        h.update(f.read(CHUNK))
        f.seek(max(size - CHUNK, 0))
        h.update(f.read(CHUNK))
        h.update(str(size).encode())
        return "sha256-sparse", h.hexdigest(), size


def atomic_write_json(path, obj):
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def git_sha(repo_dir):
    try:
        p = subprocess.run(["git", "-C", os.path.expanduser(repo_dir), "rev-parse", "--short=12", "HEAD"],
                           capture_output=True, text=True, timeout=10)
        return p.stdout.strip() if p.returncode == 0 else None
    except Exception:
        return None


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def file_entry(case_dir, rel):
    algo, digest, size = sha256_file(os.path.join(case_dir, rel))
    return {"path": rel, "bytes": size, "hash_algo": algo, "sha256": digest}


def read_gate_artifact(case_dir, rel):
    """自动 gate 适配：产物 JSON 必须有 verdict + exit_code 字段（accounting_mode/supply_truth 均满足）。"""
    obj = load_json(os.path.join(case_dir, rel))
    return {"verdict": obj.get("verdict"), "exit_code": obj.get("exit_code")}


# ---------------- generate ----------------

def cmd_generate(a):
    case_dir = os.path.abspath(a.case_dir)
    if not os.path.isdir(case_dir):
        print(f"[generate] 案目录不存在: {case_dir}", file=sys.stderr)
        return 1
    if a.status not in STATUSES:
        print(f"[generate] status 必须是 {sorted(STATUSES)}", file=sys.stderr)
        return 1
    chains = [resolve_alias(c) for c in (a.chain or "").split(",") if c.strip()]
    if a.status == "READY":
        if not chains or not str(a.contract or "").strip():
            print("[generate] READY 必须显式给 --chain 与 --contract", file=sys.stderr)
            return 2
        if len(set(chains)) != 1:
            print("[generate] READY 当前只接受单链 scope；reconciliation target 必须唯一", file=sys.stderr)
            return 2
        chains = sorted(set(chains))
        unknown = sorted(set(chains) - READY_CHAINS)
        if unknown:
            print(f"[generate] READY 含非正式链 {unknown}；先补正式链能力再生成", file=sys.stderr)
            return 2

    artifacts, missing_required = [], []
    seen = set()
    data_map_paths = set()

    def add_path(rel):
        if rel in seen:
            return
        base = os.path.basename(rel)
        if base in EXCLUDE_NAMES or base.endswith(EXCLUDE_SUFFIXES):
            return
        artifacts.append(file_entry(case_dir, rel))
        seen.add(rel)

    def discover(rel):
        path = safe_case_file(case_dir, rel, must_exist=False)
        if path.exists():
            add_path(rel)

    def add_explicit(rel):
        path = safe_case_file(case_dir, rel)
        add_path(rel)

    for name in CONTRACT_FILES:
        discover(name)
    # data_map 里登记的数据文件并入 allowlist（避免 glob 大杂烩，索引即白名单）
    dm_path = os.path.join(case_dir, "data_map.json")
    if os.path.isfile(dm_path):
        try:
            dm = load_json(dm_path)
        except Exception as e:
            print(f"[generate] data_map.json 解析失败（将继续，但 READY 会被 verify 拒）: {e}", file=sys.stderr)
        else:
            try:
                for ent in dm.get("files", []):
                    if isinstance(ent, dict) and isinstance(ent.get("path"), str):
                        data_map_paths.add(ent["path"])
                    add_explicit(ent.get("path"))
            except ValueError as e:
                print(f"[generate] data_map.json 显式文件路径非法: {e}", file=sys.stderr)
                return 2
            except Exception as e:
                print(f"[generate] data_map.json 解析失败（将继续，但 READY 会被 verify 拒）: {e}", file=sys.stderr)
    for extra in a.include or []:
        try:
            add_explicit(extra)
        except ValueError as e:
            print(f"[generate] --include 路径非法: {e}", file=sys.stderr)
            return 2
    # sealed/ 只记哈希（密封纪律：manifest 记哈希不记内容，读取由 --check-unseal 把关）
    sealed_dir = os.path.join(case_dir, "sealed")
    sealed = []
    if os.path.islink(sealed_dir):
        print("[generate] sealed/ 目录不得是符号链接", file=sys.stderr)
        return 2
    if os.path.isdir(sealed_dir):
        for name in sorted(os.listdir(sealed_dir)):
            p = os.path.join(sealed_dir, name)
            if os.path.islink(p):
                print(f"[generate] sealed/ 条目不得是符号链接: {name}", file=sys.stderr)
                return 2
            if os.path.isfile(p):
                rel = f"sealed/{name}"
                try:
                    safe_path = safe_case_file(case_dir, rel)
                except ValueError as e:
                    print(f"[generate] sealed/ 条目路径非法: {e}", file=sys.stderr)
                    return 2
                algo, digest, size = sha256_file(safe_path)
                sealed.append({"path": rel, "bytes": size, "hash_algo": algo, "sha256": digest})

    if a.status == "READY":
        try:
            recon_target, recon_receipts = validate_reconciliation_report(
                case_dir, return_receipts=True)
            if resolve_alias(recon_target["chain"]) == "sol":
                wrapper = load_json(os.path.join(case_dir, "reconciliation_report.json"))
                required_exact = _solana_required_exact_paths(
                    wrapper, recon_receipts["exact_reconcile"])
                missing_map = sorted(required_exact - data_map_paths)
                missing_artifacts = sorted(required_exact - seen)
                if missing_map or missing_artifacts:
                    raise ValueError(
                        f"Solana exact receipt 及 inputs 必须同时进 data_map/artifacts；"
                        f"data_map缺={missing_map}, artifacts缺={missing_artifacts}")
                validate_solana_derived_bindings(
                    case_dir, recon_receipts["exact_reconcile"]["edge_source_binding"],
                    extra_paths=seen)
        except Exception as exc:
            print(f"[generate] reconciliation READY 深验失败: {exc}", file=sys.stderr)
            return 2
        required = list(REQUIRED_FOR_READY)
        if set(chains) & evm_family():
            required += REQUIRED_FOR_READY_EVM
        missing_required = [n for n in required if n not in seen]
        if missing_required:
            print(f"[generate] status=READY 但缺必备契约件: {missing_required}（改报 PARTIAL 或补齐；"
                  "time_spotcheck.json 由 scripts/lib/time_spotcheck.py 产出）", file=sys.stderr)
            return 2

    gates = {}
    for gname, rel in AUTO_GATES.items():
        if rel in seen:
            try:
                gates[gname] = {"artifact": rel, **read_gate_artifact(case_dir, rel), "source": "auto"}
            except Exception as e:
                print(f"[generate] 读 gate 产物 {rel} 失败: {e}", file=sys.stderr)
                return 1
    for spec in a.gate or []:
        parts = spec.split(":", 3)
        if len(parts) != 4:
            print(f"[generate] --gate 格式应为 name:verdict:exit:artifact，收到: {spec}", file=sys.stderr)
            return 1
        gname, verdict, exit_code, rel = parts
        if gname in AUTO_GATES:
            print(f"[generate] --gate {gname} 已有 AUTO_GATES 适配，禁止 declared 覆盖机器读数",
                  file=sys.stderr)
            return 2
        try:
            add_explicit(rel)
        except ValueError as e:
            print(f"[generate] --gate {gname} 绑定路径非法: {e}", file=sys.stderr)
            return 2
        if rel not in seen:
            print(f"[generate] --gate {gname} 绑定的产物不存在: {rel}", file=sys.stderr)
            return 2
        gates[gname] = {"artifact": rel, "verdict": verdict, "exit_code": int(exit_code), "source": "declared"}

    manifest_path = os.path.join(case_dir, MANIFEST_NAME)
    supersedes = None
    if os.path.isfile(manifest_path):
        try:
            old = load_json(manifest_path)
            old_run = old.get("run_id", "unknown")
            archived = os.path.join(case_dir, f"handoff_manifest.{old_run}.superseded.json")
            old["status"] = "SUPERSEDED"
            atomic_write_json(archived, old)
            supersedes = old_run
        except Exception as e:
            print(f"[generate] 旧 manifest 归档失败: {e}", file=sys.stderr)
            return 1

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "consumer_min_schema": SCHEMA_VERSION,
        "case_id": a.case_id or os.path.basename(case_dir),
        "run_id": a.run_id or datetime.now(timezone.utc).strftime("s1-%Y%m%d-%H%M%S"),
        "stage": "stage1_mechanical",
        "mode": a.mode,
        "status": a.status,
        "status_reason": a.status_reason,
        "producer_model": a.producer_model,
        "generated_at": utcnow(),
        "skill_git_sha": {"cc": git_sha("~/.claude/skills/token-chip-analysis"),
                          "codex": git_sha("~/.codex/skills/token-chip-analysis")},
        "scope": {"chains": chains or None,
                  "contract": str(a.contract).strip() if a.contract is not None else None,
                  "cutoff_utc": a.cutoff,
                  "frozen_block": a.frozen_block,
                  "denominators": json.loads(a.denominators) if a.denominators else None},
        "gates": gates,
        "artifacts": artifacts,
        "sealed": sealed,
        "supersedes_run_id": supersedes,
        "late_additions": [],
    }
    atomic_write_json(manifest_path, manifest)
    print(f"[generate] {a.status}  {len(artifacts)} 件产物  {len(gates)} 个 gate  {len(sealed)} 件密封 → {manifest_path}"
          + (f"（取代 run {supersedes}）" if supersedes else ""))
    return 0


# ---------------- verify ----------------

def _verify_light_schema(case_dir, fails, manifest, legacy=False):
    """轻量 schema 检查：防 −1 交空壳（split-run §3.1 步 2 的语义验证部分）。
    legacy=True（--legacy-read-only）时跳过两扫描器新版检查——旧案产物是旧格式，只验哈希与公共件。"""
    try:
        cu = load_json(os.path.join(case_dir, "candidate_universe.json"))
        cands = cu.get("candidates")
        if not isinstance(cands, list) or not cands:
            fails.append("candidate_universe.json 无 candidates 数组或为空")
        elif not all(("id" in c and "address" in c and "reasons" in c) for c in cands[:50]):
            fails.append("candidate_universe.json 条目缺 id/address/reasons 字段")
    except Exception as e:
        fails.append(f"candidate_universe.json 读取失败: {e}")
    try:
        an = load_json(os.path.join(case_dir, "anomalies.json"))
        items = an if isinstance(an, list) else an.get("anomalies", [])
        for it in items:
            if not all(k in it for k in ("id", "severity", "blocking", "stage", "status")):
                fails.append(f"anomalies 条目缺字段: {json.dumps(it, ensure_ascii=False)[:80]}")
                break
        blocking_open = [it["id"] for it in items
                         if it.get("blocking") and str(it.get("status")).lower() not in ("resolved", "waived")]
        if blocking_open:
            fails.append(f"blocking 异常未解决却报 READY: {blocking_open}")
    except Exception as e:
        fails.append(f"anomalies.json 读取失败: {e}")
    art_paths = {item.get("path") for item in manifest.get("artifacts") or []
                 if isinstance(item, dict)}
    # Legacy only waives absent Batch-2 artifacts.  If the wrapper is listed, it
    # is evidence and must pass the same current deep validator and scope bind.
    wrapper_present = ("reconciliation_report.json" in art_paths
                       or os.path.isfile(os.path.join(case_dir, "reconciliation_report.json")))
    if not legacy or wrapper_present:
        try:
            target, recon_receipts = validate_reconciliation_report(
                case_dir, return_receipts=True)
            scope = manifest.get("scope") or {}
            chains = {resolve_alias(chain) for chain in scope.get("chains") or []}
            if len(chains) != 1 or resolve_alias(target.get("chain")) not in chains:
                fails.append("reconciliation target.chain 未与唯一 READY scope 链绑定")
            scope_target = {"chain": next(iter(chains), None),
                            "token": scope.get("contract"),
                            "as_of_block": target.get("as_of_block")}
            if canonical_target(target) != canonical_target(scope_target):
                fails.append("reconciliation target.token 未与 READY scope.contract 绑定")
            if resolve_alias(target.get("chain")) == "sol":
                exact = recon_receipts["exact_reconcile"]
                wrapper = load_json(os.path.join(case_dir, "reconciliation_report.json"))
                required_exact = _solana_required_exact_paths(wrapper, exact)
                data_map = load_json(os.path.join(case_dir, "data_map.json"))
                mapped = {row.get("path") for row in data_map.get("files", [])
                          if isinstance(row, dict)}
                missing_map = sorted(required_exact - mapped)
                missing_artifacts = sorted(required_exact - art_paths)
                if missing_map or missing_artifacts:
                    fails.append(
                        "Solana exact receipt 及 inputs 未同时绑定 data_map/artifacts: "
                        f"data_map缺={missing_map}, artifacts缺={missing_artifacts}")
                validate_solana_derived_bindings(
                    case_dir, exact["edge_source_binding"], extra_paths=art_paths)
            if not legacy:
                expected_accounting = accounting_expected_target(
                    target, recon_receipts)
                _, accounting, _ = validate_accounting_receipt(
                    case_dir, expected_target=expected_accounting)
                validate_evm_observation_source_chain(
                    case_dir, accounting, recon_receipts["supply_truth"])
        except Exception as exc:
            fails.append(f"reconciliation/accounting 公共深验失败: {exc}")
    if legacy:
        return
    try:
        ws = load_json(os.path.join(case_dir, "wave_scan_report.json"))
        if ws.get("schema") in ("wave-scan/v1", "wave-scan/v2", "wave-scan/v3",
                                "wave-scan/v4"):
            fails.append(f"wave_scan_report.json 是旧版（{ws.get('schema')}）——v2 及更早缺 scan_universe "
                         "逐址全集，v3 又缺边顺序/legacy 标记，v4 缺边源绑定；"
                         "重跑 wave_scan.py（v5）后重 generate；"
                         "已冻结旧案走 verify --legacy-read-only")
        elif ws.get("schema") != WAVE_SCHEMA:
            fails.append(f"wave_scan_report.json schema 异常: {ws.get('schema')}")
        elif not has_formal_wave_semantics(ws):
            fails.append("wave_scan_report.json v5 必须是 formal 且携带合法边顺序/边源语义；"
                         "legacy-sol5 诊断产物不得进入 READY")
        elif not isinstance(ws.get("waves"), list) or not isinstance(ws.get("equal_amount_groups"), list) \
                or not isinstance(ws.get("requires_adjudication"), bool):
            fails.append("wave_scan_report.json 缺 waves/equal_amount_groups/requires_adjudication——空壳拒收")
        elif not isinstance(ws.get("scan_universe"), list) \
                or not isinstance(ws.get("must_adjudicate_count"), int) \
                or len(ws["scan_universe"]) != ws.get("scan_universe_count"):
            fails.append("wave_scan_report.json v5 全集不完整（scan_universe 须为数组、"
                         "must_adjudicate_count 须为整数、len(scan_universe)==scan_universe_count）"
                         "——贴 v4 标签不带逐址全集同属空壳，拒收")
        elif any(not isinstance(u, dict) or not str(u.get("addr") or "").strip()
                 or not isinstance(u.get("must_adjudicate"), bool)
                 for u in ws["scan_universe"]) \
                or sum(1 for u in ws["scan_universe"] if u.get("must_adjudicate")) \
                != ws["must_adjudicate_count"]:
            fails.append("wave_scan_report.json v5 全集内部矛盾（每条须有 addr 且 "
                         "must_adjudicate 为布尔；must_adjudicate_count 必须等于逐条 true 计数"
                         "——count=0 配 must=true 条目这类自相矛盾拒收，v6.9.4）")
    except Exception as e:
        fails.append(f"wave_scan_report.json 读取失败（波次扫描未跑？补跑 wave_scan.py 后重 generate）: {e}")
    try:
        fa = load_json(os.path.join(case_dir, "flow_anomaly_report.json"))
        if fa.get("schema") != "flow-anomaly/v3":
            fails.append(f"flow_anomaly_report.json schema 异常: {fa.get('schema')}"
                         "（需要 flow-anomaly/v3——旧 v1/v2 产物重跑 flow_anomaly_scan.py）")
        elif not isinstance(fa.get("sinks"), list) or not isinstance(fa.get("sprays"), list) \
                or not isinstance(fa.get("requires_adjudication"), bool):
            fails.append("flow_anomaly_report.json 缺 sinks/sprays/requires_adjudication——空壳拒收")
    except Exception as e:
        fails.append(f"flow_anomaly_report.json 读取失败（资金流异常扫描未跑？补跑 flow_anomaly_scan.py 后重 generate）: {e}")
    scan_script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "holder_distribution_scan.py")
    pv = subprocess.run([sys.executable, scan_script, "validate", "--case-dir", case_dir,
                         "--scan", "distribution_scan.json", "--expected-stage", "initial"],
                        capture_output=True, text=True)
    if pv.returncode != 0:
        fails.append("distribution_scan.json 独立重算未通过（initial 产物缺失、被手改或上游漂移）: "
                     + (pv.stdout + pv.stderr)[-800:])


def verify_case(case_dir, legacy_read_only=False):
    """verify 核心（cmd_verify 与 cmd_freeze 共用——freeze 内联同进程 verify，
    v6.8.1 codex 复核修复：manifest 缺失/BLOCKED/哈希漂移时不得冻结）。
    返回 (fails, manifest|None, legacy_mode)。"""
    manifest_path = os.path.join(case_dir, MANIFEST_NAME)
    if not os.path.isfile(manifest_path):
        return ([f"缺 {MANIFEST_NAME}——−1 未收工或目录不对"], None, False)
    try:
        m = load_json(manifest_path)
    except Exception as e:
        return ([f"manifest 解析失败: {e}"], None, False)

    fails = []
    legacy_mode = False
    schema = m.get("consumer_min_schema")
    if schema not in SUPPORTED_SCHEMAS:
        if schema in LEGACY_SCHEMAS and legacy_read_only:
            legacy_mode = True
        elif schema in LEGACY_SCHEMAS:
            fails.append(f"schema {schema} 是旧版——新运行必须重跑 v6.8.0 生产器"
                         "（wave-scan/v5、flow-anomaly/v3）后重 generate；只读旧案加 --legacy-read-only")
        else:
            fails.append(f"schema 不兼容: 需要 {schema}，本端支持 {sorted(SUPPORTED_SCHEMAS)}")
    status = m.get("status")
    if status != "READY":
        fails.append(f"状态 {status} ≠ READY，拒绝消费（原因: {m.get('status_reason')}）")
    if status == "READY":
        scope = m.get("scope") or {}
        raw_chains = scope.get("chains")
        if not isinstance(raw_chains, list) or len(raw_chains) != 1 \
                or not isinstance(raw_chains[0], str) or not raw_chains[0].strip():
            chains = set()
            fails.append("READY scope.chains 为空——缺正式链范围")
            if isinstance(raw_chains, list) and raw_chains:
                fails[-1] = "READY scope.chains 必须恰有一个非空字符串链名"
        else:
            chains = {resolve_alias(raw_chains[0])}
        if len(chains) == 1 and legacy_mode:
            chain = next(iter(chains))
            if get_chain_config(chain) is None:
                fails.append(f"legacy READY scope 链未登记: {chain}")
            elif release_tier_for(chain) == "exploration":
                fails.append(f"legacy READY scope 链为 exploration，拒绝正式回流: {chain}")
            elif release_tier_for(chain) != "formal":
                fails.append(f"legacy READY scope 链非 formal tier: {chain}")
        elif len(chains) == 1:
            unknown = sorted(chains - READY_CHAINS)
            if unknown:
                fails.append(f"READY scope 含非正式链 {unknown}")
        if not str(scope.get("contract") or "").strip():
            fails.append("READY scope.contract 为空")

    if not fails:  # schema/状态硬伤先报，避免在坏 manifest 上白跑哈希
        artifacts = m.get("artifacts", [])
        safe_artifacts = []
        art_paths = set()
        if not isinstance(artifacts, list):
            fails.append("manifest artifacts 不是数组")
            artifacts = []
        for index, ent in enumerate(artifacts):
            if not isinstance(ent, dict):
                fails.append(f"manifest artifacts[{index}] 不是对象")
                continue
            rel = ent.get("path")
            try:
                path = safe_case_file(case_dir, rel)
            except ValueError as e:
                fails.append(f"artifact 路径非法: {e}")
                continue
            safe_artifacts.append((ent, path))
            art_paths.add(rel)
        # READY 必备件独立重算（v6.8.1：不信 generate 曾正确执行——手改 manifest 的
        # artifacts/gates 列表同样过不了这道重查）
        if not legacy_mode:
            required = list(REQUIRED_FOR_READY)
            chains = {resolve_alias(c) for c in (m.get("scope", {}) or {}).get("chains") or []}
            if chains & evm_family():
                required += REQUIRED_FOR_READY_EVM
            miss = [n for n in required if n not in art_paths]
            if miss:
                fails.append(f"READY 必备件不在 artifact 清单: {miss}（manifest 被手改或 generate 版本过旧）")
            gates_m = m.get("gates") or {}
            normalized_gate_names = {
                LEGACY_AUTO_GATE_ALIASES.get(name, name) for name in gates_m}
            for gname, rel in AUTO_GATES.items():
                if rel in art_paths and gname not in normalized_gate_names:
                    fails.append(f"gate {gname} 缺失（产物 {rel} 在场却无对应 gate 记录）")
        elif "reconciliation_report.json" in art_paths \
                and not ({"reconciliation_four_checks", "reconciliation_checks"}
                         & set(m.get("gates") or {})):
            fails.append("legacy 案在场 reconciliation_report.json 缺对应 gate 记录")
        for ent, p in safe_artifacts:
            algo, digest, size = sha256_file(p)
            if size != ent["bytes"] or digest != ent["sha256"] or algo != ent.get("hash_algo"):
                fails.append(f"哈希/大小漂移: {ent['path']}")
        for gname, g in (m.get("gates") or {}).items():
            if not isinstance(g, dict):
                fails.append(f"gate {gname} 记录不是对象")
                continue
            try:
                safe_case_file(case_dir, g.get("artifact"))
            except ValueError as e:
                fails.append(f"gate {gname} artifact 路径非法: {e}")
                continue
            if g.get("source") == "auto":
                try:
                    now = read_gate_artifact(case_dir, g["artifact"])
                    if now["verdict"] != g.get("verdict") or now["exit_code"] != g.get("exit_code"):
                        fails.append(f"gate {gname} 语义漂移: manifest 记 {g.get('verdict')}/{g.get('exit_code')}，"
                                     f"产物现为 {now['verdict']}/{now['exit_code']}")
                    elif str(now["verdict"] or "").upper() not in \
                            AUTO_GATE_ACCEPTED_VERDICTS.get(gname, {"PASS"}) \
                            or now["exit_code"] != 0:
                        accepted = sorted(AUTO_GATE_ACCEPTED_VERDICTS.get(gname, {"PASS"}))
                        fails.append(f"gate {gname} 不满足 READY 语义（允许 verdict={accepted}, exit_code=0）: {now}")
                except Exception as e:
                    fails.append(f"gate {gname} 产物重读失败: {e}")
            else:
                if str(g.get("verdict", "")).upper() not in ("PASS", "OK"):
                    fails.append(f"gate {gname}（declared）非 PASS 却报 READY: {g.get('verdict')}")
                if g.get("exit_code") != 0:
                    fails.append(f"gate {gname}（declared）exit_code={g.get('exit_code')} ≠ 0 却报 READY")
        _verify_light_schema(case_dir, fails, m, legacy=legacy_mode)
    return (fails, m, legacy_mode)


def cmd_verify(a):
    case_dir = os.path.abspath(a.case_dir)
    fails, m, legacy_mode = verify_case(case_dir, legacy_read_only=bool(a.legacy_read_only))
    if fails:
        print("[verify] FAIL（fail-closed，逐条修复或退回 −1）:")
        for x in fails:
            print(f"  ✗ {x}")
        return 2
    if legacy_mode:
        # 机器只读收据（v6.8.1 codex 复核修复：降级不能只是一句口头警告——落盘 receipt，
        # freeze 靠严格 v2 verify 拒 legacy，正式报告入口按本 receipt 统一拒绝）
        _, mdigest, _ = sha256_file(os.path.join(case_dir, MANIFEST_NAME))
        atomic_write_json(os.path.join(case_dir, LEGACY_RECEIPT_NAME), {
            "schema": "legacy-readonly-receipt/v1",
            "verified_at": utcnow(),
            "manifest_schema": m.get("consumer_min_schema"),
            "manifest_sha256": mdigest,
            "note": "旧契约只读降级：仅供读取既有冻结结论；不得据此生成新正式报告、"
                    "不得重新判级、不得冻结实体（freeze 端严格 v2 verify 必拒）",
        })
        print(f"[verify] ⚠ LEGACY READ-ONLY：{m.get('consumer_min_schema')} 旧格式仅供读取既有冻结结论，"
              f"不得据此生成新正式报告、不得重新判级——机器收据已落 {LEGACY_RECEIPT_NAME}")
        return 0
    print(f"[verify] PASS  {len(m.get('artifacts', []))} 件产物哈希一致，{len(m.get('gates') or {})} 个 gate 重查通过，"
          f"状态 READY（run {m.get('run_id')}，producer={m.get('producer_model')}）")
    return 0


# ---------------- receipt ----------------

def cmd_receipt(a):
    case_dir = os.path.abspath(a.case_dir)
    path = os.path.join(case_dir, RECEIPTS_NAME)
    rows = []
    if os.path.isfile(path):
        try:
            rows = load_json(path)
        except Exception as e:
            print(f"[receipt] 现有收据文件损坏（不覆盖，请人工处理）: {e}", file=sys.stderr)
            return 1
    rows.append({
        "seq": len(rows) + 1, "step": a.step, "cmd": a.cmd, "exit_code": a.exit,
        "artifacts": [x for x in (a.artifacts or "").split(",") if x],
        "ts_utc": utcnow(), "blind_mode": os.environ.get("CHIP_BLIND_SERIAL") == "1",
        "note": a.note,
    })
    atomic_write_json(path, rows)
    print(f"[receipt] #{len(rows)} {a.step} exit={a.exit} blind={rows[-1]['blind_mode']}")
    return 0


# ---------------- freeze ----------------

def full_sha256_file(path):
    """provenance 输入绑定使用完整 SHA-256；不能拿 manifest 的大文件抽样哈希代替。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(CHUNK), b""):
            h.update(blk)
    return h.hexdigest(), os.path.getsize(path)


def resolve_bound_path(case_dir, shown):
    safe_case_file(case_dir, shown)
    return os.path.join(case_dir, shown)


def validate_evm_v2_argument(case_dir, shown):
    """Validate a directory argument before it can reach glob or SQL assembly."""
    if isinstance(shown, str):
        forbidden = "*?[]'\\"
        if any(char in shown for char in forbidden) \
                or any(unicodedata.category(char) == "Cc" for char in shown):
            raise ValueError(f"evm_v2 目录参数含 glob/SQL/控制字符: {shown!r}")
    return safe_case_dir(case_dir, shown)


def enumerate_evm_v2_sources(case_dir, argument, edge_dir):
    """Enumerate the loader's fixed two-pattern input set without following links."""
    found = set()
    root_real = os.path.realpath(case_dir)
    try:
        with os.scandir(edge_dir) as children:
            run_entries = sorted(children, key=lambda entry: entry.name)
        for entry in run_entries:
            if not entry.name.startswith(EVM_V2_RUN_PREFIX):
                continue
            if entry.is_symlink():
                raise ValueError(f"evm_v2 run 目录不得是符号链接: {entry.name!r}")
            if not entry.is_dir(follow_symlinks=False):
                continue
            with os.scandir(entry.path) as run_children:
                edge_entries = sorted(run_children, key=lambda child: child.name)
            for child in edge_entries:
                if child.name not in EVM_V2_EDGE_NAMES:
                    continue
                rel = f"{argument}/{entry.name}/{child.name}"
                path = safe_case_file(case_dir, rel)
                found.add(os.path.relpath(path, root_real).replace(os.sep, "/"))
    except ValueError:
        raise
    except (OSError, TypeError) as exc:
        raise ValueError(f"evm_v2 目录枚举失败: {argument!r}: {exc}") from exc
    return found


def check_bound_file(case_dir, rec, expected_path=None):
    if not isinstance(rec, dict):
        return None, "文件绑定不是对象"
    try:
        p = resolve_bound_path(case_dir, rec.get("path"))
        if expected_path and os.path.realpath(p) != os.path.realpath(expected_path):
            return p, f"绑定路径 {p} ≠ 当前要求路径 {expected_path}"
        if not os.path.isfile(p):
            return p, f"绑定文件不存在: {p}"
        digest, size = full_sha256_file(p)
        if digest != rec.get("sha256") or size != rec.get("bytes"):
            return p, f"绑定文件哈希/大小漂移: {rec.get('path')}"
        return p, None
    except (OSError, ValueError, TypeError) as e:
        return None, f"文件绑定校验失败: {e}"


def check_algorithm_file(rec, expected_path):
    """Validate a repository code dependency against one fixed trusted path.

    Algorithm files are intentionally outside the case root, so they cannot use
    the case-artifact resolver.  No arbitrary absolute path is accepted: the
    record must name the exact dependency selected by this verifier.
    """
    if not isinstance(rec, dict):
        return None, "算法文件绑定不是对象"
    shown = rec.get("path")
    if not isinstance(shown, str) or not shown or not os.path.isabs(shown):
        return None, "算法文件 path 必须是验证器指定实物的绝对路径"
    expected = os.path.realpath(expected_path)
    if os.path.realpath(shown) != expected:
        return None, f"算法文件绑定路径 {shown} ≠ 当前验证器依赖 {expected_path}"
    if os.path.islink(shown) or not os.path.isfile(expected):
        return None, f"算法文件不存在、非普通文件或为符号链接: {shown}"
    try:
        digest, size = full_sha256_file(expected)
    except OSError as e:
        return None, f"算法文件读取失败: {e}"
    if digest != rec.get("sha256") or size != rec.get("bytes"):
        return None, f"算法文件哈希/大小漂移: {shown}"
    return expected, None


def provenance_semantic_payload(report):
    return {k: report.get(k) for k in ("schema", "total_supply_raw", "input_binding",
                                        "entities", "unresolved_total_pct", "bounds_sensitivity")}


# ---------------- flip 裁决收据（flip-adjudications/v1，F-06）----------------
# 共享实现：entity_source_trace（producer 消费收据）、本文件 freeze 前置 3（重验）、
# a5_report_seal（披露实文核对）三处同源，不手抄三份。

FLIP_ADJUDICATIONS_SCHEMA = "flip-adjudications/v1"
FLIP_POLICIES = ("pro_rata", "fifo", "lifo")
# N-D1（批 D 收口补丁）：披露段的策略名判据＝中英文别名族——纯中文真实披露写法
# （"按比例/先进先出/后进先出"）是合格的并列披露，不得逼作者在中文报告里塞英文
# 标识符。每策略一组等价词，切片内命中任一即算该策略在场（契约见 scan-schemas §4a）。
FLIP_POLICY_ALIASES = {
    "pro_rata": ("pro_rata", "按比例"),
    "fifo": ("fifo", "先进先出"),
    "lifo": ("lifo", "后进先出"),
}


def canonical_json_sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def flip_fingerprint(policy_details):
    """翻转指纹＝该锚点三策略 policy_details 的规范化子集 sha。

    底层数据（边表/名册/参数）一变，三策略明细必变，指纹随之失配——旧收据自动失效，
    必须重新人工裁决。这是收据的必选绑定件，不接受"只按 entity:anchor 键豁免"。"""
    subset = {policy: policy_details.get(policy) for policy in FLIP_POLICIES}
    return canonical_json_sha({"policy_details": subset})


def format_share_pct(raw, stock):
    """披露用份额字符串（两位小数），trace 生成与 A5 核对同一函数——无浮点边界分叉。"""
    return f"{int(raw) * 100.0 / int(stock):.2f}"


def ledger_real_flips(pl):
    """从 ledger 的三策略完整明细独立重算真实翻转锚点（不读 agree/stable 自报值）。

    返回 {(entity_id, anchor): {"fingerprint", "tops": {policy: terminal list},
    "shares": {policy: "12.34"}, "stock": int}}；尘埃锚点（<总供应 0.01%）不入。"""
    out = {}
    try:
        total_supply = int(pl.get("total_supply_raw") or 0)
    except (TypeError, ValueError):
        total_supply = 0
    per = ((pl.get("bounds_sensitivity") or {}).get("per_entity")) or {}
    for ent in pl.get("entities") or []:
        eid = ent.get("entity_id")
        anchors_detail = ((per.get(eid) or {}).get("anchors")) or {}
        for anchor_name in ("current", "peak"):
            stock = int(((ent.get("anchors") or {}).get(anchor_name) or {}).get("stock_raw", 0))
            if stock <= 0:
                continue
            if total_supply > 0 and stock * 10000 < total_supply:
                continue  # 尘埃锚点
            pd = (anchors_detail.get(anchor_name) or {}).get("policy_details")
            if not isinstance(pd, dict):
                continue  # 明细缺失由 recompute 的既有检查报错，这里不重复
            tops, shares = {}, {}
            for policy in FLIP_POLICIES:
                rows = pd.get(policy) or []
                ranked = []
                for row in rows:
                    try:
                        ranked.append((tuple(row["terminal"]), int(row["raw"])))
                    except (KeyError, TypeError, ValueError):
                        continue
                if not ranked:
                    tops[policy] = None
                    continue
                # 独立重排取第一大（与 trace.top_entry 同键），不信 producer 行序自报
                terminal, raw = sorted(ranked, key=lambda kv: (-kv[1], str(kv[0])))[0]
                tops[policy] = list(terminal)
                shares[policy] = format_share_pct(raw, stock)
            if len({json.dumps(t, ensure_ascii=False) for t in tops.values()}) != 1:
                out[(eid, anchor_name)] = {
                    "fingerprint": flip_fingerprint(pd),
                    "tops": tops, "shares": shares, "stock": stock}
    return out


def load_flip_adjudications(path, *, current_entity_file=None):
    """加载并验证 flip-adjudications/v1 裁决收据（强度对齐 distribution/tolerance waiver 先例）。

    验：schema／裁决主体 approved_by／user_decided_at_utc（UTC Z）／entity_file 三验＋与
    本次运行名册 sha 相等（给了 current_entity_file 时）／evidence_refs 非空逐项三验
    （收据同目录内、拒绝绝对路径・越界・符号链接）／每行 entity_id・anchor・reason≥10・
    flip_fingerprint（64 hex）・disclosure（三策略 terminal＋share_pct＋report_locations）。
    返回 (收据对象, {(entity_id, anchor): 行})。任何不合法抛 ValueError。"""
    shown = os.path.expanduser(str(path))
    receipt_path = os.path.realpath(shown)
    if os.path.islink(shown) or not os.path.isfile(receipt_path):
        raise ValueError("flip 裁决收据必须是普通文件且不得为符号链接")
    with open(receipt_path, encoding="utf-8") as fh:
        doc = json.load(fh)
    if not isinstance(doc, dict) or doc.get("schema") != FLIP_ADJUDICATIONS_SCHEMA:
        raise ValueError(f"flip 裁决收据 schema 必须是 {FLIP_ADJUDICATIONS_SCHEMA}")
    # F-D4：人工裁决面的形式 sanity 闸。机器验不了"裁决实质真伪"（谁批的、批得对不对
    # ——与 tolerance-waiver 同款设计边界，见工单残余边界声明），但单字符占位主体、
    # 荒谬时间、垃圾字节证据这类"形式上就不是裁决"的收据必须当场拒。
    approved_by = doc.get("approved_by")
    if not isinstance(approved_by, str) or len(approved_by.strip()) < 2:
        raise ValueError("flip 裁决收据 approved_by 缺失或为单字符占位（裁决主体须可辨识）")
    decided = doc.get("user_decided_at_utc")
    try:
        if not isinstance(decided, str) or not decided.endswith("Z"):
            raise ValueError
        decided_dt = datetime.fromisoformat(decided[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("flip 裁决收据 user_decided_at_utc 必须是有效 UTC 时间") from exc
    earliest = datetime(2026, 1, 1, tzinfo=timezone.utc)  # 本收据制诞生于 2026-08
    if not earliest <= decided_dt <= datetime.now(timezone.utc) + timedelta(days=1):
        raise ValueError("flip 裁决收据 user_decided_at_utc 超出合理时间范围"
                         "（1970/未来时间戳不是真实裁决时间）")

    receipt_dir = os.path.dirname(receipt_path)

    def bound_ref(ref, label):
        if not isinstance(ref, dict) or not {"path", "size", "sha256"} <= set(ref):
            raise ValueError(f"flip 裁决收据 {label} 必须绑定 path/size/sha256")
        raw = str(ref.get("path") or "")
        parts = raw.split("/")
        if os.path.isabs(raw) or not raw or ".." in parts:
            raise ValueError(f"flip 裁决收据 {label} path 必须是收据同目录内的安全相对路径")
        lexical = receipt_dir
        for part in parts:
            lexical = os.path.join(lexical, part)
            if os.path.islink(lexical):
                raise ValueError(f"flip 裁决收据 {label} 不得引用符号链接")
        target = os.path.realpath(lexical)
        if not os.path.isfile(target) \
                or os.path.commonpath([target, os.path.realpath(receipt_dir)]) \
                != os.path.realpath(receipt_dir):
            raise ValueError(f"flip 裁决收据 {label} 文件不存在或越界")
        digest, size = full_sha256_file(target)
        if ref.get("size") != size or ref.get("sha256") != digest:
            raise ValueError(f"flip 裁决收据 {label} sha256/size 不匹配")
        return target

    entity_ref = doc.get("entity_file")
    entity_path = bound_ref(entity_ref, "entity_file")
    if current_entity_file is not None:
        current_digest, _ = full_sha256_file(str(current_entity_file))
        if entity_ref.get("sha256") != current_digest:
            raise ValueError("flip 裁决收据 entity_file 与本次运行名册内容不一致"
                             "——名册改动后旧裁决失效，须重新裁决")
    refs = doc.get("evidence_refs")
    if not isinstance(refs, list) or not refs:
        raise ValueError("flip 裁决收据 evidence_refs 必须是非空数组")
    for index, ref in enumerate(refs):
        evidence_path = bound_ref(ref, f"evidence_refs[{index}]")
        if evidence_path == entity_path:
            raise ValueError(f"flip 裁决收据 evidence_refs[{index}] 不得就是名册自身"
                             "——人工核对证据必须独立")
        # F-D4：最低实物强度——1 字节垃圾文件不构成"人工核对证据"。16 字节是形式下限，
        # 证据内容真伪仍属机器验不了的残余边界（工单如实声明）。
        if os.path.getsize(evidence_path) < 16:
            raise ValueError(f"flip 裁决收据 evidence_refs[{index}] 实物过小（<16 字节），"
                             "不构成可核对的证据文件")
    rows = doc.get("adjudications")
    if not isinstance(rows, list) or not rows:
        raise ValueError("flip 裁决收据 adjudications 必须是非空数组")
    by_key = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"flip 裁决收据 adjudications[{index}] 不是对象")
        eid = row.get("entity_id")
        anchor = row.get("anchor")
        if not isinstance(eid, str) or not eid or anchor not in ("peak", "current"):
            raise ValueError(f"flip 裁决收据 adjudications[{index}] entity_id/anchor 非法")
        if len(str(row.get("reason", "")).strip()) < 10:
            raise ValueError(f"flip 裁决收据 adjudications[{index}] reason 须 ≥10 字符")
        fp = row.get("flip_fingerprint")
        if not isinstance(fp, str) or len(fp) != 64 \
                or any(c not in "0123456789abcdef" for c in fp.lower()):
            raise ValueError(f"flip 裁决收据 adjudications[{index}] flip_fingerprint 非法")
        disclosure = row.get("disclosure")
        tbp = (disclosure or {}).get("top_by_policy") if isinstance(disclosure, dict) else None
        if not isinstance(tbp, dict) or set(tbp) != set(FLIP_POLICIES):
            raise ValueError(f"flip 裁决收据 adjudications[{index}] disclosure 缺三策略 "
                             "top_by_policy")
        for policy in FLIP_POLICIES:
            cell = tbp.get(policy)
            if not isinstance(cell, dict) or not isinstance(cell.get("terminal"), list) \
                    or not isinstance(cell.get("share_pct"), str) or not cell["share_pct"]:
                raise ValueError(f"flip 裁决收据 adjudications[{index}] {policy} 披露单元 "
                                 "缺 terminal/share_pct")
        locations = (disclosure or {}).get("report_locations")
        if not isinstance(locations, list) or not locations \
                or not all(isinstance(x, str) and x.strip() for x in locations):
            raise ValueError(f"flip 裁决收据 adjudications[{index}] 缺报告可核位置 "
                             "report_locations")
        key = (eid, anchor)
        if key in by_key:
            raise ValueError(f"flip 裁决收据 adjudications 重复锚点行: {key}")
        by_key[key] = row
    return doc, by_key


def verify_flip_receipt_against_ledger(receipt_rows, real_flips):
    """收据行 × ledger 真实翻转逐锚点对账。返回失败列表（空＝覆盖成立）。

    要求：①每个真实翻转锚点有收据行；②行指纹＝当前明细重算指纹（数据一变自动失效）；
    ③行披露的三策略 top terminal 与份额＝当前明细重算值（防收据写假数）；
    ④收据不得含指向非真实翻转锚点的行（不许预防性豁免）。"""
    fails = []
    for key, info in sorted(real_flips.items()):
        row = receipt_rows.get(key)
        if row is None:
            fails.append(f"{key[0]} {key[1]} 三策略主导终点翻转未获裁决收据覆盖"
                         "——真实多来源结构须 flip-adjudications/v1 书面裁决后重跑")
            continue
        if row.get("flip_fingerprint") != info["fingerprint"]:
            fails.append(f"{key[0]} {key[1]} 裁决收据指纹与当前三策略明细不符"
                         "——底层数据已变化，旧裁决失效，须重新裁决")
            continue
        tbp = (row.get("disclosure") or {}).get("top_by_policy") or {}
        for policy in FLIP_POLICIES:
            cell = tbp.get(policy) or {}
            want_terminal = info["tops"].get(policy)
            want_share = info["shares"].get(policy)
            if list(cell.get("terminal") or []) != (want_terminal or []) \
                    or cell.get("share_pct") != want_share:
                fails.append(f"{key[0]} {key[1]} 裁决收据 {policy} 披露值与明细重算不符"
                             f"（应为 terminal={want_terminal} share={want_share}）")
    extra = set(receipt_rows) - set(real_flips)
    if extra:
        fails.append(f"flip 裁决收据含指向非真实翻转锚点的行（不许预防性豁免）: {sorted(extra)}")
    return fails


def provenance_semantic_sha(report):
    return hashlib.sha256(json.dumps(provenance_semantic_payload(report), sort_keys=True,
                                     ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def recompute_provenance_sensitivity(case_dir, pl):
    """只读各策略完整明细重算，不读取 stable/agree/top_by_policy 汇总布尔值作裁决。

    两条豁免（v6.39.4 尘埃线；F-06 批 D 起裁决收据制）：
    ①尘埃锚点（<总供应 0.01%）不入翻转判定；②真实翻转必须被 input_binding 绑定的
    flip-adjudications/v1 裁决收据精确覆盖（本函数重验收据三验＋逐锚点指纹＋披露值，
    **不再信 ledger 内嵌自报的 acknowledged_flips**）；顺序未决无豁免。"""
    fails = []
    bs = pl.get("bounds_sensitivity") or {}
    per = bs.get("per_entity")
    if not isinstance(per, dict):
        return ["bounds_sensitivity.per_entity 缺失"]
    try:
        total_supply = int(pl.get("total_supply_raw") or 0)
    except (TypeError, ValueError):
        total_supply = 0
    # F-06：acks 只认 manifest/ledger input_binding 绑定的裁决收据文件——三验＋名册绑定
    # ＋逐锚点指纹重算。ledger 自报 acknowledged_flips（6.39.4 旧格式）不再作数：
    # 存量用过旧 ack 的案（MOG）重 freeze 会在此拦下，须重跑 trace（迁移声明见文档）。
    binding = pl.get("input_binding") or {}
    receipt_rows = {}
    flips_ref = (binding.get("algorithm_params") or {}).get("flip_adjudications")
    if flips_ref is not None:
        fpath, err = check_bound_file(case_dir, flips_ref)
        if err:
            fails.append(f"flip 裁决收据绑定 {err}")
        else:
            try:
                entity_path, entity_err = check_bound_file(case_dir, binding.get("entity_file"))
                _, receipt_rows = load_flip_adjudications(
                    fpath, current_entity_file=None if entity_err else entity_path)
            except (OSError, ValueError, TypeError) as exc:
                fails.append(f"flip 裁决收据不可验: {exc}")
    real_flips = ledger_real_flips(pl)
    fails += verify_flip_receipt_against_ledger(receipt_rows, real_flips)
    acks = set(receipt_rows) & set(real_flips)
    entity_ids = {e.get("entity_id") for e in pl.get("entities") or []}
    if set(per) != entity_ids:
        fails.append("敏感性实体集与 provenance entities 不一致")
    all_stable = True
    for eid in sorted(entity_ids):
        ent_s = per.get(eid) or {}
        anchors = ent_s.get("anchors") or {}
        for anchor_name in ("current", "peak"):
            # stock=0 的锚点允许没有敏感性明细；正库存必须三策略齐全。
            ent = next((x for x in pl.get("entities", []) if x.get("entity_id") == eid), {})
            stock = int(((ent.get("anchors") or {}).get(anchor_name) or {}).get("stock_raw", 0))
            if stock <= 0:
                continue
            if total_supply > 0 and stock * 10000 < total_supply:
                continue  # 尘埃锚点：构成排序不承载结论
            detail = anchors.get(anchor_name) or {}
            pd = detail.get("policy_details")
            if not isinstance(pd, dict) or set(pd) != {"pro_rata", "fifo", "lifo"}:
                fails.append(f"{eid} {anchor_name} 缺三策略完整 policy_details")
                all_stable = False
                continue
            tops = []
            for policy in ("pro_rata", "fifo", "lifo"):
                rows = pd.get(policy)
                if not isinstance(rows, list) or not rows:
                    fails.append(f"{eid} {anchor_name} {policy} 明细为空")
                    tops.append(None)
                    continue
                try:
                    parsed = [(tuple(r["terminal"]), int(r["raw"])) for r in rows]
                    if any(v < 0 for _, v in parsed):
                        raise ValueError("raw<0")
                    total = sum(v for _, v in parsed)
                    if abs(total - stock) > stock * 0.005:
                        fails.append(f"{eid} {anchor_name} {policy} 明细不闭合: {total} vs {stock}")
                    tops.append(sorted(parsed, key=lambda kv: (-kv[1], str(kv[0])))[0][0])
                except (KeyError, TypeError, ValueError) as e:
                    fails.append(f"{eid} {anchor_name} {policy} 明细结构异常: {e}")
                    tops.append(None)
            if len(set(tops)) != 1:
                all_stable = False
                if (eid, anchor_name) not in acks:
                    fails.append(f"{eid} {anchor_name} 三策略主导终点翻转（机器从明细独立重算）"
                                 "——真实多来源结构须 flip-adjudications/v1 裁决收据覆盖"
                                 "（--acknowledge-flip <收据文件> 重跑 trace）")
            order_rows = pd.get("pro_rata") or []
            order_raw = sum(int(r.get("raw", 0)) for r in order_rows
                            if r.get("terminal") == ["UNRESOLVED", "order_ambiguous", None])
            threshold = float(((detail.get("ordering_sensitivity") or {}).get("materiality_pct", 0.5)))
            if order_raw * 100.0 / stock > threshold:
                fails.append(f"{eid} {anchor_name} 事件顺序未决 {order_raw*100.0/stock:.4f}% > {threshold}%")
                all_stable = False
    if bs.get("conservative_vs_aggressive_verdict_stable") is not all_stable:
        fails.append("溯源敏感性 bounds_sensitivity 汇总布尔值与策略明细机器重算不一致")
    return fails


def validate_and_replay_provenance(case_dir, pl, pl_path, ep, manifest):
    """完整输入绑定 + 当前代码真实重放。返回失败列表；空列表才允许 freeze。"""
    fails = []
    b = pl.get("input_binding")
    if not isinstance(b, dict):
        return ["provenance 缺 input_binding——旧/人工台账不可冻结，必须从原始边重跑"]
    if pl.get("exploration") is True or b.get("mode") == "exploration":
        return ["provenance 是 allow-no-labels 探索产物，禁止进入正式 freeze"]
    if b.get("labels_file") is None:
        return ["provenance labels_file 为空——正式 freeze 必须绑定标签快照"]

    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "entity_source_trace.py")
    algorithm = b.get("algorithm") or {}
    algo = algorithm.get("script_sha256")
    current_algo, _ = full_sha256_file(script)
    if algo != current_algo:
        fails.append("entity_source_trace.py 算法哈希已变化——必须用当前代码重跑 provenance")
    algo_files = algorithm.get("files") or {}
    loader = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wave_scan.py")
    identity = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "solana",
                            "sqd_cache_identity.py")
    for name, expected in (("entity_source_trace.py", script), ("wave_scan.py", loader),
                           ("sqd_cache_identity.py", identity)):
        _, err = check_algorithm_file(algo_files.get(name), expected)
        if err:
            fails.append(f"算法依赖 {name} {err}")

    _, err = check_bound_file(case_dir, b.get("entity_file"), expected_path=ep)
    if err:
        fails.append(f"entity_file {err}")
    labels_path, err = check_bound_file(case_dir, b.get("labels_file"))
    if err:
        fails.append(f"labels_file {err}")
    elif labels_path:
        try:
            labels_obj = load_json(labels_path)
            valid_labels = [meta for meta in labels_obj.values()
                            if isinstance(meta, dict) and meta.get("kind") in PROVENANCE_LABEL_KINDS]
            if not valid_labels:
                fails.append("labels_file 有效标签数为 0——正式 freeze 不接受空标签快照")
        except (AttributeError, OSError, ValueError, TypeError) as exc:
            fails.append(f"labels_file 内容校验失败: {exc}")

    hb = b.get("handoff_manifest")
    if not isinstance(hb, dict):
        fails.append("provenance 未绑定 handoff_manifest")
    else:
        _, err = check_bound_file(case_dir, hb.get("file"),
                                  expected_path=os.path.join(case_dir, MANIFEST_NAME))
        if err:
            fails.append(f"handoff_manifest {err}")
        if hb.get("run_id") != manifest.get("run_id") or hb.get("scope") != manifest.get("scope"):
            fails.append("provenance 绑定的 manifest run_id/scope(cutoff,block,denominators) 与当前不一致")

    dm = b.get("data_map")
    data_paths = set()
    if not isinstance(dm, dict):
        fails.append("provenance 未绑定 data_map.json")
    else:
        _, err = check_bound_file(case_dir, dm.get("file"),
                                  expected_path=os.path.join(case_dir, "data_map.json"))
        if err:
            fails.append(f"data_map {err}")
        data_paths = set(dm.get("paths") or [])

    # 分母与边界必须来自同一已验证 manifest；没有冻结分母/边界本身就是不可复现。
    scope = manifest.get("scope") or {}
    den = scope.get("denominators")
    supply = None
    if isinstance(den, dict):
        # 分母键按优先级取第一个命中；细分分母 manifest（ANOM-A2-002 型拆分）以
        # nominal_allocation_supply_raw 为占比口径的冻结值，同受一致性绑定约束。
        for key in ("total_supply_raw", "total_supply", "supply_raw",
                    "nominal_allocation_supply_raw"):
            if den.get(key) is not None:
                supply = str(den[key])
                break
    if supply is None or supply != str(pl.get("total_supply_raw")) \
            or supply != str(b.get("total_supply_raw")):
        fails.append("total_supply 未与 manifest.scope.denominators 的冻结值一致绑定")
    if scope.get("cutoff_utc") in (None, "") and scope.get("frozen_block") in (None, ""):
        fails.append("manifest 未冻结 cutoff_utc/frozen_block，provenance 不可复现")

    source = b.get("source") or {}
    source_files = source.get("files")
    if not isinstance(source_files, list) or not source_files:
        fails.append("provenance source.files 为空")
    else:
        art_paths = {x.get("path") for x in manifest.get("artifacts") or []}
        for rec in source_files:
            _, err = check_bound_file(case_dir, rec)
            if err:
                fails.append(f"source {err}")
                continue
            rel = rec.get("path")
            if os.path.isabs(str(rel)) or rel not in data_paths or rel not in art_paths:
                fails.append(f"source {rel} 未同时绑定 verified manifest.artifacts 与 data_map")

    fails += recompute_provenance_sensitivity(case_dir, pl)
    if fails:
        return fails

    # 从允许字段重建命令，不执行 ledger 自报的自由文本 command。
    kind = source.get("kind")
    if kind == "evm_v2":
        argument = source.get("argument")
        try:
            arg = validate_evm_v2_argument(case_dir, argument)
            current_paths = enumerate_evm_v2_sources(case_dir, argument, arg)
        except ValueError as e:
            return [f"source argument 异常: {e}"]

        registered_paths = []
        seen_paths = set()
        for index, rec in enumerate(source_files):
            if not isinstance(rec, dict):
                return [f"evm_v2 source.files[{index}] 不是对象"]
            rel = rec.get("path")
            if not isinstance(rel, str):
                return [f"evm_v2 source.files[{index}].path 不是字符串"]
            if rel in seen_paths:
                return [f"evm_v2 source.files 登记路径重复: {rel!r}"]
            seen_paths.add(rel)
            registered_paths.append(rel)
        registered_set = set(registered_paths)
        disk_only = sorted(current_paths - registered_set)
        ledger_only = sorted(registered_set - current_paths)
        if disk_only or ledger_only:
            return [
                "evm_v2 重放前集合闸不等: "
                f"disk_only_count={len(disk_only)}, ledger_only_count={len(ledger_only)}, "
                f"disk_only_first10={disk_only[:10]}, ledger_only_first10={ledger_only[:10]}"
            ]
        # Guarantee assumes no concurrent writer mutates the case directory from
        # this completed check until the replay subprocess exits.  The remaining
        # validation-to-read TOCTOU window is known residual risk outside F-008.
        arg = str(arg)
    else:
        try:
            arg = resolve_bound_path(case_dir, source.get("argument"))
        except ValueError as e:
            return [f"source argument 异常: {e}"]
    fd, replay_path = tempfile.mkstemp(prefix=".provenance-replay-", suffix=".json", dir=case_dir)
    os.close(fd)
    try:
        cmd = [sys.executable, script]
        if kind == "sol":
            try:
                cache_meta = resolve_bound_path(case_dir, source.get("cache_meta"))
            except ValueError as exc:
                return [f"Solana provenance cache meta 异常: {exc}"]
            mint = source.get("mint")
            if not isinstance(mint, str) or not mint:
                return ["Solana provenance 未绑定 mint"]
            cmd += ["--edges-sol", os.path.realpath(arg),
                    "--sol-cache-meta", os.path.realpath(cache_meta),
                    "--mint", mint, "--case-root", os.path.realpath(case_dir)]
        elif kind == "evm_v2":
            cmd += ["--edges-evm-v2", arg]
        elif kind == "duckdb":
            cmd += ["--duckdb", arg, "--edges-table", str(source.get("edges_table") or "edges")]
        else:
            return [f"未知 provenance source kind: {kind!r}"]
        params = b.get("algorithm_params") or {}
        cmd += ["--total-supply", str(b.get("total_supply_raw")),
                "--entity-file", ep, "--out", replay_path,
                "--depth-limit", str(params["depth_limit"]),
                "--facility-min-degree", str(params["facility_min_degree"]),
                "--node-budget", str(params["node_budget"]),
                "--edge-budget", str(params["edge_budget"])]
        # F-06：翻转裁决改收据文件制——重放装配传绑定的收据文件引用（三验后原路径），
        # 与 trace 消费同一份实物；旧 acknowledged_flips 字符串参数不再受理（同批同 hunk 组，
        # 否则 freeze 重放当场断裂自卡死）。
        flips_ref = params.get("flip_adjudications")
        if flips_ref is not None:
            flips_path, flips_err = check_bound_file(case_dir, flips_ref)
            if flips_err:
                return [f"flip 裁决收据绑定 {flips_err}"]
            cmd += ["--acknowledge-flip", flips_path]
        if params.get("acknowledged_flips"):
            return ["provenance 携带 6.39.4 旧式 acknowledged_flips 字符串参数——"
                    "裁决收据制（flip-adjudications/v1）起旧确认不再受理，须重跑 trace"]
        if labels_path:
            cmd += ["--labels-file", labels_path]
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        p = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if p.returncode != 0:
            return [f"provenance 原始数据重放失败 exit={p.returncode}: "
                    f"{(p.stdout + p.stderr)[-1200:]}"]
        fresh = load_json(replay_path)
        if provenance_semantic_sha(fresh) != provenance_semantic_sha(pl):
            return ["provenance 重放语义摘要与待冻结台账不一致——台账过期/人工构造/参数漂移"]
    except (KeyError, OSError, ValueError, TypeError) as e:
        return [f"provenance 重放参数/执行异常: {e}"]
    finally:
        if os.path.isfile(replay_path):
            os.unlink(replay_path)
    return []

def cmd_freeze(a):
    case_dir = os.path.abspath(a.case_dir)
    path = os.path.join(case_dir, FREEZE_NAME)
    if a.check_unseal:
        if os.path.isfile(path):
            try:
                fz = load_json(path)
                checks = ((fz.get("members_source"), fz.get("members_sha256")),
                          (fz.get("entity_file"), fz.get("entity_file_sha256")),
                          ("provenance_ledger.json", fz.get("provenance_ledger_sha256")),
                          (MANIFEST_NAME, fz.get("manifest_sha256")),
                          ("data_map.json", fz.get("data_map_sha256")))
                if fz.get("distribution_adjudications_sha256"):
                    checks += ((DISTRIBUTION_ADJUDICATIONS_NAME,
                                fz.get("distribution_adjudications_sha256")),)
                drift = []
                for rel, want in checks:
                    if not rel or not want:
                        drift.append(f"冻结记录缺绑定字段: {rel or 'unknown'}")
                        continue
                    p = resolve_bound_path(case_dir, rel)
                    if not os.path.isfile(p):
                        drift.append(f"冻结后缺文件: {rel}")
                        continue
                    _, got, _ = sha256_file(p)
                    if got != want:
                        drift.append(f"冻结后哈希漂移: {rel}")
                # provenance ledger 内绑定的原始边、标签和算法依赖也必须仍是冻结时版本；
                # 只验 ledger 自身哈希会漏掉“ledger 未动、raw/labels 已换”的揭盲绕过。
                pl_now = load_json(os.path.join(case_dir, "provenance_ledger.json"))
                binding = pl_now.get("input_binding") or {}
                bound_records = []
                bound_records += list(((binding.get("source") or {}).get("files") or []))
                algo_files = ((binding.get("algorithm") or {}).get("files") or {})
                script_dir = os.path.dirname(os.path.abspath(__file__))
                for name in ("entity_source_trace.py", "wave_scan.py"):
                    _, err = check_algorithm_file(algo_files.get(name), os.path.join(script_dir, name))
                    if err:
                        drift.append(f"算法依赖 {name} {err}")
                for key in ("entity_file", "labels_file"):
                    if binding.get(key) is not None:
                        bound_records.append(binding.get(key))
                # F-D2：flip 裁决收据与 labels_file 同待遇——冻结后改写/删除裁决存证
                # （裁决主体/时间/理由/证据）必须被揭盲把关抓住，不能只靠 A5 兜底。
                flips_rec = (binding.get("algorithm_params") or {}).get("flip_adjudications")
                if flips_rec is not None:
                    bound_records.append(flips_rec)
                for key in ("handoff_manifest", "data_map"):
                    if isinstance(binding.get(key), dict) and binding[key].get("file"):
                        bound_records.append(binding[key]["file"])
                for rec in bound_records:
                    _, err = check_bound_file(case_dir, rec)
                    if err:
                        drift.append(err)
                if not drift:
                    print(f"[freeze] 已冻结（{fz.get('frozen_at_utc')}，成员表 {fz['members_sha256'][:12]}…）——允许揭盲/读 sealed")
                    return 0
                print("[freeze] 冻结绑定已漂移——禁止揭盲:", file=sys.stderr)
                for x in drift:
                    print(f"  ✗ {x}", file=sys.stderr)
                return 2
            except Exception:
                pass
        print("[freeze] entity_freeze.json 不存在或无效——实体未冻结，禁止揭盲、禁止读 sealed/", file=sys.stderr)
        return 2

    if not a.members:
        print("[freeze] 需要 --members <成员表文件>（如 analysis-state.json）", file=sys.stderr)
        return 1
    if not a.entity_file:
        print("[freeze] 需要 --entity-file <实体名册 {entity_id:[addr…]}>——裁决 linked_entity 绑定"
              "与溯源台账逐实体比对都以它为准（v6.8.1 无跳过通道）", file=sys.stderr)
        return 1
    try:
        safe_case_file(case_dir, a.members)
        safe_case_file(case_dir, a.entity_file)
        mp = os.path.join(case_dir, a.members)
        ep = os.path.join(case_dir, a.entity_file)
    except ValueError as e:
        print(f"[freeze] 成员表/实体名册路径非法: {e}", file=sys.stderr)
        return 2
    try:
        entity_map = load_json(ep)
        assert isinstance(entity_map, dict) and entity_map
        assert all(isinstance(k, str) and isinstance(v, list)
                   and all(isinstance(x, str) and x for x in v) for k, v in entity_map.items())
    except Exception:
        print(f"[freeze] 实体名册格式错误（需非空 {{entity_id:[addr…]}}）: {ep}", file=sys.stderr)
        return 2

    # ── 前置 0：同进程严格 v2 verify（v6.8.1 codex 复核修复——manifest 缺失/BLOCKED/
    # 哈希漂移/legacy 契约时一律禁止冻结；不存在绕过 verify 的冻结路径）
    vfails, verified_manifest, _ = verify_case(case_dir, legacy_read_only=False)
    if vfails:
        print("[freeze] handoff verify 未通过——禁止冻结（fail-closed）:", file=sys.stderr)
        for x in vfails:
            print(f"  ✗ {x}", file=sys.stderr)
        return 2

    # ── 前置 1：裁决闭环（v6.8.0；v6.8.1 起把实体名册传给 validator——
    # linked_entity 绑定校验不可跳过）："报警器响了没人管照样冻结"从此机器堵死。
    # 旧案 revision 追加同样过此闸：改成员表＝新结论，必须先重跑 v2 扫描器补裁决。
    validator = os.path.join(os.path.dirname(os.path.abspath(__file__)), "adjudication_validator.py")
    pv = subprocess.run([sys.executable, validator, "validate", "--case-dir", case_dir,
                         "--entity-file", a.entity_file],
                        capture_output=True, text=True)
    if pv.returncode != 0:
        print("[freeze] 候选裁决闭环未通过——禁止冻结（validator 输出如下）:", file=sys.stderr)
        sys.stderr.write(pv.stdout + pv.stderr)
        return 2

    distribution_adj_path = os.path.join(case_dir, DISTRIBUTION_ADJUDICATIONS_NAME)
    distribution_adj_digest = None
    if os.path.isfile(distribution_adj_path):
        pd = subprocess.run([sys.executable, validator, "distribution-validate",
                             "--case-dir", case_dir, "--entity-file", a.entity_file],
                            capture_output=True, text=True)
        if pd.returncode != 0:
            print("[freeze] 分布异常裁决闭环未通过——禁止冻结:", file=sys.stderr)
            sys.stderr.write(pd.stdout + pd.stderr)
            return 2
        _, distribution_adj_digest, _ = sha256_file(distribution_adj_path)

    # ── 前置 2：溯源闸内容级绑定（v6.8.1 codex 复核修复——不再信文件自报：
    # ①schema 必须 v2（v1 是 pro-rata 数学错误版）；②台账实体 ID 集与本次名册双向一致；
    # ③逐实体 members_sha256 与名册成员集哈希一致（改过名册的旧台账自动失效）；
    # ④closure 从 composition[].raw 重算，不读自报 closure_check；
    # ⑤stock>0 而 composition 为空＝空壳台账，拒。敏感性与原始数据真实性归前置 3 重算/重放。）
    pl_path = os.path.join(case_dir, "provenance_ledger.json")
    if not os.path.isfile(pl_path):
        print("[freeze] 缺 provenance_ledger.json——先对临时实体表跑 entity_source_trace.py"
              "（溯源闸），新支路补候选回裁决环后再冻结", file=sys.stderr)
        return 2
    try:
        pl = load_json(pl_path)
        if pl.get("schema") != PROVENANCE_SCHEMA:
            print(f"[freeze] provenance_ledger schema {pl.get('schema')!r} ≠ {PROVENANCE_SCHEMA}——"
                  "v1 算法有数学错误（累计流入归一化不扣流出），一律重跑 v2 溯源", file=sys.stderr)
            return 2
        ents = pl.get("entities") or []
        if not ents:
            print("[freeze] provenance_ledger 无实体条目——空壳台账拒收", file=sys.stderr)
            return 2
        led_ids = {e.get("entity_id") for e in ents}
        map_ids = set(entity_map)
        if led_ids != map_ids:
            print(f"[freeze] 溯源台账实体集与名册不一致: 台账多 {sorted(led_ids - map_ids)}，"
                  f"名册多 {sorted(map_ids - led_ids)}——名册改动后必须重跑溯源", file=sys.stderr)
            return 2
        for ent in ents:
            eid = ent["entity_id"]
            want = hashlib.sha256(",".join(sorted(set(entity_map[eid]))).encode()).hexdigest()
            if ent.get("members_sha256") != want:
                print(f"[freeze] {eid} 成员集哈希不符（台账 {str(ent.get('members_sha256'))[:12]}… ≠ "
                      f"名册 {want[:12]}…）——成员改动后的旧台账不得复用", file=sys.stderr)
                return 2
            for anchor_name in ("current", "peak"):
                anchor = ent["anchors"][anchor_name]
                stock = int(anchor["stock_raw"])
                comp = anchor.get("composition")
                if stock <= 0:
                    continue
                if not comp:
                    print(f"[freeze] {eid} {anchor_name} 锚点库存 {stock} > 0 但 composition 为空"
                          "——空壳台账拒收", file=sys.stderr)
                    return 2
                s_raw = sum(int(c["raw"]) for c in comp)
                if abs(s_raw - stock) > stock * 0.005:
                    print(f"[freeze] 溯源闭合重算失败: {eid} {anchor_name} Σraw={s_raw} vs "
                          f"stock={stock}（偏差 {abs(s_raw-stock)*100.0/stock:.2f}% > 0.5%——"
                          "closure 按构成明细重算，自报值不作数）", file=sys.stderr)
                    return 2
    except (KeyError, ValueError, TypeError) as e:
        print(f"[freeze] provenance_ledger.json 结构异常: {e}", file=sys.stderr)
        return 2

    # ── 前置 3：完整输入绑定＋当前代码真实重放。此闸也从 policy_details 独立重算
    # FIFO/LIFO/pro-rata 与顺序敏感性，不读取 ledger 自报 stable 布尔值作裁决。
    replay_fails = validate_and_replay_provenance(
        case_dir, pl, pl_path, ep, verified_manifest)
    if replay_fails:
        print("[freeze] provenance 原始数据绑定/重放未通过——禁止冻结:", file=sys.stderr)
        for x in replay_fails:
            print(f"  ✗ {x}", file=sys.stderr)
        return 2

    algo, digest, size = sha256_file(mp)
    _, ent_digest, _ = sha256_file(ep)
    _, pl_digest, _ = sha256_file(pl_path)
    _, manifest_digest, _ = sha256_file(os.path.join(case_dir, MANIFEST_NAME))
    _, data_map_digest, _ = sha256_file(os.path.join(case_dir, "data_map.json"))
    binding_digest = hashlib.sha256(json.dumps(pl.get("input_binding"), sort_keys=True,
                                               ensure_ascii=False).encode()).hexdigest()
    now = utcnow()
    entry = {"members_source": os.path.relpath(mp, case_dir), "members_sha256": digest,
             "entity_file": os.path.relpath(ep, case_dir), "entity_file_sha256": ent_digest,
             "provenance_ledger_sha256": pl_digest,
             "provenance_input_binding_sha256": binding_digest,
             "manifest_sha256": manifest_digest,
             "manifest_run_id": verified_manifest.get("run_id"),
             "manifest_scope": verified_manifest.get("scope"),
             "data_map_sha256": data_map_digest,
             "distribution_adjudications_sha256": distribution_adj_digest,
             "frozen_at_utc": now, "pending_items": [x for x in (a.pending or "").split(";") if x],
             "casebook_note": a.casebook_note}
    rev_keys = ("members_source", "members_sha256", "entity_file", "entity_file_sha256",
                "provenance_ledger_sha256", "provenance_input_binding_sha256",
                "manifest_sha256", "manifest_run_id", "manifest_scope", "data_map_sha256",
                "distribution_adjudications_sha256", "frozen_at_utc", "pending_items", "casebook_note")
    if os.path.isfile(path):
        fz = load_json(path)
        no_op_keys = tuple(k for k in rev_keys if k != "frozen_at_utc")
        if all(fz.get(k) == entry.get(k) for k in no_op_keys):
            print("[freeze] 成员/名册/provenance/manifest/data_map 全部绑定未变化，无需新 revision")
            return 0
        fz.setdefault("revisions", []).append({k: fz[k] for k in rev_keys if k in fz})
        fz.update(entry)
        atomic_write_json(path, fz)
        print(f"[freeze] revision #{len(fz['revisions'])} 追加（不覆盖历史）——新成员表 {digest[:12]}…")
        return 0
    fz = {"schema": "entity-freeze/v1", **entry, "revisions": []}
    atomic_write_json(path, fz)
    print(f"[freeze] 初次冻结 → {path}（成员表 {digest[:12]}…，实体名册 {ent_digest[:12]}…，"
          f"未决项 {len(entry['pending_items'])}）")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="subcmd", required=True)  # 勿用 dest="cmd"：与 receipt 的 --cmd 参数冲突

    g = sub.add_parser("generate", help="−1 收工产 manifest")
    g.add_argument("--case-dir", required=True)
    g.add_argument("--mode", required=True, choices=["full"])
    g.add_argument("--status", required=True)
    g.add_argument("--status-reason", default=None)
    g.add_argument("--producer-model", required=True)
    g.add_argument("--case-id", default=None)
    g.add_argument("--run-id", default=None)
    g.add_argument("--chain", default=None, help="逗号分隔链范围")
    g.add_argument("--contract", default=None)
    g.add_argument("--cutoff", default=None, help="UTC 数据截止时间")
    g.add_argument("--frozen-block", default=None)
    g.add_argument("--denominators", default=None, help="三分母 JSON 字符串")
    g.add_argument("--gate", action="append", help="name:verdict:exit:artifact，可重复")
    g.add_argument("--include", action="append", help="附加产物相对路径，可重复")

    v = sub.add_parser("verify", help="−2 开工 fail-closed 校验")
    v.add_argument("--case-dir", required=True)
    v.add_argument("--legacy-read-only", action="store_true",
                   help="显式降级：允许 handoff/v1 旧案只读（不得生成新正式报告）")

    r = sub.add_parser("receipt", help="−1 追加执行收据")
    r.add_argument("--case-dir", required=True)
    r.add_argument("--step", required=True)
    r.add_argument("--cmd", required=True)
    r.add_argument("--exit", type=int, required=True)
    r.add_argument("--artifacts", default=None, help="逗号分隔产物相对路径")
    r.add_argument("--note", default=None)

    f = sub.add_parser("freeze", help="−2 实体冻结 / --check-unseal 揭盲把关")
    f.add_argument("--case-dir", required=True)
    f.add_argument("--members", default=None, help="成员表文件（含实体成员名册，快照哈希入冻结记录）")
    f.add_argument("--entity-file", default=None,
                   help="规范实体名册 {entity_id:[addr…]}——裁决 linked_entity 绑定＋溯源台账"
                        "逐实体哈希比对以它为准（v6.8.1 必填）")
    f.add_argument("--pending", default=None, help="未决项，分号分隔")
    f.add_argument("--casebook-note", default=None)
    f.add_argument("--check-unseal", action="store_true")

    a = ap.parse_args()
    try:
        return {"generate": cmd_generate, "verify": cmd_verify,
                "receipt": cmd_receipt, "freeze": cmd_freeze}[a.subcmd](a)
    except Exception as e:
        print(f"[{a.subcmd}] 脚本自身错误（exit 1，修完重跑）: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
