# 工单 W1 复核提示词 r3（只读）
## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读本工程目录 `maintenance/repair-20260924b-sol-stage1-speed/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
2. 只读、离线、不 commit、不新建/修改文件。**报告全文放在最终答复消息里**。工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`，基线＝HEAD（含 `cc6298b`；注意 HEAD 已含 W3 施工 commit——`scripts/lib/net.py` 与 `scripts/tests/test_net_result.py` 相对 cc6298b 有差异，其余生产源码无差异）。
3. 每条意见须给出可直接替换进工单的原文（含行号/锚），标注「必改/建议/存疑」；结尾汇总表。若 v3 已可派工，明确写「通过」并只列建议项。
首行固定 `# 工单W1复核r3：通过` 或 `# 工单W1复核r3：退回`。
## 任务
复核 `maintenance/repair-20260924b-sol-stage1-speed/workorder_W1.md`（**v3**，已吸收你 r2 意见 `review_W1_reply_r2.md`；背景 `README.md`、`fable_probes_20260924.md`）。重点对照 `review_W1_reply_r2.md` 8 条逐一核吸收；再亲核 v3 新写的修复来源字段（`sqd_gap_repair.py:1336-1350/:1483-1490/:1587-1591`）、副本发布协议定形（`_same_generation/_clear_pending/RawBytes`）、`--no-repair` 冲突路径、链式 evidence 转换与 `origin_asset_sha256` 规则是否自洽可施工。
