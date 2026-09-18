# 工单 F04 复核提示词（只读，r2）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260918c-p1-f02-f04-f05/` 以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 工单F04复核：通过` 或 `# 工单F04复核：退回`。退回时逐条给出：编号（F04-R2-NN）、工单位置、事实、修订建议。通过时列出实际核过的项。
3. 这是修复计划复核（非攻击式验收）。

## 任务
复核 `maintenance/repair-20260918c-p1-f02-f04-f05/workorder_F04_rpc_envelope.md`（**v2**）是否正确消化了 `review_F04_reply_r1.md` 的三条意见，且没有引入新问题。工作目录＝本仓库根（`scripts/` 与 8b041842 逐字节相同）。逐项核：
a) R1-01：§2.2 `re.fullmatch(r"0x(?:[0-9a-fA-F]{2})*", code)` 是否恰好接受 `"0x"` 与偶数长度十六进制串、拒绝 `"0x0"`/`"0xgg"`/非字符串；`re` 是否已在 `rpc_batch.py:26` 导入；`badhex` 场景是否已进 §2.3。
b) R1-02：§2.3 的 `_getcode_scenario` helper 与逐场景循环是否能独立取得七场景各自的 rc/结果/stdout；`contextlib.redirect_stdout` 是否能捕获 `rpc_batch.main()` 的 `[SUMMARY]` 行（`:90` 为 `print`，无 `file=sys.stderr`？请核）；RED 段对 `int` 场景的基线预期（TypeError）与 `badhex` 场景（基线 `is_contract` True）是否写对；新增 `import contextlib`/`import io` 的插入锚 `:5 import asyncio` 是否唯一、字母序位置是否正确。
c) R1-03：台账 Q13 与 §0.4/§4 的表述是否准确反映 `_run:354-372` 的三端点轮转行为；工单是否明确"本段不改 `_run`"。
d) 重核 §2 全部锚文本命中数与行号（含 v2 新增的 `:5`、`:26`）；§0.8 新增的 `test_evm_observation_nonempty_code.py`、`test_g3_alt_collectors.py` 是否存在且与本段相关。
e) 终点判据（`ruling_20260918.md` `rpc_missing_result`）在 v2 修法下是否仍必然成立。
