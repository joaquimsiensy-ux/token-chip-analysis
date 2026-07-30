---
description: 批量预采集多个代币的全量转账事件——只采集不分析，产物落各币标准工作目录，后续 /token-easy-analysis 或 /token-analyze 直接复用（断点续拉增量）
argument-hint: <币1 链 地址> <币2 链 地址> …（或初筛清单文件路径 / 自然语言列表）
---

调用 token-chip-analysis skill 的**批量预采集模式**，对以下候选清单只做全量转账事件采集：

**清单：$ARGUMENTS**

执行要求：
1. **只采集，不分析，零结论**：对账/重放/聚类都是后续分析会话的事。
2. 全部执行细节按 skill 的 `references/collect-workflow.md`：清单解析（地址核定规则、Solana 必查发射时间）→ plan.json → run_guarded 脱管队列（泳道调度/跨进程锁/--resume）→ 夜间模式（pending_plan.json）。
3. 脱管后交代：预计总时长、collect_manifest 路径、查进度命令；结束汇报只给采集事实（每币状态/行数/块范围/耗时/落盘路径），`done_with_gaps` 与 `failed` 单独点名。
4. 衔接：已采集币后续跑分析命令时同目录开工自动复用并断点续拉增量，采集成本不重复发生。
