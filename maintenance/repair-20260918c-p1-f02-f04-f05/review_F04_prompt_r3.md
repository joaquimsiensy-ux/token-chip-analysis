# 工单 F04 复核提示词（只读，r3）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260918c-p1-f02-f04-f05/` 以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 工单F04复核：通过` 或 `# 工单F04复核：退回`。退回时逐条给出：编号（F04-R3-NN）、工单位置、事实、修订建议。通过时列出实际核过的项。
3. 这是修复计划复核（非攻击式验收）。

## 任务
复核 `maintenance/repair-20260918c-p1-f02-f04-f05/workorder_F04_rpc_envelope.md`（**v3**）与 `code_change_pending.md` Q13 是否正确消化了 `review_F04_reply_r2.md` 的两条意见（F04-R2-01 import 插入锚拆开为 `:5`/`:7`；F04-R2-02 Q13 三端点反例不泛化），且没有引入新问题。工作目录＝本仓库根（`scripts/` 与 8b041842 逐字节相同）。只核：
a) §2.3 import 插入说明：`:7 import importlib.util` 锚是否唯一；落地后 `:5-10` 顺序是否与工单所述一致（asyncio/contextlib/csv/importlib.util/io/json）；§2.3 后续行号引用（`:326`/`:327`/`:334`）是否已说明按插入后偏移或仍按基线（若工单未说明偏移，指出即可，不算退回条件，除非会导致锚不唯一）。
b) §4 与台账 Q13 的多端点表述是否与 `_run:355`/`:372` 实际行为一致（三端点 A→B→A、四端点 A→B→D、八端点 A→B→D→G→C），是否仍明确"本段不改 `_run`"。
c) r2 已通过的项（修法、七场景 RED 预期、锚表、终点判据）本轮无需重演，仅确认 v3 未改动这些段落的实质内容。
