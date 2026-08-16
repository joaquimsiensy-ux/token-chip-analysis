# 包 3 fix 阶段施工报告（F-03 / F-14）

日期：2026-08-15
状态：**BLOCKED，未达到交付门槛**
结论：F-03 冻结定向测试已由 9 红转为 11/11 绿；但两项指定存量回归与蓝图不变量存在可复现冲突。未登记 `run_all.py`，未声称全绿，未执行任何 git 命令。

## 1. 本轮文件范围

已改：

1. `scripts/report/audit_release_gate.py`
2. `maintenance/repair-20260815-g1/workorder_pack3_fix_done.md`

明确未改：

- `scripts/tests/test_repair_g1_cross_target.py`
- `scripts/tests/test_repair_g1_text_hygiene.py`
- `scripts/tests/` 下全部冻结断言
- `scripts/tests/run_all.py`（因指定回归未全绿，不登记失败 suite）
- `scripts/report/audit_release_gate.py` 原 adversarial 校验段

## 2. 生产改动与行号

| 行段 | 改动 | 对应 finding |
|---|---|---|
| `audit_release_gate.py:19-22` | 引入 `chain_registry.evm_family` | F-03 token 按链族归一 |
| `audit_release_gate.py:83-150` | 统一专属错误类；严格挂载在场 JSON；chain/token/block 收集与唯一性校验 | F-03 跨分区等式、字段缺失 fail-closed、诊断文案 |
| `audit_release_gate.py:153-206` | 由 `snapshot_binding.receipt_file` 定位 identity receipt，重验案根 containment、receipt 字节 SHA256、v2 schema、adapter/block/schema binding 后导出 token/block | F-03 identity-receipt 桥 |
| `audit_release_gate.py:209-317` | state 双 chain、identity/A4/A5/evidence chain 全收；accounting/recon/shared 与 identity receipt 的 token/block 全收；A4⇒identity 条件必需；exploration 原因与等式错误并列保留 | F-03 主不变量与 g3 旁路封口 |
| `audit_release_gate.py:1388` | `run()` 将 `case_dir` 接入扩展后的检查器 | F-03 发布必经路接线 |

错误统一以 `正式发布跨分区 target 不一致:` 开头，并在不等时列出来源文件、字段和原始值；同时含“不一致/矛盾/漂移”语义，满足 test-only 工单第 2 节专属分类。

## 3. 九红转绿实况

命令：

```text
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/private/tmp/tca-repair-g1-mpl \
  python3 scripts/tests/test_repair_g1_cross_target.py
rc=0
```

| 用例 | 修后实况 | 命中的专属错误 |
|---|---|---|
| r1 | PASS | 结论 eth、证据 bsc，chain 声明矛盾；列出 state/identity/A4/A5/accounting/recon/shared |
| r2 | PASS | 证据 eth、结论 bsc，chain 声明矛盾 |
| r3 | PASS | identity receipt token=`0xbb…` 与三份证据 token=`0xaa…` 矛盾 |
| r4 | PASS | identity receipt block=456 与三份证据 block=123 矛盾 |
| r5 | PASS | 仅 A5 chain=eth 漂移被统一错误类捕获 |
| r6 | PASS | 仅 shared target.chain=eth 漂移被统一错误类捕获 |
| r7 | PASS | `state.chain=bsc` 与 `state.token.chain=eth` 分别入表后捕获 |
| r8 | PASS | Solana mint 仅大小写不同仍判为不同 |
| g1 | PASS | `solana` / `sol` chain alias 归一后未误报 |
| g2 | PASS | independent-audit 无 state/identity/A4 未被硬要 |
| g3 | PASS | A4 在场而 identity bridge 缺席被专属错误阻断 |

## 4. 指定回归 rc 表

