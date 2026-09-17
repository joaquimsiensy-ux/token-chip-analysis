# 施工 C：完成

按 workorder_C.md v3 执行，开工及完工 HEAD 均为 8dea1ab。C1–C6 已完成；指定 13 个测试与 invariant_scan.py 最终均 exit 0。未 commit、push 或部署。

## ① 开工基线

以下两条命令已在任何写入前实际运行，均 exit 0。git status --short 的 stdout 为空：

```console
$ git status --short

$ git rev-parse --short HEAD
8dea1ab
```

工单文件头为 v3。39 个 grep -n -F 锚点均恰好一处且指定行号一致；白名单源码 git diff --stat 8ead156 HEAD -- <白名单源码及文档> 输出为空。开工字节数：SKILL.md=8021、commands-staging=8798、references=930070。

## ② C1/C2/C3 diff 原文

C1：新增纯函数 derive_facts 与 build 分派；严格 JSON、三账非空及闭合、峰值来源与证据绑定、既有 gate 自检、确定性原子输出。C2：facts.json 纳入 new-analysis 必需件，逐字段重算，函数开头先执行 regular_case_path 拒绝符号链接/越界。C3：facts_gate 后追加 facts_vs_ledgers，收口由 11 项增至 12 项。

```diff
diff --git a/scripts/report/audit_release_gate.py b/scripts/report/audit_release_gate.py
index 340e742..ced419f 100644
--- a/scripts/report/audit_release_gate.py
+++ b/scripts/report/audit_release_gate.py
@@ -49,6 +49,8 @@ NEW_ANALYSIS_REQUIRED = (
     # F-C5：图 2 末点对账留痕收据（figures_from_facts check 每跑必写）——
     # 发布闸复验 mode==formal、tol_pp==默认、verdict==PASS
     "figure2_check_receipt.json",
+    # R07（7.2.0）：facts.json 必须由 facts_gate build 从三账生成，发布闸重算比对
+    "facts.json",
 )
 LEGACY_READONLY_RECEIPT = "legacy_readonly_receipt.json"
 REQUIRED_BY_PROFILE = {
@@ -1341,6 +1343,7 @@ def check_distribution_snapshot_binding(case_dir: Path, data: dict, chain, error
 
 FIGURE2_RECEIPT_SCHEMA = "figure2-check-receipt/v1"
 FIGURE2_DEFAULT_TOL_PP = 0.05
+FACTS_PROVENANCE_SCHEMA = "facts-provenance/v1"
 
 
 def _figure2_input_check(case_dir: Path, ref, label: str, errors: list[str]):
@@ -1365,6 +1368,60 @@ def _figure2_input_check(case_dir: Path, ref, label: str, errors: list[str]):
                       "不一致——收据不是对当前案内文件跑出来的")
 
 
+def check_facts_vs_ledgers(case_dir: Path, facts, errors: list[str], receipt=None):
+    """R07（7.2.0）：facts.json 必须是 facts_gate build 从三账生成的产物——
+    验 provenance 绑定块（schema/binding/mode=formal），再用 facts_gate.derive_facts 按案内
+    三账＋identity_gate＋provenance_ledger＋state_source 重算，与落盘 facts 逐字段比对
+    （producer.sha256 只记录不比对；inputs/state_source/evidence 的 sha 由重算侧复核）。
+    receipt＝figure2 对账收据（给了就验其 facts 绑定的是本名 facts.json，防另名 facts 绕开）。"""
+    if regular_case_path(case_dir, "facts.json") is None:
+        errors.append("facts.json 不是案根常规文件（符号链接/越界）")
+        return
+    if isinstance(receipt, dict):
+        bound = Path(str((receipt.get("facts") or {}).get("path") or "")).name
+        if bound != "facts.json":
+            errors.append(f"figure2 收据绑定的 facts 是 {bound!r}——必须是案根 facts.json（三账重算比对的对象）")
+    if not isinstance(facts, dict):
+        errors.append("facts.json 顶层必须是对象")
+        return
+    prov = facts.get("provenance")
+    if not isinstance(prov, dict):
+        errors.append("facts.json 缺 provenance 绑定块——须由 facts_gate.py build 从三账生成，禁手写")
+        return
+    if prov.get("schema") != FACTS_PROVENANCE_SCHEMA:
+        errors.append(f"facts.provenance.schema 必须是 {FACTS_PROVENANCE_SCHEMA}")
+    if prov.get("facts_binding") != "ledger-derived":
+        errors.append("facts.provenance.facts_binding 必须是 ledger-derived")
+    if prov.get("mode") != "formal":
+        errors.append(f"facts.provenance.mode={prov.get('mode')!r}——exploration 构建不得进正式发布")
+        return
+    try:
+        import facts_gate
+        rebuilt = facts_gate.derive_facts(case_dir, exploration=False)
+    except (KeyError, ValueError, OSError, TypeError) as exc:
+        errors.append(f"facts 按三账重算失败: {exc}")
+        return
+    got, want = dict(facts), dict(rebuilt)
+    got_prov, want_prov = dict(got.pop("provenance") or {}), dict(want.pop("provenance") or {})
+    got_prov.pop("producer", None)
+    want_prov.pop("producer", None)
+    for key in sorted(set(got) | set(want)):
+        if key == "entities":
+            continue
+        if got.get(key) != want.get(key):
+            errors.append(f"facts.{key} 与三账重算值不一致")
+    ge, we = got.get("entities") or {}, want.get("entities") or {}
+    if set(ge) != set(we):
+        errors.append(f"facts 实体集合与三账不一致: 多 {sorted(set(ge) - set(we))[:3]} "
+                      f"少 {sorted(set(we) - set(ge))[:3]}")
+    for eid in sorted(set(ge) & set(we)):
+        if ge[eid] != we[eid]:
+            diff = sorted(k for k in set(ge[eid]) | set(we[eid]) if ge[eid].get(k) != we[eid].get(k))
+            errors.append(f"facts 实体 {eid} 字段 {diff[:4]} 与三账重算值不一致")
+    if got_prov != want_prov:
+        errors.append("facts.provenance（inputs/state_source/peak_overrides 的 sha 或绑定）与当前案内实物不一致——输入已变，须重新 build")
+
+
 def check_figure2_receipt(case_dir: Path, d: dict, errors: list[str]):
     """F-C5：图 2 末点对账收据复验（new-analysis 必经）。
 
@@ -1643,6 +1700,10 @@ def _run(case_dir: Path, report: Path | None, *, profile="independent-audit"):
         # F-C5/F-C1（批 C 消化轮）：图 2 对账收据复验＋阵营序列 producer 绑定复验
         if profile == "new-analysis" and "figure2_check_receipt.json" in data:
             check_figure2_receipt(case_dir, data["figure2_check_receipt.json"], errors)
+        # R07（7.2.0）：facts.json（new-analysis 必需件，已随 required 装载）按三账重算复核
+        if profile == "new-analysis" and "facts.json" in data:
+            check_facts_vs_ledgers(case_dir, data["facts.json"], errors,
+                                   receipt=data.get("figure2_check_receipt.json"))
         state_path = case_dir / "analysis-state.json"
         if state_path.is_file():
             state_obj = load_json(state_path, errors)
diff --git a/scripts/report/facts_gate.py b/scripts/report/facts_gate.py
index 22d30a0..bf8d4a9 100644
--- a/scripts/report/facts_gate.py
+++ b/scripts/report/facts_gate.py
@@ -5,7 +5,7 @@
 报告 md 里写宏引用，本模块渲染+语义 gate：正文数字、附录 B、analysis-state.json 三处
 永远同源；改一处数据其余处必然跟着变，对不上编译直接失败（fail-closed）。
 
-facts.json schema（每案一份，阶段 3 结束时从落盘数据构建；数值一律**原始整数字符串**）：
+facts.json schema（每案一份，阶段 3 结束时由 build 子命令从三账生成，禁手抄；数值一律**原始整数字符串**）：
 {
   "token": {"symbol": "QUQ", "decimals": 18, "total_supply_raw": "1000...0"},
   "entities": {
@@ -57,11 +57,25 @@ entity_id 匹配**，label 只是展示文案（改措辞不再断链路）；
 
 用法（库 + CLI 双形态；build_html.py --facts 参数内部调用）：
   python3 facts_gate.py --facts facts.json --state analysis-state.json   # 纯校验
+  python3 facts_gate.py build [--case-dir .] [--source state_source.json] [--out facts.json] [--exploration]
+      # 从三账＋identity_gate＋provenance_ledger＋state_source.facts_inputs 生成 facts.json（7.2.0，R07）
+state_source.facts_inputs schema：
+  symbol: str（必填）；decimals: int≥0（必填）
+  entity_labels: {eid: label}（必填、非空、覆盖全部实体）
+  peak_overrides: {eid: {peak_raw, peak_date, evidence: {path, sha256, note?}}}
+      （可选，优先于 provenance 锚点，证据须为案根常规文件）
+  merge_evidence: {eid: {earliest, note}}（可选）
+  role_notes: {eid: {addr: note}}（可选）
+  metrics: {}（可选透传）；dual_basis: {}（可选透传）
+  禁止 provenance/facts_binding 键；绑定块只能由 build 生成。
 """
 import argparse
+import hashlib
 import json
+import os
 import re
 import sys
+from pathlib import Path
 
 # 字符类含连字符：实体键约定（3.19 起 entities 字典键=stable entity_id）允许
 # ENT-PROJ 型命名——缺连字符时这类宏既不渲染也不被 G4 检出（死宏静默漏进正文，
@@ -247,6 +261,239 @@ def gate_check(facts, state=None, rendered_md=None):
     return errors, notes
 
 
+FACTS_PROVENANCE_SCHEMA = "facts-provenance/v1"
+STATE_SOURCE_SCHEMA = "analysis-state-source/v1"
+FACTS_INPUTS_KEY = "facts_inputs"
+FACTS_LEDGER_INPUTS = ("membership_ledger.json", "position_ledger.json",
+                       "economic_control_ledger.json", "identity_gate.json")
+
+
+def _sha256_path(path):
+    h = hashlib.sha256()
+    with open(path, "rb") as fh:
+        for chunk in iter(lambda: fh.read(1 << 20), b""):
+            h.update(chunk)
+    return h.hexdigest()
+
+
+def _norm_addr(value):
+    v = str(value or "").strip()
+    return v.lower() if v.lower().startswith("0x") else v
+
+
+def _case_file(case_dir, rel, label):
+    """案内常规文件：basename 相对案根、非符号链接、必须在场；否则 ValueError。"""
+    name = Path(str(rel or "")).name
+    if not name or name != str(rel):
+        raise ValueError(f"{label} 路径必须是案根内 basename: {rel!r}")
+    p = Path(case_dir) / name
+    if p.is_symlink() or not p.is_file():
+        raise ValueError(f"{label} 不在案根或是符号链接: {name}")
+    return p
+
+
+def _reject_constant(value):
+    raise ValueError(f"JSON 含非有限常量 {value}（NaN/Infinity 不允许）")
+
+
+def _finite_float(text):
+    v = float(text)
+    if v != v or v in (float("inf"), float("-inf")):
+        raise ValueError(f"JSON 浮点非有限: {text}")
+    return v
+
+
+def _load_case_json(case_dir, rel, label):
+    with open(_case_file(case_dir, rel, label), encoding="utf-8") as fh:
+        try:
+            return json.load(fh, parse_constant=_reject_constant, parse_float=_finite_float)
+        except ValueError as exc:
+            raise ValueError(f"{label} 解析失败: {exc}") from exc
+
+
+def _raw_str(value, label):
+    n = _int(value)
+    if n < 0:
+        raise ValueError(f"{label} 不得为负: {value!r}")
+    return str(n)
+
+
+def derive_facts(case_dir, *, exploration=False):
+    """R07（7.2.0）：从三账＋identity_gate＋（可选）provenance_ledger＋state_source.facts_inputs
+    重算 facts.json。纯函数：只读案内文件，不写盘，不带时间戳；build 与发布闸/收口共用，
+    闸用它重算后与落盘 facts 逐字段比对。任何缺件/不闭合/证据不符一律 ValueError（fail-closed）。"""
+    case_dir = Path(case_dir)
+    data = {n: _load_case_json(case_dir, n, n) for n in FACTS_LEDGER_INPUTS[:3]}
+    for name, obj in data.items():
+        rows = obj.get("entries", obj.get("entities")) if isinstance(obj, dict) else None
+        if not isinstance(rows, list) or not rows:
+            raise ValueError(f"{name} 缺 entries/entities 或为空——空账不得生成 facts")
+    import audit_release_gate  # 同目录；三账闭合复用发布闸同一实现
+    errs = []
+    audit_release_gate.check_three_ledgers(case_dir, data, errs, chain=None)
+    if errs:
+        raise ValueError("三账不闭合，拒绝生成 facts: " + "; ".join(errs[:3]))
+    identity = _load_case_json(case_dir, "identity_gate.json", "identity_gate.json")
+    total_raw = _raw_str(identity.get("total_supply_raw"), "identity_gate.total_supply_raw")
+    if int(total_raw) <= 0:
+        raise ValueError("identity_gate.total_supply_raw 必须为正")
+    ledger_path = case_dir / "provenance_ledger.json"
+    ledger = None
+    if ledger_path.is_file() and not ledger_path.is_symlink():
+        ledger = _load_case_json(case_dir, "provenance_ledger.json", "provenance_ledger.json")
+        if not exploration and ledger.get("exploration") is True:
+            raise ValueError("provenance_ledger 为探索产物，formal build 拒绝")
+        lt = ledger.get("total_supply_raw")
+        if lt is not None and _raw_str(lt, "provenance_ledger.total_supply_raw") != total_raw:
+            raise ValueError(f"total_supply_raw 冲突: identity_gate {total_raw} != provenance_ledger {lt}")
+    source = _load_case_json(case_dir, "state_source.json", "state_source.json")
+    if source.get("schema") != STATE_SOURCE_SCHEMA:
+        raise ValueError(f"state_source.schema 必须是 {STATE_SOURCE_SCHEMA}")
+    fi = source.get(FACTS_INPUTS_KEY)
+    if not isinstance(fi, dict):
+        raise ValueError(f"state_source 缺 {FACTS_INPUTS_KEY} 对象")
+    if "provenance" in fi or "facts_binding" in fi:
+        raise ValueError("state_source.facts_inputs 不得预置 provenance/facts_binding——绑定块只能由 build 生成")
+    symbol = str(fi.get("symbol") or "").strip()
+    decimals = fi.get("decimals")
+    if not symbol or isinstance(decimals, bool) or not isinstance(decimals, int) or decimals < 0:
+        raise ValueError("facts_inputs.symbol/decimals 缺失或非法")
+    labels = fi.get("entity_labels")
+    if not isinstance(labels, dict) or not labels:
+        raise ValueError("facts_inputs.entity_labels 缺失或为空")
+    overrides = fi.get("peak_overrides") or {}
+    merges = fi.get("merge_evidence") or {}
+    roles = fi.get("role_notes") or {}
+    if not all(isinstance(x, dict) for x in (overrides, merges, roles)):
+        raise ValueError("facts_inputs.peak_overrides/merge_evidence/role_notes 须为对象")
+
+    members = data["membership_ledger.json"]
+    members = members.get("entries", members.get("entities", []))
+    strict_by_entity = {}
+    for row in members:
+        if str(row.get("membership", "")).strip() == "strict":
+            strict_by_entity.setdefault(str(row.get("entity_id", "")).strip(), set()).add(
+                _norm_addr(row.get("address")))
+    ledger_entities = {}
+    if ledger is not None:
+        for item in ledger.get("entities") or []:
+            if isinstance(item, dict) and item.get("entity_id"):
+                ledger_entities[str(item["entity_id"])] = item
+
+    econ = data["economic_control_ledger.json"]
+    econ = econ.get("entries", econ.get("entities", []))
+    entities, used_overrides = {}, {}
+    for row in econ:
+        eid = str(row.get("entity_id", "")).strip()
+        label = str(labels.get(eid) or "").strip()
+        if not label:
+            raise ValueError(f"facts_inputs.entity_labels 缺实体 {eid} 的 label")
+        current = _raw_str(row.get("confirmed_economic_control_raw"),
+                           f"economic {eid}.confirmed_economic_control_raw")
+        ent = {"label": label, "addresses": sorted(strict_by_entity.get(eid, set())),
+               "current_raw": current}
+        ov = overrides.get(eid)
+        if ov is not None:
+            if not isinstance(ov, dict):
+                raise ValueError(f"peak_overrides.{eid} 须为对象")
+            ev = ov.get("evidence")
+            if not isinstance(ev, dict) or not ev.get("path") or not ev.get("sha256"):
+                raise ValueError(f"peak_overrides.{eid} 缺 evidence.path/sha256")
+            ev_path = _case_file(case_dir, ev["path"], f"peak_overrides.{eid}.evidence")
+            if _sha256_path(ev_path) != str(ev["sha256"]).lower():
+                raise ValueError(f"peak_overrides.{eid}.evidence sha256 与案内实物不一致")
+            peak = _raw_str(ov.get("peak_raw"), f"peak_overrides.{eid}.peak_raw")
+            peak_date = str(ov.get("peak_date") or "").strip()
+            if not peak_date:
+                raise ValueError(f"peak_overrides.{eid} 缺 peak_date")
+            used_overrides[eid] = {"peak_raw": peak, "peak_date": peak_date,
+                                   "evidence": {"path": ev_path.name,
+                                                "sha256": str(ev["sha256"]).lower()}}
+        elif eid in ledger_entities:
+            anchor = ((ledger_entities[eid].get("anchors") or {}).get("peak") or {})
+            peak = _raw_str(anchor.get("stock_raw"), f"provenance_ledger {eid}.anchors.peak.stock_raw")
+            peak_date = str(anchor.get("date") or "").strip()
+            if not peak_date:
+                raise ValueError(f"provenance_ledger {eid}.anchors.peak 缺 date")
+        elif exploration:
+            peak, peak_date = current, None
+        else:
+            raise ValueError(f"实体 {eid} 无峰值来源（provenance_ledger 锚点或 peak_overrides）——formal build 拒绝")
+        if int(peak) < int(current):
+            raise ValueError(f"实体 {eid} peak_raw {peak} < current_raw {current}")
+        ent["peak_raw"] = peak
+        ent["peak_date"] = peak_date
+        m = merges.get(eid)
+        if isinstance(m, dict) and m.get("earliest"):
+            ent["merge_evidence_earliest"] = str(m["earliest"])
+            if m.get("note"):
+                ent["merge_evidence_note"] = str(m["note"])
+        r = roles.get(eid)
+        if isinstance(r, dict) and r:
+            ent["role_notes"] = {str(k): str(v) for k, v in r.items()}
+        entities[eid] = ent
+    unknown = sorted(set(labels) - set(entities))
+    if unknown:
+        raise ValueError(f"facts_inputs.entity_labels 含三账之外的实体: {unknown[:5]}")
+    unknown = sorted(set(overrides) - set(entities))
+    if unknown:
+        raise ValueError(f"facts_inputs.peak_overrides 含三账之外的实体: {unknown[:5]}")
+
+    inputs = {n: {"sha256": _sha256_path(case_dir / n)} for n in FACTS_LEDGER_INPUTS}
+    if ledger is not None:
+        inputs["provenance_ledger.json"] = {"sha256": _sha256_path(ledger_path)}
+    facts = {"token": {"symbol": symbol, "decimals": decimals, "total_supply_raw": total_raw},
+             "entities": entities, "metrics": fi.get("metrics") or {}}
+    if isinstance(fi.get("dual_basis"), dict):
+        facts["dual_basis"] = fi["dual_basis"]
+    facts["provenance"] = {
+        "schema": FACTS_PROVENANCE_SCHEMA, "facts_binding": "ledger-derived",
+        "mode": "exploration" if exploration else "formal",
+        "inputs": inputs,
+        "state_source": {"path": "state_source.json",
+                         "sha256": _sha256_path(case_dir / "state_source.json")},
+        "peak_overrides": used_overrides,
+        "producer": {"path": "scripts/report/facts_gate.py",
+                     "sha256": _sha256_path(Path(__file__).resolve())},
+    }
+    # 生成物必须过既有 facts gate（G2 供给上界/G3 内部一致等；无 state/渲染文本时 G1/G5 自然跳过）
+    gate_errors, _notes = gate_check(Facts(facts))
+    if gate_errors:
+        raise ValueError("生成的 facts 未过既有 facts gate: " + "; ".join(gate_errors[:3]))
+    return facts
+
+
+def build_main(argv):
+    ap = argparse.ArgumentParser(prog="facts_gate.py build")
+    ap.add_argument("--case-dir", default=".")
+    ap.add_argument("--source", default="state_source.json",
+                    help="人工输入文件（basename，须在案根；读取其 facts_inputs 块）")
+    ap.add_argument("--out", default="facts.json")
+    ap.add_argument("--exploration", action="store_true",
+                    help="允许缺峰值来源（peak=current）；产物 provenance.mode=exploration，发布闸/收口必拒")
+    a = ap.parse_args(argv)
+    case_dir = Path(a.case_dir)
+    if a.source != "state_source.json":
+        print("FAIL: --source 只接受案根 state_source.json（人工字段复用该文件，不另立文件）")
+        return 2
+    try:
+        facts = derive_facts(case_dir, exploration=a.exploration)
+    except (KeyError, ValueError, OSError, TypeError) as exc:
+        print(f"FAIL: facts 生成失败——{exc}")
+        return 2
+    out = case_dir / Path(a.out).name
+    payload = json.dumps(facts, ensure_ascii=False, indent=2) + "\n"
+    tmp = out.with_name(out.name + ".tmp")
+    tmp.write_text(payload, encoding="utf-8")
+    os.replace(tmp, out)
+    mode = facts["provenance"]["mode"]
+    print(f"PASS: facts 生成 {out.name}（mode={mode}，实体 {len(facts['entities'])} 个，"
+          f"override {len(facts['provenance']['peak_overrides'])} 个）")
+    if mode == "exploration":
+        print("[exploration] 产物带非正式标记，new-analysis 发布闸与 stage2 收口必拒")
+    return 0
+
+
 def load_and_check(facts_path, state_path=None, md_text=None):
     """build_html.py 的接入点：渲染 md 并跑全 gate。返回 (rendered_md, errors, notes)。"""
     facts = Facts(json.load(open(facts_path, encoding="utf-8")))
@@ -257,6 +504,8 @@ def load_and_check(facts_path, state_path=None, md_text=None):
 
 
 def main():
+    if sys.argv[1:2] == ["build"]:
+        return build_main(sys.argv[2:])
     ap = argparse.ArgumentParser()
     ap.add_argument("--facts", required=True)
     ap.add_argument("--state", help="analysis-state.json（给了才做 G1 成员集合对账）")
diff --git a/scripts/report/stage2_closeout.py b/scripts/report/stage2_closeout.py
index b72e15c..7a6885a 100644
--- a/scripts/report/stage2_closeout.py
+++ b/scripts/report/stage2_closeout.py
@@ -572,7 +572,14 @@ def run_checks(case, report_rel, workorder_rel=WORKORDER):
     record("dual_basis", dual)
     record("fig2_series", lambda: rules(lambda: fig2_series_errors(case, workorder_rel)))
     record("workorder", lambda: rules(lambda: workorder_errors(case, report_rel, workorder_rel)))
+
+    def facts_vs_ledgers():
+        errors = []
+        audit_release_gate.check_facts_vs_ledgers(case, load(case, "facts.json"), errors)
+        return errors, [], "PASS"
+
     record("facts_gate", facts_check)
+    record("facts_vs_ledgers", facts_vs_ledgers)
     return checks
```

