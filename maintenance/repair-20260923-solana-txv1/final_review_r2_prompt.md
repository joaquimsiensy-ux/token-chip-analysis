# 收官 review r2：分支 fix/solana-txv1 终局确认（vs main）

纪律与审查内容与 `final_review_prompt.md` 完全相同（**只读**、离线、禁读目录、报告作为最终回复文本输出，首行 `# 收官 review r2: PASS / FAIL`），本轮补充两点：
1. **临时目录**：沙箱禁止在 `/private/tmp` 创建目录。跑 `test_sqd_gap_repair.py`、`test_batch8_repair_scale.py`、`test_batch7_validator_coverage_gaps.py` 时先 `mkdir -p .staging_b3/tmp`（该目录已被 gitignore）并设 `TMPDIR=$PWD/.staging_b3/tmp`；三项须真实跑到尾行。若仍被阻断，注明原因并以内存核验为准，不把环境阻断记为代码缺陷；结束时删除 `.staging_b3/tmp` 内容。
2. **上一轮 4 条 P2 的处置**：第一条（CHANGELOG 成本行）按 `CHANGELOG.md` 头部「每条迭代条目附成本指标+质量指标」规则**保留**；其余三条已按最小文本改动落地——请核对 `CHANGELOG.md` 9.1.0 段与 `references/scan-schemas.md` §14.8 的对应措辞现在是否与代码行为一致，且未引入新的不准确。

判定：仍存在 P0/P1 → FAIL；仅 P2 → PASS 并列出。
