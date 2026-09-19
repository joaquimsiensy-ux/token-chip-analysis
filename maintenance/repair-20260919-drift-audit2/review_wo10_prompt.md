# 工单 R10 复核提示词（只读）

## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`（含通配读取）；`maintenance/` 下只读本工程目录 `maintenance/repair-20260919-drift-audit2/`。
2. 只读、离线、不 commit、不新建文件。报告打印到 stdout，首行：`# 工单R10复核：通过` 或 `# 工单R10复核：退回`。

## 任务
复核 `maintenance/repair-20260919-drift-audit2/workorder_r10.md`（v1；依据同目录 `blind_r10a_report.md`、`blind_r10b_report.md`），逐条审：
a) 每个锚按代码块内整行 `grep -n -F` 恰 1 处且行号与工单一致；
b) **专门核每条"依据"里的代码事实**（identity_snapshot_receipt 是否在 raw/supply 重放前先核 producer 哈希等于当前 scan_token_accounts.py 并 exit 2；scan_token_accounts 写 producer.sha256 为自身文件哈希；新句两个条件是否与代码校验顺序和语义一致）是否真实存在于现行代码；替换后文本与代码一致、无新引入不实断言；
c) 字节预算按 UTF-8 逐条重算，是否等于工单声明值；一处整行替换无删行；
d) 回归面：同一概念在其他文档是否还有同款旧表述被漏掉（"直接重新 emit"、round4b 存量在其他文档的同款残留；新句有无更短等价写法；是否有旧案存量因此须重跑扫描器需登记）；白名单是否够用；
e) 是否遵守"只改文本、删除>修改>新增、不增加 skill 上下文"，有无更短等价改法；
f) 是否越界修了范围外问题或把措辞偏好当漂移。
输出：通过/退回 ＋ 逐条意见（采纳需给出替换文本原文）＋ 汇总表。
