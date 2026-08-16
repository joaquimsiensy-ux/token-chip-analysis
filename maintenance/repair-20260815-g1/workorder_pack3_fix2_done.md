# 包 3 fix 第二轮施工报告（F-03 / F-14）

日期：2026-08-15
状态：**BLOCKED，生产缺陷已修，但冻结 fixture / manifest 仍与新 target 等式冲突**
结论：`canonical_target()` 与 Solana reconciliation producer 链已改为按链族处理 token；EVM 继续小写归一，Solana base58 从 observation、四查、window 到 shared 全程保留原串。`test_a4_gate.py` 的三项旧正例已转绿，包 3 两项测试已登记 `run_all.py`。但 `test_batch3_solana_vertical_slice.py` 自身仍把 adversarial target 写成 `MINT.lower()`，另有三组未获解冻的存量 fixture / manifest 回归继续失败；因此不得声称全绿或 fix complete。全程未执行任何 git 命令。

## 1. 本轮改动文件与边界

生产代码：

1. `scripts/report/shared_release_receipt.py`
2. `scripts/lib/solana_observation.py`
3. `scripts/lib/supply_truth_gate.py`
4. `scripts/solana/scan_token_accounts.py`
5. `scripts/solana/anchor_sampler.py`
6. `scripts/solana/window_fetch.py`

获批 fixture / suite：

1. `scripts/tests/identity_gate_fixture.py`
2. `scripts/tests/test_a4_gate.py`
3. `scripts/tests/run_all.py`

交付报告：

1. `maintenance/repair-20260815-g1/workorder_pack3_fix2_done.md`

边界核验：

- `shared_release_receipt.py` **仅改 `canonical_target()`、它的 `evm_family` import，以及 `validate_accounting_receipt()` 调用前的重复 token 小写化**；未触碰 balance/time/anchor/gmgn/A4 消费区。
- 未改 `scripts/evm/verify_recon.py`、`scripts/lib/time_spotcheck.py`。
- fixture 只改造件值/参数；未改任何 `check()` 判据、needle 或 rc 预期。
- 未改 `test_repair_g1_cross_target.py`、`test_repair_g1_text_hygiene.py`。

## 2. shared `canonical_target()` 定点破例（显著行区间）

> **定点破例行区间：`scripts/report/shared_release_receipt.py:32-33,257-269,862-865`。该文件其余函数区未改。**

| 行段 | 改动 | 不变量 |
|---|---|---|
| `shared_release_receipt.py:32-33` | 从 `chain_registry` 引入 `evm_family` | 链族判定使用机器单源，不手写链名单 |
| `shared_release_receipt.py:257-269` | 先 `resolve_alias(chain)`；token 仅在 canonical chain 属 `evm_family()` 时 `.lower()`；Solana 保留 `strip()` 后原串 | EVM 地址大小写归一；Solana base58 原串精确比较 |
| `shared_release_receipt.py:862-865` | accounting token 不再在调用 `canonical_target()` 前无条件 `.lower()` | 禁止调用方预先破坏 Solana 地址语义 |

直接白盒回归：

```text
PASS canonical_target: EVM lower, Solana exact
rc=0
```

## 3. reconciliation 侧小写化产生点与修复

定位结果不是单一 wrapper，而是同一正式证据链的多个 target 写出点：

| 文件:行段 | 原产生点 | 修复 |
|---|---|---|
| `scripts/lib/solana_observation.py:454-455` | observation core `mint.lower()` | canonical target 写入原始 `mint` |
| `scripts/lib/solana_observation.py:543-544` | bundle validator 用 `expected_mint.lower()` | Solana mint 改为原串精确比较 |
| `scripts/solana/scan_token_accounts.py:192-194,218-222` | ERROR / observed-slot envelope 再次写 `args.mint.lower()` | 两条路径均写原始 `args.mint` |
| `scripts/solana/anchor_sampler.py:153-154` | balance/time receipt target 写 `MINT.lower()` | 写原始 `MINT` |
| `scripts/lib/supply_truth_gate.py:61-62,610-614` | supply-truth target 对 EVM/Solana 一律 `.lower()` | `resolve_alias` 后仅 EVM family 小写；Solana 原串 |
| `scripts/solana/window_fetch.py:212-213` | window receipt target 写 `MINT.lower()` | 写原始 `MINT` |

全库定向复扫：

```text
rg '"token": .*\.lower\(\)|expected_mint.*lower|canonical_target.*lower' \
  scripts/solana scripts/lib/solana_observation.py \
  scripts/lib/supply_truth_gate.py scripts/report/shared_release_receipt.py
```

结果：0 命中。

可绑定 loopback 的真实 Solana 纵切片已经证明 producer→runner 四查链原串闭合：

