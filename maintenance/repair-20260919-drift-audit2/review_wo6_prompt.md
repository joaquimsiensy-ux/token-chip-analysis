# 工单 R6 复核提示词（只读）

## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`（含通配读取）；`maintenance/` 下只读本工程目录 `maintenance/repair-20260919-drift-audit2/`。
2. 只读、离线、不 commit、不新建文件。报告打印到 stdout，首行：`# 工单R6复核：通过` 或 `# 工单R6复核：退回`。

## 任务
复核 `maintenance/repair-20260919-drift-audit2/workorder_r6.md`（v1；依据同目录 `blind_r6a_report.md`、`blind_r6b_report.md`），逐条审：
a) 每个锚按代码块内整行 `grep -n -F` 恰 1 处且行号与工单一致；
b) **专门核每条"依据"里的代码事实**（replay_pass1 去重键 (tag,tx,li) 与 li 来源；tiering 类型②措辞上限与 :60 分开报；solana-scan:116 与 methods:102 的共用出纳表述）是否真实存在于现行代码；替换后文本与代码一致、无新引入不实断言；
c) 字节预算按 UTF-8 逐条重算，不高于基线是否成立；两处均整行替换无删行；
d) 回归面：同一概念在其他文档是否还有同款旧表述被漏掉（"tx hash 去重"与"一律高度疑似"在其他文档的同款表述；D2 收窄后是否与 methods:102、tiering §6 硬规则冲突；D1 删除后"容忍少量重复"是否仍有去重出处）；白名单是否够用；
e) 是否遵守"只改文本、删除>修改>新增、不增加 skill 上下文"，有无更短等价改法；
f) 是否越界修了范围外问题或把措辞偏好当漂移。
输出：通过/退回 ＋ 逐条意见（采纳需给出替换文本原文）＋ 汇总表。
