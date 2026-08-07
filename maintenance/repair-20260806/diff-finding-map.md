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
| `B2-G0:scripts/{labels/risk_flags.py,labels/build_labels.py,lib/receipt_kernel.py}; scripts/tests/test_batch2_p3_hardening.py` | `INV-05, INV-15`; secondary `INV-11` | `R8-04` 附注；`R7-14, R8-10` secondary 加固 | 拒绝 producer 中间 symlink；规范零宽/不可见边界空白，拒绝非字符串；OB-2 复用 canonical merge；`build_labels.py` `BUILD_CHAINS` 注释的 owner 归属能力矩阵 | `B2-P3-RK-01`; `B2-P3-RF-01/02`; 批一 RF/RK 回归 |  |
| `B2-G1:scripts/lib/chain_registry.py; scripts/{evm/accounting_gate.py,evm/verify_recon.py,lib/supply_truth_gate.py,lib/time_spotcheck.py}; 其余 6 个 RPC CLI choices` | `INV-11` | `R7-07, R8-02` | 以不可变 release tier+可执行能力事实取代手工 formal 开关；10 个 choices 从矩阵派生且保持 attestation | `B2-CAP-01`～`B2-CAP-04`; `test_batch2_capability_matrix.py`; `test_batch1_rpc_attestation.py` |  |
| `B2-G1:scripts/tests/{test_batch2_capability_matrix.py,test_chain_registry.py,test_chain_support_matrix.py,test_r7_findings.py}` | `INV-11` | `R7-07, R8-02` | 固化手工开关灭迹、逐能力缺项关闭、批三前全链 not-ready 与 registry/CLI/handoff/release 对表 | `B2-CAP-01`～`B2-CAP-04`; R7 15/15 |  |
| `B2-G2:scripts/report/{handoff_manifest.py,audit_release_gate.py,shared_release_receipt.py}; scripts/tests/{formal_ready_test_harness.py,test_handoff_manifest.py,test_batch2_ready_reconciliation.py,test_adjudication_validator.py,test_audit_release_gate.py,test_a4_gate.py,test_review_20260804_p105.py,test_review_20260804_p106.py,test_round4_a5_seal.py}` | `INV-12` | `R8-06`; 同族 `R7-08`; secondary `R7-07` | READY 无条件纳入 reconciliation，深验 wrapper target/current runner/四个 current producer/四回执语义与哈希；测试专用纵切片复制保留正式正例，生产无 bypass | `B2-REC-01`～`B2-REC-04`; 缺 wrapper 及跨链复用负例；65 项 handoff 契约 |  |
| `B2-G3:scripts/tests/test_batch2_robinhood_exploration.py; SKILL.md; references/{data-pipeline-robinhood*.md,analyze-workflow.md,labels/README.md,labels/MAINTENANCE.md}; maintenance/repair-20260806/robinhood-impact.md` | `INV-11, INV-20` | `R8-02, R7-07`; `RH-EX-01, RH-EX-02`; secondary `full-F-04` / INV-18 | Robinhood 降为 exploration，切断 READY/A4/A5/build/audit/旧 seal 回流；同步现役入口口径和 16 文件实数 | `B2-RH-01`; 豁免失效哨兵；`B2-DOC-RH-COUNT`; docs lint |  |
| `B2-G4:scripts/tests/run_all.py; maintenance/repair-20260806/{ledger.md,diff-finding-map.md,batch2-report.md}` | `INV-05, INV-11, INV-12, INV-15, INV-20` | 批二上述 findings/豁免 | 挂载新测试、登记先红后绿与分组 owner，供 Fable 分组代 commit | 74 项全量 suite；未映射 hunk=0 待复核 |  |
| `B2F-G1:scripts/report/{handoff_manifest.py,audit_release_gate.py}; scripts/tests/test_batch2_legacy_hardening.py` | `INV-12`; secondary `INV-20` | `B2R-01, OB-A`; 同族 `R8-06, R8-02` | legacy 只豁免缺席的批二新件；案内 scope/tier 必验，在场 reconciliation 深验并绑定；audit release 真实消费 legacy receipt 阻断新正式报告 | `B2F-LG-01`～`B2F-LG-04`; OB-A 消费点；handoff 65 项 |  |
| `B2F-G2:scripts/lib/chain_registry.py; scripts/tests/{formal_ready_test_harness.py,test_batch2_capability_matrix.py,test_chain_registry.py,test_audit_release_gate.py,test_round4_a5_seal.py,test_batch2_registry_harness_hardening.py}` | `INV-11`; secondary `INV-12` | `B2R-02, B2R-03, B2R-04` | readiness 公开 API 只接受链名；测试矩阵三层只读、作用域内激活且 finally 恢复；子进程默认禁字节码 | 伪造 Mapping 拒绝；字母序 import 无泄漏；三层赋值均 `TypeError`; `B2F-G2` 回归 |  |
| `B2F-G3:scripts/tests/run_all.py; maintenance/repair-20260806/{diff-finding-map.md,batch2-report.md,reviews/batch2-review.md}` | `INV-11, INV-12` | `B2R-05, OB-D`; 记录 `OB-B, OB-C` | 回填 owner/批二区间，修正 harness 不实表述，登记批内消化红绿证据、分组和全量门禁 | 76/76 PASS；无 `.pyc`/`__pycache__` |  |
| `B2F2-G1:scripts/report/handoff_manifest.py; scripts/tests/test_batch2_legacy_hardening.py; maintenance/repair-20260806/{diff-finding-map.md,batch2-report.md}` | `INV-12, INV-11` | owner `B2FR-01, B2FR-02, B2FR-03, B2FR-04` | legacy wrapper 在场判据改为清单或磁盘；generate 单链去重规范化；补列审查报告并统一区间 tip 规则 | `B2F-LG-05`; `bsc,bsc` generate→verify；76 项全量 suite |  |
| `B3-G1:scripts/{evm/accounting_gate.py,lib/time_spotcheck.py,report/holder_distribution_scan.py,lib/chain_registry.py}; scripts/tests/test_batch3_evm_vertical_slice.py` | `INV-06, INV-07, INV-11, INV-12` | `R8-07, R8-08, R8-09, R7-13, R8-06`; 纵切片承接 `full-F-01, six-F-03, R7-01` | eth/bsc/base 真实 accounting+四 producer runner+consumer+READY+release；plan/final-block 精确绑定；错链业务 RPC=0；能力闭合后 readiness 派生为真 | `B3-TIME-01/02`; `B3-EVM-E2E-ETH/BSC/BASE`; `B3-EVM-WRONG-ETH/BSC/BASE` |  |
| `B3-G2:scripts/lib/{receipt_kernel.py,supply_truth_gate.py}; scripts/report/{reconciliation_report.py,shared_release_receipt.py}; scripts/solana/{accounting_gate_sol.py,anchor_sampler.py,scan_token_accounts.py,window_fetch.py}` | `INV-05, INV-08, INV-09, INV-10, INV-12` | `R7-03, R7-05, R7-06, R8-01, R8-03, R8-11, R8-12`; secondary `full-C-02/full-C-03` | 冻结 slot 单源；supply current envelope/runner 可执行；anchor/window data+receipt 联合事务；timestamp/alias/None target fail-closed；Solana target canonical 深验 | `B3-SOL-PROD-01`～`06`; `B3-SOL-E2E` |  |
| `B3-G3:scripts/tests/{test_batch3_solana_producers.py,test_batch3_solana_vertical_slice.py,test_time_spotcheck.py,test_batch1_rpc_attestation.py,test_r7_findings.py,test_sixlens_receipts.py,test_round4_identity_emitter.py,test_batch2_capability_matrix.py,test_batch2_registry_harness_hardening.py,test_chain_registry.py,test_chain_support_matrix.py,formal_ready_test_harness.py,test_handoff_manifest.py,invariant_manifest.json,run_all.py}` | `INV-01, INV-05, INV-06, INV-07, INV-08, INV-09, INV-10, INV-11, INV-12` | 批三上述 findings | 挂载四链真实纵切片、生产者反例和历史 fixture 兼容；同步静态 schema 调用图与 harness 当前口径 | 全量 suite；`invariant_scan.py` |  |
| `B3-G4:maintenance/repair-20260806/{ledger.md,diff-finding-map.md,transport-injections.json,batch3-report.md}` | `INV-01, INV-05, INV-06, INV-07, INV-08, INV-09, INV-10, INV-11, INV-12` | 批三上述 findings | 登记纵切片证据、transport-only fake 注入、红绿与逻辑分组 | `B3-EVM-*`; `B3-SOL-*`; 全量 suite |  |
| `B3F-G1:scripts/solana/{window_fetch.py,anchor_sampler.py}; scripts/tests/test_batch3_solana_producers.py` | `INV-05`; secondary `INV-03, INV-04` | owner `B3R-01`; 同族 `R8-12, R7-03, R7-06`；物理兼含 `B3R-02` 的 window_fetch timestamps hunk 与 `B3F-TS-01` 反例（语义 owner 见 B3F-G2 行） | 提交后独立自检失败先撤 canonical PASS receipt，再把 data 移出正式位；删除 window 恒假回滚状态 | `B3F-TXN-01/02`; `B3F-TS-01` |  |
| `B3F-G2:scripts/tests/{test_sixlens_receipts.py,test_r7_findings.py}` | `INV-09`; secondary `INV-05` | owner `B3R-02`; 同族 `R8-11`；其生产侧 hunk（window_fetch 删 2 元组分支+timestamps 闭环）与 `B3F-TS-01` 反例因文件级 commit 物理落于 `B3F-G1`=`75d112f`，本行为语义 owner | 历史 mock 改为生产 3 元组契约（B3R-02 测试面）；生产侧改动见 B3F-G1 注 | `B3F-TS-01`; six-lens/R7 回归 |  |
| `B3F-G3:maintenance/repair-20260806/{diff-finding-map.md,batch3-report.md,transport-injections.json,ledger.md}` | `INV-05, INV-07, INV-09, INV-17` | owner `B3R-03, OB-H, OB-I, OB-J`; batch4 `B3R-Q1` | 修正 B3-G3 文件 owner；如实记录 resume 权衡、错链证据边界与 `/query` 计数盲区；登记批四双条件纵切片守卫 | 台账对表；JSON parse；全量 suite |  |
| `B4-G1:scripts/tests/{invariant_scan.py,invariant_manifest.json,test_batch4_invariant_guards.py,run_all.py}` | `INV-17`; secondary `INV-07, INV-11, INV-15, INV-18` | `R8-05`; `B1R-01, OB-B, B3R-Q1`; secondary `full-F-04` | 以能力矩阵+producer registry 闭合 formal 分母；覆盖 urllib/httpx/变量 curl；阻断裸池、labels 双向漂移、纵切片脱挂、分母缩减与 RH 数字漂移 | `B4-RPC-01`; `B4-LABEL-01/02`; `B4-VS-01/02`; `B4-INV17-01/02`; `B4-RH-COUNT-01` |  |
| `B4-G2:references/maintenance-review-repair.md` | `INV-18, INV-19` | 批四方法论写回；承接历轮新引入/半修残留 | 只追加闭环章节，固化分层收口、三循环止损、批内节拍、map 三通例、攻击式验收和 transport-only fake 五字段 | `docs_lint.py --all`; 内容逐项对表 |  |
| `B4-G3:maintenance/repair-20260806/{ledger.md,diff-finding-map.md,batch4-report.md}` | `INV-17, INV-18, INV-19` | `R8-05, full-F-04`; 18 项 baseline-fixed finding 证据补齐；六 producer 判定 | 登记红绿、fixture 零过时审计、发布路径可达性、逻辑分组和剩余主账证据 | fixture rg/契约测试；全量 suite |  |
| `B4F-G1:scripts/tests/{invariant_scan.py,test_batch4_invariant_guards.py}; maintenance/repair-20260806/{batch4-report.md,diff-finding-map.md}; references/maintenance-review-repair.md` | `INV-17, INV-19`; secondary `INV-15` | owner `B4R-01, B4R-02, OB-K, OB-L` | 补齐 labels 第八资产面；派生源失配改为明确 scanner 诊断；收窄裸池威胁模型并要求注入自证命中目标分支 | `B4F-LABEL-03`; `B4F-FORMAL-01`; 全量 suite |  |

