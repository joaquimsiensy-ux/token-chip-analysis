# 工单 T3 复核提示词 r2（只读）

纪律同 `review_T3_prompt.md`；报告全文放最终答复消息；首行固定 `# 工单T3复核r2：通过` 或 `# 工单T3复核r2：退回`。工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`，基线＝HEAD。

任务：复核 `maintenance/repair-20260923-t1-spotcheck-dir-input/workorder_T3.md`（v2；v1 存 `workorder_T3_v1.md`，你的 r1 意见存 `review_T3_reply_r1.md`）。
a) 逐条核 r1 汇总表各项是否在 v2 吸收（①入口/缓存/witness 边界、1.1 共享发布收据重建、1.2 前提、1.3/2.1(c) 两行简化、0.5、步骤 4/5/6、L61 不刷新、索引 176 B、详细段成本与存量影响）。
b) 亲核步骤 6 needle：`_shared_authority` 对文件输入在覆写 CSV 末字节后，被拒文本是否恰为 `time plan input identity sha256 mismatch`（含外层前缀后的完整文本亦请给出）；步骤 5 needle `input directory contains symlink` 经外层前缀后是否仍被 `_expect_reject` 的子串匹配命中。
c) v2 相对 v1 是否引入新问题；索引行 176 B 实测。
输出：通过/退回 ＋ 逐条意见（采纳需给出替换文本原文）＋ 汇总表。
