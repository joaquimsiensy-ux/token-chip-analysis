# W5 施工提示词（codex --write）
## 纪律（优先级高于工单）
1. 你是施工者。工作目录 `/Users/uravvv/.claude/skills/token-chip-analysis`。**只按下方工单 W5 v3（已通过三轮 codex 复核）施工**：六处逐字片段替换＋完成报告，不扩展范围；停工条件触发即停工写报告。
2. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读 `maintenance/repair-20260924b-sol-stage1-speed/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。禁读同样适用于子进程与测试。
3. 离线；不 commit、不 push；禁 stash/checkout/reset；不建 worktree；只写工单 §0.3 白名单四文件与完成报告；测试临时目录按 §0.7 保留（`self._finalizer.detach()`）、禁自动删除；禁止批量删除。
4. 完成报告写到 `maintenance/repair-20260924b-sol-stage1-speed/W5_done.md`，**并把报告全文放在最终答复消息里**。
5. 替换前用 `grep -n -F -e "<旧片段>"` 确认各恰 1 处；替换后 `wc -c` 核字节预算；`test_commands_deploy_sync.py` 预期 FAIL 如实写。

---

# 以下为工单 W5 v3 全文

