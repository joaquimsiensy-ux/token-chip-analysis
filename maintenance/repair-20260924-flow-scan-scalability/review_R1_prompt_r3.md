# 工单 R1 复核提示词 r3（只读）

## 纪律
同 r1/r2：禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读本工程目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。只读、离线、不 commit、不新建/修改文件。**报告全文放在最终答复消息里**。首行固定 `# 工单R1复核r3：通过` 或 `# 工单R1复核r3：退回`。工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`，基线＝HEAD（含 `634c083`）。

## 任务
复核 `maintenance/repair-20260924-flow-scan-scalability/workorder_R1.md`（v3）对你 r2 报告（`review_R1_reply_r2.md`）六处修订的落地：①`:194` 锚；②1.1 候选遍历顺序句；③1.5 保序段（注意：调度方本机探针 `R1_fable_ctas_probe.md` 与你 r2 的 rowid 实验结论互补——rowid 无下降但点查慢约 180 倍，据此把"临时设 true"从可选改为必须，请评估该改写是否成立、措辞是否越过证据）；④0.7 空 elig/负值/EVM block 互斥三处追加；⑤0.8 全文替换；⑥§3 措辞。逐处对照原文给出是否准确，有无引入新矛盾或遗漏；再通读全单一遍指出任何仍会让施工者停工或误解的表述。若全部落地且无新问题，判"通过"并给出施工者最容易踩的三个点作提醒（不改工单）。
