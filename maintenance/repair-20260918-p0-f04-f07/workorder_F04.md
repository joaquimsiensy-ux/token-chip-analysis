# 工单 F04（v3，融合 codex 复核 r1 四条＋r2 两条 F04-R2-01/02）：new-analysis 发布闸对图 2 收据做发布期重算 —— repair-20260918-p0-f04-f07 第二段

> 出处：codex 对 7.2.0（311e6c4）的六视角 review F04（P0，**半修复 R08**）：`figures_from_facts.fig2_check_errors`（`:296-337`）已拒非有限值与末点偏差，但 new-analysis 发布消费者 `audit_release_gate.check_figure2_receipt`（`:1551-1572`）只验 schema/mode/tol/verdict 与两输入 sha——只要收据同 schema、sha 对得上，末点差 80pp 或 NaN 的序列照样签发 HTML；R08 修复前产出的旧 PASS 收据也没有失效机制。反例：review 附录 D `repro_core.py` F04-numeric（实际校验报 90% vs 10%，消费者 `[]`）、`repro_formal.py`（真实 A4/A5 案 1% vs 100%，`build_html --mode analysis-new` rc=0）。用户 2026-09-18 裁决：修。总原则：**skill 上下文不增**；能删不增、能改不增；`stage2_closeout` 不改为必经（改动量大，本段不做）。
> v3 变更（`review_F04_reply_r2.md`）：R2-01 §0.8 补冷字体缓存环境项的处理（`test_a4_gate.py:307`/`test_stage2_closeout.py:17` 自设新缓存目录 → 本机 matplotlib `font_manager.py:275` 读 `_items` 缺键 → `holder_distribution_scan.py:1004` 转 `data_broken`；遇此保留首次失败输出并用 `MPLCONFIGDIR="$HOME/.matplotlib"` 重跑，重跑仍须真实 PASS）；R2-02 订正"生产 `a4_gate.py` 不调发布闸；`test_a4_gate.py:530` 经 build_html 进入 new-analysis 闸，是本段直接回归面"；§4 Agg 引用订正为 `standard_charts.py:38`。
> v2 变更（`review_F04_reply_r1.md`）：R1-01 用例 3 改用既有 `run()`（它已自动加解释器，不得再传 `sys.executable`）；R1-02 except 补 `AttributeError`/`OverflowError`（series `[null]`/facts 顶层 `[]`/超大 current_raw 实证会绕过 ValueError），并订正异常依据；R1-03 §0.2 为既有测试自身加载 `maintenance/repair-20260814-batch2/import_pythia_legacy.py` 立精确读取例外；R1-04 §0.8 删去误挂的 F12 例外；另补 `_r08_case_12` 定义 `:1430`、旧断言 `:1453` 原文与订正文本，§4 补缓存 I/O 与"旧 PASS 失效"限定。
> 内容基线：`311e6c4`（v7.2.0）加本工程已入库的工单/提示词/前段施工 commit；`scripts/report/audit_release_gate.py`、`scripts/tests/test_repair_batch_c.py` 在开工时与 311e6c4 逐字节相同（F06 段不触及这两文件）。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先跑并贴进 `F04_done.md`：`git status --short`（须为空）；`git diff --stat 311e6c4 HEAD -- scripts/report/audit_release_gate.py scripts/tests/test_repair_batch_c.py references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`（须为空）。不空即停工写 `F04_done_attempt1_stopped.md`。
- 0.2 **禁读** `~/.codex/`（启动搜索若已读 memories 披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260917-p0-four/` 以外的历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。**精确读取例外**：`scripts/tests/test_repair_batch_c.py:1549` 与 `:2025-2030` 的既有用例会 `importlib` 加载 `maintenance/repair-20260814-batch2/import_pythia_legacy.py`——允许测试进程自行加载它，施工方不得主动阅读、引用或改动该文件；done 里如实注明该例外被测试触发。
- 0.3 **白名单**：生产 `scripts/report/audit_release_gate.py`；测试 `scripts/tests/test_repair_batch_c.py`；本目录新建 `F04_done.md`、`F04_red_evidence.txt`，停工时 `F04_done_attempt1_stopped.md`。
- 0.4 **不改**：`scripts/report/figures_from_facts.py`（`fig2_check_errors` 是本段复用的只读纯校验器，一字不动）；`audit_release_gate.py` 中 `FIGURE2_RECEIPT_SCHEMA`/`FIGURE2_DEFAULT_TOL_PP`（`:1470-1471`）、`_figure2_input_check`（`:1475-1494`）、`check_facts_vs_ledgers`、`run/_run`；`build_html.py`、`stage2_closeout.py`；任何 `references/`、`SKILL.md`、`commands-staging/`、`VERSION`、`pyproject.toml`、`CHANGELOG.md`、`contract_manifest.json`、`invariant_manifest.json`；其他测试只跑不改。
- 0.5 行号均指施工前基线；锚 `grep -n -F` 恰 1 处且行号一致，不符**停工**。删除 > 修改 > 新增。
- 0.6 离线；不 commit、不 push、不部署；禁 stash/checkout/reset。
- 0.7 先红后绿：§2.2 新用例改动前逐例取 RED 写 `F04_red_evidence.txt`（逐例捕获 AssertionError，按真实基线记 RED 或 GREEN→GREEN）。
- 0.8 不跑 `run_all.py`。定向跑：`python3 -B scripts/tests/test_repair_batch_c.py`、`test_figures_from_facts.py`、`test_audit_release_gate.py`、`test_a4_gate.py`、`test_repair_batch_d.py`、`test_repair_g1_cross_target.py`、`test_review_20260804_p105.py`、`test_stage2_closeout.py`、`python3 -B scripts/tests/invariant_scan.py`。全部须 PASS。（F12 环境项 `test_stage2_reseal.py::dry_run_touches_nothing` 不在本段定向清单内，由调度方全套验收处理。生产 `a4_gate.py` 本身不调发布闸；`test_a4_gate.py:530` 经 `build_html --mode analysis-new` 进入 new-analysis 发布闸，是本段直接回归面。**冷字体缓存环境项**：`test_a4_gate.py`/`test_stage2_closeout.py` 自设新 `MPLCONFIGDIR`，本机 matplotlib 字体枚举缺 `_items` 会报 `BLOCK: distribution data_broken: '_items'`——遇此保留首次失败输出写进 done，再用 `MPLCONFIGDIR="$HOME/.matplotlib" python3 -B scripts/tests/<该测试>.py` 重跑，重跑必须真实 PASS，不得当跳过项。）

## 1. 硬约束

- 1.1 文档三处字节不变：SKILL.md 8021、references 930061、commands-staging 8798（命令同工单 F06 §1.1）。
- 1.2 `git diff --stat` 只含 0.3 白名单。
- 1.3 既有 `t_fc5_receipt_chain`（`:1109` 起）的 NC1 三段手写收据断言（`:1174-1198`）不改且仍 PASS（它们断言的是"拒"，重算只会多加错误不会减少）。
- 1.4 重算只在两输入实物检查（`_figure2_input_check` 两处）**零新增错误**时执行——文件缺席/sha 不符时不重算（避免对不存在文件抛异常、避免重复报错）。

## 2. 逐条施工

### 2.1 `scripts/report/audit_release_gate.py` —— `check_figure2_receipt` 末尾接入纯校验器重算

定位锚：`:1571`（锚 `    _figure2_input_check(case_dir, d.get("series"), "series", errors)`，唯一）与 `:1572`（锚 `    _figure2_input_check(case_dir, d.get("facts"), "facts", errors)`，唯一）。把这两行改为：

```python
    n0 = len(errors)
    _figure2_input_check(case_dir, d.get("series"), "series", errors)
    _figure2_input_check(case_dir, d.get("facts"), "facts", errors)
    if len(errors) > n0:
        return
    # F04（7.2.1）：收据只是留痕，发布期用同一只读纯校验器按案内实物重算——旧 PASS 收据
    # （R08 修复前产出）与手改序列在这里失效；exploration/容差放宽已由上面三条拦。
    series_p = case_dir / Path(str((d.get("series") or {}).get("path") or "")).name
    facts_p = case_dir / Path(str((d.get("facts") or {}).get("path") or "")).name
    try:
        import figures_from_facts
        errs, _okc = figures_from_facts.fig2_check_errors(facts_p, series_p, FIGURE2_DEFAULT_TOL_PP)
    except (ValueError, OSError, KeyError, TypeError, AttributeError, OverflowError) as exc:
        errors.append(f"figure2 发布期重算失败: {exc}")
        return
    errors.extend(f"figure2 发布期重算: {e}" for e in errs)
