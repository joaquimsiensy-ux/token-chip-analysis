# 施工 R4 提示词：按 workorder_r4.md v1 施工（写模式）

## 纪律（首条最重要）
1. **禁读 `~/.codex/` 下任何文件**（插件启动搜索若已读 memories，如实披露一次，之后不再读）。禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md` 的内容（§1.1 统计字节时 attic.md 只计大小不读内容）。
2. 工单全文＝`maintenance/repair-20260916-drift-audit/workorder_r4.md`（v1），逐字执行其 §0–§3。§0.1 的内容基线校验命令须实际运行并把输出贴进 r4_done.md。
3. 只改工单 §0.3 白名单文件；只动工单指定的片段；锚不唯一或行号不符即停工汇报（不猜、不扩）。
4. 不 commit、不 push、不部署 `~/.claude/commands/`、不改 `scripts/`、不改 `scripts/tests/contract_manifest.json`。
5. 离线完成；`docs_lint.py` 等守卫脚本自身会遍历文档，允许运行（那是被测代码的既有行为，不算你读禁读文件）。
6. 完成后：把 §3 要求的完成报告写到 `maintenance/repair-20260916-drift-audit/r4_done.md`，并在 stdout 首行打印 `# 施工 R4：完成` 或 `# 施工 R4：停工`，随后打印 `git diff --stat` 与 §1.1 三个字节数。
