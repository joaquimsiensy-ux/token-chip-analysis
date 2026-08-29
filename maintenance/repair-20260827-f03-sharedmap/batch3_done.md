# F-03b 批 3 完成报告

## 结论

- 主体段已完成；冻结基线 `HEAD=9b1c4b5`（v6.52.14）未发生 git 写操作。
- 当前全量入口共有 139 项，不是历史批次的 137 项。本机原样结果为 **137 PASS / 2 FAIL**；两项失败均在业务断言前因沙箱禁止绑定 `127.0.0.1` 而退出，不能记作全绿。
- F-03b 定向测试 `15/15` 通过；原 SQD coverage lifecycle/roundtrip `12/12` 通过。
- `validate_shared_map(assets/sqd-solana-coverage-map/20260827.json)` 返回 `{"ok": true, "reasons": []}`。
- `solana_exact_validate.py`、契约两件、版本面、登记面、20260827 资产均零改动。

## 工单五栏回填

### 1. 不变量

- 值不匹配仍整体回退：首轮或末尾重试出现任一逐 slot mismatch，最终原因保持 `recheck-mismatch:<slot>`；canary 逐值不等分支保持 `canary-counts-changed`。
- 请求失败局部剔除：transport 失败、`part is None`、返回长度短于请求区间、worker 异常均分类为 request-failed；全部首轮失败区间在同一 `ThreadPoolExecutor` 末尾统一重试一次。
- canary 核心不带伤：canary 所在区间重试后仍不可用，整体回退并记录 `canary-recheck-unavailable`。
- 非 canary 持续失败段写入 `unverified_ranges`，复用缓冲对应字节清零，随后由 `_missing_ranges` 纳入 full 扫描；最终 candidate/refuted 分类只读补扫后的 fresh counts。
- P1-1 来源一致性：每个 `map-reuse` ledger 行只覆盖一个实际复用连续子区间，逐段哈希真实复用字节；未验证段、案区间外 slot 不进入 map-reuse 声明。失败 recheck 行直接 `counts_coverage=false`；案件区间外的成功 recheck 也只作地图审计，不冒充交付覆盖。

### 2. 同族清单与逐处结论

- `scripts/solana/sqd_coverage_probe.py:573` `_recheck_known_slots`：已改为 verified/mismatch/request-failed 三分、同池末尾重试、mismatch 优先裁决、失败行零 coverage。
- `scripts/solana/sqd_coverage_probe.py:650` `_reuse_ranges_excluding`：从本轮实测得到的 unverified 请求区间机械求补集；非法范围或清零闭合异常抛错，外层整体回退。
- `scripts/solana/sqd_coverage_probe.py:670` `_load_known_map`：新增 `unverified_ranges`/`recheck_stats`，canary 不可用硬回退，返回带零洞复用缓冲与实际 `reused_ranges`。
- `scripts/solana/sqd_coverage_probe.py:1163` `run_probe`：map-reuse ledger 按连续复用子区间逐行生成；full 自然补扫零洞；最终 scan_ranges 仍从成功且 `counts_coverage=true` 的 ledger 重建。
- `scripts/lib/solana_exact_validate.py:705` `validate_shared_map`：零改动；20260827 冻结资产实测 `ok=true`。
- `scripts/lib/solana_exact_validate.py:452` `validate_coverage`：零改动；“三段 map-reuse + 两段 full 补扫”端到端发布后实测 PASS。
- `scripts/tests/test_sqd_coverage_probe.py`：零改动；既有 lifecycle/roundtrip `12/12` 继续通过。
- `assets/sqd-solana-coverage-map/README.md:51`、`references/scan-schemas.md:647,673-690`：已登记大白话语义、字段、range 计数口径、失败分级和逐段声明规则。

### 3. 三件套

