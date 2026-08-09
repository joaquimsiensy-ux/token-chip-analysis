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
| `B1F-G1:scripts/lib/time_spotcheck.py; scripts/tests/test_time_spotcheck.py; maintenance/repair-20260806/b1_progress.md` 的 G1 消化 hunk | `INV-10`; secondary `INV-02` | owner `B1R-01` | consumer 固定绑定 `scripts/lib/anchor_plan.py`，伪造仓库 Markdown producer 在 dry-run/正式路径均于 RPC 前拒绝 | `test_time_spotcheck.py` 10 项；eth/bsc/base 纵切片 |  |
| `B1F-G2:scripts/lib/{artifact_quarantine.py,anchor_plan.py}; scripts/{evm/fetch_pool_swaps.py,solana/scan_token_accounts.py}; scripts/tests/{test_r9_batch1_boundaries.py,invariant_manifest.json}; maintenance/repair-20260806/b1_progress.md` 的 G2 消化 hunk | `INV-03`; secondary `INV-04, INV-17` | owner `B1R-02` | pool/scan/anchor 共用唯一启动隔离原语；anchor 先隔离 receipt 再隔离 plan，失败无 current 可消费对；同步 atomic locator | R9 边界 3/3；fetch failclosed；Solana producer；`invariant_scan.py --self-test` |  |
| `B1F-G3:scripts/lib/solana_attested_session.py; scripts/tests/test_r9_solana_attested_session.py; maintenance/repair-20260806/b1_progress.md` 的 G3 消化 hunk | `INV-11`; secondary `INV-02, INV-08` | owner `B1R-03` | 删除调用方 `expected_genesis` 覆盖口，信任根只取 mainnet 库常量，docstring 与唯一 transport 注入边界对齐 | 原 5 条 transport 反例+构造口 TypeError，6/6 |  |
| `B1F-G4:maintenance/repair-20260806/{invariant-merge.md,diff-finding-map.md,b1_progress.md}` 的 G4 消化 hunk | `INV-18, INV-19` | owner `B1R-04`; 登记 `B1R-01`～`B1R-03` 消化 owner | 恢复不变量拆分/合并须 Fable 批准且同步 ledger 双台账的治理条文；补齐四组 owner 和消化区间 | 精确 needle 守卫；`docs_lint.py --all`；未映射 hunk=0 |  |
| `B1F2-G1:scripts/lib/{anchor_selection.py,anchor_plan.py,time_spotcheck.py}; scripts/tests/{test_time_spotcheck.py,test_batch3_evm_vertical_slice.py,test_r7_findings.py,test_batch1_rpc_attestation.py,test_r9_batch1_boundaries.py}; maintenance/repair-20260806/b1_progress.md` 的 G1 终修 hunk | `INV-10`; secondary `INV-02, INV-06, INV-08` | owner `B1R-01 REOPEN→终修` | 输入身份与确定性选点核心唯一抽取；plan 补齐重放参数；consumer 在 dry-run/正式路径任何 RPC 前全量重放统计与完整点集合 | 审查 C2/正式 PASS 攻击；五类变形；time 20 项；eth/bsc/base 纵切片；百万行性能 |  |
| `B1F2-G2:scripts/lib/{anchor_selection.py,time_spotcheck.py}; scripts/tests/test_time_spotcheck.py; maintenance/repair-20260806/b1_progress.md` 的 G2 单源 hunk（与 G1 同文件时按语义 owner 拆分） | `INV-10`; secondary `INV-17` | owner `B1R2-02` | `EXPECTED_PLAN_PRODUCER` 只在共享模块赋值，consumer import；契约测试与 invariant manifest 唯一 anchor 登记对账 | baseline 单源断言红；manifest 对账守卫绿；`invariant_scan.py` |  |
| `B1F2-G3:scripts/lib/solana_attested_session.py; maintenance/repair-20260806/{diff-finding-map.md,b1_progress.md}` 的 G3 清理/台账 hunk | `INV-11, INV-19`; secondary `INV-10` | owner `B1R2-01`; 登记 `B1R-01/B1R2-02` 终修 owner | 恢复被无主删除的末尾空行；补 B1F2 三组 owner、空 SHA 与真实未映射 hunk 复算 | 末尾双换行字节断言；docs lint；B1F2 未映射 hunk=0 |  |

