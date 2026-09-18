# 盲审 G1（r1）提示词（只读，施工后独立复核）
# 审查范围 commit＝git diff 40c090a..7a21bf1 -- scripts/（G1 施工 commit 7a21bf1）

## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260918-p0-f04-f07/` 与 `maintenance/repair-20260918b-p0-fig2-decimals/` 以外的历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。测试进程自行加载的历史文件按工单 §0.2 例外处理，你本人不读。
2. 只读、离线、不 commit、不改文件。报告全文打印到 stdout，首行固定 `# 盲审 G1：PASS` 或 `# 盲审 G1：FAIL`。FAIL 时逐条给：编号（G1-B1-NN）、严重度（blocker/minor/nit）、位置 path:line、事实（代码原文或可复现命令）、修法建议。PASS 时列出实际核过的项与未实跑的项。
3. 这是常规盲审，不是攻击式验收：判断本段改动是否正确、完整地实现了工单不变量且无回归；不要求构造边界外攻击向量。

## 范围
- 审查对象：上方标注的 diff 范围；工单 `workorder_G1_fig2.md`（v2）与复核意见 `review_G1_reply_r1.md`/`review_G1_reply_r2.md`；施工报告 `G1_done.md` 与 `G1_red_evidence.txt`（同目录）。
- 不审：`references/`、`SKILL.md`、`commands-staging/`（本段零改动，只需确认 diff 未触及）；G2。

## 任务
a) **终点判据（最重要）**：`ruling_20260918.md` 规定"修的终点是问题消失，不是盲审 PASS"。请**独立复现**原始反例：facts.json `{"token":{"total_supply_raw":"1000","decimals":0},"entities":{"e1":{"label":"大庄#1","current_raw":"100","peak_raw":"200","addresses":["A"]}}}` ＋ whale_series.json `[]`，在 HEAD 上依次跑 `figures_from_facts.py check`（须 rc≠0、写 FAIL 收据）、手写同 schema PASS 收据喂 `audit_release_gate.check_figure2_receipt`（须报"缺必画实体线"）；沙箱不能建临时目录则用内存执行真实函数并注明。再核 `build_html --mode analysis-new` 路径上该错误能否阻断落盘（静态：`build_html.py` 收集 errors 后的退出逻辑）。
b) **不变量**：对照工单 §2 逐条判断改后是否闭合；closeout `fig2_selection_errors` 与 `fig2_check_errors` 是否真的同一规则来源。
c) **六视角**（`references/maintenance-review-repair.md` §1）：①字段来源 ②失败分支 ③存量迁移（工单 §4）④同族调用面 ⑤producer/consumer 双向一致 ⑥检查点可绕性（同 schema 手写、改名、清空字段、id/label 混用重复线）。每视角给结论。
d) **测试真实性**：`G1_red_evidence.txt` 的 RED 是否与基线代码行为一致（`git show <前>:<path>` 读基线静态推演）；新用例断言是否真的区分改前改后；有无为了变绿而弱化的既有断言。
e) **回归**：`git diff --stat` 是否只含白名单；工单 §0.8 定向测试在 done 里是否有真实结果尾行；沙箱允许则实跑 §0.8 列出的测试，不允许则注明未实跑。
f) **工单符合度**：diff 是否有工单之外的改动（含注释/docstring/空白），有则列出并判断是否可接受。
