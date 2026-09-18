# 施工 F04：完成

执行工单：`maintenance/repair-20260918-p0-f04-f07/workorder_F04.md` v3；工作目录：`/Users/uravvv/.claude/skills/token-chip-analysis`。

## 1. 开工核验

派工基线为 `6749cbc`，实际开工 HEAD 为 `b1ccf2369c81e344c7be997779c90d15d0e8c6aa`，其直接父提交为 `6749cbc518c1cd43b96baa8963d42f4a6819c229`，符合提示词自身多一个提交的预期。

```text
$ git status --short

[stdout 为空；exit=0]

$ git diff --stat 311e6c4 HEAD -- scripts/report/audit_release_gate.py scripts/tests/test_repair_batch_c.py references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md

[stdout 为空；exit=0]

$ git log -2 --format='%H %s'
b1ccf2369c81e344c7be997779c90d15d0e8c6aa repair-20260918-p0-f04-f07: 施工 F04 提示词填派工 HEAD 6749cbc
6749cbc518c1cd43b96baa8963d42f4a6819c229 repair-20260918-p0-f04-f07: 工单 F04 v3(r2 两条验收说明)+r2 复核回复;F04 复核通过
```

开工全部定位锚 `grep -n -F` 唯一且行号吻合：

```text
$ grep -n -F '    _figure2_input_check(case_dir, d.get("series"), "series", errors)' scripts/report/audit_release_gate.py
1571:    _figure2_input_check(case_dir, d.get("series"), "series", errors)
anchor: PASS
$ grep -n -F '    _figure2_input_check(case_dir, d.get("facts"), "facts", errors)' scripts/report/audit_release_gate.py
1572:    _figure2_input_check(case_dir, d.get("facts"), "facts", errors)
anchor: PASS
$ grep -n -F 'def _r08_case_13():' scripts/tests/test_repair_batch_c.py
1465:def _r08_case_13():
anchor: PASS
$ grep -n -F 'def t_r08_nonfinite():' scripts/tests/test_repair_batch_c.py
1497:def t_r08_nonfinite():
anchor: PASS
$ grep -n -F '    _r08_case_13()' scripts/tests/test_repair_batch_c.py
1510:    _r08_case_13()
anchor: PASS
$ grep -n -F '        check("R08 同输入手写 PASS 基线消费者接受", errs == [], str(errs))' scripts/tests/test_repair_batch_c.py
1453:        check("R08 同输入手写 PASS 基线消费者接受", errs == [], str(errs))
anchor: PASS
$ grep -n -F 'def _r08_case_12():' scripts/tests/test_repair_batch_c.py
1430:def _r08_case_12():
anchor: PASS
$ grep -n -F 'def t_fc5_receipt_chain():' scripts/tests/test_repair_batch_c.py
1109:def t_fc5_receipt_chain():
anchor: PASS
```

开工三处字节数为 8021 / 930061 / 8798（只查文件大小元数据）。确认 `Path` 已于生产文件原第 16 行导入，既有 `run()` 原第 60–66 行自动前置解释器；新用例没有重复传入解释器。

## 2. 改动原始 diff（§2.1 / §2.2）