## R9 批二：可执行能力矩阵

| commit/hunk | primary invariant | finding 列表或配套任务 | 修改目的 | 测试/纵切片/守卫 | 审查结论 |
|---|---|---|---|---|---|
| `R9-B2-G1:scripts/lib/{attestation_adapters.py,chain_registry.py}; scripts/tests/{test_r9_batch2_attestation_adapters.py,test_batch2_capability_matrix.py,run_all.py}` 的 attestation hunk | `INV-11`; secondary `INV-02, INV-08` | `R9-05`; B2-G1 | `chain_attestation` 键必须 import 到 EVM/Solana 真实 session factory，未知或缺实现不得当能力 | `test_r9_batch2_attestation_adapters.py`; Solana session 6/6 |  |
| `R9-B2-G2:scripts/lib/{formal_capability_probes.py,chain_registry.py}; scripts/tests/{formal_ready_test_harness.py,test_r9_batch2_executable_capabilities.py,test_batch2_capability_matrix.py,test_batch2_registry_harness_hardening.py,test_chain_registry.py,test_chain_support_matrix.py,test_batch3_evm_vertical_slice.py,test_batch3_solana_vertical_slice.py,invariant_scan.py,test_batch4_invariant_guards.py,run_all.py}` 的六探针 hunk | `INV-11`; secondary `INV-12, INV-17` | `R9-05`; B2-G2 | readiness 改为六项真实 callable/test/gate 探针；R9 evidence registry 批二留空，四链只因能力④缺席而自然 not-ready；旧 R8 纵切片仅在测试可恢复 callable 上下文中保留回归作用，不计 R9 证据 | 六项逐一破坏；bool True 伪证据拒绝；`formal_ready_chains()==set()`；invariant scanner；旧 R8 loopback 回归 |  |
| `R9-B2-G3:scripts/lib/solana_sqd_dataset.py; scripts/tests/{test_r9_batch2_solana_sqd_adapter.py,run_all.py}` | `INV-11`; secondary `INV-02, INV-08` | `R9-05`; B2-G3 | 固定 `solana-mainnet + mint + slot range`，以真实 attested RPC genesis/slot 锚定状态；不接业务 callsite | dataset/mint/slot 负例；错 genesis 业务=0；anchor 覆盖区间 |  |
| `R9-B2-G4:SKILL.md; scripts/tests/test_chain_support_matrix.py` 的 frontmatter hunk | `INV-11, INV-20`; secondary `INV-18` | `R9-05`; `RH-EX-01/02`; B2-G4 | SKILL 与六探针矩阵单口径；Robinhood/Arbitrum 保持 exploration；不改 VERSION | chain support/RH/Arbitrum/docs lint；`SKILL.md=7707B` |  |
| `R9-B2-G5:maintenance/repair-20260806/{ledger.md,diff-finding-map.md,b2_progress.md}` | `INV-11, INV-18, INV-19` | `R9-05`; B2-G1～G5 | 登记逐组红绿、owner 与“矩阵层闭合，callsite 留批三”的未完全销账状态 | 受影响测试；全量 suite；未映射 hunk=0 |  |

## R9 批三：正式纵切片与 Solana 精确快照