## C4/C5/C6 diff 摘要

| 项目 | 已实施片段 |
|---|---|
| C4-0 | test_audit_release_gate.py 仅增加 build_facts_from_ledgers；既有用例未改。 |
| C4-a | stage2 夹具 state/identity 地址对齐为 0xabc；移除手写 facts；先落 provenance，再 build，再 A4 finalize；三处检查计数 11→12；加入三个手改拒绝变体。 |
| C4-a′ | test_stage2_reseal.py 仅把 add_reseal_prereqs 函数体改为 w2.add_provenance_ledger(case)；原函数体逐字搬到 test_stage2_closeout.py；未运行 reseal。 |
| C4-b | Solana 夹具导入共享助手，移除手写 facts；identity 后 build；新增独立 t_r07_facts_vs_ledgers 并登记 main，验证手改和缺件。 |
| C4-c/c′ | P105 从真实 240-owner balances 建 identity，再生成 facts；augment_gate 仅增加可选 balances 参数和指定分支，默认逻辑保持。 |
| C4-d | 新增规定的 build/derive/闸测试：14 类拆为 28 个独立目录变体，逐例捕获 AssertionError/ImportError/AttributeError。 |
| C4-e | test_a4_gate.py 仅改 import 与 case_new 的一处 build；原 analysis-audit 案手写 facts 保留。 |
| C5 | 根据扫描缺项增加 facts-provenance producer、两个 consumer schema 点和 build_main overwrite_single；无整体重排。minimum_counts 无扫描缺项，保留原值。 |
| C6 | report-template.md 原 :212 唯一子串替换，文件减少 5 B；其余文档未改。 |

