# W2 v6 施工交付记录（全套 148 PASS / 2 FAIL；原案验收待裁决）

开工 HEAD：`18da7d630fcf59baad9b605bece5fde0e5dfe62c`，分支 `main`。恢复开工时只有调度方已允许保留的 `w2_done.md` / `w2_red_evidence.txt` 未跟踪，其他工作树改动为空。

A→F 已实现。23 个指定用例＋4 个补充用例共 27/27 PASS；`test_a4_gate.py` 单跑 23 项 PASS。`run_all` 实读 150 项：148 PASS、2 FAIL，进程 exit 1。两项失败均为沙箱禁止绑定本地端口的 PermissionError；未改测试，未宣称全套 PASS。

## 改动清单与 sha256

- `scripts/report/audit_release_gate.py`：新增 stage2-dryrun；保留深验缓存与系列绑定；只豁免三件 −3 产物。
  - sha256：`f865d53ab2c73eaf15c63226836d385c65c1bc12eec2ab4cfd8af35b0fb4a4d2`。
- `scripts/report/figures_from_facts.py`：抽出纯末点校验；新增确定性 fig2-series 与三项绑定旁车；共享单文件原子写函数。
  - sha256：`0ba4e6607cbb8211a0e03311bdfa9dc61d1623bac7f289b7406e48f448213bd8`。
- `scripts/report/a4_gate.py`：新增 G9 非图片完整性函数、下游漂移函数及 downstream-check；原封口函数不变。
  - sha256：`925c8c13e57da06570e02d970a0fd83cb43078c63278ece264595b34b80047dc`。
- `scripts/report/build_html.py`：只将 G9 非图片段替换为共享函数调用，保留 workflow、图片和监控 JSON 消费。
  - sha256：`dd759a3829759e2d1186cec05f6284f88367090b67947cedb14226f857287a95`。
- `scripts/report/stage2_closeout.py`：实现 check / fill-workorder / amend、十一项检查、收据复验及字节级 amendment 重放。
  - sha256：`5b7ad43756eaa40661b6f5bb5e6c58a02e508028d69c8d9a8bfdb5ff29ff6c14`。
- `scripts/tests/test_stage2_closeout.py`：真实生产者夹具；23 个工单用例＋4 个补充边界用例。
  - sha256：`a732edb648a459395d13625cb306d90737ef1da01168b00c2a7c850ee60f31bc`。
- `scripts/tests/run_all.py`：SUITE 末尾登记新测试，149 → 150。
  - sha256：`41357f85da7768c8cb5ee7dea9c9a96a72afdfff3ef0279c128c1bb0f6aa9fe8`。
- `scripts/tests/invariant_manifest.json`：仅扩展/新增获准 schema 与两条 overwrite_single 原子写登记。
  - sha256：`32534a3f8413d3fbbf77fd965743429bff738034946291330b7abac8fd559d23`。

本记录及 `w2_red_evidence.txt` 是另外两份获准记录文件。证据文件 sha256：`78e975c7e5ee633ebe3f5b74cad66c618b67ea75edd124bf9e7664749b1b8709`；本文件自身完整 sha256 通过落盘后的外部读回提供，避免自引用哈希。

## 每段红 → 绿

- A：旧 CLI argparse 拒绝 stage2-dryrun（exit 2）→ 真实夹具新 profile PASS。
- B：旧 CLI argparse 拒绝 fig2-series（exit 2）→ 新 producer 生成序列和旁车，check 末点对账 PASS。首次验证发现 macOS /var 与 /private/var 案根别名问题，规范化案根后修复。APU 原件副本三线验证未执行，见验收差异。
- C：真实 registry 漂移夹具下旧 CLI 不识别 downstream-check（exit 2）→ 新 CLI exit 3 并定位 adversarial_review；共享 seal 完整性正例 PASS。该只读命令存在性探针在 B 最终绿测前取得，C 代码在 B 绿后才改。
- D：原代码不存在共享函数委托（静态红断言）→ 实际 `test_a4_gate.py` 23 项 PASS，含 G9 正例、两处封口改动拒收及监控 JSON 正例。这里没有把原本通过的 G9 回归伪记为红测试。
- E：旧基线无 stage2_closeout.py，实际 CLI exit 2/No such file → 完整真实夹具整体 PASS；amend、receipt-only 等由下表逐项验证。
- F：SUITE=149 且未登记新测试；invariant 实际报 6 项预期差异 → SUITE=150，获准登记补齐，invariant PASS；无额外未登记项。
- 补充实际红测：畸形 amendment_chain 导致 receipt-only exit 1、Decimal 舍入把 2.675 错格式化为 2.68%、既有工单缺 fig2 时 fill 未补 null。均已修正并由补充测试变绿。