| commit/hunk | primary invariant | finding 列表或配套任务 | 修改目的 | 测试/纵切片/守卫 | 审查结论 |
|---|---|---|---|---|---|
| `R9-B3-G1:scripts/lib/solana_observation.py; scripts/tests/test_r9_batch3_solana_observation.py` 的 observation/activity hunk | `INV-08`; secondary `INV-02, INV-11` | `R9-01`; B3-G1/G4 九负例 | 以 attested session 实现前观测→GPA canonical slot→后观测→活动验证→supply 交叉→三方闭合；声明 slot 只作断言；完整/轻量预算 fail-closed | 错 genesis 业务=0；77≠103；前后变化；分页中断；双模式 writable；supply 过早；三方不闭合；RPC 预算 |  |
| `R9-B3-G2:scripts/solana/{scan_token_accounts.py,accounting_gate_sol.py,anchor_sampler.py,window_fetch.py}; scripts/lib/supply_truth_gate.py; scripts/report/{reconciliation_report.py,shared_release_receipt.py}; scripts/tests/{test_r9_batch3_dynamic_runner.py,test_batch3_solana_producers.py,test_r7_findings.py,test_round4_identity_emitter.py}` | `INV-05, INV-08, INV-10, INV-12`; secondary `INV-01, INV-03, INV-04` | `R9-01`; `R8-04, R8-12`; `R7-03, R7-05, R7-06, R8-01, R8-03` | scan 生产 bundle+snapshot 联合发布；accounting/supply truth 绑定同 bundle；runner 从 supply 观测 slot 动态派生；anchor/window 以 txn 作最后可失败操作 | stale marker 隔离；三 consumer slot/bundle 绑定；动态 runner；提交后自检红例 |  |
| `R9-B3-G3:scripts/lib/formal_capability_probes.py; scripts/tests/{test_batch3_evm_vertical_slice.py,test_r9_batch2_executable_capabilities.py,formal_ready_test_harness.py,test_batch2_capability_matrix.py,test_batch2_registry_harness_hardening.py,test_chain_registry.py,test_chain_support_matrix.py}` 的 EVM/target hunk | `INV-11`; secondary `INV-06, INV-07, INV-10, INV-12, INV-17` | `R9-05`; `R9-02`; eth/bsc/base 纵切片 | 注册三链真实 callable；每链现场 anchor plan、错链零业务、runner→READY→release；删 target 或摘 SUITE 即掉 ready | time_spotcheck 20 项；target 删除回归；loopback E2E 待允许 bind 环境复跑 |  |
| `R9-B3-G4:scripts/solana/fetch_sqd_transfers_v2.py; scripts/tests/{test_batch3_solana_vertical_slice.py,test_r9_batch3_solana_observation.py}; maintenance/repair-20260806/transport-injections.json` | `INV-11`; secondary `INV-02, INV-08, INV-17` | `R9-05`; Solana PYTHIA 纵切片；SQD 负例⑨ | transport fake 增加 genesis、单调 slot、双模式活动、mint/GPA/supply；SQD dataset/mint/range 进入真实消费路径 | 九负例；SQD scope；Solana loopback E2E 待允许 bind 环境复跑 |  |
| `R9-B3-G5:maintenance/repair-20260806/g3_preflight/{g3_0a_usdc_activity.py,g3_0b_pythia_gpa.py}; scripts/tests/test_r9_batch3_preflight.py` | `INV-08, INV-11` | G3-0 双载体 | 两壳直接 import G1 生产活动/完整 observation；逐 endpoint 成本、字节、耗时、429 如实登记；USDC 禁 GPA | 两壳 `--help` 独立启动；fake transport 各一绿例 |  |
| `R9-B3-G6:maintenance/repair-20260806/b3_progress.md` 的裁判执行手册 hunk | `INV-08, INV-18` | `R9-01`; G3-0/mainnet smoke 待登记 | 固化 Helius key-file 拼接、同 bundle 三 consumer 命令、代理边界与 PASS 判据，不在无网沙箱伪跑 | 裁判 G3-0a/G3-0b/PYTHIA smoke 待回填 |  |
| `R9-B3-G7:SKILL.md; scripts/tests/{run_all.py,invariant_scan.py,invariant_manifest.json,test_chain_support_matrix.py}; maintenance/repair-20260806/{ledger.md,diff-finding-map.md,b3_progress.md,transport-injections.json}` 的治理/门禁 hunk | `INV-17, INV-18, INV-19, INV-20`; secondary `INV-11` | `R9-01, R9-05`; B3-G1～G7 | 同步四链 ready 口径、transport/receipt/entrypoint census、逐组红绿、裁判待跑位与未映射 hunk | docs lint；SKILL 字节闸；invariant scan；全量 85/87，唯二 EPERM bind |  |

## R9 批三批内修复循环 1

