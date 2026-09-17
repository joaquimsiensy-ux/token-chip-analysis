# 施工 A 提示词：按 workorder_A.md 最新版施工（写模式）

## 纪律（首条最重要）
1. **禁读 `~/.codex/` 下任何文件**（插件启动搜索若已读 memories，如实披露一次，之后不再读）。禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md` 的内容（§1.1 统计字节时只计大小不读内容）。
2. 工单全文＝`maintenance/repair-20260917-p0-four/workorder_A.md`（以文件头版本号为准），逐字执行其 §0–§3。§0.1 的两条基线校验命令须实际运行并把输出贴进 `A_done.md`。
3. 只改工单 §0.3 白名单文件；只动工单指定的片段；锚不唯一或行号不符即停工汇报（不猜、不扩）。
4. 先红后绿：A5 用例先在改动前跑取 RED 证据写 `A_red_evidence.txt`，再改生产代码。
5. 不 commit、不 push、不部署 `~/.claude/commands/`、不改 `scripts/tests/contract_manifest.json`/`invariant_manifest.json`。
6. 离线完成；不跑 `run_all.py`；守卫/测试脚本自身会遍历文档，允许运行。
7. 完成后：把 §3 要求的完成报告写到 `maintenance/repair-20260917-p0-four/A_done.md`，并在 stdout 首行打印 `# 施工 A：完成` 或 `# 施工 A：停工`，随后打印 `git diff --stat` 与 §1.1 三个字节数。
