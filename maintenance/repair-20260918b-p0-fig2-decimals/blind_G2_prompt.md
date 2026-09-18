# 盲审 G2（r1）提示词（只读，施工后独立复核）
# 审查范围 commit＝git diff 6412d2e..9ecc962 -- scripts/ references/（G2 施工 commit 9ecc962）

## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260918-p0-f04-f07/` 与 `maintenance/repair-20260918b-p0-fig2-decimals/` 以外的历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。测试/守卫进程自行加载的历史文件按工单 §0.2 例外处理，你本人不读。
2. 只读、离线、不 commit、不改文件。报告全文打印到 stdout，首行固定 `# 盲审 G2：PASS` 或 `# 盲审 G2：FAIL`。FAIL 时逐条给：编号（G2-B1-NN）、严重度（blocker/minor/nit）、位置 path:line、事实（代码原文或可复现命令）、修法建议。PASS 时列出实际核过的项与未实跑的项。
3. 这是常规盲审，不是攻击式验收：判断本段改动是否正确、完整地实现了工单不变量且无回归；不要求构造边界外攻击向量。

## 范围
- 审查对象：上方标注的 diff 范围；工单 `workorder_G2_decimals.md`（v4）与复核意见 `review_G2_reply_r1.md`…`review_G2_reply_r4.md`；施工报告 `G2_done.md` 与 `G2_red_evidence.txt`（同目录）。
- 不审：G1（已收官）；`SKILL.md`、`commands-staging/`（本段零改动，只需确认 diff 未触及）。

## 任务
a) **终点判据（最重要）**：`ruling_20260918.md` 规定"修的终点是问题消失，不是盲审 PASS"。请**独立复现**原始反例 `decimals_selfreport`：EVM 案 raw_supply 不变，verify_recon config 从 `decimals=0/human=100` 改为 `decimals=2/human=1` 并更新内容哈希（inputs.config sha 与 wrapper sha 重绑），在 HEAD 上依次核：①`shared_release_receipt.validate_accounting_receipt` EVM 分支——accounting `checks.decimals` 与 bundle `supply.decimals` 不等须拒；②`audit_release_gate.check_facts_decimals`——config.decimals 与观测不一致须报"与链上观测 … 不一致"，facts.token.decimals 与观测不一致须拒；③`checks` 非 dict 须返回拒收理由而不抛异常。同时给出**来源链**：`evm_observation.observe_evm_supply` 第 4 笔 eth_call selector `0x313ce567` 的写出点行号→bundle `supply.decimals`→`accounting_gate` 写 `checks.decimals` 的行号→两处闸的读取行号；任何一环若仍是"自报对自报"即 FAIL。沙箱不能建临时目录则用内存执行真实函数并注明。
b) **不变量**：对照工单 §1.1–1.5 与 §2 逐条判断：transcript 恰 9 笔且方法序如 §1.4；decimals uint8 校验（观测侧＋bundle 校验侧）；schema v1→v2 共 18 处字面量同步、`validate_evm_observation_bundle` 对 v1 抛 ValueError；排除式 grep `evm-observation-bundle/v1` 在 scripts/references/SKILL.md/commands-staging 零命中（自行实跑，贴输出）；references 字节恰 +15、SKILL/commands 不变（自行实跑三条字节命令）。
c) **六视角**（`references/maintenance-review-repair.md` §1）：①字段来源（decimals 是否真来自链上 eth_call 而非任何 config/facts 自报）②失败分支（RPC 返回非法/越界/非标 ERC20 时的行为）③存量迁移（工单 §4 三类分述与代码是否一致；旧 v1 bundle 是否确被拒）④同族调用面（Solana 侧 `accounting_gate_sol.checks.decimals` 读取路径未回归；`_recon_bound_reality` 未动）⑤producer/consumer 双向一致 ⑥检查点可绕性（同 schema 手写 v2 bundle 无 decimals、decimals 为 bool/str、accounting 与 bundle 各填不同值）。每视角给结论。
d) **测试真实性**：`G2_red_evidence.txt` 四处 RED 是否与基线代码行为一致（`git show 6412d2e:<path>` 静态推演）；c 例（decimals=2 双错误）基线是否确为 `[]`；新用例断言是否真的区分改前改后；有无为了变绿而弱化的既有断言（尤其 transcript 下标顺延处）。
e) **回归**：`git diff --stat` 是否只含工单 §0.3 白名单；done 里 §0.8 各测试是否有真实结果尾行；沙箱允许则实跑 §0.8 列出的测试（至少 `test_evm_observation.py`、`test_evm_observation_nonempty_code.py`、`invariant_scan.py`、`docs_lint.py --all`），不允许则注明未实跑。
f) **工单符合度**：diff 是否有工单之外的改动（含注释/docstring/空白/文档新增句），有则列出并判断是否可接受。
