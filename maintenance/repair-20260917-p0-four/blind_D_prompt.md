# 盲审 D 提示词（只读，施工后独立复核）

## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md` 的内容；禁读 `/Users/uravvv/Desktop` 下任何文件。
2. 只读、离线、不 commit、不改文件。报告全文打印到 stdout，首行固定 `# 盲审 D：PASS` 或 `# 盲审 D：FAIL`。FAIL 时逐条给：编号、严重度（blocker/minor/nit）、位置 path:line、事实（代码原文或可复现命令）、修法建议。PASS 时列出实际核过的项与未实跑的项。
3. 这是常规盲审，不是攻击式验收：目标是判断本段改动是否正确、完整地实现了工单不变量且无回归；不要求构造边界外攻击向量。

## 范围
- 审查对象：`git diff __BASE__..__HEAD__ -- scripts/ references/`（施工 commit 范围，由调度方填入）；工单 `maintenance/repair-20260917-p0-four/workorder_D.md`（以文件头版本号为准）；施工报告 `D_done.md` 与 `D_red_evidence.txt`；工单复核记录 `review_D_reply_r*.md`。
- 不审：`SKILL.md`、`commands-staging/`（本段零改动，只需确认 diff 未触及）；其他段（R03/R07/R08）。

## 任务
a) **不变量**：①发布闸 `check_daily_peaks` 用 rglob 在案内任意子目录定位 `peaks_summary.json`（跳隐藏/`_history`/符号链接/`.duck_tmp`），零份 return、多份拒，其余文件相对 summary 所在目录解析；②summary 必须登记 `needs_block_precision_sha256` 并与实物咬合；③needs 各档 ∪ trigger_days 活跃候选非空时 `block_precision_followup.json` 必在，schema `block-precision-followup/v1`、engine `replay_duck.py`、inputs 绑 needs（及 trigger_days）sha、addresses 覆盖并集每址且形状 `{peak, peak_blk}`；④`peaks_daily.py` summary 新增 needs sha；⑤`replay_duck.py --only-addrs` 只算指定地址的块级峰值（窗口 SQL 与全量逐字同源、无门槛、无事件地址 peak 0/peak_blk null）、写收据到首个 --only-addrs 文件目录、**不**触碰全量产物（replay_stats/peaks/balances_final/mint_ledger/merged/pass2）；⑥原有错误文案逐字保留。逐条对照 diff 判断是否成立，列出你核到的代码行。
b) **六视角**（`references/maintenance-review-repair.md` §1）：①字段来源（并集与覆盖用实物重算还是 summary 自报）②失败分支（多份/缺 sha/不咬合/缺收据/少址/schema 错/inputs sha 错 是否都 fail-closed 且错误互斥可断言）③存量迁移（旧 summary 无 needs sha 的存量案改后必红＝设计意图；无 peaks 产物的案零影响）④同族调用面（其他读 `peaks_summary.json`/`needs_block_precision.json` 的消费者是否漏改）⑤双向一致性（recon.md:132 / tiering.md:149 新句与代码行为；`peaks_daily.py` docstring）⑥检查点可绕性（summary 放两处、needs 改档名、followup 用旧 needs sha、`--only-addrs` 传空/坏 JSON）。每视角给结论。
c) **测试真实性**：`D_red_evidence.txt` 的 RED 是否与基线一致（用 `git show __BASE__:<path>` 静态推演）；`_r09_case_1..7`、`followup_case`、`test_peaks_daily` 新断言是否真的区分改前改后；有无为了变绿而弱化既有断言（尤其 h 例 summary 如何处理缺 needs sha）。
d) **回归**：`git diff --stat` 只含白名单；工单 §0.8 各测试在 `D_done.md` 有真实结果尾行；沙箱允许则实跑 `python3 -B scripts/tests/test_audit_release_gate.py`、`test_engine_equivalence.py`、`test_peaks_daily.py`、`invariant_scan.py`，不允许则注明。
e) **工单符合度**：diff 有无工单之外改动（含注释/docstring/空白）；references 字节是否恰 930061、SKILL.md 8021、commands-staging 8798（只 stat）。
