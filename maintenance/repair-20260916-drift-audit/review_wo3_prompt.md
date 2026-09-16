# 工单 R3 复核提示词（只读）

## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`（含通配读取）。
2. 只读、离线、不 commit。报告打印到 stdout，首行：`# 工单R3复核：通过` 或 `# 工单R3复核：退回`。

## 任务
复核 `maintenance/repair-20260916-drift-audit/workorder_r3.md`（依据 `blind_r3_report.md`）：
a) 每个锚 `grep -n -F` 恰 1 处且行号一致；
b) 替换文本与 `scripts/` 代码事实一致（D1 sqd_gap_repair 的 KEYS_FILE/KEY_FILE 读取顺序与显式覆盖参数、D2 生产者排序键与消费者校验条件、F3 stake_decode 容差）；
