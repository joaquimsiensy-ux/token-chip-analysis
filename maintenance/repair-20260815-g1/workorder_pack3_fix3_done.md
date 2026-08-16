# 包 3 fix 第三轮收尾施工报告

日期：2026-08-15

施工目录：`/Users/uravvv/.claude/skills/tca-repair-g1`

状态：**BLOCKED**

阻断只剩一项：四组获批迁移均已完成，目标 new-analysis 正负例也已通过；但完整 `test_repair_batch_d.py` 继续执行后暴露 F-D2 两条旧 fixture 未登记 `entity_source_trace.py` / `wave_scan.py` 算法文件绑定，整文件 rc=1。该项不属于本轮批准的 new-analysis fixture 迁移，未越界修改。另有两条纵切片在本沙箱的 loopback `socket.bind()` 处命中 `PermissionError: [Errno 1] Operation not permitted`，按裁决记为环境限制，待调度方本机复跑。

本轮只改批准的五个测试/manifest 文件及本报告；未改生产代码，未执行任何 git 命令。

## 1. 四组迁移明细

### 1.1 Solana 纵切片 fixture 原串

- `scripts/tests/test_batch3_solana_vertical_slice.py`
  - runner target：`MINT.lower()` → `MINT`。
  - adversarial target：`MINT.lower()` → `MINT`。
- 仅迁移 fixture token 值；runner/adversarial 结构、执行链和断言逻辑未改。
- 定向静态核对：该文件已无 `MINT.lower()`。

### 1.2 Solana producer 正例期望原串

- `scripts/tests/test_batch3_solana_producers.py`
  - `payload["target"]["token"] == MINT.lower()` → 与原比较方式相同的 `== MINT`。
- 断言结构和比较方式未改。
- 基线 rc=1，失败点为该旧小写期望；迁移后 rc=0。

### 1.3 两组 new-analysis fixture 补 target / identity bridge

#### `test_review_20260804_p105.py`

- `analysis-state.json` 增加 `token.chain="bsc"`，与顶层 `chain="bsc"` 一致。
- 新建 `identity_gate.json` 和 `identity-holder-snapshot/v2` receipt。
- bridge 在 `identity_bridge/` 隔离子目录复用 `identity_gate_fixture.augment_gate()` 的现成 EVM producer，避免覆盖主 fixture 的四查文件。
- identity receipt token 使用 `fixture.CASE_TOKEN`，与 accounting/reconciliation/shared target 精确一致；state SHA 绑定当前 `analysis-state.json`。
- gate 判据和原断言未改。基线 rc=1；迁移后 rc=0。

#### `test_repair_batch_d.py`

- Solana state 增加 `token.chain="solana"`，与顶层 `chain="solana"` 一致。
- 在 `identity_bridge/` 隔离子目录用测试 transport 真跑 `scan_token_accounts.py`，实测 `snapshot_slot=500`；再由生产 emitter `identity_snapshot_receipt.emit_solana()` 生成 `identity-holder-snapshot/v2` receipt。
- `identity_gate.json` 的 chain/token/as-of 分别绑定 `solana`、原始 `SOL_MINT`、`SOL_SLOT=500`；receipt adapter 为生产口径 `sol`。
- new-analysis 发布闸绿例、owners 换包负例、缺件负例均通过；gate 判据和三条原断言未改。

### 1.4 invariant manifest 登记

先执行：

```text
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/invariant_scan.py --dump-actual
```

实测 `scripts/report/audit_release_gate.py` 的 consumer schemas 为：

```text
address-balance-snapshot/v1
adversarial-review/v2
adversarial-review/v3
adversarial-review/v4
figure2-check-receipt/v1
identity-holder-snapshot/v2
reconciliation-report/v2
reproduce-receipt/v2
```

据此只做两项同步：

- `audit_release_gate.py` 的 `receipt_consumers.schemas` 增加 `identity-holder-snapshot/v2`。
- `minimum_counts.receipt_consumers` 从 78 上调到 79；其他 floor 不动。

基线 `invariant_scan.py` rc=1，精确报告 manifest/code 一进一出共 2 discrepancies；迁移后正常扫描与 `--self-test` 均 rc=0。