- 原反例：非 canary `170..171` 持续失败；冻结基线返回 `reused=None`、`fallback_reason=recheck-request-failed:170-171`。RED 原始证据见 `batch3_red_evidence.md`。修后保留验证段并只把该段交 full。
- 同族变体：覆盖首轮失败后重试成功、首轮失败后重试 mismatch、已有 mismatch 时其他失败段仍按工单完成末尾重试、canary 请求持续失败、canary counts changed、分页截断、worker 异常。
- 失败分支：持续失败段剔除；剔除补集函数注入异常时整体回退；案件区间全部落入 non-canary unverified 段时零 map-reuse 行、退化纯 full，发布和 `validate_coverage` 仍 PASS。

### 4. 新建代码自审（双视角）

- 视角①实现/会计：unverified 的边界只取自本轮调度的 `(start,end)` 与本轮 `part` 长度/异常结果，不读取 provider 自报范围决定剔除；清零后用 `_missing_ranges` 反算并与 excluded union 精确相等，不等即整体回退。最终 ledger union、scan_ranges union 与非零 counts 由现有 validator 闭合。
- 视角②攻击/旁路：尝试用 HTTP 529/429、成功但截断、worker 抛错、重试改值、canary 不可用、剔除 helper 抛错、案件子区间外 recheck、全案零复用等路径攻击。所有新分支方向均为“宁可多扫或整体回退，不得错用”；未发现可让 unverified slot 进入 map-reuse 声明的路径。

### 5. 归因

- 归因为 F-03 前单 fail-closed 粒度过粗的实用性残余，不是值校验代码错误。本批只调整“请求未知”的回退粒度，不放宽“数据可疑”的整体回退。

## 修改摘要

追踪文件 diff（报告文件为新增未跟踪文件，不计入下列 git diff）：

```text
 assets/sqd-solana-coverage-map/README.md  |   2 +-
 references/scan-schemas.md                |   9 +-
 scripts/solana/sqd_coverage_probe.py      | 148 +++++++++++---
 scripts/tests/test_f03_sharedmap_reuse.py | 328 +++++++++++++++++++++++++++++-
 4 files changed, 446 insertions(+), 41 deletions(-)
```

- FixtureTransport 仅新增 digest 级响应序列能力；普通单响应 fixture 行为不变。
- 生产语义集中在 recheck 分级/重试、复用补集/清零、map-reuse 逐段 ledger 三处。
- 测试新增/扩展后仍为一个 F-03 文件内 15 个组；未新增仓库 fixture 目录或大文件。

## §7.5 transport-only fake 登记

| 生产 callsite | 协议 | fake backend / loopback | 测试 ID | 允许理由 |
|---|---|---|---|---|
| `run_probe` → `_check_identity_anchor` / `_recheck_known_slots` / `_scan_ranges` → `FixtureTransport.call` | SQD `/head` 与 `/stream` 标准 body；fixture envelope=`sqd-coverage-transport-fixture-v1` | digest-addressed transport fake；同 digest 支持第 N 次响应序列；无 loopback server | `test_partial_rate_limit_end_to_end_full_repairs_failed_ranges`、`test_exclusion_failure_falls_back_and_case_can_degrade_to_pure_full` | 只替换 transport，真实执行 producer、并发 recheck、ledger、counts、publisher、pointer 和未改 validator；用于确定性模拟 529/429 两次失败后 full 成功 |
| `_load_known_map` → `_recheck_known_slots` → `FixtureTransport.call` | 同上 | 同上 | `test_retry_rescues_range_and_retry_mismatch_falls_back`、`test_canary_unavailable_and_canary_counts_changed_fall_back`、`test_truncated_and_worker_exception_ranges_are_unverified` | 必须让同一请求首轮/重试得到不同结果并覆盖 transport/截断/worker 分支；未伪造 PASS receipt，未绕过生产判定 |

## 验收摘要

```text
python3 -m py_compile scripts/solana/sqd_coverage_probe.py scripts/tests/test_f03_sharedmap_reuse.py
exit 0

python3 scripts/tests/test_f03_sharedmap_reuse.py
PASS F-03 shared-map reuse: 15/15 groups

python3 scripts/tests/test_sqd_coverage_probe.py
PASS SQD coverage probe: 12/12 offline groups

python3 scripts/tests/docs_lint.py
PASS: 45 个文档，引用无断链、粗体配对完整

python3 scripts/tests/test_contract_routes.py
PASS: R-01/R-02 注册表、ID 快照、五组锚与 SKILL 原子阶段双向闭合

python3 scripts/tests/invariant_scan.py
PASS invariant manifest: receipt_producers=75, receipt_consumers=112, transport_calls=65, atomic_writes=56, formal_entrypoints=61, exceptions=0

validate_shared_map(assets/sqd-solana-coverage-map/20260827.json)
{"ok": true, "reasons": []}

git diff --check
exit 0
```

