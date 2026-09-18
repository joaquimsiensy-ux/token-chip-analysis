# 施工 G1：完成

按 `workorder_G1_fig2.md` 文件头 v2（含 r2 标题勘误）施工。图 2 对必画实体的空序列、缺线和重复线均拒绝；非必画实体允许空序列。生产代码只改工单 §2.1–§2.3，测试只加 §2.4/§2.5 指定用例。全程离线，未运行 `run_all.py`，未 commit、push、stash、checkout、reset 或部署。

## 1. §0.1 开工基线原始输出

工作目录：`/Users/uravvv/.claude/skills/token-chip-analysis`。

```console
$ git status --short
$ git diff --stat f1f473f3 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
```

以上两条实际运行，退出码均为 0，stdout 均为 0 字节；开工工作树与 HEAD 无差异，指定生产/文档路径与内容基线无差异。

```console
$ git log -2 --format='%H %s'
40c090a0cf4fc8f35f11d34302bc2efc3dcda0f3 G1 施工提示词填派工基线 0d3b0c0
0d3b0c0d90ee12aedfdc8a9e5a58276a05a65679 工单 G2 v2:融合 codex 复核 r1 七条;G1 r2 通过(标题勘误);G1 r2/G2 r1 报告与 G2 r2 提示词入库;台账 Q7 补迁移代价
$ git rev-list --count 0d3b0c0..HEAD
1
```

开工 HEAD 为 `40c090a0cf4fc8f35f11d34302bc2efc3dcda0f3`，派工基线 `0d3b0c0` 后恰 1 个预期提交。

## 2. 开工核实与改动边界

- 全部施工锚已用 `grep -n -F` 实际核验，唯一性及基线行号全部吻合。§2.3 的两个重复锚按工单例外处理，只修改 `fig2_selection_errors` 中第一处；`flow_selection_errors` 保持原文。
- §1.3：`test_a4_gate.py:498/507` 显式使用 `{"e1":"实体1"}`；`test_repair_batch_d.py:1205/1206` 与 `test_review_20260804_p105.py:214/222` 未传 labels。已核实 `test_audit_release_gate.py:202–226`，第 216 行为 `names[eid] = (labels or {}).get(eid, eid)`；对应夹具的 `align_ledgers_to_owner_snapshot` 生成 `entity_id="e1"`，默认 label 因而是 `e1`。三处均不带必画前缀，空序列应继续通过。
- §2.2④：实际执行 `grep -n "self.entities" scripts/report/facts_gate.py`，第 117 行为 `self.entities = facts_dict.get("entities") or {}`，属性名及 dict 来源吻合。
- §2.4：`test_figures_from_facts.py:22–32` 的 `FACTS.entities.e1.label` 为 `大庄#1`，current/total 为 27.84%，满足新增空序列及重复线测试前提。
- §1.4：已核实 closeout 原有必画标签、`观察实体`、额外线 e2 用例；共享规则沿用原前缀。
- 逐函数源码比较确认 `mode_check`、`build_fig2_series`、`_write_check_receipt`、`fig2_series_errors`、`flow_selection_errors`、批 C `main()` 均与 HEAD 原文一致；非 list 的固定返回句、装载异常转换及收据 schema 未变。
- `audit_release_gate.py`、`build_html.py`、`a5_report_seal.py`、`facts_gate.py`、两个 manifest 和所有文档路径均未修改。

锚点检查原始输出：

