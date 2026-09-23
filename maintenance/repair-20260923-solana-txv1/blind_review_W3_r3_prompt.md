# 盲审任务 r3：W3 增量（分支 fix/solana-txv1，只审最近一次测试改动）

纪律：**只读**，不改文件、不 commit；禁读 `~/.codex`（启动自动披露除外）、`~/Documents`、`~/Desktop`；离线。报告**作为最终回复文本直接输出**，首行 `# 盲审 W3 r3: PASS / FAIL`。不读 `maintenance/` 目录下任何文件。

背景：上一轮独立审查指出 `scripts/tests/test_sqd_gap_repair.py` E27(d) 深验篡改循环中"改 `predecessor_plan_digest`"的向量因保留原 `source` 而先被目录名绑定拒绝，从未走到 `_plan_digest_from_generation` 重算。本轮改动应只有该向量一处（`git log -1 --stat` 与 `git diff HEAD~1 -- scripts/tests/test_sqd_gap_repair.py`）。

审查：①改动是否仅此一处、生产代码零改动；②用 `unittest.mock.patch(..., wraps=...)` 自己在内存里核验：新向量下 `validate_repair_bundle_deep` 对 `_plan_digest_from_generation` 的调用次数与参数（应为 2 次：当前代 sha、前代 sha），reasons 含 `adopted record invalid`；未篡改 gen 仍 PASS；③`MPLCONFIGDIR=$HOME/.matplotlib python3 -B scripts/tests/test_sqd_gap_repair.py` 尾行（若沙箱禁写临时目录，注明并以内存核验为准）。FAIL 条件＝存在 P0/P1。
