# F-03 批 1b 完工报告

## 基线与边界

- 开工基线为批 1 施工后的当前未提交工作树；`HEAD=5156f6e9a51ac0235a6855033ed3f2b53fe35686`。
- 本批没有执行 `add/commit/checkout/rebase/merge/push` 或其他 git 写操作，也没有联网。
- 本批只修改了点名实现段与点名测试，并新增本报告：
  - `scripts/solana/sqd_coverage_probe.py`
  - `scripts/lib/solana_exact_validate.py`
  - `scripts/tests/test_f03_sharedmap_reuse.py`
  - `maintenance/repair-20260827-f03-sharedmap/batch1b_done.md`
- 文档、契约、测试登记、tracked 资产及其他批 1 既有改动均未触碰。
- 权威工单 `workorder_batch1b.md` 只读，完工时 SHA-256 为 `d14a477f315bd3f51aa1c3da5d476965182369cfb56f87fa21524e41aa53746c`。

## 三项修复

### P1-1：复用失败后撤销本轮 recheck 覆盖声明

- `_load_known_map` 进入时记录 `ledger_start=len(ledger)`。
- 任一 fallback 进入统一 `except` 后，只遍历本轮新增区间 `ledger[ledger_start:]`，把所有 `mode="recheck"` 行的 `counts_coverage` 改为 `false`；行仍保留，`ok`、响应哈希和观测事实均不改。
- 成功复用路径不经过 fallback，recheck 行继续保持 `counts_coverage=true`。
- 覆盖消费者复核结论：producer `_successful_coverage_range`、发布前 `scan_ranges` 重建、validator `_success_ranges` 均同时要求 `ok is True` 和 `counts_coverage is True`；降级行自然退出覆盖并集，无需改 validator。
- 新增 run_probe 端到端守卫：资产 slot 180 为 3，recheck 返回 4，fallback full 返回 5；最终发布成功、`validate_coverage` 通过、recheck 行仍在且 `ok=true/counts_coverage=false`、`scan_ranges` 不含 recheck、最终 counts byte 为 5。

### P1-2：稳定身份严格类型，不要求真实 `/head` 补配置常量

- `_normalize_metadata` 保持零改动。
- `_validate_known_map_identity` 对资产和归一化当前值的三个稳定键执行严格形态校验：
  - `dataset_id`：精确 `str` 且非空；
  - `start_block`：精确 `int`、非 bool、非负；
  - `real_time`：精确 `bool`。
- 稳定值比较统一要求 `type(left) is type(right) and left == right`。
- 原始响应中的稳定键若在场，先按同一严格类型校验，再与资产严格比较；缺席允许，符合真实 SQD `/head` 只返回 `{number, hash}` 的形状。
- `validate_shared_map` 对资产 `metadata_normalized` 增加同深稳定身份校验，失败 reason 为 `shared map SQD stable identity invalid`。
- 新增负例覆盖原始 `start_block=false`、原始 `real_time="false"`、资产 `real_time=1`、资产缺 `dataset_id`；新增带解释注释的 `{number, hash}` 正例。

### P2-1：anchor transport 裸异常结构化并留账

- `_check_identity_anchor` 先构造 `ok=false/counts_coverage=false` 的 anchor 行，再把 `transport.call(...)` 和 HTTP 状态提取纳入 `try`。
- Result 失败与 transport 直接抛异常都追加同一类诚实审计行，并统一返回 `identity-anchor-request-failed`。
- 直接异常的 `error` 通过 `_safe_text` 脱敏；没有把裸异常文本提升为 fallback reason。

## RED 原始输出

测试先加在批 1 施工态，生产实现尚未修改时分别隔离运行。

### P1-1 RED

命令：

```text
PYTHONDONTWRITEBYTECODE=1 python3 -c "import sys;sys.path.insert(0,'scripts/tests');import test_f03_sharedmap_reuse as t;t.test_fallback_rechecks_removed_from_published_coverage()"
```

退出码：`1`

```text
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    import sys;sys.path.insert(0,'scripts/tests');import test_f03_sharedmap_reuse as t;t.test_fallback_rechecks_removed_from_published_coverage()
                                                                                       ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_f03_sharedmap_reuse.py", line 291, in test_fallback_rechecks_removed_from_published_coverage
    assert target_rows[0]["counts_coverage"] is False, target_rows[0]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: {'bytes': 90, 'counts_coverage': True, 'empty_response': False, 'from': 180, 'http_status': 200, 'mode': 'recheck', 'n_blocks': 1, 'ok': True, 'provider': 'SQD', 'query_body_sha256': '8e8913921652c062f50df9b8903b15a760ec69d95ded545eb88853a762bbef11', 'response_sha256': '8bb50c9402fcad927fafd15e46d6a8758f8cfe54d2160dc1ebdfb6ad3b525b13', 'returned_from': 180, 'returned_to': 180, 'seq': 4, 'slots_covered': 1, 'to': 180, 'ts': '2026-08-27T13:24:23.985029+00:00'}
{"probe_id": "8c88b505b305b919", "status": "published", "verdict": "NO_KNOWN_NONCE_OMISSION_DETECTED"}
```

### P1-2 RED

命令：

```text
PYTHONDONTWRITEBYTECODE=1 python3 -c "import sys;sys.path.insert(0,'scripts/tests');import test_f03_sharedmap_reuse as t;t.test_stable_identity_types_and_real_head_shape()"
```

退出码：`1`