```text
$ grep -n -F -- 'FIG1_LEGEND_RECEIPT_SCHEMA = "figure1-legend/v1"' scripts/report/figures_from_facts.py
60:FIG1_LEGEND_RECEIPT_SCHEMA = "figure1-legend/v1"
$ grep -n -F -- '    errs, okc = [], 0' scripts/report/figures_from_facts.py
307:    errs, okc = [], 0
$ grep -n -F -- '        pct = line.get("pct") or []' scripts/report/figures_from_facts.py
320:        pct = line.get("pct") or []
$ grep -n -F -- '    return errs, okc' scripts/report/figures_from_facts.py
337:    return errs, okc
$ grep -n -F -- '         series 条目带 entity_id 的按 id 对 facts 实体；否则按 label 匹配。' scripts/report/figures_from_facts.py
29:         series 条目带 entity_id 的按 id 对 facts 实体；否则按 label 匹配。
$ grep -n -F -- 'def fig2_selection_errors(facts, fig2):' scripts/report/stage2_closeout.py
168:def fig2_selection_errors(facts, fig2):
$ grep -n -F -- '    required = set()' scripts/report/stage2_closeout.py
171:    required = set()
211:    required = set()
$ grep -n -F -- '            required.add(entity_id)' scripts/report/stage2_closeout.py
178:            required.add(entity_id)
216:                required.add(entity_id)
$ grep -n -F -- '        assert r.returncode != 0 and "不同源" in r.stdout, f"偏 0.5pp 应挂: {r.stdout}"' scripts/tests/test_figures_from_facts.py
182:        assert r.returncode != 0 and "不同源" in r.stdout, f"偏 0.5pp 应挂: {r.stdout}"
$ grep -n -F -- 'def _f04_case_4():' scripts/tests/test_repair_batch_c.py
1563:def _f04_case_4():
$ grep -n -F -- 'def t_r08_nonfinite():' scripts/tests/test_repair_batch_c.py
1584:def t_r08_nonfinite():
$ grep -n -F -- '    _f04_case_4()' scripts/tests/test_repair_batch_c.py
1601:    _f04_case_4()
ANCHOR_CHECK=PASS
```

## 3. RED → GREEN 证据

完整原始证据及可复现取证命令：`G1_red_evidence.txt`。在任何生产修改前，取证器以 `git show HEAD:<path>` 验证两份生产文件逐字节未变，并记录生产者、消费者、facts 模块、两份测试文件及每次输入的 SHA-256。

| 用例 | 基线实际结果 | 修复后要求 |
| --- | --- | --- |
| §2.4 空 series | RED：rc=0，输出 PASS 0 条 | 拒绝，含“缺必画实体线” |
| §2.4 重复线 | RED：rc=0，输出 PASS 2 条 | 拒绝，含“重复出现” |
| §2.5 case 1 空 series producer | RED：rc=0，输出 PASS 0 条 | 拒绝 |
| §2.5 case 1 空 series 消费者 | RED：errs=[] | 发布期重算拒绝 |
| §2.5 case 2 重复线 producer | RED：rc=0，输出 PASS 2 条 | 拒绝 |
| §2.5 case 3 观察实体空 series | 3 条 GREEN：producer rc=0、收据 PASS、消费者 errs=[] | 3 条保持 GREEN |
| §2.5 case 4 只画 e1、漏 e2 | 2 条 RED：producer rc=0、消费者 errs=[] | 两端均报告缺 e2 |
| §2.5 case 4 补齐 e1+e2 | 2 条 GREEN：producer rc=0、消费者 errs=[] | 2 条保持 GREEN |

合计 7 条预期 RED、5 条基线 GREEN。§2.4 直接运行新增语句的 AST；§2.5 逐个实际调用 `_g1_case_1/2/3/4`，只在取证进程包装既有 `check`，逐条捕获真实 AssertionError，避免第一条失败截断后续消费者证据。生产者和消费者都先执行，再进行断言；case 4 的补齐段也完成执行。

取证器首次在选择无 msg 的旧 Assert 时触发 `AttributeError`，尚未运行新增用例；已在同一证据文件保留该次失败与修正后的完整运行。仅修正取证器的 AST 选择条件，未把该异常计入产品 RED，未为此修改仓库代码。

## 4. §0.8 定向测试结果

10/10 项首次运行退出码均为 0。均设置 `PYTHONDONTWRITEBYTECODE=1`，实际执行下列 `python3 -B` 命令，未跳过用例。A4 与 closeout 未出现 `data_broken: '_items'`，无需执行该环境例外的重跑。

```console
$ python3 -B scripts/tests/test_figures_from_facts.py
PASS: figures_from_facts fig1白名单/legacy销毁键/legend receipt/burn豁免/overlay组成/价格绑定/flow宏同源/check终值对账全过
```

退出码：0；用时：59.57 秒。

