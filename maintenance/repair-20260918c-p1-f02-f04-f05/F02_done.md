# 施工 F02：完成

已按工单 v2 §2.1–§2.6 落地。流通量声明经过校验进入 facts.token，发布闸按原有整 token 比对重算，closeout 记录口径并沿用原阈值。施工范围为四个代码/测试文件及本目录两份交付文件。

**① 开工基线与 §0.1 原始输出**

工作目录：`/Users/uravvv/.claude/skills/token-chip-analysis`。

```console
$ git rev-parse HEAD
830ce9f8323bb57ef7d896eb4608f84d866ca796
```

```console
$ git branch --show-current
main
```

```console
$ git status --short
```

输出为空，exit=0。

```console
$ git diff --stat 8b041842 HEAD -- scripts/report/facts_gate.py scripts/tests/test_report_facts.py references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
```

输出为空，exit=0。

派工提示词中的累计范围也已核对，仅含 F04/F05 已入库的六个文件：

```console
$ git diff --stat 8b041842 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
 scripts/lib/net.py                           |  5 +-
 scripts/lib/rpc_batch.py                     | 10 ++--
 scripts/prices/price_check.py                | 11 ++++
 scripts/report/stage2_closeout.py            | 63 ++++++++++++++++++++--
 scripts/tests/test_batch1_rpc_attestation.py | 71 ++++++++++++++++++++++++
 scripts/tests/test_stage2_closeout.py        | 80 ++++++++++++++++++++++++++--
 6 files changed, 226 insertions(+), 14 deletions(-)
```

开工 invariant_scan（exit=0）：

```console
$ python3 -B scripts/tests/invariant_scan.py
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
```

**② §2 各处 git diff 原文**

