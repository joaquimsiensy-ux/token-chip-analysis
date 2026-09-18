# 施工 F05：完成

按 `workorder_F05.md` v3 的 §0–§3 施工。开工与收工 HEAD 均为 `d7baf54`；6 个白名单代码/测试文件改动，另新增本报告与 `F05_red_evidence.txt`。先保存 RED 证据，再修改生产代码；9 项指定测试/守卫全部 exit=0。未 commit、push、部署；未运行 `run_all.py`。

## ① §0.1 基线校验原始输出

```text
$ git status --short

$ git rev-parse --short HEAD
d7baf54

$ git diff --stat 311e6c4 HEAD -- scripts/report/facts_gate.py scripts/tests/test_report_facts.py references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
```

以上三条命令均 exit=0；`git status --short` 与指定范围的 `git diff --stat 311e6c4 HEAD` 均为空输出。

当前用户提示及 `construct_F05_prompt.md:2` 明示：派工基线为 `bf60b50`，施工提示词自身的提交使实际开工 HEAD 恰多一个提交。因此按该已明确的规则核验，实际 HEAD 为 `d7baf54`，父提交为 `bf60b50`，符合预期；未将工单 §0.1 的“首行一致”机械解释为首行标题文本中的不存在的 hash。

```text
$ git log -2 --format='%h %s'
d7baf54 F07 盲审 r2 提示词 / F05 施工提示词对齐基线
bf60b50 F07 盲审 r1 minor 修复:迁移命令补必填 --out-dir(工单 §1.4/done ⑦);blind_F07_reply_r1 归档
```

开工文件 SHA-256：

```text
$ shasum -a 256 scripts/report/facts_gate.py scripts/report/audit_release_gate.py scripts/tests/test_report_facts.py scripts/tests/test_audit_release_gate.py scripts/tests/test_repair_batch_d.py scripts/tests/test_review_20260804_p105.py
b9bc055919af6d9264e0323d5fd2f70fb63a05826aeacb20812490aa254994b2  scripts/report/facts_gate.py
07cad8c9aeeccc950b7dcf2dfcfdf6323f943aa5ea5fdf79e123a151873c0e80  scripts/report/audit_release_gate.py
658c4c299a808e2a460f55eb6b3ef9c879685b9b659662f1708f8802bd24a651  scripts/tests/test_report_facts.py
2c64f22385b9a9834b32d9fc5af0d99e02929c6b9c41ae3aba242336c6adad34  scripts/tests/test_audit_release_gate.py
4ddb36e078d092fc52002c79de42d3ee2ecd0a0e0878f0dab97ae05f6d96a8bb  scripts/tests/test_repair_batch_d.py
8686b7cc5c2eed13e9f48a3d7e91b8531657dabcc9b90b18db208ee133f85e66  scripts/tests/test_review_20260804_p105.py
```

## ② §2.1–§2.4 git diff 原文

