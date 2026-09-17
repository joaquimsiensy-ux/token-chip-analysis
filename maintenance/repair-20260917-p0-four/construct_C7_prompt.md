# 施工 C7 提示词：只施工 workorder_C.md 最新版（v5）的 **C7 段**（写模式）——开工 HEAD＝`__HEAD__`

## 纪律（首条最重要）
1. **禁读 `~/.codex/` 下任何文件**（插件启动搜索若已读 memories，如实披露一次，之后不再读）。禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md` 的内容。禁读 `/Users/uravvv/Desktop` 下任何文件。
2. 工单＝`maintenance/repair-20260917-p0-four/workorder_C.md`（v5）的 **C7 段**；C1–C6 已落地（1b317b3），**不得再动**。开工先跑 `git status --short`（须为空）与 `git rev-parse --short HEAD`（须等于本文件首行标注），贴进 `C7_done.md`。
3. 只改 `scripts/report/facts_gate.py`、`scripts/tests/test_report_facts.py`；只动 C7 指定片段；锚不唯一或行号不符即停工汇报。
4. 先红后绿：用例 15 六变体先在改动前跑取 RED 写 `C7_red_evidence.txt`（逐例独立，decimals "18" 变体基线即绿如实记录），再改生产代码。
5. 不 commit、不 push、不改其他文件；离线；只跑 C7 段列出的 6 项，不跑 run_all、不跑 reseal、不跑 docs_lint。
6. 完成后：完成报告写 `maintenance/repair-20260917-p0-four/C7_done.md`（含 0.1 输出、diff 原文、RED 摘要、6 项测试尾行、`git diff --stat`），stdout 首行 `# 施工 C7：完成` 或 `# 施工 C7：停工`。