```diff
diff --git a/scripts/report/facts_gate.py b/scripts/report/facts_gate.py
index 3a1735d..7d52a25 100644
--- a/scripts/report/facts_gate.py
+++ b/scripts/report/facts_gate.py
@@ -8,6 +8,7 @@
 facts.json schema（每案一份，阶段 3 结束时由 build 子命令从三账生成，禁手抄；数值一律**原始整数字符串**）：
 {
   "token": {"symbol": "QUQ", "decimals": 18, "total_supply_raw": "1000...0"},
+           # 可选（F02）：circulating_supply_raw + circulating_supply_source {asof, source}，来自 facts_inputs.circulating_supply
   "entities": {
     "e_big1": {"label": "大庄#1(bot体系)",
                "addresses": ["0x完整地址", ...],
@@ -64,6 +65,7 @@ state_source.facts_inputs schema：
   entity_labels: {eid: label}（必填、非空、覆盖全部实体）
   peak_overrides: {eid: {peak_raw, peak_date, evidence: {path, sha256}}}，证据 JSON 须为 {entity_id: {peak_raw, peak_date}} 与申报相等
       （可选，优先于 provenance 锚点，证据须为案根常规文件）
+  circulating_supply: {raw, asof, source}（可选；raw 正整数串且 ≤ total_supply_raw、asof 严格 YYYY-MM-DD、source 非空口径说明；写入 token.circulating_supply_raw/circulating_supply_source；扁平键 circulating_supply_raw 拒）
   merge_evidence: {eid: {earliest, note}}（可选）
   role_notes: {eid: {addr: note}}（可选）
   metrics: {mid: {...}}（可选；对象且每项为对象）；dual_basis: {}（可选；对象）
@@ -378,6 +380,28 @@ def derive_facts(case_dir, *, exploration=False):
     dual_basis = fi.get("dual_basis")
     if "dual_basis" in fi and not isinstance(dual_basis, dict):
         raise ValueError("facts_inputs.dual_basis 须为对象")
+    if "circulating_supply_raw" in fi:
+        raise ValueError("facts_inputs.circulating_supply_raw 键名错位——流通量须写成 "
+                         "circulating_supply: {raw, asof, source}")
+    circ = fi.get("circulating_supply")
+    circulating = None
+    if circ is not None:
+        if not isinstance(circ, dict):
+            raise ValueError("facts_inputs.circulating_supply 须为对象 {raw, asof, source}")
+        circ_raw = _raw_str(circ.get("raw"), "facts_inputs.circulating_supply.raw")
+        if not 0 < int(circ_raw) <= int(total_raw):
+            raise ValueError(f"facts_inputs.circulating_supply.raw {circ_raw} 须在 (0, total_supply_raw={total_raw}] 内")
+        asof = str(circ.get("asof") or "").strip()
+        try:
+            asof_ok = _dt.date.fromisoformat(asof).isoformat() == asof
+        except ValueError:
+            asof_ok = False
+        if not asof_ok:
+            raise ValueError(f"facts_inputs.circulating_supply.asof {asof!r} 非 YYYY-MM-DD")
+        src = circ.get("source")
+        if not isinstance(src, str) or not src.strip():
+            raise ValueError("facts_inputs.circulating_supply.source 须为非空口径说明（如 'CoinGecko circulating 2026-09-14'）")
+        circulating = {"raw": circ_raw, "asof": asof, "source": src.strip()}
 
     members = data["membership_ledger.json"]
     members = members.get("entries", members.get("entities", []))
@@ -474,7 +498,11 @@ def derive_facts(case_dir, *, exploration=False):
     inputs = {n: {"sha256": _sha256_path(case_dir / n)} for n in FACTS_LEDGER_INPUTS}
     if ledger is not None:
         inputs["provenance_ledger.json"] = {"sha256": _sha256_path(ledger_path)}
-    facts = {"token": {"symbol": symbol, "decimals": decimals, "total_supply_raw": total_raw},
+    token = {"symbol": symbol, "decimals": decimals, "total_supply_raw": total_raw}
+    if circulating is not None:
+        token["circulating_supply_raw"] = circulating["raw"]
+        token["circulating_supply_source"] = {"asof": circulating["asof"], "source": circulating["source"]}
+    facts = {"token": token,
              "entities": entities, "metrics": metrics}
     if dual_basis is not None:
         facts["dual_basis"] = dual_basis
diff --git a/scripts/report/stage2_closeout.py b/scripts/report/stage2_closeout.py
index 9330f06..3f74ea0 100644
--- a/scripts/report/stage2_closeout.py
+++ b/scripts/report/stage2_closeout.py
@@ -207,6 +207,8 @@ def flow_selection_errors(facts, flow):
         notes.append("NOTE: 未声明流通量，门槛仅按总供应判")
     else:
         circulating = int(circulating)
+        src = facts.get("token", {}).get("circulating_supply_source") or {}
+        notes.append(f"NOTE: 流通量 {circulating}（口径 {src.get('source')}，{src.get('asof')}）")
     required = set()
     for entity_id, entity in facts["entities"].items():
         if str(entity.get("label") or "").strip().startswith(("项目方", "大庄")):
diff --git a/scripts/tests/test_report_facts.py b/scripts/tests/test_report_facts.py
index fbcb550..3d048e0 100644
--- a/scripts/tests/test_report_facts.py
+++ b/scripts/tests/test_report_facts.py
@@ -324,8 +324,44 @@ def _r07_build_cases():
     run("20 F05 peak_date 晚于当前锚点日拒", f05_after_current)
     run("21 F05 证据非对象拒", lambda root: f05_override(
         root, "150", "2026-01-02", [1, 2], "证据内容"))
+
+    def circ(root, value, needle=None):
+        edit(root, "state_source.json", lambda obj: obj["facts_inputs"].update(value))
+        if needle:
+            reject(root, needle)
+            return None
+        return build(root)
+
+    def circ_green(root):
+        facts = circ(root, {"circulating_supply": {"raw": "400", "asof": "2026-01-03", "source": "test circulating"}})
+        assert facts["token"]["circulating_supply_raw"] == "400", facts
+        assert facts["token"]["circulating_supply_source"] == {"asof": "2026-01-03", "source": "test circulating"}, facts
+        assert set(facts["token"]) == {"symbol", "decimals", "total_supply_raw",
+                                       "circulating_supply_raw", "circulating_supply_source"}, facts
+        errors = []
+        gate.check_facts_vs_ledgers(root, facts, errors)
+        assert errors == [], errors
+
+    def circ_hand_edit(root):
+        facts = build(root)
+        facts["token"]["circulating_supply_raw"] = "400"
+        _r07_write(root, "facts.json", facts)
+        errors = []
+        gate.check_facts_vs_ledgers(root, facts, errors)
+        assert any("facts.token" in error for error in errors), errors
+
+    run("22 F02 流通量声明→token 带字段、发布重算一致", circ_green)
+    for value, needle in (
+            ({"circulating_supply": {"raw": "2000", "asof": "2026-01-03", "source": "x"}}, "total_supply_raw"),
+            ({"circulating_supply": {"raw": "0", "asof": "2026-01-03", "source": "x"}}, "total_supply_raw"),
+            ({"circulating_supply": {"raw": "400", "asof": "20260103", "source": "x"}}, "非 YYYY-MM-DD"),
+            ({"circulating_supply": {"raw": "400", "asof": "2026-01-03", "source": " "}}, "source"),
+            ({"circulating_supply": "400"}, "须为对象"),
+            ({"circulating_supply_raw": "400"}, "键名错位")):
+        run("23 F02 流通量非法拒 " + needle, lambda root, v=value, n=needle: circ(root, v, n))
+    run("24 F02 手补 token.circulating_supply_raw 无声明→闸拒（GREEN→GREEN）", circ_hand_edit)
     assert not failures, f"R07 失败 {len(failures)}/{len(results)}: {failures}"
-    print(f"PASS: R07 build/derive/发布闸 21 类、{len(results)} 个独立用例", flush=True)
+    print(f"PASS: R07 build/derive/发布闸 24 类、{len(results)} 个独立用例", flush=True)
 
 
 def main():
diff --git a/scripts/tests/test_stage2_closeout.py b/scripts/tests/test_stage2_closeout.py
index d212b0d..9f6111f 100644
--- a/scripts/tests/test_stage2_closeout.py
+++ b/scripts/tests/test_stage2_closeout.py
@@ -672,6 +672,29 @@ def price_receipt_content_enforced(cases):
     check_result(case)
 
 
+def circulating_supply_producer_to_consumer(cases):
+    """F02：流通量由 state_source 声明 → facts_gate.derive_facts 产出 → flow_selection_errors 按流通量分母命中必画。
+    用 test_report_facts._r07_case（total 1000 / e1 current 100 = 10%，总量分支不命中；声明流通量 400 → 25% 命中）；
+    公共 closeout seed 为 100/100 不可辨，故独立建案。不落盘 facts。"""
+    import facts_gate
+    import stage2_closeout as closeout
+    from test_report_facts import _r07_case
+    root = Path(tempfile.mkdtemp(prefix="f02-circ-", dir="/private/tmp"))
+    _r07_case(root)
+    baseline = facts_gate.derive_facts(root)
+    assert "circulating_supply_raw" not in baseline["token"], baseline["token"]
+    errors, notes = closeout.flow_selection_errors(baseline, {"eligible_entity_ids": [], "charts": []})
+    assert not any("包含下限" in e for e in errors), errors
+    assert any("未声明流通量" in n for n in notes), notes
+    update(root, "state_source.json", lambda s: s["facts_inputs"].update(
+        circulating_supply={"raw": "400", "asof": "2026-01-03", "source": "fixture circulating"}))
+    facts = facts_gate.derive_facts(root)
+    assert facts["token"]["circulating_supply_raw"] == "400", facts["token"]
+    errors, notes = closeout.flow_selection_errors(facts, {"eligible_entity_ids": [], "charts": []})
+    assert any("包含下限 ['e1']" in e for e in errors), errors
+    assert any("口径 fixture circulating" in n for n in notes), notes
+
+
 def facts_vs_ledgers_rejects_hand_edit(cases):
     case = cases.fresh()
     update(case, "facts.json", lambda obj: obj["entities"]["e1"].update(current_raw="90"))
@@ -698,7 +721,7 @@ TESTS = [dryrun_profile_exempts_stage3_artifacts, only_findings_changed_is_rejec
          downstream_check_cli_exit3, amendments_chain_gap_rejected,
          workorder_reference_contracts, receipt_shape_and_fill_nulls,
          caption_raw_rounding_and_pure_series_errors, amend_rechecks_all_and_is_atomic,
-         facts_vs_ledgers_rejects_hand_edit, price_receipt_content_enforced]
+         facts_vs_ledgers_rejects_hand_edit, price_receipt_content_enforced, circulating_supply_producer_to_consumer]
 
 
 def main():
```