## 2. invariant manifest 前后计数

这里区分 manifest denominator 与 minimum floor，避免把 floor 误写成实测总数。

| 键 | manifest 迁移前 | manifest 迁移后 | minimum 迁移前 | minimum 迁移后 |
|---|---:|---:|---:|---:|
| `receipt_producers` | 62 | 62 | 61 | 61 |
| `receipt_consumers` | 82 | 83 | 78 | 79 |
| `transport_calls` | 63 | 63 | 63 | 63 |
| `atomic_writes` | 52 | 52 | 52 | 52 |
| `formal_entrypoints` | 58 | 58 | 58 | 58 |

迁移后扫描摘要：

```text
PASS invariant manifest: receipt_producers=62, receipt_consumers=83, transport_calls=63, atomic_writes=52, formal_entrypoints=58, exceptions=0
SELFTEST delete scripts/evm/accounting_gate.py:net.py -> RED (rc=1)
SELFTEST add scripts/report/does_not_exist.py:requests -> RED (rc=1)
```

`--self-test` 总命令 rc=0；其中两个注入场景的内部 rc=1 是预期 RED。

## 3. 指定全回归 rc 表

以下为修后真实重跑结果；环境统一使用 `PYTHONDONTWRITEBYTECODE=1`，涉及图形的测试使用可写的 `/private/tmp` Matplotlib cache。

| 命令 | rc | 结果 |
|---|---:|---|
| `python3 scripts/tests/test_repair_g1_cross_target.py` | 0 | PASS |
| `python3 scripts/tests/test_batch3_solana_producers.py` | 0 | PASS |
| `python3 scripts/tests/test_repair_batch_d.py` | 1 | **BLOCKED**：仅 F-D2 两条旧 fixture 失败；本轮 new-analysis 正负例全过 |
| `python3 scripts/tests/test_review_20260804_p105.py` | 0 | PASS |
| `python3 scripts/tests/invariant_scan.py` | 0 | PASS，62/83/63/52/58，exceptions=0 |
| `python3 scripts/tests/invariant_scan.py --self-test` | 0 | PASS，两个 mutant 均预期 RED |
| `python3 scripts/tests/test_batch4_invariant_guards.py` | 0 | PASS |
| `python3 scripts/tests/test_a4_gate.py` | 0 | PASS |
| `python3 scripts/tests/test_build_html.py` | 0 | PASS |
| `python3 scripts/tests/test_audit_release_gate.py` | 0 | PASS |
| `python3 scripts/tests/test_repair_g1_audit_report.py` | 0 | PASS |
| `python3 scripts/tests/test_handoff_manifest.py` | 0 | PASS |
| `python3 scripts/tests/test_repair_g1_handoff_containment.py` | 0 | PASS |
| `python3 scripts/tests/test_supply_truth_gate.py` | 0 | PASS |
| `python3 scripts/tests/test_sixlens_receipts.py` | 0 | PASS |
| `python3 scripts/tests/test_evm_observation_release.py` | 0 | PASS |
| `python3 scripts/tests/test_r9_batch3_release_guards.py` | 0 | PASS |
| `python3 scripts/tests/test_reconciliation_runner.py` | 0 | PASS |
| `python3 scripts/tests/test_repair_batch_a.py` | 0 | PASS |
| `python3 scripts/tests/test_r7_findings.py` | 0 | PASS |
| `python3 scripts/tests/docs_lint.py` | 0 | PASS |
| `python3 scripts/tests/test_repair_g1_text_hygiene.py` | 0 | PASS |

有效汇总：指定 22 条命令中 21 条 rc=0，1 条 rc=1（F-D2 越界存量 fixture）。

### 3.1 两条纵切片沙箱限制

两条虽未单列在上述指定命令名中，仍按工单要求额外实跑：

| 命令 | rc | 环境证据 |
|---|---:|---|
| `python3 scripts/tests/test_batch3_evm_vertical_slice.py` | 1 | `ThreadingHTTPServer(("127.0.0.1", 0), ...)` → `socket.bind` → `PermissionError: [Errno 1] Operation not permitted` |
| `python3 scripts/tests/test_batch3_solana_vertical_slice.py` | 1 | 同上，在任何业务断言前失败 |

