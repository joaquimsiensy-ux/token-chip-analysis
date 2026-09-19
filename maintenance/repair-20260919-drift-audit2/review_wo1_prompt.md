# 工单 R1 复核提示词（只读）

## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`（含通配读取）；`maintenance/` 下只读本工程目录 `maintenance/repair-20260919-drift-audit2/`。
2. 只读、离线、不 commit、不新建文件。报告打印到 stdout，首行：`# 工单R1复核：通过` 或 `# 工单R1复核：退回`。

## 任务
复核 `maintenance/repair-20260919-drift-audit2/workorder_r1.md`（依据同目录 `blind_r1a_report.md`、`blind_r1b_report.md`），逐条审：
a) 每个锚 `grep -n -F` 恰 1 处且行号与工单一致；
b) **专门核每条"依据"里的代码事实**：工单引用的脚本行号与行为描述（如 audit_release_gate expanded 分流、facts_gate facts_inputs 必填、price_check exit 3、stage2_closeout 只接 PASS/WARN、figures_from_facts 不落收据的分支、peaks_daily `--pct` 默认与口径、state_from_facts 序列逐点相等）是否真实存在于现行代码；替换后的文本是否与代码一致、有无新引入不实断言；
c) 字节预算（§1.1）是否可达：逐条按 UTF-8 计算净增，核对 ≤930330 与 commands-staging = 8789 是否成立；
d) 回归面：同一概念在其他文档是否还有同款旧表述被漏掉（例如 wallet 公式、exit 3 回退、峰值宏口径、≤500 点、第⑤条）；白名单是否够用；
e) 是否遵守"只改文本、删除>修改>新增、不增加 skill 上下文"原则，有无更短的等价改法；
f) 是否越界修了范围外问题（结构/门禁有效性/代码质量等）或把措辞偏好当漂移。
输出：通过/退回 ＋ 逐条意见（采纳需给出替换文本原文），末尾汇总表。