| commit/hunk | primary invariant | finding 列表或配套任务 | 修改目的 | 测试/纵切片/守卫 | 审查结论 |
|---|---|---|---|---|---|
| `B3F2-G1:scripts/lib/{endpoint_identity.py,solana_attested_session.py,solana_observation.py,net.py}; scripts/solana/{accounting_gate_sol.py,anchor_sampler.py}; maintenance/repair-20260806/g3_preflight/g3_0a_usdc_activity.py; scripts/tests/{test_r9_solana_attested_session.py,test_batch1_rpc_attestation.py,test_r9_batch3_solana_observation.py,test_r9_batch3_preflight.py,test_sixlens_receipts.py}` | `INV-11`; secondary `INV-02, INV-08` | `B3FIX-01` P2、`B3FIX-02` P1；源头 R9-05 | certifi CA context 构造一次复用且可选依赖缺失回退；endpoint 日志/异常/receipt/行身份统一 public origin；G3-0 成本壳不再旁路生产 urllib transport | certifi 有/无与 context 复用；transport/RPC/attestation/exhausted 四型密钥负例；preflight/scan/anchor 持久化负例；EVM 同族回归 |  |
| `B3F2-G2:maintenance/repair-20260806/{g3_preflight/g3_0a_usdc_activity.json(删除),b3_progress.md,ledger.md,diff-finding-map.md}` | `INV-18, INV-19`; secondary `INV-11` | 批内修复循环 1 止损与污染清理 | 删除裁判首跑含 key 报告且不留副本；如实登记第一循环、红绿与裁判重跑位 | 文件不存在断言；docs lint；全量 suite |  |

## R9 批三批内修复循环 2

| commit/hunk | primary invariant | finding 列表或配套任务 | 修改目的 | 测试/纵切片/守卫 | 审查结论 |
|---|---|---|---|---|---|
| `B3F3-G1:scripts/lib/{endpoint_identity.py,solana_observation.py}; scripts/evm/accounting_gate.py; scripts/solana/{decode_txs_v2.py,fetch_sqd_transfers_v2.py}; scripts/tests/{invariant_manifest.json,test_r9_solana_attested_session.py,test_batch1_rpc_attestation.py,test_review_solana_integrity.py,test_review_resume_integrity.py,test_r9_batch3_solana_observation.py}` | `INV-11`; secondary `INV-02, INV-05` | `B3R9-01` | path/query/userinfo/fragment 密钥统一脱敏且普通正文不被 query key 腐蚀；持久化 endpoint 身份只存 public origin+不可逆 digest | Alchemy/Infura/无 scheme/path token；EVM+Solana 异常链；accounting/decode/SQD receipt/cache metadata；legacy meta 原子清洗登记 |  |
| `B3F3-G2:scripts/lib/solana_observation.py; scripts/solana/scan_token_accounts.py; scripts/tests/test_r9_batch3_solana_observation.py` | `INV-08`; secondary `INV-02, INV-11` | `B3R9-02, B3R9-09, B3R9-13` | producer 发布前运行共享对象 validator；修降级样本、pre/parsed/GPA 下限与 supply retry 分类 | 两条正式位假成功红；validator 注入；min slot；retry attempt=2 |  |
| `B3F3-G3:scripts/tests/{test_r9_batch3_release_guards.py,run_all.py}` | `INV-12`; secondary `INV-08, INV-17` | `B3R9-03` | 六条 Solana 发布断言各有独立负例且挂全量 SUITE | 六负例；D1～D4 临时 mutant 均红 |  |
| `B3F3-G4:scripts/tests/{test_r9_batch2_executable_capabilities.py,test_r9_batch3_solana_observation.py,test_batch2_registry_harness_hardening.py,test_r7_findings.py}` | `INV-11, INV-17`; secondary `INV-08` | `B3R9-04, B3R9-05, B3R9-06` | 消除同名影子 target；恢复 harness 可逆/不泄漏判别力；slot 改精确断言 | AST shadow 红；H1/H2/R1 mutant 红 |  |
| `B3F3-G5:maintenance/repair-20260806/g3_preflight/g3_0b_pythia_gpa.json; maintenance/repair-20260806/g3_preflight/smoke-20260808/accounting_mode.json; maintenance/repair-20260806/g3_preflight/smoke-20260808/solana_observation_bundle.json; maintenance/repair-20260806/g3_preflight/smoke-20260808/supply_truth.json; maintenance/repair-20260806/{ledger.md,diff-finding-map.md,b3_progress.md}; scripts/tests/test_sixlens_docs.py` | `INV-18, INV-19`; secondary `INV-08` | `B3R9-07, B3R9-08` | 给裁判 mainnet 证据建 owner；明确 R9-01 观测闭合不等于 bundle 防伪 | 四文件逐名守卫；R9-01 三条边界 needle；未映射复算 |  |
| `B3F3-G5-cross:scripts/lib/solana_sqd_dataset.py` 的批三 docstring hunk（物理落 `160a852`，批二生产实现语义 owner 仍见 `R9-B2-G3`） | `INV-19`; secondary `INV-11` | `B3R9-07` 跨批注记 | 批三消费接入时对批二 adapter docstring 的修改不再只挂批二 owner | map 双向文本守卫 |  |
| `B3F3-G6:scripts/lib/{solana_observation.py,supply_truth_gate.py,formal_capability_probes.py}; scripts/solana/{accounting_gate_sol.py,scan_token_accounts.py,window_fetch.py,anchor_sampler.py}; scripts/tests/{test_r9_batch3_solana_observation.py,test_batch3_solana_producers.py,test_sixlens_docs.py,formal_ready_test_harness.py}; maintenance/repair-20260806/b3_progress.md` | `INV-02, INV-05, INV-08, INV-18`; secondary `INV-11` | `B3R9-10`～`B3R9-15` | writable 保守判定；零样本诚实措辞；CLI/doc 同步；删死闸；supply retry；txn 失败保留 partial 且提交后清理不反转 PASS | lookup/lying flag/zero sample；doc needles；txn fail/cleanup fail |  |