原始输出见 `w2_red_evidence.txt`。基线完全没有 closeout 命令，因此 E 下用例共用该“命令不存在”的真实红证据；没有声称在基线逐条跑出了不存在的业务检查。下表的变异负例均先证明独立副本正例可用，再断言指定子检查与业务文案。

| 用例 | 红证据 | 绿验证 |
|---|---|---|
| `dryrun_profile_exempts_stage3_artifacts` | E 公共红：基线无 closeout 命令 | PASS：三件 −3 资产均缺席，整体 PASS，收据与 receipt-only PASS。（测试 :165） |
| `only_findings_changed_is_rejected` | E 公共红：基线无 closeout 命令 | PASS：仅改 findings：#2 BLOCK，保留“封口后被改动”。（测试 :174） |
| `stale_registry_sha_detected` | E 公共红：基线无 closeout 命令 | PASS：真实 registry registered_at_utc 漂移：#3 检出 adversarial_review。（测试 :182） |
| `stale_a4_seal_sha_detected` | E 公共红：基线无 closeout 命令 | PASS：seal 增加一个空白字节：#3 检出 rounds.a4_seal_sha。（测试 :189） |
| `old_receipt_new_report_rejected` | E 公共红：基线无 closeout 命令 | PASS：旧收据配新正文：receipt-only exit 2。（测试 :197） |
| `receipt_only_checks_whale_series_and_commit` | E 公共红：基线无 closeout 命令 | PASS：序列或收据 commit 漂移：exit 2，分别命中对应文案。（测试 :205） |
| `fig2_entity_id_must_be_facts_key` | E 公共红：基线无 closeout 命令 | PASS：展示名充当键：#10 BLOCK，字段路径及业务文案吻合。（测试 :216） |
| `fig2_required_from_label` | E 公共红：基线无 closeout 命令 | PASS：大庄 label 得非空下限；空 lines、merge_groups 均 BLOCK。（测试 :223） |
| `flow_items_compat_and_extra_allowed` | E 公共红：基线无 closeout 命令 | PASS：items 兼容；额外合法图 PASS；空图清单 BLOCK；总供应/流通门槛与缺流通量 NOTE。（测试 :238） |
| `caption_mismatch_rejected` | E 公共红：基线无 closeout 命令 | PASS：整段全部 100.00% 替换后，#7 指定 private_main 不同源 BLOCK。（测试 :264） |
| `caption_btw_style_tiny_values_accepted` | E 公共红：基线无 closeout 命令 | PASS：0.0056%/0.0% 兼容；去掉 HHI/top 后 #7 NOTE。（测试 :274） |
| `amend_chain_updates_receipt` | E 公共红：基线无 closeout 命令 | PASS：合法机械替换后 amend、receipt-only PASS；改工单冻结字段 BLOCK 且不写收据。（测试 :295） |
| `amend_replay_mismatch_rejected` | E 公共红：基线无 closeout 命令 | PASS：混入正文、CRLF 字节变化均 BLOCK；删除型无 previous 拒，有正确前稿 PASS。（测试 :310） |
| `old_amendment_rewritten_rejected` | E 公共红：基线无 closeout 命令 | PASS：旧 approved_by 被改：receipt-only 拒；追加第二条仍因旧前缀漂移拒。（测试 :334） |
| `amend_passes_with_note` | E 公共红：基线无 closeout 命令 | PASS：#8 NOTE 不拦 amend；确实重跑全部十一项。（测试 :345） |
| `fill_never_overwrites_report_anchor` | E 公共红：基线无 closeout 命令 | PASS：既有 report_md 对象逐值保留。（测试 :355） |
| `low_sample_terminal_not_blocked` | E 公共红：基线无 closeout 命令 | PASS：真实单 owner LOW_SAMPLE：#6/#7 PASS，使用 small_sample_mode。（测试 :364） |
| `waived_terminal_not_blocked` | E 公共红：基线无 closeout 命令 | PASS：真实 ABNORMAL 扫描、两轮台账、合法 waiver：#6 PASS/WAIVED。（测试 :373） |
| `fig2_series_replay_binds_workorder` | E 公共红：基线无 closeout 命令 | PASS：改序列字节或工单多出线：#9 按重放/集合错误 BLOCK。（测试 :405） |
| `fig2_sidecar_substitution_rejected` | E 公共红：基线无 closeout 命令 | PASS：旁车改绑 alt 输出或同内容异路径源：#9 BLOCK。（测试 :418） |
| `fig2_duplicate_and_label_rejected` | E 公共红：基线无 closeout 命令 | PASS：重复键、逐行交换 key、空展示名拒；非空缩写仍 #9 PASS＋NOTE。（测试 :432） |
| `downstream_check_cli_exit3` | E 公共红：基线无 closeout 命令 | PASS：真实 registry 漂移，CLI exit 3，JSON item 命中 adversarial_review。（测试 :466） |
| `amendments_chain_gap_rejected` | E 公共红：基线无 closeout 命令 | PASS：两条 amendments 断链：#10 明确定位第二条 before_sha256。（测试 :474） |
| `workorder_reference_contracts` | E 公共红：基线无 closeout 命令 | PASS：必需引用、三条价格规则、fig1 四键、self-ref 窄豁免、别名与路径围栏。（测试 :487） |
| `receipt_shape_and_fill_nulls` | E/F 补充实际红测 | PASS：畸形收据由 exit 1 修为 exit 2；既有工单缺选材键时补 null 并列待亲笔。（测试 :535） |
| `caption_raw_rounding_and_pure_series_errors` | E/F 补充实际红测 | PASS：2.675 严格格式化 2.67%；原始阈值；纯函数非 list/缺件/非法 JSON 契约。（测试 :550） |
| `amend_rechecks_all_and_is_atomic` | E 公共红：基线无 closeout 命令 | PASS：正文替换合法但另改封口件仍拒且旧收据不变；异常不截断十一项。（测试 :577） |

