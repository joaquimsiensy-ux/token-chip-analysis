# 盲审 F07（r2）提示词（只读，r1 FAIL 一项 minor 修复后的复核）
# 审查范围 commit＝git diff 0b0a5f6..bf60b50 -- scripts/ maintenance/repair-20260918-p0-f04-f07/workorder_F07.md maintenance/repair-20260918-p0-f04-f07/F07_done.md（F07 施工 commit a201c63＋文本修复 commit bf60b50）

## r2 说明（最重要）
- r1（`blind_F07_reply_r1.md`）判 FAIL，唯一缺陷 F07-B1-01（minor）：工单 §1.4 与 `F07_done.md` ⑦ 的存量迁移命令漏必填 `--out-dir`。修复 commit bf60b50 只改这两处文本，`scripts/` 零改动。
- 本轮任务：①核 bf60b50 是否闭合 F07-B1-01（命令含 `--out-dir <补算工作目录>` 且保留两次 `--only-addrs`，与 `scripts/evm/replay_duck.py` 参数定义一致）；②用 `git diff a201c63..bf60b50 -- scripts/` 确认为空；③r1 其余判 PASS 的项不必重核，只需确认没有被 bf60b50 改动。
- **只看 git 对象**（`git show`/`git diff` 指定 commit），**不要以工作树文件为准、不要跑任何测试**：工作树同时有另一段（F05）的施工在进行，`scripts/report/facts_gate.py`、`scripts/report/audit_release_gate.py` 与若干测试文件可能含未提交改动，与本轮无关。
- 首行仍固定 `# 盲审 F07：PASS` 或 `# 盲审 F07：FAIL`。

## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260917-p0-four/` 以外的历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
2. 只读、离线、不 commit、不改文件。报告全文打印到 stdout，首行固定 `# 盲审 F07：PASS` 或 `# 盲审 F07：FAIL`。FAIL 时逐条给：编号（F07-B1-NN）、严重度（blocker/minor/nit）、位置 path:line、事实（代码原文或可复现命令）、修法建议。PASS 时列出实际核过的项与未实跑的项。
3. 这是常规盲审，不是攻击式验收：判断本段改动是否正确、完整地实现了工单不变量且无回归；不要求构造边界外攻击向量。

## 范围
- 审查对象：上方标注的 diff 范围；工单 `maintenance/repair-20260918-p0-f04-f07/workorder_F07.md`（最新版）与复核意见 `review_F07_reply_r*.md`；施工报告 `F07_done.md` 与 `F07_red_evidence.txt`。
- 不审：`references/`、`SKILL.md`、`commands-staging/`（本段零改动，只需确认 diff 未触及）；其他段。

## 任务
a) **不变量**：对照工单 §2 与 review 原始反例（工单头部引用的 repro 场景），逐条判断改后是否闭合；列出你核到的代码行。
b) **六视角**（`references/maintenance-review-repair.md` §1）：①字段来源 ②失败分支 ③存量迁移（工单 §1.4 若有）④同族调用面 ⑤producer/consumer 双向一致 ⑥检查点可绕性（同 schema 手写、改名、清空字段）。每视角给结论。
c) **测试真实性**：`F07_red_evidence.txt` 的 RED 是否与基线代码行为一致（用 `git show <前>:<path>` 读基线静态推演）；新用例断言是否真的区分改前改后；有无为了变绿而弱化的既有断言。
d) **回归**：`git diff --stat` 是否只含白名单；工单 §0.8 定向测试在 done 里是否有真实结果尾行；沙箱允许则实跑工单 §0.8 列出的测试，不允许则注明未实跑。
e) **工单符合度**：diff 是否有工单之外的改动（含注释/docstring/空白），有则列出并判断是否可接受。
