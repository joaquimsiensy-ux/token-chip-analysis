---
description: 对指定代币做简化筹码筛查——引擎与完整版同强度（采集/对账/深挖/复核不减），只交付阵营演变图(含价格)+阵营划分表+判定块的单页 HTML
argument-hint: <代币名或合约地址> [链名等补充信息]
---

调用 token-chip-analysis skill 的**简化筛查模式**：

**标的：$ARGUMENTS**

1. 按 `references/easy-workflow.md` E0–E7 执行；铁律 7 条与"绝不自动转完整版"以 SKILL.md 为准。**分析引擎与完整版同强度、一分不减，砍掉的只有完整报告的排版交付**。
2. 地址核定：只给代币名先多源交叉核定并 AskUserQuestion 确认；来自初筛清单的地址可直接采信，但多链硬关卡与供给口径核定不可跳。
3. 交付到工作目录 `<代币>分析/`：单页 HTML ＋ `analysis-state.json` ＋ charts png（细则按 E5，build_html WARN=0 才交付）。
