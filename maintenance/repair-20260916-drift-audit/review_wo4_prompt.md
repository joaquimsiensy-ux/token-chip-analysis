# 工单 R4 复核提示词（只读）

## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`（含通配读取）。
2. 只读、离线、不 commit。报告打印到 stdout，首行：`# 工单R4复核：通过` 或 `# 工单R4复核：退回`。

## 任务
复核 `maintenance/repair-20260916-drift-audit/workorder_r4.md`（依据 `blind_r4_report.md`）：
a) 每个锚 `grep -n -F` 恰 1 处且行号一致；
b) 替换文本与 `scripts/` 代码事实一致（D1 select_fig1_series 三集合与 stack_exempt_for 豁免派生、D2 retrospective 版本约定原文、D3 §3.6 与 accounting_gate 窗口、D4 SigCache.put 路径表达式）；
