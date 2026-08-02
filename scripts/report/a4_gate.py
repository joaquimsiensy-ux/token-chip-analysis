#!/usr/bin/env python3
"""A4 对抗复核封口闸——claim 注册表全覆盖裁决 + 终版分析文件哈希封口，产 a4_seal.json。

痛点定位：A4→A5 之间此前无任何闸门（A2 有"四查全过才进分析"准入措辞与 exit-code
硬闸，A4 只有"必做"两个字）——历史 16 个时间戳可判定案 12 案图表/报告在复核完成前
落盘、其中 7 案因翻案实际返工（APU 报告写 3 遍、GOAT 阵营图 4 代、TROLL easy 版
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
      --seal-files findings.md,analysis-state.json,facts.json,identity_gate.json [--charts-dir charts/final]
      # verdicts.json: [{"id": "C1", "verdict": "CONFIRMED|WEAKENED|REFUTED",
      #                  "revision_note": "WEAKENED/REFUTED 必填"}, ...]

退出码: 0=封口成功 / 2=校验不过（硬停，修完重跑）/ 1=脚本自身错误。
（来源：A4 前提前做 A5 七案返工核查 + codex 交叉复核，2026-08-01）"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

CLAIMS_NAME = "a4_claims.json"
SEAL_NAME = "a4_seal.json"
VERDICTS = {"CONFIRMED", "WEAKENED", "REFUTED"}
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


def cmd_register(a):
    case_dir = os.path.abspath(a.case_dir)
    try:
        claims = json.load(open(a.claims_file, encoding="utf-8"))
    except Exception as e:
        print(f"[register] claims 文件读取失败: {e}", file=sys.stderr)
        return 1
    if not isinstance(claims, list) or not claims:
        print("[register] claims 必须是非空数组——A4 没有结论可复核＝A3 没产出，先回 A3", file=sys.stderr)
        return 2
    ids = [str(c.get("id", "")).strip() for c in claims]
    if any(not i for i in ids):
        print("[register] 存在空 id 的 claim——每条结论必须有稳定 id", file=sys.stderr)
        return 2
    if len(set(ids)) != len(ids):
        dup = sorted({i for i in ids if ids.count(i) > 1})
        print(f"[register] id 重复: {dup}", file=sys.stderr)
        return 2
    if any(not str(c.get("text", "")).strip() for c in claims):
        print("[register] 存在空 text 的 claim", file=sys.stderr)
        return 2
    normalized = []
    try:
        for c in claims:
            files = []
            for rel in c.get("files") or []:
                safe_case_file(case_dir, rel)
                files.append(rel)
            normalized.append({"id": str(c["id"]).strip(), "text": str(c["text"]).strip(),
                               "files": files})
    except ValueError as e:
        print(f"[register] claim 引用文件非法: {e}", file=sys.stderr)
        return 2
    reg = {"schema": "a4-claims/v1", "registered_at_utc": utcnow(),
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
    reg_ids = {c["id"] for c in reg.get("claims", [])}
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

    seal_files = {x.strip() for x in (a.seal_files or "").split(",") if x.strip()}
    seal_files |= MANDATORY_SEAL_FILES
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
    seal = {"schema": "a4-seal/v2", "gate": "a4_gate", "verdict": "PASS", "exit_code": 0,
            "sealed_at_utc": utcnow(),
            "registry": {"path": CLAIMS_NAME, "sha256": sha256_file(reg_path)},
            "verdicts": {"path": verdict_rel, "sha256": sha256_file(verdict_path)},
            "claims": [{"id": str(v["id"]).strip(),
                        "verdict": str(v["verdict"]).strip().upper(),
                        "revision_note": str(v.get("revision_note", "")).strip() or None}
                       for v in verdicts],
            "counts": counts, "sealed_files": sealed, "claim_files": sorted(claim_files),
            "charts_dir": charts_dir}
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
    a = ap.parse_args()
    try:
        return {"register": cmd_register, "finalize": cmd_finalize}[a.subcmd](a)
    except Exception as e:
        print(f"[{a.subcmd}] 脚本自身错误（exit 1，修完重跑）: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