**③ RED 摘要（逐例）**

生产代码未修改时，按新增用例逐例独立 try/except 捕获；用例 22 的 KeyError 未截断后续六个非法输入变体。原有 run() 的捕获列表未改动。完整证据见 [F02_red_evidence.txt](F02_red_evidence.txt)。

```text
F02 RED evidence — independent per-case capture before production edits
HEAD: 830ce9f8323bb57ef7d896eb4608f84d866ca796
git diff -- scripts/report/facts_gate.py scripts/report/stage2_closeout.py: (empty)
scripts/report/facts_gate.py sha256: f898ac87986351946e66d7bd6c198313dbb76a0c70dc51b9ab441e7f38fb9dac
scripts/report/stage2_closeout.py sha256: a889e6c75f94e08cbd274ce5f92830ff4891d461b4da991c08da10e447ebd37e
Method: execute the newly added test bodies; replace only nested run in memory with independent try/except capture. No test-file catch-list changes. Temporary fixtures are retained, with no cleanup deletion.
RED: 22 F02 流通量声明→token 带字段、发布重算一致 | KeyError: 'circulating_supply_raw'
RED: 23.1 23 F02 流通量非法拒 total_supply_raw input={"circulating_supply": {"raw": "2000", "asof": "2026-01-03", "source": "x"}} | AssertionError: derive_facts 应拒绝该输入: total_supply_raw
RED: 23.2 23 F02 流通量非法拒 total_supply_raw input={"circulating_supply": {"raw": "0", "asof": "2026-01-03", "source": "x"}} | AssertionError: derive_facts 应拒绝该输入: total_supply_raw
RED: 23.3 23 F02 流通量非法拒 非 YYYY-MM-DD input={"circulating_supply": {"raw": "400", "asof": "20260103", "source": "x"}} | AssertionError: derive_facts 应拒绝该输入: 非 YYYY-MM-DD
RED: 23.4 23 F02 流通量非法拒 source input={"circulating_supply": {"raw": "400", "asof": "2026-01-03", "source": " "}} | AssertionError: derive_facts 应拒绝该输入: source
RED: 23.5 23 F02 流通量非法拒 须为对象 input={"circulating_supply": "400"} | AssertionError: derive_facts 应拒绝该输入: 须为对象
RED: 23.6 23 F02 流通量非法拒 键名错位 input={"circulating_supply_raw": "400"} | AssertionError: derive_facts 应拒绝该输入: 键名错位
GREEN: 24 F02 手补 token.circulating_supply_raw 无声明→闸拒（GREEN→GREEN）
GREEN: §2.6 前半 — 无流通量新键、未命中总量下限、NOTE 未声明流通量
Fixture: total=1000, current=100, label=大庄#1, peak=150, mode=formal, peak_overrides={}
RED: §2.6 后半 — 声明后 producer→consumer | KeyError: 'circulating_supply_raw'
Compatibility fixture retained for post-change comparison: /private/tmp/f02-compat-m2k_7ln4
SUMMARY: 22 RED; 23 six variants each RED; 24 GREEN; §2.6 prefix GREEN / declaration suffix RED. Expected RED distribution verified.
```

