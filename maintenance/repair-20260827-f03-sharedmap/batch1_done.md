# F-03 batch 1 completion report

## Baseline and boundary

- Frozen baseline verified before construction: branch `main`, HEAD `5156f6e9a51ac0235a6855033ed3f2b53fe35686`, VERSION `6.52.13`.
- No rebase, merge, commit, add, checkout, push, or other git write was executed. No network request was made.
- `VERSION`, `pyproject.toml`, `SKILL.md`, `CHANGELOG.md`, and `scripts/lib/producer_history.py` were not changed.
- The pre-existing untracked `workorder_batch1.md` was present at the opening status check and was not edited (final SHA-256 `621308ddd68cfd59a2593861b8cd72bd47faf3bedff2f58c5c98a871a50fbab9`).

## Five-column closeout

### 1. Invariant

PASS at the implemented boundary.

- Reuse now requires: exact endpoint fingerprint; exact stable metadata identity (`dataset_id`, `start_block`, `real_time`); no unknown metadata keys on either the stored normalized identity or the unwrapped current head response; consistent non-negative integer head aliases; non-regressing finalized head; map upper bound no later than the scan head; exact counts query-template hash; and a live-fixture historical-anchor block hash match.
- The current `finalized_head`, `number`, `height`, and current-head `hash` are dynamic observations and no longer participate in whole-dictionary equality.
- The historical anchor is independently requested with block number/hash fields. Its ledger row is `provider="SQD"`, `mode="identity-anchor"`, `counts_coverage=false`, with request/response hashes recorded from the actual fixture transport payload.
- Known slots remain `canary ∪ candidate ∪ refuted`. Only genuinely consecutive slots are combined. Separate ranges remain separate requests and ledger rows. `args.workers` controls `ThreadPoolExecutor` concurrency.
- Every recheck future is collected before a reuse decision. A timeout/transport failure, malformed or truncated response, worker exception, or byte mismatch rejects the entire reuse. Already completed rows remain in the ledger; `run_probe` clears reused counts and full-scans all missing slots.
- `identity-anchor` cannot enter coverage union: producer `_successful_coverage_range` and validator `_success_ranges` both require `counts_coverage is True`. No validator mode relaxation was needed. Actual recheck ranges retain `counts_coverage=true` only for their exact continuous boundaries.

### 2. Same-family inventory

Final command:

```text
rg -n "metadata_normalized|_load_known_map|validate_shared_map|known.map" scripts/
```

Relevant result classification:

- Reuse gate and callsite: `scripts/solana/sqd_coverage_probe.py:212,581,1113-1117` — repaired.
- Export side: `scripts/solana/sqd_coverage_probe.py:754` — verified by export→head-advance→reload roundtrip; production export code remained unchanged.
- Independent validator: `scripts/lib/solana_exact_validate.py:705` — repaired to the required depth.
- Shared `validate_coverage`: `scripts/lib/solana_exact_validate.py:452` — D1 historical producer admission repaired.
- Four consumption paths are still shared and were not individually changed: `scripts/solana/replay_edges.py:341`, `scripts/solana/sqd_gap_repair.py:374`, repair-bundle deep validation at `scripts/lib/solana_exact_validate.py:1478`, and reconcile deep validation at `scripts/lib/solana_exact_validate.py:2008`.
- Remaining grep hits are fixtures, documentation-facing metadata construction, or tests; none contains a second shared-map reuse decision.

### 3. Red/green test set

RED evidence is preserved at `maintenance/repair-20260827-f03-sharedmap/batch1_red_evidence.md`:

- Head 1000→1010 with stable identity unchanged: baseline rejected with `fallback_reason=metadata-changed`.
- Historical anchor hash mismatch: baseline had no anchor request, reused the map, and failed `assert reused is None`.

GREEN targeted output:

```text
{"probe_id": "fafd5fa6f7bce206", "status": "published", "verdict": "NO_KNOWN_NONCE_OMISSION_DETECTED"}
PASS F-03 shared-map reuse: 6/6 groups
```

