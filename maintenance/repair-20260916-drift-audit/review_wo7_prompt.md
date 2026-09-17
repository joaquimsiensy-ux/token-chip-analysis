# 工单 R7 复核提示词（只读）

## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`（含通配读取）。
2. 只读、离线、不 commit。报告打印到 stdout，首行：`# 工单R7复核：通过` 或 `# 工单R7复核：退回`。

## 任务
复核 `maintenance/repair-20260916-drift-audit/workorder_r7.md`（依据 `code_change_pending.md` 三项与用户裁决）：
a) 每个锚 `grep -n -F` 恰 1 处且行号一致；
b) 替换文本与 `scripts/` 代码事实一致（D1 wave_scan.py:735-746 浮点比较事实与例外措辞是否如实；D2/D3 两处 .py 改动是否仅注释/docstring、锚唯一、contract_manifest/invariant_manifest 无 needle 撞击、无哈希绑定）；
