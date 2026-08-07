# R8 修复闭环：diff → invariant → finding 映射

本表从施工批次开始逐 commit 填写。准备阶段不登记任何真实 commit/hunk；Fable 代为 commit 后，以 candidate SHA 中本表为准。

规则：

1. 每个生产代码、测试、fixture、删除、文档和元数据 hunk 都必须有 owner。
2. owner 先指向一个 primary invariant，再展开到全部受影响 finding；不能用“顺手整理”或笼统“R8 fixes”代替。
3. 若属于第四类豁免，finding 栏写明豁免 ID，并链接 `robinhood-impact.md` 或相应影响台账。
4. 一个 hunk 涉及多个不变量时拆行；同一 commit 可有多行。
5. 审查结论由批内审查/Fable 填写；准备阶段留空。

| commit/hunk | primary invariant | finding 列表或豁免 | 修改目的 | 测试/纵切片/守卫 | 审查结论 |
|---|---|---|---|---|---|
| `示例：<candidate-sha>:scripts/lib/example.py:L10-L42` | `INV-07` | `R7-12, R8-07, R8-09` | 让正式 EVM 状态读取在业务 RPC 前完成 chain-id attestation | `test-id`；EVM eth/bsc/base 错链时业务 RPC=0 |  |
| `B1-G1:scripts/lib/receipt_kernel.py` | `INV-05` | `R8-04`; `R8-12` 仅 kernel 能力 | 用逐级 `lstat`、dirfd、`O_NOFOLLOW`、物理身份判重和保留备份的回滚闭合四类发布/恢复 primitive | `B1-RK-01`～`B1-RK-06`; `test_batch1_receipt_paths.py`; `test_receipt_kernel.py` |  |
| `B1-G1:scripts/tests/{test_batch1_receipt_paths.py,test_receipt_kernel.py,test_r7_findings.py,test_sixlens_receipts.py,run_all.py}; maintenance/repair-20260806/{ledger.md,batch1-report.md}` | `INV-05` | `R8-04`; `R8-12` 仅 kernel 能力 | 固化 symlink/alias/TOCTOU、失败分支、fault-on-fault 与 PASS 保护反例；现有 receipt fixture 以无 symlink 的解析后临时根运行；登记批三 producer 边界 | `B1-RK-01`～`B1-RK-06`; 全量 suite |  |
| `B1-G2:scripts/lib/{net.py,rpc_batch.py,time_spotcheck.py,supply_truth_gate.py}; scripts/evm/{accounting_gate.py,verify_recon.py,multicall_balances.py,pierce_stake.py,lp_positions.py,scan_bloxroute_seg.py,fetch_alchemy.py}` | `INV-07` | `R7-12, R8-07, R8-09` | 将 10 个正式 EVM 业务 RPC 调用点统一迁入从 registry 取期望链 ID 的 attested session | `B1-RPC-01`～`B1-RPC-06`; 10 个 `B1-RPC-CALLSITE-*` |  |
| `B1-G2:scripts/tests/{test_batch1_rpc_attestation.py,test_r7_findings.py,test_sixlens_receipts.py,invariant_manifest.json,run_all.py} 的 RPC/session hunk; maintenance/repair-20260806/{transport-injections.json,ledger.md,batch1-report.md}` | `INV-07` | `R7-12, R8-07, R8-09` | 登记唯一 fake 注入边界，证明错链零业务调用、attestation 失败关闭、正链和 failover 重验，并同步静态调用图 | `B1-RPC-01`～`B1-RPC-06`; `invariant_scan.py`; 全量 suite |  |
| `B1-G3:scripts/labels/{risk_flags.py,add_labels.py,validate_labels.py,roundtrip_check.py,labels_resolver.py,build_labels.py}` | `INV-15` | `R7-14, R8-10` | 建立唯一 canonical parser；读取宽进、写入/验证严出，所有 policy 判断共用规范集合 | `B1-RF-01`～`B1-RF-03`; 现役 470879 行语义对表 |  |
| `B1-G3:scripts/tests/{test_batch1_risk_flags.py,run_all.py}; maintenance/repair-20260806/{ledger.md,batch1-report.md}` | `INV-15` | `R7-14, R8-10` | 固化前导空格、重复/乱序/空段以及全部现役表兼容反例 | `B1-RF-01`～`B1-RF-03`; 全量 suite |  |
| `B2-G0:scripts/{labels/risk_flags.py,labels/build_labels.py,lib/receipt_kernel.py}; scripts/tests/test_batch2_p3_hardening.py` | `INV-05, INV-15` | `R8-04` 附注；`R7-14, R8-10` secondary 加固 | 拒绝 producer 中间 symlink；规范零宽/不可见边界空白，拒绝非字符串，OB-2 复用 canonical merge | `B2-P3-RK-01`; `B2-P3-RF-01/02`; 批一 RF/RK 回归 |  |
| `B2-G1:scripts/lib/chain_registry.py; scripts/{evm/accounting_gate.py,evm/verify_recon.py,lib/supply_truth_gate.py,lib/time_spotcheck.py}; 其余 6 个 RPC CLI choices` | `INV-11` | `R7-07, R8-02` | 以不可变 release tier+可执行能力事实取代手工 formal 开关；10 个 choices 从矩阵派生且保持 attestation | `B2-CAP-01`～`B2-CAP-04`; `test_batch2_capability_matrix.py`; `test_batch1_rpc_attestation.py` |  |
| `B2-G1:scripts/tests/{test_batch2_capability_matrix.py,test_chain_registry.py,test_chain_support_matrix.py,test_r7_findings.py}` | `INV-11` | `R7-07, R8-02` | 固化手工开关灭迹、逐能力缺项关闭、批三前全链 not-ready 与 registry/CLI/handoff/release 对表 | `B2-CAP-01`～`B2-CAP-04`; R7 15/15 |  |
| `B2-G2:scripts/report/{handoff_manifest.py,audit_release_gate.py,shared_release_receipt.py}; scripts/tests/{formal_ready_test_harness.py,test_handoff_manifest.py,test_batch2_ready_reconciliation.py,test_adjudication_validator.py,test_audit_release_gate.py,test_a4_gate.py,test_review_20260804_p105.py,test_review_20260804_p106.py,test_round4_a5_seal.py}` | `INV-12` | `R8-06`; 同族 `R7-08`; secondary `R7-07` | READY 无条件纳入 reconciliation，深验 wrapper target/current runner/四个 current producer/四回执语义与哈希；测试专用纵切片复制保留正式正例，生产无 bypass | `B2-REC-01`～`B2-REC-04`; 缺 wrapper 及跨链复用负例；65 项 handoff 契约 |  |
| `B2-G3:scripts/tests/test_batch2_robinhood_exploration.py; SKILL.md; references/{data-pipeline-robinhood*.md,analyze-workflow.md,labels/README.md,labels/MAINTENANCE.md}; maintenance/repair-20260806/robinhood-impact.md` | `INV-11, INV-20` | `R8-02, R7-07`; `RH-EX-01, RH-EX-02`; secondary `full-F-04` / INV-18 | Robinhood 降为 exploration，切断 READY/A4/A5/build/audit/旧 seal 回流；同步现役入口口径和 16 文件实数 | `B2-RH-01`; 豁免失效哨兵；`B2-DOC-RH-COUNT`; docs lint |  |
| `B2-G4:scripts/tests/run_all.py; maintenance/repair-20260806/{ledger.md,diff-finding-map.md,batch2-report.md}` | `INV-05, INV-11, INV-12, INV-15, INV-20` | 批二上述 findings/豁免 | 挂载新测试、登记先红后绿与分组 owner，供 Fable 分组代 commit | 74 项全量 suite；未映射 hunk=0 待复核 |  |