The six groups cover head-forward/anchor success and exact gap boundaries; anchor mismatch; candidate count mismatch; concurrent request failure; stable/dynamic/unknown identity reasons including bool/negative/string heads; tracked-asset JSON-only pure identity admission; shared validator malformed inputs/UNSCANNED; and D1 current/history/random/REVOKED/protocol mismatch behavior.

Existing probe regression output ended:

```text
PASS SQD coverage probe: 12/12 offline groups
```

The lifecycle fixture now carries `dataset`, `metadata_sha256`, `finalized_head_at_scan`, `query_body_sha256`, and an anchor hash. The export roundtrip advances the current head from 1000 to 1010 with a new current hash and still reuses after the old-slot anchor matches.

Tracked asset hard gate was run against the complete triplet (including decompression/recomputation):

```text
True
[]
133916665 16739584
```

Its bytes remained unchanged:

```text
519005acf7742478c8b34bec42f86611d49f867d70ab6bd80aa13087976c85bb  assets/sqd-solana-coverage-map/20260827.blocks.bin.gz
475c73d92e807e2d060e6ffda080e404161908076edd5a0593e171e457257304  assets/sqd-solana-coverage-map/20260827.counts.bin.gz
94aba34ccd139eff904f00b54117e714fa53f47fbcd801c440d8e3cf5ac86642  assets/sqd-solana-coverage-map/20260827.json
```

Other focused gates passed: Python compilation, `git diff --check`, `docs_lint.py --all`, `test_contract_routes.py`, `invariant_scan.py`, `test_sqd_gap_repair.py`, `test_reconcile_v4_receipt.py`, `test_recon_fifth_check.py`, `test_batch7_validator_coverage_gaps.py`, and `test_batch2d_stream_tail.py`.

### 4. New-code six-lens self-review

Field-source lens:

- Stable identity is compared between the stored asset and the normalized current response, while unknown-key detection uses the unwrapped raw current head object so arrays/objects/null cannot disappear through `_normalize_metadata`.
- The asset anchor hash is only an expected value. The decisive observed hash comes from the current `transport.call("sqd-stream", anchor_body)` response. No stored self-attestation is treated as observed proof.
- Current finalized head comes from current raw aliases; `finalized_head_at_scan`, query-template hash, and old anchor hash come from the validated stored asset; endpoint identity comes from the current configured endpoint fingerprint.
- Recheck bytes come only from current SQD fixture transport responses and are compared slot-for-slot against decompressed stored counts.

Failure-branch lens:

- Identity checks return structured reasons rather than throwing. The outer `_load_known_map` catch records `shared_map.fallback_reason` and returns no reused bytes.
- Anchor transport failure, malformed shape, wrong number, missing hash, or hash mismatch all fail closed after an honest non-coverage ledger row is appended.
- Recheck transport/worker failure and short pagination fail the entire reuse; no completed subset authorizes reuse.
- `validate_shared_map` now guards non-object SQD/canary/slot lists, rejects bool and mixed scalar types before sorting, parses ISO time, rejects unknown UNSCANNED bytes, and returns reasons rather than exposing malformed-input exceptions.
- D1 accepts the current worktree producer or a hash returned by `historical_producer_hashes` for both coverage and pointer protocols. Hash-wide REVOKED precedence and protocol separation remain owned by `producer_history.py` and were tested without changing that file.

Conclusion: no self-reported field is promoted to live evidence, and every new exception/error path remains fail-closed.

### 5. Attribution

Confirmed: F-03 is “introduced during repair.” The shared-map feature added in the SQD coverage work treated a changing live head dictionary as immutable dataset identity and lacked a real lifecycle positive case. The new 1000→1010 head-forward tests close that process gap while the historical anchor prevents the relaxation from admitting a fork or different history.

## Diff summary by file

