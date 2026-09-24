# W1F 调度方验收（2026-09-24）

- 施工任务：codex `task --write --fresh`（首派 task-mufaof0u 因调度方树不净按 §0.1 停工，见 `W1F_done_halt_r1.md`；重派 task-mufas2p7 完成）。
- 生产 diff 亲核：`scripts/lib/solana_exact_validate.py` 恰 2 处整行替换（:567 空响应→全 1 映射；:586 完整响应→缺失 slot 补 1），与返修单 v2 §2.1 逐字一致；`_validated_inherited`、`:536` 早退未动。numstat 2/2 与 76/0。
- 本机定向（含施工方按禁读纪律跳过的 `.staging_b3` 四入口，全部完整运行）：

| 入口 | rc | 尾行 |
|---|---|---|
| test_sqd_coverage_probe | 0 | PASS SQD coverage probe: 20/20 offline groups |
| test_f03_sharedmap_reuse | 0 | PASS F-03 shared-map reuse: 15/15 groups |
| test_batch3_solana_producers | 0 | PASS B3-G2 |
| test_reconcile_v4_receipt | 0 | GREEN 32 |
| test_batch4_invariant_guards | 0 | PASS B4-G1 |
| test_exemption_guards | 0 | PASS EX-01 |
| test_sqd_gap_repair（完整） | 0 | GREEN 29c |
| invariant_scan | 0 | PASS exceptions=0 |

- run_all（`MPLCONFIGDIR=~/.matplotlib`，本机）：PASS 149 项，红 2 项与 W1 收官时完全相同——① `test_producer_registry_current` 6 FAIL＝probe/repair 改动未登记（预期，WR-a/WR-b 登记后消）；② `test_stage2_reseal.dry_run_touches_nothing`「验收 worktree 缺失」＝环境项，非回归。日志 scratchpad `run_all_W1F.log`。
- 盲审 r3：提示词 `blind_W1_prompt_r3.md`，结果 `blind_W1_reply_r3.md`。
