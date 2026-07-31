---
description: 对已有筹码研报做增量更新——只拉上次截止点之后的新数据，扫新庄/旧庄增减持/观察哨核查，交付轻量更新简报
argument-hint: <代币名或旧研报目录路径> [补充信息]
---

调用 token-chip-analysis skill 的**增量更新模式**：

**标的：$ARGUMENTS**

1. 按 `references/update-workflow.md` U0–U6 执行；铁律 7 条与"判定标准一律以当前 skill 版本为准（判级变化须区分持仓变动 vs 标准迁移）"以 SKILL.md 为准。
2. 找不到旧研报或不满足增量前提时按 U0 兜底分级处理，明确建议 /token-analyze 全量重做，不硬凑。
3. 交付到旧研报目录：轻量更新简报 HTML ＋ 滚动更新的 appendix.json（细则按 U5，build_html WARN=0）。
