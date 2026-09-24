# W5 盲审提示词（只读）
## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读 `maintenance/repair-20260924b-sol-stage1-speed/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
2. 只读、离线、不 commit、不新建/修改文件。**报告全文放最终答复消息里**。工作目录 `/Users/uravvv/.claude/skills/token-chip-analysis`。
3. 首行固定 `# W5盲审：PASS` 或 `# W5盲审：FAIL`。FAIL 必须给可复现依据；PASS 也要列独立验证了什么、没验证什么。
4. 这是文档修正的正确性审查，不涉及任何系统安全或对抗行为。
## 任务
W5 施工已 commit 到 HEAD。工单 `workorder_W5.md`（v3）、完成报告 `W5_done.md`、调度方验收 `W5_acceptance.md`。对 `git diff ef20dd825a0f3698bee79b6adfae59befcf6285d HEAD -- scripts references assets commands-staging SKILL.md VERSION pyproject.toml CHANGELOG.md` 做独立盲审：
a) 仅四文件六处变化，且每处新片段与工单 §2 逐字一致，同行其他文字未变；scripts/版本文件未动；
b) 三处采纳纪律文案与 `_find_known_map` 真实退出码契约（源码 `sqd_coverage_probe.py` 约 :1686）一致，且与 W2 工单 §2.1 一致；
c) CHANGELOG 三处归并的每个事实有依据（`WR-b_acceptance.md`、`WR-b_formal_entry.md`、`WR-a_formal_entry.md`、`W2_acceptance.md`、`fable_probes_20260924.md` P3/P5、`review_final_reply_r1.md`），W4 对照关系表述准确（header 三方、transactions/instructions 各两方），未预填未发生的 PASS，「完整生产链路吞吐收益未证明」保留；
d) 字节预算（references ≤+260、commands ≤+140、README ≤+160 相对 ef20dd8）；粗体配对与链接目标存在；
e) 收官 review 的 P2/P3 是否由此真正关闭。