## run_all 结果行原文

实际进程返回码：`1`。完整日志：`/tmp/run_all_w2.log`；sha256：`eeef1e971cf9c810f7a10bd192f50978c36fc1d8e9ad51d0a7b232266a98ab58`。以下 150 项结果行及最终结论逐字从落盘日志读回：

```text
========================================================
      PASS  changelog_lint.py        PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 71 条 + 归档 139 条
      PASS  docs_lint.py --all       PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）
      PASS  labels_manifest.py       PASS: 9 个发布表与 manifest（2026-08-20 00:48:52）指纹一致
      PASS  invariant_scan.py        PASS invariant manifest: receipt_producers=79, receipt_consumers=115, 
      PASS  test_r7_findings.py      PASS R7 regression suite: 15/15 observed green; EXPECTED_RED=0
      PASS  test_net_result.py       PASS: net Result 显式状态与 curl_json 失败分类
      PASS  test_batch1_rpc_attestation.py PASS B1-B RPC session: wrong-chain zero business/fail-closed/correct/f
      PASS  test_batch2_p3_hardening.py PASS B2-G0: invisible/type risk flags + producer symlink + OB-2 canoni
      PASS  test_batch2_capability_matrix.py PASS B2-D: immutable release tier + capability closure + derived CLI c
      PASS  test_batch2_ready_reconciliation.py PASS B2-D: READY rejects missing reconciliation wrapper and bound rece
      PASS  test_batch2_robinhood_exploration.py PASS B2-E: RH exploration is blocked by READY/A4/A5/build/audit and ex
      PASS  test_batch2_legacy_hardening.py PASS B2F2-G1: B2F-LG-01..05 + duplicate-chain canonicalization
      PASS  test_batch2_registry_harness_hardening.py PASS B2F-G2: string-only readiness API + reversible immutable harness
      PASS  test_batch3_solana_producers.py PASS B3-G2: Solana slot/envelope/txn/timestamp producer guards
FAIL(rc=1)  test_batch3_solana_vertical_slice.py (无输出)
FAIL(rc=1)  test_batch3_evm_vertical_slice.py (无输出)
      PASS  test_r9_batch1_boundaries.py PASS R9 batch1 process-boundary suite: 3/3
      PASS  test_r9_solana_attested_session.py PASS R9 SolanaAttestedSession: 10/10
      PASS  test_r9_batch2_attestation_adapters.py PASS R9 B2-G1: attestation keys resolve to callable factories
      PASS  test_r9_batch2_executable_capabilities.py PASS R9 B3-G3/G4: six probes ready; deleting one slice drops its chain
      PASS  test_r9_batch2_solana_sqd_adapter.py PASS R9 B2-G3: SQD dataset scope fixed and Solana mainnet RPC anchored
      PASS  test_r9_batch3_solana_observation.py PASS R9 B3-G1/G4: Solana observation protocol and negative variants
      PASS  test_r9_batch3_dynamic_runner.py PASS R9 B3-G2/batch10: dynamic checks use observed slot; exact stays f
      PASS  test_r9_batch3_preflight.py PASS R9 B3-G5: both preflight shells execute production observation co
      PASS  test_r9_batch3_release_guards.py PASS R9 B3F3-G3: Solana release negatives 6/6
      PASS  test_batch4_invariant_guards.py PASS B4-G1: bare pool / labels / vertical slice / denominator injectio
      PASS  test_exemption_guards.py PASS: exemption guards (EX-01 full-F-03)
      PASS  test_receipt_kernel.py   PASS receipt kernel: golden + target/hash/disk/concurrency/error/path/
      PASS  test_batch1_receipt_paths.py PASS B1-A receipt paths: symlink/alias/rollback/fail-closed/PASS prote
      PASS  test_reconciliation_runner.py PASS: reconciliation runner rejected all 7 controlled-execution counte
      PASS  test_chain_registry.py   PASS: six executable probes drive release/identity consumers; R9 verti
      PASS  ../labels/check_manual_sync.py   一致 ✓
      PASS  env_check.py             PASS: 21 个直接依赖逐项满足 pyproject→lock→installed；Python 3.14.6 满足 requires-
      PASS  test_commands_deploy_sync.py PASS: 4 份 staging/部署命令 SHA-256 逐文件一致
      PASS  casebook_lint.py         casebook lint 通过：6 册 38 条，ID 唯一、六字段齐全
      PASS  fixtures_lint.py         fixtures_lint PASS：pythia_anchors.json 结构完整（数值以文件为权威，回测后人工更新）
      PASS  test_build_html.py       PASS: build_html 九条契约全过（含 analysis/legacy 模式边界）
      PASS  test_engine_equivalence.py PASS: 三引擎 gate/退出码 10 例 hypothesis 全等；gate PASS 六产物全等；gate FAIL 正式序列零产
      PASS  test_report_facts.py     PASS: facts 宏渲染/附录B同源/G1集合gate(含entity_id主键)/G4宏名gate/G5手写检出/G2上界/G6归并
      PASS  test_fault_injection.py  PASS: 故障注入 F0–F5 + P0-02 四类通道完整性×三引擎 + R1 receipt 生成/漂移
      PASS  test_review_evm_integrity.py PASS: B-01 payload mismatches and B-02 rejected rows fail closed
      PASS  test_review_solana_integrity.py PASS: B-06/B-07/B-08 + P1-03 v1/v2 decode retry, identity and failure 
      PASS  test_review_labels.py    PASS: B-09 manual address-book rows are chain-scoped; composite sync k
      PASS  test_review_robinhood_integrity.py PASS: B-10 decimal conversions/V3 scaling and H-01 truncated gzip pres
      PASS  test_review_resume_integrity.py PASS: H-02/H-03 + U2b staged first capture + R2 legacy manifest refres
      PASS  test_entity_identity_gate.py PASS: P1-01 无标签实体成员 + 严格 identity gate schema/计数/唯一性/实体绑定
      PASS  test_review_chain_collectors.py PASS: H-10 overlap resume integrity
      PASS  test_labels_resolver_guards.py PASS: M-02 strict addresses and empty-file schema
      PASS  test_batch1_risk_flags.py PASS B1-C risk_flags: canonical parser + four-consumer/live-table agre
      PASS  test_roundtrip_check.py  PASS: round-trip 缺表与行内退化均 fail-closed
      PASS  test_label_snapshot_roundtrip.py PASS: source_snapshot_at 新行透传、默认回落、高优先覆盖、低优先补空
      PASS  test_goldset_curated_rebuild.py PASS: curated 金标真实重建 18/18 逐语义保留，Arbitrum weak_gate=false
      PASS  test_arbitrum_label_consumers.py PASS: Arbitrum lookup/cluster 直接命中；CEX no_merge/exclude 生效且非跨链推导
      PASS  test_benchmark_labels.py PASS: benchmark 六表完整性与 manual 召回硬闸生效
      PASS  test_add_labels_rollback.py PASS: add_labels validate/benchmark/manifest 三闸与失败回滚
      PASS  test_fetch_failclosed.py PASS: HyperSync 采集器失败与游标异常均 fail-closed
      PASS  test_fetch_gmgn_sh.py    PASS: GMGN 临时文件、JSON 校验和失败聚合生效
      PASS  test_sixlens_receipts.py PASS: 六视角批①结构化回执与 fail-closed
      PASS  test_sixlens_docs.py     PASS: 六视角批⑤大小口径与 archive 路由
      PASS  test_token_no_positional.py PASS: 自动枚举 4 个 HyperSync 入口；拒绝位置 token、输出无 secret、优先序三层闭合: fetch_hyper
      PASS  test_contract_routes.py  PASS: R-01/R-02 注册表、ID 快照、五组锚与 SKILL 原子阶段双向闭合
      PASS  test_version_consistency.py PASS: M-03 version metadata consistent at 7.0.4
      PASS  test_chain_support_matrix.py PASS: formal-candidate matrix closes frontmatter + labels capability: 
      PASS  test_formal_chain_support.py PASS: Arbitrum collection/G8 capability retained; release/A4/A5/formal
      PASS  test_review_scale_guards.py PASS: M-04 bounded helpers, streaming parquet batches, and bound input
      PASS  test_figures_from_facts.py PASS: figures_from_facts fig1白名单/legacy销毁键/legend receipt/burn豁免/overl
      PASS  test_cluster_quality.py  PASS: test_cluster_quality 3/3（盲化/冲突阳性/敏感度冒烟）
      PASS  test_sqd_merge_equiv.py  PASS: fetch_sqd_transfers_v2 v4 八组契约全过
      PASS  test_spl_edge_core.py    PASS: spl_edge_core T1 三件套 + T2 迁移等价 + T3 语义常量
      PASS  test_sqd_collector_meta_v4.py PASS: SQD v4 collector meta logical evidence matches replay
      PASS  test_sqd_consumer_v4.py  PASS: SQD v4 consumer split-mode regressions
      PASS  test_supply_truth_gate.py supply_truth_gate 形态①/②离线契约测试全部通过
      PASS  test_repair_batch_a.py   PASS batch A F-01/F-02 regressions 45/45
      PASS  test_repair_batch_b.py   PASS batch B F-03/F-08 regressions 41/41
      PASS  test_repair_batch_c.py   PASS: repair batch C (F-05+F-04+fixround1+fixround2) 227 checks
      PASS  test_handoff_manifest.py handoff_manifest 契约测试全部通过（93 项）
      PASS  test_audit_release_gate.py PASS: audit_release_gate 净室资产/哈希/CEX受益权/阴性结论/图表封口与负钳零/对抗复核否决/四查WARN拦截/
      PASS  test_review_20260804_p0.py PASS: P0-01 collector provenance + P0-02 reproduce freshness regressio
      PASS  test_review_20260804_p101.py PASS: P1-01 immutable HyperSync outdir identity and legal capture coex
      PASS  test_review_20260804_p104.py PASS: P1-04 strict finite percentages/raw integers/unresolved counts
      PASS  test_review_20260804_p105.py PASS: P1-05 mandatory new-analysis vs independent-audit release profil
      PASS  test_review_20260804_p106.py PASS: P1-06 claim registry id/text/verdict/evidence/location alignment
      PASS  test_review_20260804_p201.py PASS: P2-01 total-supply share binding + Arbitrum G8 support
      PASS  test_review_20260804_p202.py PASS: P2-02 12 required-asset deletions return exit 2 JSON BLOCK
      PASS  test_round4_csv_adapters.py PASS: alternate adapters are native-receipted or explicit nonformal
      PASS  test_param_scripts.py    PASS: 三脚本参数反例、旧案字面量与 cadence identity 绑定
      PASS  test_round4_a5_seal.py   PASS: A5 seal binds A4, Markdown and every report image
      PASS  test_round4_identity_emitter.py PASS: real EVM collector+preflight+replay and Solana scan chains; copi
      PASS  test_round4b_provenance.py PASS: copied-hash identity self-reports, producers and runners blocked
      PASS  test_round4c_solana_provenance.py PASS: raw GPA replay rejects six-file/owner/supply forgeries; pubkey d
      PASS  test_state_from_facts.py PASS: D-05 state_from_facts compiler owns membership and raw-derived s
      PASS  test_a4_gate.py          a4_gate 契约测试全部通过（23 项）
      PASS  test_time_spotcheck.py   time_spotcheck 契约测试全部通过（20 项）
      PASS  test_peaks_daily.py      PASS：0 项失败
      PASS  test_wave_scan.py        PASS：0 项失败
      PASS  test_flow_anomaly.py     PASS：0 项失败
      PASS  test_entity_source_trace.py PASS：0 项失败
      PASS  test_adjudication_validator.py PASS：0 项失败
      PASS  test_distribution_gate.py PASS: distribution gate red-green contract
      PASS  test_distribution_chart.py PASS: distribution chart contract
      PASS  test_apu_legacy_gaps.py  PASS: APU 存量缺口工单契约测试全绿
      PASS  test_repair_batch_d.py   BATCH D 全部通过
      PASS  test_repair_batch1.py    PASS v6.41.0 batch1 steps 1-6 RV-07/RV-04/RV-17/F-03/F-01/A5v3/F-04
      PASS  test_batch6_sqd_v4_blind_review.py PASS: 批6 opus 盲审防回归
      PASS  test_repair_batch2_f02.py PASS workorder B F-02 regressions
      PASS  test_repair_batch3_f01.py all batch3 F01 tests passed
      PASS  test_repair_batch3_gates.py PASS: 批3 deploy-sync/env-check/R10-ledger gates 回归全部通过
      PASS  test_evm_observation.py  PASS EVM observation bundle protocol: 10/10
      PASS  test_evm_observation_release.py PASS workorder C EVM observation release: 11/11
      PASS  test_repair_g1_audit_report.py PASS: F-02 independent-audit --report fail-closed 四件套
      PASS  test_repair_g1_risk_flags_pipeline.py PASS: F-12 risk_flags lint/consumer/artifact fail-closed
      PASS  test_repair_g1_handoff_containment.py PASS: 16/16 checks
      PASS  test_repair_g1_cross_target.py PASS: F-03 cross-partition target equality and absence policy
      PASS  test_repair_g1_text_hygiene.py PASS real repository: 358 tracked active files, zero hits
      PASS  test_evm_observation_nonempty_code.py PASS F-04 EVM nonempty code and ABI word checks: 5/5
      PASS  test_arbitrum_exploration_cli.py PASS F-10: exploration CLI execution + formal consumer isolation
      PASS  test_recon_deep_reverify.py PASS test_recon_deep_reverify
      PASS  test_gmgn_divergence_note.py PASS test_gmgn_divergence_note
      PASS  test_g3_docs_guards.py   PASS: F-05 machine boundary
      PASS  test_g3_alt_collectors.py SUMMARY: 13 passed, 0 failed, 0 skip-red
      PASS  test_collector_history.py PASS: every registry entry is git-verifiable
      PASS  test_v2_identity_history.py PASS: R-3 v2 historical identity maintenance/consumer parity
      PASS  test_anchor_plan_v3.py   anchor-plan v3: 15/15 PASS
      PASS  test_done_v4_collector.py PASS: U2 done/v4 collector + C12 recovery (24/24)
      PASS  test_csv_resume_collector_gate.py PASS: hash-wide REVOKED rejects current collector at startup
      PASS  test_sqd_coverage_probe.py PASS SQD coverage probe: 12/12 offline groups
      PASS  test_f03_sharedmap_reuse.py PASS F-03 shared-map reuse: 15/15 groups
      PASS  test_batch2d_stream_tail.py PASS batch2d SQD stream tail: 4/4 groups
      PASS  test_sqd_gap_repair.py   GREEN 29c implemented validate_current_candidates 已实现
      PASS  test_reconcile_v4_receipt.py GREEN 32 verdict/exit_code/gate_pass 三元互洽
      PASS  test_recon_fifth_check.py GREEN 22 wave-scan/v4 与 flow-anomaly/v2 旧产物被 v5/v3 验收拒收
      PASS  test_batch3c_census_fields.py PASS batch3c census fields match the SQD contract
      PASS  test_batch8_repair_scale.py PASS batch8: key-neutral identity/pool failover/ordered workers/resume
      PASS  test_batch7_validator_coverage_gaps.py 批7 validator 覆盖缺口加固回归全部 GREEN (缺口1遍历主键 + 缺口3边slot窗口)
      PASS  test_batch11_frozen_bundle_binding.py PASS batch11 frozen/live binding regressions
      PASS  test_batch12_frozen_supply_drift.py PASS: batch12 frozen supply drift contract
      PASS  test_batch13_accounting_target.py PASS batch13 accounting target regressions: 8/8
      PASS  test_batch14_accounting_bundle_fallback.py batch14 tests=9 failed=0
      PASS  test_batch15_three_ledgers_frozen.py PASS batch15 frozen consumers: 12/12
      PASS  test_lit_regression_f007.py SUMMARY: 15/15 PASS
      PASS  test_lit_regression_f008.py SUMMARY: 46/46 PASS
      PASS  test_batch16_resolve_ref_case_path.py PASS batch16 resolve_ref case path: 16/16
      PASS  test_batch17_identity_chain_alias.py PASS batch17 identity chain alias: 4/4
      PASS  test_batch18_shared_bundle_witness.py PASS batch18 shared bundle witness: 6/6
      PASS  test_batch18_manifest_stage2_loop.py PASS batch18 manifest stage2 loop: 7/7
      PASS  test_batch18_review_digest.py PASS batch18 review digest: 11/11
      PASS  test_producer_registry_current.py producer registry: 0 FAIL
      PASS  test_reopen_cycle.py     reopen-cycle: 13/13 PASS
      PASS  test_a4_limits_extract.py limits-extract: 12/12 PASS
      PASS  test_stage2_closeout.py  stage2_closeout: 27/27 PASS
========================================================
2 项失败——修完再收工
```