```diff
$ git diff -- scripts/report/facts_gate.py scripts/report/audit_release_gate.py scripts/tests/test_report_facts.py scripts/tests/test_audit_release_gate.py scripts/tests/test_repair_batch_d.py scripts/tests/test_review_20260804_p105.py
diff --git a/scripts/report/audit_release_gate.py b/scripts/report/audit_release_gate.py
index e3d5708..f8a4ef1 100644
--- a/scripts/report/audit_release_gate.py
+++ b/scripts/report/audit_release_gate.py
@@ -1583,6 +1583,33 @@ def check_facts_vs_ledgers(case_dir: Path, facts, errors: list[str], receipt=Non
         errors.append("facts.provenance（inputs/state_source/peak_overrides 的 sha 或绑定）与当前案内实物不一致——输入已变，须重新 build")
 
 
+def check_facts_decimals(case_dir: Path, facts, accounting, errors: list[str]):
+    """F05（7.2.1）：token.decimals 绑定链上观测——solana 家族取 accounting_mode.checks.decimals
+    （accounting_gate_sol 写出），evm 家族取 balance 对账收据绑定的 verify_recon config.decimals
+    （深验 witness 已缓存，不重跑）；取不到即拒，不让调用者自报数量单位。只挂 new-analysis，
+    不进共享 check_facts_vs_ledgers（stage2 收口/reseal 复用后者）。"""
+    declared = ((facts or {}).get("token") or {}).get("decimals")
+    chain = str((accounting or {}).get("chain") or "")
+    observed = None
+    try:
+        import shared_release_receipt
+        family = shared_release_receipt.chain_family(chain)
+        if family == "solana":
+            observed = ((accounting or {}).get("checks") or {}).get("decimals")
+        else:
+            witness = _validate_reconciliation_report_once(case_dir)
+            bal = (witness.receipts or {}).get("balance") or {}
+            _, cfg = shared_release_receipt._bound_json_input(case_dir, bal, "config", "verify_recon config")
+            observed = cfg.get("decimals")
+    except Exception as exc:
+        errors.append(f"facts.token.decimals 无法取链上观测值: {exc}")
+        return
+    if isinstance(observed, bool) or not isinstance(observed, int):
+        errors.append("facts.token.decimals 无链上观测来源可核（accounting_mode.checks/对账收据 config 缺 decimals）")
+    elif declared != observed:
+        errors.append(f"facts.token.decimals={declared!r} 与链上观测 {observed} 不一致——state_source.facts_inputs.decimals 填错")
+
+
 def check_figure2_receipt(case_dir: Path, d: dict, errors: list[str]):
     """F-C5：图 2 末点对账收据复验（new-analysis 必经）。
 
@@ -1880,6 +1907,7 @@ def _run(case_dir: Path, report: Path | None, *, profile="independent-audit"):
         if profile == "new-analysis" and "facts.json" in data:
             check_facts_vs_ledgers(case_dir, data["facts.json"], errors,
                                    receipt=data.get("figure2_check_receipt.json"))
+            check_facts_decimals(case_dir, data["facts.json"], data.get("accounting_mode.json"), errors)
         state_path = case_dir / "analysis-state.json"
         if state_path.is_file():
             state_obj = load_json(state_path, errors)
diff --git a/scripts/report/facts_gate.py b/scripts/report/facts_gate.py
index adb86b8..3a1735d 100644
--- a/scripts/report/facts_gate.py
+++ b/scripts/report/facts_gate.py
@@ -62,7 +62,7 @@ entity_id 匹配**，label 只是展示文案（改措辞不再断链路）；
 state_source.facts_inputs schema：
   symbol: str（必填）；decimals: int≥0（必填）
   entity_labels: {eid: label}（必填、非空、覆盖全部实体）
-  peak_overrides: {eid: {peak_raw, peak_date, evidence: {path, sha256, note?}}}
+  peak_overrides: {eid: {peak_raw, peak_date, evidence: {path, sha256}}}，证据 JSON 须为 {entity_id: {peak_raw, peak_date}} 与申报相等
       （可选，优先于 provenance 锚点，证据须为案根常规文件）
   merge_evidence: {eid: {earliest, note}}（可选）
   role_notes: {eid: {addr: note}}（可选）
@@ -70,6 +70,7 @@ state_source.facts_inputs schema：
   禁止 provenance/facts_binding 键；绑定块只能由 build 生成。
 """
 import argparse
+import datetime as _dt
 import hashlib
 import json
 import os
@@ -197,6 +198,8 @@ def gate_check(facts, state=None, rendered_md=None):
         peak = _int(ent.get("peak_raw", ent.get("current_raw", "0")))
         if cur > peak:
             errors.append(f"G3 {eid} current_raw > peak_raw（{cur} > {peak}）")
+        if facts.total_raw and peak > facts.total_raw:
+            errors.append(f"G2 {eid} peak_raw {peak} 超过总供应 {facts.total_raw}")
     # G2 供给上界
     total_cur = sum(_int(e.get("current_raw", "0")) for e in facts.entities.values())
     if facts.total_raw and total_cur > facts.total_raw:
@@ -415,6 +418,15 @@ def derive_facts(case_dir, *, exploration=False):
             peak_date = str(ov.get("peak_date") or "").strip()
             if not peak_date:
                 raise ValueError(f"peak_overrides.{eid} 缺 peak_date")
+            # F05（7.2.1）：证据内容须可解释——JSON 对象，以 entity_id 为键，给出与申报相等的
+            # peak_raw/peak_date；hash 只证明文件没变，不证明值来自文件。
+            ev_obj = _load_case_json(case_dir, ev["path"], f"peak_overrides.{eid}.evidence")
+            ev_ent = ev_obj.get(eid) if isinstance(ev_obj, dict) else None
+            if (not isinstance(ev_ent, dict)
+                    or _raw_str(ev_ent.get("peak_raw"), f"evidence[{eid}].peak_raw") != peak
+                    or str(ev_ent.get("peak_date") or "").strip() != peak_date):
+                raise ValueError(f"peak_overrides.{eid} 证据内容与申报 peak_raw/peak_date 不一致"
+                                 f"（证据须为 {{\"{eid}\": {{\"peak_raw\", \"peak_date\"}}}}）")
             used_overrides[eid] = {"peak_raw": peak, "peak_date": peak_date,
                                    "evidence": {"path": ev_path.name,
                                                 "sha256": str(ev["sha256"]).lower()}}
@@ -428,6 +440,17 @@ def derive_facts(case_dir, *, exploration=False):
             peak, peak_date = current, None
         else:
             raise ValueError(f"实体 {eid} 无峰值来源（provenance_ledger 锚点或 peak_overrides）——formal build 拒绝")
+        if peak_date is not None:
+            try:
+                peak_day = _dt.date.fromisoformat(peak_date)
+            except ValueError as exc:
+                raise ValueError(f"实体 {eid} peak_date {peak_date!r} 非 YYYY-MM-DD: {exc}") from exc
+            if peak_day.isoformat() != peak_date:
+                raise ValueError(f"实体 {eid} peak_date {peak_date!r} 非 YYYY-MM-DD（fromisoformat 接受 20260102/周格式，此处严格）")
+            cur_date = str((((ledger_entities.get(eid) or {}).get("anchors") or {})
+                            .get("current") or {}).get("date") or "").strip()
+            if cur_date and peak_day > _dt.date.fromisoformat(cur_date):
+                raise ValueError(f"实体 {eid} peak_date {peak_date} 晚于 provenance 当前锚点日 {cur_date}")
         if int(peak) < int(current):
             raise ValueError(f"实体 {eid} peak_raw {peak} < current_raw {current}")
         ent["peak_raw"] = peak
diff --git a/scripts/tests/test_audit_release_gate.py b/scripts/tests/test_audit_release_gate.py
index 7ff748d..331b9de 100644
--- a/scripts/tests/test_audit_release_gate.py
+++ b/scripts/tests/test_audit_release_gate.py
@@ -206,7 +206,9 @@ def build_facts_from_ledgers(root, *, symbol="TT", decimals=0, labels=None, peak
     econ = json.loads((root / "economic_control_ledger.json").read_text(encoding="utf-8"))
     rows = econ.get("entries", econ.get("entities", []))
     (root / "peak_evidence.json").write_text(
-        json.dumps({"note": "fixture: peak == confirmed"}) + "\n", encoding="utf-8")
+        json.dumps({str(row["entity_id"]): {
+            "peak_raw": str(int(str(row["confirmed_economic_control_raw"]))),
+            "peak_date": peak_date} for row in rows}) + "\n", encoding="utf-8")
     evidence = {"path": "peak_evidence.json", "sha256": sha(root / "peak_evidence.json")}
     names, overrides = {}, {}
     for row in rows:
diff --git a/scripts/tests/test_repair_batch_d.py b/scripts/tests/test_repair_batch_d.py
index 4b886e9..cb7044a 100644
--- a/scripts/tests/test_repair_batch_d.py
+++ b/scripts/tests/test_repair_batch_d.py
@@ -981,7 +981,7 @@ def build_solana_case(root: Path):
         "observation_bundle": {"path": "supply_receipt.json",
                                "size": bundle_path.stat().st_size,
                                "sha256": sha_file(bundle_path)},
-        "checks": {"fot": {"status": "clean"}}})
+        "checks": {"fot": {"status": "clean"}, "decimals": 0}})
     producers = {"balance": "scripts/solana/anchor_sampler.py",
                  "supply": "scripts/solana/scan_token_accounts.py",
                  "supply_truth": "scripts/lib/supply_truth_gate.py",
diff --git a/scripts/tests/test_report_facts.py b/scripts/tests/test_report_facts.py
index 3cdfd4b..fbcb550 100644
--- a/scripts/tests/test_report_facts.py
+++ b/scripts/tests/test_report_facts.py
@@ -150,7 +150,7 @@ def _r07_build_cases():
         assert proc.returncode == 2, proc.stdout + proc.stderr
 
     def override(root, variant):
-        evidence = _r07_write(root, "peak_evidence.json", {"note": "observed peak"})
+        evidence = _r07_write(root, "peak_evidence.json", {"e1": {"peak_raw": "160", "peak_date": "2026-01-03"}})
         ov = {"peak_raw": "160", "peak_date": "2026-01-03",
               "evidence": {"path": evidence.name, "sha256": _r07_sha(evidence)}}
         if variant == "bad_sha":
@@ -289,8 +289,43 @@ def _r07_build_cases():
                                ("metrics", [{"value": "7"}], "metrics"), ("metrics", {"m1": "7"}, "metrics"),
                                ("dual_basis", "x", "dual_basis"), ("dual_basis", None, "dual_basis")):
         run(f"15 类型非法拒 {field}", lambda root, f=field, v=value, t=text: bad_type(root, f, v, t))
+
+    def f05_override(root, peak_raw, peak_date, evidence_obj, error=""):
+        evidence = _r07_write(root, "peak_evidence.json", evidence_obj)
+        ov = {"peak_raw": peak_raw, "peak_date": peak_date,
+              "evidence": {"path": evidence.name, "sha256": _r07_sha(evidence)}}
+        edit(root, "state_source.json", lambda obj: obj["facts_inputs"].update(peak_overrides={"e1": ov}))
+        if error:
+            reject(root, error)
+        else:
+            facts = build(root)
+            assert facts["entities"]["e1"]["peak_raw"] == "150", facts
+
+    def f05_bad_date(root, value):
+        edit(root, "provenance_ledger.json", lambda obj:
+             obj["entities"][0]["anchors"]["peak"].update(date=value))
+        reject(root, "非 YYYY-MM-DD")
+
+    def f05_after_current(root):
+        edit(root, "provenance_ledger.json", lambda obj:
+             obj["entities"][0]["anchors"]["current"].update(date="2026-01-01"))
+        reject(root, "晚于")
+
+    run("16 F05 证据内容与申报不一致拒", lambda root: f05_override(
+        root, "1000000", "1900-01-01",
+        {"e1": {"peak_raw": "100", "peak_date": "2026-01-01"}}, "证据内容与申报"))
+    run("17 F05 证据一致放行（GREEN）", lambda root: f05_override(
+        root, "150", "2026-01-02", {"e1": {"peak_raw": "150", "peak_date": "2026-01-02"}}))
+    run("18 F05 peak 超总供应拒", lambda root: f05_override(
+        root, "2000", "2026-01-02",
+        {"e1": {"peak_raw": "2000", "peak_date": "2026-01-02"}}, "超过总供应"))
+    for value in ("1900-1-1x", "20260102"):
+        run("19 F05 peak_date 非法拒 " + value, lambda root, v=value: f05_bad_date(root, v))
+    run("20 F05 peak_date 晚于当前锚点日拒", f05_after_current)
+    run("21 F05 证据非对象拒", lambda root: f05_override(
+        root, "150", "2026-01-02", [1, 2], "证据内容"))
     assert not failures, f"R07 失败 {len(failures)}/{len(results)}: {failures}"
-    print(f"PASS: R07 build/derive/发布闸 15 类、{len(results)} 个独立用例", flush=True)
+    print(f"PASS: R07 build/derive/发布闸 21 类、{len(results)} 个独立用例", flush=True)
 
 
 def main():
diff --git a/scripts/tests/test_review_20260804_p105.py b/scripts/tests/test_review_20260804_p105.py
index a47d0a7..ce6d438 100644
--- a/scripts/tests/test_review_20260804_p105.py
+++ b/scripts/tests/test_review_20260804_p105.py
@@ -138,7 +138,7 @@ def bind_balance_receipt_to_snapshot(root: Path, snap: Path) -> None:
     create_bundle(root)
 
 
-def add_new_analysis_distribution(root: Path, report: Path) -> None:
+def add_new_analysis_distribution(root: Path, report: Path, decimals=0) -> None:
     balances = {f"owner-{i:03d}": max(1, int(2_000_000 / (1.035 ** i))) for i in range(240)}
     snap = root / "data/holders_owners.json"; write_json(snap, balances)
     bind_balance_receipt_to_snapshot(root, snap)
@@ -211,7 +211,7 @@ def add_new_analysis_distribution(root: Path, report: Path) -> None:
         identity["snapshot_binding"][key] = \
             f"identity_bridge/{identity['snapshot_binding'][key]}"
     write_json(root / "identity_gate.json", identity)
-    fixture.build_facts_from_ledgers(root, symbol="FX")
+    fixture.build_facts_from_ledgers(root, symbol="FX", decimals=decimals)
     # a4_claims 是对抗复核 v3 的权威锚；夹具改 registry 后必须真重跑 runner/finalize，
     # 不得手补 aggregate 的 sha 自证。
     fixture.refresh_adversarial(root)
@@ -268,6 +268,22 @@ def main():
         report = fixture.build_case(root, historical=False)
         assert not fixture.gate.run(root, report, profile="independent-audit")
 
+    with tempfile.TemporaryDirectory() as td:
+        root = Path(td)
+        report = fixture.build_case(root, historical=False)
+        add_new_analysis_distribution(root, report, decimals=2)
+        errors = fixture.gate.run(root, report, profile="new-analysis")
+        assert any("与链上观测 0 不一致" in error for error in errors), errors
+        print("PASS: F05 decimals 与链上观测不符拒", flush=True)
+
+    with tempfile.TemporaryDirectory() as td:
+        root = Path(td)
+        report = fixture.build_case(root, historical=False)
+        add_new_analysis_distribution(root, report, decimals=0)
+        errors = fixture.gate.run(root, report, profile="new-analysis")
+        assert errors == [], errors
+        print("PASS: F05 decimals 一致放行（GREEN→GREEN）", flush=True)
+
     print("PASS: P1-05 mandatory new-analysis vs independent-audit release profiles")
     return 0
 
```

