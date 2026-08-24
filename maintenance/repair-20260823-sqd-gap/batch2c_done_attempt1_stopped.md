# 批 2c 停工报告

## 状态

`STOPPED_WORKORDER_ANCHOR_MISMATCH`

基线核对通过：分支为 `fix/sqd-gap-v6520`，HEAD 为
`b005a468b919fd8c39108f513db862a2edb84555`。

## 实况差异

工单白名单第 1 项要求 main 的三处 `_scan_ranges(...)` 调用（“全扫/已知地图缺口/其他 mode”）逐处传入 `checkpoint` 与 `checkpoint_every`。

当前 HEAD 中，`scripts/solana/sqd_coverage_probe.py` 的 main 路径只有一处 `_scan_ranges(...)` 调用：

- `scripts/solana/sqd_coverage_probe.py:829`：对 `_missing_ranges(counts, args.from_slot)` 的统一缺口结果调用 `_scan_ranges(..., mode="full")`。

仓库内其余 `_scan_ranges(...)` 调用均位于 `scripts/tests/test_sqd_coverage_probe.py`（当前为 4 处），不存在工单所述的另外两处 main 调用。因此无法在不猜测设计意图的前提下满足“三处调用逐处接入”的施工指令。

## 本次未执行

- 未新增第 11 组测试，未形成 RED/GREEN 对照。
- 未修改 `scripts/solana/sqd_coverage_probe.py` 或 `scripts/tests/test_sqd_coverage_probe.py`。
- 未创建或修改 `batch2c_green_evidence.txt`。
- 未运行 `python3 scripts/tests/test_sqd_coverage_probe.py` 或 `python3 scripts/tests/run_all.py`。
- 未 commit、未切分支、未联网、未进入批 3。

## 需要澄清

请由工单方明确以下二者之一后重新派工：

1. 认可当前单一 main 调用为三种入口汇合后的唯一接入点，并把工单改为“按所有实际 main 调用接入”；或
2. 指明预期存在的另外两处调用及其准确锚文本/控制流位置。
