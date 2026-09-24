# WR-b 调度方验收（2026-09-24）

- 施工任务：codex `task --write --fresh`（task-muffpmct），HEAD fcf81f0；只改 `scripts/lib/producer_history.py` +16/−0（两条同构 ACTIVE：coverage/v1、coverage-pointer/v1；sha `d4adc0c8…`、commit `f78b5c4…`、reason「9.2.0 驳回继承导出/继承（W1）＋find-known-map（W2）」），既有 38 条未动，现 40 条。
- 本机：`test_producer_registry_current` **0 FAIL rc=0**（53 项 ok）；test_sqd_coverage_probe 24/24、test_f03 15/15、test_batch3 PASS。
- commands 同步：`commands-staging/token-analyze-1.md` → `~/.claude/commands/token-analyze-1.md`（备份 `token-analyze-1.md.bak_20260924_072213`；同步前部署件与 W2 前 staging 逐字一致，同步后 cmp 逐字一致；`test_commands_deploy_sync` 转 PASS）。
- run_all：见追记。
- 0.7 验收：写模式任务 `formal_entry_WR-b_prompt.md` → `WR-b_formal_entry.md`，结果追记。

## 追记（2026-09-24）
- run_all（本机）：PASS 150 项；唯一红项 `test_stage2_reseal.dry_run_touches_nothing`「验收 worktree 缺失」＝环境项（登记守卫与 commands 同步守卫均已转 PASS）。日志 scratchpad `run_all_WRb.log`。
- 0.7 验收（写模式任务 `WR-b_formal_entry.md`）：**PASS**——真实 `historical_producer_hashes` 两协议均含 `d4adc0c8…`（各 5 个 ACTIVE）；仅内存移除两条登记后两协议均不含（各 4 个）；`_w1_run` 动态夹具真实 `validate_coverage` ok=True reasons=[]；既有 38 条字节级不变；守卫 0 FAIL。
- **WR-b 收官。**
