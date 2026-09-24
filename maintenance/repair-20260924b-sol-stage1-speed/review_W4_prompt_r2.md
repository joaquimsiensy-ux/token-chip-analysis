# 工单 W4 复核提示词 r2（只读）
## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读本工程目录 `maintenance/repair-20260924b-sol-stage1-speed/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
2. 只读、离线、不 commit、不新建/修改文件。**报告全文放在最终答复消息里**。工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`，基线＝HEAD（须含 `cc6298b`；生产源码相对 cc6298b 仍无差异）。
3. 每条意见须给出可直接替换进工单的原文（含行号/锚），并标注「必改/建议/存疑」；结尾给汇总表（条目/等级/依据文件:行）。你复核的是**工单定形**，不是施工；工单事实与源码不符优先级最高。若 v2 已可派工，明确写「通过」并只列建议项。
首行固定 `# 工单W4复核r2：通过` 或 `# 工单W4复核r2：退回`。

## 任务
复核 `maintenance/repair-20260924b-sol-stage1-speed/workorder_W4.md`（**v2**，已吸收你上一轮 r1 意见 `review_W4_reply_r1.md`；背景 `README.md`、调度方实测 `fable_probes_20260924.md`）。逐条亲核事实段行号/锚（`grep -n -F -x`）与设计。重点：①r1 的 9 条是否每条被正确吸收（逐条对照 `review_W4_reply_r1.md`）；②事实⑥调度方实测记录（`fable_probes_20260924.md` §P2）是否足以支撑合并方案（是否还缺样本类型）；③1.2 新采/认领区分与 2.5 深验兼容测试是否可在现有夹具体系构造；④派工基线为 W1 收官 commit（W1 改本脚本 `validate_coverage_state_consistency` 一函数），本单与 W1 改动是否可能冲突。
