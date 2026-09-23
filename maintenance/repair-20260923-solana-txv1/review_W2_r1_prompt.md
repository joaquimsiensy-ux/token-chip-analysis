# 只读复核任务：工单 W2 v1（盲审 r1 消化）

纪律：**只读**，不改文件、不 commit；禁读 `~/.codex`（启动自动披露除外）、`~/Documents`、`~/Desktop`。

材料：`maintenance/repair-20260923-solana-txv1/workorder_W2_v1.md`、`blind_review_W1_r1_report.md`。

任务：核对 W2 的修法是否正确消化盲审 P1/P2，且不引入回归；用 `grep -n`/`nl -ba` 亲核工单每个行号与锚文本；特别核：①深验里按 seq 顺序取前 rows 行 slot 的可行位置（`solana_exact_validate.py:1370-1392` 行循环结构）；②`sorted(all_candidates)` 与生产者 `plan["candidate_slots"]` 是否严格同构（`sqd_gap_repair.py:595-596`）；③E27(d) 现有正向产物能否被 §3 向量复用而不破坏后续断言；④CHANGELOG 头部对成本指标的规则。**报告作为最终回复文本直接输出**，首行 `# 复核 W2 r1: 通过 / 退回`，正文 ≤ 60 行，结尾「v2 修订清单」（通过则写“无”）。