C5 首次扫描原始结果（随后按缺项增补；audit_release_gate consumer 的新旧集合差异占两条）：

```text
FAIL receipt_producers: code point missing from manifest: ('scripts/report/facts_gate.py', ('facts-provenance/v1',))
FAIL receipt_consumers: code point missing from manifest: ('scripts/report/audit_release_gate.py', ('address-balance-snapshot/v1', 'adversarial-review/v2', 'adversarial-review/v3', 'adversarial-review/v4', 'facts-provenance/v1', 'figure2-check-receipt/v1', 'identity-holder-snapshot/v2', 'reproduce-receipt/v2'))
FAIL receipt_consumers: code point missing from manifest: ('scripts/report/facts_gate.py', ('analysis-state-source/v1',))
FAIL receipt_consumers: manifest point missing from code: ('scripts/report/audit_release_gate.py', ('address-balance-snapshot/v1', 'adversarial-review/v2', 'adversarial-review/v3', 'adversarial-review/v4', 'figure2-check-receipt/v1', 'identity-holder-snapshot/v2', 'reproduce-receipt/v2'))
FAIL atomic_writes: code point missing from manifest: ('scripts/report/facts_gate.py', 'build_main')
invariant manifest FAIL: 5 discrepancy(s)
```

## ③ RED 摘要（逐例）

