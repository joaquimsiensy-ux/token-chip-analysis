---
description: 批量预采集多个代币的全量转账事件——只采集不分析，产物落各币标准工作目录，后续 /token-easy-analysis 或 /token-analyze 直接复用（断点续拉增量）
argument-hint: <币1 链 地址> <币2 链 地址> …（或初筛清单文件路径 / 自然语言列表）
---

调用 token-chip-analysis skill 的**批量预采集模式**，对以下候选清单只做全量转账事件采集（只采集、零结论）：

**清单：$ARGUMENTS**

1. 全部执行细节按 `references/collect-workflow.md`（清单解析→plan.json→run_guarded 脱管队列→夜间模式）。
2. 脱管后交代：预计总时长、collect_manifest 路径、查进度命令；结束汇报只给采集事实（每币状态/行数/块范围/耗时/落盘路径），`done_with_gaps` 与 `failed` 单独点名。