**④ §0.8 定向测试结果尾行**

以下 11 条命令全部首次执行 exit=0；未触发 F05 §0.8 的 `data_broken: '_items'` 冷字体缓存重跑。完整日志保留在 `/private/tmp/f02-tests-_ihxqwvs/`，以下保留各命令结果尾行。

```console
$ python3 -B scripts/tests/test_report_facts.py
PASS: facts 宏渲染/附录B同源/G1集合gate(含entity_id主键)/G4宏名gate/G5手写检出/G2上界/G6归并时点/G7血缘提示，七契约全过
```

```console
$ python3 -B scripts/tests/test_stage2_closeout.py
stage2_closeout: 30/30 PASS
```

```console
$ python3 -B scripts/tests/test_audit_release_gate.py
PASS: audit_release_gate 净室资产/哈希/CEX受益权/阴性结论/图表封口与负钳零/对抗复核否决/四查WARN拦截/双线阈值/嵌套未决暴露/静置仓全集对账/日级峰值口径闭环十一类契约全过
```

```console
$ python3 -B scripts/tests/test_state_from_facts.py
PASS: D-05 state_from_facts compiler owns membership and raw-derived shares
```

```console
$ python3 -B scripts/tests/test_build_html.py
PASS: build_html 九条契约全过（含 analysis/legacy 模式边界）
```