证据文件：[C_red_evidence.txt](C_red_evidence.txt)。生产改动前 C4-d 28/28、集成断言 9/9 取得 RED；三个生产文件取证前后 SHA256 完全一致。证据内保留异常原文、CLI stderr 与生产基线输出。

C_red_evidence.txt SHA256: f76111d2af0311e3d122fe23fd41a62b8087478b77cc57c3b82dd1f6257bc97d

```text
FAIL  R07 1 derive 绿例: AttributeError: module 'facts_gate' has no attribute 'derive_facts'
FAIL  R07 2 CLI build 幂等: AssertionError: usage: facts_gate.py [-h] --facts FACTS [--state STATE] [--md MD]
FAIL  R07 3 override valid: AttributeError: module 'facts_gate' has no attribute 'derive_facts'
FAIL  R07 3 override bad_sha: AttributeError: module 'facts_gate' has no attribute 'derive_facts'
FAIL  R07 3 override missing_evidence: AttributeError: module 'facts_gate' has no attribute 'derive_facts'
FAIL  R07 4 formal 无峰值拒 / exploration 放行: AttributeError: module 'facts_gate' has no attribute 'derive_facts'
FAIL  R07 5 预置绑定拒: AttributeError: module 'facts_gate' has no attribute 'derive_facts'
FAIL  R07 6 label missing: AttributeError: module 'facts_gate' has no attribute 'derive_facts'
FAIL  R07 6 label empty: AttributeError: module 'facts_gate' has no attribute 'derive_facts'
FAIL  R07 6 label extra: AttributeError: module 'facts_gate' has no attribute 'derive_facts'
FAIL  R07 7 三账不闭合拒: AttributeError: module 'facts_gate' has no attribute 'derive_facts'
FAIL  R07 8 总量冲突拒: AttributeError: module 'facts_gate' has no attribute 'derive_facts'
FAIL  R07 9 闸绿例: AttributeError: module 'facts_gate' has no attribute 'derive_facts'
FAIL  R07 10 闸拒手改 current: AttributeError: module 'facts_gate' has no attribute 'derive_facts'
FAIL  R07 10 闸拒手改 provenance: AttributeError: module 'facts_gate' has no attribute 'derive_facts'
FAIL  R07 10 闸拒手改 exploration: AttributeError: module 'facts_gate' has no attribute 'derive_facts'
FAIL  R07 10 闸拒手改 identity: AttributeError: module 'facts_gate' has no attribute 'derive_facts'
FAIL  R07 10 闸拒手改 receipt: AttributeError: module 'facts_gate' has no attribute 'derive_facts'
FAIL  R07 11 peak < current 拒: AttributeError: module 'facts_gate' has no attribute 'derive_facts'
FAIL  R07 12 空账 membership_ledger.json missing=False: AttributeError: module 'facts_gate' has no attribute 'derive_facts'
FAIL  R07 12 空账 membership_ledger.json missing=True: AttributeError: module 'facts_gate' has no attribute 'derive_facts'
FAIL  R07 12 空账 position_ledger.json missing=False: AttributeError: module 'facts_gate' has no attribute 'derive_facts'
FAIL  R07 12 空账 position_ledger.json missing=True: AttributeError: module 'facts_gate' has no attribute 'derive_facts'
FAIL  R07 13 非有限输入 NaN: AttributeError: module 'facts_gate' has no attribute 'derive_facts'
FAIL  R07 13 非有限输入 Infinity: AttributeError: module 'facts_gate' has no attribute 'derive_facts'
FAIL  R07 13 非有限输入 1e999: AttributeError: module 'facts_gate' has no attribute 'derive_facts'
FAIL  R07 13 facts 溢出值拒: AttributeError: module 'facts_gate' has no attribute 'derive_facts'
FAIL  R07 14 产物过既有 G2 gate: AttributeError: module 'facts_gate' has no attribute 'derive_facts'
FAIL C4-0 shared helper: ImportError: cannot import name 'build_facts_from_ledgers' from 'test_audit_release_gate' (/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_audit_release_gate.py)
FAIL C4-b hand-edit: ImportError: cannot import name 'build_facts_from_ledgers' from 'test_audit_release_gate' (/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_audit_release_gate.py)
FAIL C4-b missing facts: ImportError: cannot import name 'build_facts_from_ledgers' from 'test_audit_release_gate' (/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_audit_release_gate.py)
FAIL C4-e case_new: ImportError: cannot import name 'build_facts_from_ledgers' from 'test_audit_release_gate' (/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_audit_release_gate.py)
FAIL C4-c P105 fixture helper: AttributeError: module 'audit_fixture_profiles' has no attribute 'build_facts_from_ledgers'
FAIL C4-c-prime balances argument: AssertionError: (root, gate_obj, *, chain, token='0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')
FAIL C4-a current: AssertionError: expected 12 checks, actual 11; names=['release_gate_dryrun', 'a4_seal_integrity', 'downstream_stale', 'identity_gate', 'a5_provenance_flip', 'a5_distribution', 'caption_same_source', 'dual_basis', 'fig2_series', 'workorder', 'facts_gate']
FAIL C4-a provenance: AssertionError: PASS: release_gate_dryrun
FAIL C4-a exploration: AssertionError: expected 12 checks, actual 11; names=['release_gate_dryrun', 'a4_seal_integrity', 'downstream_stale', 'identity_gate', 'a5_provenance_flip', 'a5_distribution', 'caption_same_source', 'dual_basis', 'fig2_series', 'workorder', 'facts_gate']
```

