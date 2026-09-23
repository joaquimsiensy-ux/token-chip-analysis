# 只读复核：工单 W3 v1（分支 fix/solana-txv1）

纪律：**只读**，不改文件、不 commit；禁读 `~/.codex`（启动自动披露除外）、`~/Documents`、`~/Desktop`；离线。报告**作为最终回复文本直接输出**，首行 `# 复核 W3 v1: 通过 / 退回`。

读 `maintenance/repair-20260923-solana-txv1/workorder_W3_v1.md` 与 `blind_review_W1_r2_report.md`，对照 `scripts/tests/test_sqd_gap_repair.py:960-1010` 与 `scripts/lib/solana_exact_validate.py:1340-1360,1520-1535` 实况，回答：①工单对根因的描述是否准确（该向量是否确实在 :1353 被先拒）；②§1 改法是否让该向量真正走到 `_plan_digest_from_generation` 并被拒，期望 reason 子串是否仍匹配；③§2 隔离证据方法是否可行、是否有更简做法；④行号/锚文本是否与实况一致；⑤有无遗漏的同类"被前置检查挡住"的向量（逐个看该循环里其余 6 个向量）。逐条给结论与文件:行；不通过项给具体改法。
