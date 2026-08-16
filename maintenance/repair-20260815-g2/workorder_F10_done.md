# 工单 F-10 完工报告

## 结论

F-10 已按强制顺序完成：先建立正式消费面负向测试并取得基线红证据，再实施 A 部分双断言；确认消费面转绿后，才实施 B 部分 CLI 执行集放宽。工单列出的验收测试全部通过。

施工期间未运行任何 git 命令，未修改 VERSION、CHANGELOG、SKILL.md、r10_ledger.md、pyproject、run_all.py、manifest、audit_release_gate.py、handoff_manifest.py，也未触碰 `shared_release_receipt.py` 的 A4/adversarial 函数区。

## A. 正式消费面双断言

- `scripts/report/shared_release_receipt.py`
  - 扩展既有 `chain_registry` import，引入 `formal_ready`。
  - EVM balance/supply、Solana anchor balance/time、supply_truth、EVM time 四个分支均同时要求：
    - receipt `mode == "formal"`；
    - wrapper target 的 chain 满足 `formal_ready(...)`。
  - `validate_reconciliation_report` 在 target 层新增 formal-ready 断言；错误文案包含“正式对账消费面只接受 formal-ready 链”及重跑、重建 wrapper 的迁移指引。
  - 未改各分支的其他观测语义。

## B. CLI 执行集放宽

- `scripts/lib/chain_registry.py`
  - 新增 `executable_evm_chains(capability)`：只取 formal/exploration 两档，并要求 EVM capture family 与非空 chain id。
  - 新增 `executable_reconciliation_chains(kind)`：复用 reconciliation capability 映射，放宽至 formal/exploration 两档。
  - 新增唯一策略函数 `resolve_execution_mode(chain, exploration, capability_kind)`，覆盖四态：正式链默认 formal、正式链显式探索、探索档链显式探索、探索档链缺 flag 硬拒。

四 CLI 统一性自查：

| CLI | choices 来源 | 策略参数 | mode 落点/拒绝点 |
|---|---|---|---|
| `scripts/evm/accounting_gate.py` | `executable_evm_chains("accounting_adapter")` | `resolve_execution_mode(..., "accounting_adapter")` | receipt schema/execution_mode；既有 bundle/exploration 互斥保留 |
| `scripts/evm/verify_recon.py` | `executable_evm_chains("balance_producer")` | `resolve_execution_mode(..., "balance")` | 两处 `build_envelope` 均使用策略返回值 |
| `scripts/lib/time_spotcheck.py` | `executable_evm_chains("time_producer")` | `resolve_execution_mode(..., "time")` | 正式/探索 envelope mode；dry-run 仍保持离线 |
| `scripts/lib/supply_truth_gate.py` | `executable_reconciliation_chains("supply")` | `resolve_execution_mode(..., "supply")` | 既有 mode 语义统一由策略返回；sol→solana choices 显示映射保留 |

四个 CLI 均无本地复制的 formal/exploration 档位 if/else。Arbitrum 缺 `--exploration` 时统一报“探索档链必须显式 --exploration”。

## 测试与存量适配

- 新增 `scripts/tests/test_arbitrum_exploration_cli.py`：
  - 消费面拒绝 exploration mode；
  - 消费面拒绝把 Arbitrum 收据整体改标为 formal；
  - wrapper target 层拒绝 Arbitrum，并检查迁移指引；
  - 四 CLI 接受 `arbitrum --exploration` 进入执行路径、缺 flag 拒绝；
  - 全程零网络：accounting 用执行边界 mock，verify 只走 parser，time/supply 用缺失离线输入在网络前退出；
  - eth/bsc/base/solana 四个正式链对应入口无 flag 行为回归；正式 BSC 收据继续通过消费面。
- 更新 `scripts/tests/test_batch2_capability_matrix.py`：原测试硬断言四 CLI 必须使用 formal-only helper，与本工单明确的新语义冲突；现改为断言 executable choices、Arbitrum 集合成员、四态 mode 策略和四 CLI 必经统一策略函数。除此之外未改任何存量测试。

## 红绿证据

红证据：`maintenance/repair-20260815-g2/f10_red.log`

- 在生产代码未修时运行：
  - `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_arbitrum_exploration_cli.py --consumer-only`
- exit 1；两个负例均显示“formal reconciliation consumer accepted forbidden receipt”；正式 BSC 收据绿例通过。

绿证据：`maintenance/repair-20260815-g2/f10_green.log`

- 同一批次顺序运行并整体 exit 0：
  - `test_arbitrum_exploration_cli.py`
  - `test_batch2_capability_matrix.py`
  - `test_sixlens_receipts.py`
  - `test_handoff_manifest.py`（68 项）
  - `test_audit_release_gate.py`
  - `test_reconciliation_runner.py`（7 个反例）
- 日志内的 `disk full`、FAIL/ERROR/BLOCK 文本来自既有 fail-closed 负向场景；各所属测试的最终状态均为 PASS，批次退出码为 0。

## 实际改动文件

生产/测试授权面：

- `scripts/report/shared_release_receipt.py`
- `scripts/lib/chain_registry.py`
- `scripts/evm/accounting_gate.py`
- `scripts/evm/verify_recon.py`
- `scripts/lib/time_spotcheck.py`
- `scripts/lib/supply_truth_gate.py`
- `scripts/tests/test_batch2_capability_matrix.py`
- `scripts/tests/test_arbitrum_exploration_cli.py`

工单证据与交付件：

- `maintenance/repair-20260815-g2/f10_red.log`
- `maintenance/repair-20260815-g2/f10_green.log`
- `maintenance/repair-20260815-g2/workorder_F10_done.md`

未发现需要列入红名单的授权外测试失败。
