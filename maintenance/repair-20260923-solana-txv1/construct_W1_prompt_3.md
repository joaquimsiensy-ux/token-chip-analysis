# 施工任务（第 3 段）：勘误 A2 ＋ 工单 W1 v5 §3（登记）、§5（文档/版本）（分支 fix/solana-txv1）

纪律（优先级高于工单正文）：
1. **禁读 `~/.codex`**（启动自动披露除外）；禁读 `~/Documents`、`~/Desktop`。
2. **`.git` 对你只读，git add/commit 由调度方代做**——不要尝试 git 写操作，也不以此停工。开工时 `git status --short` 应为空（第 1、2 段改动已由调度方 commit）。
3. 先读 `maintenance/repair-20260923-solana-txv1/workorder_W1_amendment_A2.md`，按它①登记 manifest 条目并确认 `invariant_scan.py` exit 0；②按 `workorder_W1_v5.md` §3 登记 producer_history（commit 哈希与 sha 以 A2 第 3 条为准，先复核）；③按 v5 §5 改文档与版本（措辞按 A1 第 4 条、A2 第 4 条；§2.1 的「来源可信是输入前提」措辞与 §2.3 第 8 步硬链接边界照写）。§0 纪律全部适用（白名单、不改项除 A2 放开的一条、行号不符停工、离线、`MPLCONFIGDIR`）。
4. 定向测试：`invariant_scan.py`、`test_producer_registry_current.py`、`test_version_consistency.py`、`changelog_lint.py`、`docs_lint.py --all`、`test_sqd_gap_repair.py`、`test_batch8_repair_scale.py`、`test_batch4_invariant_guards.py`、`test_r7_findings.py`、`test_sixlens_docs.py` 全部 PASS 并贴尾行。
5. 完成后把本段记录追加进 `W1_done.md`（改动清单文件:行、与工单差异、测试尾行、自报禁读路径），末尾写「待调度方 commit」。工单里任何行号/断言与实况不符：停工写明。
