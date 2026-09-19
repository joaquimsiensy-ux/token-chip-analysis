# 工单 R3 v2 复核提示词（只读，第二轮）

## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`（含通配读取）；`maintenance/` 下只读本工程目录 `maintenance/repair-20260919-drift-audit2/`。
2. 只读、离线、不 commit、不新建文件。报告打印到 stdout，首行：`# 工单R3复核r2：通过` 或 `# 工单R3复核r2：退回`。

## 任务
复核 `maintenance/repair-20260919-drift-audit2/workorder_r3.md`（**v2**，是否正确吸收第一轮复核 `review_wo3_reply.md` 的意见：D1 整行锚、D2 只补类型、D3 删过强说明并补 :667；依据同目录 `blind_r3a_report.md`、`blind_r3b_report.md`），逐条审：
a) 每个锚按代码块内整行 `grep -n -F` 恰 1 处且行号与工单一致；
b) **专门核每条"依据"里的代码事实**（sqd_gap_repair `--live-canary` 归属与 canary 比对内容、`sqd_blockhash` 缺块分支为 None、sqd_coverage_probe 回退对象初值与写出）是否真实存在于现行代码；替换后文本与代码一致、无新引入不实断言；
c) 字节预算按 UTF-8 逐条重算，≤930260 与净减 6 B 是否成立；表格行 `\|` 转义是否按字面处理；
d) 回归面：同一概念在其他文档是否还有同款旧表述被漏掉（live-canary、sqd_blockhash、shared_map 子字段在 scan-schemas 其他段或其他文档的同款约束）；白名单是否够用；
e) 是否遵守"只改文本、删除>修改>新增、不增加 skill 上下文"，有无更短等价改法；
f) 是否越界修了范围外问题或把措辞偏好当漂移。
只对 v2 新引入或未吸收的问题退回，不重复第一轮已被采纳的意见。输出：通过/退回 ＋ 逐条意见（采纳需给出替换文本原文）＋ 汇总表。