- `scripts/solana/sqd_coverage_probe.py`: explicit metadata key classes; pure identity/head/template gate; independent identity-anchor request/ledger row; gap-exact concurrent rechecks; raw head and workers passed from `run_probe`.
- `scripts/lib/solana_exact_validate.py`: current-or-ACTIVE-history producer admission for both protocols; complete shared-map identity, metadata, head, interval, UNSCANNED, candidate/refuted, ISO-time, and malformed-input checks.
- `scripts/tests/test_f03_sharedmap_reuse.py` (new): F-03 identity/anchor/concurrency/validator/D1 matrix.
- `scripts/tests/test_sqd_coverage_probe.py`: lifecycle fields and anchor fixtures; exact ledger ranges; export→advanced-head roundtrip.
- `scripts/tests/run_all.py`: registers the new F-03 guard.
- `assets/sqd-solana-coverage-map/README.md`: required SQD fields and plain-language stable/dynamic/unknown reuse contract.
- `references/scan-schemas.md`: metadata class semantics, mandatory scan head/query binding, and non-coverage identity-anchor ledger semantics.
- `scripts/tests/contract_manifest.json`, `scripts/tests/contract_ids_snapshot.json`: paired `CT-SQDGAP-35` registration.
- `maintenance/repair-20260827-f03-sharedmap/batch1_red_evidence.md`: immutable baseline RED transcript.
- `maintenance/repair-20260827-f03-sharedmap/batch1_done.md`: this closeout.

`scripts/tests/invariant_manifest.json` was not changed: the new call uses the already registered `FixtureTransport`/`LiveTransport` transport boundary, and invariant scan remained exactly `transport_calls=65`, `exceptions=0`.

## Transport fixture registration (§7.5)

| Field | Registration |
|---|---|
| Production callsite | `sqd_coverage_probe.py::_check_identity_anchor` → `transport.call("sqd-stream", sqd_identity_anchor_body(slot))`; rechecks continue through `_scan_request` → the same `sqd-stream` transport call |
| Protocol | `sqd-coverage-transport-fixture-v1`, digest-addressed kind `sqd-stream`; anchor body requests exactly `block.number` and `block.hash` |
| Fake backend | Existing `FixtureTransport`, backed by `responses.json`; no production transport bypass |
| Test IDs | `test_head_forward_anchor_and_gap_exact_rechecks`, `test_anchor_mismatch_is_not_ignored`, `test_recheck_mismatch_and_parallel_failure_fail_closed`, existing `test_shared_map_lifecycle_rechecks_all_known_and_canary`, existing `test_export_shared_map_roundtrip_and_tamper_rejection` |
| Allowed reason | The workorder prohibits networking and supplies the live feasibility evidence; digest fixtures exercise the exact production callsite, request body, response parser, ledger hashing, failure classes, and concurrency behavior offline |

## Full-suite raw result

Command:

```text
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py
```

Exit code: `1`. Suite size: 139. Result: 137 PASS / 2 FAIL. Both failures are the pre-existing sandbox loopback bind restriction and occur before business assertions.

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
      PASS  changelog_lint.py        PASS: 版本号唯一（豁免 2 组历史撞号存档）、顺序正确；活跃 55 条 + 归档 139 条
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
      PASS  test_version_consistency.py PASS: M-03 version metadata consistent at 6.52.13
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
      PASS  test_repair_g1_text_hygiene.py PASS real repository: 347 tracked active files, zero hits
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
      PASS  test_f03_sharedmap_reuse.py PASS F-03 shared-map reuse: 6/6 groups
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

## Workorder-external findings

- No new repository defect was found outside the workorder scope.
- The two full-suite failures are environmental loopback restrictions already known on this sandbox. They were not repaired or reclassified as PASS.

## Final handoff

- Current repaired probe SHA-256 for the second-segment producer-history/version registration: `98528b1c0a9098e3d88114b17a3390916c9b76e915b03b3350d47193cf358643`.
- Current validator SHA-256: `945de95278f65acbb6c779e047577c6042eb37cdcec00ebba2ddaba8cea4d68a`.
- The final worktree changes are limited to the workorder whitelist, plus the pre-existing untouched `workorder_batch1.md` inside the same maintenance directory.
