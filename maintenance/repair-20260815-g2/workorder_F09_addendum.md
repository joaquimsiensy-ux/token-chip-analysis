# 工单 F-09 补充轮：调度方裁决——授权三个 fixture 补 warnings 字段

> 前置：workorder_F09.md 主体 STOPPED_AWAITING_SCOPE_DECISION（done 报告"名单外打红与请示"节）。

## 裁决

授权按你请示的最小方案执行：`test_sixlens_receipts.py`、`test_handoff_manifest.py`、`test_audit_release_gate.py` 三个文件，仅给其手造的零差异 `evm-reconciliation-receipt/v3` fixture 补 `warnings: []`。不放宽 consumer（你"缺字段视为空数组会让旧 v3 静默绕过新契约"的定性正确）。

## 收口目标

- 三个测试转绿；重跑 `test_gmgn_divergence_note.py`、`test_recon_deep_reverify.py` 不回归；
- 沙箱内 `run_all.py` 除两个 loopback EPERM 外全绿；
- `workorder_F09_done.md` 末尾追加"补充轮"一节：三处改动位置、最终测试输出。

## 硬约束（同主工单）

仅改上述三个测试文件的 fixture 字段；名单外再打红停下请示；禁止 git 操作。
