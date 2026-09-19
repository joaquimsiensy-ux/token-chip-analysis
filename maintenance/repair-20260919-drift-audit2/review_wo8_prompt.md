# 工单 R8 复核提示词（只读）

## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`（含通配读取）；`maintenance/` 下只读本工程目录 `maintenance/repair-20260919-drift-audit2/`。
2. 只读、离线、不 commit、不新建文件。报告打印到 stdout，首行：`# 工单R8复核：通过` 或 `# 工单R8复核：退回`。

## 任务
复核 `maintenance/repair-20260919-drift-audit2/workorder_r8.md`（v1；依据同目录 `blind_r8a_report.md`、`blind_r8b_report.md`；R8a 待确认项由 Fable 亲核升为 D2），逐条审：
a) 每个锚按代码块内整行 `grep -n -F` 恰 1 处且行号与工单一致；
b) **专门核每条"依据"里的代码事实**（solana_observation 观测请求 filters 是否确无 dataSize 且两程序同路径、choose_datasizes 是否确无调用；accounting_gate_sol 写 v1 与 shared_release_receipt 分链要求；capture §8 确无 Plan B 定义；C-06/E-12 条目确在 -methods 续册且主册无同号）是否真实存在于现行代码；替换后文本与代码一致、无新引入不实断言；
c) 字节预算按 UTF-8 逐条重算，是否等于工单声明值；九处均整行替换无删行；
d) 回归面：同一概念在其他文档是否还有同款旧表述被漏掉（dataSize 165/datasizes、accounting-gate/v2 无链限定、Plan B、指向主册的 C-06/E-12 在其他文档的同款残留；D4 改为不带路径的"casebook C-06"是否与文档既有惯例一致、docs_lint 引用检查是否仍通过；D1 新句是否准确反映"显式 165 对 SPL 被接受但被忽略"）；白名单是否够用；
e) 是否遵守"只改文本、删除>修改>新增、不增加 skill 上下文"，有无更短等价改法；
f) 是否越界修了范围外问题或把措辞偏好当漂移。
输出：通过/退回 ＋ 逐条意见（采纳需给出替换文本原文）＋ 汇总表。