```

说明：①`Path` 已在 `:16` import；②`figures_from_facts` 与本文件同目录，`build_html.py`/`stage2_closeout.py` 已用同方式局部 import 同目录模块（`:1525` `import facts_gate`、`:1817` `import holder_distribution_scan` 为同款惯例）；它会连带 import `standard_charts`→matplotlib，属发布期一次性成本，登记 §4；③docstring `:1552-1558` 追加一行 `F04（7.2.1）：两输入实物在场时用 fig2_check_errors 重算，收据 PASS 不作为放行依据。`；④`fig2_check_errors` 并非只抛 ValueError：`:298-302` 只把装载阶段 OSError/ValueError 转 ValueError，其后 `:309` `line.get(...)`（series 元素为 null）、`:330-331` `int(str(ent.get(...)))`/除法（facts 顶层非对象、current_raw 超大整数）会抛 AttributeError/OverflowError（复核 r1 实证三例），故 except 元组含这两类，一律转 "发布期重算失败"；`Facts.__init__`（facts_gate `:110-116`）缺 total_supply_raw 抛 ValueError，已覆盖；⑤`fig2_check_errors` 对非 list series 返回 `["--series 应为图 2 whale_series JSON（list of lines）"]`，走 `errors.extend` 即可；⑥`_okc==0 且 errs==[]`（空 series）维持基线放行——split-run.md:183 用户已接受残余，不在本段扩。

### 2.2 `scripts/tests/test_repair_batch_c.py` —— 新用例 `_f04_case_1..4` 并挂进 `t_r08_nonfinite`

在 `:1465`（锚 `def _r08_case_13():`）所在函数结束后、`:1497`（锚 `def t_r08_nonfinite():`）之前新增四个子函数（各自 tempdir；facts 同 `:1111-1120` 夹具：e1 current 278 / total 1000 → 27.8；`check`/`run`/`ROOT` 为既有；`import audit_release_gate as gate` 同 `:1112`）；在 `:1510`（锚 `    _r08_case_13()`，唯一）之后紧接四行调用 `_f04_case_1()` … `_f04_case_4()`。`main()` 不动。

1. `F04 手写 PASS 收据末点不同源拒`：ws `[{"entity_id":"e1","ts":["2026-01-01"],"pct":[90.0]}]`；手写 PASS 收据（schema/mode formal/tol 0.05/verdict PASS，facts/series `{path,sha256}` 用真实 sha，写法照 `:1176-1179`）→ `errs=[]; gate.check_figure2_receipt(td, rcpt, errs)`；断言 `any("发布期重算" in x and "≠ facts 当前" in x for x in errs)`。**RED**（基线 `[]`）。
2. `F04 手写 PASS 收据 NaN 字面量拒`：ws 原文 `[{"entity_id":"e1","ts":["2026-01-01"],"pct":[NaN]}]`（`write_text` 写原文）；手写 PASS 收据 sha 正确 → 断言 `any("重算失败" in x for x in errs)`。**RED**。
3. `F04 真跑 check 同源收据仍放行（GREEN→GREEN）`：ws pct `[27.8]`；`p = run([fff, "check", "--facts", "facts.json", "--series", "ws.json"], td)`（既有 `run()` `:60` 已自动前置 `sys.executable`，**不得再传解释器**，否则 rc=1 SyntaxError）→ `p.returncode == 0`；读 `figure2_check_receipt.json` 喂消费者 → `errs == []`。
4. `F04 输入缺席不重算不重复报错`：ws 不写；手写收据 series.path 指 `ws.json`（不存在）→ `errs` 恰 1 条且含"不在案根"，且无"重算"字样。GREEN→GREEN（验 §1.4）。

**既有用例 `_r08_case_12`（定义 `:1430`）须同步订正**：`:1453`（锚 `        check("R08 同输入手写 PASS 基线消费者接受", errs == [], str(errs))`，唯一）改为

```python
        check("R08 消费者对 NaN 手写收据直接拒（F04）",
              any("重算失败" in x for x in errs), str(errs))