```console
$ python3 -B scripts/tests/test_repair_batch_c.py
PASS: repair batch C (F-05+F-04+fixround1+fixround2) 259 checks
```

退出码：0；用时：414.75 秒。

```console
$ python3 -B scripts/tests/test_stage2_closeout.py
stage2_closeout: 28/28 PASS
```

退出码：0；用时：56.91 秒。

```console
$ python3 -B scripts/tests/test_a4_gate.py
a4_gate 契约测试全部通过（23 项）
```

退出码：0；用时：28.65 秒。

```console
$ python3 -B scripts/tests/test_repair_batch_d.py
BATCH D 全部通过
```

退出码：0；用时：124.02 秒。

```console
$ python3 -B scripts/tests/test_review_20260804_p105.py
PASS: P1-05 mandatory new-analysis vs independent-audit release profiles
```

退出码：0；用时：113.32 秒。

```console
$ python3 -B scripts/tests/test_repair_batch_b.py
PASS batch B F-03/F-08 regressions 41/41
```

退出码：0；用时：166.43 秒。

```console
$ python3 -B scripts/tests/test_audit_release_gate.py
PASS: audit_release_gate 净室资产/哈希/CEX受益权/阴性结论/图表封口与负钳零/对抗复核否决/四查WARN拦截/双线阈值/嵌套未决暴露/静置仓全集对账/日级峰值口径闭环十一类契约全过
```

退出码：0；用时：46.69 秒。

```console
$ python3 -B scripts/tests/test_repair_g1_cross_target.py
PASS: F-03 cross-partition target equality and absence policy
```

退出码：0；用时：23.64 秒。

```console
$ python3 -B scripts/tests/invariant_scan.py
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
```

退出码：0；用时：4.34 秒。

以上正式测试覆盖了新增全部断言：7 条 RED 已转 GREEN，原先 5 条 GREEN 保持通过。closeout 28/28（含必画前缀、观察实体及额外线 e2）、A4 和 §1.3 另外两处非必画空序列兼容用例均通过。

测试原始日志仍保留在临时目录，便于核验尾行；SHA-256 由执行器在测试完成后记录：

| 测试 | 原始日志 | SHA-256 |
| --- | --- | --- |
| `test_figures_from_facts.py` | `/private/tmp/g1-test_figures_from_facts.py-first-wxuc1_oo.log` | `88c44e6e7f8dade1fe2110f79f9e0a9a6e1c19d4d47ec31384945a013329d978` |
| `test_repair_batch_c.py` | `/private/tmp/g1-test_repair_batch_c.py-first-cyed0mjc.log` | `eb2068f2c3535660816aa6f9fd089df9b0f88b85cea5085b5df215a8bd102e25` |
| `test_stage2_closeout.py` | `/private/tmp/g1-test_stage2_closeout.py-first-sd288mri.log` | `57832e98bed405eee74c7af10b6effccbb8d5cbf3b4486d1529e332e1c7d1c01` |
| `test_a4_gate.py` | `/private/tmp/g1-test_a4_gate.py-first-_lkudfb2.log` | `f4dc99503a89cd99d904cad7918192b22f0a6fe78df837c581612027457b373a` |
| `test_repair_batch_d.py` | `/private/tmp/g1-test_repair_batch_d.py-first-cvl329nt.log` | `a786a39a116176838222ca8071737c29c3d1688a0ee493d41df642b399058263` |
| `test_review_20260804_p105.py` | `/private/tmp/g1-test_review_20260804_p105.py-first-zpeboget.log` | `0b152264ed759ed07b4b924071f7384de97081b0821302f0aa55cf421c3ea2eb` |
| `test_repair_batch_b.py` | `/private/tmp/g1-test_repair_batch_b.py-first-s3_1ttud.log` | `c2e51615f8209b74b1e904027c6c29cf7540c16b824ad352cbe6f2e25dc01451` |
| `test_audit_release_gate.py` | `/private/tmp/g1-test_audit_release_gate.py-first-v77po87r.log` | `b3edc65f36db29d5f3409d5fde0c4337257c3ed9160c199bd34ced0f0502e468` |
| `test_repair_g1_cross_target.py` | `/private/tmp/g1-test_repair_g1_cross_target.py-first-avco6h3p.log` | `1c7ccd8d098a79f75bd3a59cf0610fe15d0c0a70df426d7c3e63a503b48fbb9b` |
| `invariant_scan.py` | `/private/tmp/g1-invariant_scan.py-first-hrlnjr34.log` | `ca4347e70be8d1f42dcdfcb4b2528650a79bc2b8b405a0bdefe593cb0feb30b0` |