C4-a 的 current/exploration 变体均看到基线仅有 11 项检查；缺 provenance 变体在基线仍返回 PASS。完整断言输出见证据文件。C4-a′ 按 §0.8 不执行，未以静态核对冒充运行验收。

## ④ 指定验收结果尾行

各项实际命令为 python3 -B scripts/tests/<文件名>；运行环境设置 PYTHONDONTWRITEBYTECODE=1，避免子进程生成字节码。下表均为最终运行的原始尾行：

| 文件 | exit code | stdout/stderr 最后非空行 |
|---|---:|---|
| test_report_facts.py | 0 | PASS: facts 宏渲染/附录B同源/G1集合gate(含entity_id主键)/G4宏名gate/G5手写检出/G2上界/G6归并时点/G7血缘提示，七契约全过 |
| test_stage2_closeout.py | 0 | stage2_closeout: 28/28 PASS |
| test_repair_batch_d.py | 0 | BATCH D 全部通过 |
| test_review_20260804_p105.py | 0 | PASS: P1-05 mandatory new-analysis vs independent-audit release profiles |
| test_repair_batch_b.py | 0 | PASS batch B F-03/F-08 regressions 41/41 |
| test_audit_release_gate.py | 0 | PASS: audit_release_gate 净室资产/哈希/CEX受益权/阴性结论/图表封口与负钳零/对抗复核否决/四查WARN拦截/双线阈值/嵌套未决暴露/静置仓全集对账/日级峰值口径闭环十一类契约全过 |
| test_batch15_three_ledgers_frozen.py | 0 | PASS batch15 frozen consumers: 12/12 |
| test_batch18_shared_bundle_witness.py | 0 | PASS batch18 shared bundle witness: 6/6 |
| test_batch13_accounting_target.py | 0 | PASS batch13 accounting target regressions: 8/8 |
| test_recon_fifth_check.py | 0 | GREEN 22 wave-scan/v4 与 flow-anomaly/v2 旧产物被 v5/v3 验收拒收 |
| test_state_from_facts.py | 0 | PASS: D-05 state_from_facts compiler owns membership and raw-derived shares |
| test_figures_from_facts.py | 0 | PASS: figures_from_facts fig1白名单/legacy销毁键/legend receipt/burn豁免/overlay组成/价格绑定/flow宏同源/check终值对账全过 |
| test_a4_gate.py | 0 | a4_gate 契约测试全部通过（23 项） |
| invariant_scan.py | 0 | PASS invariant manifest: receipt_producers=80, receipt_consumers=117, transport_calls=65, atomic_writes=60, formal_entrypoints=61, exceptions=0 |