```diff
diff --git a/scripts/report/audit_release_gate.py b/scripts/report/audit_release_gate.py
index b0171fd..4ecafe8 100644
--- a/scripts/report/audit_release_gate.py
+++ b/scripts/report/audit_release_gate.py
@@ -1556,6 +1556,7 @@ def check_figure2_receipt(case_dir: Path, d: dict, errors: list[str]):
     N-C1（消化轮 2）：series 与 facts 两个输入实物**无条件**验（轮 1 的 series
     条件式验证＋facts 不验被盲审"纯手写收据"攻击穿透——path 写个不存在的名字
     就整段跳过）。
+    F04（7.2.1）：两输入实物在场时用 fig2_check_errors 重算，收据 PASS 不作为放行依据。
     """
     if d.get("schema") != FIGURE2_RECEIPT_SCHEMA:
         errors.append(f"figure2 收据 schema 必须是 {FIGURE2_RECEIPT_SCHEMA}")
@@ -1568,8 +1569,22 @@ def check_figure2_receipt(case_dir: Path, d: dict, errors: list[str]):
                       f"{FIGURE2_DEFAULT_TOL_PP}（判定翻转参数不得放宽）")
     if d.get("verdict") != "PASS":
         errors.append(f"figure2 对账收据 verdict={d.get('verdict')!r} 非 PASS")
+    n0 = len(errors)
     _figure2_input_check(case_dir, d.get("series"), "series", errors)
     _figure2_input_check(case_dir, d.get("facts"), "facts", errors)
+    if len(errors) > n0:
+        return
+    # F04（7.2.1）：收据只是留痕，发布期用同一只读纯校验器按案内实物重算——旧 PASS 收据
+    # （R08 修复前产出）与手改序列在这里失效；exploration/容差放宽已由上面三条拦。
+    series_p = case_dir / Path(str((d.get("series") or {}).get("path") or "")).name
+    facts_p = case_dir / Path(str((d.get("facts") or {}).get("path") or "")).name
+    try:
+        import figures_from_facts
+        errs, _okc = figures_from_facts.fig2_check_errors(facts_p, series_p, FIGURE2_DEFAULT_TOL_PP)
+    except (ValueError, OSError, KeyError, TypeError, AttributeError, OverflowError) as exc:
+        errors.append(f"figure2 发布期重算失败: {exc}")
+        return
+    errors.extend(f"figure2 发布期重算: {e}" for e in errs)
 
 
 def check_figure1_legend_receipt(case_dir: Path, d: dict, state: dict,
diff --git a/scripts/tests/test_repair_batch_c.py b/scripts/tests/test_repair_batch_c.py
index 9f8a027..e028b1f 100644
--- a/scripts/tests/test_repair_batch_c.py
+++ b/scripts/tests/test_repair_batch_c.py
@@ -1450,7 +1450,8 @@ def _r08_case_12():
         rcpt_path.write_text(json.dumps(handwritten), encoding="utf-8")
         errs = []
         gate.check_figure2_receipt(td, handwritten, errs)
-        check("R08 同输入手写 PASS 基线消费者接受", errs == [], str(errs))
+        check("R08 消费者对 NaN 手写收据直接拒（F04）",
+              any("重算失败" in x for x in errs), str(errs))
         p = run([fff, "check", "--facts", "facts.json", "--series", "ws.json"], td)
         out = p.stdout + p.stderr
         rcpt = json.loads(rcpt_path.read_text()) if rcpt_path.is_file() else {}
@@ -1494,6 +1495,92 @@ def _r08_case_13():
         check("R08 收据写入失败提示未更新", "收据未更新" in buf.getvalue(), detail)
 
 
+def _f04_case_1():
+    import audit_release_gate as gate
+    with tempfile.TemporaryDirectory() as s:
+        td = Path(s)
+        facts = write_json(td / "facts.json",
+            {"token": {"symbol": "TT", "decimals": 0, "total_supply_raw": "1000"},
+             "entities": {"e1": {"label": "大庄#1", "addresses": [A],
+                                 "current_raw": "278", "peak_raw": "300"}}})
+        ws = write_json(td / "ws.json",
+            [{"entity_id": "e1", "ts": ["2026-01-01"], "pct": [90.0]}])
+        rcpt = {
+            "schema": "figure2-check-receipt/v1", "mode": "formal",
+            "tol_pp": 0.05, "verdict": "PASS",
+            "facts": {"path": "facts.json", "sha256": hashlib.sha256(facts.read_bytes()).hexdigest()},
+            "series": {"path": "ws.json", "sha256": hashlib.sha256(ws.read_bytes()).hexdigest()},
+        }
+        errs = []
+        gate.check_figure2_receipt(td, rcpt, errs)
+        check("F04 手写 PASS 收据末点不同源拒",
+              any("发布期重算" in x and "≠ facts 当前" in x for x in errs), str(errs))
+
+
+def _f04_case_2():
+    import audit_release_gate as gate
+    with tempfile.TemporaryDirectory() as s:
+        td = Path(s)
+        facts = write_json(td / "facts.json",
+            {"token": {"symbol": "TT", "decimals": 0, "total_supply_raw": "1000"},
+             "entities": {"e1": {"label": "大庄#1", "addresses": [A],
+                                 "current_raw": "278", "peak_raw": "300"}}})
+        ws = td / "ws.json"
+        ws.write_text('[{"entity_id":"e1","ts":["2026-01-01"],"pct":[NaN]}]',
+                      encoding="utf-8")
+        rcpt = {
+            "schema": "figure2-check-receipt/v1", "mode": "formal",
+            "tol_pp": 0.05, "verdict": "PASS",
+            "facts": {"path": "facts.json", "sha256": hashlib.sha256(facts.read_bytes()).hexdigest()},
+            "series": {"path": "ws.json", "sha256": hashlib.sha256(ws.read_bytes()).hexdigest()},
+        }
+        errs = []
+        gate.check_figure2_receipt(td, rcpt, errs)
+        check("F04 手写 PASS 收据 NaN 字面量拒",
+              any("重算失败" in x for x in errs), str(errs))
+
+
+def _f04_case_3():
+    fff = ROOT / "scripts/report/figures_from_facts.py"
+    import audit_release_gate as gate
+    with tempfile.TemporaryDirectory() as s:
+        td = Path(s)
+        write_json(td / "facts.json",
+            {"token": {"symbol": "TT", "decimals": 0, "total_supply_raw": "1000"},
+             "entities": {"e1": {"label": "大庄#1", "addresses": [A],
+                                 "current_raw": "278", "peak_raw": "300"}}})
+        write_json(td / "ws.json",
+            [{"entity_id": "e1", "ts": ["2026-01-01"], "pct": [27.8]}])
+        p = run([fff, "check", "--facts", "facts.json", "--series", "ws.json"], td)
+        check("F04 真跑 check 同源收据生成", p.returncode == 0,
+              f"rc={p.returncode}\n{p.stdout}{p.stderr}")
+        rcpt = json.loads((td / "figure2_check_receipt.json").read_text())
+        errs = []
+        gate.check_figure2_receipt(td, rcpt, errs)
+        check("F04 真跑 check 同源收据仍放行（GREEN→GREEN）", errs == [], str(errs))
+
+
+def _f04_case_4():
+    import audit_release_gate as gate
+    with tempfile.TemporaryDirectory() as s:
+        td = Path(s)
+        facts = write_json(td / "facts.json",
+            {"token": {"symbol": "TT", "decimals": 0, "total_supply_raw": "1000"},
+             "entities": {"e1": {"label": "大庄#1", "addresses": [A],
+                                 "current_raw": "278", "peak_raw": "300"}}})
+        rcpt = {
+            "schema": "figure2-check-receipt/v1", "mode": "formal",
+            "tol_pp": 0.05, "verdict": "PASS",
+            "facts": {"path": "facts.json", "sha256": hashlib.sha256(facts.read_bytes()).hexdigest()},
+            "series": {"path": "ws.json", "sha256": "a" * 64},
+        }
+        errs = []
+        gate.check_figure2_receipt(td, rcpt, errs)
+        check("F04 输入缺席不重算不重复报错",
+              len(errs) == 1 and "不在案根" in errs[0]
+              and not any("重算" in x for x in errs), str(errs))
+
+
 def t_r08_nonfinite():
     _r08_case_1()
     _r08_case_2()
@@ -1508,6 +1595,10 @@ def t_r08_nonfinite():
     _r08_case_11()
     _r08_case_12()
     _r08_case_13()
+    _f04_case_1()
+    _f04_case_2()
+    _f04_case_3()
+    _f04_case_4()
 
 
 def t_f04_tolpp_clamp():
```