## ③ RED 摘要

RED 原文、命令、生产文件和被测测试文件 SHA-256、异常原文见 [F05_red_evidence.txt](F05_red_evidence.txt)。该文件在修改两个生产文件之前已保存；当时两生产文件的 `git diff --stat` 为空，其 SHA-256 与开工值相同。

| 用例 | 旧生产代码的实际结果 | 修改后 |
| --- | --- | --- |
| 16 证据与申报不一致 | 未抛 ValueError，拒绝断言 RED | PASS |
| 17 证据一致 | GREEN 基线 | PASS |
| 18 peak=2000 > total=1000 | 未抛 ValueError，拒绝断言 RED | PASS |
| 19 日期 `1900-1-1x` | 未抛 ValueError，拒绝断言 RED | PASS |
| 19 日期 `20260102` | 未抛 ValueError，拒绝断言 RED | PASS |
| 20 peak_date 晚于 current.date | 未抛 ValueError，拒绝断言 RED | PASS |
| 21 证据为数组 `[1,2]` | 未抛 ValueError，拒绝断言 RED | PASS |
| a decimals=2 | `errors=[]`；目标拒绝断言 `AssertionError: []`，RED | PASS，拒绝不一致 |
| b decimals=0 | `errors=[]`，GREEN 基线 | PASS，仍零 errors |