新增路径的 GREEN 原文：

```text
ok    R07 1 derive 绿例
ok    R07 2 CLI build 幂等
ok    R07 3 override valid
ok    R07 3 override bad_sha
ok    R07 3 override missing_evidence
ok    R07 4 formal 无峰值拒 / exploration 放行
ok    R07 5 预置绑定拒
ok    R07 6 label missing
ok    R07 6 label empty
ok    R07 6 label extra
ok    R07 7 三账不闭合拒
ok    R07 8 总量冲突拒
ok    R07 9 闸绿例
ok    R07 10 闸拒手改 current
ok    R07 10 闸拒手改 provenance
ok    R07 10 闸拒手改 exploration
ok    R07 10 闸拒手改 identity
ok    R07 10 闸拒手改 receipt
ok    R07 11 peak < current 拒
ok    R07 12 空账 membership_ledger.json missing=False
ok    R07 12 空账 membership_ledger.json missing=True
ok    R07 12 空账 position_ledger.json missing=False
ok    R07 12 空账 position_ledger.json missing=True
ok    R07 13 非有限输入 NaN
ok    R07 13 非有限输入 Infinity
ok    R07 13 非有限输入 1e999
ok    R07 13 facts 溢出值拒
ok    R07 14 产物过既有 G2 gate
PASS: R07 build/derive/发布闸 14 类、28 个独立用例
ok    facts_vs_ledgers_rejects_hand_edit
ok    R07 facts 手改被三账重算拒绝
ok    R07 new-analysis 缺 facts 必拒
ok    P1-05 全新分析无净室资产仍过必经共享门禁
```

