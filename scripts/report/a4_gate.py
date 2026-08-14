#!/usr/bin/env python3
"""A4 对抗复核封口闸——claim 注册表全覆盖裁决 + 终版分析文件哈希封口，产 a4_seal.json。

痛点定位：A4→A5 之间此前无任何闸门（A2 有"四查全过才进分析"准入措辞与 exit-code
硬闸，A4 只有"必做"两个字）——历史 16 个时间戳可判定案 12 案图表/报告在复核完成前
落盘、其中 7 案因翻案实际返工（APU 报告写 3 遍、GOAT 阵营图 4 代、TROLL 旧轻量版
HTML 作废……2026-08-01 核查）。本闸把"A4 全部裁决落定"变成机器可验前置：
  register  A4 开工登记 claim 注册表（稳定 id；与 adversarial-review skill 的
            args.claims 及 split-run §3.3 外部异构路输入的 claim registry 同构）
  finalize  A4 收尾封口：裁决 id 集合与注册表**完全相等**（缺一条=有结论没复核，
            多一条=复核了没登记的结论，都拒）＋三档枚举合法＋WEAKENED/REFUTED 必带
            修订摘要＋registry/verdicts/findings/state/facts/identity/claim 引用文件逐个 sha256
            封口＋charts/final/ 必须为空（A5 尚未开始的物证）→ 产 a4_seal.json。
            build_html --a4-seal 编译时重算哈希校验（G9）：封口后再改结论不重封，
            报告物理上编不出来。翻案后重新修订＝改完再跑一次 finalize 重新封口。

mtime 不作裁决依据（cp -p 误伤 / touch 绕过，codex 复核否决）；封口一律哈希。

用法:
  python3 a4_gate.py register --case-dir <案目录> --claims-file <claims.json>
      # claims.json: [{"id": "C1", "text": "……", "files": [...]}, ...]
  python3 a4_gate.py finalize --case-dir <案目录> --verdicts-file <verdicts.json> \
      --workflow-type <new-analysis|independent-audit> \
      --seal-files findings.md,analysis-state.json,facts.json,identity_gate.json [--charts-dir charts/final]
      # verdicts.json: [{"id": "C1", "verdict": "CONFIRMED|WEAKENED|REFUTED",
      #                  "revision_note": "WEAKENED/REFUTED 必填"}, ...]

退出码: 0=封口成功 / 2=校验不过（硬停，修完重跑）/ 1=脚本自身错误。
（来源：A4 前提前做 A5 七案返工核查 + codex 交叉复核，2026-08-01）"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

CLAIMS_NAME = "a4_claims.json"
SEAL_NAME = "a4_seal.json"
VERDICTS = {"CONFIRMED", "WEAKENED", "REFUTED"}
WORKFLOW_TYPES = {"new-analysis", "independent-audit"}
MANDATORY_SEAL_FILES = {"findings.md", "analysis-state.json", "facts.json", "identity_gate.json"}


def utcnow():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(blk)
    return h.hexdigest()


def safe_case_file(case_dir, rel, must_exist=True):
    """Resolve a relative regular file inside case_dir; reject abs/.. and symlink escape."""
    if not isinstance(rel, str) or not rel.strip() or os.path.isabs(rel):
        raise ValueError(f"路径必须是案目录内相对路径: {rel!r}")
    raw = Path(rel)
    if ".." in raw.parts:
        raise ValueError(f"路径含 ..: {rel}")
    root = Path(case_dir).resolve()
    unresolved = root / raw
    if unresolved.is_symlink():
        raise ValueError(f"拒绝符号链接文件: {rel}")
    p = unresolved.resolve()
    try:
        p.relative_to(root)
    except ValueError:
        raise ValueError(f"路径越出案目录: {rel}")
    if must_exist and not p.is_file():
        raise ValueError(f"文件不存在、非普通文件或为符号链接: {rel}")
    return p


def validate_revision_chain(case_dir, seal):
    """逐级核对 A4 v4 归档链，旧版本或断链都拒收。"""
    errors = []
    seen = set()
    current = seal
    import audit_release_gate
    expected_chain = audit_release_gate.normalize_chain(current.get("chain"))
    chain_error = audit_release_gate.formal_chain_error(expected_chain)
    if chain_error:
        return [f"A4 seal 链不允许正式封口: {chain_error}"]
    expected_revision = current.get("revision")
    if not isinstance(expected_revision, int) or expected_revision < 1:
        return ["A4 seal revision 非正整数"]
    while True:
        if current.get("schema") != "a4-seal/v4" or current.get("revision") != expected_revision:
            errors.append("A4 revision 链 schema 或序号不连续")
            break
        current_chain = audit_release_gate.normalize_chain(current.get("chain"))
        if current_chain != expected_chain:
            errors.append(f"A4 revision 链 chain 漂移: {current_chain!r} != {expected_chain!r}")
            break
        previous = current.get("previous_seal")
        if expected_revision == 1:
            if previous is not None:
                errors.append("A4 revision 1 不得带 previous_seal")
            break
        if not isinstance(previous, dict) or previous.get("revision") != expected_revision - 1:
            errors.append("A4 revision 链缺上一版指针")
            break
        rel = previous.get("path")
        if rel in seen:
            errors.append("A4 revision 链出现循环")
            break
        seen.add(rel)
        try:
            path = safe_case_file(case_dir, rel)
            if sha256_file(path) != previous.get("sha256"):
                errors.append(f"A4 归档哈希漂移: {rel}")
                break
            current = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"A4 归档不可读: {exc}")
            break
        expected_revision -= 1
    return errors


def validate_formal_case_chain(case_dir):
    """A4 seals are formal artifacts; bind state and G8 to one formal chain."""
    errors = []
    root = Path(case_dir).resolve()
    try:
        state = json.loads(safe_case_file(root, "analysis-state.json").read_text(encoding="utf-8"))
        identity = json.loads(safe_case_file(root, "identity_gate.json").read_text(encoding="utf-8"))
    except Exception as exc:
        return None, [f"正式封口链资产不可读: {exc}"]
    import audit_release_gate
    state_chain = audit_release_gate.normalize_chain(
        state.get("chain") or (state.get("token") or {}).get("chain"))
    identity_chain = audit_release_gate.normalize_chain(identity.get("chain"))
    if not state_chain or not identity_chain:
        errors.append("analysis-state.json 或 identity_gate.json 缺 chain")
        return None, errors
    if state_chain != identity_chain:
        errors.append(f"正式封口链不一致: state={state_chain!r} identity={identity_chain!r}")
        return None, errors
    reason = audit_release_gate.formal_chain_error(state_chain)
    if reason:
        errors.append(reason)
        return None, errors
    return state_chain, errors


_ZERO_RENDERING_EXTRAS = {"\u3164", "\u115f", "\u1160", "\uffa0", "\u2800"}


def _norm_text(value):
    """Build a fail-closed reconciliation key without deleting unknown semantics."""
    normalized = unicodedata.normalize("NFC", str(value or ""))
    kept = []
    for char in normalized:
        category = unicodedata.category(char)
        if category in {"Cf", "Cc", "Zl", "Zp", "Mn", "Me"} \
                or char in _ZERO_RENDERING_EXTRAS:
            continue
        kept.append(" " if category == "Zs" else char)
    # The meaningful-text gate is an allowlist because an unknown character there
    # could make an empty shell pass.  Reconciliation keys need the opposite safety
    # direction: only known zero-rendering characters are denied, so an unknown
    # symbol/script remains visible and causes a fail-closed mismatch for review.
    return " ".join("".join(kept).split())


def check_audit_registry_alignment(case_dir, reg, verdicts, fails):
    """Bidirectionally align the A4 registry with the clean-room registry."""
    from adversarial_review_runner import _meaningful_text

    def claim_id(value):
        if not isinstance(value, str):
            return None
        stripped = value.strip()
        if not stripped or not all(_meaningful_text(char) for char in stripped):
            return None
        return stripped

    try:
        path = safe_case_file(case_dir, "claim_registry.json")
        audit = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fails.append(f"净室 claim_registry.json 不可读: {exc}")
        return None
    audit_claims = audit.get("claims")
    if not isinstance(audit_claims, list):
        fails.append("净室 claim_registry.json claims 非数组")
        return path
    a4_claims = reg.get("claims") if isinstance(reg, dict) else None
    if not isinstance(a4_claims, list):
        fails.append("a4_claims.json claims 非数组")
        return path
    a4_rows = [c for c in a4_claims if isinstance(c, dict)]
    audit_rows = [c for c in audit_claims if isinstance(c, dict)]
    verdict_rows = [v for v in verdicts if isinstance(v, dict)]
    a4_ids = [claim_id(c.get("id")) for c in a4_rows]
    audit_ids = [claim_id(c.get("claim_id")) for c in audit_rows]
    verdict_ids = [claim_id(v.get("id")) for v in verdict_rows]
    if any(cid is None for cid in a4_ids + audit_ids + verdict_ids):
        fails.append("A4/净室/verdict claim id 非法")
        return path
    a4_map = dict(zip(a4_ids, a4_rows))
    audit_map = dict(zip(audit_ids, audit_rows))
    verdict_map = {cid: str(row.get("verdict", "")).upper()
                   for cid, row in zip(verdict_ids, verdict_rows)}
    if len(audit_ids) != len(set(audit_ids)) or not all(audit_ids):
        fails.append("净室 claim_registry claim_id 缺失或重复")
    if set(a4_map) != set(audit_map):
        fails.append(f"两套 claim id 集合不一致: "
                     f"only_a4={sorted(set(a4_map)-set(audit_map))} "
                     f"only_audit={sorted(set(audit_map)-set(a4_map))}")
    for cid in sorted(set(a4_map) & set(audit_map)):
        left, right = a4_map[cid], audit_map[cid]
        if _norm_text(left.get("text")) != _norm_text(right.get("statement")):
            fails.append(f"claim {cid} 命题文本不一致")
        if set(map(str, left.get("files") or [])) != set(map(str, right.get("evidence_files") or [])):
            fails.append(f"claim {cid} 证据文件集合不一致")
        if set(map(str, left.get("report_locations") or [])) != \
                set(map(str, right.get("report_locations") or [])):
            fails.append(f"claim {cid} 报告位置集合不一致")
        if str(right.get("verdict", "")).upper() != verdict_map.get(cid):
            fails.append(f"claim {cid} 最终 verdict 不一致")
    return path


def validate_claim_rows(case_dir, claims):
    """Canonical validator shared by register and finalize; never trust stale registration."""
    if not isinstance(claims, list) or not claims:
        raise ValueError("claims 必须是非空数组")
    if any(not isinstance(c, dict) for c in claims):
        raise ValueError("claim 每项必须是对象")
    ids = [str(c.get("id", "")).strip() for c in claims]
    if any(not i for i in ids):
        raise ValueError("存在空 id 的 claim")
    if len(set(ids)) != len(ids):
        dup = sorted({i for i in ids if ids.count(i) > 1})
        raise ValueError(f"id 重复: {dup}")
    if any(not str(c.get("text", "")).strip() for c in claims):
        raise ValueError("存在空 text 的 claim")
    normalized = []
    for c in claims:
        files = []
        for rel in c.get("files") or []:
            safe_case_file(case_dir, rel)
            files.append(rel)
        locations = c.get("report_locations") or []
        if not isinstance(locations, list) or any(not isinstance(x, str) or not x.strip() for x in locations):
            raise ValueError(f"claim {c['id']} report_locations 必须是非空字符串数组")
        normalized.append({"id": str(c["id"]).strip(), "text": str(c["text"]).strip(),
                           "files": files, "report_locations": list(locations),
                           "claim_type": c.get("claim_type"),
                           "distribution_explanation": c.get("distribution_explanation")})
    return normalized


def distribution_claim_source(case_dir, workflow_type, claims, fails):
    """Return the current distribution claim source and close dist-* IDs bidirectionally."""
    if workflow_type != "new-analysis":
        return None
    scan_rel = "distribution_scan.json"
    expected_stage = "initial"
    rounds_path = Path(case_dir) / "distribution_rounds.json"
    if rounds_path.is_file():
        try:
            ledger = json.loads(rounds_path.read_text(encoding="utf-8"))
            rounds = ledger.get("rounds") or []
            if ledger.get("terminal") is not None:
                fails.append("distribution rounds 已到 terminal，禁止再次 A4 finalize")
                return None
            if rounds and ledger.get("terminal") is None:
                scan_rel = str(rounds[-1].get("final_scan_path"))
                expected_stage = "final"
        except Exception as exc:
            fails.append(f"distribution_rounds.json 不可读: {exc}")
    try:
        scan_path = safe_case_file(case_dir, scan_rel)
        scan_script = Path(__file__).with_name("holder_distribution_scan.py")
        pv = subprocess.run([sys.executable, str(scan_script), "validate", "--case-dir", case_dir,
                             "--scan", scan_rel, "--expected-stage", expected_stage],
                            capture_output=True, text=True)
        if pv.returncode != 0:
            fails.append("distribution scan 独立重算未通过: " + (pv.stdout + pv.stderr)[-800:])
            return None
        scan = json.loads(scan_path.read_text(encoding="utf-8"))
        expected = {f"dist-{x['cluster_id']}" for x in scan.get("abnormal_clusters", [])}
        actual = {str(x.get("id")) for x in claims if str(x.get("id", "")).startswith("dist-")}
        if expected != actual:
            fails.append(f"dist-* claims 与分布异常簇不闭合: missing={sorted(expected-actual)} "
                         f"extra={sorted(actual-expected)}")
        return {"path": scan_rel, "sha256": sha256_file(scan_path),
                "stage": expected_stage, "cluster_claim_ids": sorted(expected)}
    except Exception as exc:
        fails.append(f"distribution claim source 不可读: {exc}")
        return None


def cmd_register(a):
    case_dir = os.path.abspath(a.case_dir)
    try:
        claims = json.load(open(a.claims_file, encoding="utf-8"))
    except Exception as e:
        print(f"[register] claims 文件读取失败: {e}", file=sys.stderr)
        return 1
    try:
        normalized = validate_claim_rows(case_dir, claims)
    except ValueError as e:
        print(f"[register] {e}", file=sys.stderr)
        return 2
    reg = {"schema": "a4-claims/v2", "registered_at_utc": utcnow(),
           "claims": normalized}
    path = os.path.join(case_dir, CLAIMS_NAME)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=1)
    print(f"[register] {len(claims)} 条 claim 登记 → {path}")
    return 0


def cmd_finalize(a):
    case_dir = os.path.abspath(a.case_dir)
    reg_path = os.path.join(case_dir, CLAIMS_NAME)
    if not os.path.isfile(reg_path):
        print(f"[finalize] 缺 {CLAIMS_NAME}——A4 开工必须先 register 登记结论清单", file=sys.stderr)
        return 2
    try:
        reg = json.load(open(reg_path, encoding="utf-8"))
        verdicts = json.load(open(a.verdicts_file, encoding="utf-8"))
    except Exception as e:
        print(f"[finalize] 输入读取失败: {e}", file=sys.stderr)
        return 1

    fails = []
    case_chain, chain_errors = validate_formal_case_chain(case_dir)
    fails.extend(chain_errors)
    if not isinstance(reg, dict) or reg.get("schema") != "a4-claims/v2":
        fails.append("a4_claims.json schema 必须为 a4-claims/v2")
        claims = []
    else:
        try:
            claims = validate_claim_rows(case_dir, reg.get("claims"))
            reg["claims"] = claims
        except ValueError as exc:
            fails.append(str(exc))
            claims = []
    reg_ids = {c["id"] for c in claims}
    if not isinstance(verdicts, list):
        print("[finalize] verdicts 必须是数组", file=sys.stderr)
        return 2
    v_ids = [str(v.get("id", "")).strip() for v in verdicts]
    if len(set(v_ids)) != len(v_ids):
        fails.append(f"verdict id 重复: {sorted({i for i in v_ids if v_ids.count(i) > 1})}")
    missing = sorted(reg_ids - set(v_ids))
    extra = sorted(set(v_ids) - reg_ids)
    if missing:
        fails.append(f"未裁决的 claim（有结论没复核，禁封口）: {missing}")
    if extra:
        fails.append(f"裁决了未登记的 claim（复核对象漂移，先补 register）: {extra}")
    for v in verdicts:
        vd = str(v.get("verdict", "")).strip().upper()
        if vd not in VERDICTS:
            fails.append(f"claim {v.get('id')} verdict 非法: {v.get('verdict')}（必须 {sorted(VERDICTS)}，"
                         "'理论上可能'不算推翻——必须实际核查后三选一）")
        elif vd in ("WEAKENED", "REFUTED") and not str(v.get("revision_note", "")).strip():
            fails.append(f"claim {v.get('id')} 判 {vd} 但无 revision_note——翻案必须写修订摘要（改了什么、改后结论）")

    audit_registry_path = None
    if a.workflow_type == "independent-audit":
        audit_registry_path = check_audit_registry_alignment(case_dir, reg, verdicts, fails)

    distribution_source = distribution_claim_source(case_dir, a.workflow_type, claims, fails)

    seal_files = {x.strip() for x in (a.seal_files or "").split(",") if x.strip()}
    seal_files |= MANDATORY_SEAL_FILES
    if audit_registry_path is not None:
        seal_files.add("claim_registry.json")
    if distribution_source is not None:
        seal_files.add(distribution_source["path"])
    claim_files = {str(rel) for c in reg.get("claims", []) for rel in (c.get("files") or [])}
    seal_files |= claim_files
    sealed = []
    for rel in sorted(seal_files):
        try:
            p = safe_case_file(case_dir, rel)
        except ValueError as e:
            fails.append(f"待封口文件非法: {e}")
            continue
        sealed.append({"path": rel, "sha256": sha256_file(p)})

    try:
        verdict_path = safe_case_file(case_dir, os.path.relpath(a.verdicts_file, case_dir))
        verdict_rel = str(verdict_path.relative_to(Path(case_dir).resolve()))
    except ValueError as e:
        fails.append(f"verdicts 文件非法: {e}")
        verdict_rel = None

    charts_dir = a.charts_dir
    try:
        cd_abs = safe_case_file(case_dir, charts_dir, must_exist=False)
        if cd_abs.exists() and (not cd_abs.is_dir() or cd_abs.is_symlink()):
            raise ValueError(f"charts_dir 非普通目录或为符号链接: {charts_dir}")
    except ValueError as e:
        fails.append(str(e))
        cd_abs = Path(case_dir) / "__invalid_charts__"
    if os.path.isdir(cd_abs):
        residue = [x for x in os.listdir(cd_abs) if not x.startswith(".")]
        if residue:
            fails.append(f"{charts_dir}/ 非空（{len(residue)} 件，如 {residue[0]}）——A5 报告图只准在封口后"
                         f"生成到该目录；封口前它必须为空（提前画的草稿图挪出去或删除后重跑；"
                         f"翻案重封同理：目录里的旧图基于被推翻的结论已作废，清空重封后重画）")

    if fails:
        print("[finalize] FAIL（逐条修复后重跑，翻案后重新 finalize 即重新封口）:", file=sys.stderr)
        for x in fails:
            print(f"  ✗ {x}", file=sys.stderr)
        return 2

    counts = {}
    for v in verdicts:
        vd = str(v["verdict"]).strip().upper()
        counts[vd] = counts.get(vd, 0) + 1
    old_path = Path(case_dir) / SEAL_NAME
    revision = 1
    previous = None
    if old_path.is_file():
        try:
            old = json.loads(old_path.read_text(encoding="utf-8"))
            if old.get("schema") == "a4-seal/v4":
                chain_errors = validate_revision_chain(case_dir, old)
                if chain_errors:
                    raise ValueError("; ".join(chain_errors))
                revision = int(old.get("revision", 0)) + 1
                archive_rel = f"a4_seals/revision_{revision - 1}.json"
                archive = Path(case_dir) / archive_rel
                archive.parent.mkdir(parents=True, exist_ok=True)
                if archive.exists() and sha256_file(archive) != sha256_file(old_path):
                    raise ValueError("A4 revision 归档已存在但内容不同")
                if not archive.exists():
                    shutil.copyfile(old_path, archive)
                previous = {"path": archive_rel, "sha256": sha256_file(archive),
                            "revision": revision - 1}
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            print(f"[finalize] 旧 A4 seal revision 链不可用: {exc}", file=sys.stderr)
            return 2
    seal = {"schema": "a4-seal/v4", "gate": "a4_gate", "verdict": "PASS", "exit_code": 0,
            "chain": case_chain,
            "workflow_type": a.workflow_type,
            "revision": revision, "previous_seal": previous,
            "sealed_at_utc": utcnow(),
            "registry": {"path": CLAIMS_NAME, "sha256": sha256_file(reg_path)},
            "verdicts": {"path": verdict_rel, "sha256": sha256_file(verdict_path)},
            "claims": [{"id": str(v["id"]).strip(),
                        "verdict": str(v["verdict"]).strip().upper(),
                        "revision_note": str(v.get("revision_note", "")).strip() or None}
                       for v in verdicts],
            "counts": counts, "sealed_files": sealed, "claim_files": sorted(claim_files),
            "charts_dir": charts_dir, "distribution_claim_source": distribution_source}
    path = os.path.join(case_dir, SEAL_NAME)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(seal, f, ensure_ascii=False, indent=1)
    print(f"[finalize] 封口 PASS  {len(verdicts)} 条裁决（{json.dumps(counts, ensure_ascii=False)}）  "
          f"{len(sealed)} 件终版文件哈希封口 → {path}")
    print(f"[finalize] 现在可进 A5：图一律输出到 {charts_dir}/，编译带 --a4-seal {SEAL_NAME}；"
          "封口后再改结论文件必须改完重跑 finalize")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="subcmd", required=True)
    r = sub.add_parser("register", help="A4 开工登记 claim 注册表")
    r.add_argument("--case-dir", required=True)
    r.add_argument("--claims-file", required=True)
    f = sub.add_parser("finalize", help="A4 收尾封口（全覆盖裁决+哈希封口+final 目录空检查）")
    f.add_argument("--case-dir", required=True)
    f.add_argument("--verdicts-file", required=True)
    f.add_argument("--seal-files", required=True,
                   help="逗号分隔终版分析文件（相对案目录），如 findings.md,analysis-state.json")
    f.add_argument("--charts-dir", default="charts/final",
                   help="A5 报告图专用目录（封口时必须为空；默认 charts/final）")
    f.add_argument("--workflow-type", choices=sorted(WORKFLOW_TYPES), required=True,
                   help="不可变发布轨道：全新分析或净室复核")
    a = ap.parse_args()
    try:
        return {"register": cmd_register, "finalize": cmd_finalize}[a.subcmd](a)
    except Exception as e:
        print(f"[{a.subcmd}] 脚本自身错误（exit 1，修完重跑）: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
