# 批 13 工单：handoff verify 对 accounting 收据的期望时点两态（方案 A 同族第五消费点）

- 裁决依据：延续用户 2026-08-26 方案 A。批 10（runner target 层）/批 11（发布深验
  文件绑定层）/批 12（分布扫描器供应层）之后，ARC handoff verify 实跑暴露第五个
  静态时点假设消费点。
- 背景（大白话）：A0 的会计模式核定（accounting_mode.json）在**封账当天**跑，
  它的 as_of_block 天然=冻结点（ARC 实测 440368381，checked_at=封账时刻）。
  handoff verify（handoff_manifest.py:451-452）把五查 wrapper 的 target 当
  expected_target 传给 `validate_accounting_receipt`——wrapper target 在方案 A
  动态模式下是**观测时点**（链上现在，ARC 实测 441940997）→ canonical 全等比对
  必炸 "accounting target mismatch"。静态案两者相等所以从没炸过。
- 修正哲学：与批 10/11 同一把尺子——冻结态下，会计核定绑定的对象是**冻结账本**，
  期望时点应取 exact_reconcile 收据的 target（冻结点），不是观测时点。

## 现状事实（ARC 实测，可作夹具参照）

- accounting_mode.json：as_of_block=440368381、checked_at=2026-08-20T00:25:18Z、
  verdict=PASS、schema=accounting-gate/v1、execution_mode=formal。
- 五查 wrapper target.as_of_block=441940997（观测）；exact receipt
  target.as_of_block=440368381（冻结）。
- verify 报错原文：`reconciliation/accounting 公共深验失败: accounting target mismatch`。

## 改动面

### 1. handoff_manifest.py `_verify_light_schema`（:451-452）

expected_target 改两态：
- **静态态**（exact receipt target.as_of_block == wrapper target.as_of_block）：
  维持现状（传 wrapper/recon target），零变化。
- **冻结态**（exact < wrapper，仅 Solana 动态案存在）：传
  `recon_receipts["exact_reconcile"]` 的 canonical target（冻结点）。
  chain/token 部分两者本就相同——变的只有 as_of_block 的取向。
- 该函数上下文里 `target` 与 `recon_receipts` 都已在手（validate_reconciliation_report
  return_receipts=True 已返回），改动应为几行。

### 2. 调用点全量核查（关到同一深度，生产面共 4 处）

- `shared_release_receipt.py:1778`（`validate_accounting_receipt(root)` 无
  expected_target）——确认该路径语义（谁消费、要不要两态），给行号结论；
  若它下游还有拿 accounting target 与观测时点比对的环节，同修。
- `audit_release_gate.py:462-463`（accounting=d、无 expected_target）——同上核查。
- `handoff_manifest.py` generate 路径是否也有同型比对（generate 本轮 exit 0，
  预期无，但给行号证明）。
- rg 全库再扫一遍"拿 accounting as_of 与 wrapper/observed 比对"的其他形态
  （字符串比对、canonical_target 相等式），逐处结论写 done 报告。

### 3. 文档与契约

- scan-schemas.md / split-run.md 相应段落若有"accounting target 与对账 wrapper
  target 全等"的表述，改两态表述并附大白话；无则不动并在 done 说明。
- 新拒绝路径若需契约锚点沿用 CT-SQDGAP 下一号；纯放宽无新锚则论证后不加。

### 4. 测试（先红后绿）

- R1 红：冻结态夹具（accounting@冻结点 + wrapper@观测点 + exact@冻结点）→
  现行 verify 路径拒 "accounting target mismatch"（留红证据）。
- G1 绿：同夹具改后通过。
- N1：accounting as_of ≠ exact 冻结点（两者都非）→ 仍拒。
- N2：accounting chain/token 错配 → 仍拒。
- N3：静态态（三者同点）现有夹具零变化（回归；纵切片测试是现成静态全链）。
- run_all 全套（真实失败清零）。

## 边界与禁改面

- validate_accounting_receipt 本体的校验逻辑（schema/execution_mode/producer/
  canonical 全等比对本身）不放宽——改的只是**调用方传入的期望时点取向**；
  若你分析后认为在函数内部做两态更内聚，可以，但必须保证 EVM 与静态 Solana
  行为逐字不变，且 done 报告论证选型。
- accounting 生产者、五查 runner、replay_edges、批 10-12 已改面一律不动。
- 不触碰密钥；ARC 案根一个字不动（重跑 handoff 由验收方执行）。
- 纯改文件不 commit、不动版本登记面；完成写 batch13_done.md（行号清单、红绿
  证据、4 处调用点核查结论、run_all 结果、边界自查），Fable 验收后代 commit。