## R9 批一：公共原语和真实边界

| commit/hunk | primary invariant | finding 列表或配套任务 | 修改目的 | 测试/纵切片/守卫 | 审查结论 |
|---|---|---|---|---|---|
| `R9-B1-G1:scripts/tests/test_r9_batch1_boundaries.py`（同文件多 owner） | `INV-10`（anchor hunk）；`INV-03`（pool/scan hunk） | `R9-02, R9-03, R9-04` | 在未修基线用真实 subprocess 同时抓 producer/consumer 断契约、进程 rc=0 与旧 canonical/marker | `B1-R9-02-PRODUCER-CONSUMER`; `B1-R9-03-PROCESS/STALE`; `B1-R9-04-PROCESS/MARKER` |  |
| `R9-B1-G1/G5:scripts/tests/run_all.py` | `INV-03, INV-10, INV-11` | `R9-02, R9-03, R9-04`; `R9-05` 批一原语；`T2,T5,T6` | 挂载 R9 进程边界与 Solana session 测试；同文件两个新增行分别归 G1/G5 | 全量 suite |  |
| `R9-B1-G2:scripts/evm/fetch_pool_swaps.py` | `INV-03`; secondary `INV-04, INV-06` | `R9-03`; `T2,T3` | 传播 main 返回码；启动即隔离旧 CSV，失败无 current canonical，成功原子发布 | `B1-R9-03-PROCESS/STALE`; `test_fetch_failclosed.py` |  |
| `R9-B1-G2:scripts/solana/scan_token_accounts.py` 的 `__main__` hunk | `INV-03` | `R9-04`; `T2` | 让四个显式 return 进入真实进程退出码 | `B1-R9-04-PROCESS/MARKER` 四 return 分支 |  |
| `R9-B1-G2:scripts/{evm/accounting_gate.py,report/entity_identity_gate.py,evm/cadence_fingerprint.py,bench/golden_baseline.py}` | `INV-03` | `T2` CLI 同族闭合 | 裁定的正式 producer/gate 入口统一 `raise SystemExit(main())` | 六文件裸调用 rg=0；受影响 suite |  |
| `R9-B1-G3:scripts/solana/scan_token_accounts.py` 的 quarantine hunk | `INV-03`; secondary `INV-04, INV-10` | `R9-04`; `T4` | marker 先失效、data 后失效；新 data 先发布、receipt marker 最后发布 | `B1-R9-04-PROCESS/MARKER`; `test_batch3_solana_producers.py` |  |
| `R9-B1-G4:scripts/lib/{anchor_plan.py,time_spotcheck.py}` | `INV-10`; secondary `INV-06, INV-08` | `R9-02`; `T5` | 真实 producer 生成 v2 plan+receipt，绑定 final block/输入/producer/output；consumer 独立验 receipt 后消费 | `B1-R9-02-PRODUCER-CONSUMER`; `test_time_spotcheck.py` |  |
| `R9-B1-G4:scripts/tests/{test_batch3_evm_vertical_slice.py,test_time_spotcheck.py,test_r9_batch1_boundaries.py,test_r7_findings.py,test_batch1_rpc_attestation.py}` 的 anchor hunk | `INV-10`; secondary `INV-06, INV-08` | `R9-02`; `T5` | EVM 正例与既有错链回归现场运行 anchor producer；补越界、篡改、缺 receipt 与 producer→consumer 反例，防 receipt 前置门制造假绿 | `B3-EVM-E2E-ETH/BSC/BASE`; time 契约 8 项；R7/RPC 回归 |  |
| `R9-B1-G5:scripts/lib/solana_attested_session.py; scripts/tests/test_r9_solana_attested_session.py` | `INV-11`; secondary `INV-02, INV-08` | `R9-05` 批一部分；`T6` | 建立每 endpoint 首次业务前 genesis attestation 与 failover 重验原语；本批不接 callsite | 错 genesis 业务=0；failover 重验；5/5 |  |
| `R9-B1-G6:maintenance/repair-20260806/{ledger.md,invariant-merge.md,diff-finding-map.md,b1_progress.md}; references/maintenance-review-repair.md` | `INV-18, INV-19` | `T1`; `R9-01`～`R9-05` 归因/归并/覆盖登记 | 49 项主账、primary INV、唯一覆盖类别、严格三分类与本批逐组证据/owner 单源落盘 | 表计数/ID/未映射 hunk 自查；docs lint |  |
| `R9-B1-G7:scripts/tests/invariant_manifest.json; maintenance/repair-20260806/{diff-finding-map.md,b1_progress.md}` | `INV-17`; secondary `INV-03, INV-10, INV-11` | `T2,T5,T6`; `R9-02`～`R9-05` | 将 anchor producer/time consumer、Solana urllib transport 和两个 quarantine locator 纳入既有机器 census；同步最低分母 | `invariant_scan.py`; `--self-test`; 全量 suite |  |

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
| `B2F-G1` | `138b707` | legacy 旁路补闸(B2R-01+OB-A)+B2F-LG-01~04 |
| `B2F-G2` | `ee7d4d5` | registry API 收严+harness 可逆化(B2R-02/03/04) |
| `B2F-G3` | `af92a91` | 批内消化台账/门禁+opus 批二审查报告入库 |
| `B2F2-G1` | `9609655` | 消化第二轮(B2FR-01~04):伪缺席补闸+generate 规范化+台账修正 |
| `B3-G1` | `4ac3d04` | EVM 正式链纵切片 + final-block/readiness |
| `B3-G2` | `d2e9409` | Solana producer envelope/txn/slot/timestamp + 纵切片 |
| `B3-G3` | `73113ba` | 批三测试、兼容 fixture 与静态 manifest |
| `B3-G4` | `5c41f05` | 批三台账、transport 注入与施工报告 |
| `B3F-G1` | `75d112f` | B3R-01 提交后自检失败真实撤回 |
| `B3F-G2` | `7c04b72` | B3R-02 timestamps 证据闭环与测试契约收口 |
| `B3F-G3` | `a85974d` | B3R-03 与 OB-H/I/J 台账 |
| `B4-G1` | `ba6b98e` | scanner 分母与三条自动守卫 |
| `B4-G2` | `1850205` | 维护方法论追加章节 |
| `B4-G3` | `1e3d5a6` | ledger/map/fixture 与路径判定报告 |
| `B4F-G1` | `13d76c0` | 批四消化：labels 第八面+派生源诊断+措辞收窄+方法论补条 |

