# 工单R5复核：通过

未发现需要退回的缺陷，完整报告已打印到 stdout。

| 锚点 | `grep -n -F` 命中数 | 实际／工单行号 |
|---|---:|---:|
| [data-pipeline-robinhood-traps.md](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-robinhood-traps.md:62) | 1 | 62／62 |
| [report-template.md](/Users/uravvv/.claude/skills/token-chip-analysis/references/report-template.md:162) | 1 | 162／162 |

**D1 通过。** 四处登记均为 `0xe72688f7d25d7318b9a81f21edda640ca948c83b`：

- [address-book.md:147](/Users/uravvv/.claude/skills/token-chip-analysis/references/address-book.md:147)
- [labels-robinhood.csv:85](/Users/uravvv/.claude/skills/token-chip-analysis/references/labels/labels-robinhood.csv:85)
- [goldset.csv:881](/Users/uravvv/.claude/skills/token-chip-analysis/references/labels/benchmark/goldset.csv:881)
- [manual_labels.csv:118](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/labels/sources/manual_labels.csv:118)

坑册同行的 DexAggregatorCore、relayer 两址分别与地址簿第 154、156 行一致。删除重复硬编码、改指向地址簿有据；未裁定链上真值。

**D2 通过。**

- [stage2_closeout.py:197](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/stage2_closeout.py:197)：`merge_groups` 键在场即 `WORKORDER BLOCK`，包括 `null`、空列表和实际分组。
- [figures_from_facts.py:292](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/figures_from_facts.py:292)：逐线优先按有效实体 ID、否则按标签匹配一个实体，再核对其末点；没有成员持仓求和语义。
- 原函数内存复现：9 条独立实体线通过；三种合并声明均被拒绝；将 1.7% 合计值挂到当前占比 0.8% 的单实体上，报差 0.9 个百分点。替换文本准确。

内存替换实测净减 **18／63 B，合计 81 B**，与工单一致。

HEAD 前后均为 `3bbf6fedaa22aed4a4c0d31d466b0ac4f11286ba`，工作树前后均为空。全程只读、离线、无文件写入、无提交，未读取禁读路径。通过范围为本次工单 a/b 复核；未执行施工或 §1.2 守卫。
