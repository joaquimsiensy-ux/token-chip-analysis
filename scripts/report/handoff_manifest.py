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
  python3 handoff_manifest.py freeze --case-dir <案目录> --members analysis-state.json
  python3 handoff_manifest.py freeze --case-dir <案目录> --check-unseal
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
EXCLUDE_SUFFIXES = (".log", ".duckdb", ".duckdb.wal", ".lock", ".tmp", ".bak")
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
        if ws.get("schema") == "wave-scan/v1":
            fails.append("wave_scan_report.json 是 v6.6.1 旧版（wave-scan/v1）——重跑 wave_scan.py（v2）"
                         "后重 generate；已冻结旧案走 verify --legacy-read-only")
        elif ws.get("schema") != "wave-scan/v2":
            fails.append(f"wave_scan_report.json schema 异常: {ws.get('schema')}")
        elif not isinstance(ws.get("waves"), list) or not isinstance(ws.get("equal_amount_groups"), list) \
                or not isinstance(ws.get("requires_adjudication"), bool):
            fails.append("wave_scan_report.json 缺 waves/equal_amount_groups/requires_adjudication——空壳拒收")
    except Exception as e:
        fails.append(f"wave_scan_report.json 读取失败（波次扫描未跑？补跑 wave_scan.py 后重 generate）: {e}")
    try:
        fa = load_json(os.path.join(case_dir, "flow_anomaly_report.json"))
        if fa.get("schema") != "flow-anomaly/v1":
            fails.append(f"flow_anomaly_report.json schema 异常: {fa.get('schema')}")
        elif not isinstance(fa.get("sinks"), list) or not isinstance(fa.get("sprays"), list) \
                or not isinstance(fa.get("requires_adjudication"), bool):
            fails.append("flow_anomaly_report.json 缺 sinks/sprays/requires_adjudication——空壳拒收")
    except Exception as e:
        fails.append(f"flow_anomaly_report.json 读取失败（资金流异常扫描未跑？补跑 flow_anomaly_scan.py 后重 generate）: {e}")


def cmd_verify(a):
    case_dir = os.path.abspath(a.case_dir)
    manifest_path = os.path.join(case_dir, MANIFEST_NAME)
    if not os.path.isfile(manifest_path):
        print(f"[verify] 缺 {MANIFEST_NAME}——−1 未收工或目录不对", file=sys.stderr)
        return 2
    try:
        m = load_json(manifest_path)
    except Exception as e:
        print(f"[verify] manifest 解析失败: {e}", file=sys.stderr)
        return 2

    fails = []
    schema = m.get("consumer_min_schema")
    if schema not in SUPPORTED_SCHEMAS:
        if schema in LEGACY_SCHEMAS and a.legacy_read_only:
            print(f"[verify] ⚠ LEGACY READ-ONLY：{schema} 旧格式仅供读取既有冻结结论，"
                  "不得据此生成新正式报告、不得重新判级（fail-open 修复条款）")
        elif schema in LEGACY_SCHEMAS:
            fails.append(f"schema {schema} 是旧版——新运行必须重跑 v6.8.0 生产器"
                         "（wave_scan v2/flow_anomaly）后重 generate；只读旧案加 --legacy-read-only")
        else:
            fails.append(f"schema 不兼容: 需要 {schema}，本端支持 {sorted(SUPPORTED_SCHEMAS)}")
    status = m.get("status")
    if status != "READY":
        fails.append(f"状态 {status} ≠ READY，拒绝消费（原因: {m.get('status_reason')}）")

    if not fails:  # schema/状态硬伤先报，避免在坏 manifest 上白跑哈希
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
        _verify_light_schema(case_dir, fails, legacy=bool(a.legacy_read_only and schema in LEGACY_SCHEMAS))

    if fails:
        print("[verify] FAIL（fail-closed，逐条修复或退回 −1）:")
        for x in fails:
            print(f"  ✗ {x}")
        return 2
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