```console
$ python3 -B scripts/tests/test_repair_batch_c.py
PASS: repair batch C (F-05+F-04+fixround1+fixround2) 259 checks
```

```console
$ python3 -B scripts/tests/test_repair_batch_d.py
BATCH D 全部通过
```

```console
$ python3 -B scripts/tests/test_figures_from_facts.py
PASS: figures_from_facts fig1白名单/legacy销毁键/legend receipt/burn豁免/overlay组成/价格绑定/flow宏同源/check终值对账全过
```

```console
$ python3 -B scripts/tests/test_a4_gate.py
a4_gate 契约测试全部通过（23 项）
```

```console
$ python3 -B scripts/tests/test_review_20260804_p105.py
PASS: P1-05 mandatory new-analysis vs independent-audit release profiles
```

```console
$ python3 -B scripts/tests/invariant_scan.py
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
```

新增用例及同版本 CLI build 幂等的原始 PASS 行（行号为测试日志行号）：

```text
1:ok    R07 1 derive 绿例
2:ok    R07 2 CLI build 幂等
42:ok    R07 22 F02 流通量声明→token 带字段、发布重算一致
43:ok    R07 23 F02 流通量非法拒 total_supply_raw
44:ok    R07 23 F02 流通量非法拒 total_supply_raw
45:ok    R07 23 F02 流通量非法拒 非 YYYY-MM-DD
46:ok    R07 23 F02 流通量非法拒 source
47:ok    R07 23 F02 流通量非法拒 须为对象
48:ok    R07 23 F02 流通量非法拒 键名错位
49:ok    R07 24 F02 手补 token.circulating_supply_raw 无声明→闸拒（GREEN→GREEN）
50:PASS: R07 build/derive/发布闸 24 类、49 个独立用例
51:PASS: facts 宏渲染/附录B同源/G1集合gate(含entity_id主键)/G4宏名gate/G5手写检出/G2上界/G6归并时点/G7血缘提示，七契约全过
```

**⑤ §1.1 文档字节数**

开工与完工一致：SKILL.md 为 8021，references Markdown 合计为 930076，commands-staging Markdown 合计为 8798。只访问文件元数据。

```console
$ stat -f %z SKILL.md
8021
```

```console
$ find references -name '*.md' -print0 | xargs -0 stat -f %z | awk '{s+=$1} END{print s}'
930076
```

```console
$ stat -f %z commands-staging/*.md | awk '{s+=$1} END{print s}'
8798
```

**⑥ git diff --stat 与白名单**

```console
$ git diff --stat
 scripts/report/facts_gate.py          | 30 ++++++++++++++++++++++++++-
 scripts/report/stage2_closeout.py     |  2 ++
 scripts/tests/test_report_facts.py    | 38 ++++++++++++++++++++++++++++++++++-
 scripts/tests/test_stage2_closeout.py | 25 ++++++++++++++++++++++-
 4 files changed, 92 insertions(+), 3 deletions(-)
```

上述 diff 只含四个白名单文件；新建的未跟踪交付文件为本目录的 F02_done.md 与 F02_red_evidence.txt，未计入 git diff --stat。`git diff --check` 输出为空、exit=0。HEAD 与分支保持开工记录不变。

**⑦ 与工单差异、锚点与边界核实**

无施工方案差异、无停工点。§2.2–§2.6 的代码块已与工单逐字核对；§2.1 两处 docstring、24 类统计文案和 TESTS 追加均按工单落地。

施工前锚点核验原始输出：