| 测试 | rc | 结果 |
|---|---:|---|
| `test_repair_g1_cross_target.py` | 0 | 11/11 PASS |
| `test_audit_release_gate.py` | 0 | PASS |
| `test_repair_g1_audit_report.py` | 0 | F-02 四件套 PASS |
| `test_a4_gate.py` | 1 | **BLOCKER：3 项旧正例违反新 target 等式** |
| `test_handoff_manifest.py` | 0 | 68 项 PASS |
| `test_repair_g1_handoff_containment.py` | 0 | 14/14 PASS |
| `test_batch3_evm_vertical_slice.py` | 0 | 沙箱内先因 loopback bind `EPERM` rc=1；获准在可绑定 127.0.0.1 的环境复跑后 PASS |
| `test_batch3_solana_vertical_slice.py` | 1 | **BLOCKER：真实 producer token 大小写发生语义漂移** |
| `test_formal_chain_support.py` | 0 | PASS |
| `test_batch2_robinhood_exploration.py` | 0 | PASS |
| `docs_lint.py` | 0 | 45 个文档 PASS |
| `test_repair_g1_text_hygiene.py` | 0 | h1/h2/h3 与真实仓库 PASS |

`run_all.py` 未登记、未运行：当前登记会把已知失败永久并入 suite，不满足“回归全绿后登记”的施工顺序。

## 5. 阻断 1：`test_a4_gate.py` 的旧正式正例与 identity bridge 矛盾

真实输出：

```text
正式发布跨分区 target 不一致: analysis-state.json.token 缺失或不是对象，token.chain 无法收集
正式发布跨分区 target 不一致: token 声明矛盾:
accounting/reconciliation/shared='0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
identity_holders_receipt.json='0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'
```

该测试的 `identity_gate_fixture.write_binding()` 固定以 `0xee…` 生成真实 `identity-holder-snapshot/v2` receipt；同案 `build_case()` 的正式证据 target 固定为 `0xaa…`。同时其 `analysis-state.json` 只有顶层 `chain=bsc`，没有本蓝图要求单独收集的 `token.chain`。因此 D-06、P1-05、G9 三个旧正例被新等式正确阻断。

若在 gate 内为该 fixture 放行，只能采取以下任一错误做法：忽略 identity receipt token、允许 state 缺 `token.chain`、或按测试路径/值写特判；三者都会重开 F-03 旁路。

## 6. 阻断 2：Solana 真实 producer 链当前会改变 base58 token 大小写

在沙箱外复跑真实纵切片后，失败发生在最终 `audit_release_gate.py`：

```text
accounting_mode.json.token|mint='CreiuhfwdWCN5mJbMJtA9bBpYQrQF2tCBuZwSPWfpump'
reconciliation_report.json.target.token='creiuhfwdwcn5mjbmjta9bbpyqrqf2tcbuzwspwfpump'
shared_release_receipt.json.target.token='creiuhfwdwcn5mjbmjta9bbpyqrqf2tcbuzwspwfpump'
```

`accounting_gate_sol.py` 保留用户输入的原始 mint；现有 reconciliation/shared target 路径把 token 小写化。Solana base58 大小写敏感，这两个字符串不是同一地址，不能用 EVM 规则折叠。新等式将其阻断符合本包 r8 与计划 §四的明确要求，但与“Solana 真实 producer 纵切片必须 rc=0”要求直接冲突。

## 7. 问题决策

1. 不对 Solana mint 做 `.lower()`；否则 r8 由绿退红，且把不同 base58 地址当成同一 target。
2. 不因 `profile=independent-audit` 跳过 evidence 分区等式；否则真实审计仍可让 accounting/recon/shared 指向不同 target。
3. 不在 state 缺 `token.chain` 时静默跳过 identity token；否则删除一个字段即可绕开 identity bridge。
4. 不按测试文件名、固定 token 或 receipt source 写 test-only 特判。
5. exploration 链与 bsc 混杂时，同时保留“跨分区不一致”和正式支持矩阵拒绝原因，使既有 formal-chain 回归不丢失更严格诊断。

## 8. 需要的上游裁决

当前约束集合不可同时满足。继续施工至少需要批准以下范围之一：

1. **推荐：扩大修复范围并解冻相应测试 fixture。** 修正 reconciliation/shared 的 Solana target 规范化，端到端保留原始 base58；同时把 `test_a4_gate.py` 正例的 state/identity target 与证据 target 对齐。随后重跑本报告全部回归，再登记 `run_all.py` 两项。
2. 明确撤回“Solana base58 原串精确比较”或“所有在场字段/identity receipt 必须入等式”中的一项，并接受相应 F-03 旁路；当前不建议。

在未获该裁决前，本包不能诚实标记为 fix complete。
