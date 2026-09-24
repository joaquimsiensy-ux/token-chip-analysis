# 返修单 W1F 复核提示词 r1（只读）
## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读 `maintenance/repair-20260924b-sol-stage1-speed/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
2. 只读、离线、不 commit、不新建/修改文件。**报告全文放最终答复消息里**。工作目录 `/Users/uravvv/.claude/skills/token-chip-analysis`，基线＝HEAD（含 65132ab）。
3. 每条意见给可直接替换进工单的原文并标「必改/建议/存疑」；结尾汇总表。可派工写「通过」。首行固定 `# 返修单W1F复核r1：通过` 或 `# 返修单W1F复核r1：退回`。
4. 这是数据校验器正确性（fail-closed）审查，负例＝不合法输入应被拒收。
## 任务
复核 `maintenance/repair-20260924b-sol-stage1-speed/workorder_W1F.md`（v1；背景 `blind_W1_reply_r2.md` 的反例与 `workorder_W1.md` v4）。亲核事实①–③行号与探针语义是否一致；§1.1 修法是否足以让反例 A/B 被拒且不引入误拒（例如跨案边界 recheck 行、canary 区间、部分继承）；§2.2 两负例/两正例是否可在现有夹具体系构造；有无更小或更正确的修法。
