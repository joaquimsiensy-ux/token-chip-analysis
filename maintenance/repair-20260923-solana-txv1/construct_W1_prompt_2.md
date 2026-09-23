# 施工任务（第 2 段）：勘误 A1 ＋ 工单 W1 v5 §2、§4（分支 fix/solana-txv1）

纪律（优先级高于工单正文）：
1. **禁读 `~/.codex`**（启动自动披露除外）；禁读 `~/Documents`、`~/Desktop`。
2. **本仓库 `.git` 对你只读，git add/commit 一律由调度方代做**——不要再尝试 git add/commit，也不要因此停工。开工时工作树**应当**含第 1 段施工留下的未提交改动（清单见 `maintenance/repair-20260923-solana-txv1/W1_done.md`「已做改动」；`git diff --stat` 应为 16 个文件），这不是外来脏文件；除此之外不应有其他改动。
3. 先读 `maintenance/repair-20260923-solana-txv1/workorder_W1_amendment_A1.md`，**按勘误 A1 修正第 1 段的常量落点**（撤销 session 的改动、常量移到 endpoint_identity、全部导入改指向它），跑 `invariant_scan.py` 与 `test_batch4_invariant_guards.py` 确认绿。
4. 再按 `workorder_W1_v5.md` 的 **§2（认领机制）与 §4（测试）** 施工；§0 纪律全部适用（白名单 0.3、不改 0.4、行号不符停工 0.5、离线、`MPLCONFIGDIR`）。§3 登记与 §5 版本/文档**本段不做**（登记需要代码 commit 哈希，由调度方 commit 后另派）。`test_producer_registry_current.py` 在本段预期 FAIL（新 sha 未登记），记录即可。
5. 定向测试按 v5 §0.7 清单（除 registry）全部跑并贴尾行；`test_sqd_gap_repair.py` 与 `test_batch8_repair_scale.py` 必须绿。
6. 每完成一节（A1、§2、§4）就把该节记录追加进 `W1_done.md`（改动清单文件:行、与工单差异、测试尾行），以便中断后调度方接手；完成 §4 后**停下**，末尾写「待调度方 commit」。
7. 工单里任何行号/断言与实况不符：停工，把不符点写进 `W1_done.md`「停工原因」。
