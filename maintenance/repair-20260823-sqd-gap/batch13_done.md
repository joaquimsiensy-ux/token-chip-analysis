# 批 13 完成记录：accounting 期望 target 静态/冻结两态

## 结论

- **代码与定向验收完成；全套验收仍为 PARTIAL，不得报全绿。**
- 冻结态现在只在已通过现行 reconciliation 深验、且 Solana
  `exact_reconcile.target.as_of_block < wrapper.target.as_of_block` 时，把 accounting
  的 `expected_target` 取为 exact 冻结点。静态 Solana 与全部 EVM 仍取 wrapper target。
- `validate_accounting_receipt` 的 schema、execution_mode、producer、canonical target
  全等比较及 observation bundle 深验逻辑一个字未改；生产者、五查 runner、
  `replay_edges.py`、批 10–12 改面均未改。
- 最终 `run_all.py` 共 137 项：**135 PASS / 2 FAIL，exit 1**。两项均在业务逻辑前
  绑定本机 fixture server 时被沙箱拒绝；详见“全套结果”。因此须由允许 localhost
  bind 的 Fable 环境重跑到 137/137 后才算正式验收完成。

## RED 证据（生产代码修改前）

- 证据：`maintenance/repair-20260823-sqd-gap/batch13_red_evidence.txt`
- 命令：`python3 scripts/tests/test_batch13_accounting_target.py --r1`
- 退出码：`1`
- 原始失败：`reconciliation/accounting 公共深验失败: accounting target mismatch`
- 夹具事实：accounting/exact 冻结点为 103，wrapper 观测点为 104；现行 handoff
  verify 错把 104 传给 accounting validator，故稳定复现工单 R1。

## 改动与行号

1. `scripts/report/shared_release_receipt.py:1489-1504`
   - 新增 `accounting_expected_target(...)`：EVM 直接返回 wrapper；Solana 先复核
     exact 与 wrapper 的 chain/token 相同且 exact 不晚于 wrapper，静态态返回 wrapper，
     冻结态返回 exact。
2. `scripts/report/handoff_manifest.py:452-455`
   - verify 在调用未放宽的 `validate_accounting_receipt` 前，用上述函数选择期望 target。
3. `scripts/report/shared_release_receipt.py:1794-1817`
   - shared release 保留 EVM 原调用路径；静态 Solana 保留原 wrapper/accounting
     全等错误语义；冻结 Solana 用 exact target 调用原 accounting validator，并继续让
     adversarial/shared receipt 绑定冻结账本 target。
4. `scripts/report/audit_release_gate.py:282-311,324-341`
   - 只有 accounting 与 wrapper 时点不同才尝试两态；必须先由当前
     `validate_reconciliation_report(..., return_receipts=True)` 深验 exact，再确认
     accounting canonical target 与 exact 全等，才把 reconciliation 的 block claim
     投影到冻结点。任何异常都不授予豁免，仍由原唯一性检查与后续公共深验拒绝。
5. `scripts/tests/test_batch13_accounting_target.py:34-293`
   - 新增 R1/G1、N1、N2（chain 与 token 各自错配）、静态 Solana、EVM、shared
     下游、audit 两态/负例、audit 静态回归，共 8 项。
6. `scripts/tests/run_all.py:177-178`
   - 新测试已登记进守护全套。

## 生产面 4 处调用点全量核查

1. **handoff verify** — `scripts/report/handoff_manifest.py:425-459`
   - 这是工单命中的错误消费点。reconciliation 先返回 wrapper 与五份已深验 receipt；
     :452-455 再按静态/冻结两态选择 accounting 期望 target。G1 通过；N1/N2 仍拒。
2. **shared release** — `scripts/report/shared_release_receipt.py:1794-1817`
   - :1796 的首次 `validate_accounting_receipt(root)` 只验证 accounting 自身真实收据与
     observation bundle，不做跨件比较；旧下游 :1799-1800 曾把 accounting 冻结点作为
     wrapper 期望点，冻结态会炸。现已分家：EVM 维持原路径，静态 Solana 维持原全等，
     冻结 Solana 在 :1812-1813 把 exact 冻结点传回未放宽的 accounting validator。
   - `create_bundle` / `validate_bundle` 都经 `validate_sources`，故 shared receipt 在冻结态
     继续绑定 accounting/exact 冻结账本，而不是 wrapper 的活观测点。
3. **audit release** — `scripts/report/audit_release_gate.py:282-341,487-493,1435-1446`
   - :487-493 的 `check_accounting` 无 `expected_target`，语义仅是独立重验 accounting
     收据本体，不应改。真正同型假设在 `check_formal_case_chain`：原先把 accounting、
     wrapper、shared、identity 的 `as_of_block` 强制成单值；现仅在 exact 已深验且
     accounting==exact 时把 wrapper block claim 投影到冻结点。N1/N2 证明错误 slot、
     chain、token 均不获豁免。