`test_report_facts.py` 在旧生产代码下 exit=1，明确记录 6/41 个独立失败（用例 19 拆为两个 tempdir）。decimals 收集器逐案使用相同夹具；为继续采集 b，它捕获 a 的预期 AssertionError 后 exit=0，此收集器退出码不等于 a 通过。新用例与断言在转 GREEN 时未再修改。

## ④ §0.8 定向测试结果尾行

全部 9 项实际执行并 exit=0。设置 `PYTHONDONTWRITEBYTECODE=1`，避免子进程写字节码；正式验证阶段使用临时目录 `/private/tmp/f05-mpl-__0ifwi4` 作为 Matplotlib 缓存。RED 阶段出现默认缓存目录不可写提示，Matplotlib 自动转临时目录，a/b 均完成。图表测试中的字体替代提示未导致失败，无验收项跳过。

```text
$ PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/f05-mpl-__0ifwi4 python3 -B scripts/tests/test_report_facts.py
PASS: R07 build/derive/发布闸 21 类、41 个独立用例
PASS: facts 宏渲染/附录B同源/G1集合gate(含entity_id主键)/G4宏名gate/G5手写检出/G2上界/G6归并时点/G7血缘提示，七契约全过
exit=0
```

```text
$ PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/f05-mpl-__0ifwi4 python3 -B scripts/tests/test_audit_release_gate.py
PASS: audit_release_gate 净室资产/哈希/CEX受益权/阴性结论/图表封口与负钳零/对抗复核否决/四查WARN拦截/双线阈值/嵌套未决暴露/静置仓全集对账/日级峰值口径闭环十一类契约全过
exit=0
```

