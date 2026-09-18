# 盲审 F04（r1）提示词（只读，施工后独立复核）
# 审查范围 commit＝git diff b1ccf23..b794325 -- scripts/（F04 施工 commit b794325）

## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260917-p0-four/` 以外的历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
2. 只读、离线、不 commit、不改文件。报告全文打印到 stdout，首行固定 `# 盲审 F04：PASS` 或 `# 盲审 F04：FAIL`。FAIL 时逐条给：编号（F04-B1-NN）、严重度（blocker/minor/nit）、位置 path:line、事实（代码原文或可复现命令）、修法建议。PASS 时列出实际核过的项与未实跑的项。
3. 这是常规盲审，不是攻击式验收：判断本段改动是否正确、完整地实现了工单不变量且无回归；不要求构造边界外攻击向量。

## 范围
- 审查对象：上方标注的 diff 范围；工单 `maintenance/repair-20260918-p0-f04-f07/workorder_F04.md`（最新版）与复核意见 `review_F04_reply_r*.md`；施工报告 `F04_done.md` 与 `F04_red_evidence.txt`。
- 不审：`references/`、`SKILL.md`、`commands-staging/`（本段零改动，只需确认 diff 未触及）；其他段。

## 任务
a) **不变量**：对照工单 §2 与 review 原始反例（工单头部引用的 repro 场景），逐条判断改后是否闭合；列出你核到的代码行。
b) **六视角**（`references/maintenance-review-repair.md` §1）：①字段来源 ②失败分支 ③存量迁移（工单 §1.4 若有）④同族调用面 ⑤producer/consumer 双向一致 ⑥检查点可绕性（同 schema 手写、改名、清空字段）。每视角给结论。
c) **测试真实性**：`F04_red_evidence.txt` 的 RED 是否与基线代码行为一致（用 `git show <前>:<path>` 读基线静态推演）；新用例断言是否真的区分改前改后；有无为了变绿而弱化的既有断言。
d) **回归**：`git diff --stat` 是否只含白名单；工单 §0.8 定向测试在 done 里是否有真实结果尾行；沙箱允许则实跑工单 §0.8 列出的测试，不允许则注明未实跑。
e) **工单符合度**：diff 是否有工单之外的改动（含注释/docstring/空白），有则列出并判断是否可接受。
