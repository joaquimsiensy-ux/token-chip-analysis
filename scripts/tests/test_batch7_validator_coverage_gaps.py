#!/usr/bin/env python3
"""批7 回归：修复代深验(validate_repair_bundle_deep)三处校验覆盖缺口的加固。

缺口1(主)：formal 逐 slot 严格校验的遍历主键原本只绑定 coverage 候选集，而修复边
           准入只查 `slot in confirmed`(census 自报)。当 confirmed 的 slot 不在候选集
           内时严格校验被整段跳过，凭空修复边即可通过深验、被合并抬高余额/供应。
           加固：formal 遍历主键 = 候选集 ∪ census 确认集 ∪ 修复层各 slot，并加反向
           包含 confirmed ⊆ 候选集、干净 verdict 零修复边、formal 拒 exploration 指纹、
           ledger 请求数 ≥ 修复 slot 数。exploration 探索代豁免(不进正式发布路径)。
缺口3：深验/reconcile 均不校验"边 slot ⊆ 声明窗口"，slot>声明 upper 的边可被夹带。
       加固：深验补 merged 边 slot ⊆ coverage 窗口[from,to] 且 upper==base.finalized_upper。

缺口2(自扫 coverage 无真实性复查)判定为离线 validator 的固有信任边界(无外部锚点、
禁联网无法复制复用路径的实时 canary recheck)，裁定见 batch7_done.md，本文件不做断言。

每个回归同时验证：合法 formal 代仍放行(不误伤) + 对应篡改代被拒(加固生效)。
先红证据(加固前篡改代 ok=True)见 batch7_green_evidence.txt。
"""
from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
from pathlib import Path

import test_sqd_gap_repair as T
from scripts.solana import sqd_gap_repair as repair
from scripts.lib import solana_exact_validate as exact

MINT, CURVE = T.MINT, T.CURVE


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _missing_tx(slot):
    """AdvanceNonce durable-nonce 交易，产生一条 A->CurveOwner 50 的修复边。"""
    return {
        "transaction": {"signatures": [f"MissingOrderingSignature{slot}"],
            "message": {"accountKeys": ["AccountA", "AccountCurve"],
                "instructions": [{"programId": "11111111111111111111111111111111",
                                  "data": "5"}]}},
        "meta": {"err": None, "loadedAddresses": {},
            "preTokenBalances": [
                {"accountIndex": 0, "mint": MINT, "owner": "A",
                 "uiTokenAmount": {"amount": "50"}},
                {"accountIndex": 1, "mint": MINT, "owner": CURVE,
                 "uiTokenAmount": {"amount": "0"}}],
            "postTokenBalances": [
                {"accountIndex": 0, "mint": MINT, "owner": "A",
                 "uiTokenAmount": {"amount": "0"}},
                {"accountIndex": 1, "mint": MINT, "owner": CURVE,
                 "uiTokenAmount": {"amount": "50"}}]}}


def _build_formal_generation(root, slot=19_999):
    base_rows = [[1_700_000_000, slot, 0, -1, CURVE, "B", 100]]
    case = T.build_batch3b_case(root, {slot}, base_rows)
    fixture = T.write_repair_fixture(root / "repair-fixture",
        T.repair_slot_responses(repair, slot, _missing_tx(slot),
                                nonce_count=0, missing_first=True))
    assert repair.main(["repair", "--mint", MINT, "--case-root", str(case),
                        "--transport-fixture", str(fixture)]) == 0
    key = hashlib.sha256(MINT.encode()).hexdigest()
    parent = case / f"data/sqd_repair/{key}"
    gid = json.loads((parent / "CURRENT.json").read_text())["gid"]
    return case, parent, parent / f"gen-{gid}"