```text
PASS: scripts/report/facts_gate.py expected=10
10:  "token": {"symbol": "QUQ", "decimals": 18, "total_supply_raw": "1000...0"},
PASS: scripts/report/facts_gate.py expected=66
66:      （可选，优先于 provenance 锚点，证据须为案根常规文件）
PASS: scripts/report/facts_gate.py expected=380
380:        raise ValueError("facts_inputs.dual_basis 须为对象")
PASS: scripts/report/facts_gate.py expected=477
477:    facts = {"token": {"symbol": symbol, "decimals": decimals, "total_supply_raw": total_raw},
PASS: scripts/report/stage2_closeout.py expected=209
209:        circulating = int(circulating)
PASS: scripts/tests/test_report_facts.py expected=326
326:        root, "150", "2026-01-02", [1, 2], "证据内容"))
PASS: scripts/tests/test_report_facts.py expected=328
328:    print(f"PASS: R07 build/derive/发布闸 21 类、{len(results)} 个独立用例", flush=True)
PASS: scripts/tests/test_stage2_closeout.py expected=unique only
675:def facts_vs_ledgers_rejects_hand_edit(cases):
PASS: scripts/tests/test_stage2_closeout.py expected=unique only
701:         facts_vs_ledgers_rejects_hand_edit, price_receipt_content_enforced]
```

`test_stage2_closeout.py` 按工单只核唯一性：插入函数锚在施工前第 675 行，TESTS 末行锚在第 701 行；既有“NOTE: 未声明流通量”断言在第 272 行，手补 raw="50" 的直接消费者用例在第 285 行。`stage2_closeout.py` 前 236 行与 8b041842 逐字节相同。

`_r07_case` 静态与实跑均核实：total_supply_raw="1000"，e1.current_raw="100"，label="大庄#1"，peak_raw="150"，peak_date="2026-01-02"，peak_overrides={}，mode=formal。未声明时为总量 10%，没有命中选材下限；声明流通量 400 后为 25%，e1 必须入选。新用例使用独立 tempdir，公共 seed 保持原样。

禁止修改的代码片段核验：

```text
PASS: facts_gate.Facts unchanged
PASS: facts_gate.gate_check unchanged
PASS: facts_gate.build_main unchanged
PASS: facts_gate peak/override 407–460 unchanged
PASS: facts_gate provenance producer unchanged
PASS: flow_selection_errors threshold 210–216 unchanged
PASS: test_stage2_closeout.build_release_case unchanged
PASS: test_stage2_closeout.build_closeout_case unchanged
PASS: test_stage2_closeout.flow_items_compat_and_extra_allowed unchanged
BASELINE LINE: 272:    assert "NOTE: 未声明流通量" in detail(row), row
BASELINE LINE: 285:    lower = copy.deepcopy(facts); lower["token"]["circulating_supply_raw"] = "50"
```

未声明流通量的旧案兼容性实测：

```text
PASS: 未声明流通量时，仅 provenance.producer.sha256 变化，其他 derive 内容一致；token 原三键
PASS: 保留旧 facts.json，不重写文件，发布闸重算继续通过
old producer.sha256: f898ac87986351946e66d7bd6c198313dbb76a0c70dc51b9ab441e7f38fb9dac
new producer.sha256: ff77d3f81d57b61ac469e2a8f08d705cb596262421191996a0d49b41b7d188fa
```

旧案保留原 facts.json 无需迁移。若主动增加流通量声明并重 build，须依次刷新 A4、图 2 旁车/对账收据、工单与 closeout、A5/HTML 绑定；新增命中下限的实体须补流转图和报告引用。本段未执行迁移，未修改调度方维护的 code_change_pending.md。Q10/Q11 保持原范围：流通量不进入宏/G2 上界；其来源为人工第三方口径声明。

未运行 run_all.py、test_stage2_reseal.py；reseal 交调度方本机补验。全程离线，未 commit、push、部署，未使用 stash/checkout/reset，未主动执行文件删除。

**⑧ 禁读披露**

未读取 ~/.codex/（含 memories）、archive/、blind-reviews/、.staging_*、references/attic.md 内容、/Users/uravvv/Desktop 或 /Users/uravvv/Documents；references 字节统计仅访问元数据。未主动打开、阅读、复制或修改本工单目录以外的历史 maintenance 文件。历史 maintenance 依赖仅由测试子进程访问，包含工单明确豁免的 test_repair_batch_c.py importlib 加载；未借测试豁免主动读取历史文件。
