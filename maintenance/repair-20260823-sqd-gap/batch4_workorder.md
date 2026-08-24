# 批 4 工单（codex 施工）：消费端经 resolver ＋ 顺序语义闭合 ＋ `edge_source_binding` 写入 ＋ `--case-root` ＋ wave-scan/v5・flow-anomaly/v3 升版面（分支 fix/sqd-gap-v6520，基线 5782f76）

- 权威：PLAN §4.2.9（binding 与承载产物升版）、§4.3.3（同 slot 顺序语义）、§4.4.2（resolver 调用点与正式路径规则）、§4.5.2（wave/flow 升版影响面）；`PLAN_errata_batch0.md` E1–E27（优先）；契约草案 `edge-source-binding` 相关条目与 `references/scan-schemas.md` §14 对应节。
- 目标对齐：**所有 Solana 正式读边入口统一走 `sqd_cache_identity.resolve_formal_cache(mint, case_root)`**（批 3 已交付），读到 base 或当前修复代的合并缓存（缺陷 slot 已按参考非投票序号重排——顺序语义由此闭合）；每个 Solana 派生产物写入 `edge_source_binding{cache_kind,gid|null,soltx_edges_sha256,soltx_meta_sha256,edge_logical_sha256}`（resolver 返回的 binding 原样落盘）；wave/flow 升版承载；显式路径必须配 `--case-root`（拒 symlink、不猜 cwd）。**不碰 reconcile 收据 v4／wrapper v3／第五项／handoff AUTO_GATES 键名与 binding 全等检查（批 5）**。离线、不 commit、完成即停；锚文本不符即停工报告。
- 开工门禁：`git rev-parse --short HEAD` == 5782f76。

## 实况锚点（5782f76，已 grep）
- `scripts/solana/sqd_cache_identity.py`：`validate_cache_meta_v2(meta, mint, *, case_root, meta_path)` :178、`resolve_formal_cache(mint, case_root) -> (edge_path, meta_path, kind, gid, binding)` :250、`_binding` :118、`validate_repair_bundle` :127、legacy `validate_cache_meta` :30。
- `scripts/solana/replay_edges.py`：`load_edges(mint, *, legacy_sol5=False)` :172-201（cwd 相对 `data/soltx-<h>` 路径、`_validate_cache_meta` legacy 入口）；`cmd_reconcile` :292（**不动**，批 5）；`cmd_evolution` :437。
- `scripts/solana/curve_cost.py`：`load_edges(mint, data_dir=Path("data"))` :52-64（`soltx_cache_paths`＋legacy `validate_cache_meta`）。
- `scripts/solana/audit_closed_accounts.py`：`main` :243；`--edges` :246；默认 `soltx_cache_paths(mint, Path("data"))` :270。
- `scripts/report/wave_scan.py`：`SCHEMA = "wave-scan/v4"` :77；`load_sol(con, pattern, *, legacy_sol5=False, cache_meta_path=None, expected_mint=None)` :104-125（glob 任意文件＋legacy `validate_cache_meta`）；`--edges-sol` :601；docstring :39。
- `scripts/lib/wave_contract.py`：`WAVE_SCHEMA = "wave-scan/v4"` :3；`has_formal_wave_semantics` :19。
- `scripts/report/flow_anomaly_scan.py`：`SCHEMA = "flow-anomaly/v2"` :66；复用 `wave_scan.load_sol` :63/:195；docstring :10/:41。
- `scripts/report/entity_source_trace.py`：`load_sol` :745；`input_binding` :826；docstring :54。
- `scripts/lib/camp_series_provenance.py`：`RECONCILE_SCHEMA` :404（**不动**，批 5）；边文件路径/meta 校验段 :582-619（`validate_cache_meta` :593、`edge_file_size` :608-619）。
- `scripts/report/handoff_manifest.py`：wave 版本检查 :396-400（`WAVE_SCHEMA` 来自 wave_contract）、flow :426-428、提示句 :464；`AUTO_GATES` :97-99（**不动**，批 5）。
- `scripts/report/audit_release_gate.py`：wave-scan/v4 文案与判定 :839-854；`scripts/report/adjudication_validator.py`：`FLOW_SCHEMA = "flow-anomaly/v2"` :80、提示 :88/:93。
- 引用 v4/v2 的测试：`test_wave_scan.py`、`test_flow_anomaly.py`、`test_handoff_manifest.py`、`test_audit_release_gate.py`、`test_adjudication_validator.py`、`test_evm_observation_release.py`（:184/:191 fixture）、`test_repair_batch_d.py`（:986）、`test_entity_source_trace.py`、`test_sqd_consumer_v4.py`、`sqd_v4_test_fixture.py`；先红项所在：`test_reconcile_v4_receipt.py`／`test_recon_fifth_check.py`（本批只转 (2)(9)(22)(23) 相关项，其余留批 5——逐项核对 `batch1b_red_evidence.txt` 项号）。

