# 工单 W1 复核提示词 r4（只读）
## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读本工程目录 `maintenance/repair-20260924b-sol-stage1-speed/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
2. 只读、离线、不 commit、不新建/修改文件。**报告全文放在最终答复消息里**。工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`，基线＝HEAD（含 W3 施工 commit 6b36dcd；三个 W1 生产文件相对 cc6298b 无差异）。
3. 每条意见须给出可直接替换进工单的原文（含行号/锚），标注「必改/建议/存疑」；结尾汇总表。若 v4 已可派工，明确写「通过」并只列建议项。
首行固定 `# 工单W1复核r4：通过` 或 `# 工单W1复核r4：退回`。
## 任务
复核 `maintenance/repair-20260924b-sol-stage1-speed/workorder_W1.md`（**v4**，已吸收你 r3 意见 `review_W1_reply_r3.md` 的必改 1 与建议 2、3）。逐条核：§0.1/1.10/1.11/§3 的 `W1_BASE` 门禁在当前 HEAD 下能否通过（实际跑 `git diff --quiet 6b36dcdd043d0b2b51c03de9ab0bb555b25f436a HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md assets`）；§2.6(c) 部分继承正例/负例措辞；§2.2 helper 签名；其余不再重复 r2/r3 已通过项，除非发现新的事实错误。