```text
$ PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/f05-mpl-__0ifwi4 python3 -B scripts/tests/test_state_from_facts.py
PASS: D-05 state_from_facts compiler owns membership and raw-derived shares
exit=0
```

```text
$ PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/f05-mpl-__0ifwi4 python3 -B scripts/tests/test_a4_gate.py
a4_gate 契约测试全部通过（23 项）
exit=0
```

```text
$ PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/f05-mpl-__0ifwi4 python3 -B scripts/tests/test_repair_batch_d.py
BATCH D 全部通过
exit=0
```

```text
$ PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/f05-mpl-__0ifwi4 python3 -B scripts/tests/test_review_20260804_p105.py
PASS: F05 decimals 与链上观测不符拒
PASS: F05 decimals 一致放行（GREEN→GREEN）
PASS: P1-05 mandatory new-analysis vs independent-audit release profiles
exit=0
```

```text
$ PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/f05-mpl-__0ifwi4 python3 -B scripts/tests/test_stage2_closeout.py
stage2_closeout: 28/28 PASS
exit=0
```

```text
$ PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/f05-mpl-__0ifwi4 python3 -B scripts/tests/test_figures_from_facts.py
PASS: figures_from_facts fig1白名单/legacy销毁键/legend receipt/burn豁免/overlay组成/价格绑定/flow宏同源/check终值对账全过
exit=0
```

```text
$ PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/f05-mpl-__0ifwi4 python3 -B scripts/tests/invariant_scan.py
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
exit=0
```

额外原始核验：

```text
$ git diff --check
exit=0
```

`invariant_scan.py` 未报缺项，因此 `invariant_manifest.json` 未改；`contract_manifest.json` 未改。全量 `run_all.py` 与 reseal 全套未运行，仍属调度方验收范围。

## ⑤ §1.1 三个字节数

开工与收工均为 `8021 / 930061 / 8798`。使用工单 F06 §1.1 指定的元数据命令：

```text
$ stat -f %z SKILL.md
8021

$ find references -name '*.md' -print0 | xargs -0 stat -f %z | awk '{s+=$1} END{print s}'
930061

$ stat -f %z commands-staging/*.md | awk '{s+=$1} END{print s}'
8798
```

