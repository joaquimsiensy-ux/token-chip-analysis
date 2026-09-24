# WR-b 调度方验收（2026-09-24）

- 施工任务：codex `task --write --fresh`（task-muffpmct），HEAD fcf81f0；只改 `scripts/lib/producer_history.py` +16/−0（两条同构 ACTIVE：coverage/v1、coverage-pointer/v1；sha `d4adc0c8…`、commit `f78b5c4…`、reason「9.2.0 驳回继承导出/继承（W1）＋find-known-map（W2）」），既有 38 条未动，现 40 条。
- 本机：`test_producer_registry_current` **0 FAIL rc=0**（53 项 ok）；test_sqd_coverage_probe 24/24、test_f03 15/15、test_batch3 PASS。
- commands 同步：`commands-staging/token-analyze-1.md` → `~/.claude/commands/token-analyze-1.md`（备份 `token-analyze-1.md.bak_20260924_072213`；同步前部署件与 W2 前 staging 逐字一致，同步后 cmp 逐字一致；`test_commands_deploy_sync` 转 PASS）。
- run_all：见追记。
- 0.7 验收：写模式任务 `formal_entry_WR-b_prompt.md` → `WR-b_formal_entry.md`，结果追记。