## 3. RED 证据

生产代码改动前已逐例运行并捕获 AssertionError，完整命令、输出和被测文件 sha256 见 [F04_red_evidence.txt](F04_red_evidence.txt)。证据文件在生产补丁之前落盘；取证前后生产文件 sha256 均为 `23b6f95bd2a9a7f8a84ac2606886ca3ad503f0b0ce2a6359c3678f0ed81da334`。

| 用例 | 基线真实结果 | 原始断言错误 |
| --- | --- | --- |
| `_f04_case_1` | RED | `AssertionError: F04 手写 PASS 收据末点不同源拒: []` |
| `_f04_case_2` | RED | `AssertionError: F04 手写 PASS 收据 NaN 字面量拒: []` |
| `_f04_case_3` | GREEN→GREEN 的基线 GREEN | 无 |
| `_f04_case_4` | GREEN→GREEN 的基线 GREEN | 无 |
| 订正后的 `_r08_case_12` | RED | `AssertionError: R08 消费者对 NaN 手写收据直接拒（F04）: []` |

RED runner exit=0 表示逐例结果与预期的 3 RED / 2 GREEN 相符，不表示三个缺陷用例在旧生产代码上通过。

## 4. 定向验收
以下九项全部首轮真实 PASS、退出码均为 0。命令统一设置 `PYTHONDONTWRITEBYTECODE=1`，使子进程也不生成 pyc；未修改测试内部流程。新增四例和订正后的 `_r08_case_12` 已由批 C 的 `t_r08_nonfinite()` 实际执行并通过。

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/test_repair_batch_c.py
PASS: repair batch C (F-05+F-04+fixround1+fixround2) 249 checks
exit=0
```

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/test_figures_from_facts.py
PASS: figures_from_facts fig1白名单/legacy销毁键/legend receipt/burn豁免/overlay组成/价格绑定/flow宏同源/check终值对账全过
exit=0
```

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/test_audit_release_gate.py
PASS: audit_release_gate 净室资产/哈希/CEX受益权/阴性结论/图表封口与负钳零/对抗复核否决/四查WARN拦截/双线阈值/嵌套未决暴露/静置仓全集对账/日级峰值口径闭环十一类契约全过
exit=0
```

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/test_a4_gate.py
a4_gate 契约测试全部通过（23 项）
exit=0
```

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/test_repair_batch_d.py
BATCH D 全部通过
exit=0
```

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/test_repair_g1_cross_target.py
PASS: F-03 cross-partition target equality and absence policy
exit=0
```

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/test_review_20260804_p105.py
PASS: P1-05 mandatory new-analysis vs independent-audit release profiles
exit=0
```

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/test_stage2_closeout.py
stage2_closeout: 28/28 PASS
exit=0
```

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/invariant_scan.py
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
exit=0
```

`test_a4_gate.py` 与 `test_stage2_closeout.py` 首轮均通过，没有触发 `BLOCK: distribution data_broken: '_items'`，因此未使用 §0.8 的缓存重跑分支。若干测试输出默认 matplotlib 缓存目录不可写、自动改用临时目录及构建字体缓存的提示；这未导致验收失败，所有结果均来自实际测试结束后的退出码与尾行。

## 5. 字节数与改动范围

仅使用大小元数据统计，施工前后三数一致：

```text
$ stat -f %z SKILL.md
8021
exit=0
$ find references -name '*.md' -print0 | xargs -0 stat -f %z | awk '{s+=$1} END{print s}'
930061
exit=0
$ stat -f %z commands-staging/*.md | awk '{s+=$1} END{print s}'
8798
exit=0
```

实际 `git diff --stat` 输出：

```text
 scripts/report/audit_release_gate.py | 15 ++++++
 scripts/tests/test_repair_batch_c.py | 93 +++++++++++++++++++++++++++++++++++-
 2 files changed, 107 insertions(+), 1 deletion(-)
```

`git diff --stat` 不列出未跟踪的新文件；本段另新建白名单内 `F04_done.md` 与 `F04_red_evidence.txt`，最终以 `git status --porcelain=v1 --untracked-files=all` 一并核验。

```text
$ git status --porcelain=v1 --untracked-files=all
 M scripts/report/audit_release_gate.py
 M scripts/tests/test_repair_batch_c.py
?? maintenance/repair-20260918-p0-f04-f07/F04_done.md
?? maintenance/repair-20260918-p0-f04-f07/F04_red_evidence.txt
```

最终状态恰为以上四个白名单文件，未发现白名单外改动。

## 6. 工单一致性、实际行号与未改范围

无工单与代码事实冲突，无施工范围差异，未触发停工。生产修改与 §2.1 指定代码逐字一致；测试只新增四个子函数、四行调用并订正指定的一处断言。`_r08_case_12` 的订正断言实际位于 `scripts/tests/test_repair_batch_c.py:1453`（续行 1454）；原 1454–1462 的后续检查保持原文。

NC1 原 1174–1198 三段手写收据断言未改，批 C 全量定向运行覆盖该函数与五个 F04 相关用例。输入实物检查新增错误时立即返回；事实、序列 sha 不匹配或文件缺席均不会继续重算。

```text
PASS: production changes exactly match workorder §2.1
PASS: test changes limited to four cases, four calls, and one assertion
PASS: NC1 baseline lines 1174-1198 and R08 baseline lines 1454-1462 unchanged
UNCHANGED 557c7099ccec38615771da8fd64facd83deab93928dda0aa2e6c9e6b6a28a9e0 scripts/report/figures_from_facts.py
UNCHANGED dd759a3829759e2d1186cec05f6284f88367090b67947cedb14226f857287a95 scripts/report/build_html.py
UNCHANGED d765356dfacc688f9ebda216fd68f1c8afb4c62bc466a86c4d5849bb7b989e5e scripts/report/stage2_closeout.py
UNCHANGED b301dfcc3ed80e3bd64f11e5b2c5b0d1ec13ace7f9df16a62906cced12cdfa96 scripts/tests/contract_manifest.json
UNCHANGED 7fe9588886cf0ef8f9a66a626df1ca4d466a9724a5217a448ac29444979ed11a scripts/tests/invariant_manifest.json
R08 corrected assertion line 1453
```

`git diff --check` 无输出、exit=0。受保护的两个 manifest 未修改，invariant 扫描通过且未报缺项。`FIGURE2_RECEIPT_SCHEMA`、`FIGURE2_DEFAULT_TOL_PP`、`_figure2_input_check`、`check_facts_vs_ledgers`、`run/_run`、测试 `main()` 均保持原文。

最终源文件与 RED 证据哈希：

```text
c35d4a489eb7651e24aa77a872a51fa7c717c103883c74043c177f0613fa3a16 scripts/report/audit_release_gate.py
d364329c8182b169904de59476b8e1d09ffbe977ef55ea831560e651c3542a30 scripts/tests/test_repair_batch_c.py
557c7099ccec38615771da8fd64facd83deab93928dda0aa2e6c9e6b6a28a9e0 scripts/report/figures_from_facts.py
a5a167bbc0f88c8fbb506ff5d243b6fe7a70dd613ed137318ab95219c4f6a3b9 maintenance/repair-20260918-p0-f04-f07/F04_red_evidence.txt
```

工单 §4 登记项由调度方维护，本段未改 `code_change_pending.md`；空 series 仍按既有规则放行、合法同源旧 PASS 收据仍可通过，收据 schema 未升版。

## 7. 禁读与执行披露

开工已披露：会话自动提供了历史记忆摘要；本轮未通过工具读取 `~/.codex/` 下任何文件，未读取任何 SKILL.md。未主动阅读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、受禁历史 maintenance 目录、`/Users/uravvv/Desktop` 或 `/Users/uravvv/Documents`。文档总字节统计只读取文件大小元数据；本次只主动读取当前工单目录中的 F04 全文和 F06 字节统计命令上下文。

工单 §0.2 的精确例外被批 C 测试触发：既有 `t_f09_importer_fail_closed` 与 `t_fixround2` 测试进程自行通过 importlib 加载 `maintenance/repair-20260814-batch2/import_pythia_legacy.py`。施工方未主动阅读、引用其内容或改动该文件；守卫与测试自身的文档遍历按授权执行。

全程离线；未运行 `run_all.py`，未 commit、push、stash、checkout、reset 或部署 `~/.claude/commands/`。结束 HEAD 仍为 `b1ccf2369c81e344c7be997779c90d15d0e8c6aa`。