## R9 批四：防复发守卫与主账收口

| commit/hunk | primary invariant | finding 列表或配套任务 | 修改目的 | 测试/纵切片/守卫 | 审查结论 |
|---|---|---|---|---|---|
| `R9-B4-G1:scripts/tests/{invariant_scan.py,test_batch4_invariant_guards.py}` 的 main-exit AST hunk | `INV-03, INV-17` | R9-03/04 族；G1 | 整数 `main` 在真实入口必须传播给 SystemExit | `R9-B4-MAIN-01` 裸 main 临时样例 |  |
| `R9-B4-G2:scripts/tests/{invariant_scan.py,test_batch4_invariant_guards.py}` 的 formal E2E 调用图 hunk | `INV-01, INV-17` | `B3R9-08`; G2 | 正式 evidence target 必须现场运行 controlled runner+登记 producer，不认手写自报产物 | `R9-B4-E2E-01` 手写 bundle mutant |  |
| `R9-B4-G3:scripts/lib/formal_capability_probes.py; scripts/tests/{test_r9_batch2_executable_capabilities.py,test_batch3_evm_vertical_slice.py,test_batch3_solana_vertical_slice.py,invariant_manifest.json}` | `INV-11`; secondary `INV-17` | B3R9-04 5e/5f；G3 | target decorator 将真实 adapter 错身份零业务探针变成每次 evidence 的前置必经路 | unrelated callable mutant；四链 runtime negative probe |  |
| `R9-B4-G4:scripts/tests/{invariant_scan.py,invariant_manifest.json,test_batch4_invariant_guards.py,test_r9_batch1_boundaries.py}; scripts/lib/anchor_plan.py; scripts/evm/fetch_pool_swaps.py` | `INV-03, INV-04, INV-17` | R9-03/04 stale 族；G4 | 从 accounting/reconciliation registry 派生全部 formal producer，与 standalone stale-sensitive producer 一起逐个登记 canonical/marker/error 角色及保护方式；anchor/pool 失败统一 ERROR side receipt，pool 增 commit marker | `R9-B4-STALE-01/02`；anchor/pool/scan 真子进程 |  |
| `R9-B4-G5:scripts/lib/{anchor_selection.py,anchor_plan.py,time_spotcheck.py}; scripts/tests/{test_time_spotcheck.py,test_r9_batch1_boundaries.py}` | `INV-06, INV-10, INV-18` | `B1R3-01`；四类 fixture 审计；G5 | producer/consumer 共享覆盖下限；批一旧 Solana curl/fixed-77 fake 升级 genesis+单调 urllib transport fake | 1/1 弱 plan 双端红；20 项 spotcheck；scan-only |  |
| `R9-B4-G6:references/maintenance-review-repair.md; maintenance/repair-20260806/{ledger.md,invariant-merge.md,diff-finding-map.md,b4_progress.md}; scripts/tests/test_sixlens_docs.py` | `INV-18, INV-19`; secondary `INV-17` | R9-01～05；49 项主账；G6 | 追加 R9 方法论；主表/详情零空栏；18 baseline-fixed 和 8 supplementary 复核；守卫归并/owner | docs 结构门禁；49 行精确计数；未映射 hunk=0 |  |