只统计文件大小，不读取这些文档内容。

## ⑥ git diff --stat

```text
$ git diff --stat
 scripts/report/audit_release_gate.py       | 28 +++++++++++++++++++++
 scripts/report/facts_gate.py               | 25 ++++++++++++++++++-
 scripts/tests/test_audit_release_gate.py   |  4 ++-
 scripts/tests/test_repair_batch_d.py       |  2 +-
 scripts/tests/test_report_facts.py         | 39 ++++++++++++++++++++++++++++--
 scripts/tests/test_review_20260804_p105.py | 20 +++++++++++++--
 6 files changed, 111 insertions(+), 7 deletions(-)
```

此统计为已跟踪文件的差异。另有本目录两个新建白名单交付文件：`F05_done.md`、`F05_red_evidence.txt`；未执行 git add。

## ⑦ 开工核实、实际落点、差异与停工点

无停工点。除当前用户提示已经明确的 HEAD 规则，以及工单 §2.3 明示须现场定位的行号外，无施工范围或行为偏离。

固定锚点的 `grep -n -F` 实证如下，全部唯一且与施工前工单行号一致：

```text
$ grep -n -F -- '  peak_overrides: {eid: {peak_raw, peak_date, evidence: {path, sha256, note?}}}' scripts/report/facts_gate.py
65:  peak_overrides: {eid: {peak_raw, peak_date, evidence: {path, sha256, note?}}}
PASS
$ grep -n -F -- 'import argparse' scripts/report/facts_gate.py
72:import argparse
PASS
$ grep -n -F -- 'from pathlib import Path' scripts/report/facts_gate.py
78:from pathlib import Path
PASS
$ grep -n -F -- '        if cur > peak:' scripts/report/facts_gate.py
198:        if cur > peak:
PASS
$ grep -n -F -- '            errors.append(f"G3 {eid} current_raw > peak_raw（{cur} > {peak}）")' scripts/report/facts_gate.py
199:            errors.append(f"G3 {eid} current_raw > peak_raw（{cur} > {peak}）")
PASS
$ grep -n -F -- '            ev = ov.get("evidence")' scripts/report/facts_gate.py
408:            ev = ov.get("evidence")
PASS
$ grep -n -F -- '                                                "sha256": str(ev["sha256"]).lower()}}' scripts/report/facts_gate.py
420:                                                "sha256": str(ev["sha256"]).lower()}}
PASS
$ grep -n -F -- '        if int(peak) < int(current):' scripts/report/facts_gate.py
431:        if int(peak) < int(current):
PASS
$ grep -n -F -- 'def _r07_build_cases():' scripts/tests/test_report_facts.py
77:def _r07_build_cases():
PASS
$ grep -n -F -- '        evidence = _r07_write(root, "peak_evidence.json", {"note": "observed peak"})' scripts/tests/test_report_facts.py
153:        evidence = _r07_write(root, "peak_evidence.json", {"note": "observed peak"})
PASS
$ grep -n -F -- '    print(f"PASS: R07 build/derive/发布闸 15 类、{len(results)} 个独立用例", flush=True)' scripts/tests/test_report_facts.py
293:    print(f"PASS: R07 build/derive/发布闸 15 类、{len(results)} 个独立用例", flush=True)
PASS
$ grep -n -F -- '        "checks": {"fot": {"status": "clean"}}})' scripts/tests/test_repair_batch_d.py
984:        "checks": {"fot": {"status": "clean"}}})
PASS
$ grep -n -F -- 'def add_new_analysis_distribution(root: Path, report: Path) -> None:' scripts/tests/test_review_20260804_p105.py
141:def add_new_analysis_distribution(root: Path, report: Path) -> None:
PASS
$ grep -n -F -- '    fixture.build_facts_from_ledgers(root, symbol="FX")' scripts/tests/test_review_20260804_p105.py
214:    fixture.build_facts_from_ledgers(root, symbol="FX")
PASS
$ grep -n -F -- 'def build_facts_from_ledgers(root, *, symbol="TT", decimals=0, labels=None, peak_date="2026-01-01"):' scripts/tests/test_audit_release_gate.py
202:def build_facts_from_ledgers(root, *, symbol="TT", decimals=0, labels=None, peak_date="2026-01-01"):
PASS
ANCHOR_FAILURES=[]
```

工单允许现场定位的发布闸锚点：

