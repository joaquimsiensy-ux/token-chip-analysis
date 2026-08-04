---
description: 对指定代币做完整庄家链上行为分析（v5.0 三问一异常框架 + 对抗复核 + 自包含 HTML 报告）
argument-hint: <代币名或合约地址> [链名等补充信息]
---

调用 token-chip-analysis skill，对以下标的做完整分析：

**标的：$ARGUMENTS**

1. 按 skill 全流程路由表 A0–A5 执行（手册＝`references/analyze-workflow.md`；A6 复盘不自动执行，仅我明确要求时跑）；三问一异常框架、铁律 7 条、"监控包默认不生成"均以 SKILL.md 为准，此处不复述。
2. 只给代币名没给合约地址时：先多源交叉核定合约地址与所在链，AskUserQuestion 和我确认后再开工；同名多币把候选列表摆出来让我选。
3. 交付到当前工作目录：自包含 HTML 报告 ＋ `analysis-state.json`。
