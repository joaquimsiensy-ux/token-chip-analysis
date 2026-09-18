# 施工 G1 提示词：按 workorder_G1_fig2.md 最新版施工（写模式）
# 派工基线 HEAD＝__HEAD__（本提示词自身的 commit 会使实际开工 HEAD 比此多恰一个提交，属预期；§0.1 的"须为空"指工作树与 HEAD 无差异）

## 纪律（首条最重要）
1. **禁读 `~/.codex/` 下任何文件**（插件启动搜索若已读 memories，如实披露一次，之后不再读）。禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260918-p0-f04-f07/` 与 `maintenance/repair-20260918b-p0-fig2-decimals/` 以外的历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`（§1.1 统计字节只计大小不读内容）。
2. 工单全文＝`maintenance/repair-20260918b-p0-fig2-decimals/workorder_G1_fig2.md`（以文件头版本号为准），逐字执行其 §0–§3。§0.1 的基线校验命令须实际运行并把输出贴进 `G1_done.md`。
3. 只改工单 §0.3 白名单文件；只动工单指定的片段；锚不唯一或行号不符即停工汇报（不猜、不扩）。工单里标注"开工核实"的项先核实并把结果写进 done。
4. 先红后绿：新用例先在改动前跑取 RED 证据写 `G1_red_evidence.txt`，再改生产代码。
5. 不 commit、不 push、不部署 `~/.claude/commands/`；`contract_manifest.json`/`invariant_manifest.json` 只在工单白名单明示的字符替换范围内改。
6. 离线完成；不跑 `run_all.py`；守卫/测试脚本自身会遍历文档，允许运行。
7. 中途遇到工单与代码事实冲突、或需要动白名单外文件：停工写 `G1_done_attemptN_stopped.md` 并在 stdout 说明，不自行扩权。
8. 完成后：把 §3 要求的完成报告写到 `maintenance/repair-20260918b-p0-fig2-decimals/G1_done.md`，并在 stdout 首行打印 `# 施工 G1：完成` 或 `# 施工 G1：停工`，随后打印 `git diff --stat` 与 §1.1 三个字节数。