两项失败的真实异常均为：

```text
PermissionError: [Errno 1] Operation not permitted
```

堆栈均在测试创建本地 HTTP server 时落到 `self.socket.bind(self.server_address)`；完整失败堆栈已进入 w2_red_evidence.txt。


按指令使用 `nohup python3 scripts/tests/run_all.py > /tmp/run_all_w2.log 2>&1 &`。首次 zsh 启动报 `nice(5) failed: operation not permitted`，进程未存活、日志 0 字节，无测试结果；随后在 `/bin/bash` 执行同一命令并用 shell wait 保留作业会话。测试文件未作沙箱适配修改。

## 与工单差异、未做项及范围边界

1. 已按 v6 实现“本版不支持合并线”，这是工单已声明的范围调整；未实现 reseal（W3），未改三册手册、VERSION、CHANGELOG。
2. 夹具复制时用 copytree 的排除清单省去六件净室件，结果等价于工单的“复制后删除六件”，避免批量删除操作。没有伪造或覆盖真实 adversarial_review.json。
3. 新脚本 fill 和收据共用 `_atomic_json`，只登记一个实际含 os.replace 的函数；fig2 输出与旁车依次替换，登记 overwrite_single，不冒充双文件事务。
4. APU 0914 的已知案路径、COLLECT、LIT 的输入读取遭 PermissionError。BTW 的猜测路径不存在，父目录不可枚举，未取得可定位的指定原案。没有运行这些原案验收，也没有以合成夹具代称原案 PASS。已完成夹具对两案别名/缩写/小数格式的规则覆盖；APU 完整 closeout 仍留 W3。
5. 当前可读 MELANIA 原件复制到临时目录后，仅运行 E2 图注规则：五桶 95.83% / 0.03% / 4.14% / 0 / 0 均命中，图注段无 HHI/top，因此为 NOTE，**未复现工单预期的 BLOCK**。记录了报告、rounds、终态 scan 的完整 sha256 与图注原文；不能确定工单是否指另一份历史输入，未为强行满足预期放宽或收紧规则。该差异未视作原案验收通过。
6. 图注仍为“存在性检查，非逐桶配对”；time_range 不消费；序列旁车/figure2_check_receipt 均不证明 PNG 使用了该序列。以上边界已进入 detail/help。
7. 本轮没有 commit/push、fetch 或下载任何源。测试期间外部提交将 HEAD 推进至 `7c0e8716fa656729d43c3f146a31d178ecf6a919`；`18da7d6..HEAD` 仅修改 W3 工单，与 W2 白名单无交集，未归为本轮改动。

