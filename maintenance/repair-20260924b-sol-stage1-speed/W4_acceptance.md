# W4 调度方验收（2026-09-24）

- 施工任务：codex `task --write --fresh`（task-mufbx196），基线 cfe2f41，无停工、无中途提问。
- 生产 diff 亲核（`scripts/solana/sqd_gap_repair.py` 19/33，增删 52 ≤60）：`_census_body` 经 `sqd_query_body` 复用 instruction 字段选择器与 `instructions` 过滤；`_fetch_live_slot` 改为单次 `sqd-census`（经 `_sqd_call_with_backoff`）→ 去重（>1 拒 `SQD census duplicated slot`）→ present/nonce_count（算法与被删 `_state_probe` 一致，不截断）→ `validate_coverage_state_consistency`（Helius 之前，函数体未动）→ Helius；原第二次 census 与「探针/census 块头不一致」检查删除；`_state_probe` 定义删除，仓库零残留（`grep -c` = 0）；`_probe_fingerprint`/β 搜索/退避未动；头部加 9.2.0 换代注释。与工单 §2.2 逐项一致。
- 本机定向（含施工方按禁读纪律跳过的 `.staging_b3` 夹具入口，全部完整运行）：

| 入口 | rc | 尾行 |
|---|---|---|
| test_sqd_gap_repair（完整） | 0 | GREEN 29c |
| test_batch8_repair_scale（完整） | 0 | PASS batch8: key-neutral identity/pool failover/ordered workers/resume/streaming |
| test_batch3c_census_fields | 0 | PASS batch3c census fields match the SQD contract |
| test_sqd_coverage_probe | 0 | PASS 20/20 |
| test_batch3_solana_producers | 0 | PASS B3-G2 |
| test_repair_batch1 | 0 | PASS v6.41.0 batch1 |
| test_reconcile_v4_receipt | 0 | GREEN 32 |
| test_batch4_invariant_guards | 0 | PASS B4-G1 |
| test_exemption_guards | 0 | PASS EX-01 |
| invariant_scan | 0 | PASS exceptions=0 |

- run_all（本机）：PASS 149 项；红 2 项同 W1/W1F——① producer 登记守卫 6 FAIL（probe 哈希 `ab2371f5…`、repair 哈希 `15822564…` 未登记；WR-a/WR-b 登记后消）；② reseal 环境项。日志 scratchpad `run_all_W4.log`。
- 施工者结束检查报告 `workorder_W2.md` 有外部修改：系调度方在施工期间补记 §0.5 grep `-e` 说明（工作树、未 commit），不影响 W4。
- 后续：codex 盲审（`blind_W4_prompt.md`→`blind_W4_reply_r1.md`）；WR-a 登记（`workorder_WR-a.md`）；登记后真实注册表入口验收记于 `WR-a_acceptance.md`。
