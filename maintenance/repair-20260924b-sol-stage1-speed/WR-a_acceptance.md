# WR-a 调度方验收（2026-09-24）

- 施工任务：codex `task --write --fresh`（task-mufdgtam），HEAD c3660b1；只改 `scripts/lib/producer_history.py` +32/−0（元组闭合前追加四条同构 ACTIVE：cache/v4、repair-bundle/v1、coverage-resolution/v1、repair-pointer/v1；sha `15822564…`、commit `59f88b8…`、reason「9.2.0 α/β 候选修复状态探针并入 census 请求（W4）」），既有 34 条未动。
- 本机定向（含完整 `.staging_b3` 夹具）：test_sqd_gap_repair rc=0 GREEN 29c；test_batch3_solana_producers PASS；test_sqd_coverage_probe 20/20；test_f03_sharedmap_reuse 15/15；invariant_scan PASS；`test_producer_registry_current` 尾行 `producer registry: 2 FAIL`（rc=1）——repair 四协议 ok、38 条 Git 复现 ok，剩余仅 probe 两协议未登记（WR-b 预期）。
- 登记 commit：见下（本文件与登记同 commit）。
- 0.7 真实注册表入口验收：由 codex 只读任务执行（`blind_WR-a_prompt.md` → `blind_WR-a_reply_r1.md`），结果追记于本文件末尾。
