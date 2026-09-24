# W1 施工提示词（codex --write）
## 纪律（优先级高于工单）
1. 你是施工者。工作目录 `/Users/uravvv/.claude/skills/token-chip-analysis`。**只按下方工单（v4）施工**，不扩展范围；工单内「停工」条件触发即停工写报告。
2. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读 `maintenance/repair-20260924b-sol-stage1-speed/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。禁读纪律同样适用于你运行的子进程与测试（`test_sqd_gap_repair.py`/`test_batch8_repair_scale.py` 触及 `.staging_b3` 的用例不要运行，报告列为「未运行，调度方本机补验」）。
3. 离线；不 commit、不 push；禁 stash/checkout/reset；不建 worktree；只写工单白名单文件与完成报告；临时目录只用系统 tempfile；禁止批量删除。
4. 完成报告写到 `maintenance/repair-20260924b-sol-stage1-speed/W1_done.md`，**并把报告全文放在最终答复消息里**。停工同样写报告并说明原因。
5. 本单较大：先通读工单与相关源码再动手；实现优先复用现有 helper；每个施工点改完即跑对应定向测试。
