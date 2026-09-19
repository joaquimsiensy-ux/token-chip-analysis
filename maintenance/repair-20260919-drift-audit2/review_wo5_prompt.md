# 工单 R5 复核提示词（只读）

## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`（含通配读取）；`maintenance/` 下只读本工程目录 `maintenance/repair-20260919-drift-audit2/`。
2. 只读、离线、不 commit、不新建文件。报告打印到 stdout，首行：`# 工单R5复核：通过` 或 `# 工单R5复核：退回`。

## 任务
复核 `maintenance/repair-20260919-drift-audit2/workorder_r5.md`（v1；依据同目录 `blind_r5a_report.md`、`blind_r5b_report.md`），逐条审：
a) 每个锚按代码块内整行 `grep -n -F` 恰 1 处且行号与工单一致；
b) **专门核每条"依据"里的代码事实**（token-analyze-1 argument-hint 的 full 必填、spl_edge_core 按 (slot,tx_index) 分组与 digest 冲突硬失败、scan_bloxroute_seg 的 done.json/fails/空时间戳与无 scan_meta）是否真实存在于现行代码；替换后文本与代码一致、无新引入不实断言；
c) 字节预算按 UTF-8 逐条重算，不高于基线是否成立；整行删除是否连同换行计入；
d) 回归面：同一概念在其他文档是否还有同款旧表述被漏掉（token-analyze-1 调用示例、无 sig 去重、scan_meta/锚点采集在其他文档的同款表述；casebook S-04 六字段是否仍完整）；白名单是否够用；
e) 是否遵守"只改文本、删除>修改>新增、不增加 skill 上下文"，有无更短等价改法；
f) 是否越界修了范围外问题或把措辞偏好当漂移。
输出：通过/退回 ＋ 逐条意见（采纳需给出替换文本原文）＋ 汇总表。