## R9 批四批内修复循环 1

| commit/hunk | primary invariant | finding 列表或配套任务 | 修改目的 | 测试/纵切片/守卫 | 审查结论 |
|---|---|---|---|---|---|
| `R9-B4F-G1:scripts/tests/{invariant_scan.py,test_batch4_invariant_guards.py}; maintenance/repair-20260806/b4_progress.md` 的 execution-authenticity hunk | `INV-01, INV-17` | `F-B4-01` | 本地 run wrapper 必须递归可达白名单执行原语，空同名函数不计 formal E2E 证据 | `B4F2-E2E-02`；四链现役 target 零误报 |  |
| `R9-B4F-G2:scripts/tests/{invariant_scan.py,test_batch4_invariant_guards.py}; maintenance/repair-20260806/b4_progress.md` 的 reachable-contract hunk | `INV-03, INV-04, INV-17` | `F-B4-02` | quarantine / ERROR 契约只计静态可达路径，死分支和 return 后代码不计 | `B4F2-STALE-03` |  |
| `R9-B4F-G3:scripts/tests/{invariant_scan.py,test_batch4_invariant_guards.py}; maintenance/repair-20260806/b4_progress.md` 的 top-level-main hunk | `INV-03, INV-17` | `F-B4-03` | 扩展 main 退出传播守卫到模块顶层裸调 | `B4F2-MAIN-02` |  |
| `R9-B4F-G4:scripts/tests/{invariant_scan.py,test_batch4_invariant_guards.py}; maintenance/repair-20260806/b4_progress.md` 的 standalone-denominator hunk | `INV-03, INV-04, INV-17` | `F-B4-04` | 从 standalone 入口可达的成功发布+ERROR receipt 语义自动派生 stale-sensitive producer 分母 | `B4F2-STALE-04` |  |
| `R9-B4F-G5:scripts/evm/fetch_pool_swaps.py; scripts/tests/{test_fetch_failclosed.py,invariant_scan.py,invariant_manifest.json}; maintenance/repair-20260806/{b4_progress.md,diff-finding-map.md}` | `INV-03, INV-05, INV-17, INV-19` | `F-B4-05` | pool CSV+PASS marker 迁入 receipt-kernel 联合事务；发布第二件失败撤回 CSV；补齐 txn atomic census | receipt rename fault injection；fetch failclosed；invariant scan |  |

## R9 批四批内修复循环 2

