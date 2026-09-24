# 工单 W1 复核提示词 r2（只读）
## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读本工程目录 `maintenance/repair-20260924b-sol-stage1-speed/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
2. 只读、离线、不 commit、不新建/修改文件。**报告全文放在最终答复消息里**。工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`，基线＝HEAD（须含 `cc6298b`；生产源码相对 cc6298b 仍无差异）。
3. 每条意见须给出可直接替换进工单的原文（含行号/锚），并标注「必改/建议/存疑」；结尾给汇总表（条目/等级/依据文件:行）。你复核的是**工单定形**，不是施工；工单事实与源码不符优先级最高。若 v2 已可派工，明确写「通过」并只列建议项。
首行固定 `# 工单W1复核r2：通过` 或 `# 工单W1复核r2：退回`。

## 任务
复核 `maintenance/repair-20260924b-sol-stage1-speed/workorder_W1.md`（**v2**，已吸收你上一轮 r1 意见 `review_W1_reply_r1.md`；背景 `README.md`、调度方实测 `fable_probes_20260924.md`）。逐条亲核事实段行号/锚（`grep -n -F -x`）与设计。重点：①v2 三项新设计（资产副本 `source_ref` 随 coverage 发布件落盘作成员见证；`refuted_origin` 索引数组绑定 slot→证据；`origin_generated_at` 时效不随链式导出刷新）在现有发布协议（`publish_exclusive`/三目录 fsync/`_sha_ref`/`_check_file_ref`）下是否可实现、有无更简方案；②§2.2 校验器 helper 的绑定清单字段名是否与 bundle/resolution 实际一致（`coverage.map_sha256`、`plan_candidates.coverage/beta`、census 各字段）；③1.4 β 兼容的最小改法是否正确、白名单是否够；④2.6 夹具（≥10,000 块头、450 分页）是否可行；⑤r1 的 13 条是否每条都被正确吸收（逐条对照 `review_W1_reply_r1.md`），有无吸收错的。
