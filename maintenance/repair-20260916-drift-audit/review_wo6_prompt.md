# 工单 R6 复核提示词（只读）

## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`（含通配读取）。
2. 只读、离线、不 commit。报告打印到 stdout，首行：`# 工单R6复核：通过` 或 `# 工单R6复核：退回`。

## 任务
复核 `maintenance/repair-20260916-drift-audit/workorder_r6.md`（依据 `blind_r6_report.md`）：
a) 每个锚 `grep -n -F` 恰 1 处且行号一致；
b) 替换文本与 `scripts/` 代码事实一致（D1 同文 :117 与 :247 的规则原文、同句"同窗批次注资＝中等"是否已独立覆盖被删例外的信息；本条为文档内部口径冲突，无代码事实）；
