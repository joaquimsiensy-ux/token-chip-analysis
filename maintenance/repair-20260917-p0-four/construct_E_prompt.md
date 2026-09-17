# 施工 E 提示词：按 workorder_E_version.md 最新版施工（写模式，纯文档/元数据）——开工 HEAD＝`__HEAD__`

## 纪律
1. **禁读 `~/.codex/` 下任何文件**（插件启动搜索若已读 memories，如实披露一次，之后不再读）。禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md` 的内容。禁读 `/Users/uravvv/Desktop` 下任何文件。
2. 工单全文＝`maintenance/repair-20260917-p0-four/workorder_E_version.md`（以文件头版本号为准），逐字执行 §0–§4。开工先跑 `git status --short`（须为空）与 `git rev-parse --short HEAD`（须等于本文件首行标注），贴进 `E_done.md`。
3. 只改工单 §0 四个文件；CHANGELOG 两处插入逐字照工单；`references/`、`scripts/` 一字不动；锚不唯一或行号不符、或 §2 文案与仓库事实不符即停工汇报（退回本单而非自行改写事实）。
4. 不 commit、不 push；离线；只跑 §3 的 `test_version_consistency` 与 `wc -c SKILL.md`；**不跑** `changelog_lint`、`docs_lint --all`（读 archive/，调度方本机跑）、不跑 run_all。
5. 完成后：报告写 `maintenance/repair-20260917-p0-four/E_done.md`，stdout 首行 `# 施工 E：完成` 或 `# 施工 E：停工`，随后打印 `git diff --stat`。
