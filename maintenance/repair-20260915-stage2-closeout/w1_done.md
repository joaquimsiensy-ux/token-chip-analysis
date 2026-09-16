# W1（v2.1）施工交付记录

**验收结论：PARTIAL，未达到工单“run_all 全绿”的完成标准。** 已落实本批 A–D 施工范围以及调度方追加授权的 3 行 schema 登记；最终工作树的全套测试实跑为 **147 PASS / 2 FAIL / 149 项，exit 1**。两项失败均发生在本地测试服务器绑定端口时，错误为 `PermissionError: [Errno 1] Operation not permitted`。不能把这两项计为通过。

记录时间：2026-09-16T04:44:38.213668+00:00。物理仓库 `/Users/uravvv/.claude/skills/token-chip-analysis`；分支 `main`。本轮未执行 commit、fetch 或外网访问，C 段仅做 CSV 与 `--dry`，未正式入库。

## 基线、续工与并发状态

- 工单基线 `764b60c`（7.0.4）；最初施工 HEAD `be9e1f7714623a06d711568be8cfa2d2b42f183e`。
- v2.1 续工 HEAD `8615050efe49aef0326aa1efa7a85c4cc3fa86c3`。按已核实的勘误，在 N8 的 `build_unit_case(root)` 后补写 `data/holders_owners.json` 的 data_map 登记及实物 SHA256；三条原断言逐字保留。
- 交付 HEAD `0a507f7f96f91e7273e72b3f5c92cae999ad4282`。续工期间调度方并发提交了 W2 工单；W1 工作树改动仍未提交。本轮没有修改 W1/W2 工单、`workorder_w3.md` 或原停工记录。
- 原停工原因、现场与历史访问偏差保留在 `w1_done_attempt1_stopped.md`；本次续工没有再次读取 `~/.codex`、`_archive/` 或禁读 tag。

续工 HEAD 至交付 HEAD 的已提交差异：

```text
 .../workorder_w2.md                                | 188 +++++++++++----------
 1 file changed, 102 insertions(+), 86 deletions(-)
```

## 改动文件与最终行为

| 文件 | 改动 |
|---|---|
| `scripts/report/holder_distribution_scan.py` | 快照按显式路径、initial 绑定、data_map 唯一登记解析；新增受控 `reopen-cycle`，先检查再归档、失败逆序回搬，复制 A4 seal/registry；每轮 final scan 独立重建重开回执绑定 |
| `scripts/tests/test_batch15_three_ledgers_frozen.py` | 两处调用同步 stage 参数；按 v2.1 补齐 N8 的真实 data_map 登记，原三条断言不改 |
| `scripts/tests/test_reopen_cycle.py` | 工单要求的 12 例，加手工周期编号及搬运失败回滚回归；13/13 PASS，两个集成路径均实际执行，无跳过 |
| `scripts/report/a4_gate.py` | 新增 `limits-extract` 和 CLI 帮助；唯一标题、编号/项目符、严格续行、代码围栏、路径与输入覆盖保护、稳定 JSON 输出 |
| `scripts/tests/test_a4_limits_extract.py` | 黑盒 12 例，负例先验证正例可用；12/12 PASS |
| `scripts/tests/run_all.py` | 登记两项新测试，SUITE 从 147 增至 149 |
| `scripts/tests/invariant_manifest.json` | **工单白名单外、经调度方授权的最小改动**：仅新增指定 3 行 schema 登记，diff 为 +3/-0，未改其他内容 |
| `maintenance/repair-20260915-stage2-closeout/curation_overrides_20260915_apu.csv` | 工单指定的 15 列、4 行 curation 补录，未放入 additions |
| `maintenance/repair-20260915-stage2-closeout/w1_red_evidence.txt` | 保留各段 RED→GREEN 命令、退出码、原文、测试/生产 SHA256，以及两轮 run_all 全文 |
| `maintenance/repair-20260915-stage2-closeout/w1_done.md` | 本交付记录 |

前轮另已写入 `maintenance/repair-20260915-stage2-closeout/w1_done_attempt1_stopped.md`，本次续工保持原样。`workorder_w3.md` 是并发产物，不属于本轮改动。