部分绘图相关测试提示默认 Matplotlib 缓存目录不可写，自动使用系统临时目录；最终返回码均为 0，无未通过测试。

## ⑤ §1.1 三个字节数（只 stat，不读内容）

```console
$ stat -f %z SKILL.md
8021
```

```console
$ stat -f %z commands-staging/*.md | awk '{s+=$1} END{print s}'
8798
```

```console
$ find references -name '*.md' -print0 | xargs -0 stat -f %z | awk '{s+=$1} END{print s}'
930065
```

结果：SKILL.md=8021（不变）、commands-staging=8798（不变）、references=930065（−5 B）。

## ⑥ git diff --stat

```text
 references/report-template.md              |   2 +-
 scripts/report/audit_release_gate.py       |  61 +++++++
 scripts/report/facts_gate.py               | 251 +++++++++++++++++++++++++++-
 scripts/report/stage2_closeout.py          |   7 +
 scripts/tests/identity_gate_fixture.py     |  11 +-
 scripts/tests/invariant_manifest.json      |  18 ++
 scripts/tests/test_a4_gate.py              |   3 +-
 scripts/tests/test_audit_release_gate.py   |  25 +++
 scripts/tests/test_repair_batch_d.py       |  24 ++-
 scripts/tests/test_report_facts.py         | 253 +++++++++++++++++++++++++++++
 scripts/tests/test_review_20260804_p105.py |   6 +-
 scripts/tests/test_stage2_closeout.py      |  52 ++++--
 scripts/tests/test_stage2_reseal.py        |  12 +-
 13 files changed, 688 insertions(+), 37 deletions(-)
```