```text
$ grep -n -F -e 'def check_facts_vs_ledgers(' -e 'errors.append("facts.provenance（inputs/state_source/peak_overrides 的 sha 或绑定）与当前案内实物不一致——输入已变，须重新 build")' -e '            check_facts_vs_ledgers(case_dir, data["facts.json"], errors,' -e '                                   receipt=data.get("figure2_check_receipt.json"))' scripts/report/audit_release_gate.py
1532:def check_facts_vs_ledgers(case_dir: Path, facts, errors: list[str], receipt=None):
1583:        errors.append("facts.provenance（inputs/state_source/peak_overrides 的 sha 或绑定）与当前案内实物不一致——输入已变，须重新 build")
1881:            check_facts_vs_ledgers(case_dir, data["facts.json"], errors,
1882:                                   receipt=data.get("figure2_check_receipt.json"))
```

- 开工 `check_facts_vs_ledgers` 为 1532–1583 行，末行锚为 1583；施工后仍为 1532–1583 行。
- 开工 `_run` 的共享函数调用块为 1881–1882；施工后为 1908–1909，新增 decimals 调用在 1910，处于同一个 `profile == "new-analysis" and "facts.json" in data` 块内。
- 新增 `check_facts_decimals` 从 1586 行开始。

```text
$ grep -n -F -e 'def check_facts_vs_ledgers(' -e 'errors.append("facts.provenance（inputs/state_source/peak_overrides 的 sha 或绑定）与当前案内实物不一致——输入已变，须重新 build")' -e 'def check_facts_decimals(' -e '            check_facts_vs_ledgers(case_dir, data["facts.json"], errors,' -e '                                   receipt=data.get("figure2_check_receipt.json"))' -e '            check_facts_decimals(case_dir, data["facts.json"], data.get("accounting_mode.json"), errors)' scripts/report/audit_release_gate.py
1532:def check_facts_vs_ledgers(case_dir: Path, facts, errors: list[str], receipt=None):
1583:        errors.append("facts.provenance（inputs/state_source/peak_overrides 的 sha 或绑定）与当前案内实物不一致——输入已变，须重新 build")
1586:def check_facts_decimals(case_dir: Path, facts, accounting, errors: list[str]):
1908:            check_facts_vs_ledgers(case_dir, data["facts.json"], errors,
1909:                                   receipt=data.get("figure2_check_receipt.json"))
1910:            check_facts_decimals(case_dir, data["facts.json"], data.get("accounting_mode.json"), errors)
```

p105 开工 `nl -ba` 核实：已有 new-analysis 零错误断言在 261 行；既有 independent-audit 绿例在 266–269，main 收尾 print/return 在 271–272。新增两个独立 tempdir 用例插在原 270 行空白之后、原 271 行 print 之前；实际 a 用例为 271–277，b 为 279–285，原 main 收尾移至 287–288。

```text
$ nl -ba scripts/tests/test_review_20260804_p105.py | sed -n '254,291p'
   254	def main():
   255	    with tempfile.TemporaryDirectory() as td:
   256	        root = Path(td)
   257	        report = fixture.build_case(root, historical=False)
   258	        for name in AUDIT_ONLY:
   259	            (root / name).unlink(missing_ok=True)
   260	        add_new_analysis_distribution(root, report)
   261	        assert not fixture.gate.run(root, report, profile="new-analysis")
   262	        audit_errors = fixture.gate.run(root, report, profile="independent-audit")
   263	        assert any("audit_input_manifest.json" in x for x in audit_errors)
   264	        assert any("claim_registry.json" in x for x in audit_errors)
   265	
   266	    with tempfile.TemporaryDirectory() as td:
   267	        root = Path(td)
   268	        report = fixture.build_case(root, historical=False)
   269	        assert not fixture.gate.run(root, report, profile="independent-audit")
   270	
   271	    with tempfile.TemporaryDirectory() as td:
   272	        root = Path(td)
   273	        report = fixture.build_case(root, historical=False)
   274	        add_new_analysis_distribution(root, report, decimals=2)
   275	        errors = fixture.gate.run(root, report, profile="new-analysis")
   276	        assert any("与链上观测 0 不一致" in error for error in errors), errors
   277	        print("PASS: F05 decimals 与链上观测不符拒", flush=True)
   278	
   279	    with tempfile.TemporaryDirectory() as td:
   280	        root = Path(td)
   281	        report = fixture.build_case(root, historical=False)
   282	        add_new_analysis_distribution(root, report, decimals=0)
   283	        errors = fixture.gate.run(root, report, profile="new-analysis")
   284	        assert errors == [], errors
   285	        print("PASS: F05 decimals 一致放行（GREEN→GREEN）", flush=True)
   286	
   287	    print("PASS: P1-05 mandatory new-analysis vs independent-audit release profiles")
   288	    return 0
   289	
   290	
   291	if __name__ == "__main__":
```

其他开工事实核实：

