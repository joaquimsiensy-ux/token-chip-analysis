# 工单R4复核：通过

本次要求的 a、b 两项均通过，未发现需退回的问题。

| 条目 | 锚点文件 | 预期行／实测行 | `grep -n -F` 命中 |
|---|---|---:|---:|
| D1 | `references/casebook/supply-accounting.md` | 82／82 | 1 |
| D2 | `references/analyze-workflow.md` | 198／198 | 1 |
| D3 | `references/data-pipeline-evm-channels.md` | 245／245 | 1 |
| D4 | `references/data-pipeline-solana-capture.md` | 169／169 | 1 |

四个锚的全文出现次数也均为 1。

- **D1：一致。** [select_fig1_series](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/standard_charts.py:178) 返回实绘、豁免、拒绝三集合；`ts` 不属于阵营键，拒绝集合非空时绘图入口报错。因此成功出图后的“实绘＋豁免键＝传入阵营键”成立。[stack_exempt_for](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/camp_series_provenance.py:75) 按格式派生：`sol-rows` 豁免两种烧毁键，`evm-dict` 仅豁免 `burn_cum_pct`，`sol-anchor-rows` 无豁免。离线复算含合法输入、未知键及未知格式，均符合代码。
- **D2：一致。** [retrospective 原文](/Users/uravvv/.claude/skills/token-chip-analysis/references/retrospective.md:139)明确：“主版本=不兼容的工作流/schema/入口边界变更；次版本=向后兼容的新能力、新公开接口或持久化契约扩展（含分析复盘迭代）；修订号=既定契约内的修复、加固、回归补充与文档修订。”下一行另列 labels 数据版本。替换为引用该约定，消除了固定增加次版本的冲突。
- **D3：一致。** [§3.6](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-evm-channels.md:227)记载历史 `eth_call` 约 128 块且节点池深度抖动；[accounting_gate](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/accounting_gate.py:309) 的非 archive rebase 窗口实际为 `min(window, 64, tip - 1)`。替换文本符合该口径；本次未联网验证节点现状。
- **D4：一致。** [SigCache.put](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/decode_txs_v2.py:75) 的实际表达式为 `fp = self.root / f"{row['sig'][:2]}.jsonl"`，没有固定 256 桶映射。提取表达式离线复算，4,096 个合成 Base58 输入产生 **898** 个不同路径，支持删除“256 片”。

当前 HEAD 为 `d7fd9eb5`；本次核对的正文和代码与工单内容基线 `388eed6` 无差异，核对路径前后状态均为空。全程离线，未修改文件、未 commit；未执行施工及其守卫验收。
