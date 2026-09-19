# 工单 R1 v2 复核提示词（只读，第二轮）

## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`（含通配读取）；`maintenance/` 下只读本工程目录 `maintenance/repair-20260919-drift-audit2/`。
2. 只读、离线、不 commit、不新建文件。报告打印到 stdout，首行：`# 工单R1复核r2：通过` 或 `# 工单R1复核r2：退回`。

## 任务
复核 `maintenance/repair-20260919-drift-audit2/workorder_r1.md`（**v2**）是否正确吸收第一轮复核 `review_wo1_reply.md` 的意见。调度方的处置：D1/D8/D9 照采；D3/D4/D5/D6/D7 采用复核建议文本；D2 采纳"锚去前导空格"，但**不采纳**"其余状态字段见编译器 schema"的写法（无可指的实锚），改为保留字段列举的压缩版；预算改 ≤930130。逐条核：
a) 每个锚按代码块内整行 `grep -n -F` 恰 1 处、行号一致（尤其 D2/D4/D6/D7 的代码块锚）；
b) 每条替换文本与现行代码事实一致，无新引入不实断言；D4 新 `:215` 与不动的 `:216` 连读是否通顺且无歧义；
c) 字节预算按 UTF-8 逐条重算，≤930130 与 commands-staging = 8789 是否成立；
d) 仍有异议的条目给出替换文本原文；只对 v2 新引入或未吸收的问题退回，不重复第一轮已被采纳的意见。
输出：通过/退回 ＋ 逐条意见 ＋ 汇总表。
