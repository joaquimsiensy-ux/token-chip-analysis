# 工单 T2 复核提示词 r3（只读，范围限定）

纪律同 `review_T2_prompt_r2.md`；报告全文放最终答复消息；首行固定 `# 工单T2复核r3：通过` 或 `# 工单T2复核r3：退回`。工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`，基线＝HEAD。

任务：只核 `workorder_T2.md`（v3）相对 v2 的三处文本修订是否逐字吸收你 r2 的替换文（§1.2 整行、§2.3 H16 括号内兜底文字、§2.1 注释锚三行原文补全），以及 v3 除这三处与版本标题/修订说明外无其他变化（可 `git diff HEAD~1 -- maintenance/repair-20260923-t1-spotcheck-dir-input/workorder_T2.md`）。通过则一句话＋汇总表；退回给出替换文本。