## 未映射 hunk 计数

- 准备阶段：`0`（本阶段没有生产/测试 hunk）。
- 批一（`66d7ba7..e657732`）：`0`（全部 hunk 归属四组；opus 批内审查独立复算=0）。
- 批二（`553806b..5924cd5`）：`0` 候选（所有 hunk 已归属 `B2-G0`～`B2-G4`；批内审查回填 commit 已包含）。
- 批二批内消化（`5924cd5..3ca824e`）：`0` 候选（所有新 hunk 已归属 `B2F-G1`～`B2F-G3`；增量重审独立复算=0，文档漏列项已由 B2F2-G1 修正）。
- 批二批内消化第二轮（`3ca824e..` 至本回填 commit 即候选 tip，含 `B2F2-G1`=`9609655` 与本表自身回填）：`0` 候选（全部 hunk 归属 `B2F2-G1`；回填 commit 按通例自指式计入）。
- 批三（`62efbf9..3df1234`，含 `B3-G1`=`4ac3d04`/`B3-G2`=`d2e9409`/`B3-G3`=`73113ba`/`B3-G4`=`5c41f05` 与本表自身回填 `3df1234`）：`0` 候选（批内审查独立复算=0，B3-G3 行多列项已由 B3F-G3 修正）。
- 批三批内消化（`3df1234..` 至本回填 commit 即候选 tip，含 `B3F-G1`=`75d112f`/`B3F-G2`=`7c04b72`/`B3F-G3`=`a85974d` 与本表自身回填）：`0` 候选（全部 hunk 归属 `B3F-G1`～`B3F-G3`；回填 commit 按通例自指式计入；待增量重审独立复算）。

- 批四（`f2a6e41..6b7ab8d`，含 `B4-G1`=`ba6b98e`/`B4-G2`=`1850205`/`B4-G3`=`1e3d5a6` 与本表自身回填 `6b7ab8d`）：`0` 候选（批内审查独立复算=0，清单与 commit 边界逐文件吻合）。
- 批四批内消化（`6b7ab8d..` 至本回填 commit 即候选 tip，含 `B4F-G1`=`13d76c0` 与本表自身回填）：`0` 候选（全部 hunk 归属 `B4F-G1`；回填 commit 按通例自指式计入；待重审独立复算）。
- R9 批一（冻结基线 `63cf715` 至当前 worktree，禁止 git 写操作，尚无施工 commit）：`0` 候选（22 个改动/新增文件全部归属 `R9-B1-G1`～`R9-B1-G7`；多 owner 文件已按 hunk 显式拆分，本表和进度账按自指式维护件计入 `T1`）。

通例：区间末端恒取候选 tip；自指式 SHA 回填 commit 计入本区间。map 行文件清单以 Fable 实际 commit 分组为准；一文件含多 owner 的 hunk 时（文件级 commit 无法拆分），物理归属行与语义 owner 行互相注明，Fable 回填 SHA 时校正清单。