| commit/hunk | primary invariant | finding 列表或配套任务 | 修改目的 | 测试/纵切片/守卫 | 审查结论 |
|---|---|---|---|---|---|
| `B4F2C2:scripts/tests/{invariant_scan.py,test_batch4_invariant_guards.py}; maintenance/repair-20260806/{b4_progress.md,diff-finding-map.md}` 的 import-binding / local-shadow hunk | `INV-01, INV-17, INV-19` | owner `F-B4-01`（STILL-OPEN 二次消化） | 执行原语必须由真实 import 绑定解析，且调用点直接函数作用域内不得有同名本地重绑；同步诚实静态边界与循环 1 勘误 | `B4F2C2-E2E-04/05/06/07`；M4/M5；四链 ready；全量 suite |  |

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
| `R9-B1-G2/G3` | `85753da` | R9 批一：六入口 SystemExit + pool/scan 启动隔离与 marker 先失效（commit message 前缀作 B1-G2/G3，属 R9 区间） |
| `R9-B1-G5` | `2f197d2` | R9 批一：SolanaAttestedSession 原语+5 反例测试 |
| `R9-B1-G1/G4` | `592b0c2` | R9 批一：anchor-plan/v2 producer/receipt/consumer + 真实 subprocess 边界测试 + run_all 挂载（run_all 的 G5 挂载行物理归此 commit，语义 owner 见上表） |
| `R9-B1-G6/G7` | `35c94eb` | R9 批一：台账 49 项+归因规则回写+invariant census 同步 |
| `B1F-G1` | `fa82b32` | 批一消化：B1R-01 consumer 真实 producer 身份绑定（G1/G2/G3 同 commit） |
| `B1F-G2` | `fa82b32` | 批一消化：B1R-02 公共 quarantine 与 anchor 启动隔离（同上） |
| `B1F-G3` | `fa82b32` | 批一消化：B1R-03 Solana genesis 信任根收紧（同上） |
| `B1F-G4` | `8477e04` | 批一消化：B1R-04 治理条文与 owner/区间回填 |
| `B1F2-G1` | `1a7e685` | 批一消化第二轮：B1R-01 consumer 数学重放终修（G1/G2 同 commit） |
| `B1F2-G2` | `1a7e685` | 批一消化第二轮：B1R2-02 producer 常量单源与 manifest 守卫（同上） |
| `B1F2-G3` | `658f78e` | 批一消化第二轮：B1R2-01 无主空行恢复与台账收口 |
| `R9-B2-G1` | `ae3ff29`(生产)+`3b69e5d`(测试) | 可执行 chain-attestation 适配器键（commit 按生产/测试横切，下同） |
| `R9-B2-G2` | `ae3ff29`(生产)+`3b69e5d`(测试) | 六探针 readiness 与 R9 纵切片证据接口 |
| `R9-B2-G3` | `ae3ff29`(生产)+`3b69e5d`(测试) | Solana SQD dataset scope 适配器 |
| `R9-B2-G4` | `4bc31db`(SKILL)+`3b69e5d`(test_chain_support_matrix) | SKILL 单口径与 exploration 降级保持 |
| `R9-B2-G5` | `cf67cd0` | ledger/map/progress 与全量门禁 |
| `R9-B3-G1` | `160a852` | Solana observation bundle 核心与活动判定 |
| `R9-B3-G2` | `160a852` | 三消费者、动态 runner、producer txn 尾巴 |
| `R9-B3-G3` | `160a852` | EVM 三链纵切片与 evidence targets |
| `R9-B3-G4` | `160a852` | Solana 纵切片 fake 与 SQD callsite |
| `R9-B3-G5` | `160a852` | G3-0 双载体预演壳 |
| `R9-B3-G6` | `160a852` | mainnet smoke 裁判手册 |
| `R9-B3-G7` | `160a852` | 台账、矩阵、门禁与待跑位 |
| `B3F2-G1` | `160a852` | CA context、endpoint public identity 与生产 G3-0 transport 接线 |
| `B3F2-G2` | `160a852` | 污染清理、批内循环 1 台账与门禁 |
| `B3F3-G1` | `c46ef9f` | endpoint path/query 密钥脱敏 |
| `B3F3-G2` | `c46ef9f` | producer-validator 等价与 slot/retry |
| `B3F3-G3` | `c46ef9f` | Solana 发布层六负例 |
| `B3F3-G4` | `c46ef9f` | 测试守卫判别力恢复 |
| `B3F3-G5` | `c46ef9f` | 证据 owner、跨批注记与闭合边界 |
| `B3F3-G6` | `c46ef9f` | P3 writable/措辞/docstring/partial 时序 |
| `R9-B4-G1` | `3b76db8` | main 退出码 AST 守卫 |
| `R9-B4-G2` | `3b76db8` | formal E2E producer/consumer 现场生成守卫 |
| `R9-B4-G3` | `3b76db8` | capability adapter 错身份执行守卫 |
| `R9-B4-G4` | `3b76db8` | stale canonical/marker/error 登记守卫 |
| `R9-B4-G5` | `3b76db8` | fixture 审计与 anchor 弱覆盖下限 |
| `R9-B4-G6` | `3b76db8` | 方法论、49 项主账、归并表与 map 收口 |
| `R9-B4F-G1` | `c121422` | F-B4-01 run 真实性收紧 |
| `R9-B4F-G2` | `c121422` | F-B4-02 failure contract 可达性 |
| `R9-B4F-G3` | `c121422` | F-B4-03 顶层 main 退出传播 |
| `R9-B4F-G4` | `c121422` | F-B4-04 standalone 分母自动派生 |
| `R9-B4F-G5` | `c121422` | F-B4-05 pool 双件事务发布与循环台账 |
| `B4F2C2` | `f6523ef` | F-B4-01 import 真绑定与本地遮蔽终修 |

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
- R9 批一（`63cf715..` 至本回填 commit 即候选 tip，含 `85753da`/`2f197d2`/`592b0c2`/`35c94eb` 与本表自身回填）：`0` 候选（22 个改动/新增文件全部归属 `R9-B1-G1`～`R9-B1-G7`；多 owner 文件已按 hunk 显式拆分；回填 commit 按通例自指式计入；待批内审查独立复算）。
- R9 批一批内消化（`144c652..0bb94ba`，含 `B1F-G1`～`B1F-G4` 与 SHA 回填）：重审独立复算未映射 hunk=`1`，即 `solana_attested_session.py` 末尾空行删除（`B1R2-01`）；原自报 `0` 作废并由 B1F2-G3 恢复。
- R9 批一批内消化第二轮（`0bb94ba..` 至候选 tip，含 `B1F2-G1/G2`=`1a7e685`/`B1F2-G3`=`658f78e` 与本表自身回填）：`0` 候选（全部 hunk 归属三组；回填 commit 按通例自指式计入）。第三轮增量重审（report-recheck2.md）**ALL-CLEAR**：B1R-01 CLOSED、两 P3 CLOSED；新增历史漏检 `B1R3-01`（P3 非阻断，anchor per_cell/edge_max 无下界→弱覆盖 plan，非 B1R-01 未闭合）留批四守卫层处理+最终盲审复验。
- R9 批二（`5b06677..` 至本回填 commit 即候选 tip，含生产 `ae3ff29`/测试 `3b69e5d`/SKILL `4bc31db`/台账 `cf67cd0` 与本表自身回填）：`0` 候选（全部 hunk 归属 `R9-B2-G1`～`R9-B2-G5`；commit 按生产/测试/SKILL/台账横切，各 G 跨 commit 已在 SHA 对照注明；回填 commit 自指式计入；待批内审查独立复算）。
- R9 批三（`5771419..160a852`，主体+批内循环 1+裁判证据登记合一 commit）：`0` 候选（全部生产、测试、fixture、SKILL 与 maintenance hunk 已归属 `R9-B3-G1`～`R9-B3-G7`；SHA 已回填 `160a852`；待批内审查独立复算）。
- R9 批三批内修复循环 1（物理并入 `160a852`）：`0` 候选（CA/endpoint identity、G3-0 transport 旁路、上层持久化负例、污染文件删除与三份台账 hunk 均归属 `B3F2-G1/G2`；SHA 已回填 `160a852`；本表自身回填 commit 按通例自指式计入）。
- R9 批三批内修复循环 2（`b4e9595..c46ef9f`）：`0` 候选（全部 hunk 已归属 `B3F3-G1`～`B3F3-G6`；四个既有裁判 mainnet JSON 与 SQD docstring 跨批 hunk 由 G5 追补 owner；SHA 已回填 `c46ef9f`；本表自身回填 commit 按通例自指式计入；待 opus 复审独立复算）。
- R9 批四（`f4c40ea..3b76db8`）：`0` 候选（全部生产、测试、fixture、方法论与 maintenance hunk 已归属 `R9-B4-G1`～`R9-B4-G6`；同文件多 owner 已按 hunk 拆分说明；SHA 已回填 `3b76db8`；本表自指式计入 G6；待 opus 批四批内审查独立复算）。
- R9 批四批内修复循环 1（`c86f251..c121422`；`c86f251` 仅比用户所报 `65443cf` 多批四审查报告入库）：`0` 候选（生产、scanner、manifest、两测试与两台账 hunk 均已归属 `R9-B4F-G1`～`R9-B4F-G5`；SHA 已回填 `c121422`；本表自指式计入 G5；待 opus 复审独立复算）。
- R9 批四批内修复循环 2（`6b93e9d..` 候选 tip）：`0` 候选（scanner、正式回归与两份台账 hunk 全部归属唯一 owner `B4F2C2`；SHA 留空待 Fable 回填；本表自指式计入）。

通例：区间末端恒取候选 tip；自指式 SHA 回填 commit 计入本区间。map 行文件清单以 Fable 实际 commit 分组为准；一文件含多 owner 的 hunk 时（文件级 commit 无法拆分），物理归属行与语义 owner 行互相注明，Fable 回填 SHA 时校正清单。审查产物豁免：opus 批内审查/复审报告入库件（`maintenance/repair-20260806/reviews/r9-batch*-*.md`，由 Fable 从 `r9-reviews/` 转录或 cp 入库）与 `r9-reviews/`、`blind-reviews/` 原件同性质，属审查记录非施工 hunk，owner=对应批次裁决 commit，不逐行登记 finding owner（2026-08-09 最终验收 SHA 回放时明文化）。