4. **handoff generate** — `scripts/report/handoff_manifest.py:289-307`
   - generate 只深验 reconciliation、exact inputs 与 derived bindings，不调用
     `validate_accounting_receipt`，也没有把 accounting target 与 wrapper target 比较；
     本轮无需改。现有 `test_recon_fifth_check.py` 的 generate/verify 回归通过。

## 全库同型扫描结论

- 对 `validate_accounting_receipt`、`accounting/as_of/target`、`canonical_target` 的生产
  Python 面做了全库 `rg`。除上述 handoff/shared/audit 外，没有发现另一个把 accounting
  `as_of_block` 与 wrapper/observed 时点直接全等比较的消费点。
- `scripts/report/adversarial_review_runner.py:568-579,671` 从 accounting 生成冻结 target；
  shared release 现于 `shared_release_receipt.py:1816` 同样用已验证 accounting target
  重验 adversarial，语义一致。
- `scripts/lib/supply_truth_gate.py:548` 与 `scripts/solana/anchor_sampler.py:147` 的文案均明确
  是“与 accounting target 对齐的冻结块/slot”，不是活 wrapper 全等假设，无需改。

## 文档与契约

- `references/scan-schemas.md` 与 `references/split-run.md` 未出现“accounting target 必须与
  reconciliation wrapper target 全等”的现役表述；按工单“无则不动”，两文件未改。
- 本批是调用方在两份**已深验** target 中选择正确期望对象，不放宽
  `validate_accounting_receipt`，也没有新增独立发布拒绝路径；因此不新增 CT-SQDGAP 锚。
- `docs_lint.py --all`、`test_contract_routes.py`、`test_version_consistency.py` 均通过。

## 测试结果

### 定向与硬闸

- `python3 scripts/tests/test_batch13_accounting_target.py`：**8/8 PASS**。
- `test_recon_fifth_check.py`、`test_batch11_frozen_bundle_binding.py`、
  `test_batch12_frozen_supply_drift.py`：PASS。
- `test_evm_observation_release.py`：**11/11 PASS**。
- `test_reconciliation_runner.py`：7 个反例全部拒绝，PASS。
- `test_handoff_manifest.py`：**68 项 PASS**。
- `test_audit_release_gate.py`：PASS。
- `invariant_scan.py`：PASS，计数保持
  `receipt_producers=75, receipt_consumers=112, transport_calls=65,`
  `atomic_writes=56, formal_entrypoints=61, exceptions=0`。
- `docs_lint.py --all`、`test_version_consistency.py`、
  `test_batch4_invariant_guards.py`、`test_contract_routes.py`：PASS。

### 最终 run_all

- 命令：`python3 scripts/tests/run_all.py`
- 最终内容变更后重新完整执行；结果：**137 total / 135 PASS / 2 FAIL，exit 1**。
- 新登记的 `test_batch13_accounting_target.py` 在全套内：**8/8 PASS**。
- 仅余两项：
  - `test_batch3_solana_vertical_slice.py:625`：
    `ThreadingHTTPServer(("127.0.0.1", 0), ...)` →
    `PermissionError: [Errno 1] Operation not permitted`。
  - `test_batch3_evm_vertical_slice.py:281`：同一 localhost bind 错误。
- 两项都在 producer/business assertions 之前失败；不是本批代码回归，但真实全套退出码仍为
  1，故本记录明确保持 PARTIAL。未修改纵切片、未把环境失败伪装成 PASS。

## 边界自查

- 改/建文件仅为：
  - `scripts/report/handoff_manifest.py`
  - `scripts/report/shared_release_receipt.py`
  - `scripts/report/audit_release_gate.py`
  - `scripts/tests/test_batch13_accounting_target.py`
  - `scripts/tests/run_all.py`
  - `maintenance/repair-20260823-sqd-gap/batch13_red_evidence.txt`
  - `maintenance/repair-20260823-sqd-gap/batch13_done.md`
- 用户提供的 `batch13_workorder.md` 只读，未改。
- `VERSION`、`SKILL.md`、`pyproject.toml`、`reconciliation_report.py`、
  `replay_edges.py`、`holder_distribution_scan.py` 与版本登记面相对 HEAD 无差异。
- `git diff --check` 通过；分支仍为 `main`；HEAD
  `672893067d555788979dc8a99f77437ce69c6053`；未 commit、未 push、未切分支。
- 未读取或修改密钥；未访问、修改或重跑 ARC 案根；未执行 handoff 实案验收。
- 本检出没有 `sync-from-cc.sh` / `SYNC.md`，只记录缺失，不当作同步 PASS。

## Fable 验收待办

在允许绑定 localhost 的验收环境执行：

```bash
python3 scripts/tests/run_all.py
```

只有得到 **137/137 PASS、exit 0** 后，才可把批 13 从 PARTIAL 改为正式完成并由 Fable
代 commit；ARC handoff 实案重跑仍由验收方按工单执行。
