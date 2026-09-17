# 施工 B 提示词：按 workorder_B.md 最新版施工（写模式）

## 纪律（首条最重要）
1. **禁读 `~/.codex/` 下任何文件**（插件启动搜索若已读 memories，如实披露一次，之后不再读）。禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md` 的内容（§1.1 统计字节时只计大小不读内容）。禁读 `/Users/uravvv/Desktop` 下任何文件。
2. 工单全文＝`maintenance/repair-20260917-p0-four/workorder_B.md`（以文件头版本号为准），逐字执行其 §0–§3。§0.1 的两条基线校验命令须实际运行并把输出贴进 `B_done.md`。
3. 只改工单 §0.3 白名单文件；只动工单指定的片段；锚不唯一或行号不符即停工汇报（不猜、不扩）。
4. 先红后绿：B3 用例先在改动前跑取 RED 证据写 `B_red_evidence.txt`，再改生产代码。
5. 不 commit、不 push、不部署 `~/.claude/commands/`、不改 `scripts/tests/contract_manifest.json`/`invariant_manifest.json`、不动其他测试文件。
6. 离线完成；只跑 §0.8 列的三个测试，不跑 `run_all.py`。
7. 完成后：把 §3 要求的完成报告写到 `maintenance/repair-20260917-p0-four/B_done.md`，并在 stdout 首行打印 `# 施工 B：完成` 或 `# 施工 B：停工`，随后打印 `git diff --stat` 与 §1.1 三个字节数。