已逐字核对禁改函数与 HEAD：`holder_distribution_scan.py` 的 `verify_data_map`、`validate_rounds_ledger`、`cmd_record_round`、`analyze`、`bin_scan`、`semantic_payload`，以及 `a4_gate.py` 的 `cmd_register`、`cmd_finalize`、`distribution_claim_source`，全部未改。指定既有测试文件、三个标签处理器、标签库、版本号、CHANGELOG、三册手册均未改；`git diff --check` exit 0。

## 各段 RED→GREEN

表内命令从仓库根执行。常规测试设 `PYTHONDONTWRITEBYTECODE=1`；涉及绘图的 GREEN 另设 `MPLCONFIGDIR=/private/tmp/w1-mplconfig`。原始准确命令及对应哈希均在 `w1_red_evidence.txt`。

| 段 | 命令 | RED | GREEN |
|---|---|---|---|
| A | `python3 scripts/tests/test_reopen_cycle.py` | exit 1，1/13 PASS、12/13 FAIL（生产修改前） | exit 0，13/13 PASS；最终全套再次 PASS |
| A1 v2.1 | `python3 scripts/tests/test_batch15_three_ledgers_frozen.py` | 前轮 exit 1，11/12，N8 缺 data_map | exit 0，12/12；最终全套再次 PASS |
| B | `python3 scripts/tests/test_a4_limits_extract.py` | exit 1，0/12；负例因前置正例不可用而红 | exit 0，12/12；最终全套再次 PASS |
| C | `python3 -B /tmp/w1_c_input_check.py` | exit 1，补录 CSV 尚不存在 | exit 0，4/4、15 列及全部字段与工单一致 |
| C2 | `python3 scripts/labels/add_labels.py maintenance/repair-20260915-stage2-closeout/curation_overrides_20260915_apu.csv --dry` | C1 输入验收 RED 见上 | exit 0，3 覆盖＋1 新增 |
| D | `python3 -B /tmp/w1_suite_registration_check.py` | exit 1，SUITE 147，缺两项登记 | exit 0，SUITE 149，两项各登记一次 |
| 授权清单补登 | `python3 scripts/tests/invariant_scan.py` | 首轮全套 exit 1，6 discrepancy(s) | 仅补 3 行后 exit 0；最终全套再次 PASS |

C/D 的临时检查脚本全文和 SHA256 也已嵌入证据文件，可脱离 `/tmp` 重建。没有新增白名单外的仓库测试文件。

## C 段 dry-run 原文

```text
  ~ eth 0x7a250d5630b4 分类覆盖: flashbots-user/identity → router/exclude（高置信新条目）
  ~ eth 0x3fc91a3afd70 分类覆盖: sandwich-bot/identity → router/exclude（高置信新条目）
  ~ eth 0x66a9893cc07d 分类覆盖: sandwich-bot/identity → router/exclude（高置信新条目）
[eth] 新增 1 | 合并进已有行 3 | 总 140047
```

退出码 0。正式入库、C3 四址查询验收及重建 roundtrip 未执行，留待 W2 验收后另派。两份标签资产在施工前后内容哈希相同：

- `references/labels/labels-eth.csv`：`f8e02f0cf2484562dbfe347d0c39ab8ed3d250218e8caaf48fb38be409223f22`
- `references/labels/manifest.json`：`22dda2282e98b197147e0a86cba4f68ca1fbcd6ffdc84c0765bfcc4845df25a5`

## run_all 实跑与最终结果

两轮均使用指定的 nohup 命令落盘后读取，无 `| tail`：

```bash
nohup python3 scripts/tests/run_all.py > /tmp/run_all_w1.log 2>&1 &
```

运行环境另设 `PYTHONDONTWRITEBYTECODE=1`、`MPLCONFIGDIR=/private/tmp/w1-mplconfig`、`PYTHONUNBUFFERED=1`。第二轮 shell 设置 `NO_BG_NICE`，避免 zsh 后台启动时请求 nice；测试命令、SUITE 和测试内容不变。shell 通过 `wait` 获取真实退出码并写入 exit 文件。

| 轮次 | 结果 | 日志 |
|---|---|---|
| 首轮（在授权补登前起跑） | 146 PASS / 3 FAIL / 149，exit 1；清单失败发生后才获授权补登，因此另跑最终轮 | `/tmp/run_all_w1_attempt1.log`，退出码 `/tmp/run_all_w1_attempt1.exit` |
| 最终轮（3 行补登后的工作树） | **147 PASS / 2 FAIL / 149，exit 1** | `/tmp/run_all_w1.log`，退出码 `/tmp/run_all_w1.exit` |

