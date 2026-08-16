# 工单 F-10：Arbitrum 探索档 CLI 兑现 + 正式消费面双断言钉死

> 执行者：codex（纯施工，改文件+跑测试，**禁止任何 git 操作**）
> 工作目录：本 worktree 根（分支 repair-20260815-g2）
> 总计划：同目录 plan.md 第 2 刀节

## 背景

外部审查 F-10（P2）：SKILL/chain_registry 承诺 Arbitrum 保留探索采集与对账（registry 里 arbitrum `release_tier="exploration"` 且 balance/supply/time/accounting 能力全 True），但四个对账 CLI 的 `--chain` choices 全部由 formal-only helper 构造（`accounting_gate.py:392`、`verify_recon.py:45`、`time_spotcheck.py:221` 用 `formal_evm_chains(cap)`；`supply_truth_gate.py:526-528` 用 `formal_reconciliation_chains("supply")`），`--chain arbitrum` 在 argparse 层 exit 2，承诺不可执行。

**施工总原则（顺序强制）：先钉死正式消费面（第 A 部分），确认负向测试到位后，再放宽 CLI（第 B 部分）**——放开执行集绝不能给正式发布面新开旁路。

## A. 正式消费面等深钉死（先做）

改 `scripts/report/shared_release_receipt.py` 的 `validate_reconciliation_check`（:471-662）与 `validate_reconciliation_report`（:665-）：

1. EVM balance/supply 分支（:497-509）、Solana anchor 分支（:510-518）、EVM time 分支（:653-659）各补**双断言**：`receipt.get("mode") == "formal"` **且** `formal_ready(target["chain"])`（`formal_ready` 从 `chain_registry` import，同文件已有 import 面可扩展）。supply_truth 分支 :586 已有 mode 断言，给它补上 formal_ready 半边，四分支等深。
2. `validate_reconciliation_report` 的 target 层（:665-679 区域）补一条 target 级正式链档位断言：wrapper 的 `target["chain"]` 必须 `formal_ready`。错误文案含"正式对账消费面只接受 formal-ready 链"与迁移指引。
3. ⚠️ 只动上述断言点，**不改动这些分支的其他观测语义**（后续刀会深化，本刀保持最小）。**绝对不碰**本文件的 A4/adversarial 相关函数区（`validate_adversarial_review` 等）。

## B. CLI 执行集放宽（A 部分负测就位后再做）

1. `scripts/lib/chain_registry.py` 新增三个 helper（复用既有 `capability_chains(name, release_tiers=)`）：
   - `executable_evm_chains(capability)`：tiers={formal, exploration} ∩ `capture_evm_family` ∩ `evm_chain_id` 非空（即 `formal_evm_chains` 的放宽版）；
   - `executable_reconciliation_chains(kind)`：同 `formal_reconciliation_chains` 的放宽版；
   - `resolve_execution_mode(chain, exploration, capability_kind)` 统一策略函数，行为契约：
     * chain 在该能力 formal 集、exploration=False → 返回 `"formal"`；
     * chain 在 formal 集、exploration=True → 返回 `"exploration"`（正式链也允许探索跑）；
     * chain 不在 formal 集但在 executable 集、exploration=True → 返回 `"exploration"`；
     * chain 不在 formal 集、exploration=False → raise ValueError（文案含"探索档链必须显式 --exploration"）。
   四个 CLI 全部经此函数裁决，禁止各自写 if/else（防四处漂移）。
2. 四 CLI 修改：
   - `scripts/evm/accounting_gate.py`：choices 换 executable 集；经策略函数裁决——效果上 arbitrum+`--bundle`（即无 exploration）直接拒；既有 `--bundle`/`--exploration` 互斥保留。
   - `scripts/evm/verify_recon.py`：choices 换 executable 集；**新增 `--exploration` 布尔 flag**；envelope 的 mode 参数（:59、:67 两处 `build_envelope(..., "formal")`）改为策略函数返回值。
   - `scripts/lib/time_spotcheck.py`：同 verify_recon（choices :221、新增 flag、envelope mode :290）。
   - `scripts/lib/supply_truth_gate.py`：choices 换 executable 版（**保留现有 sol→solana 显示映射逻辑**）；已有 `--exploration`，接入策略函数补"非 formal 链强制 flag"。

## 存量测试适配（授权范围）

- `scripts/tests/test_batch2_capability_matrix.py`（约 :53 起）硬断言四 CLI 使用 formal-only helper——因本刀语义变更必红，改为断言新策略（choices=executable 集、mode 经 `resolve_execution_mode`）。
- 其他测试若打红：停下，红名单写进 done 报告，不扩大修改。

## 新测试文件 `scripts/tests/test_arbitrum_exploration_cli.py`

自建 `main()` runner 风格。零网络（argparse 层为主；time 可用 `--dry-run` 离线模板，参考 `test_time_spotcheck.py`）：

- 正向：四入口 `--chain arbitrum --exploration` 通过 argparse 进入执行路径（可在到达网络调用前用无效输入让其失败，只断言"不再在 choices 层 exit 2"且失败原因不是链拒绝）；
- 负向：四入口 `--chain arbitrum` 缺 flag → 拒，文案含探索档提示；
- 负向（消费面，A 部分的验证）：构造 mode="exploration" 的对账收据 → `validate_reconciliation_check` 拒；构造 target.chain=arbitrum 且 mode 字段写成 "formal" 的收据 → 仍被 `formal_ready` 断言拒；
- 绿例回归：formal 四链（eth/bsc/base/solana 相应入口）无 flag 行为与基线完全一致；既有正式收据夹具过消费面不受影响。

## 先红后绿纪律

1. 先写新测试对基线跑：消费面负向用例应体现"基线不拒 exploration/arbitrum 收据"（红），落 `maintenance/repair-20260815-g2/f10_red.log`；
2. A 部分施工 → 消费面负测转绿；
3. B 部分施工 → CLI 正向测试转绿；全量证据落 `f10_green.log`。

## 验收标准

- 新测试绿；`test_batch2_capability_matrix.py` 改后绿；`test_sixlens_receipts.py`、`test_handoff_manifest.py`、`test_audit_release_gate.py`、`test_reconciliation_runner.py` 绿（正式面不受影响的回归证明）；
- done 报告 `workorder_F10_done.md`：改动清单、红绿证据指引、存量适配理由、四 CLI 策略统一性自查。

## 硬约束

- 只改：`scripts/report/shared_release_receipt.py`（限 validate_reconciliation_check/validate_reconciliation_report 及必要 import）、`scripts/lib/chain_registry.py`、四个 CLI 文件、新测试文件、`test_batch2_capability_matrix.py`。
- 禁碰：VERSION、CHANGELOG、SKILL.md、r10_ledger.md、pyproject、run_all.py、invariant/contract manifest、`audit_release_gate.py`、`handoff_manifest.py`、shared 内 A4/adversarial 函数区。
- 禁止一切 git 写操作。