- `shared_release_receipt.py:138–142` 通过 `recon_adapter_for` 归一链族；`accounting_gate_sol.py:137` 与 `test_repair_batch_d.py:976` 的真实链名均为 `solana`。
- `shared_release_receipt.py:559–567` 的 `_bound_json_input` 返回绑定 JSON；593 行有同款 config 调用，1445 行按检查名存入 receipts，1508 行返回 receipts。新函数取 `witness.receipts["balance"]` 绑定的 config。
- `audit_release_gate.py:111–118` 使用已有缓存；开工 `_run` 在 1842 行先进行对账检查，再在 1881–1882 行检查 facts。decimals 函数复用已有 witness。
- `test_repair_batch_d.py:893` 观测夹具 decimals=0，984 行原 checks 缺 decimals；仅按工单在该行补 0。
- `entity_source_trace.py:639` 的 current 锚未传 date；`wave_scan.py:87–88` 以 `%Y-%m-%d` 生成日期。
- facts 生成仍只读取案内输入；未加入时钟、时间戳或写盘行为，未改变 `FACTS_PROVENANCE_SCHEMA`。

对实际差异按施工前行区间机械核验；共享函数及受保护函数源文本另做逐字比较：

```text
scripts/report/facts_gate.py: allowed-region PASS [{"op": "replace", "old_zero_based": [64, 65], "new_zero_based": [64, 65]}, {"op": "insert", "old_zero_based": [72, 72], "new_zero_based": [72, 73]}, {"op": "insert", "old_zero_based": [199, 199], "new_zero_based": [200, 202]}, {"op": "insert", "old_zero_based": [417, 417], "new_zero_based": [420, 429]}, {"op": "insert", "old_zero_based": [430, 430], "new_zero_based": [442, 453]}]
facts macro/render + _load_case_json/_raw_str/build_main byte-identical PASS
scripts/report/audit_release_gate.py: allowed-region PASS [{"op": "insert", "old_zero_based": [1585, 1585], "new_zero_based": [1585, 1612]}, {"op": "insert", "old_zero_based": [1882, 1882], "new_zero_based": [1909, 1910]}]
check_facts_vs_ledgers byte-identical PASS sha256=267aca2b44aac0446cff0559106992f0aa589f398afd66c07274022d0e786fd8
scripts/tests/test_report_facts.py: allowed-region PASS [{"op": "replace", "old_zero_based": [152, 153], "new_zero_based": [152, 153]}, {"op": "insert", "old_zero_based": [291, 291], "new_zero_based": [291, 326]}, {"op": "replace", "old_zero_based": [292, 293], "new_zero_based": [327, 328]}]
scripts/tests/test_audit_release_gate.py: allowed-region PASS [{"op": "replace", "old_zero_based": [208, 209], "new_zero_based": [208, 211]}]
scripts/tests/test_repair_batch_d.py: allowed-region PASS [{"op": "replace", "old_zero_based": [983, 984], "new_zero_based": [983, 984]}]
scripts/tests/test_review_20260804_p105.py: allowed-region PASS [{"op": "replace", "old_zero_based": [140, 141], "new_zero_based": [140, 141]}, {"op": "replace", "old_zero_based": [213, 214], "new_zero_based": [213, 214]}, {"op": "insert", "old_zero_based": [270, 270], "new_zero_based": [270, 286]}]
All edited source regions PASS
```

共享 `check_facts_vs_ledgers` 源文本 SHA-256 为 `267aca2b44aac0446cff0559106992f0aa589f398afd66c07274022d0e786fd8`，前后一致。宏/渲染及 `_load_case_json`、`_raw_str`、`build_main` 前后一致；发布闸其他已有段未改。其余代码/测试文件仅改指定位置。

存量迁移及已裁决边界沿用工单，不对案库执行迁移、不改调度方的 `code_change_pending.md`：

- 已使用 peak_overrides 的案须按序改证据 JSON、重算 SHA-256、更新所有对应 override 的 sha/path，再重建 facts、图 2 收据、A4、stage2 收口收据、A5。
- P8：上界采用当前总供应；真实历史峰值超过当前供应的案会被保守阻断。
- 日期上界仅在 current 锚显式给出 date 时生效；未新增日期下界。
- override 仅核证据值与申报一致；峰值本身的重放不在本单。
- decimals 链上观测核验仅挂发布闸 new-analysis 分支，未加入 derive_facts 或共享 check_facts_vs_ledgers。

## ⑧ 禁读披露

会话启动上下文自动提供了记忆摘要，已在开工时披露；本轮未主动打开任何 `~/.codex/` 文件，也未运行插件/记忆搜索。未直接读取 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、任何历史 maintenance 目录、`/Users/uravvv/Desktop` 或 `/Users/uravvv/Documents`。maintenance 内容读取限于本次 repair-20260918-p0-f04-f07 目录的工单、施工提示词和本轮产物。文档目录仅执行获准的元数据统计；指定测试/守卫按用户授权运行。

全程离线执行本地命令。未 commit、push、stash、checkout、reset，未部署 `~/.claude/commands/`，未修改白名单外仓库文件。