## 5. §2 各处 git diff 原文

```diff
diff --git a/scripts/report/figures_from_facts.py b/scripts/report/figures_from_facts.py
index d4b8351..3e9991f 100644
--- a/scripts/report/figures_from_facts.py
+++ b/scripts/report/figures_from_facts.py
@@ -27,6 +27,7 @@
          python3 figures_from_facts.py check --facts facts.json \
              --series charts/whale_series.json [--tol-pp 0.05]
          series 条目带 entity_id 的按 id 对 facts 实体；否则按 label 匹配。
+         必画下限：label 以 项目方/大庄/小庄/离场庄 起头的实体须各有一条线，缺线/重复线/空 series 拒。
          图 2 的时间序列本身无法从快照型 state 重建（需重放中间序列），故此处
          做终值对账而非生成——序列中间值的正确性仍由重放脚本+对账关卡负责。
 
@@ -58,6 +59,15 @@ import standard_charts as charts  # noqa: E402
 
 FIG1_LEGEND_RECEIPT_NAME = "fig1_legend_receipt.json"
 FIG1_LEGEND_RECEIPT_SCHEMA = "figure1-legend/v1"
+FIG2_REQUIRED_LABEL_PREFIXES = ("项目方", "大庄", "小庄", "离场庄")
+
+
+def fig2_required_entity_ids(entities) -> set:
+    """图 2 必画下限：facts.entities 中 label 以 项目方/大庄/小庄/离场庄 起头的实体
+    （与 stage2_closeout 工单选材同一规则；刷量地址/观察实体不在下限内）。"""
+    return {str(eid) for eid, ent in (entities or {}).items()
+            if isinstance(ent, dict)
+            and str(ent.get("label") or "").strip().startswith(FIG2_REQUIRED_LABEL_PREFIXES)}
 
 
 def _reject_constant(token):
@@ -304,7 +314,7 @@ def fig2_check_errors(facts_path: Path, series_path: Path, tol_pp: float) -> tup
         return ["--series 应为图 2 whale_series JSON（list of lines）"], 0
     by_label = {(e.get("label") or "").strip(): (eid, e)
                 for eid, e in facts.entities.items()}
-    errs, okc = [], 0
+    errs, okc, seen = [], 0, set()
     for line in series:
         eid = (line.get("entity_id") or "").strip()
         lbl = (line.get("label") or "").strip()
@@ -317,6 +327,10 @@ def fig2_check_errors(facts_path: Path, series_path: Path, tol_pp: float) -> tup
             errs.append(f"线「{lbl or eid}」在 facts.entities 中无匹配"
                         "（加 entity_id 字段或对齐 label）")
             continue
+        if eid in seen:
+            errs.append(f"{key} 线重复出现（同一实体只能一条线）")
+            continue
+        seen.add(eid)
         pct = line.get("pct") or []
         if not pct:
             errs.append(f"{key} 线无 pct 数据")
@@ -334,6 +348,11 @@ def fig2_check_errors(facts_path: Path, series_path: Path, tol_pp: float) -> tup
                         f"（差 {abs(last-want):.4f}pp > 容差 {tol_pp}pp）")
         else:
             okc += 1
+    missing = sorted(fig2_required_entity_ids(facts.entities) - seen)
+    if missing:
+        errs.append(f"图 2 缺必画实体线 {missing}（label 以 "
+                    f"{'/'.join(FIG2_REQUIRED_LABEL_PREFIXES)} 起头的实体必须各有一条线；"
+                    "空 series 不得放行）")
     return errs, okc
 
 
diff --git a/scripts/report/stage2_closeout.py b/scripts/report/stage2_closeout.py
index 7a6885a..f48b7ce 100644
--- a/scripts/report/stage2_closeout.py
+++ b/scripts/report/stage2_closeout.py
@@ -168,14 +168,13 @@ def workorder_error(field, expected, actual):
 def fig2_selection_errors(facts, fig2):
     errors, notes = [], []
     entities = facts["entities"]
-    required = set()
     for entity_id, entity in entities.items():
         label = entity.get("label")
         if not isinstance(label, str) or not label.strip():
             errors.append(workorder_error(f"facts.entities.{entity_id}.label",
                                          f"实体 {entity_id} 无标签，无法判定必画", label))
-        elif label.strip().startswith(("项目方", "大庄", "小庄", "离场庄")):
-            required.add(entity_id)
+    import figures_from_facts
+    required = figures_from_facts.fig2_required_entity_ids(entities)
     lines = fig2.get("lines")
     declared = fig2.get("required_entity_ids")
     if not isinstance(lines, list) or not lines:
diff --git a/scripts/tests/test_figures_from_facts.py b/scripts/tests/test_figures_from_facts.py
index 86ea2cf..9b68820 100644
--- a/scripts/tests/test_figures_from_facts.py
+++ b/scripts/tests/test_figures_from_facts.py
@@ -180,6 +180,15 @@ def main():
                   open(ser_p, "w"))
         r = run(["check", "--facts", fp, "--series", ser_p])
         assert r.returncode != 0 and "不同源" in r.stdout, f"偏 0.5pp 应挂: {r.stdout}"
+        # 4b) G1：facts 有必画实体（大庄#1）而 series 为空 → FAIL（不得 PASS 0 条）
+        json.dump([], open(ser_p, "w"))
+        r = run(["check", "--facts", fp, "--series", ser_p])
+        assert r.returncode != 0 and "缺必画实体线" in r.stdout, f"空 series 应挂: {r.stdout}"
+        # 4c) G1：同一实体两条线 → FAIL
+        json.dump([{"entity_id": "e1", "ts": ["2026-01-03"], "pct": [27.84]}] * 2,
+                  open(ser_p, "w"))
+        r = run(["check", "--facts", fp, "--series", ser_p])
+        assert r.returncode != 0 and "重复出现" in r.stdout, f"重复线应挂: {r.stdout}"
 
         # 5) fig1 --overlay 合并口径线（v3.33）：正常出图 + 两条 fail-closed
         out5 = os.path.join(td, "fig1_ov.png")
diff --git a/scripts/tests/test_repair_batch_c.py b/scripts/tests/test_repair_batch_c.py
index e028b1f..48eebc4 100644
--- a/scripts/tests/test_repair_batch_c.py
+++ b/scripts/tests/test_repair_batch_c.py
@@ -1581,6 +1581,103 @@ def _f04_case_4():
               and not any("重算" in x for x in errs), str(errs))
 
 
+def _g1_case_1():
+    fff = ROOT / "scripts/report/figures_from_facts.py"
+    import audit_release_gate as gate
+    with tempfile.TemporaryDirectory() as s:
+        td = Path(s)
+        facts = write_json(td / "facts.json",
+            {"token": {"symbol": "TT", "decimals": 0, "total_supply_raw": "1000"},
+             "entities": {"e1": {"label": "大庄#1", "addresses": [A],
+                                 "current_raw": "278", "peak_raw": "300"}}})
+        ws = write_json(td / "ws.json", [])
+        p = run([fff, "check", "--facts", "facts.json", "--series", "ws.json"], td)
+        prod_rc, prod_out = p.returncode, p.stdout
+        rcpt = {
+            "schema": "figure2-check-receipt/v1", "mode": "formal",
+            "tol_pp": 0.05, "verdict": "PASS",
+            "facts": {"path": "facts.json", "sha256": hashlib.sha256(facts.read_bytes()).hexdigest()},
+            "series": {"path": "ws.json", "sha256": hashlib.sha256(ws.read_bytes()).hexdigest()},
+        }
+        errs = []
+        gate.check_figure2_receipt(td, rcpt, errs)
+        check("G1 空 series producer 拒", prod_rc != 0 and "缺必画实体线" in prod_out, prod_out)
+        check("G1 空 series 消费者拒", any("缺必画实体线" in x for x in errs), str(errs))
+
+
+def _g1_case_2():
+    fff = ROOT / "scripts/report/figures_from_facts.py"
+    with tempfile.TemporaryDirectory() as s:
+        td = Path(s)
+        write_json(td / "facts.json",
+            {"token": {"symbol": "TT", "decimals": 0, "total_supply_raw": "1000"},
+             "entities": {"e1": {"label": "大庄#1", "addresses": [A],
+                                 "current_raw": "278", "peak_raw": "300"}}})
+        write_json(td / "ws.json",
+            [{"entity_id": "e1", "ts": ["2026-01-01"], "pct": [27.8]}] * 2)
+        p = run([fff, "check", "--facts", "facts.json", "--series", "ws.json"], td)
+        check("G1 重复线拒", p.returncode != 0 and "重复出现" in p.stdout,
+              f"rc={p.returncode}\n{p.stdout}{p.stderr}")
+
+
+def _g1_case_3():
+    fff = ROOT / "scripts/report/figures_from_facts.py"
+    import audit_release_gate as gate
+    with tempfile.TemporaryDirectory() as s:
+        td = Path(s)
+        write_json(td / "facts.json",
+            {"token": {"symbol": "TT", "decimals": 0, "total_supply_raw": "1000"},
+             "entities": {"e1": {"label": "观察实体", "addresses": [A],
+                                 "current_raw": "278", "peak_raw": "300"}}})
+        write_json(td / "ws.json", [])
+        p = run([fff, "check", "--facts", "facts.json", "--series", "ws.json"], td)
+        rcpt = json.loads((td / "figure2_check_receipt.json").read_text())
+        errs = []
+        gate.check_figure2_receipt(td, rcpt, errs)
+        check("G1 非必画实体空 series producer 放行", p.returncode == 0,
+              f"rc={p.returncode}\n{p.stdout}{p.stderr}")
+        check("G1 非必画实体空 series 收据 PASS", rcpt.get("verdict") == "PASS", str(rcpt))
+        check("G1 非必画实体空 series 消费者放行", errs == [], str(errs))
+
+
+def _g1_case_4():
+    fff = ROOT / "scripts/report/figures_from_facts.py"
+    import audit_release_gate as gate
+    with tempfile.TemporaryDirectory() as s:
+        td = Path(s)
+        facts = write_json(td / "facts.json",
+            {"token": {"symbol": "TT", "decimals": 0, "total_supply_raw": "1000"},
+             "entities": {"e1": {"label": "大庄#1", "addresses": [A],
+                                 "current_raw": "278", "peak_raw": "300"},
+                          "e2": {"label": "小庄#2", "addresses": [B],
+                                 "current_raw": "100", "peak_raw": "100"}}})
+        lines = [{"entity_id": "e1", "ts": ["2026-01-01"], "pct": [27.8]}]
+        ws = write_json(td / "ws.json", lines)
+        p = run([fff, "check", "--facts", "facts.json", "--series", "ws.json"], td)
+        prod_rc, prod_out = p.returncode, p.stdout
+        rcpt = {
+            "schema": "figure2-check-receipt/v1", "mode": "formal",
+            "tol_pp": 0.05, "verdict": "PASS",
+            "facts": {"path": "facts.json", "sha256": hashlib.sha256(facts.read_bytes()).hexdigest()},
+            "series": {"path": "ws.json", "sha256": hashlib.sha256(ws.read_bytes()).hexdigest()},
+        }
+        errs = []
+        gate.check_figure2_receipt(td, rcpt, errs)
+        lines.append({"entity_id": "e2", "ts": ["2026-01-01"], "pct": [10.0]})
+        write_json(ws, lines)
+        complete = run([fff, "check", "--facts", "facts.json", "--series", "ws.json"], td)
+        complete_rcpt = json.loads((td / "figure2_check_receipt.json").read_text())
+        complete_errs = []
+        gate.check_figure2_receipt(td, complete_rcpt, complete_errs)
+        check("G1 非空 series 漏必画实体 producer 拒",
+              prod_rc != 0 and "缺必画实体线 ['e2']" in prod_out, prod_out)
+        check("G1 非空 series 漏必画实体消费者拒",
+              any("缺必画实体线 ['e2']" in x for x in errs), str(errs))
+        check("G1 补齐必画实体 producer 放行", complete.returncode == 0,
+              f"rc={complete.returncode}\n{complete.stdout}{complete.stderr}")
+        check("G1 补齐必画实体消费者放行", complete_errs == [], str(complete_errs))
+
+
 def t_r08_nonfinite():
     _r08_case_1()
     _r08_case_2()
@@ -1599,6 +1696,10 @@ def t_r08_nonfinite():
     _f04_case_2()
     _f04_case_3()
     _f04_case_4()
+    _g1_case_1()
+    _g1_case_2()
+    _g1_case_3()
+    _g1_case_4()
 
 
 def t_f04_tolpp_clamp():
```