def gap1_regression():
    """遍历主键缺口：注入 confirmed slot(不在候选集)+凭空修复边，须被拒。"""
    slot, inj_slot = 19_999, 15_000
    inj_sig = "AAAInjectedSignature15000"          # 'A'<'M' 保证 layer signature 升序
    inj_edge = [1_700_015_000, inj_slot, 0, -1, "EVILATTACKER", "VICTIMTREASURY", 999999]
    with tempfile.TemporaryDirectory(prefix="b7-gap1-", dir="/private/tmp") as td:
        root = Path(td)
        case, parent, gen = _build_formal_generation(root, slot)
        bundle = json.loads((gen / "bundle.json").read_text())
        base_edge = case / bundle["base"]["edge_file"]
        cur = {"edge_sha256": sha256_file(base_edge)}

        baseline = exact.validate_repair_bundle_deep(
            gen / "bundle.json", case_root=case, current_base=cur)
        if not baseline["ok"]:
            print(f"RED gap1 baseline formal 合法代被误伤: {baseline['reasons']}")
            return 1

        # (a) repair_layer.jsonl：header + 注入行(A) + 合法行(M)，按 signature 升序
        layer_lines = (gen / "repair_layer.jsonl").read_text().splitlines()
        header, legit = json.loads(layer_lines[0]), json.loads(layer_lines[1])
        inj_layer = {"class": "other", "edges": [inj_edge], "evidence": {},
                     "nonce": False, "nonvote_ordinal": 0, "reference_position": 0,
                     "signature": inj_sig, "slot": inj_slot}
        new_layer_rows = [inj_layer, legit]
        (gen / "repair_layer.jsonl").write_text(
            json.dumps(header, ensure_ascii=False) + "\n"
            + "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in new_layer_rows),
            encoding="utf-8")

        # (b) coverage_resolution.json：census 加注入 confirmed 行；候选集/verdict 不变
        res = json.loads((gen / "coverage_resolution.json").read_text())
        res["census"] = res["census"] + [{
            "slot": inj_slot, "result": "confirmed_injected",
            "coverage_state": "DEFECT_CANDIDATE", "sqd_nonce_count_at_repair": 0}]
        (gen / "coverage_resolution.json").write_text(
            json.dumps(res, ensure_ascii=False, sort_keys=True), encoding="utf-8")

        # (c) merged edge = base(remapped) + repair_edges(含注入)，_edge_sort 排序
        merged_rows = sorted([
            [1_700_000_000, slot, 1, -1, CURVE, "B", 100],
            [1_700_019_999, slot, 0, -1, "A", CURVE, 50], inj_edge],
            key=exact._edge_sort)
        merged_edge = gen / bundle["merged"]["edge_file"]
        merged_edge.write_bytes(gzip.compress(
            "".join(json.dumps(r, ensure_ascii=False) + "\n"
                    for r in merged_rows).encode(), mtime=0))
        logical_sha, logical_rows = exact._edge_evidence([tuple(r) for r in merged_rows])

        # (d) merged meta
        mm_path = gen / bundle["merged"]["meta_file"]
        mm = json.loads(mm_path.read_text())
        mm.update({"edge_logical_sha256": logical_sha, "edge_rows": logical_rows,
                   "edge_file_sha256": sha256_file(merged_edge),
                   "edge_file_size": merged_edge.stat().st_size})
        mm_path.write_text(json.dumps(mm), encoding="utf-8")

        # (e) 重算 gid（census/transactions 变了）
        maps = [json.loads(x) for x in
                (gen / "slot_index_map.jsonl").read_text().splitlines()][1:]
        manifest = json.loads((gen / bundle["evidence_manifest"]["path"]).read_text())
        new_gid = exact._repair_gid({
            "plan_digest": bundle["plan_digest"], "kind": "repair",
            "supersedes": bundle["supersedes"], "census": res["census"],
            "transactions": new_layer_rows, "slot_index_map": maps,
            "evidence_manifest": manifest, "mode": bundle["mode"],
            "reference": {"source": bundle["reference"]["source"]}})

        # (f) 更新 bundle 各 ref
        cr = gen / "coverage_resolution.json"
        rl = gen / "repair_layer.jsonl"
        bundle["coverage_resolution"] = {
            "path": "coverage_resolution.json", "size": cr.stat().st_size,
            "sha256": sha256_file(cr)}
        bundle["repair_layer"] = {
            "path": "repair_layer.jsonl", "size": rl.stat().st_size,
            "sha256": sha256_file(rl), "transactions": 2, "edges": 2}
        bundle["merged"].update({
            "edge_sha256": sha256_file(merged_edge), "edge_logical_sha256": logical_sha,
            "edge_rows": logical_rows, "meta_sha256": sha256_file(mm_path)})
        bundle["gid"] = new_gid
        (gen / "bundle.json").write_text(json.dumps(bundle, ensure_ascii=False),
                                         encoding="utf-8")

        # (g) 目录改名 gen-{new_gid}
        new_gen = parent / f"gen-{new_gid}"
        gen.rename(new_gen)

        tampered = exact.validate_repair_bundle_deep(
            new_gen / "bundle.json", case_root=case, current_base=cur)
        if tampered["ok"]:
            print("RED gap1 遍历主键缺口未加固：凭空注入边(15000)通过深验 ok=True")
            return 1
        if not any("escape candidate set" in r for r in tampered["reasons"]):
            print(f"RED gap1 拒收但缺预期理由: {tampered['reasons']}")
            return 1
        print(f"GREEN gap1 遍历主键缺口已加固：合法代放行 + 凭空注入边被拒 "
              f"(edge_rows tampered={tampered['edge_rows']}) "
              f"reasons0={tampered['reasons'][0]}")
        return 0


