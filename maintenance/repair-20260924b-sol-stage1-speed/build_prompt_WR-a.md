# WR-a 施工提示词（codex --write）
## 纪律（优先级高于工单）
1. 你是施工者。工作目录 `/Users/uravvv/.claude/skills/token-chip-analysis`。**只按下方登记单 WR-a v2（已通过两轮 codex 复核）施工**：白名单仅 `scripts/lib/producer_history.py`（在元组闭合 `)` 前同构追加四条 ACTIVE 条目，保留全部既有条目不改）与完成报告 `maintenance/repair-20260924b-sol-stage1-speed/WR-a_done.md`。停工条件触发即停工写报告。
2. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读 `maintenance/repair-20260924b-sol-stage1-speed/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。禁读同样适用于子进程与测试（`test_sqd_gap_repair.py` 触及 `.staging_b3` 的用例不要运行，可用 `unittest.mock.patch.object` 临时跳过，报告列为「未运行，调度方本机补验」）。
3. 离线；不 commit、不 push；禁 stash/checkout/reset；不建 worktree；临时目录只用系统 tempfile；禁止批量删除。
4. 写入前按 0.2 三方比对 sha（`git show "<CODE_COMMIT>:scripts/solana/sqd_gap_repair.py" | shasum -a 256`、工作树 `shasum`、工单填值）；不一致停工。
5. 0.7 正式入口验收由调度方在登记 commit 后执行，**你不做**；0.4 的 `test_producer_registry_current.py` 你必跑并逐项判读（预期尾行 `producer registry: 2 FAIL`，仅 probe 两协议）。
6. 完成报告首行 `# WR-a 完成：…`，含复算记录、diff 行数、各测试尾行与剩余失败明细，**并把报告全文放在最终答复消息里**。

---

# 以下为登记单 WR-a v2 全文

