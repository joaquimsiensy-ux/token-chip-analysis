# 施工 C 提示词：按 workorder_C.md 最新版施工（写模式）——开工 HEAD＝`__HEAD__`

## 纪律（首条最重要）
1. **禁读 `~/.codex/` 下任何文件**（插件启动搜索若已读 memories，如实披露一次，之后不再读）。禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md` 的内容（§1.1 统计字节时只计大小不读内容）。禁读 `/Users/uravvv/Desktop` 下任何文件。
2. 工单全文＝`maintenance/repair-20260917-p0-four/workorder_C.md`（以文件头版本号 v3 为准；复核记录 `review_C_reply_r1..r3.md` 只作背景），逐字执行其 §0–§3。§0.1 的两条基线校验命令须实际运行并把输出贴进 `C_done.md`；HEAD 须等于本文件首行标注。
3. 只改工单 §0.3 白名单文件；只动工单指定的片段；锚不唯一或行号不符即停工汇报（不猜、不扩）。C2 中 `check_facts_vs_ledgers` 开头的 `regular_case_path` 检查**必须实施**（工单 :335 段已实证 `load_json` 跟随符号链接）。
4. 先红后绿：C4 各用例先在改动前跑取 RED 证据写 `C_red_evidence.txt`（逐例独立、逐例捕获 AssertionError/ImportError/AttributeError 原文），再改生产代码。
5. 不 commit、不 push、不部署 `~/.claude/commands/`、不改 `scripts/tests/contract_manifest.json`；`invariant_manifest.json` 只按 C5 逐条增补；不动其他测试文件；`test_stage2_reseal.py` 只改 C4-a′ 指定函数体，**不跑**它（原因见工单 §0.8）。
6. 离线完成；只跑 §0.8 列的测试与 `invariant_scan.py`，不跑 `run_all.py`、不跑 docs_lint。
7. 完成后：把 §3 要求的完成报告写到 `maintenance/repair-20260917-p0-four/C_done.md`，并在 stdout 首行打印 `# 施工 C：完成` 或 `# 施工 C：停工`，随后打印 `git diff --stat` 与 §1.1 三个字节数。
