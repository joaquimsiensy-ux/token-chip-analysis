# 工单R7复核：通过

未发现本次 a/b 范围内需退回的问题。报告已打印到 stdout。

| 项目 | `grep -n -F` 实测 | 结果 |
|---|---|---|
| D1 | [analyze-workflow.md:158](/Users/uravvv/.claude/skills/token-chip-analysis/references/analyze-workflow.md:158) | 恰 1 处，行号一致 |
| D2 | [decode_txs_v2.py:8](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/decode_txs_v2.py:8) | 恰 1 处，行号一致 |
| D3 | [standard_charts.py:283](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/standard_charts.py:283) | 恰 1 处，行号一致 |

- **D1 措辞属实。** [wave_scan.py:735](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/wave_scan.py:735) 使用浮点阈值。抽取原表达式复算：`total=10^24` 时，0.1%／默认 0.05% 阈值分别上浮 `131072`／`65536 raw`，恰好达线确实可能丢标记。`peak_top200` 是整数排名判断，不受影响。
- **D2/D3 均仅改 docstring。** D2 与实际 `sig[:2]` 分片一致；D3 与 [stage2_closeout.py:197](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/stage2_closeout.py:197) 拒绝 `merge_groups` 一致。内存替换后，两文件语法检查通过，去除 docstring 后 AST 完全一致。字节数为 `16952→16947`、`23051→23009`；D1 净增 `237 B`。
- **无 needle 撞击。** 全部 200 条 contract needle 在目标文件中的命中状态不变；实际 invariant 扫描函数对替换前后的识别结果完全一致。
- **未发现两脚本源码哈希绑定。** 两者均未登记于 `producer_history`；核查调用点及源码摘要引用未发现相关校验。decode 收据绑定的是失败签名与输出文件哈希。

复核前后 HEAD 均为 `2c560d669c114c9f44fb44d19a556b4ab83fee69`，工作树干净。未修改文件、未联网、未 commit，未主动读取禁读路径。

本结论仅针对工单复核；未运行 §1.2 整套施工守卫，未独立重放 APU 原始案例。首次 here-document 被只读沙箱拒绝，随后改用 `python3 -B -c` 完成内存核验。