```text
reconciliation_report.json.target.token=
'CreiuhfwdWCN5mJbMJtA9bBpYQrQF2tCBuZwSPWfpump'
balance/supply/supply_truth/time 均 PASS/0
```

最终失败发生在 shared 校验测试手写的 adversarial target，不在 producer / runner：

```text
BLOCK: adversarial target mismatch
```

`test_batch3_solana_vertical_slice.py:216` 仍写：

```python
adversarial["target"] = {"chain": "solana", "token": MINT.lower(), ...}
```

该文件不在本轮获批 fixture 解冻名单，故未改；若放宽 shared 比较来迁就它，会直接撤回 r8 的 Solana 原串不变量。

## 4. fixture 对齐明细

| 文件:行段 | 仅 fixture 造件改动 | 结果 |
|---|---|---|
| `identity_gate_fixture.py:15-17,52-58` | `write_binding()` / `augment_gate()` 增加 token fixture 参数，默认由 `0xee…` 改为证据 target `0xaa…`；全部 replay / receipt 仍走真实 fixture producer | `test_a4_gate.py` 与共享消费者 `test_build_html.py` 均通过 |
| `test_a4_gate.py:328-331` | `analysis-state.json` fixture 增加 `token.chain=bsc`，与顶层 `chain=bsc` 一致 | D-06、P1-05、G9 三旧正例转绿 |

未改断言条件、needle、rc 预期或 test-only 特判。

## 5. `run_all.py` 登记

`scripts/tests/run_all.py:117-119` 已追加来源注释并登记：

```python
SUITE += ['test_repair_g1_cross_target.py',
          'test_repair_g1_text_hygiene.py']
```

登记已完成，但由于下节列出的冻结 fixture / manifest 红项，未把当前全量 suite 描述为全绿。

## 6. 指定回归 rc 表

统一环境：`PYTHONDONTWRITEBYTECODE=1`，绘图测试使用 `MPLCONFIGDIR=/private/tmp/tca-repair-g1-mpl`。

| 测试 | rc | 结果 |
|---|---:|---|
| `test_repair_g1_cross_target.py` | 0 | r1-r8、g1-g3，11/11 PASS；Solana 仅大小写差仍拒 |
| `test_audit_release_gate.py` | 0 | PASS |
| `test_repair_g1_audit_report.py` | 0 | F-02 四件套 PASS |
| `test_a4_gate.py` | 0 | 三项旧正例已转绿；全文件 PASS |
| `test_build_html.py` | 0 | 共享 `augment_gate()` 消费者 PASS |
| `test_handoff_manifest.py` | 0 | 68 项 PASS |
| `test_repair_g1_handoff_containment.py` | 0 | 14/14 PASS |
| `test_batch3_solana_vertical_slice.py`（受限沙箱） | 1 | loopback `socket.bind` EPERM，未到业务断言 |
| `test_batch3_solana_vertical_slice.py`（可绑定环境） | 1 | 四查 producer / runner 全 PASS 且 token 原串；最终被 fixture 的小写 adversarial target 以 `BLOCK: adversarial target mismatch` 拒绝 |
| `test_batch3_evm_vertical_slice.py`（受限沙箱） | 1 | loopback `socket.bind` EPERM，未到业务断言 |
| `test_batch3_evm_vertical_slice.py`（可绑定环境） | 0 | eth/bsc/base slices + nonzero dead vertical closure PASS |
| `test_formal_chain_support.py` | 0 | PASS |
| `test_batch2_robinhood_exploration.py` | 0 | PASS |
| `test_supply_truth_gate.py` | 0 | PASS |
| `docs_lint.py` | 0 | 45 个文档 PASS |
| `test_repair_g1_text_hygiene.py` | 0 | h1/h2/h3；303 个 tracked active 文件零命中 |

## 7. `shared_release_receipt` 相关测试扫描与 rc

搜索命令：

```text
rg -l 'shared_release_receipt' scripts/tests -g '*.py' | sort
```

除上节已列测试外，相关文件实跑结果：

| 测试 | rc | 结果 |
|---|---:|---|
| `test_sixlens_receipts.py` | 0 | PASS |
| `test_evm_observation_release.py` | 0 | 11/11 PASS，含 Solana 防误伤 |
| `test_batch4_invariant_guards.py` | 0 | PASS |
| `test_chain_registry.py` | 0 | PASS |
| `test_r9_batch3_release_guards.py` | 0 | Solana release negatives 6/6 PASS |
| `test_reconciliation_runner.py` | 0 | 7 个 controlled-execution 反例全部拒绝 |
| `test_repair_batch1.py` | 0 | PASS |
| `test_repair_batch2_f02.py` | 0 | PASS |
| `test_repair_batch3_f01.py` | 0 | PASS |
| `test_repair_batch_a.py` | 0 | 45/45 PASS |
| `test_round4b_provenance.py` | 0 | PASS |
| `test_r7_findings.py` | 0 | 15/15 PASS |
| `test_repair_batch_d.py` | 1 | 存量 Solana new-analysis fixture 缺 `analysis-state.token.chain` 与 identity bridge；同一新 F-03 gate 拒绝 |
| `test_review_20260804_p105.py` | 1 | 存量 new-analysis fixture 缺 `analysis-state.token.chain` 与 identity bridge；同一新 F-03 gate 拒绝 |
| `invariant_scan.py` | 1 | `audit_release_gate.py` 代码已消费 `identity-holder-snapshot/v2`，`invariant_manifest` 尚未登记；属于上一轮 F-03 接线的 manifest 迁移债 |
| `test_batch3_solana_producers.py` | 1 | 存量断言仍要求 `payload.target.token == MINT.lower()`；与本轮批准的 Solana 原串语义相反 |

