# 工单 R5 复核提示词（只读）

## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`（含通配读取）。
2. 只读、离线、不 commit。报告打印到 stdout，首行：`# 工单R5复核：通过` 或 `# 工单R5复核：退回`。

## 任务
复核 `maintenance/repair-20260916-drift-audit/workorder_r5.md`（依据 `blind_r5_report.md`）：
a) 每个锚 `grep -n -F` 恰 1 处且行号一致；
b) 替换文本与 `scripts/` 代码事实一致（D1 四处登记源地址一致且坑册同行另两址与地址簿一致、D2 stage2_closeout 对 merge_groups 的处理与 figures_from_facts 逐线核对语义）；
