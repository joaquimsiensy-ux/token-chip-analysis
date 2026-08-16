# 工单 F-07 补充轮：调度方裁决——扩展存量适配名单，收全量绿

> 前置：workorder_F07.md 主体 BLOCKED 于名单外测试（done 报告"全量验收阻断"节）。
> 调度方裁决如下，按此收口。

## 裁决

1. **授权适配**（同族旧夹具规则，只改测试夹具形态、不改生产语义）：
   - `scripts/tests/test_review_20260804_p105.py`（`bind_balance_receipt_to_snapshot` 换绑 helper 所在）：helper 换绑余额实物后须同步收据自报的 supply_closure 相关标量（balance_sum_raw 等），使反例继续抵达其原本要测的断言层而不是提前死于深重验；
   - `scripts/tests/test_repair_batch_b.py`（触发方）：随 helper 修复联动，必要处最小适配；
   - `scripts/tests/test_repair_batch_a.py`：**先只读单跑定位那 1/45 的具体 case 与红因**，写进 done 报告；若红因是同族旧浅夹具 → 最小适配；若红因指向生产语义问题 → 停下，只报告不改。
2. **调用链白名单追加**：上述测试若复用其他旧浅夹具，允许沿调用链追加必要的测试文件适配，每个追加文件在 done 报告单独列明"文件+红因+最小改动"。
3. `references/analyze-workflow.md` 的 v3 串级联越界披露：调度方复核为最小机械级联，**保留**，无需回退。
4. 纵切片 EPERM 属沙箱环境限制，你不用处理，调度方本机复跑。

## 收口目标

- `python3 scripts/tests/run_all.py` 在你的沙箱内除两个 loopback EPERM 纵切片外全部通过；
- 重跑 `test_recon_deep_reverify.py`、`test_audit_release_gate.py`、`test_sixlens_receipts.py` 确认不回归；
- 在 `workorder_F07_done.md` 末尾追加"补充轮"一节：batch_a 1/45 的定位结论、各文件适配理由、最终测试输出。

## 硬约束（同主工单）

仅改本补充轮授权的测试文件；禁碰一切生产文件；名单外再打红仍旧停下请示；禁止 git 操作。