最后四项失败都需要修改本轮严格冻结且未获解冻的测试 / manifest 文件；本轮未越界处理。

## 8. Hunk → finding 映射

| Hunk | finding / invariant | 目的 | 测试 owner |
|---|---|---|---|
| `shared_release_receipt.py:32-33,257-269,862-865` | F-03 / Solana 原串；EVM 链族归一 | shared 消费等式不再改变 base58 语义 | cross-target、canonical 白盒、shared 相关回归 |
| `solana_observation.py:454-455,543-544` | F-03 / producer-consumer 同深 | observation target 与 validator 原串全等 | Solana producer、release guards、纵切片 |
| `scan_token_accounts.py:192-194,218-222` | F-03 / 失败与成功 envelope 同语义 | ERROR / PASS target 均不小写 mint | sixlens receipts、producer、纵切片 |
| `anchor_sampler.py:153-154` | F-03 / 四查 balance/time 同 target | anchor 两个角色均保留原串 | sixlens receipts、纵切片 |
| `supply_truth_gate.py:61-62,610-614` | F-03 / 按链族归一 | EVM lower，Solana exact | supply_truth、batch A、纵切片 |
| `window_fetch.py:212-213` | F-03 / handoff 证据同 target | window receipt 原串 | batch1、sixlens receipts、handoff |
| `identity_gate_fixture.py:15-17,52-58` | 六视角③存量 fixture 迁移 | identity receipt token 对齐同案证据 | A4、build_html |
| `test_a4_gate.py:328-331` | F-03 / state 双 chain | fixture 的 `token.chain` 对齐顶层 chain | A4 三旧正例 |
| `run_all.py:117-119` | F-03 / F-14 防回退 | 登记包 3 两项测试 | suite 入口 |

未映射 hunk：0。

## 9. 问题决策

上一轮五条防旁路决策全部维持：

1. 不小写 Solana mint。
2. 不因 `independent-audit` 跳过 evidence 分区等式。
3. 不在 state 缺 `token.chain` 时静默跳过 identity token。
4. 不按测试文件名、固定 token 或 receipt source 写特判。
5. exploration 链混杂时，同时保留跨分区不一致与正式支持矩阵诊断。

本轮新增决策：

1. 不为迁就 `test_batch3_solana_vertical_slice.py` 的 `MINT.lower()` 放宽 `canonical_target()`；这会让真实 base58 语义缺陷回归。
2. 不修改未在裁决中解冻的 `test_batch3_solana_vertical_slice.py`、`test_batch3_solana_producers.py`、`test_repair_batch_d.py`、`test_review_20260804_p105.py` 或 invariant manifest。
3. 不把 loopback `EPERM` 记成业务失败；EVM 已在可绑定环境 rc=0，Solana 也已在可绑定环境走到最终 fixture target 等式。
4. `skill-creator` 的 `quick_validate.py` 两个本机 Python 均因缺 `yaml` 模块在导入阶段 rc=1；未越界安装依赖。仓库 AST 解析 9/9、docs lint 与目标回归均已独立执行。

## 10. 后续所需裁决

要把本包从 BLOCKED 变为完成，需再批准一次**仅 fixture / manifest 的存量迁移扩围**：

1. `test_batch3_solana_vertical_slice.py`：两处 fixture token（runner/adversarial）改为原始 `MINT`，断言逻辑不变。
2. `test_batch3_solana_producers.py`：把旧的 `MINT.lower()` 正例预期改为原始 `MINT`，断言结构不变。
3. `test_repair_batch_d.py`、`test_review_20260804_p105.py`：new-analysis fixture 补 `token.chain` 与 identity bridge；只迁移造件，不改 gate 判据。
4. 对应 invariant manifest：登记 `audit_release_gate.py` 已消费的 `identity-holder-snapshot/v2`。

在这些文件仍冻结时，“Solana 原串精确比较”“真实纵切片 rc=0”“shared 相关存量回归全绿”三者不可同时满足。
