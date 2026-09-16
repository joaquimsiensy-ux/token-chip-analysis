# 工单R6复核：通过

1. **锚点通过。** [工单第 20 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260916-drift-audit/workorder_r6.md:20)的唯一替换锚经 `grep -n -F` 核验，恰命中 **1 处、第 155 行**；全文片段计数也为 1。

2. **替换依据通过。** 同文两条约束原文已核实：
   - [:117](/Users/uravvv/.claude/skills/token-chip-analysis/references/playbook-entity-cluster-methods.md:117)：“CEX 热钱包不可作为共同资金来源证据：从同一热钱包提币的地址不构成关联（热钱包是全用户共用资金池）”。
   - [:247](/Users/uravvv/.claude/skills/token-chip-analysis/references/playbook-entity-cluster-methods.md:247)：“funder 未证为私人钱包（≤15、非合约，或已有独立证据确属该实体）前，共同来源不得作合并边。”

   改为“一律剔除。”能够消除冲突，符合盲审报告的修法。

3. **信息覆盖并非等价。** [:155](/Users/uravvv/.claude/skills/token-chip-analysis/references/playbook-entity-cluster-methods.md:155)保留条款要求“约 90 分钟集中入金、多波重复”，不完全覆盖旧例外“48h＋行为指纹一致”。它独立保留符合条件的中等注资证据；行为指纹仍按 [:144](/Users/uravvv/.claude/skills/token-chip-analysis/references/playbook-entity-cluster-methods.md:144)独立评价。被取消的公共来源升级资格正是冲突所在，故不构成退回理由；不能将此次删除解释为两条规则完全重复。

4. **内存复算通过。** 仅第 155 行变化，净减 **55 B**（48061 → 48006 B），与工单一致。D1 属文档内部口径冲突，无代码事实验收项。

未读取禁区文件，未联网、写入或 commit。复核前后工作树均为空，HEAD 均为 `76e8635`，工单及目标文件哈希未变。未运行施工守卫；本结论为工单复核通过。
