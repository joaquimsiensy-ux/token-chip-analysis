# 工单 F01 复核提示词（只读，r3）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260918d-p1-f01-f04/` 以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 工单F01复核：通过` 或 `# 工单F01复核：退回`。退回时逐条给出：编号（F01-R3-NN）、工单位置、事实、修订建议。通过时列出实际核过的项。
3. 这是修复计划复核（非攻击式验收）。

## 任务
复核 `maintenance/repair-20260918d-p1-f01-f04/workorder_F01_price_nonfinite.md`（**v3**）是否正确消化了 `review_F01_reply_r2.md` 的唯一一条意见 R2-01，且没有引入新问题。工作目录＝本仓库根。注意：**F04 段可能正在或已经施工**（`scripts/lib/camp_spec.py`、`scripts/tests/test_repair_batch_c.py` 可能已变，且未提交的施工中间态可能出现在工作树），与本工单无关、不予评价；本工单三个白名单文件仍与 868d3f61 逐字节相同，行号按 868d3f61 核。只核：
a) R2-01：§1.5 兼容前提是否已改为"主价格文件各点均为有限正数、第二源为 None 或有限数"，是否明确非正主价 fatal 1 为本轮预期变化，与 §1.7/§2.1/6b 是否自洽。
b) r2 已通过的项本轮无需重演，仅确认 v3 除导语 v3 变更段与 §1.5 外未改动其他段落。