## 待调度方裁决的原案验收事项

代码已按 v6 规则施工；未取得工单全部原案验收结果。需要调度方指定可读取的 APU 0914 / BTW / COLLECT / LIT 案卷副本路径，或明确将这些原案自检移交后续验收。MELANIA 需要指定应复现 BLOCK 的报告/scan 快照，或接受当前输入按 E2 得 NOTE 的实读结果。本轮保留规则，不自行替换历史输入或把差异算作通过；交付后停止等待 resume。

## 访问纪律与范围复验

恢复裁决后**未再读取 ~/.codex 下任何文件**；未读取 `~/.claude/skills/_archive/` 或 tag `codex-frozen-20260915`。首次启动读取 MEMORY.md 的事实已获调度方接受，仍保留在附录；不把整个会话写成从未读取。

收尾 HEAD：`7c0e8716fa656729d43c3f146a31d178ecf6a919`；本轮没有 commit。工作树写入范围复验：8 个实现/测试文件＋2 个指定记录文件，全部在白名单。AST 源段核对证明 `cmd_register` / `cmd_finalize` / `distribution_claim_source` / `validate_revision_chain` 与开工基线逐字相同；`audit_release_gate.run` 逐字相同。manifest 旧登记及 W1 登记保留，不扩 formal_entrypoints。原案只读，测试产物留在临时目录。

