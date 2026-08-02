#!/usr/bin/env python3
"""split-run 交接契约工具（references/split-run.md §2 的机器实现）。

子命令：
  generate  −1 收工产 handoff_manifest.json（语义收据：gate 状态自动适配＋产物 allowlist 哈希）
  verify    −2 开工 fail-closed 校验（文件齐/哈希对/gate 重查/schema 兼容/状态 READY）
  receipt   −1 每步追加 stage1_receipts.json 执行收据（断点恢复＋盲化审计）
  freeze    −2 实体冻结物化 entity_freeze.json（revision 追加制）；--check-unseal 把关揭盲/读 sealed

退出码语义（对齐 skill 现有 gate）：0=放行；2=验证不通过/前置未满足（硬停）；1=脚本自身错误（修完重跑）。
用法示例：
  python3 handoff_manifest.py generate --case-dir <案目录> --mode easy --status READY \
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
from datetime import datetime, timezone

SCHEMA_VERSION = "handoff/v2"
# verify 端支持集；consumer_min_schema 不在集内即拒收。
# v1（6.7.x 及以前）默认拒——fail-open 修复（2026-08-01 codex 复核）：漏跑新生产器的旧格式
# 不得静默过闸；已冻结旧案只能走 verify --legacy-read-only 显式降级（不得生成新正式报告）。
SUPPORTED_SCHEMAS = {"handoff/v2"}
LEGACY_SCHEMAS = {"handoff/v1"}
MANIFEST_NAME = "handoff_manifest.json"
RECEIPTS_NAME = "stage1_receipts.json"
FREEZE_NAME = "entity_freeze.json"
ADJUDICATIONS_NAME = "candidate_adjudications.json"
LEGACY_RECEIPT_NAME = "legacy_readonly_receipt.json"
PROVENANCE_SCHEMA = "provenance-ledger/v2"  # v1 是 pro-rata 数学错误版（2026-08-01 codex 复核），一律拒
STATUSES = {"READY", "BLOCKED", "PARTIAL", "SUPERSEDED", "BLOCKED_E0B"}
SPARSE_THRESHOLD = 64 * 1024 * 1024  # >64MB 用分片哈希（split-run §2.2：不收尾全盘重哈希）
CHUNK = 4 * 1024 * 1024

# 契约核心件（存在即登记；candidate_universe/anomalies/data_map 为 READY 必备，见 REQUIRED_FOR_READY）
CONTRACT_FILES = [
    "candidate_universe.json", "candidate_screening.json", "identity_preflight.json",
    "anomalies.json", "data_map.json", "unlock_evidence.json", RECEIPTS_NAME,
    "accounting_mode.json", "supply_truth.json", "wave_scan_report.json",
    "flow_anomaly_report.json", ADJUDICATIONS_NAME, "provenance_ledger.json",
    "time_spotcheck.json",
]
REQUIRED_FOR_READY = ["candidate_universe.json", "candidate_screening.json",
                      "identity_preflight.json", "anomalies.json", "data_map.json",
                      # A0/A2 必产的两个 gate 产物——READY 缺任一＝流程没跑完（dry-run 步 3.5 收紧）
                      "accounting_mode.json", "supply_truth.json",
                      # 波次扫描＋资金流异常扫描（W1 二次漏检复盘 v6.8.0）——两扫描器任一未跑
                      # 不得 READY；旧案目录复用须补跑后重新 generate，回退路径=旧单会话命令。
                      # candidate_adjudications.json 是 −2 判断层产物，不在 −1 READY 清单——
                      # 它的强制在 freeze 端（validator 全候选校验，缺漏即 exit 2）
                      "wave_scan_report.json", "flow_anomaly_report.json"]
# EVM 家族链另加时间抽查产物为 READY 必备（6.7.0，APU SQD 全史重拉冗余复盘）——
# time_spotcheck.py 固化后，锚点级第二源直查是 A2 第 4 查的机器凭证，缺件＝时间抽查没跑
# 或又走了自由发挥老路。Solana（anchor_sampler 通道）/hyperliquid/filecoin 等非 EVM 链
# 时间抽查形态不同，不进本硬闸（白名单法：链名命中才强制，未知新链不误伤）。
EVM_CHAINS = {"eth", "ethereum", "bsc", "base", "arbitrum", "polygon", "optimism",
              "robinhood", "opbnb", "avalanche", "fantom", "cronos", "linea",
              "scroll", "blast", "zksync"}
REQUIRED_FOR_READY_EVM = ["time_spotcheck.json"]
# 自动 gate 适配：从产物 JSON 读 verdict/exit_code（防手报）；verify 时重读比对
AUTO_GATES = {"accounting_gate": "accounting_mode.json", "supply_truth_gate": "supply_truth.json",
              "time_spotcheck": "time_spotcheck.json"}
# data_map 明确登记的 .duckdb 可能是 provenance 的正式重放源，必须进 manifest 绑定；
# WAL/临时文件仍排除。大库由 sha256-sparse 做交接哈希，freeze 的 input_binding 另做完整哈希。
EXCLUDE_SUFFIXES = (".log", ".duckdb.wal", ".lock", ".tmp", ".bak")
EXCLUDE_NAMES = {"config.json", MANIFEST_NAME}  # manifest 不含自身；config 可能含运行时 key 路径


def utcnow():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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

    artifacts, missing_required = [], []
    seen = set()

    def add(rel):
        if rel in seen:
            return
        p = os.path.join(case_dir, rel)
        if not os.path.isfile(p):
            return
        base = os.path.basename(rel)
        if base in EXCLUDE_NAMES or base.endswith(EXCLUDE_SUFFIXES):
            return
        artifacts.append(file_entry(case_dir, rel))
        seen.add(rel)

    for name in CONTRACT_FILES:
        add(name)
    # data_map 里登记的数据文件并入 allowlist（避免 glob 大杂烩，索引即白名单）
    dm_path = os.path.join(case_dir, "data_map.json")
    if os.path.isfile(dm_path):
        try:
            dm = load_json(dm_path)
            for ent in dm.get("files", []):
                rel = ent.get("path")
                if rel and not os.path.isabs(rel):
                    add(rel)
        except Exception as e:
            print(f"[generate] data_map.json 解析失败（将继续，但 READY 会被 verify 拒）: {e}", file=sys.stderr)
    for extra in a.include or []:
        add(extra)
    # sealed/ 只记哈希（密封纪律：manifest 记哈希不记内容，读取由 --check-unseal 把关）
    sealed_dir = os.path.join(case_dir, "sealed")
    sealed = []
    if os.path.isdir(sealed_dir):
        for name in sorted(os.listdir(sealed_dir)):
            p = os.path.join(sealed_dir, name)
            if os.path.isfile(p):
                algo, digest, size = sha256_file(p)
                sealed.append({"path": f"sealed/{name}", "bytes": size, "hash_algo": algo, "sha256": digest})

    if a.status == "READY":
        required = list(REQUIRED_FOR_READY)
        chains = {c.strip().lower() for c in (a.chain or "").split(",") if c.strip()}
        if chains & EVM_CHAINS:
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
        add(rel)
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
        "scope": {"chains": [c for c in (a.chain or "").split(",") if c] or None,
                  "contract": a.contract, "cutoff_utc": a.cutoff,
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

def _verify_light_schema(case_dir, fails, legacy=False):
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
    if legacy:
        return
    try:
        ws = load_json(os.path.join(case_dir, "wave_scan_report.json"))
        if ws.get("schema") in ("wave-scan/v1", "wave-scan/v2"):
            fails.append(f"wave_scan_report.json 是旧版（{ws.get('schema')}）——v2 及更早缺 scan_universe "
                         "逐址全集（候选对账没账可对），重跑 wave_scan.py（v3）后重 generate；"
                         "已冻结旧案走 verify --legacy-read-only")
        elif ws.get("schema") != "wave-scan/v3":
            fails.append(f"wave_scan_report.json schema 异常: {ws.get('schema')}")
        elif not isinstance(ws.get("waves"), list) or not isinstance(ws.get("equal_amount_groups"), list) \
                or not isinstance(ws.get("requires_adjudication"), bool):
            fails.append("wave_scan_report.json 缺 waves/equal_amount_groups/requires_adjudication——空壳拒收")
        elif not isinstance(ws.get("scan_universe"), list) \
                or not isinstance(ws.get("must_adjudicate_count"), int) \
                or len(ws["scan_universe"]) != ws.get("scan_universe_count"):
            fails.append("wave_scan_report.json v3 全集不完整（scan_universe 须为数组、"
                         "must_adjudicate_count 须为整数、len(scan_universe)==scan_universe_count）"
                         "——贴 v3 标签不带逐址全集同属空壳，拒收")
        elif any(not isinstance(u, dict) or not str(u.get("addr") or "").strip()
                 or not isinstance(u.get("must_adjudicate"), bool)
                 for u in ws["scan_universe"]) \
                or sum(1 for u in ws["scan_universe"] if u.get("must_adjudicate")) \
                != ws["must_adjudicate_count"]:
            fails.append("wave_scan_report.json v3 全集内部矛盾（每条须有 addr 且 "
                         "must_adjudicate 为布尔；must_adjudicate_count 必须等于逐条 true 计数"
                         "——count=0 配 must=true 条目这类自相矛盾拒收，v6.9.4）")
    except Exception as e:
        fails.append(f"wave_scan_report.json 读取失败（波次扫描未跑？补跑 wave_scan.py 后重 generate）: {e}")
    try:
        fa = load_json(os.path.join(case_dir, "flow_anomaly_report.json"))
        if fa.get("schema") != "flow-anomaly/v2":
            fails.append(f"flow_anomaly_report.json schema 异常: {fa.get('schema')}"
                         "（需要 flow-anomaly/v2——旧 v1 产物重跑 flow_anomaly_scan.py）")
        elif not isinstance(fa.get("sinks"), list) or not isinstance(fa.get("sprays"), list) \
                or not isinstance(fa.get("requires_adjudication"), bool):
            fails.append("flow_anomaly_report.json 缺 sinks/sprays/requires_adjudication——空壳拒收")
    except Exception as e:
        fails.append(f"flow_anomaly_report.json 读取失败（资金流异常扫描未跑？补跑 flow_anomaly_scan.py 后重 generate）: {e}")


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
                         "（wave_scan v2/flow_anomaly）后重 generate；只读旧案加 --legacy-read-only")
        else:
            fails.append(f"schema 不兼容: 需要 {schema}，本端支持 {sorted(SUPPORTED_SCHEMAS)}")
    status = m.get("status")
    if status != "READY":
        fails.append(f"状态 {status} ≠ READY，拒绝消费（原因: {m.get('status_reason')}）")

    if not fails:  # schema/状态硬伤先报，避免在坏 manifest 上白跑哈希
        art_paths = {ent.get("path") for ent in m.get("artifacts", [])}
        # READY 必备件独立重算（v6.8.1：不信 generate 曾正确执行——手改 manifest 的
        # artifacts/gates 列表同样过不了这道重查）
        if not legacy_mode:
            required = list(REQUIRED_FOR_READY)
            chains = {str(c).strip().lower() for c in (m.get("scope", {}) or {}).get("chains") or []}
            if chains & EVM_CHAINS:
                required += REQUIRED_FOR_READY_EVM
            miss = [n for n in required if n not in art_paths]
            if miss:
                fails.append(f"READY 必备件不在 artifact 清单: {miss}（manifest 被手改或 generate 版本过旧）")
            gates_m = m.get("gates") or {}
            for gname, rel in AUTO_GATES.items():
                if rel in art_paths and gname not in gates_m:
                    fails.append(f"gate {gname} 缺失（产物 {rel} 在场却无对应 gate 记录）")
        for ent in m.get("artifacts", []):
            p = os.path.join(case_dir, ent["path"])
            if not os.path.isfile(p):
                fails.append(f"缺件: {ent['path']}")
                continue
            algo, digest, size = sha256_file(p)
            if size != ent["bytes"] or digest != ent["sha256"] or algo != ent.get("hash_algo"):
                fails.append(f"哈希/大小漂移: {ent['path']}")
        for gname, g in (m.get("gates") or {}).items():
            if g.get("source") == "auto":
                try:
                    now = read_gate_artifact(case_dir, g["artifact"])
                    if now["verdict"] != g.get("verdict") or now["exit_code"] != g.get("exit_code"):
                        fails.append(f"gate {gname} 语义漂移: manifest 记 {g.get('verdict')}/{g.get('exit_code')}，"
                                     f"产物现为 {now['verdict']}/{now['exit_code']}")
                    elif now["verdict"] != "PASS" or now["exit_code"] != 0:
                        fails.append(f"gate {gname} 非 PASS 却报 READY: {now}")
                except Exception as e:
                    fails.append(f"gate {gname} 产物重读失败: {e}")
            else:
                if str(g.get("verdict", "")).upper() not in ("PASS", "OK"):
                    fails.append(f"gate {gname}（declared）非 PASS 却报 READY: {g.get('verdict')}")
        _verify_light_schema(case_dir, fails, legacy=legacy_mode)
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
    if not isinstance(shown, str) or not shown:
        raise ValueError("绑定 path 为空")
    return os.path.normpath(shown if os.path.isabs(shown) else os.path.join(case_dir, shown))


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


def provenance_semantic_payload(report):
    return {k: report.get(k) for k in ("schema", "total_supply_raw", "input_binding",
                                        "entities", "unresolved_total_pct", "bounds_sensitivity")}


def provenance_semantic_sha(report):
    return hashlib.sha256(json.dumps(provenance_semantic_payload(report), sort_keys=True,
                                     ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def recompute_provenance_sensitivity(pl):
    """只读各策略完整明细重算，不读取 stable/agree/top_by_policy 汇总布尔值作裁决。"""
    fails = []
    bs = pl.get("bounds_sensitivity") or {}
    per = bs.get("per_entity")
    if not isinstance(per, dict):
        return ["bounds_sensitivity.per_entity 缺失"]
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
                fails.append(f"{eid} {anchor_name} 三策略主导终点翻转（机器从明细重算）")
                all_stable = False
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

    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "entity_source_trace.py")
    algorithm = b.get("algorithm") or {}
    algo = algorithm.get("script_sha256")
    current_algo, _ = full_sha256_file(script)
    if algo != current_algo:
        fails.append("entity_source_trace.py 算法哈希已变化——必须用当前代码重跑 provenance")
    algo_files = algorithm.get("files") or {}
    loader = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wave_scan.py")
    for name, expected in (("entity_source_trace.py", script), ("wave_scan.py", loader)):
        _, err = check_bound_file(case_dir, algo_files.get(name), expected_path=expected)
        if err:
            fails.append(f"算法依赖 {name} {err}")

    _, err = check_bound_file(case_dir, b.get("entity_file"), expected_path=ep)
    if err:
        fails.append(f"entity_file {err}")
    labels_path = None
    if b.get("labels_file") is not None:
        labels_path, err = check_bound_file(case_dir, b.get("labels_file"))
        if err:
            fails.append(f"labels_file {err}")

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
        for key in ("total_supply_raw", "total_supply", "supply_raw"):
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

    fails += recompute_provenance_sensitivity(pl)
    if fails:
        return fails

    # 从允许字段重建命令，不执行 ledger 自报的自由文本 command。
    kind = source.get("kind")
    try:
        arg = resolve_bound_path(case_dir, source.get("argument"))
    except ValueError as e:
        return [f"source argument 异常: {e}"]
    fd, replay_path = tempfile.mkstemp(prefix=".provenance-replay-", suffix=".json", dir=case_dir)
    os.close(fd)
    try:
        cmd = [sys.executable, script]
        if kind == "sol":
            cmd += ["--edges-sol", arg]
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
                bound_records += list(((binding.get("algorithm") or {}).get("files") or {}).values())
                for key in ("entity_file", "labels_file"):
                    if binding.get(key) is not None:
                        bound_records.append(binding.get(key))
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
    mp = os.path.join(case_dir, a.members) if not os.path.isabs(a.members) else a.members
    ep = os.path.join(case_dir, a.entity_file) if not os.path.isabs(a.entity_file) else a.entity_file
    if not os.path.isfile(mp):
        print(f"[freeze] 成员表不存在: {mp}", file=sys.stderr)
        return 2
    if not os.path.isfile(ep):
        print(f"[freeze] 实体名册不存在: {ep}", file=sys.stderr)
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
                         "--entity-file", ep],
                        capture_output=True, text=True)
    if pv.returncode != 0:
        print("[freeze] 候选裁决闭环未通过——禁止冻结（validator 输出如下）:", file=sys.stderr)
        sys.stderr.write(pv.stdout + pv.stderr)
        return 2

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
             "frozen_at_utc": now, "pending_items": [x for x in (a.pending or "").split(";") if x],
             "casebook_note": a.casebook_note}
    rev_keys = ("members_source", "members_sha256", "entity_file", "entity_file_sha256",
                "provenance_ledger_sha256", "provenance_input_binding_sha256",
                "manifest_sha256", "manifest_run_id", "manifest_scope", "data_map_sha256",
                "frozen_at_utc", "pending_items", "casebook_note")
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
    g.add_argument("--mode", required=True, choices=["easy", "full"])
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