git diff --stat 不显示未跟踪文件；本段另新建 C_done.md 与 C_red_evidence.txt，均在白名单内。最终 git status --porcelain=v1 --untracked-files=all：

```text
 M references/report-template.md
 M scripts/report/audit_release_gate.py
 M scripts/report/facts_gate.py
 M scripts/report/stage2_closeout.py
 M scripts/tests/identity_gate_fixture.py
 M scripts/tests/invariant_manifest.json
 M scripts/tests/test_a4_gate.py
 M scripts/tests/test_audit_release_gate.py
 M scripts/tests/test_repair_batch_d.py
 M scripts/tests/test_report_facts.py
 M scripts/tests/test_review_20260804_p105.py
 M scripts/tests/test_stage2_closeout.py
 M scripts/tests/test_stage2_reseal.py
?? maintenance/repair-20260917-p0-four/C_done.md
?? maintenance/repair-20260917-p0-four/C_red_evidence.txt
```

## ⑦ 差异、边界与停工点

无施工偏离，无停工点；未扩展白名单。minimum_counts 原值保留，因为扫描未报该项缺失；实际扫描计数已增至 producers=80、consumers=117、atomic_writes=60。

以下为静态边界核对，不替代未执行的 reseal 验收：

```text
PASS: scripts/report/facts_gate.py:Facts unchanged
PASS: scripts/report/facts_gate.py:gate_check unchanged
PASS: scripts/report/facts_gate.py:load_and_check unchanged
PASS: facts_gate.main original argparse unchanged
PASS: scripts/report/audit_release_gate.py:check_three_ledgers unchanged
PASS: scripts/report/audit_release_gate.py:check_figure2_receipt unchanged
PASS: check_facts_vs_ledgers first executable statement rejects nonregular facts.json
PASS: stage2: original 11 record names/order preserved; facts_vs_ledgers follows facts_gate
PASS: reseal: only specified function body changed; original body copied byte for byte
PASS: shared fixture: only build_facts_from_ledgers added; existing cases unchanged
PASS: manifest: only scan-reported producer/consumer/atomic additions; all other entries/count floors unchanged
```

按 §0.8 未运行 test_stage2_reseal.py、run_all.py、docs_lint；未修改 contract_manifest.json、SKILL.md、commands-staging、analyze-workflow.md、VERSION、pyproject、CHANGELOG；未执行 stash/checkout/reset；未部署 ~/.claude/commands/。

§4 调度方验收保持待办：commit 后同步 /tmp/w3_acceptance 到新 HEAD 并确认 overlay 为空再运行 reseal；本机 APU 0801 对照；pre-commit docs_lint；code_change_pending.md 的记录。施工方未执行或冒称这些项目通过。

## ⑧ 禁读披露

会话启动上下文已由系统预载 memory 摘要；本轮未通过工具读取 ~/.codex/ 下任何文件，也未使用其旧结论作为施工证据。未读取 archive/、blind-reviews/、.staging_*、references/attic.md 或 /Users/uravvv/Desktop 下的文件内容；references/attic.md 如参与 §1.1 汇总，仅执行 stat 读取大小。全程离线。

报告生成 UTC: 2026-09-17T14:21:20.169977+00:00