## 附录：首次启动阻塞记录（裁决已接受，以下请求已解决）

# W2 v6 状态：开工阻塞，未施工

## 开工实物

- 仓库：`/Users/uravvv/.claude/skills/token-chip-analysis`。
- 分支：`main`。
- `git log -1 --format=%H` 原文：`c3ff916f1d67a538ad0aaacdd729236e3bc636db`。
- 开工 `git status --short` 原文：

```text
?? maintenance/repair-20260915-stage2-closeout/workorder_w3.md
```

HEAD 符合要求，工作树不满足 §0.1 的干净前提。该未跟踪文件在本轮写入前已存在，本轮未读取、修改、移动或删除它。

## 请求调度方裁决

1. 是否明确允许保留上述既有未跟踪文件并继续 W2，或由调度方先恢复干净开工状态？本轮不自行处置该文件。
2. 本轮启动时确实读取了 `/Users/uravvv/.codex/memories/MEMORY.md`，不满足用户首条禁读要求。是否接受本轮访问记录后继续，或终止本轮施工资格？后续没有继续读取 `~/.codex`，未读取 `~/.claude/skills/_archive/` 或 `codex-frozen-20260915` tag。

已停止，等待调度方 resume 裁决。没有进入 A–F，不将本轮记为合规完工。

