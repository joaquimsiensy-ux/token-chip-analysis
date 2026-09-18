# 工单 F05 复核提示词（只读，r3）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260918c-p1-f02-f04-f05/` 以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 工单F05复核：通过` 或 `# 工单F05复核：退回`。退回时逐条给出：编号（F05-R3-NN）、工单位置、事实、修订建议。通过时列出实际核过的项。
3. 这是修复计划复核（非攻击式验收）。

## 任务
复核 `maintenance/repair-20260918c-p1-f02-f04-f05/workorder_F05_price_receipt.md`（**v3**）与 `code_change_pending.md` Q14 是否正确消化了 `review_F05_reply_r2.md` 的三条意见，且没有引入新问题。工作目录＝本仓库根（`scripts/` 与 8b041842 逐字节相同；F04 尚未施工）。只核：
a) R2-01：§4/台账 Q14 的受影响范围表述是否与 `price_check.py:140`（单第二源不换源）、`:108-110`/`:117-122`（无数据 None）、`_get:87-100`（重试耗尽 None）、`:165-180`/`:193-194`（ALL_SKIP 退出 3）、`:143-145`（缺 symbol 退出 1）一致；是否已把 Robinhood 与本轮新增影响分开；是否未扩大为"任何 SKIP 即拒"。
b) R2-02：§2.5 RED 准备步骤是否明确"先完成 §2.3 全部测试侧变更（含 `:100` 三日夹具）、生产代码未改"，是否要求先确认生产者退出码（段 1 FAIL 2、段 3 WARN 0、段 6 ALL_SKIP 3、其余 0）再记消费端断言；这些退出码预期与 `price_check.py:165-194` 是否一致。
c) R2-03：§1.4 与 §2.2 说明②是否已把"双诊断可接受"限定为收据引用路径（`price_source_checks.path`/内联 `receipt.path`），并明确 `:522`/`:541-544` 主源路径负例仍 1 条路径诊断。
d) r2 已通过的项（修法、锚表 14 处、终点判据、迁移步骤）本轮无需重演，仅确认 v3 未改动这些段落的实质内容。