def cmd_freeze(a):
    case_dir = os.path.abspath(a.case_dir)
    path = os.path.join(case_dir, FREEZE_NAME)
    if a.check_unseal:
        if os.path.isfile(path):
            try:
                fz = load_json(path)
                if fz.get("members_sha256"):
                    print(f"[freeze] 已冻结（{fz.get('frozen_at_utc')}，成员表 {fz['members_sha256'][:12]}…）——允许揭盲/读 sealed")
                    return 0
            except Exception:
                pass
        print("[freeze] entity_freeze.json 不存在或无效——实体未冻结，禁止揭盲、禁止读 sealed/", file=sys.stderr)
        return 2

    if not a.members:
        print("[freeze] 需要 --members <成员表文件>（如 analysis-state.json）", file=sys.stderr)
        return 1
    mp = os.path.join(case_dir, a.members) if not os.path.isabs(a.members) else a.members
    if not os.path.isfile(mp):
        print(f"[freeze] 成员表不存在: {mp}", file=sys.stderr)
        return 2
    # 裁决闭环前置（v6.8.0，无跳过通道）：wave/flow 全部候选必须已按
    # candidate-adjudications/v1 成员级裁决并通过校验，否则禁止冻结实体——
    # "报警器响了没人管照样冻结"（W1 二次漏检的裁决未闭环缺口）从此机器堵死。
    # 旧案 revision 追加同样过此闸：改成员表＝新结论，必须先重跑 v2 扫描器补裁决。
    validator = os.path.join(os.path.dirname(os.path.abspath(__file__)), "adjudication_validator.py")
    pv = subprocess.run([sys.executable, validator, "validate", "--case-dir", case_dir],
                        capture_output=True, text=True)
    if pv.returncode != 0:
        print("[freeze] 候选裁决闭环未通过——禁止冻结（validator 输出如下）:", file=sys.stderr)
        sys.stderr.write(pv.stdout + pv.stderr)
        return 2
    # 溯源闸前置（v6.8.0 时序硬规则：临时实体表→溯源→补候选→重跑→最终冻结，
    # 不得先冻结再让溯源发现遗漏）：provenance_ledger.json 必须在场且闭合
    pl_path = os.path.join(case_dir, "provenance_ledger.json")
    if not os.path.isfile(pl_path):
        print("[freeze] 缺 provenance_ledger.json——先对临时实体表跑 entity_source_trace.py"
              "（溯源闸），新支路补候选回裁决环后再冻结", file=sys.stderr)
        return 2
    try:
        pl = load_json(pl_path)
        if pl.get("schema") != "provenance-ledger/v1" or not pl.get("entities"):
            print(f"[freeze] provenance_ledger.json schema/内容异常: {pl.get('schema')}，"
                  f"entities={len(pl.get('entities') or [])}", file=sys.stderr)
            return 2
        for ent in pl["entities"]:
            for anchor_name in ("current", "peak"):
                stock = int(ent["anchors"][anchor_name]["stock_raw"])
                s = ent["closure_check"][f"{anchor_name}_sum_pct"]
                if stock > 0 and abs(s - 100.0) > 0.5:
                    print(f"[freeze] 溯源闭合失败: {ent['entity_id']} {anchor_name} Σ={s}%", file=sys.stderr)
                    return 2
    except (KeyError, ValueError, TypeError) as e:
        print(f"[freeze] provenance_ledger.json 结构异常: {e}", file=sys.stderr)
        return 2
    algo, digest, size = sha256_file(mp)
    now = utcnow()
    entry = {"members_source": os.path.relpath(mp, case_dir), "members_sha256": digest,
             "frozen_at_utc": now, "pending_items": [x for x in (a.pending or "").split(";") if x],
             "casebook_note": a.casebook_note}
    if os.path.isfile(path):
        fz = load_json(path)
        if fz.get("members_sha256") == digest:
            print("[freeze] 成员表未变化，无需新 revision")
            return 0
        fz.setdefault("revisions", []).append(
            {k: fz[k] for k in ("members_source", "members_sha256", "frozen_at_utc", "pending_items", "casebook_note")
             if k in fz})
        fz.update(entry)
        atomic_write_json(path, fz)
        print(f"[freeze] revision #{len(fz['revisions'])} 追加（不覆盖历史）——新成员表 {digest[:12]}…")
        return 0
    fz = {"schema": "entity-freeze/v1", **entry, "revisions": []}
    atomic_write_json(path, fz)
    print(f"[freeze] 初次冻结 → {path}（成员表 {digest[:12]}…，未决项 {len(entry['pending_items'])}）")
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
    f.add_argument("--members", default=None, help="成员表文件（含实体成员名册）")
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