```text
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    import sys;sys.path.insert(0,'scripts/tests');import test_f03_sharedmap_reuse as t;t.test_stable_identity_types_and_real_head_shape()
                                                                                       ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_f03_sharedmap_reuse.py", line 369, in test_stable_identity_types_and_real_head_shape
    assert _identity(asset, raw)["reason"] == "metadata-identity-changed"
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError
```

同一 RED 阶段的 validator 负例也失败：资产 `real_time=1` 时 reasons 只有 `shared map SQD metadata sha256 mismatch`，缺少 `shared map SQD stable identity invalid`。修复后该负例与资产缺 `dataset_id` 负例均转绿。

### P2-1 RED

命令：

```text
PYTHONDONTWRITEBYTECODE=1 python3 -c "import sys;sys.path.insert(0,'scripts/tests');import test_f03_sharedmap_reuse as t;t.test_anchor_transport_exception_is_structured_and_audited()"
```

退出码：`1`

```text
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    import sys;sys.path.insert(0,'scripts/tests');import test_f03_sharedmap_reuse as t;t.test_anchor_transport_exception_is_structured_and_audited()
                                                                                       ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_f03_sharedmap_reuse.py", line 202, in test_anchor_transport_exception_is_structured_and_audited
    assert info["fallback_reason"] == "identity-anchor-request-failed", info
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: {'asset_path': '/private/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/f03-anchor-raise-rrcwllut/map.json', 'version': '20260827', 'sha256': '024e9ba70739ee4c182c9cb79e98749644ff03ddcaf9036aebff8507076543cb', 'supersedes': None, 'generated_at': '2026-08-27T13:24:23.985574+00:00', 'reused_ranges': [], 'canary': {'slots': [], 'counts_sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'verified_at': '2026-08-27T13:24:23.985970+00:00'}, 'fallback_reason': 'fixture anchor timeout'}
```

## GREEN 输出

三项隔离测试退出码均为 `0`。完整 F-03 文件输出：

```text
{"probe_id": "6e1c34dbb7c974a1", "status": "published", "verdict": "NO_KNOWN_NONCE_OMISSION_DETECTED"}
{"probe_id": "28e89ba293b569fe", "status": "published", "verdict": "NO_KNOWN_NONCE_OMISSION_DETECTED"}
PASS F-03 shared-map reuse: 9/9 groups
```

相邻探针回归：

```text
PASS SQD coverage probe: 12/12 offline groups
```

Python 编译检查退出码 `0`；`git diff --check` 无输出。

## 实资产硬闸

命令：

```text
PYTHONDONTWRITEBYTECODE=1 python3 -c "import json,sys;sys.path.insert(0,'scripts/lib');from solana_exact_validate import validate_shared_map;r=validate_shared_map('assets/sqd-solana-coverage-map/20260827.json');print(json.dumps({'ok':r['ok'],'reasons':r['reasons']},ensure_ascii=False))"
```

退出码：`0`

```text
{"ok": true, "reasons": []}
```

确认实资产稳定身份仍为 `dataset_id="solana-mainnet"`（str）、`start_block=0`（int）、`real_time=true`（bool），新闸不误拒。

## Diff 摘要（仅批 1b 增量）

- `scripts/solana/sqd_coverage_probe.py`：新增两个严格身份直接辅助；加深 `_validate_known_map_identity` 稳定类型/严格比较；为 `_check_identity_anchor` 增加直接异常审计；在 `_load_known_map` fallback 降级本轮 recheck 覆盖声明。
- `scripts/lib/solana_exact_validate.py`：只在 `validate_shared_map` 的 SQD metadata 段增加三稳定键严格类型校验及结构化 reason。
- `scripts/tests/test_f03_sharedmap_reuse.py`：新增 P2-1 抛异常 fake、P1-1 run_probe 端到端、P1-2 严格类型和真实 `/head` 正例；validator 新增两项资产稳定身份负例；测试组从 6 增至 9。
- `maintenance/repair-20260827-f03-sharedmap/batch1b_done.md`：本报告。

没有重构，没有修改 `_normalize_metadata`，没有顺手改其他发现。

## §7.5 transport fake 登记

| 字段 | 登记 |
|---|---|
| Production callsite | `sqd_coverage_probe.py::_check_identity_anchor` → `transport.call("sqd-stream", sqd_identity_anchor_body(slot))` |
| Protocol | 既有 transport 抽象的 `sqd-stream`；请求体为 identity-anchor 的单 slot `block.number/hash` 查询 |
| Fake backend | 测试内 `RaisingAnchorTransport`，仅替换 transport；`call` 直接抛 `TimeoutError("fixture anchor timeout")` |
| Test ID | `test_anchor_transport_exception_is_structured_and_audited` |
| 允许理由 | 点名覆盖 Result 之外的直接抛异常分支，验证生产 callsite 会统一结构化 reason 并追加非覆盖 anchor ledger 行；不绕过生产函数，不联网 |

## 工单外发现清单

1. 全量仍有两项沙箱环境失败：Solana/EVM R9 vertical slice 都在 `ThreadingHTTPServer(("127.0.0.1", 0), ...)` 绑定时得到 `PermissionError: [Errno 1] Operation not permitted`。它们发生在业务断言前，与本批三项改动无调用关系；批 1 全量已有同样结果。本批按范围铁律只记录，不修。
2. 未发现其他新的工单外代码问题。

## 全量原始输出

命令：

```text
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py
```

退出码：`1`。结果：`137 PASS / 2 FAIL`。

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
      PASS  test_f03_sharedmap_reuse.py PASS F-03 shared-map reuse: 9/9 groups
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
