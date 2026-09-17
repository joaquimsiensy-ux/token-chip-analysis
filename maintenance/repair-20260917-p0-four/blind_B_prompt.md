# 盲审 B 提示词（只读，施工后独立复核）

## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md` 的内容；禁读 `/Users/uravvv/Desktop` 下任何文件。
2. 只读、离线、不 commit、不改文件。报告全文打印到 stdout，首行固定 `# 盲审 B：PASS` 或 `# 盲审 B：FAIL`。FAIL 时逐条给：编号、严重度（blocker/minor/nit）、位置 path:line、事实（代码原文或可复现命令）、修法建议。PASS 时列出实际核过的项与未实跑的项。
3. 这是常规盲审，不是攻击式验收：目标是判断本段改动是否正确、完整地实现了工单不变量且无回归；不要求构造边界外攻击向量。

## 范围
- 审查对象：`git diff 0877f71..03507cb -- scripts/`（施工 commit 范围，由调度方填入）；工单 `maintenance/repair-20260917-p0-four/workorder_B.md`（以文件头版本号为准）；施工报告 `B_done.md` 与 `B_red_evidence.txt`；工单复核记录 `review_B_reply_r*.md`。
- 不审：`references/`、`SKILL.md`、`commands-staging/`（本段零改动，只需确认 diff 未触及）；其他段（R07/R08/R09）。

## 任务
a) **不变量**：三账检查 `check_three_ledgers` 中，`wallet_self_held_raw`/`confirmed_economic_control_raw` 只由 strict 成员位置之和（＋已闭合设施）闭合，expanded 成员位置之和只进 `expanded_economic_control_range_raw` 上限；有 expanded 成员则该字段必填；字段在场（含显式 null）须为两元素数组、下限＝confirmed 重算值、上限 ≥ 下限＋Σexpanded；逐地址闭合与实体集合闭合对 expanded 仍生效；无 expanded 且无该字段的存量案零新增错误。逐条对照 diff 判断是否成立，列出你核到的代码行。
b) **六视角**（`references/maintenance-review-repair.md` §1）：①字段来源（区间用重算值还是自报值）②失败分支（缺字段/形状/数值三类是否都 fail-closed）③存量迁移（只有 strict 成员的旧三账是否零影响；batch15/batch_d 夹具）④同族调用面（`check_ledger`、`run()` 调用点、其他读三账的脚本是否有同族口径遗漏）⑤双向一致性（与 `references/economic-control-accounting.md:40-44、:80、:93`、`playbook-entity-cluster-tiering.md:145、:150` 的口径是否一致）⑥检查点可绕性（`:907-909` 坏位置行、excluded 成员、跨实体地址）。每视角给结论。
c) **测试真实性**：`B_red_evidence.txt` 里的 RED 是否与基线代码行为一致（用 `git show 0877f71:scripts/report/audit_release_gate.py` 读基线源码静态推演）；十个用例的断言是否真的区分改前改后；有无为了变绿而弱化的断言；直调 `check_three_ledgers(chain=None)` 的封装是否使绿例断言 `errors == []` 有意义（`balance_source` sha 绑定仍生效）。
d) **回归**：`git diff --stat` 是否只含白名单；工单 §0.8 三个定向测试在 `B_done.md` 里是否有真实结果尾行；沙箱允许则实跑 `python3 -B scripts/tests/test_audit_release_gate.py` 与 `test_batch15_three_ledgers_frozen.py`，不允许则注明未实跑。
e) **工单符合度**：diff 是否有工单之外的改动（含注释/docstring/空白），有则列出并判断是否可接受。