## 白名单
1. `scripts/solana/replay_edges.py`：`load_edges(mint, *, legacy_sol5=False, case_root=None)`——`case_root` 给出且非 legacy ⇒ 经 `resolve_formal_cache`（返回 `(edges, meta_path, binding)`，调用点相应接收）；`case_root=None` 保留现行为（供批 5 前 `cmd_reconcile` 继续工作，但打印一次性 WARN"正式路径须 --case-root（批 5 强制）"）；`cmd_evolution` sidecar 写 `edge_source_binding`；CLI 加 `--case-root`（evolution 子命令必填，reconcile 子命令本批可选）。**`cmd_reconcile` 函数体与 receipt 字段一字不改。**
2. `scripts/solana/curve_cost.py`：`load_edges(mint, case_root)` 经 resolver；产物 JSON 写 `edge_source_binding`；CLI `--case-root` 必填（替代 `data_dir` 猜测；拒 symlink）。
3. `scripts/solana/audit_closed_accounts.py`：无 `--edges` 时必须 `--case-root` 经 resolver 并写 `edge_source_binding`；显式 `--edges` ⇒ 报告标 `formal:false`/`non_formal_source:"explicit-edges"`（仍走 legacy 校验）。
4. `scripts/report/wave_scan.py`：`SCHEMA="wave-scan/v5"`；`load_sol` 正式路径：必填 `case_root`＋`expected_mint`，经 `resolve_formal_cache` 取唯一边文件，`--edges-sol` glob 结果**必须恰为该文件**（多文件/不等 ⇒ exit 2）；`cache_meta_path` 若给出须等于 resolver 的 meta_path；返回 binding 并写入报告 `edge_source_binding`（EVM 产物省略该键）；CLI `--case-root`；docstring 与 `--edges-sol` help 同步。
5. `scripts/lib/wave_contract.py`：`WAVE_SCHEMA="wave-scan/v5"`；严格契约对 Solana 报告要求 `edge_source_binding` 五键齐全（EVM 不要求）；v4 一律按版本差异 fail-closed（提示重跑）。
6. `scripts/report/flow_anomaly_scan.py`：`SCHEMA="flow-anomaly/v3"`；经 `load_sol(case_root=…)` 写 `edge_source_binding`；CLI `--case-root`；docstring。
7. `scripts/report/entity_source_trace.py`：`load_sol(case_root=…)`；`input_binding` 增 `edge_source_binding`（或并入同名五键）；CLI `--case-root` 必填（Solana 路径）；docstring :54。
8. `scripts/lib/camp_series_provenance.py` :582-619：边文件/meta 定位改经 `resolve_formal_cache`（接受 base 或 repaired 对；kind 由 COLLECTORS 闭集推导）；sidecar `edge_source_binding` 与边源一致性检查（sidecar 有 binding 时须与 resolver binding 全等）；`edge_file_size/sha256` 来源：repaired meta 由生产者写出、base meta 沿用现行（批 5 改读 receipt.inputs）；`RECONCILE_SCHEMA` 不动。
9. `scripts/report/handoff_manifest.py` :396-400/:426-428/:464：wave 要求 `WAVE_SCHEMA`（v5）、flow 要求 `flow-anomaly/v3`，旧版提示重跑；`AUTO_GATES` 与 binding 全等检查不动（批 5）。
10. `scripts/report/audit_release_gate.py` :839-854、`scripts/report/adjudication_validator.py` :80/:88/:93：版本常量与文案升 v5/v3。
11. 测试与 fixture：上列全部引用 v4/v2 的测试按版本升级（fixture schema 字段改 v5/v3 并补 Solana `edge_source_binding`；EVM fixture 只改版本号）；先红项 **(2) 语义半边**（消费端经 resolver 读合并缓存：用批 3 fixture 产一个小 repaired 代，curve/entity 顺序模拟在 base 与 repaired 间结果不同且 repaired 与参考顺序一致）、**(9)** 六入口显式 base 路径绕 resolver 被拒（replay evolution／curve／wave／flow／entity／audit_closed；camp 归批 5 第二次核）、**(22)** wave v4/flow v2 旧产物被 v5/v3 验收拒、**(23)** 无 `--case-root` 或 symlink 案根被正式路径拒——由红转绿；新增 `scripts/tests/fixtures/`（≤200KB）按需。
12. `scripts/tests/invariant_manifest.json`：wave v5/flow v3 producer/consumer 代码点对齐到实现；登记 `sqd-solana-beta-trace/v1`（批 3b 发现项 #1）；**不得为绿删条目**。
13. `maintenance/repair-20260823-sqd-gap/batch4_done.md`＋`batch4_green_evidence.txt`：红→绿对照、`run_all.py` 全量与逐红项解释（预期仍红＝reconcile v4/receipt/第五项/handoff binding 相关＝批 5；沙箱回环 EPERM）、发现项、Fable 本机复验命令（在 ARC 案根跑 `wave_scan.py --case-root … --edges-sol … --mint …` 与 `flow_anomaly_scan.py`，产物含 binding 且 schema v5/v3；`curve_cost`/`audit_closed_accounts --case-root` 同）。
**不动**：`fetch_sqd_transfers_v2.py`、`spl_edge_core.py`（批 3 已加路径辅助，本批不改）、`sqd_gap_repair.py`/`sqd_repair_core.py`/`sqd_coverage_probe.py`、`replay_edges.cmd_reconcile`、`shared_release_receipt.py`/`reconciliation_report.py`（批 5）、`producer_history.py`、`run_all.py`、版本文件、references 文档、PLAN/errata/契约草案、contract_manifest（needle 已在批 1b）。

## 验收口径（Fable）
离线：定向测试绿、红→绿对照、`run_all.py` 红项只剩批 5 类；本机：ARC 案根跑 wave v5/flow v3/curve/audit_closed（resolver 解析 base，binding 写入、schema 升版），旧 v4 wave 产物被 handoff/adjudication 拒；(2) 语义测试产物检查。