两项均为 sandbox loopback 能力限制，不记作业务失败；调度方需在允许绑定 loopback 的本机环境复跑。

## 4. `test_repair_batch_d.py` 阻断证据

new-analysis 迁移部分已通过：

```text
snapshot_slot=500 accounts=1 owners=1 supply=100 activity=complete -> snapshot.json
ok    B-2 Solana new-analysis run() 端到端绿例（发布闸零 error）
ok    B-1 原反例：holder_outputs.owners 换包被 validator 三验拒
ok    B-2 换仓后发布闸拒（端到端负例）
ok    B-1 缺件：owners 实物不存在被拒
```

整文件随后在 F-D2 报两条失败：

```text
FAIL  F-D2 基线：收据原样 check-unseal 放行
  算法依赖 entity_source_trace.py 算法文件绑定不是对象
  算法依赖 wave_scan.py 算法文件绑定不是对象
FAIL  F-D2 复原后再放行（绑定即字节）  2
BATCH D FAIL 2
```

根因：`t_fd2_unseal_binds_flip_receipt()` 的手工 `provenance_ledger.json` 只有 `input_binding.algorithm_params.flip_adjudications`，没有当前 `handoff_manifest.py --check-unseal` 已强制复验的 `input_binding.algorithm.files` 两个对象绑定。此处不是本轮批准的 new-analysis fixture；若要全绿，需另行批准把 F-D2 存量 fixture 迁移到当前算法文件绑定不变量，断言与判据仍可保持不变。

## 5. Hunk → 不变量映射

| 文件 / 当前行 | 不变量 | 迁移动作 | 判据/断言结构 |
|---|---|---|---|
| `test_batch3_solana_vertical_slice.py:127,216` | Solana base58 原串精确比较 | runner/adversarial token 改用 `MINT` | 不变 |
| `test_batch3_solana_producers.py:244` | producer 输出保留 Solana 原串 | 正例期望值改用 `MINT` | 比较方式不变 |
| `test_review_20260804_p105.py:96,119-129` | state 双 chain；identity receipt target bridge | 补 `token.chain`，隔离目录真造 EVM identity gate/receipt | gate 与原断言不变 |
| `test_repair_batch_d.py:1040,1063-1098` | state 双 chain；Solana identity snapshot producer 证明 | 补 `token.chain`，真跑 scan + `emit_solana` 造 identity gate/receipt | gate 与原断言不变 |
| `invariant_manifest.json:15,407` | audit consumer schema 清单与扫描器实测一致 | 登记 `identity-holder-snapshot/v2`，floor 78→79 | scanner 不变 |

未映射施工 hunk：0。

## 6. 问题决策

`workorder_pack3_fix2_done.md` §9 的五条防旁路决策全部维持：

1. 不小写 Solana mint。
2. 不因 `independent-audit` 跳过 evidence 分区等式。
3. 不在 state 缺 `token.chain` 时静默跳过 identity token。
4. 不按测试文件名、固定 token 或 receipt source 写特判。
5. exploration 链混杂时，同时保留跨分区不一致与正式支持矩阵诊断。

本轮附加决策：

1. EVM identity fixture producer 明确拒绝 `chain=solana`，不伪装 emitter；Solana bridge 改走真实 `scan_token_accounts` + `emit_solana` producer 链。
2. identity bridge 全部放隔离子目录，避免覆盖主 fixture 的四查/回放文件。
3. 不把两条 loopback `EPERM` 写成业务失败或绿例。
4. 不为收口数字越界迁移 F-D2；因此最终状态如实为 **BLOCKED**。
5. 不执行 skill 常规同步、不执行依赖安装、不执行任何 git 操作，避免越过“只改四组文件”的施工边界。

## 7. 结论

四组已批准迁移全部完成，目标不变量均有真实验证证据；指定回归除 `test_repair_batch_d.py` 的两条越界 F-D2 存量 fixture 外全部 rc=0。由于工单要求“全部应 rc=0”，本轮不能宣称完成，交付状态为 **BLOCKED**。解除阻断只需对 F-D2 fixture 的算法文件绑定迁移另行裁决；两条纵切片由调度方在允许 loopback bind 的本机复跑。