最终轮日志 SHA256：`78f5a0f9fc43678f6127c9b0503669316db272334aad67a9ef2110d9849363c5`。
首轮日志 SHA256：`d67149d1aa9c1f346b5bbe870b1f11244bcff5c8bdfac65733db619a5cc00e6c`。
两轮原文均已归入仓库内的 `w1_red_evidence.txt`，不限于临时日志。验收期间冻结检查的 10 个代码/测试/CSV/标签文件均无内容漂移。

两项失败的实证：

- `scripts/tests/test_batch3_solana_vertical_slice.py:625`：`ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)`。
- `scripts/tests/test_batch3_evm_vertical_slice.py:281`：同样创建本地测试服务器。
- 两者均在标准库 `socketserver.py:478` 的 `self.socket.bind(self.server_address)` 抛出 `PermissionError: [Errno 1] Operation not permitted`，exit 1。

最终 run_all 结果行原文（149 项）：

```text
      PASS  changelog_lint.py        PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 71 条 + 归档 139 条
      PASS  docs_lint.py --all       PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）
      PASS  labels_manifest.py       PASS: 9 个发布表与 manifest（2026-08-20 00:48:52）指纹一致
      PASS  invariant_scan.py        PASS invariant manifest: receipt_producers=77, receipt_consumers=113, 
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
      PASS  test_repair_g1_text_hygiene.py PASS real repository: 356 tracked active files, zero hits
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
2 项失败——修完再收工
```

## 与工单差异及遗留

1. **工单白名单外、经调度方授权的最小改动**：`scripts/tests/invariant_manifest.json` 仅增加三行：a4_gate producer 的 `a4-limits/v1`，holder_distribution_scan producer 和 consumer 的 `distribution-reopen/v1`。首轮发现缺登后，先用临时副本验证、向调度方展示 3 行补丁，获明确授权后才写入原文件；其余内容未改。
2. N8 夹具按已提交的 v2.1 勘误恢复施工，保留原停工记录，不改写前轮失败证据。
3. A 测试额外覆盖周期目录历史编号和搬运失败回滚。B 的同一文件保护也核验硬链接；所有新增断言均未放宽原门禁。
4. 完整验收仍欠上述两项本地服务器测试。需要在允许绑定 `127.0.0.1` 端口的执行环境补跑完整 149 项后，才能认定“run_all 全绿”。本次没有修改这两项测试或生产门禁来消除权限失败。
5. C 仅完成 CSV 与 dry-run；正式标签入库、C3 和重建 roundtrip 均不属于本批执行结果。

## 交付内容 SHA256

- `scripts/report/holder_distribution_scan.py`：`8abcdd16864b2c5d3d639201f5985c560a4e0539f0f59d1cda0deaffe372263d`
- `scripts/report/a4_gate.py`：`a679588dcd1f6102c166122c805281347897c54183dc7b2d70a810779bcc47b0`
- `scripts/tests/test_batch15_three_ledgers_frozen.py`：`5dacdd1023094df3ab09596a438fc56f49ba6679e77c053d94a9d370b3bf6b95`
- `scripts/tests/test_reopen_cycle.py`：`70dd5ed931b73155ec53f347e1a2bedacbeaa25764dfe6383514829b0dcab908`
- `scripts/tests/test_a4_limits_extract.py`：`03802c25804813550a30f0f6b93bb86c941566f106b60b06a895a9bbf9731054`
- `scripts/tests/run_all.py`：`659de8aa73082ceb999305e2e6ed5661cd41ae7f3cd67262ed76ef9c4293aaac`
- `scripts/tests/invariant_manifest.json`：`63bd7cfdcfc39c7b3c81f1f87eca155219accd99fed2da21ce2982a2ad3df663`
- `maintenance/repair-20260915-stage2-closeout/curation_overrides_20260915_apu.csv`：`e1a3007eb4632a26d3404df3e3c12aa1b0d23ea4ce5acfe2bde76b425e85f1b5`
- `maintenance/repair-20260915-stage2-closeout/w1_red_evidence.txt`：`0ad6e19ee29668a2db625ee6766bcca598e1ad579b7ba29e4d6bae33c59b8f78`