## 改动清单与 sha256

没有修改任何脚本、测试或 manifest。仅新建工单指定的两份记录：

- `maintenance/repair-20260915-stage2-closeout/w2_red_evidence.txt`：开工原始结果与访问披露；sha256：`9493363cb711fea7d7fb21f45c4379ded13ef7e7859264254943d39e18438271`。
- `maintenance/repair-20260915-stage2-closeout/w2_done.md`：本阻塞记录；自身完整 sha256 由落盘后的外部读回给出，避免自引用哈希。

不 commit、不 push；未修改 VERSION、CHANGELOG 或三册手册；未下载任何源。

## 红 → 绿证据

A、B、C、D、E、F 均未开始，无实现测试红证据或绿证据。`w2_red_evidence.txt` 只记录前置阻塞，不冒充业务红测。以下全部用例均未执行：

- `dryrun_profile_exempts_stage3_artifacts`
- `only_findings_changed_is_rejected`
- `stale_registry_sha_detected`
- `stale_a4_seal_sha_detected`
- `old_receipt_new_report_rejected`
- `receipt_only_checks_whale_series_and_commit`
- `fig2_entity_id_must_be_facts_key`
- `fig2_required_from_label`
- `flow_items_compat_and_extra_allowed`
- `caption_mismatch_rejected`
- `caption_btw_style_tiny_values_accepted`
- `amend_chain_updates_receipt`
- `amend_replay_mismatch_rejected`
- `old_amendment_rewritten_rejected`
- `amend_passes_with_note`
- `fill_never_overwrites_report_anchor`
- `low_sample_terminal_not_blocked`
- `waived_terminal_not_blocked`
- `fig2_series_replay_binds_workorder`
- `fig2_sidecar_substitution_rejected`
- `fig2_duplicate_and_label_rejected`
- `downstream_check_cli_exit3`
- `amendments_chain_gap_rejected`

工单列出的既有回归测试、invariant_scan、APU/BTW 纯规则验收及 MELANIA/COLLECT/LIT 原案子检查也均未执行。

## run_all 结果行原文

无。本轮未启动 `nohup python3 scripts/tests/run_all.py > /tmp/run_all_w2.log 2>&1 &`，未生成本轮运行结果，不能声明 PASS、FAIL 或 PermissionError。

## 与工单差异及未做项

- 开工存在未跟踪文件，干净工作树前提未满足。
- 确实读取过 `~/.codex/memories/MEMORY.md`，违反本轮用户禁读要求；没有隐藏该访问。
- 全部施工与验收未做，原因是开工阻塞并等待调度方裁决。
- 没有白名单外写入，没有自行扩大施工范围。

