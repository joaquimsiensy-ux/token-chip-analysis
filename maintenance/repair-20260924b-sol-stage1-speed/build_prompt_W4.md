# W4 施工提示词（codex --write）
## 纪律（优先级高于工单）
1. 你是施工者。工作目录 `/Users/uravvv/.claude/skills/token-chip-analysis`。**只按下方工单（v3.2；v3.1 已通过 codex 复核 r3，v3.2 仅由调度方填实基线与行号）施工**，不扩展范围；停工条件触发即停工写报告。派工基线 `W4_BASE=cfe2f41132bd3f162f3d356f359c9eba72a500d3` 已填入工单 §0.1；工单引用行号已由调度方按该基线重核，施工前仍按 §0.5 以整行锚重核（`grep -n -F -x` 恰 1 处）。
2. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读 `maintenance/repair-20260924b-sol-stage1-speed/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。禁读同样适用于子进程与测试（`test_sqd_gap_repair.py`/`test_batch8_repair_scale.py` 中触及 `.staging_b3` 的用例不要运行，报告列为「未运行，调度方本机补验」；可用 `unittest.mock.patch.object` 临时跳过，不改测试文件）。
3. 离线；不 commit、不 push；禁 stash/checkout/reset；不建 worktree；只写工单白名单文件与完成报告；临时目录只用系统 tempfile；禁止批量删除。
4. 完成报告写到 `maintenance/repair-20260924b-sol-stage1-speed/W4_done.md`，**并把报告全文放在最终答复消息里**。
5. 本单涉及 producer 换代与深验兼容三类用例，先通读工单事实段与 `_fetch_live_slot`/`_state_probe`/`_census_body` 及两份测试文件再动手；每个施工点改完即跑对应定向测试；`_state_probe` 删除前按 §1.5 核引用。