## 6. §1.1 字节数与最终差异统计

三处字节数开工与完工一致：`SKILL.md` **8021**，`references/**/*.md` 合计 **930061**，`commands-staging/*.md` 合计 **8798**。仅用文件元数据统计，未读取文档内容。`git diff --check` 无输出、退出码 0；已跟踪改动集合恰为四个白名单源码/测试文件。HEAD 未变化。

以下为写入本报告前最后一轮核验原文；`git diff --stat` 不包含未跟踪的本报告及 RED 文件：

```text
TRACKED_SCOPE_CHECK=PASS
HEAD=40c090a0cf4fc8f35f11d34302bc2efc3dcda0f3
$ stat -f %z SKILL.md
8021
$ find references -name '*.md' -print0 | xargs -0 stat -f %z | awk '{s+=$1} END{print s}'
930061
$ stat -f %z commands-staging/*.md | awk '{s+=$1} END{print s}'
8798
$ git diff --stat
 scripts/report/figures_from_facts.py     |  21 ++++++-
 scripts/report/stage2_closeout.py        |   5 +-
 scripts/tests/test_figures_from_facts.py |   9 +++
 scripts/tests/test_repair_batch_c.py     | 101 +++++++++++++++++++++++++++++++
 4 files changed, 132 insertions(+), 4 deletions(-)
$ git status --short
 M scripts/report/figures_from_facts.py
 M scripts/report/stage2_closeout.py
 M scripts/tests/test_figures_from_facts.py
 M scripts/tests/test_repair_batch_c.py
?? maintenance/repair-20260918b-p0-fig2-decimals/G1_red_evidence.txt
?? maintenance/repair-20260918b-p0-fig2-decimals/blind_G1_prompt.md
RED_EVIDENCE_COMPLETE=PASS
```