## 分组 → commit SHA 对照（Fable 代 commit 后回填）

| 分组 | commit SHA | 说明 |
|---|---|---|
| `B1-G1` | `8150385` | kernel+两测试文件；test_r7_findings/test_sixlens_receipts 的临时根解析 hunk 因文件级暂存并入 `5801350`（该 commit 信息已注记） |
| `B1-G2` | `5801350` | net.py+10 调用点+RPC 测试 |
| `B1-G3` | `38bc632` | risk_flags parser+五消费者 |
| `B1-G4`（跨组维护件） | `8e9de5c` | run_all/invariant_manifest/transport-injections/maintenance 台账 |
| `B2-G0` | `8f3600c` | 批一 P3 收尾 |
| `B2-G1` | `f6844bf` | 不可变能力矩阵 + CLI choices |
| `B2-G2` | `2a9d5ed` | READY reconciliation 与下游派生（含 formal_ready_test_harness） |
| `B2-G3` | `5ef3186` | Robinhood exploration 防回流 + 文档 |
| `B2-G4` | `07fab90` | suite/台账/报告维护件 |

## 未映射 hunk 计数

- 准备阶段：`0`（本阶段没有生产/测试 hunk）。
- 批一（`66d7ba7..e657732`）：`0`（全部 hunk 归属四组；opus 批内审查独立复算=0）。
- 批二（`553806b..07fab90`）：`0` 候选（所有 hunk 已归属 `B2-G0`～`B2-G4`；待批内审查独立复算）。