## `run_all.py` 最终一次原始输出

命令：`python3 scripts/tests/run_all.py`

退出码：`1`

```text
--- test_batch3_solana_vertical_slice.py 完整输出 ---
Traceback (most recent call last):
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_batch3_solana_vertical_slice.py", line 646, in <module>
    raise SystemExit(main())
                     ~~~~^^
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_batch3_solana_vertical_slice.py", line 641, in main
    test_r9_solana_pythia_mainnet_vertical_slice()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/formal_capability_probes.py", line 145, in guarded
    return function(*args, **kwargs)
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_batch3_solana_vertical_slice.py", line 625, in test_r9_solana_pythia_mainnet_vertical_slice
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/socketserver.py", line 457, in __init__
    self.server_bind()
    ~~~~~~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/http/server.py", line 148, in server_bind
    socketserver.TCPServer.server_bind(self)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/socketserver.py", line 478, in server_bind
    self.socket.bind(self.server_address)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
PermissionError: [Errno 1] Operation not permitted

--- test_batch3_evm_vertical_slice.py 完整输出 ---
Traceback (most recent call last):
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_batch3_evm_vertical_slice.py", line 353, in <module>
    raise SystemExit(main())
                     ~~~~^^
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_batch3_evm_vertical_slice.py", line 344, in main
    test_r9_eth_mainnet_vertical_slice()
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/formal_capability_probes.py", line 145, in guarded
    return function(*args, **kwargs)
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_batch3_evm_vertical_slice.py", line 330, in test_r9_eth_mainnet_vertical_slice
    _run_registered_chain("eth")
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^^
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_batch3_evm_vertical_slice.py", line 281, in _run_registered_chain
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/socketserver.py", line 457, in __init__
    self.server_bind()
    ~~~~~~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/http/server.py", line 148, in server_bind
    socketserver.TCPServer.server_bind(self)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/socketserver.py", line 478, in server_bind
    self.socket.bind(self.server_address)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
PermissionError: [Errno 1] Operation not permitted

========================================================
      PASS  changelog_lint.py        PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 56 条 + 归档 139 条
      PASS  docs_lint.py --all       PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）
      PASS  labels_manifest.py       PASS: 9 个发布表与 manifest（2026-08-20 00:48:52）指纹一致
      PASS  invariant_scan.py        PASS invariant manifest: receipt_producers=75, receipt_consumers=112, 
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
      PASS  test_version_consistency.py PASS: M-03 version metadata consistent at 6.52.14
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
      PASS  test_handoff_manifest.py handoff_manifest 契约测试全部通过（68 项）
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
      PASS  test_repair_g1_text_hygiene.py PASS real repository: 348 tracked active files, zero hits
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
      PASS  test_lit_regression_f007.py SUMMARY: 15/15 PASS
      PASS  test_lit_regression_f008.py SUMMARY: 46/46 PASS
========================================================
2 项失败——修完再收工
```

## 工单外发现

1. `run_all.py` 当前实际 `len(SUITE)=139`；历史记忆中的 137 是 batch14/F-03b 登记前的旧总数。本报告按当前入口重算为 137 PASS / 2 FAIL。
2. 两项全量失败均为现有纵切片尝试绑定 loopback 时被当前沙箱拒绝，发生在业务逻辑执行前；这不是本批语义 PASS，也不能在本环境宣称 release 全绿。允许 loopback 的环境仍需补跑才能得到全量 exit 0。
3. 无其他工单外代码 finding。用户已有未跟踪 `workorder_batch3.md` 保持原样；未执行 commit、add、checkout、reset、merge、tag 或 push。

