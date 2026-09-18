# 工单 F05 复核提示词（只读，r2）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260918c-p1-f02-f04-f05/` 以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 工单F05复核：通过` 或 `# 工单F05复核：退回`。退回时逐条给出：编号（F05-R2-NN）、工单位置、事实、修订建议。通过时列出实际核过的项。
3. 这是修复计划复核（非攻击式验收）。

## 任务
复核 `maintenance/repair-20260918c-p1-f02-f04-f05/workorder_F05_price_receipt.md`（**v2**）与 `code_change_pending.md`（Q8/Q9 已订正，新增 Q13/Q14）是否正确消化了 `review_F05_reply_r1.md` 的五条意见，且没有引入新问题。工作目录＝本仓库根（`scripts/` 与 8b041842 逐字节相同；F04 尚未施工）。逐项核：
a) R1-01：导语迁移步骤是否已改为"重跑 price_check → 直接改工单引用 → 完整 check → --receipt-only"、明确禁用 amend；台账 Q8 同步。
b) R1-02：Q8 是否已写明四类新增拒收面、ARC 内联引用"结构可保留但旧收据须迁移"；Q9 是否加了分支条件；Q14 对 `report-template.md:278` 人工回退路径的登记是否准确（受影响范围表述是否过窄或过宽——请核正式候选链 ETH/BSC/Base/Solana 在 `price_check.py` 第二源（DefiLlama/币安）下 ALL_SKIP 的现实可能性）。
c) R1-03：§0.8 是否已明确施工方不跑 `test_stage2_reseal.py`、§0.4 是否把该测试列入不改；§4 是否写明调度方 commit 后本机补验。
d) R1-04：§2.5 RED 段是否已把段 3 改为 RED、并要求逐段独立取证。
e) R1-05：§2.2 行号（`:235` 返回、`:236-237` 空行、`:238` 锚；`:361-366`/`:368-381` 两段通用遍历；`:270`/`:299` 作用域）与"双诊断可接受"表述是否准确；导语对 `price_check.py:181-185` 构造处与 `:187-188` 落盘点的区分是否准确。
f) 重核 §2 全部锚文本命中数与行号（v2 把 `_sha256_file` 插入锚改为 `:46 def _load_series(path):`）。
g) 终点判据（`ruling_20260918.md` `price_gate_content`）在 v2 修法下是否仍必然成立，拒在哪一行、哪句文案。
