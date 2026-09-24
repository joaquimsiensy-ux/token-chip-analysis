# 工单 W5 复核提示词 r1（只读）
## 纪律
1. 只读、离线、不 commit、不新建/修改文件；禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读 `maintenance/repair-20260924b-sol-stage1-speed/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。工作目录 `/Users/uravvv/.claude/skills/token-chip-analysis`。**报告全文放最终答复消息里**，首行固定 `# 工单W5复核r1：通过` 或 `# 工单W5复核r1：退回`。
2. 这是对一份纯文本修正工单的可执行性与正确性复核，不是施工。
## 任务
复核 `maintenance/repair-20260924b-sol-stage1-speed/workorder_W5.md`（出处 `review_final_reply_r1.md` P2/P3）。请独立核：
a) 六处旧片段在 HEAD 是否各恰命中 1 处（`grep -n -F -e`），行号与工单一致；
b) 新片段是否与 `_find_known_map` 的真实退出码契约一致（exit 1 扫描级故障保留 chosen 但不得采用；exit 2 无图；exit 0 采用），并与 W2 工单 §2.1 一致；措辞有无歧义；
c) CHANGELOG 三处归并的每个事实是否有依据（`WR-b_acceptance.md`、`WR-b_formal_entry.md`、`WR-a_formal_entry.md`、`W2_acceptance.md`、`fable_probes_20260924.md` P3/P5、`review_final_reply_r1.md`），有无预填未发生的 PASS 或夸大（尤其"完整生产链路吞吐收益未证明"是否保留）；
d) 字节预算是否可达（自行按新旧片段 UTF-8 长度计算）；`test_g3_docs_guards`/`docs_lint` 是否会因 CHANGELOG 内加链接或粗体配对而报错；不升版本是否合规（`CHANGELOG.md:4` 档位规则；尚未 push）；
e) 白名单/不改清单与纪律有无自相矛盾。
退回须逐条给必改项与依据；通过也列核了什么。