def gap3_regression():
    """边-slot 窗口缺口：base 边追加 slot>声明 upper 的边，须被拒。"""
    slot, out_slot = 19_999, 25_000
    out_edge = [1_700_025_000, out_slot, 0, -1, "OUTWINDOWSRC", "OUTWINDOWDST", 777]
    with tempfile.TemporaryDirectory(prefix="b7-gap3-", dir="/private/tmp") as td:
        root = Path(td)
        case, parent, gen = _build_formal_generation(root, slot)
        bundle = json.loads((gen / "bundle.json").read_text())
        base_edge = case / bundle["base"]["edge_file"]

        baseline = exact.validate_repair_bundle_deep(
            gen / "bundle.json", case_root=case,
            current_base={"edge_sha256": sha256_file(base_edge)})
        if not baseline["ok"]:
            print(f"RED gap3 baseline 合法代被误伤: {baseline['reasons']}")
            return 1

        # base 边追加超声明窗口(upper=19999)的边
        with gzip.open(base_edge, "rt") as h:
            base_now = [json.loads(x) for x in h if x.strip()]
        new_base = base_now + [out_edge]
        base_edge.write_bytes(gzip.compress(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in new_base).encode(),
            mtime=0))
        new_base_phys = sha256_file(base_edge)
        new_base_logical, new_base_rows = exact._edge_evidence(
            [tuple(r) for r in new_base])
        base_meta = case / bundle["base"]["meta_file"]
        bm = json.loads(base_meta.read_text())
        bm.update({"edge_logical_sha256": new_base_logical, "edge_rows": new_base_rows})
        base_meta.write_text(json.dumps(bm), encoding="utf-8")

        merged_rows = sorted([
            [1_700_000_000, slot, 1, -1, CURVE, "B", 100], out_edge,
            [1_700_019_999, slot, 0, -1, "A", CURVE, 50]], key=exact._edge_sort)
        merged_edge = gen / bundle["merged"]["edge_file"]
        merged_edge.write_bytes(gzip.compress(
            "".join(json.dumps(r, ensure_ascii=False) + "\n"
                    for r in merged_rows).encode(), mtime=0))
        mlog, mrows = exact._edge_evidence([tuple(r) for r in merged_rows])
        mm_path = gen / bundle["merged"]["meta_file"]
        mm = json.loads(mm_path.read_text())
        mm.update({"edge_logical_sha256": mlog, "edge_rows": mrows,
                   "edge_file_sha256": sha256_file(merged_edge),
                   "edge_file_size": merged_edge.stat().st_size,
                   "base_edge_sha256": new_base_phys})
        mm_path.write_text(json.dumps(mm), encoding="utf-8")
        # base 不进 gid_material，无需改 gid / 目录名
        bundle["base"].update({
            "edge_sha256": new_base_phys, "edge_logical_sha256": new_base_logical,
            "edge_rows": new_base_rows, "meta_sha256": sha256_file(base_meta)})
        bundle["merged"].update({
            "edge_sha256": sha256_file(merged_edge), "edge_logical_sha256": mlog,
            "edge_rows": mrows, "meta_sha256": sha256_file(mm_path)})
        (gen / "bundle.json").write_text(json.dumps(bundle, ensure_ascii=False),
                                         encoding="utf-8")

        tampered = exact.validate_repair_bundle_deep(
            gen / "bundle.json", case_root=case,
            current_base={"edge_sha256": new_base_phys})
        if tampered["ok"]:
            print(f"RED gap3 边-slot 窗口缺口未加固：slot={out_slot}>upper=19999 通过深验")
            return 1
        if not any("escapes declared coverage window" in r for r in tampered["reasons"]):
            print(f"RED gap3 拒收但缺预期理由: {tampered['reasons']}")
            return 1
        print(f"GREEN gap3 边-slot 窗口缺口已加固：合法代放行 + slot={out_slot} 超窗口边被拒 "
              f"reasons={tampered['reasons']}")
        return 0


def main():
    red = 0
    red += gap1_regression()
    red += gap3_regression()
    if red:
        print(f"{red} 项 RED —— 缺口加固回归失败")
    else:
        print("批7 validator 覆盖缺口加固回归全部 GREEN (缺口1遍历主键 + 缺口3边slot窗口)")
    return red


if __name__ == "__main__":
    import sys
    sys.exit(main())