## 7. 与工单差异、停工点及工作树观察

无生产或测试范围偏离，无工单与代码事实冲突，无停工点。§2.5 case 4 在汇总断言前先执行缺线 producer/consumer 和补齐 producer/consumer，保证改动前的两条 RED 与补齐绿例都能完整取证。取证器的首次工具异常与修正已在 §3 和 RED 原始文件如实保留，未掩盖测试失败。

开工工作树为空；施工期间及报告回读时，`git status --short` 另出现本目录的 `blind_G1_prompt.md`、`review_G2_reply_r2.md` 两个未跟踪文件。本次操作未创建、读取或修改这两个文件，来源未核验，不纳入本段施工变更。未因此触碰白名单外文件。

本次仓库产物只有四个白名单代码改动，以及新建 `G1_red_evidence.txt`、`G1_done.md`；测试临时夹具和运行日志均在系统临时目录。未修改两个 manifest、收据 schema 或 §0.4 禁改段落。旧收据的缺线/重复线重算拒绝行为按工单 §4 生效，未在本段修改 CHANGELOG。

## 8. 禁读披露

未读取 `~/.codex/` 下任何文件；未进行会读取 memories 的插件启动搜索。未读取 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md` 内容，未读取 `/Users/uravvv/Desktop` 或 `/Users/uravvv/Documents`。未主动读取允许范围以外的历史 maintenance 目录；既有 legacy importer 仅由工单准许的测试进程自行加载，施工方未主动读取或改动其文件。守卫/测试脚本按明确授权运行，其自身文档遍历未改写文档。
