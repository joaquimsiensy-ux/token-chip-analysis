# 盲审 A 提示词（只读，施工后独立复核）

## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md` 的内容。
2. 只读、离线、不 commit、不改文件。报告全文打印到 stdout，首行固定 `# 盲审 A：PASS` 或 `# 盲审 A：FAIL`。FAIL 时逐条给：编号、严重度（blocker/minor/nit）、位置 path:line、事实（代码原文或可复现命令）、修法建议。PASS 时列出实际核过的项与未实跑的项。
3. 这是常规盲审，不是攻击式验收：目标是判断本段改动是否正确、完整地实现了工单不变量且无回归；不要求构造边界外攻击向量。

## 范围
- 审查对象：`git diff __BASE__..__HEAD__ -- scripts/`（施工 commit 范围，由调度方填入）；工单 `maintenance/repair-20260917-p0-four/workorder_A.md`（v2）；施工报告 `A_done.md` 与 `A_red_evidence.txt`。
- 不审：`references/`、`SKILL.md`、`commands-staging/`（本段零改动，只需确认 diff 未触及）；其他段（R03/R07/R09）。

## 任务
a) **不变量**：图 2 对账（`figures_from_facts.py check`）对任何非有限、非数值、bool、字符串 pct 及 NaN/Infinity JSON 字面量一律 FAIL 且留 FAIL 收据；合法有限序列行为不变；fig1 state 路径保留宽松解析与 `burn_cum_pct` 字段级报错。逐条对照 diff 判断是否成立，列出你核到的代码行。
b) **六视角**（`references/maintenance-review-repair.md` §1）：①字段来源 ②失败分支 ③存量迁移 ④同族调用面（`_load` 7 处调用、其他读 series/facts 的路径）⑤双向一致性（producer `dumps_fig2_series` 与 consumer `fig2_check_errors`）⑥检查点可绕性（陈旧 PASS 收据、exploration 模式、`--series` 非 list 特判）。每视角给结论。
c) **测试真实性**：`A_red_evidence.txt` 里的 RED 是否与基线代码行为一致（可用 `git stash` 以外的方式：`git show __BASE__:scripts/report/figures_from_facts.py` 读基线源码静态推演）；十个用例的断言是否真的区分改前改后；有无为了变绿而弱化的断言。
d) **回归**：`git diff --stat` 是否只含白名单；工单 §0.8 五个定向测试在 `A_done.md` 里是否有真实结果尾行；沙箱允许则实跑 `python3 -B scripts/tests/test_repair_batch_c.py` 与 `test_figures_from_facts.py`，不允许则注明未实跑。
e) **工单符合度**：diff 是否有工单之外的改动（含注释/docstring/空白），有则列出并判断是否可接受。