```

`:1454-1462`（跑 check → 收据 FAIL → 消费者报"非 PASS"）保持。该订正断言在基线为 RED，一并记入证据。

RED 证据：改生产代码前逐个调用 `_f04_case_1..4` 与订正后的 `_r08_case_12`，记录 1/2 与 `_r08_case_12` 的 AssertionError 原文（含命令与被测文件 sha256）。

## 3. 完成报告 `F04_done.md` 必含

①0.1 两条命令输出；②2.1/2.2 `git diff` 原文；③RED 摘要；④0.8 各测试结果尾行；⑤1.1 三个字节数；⑥`git diff --stat`；⑦与工单差异/停工点（含 `_r08_case_12` 实际订正行号）；⑧禁读披露。stdout 首行 `# 施工 F04：完成` 或 `# 施工 F04：停工`。

## 4. 登记不修（`code_change_pending.md`，调度方维护）

- 空 series（`lines_checked==0`）仍放行：split-run.md:183 用户 2026-08-18 接受的残余。
- 发布闸 import `figures_from_facts` 连带 matplotlib（`standard_charts.py:38` 已 `matplotlib.use("Agg")`）：import 会初始化字体/配置缓存，有一次性磁盘 I/O，缓存与临时目录均不可用时抛 OSError（except 内转闸错误）；new-analysis 链 `check_figure1_legend_receipt:1586` 与 `stage2_closeout:410` 本就 import figures，新增的只是直接调用图 2 校验器；若日后要拆，把 `fig2_check_errors`/`_pct_value_ok`/`_load` 迁到无绘图依赖模块属另单。
- `stage2_closeout` 强检查未成必经：本段以重算闭合"错误数据放行"，closeout 必经化属 7.1.0 遗留清单。
- 收据 schema 不升版：重算只使**输入不符合当前校验规则**的旧 PASS 失效（合法同源旧收据仍过），不需要 v2。
